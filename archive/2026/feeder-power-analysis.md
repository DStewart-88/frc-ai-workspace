# Feeder (shot release) — Power-Draw & Behavior Analysis

**What this is:** a log-measured analysis of the **feeder** — the single TalonFX (`FEEDER_MAIN` =
CAN ID 4, roboRIO bus) that pushes fuel out of the hopper into the shooter. It is the **last gate
before a ball leaves the robot** — the actual shot release. This is the fourth subsystem under the
microscope after the drivetrain, the HotTub, and the turret/retractomatic. Doug flagged no outward
issues with it; this dive confirms the mechanism is clean and surfaces what the data says about how
it *actually* behaves versus how the code reads.

**Method:** parsed with `claude/wpilog_reader.py`, resampled onto a uniform 50 Hz grid (AdvantageKit
logs on-change, so time-weighting matters), sliced by `/DriverStation/Enabled` and the feed gate
`/RealOutputs/RobotContainer/OnTargetRobot`. Signals:
`/RealOutputs/Feeder/{Current, Voltage, Velocity, Position, IsHealthy}`,
`/RealOutputs/RobotContainer/{OnTargetRobot, IsShooting}`, `/RealOutputs/Turret/OnTarget`,
`/RealOutputs/HotTub/Velocity`, `/SystemStats/{BatteryVoltage, BrownedOut}`. Sampled across the
**same four championship qual matches used in the HotTub and turret reviews — Newton Q23, Q34, Q64
and Newsom (NECMP2) Q14** — so the numbers line up subsystem-to-subsystem.

**Caveat on current:** `Feeder/Current` logs **torque current** (`getTorqueCurrent`), motor-side
(≈ stator). These April logs have **no `SupplyCurrent` entry** (the code now carries
`getSupplyCurrent` as `@AutoLogOutput`, so *future* logs record battery-side directly), so **supply
current and energy are estimated** as `V_motor · I_torque / V_battery`. The feeder only ever pushes
forward (net revolutions ≈ total revolutions — see below), so the sign issues that complicated the
turret don't arise here; signed and motoring-only energy are effectively identical.

---

## Headline

**The mechanism is clean — the story is that the 105 rps setpoint is unreachable under match load.**
Across all four matches the feeder never jammed (stall time ≈ 0), never reversed in normal operation
(0–2 velocity sign-flips/match, anti-jam never fired), stayed healthy the whole time, and drew a
modest **~2–3 Wh/match**. Doug's read — "no real outward issues" — is correct. Power and reliability
are non-issues.

What the data *does* show: the feeder is commanded to **105 rps** but **runs duty-saturated at ~90
rps** whenever the battery is loaded. During the shooting stack the battery sags to a **~9.8 V median
(5th-percentile ~7.5 V)**, and reaching 105 rps needs ~11.3 V of feed-forward — a voltage the battery
supplies only **8–16% of the time the feeder is trying to shoot**. So for ~85–90% of shooting time
the feeder is wide open (**97–98% duty**), voltage-starved, and topping out ~15 rps short of setpoint.
Its `kP`/`kI` gains have no authority in that regime — the "closed loop" is effectively open-loop-
at-full-throttle. It only reaches 105 when the battery is fresh (Newsom Q14 hit setpoint ~2/3 of the
time; the three Newton matches, ~1/4–1/3).

Layered on top is the **same `OnTargetRobot` chatter** that drives the HotTub and turret writeups:
the feeder is chopped on/off **41–126×/match** by turret-OnTarget flicker (median off-gap 0.06–0.10 s).
Unlike the HotTub, the feeder **can't** be decoupled from the gate — it *is* the shot release — so the
fix isn't in the feeder; it's debouncing `turret.onTarget()` upstream, which cleans up all three
subsystems at once.

---

## Measured characteristics (per-match, across 4 matches)

| Metric | Mean | Range | Note |
|---|---|---|---|
| Enabled duration | 164 s | 161–169 | |
| Feed-gate on (`OnTargetRobot`) | 63 s / **38%** | 43–79 / 26–47% | ≈ productive shot-release time |
| isShooting time | 72 s | 46–89 | gate is a subset (turret must also be on-target) |
| Shooting-but-not-feeding | 9.5 s | 3.8–17.6 | shot held while turret off-target |
| Torque/stator current, feeding | 15 A | 13.4–15.8 | mean of \|I\| |
| Torque current p95 / max | 28 / **39 A** | 26.5–28.9 / 37–41 | **stays under the 40 A stator limit** |
| Time at/above 40 A stator limit | **~0%** | 0.000 | one transient touch (Q34 40.8 A); never sits there |
| Velocity, feeding (all) | 86 rps | 81–92 | **setpoint is 105 — mean is ~18 short** |
| Velocity p50 / p95 / max | 93 / 110 / **118** | — | overshoots start, sags under load |
| Steady velocity (post spin-up) | 90 rps | 90–100 | median error **+11 to +15 rps below 105** (Newton) |
| Fraction of feeding at ≥95% of setpoint | **34%** | 25–58% | Newsom 58%, Newton ~25–30% |
| Motor voltage, feeding (mean / p95) | 9.0 / **11.3 V** | 8.5–9.6 / ~11.3 | p95 = `kV·105 + kS` exactly |
| Duty (V_motor / V_batt) while undershooting | **0.97** | 0.97–0.98 | wide open — battery-limited, not current-limited |
| Battery voltage while feeding (p50 / p05) | **9.9 / 7.6 V** | 9.8–10.7 / 7.5–8.8 | deep sag during the shooting stack |
| Feeding time with V_batt ≥ 11.3 V | **11%** | 8–16% | i.e. reaching 105 is *possible* only 1 time in 9 |
| Supply current (est), feeding (mean / max) | 14 / **35 A** | 12.4–14.5 / 32–37 | battery-side |
| Energy per match | **~2.4 Wh** | 1.8–2.8 | trivial; between turret (~1) and HotTub (~5) |
| Net / total wheel revolutions | ~5,700 | 3,900–7,100 | net ≈ total → **pure forward, no reversing** |
| Velocity direction reversals | ~1 | 0–2 | anti-jam essentially never fired |
| Stall time / stall events | ~0 s / 0 | 0–0.02 / 0 | **no jams in any of the 4 matches** |
| Feeder restarts (off→on) | 80 | 41–126 | each = a re-acceleration + shot interruption |
| Off-target gaps ≥ 0.5 s | ~4 | 1–7 | the *real* off-target excursions |
| Corr. supply current vs battery V | **~0.0** | +0.06 to −0.06 | feeder draw does **not** track the sag (cf. HotTub −0.3) |
| HotTub spinning while feeder feeds | 95% | 94–97 | well coordinated (shared gate) |
| Unhealthy time | ~0 s | 0–0.24 | healthy throughout |

---

## How it's commanded (the code behind the numbers)

`Feeder.java` + `RobotContainer.java`:

- **Default command is `stopFeeder()`** → `stopMotor()` (neutral/coast). Good: nothing feeds when no
  one is shooting — the same discipline the HotTub has.
- **It runs only inside `shoot()`** (driver right-trigger, or the auto "Shoot" NamedCommand), which
  schedules `runFeeder()`.
- **Inside `runFeeder()`:** `setFeederSpeed(() -> onTargetRobot ? 105.0 : 0.0)`. On-gate →
  `VelocityVoltage(105)`; the instant the gate drops → `VelocityVoltage(0)` (which, with feed-forward
  only, coasts). `onTargetRobot()` is the strict shot-release condition (`turret.onTarget() &&
  shooting && <scoring-time window>`, or the `shootOverride`). **The feeder is the actual release —
  it must stay gated here.**
- **This is a *real* closed-loop velocity controller** — the key difference from the HotTub. The
  preference tuple (`MotionMagicPIDPreferenceConstants` order: maxVel, maxAccel, maxJerk, kP, kI, kD,
  kV, kS, kA) is `0, 0, 0, 0.15886, 0, 0, 0.10665, 0.099049, 0.063801` → **kP = 0.159, kI = 0,
  kD = 0, kV = 0.10665, kS = 0.099**. So unlike the HotTub's open-loop voltage dial, the feeder has
  proportional feedback and *intends* to defend its speed. (maxVel/accel/jerk = 0 → no Motion Magic
  profile, so kA is inert; it's a plain `VelocityVoltage` request.)
- **The feed-forward alone nearly saturates the bus.** `kV·105 + kS = 0.10665·105 + 0.099 = 11.30 V`
  — which is *exactly* the measured voltage p95. That leaves almost no headroom for kP to add, and no
  headroom at all once the battery sags below 11.3 V (which is ~90% of shooting time).
- **Current limit:** `StatorCurrentLimit = 40 A` enabled; **no supply current limit.** Measured
  steady current tops out at ~38 A — the limit has real headroom and is essentially never the binding
  constraint.
- **No ramp is configured at all** — no `VoltageClosedLoopRampPeriod`, no acceleration limit. Each of
  the 41–126 restarts is a hard voltage step, which is why the wheel overshoots to ~110–118 rps on
  spin-up before load and sag pull it back down.
- **`isHealthy()`, `getSupplyCurrent()`** are now `@AutoLogOutput` — future logs will record supply
  current directly, worth confirming these estimates against the first logs that have it.

---

## The setpoint is unreachable under load (the core finding)

Decomposing the feeding windows into spin-up (first ~150 ms after each restart) vs. steady:

- **Steady velocity sits at ~90 rps on the three Newton matches** (medians 91–94), a persistent
  **+11 to +15 rps below the 105 setpoint**, and reaches ≥95% of setpoint only ~25–34% of the time.
  Newsom Q14 is the tell: with a fresher/less-loaded battery it holds ~103 (median error +2) and hits
  setpoint 58–66% of the time. **Same code, same gains — the difference is battery voltage.**
- **It is not current-limited.** Steady current averages 13–16 A and never sits at the 40 A stator
  limit (0.0% of feeding time). There's plenty of current headroom.
- **It is voltage/battery-limited.** During undershoot the duty cycle (V_motor / V_batt) is **0.97–
  0.98** — the controller is asking for essentially all the voltage the battery can give and still
  falling short. The battery during feeding has a **9.8 V median and a 7.5 V 5th-percentile** (that's
  only ~1 V above the 6.5 V brownout threshold), and clears the 11.3 V needed to feed-forward 105 rps
  only **8–16% of the time**.
- **Consequence: kP and kI are inert during shooting.** With the output pinned at the rail, the loop
  has no authority to close the ~15 rps gap — the "closed loop" is effectively open-loop-at-full-duty
  whenever the battery is loaded. Adding an integral term here would just wind up against the rail.

Two honest readings of this, and they point to different actions:

1. **If ~90 rps feeds fine** (and it evidently did — the robot shot well all four matches), then
   **105 is an aspirational number the mechanism can't hit under load**, and setting it to a realistic,
   reachable value (~90–95) would make the loop actually regulate (it'd have headroom again), make the
   behavior predictable, and shrink the spin-up overshoot — at **no real throughput cost**, since the
   wheel already can't exceed ~90 loaded. This is the low-risk move, validated with a practice-field
   A/B on shot cadence and reliability.
2. **If 105 is genuinely needed for shot quality**, then the feeder is a **victim of the battery sag**,
   and the real lever is the brownout/combined-load work already in flight — reduce the shooting-stack
   draw so the battery holds above ~11.3 V and the feeder can reach setpoint. The feeder itself isn't
   the culprit: its own draw is modest (~14 A) and **uncorrelated with battery voltage** (r ≈ 0, vs.
   the HotTub's −0.3), so it rides the sag rather than causing it.

Either way, the number in the code ("105") is not what the feeder is doing in a match — that gap is
worth closing so the team is tuning against reality.

---

## Findings & optimizations (priority order)

### 1. Set a reachable feed setpoint — the loop can't regulate at 105 under load *(do first, low risk)*
Highest clarity-per-effort. The feeder runs duty-saturated at ~90 rps for ~85–90% of shooting time;
105 is only reached on a fresh battery. Drop the setpoint to a value the mechanism can actually hold
under match sag (start ~90–95, A/B on the practice field), so the loop regains voltage headroom, the
velocity becomes predictable, and spin-up overshoot shrinks. Watch shot cadence and feed reliability
as you step it — take the lowest speed that still clears fuel cleanly, plus margin. **Keep it modest
and validated:** if a real shot-quality reason for 105 emerges, treat this as a battery-sag problem
(#4) instead of forcing a setpoint the bus can't support. Cross-check against the HotTub setpoint work
so the two speeds stay matched to each other.

### 2. De-chatter the shot release — fix it upstream in the turret, not the feeder *(highest cross-subsystem value)*
The feeder is chopped on/off 41–126×/match, with median off-gaps of 0.06–0.10 s — turret-OnTarget
flicker, not real off-target. Each chop stutters the shot cadence and fires a re-acceleration. But the
feeder **must stay gated** (it releases balls), so unlike the HotTub you *can't* just hold it on. The
clean fix is the turret writeup's finding: **`turret.onTarget()` is instantaneous and un-debounced** —
add a short on-target debounce (require off-target to persist ~0.15–0.2 s before the gate drops) so
the 60–100 ms noise blips pass while the genuine excursions (only 1–7 gaps ≥0.5 s/match) still cut the
feed. One change upstream smooths the feeder, the HotTub, and the shot release together. This is the
same root cause as HotTub #1 and turret #1 — worth fixing once, centrally.

### 3. Ramp the spin-up — tame the ~118 rps overshoot and the re-accel bumps *(secondary)*
No ramp is configured, so each restart steps ~11.3 V instantly and the wheel overshoots to 110–118 rps
before settling; re-accel current bumps to ~30 A p95 (still under the 40 A limit). Modest today —
total spin-up time is only 5–13 s/match and the spikes aren't threatening — so this is a polish item,
not a fire. A small `VoltageClosedLoopRampPeriod` (~0.05–0.1 s) would smooth it, but must be balanced
against fast spin-up for prompt firing (the feeder needs to be feeding the instant the gate opens).
Note that **fixing #2 reduces the *number* of these transients directly** (fewer restarts), so do #2
first and re-measure before adding ramp.

### 4. Power/thermal is a non-issue — no action *(watch only)*
~2–3 Wh/match, mean ~14–16 A, steady current never reaches the 40 A stator limit (one transient
touch), supply draw uncorrelated with battery voltage. The 40 A limit has comfortable headroom and is
fine as-is. The feeder is a supporting-cast load during the shooting stack, not a brownout driver —
its contribution to the sag is small and, unlike the HotTub, doesn't spike with it. Revisit only if
the future `SupplyCurrent` logs or a thermal fault say otherwise.

---

## What's already good (keep it)
- **Right control architecture.** Genuine closed-loop velocity config (kP/kV/kS), not the HotTub's
  open-loop dial — the intent is correct; it's just out of voltage headroom in practice.
- **No idle feed.** Default command coasts; it only feeds while shooting and on-target.
- **Clean mechanism.** No jams, no stalls, no reversing (net ≈ total revolutions), anti-jam never had
  to fire, healthy every match. Doug's "no outward issues" is confirmed in the data.
- **Stator limit present** (40 A) with real headroom, and **CAN traffic trimmed**
  (`optimizeBusUtilization`, explicit per-signal rates), consistent with the CAN work.
- **Supply-current now logged** (`getSupplyCurrent` `@AutoLogOutput`) for direct battery-side numbers
  next event.
- **Well coordinated with the HotTub** — both gate on `onTargetRobot`; the HotTub is spinning 94–97%
  of the time the feeder feeds.

---

## Plan / status (as of this review)
1. **Reachable feed setpoint (~90–95, A/B)** — *proposed.* The loop can't regulate 105 under sag;
   pick the lowest speed that feeds cleanly. Validate with practice-field logs on cadence + reliability.
2. **De-chatter via turret OnTarget debounce** — *proposed, shared fix* with HotTub #1 and turret #1;
   the feeder stays gated (it's the shot release), so the fix is upstream. Highest cross-subsystem value.
3. **Spin-up ramp** — *secondary*, do after #2 and re-measure; balance against fast firing.
4. **Power/thermal** — *no action*; re-check when logs carry real `SupplyCurrent`.
5. **Underlying battery sag** — the feeder's undershoot is a symptom; ties into `brownout-analysis.md`
   and the combined-load work. If 105 turns out to matter for shot quality, that's the lever, not the
   feeder.

**Files:** `Feeder.java` (`runFeeder()`, `setFeederSpeed()`, `configureTalons()` stator limit + PID
tuple, `antiJam()`, missing ramp config), `RobotContainer.java` (`shoot()` → `feeder.runFeeder()`,
`onTargetRobot()`, `configureDefaultCommands()` → `feeder.stopFeeder()`), `Turret.java`
(`onTarget()` — the flicker source), `Constants.java` (`FEEDER_MAIN` = 4),
`MotionMagicPIDPreferenceConstants.java` (gain-tuple order). Logs: Newton Q23/Q34/Q64, Newsom
(NECMP2) Q14. Cross-referenced with `hottub-power-analysis.md`, `turret-power-analysis.md`,
`brownout-analysis.md`.
