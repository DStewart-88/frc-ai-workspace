# Flashpoint trial on Team 88 logs (Nov 8, 2026)

Tried Ignite Robotics' Flashpoint 0.1.0 (github.com/IgniteRobotics/flashpoint) as an existing alternative to building the planned log processor ("Pitwall", see `claude/log-processor-framework.md`). Test match: **Newton Q23** (wpilog + Drivetrain CANivore hoot + rio hoot). Files saved to Doug's `FRC Logs/Claude outputs/flashpoint-trial/` (robot file, AdvantageKit shim, screenshot).

## What it took to run
1. `pip install flashpoint` — fine, but **Flashpoint 0.1.0 crashes on DuckDB 2.0** during derive (`Relation.fetchone()` removed). Pin `duckdb<2`.
2. **owlet** (CTRE hoot converter) is downloaded on first use from redist.ctr-electronics.com. Blocked in the cloud workspace; Doug downloaded `owlet-26.3.0-linuxx86-64` (2026 hoots are format C19). SHA-256 matched Flashpoint's manifest. The Linux owlet segfaults at random; Flashpoint retries (its issue #4).
3. **Flashpoint does not understand AdvantageKit logs.** It reads WPILib DataLogManager names (`DS:enabled`, `DS:autonomous`, `NT:/FMSInfo/*`, `systemTime`, `MetaData` strings) and `FRC_YYYYMMDD_HHMMSS_EVENT_Q30.wpilog` file names. Our `akit_…_newton_q23.wpilog` ingested as season "unknown", no match, not paired with the hoots → **no motor data at all**.
   - Workaround: `akit_shim.py` (~100 lines) writes a small DataLogManager-style wpilog from the AdvantageKit log (DriverStation enabled/auto, FMS event/match, EpochTimeMicros → systemTime, RealMetadata → MetaData). With it, pairing worked (enable-edges alignment, "low" confidence, 34 ms spread).
4. Robot file written by hand from the code at the Newton build (BaseComp @ 2b704a3): 19 motors + Pigeon battery proxy. Hood is a TalonFXS in code but the hoot reports it as TalonFX.

## Results (Newton Q23, whole match, first enable to last disable)
| Subsystem | Flashpoint supply energy (Wh) |
|---|---|
| Drivetrain (8 motors) | 28.7 (drive 25.7, steer 3.0) |
| Intake (pivot + 3 rollers) | 9.5 |
| Shooter (2) | 6.3 |
| HotTub spinner | 5.8 |
| Feeder | 2.7 |
| Turret + retractomatic | 1.6 |
| Hood | 0.1 |
| **Total** | **54.8** |

- **Validated independently:** integrating SupplyVoltage × SupplyCurrent straight from owlet exports of the same hoots gave 55.2 Wh total, every motor within ~1% (e.g. drive FL 7.45 vs 7.47 Wh).
- Comparable to the wpilog-based figures for BOB (52.0), River Rage (58.0), NERD (59.4) Wh/match.
- rio-bus motors log supply current at 4 Hz (250 ms); CANivore at 250 Hz. Totals are fine; rio peaks are not visible. Flashpoint warns about this itself.

## Problems found
- **Teleop phase split:** hoot `RobotMode` flickers in this match, so Flashpoint cut teleop into 29 pieces, and its per-phase "teleop" row covers only the last ~2.7 s (feeder 0.07 Wh vs 2.7 Wh for the match). The "match" row is correct. Worth an upstream issue.
- 1 rio bus logger gap of 631 ms during teleop; intake right roller shows many missed CAN frames in auto.

## Fit with Team 88
- **Data availability:** hoot files exist for spring events (MABOS, Newton, North Shore, Newsom, 4-11) but **not for BOB** (and none found for River Rage / NERD). Fall-season motor current is only in AdvantageKit wpilog keys, which Flashpoint can't read (it takes motor data only from hoots, plus `NT:` NetworkTables signals).
- **Strengths:** offline local web app (Replay, History, Anomalies, Setup), TOML robot file per robot, per-motor energy/current/temp/stall per match phase, brownouts via a battery proxy, CAN health, rclone backup, auto-import from the robot.
- **No power-budget view:** no subsystem breakdown chart, idle draw, output saturation or robot-state slices. History can plot supply energy per motor per match and filter by subsystem.

## Decision inputs
- Flashpoint already computes and validates the core power number. Missing for us: AdvantageKit log support, and a team-facing power budget page.
- Options: contribute AdvantageKit support + power budget upstream; build Pitwall for power (AdvantageKit-native); or use both. Also: keep hoot logging on at every event if Flashpoint is adopted.
