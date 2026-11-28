---
title: Decision log
status: current
date: 2026-11-27
source: sessions with Doug
superseded_by:
---

# Decisions

Newest first. One entry per decision. Add an entry whenever a session reaches one.

Format:

```
## YYYY-MM-DD · Decision in one line
Status: decided | applied (where/commit) | reversed | superseded
Why: the reason, with the key number
Rejected: alternatives considered and why
Evidence: analyses/... or archive/2026/...
```

Keep `Status` honest. In 2026 several decisions were agreed and never shipped, and nothing recorded the gap.

## 2026-11-27 · 2027 claude.ai Project created
Status: applied (by Doug, following setup/2027-project.md)
Follow-ups: confirm the archive/ exclusion took effect; frc-pitwall has no docs/ folder yet, so its sync source is empty until one is added

## 2026-11-27 · Context repo lives in Doug's personal account; Claude commits freely
Status: applied (DStewart-88/frc-ai-workspace)
Why: the team is still working out how AI fits into students' workflow; Doug keeps control of access for now
Rejected: frc-88 organization (premature); inside the robot repo (needs team buy-in, mixes AI files into team code)
Evidence: 2026 Project planning chat, 2026-11-27

## 2026-11-27 · Use both Claude Code and a 2027 Claude Project, linked by this repo
Status: decided (trial)
Why: Claude Code runs code and reads logs locally; the Project gives phone access, shareable docs and chat history. The repo keeps both on the same context.
Rejected: Project only (copy-up friction for code and logs); Claude Code only (no phone, no team docs)
Evidence: 2026 Project planning chat, 2026-11-27

---

# Carried over from 2026

Decisions from the 2026 season that still shape 2027 work. Dates are to the month where the exact day wasn't recorded. Evidence is in `archive/2026/` unless noted.

## Drive and current limits

## 2026-08 · Characterize and install drive kV/kS first, then lower kP
Status: applied (voltage-mode kV 0.871 by Aug 27), then superseded by the FOC switch
Why: kV 0.124 was a motor-shaft constant in a wheel-unit loop; lowering kP first makes the robot slower
Evidence: drive-kv-explainer.md, kv-drivetest-analysis.md

## 2026-08-28 · Drive moved to TorqueCurrentFOC
Status: applied. The FOC kV was later found ~10× too high (robot ran ~1.29× fast at partial stick); a fix of kV ≈ 1–2 A/rps was recommended but never applied
Why: ~15% more peak power and exact traction control
Evidence: foc-vs-voltage-drive-control.md, drivetests2-tuning-runs-0828.md, newfloor-practice-precomp-review.md

## 2026-10 · Steer back from TorqueCurrentFOC to Voltage at the Newton gains
Status: applied (VoltageSteer branch, aa4e5e2, per the 2026 "Pre NERD analysis" chat)
Why: FOC steer tracked about 3× worse (heading error 11–16° vs 4.6–4.8° moving)
Evidence: newfloor-practice-precomp-review.md

## 2026-11 · Drive supply limit 35 A (from 45 A); new 25 A steer supply limit
Status: applied (BaseComp 0d4e0b9, before BOB)
Why: halves time below 6.5 V for ~0.15 m of mid-sprint auto lag; the steer cap is nearly free. BOB drive charge fell ~0.8 Ah.
Rejected: 30 A (drivers feel it; the auto sprint ends short); a shooting-only cap (saves little charge, needs runtime config writes); the earlier tiered 50→35 A / 20 A steer spec (never merged)
Evidence: riverrage-drive-limit-whatif.md, practice-1029-1030-shoot-on-move.md, bob-power-review.md

## 2026-10 · Intake rollers stay on while shooting
Status: applied (kept as is)
Why: the rollers help feeding, and there was no time to measure how much
Evidence: riverrage-drive-limit-whatif.md

## 2026-09 · Drive acceleration limiting while shooting: tabled
Status: tabled; the 35 A supply limit later did part of the same job
Why: smooths drive transients but doesn't fix chronic over-draw; wait for logs with the other fixes in

## Brownout strategy

## 2026-09 · No shooting-subsystem sequencer
Status: decided
Why: the drivetrain was ~80% of composite draw at shoot-window starts; the shooting stack was only ~70–80 A
Evidence: shooter-power-analysis.md (cross-subsystem section) and the 2026 Project notes

## 2026-11 · Fall brownouts are a battery-depletion problem; judge fixes by charge saved
Status: decided
Why: 450 of 471 River Rage onsets came in the last quarter; ramps and transient caps don't move the first brownout, only lower total draw does
Evidence: riverrage-shoot-spike-review.md, bob-power-review.md

## Shooter and feeding

## 2026-09 · Shooter flywheel holds a ready speed whenever enabled (full idle)
Status: decided, **never implemented** (90% of NERD shoot windows still started cold)
Why: coast-to-zero caused ~17–20 cold spin-ups per match at ~112–120 A supply each; holding costs ~14–15 A, ~3 Wh/match
Rejected: gated or predictive pre-spin (trivial savings, reintroduces inrush when the gate leads a burst poorly). Fallback if energy ever matters: a two-tier low-floor idle.
Evidence: shooter-power-analysis.md, nerd-initial-review.md

## 2026-09 · Give the shooter follower a 60 A stator limit
Status: proposed, **never implemented** (still unlimited at NERD)
Evidence: shooter-power-analysis.md

## 2026-10-05 · Debounce turret onTarget once, upstream, at 0.2 s
Status: applied (PR #52, a190eeb), then **reversed** on Oct 29 (7f70d66 sets it to 0 s)
Why it shipped: one change de-chattered the feeder and all floor motors (33 raw flickers → 2 gate toggles)
Why it was reversed: at River Rage it let balls feed for up to 0.2 s while the turret swung back from a stale shoot-on-move lead. Accepted trade-off: the feed chatter returned (gate re-opens per match: BOB 74, RR 42, NERD 27).
Evidence: feeder-power-analysis.md, newfloor-practice-precomp-review.md, bob-power-review.md

## 2026-11-06 · Replace the team's supply > 55 A anti-jam trigger with stator current + velocity, plus a signed funnel rule, held 0.3 s
Status: decided (anti-jam-trigger branch, 0be4b45); merge unconfirmed
Why: supply current misses full stalls and false-fires during flow
Evidence: jam-review-1105.md

## 2026-11-06 · Automatic anti-jam is teleop-only
Status: decided (5aed412); merge unconfirmed
Why: a fire in auto cancels the whole auto routine, a very bad outcome. An auto-resume version (stop 0.5 s, resume) is parked on a branch until the team reports the current behavior as a problem.
Evidence: jam-review-1105.md

## 2026-10-13 · Shot counter and jam detector as watch-only code, in stacked PRs
Status: PR #57 (shot counter) never merged; the shot counter became a Pitwall module instead (Nov 10)
Evidence: shot-counter-design.md, jam-detection.md

## Health and diagnostics

## 2026-09-23 · Health monitor: WPILib AlertType severities, per-match latch, LEDs pull from the monitor
Status: applied (BaseComp fc868cc, Oct 19); LEDs never built
Rejected: custom RED/YELLOW levels; an Annunciator interface
Evidence: health-warning-system-design.md

## 2026-10 · Health monitor lists an item only when something needs to be done
Status: applied
Why: every listed item should mean an action, so the team never learns to ignore entries
Evidence: health-warning-system-design.md

## 2026-10 · Validate the health monitor by past-log replay and code review, then on the robot
Status: applied
Rejected: AdvantageKit sim/replay testing (too much extra development)
Evidence: health-monitor-nerd-replay.md

## 2026-10-17 · Health monitor tuning from NERD logs: 0.1 s disconnect debounce, Brownout as a warning, CAN utilization at 85% for 2 s
Status: applied (566dfa8, merged with fc868cc)
Why: the original thresholds gave ERROR after 10 of 11 NERD matches; afterwards every ERROR was a real dropout
Evidence: health-monitor-nerd-replay.md

## 2026-10 · CAN errors: kError at a count of 96; CAN/BusErrors moves to a rate-based trigger
Status: 96 applied; rate-based agreed (~10 episodes per 60 s proposed, number not confirmed)
Rejected: 25 (too few net transmit errors); 128 (already failing)
Evidence: health-monitor-handoff.md, health-monitor-oct20-21-review.md

## 2026-10-02 · Leave setBrownoutVoltage(6.5) alone; low-battery threshold 12.3 V
Status: applied
Why: changing the brownout voltage changes robot behavior; 12.3 V was the lowest 2026 pre-match resting voltage
Evidence: health-monitor-handoff.md

## 2026-10 · Live red/green "error active" light; drive module faults name their corner
Status: decided
Why: at River Rage it took too long to find which module had the encoder fault. Faults while disabled (pre-match) proved useful, so the enabled-only decision is being revisited.
Evidence: 2026 Project notes

## 2026-09-29 · Tread wear: wheel distance only, stored in a properties file on the roboRIO; "inspected" reset snoozes by a condition-graded distance; plain Alerts, not LEDs; one combined total
Status: applied (5cbfb6d, ran at River Rage). Thresholds not yet calibrated: no inspections recorded.
Rejected: a scrub model; Preferences storage (easily edited by accident, rewritten every loop); JSON; splitting match vs practice usage
Evidence: component-usage-tracker-design.md, tread-usage-riverrage-review.md

## 2026-10 · Pit systems check runs from a dashboard chooser in Test mode, opt-in; drive checks first
Status: decided
Why: don't change what people expect from each mode; get the framework working on one subsystem before expanding
Evidence: 2026 Project notes

## CAN, code and performance

## 2026-08 · optimizeBusUtilization on roboRIO-bus mechanisms; 1000/500 Hz signals cut to ~100 Hz
Status: applied (bus ~77% → ~41%, zero errors)
Evidence: can-bus-analysis.md, can-utilization-fix-report.md

## 2026-10 · Loop-overrun fixes carry forward as good practice, not a 2026 fix
Status: tabled for 2026
Why: with Systemcore coming, present it as efficient-code practice. Carry forward batched Phoenix reads (`refreshAll`), fewer method-level `@AutoLogOutput` getters, and a LoggedTracer-style timing utility.
Evidence: loop-overrun-analysis.md

## 2026-10-05 · Vision changes on a local `vision-tuning` branch as four separable commits
Status: decided; branch never pushed, calibrations not applied
Commits: MT2 typo fix; variance start values; a measured noise model with `visionTrustMultiplier = 3.0`; per-camera std-dev logging
Rejected for now: speed-scheduled trust, a spin gate, the MT2 position split; a "reject single-tag beyond 3.5 m" filter (worst-case error 32.1 → 38.6 cm)
Evidence: vision-analysis.md

## 2026-11 · AdvantageKit IO rewrite stays uncommitted
Status: tabled
Why: educational; the team will likely keep its current code format
Evidence: advantagekit-io-rewrite.md

## Logs and tools

## 2026-11 · Robot logs live on the team Drive, not in git
Status: applied (manual upload; rclone considered)
Why: logs don't change and exceed GitHub file limits. Layout: per-season folder with "01 events" and "02 practice"; practice days grouped under the event before them ("after <event>"); hoot logs in a subfolder per event.
Rejected: a fully chronological mix (event logs get lost among practice days)

## 2026-11-08 · Build Pitwall (DStewart-88/frc-pitwall, BSD 3-Clause) instead of adopting Flashpoint
Status: applied (v0.9.0 by Nov 19)
Why: Flashpoint can't read AdvantageKit logs and has no power-budget view; Doug wants team-specific analyses in one format, easy to customize and styled to share. Credits Flashpoint.
Shape:
- runs on a pit or personal laptop with a GUI, not on the robot or driver station
- robot profiles live in the app, so using Pitwall never requires a robot code change
- app first, then analysis modules
- match breakdowns follow the game's own periods
- one page per event or match, with a tab per module; the Overview tab stays up by default on a pit screen
Evidence: log-processor-framework.md, flashpoint-trial.md

## 2026-11 · Pitwall publishes no "charge left" estimate
Status: decided
Why: voltage collapses suddenly near the end of a pack; a backtested model ran a median 1.5–2.2 Ah late
Evidence: log-processor-framework.md

## 2026-11-11 · Pitwall support for other teams: parked
Status: tabled
Why: robot architectures differ too much; make it work for Team 88 first
Evidence: pitwall-other-teams-testset.md

## 2026-11 · Pitwall log fetch is read-only on the robot's USB stick; runs on the pit laptop
Status: applied
Why: never move or delete files on the robot. The team clears the stick by hand, with a nudge at 1000 files; the driver station laptop is left alone.

## 2026-11-17 · Pitwall covers practice only when it's run as matches
Status: decided
Why: open-ended practice questions are specific tests, better answered by giving logs to AI. Practice matches (Driver Station practice mode) get the same report and counting rules as events, one report per practice stretch between events, split by day.

## 2026-11-13 · Pitwall's 2027 status lives in `docs/` in the frc-pitwall repo
Status: decided
Why: syncs into the 2027 Project alongside this repo
Evidence: log-processor-framework.md
