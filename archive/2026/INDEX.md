---
title: 2026 archive index
status: current
date: 2026-11-27
source: "FRC 2026 Robot" claude.ai Project docs, copied 2026-11-27; status from the docs, the Project's notes and its chat history
superseded_by:
---

# 2026 archive

All 56 docs from the 2026 "FRC 2026 Robot" Project, copied verbatim. Two exceptions: a student's first name was replaced with `[student]` in `drivetests2-tuning-runs-0828.md`, and `shot-counter-code/shot-counter.patch` was rebuilt from its headers and the source files, then checked with `git apply` and `cmp`.

These files are frozen. Don't edit them, and don't treat them as current. What carries forward lives in `lessons/` and `knowledge/decisions.md`.

## How to read the status

| Status | Meaning |
|---|---|
| applied | Shipped to robot code or a tool |
| decided | Agreed, but no evidence it shipped |
| proposed | Recommended; no decision found |
| tabled | Deliberately set aside |
| superseded | Replaced; the note says by what |
| reference | Guide, spec, tool doc or explainer with no decision attached |

**The 2026 robot changed a lot during the season,** so numbers aren't comparable across these milestones:
- **Spring events:** North Shore, MA Boston, NECMP (Newsom), CMP (Newton).
- **Aug 2026:** kV fix, then a CAN fix, then the drive moved to TorqueCurrentFOC (Aug 28).
- **Fall offseason:**
  - The HotTub spinner was replaced by a roller floor and the health monitor went in.
  - Events: NERD (mid-Oct), River Rage (Oct 24), Battle of the Bay (BOB, Nov 7).
  - The 35 A drive and 25 A steer supply limits arrived before BOB.

## Drive, tuning and current limits

| Doc | Date | Status | Finding, and what happened |
|---|---|---|---|
| `brownout-analysis.md` | 07-12 | superseded | Moderate draw everywhere at once: 110–160 A teleop average, 300–350 A peaks shooting on the move, drive ~half, kP 1.5 fighting the driver. Replaced by the per-subsystem docs and the fall reviews; its "dead PDH" premise was wrong (the robot has a PDP 2.0). |
| `drive-tuning-guide.md` | 08-02 | reference | Five-pass drive tuning process (feedforward, feedback, output ramp, input slew, validation) plus a build-season checklist. Reusable for 2027. |
| `drive-kv-explainer.md` | 08-02 | applied | kV 0.124 was a motor-shaft constant in a wheel-unit loop (7.03×), so the robot reached 68% of commanded speed. Fix kV/kS first, then kP. kV 0.871 was in the code by Aug 27. |
| `drive-kv-student-test-guide.md` | 08-02 | applied | Four-run field protocol; the tracking ratio should go 0.68 → ~1.0, flat across speed. Run Aug 22 as an A/B/B/A test. |
| `kv-drivetest-analysis.md` | 08-22 | applied | A/B/B/A result: kV 0.871 tracks ~0.97 vs 0.68; top speed 4.4 vs 3.0 m/s; physical kV 0.87–0.90. |
| `drivetests2-tuning-runs-0828.md` | 08-28 | reference | Six builds mapped: P=15 and P=5 were disasters; baseline and the final FOC build track ~5%. Gains weren't logged, which led to `log-the-tune-spec.md` and the FOC switch. |
| `foc-vs-voltage-drive-control.md` | 08-27 | reference | Team 88 vs 1768 comes down to one enum (Voltage vs TorqueCurrentFOC). FOC gives ~15% more peak power and exact traction, but needs a license and locks to TalonFX. Drive went FOC on Aug 28. |
| `supply-current-analysis.md` | 08-22 | superseded | Drive draw is acceleration-peaky (~13.6 A/motor at top speed), and the 45 A limit rarely binds. Recommended 50→35 A tiered plus steer limits. Replaced by `riverrage-drive-limit-whatif.md`. |
| `supply-limit-change-spec.md` | 08-24 | superseded | Drive 50→35 A after 0.5 s and steer 20 A. Found that the 60 A steer stator limit in TunerConstants was never applied. Branch never merged; replaced by commit 0d4e0b9. |
| `steer-current-analysis.md` | 08-23 | applied | Steer averages ~0.1 A/motor, but synchronized flips stack to 90–170 A and there was no steer supply limit. Recommended 20 A; shipped as 25 A in 0d4e0b9 before BOB. |
| `steer-match-analysis.md` | 08-23 | applied | Newton teleop steer spikes of 186–208 A land on sub-7 V dips; a 20 A cap clips 3.8% of samples. Same outcome as above. Corrects the July "~10 A/motor" figure (that was the four-motor total). |
| `wheel-slip-analysis.md` | 10-18 | proposed | A wheel slips ~23–34% of moving time in spring and 55% at NERD, rising with current. A rigid-body residual check (0.4 m/s, 80 ms) works at 50 Hz. Detector sketched, not built. |
| `riverrage-drive-limit-whatif.md` | 10-31 | applied | A 35 A drive cap halves time below 6.5 V for ~0.15 m of mid-sprint auto lag; a 25 A steer cap is nearly free; a good battery alone removes every River Rage dip. 35 A / 25 A shipped in 0d4e0b9. Turning the intake off while shooting was rejected. |
| `practice-1029-1030-shoot-on-move.md` | 11-02 | applied | Oct 30: 59% of shooting happens on the move; steer p99 is 188 A while shooting; a 25 A steer cap trims p99 total current 399 → 359 A; stick scaling isn't a current lever. Feeds 0d4e0b9. |

## Power by subsystem and event reviews

| Doc | Date | Status | Finding, and what happened |
|---|---|---|---|
| `hottub-power-analysis.md` | 08-28 | superseded | ~5 Wh/match, spikes to 85–98 A supply, chopped on/off ~48×/match by onTarget flicker; its ramp config doesn't apply to its control mode. Spinner replaced by the roller floor in the fall. |
| `turret-power-analysis.md` | 09-10 | proposed | ~1 Wh/match. Hunts constantly (~1,100 reversals/match) because the solver setpoint is noisy. Zero is 8–12° off with CANcoder sync commented out; still +363–372° off at NERD. |
| `retractomatic-analysis.md` | 09-10 | proposed | ~0.75 Wh/match; 0↔−15 A chatter ~1,250×/match mirroring the turret. `RetractomaticPosition` actually logs the turret position. |
| `feeder-power-analysis.md` | 09-10 | proposed | Mechanically clean, ~2.4 Wh/match. The 105 rps setpoint needs 11.3 V, so it runs duty-saturated at ~90 rps. Setpoint still 105 at NERD. The upstream debounce it called for shipped Oct 5 (PR #52). |
| `feeder-power-baseline.md` | 10-04 | reference | Old feeder, NECMP + CMP: 2.6 Wh/match, 140 W while running, 320 W 100 ms peak, ~37 A estimated peak supply. The estimator reads ~7% low. |
| `shooter-power-analysis.md` | 09-11 | decided | Coasts to ~2 rps, so 79–100% of shoot windows start cold at ~112–120 A supply; holding speed costs ~14 A/motor; the follower had no current limit. Full idle was chosen but not implemented through NERD, and the follower stayed unlimited. |
| `hood-power-analysis.md` | 09-12 | proposed | Cleanest subsystem: ~0.1 Wh, homes off its absolute encoder. Rare 145–179 A bind spikes only when an 88 A practice stator limit was loaded. |
| `nashoba-power-review.md` | 08-27 | reference | Static read of Nashoba's 2026 code: mechanisms off by default, supply below stator limits everywhere, trickle-voltage holds, 6.0 V brownout setting. Source of the drive/steer cap idea. |
| `roller-floor-code-review.md` | 10-08 | applied | Prescreen of the roller-floor code: per-motor logging missing from BaseComp (fixed by the branch merge), open-loop 11 V floor motors, dead ramp config (not fixed). |
| `newfloor-practice-precomp-review.md` | 10-09 | proposed | Turret CANcoder ~365° off; drive FOC kV 20 overspeeds 1.29×; FOC steer tracks worse; feeder at 120 A bought nothing. Steer went back to Voltage; most other items unconfirmed. |
| `riverrage-shoot-spike-review.md` | 10-31 | proposed | The shoot-start spike isn't the fall brownout driver: 450 of 471 onsets were in the last quarter. Battery capacity separates matches. The HotTub-style ramp config is dead code. |
| `bob-power-review.md` | 11-07 | proposed | BOB 52.0 Wh / 5.51 Ah per match vs River Rage 58.0 and NERD 59.4. The 35 A / 25 A limits cut drive charge ~0.8 Ah. Ramp fixes and feeder caps don't move the first brownout. |

## CAN, loop timing, logging and tools

| Doc | Date | Status | Finding, and what happened |
|---|---|---|---|
| `can-bus-analysis.md` | 08-15 | applied | The roboRIO CAN bus grew from 30–50% to 70–77% (92% p95), going error-passive at Newton Q23: no `optimizeBusUtilization`, hood at 1000 Hz. Fixed in August. |
| `can-utilization-fix-report.md` | 08-27 | applied | Optimize plus rate trims took the bus to ~41% with zero errors (Aug 22 logs). |
| `loop-overrun-analysis.md` | 10-28 | tabled | 98% of October enabled loops ran over 20 ms (median 26.6 ms). `@AutoLogOutput` takes ~7.5 ms, GC is negligible, and batching Phoenix reads is the biggest fix. Shelved for 2026; carried to the next robot as good practice. |
| `log-the-tune-spec.md` | 08-29 | proposed | Log drive/steer gains as boot metadata, plus a dashboard test label and `event/` branch deploys, so each log identifies its tune. No evidence it shipped. |
| `wpilog-reader-guide.md` | 08-24 | reference | API, recipes and validation for `wpilog_reader.py`. |
| `wpilog_reader.py` | 08-24 | reference | Pure-stdlib WPILOG/AdvantageKit reader with struct decoding, adapted from tervay/log_reader. Also copied to `scripts/`. Pitwall has its own `pitwall/wpilog.py`; which copy is newest isn't recorded. |
| `advantagekit-io-rewrite.md` | 11-07 | tabled | BaseComp mechanisms rewritten into 6328-style IO layers for replay. Type-checks but never run or committed. Educational; the team will likely keep its current format. |

## Vision

| Doc | Date | Status | Finding, and what happened |
|---|---|---|---|
| `camera-pose-from-logs.md` | 10-03 | reference | Limelight mounting poses fitted from 5,106 tag samples. Left cam consistent within 1.4"/1.2°; right and back shifted ~5"/3° at Newton. |
| `vision-analysis.md` | 10-03 | proposed | Pose shake (10.4 cm while still, 83 jumps/min) comes from over-trusted frames, ±2–3° side-camera yaw error and weak odometry. The MT2 typo fix alone makes it worse. Four commits on a local `vision-tuning` branch, never pushed. |

## Health monitor and wear tracking

| Doc | Date | Status | Finding, and what happened |
|---|---|---|---|
| `health-warning-system-design.md` | 09-24 | applied | Detect → aggregate → annunciate; a 4-rung fault ladder; cheap detectors first. Wave 1 merged to BaseComp (fc868cc, Oct 19). LEDs and Wave 2 were never built. |
| `health-monitor-handoff.md` | 10-02 | reference | Status snapshot as of Oct 19: 36 faults, lifecycle rules, NERD tuning, PR #50 merged. Later reviews replace its open items. |
| `health-monitor-code/CanBusFaults.java` | 10-02 | superseded | Early snapshot (utilization threshold 70%). The BaseComp code is the source of truth (85% after 566dfa8). |
| `health-monitor-code/HealthMonitor.java` | 10-02 | superseded | Early snapshot of the aggregator. BaseComp fc868cc is the source of truth. |
| `nerd-initial-review.md` | 10-16 | reference | NERD faults: a damaged roboRIO in Q24, a break in the rio CAN chain past the intake pivot, Pigeon drops. CAN 66% (from 76%); brownouts unchanged. Wiring repaired later. |
| `health-monitor-nerd-replay.md` | 10-17 | applied | Replaying the 12 NERD logs gave ERROR after 10 of 11 matches. 0.1 s debounce, Brownout as a warning, CAN utilization at 85%; afterwards every ERROR was a real dropout. Merged (566dfa8). |
| `health-monitor-practice-1019-review.md` | 10-20 | decided | First run on the robot: presence faults correct, records replay after power-off. Found the pivot-triggered CAN break. CAN/BusErrors fired 35–140×/enable; loop cost +3–4 ms. Rate-based BusErrors agreed. |
| `health-monitor-oct20-21-review.md` | 10-21 | decided | CAN chain fault gone (0 dropouts in 25 logs); BusErrors 0.45/min. Proposed ≥10 episodes per 60 s; rate-based agreed, number not confirmed. |
| `component-usage-tracker-design.md` | 09-30 | applied | Tread odometer: wheel distance only, stored on the roboRIO, Inspected/Replaced actions with a graded snooze. Merged (5cbfb6d) and ran at River Rage. |
| `tread-usage-riverrage-review.md` | 10-29 | proposed | ~3.0 km/module at River Rage (265 m per full match); counts match the log; ~25% of usage had no log. No inspections were recorded, so the warning was ignored for 8.4 km. Thresholds not yet calibrated. |

## Shot counting and jams

| Doc | Date | Status | Finding, and what happened |
|---|---|---|---|
| `shot-counter-design.md` | 10-13 | superseded | Counts balls from flywheel speed dips: hub BPS 4.8 while flowing, 3.6 per trigger second, ±25% absolute. Robot PR #57 never merged; the concept became Pitwall's scoring module. |
| `shot-counter-code/shot_counter.py` | 10-13 | superseded | Offline version of the detector. Replaced by Pitwall's scoring module and `shot_detect_level.py`. |
| `shot-counter-code/shot-counter.patch` | 10-13 | proposed | BaseComp patch (ShotCounter, ShotDetector, 7 tests). PR #57, never merged. Rebuilt for this archive and verified with `git apply`. |
| `shot-counter-code/ShotCounter.java` | 10-13 | proposed | Watch-only subsystem logging shots and BPS per category. PR #57, unmerged. |
| `shot-counter-code/ShotDetector.java` | 10-13 | superseded | Dip detector with October defaults, which reject most balls after the April flywheel change. Retuned in `jam-review-1105.md`. |
| `shot-counter-code/shot_detect_level.py` | 11-11 | decided | Level-relative rules; BOB Q7 count goes from 72 to 271. Basis of Pitwall's scoring module. |
| `jam-detection.md` | 10-13 | superseded | Watch-only jam detector; the October feeder jammed 23% of feeding time. Replaced by `jam-review-1105.md`. |
| `jam-review-1105.md` | 11-07 | decided | Hybrid jam rule: stator current plus velocity, a signed funnel rule, held 0.3 s. 35 jams = 6.7% of gate time; the team's supply-current trigger misses full stalls. Teleop-only PR (0be4b45 / 5aed412) taken to the team; merge unconfirmed. |

## Pitwall

| Doc | Date | Status | Finding, and what happened |
|---|---|---|---|
| `log-processor-framework.md` | 11-08 | applied | Pitwall's design, decision log and status: app, power/scoring/health modules and log fetch built through v0.9.0 (PR #23). Its 2027 status moves to `docs/` in the frc-pitwall repo. |
| `flashpoint-trial.md` | 11-08 | decided | Flashpoint 0.1.0 can't read AdvantageKit logs. With a shim, Newton Q23 = 54.8 Wh, matching owlet's 55.2 Wh. No power-budget view, so Doug built Pitwall. |
| `pitwall-other-teams-testset.md` | 11-11 | tabled | What ties Pitwall to Team 88, and four public log sets to test against (best fit: 3467 logs-2026). Multi-team support parked. |
