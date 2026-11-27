---
title: 2026 robot baselines
status: current
date: 2026-11-27
source: archive/2026/ (doc named on each line)
superseded_by:
---

# 2026 baselines

Measured numbers to compare the 2027 robot against. Most "supply" figures are **estimated** from motor voltage × current / battery voltage, because the 2026 PDP 2.0 reported no current. Estimates were validated at r = 0.9985 for drive, but read ~7% low for the feeder.

**Robot configuration changed during the season:**
- **Spring:** kP-heavy drive with the wrong kV, HotTub spinner.
- **Aug:** kV fix, CAN fix, drive moved to TorqueCurrentFOC.
- **Fall:** roller floor, health monitor, 35 A drive / 25 A steer limits before BOB.

The events, in order: North Shore, MA Boston (MABOS), NECMP (Newsom division), CMP (Newton division), NERD (mid-Oct), River Rage (RR, Oct 24), Battle of the Bay (BOB, Nov 7).

## Whole robot, per match

| Measure | Spring | NERD | RR | BOB | Source |
|---|---|---|---|---|---|
| Energy (Wh) | 54.8 (Newton Q23) | 59.4 | 58.0 | 52.0 | flashpoint-trial, bob-power-review |
| Charge (Ah) | 4.5–5 | 6.3 | 6.1 | 5.5 | brownout-analysis, bob-power-review |
| Mean current (A) | 120–158 teleop | 142 | 137 | 124 | brownout-analysis, bob-power-review |
| p95 total current (A) | — | 260 | 252 | 237 | bob-power-review |
| Drive share of energy | ~47% (Q23) | 51% | 57% | 47% | flashpoint-trial, bob-power-review |
| Matches with a brownout | — | 8/9 | 8/10 | 3/3 | bob-power-review |
| Median time left at first brownout (s) | — | 49.3 | 29.2 | 31.6 | bob-power-review |

- **Pitwall's signed-current recount:** NERD 8/10 matches with a brownout, 49.3 s left at the first; RR 7/9, 38.1 s; BOB 5/7, 17.8 s. *(log-processor-framework)*
- **Charge delivered before the first brownout:** pooled median 4.7 Ah (range 1.8–5.8) on a ~18 Ah pack. *(log-processor-framework)*
- **Brownouts per match, mean/median:** Newton 25.7/19, Newsom 19.3/0, NERD 29.7/17.5. 94–99% fell in the last 45 s. *(nerd-initial-review)*
- **Fall brownouts are late-match:** 450 of 471 River Rage onsets came in the last quarter. *(riverrage-shoot-spike-review)*
- **Energy split, Newton Q23 (Wh):** drive 25.7, intake 9.5, shooter 6.3, HotTub 5.8, steer 3.0, feeder 2.7, turret + retractomatic 1.6, hood 0.1. *(flashpoint-trial)*
- **Charge split, River Rage (Ah):** drive 3.51, intake 0.74, shooter 0.47, steer 0.45, feeder 0.39, floor 0.29, turret + retractomatic 0.22. *(riverrage-shoot-spike-review)*

## Battery

- **Source resistance:**
  - ~11–13 mΩ early in a match, 14–23 mΩ late. *(bob-power-review, log-processor-framework)*
  - ~16 mΩ was used for spring sag estimates; a weak battery read ~23 mΩ. *(steer-match-analysis, newfloor-practice-precomp-review)*
- **Lowest pre-match resting voltage, 2026:** 12.3 V, which became the low-battery threshold. *(health-monitor-handoff)*

## Drive and steer

- **Physical drive kV:** 0.870–0.880 V per wheel-rot/s (R² 0.997). Gear ratio 7.03125, wheel radius 2.0 in. *(drive-kv-explainer, kv-drivetest-analysis)*
- **kV fixed vs broken (voltage mode, Aug 22):** tracking 0.97 vs 0.63–0.68; top speed 4.31–4.37 vs 3.0–3.3 m/s. *(kv-drivetest-analysis)*
- **Holding top speed:** ~13.6–15 A per motor. 4-motor supply peak 187–190 A. *(supply-current-analysis, riverrage-drive-limit-whatif)*
- **At a 35 A supply limit (BOB):** drive p95 34.4 A per motor; steer p99.9 24 A. At 45 A, a drive motor sat at the limit ~20% of enabled time. *(bob-power-review, riverrage-drive-limit-whatif)*
- **Steer spikes:** synchronized 4-module flips of 93–208 A before limits. River Rage: 0.45 Ah per match, 2,680 flips of 45° or more, median settle 180 ms. *(steer-match-analysis, riverrage-drive-limit-whatif)*
- **Steer heading error while moving:** 4.6–4.8° on Voltage vs 11–16° on FOC. *(newfloor-practice-precomp-review)*
- **Shooting on the move, total current p50/p99/max:** RR 108/355/549 A; Oct 30 practice 160/405/656 A. 59% of shooting happened on the move. *(practice-1029-1030-shoot-on-move)*
- **Wheel slip, share of moving time:** 23–34% spring, 55% at NERD. Slip rate by current: 3% below 20 A, ~51% at 90–100 A, ~74% above 120 A. Estimated real traction current ~60–80 A vs 90–120 A configured. *(wheel-slip-analysis)*

## Mechanisms (spring, Newton Q23/Q34/Q64 and Newsom Q14 unless noted)

| Mechanism | Energy / match | Key numbers | Source |
|---|---|---|---|
| Shooter | 4.8–8.0 Wh | Hold ~14–15 A/motor at ~41 rps; cold spin-up ~112–120 A supply, 0.18 s to setpoint; 79–100% of shoot windows started cold; FF ceiling ~83 rps at 12 V | shooter-power-analysis |
| HotTub (removed) | ~5.2 Wh | Spikes 74–98 A supply; ~48 restarts per match | hottub-power-analysis |
| Feeder (old) | 2.6 Wh | 140 W while running; 320 W 100 ms peak; ~37 A est. peak supply; ran ~90 rps against a 105 target | feeder-power-baseline, feeder-power-analysis |
| Feeder (fall, BOB) | — | Supply p50/p95/max 36/58/77 A at 72 rps | bob-power-review |
| Roller floor (fall) | — | Steady ~19–20 A total; spin-up peaks 55–100 A | newfloor-practice-precomp-review |
| Turret | ~1.1 Wh | ~1,100 reversals per match; on target 82% while shooting | turret-power-analysis |
| Retractomatic | ~0.75 Wh | ~1,250 current chatter cycles per match | retractomatic-analysis |
| Hood | ~0.1 Wh | 0.7° tracking error | hood-power-analysis |

## CAN bus (roboRIO bus, enabled mean / p95)

- **March:** 28–58% / 63–74%.
- **NECMP / Newton:** 76–79% / 91–93%, error-passive (REC 128) in Newton Q23. The disabled baseline was 67–76%, so configuration, not gameplay, drove the load. The hood signal at 1000 Hz alone was ~13% of the bus.
- **After the August fix:** ~41% / 48–51%, zero errors.
- **Fall with the roller floor:** 56–66% median enabled.
- **Healthy-bus CAN/BusErrors:** ~0.45 per enabled minute; ~13/min with a wiring fault.

*(can-bus-analysis, can-utilization-fix-report, nerd-initial-review, health-monitor-oct20-21-review)*

## Loop timing

- **Full-cycle median:** 23.1 ms enabled in April, 26.6 ms in October. 98% of October enabled loops ran over 20 ms.
- **October breakdown:**
  - Logging ~10 ms, of which `@AutoLogOutput` ~7.5 ms
  - `SmartDashboard.updateValues` ~4.9 ms
  - Scheduler shares: Drive 35%, Vision 28%, commands 18%
- **Health monitor cost:** +3–4 ms per loop.

*(loop-overrun-analysis, health-monitor-practice-1019-review)*

## Vision (21 spring matches)

- **While still:** pose wobble 10.4 cm; pose jumps over 10 cm, 83/min.
- **Position error, typical / p90:** 11.5 / 37.5 cm.
- **Heading error, typical / p90:** 2.2 / 4.7°.
- **Measured MT1 noise:** 7.6–11.4 cm (2+ tags, under 5 m).
- **Gyro scale error:** ~0.3–1%.

*(vision-analysis)*

## Scoring and jams

- **Hub shots per match:** spring 39 auto + 179 teleop; NERD 196, RR 158, BOB 200. *(shot-counter-design, log-processor-framework)*
- **BPS:**
  - Spring: 4.8 while flowing, 3.6 per trigger second.
  - Fall, while flowing: NERD 4.33, RR 4.60, BOB 4.63.
  - *(shot-counter-design, log-processor-framework)*
- **Hub trigger time, spring:** flowing 68%, waiting for the first ball 11%, empty or jammed 10%, turret off target 9%. *(shot-counter-design)*
- **Jam time:**
  - Spring: 21 s of 1,741 s feeding.
  - October practice: 23% of feeding.
  - Nov 5–6: 6.7% of gate-open time. Jams cost 19% of BPS in one session.
  - *(jam-detection, jam-review-1105)*
- **Feeder in a jam:** 0–35 rps at 95–124 A stator, vs 72 rps / 43 A when flowing. *(jam-review-1105)*

## Wear

- **Tread distance:** ~243 m per module per match in season, 265 m at River Rage. 16–17 km per module over the logged season; ~17.6 km by the end of BOB. *(tread-usage-riverrage-review, log-processor-framework)*
