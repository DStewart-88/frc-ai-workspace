# Drive Motor Tuning Guide

**Purpose:** A repeatable process for tuning swerve drive motors that catches power/tuning issues during build season instead of at competition. Built directly from the gaps found in this year's brownout analysis.

**Core principle:** This year's process was "run auto-characterization → drive it → feels fine → done." That collapses three distinct jobs into one step, and the middle one never actually happened. Going forward, treat these as **five separate passes**, each with its own test and its own pass/fail number — not a single vibe check at the end.

| Pass | Question it answers | Config values it sets | This year's status |
|---|---|---|---|
| 1. Feedforward characterization | How much voltage does steady speed need? | `kS`, `kV`, `kA` | Partial — `kV` characterized, `kS` left at 0 |
| 2. Feedback tuning | How hard should we correct when we're off? | `kP`, `kD` | Skipped — left at generator default (`kP=1.5`) |
| 3. Output shaping | How fast can commanded voltage change? | `VoltageClosedLoopRampPeriod` | Skipped — left unset (0) |
| 4. Input shaping | How fast can the driver's request change? | `SlewRateLimiter` params in `DriveCommands` | Misapplied — asymmetric, built for shooting not driving |
| 5. Validation | Does the real robot match the model? | N/A — a test, not a config | Skipped — no power check before competition |

---

## Pass 1: Feedforward Characterization (`kS`, `kV`, `kA`)

**What it measures:** The voltage a motor needs just to hold a given speed, with zero contribution from correcting error. `kS` is the voltage to overcome static friction (break from rest). `kV` is the voltage per unit speed to overcome back-EMF. `kA` is the voltage per unit acceleration to overcome inertia.

**Why it matters:** This is the term that should be doing almost all the work during smooth, steady driving. If it's accurate, `kP` only has to clean up small residual error — which is what makes Pass 2 possible to tune correctly. An inaccurate or incomplete feedforward (like `kS=0` this year) forces `kP` to compensate for things it was never meant to handle, which is exactly what happened.

**You already have two tools for this in the codebase — use both, they answer different questions:**

### Test A: Quick ramp characterization (`DriveCommands.feedforwardCharacterization()`)
Already wired up on SmartDashboard as **"Drive Simple FF Characterization."**

- Procedure: robot enabled, open area, press the button. It ramps drive voltage slowly and logs velocity vs. voltage, then linear-regresses `kS` and `kV` and prints them to the console.
- Gives you: `kS`, `kV` only (no `kA`).
- Use this for: a fast sanity check, or re-checking `kS`/`kV` after a mechanical change (new wheels, bearing service, weight change) without a full SysId pass.
- **This is the test that was apparently skipped or discarded this year** — the button exists, but live `kS` is still 0. Run it and actually apply the printed value to `TunerConstants`.

### Test B: Full SysId routine (`Drive.sysIdQuasistatic()` / `sysIdDynamic()`)
- Procedure: run quasistatic forward, quasistatic reverse, dynamic forward, dynamic reverse (standard SysId 4-test sequence), each logged as a `.wpilog`. Feed the log into the WPILib SysId analysis tool.
- Gives you: `kS`, `kV`, **and `kA`** — the full picture, including how the motor responds to sudden acceleration, not just steady speed.
- Use this for: the primary once-per-robot characterization pass. It's slower to run and analyze than Test A, but it's the one that gives you a complete, defensible model.

**Test data to log during both:** per-motor voltage, velocity, and stator current — even though these routines are about voltage/velocity, logging current alongside lets you eyeball whether current tracks the predicted curve later, without needing a separate test.

**Pass criteria:**
- `kS` should come out **non-zero**. If a characterization run gives you `kS ≈ 0`, that's a red flag to re-run the test, not a result to accept — real drivetrains always have some static friction (bearings, gear mesh, wheel-to-carpet).
- Sanity-check `kV` against `kSpeedAt12Volts`: compute free speed from `kV` and your gear ratio/wheel radius, and confirm it's close to the `kSpeedAt12Volts` value in `TunerConstants`. If they disagree significantly, something's wrong with the ratio or the test, not just the number.

---

## Pass 2: Feedback Tuning (`kP`, `kD`)

**What it measures:** How much extra voltage to add per unit of *tracking error* — the gap between commanded and actual velocity that feedforward alone doesn't close.

**Why it matters:** This is the term that was never actually tuned this year — `kP=1.5` is the untouched Tuner X generator default. With good feedforward already doing most of the work (from Pass 1), `kP`'s job is small: clean up residual error, not drive the whole response. Tuning it too high is what caused this year's problem — every setpoint change got treated as a full-authority correction instead of a small cleanup.

**Test: step response, with current logged alongside velocity.**

- Setup: robot on blocks or in an open area, one module at a time if possible (or all four, if isolating one is impractical).
- Procedure: command a step change in target velocity — not a ramp, an actual step (e.g., 0 → 2 m/s instantly via a test command). Log commanded velocity, actual velocity, and stator current on the same timeline.
- Start with `kP = 0` (pure feedforward) and increase in small increments (e.g., start near 0.1-0.2, well below this year's 1.5).
- **What you're looking for at each increment:**
  - Does velocity settle to the commanded value, or does it plateau short of it? (Steady-state error means you need more `kP`.)
  - Does current spike, then decay back down as velocity converges? (Expected, healthy.)
  - Does current stay elevated *after* velocity has already settled? (You've gone past the useful range — more `kP` now, just costs current without improving response.)
- **Stop at the smallest `kP` that removes steady-state tracking error.** Not "the value that feels snappiest" — that's exactly the instinct that led here.

**On `kD`:** be cautious. `kD` acts on the *derivative* of velocity error, and velocity signals from encoders are inherently noisy — differentiating noise amplifies it, and a poorly-tuned `kD` can inject high-frequency current chatter that looks a lot like the original problem. Leave `kD=0` unless the step response after `kP` tuning shows genuine overshoot/oscillation that a small amount of `kD` measurably damps. Don't add it preemptively.

---

## Pass 3: Closed-Loop Output Shaping (`VoltageClosedLoopRampPeriod`)

**What it measures:** How fast the Talon is allowed to change its actual applied voltage, regardless of how fast the PID+FF math wants to move.

**Why it matters:** Even with a well-tuned `kP`, a sudden setpoint change (like a driver reversing the stick) still produces a real, large error for one control cycle. This setting is what prevents that instantaneous error from becoming an instantaneous voltage swing and current spike.

**Test:**

- Set a candidate ramp period (start around 0.1-0.2s) in `TunerConstants` drive motor config.
- Have a driver run a normal practice session — not a scripted test, actual stick-driving with typical corrections — with per-motor current logged.
- Compare average and peak current against the same drill run with the ramp period at 0.
- **Also get driver feedback specifically on responsiveness** — ask directly, don't infer from watching. A ramp period that's too long will feel sluggish on quick reversals, and that's a real cost, not a false complaint.

**Pass criteria:** the shortest ramp period where current during normal driving drops meaningfully (aim to get within range of your Pass 1 feedforward-predicted current — see Pass 5) *and* drivers don't report noticeably worse responsiveness. This is a genuine tradeoff — document both numbers (current saved, driver-reported feel) when you land on a value, so it's a documented decision and not a guess buried in a constants file.

---

## Pass 4: Input Shaping (`SlewRateLimiter`)

**What it measures:** How fast the *commanded* setpoint (from joystick input) is allowed to change, before it even reaches the control loop.

**Why it matters:** This is the one that got misapplied this year — added for shooting stability, with a negative rate effectively unlimited, so it never smoothed deceleration at all. This is a separate layer from Pass 3: Pass 3 shapes the voltage *output*, this shapes the setpoint *input*. You likely want both, tuned independently.

**Steps:**
1. Fix the immediate bug: give the negative (deceleration) rate a real, finite value — start by mirroring the positive rate, then tune independently if needed.
2. Decide whether shooting-stability smoothing and general-driving smoothing should be the same limiter or two separate ones. Reusing one limiter for two different jobs is likely how this got tangled in the first place — a dedicated, tighter limiter that only engages during shooting (via the existing `shouldSlow` flag) plus a separate, always-on baseline limiter for normal driving is probably the cleaner design.
3. Test the same way as Pass 3: practice driving, log current, get driver feedback on feel, particularly during shooting sequences where the original limiter was actually needed.

---

## Pass 5: Validation — Does the Real Robot Match the Model?

**This is the step that was missing entirely this year, and it's the one that would have caught the problem before competition.**

**What it does:** Confirms that after Passes 1-4, actual measured current during real driving matches what your characterization model predicts — not just that the robot "feels" fine.

**Procedure:**
1. Using your Pass 1 `kS`/`kV`/`kA` and the robot's actual mass/gear ratio, compute predicted current for a representative practice drive (a normal 1-2 minute scrimmage-style session, no shooting, no game pieces — just driving).
2. Run that same drive for real, logging actual per-motor current and velocity.
3. Compare: does measured average current land close to the model's prediction? Does current visibly track velocity/acceleration the way the model says it should — rising during real accelerations, dropping near zero at steady cruise and at rest?

**The specific failure signature to check for** (this is what this year's data showed, and what a validation pass would have surfaced immediately): current staying elevated independent of speed — high even when velocity is near zero, or not dropping at steady cruise. That mismatch is the tell, more than any single "too high" number.

**Set a numeric bar before you start, not after:** e.g., "average drive current during a representative practice run should be within ~2x of the feedforward model's prediction." Make it a real pass/fail line, run early in build season — not a subjective "seems fine" at the end.

---

## Build-Season Checklist (carry this forward every year)

- [ ] Run **both** feedforward characterization tests (quick ramp + full SysId) — don't stop at whichever one runs first
- [ ] Confirm `kS` came out non-zero; re-test if it didn't
- [ ] Cross-check `kV` against `kSpeedAt12Volts` for a sanity match
- [ ] Tune `kP` via step-response test with current logged, stopping at the smallest value that removes steady-state error
- [ ] Leave `kD=0` unless step response shows measurable oscillation
- [ ] Set a real `VoltageClosedLoopRampPeriod` as a default in the swerve template, not an afterthought
- [ ] Audit any `SlewRateLimiter` usage on the drivetrain — confirm both rate directions are intentional, not generator defaults or leftovers from an unrelated feature
- [ ] Run a validation pass with a real numeric target **before** the first competition, not after a brownout at one
- [ ] Confirm PDH/PDP total current and brownout fault logging is actually capturing data (unconfirmed as of this year — verify this explicitly)
