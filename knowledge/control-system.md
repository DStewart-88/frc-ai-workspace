---
title: Control system — Systemcore and WPILib 2027
status: stub
date: 2026-11-27
source: docs.wpilib.org "New for 2027" and "Removed features", checked 2026-11-27
superseded_by:
---

# Systemcore and WPILib 2027

All teams use Systemcore (replacing the roboRIO) for 2027.

## Known changes that affect our code and tools

- Java packages move from `edu.wpi.first` to `org.wpilib`; C++ namespaces from `frc::` to `wpi::`. The VS Code importer attempts the update.
- 2026 projects must be imported to work with WPILib 2027.
- Hardware support differs: multiple CAN buses, Smart IO, onboard IMU, Expansion Hub.
- Removed on Systemcore: relays, analog outputs, analog gyros, SPI (and SPI-based IMUs).
- Telemetry and tunables have new APIs, with migration guides from the 2026 APIs.
- Systemcore is configured through a web interface (no roboRIO team-number setter).

## To check before relying on our 2026 tools

- Log file location and transfer: Pitwall's log fetch uses SFTP to the roboRIO.
- Whether `.wpilog` format and AdvantageKit keys change with the new telemetry APIs.
- CAN analysis assumptions: the 2026 CAN utilization work was built around the roboRIO bus layout.
- New Driver Station: where its logs live.

## Links

- New for 2027: https://docs.wpilib.org/en/latest/docs/yearly-overview/yearly-changelog.html
- Removed features: https://docs.wpilib.org/en/latest/docs/yearly-overview/removed-features.html
