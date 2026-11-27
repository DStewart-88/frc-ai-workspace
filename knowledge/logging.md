---
title: Logging contract
status: stub
date: 2026-11-27
source:
superseded_by:
---

# Logging contract

What the robot must log, and under which keys, so analysis and Pitwall work.

To fill before build season. Start from the 2026 "log the tune" spec, plus the gaps 2026 exposed:

- Power distribution total and per-channel current were not logged (the 2026 PDP 2.0 couldn't report them).
- BatteryCurrent read a bogus ~0.5 A.
- `isPreAiming` was not logged.
- Some subsystems with dynamic setpoints lacked commanded-vs-actual pairs.
