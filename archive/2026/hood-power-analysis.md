# Hood (launch-angle) — Power-Draw & Behavior Analysis

**What this is:** a log-measured analysis of the **hood** — the mechanism that sets the shooter's
launch angle. It's a single **TalonFXS driving a CTRE Minion** (`HOOD` = CAN ID 5, roboRIO bus) with
an absolute (pulse-width) encoder for homing. This is the sixth and final subsystem under the power
microscope, after the drivetrain, HotTub, turret, retractomatic, feeder and shooter.

**Method:** parsed with `claude/wpilog_reader.py`, resampled onto a uniform 50 Hz grid (AdvantageKit
logs on-change, so time-weighting matters), sliced by `/DriverStation/Enabled` and
`/RealOutputs/Hood/IsShooting`. Signals: `/RealOutputs/Hood/{Angle, Position, Velocity, Voltage,
Current, PulseWidthDeg, IsShooting, IsCalibrated, IsHealthy}`, `/RealOutputs/Trajectory/HoodAngle`
(the commanded setpoint), `/SystemStats/{BatteryVoltage, BrownedOut}`. Sampled across the **same four
championship qual matches used in the other subsystem reviews — Newton Q23, Q34, Q64 and Newsom
(necmp2) Q14** — so the numbers line up subsystem-to-subsystem.

**Caveat on current:** `Hood/Current` logs **torque current** (`getTorqueCurrent`), which is
motor-side (≈ stator). These logs have **no `SupplyCurrent` entry** (the code now carries
`getSupplyCurrent` as `@AutoLogOutput`, so *future* logs will record battery-side directly), so
**supply current and energy are estimated** as `V_motor · I_torque / V_battery`. The hood spends most
of the match at near-zero applied voltage, so those estimates are small numbers computed from small
numbers — good enough to rank the subsystem, and the conclusion (energy is negligible) is robust to
the method.

---

## Headline

**The hood is the cleanest subsystem we've looked at — there is essentially nothing to fix.** It is
the **smallest energy load on the robot by a wide margin: ~0.1 Wh per match** (0.06–0.13). That's
~10× less than the turret (~1 Wh), ~50× less than the HotTub (~5 Wh), and negligible against the
drivetrain. Mean applied voltage is **~0.3 V** — the mechanism is so well balanced that holding it in
place costs almost nothing.

Two things it does *right* are worth calling out because other subsystems don't: **it homes to its
absolute encoder at boot and stays calibrated** — the pulse-width encoder and the motor position agree
to within **±2° all match, ~0.02° mean** (contrast the turret, which ran 8–12° mis-zeroed and never
synced) — and **its always-on position servo is genuinely free**: parked at 15° when not shooting, it
draws ~1 W and barely moves (3–9% of idle time).

The only things the logs flag are minor: (1) rare **near-stall current transients (145–179 A for 1–2
samples)** that appear *only* in the two matches where the stator limit was clearly above the intended
comp value — momentary mechanical binds the limit is supposed to catch; (2) the hood **micro-dithers
while shooting** because the trajectory solver's angle setpoint is noisy — the same root cause as the
turret's hunting, but here it costs no measurable energy and tracks to <1°; and (3) a few **latent code
smells** in the calibration/manual paths. None of these is a power problem.

---

## Measured characteristics (per-match, across 4 matches)

| Metric | Mean | Range | Note |
|---|---|---|---|
| **Energy per match** | **~0.1 Wh** | 0.06–0.13 | supply-side; the smallest load on the robot |
| — idle (not shooting) share | ~0.03 Wh | 0.02–0.04 | parked-at-15° hold is nearly free |
| Torque/stator current, mean \|I\| | 4 A | 2.9–4.8 | holding current at ~0 V |
| Torque current p95 | 12 A | 7.8–16 | brief slew currents |
| Torque current max | **35 → 179 A** | 35–179 | see finding #1 — split by match |
| Supply current (est), mean | ~0.2 A | 0.1–0.3 | battery-side; trivial |
| Motor voltage, mean \|V\| | **0.31 V** | 0.27–0.34 | near-zero effort to hold |
| Hood angle traveled | 13–34° | min ~13.5, max ~33 | full soft-limit range is 13.9–34.5° |
| Time shooting (of enabled) | 44% | 29–54 | hood tracks the shot solution only here |
| Time moving (\|ω\|>2°/s) | 23% | 15–32 | **overwhelmingly during shooting** |
| Angular rate p95 / max | 25 / **540 °/s** | — | fast, snappy profile (cruise ≈ 750 °/s) |
| Direction reversals | ~1,000/match | 700–1,555 | ~8/s **while shooting**, ~near-still idle |
| Track error vs setpoint (shooting) | 0.7° | 0.6–0.9 | p95 2.3–4.4° — tracks tightly |
| Setpoint (`Trajectory/HoodAngle`) reversals | ~2,000/match | 1,576–2,482 | **more than the hood itself** → noisy input |
| Calibrated fraction | **100%** | — | homed at boot, stays calibrated |
| Abs-encoder vs motor offset | **~0.02°** | ±2° all match | excellent — the turret's opposite |
| Unhealthy time | ~0 s | 0–0.3 | healthy throughout |

---

## How it's commanded (the code behind the numbers)

`Hood.java` + `RobotContainer.java`:

- **Default command is `setPositionTargeting()`** → `RunCommand(calibrateFirst(m_targetPitch))`, so the
  hood is **always position-servoing** the whole match (like the turret, unlike the HotTub/feeder which
  default to stop). What it servos *to* is set in `periodic()`: **shooting → clamp(solver angle, 15°,
  34°); not shooting → 15°.** So it parks at 15° whenever the driver isn't shooting.
- **Control mode is `MotionMagicVoltage`** with a real closed loop: from `Hood/HoodMotor`, the gains are
  **kP = 8.0, kI = 0, kD = 0, kV = 0.08, kS = 0.45**, cruise velocity 100 rot/s, accel 250 rot/s²
  (Minion rotor units). The rotor→hood ratio is `(287/18)·(36/12) = 47.83` rotor rev per hood rev, so
  cruise ≈ 752 °/s of hood — very fast against a ~21° total range. This is a genuine position servo.
- **The pitch source** is `trajectorySolver::getAngle` — the ballistic launch angle, recomputed every
  loop from the (vision-fed) pose estimate. That's why the setpoint is as busy as it is.
- **Homing is done right.** At construction `setCalibrate()` seeds the motor position from the
  **absolute pulse-width encoder** (`20° + encoderRotationsToHoodDegrees(-rawPW + offset)`) and sets
  `m_calibrated = true`. `IsCalibrated` is true 100% of every match and the abs-vs-motor offset stays
  ±2°. This is exactly the startup sync the turret is missing.
- **Soft limits** ±: reverse 13.9°, forward 34.5° (13.4/35.0 with a 0.5° buffer), enabled.
- **Stator current limit = 88 A in the synced code**, with the comment *"changed to 88 for practice
  robot, comp is 40"*. No supply current limit. See finding #1 — the logs show the *effective* limit
  differed match to match.
- **CAN traffic trimmed:** `optimizeBusUtilization()` with explicit per-signal rates, and the
  pulse-width position rate was cut from 1000→100 Hz (the comment notes it was ~13% of the roboRIO bus)
  — consistent with the CAN work.

---

## Findings & issues (priority order — all low-stakes)

### 1. Rare near-stall current transients — and an inconsistent stator limit *(the one worth a look)*
Torque current tops out very differently by match: **Newton Q23 145 A, Q34 179 A**, but **Q64 35 A and
Newsom 37 A**. The big spikes are **1–2 samples each (~30–50 ms)** at **near-zero velocity** (e.g. Q34:
−179 A at 0.1 rot/s, hood stuck at 20.9°) — the signature of the hood momentarily binding (a ball
lodged near the hood, or a mechanical catch) while the servo slams current in to hold position, then
clearing. They are real events, not decode glitches, but they are vanishingly rare (**<0.1% of
samples**) and cost no energy.

The tell is that the spikes appear **only in the two matches whose ceiling is above 40 A**. Q64 and
Newsom never exceed ~37 A — right at the intended 40 A comp limit — while Q23/Q34 run to 145–179 A.
That's strong evidence the stator limit was **not at the comp value of 40 A during Q23/Q34** (it was at
the 88 A practice value, or effectively higher), and that when the 40 A limit *is* active it does its
job. Since energy is a non-issue, the reason to care is **mechanical/thermal protection of the small
Minion**, not power.

**Action:** decide the intended competition stator limit and make sure it's actually the one loaded at
events — the code as synced carries the 88 A practice value. A limit in the **40 A** range clamps these
bind transients (proven by Q64/Newsom) without touching normal operation (p95 is only ~12 A). This is
also the subsystem that most wants the **now-available `Hood/SupplyCurrent`** logged at the next event,
to confirm the estimate and watch the bind events with a real battery-side number.

### 2. The hood micro-dithers while shooting — noisy setpoint, same root as the turret *(cosmetic here)*
While shooting, the hood moves 34–43% of the time and reverses direction **~8×/second**; while idle it's
nearly still (3–9% moving, except Newsom at 23%). The cause is the same one the turret writeup
identified: the **commanded setpoint is noisier than the mechanism** — `Trajectory/HoodAngle` reverses
~1,576–2,482×/match, *more often* than the hood's own angle does, so the hood is already low-passing a
jittery ballistic solution driven by sub-degree pose-estimate noise.

The difference from the turret is that here it **doesn't matter**: energy is ~0.1 Wh either way, and the
hood still **tracks its setpoint to a mean 0.7° (p95 <4.4°)**, well inside any reasonable launch-angle
tolerance. So this is not worth a hood-specific fix. **If** the pose-estimate smoothing proposed in the
turret review gets done, the hood's dither cleans up for free as a side effect — the leverage is
upstream, shared across both aimers. Flagging it only so the connection is on record; the sole local
cost is a little mechanical wear on a small mechanism.

### 3. Minor code smells in the calibration / manual paths *(latent, not match-affecting)*
Three things a future reader should know, none of which affected these matches:
  - **`calibrateFirst(double angle)` ignores its parameter** and always servos to the `m_targetPitch`
    *field*. For the default targeting path that's harmless (it's called with `m_targetPitch`), but
    `setPositionManual()` passes `targetPos.getValue()` expecting the manual dashboard target to take
    effect — it silently doesn't. Dead/misleading path; either wire the parameter through or delete it.
  - **`hardStopCalibrate()` uses two different stall thresholds:** the command ends when stator current
    exceeds **10 A**, but `hardCalibrate()` only actually re-zeros the position when it exceeds **25 A**.
    So the command can stop *before* the re-zero fires. Since boot homing off the absolute encoder
    already works well, the hard-stop path is a rarely-used backup (button 2) — but if it's ever relied
    on, unify the thresholds.
  - **Stator limit hard-coded to the practice value** (see #1).

### 4. The always-on servo is *not* a problem — confirmed
Worth stating explicitly because it's a natural worry with an always-scheduled position command:
holding at 15° when idle costs **~1 W (~0.03 Wh/match)** and produces almost no motion. There is **no
power reason to add an idle-stop** the way we discussed for the turret's tracking. Leave it as is.

---

## What's already good (keep it)
- **Homing is a model for the rest of the robot.** Boots calibrated off the absolute encoder, stays
  within ±2° all match, `IsCalibrated` 100%. This is exactly what the turret review asks the turret to
  start doing — point to the hood as the reference implementation.
- **Negligible energy and near-zero holding effort.** ~0.1 Wh/match at ~0.3 V mean; the smallest load
  on the robot. No power budget concern at all.
- **Tracks tightly.** Mean launch-angle error 0.7° while shooting despite a noisy setpoint.
- **CAN traffic trimmed**, pulse-width rate cut 1000→100 Hz — consistent with the CAN work.
- **Healthy throughout** and **not a brownout contributor** — in the deepest 2% of battery sags the
  hood is drawing only ~0.5–2 A (est), a bystander to the drivetrain/HotTub stack.

---

## Plan / status (as of this review)
1. **Confirm & set the competition stator limit** (target ~40 A) and make sure it's the value loaded at
   events, not the 88 A practice value in the synced code — *proposed.* Cheap mechanical/thermal
   insurance for the bind transients; no downside given p95 is ~12 A. Log `Hood/SupplyCurrent` next
   event to verify.
2. **No hood-specific de-dither work** — the shared fix is upstream pose-estimate smoothing (see the
   turret review); the hood cleans up for free if that happens. *Deferred to the turret track.*
3. **Tidy the calibration/manual code smells** (param-ignoring `calibrateFirst`, mismatched hard-stop
   thresholds) — *housekeeping,* do opportunistically.
4. **Nothing on energy.** The hood is a confirmed non-issue for the power budget.

**Files:** `Hood.java` (`periodic()` target logic, `setPositionTargeting()`/`calibrateFirst()`,
`setCalibrate()`/`getPulseWidthDeg()` homing, `configureMinion()` stator limit + gains + soft limits,
`hardCalibrate()`/`hardStopCalibrate()` thresholds, `setPositionManual()`),
`RobotContainer.java` (`configureDefaultCommands()` → `hood.setPositionTargeting()`, `shoot()` →
`hood.setIsShootingCommand()`), `Constants.java` (`HOOD` = 5), `MotionMagicPIDPreferenceConstants.java`
(gain-tuple order: maxVel, maxAccel, maxJerk, kP, kI, kD, kV, kS, kA). Logs: Newton Q23/Q34/Q64, Newsom
(necmp2) Q14. Cross-referenced with `turret-power-analysis.md` (shared setpoint-noise root cause;
calibration contrast), `hottub-power-analysis.md`, `brownout-analysis.md`.
