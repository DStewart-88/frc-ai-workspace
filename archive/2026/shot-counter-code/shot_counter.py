#!/usr/bin/env python3
"""Count balls shot per match from AdvantageKit .wpilog files.

Same detection logic as ShotDetector.java on the robot, so it can be run on old logs (the whole
2026 season) and used to tune the settings before changing robot code.

Usage:
    python3 shot_counter.py LOG_OR_FOLDER [LOG_OR_FOLDER ...] [--csv out.csv] [--lockout 0.10]

Needs numpy and wpilog.py (in this folder).

How it works, in one paragraph: every ball that goes through the shooter pulls the flywheel speed
down for about 0.1 s. While the shoot command is running and the feeder gate is open, the script
watches the flywheel's tracking error (measured speed minus setpoint) and counts a ball each time
that error drops sharply. Shots are put in three buckets by what the trajectory solver was aiming
at: Hub (scoring), ShuttleMid (shuttle target from the neutral zone) and ShuttleFull (shuttle
target from the opponent's zone, setpoint 100 rps).

Logs from before NECMP (March events) don't have RobotContainer/OnTargetRobot,
RobotContainer/IsShooting or TrajectorySolver/IsTargetingHub, so they are skipped.
"""
import argparse
import csv
import glob
import os
import sys
from collections import deque

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wpilog  # noqa: E402

DT = 0.02  # resample grid; matches the 50 Hz robot loop

SIGNALS = {
    "enabled": ("/DriverStation/Enabled", "b"),
    "auto": ("/DriverStation/Autonomous", "b"),
    "matchtime": ("/DriverStation/MatchTime", "d"),
    "v": ("/RealOutputs/Shooter/Velocity", "d"),
    "sp": ("/RealOutputs/Trajectory/ShooterSpeed", "d"),
    "gate": ("/RealOutputs/RobotContainer/OnTargetRobot", "b"),
    "shoot": ("/RealOutputs/RobotContainer/IsShooting", "b"),
    "hub": ("/RealOutputs/TrajectorySolver/IsTargetingHub", "b"),
    "fullfield": ("/RealOutputs/TrajectorySolver/IsFullField", "b"),  # new key; older logs: sp==100
}
REQUIRED = ("enabled", "v", "sp", "gate", "shoot", "hub")


class Config:
    dip = 1.5            # rps drop below recent peak that counts as a ball
    rearm = 0.75         # rps recovery from the dip bottom before the next ball can count
    lockout = 0.10       # s minimum between counted balls (main calibration knob)
    vmin = 10.0          # rps; nothing counted below this
    overspeed = 2.0      # rps; peak above setpoint by more than this = braking, not a ball
    below = 0.75         # rps; dip must take the speed this far under setpoint
    hangover = 0.30      # s; keep looking this long after the gate closes
    window = 0.20        # s; how far back the peak is taken from


def detect(t, v, sp, shooter_on, gate_open, cfg=Config):
    """Return indices of detected shots. Mirrors ShotDetector.update() line for line."""
    events = []
    buf = deque()
    in_dip = False
    trough = 0.0
    last_shot = -1e9
    last_gate = -1e9
    for i in range(len(t)):
        if gate_open[i]:
            last_gate = t[i]
        armed = shooter_on[i] and (t[i] - last_gate) <= cfg.hangover and v[i] > cfg.vmin
        if not armed:
            buf.clear()
            in_dip = False
            continue
        e = v[i] - sp[i]
        if in_dip:
            trough = min(trough, e)
            if e - trough >= cfg.rearm:
                in_dip = False
                buf.clear()
            else:
                continue
        while buf and buf[0][0] < t[i] - cfg.window:
            buf.popleft()
        peak = max([x[1] for x in buf] + [e])
        buf.append((t[i], e))
        if (peak - e >= cfg.dip and peak <= cfg.overspeed and e <= -cfg.below
                and t[i] - last_shot >= cfg.lockout):
            events.append(i)
            last_shot = t[i]
            in_dip = True
            trough = e
    return np.array(events, dtype=int)


def zoh(ts, vs, tq):
    if len(ts) == 0:
        return np.full(len(tq), np.nan)
    i = np.clip(np.searchsorted(ts, tq, side="right") - 1, 0, len(ts) - 1)
    out = vs[i].astype(float)
    out[tq < ts[0]] = 0.0
    return out


def load(path):
    names = {n for n, _ in SIGNALS.values()}
    ents = wpilog.read_log(path, keep=lambda n, t: n in names)
    raw = {}
    for k, (n, ty) in SIGNALS.items():
        e = ents.get(n)
        if e is None or not e.records:
            raw[k] = None
            continue
        ts = np.array([r[0] for r in e.records]) / 1e6
        if ty == "b":
            vs = np.array([1.0 if r[1][0] else 0.0 for r in e.records])
        else:
            vs = np.array([wpilog.dec_double(r[1]) for r in e.records])
        raw[k] = (ts, vs)
    missing = [k for k in REQUIRED if raw[k] is None]
    if missing:
        return None, missing
    tmax = max(r[0][-1] for r in raw.values() if r is not None)
    tq = np.arange(0.0, tmax, DT)
    d = {"t": tq}
    for k in SIGNALS:
        d[k] = zoh(*raw[k], tq) if raw[k] is not None else np.zeros(len(tq))
    if raw["fullfield"] is None:
        d["fullfield"] = (d["sp"] >= 99.5).astype(float)  # TrajectorySolver uses exactly 100 there
    return d, []


def bursts(times, gap=0.6):
    out = []
    for x in times:
        if out and x - out[-1][-1] < gap:
            out[-1].append(x)
        else:
            out.append([x])
    return out


CATS = ("Hub", "ShuttleMid", "ShuttleFull")


def analyze(d, cfg=Config):
    t = d["t"]
    en = d["enabled"] > 0.5
    auto = d["auto"] > 0.5
    on = en & (d["shoot"] > 0.5)
    gate = on & (d["gate"] > 0.5)
    cat = np.where(d["hub"] > 0.5, 0, np.where(d["fullfield"] > 0.5, 2, 1))
    ev = detect(t, d["v"], d["sp"], on, gate, cfg)
    r = {}
    for c, name in enumerate(CATS):
        sel = ev[cat[ev] == c]
        r[name + "_auto"] = int(np.sum(auto[sel]))
        r[name + "_teleop"] = int(np.sum(~auto[sel]))
        r[name + "_total"] = len(sel)
        feed = float(np.sum(gate & (cat == c)) * DT)
        trig = float(np.sum(on & (cat == c)) * DT)
        r[name + "_feed_s"] = round(feed, 1)
        r[name + "_trigger_s"] = round(trig, 1)
        r[name + "_bps_feed"] = round(len(sel) / feed, 2) if feed > 1 else None
        r[name + "_bps_trigger"] = round(len(sel) / trig, 2) if trig > 1 else None
        b = [x for x in bursts(t[sel]) if len(x) >= 4]
        bt = sum(x[-1] - x[0] for x in b)
        r[name + "_bps_flow"] = round(sum(len(x) - 1 for x in b) / bt, 2) if bt > 0.5 else None
    r["total"] = len(ev)
    return r, ev


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--csv", help="write one row per log to this CSV")
    ap.add_argument("--lockout", type=float, default=Config.lockout)
    ap.add_argument("--dip", type=float, default=Config.dip)
    args = ap.parse_args()
    Config.lockout = args.lockout
    Config.dip = args.dip

    files = []
    for p in args.paths:
        files += sorted(glob.glob(os.path.join(p, "*.wpilog"))) if os.path.isdir(p) else [p]

    rows = []
    print(f"{'log':48s} {'hub a/t':>9s} {'mid':>4s} {'full':>4s} {'total':>5s}  {'hub BPS feed/flow':>17s}")
    for f in files:
        if os.path.getsize(f) < 1_000_000:
            continue
        d, missing = load(f)
        if d is None:
            print(f"{os.path.basename(f):48s} skipped (no {', '.join(missing)})")
            continue
        r, _ = analyze(d)
        if r["total"] == 0 and r["Hub_feed_s"] == 0:
            continue
        r = {"log": os.path.basename(f), **r}
        rows.append(r)
        bf = r["Hub_bps_feed"] or 0
        bfl = r["Hub_bps_flow"] or 0
        print(f"{r['log']:48s} {r['Hub_auto']:4d}/{r['Hub_teleop']:<4d} {r['ShuttleMid_total']:4d} "
              f"{r['ShuttleFull_total']:4d} {r['total']:5d}  {bf:8.2f} / {bfl:5.2f}")
    if args.csv and rows:
        with open(args.csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print("wrote", args.csv)


if __name__ == "__main__":
    main()
