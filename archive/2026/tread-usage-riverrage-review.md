# Tread Usage Tracker — River Rage (Oct 24, 2026) Review

*First event with the tread usage tracker (`TreadUsageTracker`, BaseComp builds `fc868ccc` and `b2e88a99`) running. roboRIO `03223846`. Source: all 17 `.wpilog` files in `2026 Logs/river rage/`, plus the Oct 19–23 practice / STEAM-day logs for context. Scripts and a per-log CSV are in `FRC Logs/tread-usage-riverrage-1024/`.*

## Headline numbers

**River Rage added about 3.0 km of tread travel per module in one day.**

| Module | Start of event (m) | End of event (m) | Accrued at River Rage (m) |
|---|---|---|---|
| FL | 7,490 | 10,417 | 2,927 |
| FR | 7,465 | 10,478 | 3,014 |
| BL | 7,120 | 10,185 | 3,065 |
| BR | 7,300 | 10,307 | 3,007 |

- **All of it was on the field.** The three non-FMS logs (pit/queue boots) recorded 0 m. Distance while disabled was under 4 m per module for the whole day.
- **Per full match: mean 265 m, median 268 m** (10 matches with a full 160 s of driving; range 183–321 m). That's about 10% above the 2026-season figure of 243 m/match.
- **Match breakdown:** Q4, Q7 (two logs: a 114 s attempt that appears to have been replayed, 252 m, then the full 321 m match), Q12, Q18, E4, E8, E10, E12, E13, E14, E15, E16.
  - **E15: only 104 m.** The drive moved for about 60 s, then stopped for the rest of the match while still enabled.
  - **E16: 0 m.** Every drive and steer motor, every steer encoder and the gyro reported disconnected for the whole match. The tracker had no signal to count, but the robot couldn't drive either.
- **Module balance:** BL ran the furthest at the event (+4.7% over FL). Since the tracker was installed, the front modules lead slightly (FR 10.48 km vs BL 10.18 km, a 2.9% spread). That's smaller than the ~7% front/back gap in the 2026 comp season.

## Tracker correctness (test plan stage 1)

- **Counting matches the raw signal exactly.** Recomputing |ΔDrivePositionRad| × 2.0 in from the logged positions gives the same totals as `LifetimeMeters` on all four modules (ratio 1.0000). No reboot-guard skips and no NaN readings all day.
- **Persistence works across boots.** Each log starts where the previous one ended, across all 17 boots.
- **Small loss at power-off (negligible).** Motion after the last save is lost when the robot powers off. This is up to 0.2 m per boot (about 0.5 m all day). The cause: saves happen on the transition to disabled and every 60 s while enabled, but **not while disabled**, so pushing or carting the robot after a match isn't saved. Fix if wanted: also save on power-down or periodically while disabled when the value has changed.
- **No service actions were ever recorded.** All four modules still show label `unknown` with no grade. `NextInspectionAtMeters` = 2,000, and `InspectionDue` = true for the whole event. `Usage/LastAction` never left "Ready".

## Usage history since the tracker was installed

The counters started from zero on **Oct 19, 2026 at 22:49** (third log of that practice; the first Oct 19 session, 777 s enabled, came before the tracker and isn't counted).

| Period | FL distance (km) | Notes |
|---|---|---|
| Oct 19 practice (after install) | 1.35 | |
| Oct 20 practice | 1.19 | FL crossed 2.0 km here; warning active ever since |
| *Gap: Oct 20 night → Oct 21 morning* | *0.98* | *Counted by tracker, no log in the archive* |
| Oct 21 STEAM day | 2.05 | |
| *Gap: Oct 21 evening → Oct 22 night* | *1.61* | *Counted by tracker, no log in the archive* |
| Oct 22 practice | 0.32 | |
| Oct 24 River Rage | 2.93 | |
| **Total** | **10.42** | 6 calendar days |

**About 2.6 km per module (~25% of the total) was driven with no log in the archive.** Either logs weren't saved or they weren't copied off the robot. This is the on-robot counter doing exactly what it was designed for. It also means log-only sweeps, like the 2026 season backfill, undercount real usage by a lot.

## What this says about the inspection thresholds

Current schedule (`TREAD_SCHEDULE`): first inspection at 2.0 km; snooze Good +2.0 / Worn +1.0 / Poor +0.25 km.

**What River Rage validates: the conversion from distance to matches and events.**

| Interval | Full matches at the River Rage rate (265 m) | Design assumption |
|---|---|---|
| 2.0 km (first inspection / Good) | ~7.5 | ~8 |
| 1.0 km (Worn) | ~3.8 | ~4 |
| 0.25 km (Poor) | ~0.9 | ~1 |
| One-day event | 3.0 km | "roughly 3–4 km including practice matches" |

- The match-count assumptions hold, slightly on the conservative side.
- At this rate, fresh tread installed before a one-day event like this would come due around the 8th match (about Q18/E4 here).
- A Good grade would then come due again around the end of elims. So a 2.0 km interval means roughly 1–2 inspection prompts per event day.
- **Practice weeks accrue as fast as events.** The four shop/STEAM days before River Rage added 7.5 km, about 2.5 events' worth. A 2.0 km interval means several prompts per heavy practice week.

**What River Rage cannot validate: whether 2.0 km is the right *wear* point.**

- No inspection grades exist yet, so there's nothing that ties distance to tread condition.
- The tread is now at **10.2–10.5 km since install**. That's a lower bound on its real age: the pre-tracker Oct 19 session and any use before Oct 19 aren't counted.
- The inspection warning has been showing continuously for about 8.4 km without anyone acting on it. This is the ignored-warning failure the health-system design warns about.

## Recommended next steps

1. **Inspect all four treads now and press Record Inspection with a grade for each.**
   - This is the first real calibration point, at about 10.2–10.5 km (a lower bound on tread age).
   - If the tread grades Good at 10 km, the 2.0 km first interval is very conservative. A starting value of 4–5 km would better match the "only prompt when action is needed" principle.
   - If it grades Worn or Poor, 2.0 km is a reasonable early-warning point.
2. **When this tread is eventually replaced,** use Record Replacement with a real design label. The service-log row will capture the final distance (and the label `unknown`) as the old tread's life.
3. **Pull every log off the robot after each session** (the two gaps above), or accept that the on-robot counter is the source of truth for usage.
4. *(Optional)* Save the counters while disabled as well, to close the small power-off loss.
