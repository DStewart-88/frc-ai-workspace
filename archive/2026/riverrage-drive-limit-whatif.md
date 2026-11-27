# River Rage: what if the drive supply limit were lower?

*Companion to `riverrage-shoot-spike-review.md`. Uses the 10 full River Rage matches (Q4, Q7, Q12, Q18, E4, E8, E10, E12, E13, E14) and BaseComp build `b2e88a99`. Scripts are `simdrive.py`, `simdrive_shooting.py`, `shoot_vs_not.py`, `drive_at_brownout.py`, `drive_eff.py`, `extract_steer.py`, `steer_analysis.py`, `steer_cap_cost.py`, `extract_auto.py`, `auto_overview.py`, `auto_fit3.py`, `auto_capsim2.py`, `overspeed.py` and `sim_combo.py` in `FRC Logs/shoot-spike-riverrage-1024/`.*

> **Update (Nov 1, 2026):** the Oct 29–30 practice logs (`practice-1029-1030-shoot-on-move.md`) revise two points here.
> 1. The shooting-brownout breakdown is now split into moving and still. When shooting on the move, the drive is about half the load.
> 2. The steer limit matters more with the current driver and build.
>
> Corrected below where marked.

## Limits as raced
| | Setting | Where |
|---|---|---|
| Drive supply | **45 A flat** per motor (`SupplyCurrentLowerTime = 0`, so no lower tier) | `ModuleIOTalonFX` |
| Drive stator / torque | 90 A (`kSlipCurrent`, also used as Peak±TorqueCurrent) | `TunerConstants` → `ModuleIOTalonFX` |
| Drive control | `TorqueCurrentFOC`, kP 70 / kS 5.5 / kV 20 | `TunerConstants` |
| Steer | **Phoenix defaults** (70 A supply → 40 A after 1 s, 120 A stator). The 60 A stator limit in `steerInitialConfigs` is never applied, because `turnConfig` is built fresh. The 20 A steer limit only exists on the unmerged `current-limits` branch. Steer control is `Voltage` (`PositionVoltage`, kP 100 / kD 0.5 / kS 0.1 / kV 2.49). | `ModuleIOTalonFX` |
| Stick scaling while shooting at the hub | x/y **×0.25**; rotation ×0.625 at all times; on-target debounce 0.2 s | `RobotContainer.driveRebuiltSOMETHING` (b2e88a99) |

**The 45 A supply limit does work under TorqueCurrentFOC.** Per-motor supply samples pile up at 40–45 A and fall off sharply above 45 A. A drive motor is at or near the limit about **20% of enabled time**.

## How much drive draw a cap would touch
| Cap | Time a drive motor sits above it | Share of drive Ah above the cap |
|---|---|---|
| 40 A | 20% | 4% |
| 35 A | 30% | 11% |
| 30 A | 37% | 19% |
| 25 A | 42% | 29% |

Holding top speed (3.5–4 m/s) takes about **15 A per motor**, so caps down to about 25 A don't cost top speed. They soften acceleration through the middle of the speed range, and at 30–35 A drivers will feel that.

## Load at the moment brownouts start
In the 200 ms before each of the 25 brownout episodes:
- Median total robot draw was only about **205 A**.
- Per drive motor, the median was 22 A. On average 1.4 of the 4 motors were at 40 A or more.

The batteries are so depleted by then that a moderate load browns them out. So a cap gives little *instant* relief: about 0.06 V at 35 A and about 0.13 V at 30 A, using a 11 mΩ source resistance. Any real benefit has to come from using **less charge over the match**, which keeps the battery's voltage higher late in the match.

## Model
For each match I modelled battery voltage as V = Voc(Ah used) − 0.011 Ω × I, with the Voc-vs-Ah curve fitted from that match's own log. A lower cap then helps two ways: less instantaneous sag, and less charge used. For the current a cap clips off, there are two bounds:
- **Drop:** that current is never drawn, because the robot accelerates more gently and reaches lower peak speeds in short moves.
- **Carry:** the same charge is drawn later instead.

The logged brownout total was 59.3 s across the 10 matches; the as-raced row is the model's baseline.

| Drive cap | Dips < 6.5 V (drop) | Time < 6.5 V (drop) | Ah/match (drop) | Dips < 6.5 V (carry) |
|---|---|---|---|---|
| 45 A (as raced) | 20 | 26.7 s | 6.11 | 20 |
| 40 A | 16 | 21.7 s | 5.96 | 24 |
| 35 A | 14 | 11.6 s | 5.74 | 25 |
| 30 A | 8 | 2.4 s | 5.44 | 25 |
| 25 A | 0 | 0 s | 5.08 | 25 |

Adding a 20 A steer limit moves either column only slightly.

**Where the truth sits:** the measured drive mechanical/electrical ratio in the high-current bands is about 0.75–0.8. So most of the clipped current would otherwise have turned into motion, and the carry bound isn't unrealistic. The savings are real only to the extent that gentler acceleration means less kinetic energy per short move. Expect somewhere between the two columns, probably less than the drop column.

**No kV overspeed at River Rage.** In steady partial-speed teleop driving (0.5–3 m/s commanded), measured speed was a median **0.87×** the commanded speed (p25 0.53, p75 1.08). Only 2% of teleop drive charge was drawn while the robot was more than 10% faster than commanded. The ~1.27× overspeed seen at practice (`newfloor-practice-precomp-review.md`) did not show up here, so a kV correction isn't a measurable power lever in these logs.

Q18 still browns out in the drop model at every cap above 25 A. That fits the earlier finding that battery capacity, not load, separates the bad matches from the good ones.

## Variant: cap the drive only while shooting
Shooting brownouts are over-represented, but most of the drive's charge is used outside shooting:

| | Not shooting | Shooting |
|---|---|---|
| Time per match | 103 s | 57 s (36%) |
| Drive Ah per match | 2.93 | **0.58** |
| Per-motor drive supply, median / p90 | 29.5 / 43.8 A | **0.4** / 37.2 A |
| Time a drive motor is above 40 A | 27% | 7.6% |
| Brownout episodes starting here | 9 | **16 of 25** |
| Drive / total draw just before those episodes (median) | 121 / 168 A | 78 / 283 A |

**Corrected (Nov 1):** the 78 A median for shooting brownouts mixes two very different cases.
- **Shooting while moving** (8 episodes): drive 169 A, stack 141 A, total 336 A.
- **Shooting while still** (8 episodes): drive 0 A, stack 75 A, total 211 A.

So when the robot shoots on the move, the drive is about half the load, not a minor part.

Drop model (the carry bound isn't meaningful here, because motion skipped while shooting isn't owed afterwards):

| Cap | Where | Time < 6.5 V | Dips < 6.5 V | Ah/match |
|---|---|---|---|---|
| none (as raced) | — | 26.7 s | 20 | 6.11 |
| 30 A | shooting only | 22.0 s | 18 | 6.01 |
| 20 A | shooting only | 17.6 s | 14 | 5.90 |
| 10 A | shooting only | 11.5 s | 15 | 5.75 |
| 35 A | whole match | 11.6 s | 14 | 5.74 |
| 30 A | whole match | 2.4 s | 8 | 5.44 |

**Result:** for battery charge, a shooting-only cap is less effective than an across-the-board one. Matching a 35 A whole-match cap takes about 10 A while shooting, which effectively means shooting from a standstill. The brownouts are mainly a battery-depletion effect, and only about 17% of the drive's charge is used while shooting.

**Implementation note (corrected Nov 1):** the River Rage build (`b2e88a99`) scaled the sticks while shooting at the hub: x/y ×0.25, and rotation ×0.625 at all times.
- The Oct 30 practice build (`e05fd5ee`) raised that to x/y ×0.5 with rotation ×1.0.
- Current `BaseComp` (`4c190e5`) uses x/y ×0.5 and rotation ×0.75 while shooting.
- Either way, the scaling limits commanded *speed*, not current. The practice logs confirm it: drive-sum peaks while shooting were the same at ×0.25 and ×0.5, pinned near the 4 × 45 A supply ceiling.
- A true shooting-only current cap would need runtime config writes to four Talons on each shooting transition. That's new code that needs testing, on a loop that already overruns.

## Steer supply limit
**Steer draw at River Rage (Voltage steer, Phoenix-default limits):**
- 0.45 Ah per match, which is 7% of the robot's total.
- Per motor, supply current is near zero most of the time: p50 0.3 A, p95 16 A, p99 35 A, max 120 A.
- The 4-module sum reaches p99.9 166 A and a max of 223 A, when several modules flip at once.
- The high current is all slewing: samples above 20 A essentially never occur with the azimuth nearly still, so the steer isn't pushing against anything.
- Steer runs a bang-bang move at full voltage on any setpoint step of about 45° or more (kP 100 V/rot). The 10 matches had 2,680 such flips, with a median settle-to-5° time of about 180 ms.

| Steer cap | Motor time above cap | Charge above cap (Ah/match) | Extra time per ≥45° flip, pessimistic: median / p90 |
|---|---|---|---|
| 30 A | 1.8% | 0.028 | ~2 / 27 ms |
| 25 A | 2.7% | 0.048 | ~10 / 47 ms |
| 20 A | 3.8% | 0.077 | ~25 / 79 ms |
| 15 A | 5.3% | 0.117 | — |

*Extra time assumes all the clipped charge is still drawn, just later, so it's an upper bound. Logs are at 50 Hz, so settle times are quantized to 20 ms.*

**At brownouts:**
- In the 200 ms before the 25 brownout episodes, the steer-sum peak had a median of 31 A, p75 72 A, max 139 A.
- A 20 A cap removes a median of 0 A at those moments (p75 12 A, max 59 A). It removes ≥30 A in only 4 of the 25 episodes.

**Result:**
- A steer cap saves almost no charge. Even 20 A saves 0.08 Ah out of 6.1 Ah per match, about 1%. So it does nothing for late-match battery depletion.
- What it does do is shave the synchronized flip spikes. **Updated Nov 1:** with the Oct 30 driver and build, steer spikes while shooting roughly doubled. A 25 A steer cap there takes the shooting-time p99 total from 399 to 359 A on top of a 35 A drive cap. That makes it a worthwhile peak fix, not just an optional one.
- **25 A is the "won't notice" setting**: about 10 ms added to a typical big flip. 20 A shaves more but adds about 25 ms per flip, around 15% slower, which drivers might feel as heading lag.
- The limit has to go in `turnConfig` in `ModuleIOTalonFX` (not `TunerConstants`), and it's three added lines, not a changed value.

## Autonomous: effect of a 35 A drive cap
**What ran:** every match ran *Double Bump OP Left* or its mirror, *Right*. The auto is 20 s long. Its sequence:
1. Sprint to the center to intake (`LeftDeepBumpChompei`: 4.58 m/s, 9.3 m/s², with a 1.0 m/s zone at the bump).
2. Slow unload path while shooting (`LeftBumpUnloadToLeftTrench`: 0.5 m/s), then a 1.125 s wait.
3. A second intake sprint (`LeftBumpChompei`: 4.58 m/s, with a 3.0 m/s zone).
4. The slow unload path again, in parallel with Shoot until the auto ends.

PathPlanner trajectories are **time-parameterized**. A slower robot doesn't stretch the auto. It falls further behind the setpoint, and each path ends wherever the robot has reached when the trajectory time runs out. So the effect shows up as extra tracking error, not lost time.

**Data:** the 10 auto logs that were usable; both Q7 logs were excluded because their odometry/setpoint error was 4–5 m.
- About 29 m driven and 0.34 Ah of drive charge per auto.
- No brownouts in auto. Minimum bus voltage was 7.3–9.1 V.
- A drive motor sits above 35 A supply about **24%** of auto time.
- As raced, tracking error was a median of about 0.1 m while moving. It peaked at **1.2–1.9 m** during the sprints (2.5–2.9 m in Q18), because the paths ask for more acceleration than the robot delivers.

**Where a 35 A cap bites:**

| Wheel speed | Share of cap-binding samples | Torque kept at 35 A (median) |
|---|---|---|
| 0–1 m/s | 4% | 100% (stator-limited at 90 A anyway) |
| 1–2 m/s | 21% | 90% (67 → 61 A) |
| 2–3 m/s | 51% | 84% (52 → 43 A) |
| 3–4 m/s | 24% | 85% (43 → 36 A) |

Here is the stator current allowed at 11 V on the bus, by wheel speed:

| Supply limit | 0.5 m/s | 1 m/s | 2 m/s | 3 m/s | 4 m/s |
|---|---|---|---|---|---|
| 45 A | 137 A | 109 A | 73 A | 53 A | 42 A |
| 35 A | 117 A | 90 A | 59 A | 42 A | 33 A |

Both limits leave the full 90 A available below about 1 m/s. So launches and bump climbing at the slow zone are unaffected. The cap trims mid-range acceleration, at 1.5–3.5 m/s.

**Simulated added tracking lag:**
- Method: a perturbation on the logged run. The motor model is fitted from the auto data (R 16 mΩ, kE 0.0203 V·s/rad). Its supply prediction matches the logged supply current at a median ratio of 0.99.
- The controller is modelled as the logged current plus drive kP and PathPlanner translation kP 6.
- Acceleration per amp is bracketed between 0.083 (log fit) and 0.14 m/s² per A (physics).
- Validation: re-running at 45 A adds ≤0.004 m.

| Path | Added peak lag at 35 A | Added lag at path end, 35 A | Added peak lag at 30 A | Added lag at path end, 30 A |
|---|---|---|---|---|
| First intake sprint | 0.10–0.35 m (typ. ~0.15) | ~0 m (≤0.05) | 0.24–0.99 m | 0–0.33 m |
| Second intake sprint | 0.04–0.10 m | ~0 m | 0.12–0.32 m | ~0 m |
| Slow unload paths | ~0 | ~0 | ≤0.2 m | ~0 |

**Result:**
- At 35 A the auto is essentially unaffected where it matters. The robot sits up to about 0.15 m (worst 0.35 m) further behind the setpoint mid-sprint, which is about 10–20% on top of the 1.2–1.9 m lag it already has. It catches up before each path ends, because the paths finish with slow zones or decelerations. Intake and shooting positions at the end of each path are unchanged.
- At 30 A it starts to show. The first sprint can end up to about 0.3 m short.
- The charge saved in auto is small: about 0.035 Ah in the drop bound, roughly 10% of the auto's drive charge.
- Caveat: wheel slip, bump impacts and robot rotation make the acceleration-per-amp fit noisy (R² ≈ 0.1). That's why the effect is given as a range, not a single number.

## Would the 35 A cap alone have been enough?
I used the same battery model, with the drive cap in its optimistic (drop) bound. Two more changes are added on top:
- **Intake rollers off while shooting.** `justIntakeOut` forces the rollers to at least 90 rps whenever `isShooting` is set, and that costs 0.24 Ah per match. This one is a true removal, so it isn't optimistic. *The team has decided not to pursue this one: the rollers help feeding, and there's no time to measure how much before competing.*
- **25 A steer cap.**

The "best battery" rows run each match's actual load against the Voc-vs-Ah curve of the strongest battery seen at the event (Q12's: it used 6.47 Ah with no dips).

| Scenario | Dips < 6.5 V | Time < 6.5 V | Matches still dipping |
|---|---|---|---|
| As raced (model baseline) | 20 | 26.7 s | 7 of 10 |
| 35 A drive only | 14 | 11.6 s | 5 (Q4, Q18, E8, E12, E14) |
| Intake off while shooting only | 15 | 15.4 s | 6 |
| 35 A drive + intake off while shooting | 7 | 3.5 s | 2 (Q18, E14) |
| 35 A drive + intake off + 25 A steer | 8 | 2.7 s | 1 (Q18) |
| 30 A drive + intake off + 25 A steer | 2 | 0.1 s | 1 (Q18, barely) |
| No code change, best battery every match | 0 | 0 s | 0 |

**Result:**
- **The 35 A cap alone would not have been enough.** Even in its optimistic bound, half the matches still dip below the brownout threshold. In its pessimistic bound it changes nothing.
- Stacking the intake-off-while-shooting change gets close to clean (3.5 s, 2 matches). That part of the gain doesn't depend on the drive cap's uncertain bound.
- Q18 is the hard case. It still dips with every code change short of 30 A plus the extras.
- **The model says a good battery alone would have removed every dip at River Rage, with no code changes.**

**Model caveats:**
- The baseline is 26.7 s below 6.5 V, against 59.3 s of logged brownout. The real robot also has brownout cascades and sub-20 ms dips that the model doesn't capture.
- The best-battery scenario assumes the team can field batteries as good as the Q12 pack every match, and that pack hasn't been identified, because battery IDs aren't logged.
- Voc curves past each match's own used Ah are extrapolated.

## Recommendation
- Battery quality is the largest factor in this data. The team-facing write-up leaves it out by choice, because the team has already put a lot of work into batteries.
- If the team lowers the drive limit, **35 A is the reasonable compromise.** In the drop model it halves the time spent below 6.5 V and touches 30% of drive time. In auto it adds only about 0.15 m of mid-sprint lag and nothing at path ends. 30 A does more, but it caps 37% of drive time, drivers will notice the softer acceleration, and the first auto sprint can end short.
- A whole-match cap is a better single change than a shooting-only cap.
- **A 25 A steer supply limit (upgraded Nov 1).** It's nearly free in performance. With the Oct 30 driver and build, it's the bigger instantaneous lever while shooting on the move.
- Change, in `ModuleIOTalonFX.java`: `driveConfig.CurrentLimits.SupplyCurrentLimit = 35.0;` (from 45.0). For steer, add `turnConfig.CurrentLimits.SupplyCurrentLimitEnable = true; turnConfig.CurrentLimits.SupplyCurrentLimit = 25.0; turnConfig.CurrentLimits.SupplyCurrentLowerTime = 0.0;`.
