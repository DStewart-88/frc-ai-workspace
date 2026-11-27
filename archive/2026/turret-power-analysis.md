# Turret (pointing) — Power-Draw & Behavior Analysis

**What this is:** a log-measured analysis of the **turret pointing motor** — the single TalonFX
(`TURRET_MOTOR_ID` = CAN ID 3, roboRIO bus, with `CANcoder` ID 3) that rotates the turret to aim
the shooter. This is the third subsystem under the power microscope after the drivetrain and the
HotTub. The turret's companion mechanism, the **retractomatic** (wire retractor, CAN ID 17), shares
the subsystem and the same `Turret.java`, but is a different machine with a different job, so it gets
its own writeup — see `retractomatic-analysis.md`. Read them together; several findings are linked.

**Method:** parsed with `claude/wpilog_reader.py`, resampled onto a uniform 50 Hz grid (AdvantageKit
logs on-change, so time-weighting matters), sliced by `/DriverStation/Enabled` and
`/RealOutputs/RobotContainer/IsShooting`. Signals:
`/RealOutputs/Turret/{TurretCurrent, TurretVoltage, TurretVelocity, Velocity (facing deg/s), Facing,
FacingError, TargetFacing, OnTarget, IsCircumnavigating, IsTargeting, IsSynchronized, SyncError,
CANCoderFacing, IsHealthy}`, `/SystemStats/BatteryVoltage`, `/DriverStation/Enabled`. Sampled across
the **same four championship qual matches used in the HotTub review — Newton Q23, Q34, Q64 and
Newsom Q14** — so the numbers line up subsystem-to-subsystem.

**Caveat on current:** `Turret/TurretCurrent` logs **torque current** (`getTorqueCurrent`), which is
motor-side (≈ stator). These logs have **no `SupplyCurrent` entry** (the code now carries
`getTurretSupplyCurrent` as `@AutoLogOutput`, so *future* logs will record battery-side directly), so
**supply current and energy are estimated** as `V_motor · I_torque / V_battery`. Because the turret
spends much of its time near zero speed and reversing, the sign of that product flips often; energy is
reported both signed and motoring-only.

---

## Headline

**Energy is a non-issue — behavior is the story.** The turret draws only **~1 Wh per match**
(0.9–1.5 Wh), an order of magnitude *less* than the HotTub's ~5 Wh and negligible against the
drivetrain. You could stop worrying about the turret as an energy load entirely.

What the logs *do* show is a turret that **never settles**. It is slewing **85–91% of every match**,
it **reverses direction ~1,100 times per match (~7×/second)**, and it is **only on-target ~75–80% of
the time** (79–86% even while the driver is actively shooting). It is just as busy when *not* shooting
(92–94% moving) as when shooting — so roughly half of that motion is idle tracking that scores
nothing. And the absolute encoder says the turret's zero is **~8–12° off** from what the motor thinks,
all match long, with nothing reconciling it. The turret is cheap to run and works well enough to
compete, but it is hunting hard and aiming from a mis-zeroed reference — both are worth a look for
next season.

---

## Measured characteristics (per-match, across 4 matches)

| Metric | Mean | Range | Note |
|---|---|---|---|
| Energy per match | **~1.1 Wh** | 0.9–1.5 | motoring-only; trivial |
| Torque/stator current | 12 A | 11.5–13.7 | mean of \|I\| |
| Torque current p95 / max | 37 / **68 A** | 32–39 / 52–68 | **exceeds the 40 A stator limit on transients** |
| Supply current (est), mean | ~2.5 A | 2.2–3.4 | battery-side |
| Supply current (est), max | **~45 A** | 37–57 | slew/regen transients |
| Motor voltage | ~0 V (mean) | ±12 V swings | symmetric — constant back-and-forth |
| Facing slew rate \|ω\| | 100 °/s | 93–104 | p95 ~300–330 °/s, max ~900 °/s |
| Time moving (\|ω\| > 5 °/s) | **89%** | 85–91 | of enabled; **higher when idle** |
| Direction reversals (>10 °/s) | **~1,100/match** | 1,077–1,235 | ≈ 7 per second — constant hunting |
| FacingError while targeting | 10.6° | 9.7–11.5 | p95 ~29–44° |
| OnTarget fraction (all enabled) | 76% | 74–80 | instantaneous, un-debounced |
| OnTarget while **shooting** | **82%** | 79–86 | ~1 in 6 shot-frames off-target |
| Time not synchronized to CANcoder | **>99%** | — | `IsSynchronized` almost never true |
| Motor-vs-CANcoder offset | **~8–12°** | ~4–16 | roughly constant; set at boot |
| Circumnavigation events | 0 | 0 | never triggered in these matches |
| Unhealthy time | ~0 s | 0–0.5 | motors/encoder healthy throughout |

---

## How it's commanded (the code behind the numbers)

`Turret.java` + `RobotContainer.java`:

- **Default command is `aim()`** → `RunCommand(aimAtTarget)`. Unlike the HotTub (default = stop), the
  turret is **always aiming** — the whole match, shooting or not. `aimAtTarget()` sends it to
  `trajectorySolver.getTurretTarget()` (or facing 0 if `m_targeting` is false; it defaults true and is
  rarely cleared). This is the root of the "always moving" numbers.
- **Control mode is `MotionMagicVoltage`** with a real closed loop: from `Turret/PID`, the gains are
  **kP = 12.0, kI = 0, kD = 0, kV = 0.12, kS = 0.35**, cruise velocity 200 rot/s, accel 300 rot/s²
  (motor-rotor units; gear ratio motor→turret is `7 × 68/12 = 39.67`, so cruise ≈ 5 turret rev/s ≈
  1,800 °/s — very fast). This is a genuine position servo, not the HotTub's open-loop voltage dial.
- **Stator current limit = 40 A** (enabled). No supply current limit. Measured torque current stays
  under 40 A at p95 but **spikes to 52–68 A on ~4% of samples** — about a third of those coincide with
  fast slews (regen/decel transients), the rest with hard accel. The limit bounds the *steady* draw
  but not the brief transitions.
- **Spin compensation:** every loop, `goToPosition` offsets the target by
  `−0.015 × robotYawRate` (a feed-forward so the turret holds field-heading while the chassis spins).
  This injects the gyro rate — and its noise — straight into the *position* setpoint on every cycle.
- **Zeroing:** at construction the code does `m_turret.setPosition(0.0)` and the CANcoder-sync path is
  **commented out** (`sync()` / `syncCommand()` at startup are disabled; only a manual button-3 sync
  remains). So the turret trusts whatever position it powered on in as "0" and never auto-reconciles
  with the absolute encoder during a match.
- **`onTarget()`** is instantaneous and un-debounced: `distance ≥ 1.76 m` and facing error `< 9°`
  (hub) / `< 20°` (shuttle). It is the same signal the HotTub and feeder gate on — its flicker is
  documented in the HotTub review.

---

## Findings & issues (priority order)

### 1. The turret hunts constantly — because it's chasing a noisy target *(highest-value behavior fix)*
It is moving 89% of the match and reversing direction ~7×/second, yet on-target only ~80% of the time.
A well-tracking turret should sit still on a steady target and slew only when the target actually moves.

**The root is setpoint noise, not an over-eager loop — the data is specific about this.** Decomposing the
setpoint vs. the response: the trajectory-solver `TargetFacing` reverses direction **~2,000–2,300×/match**,
*more* than the turret's actual facing reverses (**~1,330–1,400×**). That ordering is the tell — the turret
is already acting as a partial low-pass on the target, faithfully chasing a setpoint that bounces faster
than the mechanism can follow. The target is essentially still (<0.02°/loop) only ~27–32% of the time and
"small-wiggles" (0.02–1°/loop) ~30% of the time. FacingError is tight in the middle (median ~4°) with the
mean (~11°) pulled up by occasional large, *legitimate* slews. So this is a **dirty-input** problem, and
the loop (kP = 12) is mostly just following orders.

Where the dirty input comes from: the solver computes turret bearing from the **vision-fed pose estimate**
every loop, and that pose carries sub-degree noise — exactly the scale the turret is twitching at. A second,
smaller source is stacked on top: the spin-comp feed-forward `−0.015 × robotYawRate` in `goToPosition`,
which injects the (noisy) yaw-rate signal straight into the *position* setpoint.

Fixes, in order:
  - **Target deadband — the primary lever, low risk.** Only *update* the commanded Motion Magic target when
    the new solver target differs from the last **commanded** target by more than ~1° (well inside the 9°
    on-target window). Implement it as a **setpoint latch, not an output deadband**: hold the last setpoint
    and let the position loop keep regulating tightly to it — don't gate on "error < threshold," which
    limit-cycles at the band edge. Compare against the last *latched* target (not current facing) so slow
    drift doesn't accumulate past the band. Keep it modest (~1°): the make-window physically narrows with
    range, and the deadband quantizes aim to its width. This directly removes the ~30%-of-loops sub-degree
    chase.
  - **Low-pass the spin-comp yaw rate (complement, don't drop it).** Filter `robotYawRate` (a single-pole
    IIR, ~50–150 ms) so it passes real rotation and strips the hash before the `0.015` gain. Keep the term
    — during genuine robot rotation the target really does move fast and the feed-forward earns its keep;
    the deadband handles the noise floor, the filtered feed-forward handles real motion. *Also verify what
    that supplier returns:* `drive.getChassisSpeedsFieldRelative().getRotation().getDegrees()` is a
    nonstandard way to read a yaw **rate** — if it's actually the heading/angle of the translation vector,
    the term is injecting a semi-unrelated signal and is a correctness bug, not just noise.
  - **Response-shaping, only if still busy (secondary).** A Motion Magic **jerk limit** (`maxJerk` is 0 =
    unlimited today → S-curve the profile so it can't chase one-tick wiggles) and a **small kD** damp the
    reaction. kD differentiates a noisy measurement, so add it *after* the input is cleaned, not before.
    Lowering **kP** is the blunt fallback — it trades away real tracking, so treat it as a last trim, not a
    first move.

  The upstream root-fix, if the turret-local deadband isn't enough: smooth the **pose estimate** itself
  (vision measurement filtering / trusting odometry more between camera updates), which also helps
  drive-on-the-move — higher-touch and higher-risk, so it's the second move, not the first.

  **Clean the input before detuning the loop** — the reversal counts show the loop is already low-passing a
  noisy target, so the leverage is upstream in the setpoint; detuning a loop that's merely doing its job
  just costs tracking. **Validate on the practice field with logs** — watch target-vs-turret reversal
  counts, FacingError, and OnTarget% before/after.

### 2. The turret is aiming from a mis-zeroed reference — sync to the absolute encoder *(aim accuracy)*
`IsSynchronized` is false >99% of every match, and `CANCoderFacing` sits a **consistent ~8–12° above**
the motor's `Facing` — present from t = 0 (the motor is zeroed to 0 at boot while the CANcoder reads
~+11°). Aiming uses the **motor** position, so if the CANcoder is the true turret angle, the turret is
systematically pointing ~10° off from where the code believes — which is exactly the kind of error that
produces a 10° mean FacingError and ~80% on-target. Part of the offset is likely mechanical (belt/gear
backlash between the motor and the turret-mounted CANcoder), which no software can remove, but the
**boot-zero offset can and should be**:
  - **Re-enable a startup sync to the CANcoder** (the code path exists, it's just commented out), or
    aim directly off the absolute encoder, so "face the hub" means the *turret* faces the hub, not the
    motor's power-on guess.
  - **Verify the `getCANCoderFacing()` scaling.** It multiplies the absolute position by a magic
    `100 × 7/5` before the gear conversion. Empirically it tracks `Facing` in slope across the full
    ±220° range (so the scale is about right), but the stacked constants are hard to audit — confirm
    them against the real CANcoder gearing so the sync you turn on is trustworthy.

  This is the single most likely lever on *shot accuracy* in this subsystem, and a good teaching case:
  **an absolute encoder is only useful if something acts on it.**

### 3. Idle tracking is free energy-wise but not free mechanically — consider quieting it
About half of every match the robot isn't shooting (77–115 s), yet the turret is slewing **92–94%** of
that time and the retractomatic is pulling >50% (see its writeup). Energy is negligible, so there's no
power reason to stop — but the constant idle motion is wear, heat, and tether cycling for no scoring
benefit. Options, in increasing aggressiveness: keep pre-aiming (today's behavior — fastest time-to-
shoot, most wear), pre-aim only when reasonably close to a scoring pose, or **park at a neutral facing
when not shooting and not pre-aiming**. This is a design trade (readiness vs. wear), not a bug — flagging
it so it's a *choice* next season rather than a default.

### 4. Minor: the 40 A stator limit is exceeded on transients — decide if that matters
Torque current tops out at 52–68 A on ~4% of samples despite the 40 A stator limit. This is normal for
voltage-mode control (the limit governs steady stator current; brief accel/regen transitions overshoot),
and the turret is small, so it's probably fine. But if you ever see turret thermal faults or want tighter
bus behavior, this is where to look — a supply-current limit or a tighter/torque-current control mode
would clamp it. Low priority.

---

## What's already good (keep it)
- **CAN traffic trimmed.** `optimizeBusUtilization()` on both motors and the CANcoder, with explicit
  per-signal update rates — consistent with the CAN work.
- **Soft limits + a safe-target / circumnavigation system.** Forward/reverse soft limits (±260°) with a
  10° buffer, and logic to unwind rather than drive into a hard stop. Circumnavigation never had to fire
  in these four matches, but it's there.
- **Health-gated motion.** `goToPosition` stops both motors if the motors/encoder report unhealthy —
  and they stayed healthy all match.
- **Energy is a genuine non-problem.** ~1 Wh/match; no action needed on the power budget.

---

## Plan / status (as of this review)
1. **De-hunt the setpoint** — the target (not the loop) is the noise source: `TargetFacing` reverses more
   often than the turret does. Primary fix is a **target deadband (~1°, as a setpoint latch)**; complement
   with a **low-passed spin-comp yaw rate** (and verify that supplier is a real yaw rate); response-shaping
   (jerk limit, small kD, lower kP) only if still busy; pose-estimate smoothing is the upstream root-fix.
   *Proposed, not started.* Validate with practice-field logs on target-vs-turret reversal count,
   FacingError, OnTarget%.
2. **Startup CANcoder sync + verify CANcoder scaling** — *proposed.* Likely the biggest win on aim
   accuracy; re-enables an existing, commented-out code path.
3. **Idle-tracking policy** — *design decision for next season*, not a fix.
4. **Transient stator overshoot** — *watch only*, revisit if thermals appear.

**Files:** `Turret.java` (`aim()`, `goToFacing()`, `goToPosition()`, spin-comp offset, `configureMotors()`
stator limit, commented-out `sync()`/`syncCommand()`, `getCANCoderFacing()` scaling, `onTarget()`),
`RobotContainer.java` (`configureDefaultCommands()` → `turret.aim()`, `shoot()`),
`MotionMagicPIDPreferenceConstants.java` (gain-tuple order: maxVel, maxAccel, maxJerk, kP, kI, kD, kV,
kS, kA), `Constants.java` (`TURRET_MOTOR_ID`, `TURRET_CANCODER_ID2`). Logs: Newton Q23/Q34/Q64, Newsom
Q14. Companion: `retractomatic-analysis.md`. Cross-referenced with `hottub-power-analysis.md`,
`brownout-analysis.md`.
