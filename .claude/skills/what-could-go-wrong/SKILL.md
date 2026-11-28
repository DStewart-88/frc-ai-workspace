---
name: "what-could-go-wrong"
description: "Check a new or changed piece of robot code, config, tuning or Pitwall for bugs and side effects before it ships. Use after developing anything, or when asked what could go wrong."
---

# What could go wrong

A review of a change before it ships. The goal is to find what it breaks, what it silently fails to do, and how the team would notice. Doug is strong on hardware and control but describes his programming background as weak, so explain code findings in plain language.

If you wrote the change in this same session, say so in the report and recommend a second pass by a fresh session. A session tends to confirm its own work (lessons #66).

Rules come from `CLAUDE.md` in DStewart-88/frc-ai-workspace; lesson numbers refer to `lessons/lessons-2026.md` there. Read both if you can. Team robot repos (`frc-88/*`) are preview only: no branch, commit or push without Doug's explicit go-ahead.

## 1. Pin down the change

- State the repo, branch and commit, and the diff being reviewed. For robot code, confirm which branch the team develops on; it may not be `main`.
- Write one sentence each: what it is meant to do, and what must behave exactly as before.
- For 2027 robot code, check `knowledge/control-system.md` and current WPILib docs before judging any API. Don't assume `edu.wpi.first`.

## 2. Trace what it touches

Read callers and consumers, not just the diff.
- Who else reads each changed value, signal, gate or log key? Who else commands the same mechanism?
- What starts at the same moment (parallel command groups, shared gates)?
- Behavior in disabled, auto, teleop and test, at boot, on re-enable, and after a command is interrupted.
- Followers and sibling motors that should have received the same change.
- Renamed log keys, which break Pitwall robot profiles silently.

## 3. Check the known failure patterns

Skip the groups that can't apply, and say which you skipped.

**Does it actually take effect?**
- Config fields for the wrong control mode (#11); config built but never applied (#12); empty follower config (#13); practice values left in the competition config (#14).
- Stator limit above the TorqueCurrentFOC command, so it never engages (#15).
- A saved robot preference overriding the code default (#16).

**Units and control**
- Shaft reference and units of every gain and setpoint (#1); gains re-derived after a control mode change (#5).
- Setpoint reachable under battery sag (#7). Feedforward right before feedback is adjusted (#3).

**Gates and detection**
- What a debounce costs while it holds (#26); every threshold has a hold time (#27); direction versus magnitude (#28); the signal can actually see the failure (#29); thresholds relative to the running level (#30).
- Stale values from signals with no update rate, with no error raised (#42).

**Shared resources**
- CAN load per bus and headroom (#40, #41); loop time, including observe-only code (#39, #44).
- New or overlapping current draw; supply versus stator limits (#21).
- Robot code stays lean: no code or functions beyond what's needed.

**Pitwall and other tools**
- Empty, partial, never-enabled and older-season logs.
- Run `python3 -m unittest`. If power math changed, run `tools/validate_bob.py` against the BOB logs. If report pages changed, bump `REPORT_VERSION` in `pitwall/eventrun.py`.
- Anything touching the robot's USB stick stays read-only.

## 4. Try to prove each suspicion

Read the path through, run a test, or replay logs (#49). Label each item **confirmed**, **plausible (not tested)** or **ruled out**. Don't present a guess as a bug. A clean result is a valid result.

## 5. Report

1. **Verdict:** ready to try, fix first, or can't tell yet (and what's needed).
2. **Risks**, worst first: what goes wrong; the symptom the team would see; status and evidence; how to check it; how to fix or roll back.
3. **Checked and fine.**
4. **Not checked,** and why.
5. **Test plan:** steps with explicit pass/fail criteria that can't give an ambiguous result. Use A/B/B/A for comparisons (#54). Students may not touch the robot while it is enabled, in any mode.

Report before changing code. If the review leads to a decision, offer an entry for `knowledge/decisions.md`, marked `decided` until there is evidence it shipped.
