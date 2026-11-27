# WPILOG Reader — reusable parser for FRC 2026 log analyses

`claude/wpilog_reader.py` is the shared parser layer for this project. Every log
analysis reads the same AdvantageKit `.wpilog` files; instead of rebuilding a
parser each time, import this module and get straight to the analysis.

**For a future session:** the module lives in this project as `claude/wpilog_reader.py`.
`project_read` it, write it to the working directory, and `import wpilog_reader`.
It has **no third-party dependencies** — pure Python standard library.

## What it does (and doesn't)

It handles the *parsing* — opening the file, decoding the WPILOG binary format,
and turning a signal name into timestamped values. It does **not** do the analysis;
which signals to pull and what to compute is still per-question work. The point is
that the fiddly, error-prone binary decoding is written and tested once.

## API

```python
from wpilog_reader import WPILog

log = WPILog("akit_..._q23.wpilog")
log                                  # WPILog(version=1.0, entries=364, duration=433.8s)

log.entries("CANBus")                # list (name, type) pairs; arg = case-insensitive filter
log.has("/DriverStation/Enabled")    # bool
log.entry(name)                      # Entry(id, name, type, metadata)

t, v = log.series(name)              # two parallel lists, sorted by time; t in seconds
t, v = log.series(name, raw=True)    # skip decoding, get raw payload bytes per sample

# slice one signal by another via sample-and-hold (both must be time-ascending):
held = log.sample_hold(other_name, t)          # values of other_name held at each t
held = WPILog.latest_at(t2, v2, t)             # same, from arrays you already have

log.struct_schemas                   # {struct name: fields} for every schema in the log
log.t0, log.duration                 # seconds
```

### Decoded types

- `double`, `float`, `int64`, `boolean`, `string`, `json` (returned as the JSON
  string, not parsed), and their `[]` array forms.
- **`struct:X` and `struct:X[]`** (added Oct 2026) — decoded to nested dicts using
  the schemas the log itself carries under `/.schema/struct:X`, so no layouts are
  hard-coded. Supports nested structs, fixed arrays, `char` strings, enums and
  bit-fields. Field names are WPILib's schema names, for example:
  - `Pose2d` → `{'translation': {'x', 'y'}, 'rotation': {'value'}}` (meters, radians)
  - `SwerveModuleState[]` → `[{'speed', 'angle': {'value'}}, ...]` (m/s, radians)
  - `ChassisSpeeds` → `{'vx', 'vy', 'omega'}`
  - `Pose3d` → `{'translation': {'x','y','z'}, 'rotation': {'q': {'w','x','y','z'}}}`
  - Team vision structs: `PoseObservation` → `{'timestamp', 'pose' (Pose3d),
    'ambiguity', 'tagCount', 'averageTagDistance', 'type'}`, where `type` is an
    enum string (`MEGATAG_1` / `MEGATAG_2` / `PHOTONVISION`);
    `TargetObservation` → `{'tx', 'ty'}` (Rotation2d each).
  - Rotation `value` is radians and is **not** wrapped to ±π.
- `proto:*`, `raw`, and structs whose schema is missing from the log come back as
  raw `bytes`. Truncated log tails (common on power-loss) stop parsing cleanly.

Struct decoding was ported from the `wpilog2json` CLI in `tervay/log_reader`
(a fellow mentor's tool), keeping this module dependency-free.

**AdvantageKit logs a value only when it changes.** Signals like
`SwerveChassisSpeeds/Measured` are sparse while the robot sits still, so use
`sample_hold` to align signals rather than assuming a fixed 50 Hz rate.

## Common recipes

Slice a signal by enabled/disabled:

```python
t, util = log.series("/SystemStats/CANBus/Utilization")
enabled = log.sample_hold("/DriverStation/Enabled", t)
enabled_util  = [x for x, e in zip(util, enabled) if e is True]
disabled_util = [x for x, e in zip(util, enabled) if e is False]   # config-only load
```

Per-module wheel speed from measured swerve states:

```python
t, states = log.series("/RealOutputs/SwerveStates/Measured")
fl_speed = [s[0]["speed"] for s in states]         # module 0, m/s
fl_angle = [s[0]["angle"]["value"] for s in states] # radians
```

## Validation

**Primitive decoding** — re-derived Newton Q23
(`akit_26-04-30_16-15-39_newton_q23.wpilog`) and matched the existing
`can-bus-analysis.md` figures exactly:

| Metric | Reader | Writeup |
|---|---|---|
| Disabled baseline (mean) | 69.5% | 70% |
| Enabled mean | 77.4% | 77% |
| Enabled p95 | 91.3% | 92% |
| Peak | 100% | 100% |
| ReceiveErrorCount max | 128 | 128 (error-passive) |
| OffCount max | 0 | 0 (no bus-off) |
| TxFullCount max | 5 | >0 (tx overflow) |

The Oct 2026 struct change didn't touch the primitive code paths.

**Struct decoding (Oct 2026), synthetic logs:**

- Wrote 60 s at 250 Hz (15,000 samples each) of `Pose2d`, `Pose3d`,
  `ChassisSpeeds` and `SwerveModuleState[4]` using WPILib's own schemas and
  serializer (robotpy 2026.2.2). Decoded values matched the written objects.
- Exotic schema features (nested, enum, bit-fields, `char[]`, fixed arrays,
  schema written after the first data sample, missing schema) matched
  `wpilog2json`'s test expectations.
- All 90,006 samples across both logs, primitives included, were identical to
  `wpilog2json`'s output.

**Struct decoding (Oct 2026), real team logs:** all 10 logs from the
Oct 20, 2026 practice (`20261020Practice/`, ~59 min of robot time).

- 1,686,790 struct samples across 11 struct types (`Pose2d`, `Pose2d[]`, `Pose3d`,
  `Pose3d[]`, `Rotation2d`, `Rotation2d[]`, `Translation2d`, `ChassisSpeeds`,
  `SwerveModuleState[]`, `PoseObservation[]`, `TargetObservation`). None fell back
  to raw bytes.
- Every sample matched `wpilog2json`, except for one tail quirk in that tool.
  When a log ends mid-record, which is normal when robot power is cut, `wpilog2json`
  emits the last complete record twice. This reader emits it once, which is correct.
  It showed up in 4 of the 10 logs.
- Physics checks against plain-number signals (21-01-38 and 22-13-15 logs):
  - `SwerveStates/Measured[m].speed ÷ DriveVelocityRadPerSec` = 0.05080 m for all
    four modules, p1–p99 identical. That's exactly a 4" wheel.
  - Module angle equals `TurnPosition` exactly.
  - d/dt of `Gyro/YawPosition` (struct) vs `YawVelocityRadPerSec` (double): r = 0.996–0.997.
  - Accepted vision `Pose3d` quaternions all have |q| = 1.000000000.
  - The `PoseObservation.type` enum decodes to `MEGATAG_1`/`MEGATAG_2` in roughly equal counts.
- Speed: the largest log (74 MB, 15 min) opens in ~6 s and decodes all 55 struct
  entries in ~6 s.

Side observation, not a decoder issue and not yet investigated:
`ChassisSpeeds/Measured.omega` vs gyro yaw rate correlates only r ≈ 0.65. The overall
slope is ~0.9–1.0, so the units are consistent. During fast spins (|ω| > 2 rad/s),
though, wheel-derived ω runs ~1.65× the gyro. Possible causes are wheel slip, a
geometry constant, or timing (r improves when the gyro is shifted ~60 ms). Worth a
look under the drive self-check / wheel-slip work.

## Useful signal names (from the 2026 logs)

- `/SystemStats/CANBus/Utilization` (float, 0–1, ~2 Hz)
- `/SystemStats/CANBus/ReceiveErrorCount`, `.../TransmitErrorCount`, `.../OffCount`, `.../TxFullCount` (int64)
- `/SystemStats/BatteryVoltage`, `/SystemStats/BrownedOut`
- `/DriverStation/Enabled` (boolean)
- `/RealOutputs/Shooter/Is*Connected` and other `/RealOutputs/...` subsystem signals
- Drive inputs: `/Drive/Module{0-3}/DriveVelocityRadPerSec`, `.../TurnPosition`
  (Rotation2d), `/Drive/Gyro/YawPosition` (Rotation2d), `/Drive/Gyro/YawVelocityRadPerSec`
- Drive outputs: `/RealOutputs/SwerveStates/Measured|Setpoints|SetpointsOptimized`
  (`SwerveModuleState[]`), `/RealOutputs/SwerveChassisSpeeds/Measured|Setpoints`
  (`ChassisSpeeds`), `/RealOutputs/Odometry/Robot` (`Pose2d`), `/RealOutputs/Quest/CurrentPose`
- Vision: `/Vision/Camera{0-2}/PoseObservations` (`PoseObservation[]`),
  `/RealOutputs/Vision/Camera{0-2}/RobotPosesAccepted|Rejected` (`Pose3d[]`)

Use `log.entries()` with a substring filter to discover the rest per file.
