# Shooter (flywheel) — Power-Draw & Behavior Analysis

**What this is:** a log-measured analysis of the **shooter** — the two TalonFX (`SHOOTER_MAIN` =
CAN ID 7, `SHOOTER_FOLLOWER` = ID 6, both roboRIO bus) that spin the launch flywheel. The follower
runs `MotorAlignmentValue.Opposed` (main "forward +", follower "forward −"), i.e. the two motors
counter-rotate to drive the flywheel. This is the fifth subsystem under the microscope after the
drivetrain, the HotTub, the turret/retractomatic, and the feeder. Doug asked for an open-ended dig
into performance and optimization; the data points to one dominant behavior (a flywheel that coasts
to zero and re-spins from cold ~20×/match) and one config gap (an unprotected follower).

**Method:** parsed with `claude/wpilog_reader.py`, resampled onto a uniform 50 Hz grid (AdvantageKit
logs on-change, so time-weighting matters), sliced by `/DriverStation/Enabled` and the shooting gate
`/RealOutputs/RobotContainer/IsShooting`. Signals:
`/RealOutputs/Shooter/{Velocity, Position, MainVoltage, FollowerVoltage, MainCurrent, FollowerCurrent}`,
`/RealOutputs/Trajectory/ShooterSpeed` (the commanded setpoint — see below),
`/RealOutputs/{Feeder/Velocity, HotTub/Velocity}`, `/RealOutputs/RobotContainer/{IsShooting, OnTargetRobot}`,
`/SystemStats/{BatteryVoltage, BrownedOut}`. Sampled across the **same four championship qual matches
used in the HotTub, turret and feeder reviews — Newton Q23, Q34, Q64 and Newsom (NECMP2) Q14** — so
the numbers line up subsystem-to-subsystem.

**Two data caveats (both matter):**
1. **No logged setpoint in these April logs.** The current code logs `Shooter/TargetVelocity`, but
   these matches predate it. The shooter's target is wired straight from `trajectorySolver::getShootSpeed`
   in `RobotContainer`, and that value **is** logged as `/RealOutputs/Trajectory/ShooterSpeed`, so the
   commanded velocity is reconstructed from it (gated by `IsShooting`, since the shooter only commands
   it while `runShooter` is scheduled — otherwise it coasts).
2. **No supply current in these logs.** `Shooter/MainCurrent` / `FollowerCurrent` log **torque current**
   (`getTorqueCurrent`), motor-side (≈ stator). `getMainSupplyCurrent` / `getFollowerSupplyCurrent` are
   now `@AutoLogOutput`, so *future* logs record battery-side directly, but these don't — so **supply
   current and energy are estimated** as `(|V_main·I_main| + |V_foll·I_foll|) / V_batt`. Treat the
   supply/energy figures as estimates; the torque-current figures are measured. All velocities are
   **motor-shaft rps** as logged (the 24/18 flywheel gear ratio is not applied in the logged signal).

---

## Headline

**The flywheel coasts to a dead stop between shots and re-spins from cold ~20 times a match — and each
cold spin-up is the single largest instantaneous electrical transient of any mechanism in this robot.**
The default command is `stopShooter()` → `stopMotor()` (coast), so between shooting bursts the flywheel
decays to **~2–3 rps** (essentially stopped). Across all four matches, **79–100 % of the 17–20 shooting
windows start cold** (< 10 rps). Each cold start slams both motors to **~80–86 A torque each — ~165–186 A
combined, ~112–120 A estimated supply** — and, because `shoot()` is a single `ParallelCommandGroup`, this
happens *simultaneously* with the feeder and HotTub spinning up from zero (all three are cold at 15–16 of
~19 window starts). That stacked inrush is a **primary brownout driver**: in Q23 the battery drops a mean
0.47 V (**max 3.76 V**) in the 0.3 s after a shoot-start and the robot logged **32 brownout blips**; the
healthier-battery Newsom Q14 saw the identical transient absorbed with **zero** brownouts. Same code —
the difference is battery state of charge.

The good news, and the reason the fix is attractive: **the shooter's control loop is well-tuned and the
flywheel is cheap to hold.** Once up, it tracks the ~41 rps setpoint tightly (median error ≈ 0, within
2 rps 66–74 % of the time), holds on only **~5.4–5.9 V and ~14 A/motor** (pure windage — far from the
12 V / 60 A ceilings), and reaches setpoint in **~0.18 s**. So the enormous cold-start current isn't
buying speed the robot needs — it's the cost of starting from zero every time. **Idling the flywheel at
a ready speed instead of coasting** would erase most of the ~20 inrush events per match at almost no
holding cost, and make shots instant.

Two smaller findings ride along: the **follower has no current limit at all** (its config object is
left empty; the main has a 60 A stator limit), and in 3 of the 4 matches it takes rare, isolated
torque-current excursions to **157–169 A** — while the 60 A-limited main, at the same instant, reads
~0 A — as it absorbs shot-disturbance torque the main sheds. And the shot-speed lookup occasionally
commands speeds **above the ~83 rps feedforward ceiling** (15 % of shooting time in Q64, which included
far/shuttle shots), which simply can't be reached on a 12 V bus.

---

## Measured characteristics (per-match, across 4 matches)

| Metric | Q23 | Q34 | Q64 | Q14 | Note |
|---|---|---|---|---|---|
| Enabled duration (s) | 169 | 165 | 162 | 161 | |
| Shooting (`IsShooting`) time (s) | 88 | 89 | 46 | 66 | |
| Commanded setpoint, mean (rps) | 40.9 | 41.6 | 50.2 | 41.6 | motor-shaft; from `Trajectory/ShooterSpeed` |
| Velocity while shooting, mean | 38.3 | 38.6 | 40.4 | 39.5 | mean dragged down by cold spin-ups |
| Tracking error, median (rps) | ≈0 | −0.2 | −0.8 | 0.0 | **on setpoint once up** |
| Fraction within 2 / 10 rps | 74/93% | 66/92% | 55/79% | 73/95% | Q64 worse (far shots, see below) |
| **Hold current, combined (A)** | 28 | 31 | 30 | 30 | **~14–15 A/motor — windage only** |
| Recovery-dip current, combined | 103 | 104 | 103 | 106 | per-ball re-accel while shooting |
| **Spin-up current, combined mean / p95 / max** | 75/136/**177** | 82/135/**186** | 83/131/**169** | 82/134/**172** | **cold start = biggest transient** |
| Main torque current, mean / p95 / max | 23/61/90 | 27/62/100 | 30/62/85 | 26/61/86 | rides its 60 A stator cap at p95 |
| Follower torque current, mean / p95 / max | 25/61/**160** | 29/63/**169** | 31/63/**157** | 28/61/86 | **max >> main: unprotected** |
| Follower samples > 120 A (raw) | 6 | 8 | 2 | 0 | rare, isolated, at speed |
| Main↔follower correlation | 0.87 | 0.89 | 0.94 | 0.96 | share load well *except* the tail |
| Hold voltage, mean / p95 (V) | 5.4/6.7 | 5.6/6.8 | 5.9/8.2 | 5.7/6.8 | **far below 12 V — not saturated** |
| Energy per match (est., Wh) | 6.6 | 8.0 | 4.8 | 5.7 | **biggest of the mechanisms** (cf. feeder ~2.4, HotTub ~5) |
| Supply current, est. mean (shooting) / max | 28/**112** | 35/**114** | 39/**118** | 30/**120** | battery-side estimate |
| Shoot windows (cold spin-ups) | 19 | 20 | 17 | 18 | |
| Velocity at window start, mean | 8.7 | 6.4 | 1.9 | 7.9 | **cold** |
| Fraction of windows starting cold (<10 rps) | 79% | 80% | 100% | 83% | |
| Time to reach setpoint, mean / max (s) | 0.19/0.38 | 0.18/0.38 | 0.22/0.48 | 0.16/0.30 | **fast — no need to slam** |
| Idle velocity between windows, mean | 2.8 | 3.2 | 2.0 | 2.6 | **coasts to ~0** |
| Setpoint > 83 rps (unreachable @12 V) | 0% | 2% | 15% | 0% | far/shuttle shots |
| **Brownout events / time (s)** | **32 / 3.8** | 15 / 1.7 | 0 / 0 | 0 / 0 | tracks battery health |
| Battery while shooting, p50 / p05 (V) | 9.9/7.6 | 9.9/7.6 | 10.2/8.0 | 10.7/8.7 | deep sag during the stack |

---

## How it's commanded (the code behind the numbers)

`Shooter.java` + `RobotContainer.java`:

- **Default command is `stopShooter()`** → `stopMotor()` (neutral/coast). So whenever no one is
  holding the shoot trigger, the flywheel spins *down* — measured idle velocity is ~2–3 rps, i.e. it
  reaches a near-dead stop between bursts.
- **It runs only inside `shoot()`** (driver right-trigger, or the auto "Shoot" NamedCommand), which is
  a **`ParallelCommandGroup`** that simultaneously schedules `shooter.runShooter()`, `hotTub.runSpinner()`,
  `feeder.runFeeder()`, hood/intake shooting state, and turret targeting. **Every trigger pull spins the
  shooter, HotTub and feeder up from idle at the same instant** — the stacked inrush behind the brownouts.
- **Dynamic setpoint.** `shooter = new Shooter(trajectorySolver::getShootSpeed)` — the target is a
  distance-based lookup, updated every `periodic()`. Measured band ~34–55 rps for hub shots, spiking to
  100 rps for far/shuttle shots (Q64).
- **Genuine closed-loop velocity control.** `VelocityVoltage` with the preference tuple (order: maxVel,
  maxAccel, maxJerk, kP, kI, kD, kV, kS, kA) `0, 0, 0, 0.13985, 0, 0, 0.14, 0.36882, 0.011146` →
  **kP = 0.140, kI = 0, kD = 0, kV = 0.14, kS = 0.369**. maxVel/accel = 0 → no Motion Magic profile, so
  kA is inert; it's a plain `VelocityVoltage` request. Unlike the HotTub's open-loop dial, this loop
  intends to defend its speed — and, crucially, it *has the headroom to*: `kV·41 + kS = 6.1 V` feed-forward
  vs. a 12 V bus, so kP has room to trim. (Contrast the feeder, whose 105 rps setpoint needs 11.3 V of
  feed-forward and saturates.) The measured hold voltage (~5.4–5.9 V, kP trimming below the 6.1 V FF) and
  hold current (~14 A/motor) confirm the loop is comfortable and the flywheel is cheap to hold.
- **The follower's config is empty.** `shooterFollowerConfig` is a fresh `TalonFXConfiguration` applied
  with nothing set — **no stator current limit** — then `setControl(new Follower(SHOOTER_MAIN, Opposed))`.
  The main gets `StatorCurrentLimit = 60 A` (enabled); the follower gets the CTRE default (no stator
  limit). So the two mechanically-coupled motors are protected asymmetrically.
- **No ramp is configured** — no `VoltageClosedLoopRampPeriod`, no acceleration limit. Each spin-up is
  an instantaneous voltage step, which is exactly why the cold-start current transient is so sharp.
- **CAN traffic is trimmed** (`optimizeBusUtilization`, explicit per-signal rates — velocity/voltage
  100 Hz, current 50 Hz), consistent with the CAN work. The control request uses `withUpdateFreqHz(1000)`.
- **Supply current is now logged** (`getMainSupplyCurrent`/`getFollowerSupplyCurrent` `@AutoLogOutput`) —
  worth confirming these estimates against the first logs that carry it.

---

## The core finding: coast-to-zero → ~20 cold spin-ups a match (the physics)

Decomposing every shooting sample into **hold** (at setpoint, velocity stable), **recovery** (dipped
below setpoint, re-accelerating after a ball), and **spin-up** (cold start / far below setpoint):

- **Hold is cheap.** ~28–31 A combined (~14–15 A/motor), on ~5.4–5.9 V. That's just windage and bearing
  drag at ~41 rps. A flywheel held at speed costs almost nothing.
- **Recovery is moderate.** ~103 A combined to re-accelerate after a ball extracts energy — unavoidable
  while actively feeding, and it stays whatever the start policy.
- **Cold spin-up is the spike.** ~80–86 A torque *per motor* from rest, **~165–186 A combined, ~112–120 A
  estimated supply** — remarkably consistent across all four matches (isupply peak 112 / 114 / 118 / 120 A).
  It's brief (~0.18 s to setpoint) because the loop commands maximum effort into a stopped, low-back-EMF
  flywheel: the main clamps at its 60 A stator limit (its torque-current p95 sits right at ~60), the
  follower runs free.

**Why it's a brownout driver, confirmed:** at 15–16 of ~19 window starts, the shooter, feeder *and*
HotTub are all cold, so the `shoot()` parallel group fires three simultaneous inrushes. In Q23 the
battery drops a mean 0.47 V (max 3.76 V) in the 0.3 s after a start and logs 32 brownout blips; Q14,
with a healthier battery, rides the same transient to zero brownouts. The transient is always there —
whether it crosses the 6.5 V threshold depends on the battery.

**Why idling wins:** the ~112–120 A supply inrush is *not* buying needed performance — hold is 14 A/motor
and spin-up already completes in 0.18 s. If the flywheel idled at a ready speed (rather than coasting to
zero), ~17–20 cold starts/match collapse into a cheap continuous hold plus small per-shot recoveries,
the biggest single contributor to the shoot-start sag disappears, and shots become instant (no 0.18 s
spin-up wait). This is the highest-value change in this writeup.

---

## Findings & optimizations (priority order)

### 1. Idle the flywheel at a ready speed instead of coasting to zero *(highest value — attacks the brownout stack)*
The flywheel coasts to ~2–3 rps between bursts and re-spins from cold in 79–100 % of the 17–20 shooting
windows per match; each cold start is a ~112–120 A supply / ~165–186 A combined inrush that fires in
lockstep with the feeder and HotTub spin-ups and drives the shoot-start battery sag (up to 3.76 V in Q23,
32 brownouts). Holding the flywheel at speed costs only ~14 A/motor on ~5.5 V, and it already reaches
setpoint in 0.18 s — so the inrush buys nothing the robot needs. **Give the shooter a non-coast idle:**
hold a floor speed whenever targeting/enabled (e.g. the low end of the shot band, ~30–35 rps, or the live
lookup value pre-warmed by the `isPreAiming`/`startTargeting` path that already exists), instead of
`stopShooter()` as the default. Each shot then needs only a small trim/recovery, not a 0→41 slam. Validate
on the practice field: confirm shot quality is unaffected, watch the shoot-start battery floor and brownout
count drop, and confirm holding draw is the expected ~14 A/motor. This is the direct lever on
`brownout-analysis.md` for this subsystem.

### 2. Give the follower a current limit *(low effort, pure protection)*
`shooterFollowerConfig` is empty — the follower has **no stator current limit**, while the main is capped
at 60 A. In 3 of 4 matches the unprotected follower took isolated torque-current excursions to **157–169 A**
(6/8/2 samples/match) at moments when the 60 A-limited main read ~0 A — the follower absorbing shot-
disturbance torque the main sheds. It's rare and brief (not an energy or brownout factor), but it's exactly
the unbounded transient a stator limit exists to prevent, on a motor that has none. Set the follower's
`StatorCurrentLimit = 60 A` (enabled) to match the main — it protects the follower thermally/mechanically
over a season and makes disturbance-sharing symmetric. Nearly free; do it regardless of #1.

### 3. Cap the setpoint at the reachable ceiling (or flag unreachable shots) *(situational)*
The shot-speed lookup can command above the feedforward ceiling: `kV·v + kS = 12 V` at **v ≈ 83 rps**
(and only ~76 rps once the battery sags to 11 V). Q64 spent **15 %** of shooting time commanding
> 83 rps (far/shuttle shots, up to 100 rps) — physically unreachable, so those shots ran well below
setpoint (Q64 median error −0.8, within-2 only 55 %). Most hub shots (~41 rps) are comfortably reachable
and track tightly, so this is situational, not systemic. Either clamp the lookup to a reachable max, or
surface an "unreachable setpoint" flag so the drive team knows a far shot won't be at speed. Ties into the
same battery-sag theme — a sagged bus lowers the ceiling further.

### 4. A spin-up ramp is a distant option — and #1 makes it moot *(watch only)*
There's no `VoltageClosedLoopRampPeriod`, so cold starts step voltage instantly, sharpening the inrush.
A small ramp would blunt the peak at the cost of a slightly slower start (there's slack — 0.18 s could
stretch toward 0.3 s and still fire promptly). But **idling (#1) removes the cold starts entirely**, which
is strictly better than ramping them. Only consider a ramp if the team decides to keep coast-to-zero.

---

## What's already good (keep it)
- **Well-tuned closed loop with real headroom.** Genuine `VelocityVoltage` (kP/kV/kS), holding on ~5.5 V
  against a 12 V bus, median tracking error ≈ 0, at-speed (within 10 rps) 92–95 % of hub-shot time. Unlike
  the feeder, the shooter is *not* feedforward-saturated — the loop works; only the start policy hurts it.
- **No idle spin.** The flywheel doesn't run when nobody's shooting — good discipline; the ask in #1 is a
  *ready idle*, a deliberate middle ground, not free-running.
- **Fast recovery.** 0.18 s to setpoint and tight per-shot recovery mean shot cadence isn't gated by the
  loop — it's gated by the cold-start policy, which #1 fixes.
- **Main is protected and CAN is trimmed** (60 A stator limit on the main, `optimizeBusUtilization`,
  explicit per-signal rates), consistent with the CAN work. #2 just extends the same protection to the follower.
- **Supply current now logged** (`getMainSupplyCurrent`/`getFollowerSupplyCurrent` `@AutoLogOutput`), and
  `TargetVelocity` too — next event's logs will give measured battery-side draw and a directly-logged
  setpoint, retiring both caveats above.

---

## Plan / status (as of this review)
1. **Ready idle instead of coast-to-zero** — *proposed, highest value.* Hold a floor/live-lookup speed
   while targeting; kills ~17–20 cold-start inrushes/match. Validate shot quality + shoot-start battery
   floor + brownout count on the practice field. Direct lever on `brownout-analysis.md`.
2. **Follower stator current limit (60 A)** — *proposed, do regardless.* Close the unprotected-follower
   gap; low effort, pure protection, symmetric disturbance sharing.
3. **Clamp/flag unreachable setpoints (> ~83 rps)** — *situational.* Matters for far/shuttle shots
   (15 % of Q64); most hub shots are fine.
4. **Spin-up ramp** — *watch only / moot if #1 ships.* Only relevant if coast-to-zero is retained.
5. **Re-measure with real `SupplyCurrent` + logged `TargetVelocity`** next event to confirm the estimated
   supply/energy figures and the setpoint reconstruction.

**Files:** `Shooter.java` (`configureTalons()` — main 60 A stator limit, **empty follower config**,
missing ramp; `runShooter()`/`stopShooter()` default = coast; `setShooterSpeed()`; PID tuple),
`RobotContainer.java` (`shoot()` `ParallelCommandGroup` → simultaneous shooter/feeder/HotTub spin-up;
`configureDefaultCommands()` → `shooter.stopShooter()`; `startTargeting()`/`isPreAiming` as an idle hook),
`Constants.java` (`SHOOTER_MAIN` = 7, `SHOOTER_FOLLOWER` = 6, `SHOOTER_GEAR_RATIO` = 24/18),
`TrajectorySolver` (`getShootSpeed` — the setpoint source / lookup to clamp). Logs: Newton Q23/Q34/Q64,
Newsom (NECMP2) Q14. Cross-referenced with `feeder-power-analysis.md`, `hottub-power-analysis.md`,
`turret-power-analysis.md`, `brownout-analysis.md`.
