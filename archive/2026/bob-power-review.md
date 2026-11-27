# BOB (Nov 7, 2026): power draw per match vs. River Rage and NERD, and mid-event savings options

*Live document, updated as BOB logs come in. So far: Q2, Q7, Q14, Q21. Build: BaseComp `0d4e0b9` (dirty, built 08:37 Nov 7). Scripts and CSV are in `FRC Logs/power-bob-1107/`: `power.py`, `summary.py`, `stall.py`, `mech.py`, `bo_load.py`, `bo_load2.py`, `model.py`, `feeder_cap.py`, `model_feeder.py`, `floorfit.py`, `ramp_sim.py`, `ramp_check.py`, `ramp_effect.py` and `power_by_match.csv`.*

## Method
- **Total draw** is the sum of every logged motor **supply** current (each motor is alone on its PDP channel). Power = battery voltage × total current. Only enabled time counts. The grid is 20 ms.
- **Not logged:** roboRIO, radio, Limelights, CANivore and Pigeon, so all figures are a few amps low.
- **Excluded as abnormal:**
  - BOB Q2: the drive CAN devices were silent and the robot lost FMS for 30 s (see the end).
  - River Rage E15: the robot went dead about 60 s into the match.
  - NERD Q1: the Pigeon dropped and the robot sat idle for long stretches.

  That leaves BOB 3 matches, River Rage 10, NERD 9.

## Event averages (per full match)
| | BOB | River Rage | NERD |
|---|---|---|---|
| Energy | **52.0 Wh** | 58.0 Wh | 59.4 Wh |
| Charge | **5.51 Ah** | 6.11 Ah | 6.32 Ah |
| Mean power / current | **1171 W / 124 A** | 1306 W / 137 A | 1337 W / 142 A |
| Auto / teleop mean power | 1172 / 1171 W | 1414 / 1290 W | 1443 / 1322 W |
| Peak 1 s average power | 2149 W | 2357 W | 2281 W |
| p95 total current | 237 A | 252 A | 260 A |
| Mean power by quarter of the match | 1268 / 1415 / 1338 / **666** W | 1404 / 1435 / 1369 / 1015 W | 1426 / 1384 / 1385 / 1154 W |
| Time shooting (`IsShooting`) | **74 s** | 57 s | 72 s |
| Balls per match (flywheel-dip count) | **~211** | ~158 | — |
| Matches with a brownout | 3 / 3 | 8 / 10 | 8 / 9 |
| Median match time left at first brownout | 31.6 s | 29.2 s | 49.3 s |

## Per BOB match
| Match | Wh | Ah | Mean W | Peak 1 s W | Min V | First brownout (s left) | Brownout onsets |
|---|---|---|---|---|---|---|---|
| Q7 | 55.2 | 5.84 | 1242 | 2107 | 6.0 | 31.6 | 60 |
| Q14 | 54.5 | 5.64 | 1226 | 2138 | 5.9 | 17.8 | 55 |
| Q21 | 46.5 | 5.03 | 1046 | 2203 | 5.7 | **52.8** | **142** |

**Q21** was the worst match despite drawing the *least* charge. Bus voltage sat near 8.3 V on a 500 W load from about 110 s, and the robot did little after that. Its fitted source resistance rose from about 11–12 mΩ early to **22 mΩ** in the last 40 s; Q7 also hit 23 mΩ in its last 20 s. This is the same late-match battery collapse as at River Rage.

## Where the energy went (Wh per match, share)
| Group | BOB | River Rage | NERD |
|---|---|---|---|
| Drive | **24.4 (47%)** | 33.1 (57%) | 30.1 (51%) |
| Steer | 2.9 (6%) | 4.3 (7%) | 4.5 (8%) |
| Shooter | 6.0 (12%) | 4.4 (8%) | 5.9 (10%) |
| Feeder | **6.3 (12%)** | 3.8 (7%) | 5.1 (9%) |
| Floor/roof/funnel | 3.7 (7%) | 2.8 (5%) | 3.4 (6%) |
| Intake rollers | 6.8 (13%) | 7.2 (12%) | 7.2 (12%) |
| Turret/retracto/hood + pivot | 2.0 (4%) | 2.5 (4%) | 3.2 (5%) |

## What changed and why
1. **The pre-BOB limits work.**
   - Commit `0d4e0b9` set the drive supply limit to 35 A (from 45 A) and added a 25 A steer limit.
   - Per drive motor, p95 supply current is 34.4 A (45.0 A at River Rage). Steer p99.9 is 24 A (54 A at River Rage).
   - Drive charge fell about 0.8 Ah per match.
2. **Much of that was spent scoring more.**
   - Shooting time rose from 57 s (River Rage) to 74 s, and balls per match from about 158 to about 211.
   - The shooting stack (shooter + feeder + floor) used 1.73 Ah per match against 1.15 Ah at River Rage. That is about 8.2 vs 7.3 mAh per ball.
3. **The feeder works harder per ball.**
   - Running, the feeder draws a median of 36 A at 72 rps, against 25 A at 78 rps at River Rage.
   - The step appears in the Oct 29 practice logs and in every session since. Per log it is 22–50 A, so it depends on the ball load. It does not line up cleanly with the funnel direction flip.
   - Not resolved; a mechanical check (belts, guides, compression) is worth doing.
4. **The feeder, intake, floor and roof all run flat out.**
   - Each sits at 98–100% duty, because the setpoints (105 / 90 / 100 / 100 rps) are above what the motors reach (72–80 rps) on match voltage.
   - So small setpoint trims save nothing. Only a setpoint below about 70 rps reduces their draw, and that changes ball flow.
5. **Little draw is wasted.**
   - Stalled draw is negligible: intake, floor, feeder and shooter each spend under 1% of their charge at near-zero speed.
   - "Dry" shooting, more than 1 s from any ball, is about 5 s and 0.08 Ah per match.
   - The intake runs about 138 s of each 160 s match. That is 0.30 Ah while shooting, 0.36 Ah while not shooting and moving, and 0.04 Ah while not shooting and still.

## Brownouts at BOB
- 16 brownout episodes (onsets more than 1 s apart) across Q7, Q14 and Q21. **12 started while shooting** (11 with the robot still), and 12 were in the last 30 s.
- **9 of the 16 started within 0.5 s of the shooter or feeder spinning up.** At those onsets the roller floor drew 52–91 A, the feeder 30–58 A and the shooter 30–89 A.
- The median load in the 200 ms before an onset was only about 90 A. At about 22 mΩ late in a match, every 45 A of spike costs about 1 V, twice the early-match cost.

## Mid-event savings options (modelled on Q7, Q14, Q21)
**Model:** V' = V − Voc(Ah) + Voc(Ah') + R(t)·(I − I').
- Voc vs. charge drawn is fitted from each match's own log, smoothed and kept non-increasing.
- R(t) is fitted per 20 s window.
- A brownout is counted when the modelled V drops below 6.75 V.
- "Drop" means the clipped current is never drawn. "Carry" means it is drawn later.
- Charge-to-time conversion: at BOB's mean draw, 0.1 Ah ≈ 3 s of match.

| Change | Where | Saves (Ah/match) | Time < 6.75 V, Q7 / Q14 / Q21 | First dip, s left (Q7 / Q14 / Q21) | Cost / risk |
|---|---|---|---|---|---|
| As raced (model) | — | — | 5.3 / 5.6 / 12.6 s | 31.6 / 17.6 / 64.8 | — |
| **Intake rollers off while shooting** | `Intake.setRollerSpeed()` | **0.30** | 2.8 / 0.0 / 6.5 s | 23.0 / none / 33.9 | Team believes rollers help feeding; no data yet. A partial speed (e.g. 45 rps) saves roughly half. |
| Intake rollers 90 → 70 rps always | same | 0.08 | 4.6 / 4.7 / 11.3 s | ≈ unchanged | Slower pickup |
| HotTub ramp bug fix (0.25 s), **physics model** | `HotTub.java` line 99 | 0.02–0.05 | 4.5 / 4.6 / 11.7 s | 31.4 / 17.5 / 64.8 (**unchanged**) | About 0.2 s slower floor spin-up; very low risk. See the ramp section. |
| + feeder 0.25 s ramp *(smoothing model, likely optimistic)* | `Feeder.java` config | 0 | 3.2 / 4.5 / 10.5 s | ≈ unchanged | First ball after each (re)start up to about 0.25 s later |
| Shooter 30 A supply limit per motor | `Shooter.java` config | 0 | 4.6 / 5.3 / 12.7 s | unchanged | Slower spin-up |
| Ramps + shooter 30 A *(smoothing model)* | | 0 | 2.7 / 4.4 / 10.3 s | ≈ unchanged | |
| Drive 35 → 30 A | `ModuleIOTalonFX` | 0.03–0.19 (drop), 0 (carry) | 3.4 / 5.2 / 11.9 s (drop) | ≈ unchanged | Softer mid-speed acceleration. River Rage auto sim: first sprint can end ~0.3 m short. |
| Drive 35 → 25 A | same | 0.21–0.48 (drop) | 1.3 / 0.0 / 8.1 s | 11.6 / none / 64.8 | Drivers will feel it; auto not validated |

**Model caveats:**
- The first-dip column is set by single isolated dips, so it is noisy.
- The as-raced model puts Q21's first dip at 64.8 s left; the logged brownout was at 52.8 s.
- Three matches is a small sample.
- The "smoothing model" rows applied a generic 0.12 s low-pass to the motor current. The physics model in the ramp section supersedes it for the HotTub, and shows the smoothing version overstated the benefit.

**Read (corrected after the ramp analysis):**
- No simple code change removes the late-match brownouts. Together they trim roughly 0.1–0.4 Ah, about 3–12 s of match.
- **Only changes that save charge move the first brownout:** intake rollers while shooting, and a lower drive limit.
- **Spike-shaping changes (HotTub ramp, feeder ramp, feeder or shooter supply limits) trim time below threshold but don't delay the first brownout.**
- The match-to-match spread in when the battery collapses is larger than any of these: Q21 collapsed on about 0.8 Ah less charge than Q7.

## HotTub ramp: effect on time to first brownout (21 full matches: BOB 3, River Rage 10, NERD 8)
**Bug:** `spinnerConfig.ClosedLoopRamps.DutyCycleClosedLoopRampPeriod = 0.25`, but the motors run `VelocityVoltage`, so the ramp has never been active. The fix is `VoltageClosedLoopRampPeriod = 0.25`, which in Phoenix 6 means 0 → 12 V in 0.25 s.

**Physics model of the floor motors (Spinner and Roof):**
- Fitted from the logs: applied V = 0.118 V/rps × speed + 0.024 Ω × stator current (median error 0.1 V). Steady load is about 12 A (Spinner) and 7 A (Roof).
- Inertia: logged spin-ups go from 10 to 60 rps in a median of about 50 ms, which gives about 18 rps/s per amp. A sensitivity check used 12 and 25.
- Gate = `IsShooting && OnTargetRobot`.
  - **Gate on:** full bus voltage, 60 A stator limit.
  - **Gate off:** 0 V (the motor brakes through its windings and draws nothing from the bus).
  - **With the ramp:** output slews at 48 V/s both ways.
- Simulated at 1 ms using each match's gate timing and smoothed bus voltage. The sim leads the logs by about 1 sample (CAN and logging latency), so it is shifted by that.

**Validation:**
- At each gate-on with the drive steady, the battery drops a median of 1.1 V. That implies about 95 A of extra draw (floor + feeder) at 12 mΩ. The sim gives about 133 A.
- So results are shown both as simulated (k = 1) and scaled to the measured dips (k = 0.71).
- The logged floor supply current under-reads these spikes (median logged peak 18–30 A per motor, against about 50 A simulated) because its status frames are slower than the spike.

**Spike at each gate-on, per motor (median):** about 51 A without the ramp, 25–30 A with 0.25 s, 15–20 A with 0.5 s.

| Scenario | Matches with a dip < 6.75 V | Median s left at first dip | Per-match change in first dip | Total time < 6.75 V (21 matches) | Charge saved |
|---|---|---|---|---|---|
| As raced (model) | 18 / 21 | 48.4 s | — | 83.4 s | — |
| Ramp 0.25 s, k = 0.71 | 18 / 21 | 48.8 s | **median 0.0 s** | 75–77 s (−8 to −10%) | ~0.03 Ah |
| Ramp 0.25 s, k = 1 | 18 / 21 | 49.0 s | median 0.0 s | 72–77 s (−8 to −13%) | ~0.04 Ah |
| Ramp 0.5 s, k = 0.71 | 18 / 21 | 48.5 s | median 0.0 s | 76–79 s (−6 to −9%) | ~0.03 Ah |

Ranges cover inertia 12 / 18 / 25 rps/s per A and lag 0 / 1 / 2 samples. The model's as-raced first dip matches the logged first brownout within 2 s in 15 of 18 matches.

- **BOB first dips with the ramp:** Q7 31.6 → 31.4 s left, Q14 17.6 → 17.5, Q21 unchanged.
- In the other matches, single near-threshold samples move the first dip by up to ±7 s in either direction. A few outliers jump further because a different near-threshold sample becomes first. Overall there is no net delay.

**Why it doesn't move the first brownout:**
- The ramp roughly halves the floor's restart spike. But the first brownout of a match comes inside a cluster of near-threshold moments on an already-depleted battery.
- With the floor spike gone, the same episode still crosses 6.75 V within about 0.1–0.2 s, from the feeder, shooter or drive.
- The ramp saves almost no charge, so the battery curve doesn't shift.

**Verdict:**
- Still worth making: it's a one-field bug fix, it removes about 25 A per floor motor from every restart, and it trims time below threshold by about 10%.
- But by the team's metrics (brownout matches, time left at the first brownout) it does **nothing measurable**.
- A longer 0.5 s ramp is no better.

## Feeder supply limit (asked Nov 7, after Q21)
**Current setting:** 60 A flat (`SupplyCurrentLimit` = `SupplyCurrentLowerLimit` = 60), 120 A stator. Control is `VelocityVoltage` at 105 rps, which the feeder never reaches, so it runs at full duty.

**Feeder supply current while running at BOB:**
- p50 / p75 / p90 / p95 / p99 / max = 36 / 45 / 54 / 58 / 64 / 77 A.
- In the first 0.3 s after a start: p50 41 A, p90 59 A.
- At River Rage the median was 25 A.

| Cap | Feeder time above cap | Share of that in startups | Charge above cap (Ah/match) | Total time < 6.75 V across Q7/Q14/Q21 (carry / drop) |
|---|---|---|---|---|
| 60 A (as raced) | — | — | — | 23.5 s |
| 50 A | 15% | 55% | 0.018 | 23.3 / 22.4 s |
| **45 A** | 25% | 45% | 0.036 | 22.8 / 20.9 s |
| 40 A | 37% | 39% | 0.064 | 21.8 / 19.5 s |
| 35 A | 54% | 33% | 0.104 | 20.7 / 17.5 s |
| *(HotTub ramp fix alone, physics model, k = 0.71)* | | | | *20.8 s* |

**Motor model** (fit from logged feeder voltage/speed/current, median error 0.14 V): applied V = 0.120 V/rps × speed + 0.0274 Ω × stator current. A supply cap limits stator × duty, so it removes torque **at speed**, not at stall. Maximum stator current on a 10 V bus:

| Speed (rps) | 0 | 10 | 20 | 30 | 50 | 70 |
|---|---|---|---|---|---|---|
| 60 A cap | 120 | 120 | 111 | 96 | 75 | 60 |
| 45 A cap | 120 | 108 | 92 | 78 | 59 | 47 |
| 40 A cap | 120 | 101 | 85 | 72 | 54 | 42 |
| 35 A cap | 113 | 93 | 78 | 65 | 48 | 37 |

**Consequences:**
- **Breakaway torque at a dead stall is unchanged at 40 A and above.**
- **Under heavy load the feeder slows instead.** For example, a 50 A stator load runs at about 64 rps under a 45 A cap, against 72 rps uncapped. At BOB, steady feeding is above 45 A about 14% of feeding time. At 35 A the cap would also clip ordinary feeding in the 35–45 A band, 23% of running time.
- **The cap bites harder late in the match**, when the bus voltage is lower.
- **The jam detector fires later.** `Feeder.isJammed()` (torque > 100 A, speed < 35 rps) can only be reached:

  | Feeder cap | Feeder must slow below |
  |---|---|
  | 60 A (now) | ~25 rps |
  | 45 A | ~14 rps |
  | 40 A | ~10 rps |

  Real jams in `jam-review-1105` reached 5–21 rps at 115–123 A, so those would still be caught, just later. Bogs at 26–30 rps / 97–101 A would no longer trip it.

**Recommendation:**
- If the team wants a feeder limit, use **45 A flat**: set both `SupplyCurrentLimit` and `SupplyCurrentLowerLimit`. Don't go below 40 A.
- It is a spike lever, not a charge lever. Like the HotTub ramp, expect it to trim time below threshold without moving the first brownout.

**Related: the feed gate chatters more at BOB.**
- `ON_TARGET_DEBOUNCE_SEC` was set from 0.2 to **0.0** in `7f70d66` ("riverrageupdates", Oct 29).
- `OnTargetRobot` re-opens while shooting 74 times per match at BOB, against 42 at River Rage and 27 at NERD. 91% of the closures last 0.2 s or less.
- Each re-open restarts the feeder and the floor.
- Why it was set to zero isn't known. If it was for shot accuracy, a small value such as 0.1 s may be a compromise.

## BOB Q2: not a power issue, but needs attention
- **Only module 0's drive motor reported.** All 4 steer motors and the other 3 drive motors logged nothing for the whole match.
- The health monitor raised Drive and Gyro faults at DS connect, before the match.
- **The DS/FMS connection also dropped for 30 s**, 75 s into teleop. The battery stayed at 12.7–12.8 V and there was no brownout.
