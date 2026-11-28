# CLAUDE.md

Context repo for Doug's AI-assisted work on FRC Team 88 (TJ²) robots. Read this file at the start of every session. The same rules apply in Claude Code and in the Claude Project that syncs this repo.

## Who you're working with

- Doug: mentor on Team 88. Strong on hardware, physics, control theory and Linux. He describes his programming background as weak, so explain code plainly.
- He wants precise answers, step-by-step diagnostics, and imprecise framings corrected rather than affirmed.
- Team context and standing rules: `knowledge/team.md`.

## How this repo is organized

- `knowledge/`: what is true now. Edit in place; git keeps the history.
- `analyses/`: dated records of findings. Never rewrite a finding after it's done; only update its `status`.
- `knowledge/decisions.md`: dated decision log. Add an entry whenever a session reaches a decision.
- `INDEX.md`: one line per doc. Update it in the same commit as any doc you add or re-status.
- `.claude/skills/`: repeatable procedures.
- `scripts/`: reusable analysis code.
- `lessons/`: distilled principles and baselines from past seasons.
- `archive/<year>/`: frozen past-season docs. Reference only. Never edit, and never treat as current.

Every doc starts with frontmatter:

```yaml
---
title:
status: current   # see the status list below
date: YYYY-MM-DD
source:           # log file + match, or repo @ commit
superseded_by:
---
```

Status values:
- `current`: a living doc that's up to date
- `stub`: placeholder, still to fill
- `proposed`: recommended, no decision yet
- `decided`: agreed, not yet shipped
- `applied`: shipped (say where, with a commit if possible)
- `tabled`: deliberately set aside
- `superseded`: replaced (fill `superseded_by`)
- `reference`: guide, spec or tool doc with no decision attached

Move an analysis from `decided` to `applied` only with evidence that it shipped.

- Every number names its source (log file and match, or a commit).
- One subject per file; keep files short.
- No logs or large binaries in git. Link to their location on Drive.

## Git rules

- **This repo:** Claude commits freely and may make any change it judges useful. A commit that changes `CLAUDE.md` must state the rule change in its message, and Claude tells Doug in chat.
- **Pitwall (`DStewart-88/frc-pitwall`):** Claude owns branches, commits and merges.
- **Team robot repos (`frc-88/*`):** preview changes first. No branch, commit or push without Doug's explicit go-ahead.
- Always state which repo, branch and commit you are reading. The branch the team develops on is not always `main`.

## Analysis standards

- Before a finding is treated as settled, re-derive it from first principles and try to falsify it. A number that nearly matches may be a units error.
- Correct feedforward before adjusting feedback gains.
- Brownout impact is measured as (1) number of matches with a brownout and (2) match time remaining when the first brownout starts. Not summed seconds below threshold.
- Team-facing charts use current (A). Doug's own analysis can use power (W).
- Team-facing write-ups do not blame battery quality.
- Before a change rolls out, list the failure symptoms it could cause.
- Design test protocols so they can't produce ambiguous results.
- For team-facing numbers, recommend a check by a fresh session that didn't write the analysis.

## Control system (2027 onward)

- The robot uses Systemcore and WPILib 2027 (`org.wpilib` packages, multiple CAN buses). Your training is mostly roboRIO-era. Check `knowledge/control-system.md` and the current WPILib docs before writing or reviewing robot code, and don't assume `edu.wpi.first` APIs.

## Privacy

- Students are referred to by role only. No personal details about students in this repo.
- **This repo is public.** Write every file and commit message as if students, parents and other teams will read it: no names of people other than Doug, no personal details, no passwords (published factory defaults are fine), no share links that open private files, and no judgments about individuals.
