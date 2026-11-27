# Pitwall on other teams' robots: findings and a test set for later (Nov 10–11, 2026)

**Parked (Doug, Nov 11):** focus is making Pitwall work for Team 88 first. Robots differ too much architecturally to promise useful reports for every team; revisit if Pitwall succeeds for us. Nothing was copied into the Pitwall repo: the logs below stay in their owners' repos and get referenced, not redistributed.

## What ties Pitwall to our robot today
- **Log format:** needs AdvantageKit logs. Match identity, enabled state, battery and build metadata come from AdvantageKit's key names (`/DriverStation/*`, `/SystemStats/BatteryVoltage`, `/RealMetadata/*`). Plain WPILib DataLogManager logs (`DS:enabled`, `NT:/FMSInfo/*`, no battery) are skipped.
- **Power (biggest limit):** needs supply current per motor. Most AdvantageKit teams log only stator/torque current for swerve ("DriveCurrentAmps"), so Pitwall refuses those logs (< half the motors have supply keys). AdvantageKit logs `/PowerDistribution/ChannelCurrent` (per-channel array) by default; a PDH-channel power mode (profile maps channels to motors) would cover most AdvantageKit teams. Our robot can't use it (PDP 2.0, no current data).
- **Game periods:** profile-driven; 2026 preset.
- **Scoring:** key-driven but assumes rps units, boolean "shooting"/"feeding" signals, and a flywheel with a logged setpoint. Needs a unit setting and numeric conditions (e.g. "feeder goal ≠ 0").
- **Robot setup scanner:** BaseComp style + AdvantageKit swerve template only.
- **Branding:** "TJ²" hard-coded in report headers (already on the parked list).

## Public log sets found
| Repo | Game | Logger | Code repo | Notes |
|---|---|---|---|---|
| `WHS-FRC-3467/logs-2026` (Team 3467 Windham Windup) | 2026 REBUILT | AdvantageKit | `WHS-FRC-3467/Skip-5.16-Perry` (and `Skip-5.16-Platypus`) | 47 gzipped logs, ~760 MB: W5 Worcester (practice/quals/elims), NE-DCMP (quals/elims/finals), Champs Hopper quals. Has `/SystemStats/BatteryVoltage`, `/PowerDistribution/ChannelCurrent`, supply current for mechanisms (`/Flywheel/SupplyCurrent`, Hood, Indexer, Intake Linear/Roller, Tower), drive only `DriveCurrentAmps`; flywheel `/Flywheel/Velocity` + `/Flywheel/GoalVelocity`; indexer feeding = `/Indexer/GoalVelocity` ≠ 0 (negative while feeding). Best fit: same game, NE events, has both channel and per-motor supply current to cross-check a PDH power mode. |
| `FRC1257/2024-Logs` | 2024 Crescendo | AdvantageKit | `FRC1257/2024-Robot` | 127 files, ~1.4 GB (Testing Robot, Week-of-1-29, dcmp, monty, seneca). Unlicense. Has PDH channels, shooter RPM keys, no supply current. |
| `TheTriSonics/Rebuilt2026-wpilogs` (Team 4003) | 2026 REBUILT | DataLogManager | `TheTriSonics/Rebuilt2026` | 28 match logs (MIBKN) + one hoot→wpilog drivetrain session. No battery or current. Good "should be skipped with a clear reason" case. |
| `MARSProgramming/RobotLogs2025` | 2025 Reefscape | DataLogManager | — | 14 logs, Houston Galileo. No battery or current. |

Quick experiment: Pitwall's shot detector on 3467 NE-DCMP Q75 (velocity + GoalVelocity, gate = indexer goal ≠ 0) counted 56 shots at 5.8 BPS flowing; units unconfirmed (velocity ~150–230, likely rad/s), so not trusted.

Related tools seen: `brunoUC/tempest-dashboard` (AdvantageKit match-log analyzer: PDH current, breakers, pose), `TripleHelixProgramming/wpilog-mcp` (MCP server for WPILib/REV logs).

## If this is picked up later
1. A `tools/fetch_testset.py` that clones pinned commits of these repos (outside the Pitwall repo) plus a manifest of expected results per log (read / skipped reason, matches counted, modules run).
2. PDH-channel power mode, cross-checked on 3467 against their per-motor supply current.
3. Scoring: unit setting and numeric gate conditions.
