---
title: Control system — Systemcore and WPILib 2027
status: stub
date: 2026-11-27
source: WPILib "New for 2027" changelog (through 2027 Alpha 8), "Removed features", 2027 DataLogManager API docs and "Downloading & Processing Data Logs", all read 2026-11-27
superseded_by:
---

# Systemcore and WPILib 2027

All teams use Systemcore (replacing the roboRIO) for 2027.

**Status: stub, because WPILib 2027 is still in alpha.** The changelog runs through **Alpha 8**. Several areas say their docs are unfinished: Commands v3 ("Documentation is in work"), and telemetry, where the wpilib-docs pages haven't been updated yet. One telemetry shim is to be "removed before the kickoff release." Re-check everything here at kickoff.

## Changes that affect our code

- **Package and namespace rename:** Java `edu.wpi.first` → `org.wpilib`; C++ `frc::` → `wpi::`. The VS Code importer attempts the update. 2026 projects must be imported.
- **Java 25** (C++ 23). ZGC becomes the default garbage collector.
- **All constants, including enum values, are now ALL_CAPS** (Alpha 7).
- **CAN device classes take a `CANPort` enum** instead of an integer port (Alpha 7). Systemcore has multiple CAN buses.
- **Hardware support differs:** multiple CAN buses, Smart IO, onboard IMU, Expansion Hub.
  - Removed on Systemcore: relays, analog outputs, analog gyros, SPI (and SPI-based IMUs), DMA.
  - Talon and VictorSP classes are removed as not legal for 2027.
- **Dashboards:**
  - SmartDashboard, SendableChooser and the Sendable APIs are replaced by new **Telemetry** and **Tunables** APIs (Alpha 7).
  - Shuffleboard and SmartDashboard are removed, and NetworkTables v3 support is gone.
- **Driver Station classes are split.** `DriverStation` becomes smaller classes, mainly `MatchState` and `RobotState` (Alpha 5). The NetworkTables `FMSInfo` table is renamed `DriverStation` (Alpha 7).
- **Commands:**
  - Commands v2 keeps going with removals (Ramsete, Mecanum/Swerve controller commands); `Command.schedule()` is deprecated.
  - A new Commands v3 framework (Java) has its own migration guide.
  - An FTC-style OpMode framework is added.
- **`Rotation2d` angle getters now return wrapped angles.** Watch turret-style code and analysis that assumed unwrapped angles; use `double` or `Angle` if wrapping isn't wanted.
- **Units:** some Java units renames; RPM is now an alias of RotationsPerMinute.
- **Vision:** the AprilTag and CameraServer libraries moved to vendordeps.
- `robotInit()` is removed; use the `Robot()` constructor.
- Systemcore is configured through a web interface, with no team-number setter tool.
- **Driver Station:** the new 2027 FIRST Driver Station is multi-platform (Alpha 6). A `DriverStationDisplay` text display is added.

## Logs: where they live and how to get them

- **Location:** `DataLogManager` saves to a `logs` folder on a USB flash drive if one is attached, otherwise to `/home/systemcore/logs` on internal flash. If logs go to internal flash, download and delete them periodically so storage doesn't fill.
- **File names:** `WPILIB_yyyyMMdd_HHmmss.wpilog` (UTC) once the DS connects, with `_{event}_{match}` added when an FMS supplies the match number. AdvantageKit may name its own files differently; check its 2027 release.
- **Fetching:** WPILib's DataLogTool downloads logs over **SFTP** from Systemcore. The docs give the Systemcore username and password as `systemcore` / `systemcore`.
- **New in Alpha 8:**
  - periodic checks for a USB drive, with log transfer to it
  - alerts for low free space
  - match logs are no longer deleted during log cleanup
- **Timestamps:** raw integer timestamps in `RobotController` / `Now()` moved to **nanoseconds** (Alpha 7). DataLog files and NetworkTables still use **microseconds**, so `.wpilog` timestamp handling is unchanged.

## What this means for our 2026 tools

| Tool | Impact | Action |
|---|---|---|
| Pitwall log fetch | SFTP still works, but the host and credentials change from the roboRIO to Systemcore (`systemcore` user). Log paths change: USB `logs/` or `/home/systemcore/logs`. | Update Pitwall's fetch settings; keep it read-only on the robot. |
| Pitwall match identification | The `FMSInfo` table was renamed `DriverStation`, and the DS classes were split, so match keys in logs may move. | Re-map in each robot profile once real 2027 logs exist. |
| `scripts/wpilog_reader.py` | File timestamps stay in microseconds, so the format itself looks unchanged. | Validate on the first real Systemcore log. |
| AdvantageKit-based logging | Depends on AdvantageKit's 2027 release. SmartDashboard/Sendable removal and the package rename touch dashboards and choosers. | Check AdvantageKit 2027 notes before build season; see `knowledge/logging.md`. |
| CAN analysis and health monitor | Multiple buses; device classes take `CANPort`. | Make CAN checks per bus (`knowledge/logging.md` §5). |
| Turret / angle math | `Rotation2d` getters now wrap. | Check any code or analysis that unwraps angles. |

## To check at kickoff

- The final release's notes, against everything above.
- Whether Systemcore has a data-capable power distribution option, and how it's logged.
- AdvantageKit's 2027 release: Systemcore support, log naming, metadata, `LoggedNetworkString`.
- Phoenix 6 for 2027: CAN bus naming on Systemcore, and whether `optimizeBusUtilization` behaves the same.
- Where the new Driver Station keeps its own logs.

## Links

- New for 2027 (changelog): https://docs.wpilib.org/en/latest/docs/yearly-overview/yearly-changelog.html
- Removed features: https://docs.wpilib.org/en/latest/docs/yearly-overview/removed-features.html
- Telemetry migration from 2026: https://github.com/wpilibsuite/allwpilib/blob/main/telemetry/doc/telemetry.md#migration-from-wpilib-2026
- Tunables migration from 2026: https://github.com/wpilibsuite/allwpilib/blob/main/tunables/doc/tunables.md#migration-from-wpilib-2026
- Commands v3 migration: https://docs.wpilib.org/en/latest/docs/software/commandbased/commands-v3/migration-guide.html
- Systemcore introduction: https://docs.wpilib.org/en/latest/docs/software/systemcore-info/systemcore-introduction.html
- Downloading data logs (2027): https://docs.wpilib.org/en/2027/docs/software/telemetry/datalog-download.html
- DataLogManager (2027 Java API): https://github.wpilib.org/allwpilib/docs/2027/java/org/wpilib/system/DataLogManager.html
