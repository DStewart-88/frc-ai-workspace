# Roller floor — code prescreen (RollerDev, 2026-10-08)

**Scope:** the hottub spinner was replaced by a powered roller floor. Code reviewed on `RollerDev` @ `ec5e6ad`
(Doug's local checkout matches it exactly). Roller work = `ba3c62c` → `ecf4218` → `a52c72c` → `a365ec3` →
`c0acec7` ("updates from testing") → `8b33990`, `ec5e6ad` (per-motor logging). Not compiled here (WPILib/CTRE
maven unreachable from the workspace); commit `a365ec3` says it builds.

**Where the code lives:** the rollers are in **`HotTub.java`**, not `Feeder.java`. HotTub now drives three TalonFXs on the roboRIO bus:

| Field | Constant | CAN ID | Invert | Notes |
|---|---|---|---|---|
| `m_spinner` | `SPINNER_MAIN` | **19** (was 21) | Clockwise_Positive | the name "spinner" is kept from the old hottub |
| `m_roof` | `ROOF_FOLLOW` | **16** | CounterClockwise_Positive | ID freed by removing the intake's inner roller |
| `m_funnel` | `FUNNEL_FOLLOW` | **21** | CounterClockwise_Positive | the old spinner's ID |

All three run `VelocityVoltage` at their own preference speed (100 default) inside `runSpinner()`, gated on
`onTargetRobot`. The default command `stopSpinner()` stops all three, and anti-jam sends `DutyCycleOut(-1)` to all three.
`Feeder.java` changed only its stator limit (40 → 60 A, `c0acec7`). `Intake.java`: the inner/pivot roller is fully commented out.

## Findings (priority order)

1. **Branch state.** PR #53 merged RollerDev into BaseComp at 18:47 on Oct 5, up to `c0acec7`. The per-motor logging commits (`8b33990` 18:53, `ec5e6ad` 18:57) landed *after* the merge and are **not on BaseComp**.
   - Deploy BaseComp → the logs contain only motor 19, under the old keys (`HotTub/Voltage`, `/Current`, `/SupplyCurrent`, `/Velocity`, `/IsStalled`, `/Position`). Roof and funnel are not logged at all.
   - Deploy RollerDev → the per-motor logs are there, but the 0.2 s on-target debounce (`a190eeb`), the BC shooter-curve change and the drive changes on BaseComp are missing.
   - Fix: merge RollerDev → BaseComp. Checked with `git merge-tree`: the merge is clean.
2. **Preference persistence hides the code defaults.** `DoublePreferenceConstant` only writes its default when the key is missing on the roboRIO.
   - `Spinner/SpinnerSpeed` has existed since the season (default 90).
   - `Spinner/RoofSpeed` and `Spinner/FunnelSpeed` were created as **90** by `a52c72c`/`a365ec3`, if those builds were deployed. `c0acec7` changed them to 100.
   - The robot runs whatever is stored, which may be 90, 100 or a mix.
   - The gains (`Spinner/SpinnerMotors kP/kV/…`) are also stored keys, and the one set is shared by all three motors.
   - Fix: check `/home/lvuser/networktables.json` or the dashboard, and log each motor's commanded setpoint.
3. **Power: three open-loop 11 V motors, unramped, chopped by the feed gate.**
   - The gain tuple is still kP = 0, kV = 0.11, so "100 rps" means 0.11 × 100 = 11.0 V. This is the same open-loop voltage dial described in `hottub-power-analysis.md`.
   - The speed setting moved 90 → 100, the opposite direction from that doc's recommendation to step it down.
   - The old single spinner already showed 85–98 A supply transients. There is no supply limit, and each motor has a 60 A stator limit.
   - The debounce on BaseComp reduces the number of restarts, but only if BaseComp code is what gets deployed.
4. **The ramp config is dead.** `ClosedLoopRamps.DutyCycleClosedLoopRampPeriod = 0.25` affects only closed-loop *duty-cycle* requests. `VelocityVoltage` needs `VoltageClosedLoopRampPeriod`, and anti-jam's open-loop `DutyCycleOut` needs `OpenLoopRamps.DutyCycleOpenLoopRampPeriod`.
   - **Correction:** `hottub-power-analysis.md` says the ramp applies to anti-jam. It does not. It applies to nothing in this subsystem.
   - `spinnerLimiter` (SlewRateLimiter) is still unused.
5. **CAN ID constants collide on paper.** `ROOF_FOLLOW` 16 = `INTAKE_INNER_ROLLER` 16 = `CLIMBER_LIFT` 16, and `SPINNER_MAIN` 19 = `CLIMBER_PIVOT` 19. This is harmless today because the climber constants are unused and the inner roller is commented out. Uncommenting either would put two controllers on one ID. Fix: delete or comment out the stale constants.
6. **Minor.**
   - SysId only drives motor 19.
   - Combined `isHealthy` can't say which of the three motors dropped.
   - The stall thresholds (55 A, < 8 rps) were copied from the spinner. They are log-only.
   - Position is logged at 100 Hz on all three motors and nothing reads it. Lower it if CAN usage climbs.
   - Naming (`HotTub`, `spinner`, `*_FOLLOW`) no longer describes the hardware.

## Checked and fine
- **Removing the `Follower` lines (`8b33990`) changes nothing.** Already in tested `c0acec7`, the default command's `stopMotor()` replaced the follower request at enable, so roof and funnel were already independent.
- **Direction is preserved.** Follower `Opposed` on a CW_Positive leader gives the same rotation as an independent CCW_Positive motor commanded positive.
- **Supply-current logging works with `optimizeBusUtilization`.** This is the same pattern as Turret and Retractomatic, whose supply current logged real values in the Aug 22 logs.
- **Sharing request objects is safe.** `m_request` and `m_voltReq` are shared across motors, and each `setControl` uses the value at the time of the call.
- **Intake inner-roller removal is complete.** Every reference is commented out.

## Log keys (RollerDev logging)
`HotTub/{Spinner,Roof,Funnel}{Voltage,Current,SupplyCurrent,Velocity,Position}`, `HotTub/Is{Spinner,Roof,Funnel}Stalled`, `HotTub/IsHealthy`.
`*Current` is **torque** current. Scripts that use the old `HotTub/Current|Voltage|Velocity|IsStalled` keys need updating.

## First-log checklist
1. Steady on-target `*Voltage` per motor: 11.0 V means 100 is stored, 9.9 V means 90.
2. `*Velocity` sign and magnitude per motor. Confirms direction and loaded speed.
3. Summed supply current across the three motors at each gate-on, against `/SystemStats/BatteryVoltage` and `BrownedOut`. Compare with the old spinner's 85–98 A peaks.
4. Toggle count of `OnTargetRobot` while shooting. Confirms the debounce is in the deployed code.
5. `/SystemStats/CANBus/Utilization` against the Aug 22 baseline (~41% enabled).
6. Feeder at the 60 A stator limit, against `feeder-power-baseline.md` (40 A era).
