# NERD offseason (MABIL1, Oct 10 2026): initial log review

**Scope:** all 23 logs in `NERDLogs`. 12 are FMS match logs: Q1 (two logs), Q9, Q15, Q20, Q24, E3, E8, E11, E13, E14, E15. The rest are pit/practice. Each metric was re-run with the same scripts on Newton (10 quals) and Newsom/NECMP2 (quals + elims) for comparison.

**Code:** every NERD build is `BaseComp @ 51350d2` marked **dirty**. There were three builds: Oct 9 16:04 (Q1), Oct 10 09:15 (Q9–Q24) and Oct 10 13:51 (elims). The 13:51 build is the deploy to the replacement roboRIO (see #1). The logs therefore don't map to committed code. From the data, the 09:15 build onward contains voltage steer (`VoltageSteer` branch) and the 60 A feeder limit (`NERD-Changes` branch). Neither branch is merged. Scripts and raw results are in `FRC Logs/nerd-review/`.

## Key errors at the event

| # | Match | What happened | Status |
|---|---|---|---|
| 1 | **Q24** | Robot went dead 4.8 s into auto. The log stops while enabled, with no brownout and the battery at ~10 V. | **Resolved: damaged roboRIO**, replaced right after the match (per Doug). Logs confirm the serial changed from `0327BA0E` (through the 17:16 UTC boot) to `0322383C` (from 17:51 UTC on). |
| 2 | **Q1 (1st log)** | Comms lost 6.5 s into auto. The DS detached 5 s later. | **Resolved: field fault.** The match was stopped and restarted; the second Q1 log is the restart. |
| 3 | **E11** | **Every roboRIO-bus mechanism except the intake pivot went silent for ~11 s**, 77 s into teleop. ~25 partial dropouts followed until ~358 s. | Open. See the deep dive below. |
| 4 | Q15, Q20, E3, E8, E13, E14 | Smaller rio-bus dropouts (0.02–1.0 s), including a 1.0 s outage 2 s into Q15's auto | Open. Q15/Q20 were on the *old* roboRIO; E3–E14 on the new one. |
| 5 | **Q1 (2nd log)** | **The Pigeon dropped 48 s into teleop and never came back.** That left 91 s on the kinematics fallback (heading drift: field-relative drive and turret aim). | Open. Only the gyro dropped, so this is the Pigeon's own wiring or power. |
| 6 | Q9, E13, E15 | Short Pigeon blips (0.4–1.0 s). In E15, the **whole CANivore bus dropped for 0.47 s**: all 4 drive, 4 steer and 4 encoders at once. | Open. The same failure class as Newton Q12's 112 s CANivore outage. |

## Deep dive: roboRIO-bus outages (#3, #4)

**Method:** AdvantageKit writes a value only when it changes, so a device whose status frames stop arriving produces no new samples. For each multi-subsystem outage I counted samples per device signal. A device was counted as still talking above 5 samples/s.

| Outage | roboRIO | Duration | CAN util | Devices still reporting |
|---|---|---|---|---|
| Q15, 233.6 s (auto) | old | 1.0 s | 16% | **intake pivot 14**, intake rollers 15 + 18 |
| Q15, 235.1 s | old | 0.3 s | 19% | **pivot 14**, rollers 15 + 18, hood 5, turret CANcoder |
| **E11, 316.2 s** | new | **11.1 s** | 11–14% | **pivot 14 only** |
| E11, 329.0 s | new | 0.3 s | 38% | **pivot 14**, rollers 15 + 18, hood 5, funnel 21 |

The short ~0.25 s windows in which most devices show as alive are `isConnected()` timeout tails, not real outages.

**What the pattern says**
- **The roboRIO is not the cause.** The same pattern shows up on both roboRIOs.
- **It is an open circuit in the chain, not bus noise.**
  - During E11's 11 s outage, utilization sat flat at 11–12% with **zero RX/TX errors** until 323.6 s.
  - Something was still ACKing the roboRIO's frames: the pivot. That is a clean break with the pivot on the roboRIO's side.
  - Error bursts came after the break: RX errors up to 23, TX errors up to 5. Utilization swung between 9% and 100% from 323.6 to ~358 s while the connection flickered. It was stable from ~360 s on.
- **The pivot survived every outage.** The intake rollers survived the shorter ones. The break is therefore downstream of the pivot, in or near the intake, if the chain runs roboRIO → pivot (14) → rollers (15/18) → …. The physical chain order is still needed to confirm this.
- **E11's outage began right after a hard bump crossing.**
  - Pose was (5.35, 2.63), heading ≈ π: the blue-side bump corridor, at 3.5 m/s.
  - Measured speed dropped from 3.5 to 1.0 m/s about 0.4 s before the outage. Wheel-derived and gyro yaw rate disagreed, which suggests slip or the wheels leaving the floor.
  - The pivot was stationary (27.2) and not moving at the time.
- The Q15 outages happened at low speed in auto (~1 m/s, mid-field) with the pivot holding at ~34 A. They have no obvious impact trigger.

**Suggested inspection:** the CAN connections immediately downstream of the intake pivot, and any CAN wiring that crosses the intake pivot joint. Check for crimp/ferrule pull-out and connector retention. Wiggle-test with the robot enabled while watching `/SystemStats/CANBus/Utilization` and device `isConnected`.

## Progress on previously tracked items

| Item | Season (Newton / Newsom) | NERD | Verdict |
|---|---|---|---|
| CAN utilization, enabled mean / p95 | 76% / 90% | **66% / 83%** | Improved by ~10 points |
| CAN utilization, disabled | 68–70% | **58%** | Improved |
| CAN RX error max (error-passive is 128) | 131 / 135 (several matches error-passive) | **23** | Improved: no error-passive episodes |
| Feed-gate chatter (`OnTargetRobot` toggles while shooting) | median ~180 per match | **median ~37** | Debounce works (~5× fewer). Raw turret flicker is unchanged (~165 vs ~215). |
| Steer tracking (steady-state heading error, p95) | 1.2–2.4° (voltage) | **1.2–2.7°** from Q9 on. Q1 build (still FOC): **34°** | Voltage steer restored and working. Merge `VoltageSteer`. |
| Steer holding current | 2.3–5 A | 1.4–2.4 A (Q1: 5.9 A) | Fine |
| Feeder stator limit | 40 A era (p99 31–35 A) | p99 64–74 A | Consistent with the 60 A change. Merge `NERD-Changes`. |
| Feeder speed while running (105 target) | 83–106 rps median | **74–83 rps** | Still the choke point, slower than the season feeder |
| Shooter cold starts per shoot window | 86% | **90%** | Unchanged. Idle-at-ready-speed is not implemented. |
| Shooter follower peak stator | 136–169 A | up to 104–112 A | Still no follower current limit |
| Drive kV (FOC kV 20 A/rps) | — | free-drive practice logs at the event: **1.30×** commanded speed (n = 480–2656 windows) | Unchanged from the pre-comp finding |
| Turret CANcoder vs motor zero | −12° to +4° | **+363° to +372° on every boot**, on both roboRIOs | Unchanged from Oct 8 onward. Check the tether / re-zero the CANcoder. |
| Loop time, enabled mean / share of cycles >20 ms | 26–29 ms / 74–88% | **28.7 ms / 90%** (elims ~30–31 ms) | Not improved |
| Brownouts per match (mean / median) | Newton 25.7 / 19; Newsom 19.3 / 0 | **29.7 / 17.5**. Q9 92, Q20 87, E3 45, Q15 25, E8 23, E13 12, E14 10, E15 3, Q1 0, E11 0 | Not improved. 94% fall in the last 45 s (Newton 99%), the same late-match depletion pattern. |
| Vision accepted poses per camera per match | 1230–2010 (23–36% accepted) | ~920–1020 (19–27%) | No vision code change at NERD (`vision-tuning` not merged). The new venue confounds the comparison. |

### Power budget (first event with full supply-current logging)
- Logged charge is **~6.0 Ah per match** (4.6–6.7). This undercounts: roboRIO, radio and Limelights are not logged.
- Mean logged draw is ~135 A. By share: drive 51%, intake 13%, shooter 10%, feeder 9%, steer 7%, floor 6%, turret/hood 5%.
- The intake's 17 A mean is the surprise: the rollers stall against a full hopper.
- Apparent battery + wiring resistance is 11–13 mΩ in every match, which is healthy. The brownouts are current transients and battery depletion, not a bad cable.

### Shot counter: the season-tuned detector undercounts on this build
- `shot_counter.py` reports 23–58 balls per match. That is roughly 0.3–0.8 balls per feeding second, against 4.2 in season.
- A plain flywheel-dip count (≥1.5 rps drop over 2 samples while the feeder runs) gives **4.0–4.2 balls/s**, the same as season (3.5–4.5).
- The likely cause: the flywheel runs **~1.9 rps above** the logged `Trajectory/ShooterSpeed` setpoint at NERD (≈0 in season), so error-based dips no longer cross the threshold.
- Fix before relying on the `ShotCounter` branch.

## Open questions
1. The physical roboRIO CAN chain order, to pin the break location (#3/#4).
2. The Pigeon's wiring path and power source (#5/#6).
3. Why is the shooter ~1.9 rps above the logged setpoint?
4. Brownouts: a per-match breakdown of the last 45 s.
