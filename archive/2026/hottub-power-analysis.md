# HotTub (ball spinner) — Power-Draw Analysis

**What this is:** a log-measured analysis of the HotTub subsystem — the spinner at the
bottom of the hopper (single Kraken/TalonFX, `SPINNER_MAIN` = CAN ID 21, on the roboRIO
bus) that guides fuel into the feeder. Goal: characterize its power draw and find
optimizations, the same way the drive-system work did. This is the second subsystem we've
put under the power microscope after the drivetrain.

**Method:** parsed with `claude/wpilog_reader.py`, resampled onto a uniform 50 Hz grid
(AdvantageKit logs on-change, so time-weighting matters), sliced by `/DriverStation/Enabled`.
Signals: `/RealOutputs/HotTub/{Current, Voltage, Velocity, IsStalled}`,
`/RealOutputs/RobotContainer/{IsShooting, OnTargetRobot, IsShootingOverride}`,
`/RealOutputs/Turret/OnTarget`, `/SystemStats/BatteryVoltage`. Sampled across four clean
championship qual matches: **Newton Q23, Q34, Q64 and Newsom Q14** (a fifth, Newton Q47,
had a corrupt timestamp tail and was dropped). The deep-dives on the on-target chatter and
the supply-current lever lean most on the two heavy-shooting matches (Q23, Q34).

**Caveat on current:** `HotTub/Current` logs **torque current** (`getTorqueCurrent`), which
is motor-side (≈ stator). These April logs have **no `SupplyCurrent` entry** and the PDH
per-channel current array is empty, so battery-side **supply current is estimated** as
`V_motor · I_torque / V_battery`. The subsystem code now carries a `getSupplyCurrent`
`@AutoLogOutput`, so *future* logs will record it directly — worth confirming these estimates
against the first logs that have it.

---

## Headline

The spinner is **not** an always-on energy hog. It runs only while the driver is shooting
(spinning time tracks shooting time almost exactly), the default command stops it, and it
draws a modest **~5 Wh per match**. Total energy is not the story.

The story is **brownout timing and spike shape**. When it runs, it runs *hard* — mean ~26 A
supply with **transient spikes to ~85–98 A** — during the shooting stack, the exact
combined-load moment our brownout work flags as worst-case. In the deepest 2% of battery sags
the spinner is spinning 59–87% of the time, and its supply draw is negatively correlated with
battery voltage (−0.28 to −0.32). Two commanding choices drive the spike shape: it is chopped
on/off ~48×/match (firing a re-acceleration spike each time), and it is run as an open-loop
~9.9 V command it never needs.

---

## Measured characteristics (per-match, across 4 matches)

| Metric | Mean | Range | Note |
|---|---|---|---|
| Spinning time (of enabled) | **44%** | 30–51% | ≈ equal to shooting time → no idle-spin |
| Torque/stator current, spinning | 31 A | 27–35 A | mean |
| Torque/stator current p95 / max | 62 / **93 A** | — | exceeds the 60 A stator limit on transients |
| Velocity, spinning | 61 rps | 54–68 | **setpoint is 90 — rarely reached** |
| Motor voltage, spinning | 7.7 V | 6.8–8.5 | steady on-target running sits at **9.7 V** (= kV·setpoint) |
| Supply current, spinning (est) | 26 A | 24–29 | mean |
| Supply current max (est) | **85 A** | 74–98 | spin-up / loaded transients |
| Energy per match | 5.2 Wh | 3.6–6.2 | positive motor electrical |
| Full stop→re-spins per match | **48** | 33–79 | each = a re-acceleration spike |
| `OnTargetRobot` toggles while shooting | 132 | 55–225 | the source of the chatter |
| Stall time per match | ~1 s | 0–2.2 | occasional real jams |

---

## How it's commanded (the code behind the numbers)

`HotTub.java` + `RobotContainer.java`:

- **Default command is `stopSpinner()`** → `stopMotor()` (NeutralOut, coast). Good: nothing
  spins when no one asked. We already have the discipline the Nashoba review calls cheapest.
- **It runs only inside `shoot()`** (right-trigger held, or the auto "Shoot" NamedCommand).
- **Inside `runSpinner()`**: `setSpinnerSpeed(() -> onTargetRobot ? 90.0 : 0.0)`. On-target →
  `VelocityVoltage(90)`; the instant on-target drops → `stopMotor()` (coast).
- **The velocity loop is feed-forward only:** the preference tuple maps to
  `kP=kI=kD=0, kV=0.11, kS=0`, so the applied voltage is just `kV·setpoint = 0.11·90 = 9.9 V`
  with **no feedback**. Measured steady on-target voltage is **9.7 V**, confirming it. "Setpoint
  90" is therefore an **open-loop voltage dial** (`setpoint × 0.11 = volts`), not a regulated
  speed — which is why the wheel settles at ~60–74 rps under load and never reaches 90.
- **Current limits:** `StatorCurrentLimit = 60 A` enabled; **no supply current limit.**
- **The configured ramp doesn't apply to the control mode in use.**
  `DutyCycleClosedLoopRampPeriod = 0.25 s` only affects `DutyCycleOut` (anti-jam); the
  `VelocityVoltage` request would need `VoltageClosedLoopRampPeriod`. Spin-ups are unramped.
- **A `SlewRateLimiter` (`spinnerLimiter`) is constructed but never used.**

---

## `isShooting` vs `onTargetRobot` (basis for the de-chatter fix)

- **`isShooting`** = the `shooting` boolean, set true only in `shoot()` (driver right-trigger,
  or auto "Shoot"), false on release / `antiJam()` / every `teleopInit()`. Coarse, latched
  "operator wants to shoot."
- **`turret.onTarget()`** = an *instantaneous, un-debounced* geometry check: `distance ≥ 1.76 m`
  and facing error `< 9°` (hub) / `< 20°` (shuttle). Flickers as the turret tracks.
- **`onTargetRobot()`** = `shooting && onTarget && <scoring-time window>`, OR `shooting &&
  shootOverride`. A strict subset of `isShooting`.

Measured: `onTargetRobot` is **true for ~87% of shooting time** (80–92%/match); gating the
hottub on `isShooting` instead would add only ~13% more spin time (~10 s/match). The dropouts
are almost all turret-flicker (the scoring-time gate alone accounted for 0–2 s/match), and
they are **short: median 0.08 s, 94% under 0.5 s, only 2 of 281 over 1 s (max 1.86 s)**.
During these gaps the wheel *already* keeps spinning by coasting (unpowered), so "hottub on
while feeder off" already occurs today for the short flickers — the change just powers it
instead of coasting. `shootOverride` (button-box 4) already forces continuous running (9–40
s/match), so continuous-while-shooting is a proven mode. **The feeder must stay gated on
`onTargetRobot`** (it is the actual shot release); only the hottub is decoupled.

---

## Findings & optimizations (priority order)

### 1. Stop chopping the spinner on/off — decouple it from `onTargetRobot` *(do first)*
Highest value, lowest performance risk. Replace the hard `onTargetRobot` gate with a
**falling-edge hold**: keep the spinner running through any off-target gap shorter than a hold
time, and only let it coast (as today) once off-target persists past that hold. A **0.5 s hold
removes ~99% of the chatter events by count** (all but the 16 gaps ≥0.5 s across 4 matches)
while preserving today's coast-down behavior for the rare long turret excursions — the cautious
choice given that a jam is a match-loser. Implementation is a small manual timer in
`runSpinner()` (a `Spinner/OffTargetHoldSec` preference + last-on-target timestamp), leaving
`setSpinnerSpeed(…0.0)`'s coast intact; log the hold state so the next practice logs show it
working. Starting simpler (gate purely on `isShooting`) is the more aggressive option to fall
back to only if the 0.5 s hold shows no staging issues.

### 2. Lower the speed setpoint — the real demand-reduction power lever
Because the loop is feed-forward-only, the setpoint **is** a voltage command: `0.11 × setpoint`.
Lowering it lowers the applied voltage, which lowers duty, which lowers **battery (supply)
current for the same ball-load torque** — so the *whole* power hump shifts down (≈ proportional
to the voltage cut: 90→65 ≈ −28% applied voltage ≈ ~−28% battery draw in the working regime),
plus lower spin-up energy and windage. This beats a supply-current limit because it *reduces the
demand* rather than clipping current mid-work. **Cost is mechanical and needs an A/B**: too slow
and fuel stops clearing (throughput drops, jam risk rises, load torque can climb and eat the
savings). Step it down on the practice field (90 → 80 → 70), watching feed reliability, shot
cadence, and the logged current/energy drop; take the lowest speed that still feeds cleanly,
plus margin. **Keep it feed-forward-only** — adding a real `kP` later would make it defend the
lower speed by drawing *more* current under load, undoing the benefit.

### 3. Supply current limit — weak lever here; revisit only after #1 and #2
Originally ranked first; the data demoted it. Battery draw peaks at **mid speed (~40–60 rps)**,
where the wheel is loaded and doing the most work (the mechanical-power hump) — it is *tiny* at
high speed (~8 A at 80+ rps). So a supply limit clips **productive ball-pushing current** (mean
speed at clip ≈ 62 rps), not a wasteful transient. And because the mechanism runs at high, fairly
constant duty (~0.8), supply ≈ 0.87 × stator, so the **existing 60 A stator limit already implies
a ~50 A supply ceiling** — a supply limit is largely redundant except for catching the transient
torque overshoots past 60 A (~5.5% of spin time). First-order clip cost: **50 A** → 4% of spinning
charge, touches 14% of time (insurance, near-free); **40 A** → 11% / 27% (starts eating work);
**30 A** → 24% / 44% (aggressive, weakens handling). **Plan: apply no supply limit initially.**
Ship #1 and #2, re-measure with the now-logged `HotTub/SupplyCurrent`, and only then consider a
**conservative 40–50 A** limit as jam/overshoot insurance if spikes persist.

### 4. Minor: stalls / anti-jam are not a power problem today
Stalls are rare (~1 s/match; Q64 worst at 2.2 s over 7 events, current pinned near the 60 A
stator limit). The stator limit already bounds the stall case. Anti-jam drives full `-1.0` duty
cycle — the one place the 0.25 s duty-cycle ramp does apply, which is fine.

---

## What's already good (keep it)
- **No idle-spin.** Default command coasts the wheel; it only runs while shooting.
- **CAN traffic already trimmed** (`optimizeBusUtilization`), consistent with the CAN work.
- **Stator limit present** (60 A) — and, given the high-duty operation, it already does most of
  the battery-side protecting a supply limit would.

---

## Plan / status (as of this review)
1. **De-chatter (0.5 s falling-edge hold)** — *staged, agreed; not yet branched/committed.* The
   cautious hold, not the bare `isShooting` gate, to protect against the rare >0.5 s excursions.
2. **Setpoint reduction** — next; separate practice-field A/B, feed-forward-only.
3. **Supply limit** — deliberately deferred; ignore for now, reconsider 40–50 A after #1 and #2
   are measured with the real `SupplyCurrent` signal.

**Files:** `HotTub.java`, `RobotContainer.java` (`shoot()`, `runSpinner()`, `onTargetRobot()`,
default commands), `Turret.java` (`onTarget()`), `Constants.java` (`SPINNER_MAIN`),
`MotionMagicPIDPreferenceConstants.java` (gain tuple order). Logs: Newton Q23/Q34/Q64, Newsom
Q14. Cross-referenced with `brownout-analysis.md`, `supply-current-analysis.md`,
`steer-current-analysis.md`, `nashoba-power-review.md`.
