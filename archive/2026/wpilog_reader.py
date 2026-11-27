"""
wpilog_reader.py — a small, dependency-free reader for WPILOG / AdvantageKit logs.

Purpose
-------
FRC 2026 Robot log analyses all read the same `.wpilog` binary files. This module
is the reusable *parser layer*: it turns a raw log into named, timestamped signal
series so each analysis can skip the boilerplate and get straight to the question.

Format reference
----------------
Implements the WPILib Data Log format (v1.0):
  Header:  b"WPILOG" | u16 version (LE) | u32 extra-header length | extra header
  Records: 1 header byte (length bitfield) | entry-id | payload-size | timestamp(us) | payload
    header byte bits:  id_len   = (b        & 0x3) + 1   (1-4 bytes)
                       size_len = ((b >> 2) & 0x3) + 1   (1-4 bytes)
                       ts_len   = ((b >> 4) & 0x7) + 1   (1-8 bytes)
  Control records (entry id == 0):
    byte0 = 0  Start:   u32 entry-id, str name, str type, str metadata
    byte0 = 1  Finish:  u32 entry-id
    byte0 = 2  SetMeta: u32 entry-id, str metadata
  (str = u32 length + UTF-8 bytes)

Struct values (WPILib "packed struct" serialization) are decoded using the schemas
the log itself carries under `/.schema/struct:<Name>`, so geometry and kinematics
types (Pose2d, Rotation2d, SwerveModuleState[], ChassisSpeeds, ...) come back as
nested dicts with no hard-coded layouts.

Quick start
-----------
    from wpilog_reader import WPILog

    log = WPILog("akit_..._q23.wpilog")

    # discover what's in the file
    for name, typ in log.entries("CANBus"):
        print(typ, name)

    # pull a signal: two parallel lists, sorted by time
    t, util = log.series("/SystemStats/CANBus/Utilization")   # t in seconds

    # slice by another (boolean) signal via sample-and-hold
    enabled = log.sample_hold("/DriverStation/Enabled", t)
    enabled_util  = [v for v, e in zip(util, enabled) if e is True]
    disabled_util = [v for v, e in zip(util, enabled) if e is False]

    # struct signals decode to dicts
    t, states = log.series("/RealOutputs/SwerveStates/Measured")
    states[0]   # [{'speed': 1.2, 'angle': {'value': 0.31}}, ... x4]

Notes
-----
* Whole file is read into memory; typical match logs (tens of MB) are fine.
* Decoded: double/float/int64/boolean/string/json + their arrays, and struct:X /
  struct:X[] (nested structs, fixed arrays, char strings, enums, bit-fields).
  protobuf, raw, and structs whose schema isn't in the log come back as raw bytes.
  Pass raw=True to series() to always get raw bytes.
* json entries are returned as the JSON *string* (not parsed), as before.
* Times are returned in seconds (FPGA microseconds / 1e6). Use `log.t0` /
  `log.duration` if you want them relative to the first record.

Struct decoding is adapted from tervay/log_reader (wpilog2json.py).
"""

import re
import struct
from typing import Any, Callable, Dict, List, Optional, Tuple

SCHEMA_PREFIX = "/.schema/struct:"

# struct schema primitive type -> Python struct format char
_PRIMS = {
    "bool": "?", "char": "c",
    "int8": "b", "uint8": "B", "int16": "h", "uint16": "H",
    "int32": "i", "uint32": "I", "int64": "q", "uint64": "Q",
    "float": "f", "float32": "f", "double": "d", "float64": "d",
}

# One schema declaration, e.g.  "double x"  "Rotation2d angle"  "uint8 a:3"
# "char name[8]"  "enum {OFF=0, ON=1} int8 mode"
_DECL = re.compile(
    r"(?:(?:enum)?\s*\{(?P<enum>[^}]*)\})?\s*(?P<type>\w+)\s+(?P<name>\w+)\s*"
    r"(?:\[\s*(?P<count>\d+)\s*\]|:\s*(?P<bits>\d+))?"
)

# parsed field: (type, name, array_count or None, bit_width or 0, {int: enum_name})
Field = Tuple[str, str, Optional[int], int, Dict[int, str]]


class WPILogError(Exception):
    pass


class Entry:
    __slots__ = ("id", "name", "type", "metadata")

    def __init__(self, entry_id: int, name: str, type_str: str, metadata: str):
        self.id = entry_id
        self.name = name
        self.type = type_str
        self.metadata = metadata

    def __repr__(self) -> str:
        return f"Entry(id={self.id}, name={self.name!r}, type={self.type!r})"


def _read_uint_le(data: bytes, pos: int, length: int) -> int:
    val = 0
    for i in range(length):
        val |= data[pos + i] << (8 * i)
    return val


# ---- struct schema parsing / decoding -----------------------------------------

def parse_struct_schema(text: str) -> List[Field]:
    """Parse a WPILib struct schema string (fields separated by ';')."""
    fields: List[Field] = []
    for decl in text.split(";"):
        m = _DECL.fullmatch(decl.strip())
        if not m:
            continue
        pairs = [p.split("=") for p in (m["enum"] or "").split(",") if p.strip()]
        enum = {int(v): k.strip() for k, v in pairs}
        count = int(m["count"]) if m["count"] else None
        fields.append((m["type"], m["name"], count, int(m["bits"] or 0), enum))
    return fields


def decode_struct(schemas: Dict[str, List[Field]], name: str, data: bytes,
                  pos: int = 0) -> Tuple[Dict[str, Any], int]:
    """Decode one `name` struct from data[pos:]. Returns (dict, new_pos).
    Raises KeyError if a needed schema is missing, struct.error if data is short."""
    out: Dict[str, Any] = {}
    bucket = None  # [unit_size_bytes, unit_value, bits_used] for packed bit-fields
    for ftype, fname, count, bits, enum in schemas[name]:
        if bits:
            size = struct.calcsize(_PRIMS[ftype])
            if (not bucket or bucket[2] + bits > bucket[0] * 8
                    or (ftype != "bool" and bucket[0] != size)):
                bucket = [size, int.from_bytes(data[pos:pos + size], "little"), 0]
                pos += size
            value = (bucket[1] >> bucket[2]) & ((1 << bits) - 1)
            bucket[2] += bits
            if _PRIMS[ftype].islower() and value >> (bits - 1):  # signed: sign-extend
                value -= 1 << bits
            out[fname] = bool(value) if ftype == "bool" else enum.get(value, value)
            continue
        bucket = None
        if ftype == "char":
            n = count or 1
            out[fname] = data[pos:pos + n].rstrip(b"\0").decode("utf-8", "replace")
            pos += n
        elif ftype in _PRIMS:
            fmt = f"<{count or 1}{_PRIMS[ftype]}"
            vals = [enum.get(v, v) for v in struct.unpack_from(fmt, data, pos)]
            pos += struct.calcsize(fmt)
            out[fname] = vals if count else vals[0]
        else:  # nested struct
            vals = []
            for _ in range(count or 1):
                v, pos = decode_struct(schemas, ftype, data, pos)
                vals.append(v)
            out[fname] = vals if count else vals[0]
    return out, pos


# ---- reader ---------------------------------------------------------------------

class WPILog:
    """Parsed WPILOG file. See module docstring for usage."""

    def __init__(self, path: str):
        with open(path, "rb") as f:
            self._data = f.read()
        self._entries_by_id: Dict[int, Entry] = {}          # entry id -> latest Entry
        self._records_by_id: Dict[int, List[Tuple[int, bytes]]] = {}  # id -> [(ts_us, payload)]
        self._name_to_ids: Dict[str, List[int]] = {}        # name -> [entry ids], in order seen
        self._schemas: Optional[Dict[str, List[Field]]] = None   # built lazily
        self._struct_decoders: Dict[str, Callable[[bytes], Any]] = {}
        self.extra_header: str = ""
        self.version: Tuple[int, int] = (0, 0)              # (major, minor)
        self._parse()

    # ---- parsing -------------------------------------------------------------

    def _parse(self) -> None:
        data = self._data
        if data[0:6] != b"WPILOG":
            raise WPILogError("Not a WPILOG file (bad magic bytes)")
        ver = data[6] | (data[7] << 8)
        self.version = (ver >> 8, ver & 0xFF)
        extra_len = struct.unpack_from("<I", data, 8)[0]
        pos = 12
        self.extra_header = data[pos:pos + extra_len].decode("utf-8", "replace")
        pos += extra_len

        n = len(data)
        while pos < n:
            header_byte = data[pos]
            pos += 1
            id_len = (header_byte & 0x3) + 1
            size_len = ((header_byte >> 2) & 0x3) + 1
            ts_len = ((header_byte >> 4) & 0x7) + 1
            if pos + id_len + size_len + ts_len > n:
                break  # truncated tail (common on power-loss); stop cleanly
            entry_id = _read_uint_le(data, pos, id_len); pos += id_len
            payload_size = _read_uint_le(data, pos, size_len); pos += size_len
            timestamp = _read_uint_le(data, pos, ts_len); pos += ts_len
            if pos + payload_size > n:
                break
            payload = data[pos:pos + payload_size]; pos += payload_size
            if entry_id == 0:
                self._handle_control(payload)
            else:
                self._records_by_id.setdefault(entry_id, []).append((timestamp, payload))

    def _handle_control(self, payload: bytes) -> None:
        if not payload:
            return
        ctype = payload[0]
        if ctype == 0:  # Start
            entry_id = struct.unpack_from("<I", payload, 1)[0]
            pos = 5
            name, pos = self._read_str(payload, pos)
            type_str, pos = self._read_str(payload, pos)
            metadata, pos = self._read_str(payload, pos)
            self._entries_by_id[entry_id] = Entry(entry_id, name, type_str, metadata)
            ids = self._name_to_ids.setdefault(name, [])
            if entry_id not in ids:
                ids.append(entry_id)
        # Finish (1) and SetMetadata (2) don't affect reading; ignored.

    @staticmethod
    def _read_str(payload: bytes, pos: int) -> Tuple[str, int]:
        length = struct.unpack_from("<I", payload, pos)[0]
        pos += 4
        s = payload[pos:pos + length].decode("utf-8", "replace")
        return s, pos + length

    # ---- struct support ------------------------------------------------------

    @property
    def struct_schemas(self) -> Dict[str, List[Field]]:
        """{struct name: parsed fields} for every schema stored in the log.
        Schemas are read from all records, so a schema written after the first
        data sample of an entry still applies to it."""
        if self._schemas is None:
            schemas: Dict[str, List[Field]] = {}
            for name, ids in self._name_to_ids.items():
                if not name.startswith(SCHEMA_PREFIX):
                    continue
                for eid in ids:
                    for _, payload in self._records_by_id.get(eid, []):
                        schemas[name[len(SCHEMA_PREFIX):]] = parse_struct_schema(
                            payload.decode("utf-8", "replace"))
            self._schemas = schemas
        return self._schemas

    def _struct_decoder(self, type_str: str) -> Callable[[bytes], Any]:
        dec = self._struct_decoders.get(type_str)
        if dec is not None:
            return dec
        schemas = self.struct_schemas
        sname = type_str[len("struct:"):]
        is_array = sname.endswith("[]")
        if is_array:
            sname = sname[:-2]

        def decode(payload: bytes) -> Any:
            try:
                if not is_array:
                    return decode_struct(schemas, sname, payload)[0]
                out, pos = [], 0
                while pos < len(payload):
                    v, new_pos = decode_struct(schemas, sname, payload, pos)
                    if new_pos <= pos:  # zero-size schema; avoid infinite loop
                        break
                    out.append(v)
                    pos = new_pos
                return out
            except (KeyError, ValueError, TypeError, struct.error):
                return payload  # schema missing or data malformed -> raw bytes

        self._struct_decoders[type_str] = decode
        return decode

    # ---- value decoding ------------------------------------------------------

    def _decode(self, type_str: str, payload: bytes) -> Any:
        t = type_str
        if t == "double":
            return struct.unpack("<d", payload)[0] if len(payload) >= 8 else None
        if t == "float":
            return struct.unpack("<f", payload)[0] if len(payload) >= 4 else None
        if t == "int64":
            return struct.unpack("<q", payload)[0] if len(payload) >= 8 else None
        if t == "boolean":
            return payload[0] != 0 if payload else None
        if t in ("string", "json"):
            return payload.decode("utf-8", "replace")
        if t == "boolean[]":
            return [b != 0 for b in payload]
        if t == "int64[]":
            c = len(payload) // 8
            return list(struct.unpack("<%dq" % c, payload[:c * 8]))
        if t == "double[]":
            c = len(payload) // 8
            return list(struct.unpack("<%dd" % c, payload[:c * 8]))
        if t == "float[]":
            c = len(payload) // 4
            return list(struct.unpack("<%df" % c, payload[:c * 4]))
        if t == "string[]":
            count = struct.unpack_from("<I", payload, 0)[0]
            pos = 4
            out = []
            for _ in range(count):
                s, pos = self._read_str(payload, pos)
                out.append(s)
            return out
        if t.startswith("struct:"):
            return self._struct_decoder(t)(payload)
        # proto:*, raw, or anything unrecognized -> raw bytes
        return payload

    # ---- public API ----------------------------------------------------------

    def entries(self, pattern: Optional[str] = None) -> List[Tuple[str, str]]:
        """List (name, type) pairs, sorted. `pattern` is a case-insensitive substring filter."""
        out = []
        for name, ids in self._name_to_ids.items():
            type_str = self._entries_by_id[ids[-1]].type if ids else ""
            if pattern is None or pattern.lower() in name.lower():
                out.append((name, type_str))
        return sorted(out)

    def has(self, name: str) -> bool:
        return name in self._name_to_ids

    def entry(self, name: str) -> Entry:
        ids = self._name_to_ids.get(name)
        if not ids:
            raise KeyError(f"No entry named {name!r}")
        return self._entries_by_id[ids[-1]]

    def series(self, name: str, raw: bool = False) -> Tuple[List[float], List[Any]]:
        """
        Return (times_seconds, values) for a signal, merged across any reused entry
        ids and sorted ascending by time. Pass raw=True to skip decoding and get the
        raw payload bytes for each sample.
        """
        ids = self._name_to_ids.get(name)
        if not ids:
            raise KeyError(f"No entry named {name!r} (use .entries() to list what's available)")
        recs: List[Tuple[int, str, bytes]] = []
        for eid in ids:
            type_str = self._entries_by_id[eid].type
            for ts, payload in self._records_by_id.get(eid, []):
                recs.append((ts, type_str, payload))
        recs.sort(key=lambda r: r[0])
        times = [ts / 1_000_000.0 for ts, _, _ in recs]
        if raw:
            values: List[Any] = [payload for _, _, payload in recs]
        else:
            values = [self._decode(type_str, payload) for _, type_str, payload in recs]
        return times, values

    @staticmethod
    def latest_at(times: List[float], values: List[Any], query_times: List[float]) -> List[Any]:
        """Sample-and-hold: for each t in query_times, the most recent value at or before t
        (None before the first sample). Both inputs must be ascending in time."""
        out = []
        j = 0
        n = len(times)
        cur = None
        for qt in query_times:
            while j < n and times[j] <= qt:
                cur = values[j]
                j += 1
            out.append(cur)
        return out

    def sample_hold(self, name: str, at_times: List[float]) -> List[Any]:
        """Values of signal `name` held at each timestamp in `at_times` (ascending).
        Handy for slicing one signal by another, e.g. by /DriverStation/Enabled."""
        t, v = self.series(name)
        return self.latest_at(t, v, at_times)

    @property
    def t0(self) -> float:
        """Earliest timestamp across all data records, in seconds (0.0 if empty)."""
        best = None
        for recs in self._records_by_id.values():
            if recs:
                first = recs[0][0]  # records appended in file order (ascending ts)
                best = first if best is None else min(best, first)
        return (best or 0) / 1_000_000.0

    @property
    def duration(self) -> float:
        """Span from first to last data record, in seconds."""
        lo = hi = None
        for recs in self._records_by_id.values():
            for ts, _ in recs:
                lo = ts if lo is None else min(lo, ts)
                hi = ts if hi is None else max(hi, ts)
        if lo is None:
            return 0.0
        return (hi - lo) / 1_000_000.0

    def __repr__(self) -> str:
        return (f"WPILog(version={self.version[0]}.{self.version[1]}, "
                f"entries={len(self._name_to_ids)}, duration={self.duration:.1f}s)")
