# Drive Tuning Runs — offseason drivetests2, 2026-08-28

Analysis of the nine AdvantageKit logs in `drivetests2` (recorded ~00:24–00:56 on Aug 28),
the night the team swept drive-tuning changes. The changes were never committed (all logs read
`GitDirty = Uncommitted changes` on commit `e85757e2`, branch `BaseComp`), so this maps runs to
configs from **log evidence + build timestamps + a teammate's scratch notes**, not from source.

## Teammate's scratch notes (verbatim, lightly ordered)

> First run was just what we were doing before. Second run same numbers but updated auto path
> (trying to make it more consistent). Third is adding a kS of .25. Then P of 15 (horrible),
> then P of 5 (bad, tower smash), then P of .1, then .5 I believe, then lastly TorqueCurrentFOC
> with numbers copilot gave that should be our previous numbers just converted over. Also
> there's an early run that's just [student] driving around with it fast.

Intended sequence: **baseline → updated auto path → +kS 0.25 → P=15 → P=5 → P=0.1 → P=0.5 →
TorqueCurrentFOC**, plus a teleop free-drive.

## What the logs are

Nine logs; two never enabled (`00-45-49`, `00-52-25`). Almost all driving was **autonomous** — a
scripted step-input routine replayed each run (commands routinely saturate 2–30× over the
~4.4 m/s max), which is good for A/B comparison. Only `00-43-41` (~10 s) and `00-56-23` (~21 s)
had teleop driving — that's where "[student] driving fast" is.

Supply-current picture is unchanged from Aug 22 (drive supply still peaks ~60 A/motor, steer to
~65 A; no new supply limit is biting — see `supply-current-analysis.md`).

## Build metadata resolves the deploy order

Every log records `/RealMetadata/BuildDate`. Tonight's nine logs came from **six distinct builds**;
in deploy order:

| Build (BuildDate) | Run(s) | Data fingerprint |
|---|---|---|
| 20:23:50 | 00-24-44 | good tune |
| 20:26:56 | 00-27-46 | good tune |
| 20:36:51 | 00-37-40 | high-P, killed at 4.6 s |
| 20:38:36 | 00-39-24 | high-P, unstable |
| 20:42:53 | 00-43-41 (+00-45-49 ∅) | recovered / low-P |
| 20:46:00 | 00-46-44, 00-52-25 ∅, 00-56-23 | clean auto + teleop (last build) |

Key consequence: **00-46-44 and 00-56-23 are the same build** → the same config → the *last* one.
That is the FOC build; 00-46-44 is its clean autonomous run and 00-56-23 its teleop/mechanisms run.
A well-converted FOC tune tracking as cleanly as voltage mode is why 00-46-44 looked so good.

## Method for reading tuning out of the logs

Per module: measured wheel speed (`SwerveStates/Measured`) vs the **desaturated** setpoint
(`SwerveStates/SetpointsOptimized`), applied volts, stator current, over enabled windows.

- **Steady tracking error** = MAE of (measured − setpoint) in a matched band (|setpoint|
  1.5–3.0 m/s, quasi-steady), as % of speed. Removes saturation/step-lag so it reflects tuning.
- **Feed-forward fit**: `V = kS·sign(ω) + kV·ω` on steady samples. kV ≈ 2.6–3.0 V/(m/s) for
  **every** run → kV feed-forward was *not* changed; the sweep was kP (+ small kS) then FOC.
- **Feedback dominance** = std of (applied V − feed-forward). High ⇒ voltage driven by *error* ⇒
  high kP or instability. (A direct kP regression fails: when tracking is good ω_meas ≈ ω_sp, so
  kV and kP are collinear.)

## Per-run results

| Log (HH-MM-SS) | Build | Enabled | Mode | Steady MAE | Feedback dom. | FF-fit R² |
|---|---|---|---|---|---|---|
| 00-24-44 | 1 | 36 s | auto | 4.9% | 1.20 V | 0.975 |
| 00-27-46 | 2 | 53 s | auto | 4.7% | 1.40 V | 0.973 |
| 00-37-40 | 3 | **4.6 s** | auto | **9.2%** | 2.42 V | 0.858 |
| 00-39-24 | 4 | 17 s | auto | 7.0% | **2.84 V** | **0.785** |
| 00-43-41 | 5 | 44 s | auto+teleop | 7.8% | 1.91 V | 0.930 |
| 00-46-44 | 6 | 53 s | auto | 5.2% | 1.15 V | 0.982 |
| 00-56-23 | 6 | 75 s | auto+teleop (mechs on) | 6.9% | 2.87 V | 0.868 |

## Run → config mapping (build order + data)

- **00-24-44 (build 1) = baseline.** *High confidence* (first build, clean tune).
- **00-27-46 (build 2) = baseline + updated auto path.** *High confidence* (second build; same
  clean tracking as build 1).
- **00-37-40 (build 3) = P=15 ("horrible").** *High confidence.* Killed after 4.6 s, worst
  tracking, feedback-dominated.
- **00-39-24 (build 4) = P=5 ("tower smash").** *High confidence.* Worst feed-forward fit,
  highest feedback action of the voltage-mode runs.
- **00-43-41 (build 5) = recovered low-P (P=0.1 or P=0.5).** *Medium.* Tracks cleaner than the
  high-P builds but not as tight as builds 1/2/6.
- **00-46-44 + 00-56-23 (build 6) = TorqueCurrentFOC (last).** *Medium-high.* Same build; 00-46-44
  is the clean auto run (tightest FF fit of the night), 00-56-23 the teleop/mechanisms run.
- Where kS=0.25 landed and whether both P=0.1 and P=0.5 were separately run isn't fully pinned —
  6 builds vs 8 listed steps, so some steps shared a build or weren't logged.

## Bottom line

Build order + tracking fingerprints together tell the story end-to-end: **P=15 and P=5 (builds 3–4)
are the clear disasters; the baseline family (builds 1–2) and the final FOC build (6) all track
cleanly at ~5%; kV never changed.** The remaining ambiguity is only *within* the good cluster
(exact kS / P=0.1 vs 0.5), because those changes are uncommitted (shared SHA) and the gain values
themselves are not logged.

**Fix for next time:** log the actual gains at boot so each run self-describes its tune —
see `claude/log-the-tune-spec.md`. The git metadata already works (SHA/branch/dirty/BuildDate),
but dirty builds share a SHA and the numbers aren't captured.
