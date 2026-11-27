---
title: Setting up the 2027 claude.ai Project
status: current
date: 2026-11-27
source: 2026 Project planning chat, 2026-11-27
superseded_by:
---

# Setting up the 2027 Project

This one is Doug's to do: Claude can't create a claude.ai Project. Work through the steps in order. The 2026 "FRC 2026 Robot" Project stays as it is, as a read-only reference.

## 1. Create the Project

- Name: something like "FRC 2027 Robot".
- Description: one line, e.g. "AI-assisted analysis, tools and write-ups for Team 88's 2027 robot. Context lives in DStewart-88/frc-ai-workspace."

## 2. Paste the instructions

Paste this into the Project's custom instructions. It's deliberately short: the full rules live in the synced `CLAUDE.md`, so they're edited in one place.

```text
This Project works from the GitHub repo DStewart-88/frc-ai-workspace, which is synced into the Project.

At the start of every chat, find and follow the synced CLAUDE.md. It holds the working rules: git permissions per repo, analysis standards, how results are framed for the team, and the Systemcore / WPILib 2027 caution. If CLAUDE.md and these instructions ever disagree, CLAUDE.md wins.

Before answering from memory about the robot, the team or past decisions, check the synced repo: knowledge/ (what's true now), knowledge/decisions.md (what was decided, and whether it shipped), lessons/ (2026 lessons and baselines).

The sync is read-only. When a chat reaches a decision or a finding worth keeping, say so and offer to commit it to the repo (knowledge/decisions.md, or a dated file in analyses/), or hand the text over for Claude Code to commit.

Always state which repo, branch and commit you are reading.
```

**Keep these two copies in step.** When `CLAUDE.md` changes in a way that affects the summary above, update the pasted text too. Claude will mention it in chat when that happens.

## 3. Sync the repos

Add each one as a GitHub sync source in the Project.

| Repo | Branch | Paths | Why |
|---|---|---|---|
| `DStewart-88/frc-ai-workspace` | `main` | Everything **except `archive/`** | The shared context. The archive is excluded so 2026 docs don't come up ahead of current ones; Claude Code can still read it on demand. |
| `DStewart-88/frc-pitwall` | `main` | `docs/` only | Pitwall's status and design notes, as decided Nov 13. Pitwall's code doesn't need to be in the Project. |
| Team 2027 robot repo (`frc-88/…`, once it exists) | **The branch the team actually develops on.** In 2026 that was `BaseComp`, not `main`; ask the software lead. | `src/` plus any build/config files worth reading | So chats read the real code. The 2026 Project synced `main` and was sometimes reading stale code. |

How to exclude `archive/`: the sync filter takes per-path include/exclude rules. The 2026 Project uses one to include only `/src/` from the 6328 repo. Include `/` and exclude `/archive/`.

If exclude isn't offered, include these instead: `/CLAUDE.md`, `/README.md`, `/INDEX.md`, `/knowledge/`, `/lessons/`, `/analyses/`, `/setup/`, `/.claude/`, `/scripts/`.

Optional: Team 6328's 2027 public code, if they publish it, with `src/` only. Use it as a structural reference, not for numbers (lessons #58).

## 4. Choose the memory setting

Projects have a memory setting on the Project's own page. It keeps the Project's memory either **connected** to your general memory or **separate** from it in both directions.

**Recommended: separate.**
- The robot context now lives in the repo, so the Project doesn't need your general memory to know who you are or how you work.
- Separate keeps robot details out of your everyday chats and keeps unrelated memory out of robot chats.
- The 2026 Project's memory isn't visible to the 2027 Project under either setting. Anything worth keeping from it is already in the repo.

Choose **connected** instead if you want everyday chats to pick up robot context, or robot chats to know your general background.

## 5. Check it works

1. In the new Project, start a chat and ask: "What are the git rules for each repo, and which branch of the robot repo are you reading?" The answer should come from the synced `CLAUDE.md` and name the branch.
2. Ask: "Was the shooter full-idle decision ever implemented?" The answer should be "no", from `knowledge/decisions.md`, not a guess.
3. In Claude Code, on your Ubuntu machine, clone the repo and start a session in it. Ask the same first question. Claude Code reads `CLAUDE.md` on its own.

## 6. After setup

- Add a `knowledge/decisions.md` entry: "2027 Project created; sync settings as in setup/2027-project.md."
- When the 2027 robot repo is created, come back to step 3 and add it.
