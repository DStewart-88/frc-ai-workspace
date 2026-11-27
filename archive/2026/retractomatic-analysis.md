# Retractomatic (wire retractor) — Power-Draw & Behavior Analysis

**What this is:** a log-measured analysis of the **retractomatic** — the second TalonFX in the turret
subsystem (`TURRET_RETRACTOMATIC_ID` = CAN ID 17, roboRIO bus). Its job is *not* to point anything: it
reels the turret's wire tether in and out as the turret rotates, keeping the harness from drooping and
snagging in the robot. It lives in `Turret.java` alongside the pointing motor but is a mechanically
separate machine with a separate control strategy, so it's analyzed on its own here. Read it with
`turret-power-analysis.md`; several findings are shared.

**Method:** same pipeline as the turret and HotTub reviews — `claude/wpilog_reader.py`, uniform 50 Hz
grid, sliced by `/DriverStation/Enabled` and `/RealOutputs/RobotContainer/IsShooting`. Signals:
`/RealOutputs/Turret/{RetractomaticCurrent, RetractomaticVoltage, RetractomaticVelocity,
RetractomaticPosition}`, plus the turret's `Velocity`/`Facing` (which drive the retractomatic logic) and
`/SystemStats/BatteryVoltage`. Same four matches: **Newton Q23, Q34, Q64, Newsom Q14.**

**Caveat on current:** `RetractomaticCurrent` logs **torque current** (`getTorqueCurrent`) — which here
is also the *commanded* quantity, since the retractomatic runs in `TorqueCurrentFOC` mode. No
`SupplyCurrent` entry in these logs (the code now carries `getRetractomaticSupplyCurrent`, so future
logs will record it); **supply current and energy are estimated** as `V_motor · I_torque / V_battery`.

---

## Headline

The retractomatic is a **torque-controlled, one-directional reel**: it applies a fixed **−15 A pull-in**
whenever the turret is moving *toward* the minimum-tether facing, and **zero current** (freewheel) when
moving away. Energy is negligible — **~0.7–0.85 Wh per match** — so, like the turret, it is not a power
concern.

The concern is **control quality**. It is commanding pull-in **53–56% of the match**, and because the
decision is driven purely by the *instantaneous sign* of the (noisy, constantly-reversing) turret
velocity, the command **slams between 0 A and −15 A about 7–8 times per second** — 1,200+ transitions a
match. It spends **~4–8 s per match stalled** (pulling at ~15 A against a stationary reel, i.e. tether
fully wound), which is harmless thermally but cycles the tether. It has **no current limit configured**,
though as finding #4 works through, a limit *above* the 15 A torque command wouldn't change any of this
— the useful lever is the command itself. And it has an outright logging bug. Good candidates for a
cleanup pass.

---

## Measured characteristics (per-match, across 4 matches)

| Metric | Mean | Range | Note |
|---|---|---|---|
| Energy per match | **~0.75 Wh** | 0.66–0.85 | motoring-only; trivial |
| Torque current, mean (signed) | −5.6 A | −5.5…−5.8 | negative = pull-in |
| Torque current, median | −2.6 A | −1.8…−4.1 | lots of time near 0, lots at −15 |
| Torque current p5 / min | −12.4 / **−15.6 A** | — | = commanded −15 A pull-in (`In Current`) |
| Torque current, max | ~+0.4 A | 0.2–0.4 | **never meaningfully positive** (see #2) |
| Supply current (est), mean | 1.6 A | 1.4–1.8 | battery-side |
| Supply current (est), max | ~13 A | 12.6–13.1 | modest |
| Time commanding pull-in (I < −1 A) | **55%** | 53–56 | of enabled |
| Time commanding pay-out torque | **0%** | — | `Out Current` = 0, so it only ever pulls or coasts |
| 0 ↔ pull-in command transitions | **~1,250/match** | 1,227–1,279 | ≈ 7.5/s — chatter mirrors the turret's |
| Motor speed \|ω\| | 20 rot/s | 19–22 | p95 ~56–59, max ~110–117 rot/s |
| Stall time (pull-in & \|ω\| < 2 rot/s) | **~6 s** | 4–8 | ~15 A held against a stopped reel |
| Heat proxy ∫I²dt (stator) | ~10,300 A²s | 9,900–10,400 | steady, not alarming for a TalonFX |

---

## How it's commanded (the code behind the numbers)

`Turret.java` → `retractomatic()`, called **from `goToPosition()` every time the turret aims** (i.e.
continuously, since `aim()` is the turret's default command):

- **Reference point:** `currentFacingAngleRelative = getFacing() + 10.0`. The tether is assumed
  shortest at facing = **−10°** (marked `TODO: find facing that is minimum tether length` — the −10 is a
  placeholder, not a measured value). Motion *toward* −10° shortens the tether → **pull in**; motion
  *away* lengthens it → **pay out**.
- **The decision is on the sign of turret velocity**, four quadrants around −10°:
  toward-minimum → `p_goingInCurrent = −15 A`; away-from-minimum → `p_goingOutCurrent = 0 A`.
- **`TorqueCurrentFOC`** regulates stator current to that target. So pull-in is a fixed ~15 A of torque
  regardless of speed or how much tether is out; pay-out is **zero torque** — the reel is expected to
  **back-drive freely** as the turret pulls wire off it.
- **No current limits configured.** `retractomaticCfg` sets only `MotorOutput.Inverted`. There is no
  stator limit, no supply limit, no timeout. (The −15 A request is self-limiting to ~15 A of stator, but
  nothing bounds a fault case beyond that, and there's no thermal/supply ceiling.)
- **Dead safety guard.** The block that would `stopMotor()` when the turret is barely moving or not
  targeting is **commented out** (lines ~311–316), so the reel reacts to every flicker of turret velocity.
- **CAN traffic trimmed** (`optimizeBusUtilization`, explicit update rates) — good, same as the turret.

---

## Findings & issues (priority order)

### 1. Logging bug: `RetractomaticPosition` logs the **turret's** position *(fix first — it's free)*
`getRetractomaticPosition()` returns `m_turret.getPosition()` — a copy-paste from the turret getter — so
`/RealOutputs/Turret/RetractomaticPosition` is just a duplicate of `TurretPosition` (confirmed: identical
in 94% of samples, the rest differing only by log-timing). **You have no real record of the reel's
position.** One-line fix (`m_retractomatic.getPosition()`), and worth doing before the next practice logs
so any tether-position tuning has real data. Good lesson on why you sanity-check new log channels against
what they *should* read.

### 2. It can only reel *in*, never *out* — confirm that's intended
`p_goingOutCurrent = 0.0`, so the "pay out" branches apply **zero torque** and the pay-out command fired
**0 times** across all four matches. The design leans entirely on the reel back-driving freely when the
turret pulls wire off it. If the reel has any meaningful friction, a return spring, or a ratchet, "0 A"
means it *doesn't* pay out smoothly and the tether goes slack or tugs — the exact drooping/snagging the
mechanism exists to prevent. Decide deliberately: either confirm free back-drive is real (and keep 0), or
give pay-out a small positive torque so the reel actively feeds line. Right now it's a placeholder value
(like the −10° reference and the −15 A pull) that never got tuned.

### 3. The 0 ↔ −15 A chatter is mostly the turret's hunt showing through — fix that first
The in/out choice keys off the *instantaneous sign* of turret velocity, so the target flips every time
the turret reverses direction. The turret reverses ~1,100×/match (turret finding #1) and the
retractomatic flips ~1,250×/match — **≈ 1:1**. So the chatter is overwhelmingly a *downstream symptom*:
de-hunt the turret and ~80% of it disappears with no retractomatic change at all.

The `LinearFilter` gate that's commented out in `retractomatic()` (`filter` / `getFilterVelocity()` —
stop when filtered \|turret speed\| < 4 rot/s ≈ 36 °/s, or when not targeting) is **not** the chatter
fix, and the data says why: the turret's speed *magnitude* stays above that threshold **~85% of the
match** (it's oscillating fast, not sitting still), so the gate would suppress only **~15–20% of the
transitions** — the ones where the turret is genuinely parked or crawling. Re-enabling it is still worth
doing — it stops the reel from working against a stopped turret and restores the intended "don't reel
when idle" behavior (~15 s/match of pull-in at near-zero turret speed) — but bill it as **idle
suppression, not de-chatter**.

To desensitize the reel *independently* of the turret fix, add **hysteresis / persistence** to the
pull↔coast decision: only switch direction after outward motion persists past a small velocity or time
threshold, so a momentary reversal doesn't flip the command. Keep it modest — too much and the reel
keeps pulling *in* after the turret has genuinely reversed to going *out*, tensioning the tether. (The
cleaner long-term design is to drive the reel off turret *position* / desired tether length rather than
instantaneous velocity sign — a rebuild, not a tweak.)

**Implementation gotcha if you re-enable the gate:** `getFilterVelocity()` already calls
`filter.calculate(...)` every loop (it's an `@AutoLogOutput`). If `retractomatic()` calls
`filter.calculate(...)` again the same loop, you step the single-pole IIR **twice per cycle** — halving
its effective time constant and corrupting its state. Compute the filtered speed **once** per loop into a
field and read it in both places. (They're also inconsistent today: the logger filters `abs(vel)`, the
commented gate filtered raw `vel` and took `abs` outside.)

### 4. No current limit is configured — but a limit above the command wouldn't do what you'd think
**Correction to an earlier draft of this section, which recommended a ~20–25 A limit as "cheap
insurance" against the stall. That reasoning was wrong, and it's worth walking through because it
sharpens the stator-vs-supply distinction.**

The retractomatic runs in **`TorqueCurrentFOC`**, so **the stator current *is* the command** (~15 A).
That has two consequences:

- **Any limit set above 15 A — stator *or* supply — can never engage**, because the command already caps
  the stator at 15 A. A 25 A limit just sits there. To change behavior you'd have to command less, or set
  a limit *below* 15 A (which weakens the pull everywhere, not only at stall).
- **A *supply* limit is the wrong tool for a stall anyway.** Supply current ≈ `duty × stator`, and duty
  → 0 at zero speed: measured, the stall case is ~15 A stator at ~0.6 V (duty ~0.06), i.e. **~0.6 A on the
  battery side**. Peak supply *anywhere* in a match was ~13 A. A battery-side limit is blind to a stalled
  motor — stall heat is an `I²R` *stator*-side phenomenon.

And the premise was thin to begin with: ~15 A for the measured ~4–8 s is well within this TalonFX's
continuous rating (`∫I²dt ≈ 10,000 A²s/match`), so it isn't a thermal problem today.

What actually changes stall/idle behavior is changing the **command**, not adding a ceiling above it:
detect near-zero reel speed for > ~0.5 s and **drop to a lower hold current** (e.g. 5–6 A, enough to keep
tension), or time it out — and that's really about tether/mechanism wear and the 0↔15 A chatter (#3),
not motor heat. The *one* defensible reason to add a stator limit is pure **fault insurance**: a sane
ceiling well above 15 A (say 40 A) that only trips if a bad preference value or code bug commands
something absurd. That's a different goal than "protect the stall," and it won't trip in any behavior
these logs show. (Contrast the turret's 40 A stator limit, which is real work: the turret is
voltage-controlled, so *there* the current is whatever the load pulls and a limit genuinely clamps it.)

### 5. Minor: unverified magic values and a dead equality branch
The **−10° minimum-tether facing** and the **−15 A pull / 0 A pay-out** are all untuned placeholders
(the −10 literally carries a `TODO`). The `currentFacingAngleRelative == 0.0 || currentVelocity == 0.0`
branch (the "at minimum / not moving → 0 A" case) uses exact float equality and so is effectively
**unreachable** — near-zero velocity falls into a sign branch instead. Harmless, but it means the "hold
nothing when stopped" intent isn't actually implemented; the filtered-gate fix in #3 is what would give
you that behavior for real.

---

## What's already good (keep it)
- **Torque control is the right tool** for a tensioning reel — commanding *force* on the tether rather
  than position is a sound choice, and it's self-capping at the commanded 15 A; the mechanism just needs
  its inputs cleaned up.
- **CAN traffic trimmed** (`optimizeBusUtilization`, explicit update rates).
- **Health-gated with the turret.** When the turret's motors/encoder report unhealthy, `goToPosition`
  stops the retractomatic too — so it can't keep reeling against a dead turret.
- **Energy is a non-problem.** ~0.75 Wh/match; nothing to optimize on the power budget.

---

## Plan / status (as of this review)
1. **Fix `getRetractomaticPosition()`** to read the retractomatic — *one-liner, do first* so future logs
   carry real reel position.
2. **Reduce the commanded current on sustained stall/idle** (lower hold current or a timeout) — the real
   lever. A current limit *above* the 15 A command is redundant and can't address the stall (see #4); a
   ~40 A stator limit is worth adding only as fault insurance against a bad command value — *proposed.*
3. **Cut the pull/coast chatter** — primarily by de-hunting the turret (turret finding #1), which the reel
   mirrors ~1:1; re-enable the filtered gate as *idle* suppression (only ~15–20% of the flips, not a
   de-chatter), add hysteresis to the direction decision if more is needed, and compute the shared filter
   once per loop — *proposed.*
4. **Tune the placeholders** — measure the true minimum-tether facing, and decide whether pay-out needs a
   small positive torque — *practice-field task.*

**Files:** `Turret.java` (`retractomatic()`, `getRetractomaticPosition()` bug, `configureMotors()`
retractomatic config with no current limit, commented-out filtered-motion guard, `p_goingInCurrent` /
`p_goingOutCurrent` preferences), `Constants.java` (`TURRET_RETRACTOMATIC_ID`). Logs: Newton Q23/Q34/Q64,
Newsom Q14. Companion: `turret-power-analysis.md`. Cross-referenced with `hottub-power-analysis.md`.
