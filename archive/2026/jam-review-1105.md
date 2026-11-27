# Jam review: Nov 5–6 practice logs (20261105 folder)

7 enabled sessions (`akit_26-11-06_00-27-20` … `20-12-28`), 506 s of shooting with the feeder gate open.

## Bottom line

> **Updated after video review: see Section 8 for the refined jam rule and corrected totals (35 jams, 34 s, 6.7% of gate-open time).** Sections 2–4 are the first pass.

- **Jams are there and they're easy to see in current.** 36 times the robot was shooting and no ball came out for ≥0.6 s while the ball path showed a jam signature. That's 48.7 s in total, about 10% of feeding time. Operators pressed anti-jam on 22 of them.
- **The best jam signal is feeder stator current, plus funnel stator current.** Floor current helps a little. Roof current and feeder *supply* current are not useful.
- **The shot counter has to be fixed first.** At its default settings it counts about 1 ball in 6 on these logs (see below), and every empty-versus-jam conclusion depends on it.

## 1. The shot counter is under-counting (fix before trusting any jam numbers)

The flywheel now sits about **+2 rps above setpoint** while holding speed. The median error with the gate open is +1.8 to +2.0 rps in all 7 logs, against −0.2 on Oct 5 and +1.3 at River Rage. `ShotDetector` rejects any dip whose peak is more than `overspeed = 2.0` rps over setpoint, because that's its braking guard. So roughly half the time it can't count anything.

| Session | Shots at overspeed = 2.0 | Shots at overspeed = 4.0 |
|---|---|---|
| 00-27-20 | 37 | 227 |
| 00-50-26 | 31 | 187 |
| 01-13-35 | 33 | 339 |
| 01-29-50 | 35 | 235 |
| 01-47-51 | 45 | 276 |
| 02-05-39 | 45 | 229 |
| 20-12-28 | 40 | 291 |

At 4.0, the detections line up one-for-one with the visible dips (`example_feeder_jam_0205.png`, 84–91 s). They also add no extra counts in the little time when the flywheel is up but the ball path has been stopped for over a second. Every number below uses overspeed = 4.0.

- **Cause:** Shooter.java hasn't changed in git since Oct 4. The gains are roboRIO preferences and aren't logged, so the likely cause is a kV/kS/kP preference change between Oct 5 and Oct 24.
- **Robot-side fix:** make the overspeed guard relative to the error just before the gate opened, or raise it to at least 8 rps (Section 7: 4 rps still drops balls that follow an overshoot). Logs from River Rage onward were also under-counted.

## 2. What a jam looks like vs an empty robot

Each starved window is measured over the part after 0.6 s with no ball. "Floor" is the HotTub spinner motor, which now drives the roller floor.

| Situation | Feeder | Feeder stator | Floor stator | Funnel stator | Roof stator |
|---|---|---|---|---|---|
| **Balls flowing** (ball within 0.3 s; 434 s of data) | 72 rps (49–82) | **43 A** (26–66) | 13 A (7–26) | **−2.6 A** (−9 to −1.5) | 7 A |
| **Jam at the feeder** | 0–35 rps | **95–124 A** (at its ~120 A stator limit) | 20–45 A | −5 to −45 A | 6–35 A |
| **Jam upstream** (feeder still turning) | 65–70 rps | 48–50 A (looks normal) | **43–55 A** | **−37 to −42 A** | ~10 A |
| **Empty** | 76–86 rps (free) | 20–40 A | 8–9 A | −2 A | 4–5 A |

Ranges in the flowing row are p10–p90. Jam rows are the medians of individual windows.

- **Funnel:** the funnel is driven at only −1.1 V and normally spins at −8.6 rps on −2 A. When balls wedge against it, it slows to about −3.5 rps (window median) and its current climbs toward −45 A. That −45 A is consistent with a stalled motor at −1.1 V. This makes it a clean, high-contrast signal. It also catches the upstream jam (`example_upstream_jam_2012.png`, 664–667 s), which feeder current misses completely.
- **Feeder supply current is a trap.** The supply limit pins it at ~60 A during heavy normal flow and during partial jams alike. At a full stall it drops to ~25 A, because low duty cycle means low supply current. Team current charts need `Feeder/Current` (stator), not `Feeder/SupplyCurrent`.

## 3. How well each current signal flags jams

Each signal is scored per starved window: did it trip, held for 0.3 s, anywhere between the last ball and the end of the window? False trips are counted per minute of *normal flowing*.

| Signal (held 0.3 s) | Anti-jam-confirmed windows caught | Self-cleared windows tripped | Stopped-shooting windows tripped | False trips per min of flow |
|---|---|---|---|---|
| Feeder stator > 80 A | 16/28 | 4/64 | 5/12 | 0.69 |
| Feeder stator > 100 A | 10/28 | 0/64 | 4/12 | 0.28 |
| Funnel stator < −15 A | 15/28 | 4/64 | 6/12 | 2.07 |
| Floor stator > 30 A | 15/28 | 3/64 | 4/12 | 1.80 |
| Roof stator > 20 A | 3/28 | 1/64 | 0/12 | 0.28 |
| Feeder supply > 55 A | 19/28 | **16/64** | 4/12 | 6.50 |
| **Feeder > 80 A OR funnel < −15 A** | **22/28** | 6/64 | **8/12** | — |

- **Detection speed:** the combined signal trips a median of **0.31 s** after the last ball (p90 0.54 s). That's sooner than the 0.6 s starve timer, so current can confirm a jam as soon as starvation is declared.
- **The 12 windows where shooting stopped without anti-jam split cleanly:**
  - 8 have a jam signature. The clearest are 01-13-35 at 221–233 s (feeder stalled at 0 rps and 120 A, three times, no press) and 02-05-39 at 62–67 s (5 s at 120 A).
  - 4 are free-running (feeder 56–86 rps, 20–54 A, funnel −2 A). Those are an empty robot, not a jam.
- **The 6 confirmed windows the rule misses:**
  - 4 are partial jams sitting just under threshold (feeder 65–79 A, floor 31–39 A, funnel −4 to −15 A).
  - 2 look free-running (feeder 76–81 rps, ~30 A). The anti-jam press there probably answered something after the window. The label is "pressed within 4 s", so it's a noisy label.

## 4. Per session

| Session | Shots | Gate-open s | Jams | Jam s | Jams with anti-jam | Other starved windows | Other starved s |
|---|---|---|---|---|---|---|---|
| 00-27-20 | 227 | 59.3 | 5 | 4.9 | 4 | 5 | 5.1 |
| 00-50-26 | 187 | 57.8 | 11 | 13.4 | 9 | 4 | 3.6 |
| 01-13-35 | 339 | 89.4 | 5 | 6.9 | 2 | 11 | 10.8 |
| 01-29-50 | 235 | 69.6 | 3 | 3.9 | 1 | 13 | 10.6 |
| 01-47-51 | 276 | 75.1 | 2 | 1.4 | 0 | 11 | 9.9 |
| 02-05-39 | 229 | 74.0 | 7 | 15.4 | 5 | 16 | 11.9 |
| 20-12-28 | 291 | 81.2 | 3 | 2.8 | 1 | 8 | 8.6 |

"Other starved" windows are mostly short gaps (median 0.7 s) where balls came back by themselves, so they're feeding hesitations rather than jams.

## 5. What this means for the on-robot `FeedJamDetector`

- **The feeder stage still works,** gated by starvation (< 55 rps and > 25 A). Requiring > 80 A instead of > 25 A would cut partial-flow ambiguity.
- **The spinner stage (< 20 rps and > 40 A) never fires on the roller floor.** The floor kept turning at 59–86 rps in every jam here.
- **Add the funnel as a stage:** current < −15 A, held 0.3 s. It's the only signal that catches upstream jams. Its threshold scales with funnel voltage, so revisit it if the −1.1 V command changes.

## Caveats

- For jams, the only ground truth is anti-jam presses. Video of 02-05-39 was used to check shot detection (Section 7) but not to label jams.
- The thresholds come from one night: 7 sessions, 104 starved windows.
- All of this depends on the shot counter running at overspeed 4.0.

## Files

- `extract.py`: caches signals from the logs into `cache/`.
- `analyze.py`: finds starved windows and writes `starved_windows.csv` and `flow_baseline.npz`.
- `score.py`: signal scoring and the per-session tally.
- `fig_summary.py` → `jam_signal_summary.png`.
- `plot_window.py LOG.npz T0 T1 OUT.png`: per-window traces. Set env `OVR=4.0` to use the fixed shot counter.
- Example figures: `example_feeder_jam_0205.png`, `example_upstream_jam_2012.png`, `example_empty_0147.png`.

## 6. BPS with and without jams: last Nov 5 session (02-05-39, match-length, 160 s enabled)

From `python3 bps_match.py cache/akit_26-11-06_02-05-39.wpilog.npz`. There were 229 shots: 192 Hub and 37 ShuttleMid.

| Measure | BPS |
|---|---|
| **Actual**, per trigger-held second (82.8 s) | **2.77** |
| **Jams removed**, per trigger-held second (82.8 − 15.4 s jammed) | **3.40** |
| Cross-check: jam-free shooting segments only (192 shots / 54.8 s) | 3.50 |
| **Ceiling**: while balls flow (bursts of 4+ shots with gaps under 0.6 s; 203 shots in 39.0 s) | **4.67** |
| CMP 2026 reference: per trigger second / flowing | 3.6 / 4.8 |

- **Cost of jams:** jams take 0.63 BPS off the per-trigger rate (−19%). The 15.4 s of jammed trigger time would have fired about 52 more balls at the jam-free rate, if the robot had them.
- **That figure undercounts the cost,** because it only counts time with the trigger held. From 61.8 s to 82.5 s, balls were stuck through three attempts. That's 21 s of match time in which the robot couldn't shoot, and about 8 s of it was spent off the trigger. A second cluster from 133 s to 148 s produced 7 balls in about 15 s.
- **Where the rest of the gap to the ceiling goes:**

| Trigger-held time | s |
|---|---|
| Balls flowing | 39.0 |
| Jammed | 15.4 |
| Starved, no jam signature (empty hopper or brief hesitations) | 12.1 |
| Gate closed (turret not on target) | 6.9 |
| Remainder (spin-up and waiting for the first ball, short bursts) | ~9.4 |

- **Jam-free, this robot is close to its CMP form.** The per-trigger rate is 3.4–3.5 against 3.6, and the flowing rate is 4.67 against 4.8. The jams are the main thing separating this session from CMP.
- **Uncertainty:** absolute counts carry about ±25% until checked against video (see the shot counter doc). The percentages above are ratios of the same count, so they don't depend on that calibration.

## 7. Shots detected in phone video (02-05-39, `PXL_20261106_020557142.mp4`)

The video is a 170 s handheld clip, 720p at 30 fps. Scripts and results are in `video/`.

**Method:**

1. Mask yellow pixels in each frame.
2. Cancel the phone's panning: track background features between frames and fit a 2-D similarity transform (shift, rotation, scale).
3. Keep the yellow blobs that moved.
4. Link the blobs into tracks. A track that rises at least 30 px at at least 6 px per frame counts as a ball leaving the robot.

The top of each arc usually leaves the frame, so a ball's falling half becomes a separate track, which isn't counted.

**Clock sync:**

- The phone filename and the robot clock disagree by about 9.4 s.
- Cross-correlating the video's rising balls against the log's shot times locks at **log time = video time + 54.71 s** (r = 0.64–0.78; about 0 at the filename estimate).
- After sync, the median timing difference between a logged shot and the video ball is **−0.01 s** (IQR ±0.05 s), so the two agree to within a frame.

**Results, with the log counter's overspeed guard at 8 rps:**

| | Count |
|---|---|
| Log shots | 251 |
| Video rising balls | 226 |
| Matched within ±0.25 s | 168 |
| Video balls outside any shooting period (false detections) | 12 |

**Where the video can't see:**

- Video 27.5–36.9 s: the robot is at the far end and the balls are too small for the detector.
- Video 61.6–67.3 s: the camera is swinging.
- Video 146.5–153.5 s: the robot is far away, behind the posts.

In the segments with a good view, the log has 178 shots, the video 192, and 148 match.

**Checked frame by frame at 30 fps:**

| Video window | Balls by eye | Video tracker | Log counter |
|---|---|---|---|
| 94.0–95.6 s | 9 | 9 (all correct) | 6 (overspeed 4) |
| 72.0–73.6 s | 8 | 8 (all correct) | 6 (overspeed 8) |

Where the robot is in clear view, the video tracker is the more accurate counter. **The log counter is undercounting by about 25–30%** even after the overspeed fix. There are two causes:

1. **The overspeed guard.** After each ball, the velocity loop overshoots to +4.5–5.7 rps. The next ball's dip then starts from a peak above the guard and is rejected. This is what caused the 94.91, 95.17 and 95.33 s misses. A guard of 8 rps or more, or a guard measured from the pre-shot baseline, fixes it.
2. **Sample rate.** `Shooter/Velocity` is logged every 33 ms on average (p90 63 ms) because the loop overruns, and a ball's dip lasts about 40 ms. Some dips fall entirely between samples. Fixing the loop overruns, or counting inside a faster callback (for example a Phoenix status-signal callback at 100+ Hz), would recover these.

**Effect on Section 6:** the BPS numbers there are probably 25–30% low in absolute terms. The jam cost (−19%) and the comparison with the ceiling are ratios of the same counter, so they still hold.

## 8. Jam rule refined with the video (02-05-39 labelled, then checked on all 7 sessions)

### What the video showed in each starved window

I recomputed starved windows using every ball either source saw: the log counter at overspeed 8, plus video balls where the robot is in view.

- **9 of the 23 starved windows from Sections 2–4 weren't starved.** The video shows 2–5 balls leaving the robot inside each one; the counter just missed them.
- **16 windows remain, 11 of them in good view.** I labelled those from the video:

| Video label | Windows (video s) | Feeder | Funnel |
|---|---|---|---|
| **Jam**: hopper visibly full, nothing comes out | 7 windows (7.1–12.2, 16.5–26.6, 79.7–85.8) | 0–27 rps, 102–123 A | −7 to −44 A |
| **Supply hesitation**: hopper full, feeder spinning free, ~0.7 s pause | 1 (44.0) | 69 rps, 59 A | −2 A |
| **Not starved**: balls flowing every 0.2–0.3 s, both counters missed (robot very close to camera) | 2 (109.8, 114.5) | 69–78 rps, 43–64 A | −4 A |
| Unclear (robot far away) | 1 (90.1) | 73 rps, 51 A | −11 A |

- **The hopper was never empty** in any window I could see. A free-running starved window means balls aren't reaching the feeder (a supply hesitation or a counting miss), not that the robot ran dry. The `EMPTY` state should be renamed `SUPPLY_GAP`.
- **The real gaps between balls during flow** (log plus video, good view) are 0.16 s median, 0.37 s p95 and **0.67 s p99**, and never over 1.0 s. A 0.6 s starve timer sits inside normal flow, which is why counter misses turned into false starves.
- **Bogs during normal flow are brief, and jams are long.** In good view, the feeder bogged (above 80 A and below 50 rps) for **at most 0.12 s** at a time and the funnel stalled below −15 A for at most 0.18 s. In the confirmed jams, the longest bog was 0.3–5 s.

### Rules compared

Ground truth across all 7 sessions is the 24 anti-jam presses made during shooting, plus the video labels on 02-05-39.

| Rule (all held 0.3 s, latched until a ball or shooting stops) | Anti-jam presses flagged | Median lead before press | Flags while balls still flowing | Video jams flagged / false flags |
|---|---|---|---|---|
| Original: starve 0.6 s + (feeder > 80 A or funnel < −15 A), counter overspeed 4 | 15/24 | 3.0 s | 0 | 6/6, 0 |
| Starve 0.6 s + loose bog, counter overspeed 8 | 14/24 | 2.6 s | 0 | 6/6, 0 |
| Current only, loose (feeder > 80 A and < 50 rps, or funnel < −15 A) | **19/24** | 2.3 s | **10** | 6/6, 0 |
| Current only, strict (feeder > 100 A and < 35 rps, or funnel < −25 A) | 16/24 | 2.8 s | 1 | 6/6, 0 |
| **Hybrid: strict alone, OR loose + starve 0.6 s** | **18/24** | **2.8 s** | **1** | **6/6, 0** |

- **Recommended rule: the hybrid.**
  - A clear jam is flagged from current alone, so it doesn't wait on the shot counter, which still misses 25–30% of balls.
  - A borderline signature (a labouring feeder, a funnel dip) needs the counter to confirm starvation as well.
- **The 6 presses it misses:**
  - 2 were pressed with the gate already closed.
  - 4 came 0.1–1.6 s after the last ball, during a partial bog (feeder 50–69 rps, 32–76 A median), which may have been a pre-emptive press.
- **Applying it:** `jam_rule_hybrid.py` finds 35 jams totalling 34 s, **6.7% of gate-open time**. 00-50-26 and 02-05-39 are the worst sessions at 16–17% each; 01-47-51 is almost clean at 0.4%.
  - That replaces the earlier 36 jams / 48.7 s from Section 4. The earlier figure counted from the last ball, while this one counts from when the rule fires, which is about 0.3–0.6 s later.

### Changes for the robot's `FeedJamDetector`

1. **Feeder stage:** bog = stator > 80 A **and** velocity < 50 rps. Mark it "strict" when > 100 A and < 35 rps.
2. **Funnel stage** (new): loose < −15 A, strict < −25 A.
3. **Logic:** a strict stage held 0.3 s → JAMMED immediately. A loose stage held 0.3 s → JAMMED only if starved (0.6 s with no ball). Keep the latch.
4. **Shot counter:** overspeed guard ≥ 8 rps (Section 7).
5. **Rename `EMPTY` to `SUPPLY_GAP`,** and only report it after **1.0 s** starved with every stage free (above the 0.67 s p99 real gap).
6. **Drop the spinner/floor stage.** The floor never bogged below 59 rps in any jam.

### Caveats

- One match was labelled with video, and the rule is perfect on it (6/6 jams, no false flags). Its labels can't separate the candidate rules, though: every rule scored 6/6 there. The choice between them rests on the anti-jam presses across all 7 sessions.
- The 1 mid-flow flag, and the flags with no anti-jam press, come from sessions with no video. Many of the unpressed ones look like real jams that cleared themselves.

## 9. Shot detector tuned against the video

### Ground truth

- **The balls:** video rising-ball tracks in four stretches where the robot is mid-range and fully in view (video 5.5–12.5, 42–47.2, 67–73.5 and 93.7–98 s). Bounces near the hub are removed: tracks that start low in the frame and rise under 100 px. That leaves **79 balls**.
- **Negatives:** the video-confirmed jams, with the flywheel at speed and no ball able to leave.
- **Matching:** one-to-one within ±0.15 s.

### Results

| Detector | Recall | Precision | False counts/s in jams | Total counted vs true |
|---|---|---|---|---|
| `ShotDetector` defaults (overspeed 2) | 0.05 | 1.00 | 0 | −95% |
| Overspeed 8 only | 0.80 | 0.90 | 0 | −11% |
| **Tuned: dip 0.75, below 0, overspeed 8, lockout 0.08, window 0.10, rearm 0.75** | **0.89** | **0.90** | **0** | **−3%** |
| Shooter stator-current rise (main + follower ≥ 40 A over 0.12 s) | 0.85 | 0.83 | 0 | +1% |
| Velocity OR current | 0.89 | 0.82 | 0 | +6% |
| Dip in raw speed (setpoint ignored) | 0.87 | 0.78–0.84 | 0.5–1.3 | ≈0% |

**Is the signal there?** Mostly. The flywheel velocity as logged carries about 90% of the balls, and the tuned detector gets the total right to within a few percent.

- **Current adds nothing new.** It sees the same balls velocity sees (before bounce filtering: 64 of 84 seen by both, only 3 more by either), so it doesn't fill the gaps.
- **Position can't be used.** `Shooter/Position` differenced over the log timestamps is too noisy, because position is stamped at loop time, not at the time its CAN frame was measured.

**The remaining ~10% of balls aren't in the logged data:**

1. **Balls under 0.1 s apart.** Two balls reaching the flywheel that close together merge into one dip. This is 6 of the 9 misses.
2. **Loop stalls.** Velocity is logged every 39 ms median, and 19% of gaps are over 60 ms (up to 148 ms). Detection is 92% when the sample gap is under 45 ms and 82% when it's over 70 ms.

### Recommendations

- **New `ShotDetector.Config` defaults:**
  - dip 1.5 → **0.75**
  - below 0.75 → **0**
  - overspeed 2.0 → **8.0**
  - lockout 0.10 → **0.08**
  - window 0.20 → **0.10**
  - rearm stays **0.75**

  On the 7 sessions this counts 5–9% more than overspeed 8 alone, consistently. In the trusted view, all 22 counts made during fast setpoint changes were real balls.
- **To recover the last ~10%, sample the flywheel faster.** Raise the shooter velocity status-signal update frequency (e.g. 200–250 Hz) and run the detector in a fast thread off timestamped samples, like the drive odometry thread already does. That removes both the loop-overrun dependence and most of the merged-dip problem. Fixing the loop overruns helps too.
- **BPS:** with the tuned settings, 02-05-39 has **270 shots** instead of the 229 used in Section 6, so those BPS figures rise about 18%. The jam-cost ratio is unchanged.

### Caveats

- One match and 79 balls.
- The negatives are only the jam periods (flywheel at speed, robot mostly stationary).
- A fixed, closer side-on camera at 60–240 fps would give a cleaner check, especially for closely spaced pairs.

## 10. The team's jam detector (BaseComp `7d466e1`, Nov 6) replayed on these logs

**What it does:** `Trigger(feeder supply current > 55 A).debounce(0.5 s, rising).onTrue(antiJam().withTimeout(0.5) + rumble)`.

`antiJam()` does three things:
- stops the shooter flywheel
- sets `shooting = false`
- reverses the feeder (−100%), HotTub and intake

It requires the shooter, feeder and HotTub subsystems, so it **cancels `shoot()`**. Because `shoot()` is bound `onTrue`, the driver has to release and re-press the trigger to resume, and the flywheel spins up from zero.

All 7 logs predate the commit (it landed Nov 6 at 15:31), so this is an offline replay. "Balls still flowing" uses the tuned shot counter (Section 9).

| Trigger (all gated to shooting except the team's) | Fires | While balls still flowing | Video-confirmed jams caught (02-05-39) | Anti-jam presses preceded by a fire | Hybrid jams ≥ 0.5 s caught |
|---|---|---|---|---|---|
| **Team: supply > 55 A, 0.5 s** | 39 (36 while shooting) | **13** | **2/6** | 15–17/24 | 7/16 |
| A: (stator > 100 A and < 35 rps) or funnel < −25 A, 0.3 s | 43 | **0** | **6/6** | 15/24 | 16/16* |
| B: (stator > 80 A and < 50 rps) or funnel < −25 A, 0.3 s | 47 | 4 | 6/6 | 17/24 | 16/16* |
| Stator > 100 A and < 35 rps only, 0.3 s | 24 | 0 | — | 9/24 | 10/16 |

\* A and B share conditions with the hybrid rule, so this column is partly circular for them. The other columns are independent.

### Why supply current is the wrong signal here

| | Feeder speed | Stator current | Supply current | Time with supply > 55 A |
|---|---|---|---|---|
| Normal flow (02-05-39) | 68 rps | 47 A | 46 A | **28%** |
| Video jam 1 (62–67 s) | 17 rps | 116 A | 49 A | 22% |
| Video jam 2 (71–76 s, full stall) | 0 rps | 120 A | **23 A** | **1%** |
| Video jam cluster (134–140 s) | 32 rps | 97 A | 59 A | 71% |

- **A full stall drops supply current to about 23 A.** Low duty cycle means low supply draw, so the trigger never sees the worst jams. It missed both 5 s jams in the video match.
- **A labouring feeder pins supply at its 60 A limit,** whether a ball is binding or the feeder is just pushing a heavy stream. That's why the trigger lines up with many operator presses but also fires during normal flow.
- **One false fire was confirmed on video:** log 126.5 s (video 71.8 s), where balls were visibly streaming out.

### Suggested changes, keeping the team's structure

1. **Change the trigger condition:**
   ```java
   new Trigger(() -> isShooting()
           && ((feeder.getStatorAmps() > 100.0 && feeder.getRps() < 35.0)
               || hotTub.getFunnelStatorAmps() < -25.0))
       .debounce(0.3, Debouncer.DebounceType.kRising)
   ```
   The getter names are placeholders: they'd be public wrappers around the existing `getCurrent()`/`getVelocity()` in Feeder and the funnel current in HotTub. Stator current, torque current and velocity are already enabled at 50/100 Hz, so this adds no CAN traffic.
2. **Gate it to shooting.** The current trigger also fired twice while not shooting, and once during a manual anti-jam (the manual reverse at −100% draws high supply current).
3. **Resume shooting automatically after the anti-jam.** Something like `antiJam().withTimeout(0.5).andThen(shoot().onlyIf(controller.rightTrigger()))`.
4. **Consider leaving the flywheel spinning during the reverse,** if stopping it wasn't deliberate. That avoids a cold spin-up after every auto anti-jam.
5. **Rumble on detection is a good idea.** Keep it, so drivers learn what the robot thinks is a jam.

## 11. Checking the PR trigger on earlier logs (Oct 24 – Nov 2)

The PR trigger is `isShooting() && (feeder torque > 100 A && feeder < 35 rps || |funnel torque| > 25 A)`, held 0.3 s. It was replayed on every log from the four stretches before Nov 5, all with the roller floor and modified feeder.

Each firing is labelled by what the robot did next with no anti-jam:
- **Stuck:** no ball for at least 1 s. This is a real jam.
- **Mid-stream:** a ball in the 0.6 s before and another within 0.4 s after. The robot wasn't stuck, so this is a false fire.
- **In-between:** anything else.

Balls come from the tuned shot counter, which misses about 10%. Scripts: `extract_to.py` → `cache_prior/`, `replay_rules.py`.

| Logs | Funnel setting (`Spinner/FunnelSpeed` pref) | Shooting | Anti-jam presses | PR fires: stuck / mid-stream / in-between (auto) | Signed funnel (< −25 A): stuck / mid / between (auto) | Team supply trigger: fires (mid-stream) |
|---|---|---|---|---|---|---|
| Nov 5–6 (7) | reverse, −1.1 V | 545 s | 24 | 43: 35 / 2 / 6 (3) | same | 39 (12) |
| Nov 2 practice (5) | reverse | 332 s | 6 | 1: 1 / 0 / 0 | same | 11 (7) |
| Oct 30 drive practice (26 logs, 6 shooting) | reverse | 350 s | 0 | 4: 3 / 0 / 1 | same | 4 (1) |
| Oct 29 (10 logs, 6 shooting) | **forward, then reverse mid-evening** | 304 s | 5 | 31: 17 / 8 / 6 | 19: 9 / 4 / 6 | 20 (5) |
| River Rage, Oct 24 (16 logs, 13 matches shooting) | **forward, +1.1 V** | 638 s | 0 | **14: 4 / 5 / 5 (4 in auto)** | **1: 1 / 0 / 0** | 7 (0) |

### Findings

- **The feeder half is solid everywhere.** On its own it fired once each at River Rage, on Oct 30 and on Nov 2, each time on a real stall. Most of its Oct 29 fires fall in that night's long jam (00-41-01, 360–450 s, feeder at 5–21 rps and 115–123 A).
  - A few of those fires are labelled "mid-stream" even though the feeder was nearly stopped. That's likely the shot counter misreading, not real balls.
- **The funnel half depends on the funnel's direction,** which is a roboRIO preference (`Spinner/FunnelSpeed`), not code. HotTub.java is unchanged since Oct 20.
  - **Run in reverse** (late Oct 29 onward): a funnel stall means balls are wedged, and it's a good jam signal.
  - **Run forward** (River Rage, early Oct 29): the funnel regularly stalls against the ball pile (0–2 rps, 26–44 A) while the feeder keeps feeding at 42–71 rps. That isn't a jam.
  - **At River Rage the PR as written** would have fired 14 times, 5 of them mid-stream and 4 in auto. Each auto fire cancels the whole auto routine.
- **Use the signed check, not `Math.abs`.** I suggested |current| so the check would survive a direction flip. The data says the opposite: a forward stall is normal behaviour. `funnelTorque < -25 A` switches itself off when the funnel runs forward (its stall current is then positive). It gives identical results on every reverse-funnel day and drops River Rage to 1 fire (a real stall, not in auto).
- **Nov 2's 6 presses were mostly supply gaps, not stalls.** The feeder ran freely at 67–82 rps and 17–51 A, and the funnel stayed at −2 to −12 A.
  - The roller floor was at about 40 A against a normal-flow median of 14 A, but normal flow reaches 44 A at its 95th percentile. Floor current can't separate these cases.
  - Only the shot counter's starve check (the hybrid rule's loose path / `SUPPLY_GAP`) could flag them.
- **The team's supply trigger** fired mid-stream 7 times out of 11 on Nov 2 and 12 out of 39 on Nov 5–6. That matches the earlier finding.

## 12. Correction: the team's auto anti-jam was already running on Nov 6 (20-12-28)

- **What the deploy metadata shows:**
  - The Nov 5 sessions ran `d80f69c`, the last two with uncommitted changes.
  - The Nov 6 afternoon session (20-12-28) ran `9effb1e` **with uncommitted changes**.
  - The committed code before `7d466e1` reverses the feeder only from button-box button 9. That's `Joystick1` bit 8, which AdvantageKit logs.
- **20-12-28 had 6 feeder reverses with button 9 not held.** They lasted 0.4–0.6 s (the 0.5 s timeout), and 5 of the 6 followed supply > 55 A for 0.5 s. That's the team's automatic trigger. All of them were in teleop: **the robot was never enabled in auto in that session**, so no log shows the trigger firing in auto.
  - **What each automatic fire did:**
    - shooting was cancelled immediately
    - the flywheel dropped to 0–12 rps
    - the driver re-pressed after 0.9–1.1 s
    - the next ball came 1.1–1.7 s after the fire
  - **3 were real feeder bogs** (26–30 rps, 97–101 A). **3 came with balls still flowing** (45–57 rps, 66–74 A); the PR rule wouldn't fire on those.
- **Earlier sections counted these 6 as operator presses.** With only real button presses there are **19, not 24.** Against those 19:
  - The team trigger fired beforehand on **13/19**. The earlier 15–17/24 included its own fires.
  - The PR trigger (with the funnel fix) fired beforehand on **12/19**.
  - The other comparisons (fires while balls flow, video-confirmed jams, River Rage) didn't use presses and are unchanged.

### PR update (`anti-jam-trigger`, commit `0be4b45`)

`HotTub.isFunnelJammed()` now requires `funnel MotorVoltage < 0` (running in reverse) as well as `|torque current| > 25 A`. Replayed results are identical on all reverse-funnel days, and River Rage drops from 14 fires to 1.

**Open issue:** whenever the trigger fires during auto, `antiJam()` takes the shooter, feeder and HotTub away from the PathPlanner auto, which **cancels the whole auto routine**.
- On the Nov 5–6 logs the PR would have fired in auto 3 times, in 2 sessions:
  - In 02-05-39 it was a real jam; the rest of that auto shot 1 ball anyway.
  - In 01-47-51 it was a bog that cleared itself; the robot went on to shoot 18 more balls in that auto.
- **Options:**
  - Gate the trigger to teleop.
  - Move the reverse into the feeder/HotTub run commands, so nothing gets cancelled and shooting resumes automatically.
- **Resolved:** commit `5aed412` gates the trigger with `DriverStation.isTeleopEnabled()`. Jams in auto stay unhandled until teleop or a manual anti-jam, which is the behaviour from before automatic anti-jam existed. `IsJammed` and `IsFunnelJammed` are still logged in auto. The in-command approach remains the longer-term option.
