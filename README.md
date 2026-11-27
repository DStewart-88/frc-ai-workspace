# frc-ai-workspace

Shared context for AI-assisted work on FRC Team 88 (TJ²) robots, starting with the 2027 season.

This repo is the go-between for two ways of working with Claude:

- **Claude Code** (local): robot code, Pitwall, and analysis of log files on disk. It reads `CLAUDE.md` automatically.
- **A Claude Project** (claude.ai): discussion, team write-ups, and access from a phone at events. It syncs this repo from GitHub.

Both read the same files, so neither has to remember what the other did.

## Where things go

| Folder | What it holds | How it changes |
|---|---|---|
| `knowledge/` | What is true now: team, robot, control system, game, logging, decisions | Edited in place; git keeps history |
| `analyses/` | Dated findings | Written once; only the status changes |
| `.claude/skills/` | Repeatable procedures (e.g. subsystem power review) | Improved over time |
| `scripts/` | Reusable analysis code | Like any code |
| `lessons/` | Principles and baselines distilled from past seasons | Rarely |
| `archive/` | Frozen docs from past seasons | Never |

`INDEX.md` lists every doc with its status. Start there.

## Syncing into the 2027 Project

Exclude `archive/` from the Project's GitHub sync. Old docs otherwise come up in searches ahead of current ones. Claude Code can still read the archive on demand.

## Conventions

- Each doc starts with a small header: title, status, date and source. The status values are listed in `CLAUDE.md`.
- Numbers name their source: a log file and match, or a commit.
- Logs and other large files live on Drive, not here.
- Students are referred to by role only.

## Ownership

Private, in Doug's account, while the team works out how AI fits into students' workflow. May transfer to the `frc-88` organization later.
