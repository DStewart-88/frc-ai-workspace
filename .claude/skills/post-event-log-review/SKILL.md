---
name: "post-event-log-review"
description: "Analyze the robot logs after an FRC event or event day: Pitwall report, standard sweep, anomaly digging and follow-ups. Use for any event or match-day log review, including scheduled ones."
---

# Post-event log review

Events leave little time for analysis. Run this after a day or a whole event to find what needs fixing, what to watch, and what the numbers were, the same way every time.

Follow `CLAUDE.md` in DStewart-88/frc-ai-workspace. Lesson numbers refer to `lessons/lessons-2026.md` there.

## 0. Scope and inventory

- Which event, and one day or the whole event? Logs are in the team archive: `<season>/01 events/<date>_<code>_<name>/` (practice is under `02 practice/`). In an unattended run, take the newest event folder and say so at the top.
- Say which computer and archive path this run used. Several computers hold archives, so any one may be incomplete.
- List the matches found against the matches played. Name missing, skipped or unreadable logs.
- Record the build (git SHA, branch, dirty flag) per log and flag changes between matches. Dirty builds can't be told apart by SHA (#46).
- If the logs can't be reached, or nothing is new since the last review, say so and stop. Never fill in from memory.
- Never move, rename or delete logs.

## 1. Run Pitwall first

From a checkout of DStewart-88/frc-pitwall (Python 3.11 or newer):

```sh
python3 -m pitwall event "<event folder>" -p <profile> -o <output folder>
```

Add `--compare <earlier event output folder>` to compare events. Read `event.json` and the match reports. Say which matches Pitwall counted and which it left out.

The profile must match the robot: `2026-comp` is for 2026 logs only. Before trusting Pitwall on 2027 logs, check the "2027 readiness" list in its `docs/status.md`. If Pitwall can't read them, use `scripts/wpilog_reader.py` from the context repo and say what was done by hand.

## 2. Standard sweep

Cover every item, or say why it couldn't be done.

- **Brownouts:** matches with a brownout, and match time remaining at the first. Late-match depletion or stacked transients (#17)?
- **Power:** charge per match and split by subsystem. Say whether current was measured or estimated, and signed or absolute.
- **Health:** devices that left a bus, especially repeats; CAN use and errors per bus; loop time; wear.
- **Mechanisms:** setpoint versus measured, saturation, current limits reached, and current that is wrong for the speed, which means something physically changed (#31).
- **Scoring:** shots per match and per shift, balls per second, jams. These are shots, not scored balls.
- **Changes since the last event:** did each one behave as intended? Check `knowledge/decisions.md` for items marked decided that never appear in the logs (#64).
- **Comparison:** against the previous event. `lessons/2026-baselines.md` describes a different robot from 2027's, so label any cross-season comparison.
- **Team observations:** ask what the drive team and pit crew saw. In an unattended run, list this as an open question.

## 3. Dig into what stands out

Take the few anomalies that matter most (about three) and find the cause. Resample AdvantageKit logs to a uniform grid before averaging (#53). Re-derive each finding and try to disprove it on another match. For a deep look at one mechanism, follow the `subsystem-power-review` skill in the context repo.

## 4. Write it up

Save as `analyses/YYYY-MM-DD-<event>-review.md` with the repo's frontmatter (`status: proposed`, `source:` log files and code commit), and update `INDEX.md` in the same commit. Without write access, hand over the text.

1. **Headline:** two or three sentences.
2. **Fix before the robot next runs:** action, owner by role, and how to confirm it worked.
3. **Watch:** not yet worth changing.
4. **Numbers:** the same table each time, with the previous event beside it.
5. **Open questions** and **not analyzed**.

Every number names its match, log and signal. Label estimates. Students appear by role only.

If a team-facing version is wanted: current in amps, brownout match counts with time left, plain language, no blaming battery quality. Recommend a fresh session check the numbers first.
