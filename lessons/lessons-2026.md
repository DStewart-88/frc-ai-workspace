---
title: Lessons from the 2026 season
status: current
date: 2026-11-27
source: archive/2026/ (doc named after each lesson) and the 2026 Project's notes
superseded_by:
---

# Lessons from 2026

Season-agnostic principles. Each one cost something to learn. The doc in `archive/2026/` named after each lesson has the evidence.

## Tuning and control

1. **A kV constant's shaft is set by the velocity in its denominator.** The motor shaft is the physical reference (back-EMF); the gear ratio falls out when you rewrite it in wheel units. In 2026 a motor-shaft kV (0.124) sat in a wheel-unit loop. The wheel value was ~0.872, and 0.872 / 7.03125 = 0.124, so the robot reached 68% of commanded speed. *(drive-kv-explainer)*
2. **A near-match can be a units failure.** ~0.139 looked like it confirmed 0.124, but it came from a different units context. *(drive-kv-explainer)*
3. **Correct feedforward before touching feedback.** With feedforward supplying ~14% of the needed voltage, kP = 1.5 was compensating through standing error. Lowering kP follows from fixing kV, and lowering it first just makes the robot slower. *(drive-kv-explainer)*
4. **Generated defaults aren't measured values.** Keep a dated "measured constants" list for each robot: kV, kS, kSpeedAt12Volts, slip current, wheel radius, gyro scale. *(drive-kv-explainer, vision-analysis)*
5. **Gains change units with the control mode.** Under TorqueCurrentFOC, kV is an amps term. A voltage-sized kV gives actual ≈ target·(1 + kV/kP), and the 2026 FOC drive ran 1.29× fast. Switching modes means re-tuning from scratch. *(newfloor-practice-precomp-review, foc-vs-voltage-drive-control)*
6. **A flat tracking ratio across speed is the fingerprint of a gain error.** A battery or traction limit droops with speed instead. *(kv-drivetest-analysis)*
7. **Check that a setpoint is reachable under sag.** Needed voltage = kV·v + kS. The feeder's 105 rps needed ~11.3 V, so it ran duty-saturated at ~90 rps, and at 97–98% duty kP and kI do nothing. *(feeder-power-analysis, shooter-power-analysis)*
8. **Clean a noisy setpoint before detuning a loop.** If the setpoint reverses more often than the mechanism should, the input is the problem: the turret made ~1,100 reversals per match. *(turret-power-analysis)*
9. **An absolute encoder only helps if something acts on it.** The hood homes off its encoder at boot; the turret's sync code was commented out, and its zero drifted to ~365° off. *(hood-power-analysis, turret-power-analysis)*
10. **A sluggish loop can be an accidental traction limiter.** Moving the drive to TorqueCurrentFOC with kP 70 raised wheel slip. *(wheel-slip-analysis)*

## Configs that silently do nothing

11. **Config fields for the wrong control mode fail silently.** `DutyCycleClosedLoopRampPeriod` does nothing under `VelocityVoltage`; the 2026 ramp configs never applied. *(hottub-power-analysis, riverrage-shoot-spike-review)*
12. **Config blocks can be built and never applied.** The swerve template never applied `steerInitialConfigs`, so a 60 A steer stator limit did nothing. Verify limits from logs, not from config. *(supply-limit-change-spec)*
13. **Check every follower config.** The shooter follower's config object was empty, so it had no current limit while the main had 60 A, and it took 157–169 A excursions. *(shooter-power-analysis)*
14. **Make sure the event config is the competition config.** The hood carried an 88 A practice stator limit. *(hood-power-analysis)*
15. **Under TorqueCurrentFOC the stator current is the command.** A stator limit above it never engages, and a supply limit can't see a stall because supply ≈ duty × stator. *(retractomatic-analysis)*
16. **roboRIO Preferences override code defaults and aren't logged.** Log commanded setpoints and gains. *(roller-floor-code-review, jam-review-1105)*

## Power and brownouts

17. **2026 had two kinds of brownout, needing different fixes.**
   - In spring, stacked transients drove them: one parallel command group started the shooter, feeder and HotTub from cold together.
   - In fall, late-match battery depletion drove them: 450 of 471 River Rage onsets came in the last quarter, and 94–99% of NERD's came in the last 45 s.
   - Find out which kind you have before choosing a fix. *(shooter-power-analysis, riverrage-shoot-spike-review, nerd-initial-review)*
18. **Spike-shaping doesn't delay the first brownout; saving charge does.** Ramps and caps on short transients trim time below threshold. Only lower total draw moves the first onset. *(bob-power-review, riverrage-drive-limit-whatif)*
19. **The drivetrain dominates the budget.** It was 47–57% of match energy and ~80% of composite draw at shoot-window starts. Fix the drive before optimizing mechanisms. *(bob-power-review, shooter-power-analysis)*
20. **Supply current scales with acceleration, not speed.** Holding top speed took ~15 A per motor. A supply cap costs launch punch, not top speed, and stick scaling isn't a current lever. *(supply-current-analysis, practice-1029-1030-shoot-on-move)*
21. **Supply and stator limits do different jobs.** Supply (battery side) feeds brownouts; stator is heat and torque. Set supply below stator. A supply cap removes torque at speed, not at stall. *(steer-current-analysis, nashoba-power-review, bob-power-review)*
22. **Peak current and energy are different problems.** A cold flywheel spin-up was ~112–120 A supply but only 25–44 mWh; holding the flywheel at speed costs ~14 A. *(shooter-power-analysis)*
23. **Raising a choke point's current limit doesn't fix binding.** Feeder 60 → 120 A gave no BPS gain, only heat. *(newfloor-practice-precomp-review)*
24. **Battery state decides whether a transient browns out.** The same shoot-start transient gave 32 brownouts in Newton Q23 and 0 in Newsom Q14. Late-match open-circuit voltage separates matches better than Ah used. Log a battery ID per match. *(shooter-power-analysis, riverrage-shoot-spike-review)*
25. **Don't publish a "charge left" estimate.** Voltage collapses suddenly near the end of a pack, and a backtested model ran a median 1.5–2.2 Ah late. *(log-processor-framework)*

## Gates, debounce and detection

26. **Debounce a shared gate once, upstream, and know what the hold costs.** A 0.2 s debounce on `onTarget()` cut 33 raw flickers to 2 gate toggles across the feeder and floor. It also let balls feed for 0.2 s while the turret swung back from a stale shoot-on-move lead, so after River Rage it was set to 0 s (commit 7f70d66, Oct 29) and the chatter returned. *(feeder-power-analysis, newfloor-practice-precomp-review, bob-power-review)*
27. **Every detection threshold needs a hold time.** Normal feeder bogs lasted ≤0.12 s against 0.3–5 s for real jams. *(jam-review-1105)*
28. **Gate on direction, not magnitude.** Funnel stall current means a jam only when the funnel runs in reverse; signed current < −25 A took false fires from 14 to 1. *(jam-review-1105)*
29. **Pick the signal that sees the failure.** A full stall drops supply current to ~23 A at low duty, while a busy feeder pins supply at its limit. Use stator current plus velocity for jams. *(jam-review-1105)*
30. **Make guard thresholds relative to the running level.** A flywheel preference change moved the running speed, and a fixed overspeed guard dropped shot-counter recall to ~5%. *(jam-review-1105, shot_detect_level.py)*
31. **Current that's wrong for the speed means the mechanism physically changed.** At BOB Q26 the roller-floor belt came off: RPM looked right, current was much lower. *(2026 health-monitor notes)*
32. **Video is cheap ground truth.** A 30 fps phone clip, clock-synced by cross-correlation, exposed a 25–30% shot undercount. *(jam-review-1105)*

## Health monitoring

33. **Generate fault categories from how components fail,** not from last season's bugs. History only tunes thresholds within a category. *(health-warning-system-design)*
34. **Sustained conditions need a debounce; rare transients need a latch.** *(health-warning-system-design)*
35. **A command-vs-response check is valid only when gated on intent:** actually commanding, and past settling. *(health-warning-system-design)*
36. **If one condition forces ERROR every match, ERROR stops meaning anything.** Brownout was downgraded to a warning so that ERROR means a device left a bus. *(health-monitor-nerd-replay)*
37. **List only what needs action, and calibrate from real inspections.** A tread warning went unacted for 8.4 km because no inspections were ever recorded. *(health-warning-system-design, tread-usage-riverrage-review)*
38. **On-robot counters catch what logs miss.** ~25% of tread usage never reached the log archive. *(tread-usage-riverrage-review)*
39. **"Observe-only" code still costs loop time:** +3–4 ms for the health monitor. Add timing outputs from the start. *(health-monitor-practice-1019-review)*

## CAN, logging and loop timing

40. **CAN headroom is the lesson, not the peak.** The same disturbances were harmless at ~50% utilization and caused dropouts at 77%. Bus load creeps up by accretion. *(can-bus-analysis, can-utilization-fix-report)*
41. **Optimize every device, then re-enable only what the code reads.** A status-frame rate matters only if something consumes the signal. Use the disabled-mode baseline to separate configuration load from gameplay. *(can-utilization-fix-report)*
42. **A silenced or rate-less signal returns a stale value with no error.** Under `optimizeBusUtilization`, an alert on such a signal never fires. *(can-bus-analysis, health-warning-system-design)*
43. **Logged status frames under-read fast events.** AdvantageKit logged CAN status every 20th loop, so fast-decaying error counts were undercounted ~20×. rio-bus supply current was 4 Hz in hoot and 50 Hz in wpilog, so infer spikes from the battery dip. *(health-monitor-practice-1019-review, bob-power-review)*
44. **Logging can cost half the loop.** Method-level `@AutoLogOutput` getters each make a native refresh, so batch reads with `refreshAll`. Rule suspects out with data: GC was ~0.1 ms per loop. *(loop-overrun-analysis)*
45. **Per-loop detectors are limited by loop timing.** A ~40 ms flywheel dip against 33–39 ms median sampling. Detect in a fast status-signal thread instead. *(shot-counter-design, jam-review-1105)*
46. **Commit deployed builds, and log gains at boot.** Dirty builds share a git SHA, so a log can't tell two tunes apart. *(log-the-tune-spec, drivetests2-tuning-runs-0828)*
47. **If it isn't logged, you'll be estimating it.** 2026 had no power-distribution current (PDP 2.0), a bogus BatteryCurrent, and no shooter supply current or setpoint in April. Log commanded and measured values for every dynamic setpoint, plus supply current for every motor. *(shooter-power-analysis, log-the-tune-spec)*

## Vision

48. **Vision noise has a floor (~7–8 cm).** A distance²-only trust model drives the assumed error to zero up close and over-trusts every frame. *(vision-analysis)*
49. **Fixing one bug can unmask mis-weighted data.** The MT2 typo fix alone raised pose jumps from 83 to 317 per minute. Replay before shipping. *(vision-analysis)*
50. **Better odometry is what lets vision be trusted less.** Calibrate gyro scale and wheel radius on each new robot. Separate slip from calibration error first: the ~9% distance over-count was mostly slip, and true radius error was ~1–2%. *(vision-analysis, wheel-slip-analysis)*
51. **Score accuracy against a sensor the estimator doesn't listen to.** *(vision-analysis)*

## Method

52. **Label estimates, and validate them when real data arrives.** The V·I / V_batt supply estimate matched measured supply at r = 0.9985 for drive and within 0.6% for steer, but read ~7% low on feeder energy. *(supply-current-analysis, steer-match-analysis, feeder-power-baseline)*
53. **AdvantageKit logs on change.** Resample onto a uniform grid (50 Hz was used) before averaging. *(shooter-power-analysis)*
54. **A/B/B/A test design rules out drift, warm-up and battery effects.** Prefer ratio shapes over magnitudes, and give field testers explicit pass/fail criteria. *(kv-drivetest-analysis, drive-kv-student-test-guide)*
55. **Measure what matches the problem.** For brownouts that means matches with a brownout and match time remaining at the first one. *(bob-power-review)*
56. **Re-check prose against its own tables.** July's "~10 A/motor" steer figure was actually the four-motor total. *(steer-match-analysis)*
57. **Validate a third-party tool's numbers independently.** Flashpoint matched owlet to ~1% per motor. *(flashpoint-trial)*
58. **Use other teams' code as structure, not numbers.** 6328's current budgeting reflects their game strategy. *(drive-tuning-guide)*
59. **Replay needs every value the code reacts to to come in as an input.** *(advantagekit-io-rewrite)*

## Communication

60. **Say what changes and what doesn't after a fix.** After the kV fix, average match current could rise because the robot reaches speeds it couldn't before. *(drive-kv-explainer)*
61. **For the team: current (A) on charts, brownout match counts, and no blaming batteries.** *(knowledge/team.md)*

## Working with AI

62. **Code lives in repos, not docs.** The 2026 Project kept Java and patch snapshots as docs, where they drifted from the real branches (`health-monitor-code/` vs BaseComp).
63. **Know which branch you're reading.** The 2026 Project synced `main` while the team worked on `BaseComp`.
64. **Track whether a decision shipped.** Several 2026 decisions were agreed but never implemented (shooter full idle, the follower current limit, the feeder setpoint), and nothing recorded the gap. Use `decided` vs `applied` in `knowledge/decisions.md`.
65. **Memory is a notebook, not a knowledge base.** It drifted into duplicate files and stale summaries. Facts go in files with a status and a date.
66. **Have a fresh session check team-facing numbers.** A session that wrote an analysis tends to confirm itself.
