# 2026 robot code, rewritten with AdvantageKit IO layers

This is a copy of the `BaseComp` branch (as of commit `7d466e1`, Nov 6 2026) with every mechanism
moved to the IO-layer structure that Team 6328 uses. Robot behavior is meant to be the same as
`BaseComp`. Nothing here has been committed to `frc-88/2026-Robot`.

**Status: it type-checks, but it has not been run.** See [Verification](#verification) for what
was and wasn't checked, and [Bring-up checklist](#bring-up-checklist) for what to do before
trusting it on the robot.

---

## Why IO layers

Before this rewrite, each subsystem created its own `TalonFX` objects and read them directly
(`m_feeder.getVelocity()`). AdvantageKit can only replay a log if everything the code *reacts to*
comes in through `Logger.processInputs(...)`. The drivetrain and vision already worked that way,
because they came from the AdvantageKit template. The six mechanisms did not, so a log could not
be replayed.

Every mechanism now has three pieces:

```
            ┌──────────────── Subsystem (all decisions) ────────────────┐
            │  Feeder / HotTub / Shooter / Hood / Intake / Turret        │
            │  periodic():  io.updateInputs(inputs);                     │
            │               Logger.processInputs("Feeder", inputs);      │
            │  commands call io.setVelocity(...), io.stop(), ...         │
            └───────────────┬───────────────────────────────────────────┘
                            │  XxxIO interface (inputs class + output methods)
          ┌─────────────────┼──────────────────┬───────────────────────┐
     XxxIOTalonFX       XxxIOSim         new XxxIO() {}
     (real robot)     (physics sim)   (replay: does nothing;
                                       inputs come from the log)
```

- **`XxxIO`**: an interface. An `@AutoLog` inputs class lists everything the subsystem reads
  (connected, position, velocity, volts, currents). Default methods are the outputs (set velocity,
  set position, stop, configure).
- **`XxxIOTalonFX` / `XxxIOTalonFXS`**: the only code that touches Phoenix. It holds the device
  config, signal rates, and control requests, and it makes no decisions.
- **`XxxIOSim`**: a simple model so the code runs in simulation.
- **Replay** uses `new XxxIO() {}`. `updateInputs` does nothing, and `processInputs` then
  overwrites the inputs with the logged values. The subsystem code runs unchanged and makes the
  same decisions it made on the robot. Its outputs are logged under `/ReplayOutputs`, so you can
  change logic and see what it *would* have done in a real match.

`RobotContainer` picks the implementation from `Constants.currentMode` (`REAL`, `SIM`, `REPLAY`).

### Running replay

1. Deploy this code and record a log on the robot. (Old `BaseComp` logs can't be replayed for the
   mechanisms. Their inputs didn't exist yet. See [Limitations](#limitations).)
2. In `Constants.java`, set `simMode = Mode.REPLAY`.
3. Run `./gradlew simulateJava`. AdvantageKit uses the log open in AdvantageScope, or asks for a
   path. It writes `<log>_sim.wpilog` next to the original.
4. Open both in AdvantageScope. With unchanged code, `/RealOutputs/...` and `/ReplayOutputs/...`
   should match. That is the acceptance test for replay.
5. `./gradlew replayWatch` re-runs replay every time you save a file.

---

## What changed, file by file

### New structure

| Package | Files | Replaces |
|---|---|---|
| `subsystems/rollers` | `RollerIO`, `RollerIOTalonFX`, `RollerIOSim` | Shared IO for every "spinning thing": a leader TalonFX with an optional hardware follower. Used 6 times (below). |
| `subsystems/feeder` | `Feeder`, `FeederConstants` | `Feeder.java` (1 roller) |
| `subsystems/hottub` | `HotTub`, `HotTubConstants` | `HotTub.java` (3 rollers: spinner/floor, roof, funnel) |
| `subsystems/shooter` | `Shooter`, `ShooterConstants` | `Shooter.java` (roller with follower, 1 kHz request rate) |
| `subsystems/intake` | `Intake`, `IntakeConstants`, `IntakePivotIO`, `IntakePivotIOTalonFX`, `IntakePivotIOSim` | `Intake.java` (pivot + roller with follower) |
| `subsystems/hood` | `Hood`, `HoodIO`, `HoodIOTalonFXS`, `HoodIOSim` | `Hood.java` |
| `subsystems/turret` | `Turret`, `TurretIO`, `TurretIOTalonFX`, `TurretIOSim` | `Turret.java` (turret, retractomatic, CANcoder) |
| `util/system` | `SystemIO`, `SystemIORoboRIO`, `SystemStatus` | Direct `RobotController` reads (battery, brownout, CAN status) used by the health faults |
| `util` | `MotionMagicGains`, `LoggedTracer` | new |

Each `*Constants.java` holds the device config as a lambda that edits a fresh
`TalonFXConfiguration`. It reads line for line like the old `configureTalons()`, so you can compare
the two directly. Gains still come from the same preference keys. The subsystem reads them and
passes them to the IO layer, so the IO layer never reads preferences.

### Edited files

- **`RobotContainer`**: selects `REAL`/`SIM`/`REPLAY` IO for every mechanism. `SystemStatus` is
  constructed first, so its periodic runs before every other subsystem's. Power faults read
  `SystemStatus`. Replay now creates three no-op cameras. It used to create two *real*
  `VisionIOLimelight`s, which don't line up with a three-camera log. Sim also uses no-op cameras.
- **`Robot`**: `PreferenceConstants.update()` moved from the **end** of `robotPeriodic()` to the
  **start**, so every subsystem sees the same values for the whole loop and replay sees them before
  first use. Added `LoggedTracer` timing (`LoggedTracer/PreferenceConstantsMS`, `CommandsMS`,
  `HealthMonitorMS`).
- **`Drive`**: `processInputs("Drive/Gyro")` was gated on `Util.logif()`, so the gyro wasn't
  replayable in `COMP` mode. It also ran *after* `gyroYaw` was read, so replay was one loop
  behind. Now it is unconditional and comes first.
- **`util/preferenceconstants`**: every preference value now goes through the log as one input,
  `/PreferenceConstants/<name>`. Replay uses the robot's values instead of whatever is in your
  laptop's `networktables.json`. **Side benefit: preferences (gains, speeds, offsets) are now in
  every log.** The Nov 5 jam review couldn't explain a feeder change because "the gains are roboRIO
  preferences and aren't logged". That gap is closed.
- **`util/health/Fault.disconnected`**: now takes a CAN ID and a `BooleanSupplier` that reads the
  IO layer's `connected` input, instead of a Phoenix `ParentDevice`. It has the same message, type,
  and 0.1 s debounce as before. It now evaluates in replay too, which the old REAL-only guard
  prevented.
- **`util/health/CanBusFaults`**: reads CAN statistics from `SystemStatus` instead of
  `RobotController`.

### Removed (unused in `BaseComp`)

`SoundManager`, `vision/Batman` (all QuestNav code was commented out; it was an empty
subsystem), `util/BaseRobot`, `util/preflib/*`, `drive/GyroIONavX`, `drive/ModuleIOTalonFXS`.
The Studica and QuestNav vendordeps are left in place in case you want any of these back.

### Not included

Branches newer than `BaseComp` that aren't merged into it: `alerts` (Nov 1 dashboard layouts),
`system-check`, `shot-counter`, `jam-detector`. They would port the same way (the jam detector and
shot counter only need values that are already in the new inputs).

---

## Behavior parity

The goal was the same robot behavior. Things that differ, all intentional:

1. **Hood boot calibration runs on the first `periodic()`**, about 20 ms after construction instead
   of in the constructor, because inputs don't exist until then. The robot is disabled at that
   point either way.
2. **Sensor reads are once per loop.** Old getters such as `m_turret.getPosition()` each did their
   own Phoenix refresh, often several per loop. Now each device does one batched
   `BaseStatusSignal.refreshAll(...)` in `periodic()`, and logic reads those values. Values are at
   most a few ms older than before. **This should also cut loop time**: about 60 per-loop
   `@AutoLogOutput` getters, each with its own JNI refresh, are gone. That is the "batched Phoenix
   logging" idea from the loop-overrun work. Check it with the new `LoggedTracer/CommandsMS`.
3. **Two config applies per roller at boot instead of one**: the static config in the IO
   constructor, then Slot 0 gains from the subsystem. The final device config is identical.
4. **Preferences are read at the start of the loop**, not the end (see `Robot` above).
5. **Health faults now evaluate in replay**. They still stay off in sim, as before.
6. **Sim** has mechanism models now. Before, mechanism code in sim talked to Talons that didn't
   exist.

Things I kept exactly as they were, even though they look unintended. Worth a look, but they're
your team's call:

- **`Hood/SetPositionManual` ignores `Hood/Target`.** `calibrateFirst(angle)` ignores its argument
  and drives to `m_targetPitch`.
- **The hood hard-stop calibration checks the angle before its own reset takes effect.** If the
  hood was more than 1° off (the case where you'd want a hard-stop calibration), `m_calibrated`
  comes back false. The command then ends the same loop (`stator > 10 A`), and
  `setPositionTargeting` re-runs the *pulse-width* calibration, which overrides the hard-stop
  result.
- **`intake.antiJamIntake()` is an `InstantCommand` with no requirement.** The intake's default
  command keeps running, so during anti-jam the intake reverses for one loop and then
  `deployJustIntake` stops it.
- **`turret.aimAtFacingCommand()` (autos "Target 90"/"Target -90") has no requirement.** It runs
  alongside the turret's default `aim()`, and both command the turret every loop.
- **kA/jerk preferences that were never applied** (feeder, hot tub, hood, intake rollers, turret).
  They are still not applied, and each subsystem passes `0.0` with a comment. Only the shooter
  applies kA, and only the intake pivot applies jerk, as before.
- **Turret `CalibrateEncoderZero`** syncs from the CANcoder reading taken before the new offset is
  applied (same as before).
- The **MegaTag2 `maxY - minX` typo** in `Vision.java` is untouched. It's your planned isolated
  fix.

Dropped: the old `Turret/RetractomaticPosition` output actually logged the *turret's* position.
The real retractomatic position was never enabled on the bus, so nothing replaces it.

---

## Log key changes

Raw sensor values moved from `@AutoLogOutput` getters (`/RealOutputs/...`) into inputs (logged at
the root, e.g. `/Feeder/...`). Derived values (angles, stall flags, on-target, healthy, sync error)
stay where they were. Scripts and charts that read raw values need these renames:

| Old (`/RealOutputs/…`) | New (input) |
|---|---|
| `Feeder/Voltage`, `Current`, `SupplyCurrent`, `Velocity`, `Position` | `/Feeder/AppliedVolts`, `TorqueCurrentAmps`, `SupplyCurrentAmps`, `VelocityRotPerSec`, `PositionRot` (+ new `StatorCurrentAmps`) |
| `Shooter/MainVoltage`, `MainCurrent`, `MainSupplyCurrent`, `Velocity`, `Position`, `MainConnected` | `/Shooter/AppliedVolts`, `TorqueCurrentAmps`, `SupplyCurrentAmps`, `VelocityRotPerSec`, `PositionRot`, `Connected` |
| `Shooter/FollowerVoltage`, `FollowerCurrent`, `FollowerSupplyCurrent`, `FollowerConnected` | `/Shooter/FollowerAppliedVolts`, `FollowerTorqueCurrentAmps`, `FollowerSupplyCurrentAmps`, `FollowerConnected` |
| `HotTub/{Spinner,Roof,Funnel}{Voltage,Current,SupplyCurrent,Velocity,Position}` | `/HotTub/{Spinner,Roof,Funnel}/{AppliedVolts,TorqueCurrentAmps,SupplyCurrentAmps,VelocityRotPerSec,PositionRot}` (+ `StatorCurrentAmps`) |
| `Hood/Voltage`, `Current`, `SupplyCurrent`, `Velocity`, `Position` | `/Hood/AppliedVolts`, `TorqueCurrentAmps`, `SupplyCurrentAmps`, `VelocityRotPerSec`, `PositionRot` (+ `StatorCurrentAmps`, `RawPulseWidthPositionRot`) |
| `Intake/PivotCurrent` (stator), `PivotSupplyCurrent`, `PivotPosition` | `/Intake/Pivot/StatorCurrentAmps`, `SupplyCurrentAmps`, `PositionRot` (+ `VelocityRotPerSec`) |
| `Intake/RollerMain{Current,SupplyCurrent,Voltage,Velocity}` (current = stator) | `/Intake/Roller/{StatorCurrentAmps,SupplyCurrentAmps,AppliedVolts,VelocityRotPerSec}` |
| `Intake/RollerFollower{Current,SupplyCurrent,Voltage,Velocity}` | `/Intake/Roller/Follower{StatorCurrentAmps,SupplyCurrentAmps,AppliedVolts,VelocityRotPerSec}` |
| `Turret/TurretVoltage`, `TurretCurrent`, `TurretSupplyCurrent`, `TurretVelocity`, `TurretPosition`/`TurretRawPosition` | `/Turret/TurretAppliedVolts`, `TurretTorqueCurrentAmps`, `TurretSupplyCurrentAmps`, `TurretVelocityRotPerSec`, `TurretPositionRot` |
| `Turret/Retractomatic{Voltage,Current,SupplyCurrent,Velocity}` | `/Turret/Retractomatic{AppliedVolts,TorqueCurrentAmps,SupplyCurrentAmps,VelocityRotPerSec}` |
| `Turret/CANCoderPosition` | `/Turret/CancoderAbsolutePositionRot` (+ `CancoderMagnetOk`, `CancoderMagnetHealth`) |

New keys: `/System/*` (battery, brownout, CAN counters), `/PreferenceConstants/*`,
`/RealOutputs/Shooter/TargetVelocity`, `/RealOutputs/Hood/TargetPitch`, and
`/RealOutputs/LoggedTracer/*`. Units are unchanged: Phoenix-native rotations, rotations/s, volts,
and amps. The old outputs used the same units without saying so in the key name; the new names
say it.

---

## Adding a mechanism the IO way

1. If it's a roller, reuse `RollerIO`: add a `XxxConstants` with a `RollerIOTalonFX.Config` and
   construct `new RollerIOTalonFX(...)`, `new RollerIOSim(...)`, or `new RollerIO() {}` in each
   `RobotContainer` case. Otherwise write an `XxxIO` interface with an `@AutoLog` inputs class.
2. Put every value your logic reads into inputs. If a decision depends on it, it has to be an
   input.
3. In `periodic()`, call `io.updateInputs(inputs)` and then `Logger.processInputs("Xxx", inputs)`
   before anything reads `inputs`.
4. No Phoenix, `RobotController`, NetworkTables, or `Preferences` reads in the subsystem. Use
   inputs, `SystemStatus`, and `PreferenceConstants` instead.
5. Health: `Fault.disconnected("Xxx/Motor", "Xxx motor", CAN_ID, () -> inputs.connected)`.

---

## Verification

**Done:**

- **The full project type-checks**, including AdvantageKit's `@AutoLog` code generation. Neither
  Maven nor GradleRIO could be reached from the build environment, so the code was compiled with
  `javac` against the real **source** of WPILib 2026.2.1, AdvantageKit 26.0.2, and PathPlannerLib
  2026.1.2 (with EJML, QuickBuffers, and Jackson built from source too). Phoenix 6 is closed-source,
  so it was compiled against **stubs**. The stubs were checked first by compiling the *unmodified*
  `BaseComp` code against them with zero errors. The rewrite uses one Phoenix call that `BaseComp`
  didn't: `TalonFXConfigurator.apply(Slot0Configs)`, which is standard Phoenix 6 API.
- **Every dashboard button key, preference key, health-fault key, and PathPlanner named command**
  matches `BaseComp` (checked by script). The Elastic layouts and autos are unaffected.
- **No subsystem reads hardware directly** (checked by grep). The only `Preferences` and
  `SmartDashboard` reads outside IO are `HealthMonitor`'s saved record and `TreadUsageTracker`.
  Both were already designed to switch themselves off in replay.

**Not done:**

- It has not been run: not on a roboRIO, not in the simulator, and not in replay. The build
  environment had no WPILib native libraries.
- No GradleRIO build, so no Spotless pass. `./gradlew build` runs `spotlessApply` first and may
  reformat a few lines.

## Bring-up checklist

1. `./gradlew build`. It should compile. If it doesn't, the most likely cause is a Phoenix
   signature the stubs got wrong.
2. Run it in sim (`simMode = SIM`): drive, shoot (right trigger), intake, anti-jam, and calibrate
   the hood, and check that nothing throws.
3. Deploy to the home roboRIO (only a CANdle attached). It should boot, with every mechanism
   showing a disconnected fault.
4. Deploy to the robot on blocks. Before enabling, compare the Phoenix Tuner config of each device
   against `BaseComp`'s, then do a short enable.
5. Record a practice log, replay it unchanged, and compare `/RealOutputs` with `/ReplayOutputs`. If
   a value differs, something the code reads is still missing from the inputs.

## Limitations

- **Logs recorded with `BaseComp` can't be fully replayed.** Drive and vision inputs exist in
  them, but the mechanism inputs don't, so mechanisms would read zeros. Replay is for logs
  recorded with this code.
- In replay, `HealthMonitor`'s carried-over "previous run" record and the tread-usage tracker are
  off by design, so their outputs won't match the robot's.
- `LoggedTracer` uses the real clock, so in replay it times the laptop.
- The sim models are rough (kinematic profiles for the hood, pivot, and turret, and DC-motor sims
  for the rollers). They're good enough to run the code, not to tune gains.
