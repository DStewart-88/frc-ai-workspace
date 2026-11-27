# Measured Supply Current Analysis — Offseason Drive Tests (2026-08-22)

Analysis of the four AdvantageKit drive-test logs from Aug 22 (the same A/B/B/A kV test
analyzed earlier), now that per-device **supply current** logging has been added. Focus:
excessive power draw, and what current limits would reduce brownout risk without a big
performance cost.

## The one-line answer

The drivetrain's power draw is **not excessive in any "something is wrong" sense** — sustained
draw is modest (~12A/motor at cruise) and the high numbers are all short **acceleration**
spikes. Because the draw is an acceleration cost and *not* a top-speed cost, you have real room
to lower the drive supply limit: **a per-motor supply limit around 35A (or a tiered 50→30A
limit) trims the launch peaks that feed brownouts while leaving cruise and top speed untouched.**
The current limit (~45A) is set so high it almost never binds.

## First, the good news: your old estimates were right

The brownout analysis back in July had to *estimate* supply current as
`|stator current| × |applied volts| / battery volts`, because no supply current was logged.
These new logs record supply current directly, so we can finally check that method.

**It was almost perfectly accurate.** Across all four runs the estimate tracks the measured
total drive supply current at **r = 0.9985**, with a median ratio of **1.005** and run-average
agreement within **0.6%** (e.g. T1: 56.08A estimated vs 56.19A measured). See Panel A of the
figure. That means every conclusion in the July brownout analysis that rested on estimated
supply current stands on solid ground — the ~110–160A match averages and 300–350A stacked peaks
were real, not artifacts of the estimation method.

## What the drivetrain actually draws (fixed-kV runs T1 & T4)

These are the runs with the correct `kV = 0.871`, i.e. how the robot will actually be configured.

| Quantity | Per motor | 4-motor total |
|---|---|---|
| Median (moving) | 3–14 A | ~48–50 A |
| Mean (moving) | 10–18 A | 52–58 A |
| 95th percentile | 40–45 A | 132–150 A |
| 99th percentile | 48–51 A | 168–170 A |
| Peak | 55–65 A | **187–190 A** |
| Cruise / top speed (>3.8 m/s) | **~13.6 A mean** | ~55 A |

Two things jump out:

**The distribution is extremely peaky.** The median motor draws single-digit amps; the mean is
~12–18A; but the top few percent of samples slam into the ~45A supply limit. Total 4-motor draw
sits near 50A most of the time and briefly spikes to ~190A during hard launches — that's all four
motors hitting the ~45–48A limit simultaneously. (Panels B and D.)

**High current lives at low-to-mid speed, not at top speed.** Binned by wheel speed, per-motor
supply averages ~13–20A from 2–4 m/s (with 95th-percentile brushing the 45A limit during
accelerations *toward* those speeds) but *falls* once you're actually at top speed — only ~13.6A
per motor above 3.8 m/s. This is the physically expected pattern: back-EMF rises with speed, so a
motor holding top speed needs little supply current; the big draw is the torque to *get* there.
(Panel C.) **This is the key to the current-limit question:** a supply limit that clips the
launch peaks costs you acceleration, not top speed.

Effective source resistance fit from these logs is **~11–13 mΩ** (Voc ≈ 12.3–12.5V) — lower than
the ~16 mΩ measured on the competition robot, consistent with a fresh battery on a lighter dev
base. Minimum bus voltage was **9.4V** (T4) with **zero time below 9V** — no brownout, as
expected for a drivetrain-only test on a fresh battery (more on that caveat below).

## Is the current limit doing anything today?

Barely. At the current ~45A per-motor supply limit, the drive motors are above 45A only **4.6% of
moving time** (7% of accelerating time). Put differently, `45A × 4 = 180A` is a ceiling the robot
touches only on the hardest launches. The July analysis flagged that `SupplyCurrentLowerTime = 0`
with a flat 45A "allows 180A sustained" — the measured data confirms the *allowance* is 180A, but
the robot only actually realizes it in brief bursts. The limit is set high enough that it is
almost never the binding constraint, which is exactly why lowering it is cheap.

## Current-limit options, quantified

Modeled on the fixed-kV data by capping each motor's supply at `L` and measuring what gets clipped
and how the worst-case simultaneous 4-motor peak shrinks. "Sag recovered" uses ~14.5 mΩ applied to
the reduction in the worst-case 4-motor peak — i.e. the voltage you'd claw back at the instant all
four motors would otherwise peak together. "Top-speed risk" is the fraction of *high-speed* samples
(>3.8 m/s) that exceed `L` — a proxy for how often the limit would bite while you're going fast.

| Per-motor limit | 4-motor ceiling | Clipped (moving) | Clipped (accel) | Sag recovered @ peak | Top-speed risk |
|---|---|---|---|---|---|
| 45 A (current) | 180 A | 4.6% | 7.0% | — | 0.3% |
| 40 A | 160 A | 10.1% | 15.8% | ~0.15 V | 1.6% |
| **35 A** | **140 A** | **13.4%** | **20.8%** | **~0.44 V** | **4.0%** |
| 30 A | 120 A | 16.9% | 25.9% | ~0.73 V | 7.3% |
| 25 A | 100 A | 21.1% | 31.6% | ~1.02 V | 13.9% |

Reading this: dropping from 45A to **35A** cuts the worst-case simultaneous drivetrain peak from
180A to 140A and would recover roughly **half a volt** at the worst stacked instant, while only
clipping ~13% of moving samples and touching top-speed operation just 4% of the time. Below 30A
the top-speed risk and the fraction of clipped acceleration start climbing fast — that's where
drivers would begin to feel it.

### Recommendation

Rather than a single flat number, use Phoenix 6's tiered supply limiting to keep launch punch but
cut the *sustained* stacked draw:

- `SupplyCurrentLimit ≈ 50 A` (brief peak — preserves the initial launch impulse)
- `SupplyCurrentLowerLimit ≈ 30–35 A` (sustained)
- `SupplyCurrentLowerTime ≈ 0.5 s`

This gives full-torque launches for half a second, then settles each motor to 30–35A — which the
data shows is far above what cruise and top speed need (~13A/motor). Worst-case sustained 4-motor
draw drops from 180A toward 120–140A, directly shrinking the drivetrain's contribution to the
stacked peaks that push the competition bus below 7V. If you'd rather start simple, a **flat 35A
supply limit** is the single-number version and is a safe, easily-felt-out first step.

One more knob worth a look: the **azimuth/steer** motors average only ~3A total but spike to
**93–170A** for all four combined when the modules snap direction simultaneously (e.g. a reversal).
Average draw is trivial, but those synchronized transients are a real (if brief) brownout
ingredient, and the steer motors are already known not to need much torque — a modest steer supply
limit would clip those spikes for essentially no performance cost.

## Three caveats — read these before acting

1. **This is drivetrain-only, smooth-auto data.** No shooter, intake, hot tub, or turret load was
   present (those channels logged a single 0.0), and the robot followed a clean auto path with no
   driver stick-correction churn. So this test *understates* real-match total draw and does not
   reproduce the accelerate/brake churn the July analysis found at competition. The drive
   current-limit numbers above transfer directly, but the *brownout benefit* only fully shows up
   when drive is stacked with the mechanisms on a tired battery. The reassuring cross-check: the
   measured drive peaks here (170–190A for 4 motors) match the 160–175A the July analysis
   attributed to drive during the worst competition dips — so the drive half of the stacked peak
   is now confirmed by direct measurement.

2. **PDH total-current logging is still dead.** `/PowerDistribution/TotalCurrent` logged a single
   0.0 record again, and `/SystemStats/BatteryCurrent` is only the roboRIO's own input current
   (~0.3A), not the robot total. The instrumentation fix recommended in July hasn't landed. The
   good news is the new per-device supply channels now give you total draw by summation — but a
   working PDH total is still worth fixing for a true, independent bus-total at events.

3. **Fresh battery, dev robot.** ~12 mΩ source resistance and no sag here vs ~16 mΩ under match
   load. Don't read "no brownout in this test" as "the fix isn't needed" — read it as "this test
   isn't where brownouts live."

## Other analyses this new data unlocks

Now that supply current is logged per device, a few things that were previously only estimable are
directly measurable, and would be worth doing:

- **A real match / driver-practice log** with all mechanisms enabled on a mid-life battery — this
  is the one that would directly demonstrate the stacked peaks and let us confirm (not just infer)
  how much a drive supply limit lowers brownout time. This is the highest-value follow-up.
- **Per-mechanism supply cost of the shooting stack** — shooter, intake, hot tub, feeder, and
  turret now all log supply current, so we can measure the simultaneous-fire peak and the flywheel
  spin-up cost directly, and validate the "idle the flywheel" recommendation with hard numbers.
- **A supply-current-limit A/B test**, run exactly like the kV test — baseline vs 35A vs tiered —
  to measure the actual acceleration cost (0–4 m/s time) against the brownout benefit on hardware.
- **Azimuth-transient study** — quantify the synchronized steer spikes and whether a steer supply
  limit or angle-hold-at-zero-speed removes them.

*Method: parsed the four `.wpilog` files directly; supply current from
`/Drive/ModuleN/DriveSupplyCurrentAmps` and `TurnSupplyCurrentAmps`, zero-order-hold resampled to
50 Hz over the enabled window; speed from `DriveVelocityRadPerSec × 0.0508 m`; source resistance
from a least-squares fit of `SystemStats/BatteryVoltage` on summed supply current. Estimate
validation compares measured supply against `|DriveCurrentAmps| × |DriveAppliedVolts| /
BatteryVoltage`. Current-limit model caps per-motor supply and recomputes clipping and peak
reduction on the fixed-kV runs.*
