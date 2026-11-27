# Why ARTEMIS Was Browning Out — Power Draw Analysis

Analysis of AdvantageKit match logs from Newton (World Champs, Apr 30–May 1) and Newsom/NECMP2 (Apr 16–18), cross-checked against MABOS logs (Mar 27–29) and the 2026-Robot codebase (frc-88/2026-Robot, main branch).

## The headline

The robot was not drawing excessive power in any single place — it was drawing *moderately high power everywhere, continuously, all at once*. Measured average battery-visible draw through teleop was **110–160A**, with coincident peaks of **300–350A** whenever you shot on the move. No single subsystem looks alarming in isolation, which is exactly why eyeballing the logs found nothing.

At ~16 mΩ effective source resistance (battery + main power path, fitted from your own logs), 330A pulls the bus from 12.3V down to ~7V. Late in the match, after you've already consumed 4–5 Ah, the battery's working voltage droops further and the same peaks push below 6.5V — hence brownouts clustering at match end. The logs confirm it: Q23, Q47, and Q87 at Newton all show the RIO `BrownedOut` flag chattering in the final 30 seconds, and in Q23 (t=303s) every mechanism on the RIO CAN bus momentarily disconnected at once.

## Match-by-match summary (teleop, gross supply amps averaged over ~140s)

| Match | minV | time <8V | Drive | Steer | Shooter | HotTub | Feeder | Intake | Turret | Total avg | Flywheel spin-ups |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MABOS Q36 (Mar) | 6.27 | 11.5s | 85.9 | 10.8 | 18.4 | 12.9 | 5.4 | 0.5 | 7.7 | 142A | 19 |
| MABOS E7 (Mar) | 7.02 | 1.3s | 73.1 | 10.2 | 15.5 | 12.3 | 5.4 | 0.5 | 7.6 | 125A | 16 |
| NECMP2 Q52 | 6.58 | 5.5s | 66.3 | 9.9 | 22.7 | 17.1 | 7.4 | 21.3 | 5.6 | 150A | 15 |
| NECMP2 Q61 | 6.81 | 5.2s | 72.1 | 9.8 | 18.3 | 15.2 | 6.5 | 21.1 | 4.2 | 147A | 19 |
| NECMP2 E13 | 7.89 | 0.1s | 63.6 | 10.0 | 11.1 | 8.9 | 4.5 | 17.3 | 4.8 | 120A | 12 |
| NECMP2 E15 | 7.40 | 0.7s | 72.5 | 9.6 | 11.7 | 8.7 | 4.5 | 17.5 | 5.2 | 130A | 13 |
| NEWTON Q23 | 6.10 | 11.5s | 69.1 | 10.0 | 15.1 | 13.9 | 5.8 | 22.1 | 4.3 | 140A | 14 |
| NEWTON Q34 | 6.02 | 11.7s | 69.7 | 10.2 | 19.2 | 14.6 | 6.2 | 19.9 | 5.3 | 145A | 14 |
| NEWTON Q47 | 5.99 | 20.4s | 83.8 | 9.4 | 15.6 | 11.4 | 5.0 | 18.7 | 4.9 | 149A | 13 |
| NEWTON Q55 | 6.30 | 8.8s | 83.2 | 11.2 | 14.7 | 10.0 | 5.2 | 16.8 | 4.6 | 146A | 17 |
| NEWTON Q64 | 6.88 | 2.2s | 84.0 | 10.9 | 10.6 | 7.6 | 3.6 | 20.4 | 4.2 | 141A | 14 |
| NEWTON Q87 | 6.03 | 18.6s | 76.4 | 11.2 | 19.7 | 13.2 | 6.3 | 20.5 | 5.2 | 153A | 19 |
| NEWTON Q99 | 6.61 | 8.5s | 86.6 | 11.2 | 19.8 | 12.6 | 6.1 | 17.0 | 4.4 | 158A | 13 |
| NEWTON Q115 | 6.69 | 4.8s | 81.5 | 10.9 | 19.9 | 14.3 | 6.3 | 20.3 | 5.0 | 158A | 14 |

Notes: "gross supply" = |stator current| × |applied volts| / battery volts, integrated per motor. Counting regenerative braking as zero recovery (the battery-realistic view), Q115 still averages ~121A. Intake current at MABOS is near zero because the always-run-rollers-while-shooting behavior was added later — and event-over-event totals grew (125→150→158A) as features were layered on, matching your "worse toward end of season" observation.

## Finding 1 — The drivetrain is half the problem, and it isn't friction or gearing

Drive motors averaged 65–87A of supply draw despite an average chassis speed of only ~1.8 m/s. The telling numbers from Q99/Q115:

- Each module's drive motor averages **33–43A stator continuously**, and the current is just as high at cruise (>1 m/s) as when nearly stationary. A swerve cruising at 1.8 m/s should draw well under 10A/motor.
- **~45% of high-current samples have motor torque opposing wheel velocity** — the drive motors spend nearly half their time actively braking. Net mechanical work is small; the energy is going into accelerate-then-brake cycles, dumped as heat.
- Current direction flips ~2×/second — the cadence of driver stick corrections, not a control-loop oscillation.

The cause is in the code: drive velocity closed loop with `kP = 1.5` (≈4.7V of correction per 1 m/s of error), **no closed-loop ramp**, brake mode, and 45A supply limit per motor that the four motors sit at during every stick movement. Every joystick twitch becomes a full-torque slam in both directions. The `SlewRateLimiter`s in `DriveCommands` only apply when `shouldSlow` is true, and they're configured as `SlewRateLimiter(5.0, -10000000.0, 0.0)` — **the negative rate is effectively unlimited**, so decelerations (the braking half of the cycle) are never limited at all.

The steer motors add ~10–11A each (≈43A total) continuously with **near-zero net power** — classic azimuth hunting. Rotate-about-turret mode and constant small heading corrections keep all four azimuths repositioning (and the wheels scrubbing) essentially all match.

One mechanical flag: module 2 consistently draws ~20% less than the others (e.g. 29.7A vs 43.3A in Q99). Either M2 is your healthiest module and the other three have extra drag (tread, bearings, alignment), or weight distribution is uneven. Worth a free-spin comparison in the pit.

## Finding 2 — The shooting stack fires every load simultaneously

`shoot()` runs shooter + hot tub spinner + feeder + intake rollers in parallel, and `IsShooting` was true for 38–62% of teleop. During the worst 100ms voltage dips in Q115, the attribution was: drive ~160–175A, shooter ~50–95A, hot tub ~45–55A, intake rollers ~30–75A, feeder ~15A — **all stacked on top of each other, ~300–350A total**.

Contributors:

- **Flywheel restarts**: the shooter's default command is `stopShooter()`, so the flywheel spins from 0 to 44.75 rps **13–19 times per match**. Each spin-up is a ~100A supply event for the pair of Krakens (no supply current limit configured, and the follower gets a default config — no 60A stator limit like the main motor, just Phoenix defaults of 120A stator / 70A supply). This also explains shooting "over a longer time period than others": you pay a spin-up wait on every cycle.
- **Hot tub spinner** runs at 90 rps whenever on-target, averaging 13–17A with logged stall events (60A stator against a jammed ball column at near-zero speed).
- **Intake rollers** (2 Krakens + inner roller) run at a *minimum* of 90 rps whenever shooting — even with no balls incoming — via `deployJustIntake`'s clamp of `(drivespeed, 90, 120)`. That's ~20A average across the entire match, and the intake stays deployed with rollers spinning by default.
- **Retractomatic** applies a constant −15A torque current whenever the turret aims (which is always — `turret.aim()` is the default command). Small (~2A supply average) but continuous, and it's torque the turret motor has to fight.

## Finding 3 — Your instruments were lying to you

Two things made this invisible when you reviewed logs by eye:

1. **PDH logging is dead in every log all season.** `/PowerDistribution/TotalCurrent`, `Voltage`, and `ChannelCurrent` each log a single record of 0.0. The one signal that would have shown "160A average, 330A peaks" plainly was never recording. (It reports 24 channels then never updates — likely the PDH isn't being polled after init or has a CAN/termination issue on the RIO bus.)
2. **`RobotController.setBrownoutVoltage(6.5)`** lowered the RIO brownout threshold from the RIO2 default of 6.75V. That suppressed the brownout indicator until things were truly dire — the battery spent 5–20 seconds per match below 8V without tripping anything.

Meanwhile the batteries look healthy: pre-match resting voltage 12.3–12.9V, and effective source resistance ~16 mΩ is normal for battery + main wiring. This was a load problem, not a battery problem — though note you consumed ~4.5–5 Ah per match, a quarter of nominal capacity at a discharge rate where the usable fraction is far below nominal.

## Recommendations

Ordered by expected impact:

**1. Ramp the drivetrain (biggest single win).** Add `ClosedLoopRamps.VoltageClosedLoopRampPeriod ≈ 0.1–0.2s` to the drive motors, and/or drop drive kP substantially (feedforward kV is doing the real work in a velocity loop; kP=1.5 is fighting the driver). Fix the slew limiters to limit deceleration too (symmetric rates), and apply them always, not just when shooting. Target: cut the accelerate/brake churn. Even a 30% reduction in drive draw frees ~25A continuous.

**2. Lower and shape the drive supply limits.** 45A × 4 sustained is the single biggest brownout ingredient. Consider `SupplyCurrentLimit = 60–70A` peak with `SupplyCurrentLowerLimit ≈ 30–35A` and `SupplyCurrentLowerTime ≈ 0.5–1.0s` — full punch for real accelerations, much lower sustained draw. (You currently have `SupplyCurrentLowerTime = 0` with a flat 45A, which allows 180A of sustained drivetrain draw.)

**3. Idle the flywheel instead of stopping it.** Make the shooter default command hold ~50–60% of shooting speed. This eliminates most of the 13–19 full spin-ups per match, removes the ~100A spin-up spikes from the shooting stack, and shortens every shot cycle (more balls scored in less time — addressing the slow-shooting observation directly). Add a supply current limit (~30–40A/motor) to bound spin-up draw, and apply the same config to the follower — it currently runs on Phoenix defaults with no tuned limits.

**4. Stop running ball-path motors when they can't do work.** Gate the hot tub spinner and intake rollers on "shooter at speed AND feeding" rather than merely `isShooting`/on-target; drop the 90 rps minimum intake roller speed when stationary. The spinner's anti-stall logic should also back off on detected stall instead of holding 60A stator against a jam. Combined these are ~30–40A of continuous draw during shooting cycles.

**5. Calm the azimuths.** ~43A continuous for near-zero net work is worth attention: don't update module angles when commanded speed is ~0 (WPILib's optimize already helps, but rotate-about-turret keeps demanding tiny angle changes), and consider lowering the steer stator limit (your own TunerConstants comment says azimuth doesn't need much torque — 60A is generous) and softening steer kP=100 or MotionMagicExpo settings if modules hunt.

**6. Fix the instrumentation before tuning anything.** Get the PDH logging working (verify CAN wiring/termination and that `LoggedPowerDistribution` is refreshing) so you can see true total current at your next event, and restore the brownout threshold to default so the DS warns you early. Consider an Elastic/dashboard alert when battery voltage dips below ~7.5V.

**7. Sequence, don't stack.** A tiny scheduler tweak — e.g., delay spinner/roller ramp by ~0.5s after shooter spin-up begins, or hold drive acceleration briefly during spin-up (you already clamp speed to 65% while shooting; clamping *acceleration* matters more) — keeps the loads from peaking simultaneously, which is what actually takes the bus below 7V.

**8. Pit checks.** Free-spin all four modules and compare (M2 vs the rest); inspect tread wear from the constant scrub. Keep the battery practices you have — the data says they're fine.

## Methodology

Supply current per motor estimated as |stator current| × |applied voltage| / battery voltage from AdvantageKit signals (`/Drive/ModuleN/*`, `/RealOutputs/*`), integrated over the teleop enabled window. Cross-checked against battery voltage sag (fitted ~16 mΩ effective source resistance). Absolute figures are estimates good to ~±15%; relative comparisons between subsystems and matches are solid. Raw parsing/analysis scripts available on request.
