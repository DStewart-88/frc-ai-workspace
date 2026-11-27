# Loop Overrun Analysis: Where the 20 ms Goes

*2026-10-28. Logs: Newton Q23/Q34/Q64 and NECMP2 Q14 (April, build `2b704a3` and `dcmp`) vs. steam day ×2 (Oct 21) and pre-River Rage ×2 (Oct 22–23), all built from `fc868cc` with uncommitted changes. Script: `loopsplit.py` (in `FRC Logs/Claude outputs/loop-timing/`).*

## Data sources and what they can and can't show

- **AdvantageKit cycle keys** (`/RealOutputs/LoggedRobot/*`, `/RealOutputs/Logger/*`) are logged every loop, so they give an unbiased split between robot code, logging, and garbage collection.
- **WPILib Tracer epochs** are the per-subsystem breakdown WPILib prints when a loop overruns. AdvantageKit captures them in `/RealOutputs/Console`. Their limits:
  - They print at most once per second, and only for loops that overran. Scheduler epochs need the scheduler alone to exceed 20 ms, so they describe slow loops. Use them for **ranking and shares**, not for typical-loop milliseconds.
  - They are wall-clock times, so a thread switch landing inside a subsystem gets charged to it.
  - A scheduler epoch block and a robot epoch block can't be reliably matched to the same loop.
- **Not traced at all:** `HealthMonitor.periodic()` and `PreferenceConstants.update()`. Both run in `robotPeriodic()` outside the scheduler.

## Top-level split (all loops, medians in ms)

| | Apr enabled | Oct enabled | Apr disabled | Oct disabled |
|---|---|---|---|---|
| **Full cycle** | 23.1 | 26.6 | 20.4 | 25.0 |
| Loops over 20 ms | 77% | 98% | 53% | 95% |
| Robot code (`UserCodeMS`) | 14.0 | 16.3 | 11.7 | 14.6 |
| Logging (`LogPeriodicMS`) | 8.6 | 10.1 | 8.3 | 10.1 |
| …of which `@AutoLogOutput` (`AutoLogMS`) | 6.1 | 7.5 | 5.9 | 7.6 |
| …conduit capture + save | 1.0 | 1.0 | 1.0 | 1.0 |
| …DriverStation + alerts | 0.7 | 0.8 | 0.7 | 0.8 |
| Garbage collection (mean per loop) | 0.09 | 0.12 | 0.11 | 0.10 |

- **The overrun predates the offseason work.** In April, 77% of enabled loops were already over 20 ms.
- **Logging alone uses half the budget.** `@AutoLogOutput` is the largest single item in the whole loop.
- **Garbage collection is negligible**, about 0.1 ms per loop on average. This rules out GC, which the earlier notes had listed as a likely cause.
- **April → October, about +3.5 ms enabled:**
  - Robot code +2.3 ms: the TreadUsageTracker and HealthMonitor additions.
  - `@AutoLogOutput` +1.4 ms: annotated items went from 83 to 106 (+28%), and `AutoLogMS` rose 23%.

## Scheduler composition (October, sampled slow loops)

| | Enabled: avg ms (share) | Disabled: avg ms (share) |
|---|---|---|
| Drive.periodic | 9.2 (35%) | 13.0 (42%) |
| Vision.periodic | 7.5 (28%) | 9.8 (32%) |
| Commands (drive RunCommand, ParallelCommandGroups) | 4.7 (18%) | — |
| TreadUsageTracker.periodic | 3.2 (12%) | 5.1 (17%) |
| TrajectorySolver.periodic | 0.8 (3%) | 0.9 (3%) |
| Dashboard.periodic | 0.6 (2%) | 0.9 (3%) |
| Turret, Hood, Shooter, Feeder, HotTub, Intake, Batman, buttons | <0.5 combined | <1 combined |

**Outside the scheduler, in sampled overrun loops:**
- `SmartDashboard.updateValues()`: median 4.9 ms enabled, 5.9 ms disabled.
- `teleopPeriodic` / `disabledPeriodic`: under 1 ms.

**April for comparison (enabled):** Vision 37%, Drive 31%, commands 24%. Autos (`Left`, `Wyndham`) took 10–18 ms when they ran.

## Why each item costs what it does (from the code)

1. **`@AutoLogOutput`, ~7.5 ms.**
   - 106 annotated items, almost all methods, called by reflection every loop.
   - Inside them are 98 separate Phoenix calls, such as `motor.getSupplyCurrent().getValue()`. Phoenix getters refresh by default, so each one is its own native call.
   - By subsystem: HotTub 27, Intake 26, Turret 15, Shooter 14, Hood 9, Feeder 7.
   - Many return unit objects (`Voltage`, `Current`), which allocate memory and take longer to log.
2. **Drive.periodic.**
   - Template work: 4 modules × 3 `refreshAll` calls + `processInputs`, then the pose estimator update for each odometry sample. The CANivore gives about 5 samples per loop at 250 Hz.
   - **Wasted work:** each sample also computes `getPose()` and `getChassisSpeedsFieldRelative()` (a kinematics solve) for `cancelX`/`cancelY`. Those variables are unused because the code that used them is commented out. Each sample also logs `Drive/RawGyro`.
   - **Disabled is about 4 ms higher than enabled.** `module.stop()` runs on all 4 modules every disabled loop, which is 8 `setControl` calls per loop.
   - `Util.logif()` is true, because `MODE = DEVELOPMENT`, so the extra setpoint logging is on.
3. **Vision.periodic.** For each of the 3 Limelights, every loop:
   - Sends a `SetThrottle` write.
   - Publishes the orientation and does an NT flush.
   - Reads the MegaTag1 and MegaTag2 queues.
   - Logs Pose3d arrays.

   Each accepted frame also goes to `addVisionMeasurement`, which replays the odometry buffer from the frame's timestamp forward.
4. **SmartDashboard.updateValues.** About 20 command buttons plus the choosers are re-published every loop.
5. **TreadUsageTracker.** This one should be cheap: 24 `recordOutput` calls with string keys built each loop, 8 `Alert.set`, and string formatting every 25 loops. 1.6–2.7 ms median is more than that code should cost. Part of it is probably time charged from other threads.
6. **Untraced: `PreferenceConstants.update()`.** 92 tunable constants (8 Motion Magic sets × 9, plus 20 singles) each call `Preferences.getDouble()` every loop, which is an NT lookup by name. HealthMonitor polls every registered fault, most of them a Phoenix `isConnected()` call, and rebuilds its summaries every loop.

## Fixes, by expected savings

1. **Batch Phoenix reads for logging (largest).**
   - Replace the method-level `@AutoLogOutput` getters with one `BaseStatusSignal.refreshAll(...)` per subsystem in `periodic()`.
   - Then read with `getValueAsDouble()` on the refreshed signals, logged as doubles. This is the 6328 IO-layer pattern.
   - Expected to recover most of the 7.5 ms. *Estimate; measure after.*
2. **Drive cleanup.**
   - Remove the unused per-sample `getPose()` / `getChassisSpeedsFieldRelative()` and the per-sample `RawGyro` log.
   - Send `stop()` once on the enabled → disabled transition, not every loop.
3. **Vision.** Send `SetThrottle` only when the enabled state changes.
4. **PreferenceConstants.** Poll at about 1 Hz, or skip when `DriverStation.isFMSAttached()`.
5. **Competition logging mode.** Set `MODE` so `Util.logif()` is false at events.
6. **Instrument first.** Port 6328's `LoggedTracer`: one `record("Name")` per subsystem, plus HealthMonitor and PreferenceConstants. Every loop then gets an unbiased per-item timing, which this analysis could only approximate.

After the loop is normally under budget, set the `Code/LoopOverrun` health-check threshold from the new `FullCycleMS` distribution.
