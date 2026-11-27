# River Rage (Oct 24, 2026): shooting-stack startup spikes vs. brownouts

*Source: the 13 enabled `.wpilog` files in `2026 Logs/river rage/` (BaseComp build `b2e88a99`). Scripts, pickles and CSVs are in `FRC Logs/shoot-spike-riverrage-1024/`. All currents are logged per-motor **supply** current (each motor is alone on its PDP channel). Logged at 50 Hz, so peaks shorter than about 20 ms are under-represented.*

## Question
At every shoot start, the shooter, feeder and roller floor (the `HotTub` class: spinner + roof + funnel) show a short, high current spike that lines up with a deep battery dip. Is there a simple fix, and is that spike what's driving the brownouts?

## Short answer
- **The spike is real, but it isn't what browns the robot out.** It's the trigger that pushes a battery over the edge only once that battery is already exhausted late in the match.
- **One simple, config-only fix exists, and it's a bug fix.** `HotTub` sets `DutyCycleClosedLoopRampPeriod = 0.25`, but the motors run `VelocityVoltage`, which uses `VoltageClosedLoopRampPeriod`. So the 0.25 s ramp the code clearly meant to add has never been active. Changing that one field gives the ramp to all three roller motors. Expected gain: a shoot-start dip about **0.15 V shallower**, with no measurable change in brownout count.
- **What the data points to instead: battery capacity.** 95% of brownout events happen in the last quarter of the match, and *how bad* they get tracks the battery, not the load.

## What the spike looks like
Ensemble average across 206 shoot-window starts (trigger pulls, `IsShooting` rising edge):

| t from start | shooter | feeder | floor/roof/funnel | intake | drive+steer | battery dip |
|---|---|---|---|---|---|---|
| −0.04 s | 0 A | 0 A | 0 A | 21 A | 104 A | — |
| +0.04 s | 32 A | 31 A | **42 A** | 20 A | 93 A | −0.66 V |
| +0.20 s | 47 A | 24 A | 20 A | 18 A | 52 A | −0.41 V |
| +0.60 s | 29 A | 22 A | 17 A | 16 A | 66 A | −0.43 V |

- The sharpest part is the **roller floor + feeder** in the first 40 ms. The shooter builds over about 0.1–0.3 s instead.
- The drive drops at the same moment, because of the shooting speed clamp, which partly cancels the spike.
- The feeder and floor restart about **2.7 times per shooting window** (549 restarts across 206 windows), because `runFeeder`/`runSpinner` gate on `OnTargetRobot`. So the spike happens far more often than the trigger is pulled.
- 26 of the 38 sub-7 V dips that happened while shooting were within 0.5 s of a feeder/floor (re)start.

## Why it isn't the brownout driver
- **When brownouts happen:** of 471 `BrownedOut` onsets, **450 are in the last quarter** of the match, 21 in the third quarter, and **0 in the first half**. Of the 40 dips below 7 V in full matches, 25 are in the last quarter and 3 in the first half. The same shoot-start spike rides through harmlessly early in the match.
- **What's running when they happen:** only 42 brownout onsets (9%) are within 0.5 s of a shoot start. 267 (57%) happen while not shooting at all.
- **What-if models** (each motor's current reshaped, battery voltage re-estimated using each log's measured source resistance of about 10–11 mΩ):

| Scenario | dips < 7.0 V | dips < 6.5 V | shoot-start minimum V |
|---|---|---|---|
| As raced | 41 | 20 | — |
| 0.25 s ramp on floor + feeder | 43 | 23 | +0.16 V |
| Shooter 40 A supply limit | 39 | 20 | +0.00 V |
| Lower supply limits on the whole stack (shooter 40, floor 30, feeder 40) | 37 | 23 | — |

  Blunting the spike doesn't remove the charge. It just spreads it later, where it still overlaps the sustained load (roughly 100 A for the stack plus about 110 A for the drive while shooting).

## Energy budget (10 full matches, mean per match)
**6.1 Ah/match**, up from about 4.5–5 Ah at the April events. Mean draw is 122–149 A for the whole match.

| Group | Ah | Share | Drawn while shooting |
|---|---|---|---|
| Drive | 3.51 | 57% | 0.58 |
| Intake rollers | 0.74 | 12% | 0.24 (the other 0.5 Ah is the always-on default command) |
| Shooter | 0.47 | 8% | 0.47 |
| Steer | 0.45 | 7% | 0.13 |
| Feeder | 0.39 | 6% | 0.39 |
| Floor/roof/funnel | 0.29 | 5% | 0.29 |
| Turret + retractomatic | 0.22 | 4% | 0.06 |

## The battery signal
Every match started on a charged battery (rested 12.7–12.95 V). The estimated open-circuit voltage in the last eighth of the match (V + 0.011 Ω × I) separates matches cleanly. The amount of energy used does not:

| Match | Ah used | Est. Voc, last eighth | Time browned out |
|---|---|---|---|
| Q12 | 6.47 | 11.1 V | 0 s |
| E13 | 6.61 | 10.9 V | 0.1 s |
| Q7 | 5.82 | 11.0 V | 0 s |
| E10 | 6.20 | 10.4 V | 0.6 s |
| E4 | 6.22 | 10.7 V | 1.5 s |
| E12 | 6.54 | 9.5 V | 5.0 s |
| Q4 | 5.53 | 8.6 V | 9.8 s |
| E8 | 6.13 | 8.8 V | 10.7 s |
| Q18 | 5.40 | 9.9–10.7 V | 15.6 s |
| E14 | 6.14 | 9.0 V | 16.0 s |

Q12 and E13 drew the *most* energy and had no meaningful brownouts. Q18 drew the *least* and was browned out for 15.6 s. **That points to differences in battery capacity across the rotation, not to load.** The batteries don't carry IDs in the logs, so this can't be pinned to specific packs yet.

## Recommendations (lowest effort first)
1. **Battery triage (no code).** Number every battery and record which one ran each match. Capacity-test the packs if a CBA or load tester is available, and pull the weak ones from match use. Internal-resistance checkers (Battery Beak) catch high-IR packs but not lost capacity. This is the cheapest lever on late-match brownouts.
2. **Fix the HotTub ramp (one field, low risk).** `spinnerConfig.ClosedLoopRamps.VoltageClosedLoopRampPeriod = 0.25;` in place of the `DutyCycle...` line. It covers the floor, roof and funnel. Expect a slightly softer shoot-start dip and a slightly slower roller spin-up, about 0.25 s to full voltage. Optionally do the same on the feeder. Don't expect fewer brownouts from this alone.
3. **The real levers need integration and testing** (already developed, not merged): drive supply/steer limits (`current-limits` branch), the drive kV fix, shooter ready-idle, and the onTarget debounce for the feeder/floor gate. Drive is 57% of the energy.
4. **Logging:** add a battery ID per match (even an NT string set from the dashboard) so the battery-capacity hypothesis can be confirmed next event.
