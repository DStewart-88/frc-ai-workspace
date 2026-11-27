# Health monitor replay: NERD offseason logs (Oct 10 2026)

**Question:** the health monitor (`alerts` branch, `8101514`) was not on the robot at NERD. What would its end-of-match report have said for each match?

**Method:** `FRC Logs/nerd-review/healthsim.py` re-implements `Fault` and `HealthMonitor` and runs them on a 20 ms grid over each match log. It mirrors the source:
- latch only while enabled
- per-match scope (auto enable resets the record; teleop continues it)
- 2 s startup grace
- debounces
- occurrence counting

| Fault group | Log source used | Fidelity |
|---|---|---|
| Shooter main/follower presence | `Shooter/IsMainConnected`, `IsFollowerConnected` (the same `isConnected()` call) | exact |
| Feeder, Hood presence | subsystem `IsHealthy` (one device each) | near-exact (`IsHealthy` also includes `isAlive()`) |
| HotTub ×3, Intake ×3, Turret ×3 presence | subsystem `IsHealthy`, attributed to a device when that device's signals went silent (>0.3 s gap) around the episode | inferred |
| Drive modules, gyro (0.25 s debounce), cameras | `/Drive/ModuleN/*Connected`, `/Drive/Gyro/Connected`, `/Vision/CameraN/Connected` | exact |
| Power/Brownout, BatterySag (<7 V for 0.1 s), LowStartingBattery (<12.3 V) | `SystemStats/BrownedOut`, `BatteryVoltage` | exact |
| CAN/BusErrors, BusErrorsSevere (≥96 / bus-off), HighUtilization (>70% for 2 s) | `SystemStats/CANBus/*` | exact (~2 Hz source) |

## What the code as written would have reported

12 match logs, 11 matches: Q1 was restarted after a field fault, so it has two logs.

| Match | End-of-match display | Notable latched faults |
|---|---|---|
| Q1 (field fault, stopped) | WARNING | CAN/HighUtilization only |
| Q1 (restart) | ERROR | **Drive/Gyro** (teleop +48.8 s; active 91 s) |
| Q9 | ERROR | Power/Brownout ×92, **Drive/Gyro** (0.28 s) |
| Q15 | ERROR | **12 roboRIO-bus devices** at auto +2.0 s (every device except the intake pivot), CAN/BusErrors, Brownout ×25 |
| Q20 | ERROR | Brownout ×87, Shooter/Main (0.24 s), Shooter/Follower (one 20 ms blip) |
| Q24 (dead roboRIO) | NONE | Nothing latched in 4.8 s. The old roboRIO's saved record was empty at its post-match reboot. |
| E3 | ERROR | Brownout ×45; HotTub Spinner + Funnel (0.04 s blip) |
| E8 | ERROR | Brownout ×23; HotTub/Spinner (0.02 s blip) |
| E11 | ERROR | **All 12 roboRIO-bus devices except the pivot, 5–12× each** from teleop +77 s; CAN/BusErrors ×12. Shooter/Main also at teleop +3.0 s. |
| E13 | ERROR | Brownout ×12, **Drive/Gyro** (0.28 s), Feeder (0.24 s) |
| E14 | ERROR | Brownout ×10; shooter, feeder and funnel drops (0.24–0.74 s); CAN/BusErrors |
| E15 | ERROR | **All 12 drive-module faults + gyro** (CANivore, teleop +71 s, 0.48 s), HotTub drops, Brownout ×3 |

CAN/HighUtilization latched in **11 of 12** match logs (7–16 times each).

## Findings for tuning

1. **The real problems would have been caught early.**
   - Gyro: caught in Q1, the first match, and again in Q9, E13 and E15.
   - roboRIO-bus wiring fault: Q15 (11:46 EDT) shows the full outage with only the pivot left. That is **~4.5 h before E11's 11 s outage** (16:15 EDT).
   - The CANivore blip in E15 was caught.
   - The camera faults stayed quiet while enabled.
2. **Red every match, so red stops meaning anything.** ERROR shows after 10 of the 11 matches (all but Q24). In 8 of them brownouts alone would force it. E11's bus failure gets the same display as an ordinary late-match brownout. The dashboard summary list still tells them apart; a single LED color would not.
3. **CAN/HighUtilization at 70% is noise after the CAN fix.** Episodes per match (util above X for 2 s, while enabled):

   | Threshold | NERD (post-fix) | Newton / Newsom (pre-fix) |
   |---|---|---|
   | 70% | 7–16 every match | — |
   | 80% | ≤1 in 5 of 11 matches | every match |
   | **85%** | **0** | 9 of 10 Newton quals, every Newsom qual checked |

   85% / 2 s separates the overloaded season bus from the fixed one.
4. **Single-loop presence blips.** Some presence faults latch on 20–40 ms `IsHealthy` blips (Q20, E3, E8). A 0.1 s debounce removes them and keeps every real outage.
5. **The brownout cascade concern (handoff item 5) did not appear.** No brownout at NERD produced device disconnects.
6. **What it cannot see.**
   - A dead roboRIO: Q24 is obvious anyway.
   - Field/comms faults: Q1.
   - Loop overruns: not implemented yet; 90% of cycles were over 20 ms.

## Variant (for discussion, not decided)

Presence debounce 0.1 s, Brownout downgraded to kWarning, HighUtilization at 85% (`healthsim_variant.py`). With those changes the display would be:
- **ERROR** in Q1 restart, Q9, Q15, Q20, E11, E13, E14, E15. Each one is a real device dropout.
- **WARNING** in E3, E8 (brownouts only).
- **NONE** in the stopped Q1, Q24.

It is still red in 8 matches, but every red now means a device actually left a bus. That reflects the robot's wiring at this event, not noise.

## Comparison with what the team caught
- Q24 (dead roboRIO) and Q1 (field fault) were caught without the monitor.
- The rest: pending Doug's input.
