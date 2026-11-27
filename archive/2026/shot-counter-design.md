# Shot counter: design, validation and 2026 season numbers

**What this is:** a way to count every ball the shooter fires, sort each one into scoring (Hub) or shuttling, and turn that into balls-per-second (BPS). It works from logged data only: no new sensors and no change to how the robot behaves. It comes in two forms that use the same detection logic:

- **Robot code**: `ShotCounter` (subsystem) + `ShotDetector` (pure logic, unit-tested). It logs live counts and BPS under `ShotCounter/...` every match.
- **Offline tool**: `shot_counter.py` runs the same detection on any `.wpilog`, so old logs (the whole 2026 season) can be counted and settings tuned before changing robot code.

Files live in `FRC Logs/shot-counter/`: `robot-code/shot-counter.patch` applies cleanly to BaseComp (checked against the working tree on 2026-10-13); `season-2026-shot-counts.csv` has the per-match results.

---

## The signal: flywheel speed, not voltage

Each ball pulls energy out of the flywheel, so its measured speed drops **about 6 rps (motor shaft) in roughly 40 ms** and the velocity loop brings it back within about 0.1 s. Across 7,360 counted dips at NECMP and CMP, the median depth is 6.5 rps (10th percentile 3.6 rps). The counting threshold is 1.5 rps, so most dips clear it easily.

Voltage is the wrong signal. When a ball slows the flywheel, the velocity loop *raises* the voltage to pull it back up, and a lot of that reaction is clipped once the main motor hits its 60 A stator limit. Current spikes too, but only about 70–77% of speed dips line up with a current spike. Speed is the cleanest signal.

## How Shooting vs Shuttling is decided (already in the code)

`TrajectorySolver.findTargetPosition()` picks the target every loop from the turret's field position (alliance-flipped):

| Turret position | Target | `IsTargetingHub` | `isFullField` | Shooter setpoint |
|---|---|---|---|---|
| Inside our alliance zone (x ≤ 181.56 in) | Hub | true | false | lookup `25.7 + 3.86·d` (~35–50 rps) |
| Neutral zone | One of 4 shuttle targets, by y | false | false | same lookup, distance to shuttle target |
| Opponent's alliance zone | Shuttle target | false | **true** | **fixed 100 rps** |
| Pre-aim button held (button box 1) | Hub (forced) | true | – | lookup |

The counter files each ball by what the solver was aiming at **when the ball left**: **Hub**, **ShuttleMid** or **ShuttleFull**. ShuttleFull is split out because 100 rps is above what the flywheel can reach (it settles at 60–70 rps while feeding). Those shots behave differently from the others.

The split depends on the pose estimate, so a ball fired right on a zone line can land in the wrong bucket. As expected, balls moved by pushing or by reversing the intake are invisible to this method.

## How a ball is counted

Every loop, `ShotDetector.update()`:

1. **Arms** only while the shoot command is running, the feeder gate (`onTargetRobot()`) is open (or closed for less than 0.3 s, since balls already in the path still come out), and the flywheel is above 10 rps.
2. Watches **tracking error = speed − setpoint**, not raw speed. The setpoint moves as the robot drives (about 8 rps/s at 2 m/s toward the hub), and subtracting it keeps that motion from looking like a ball.
3. Counts a ball when the error falls **≥ 1.5 rps below its peak over the last 0.2 s**, the speed is now at least 0.75 rps *under* setpoint, the peak wasn't more than 2 rps *over* setpoint, and the last ball was at least **0.10 s** ago. The two setpoint rules reject a flywheel that is slowing back down after its setpoint dropped. That looks like a dip but isn't a ball.
4. After counting, waits for the error to recover 0.75 rps before another ball can count, so one long sag counts once.

![Detection example](shot-detection-example.png)

## Does it count balls correctly?

There's no ground truth (no ball sensor and no video yet), so the checks come from several angles:

| Check | Result |
|---|---|
| **No balls → no counts.** Oct 8–9 practice sessions where the feeder ran with no balls (10–19 s of gate time each) | 0–1 counts per session in 10.6–18.7 s of gate time (≈ 0.05 false counts/s while armed and empty) |
| **Close-together dips are real balls, not one ball counted twice.** Dips <0.15 s from a neighbor vs isolated dips | Same median depth: 6.4 vs 6.4 rps (hub, 3,570 vs 1,362 dips). Two halves of one ball would each be shallower |
| **Timing matches FMS.** Hub shots by match period, 12 NECMP quals | 97% fall in our hub's active shifts. The 74 in inactive shifts sit at shift edges, where the code deliberately starts feeding early |
| **Never far above what the alliance scored.** Our counted hub shots vs alliance fuel (FMS), 12 NECMP quals | Auto 52%, teleop 63% of alliance fuel. One match (Q19) counted 93 teleop shots vs 71 alliance fuel, possible only with misses and weak partners |
| **Sensitivity to settings** (28 matches) | Dip 1.0 / 3.0 rps: +3% / −10%. **Lockout 0.15 / 0.20 s: −13% / −26%**. Rearm 2.0: −3%. No hangover after the gate closes: −7% |
| **Robot code = offline tool** | Java `ShotDetector` and `shot_counter.py` give identical shots on 3 full matches (fed full-precision log data) |

**Bottom line:** comparisons between matches, events, settings or robot versions are solid. **The absolute count carries about ±25% uncertainty** until it's checked against video. The lockout (the minimum time between counted balls) moves the count most: **38% of the gaps between consecutive counted balls are 0.10–0.14 s**. Those are either balls arriving in close pairs (the dip-depth check favors this) or one ball counted twice. Video settles which.

Two known biases pull in opposite directions:

- **Possible overcount:** some of the 0.10–0.14 s gaps could be one ball counted twice.
- **Undercount from loop overruns:** in the 2026 logs and the October practice logs, 13–17% of robot time is spent in loops longer than 80 ms (median loop 24–26 ms vs the 20 ms target). The counter only sees one speed sample per loop, so a 0.1 s dip can fall inside a long loop and be missed.

### Calibrating it (one practice session)

1. Film the shooter in slow motion (240 fps phone video is plenty) during 3–4 full hopper dumps at the hub, plus one shuttle dump.
2. Count balls per dump from the video, and note each dump's start time from the robot's match/enable clock.
3. Compare with `ShotCounter/Hub/Total` (or run `shot_counter.py` on that log).
4. If the counter reads high, raise `ShotCounter/LockoutSec` (a preference, editable from the dashboard) until it matches. If it reads low, look at loop timing first.

## 2026 season numbers (28 matches: NECMP Newsom quals + elims, CMP Newton quals)

March events (North Shore, Greater Boston) can't be counted: those logs don't have `OnTargetRobot`, `IsShooting` or `IsTargetingHub`.

| | Auto / match | Teleop / match | BPS per feed-gate second | BPS per trigger second | BPS while flowing (median) |
|---|---|---|---|---|---|
| **Hub** | 39 | 179 | 4.2 | 3.6 | **4.8** (match range 4.3–5.0) |
| **ShuttleMid** | 1 | 36 | 4.3 | 3.6 | 5.0 |
| **ShuttleFull** | 0 | ~40 in the 5 Newton matches that used it | 4.8 | 4.6 | 5.2 |

**Which BPS to use in strategy:**

- **BPS while flowing ≈ 4.8** is the shooter's rate once balls are moving: shots inside bursts (gaps under 0.6 s) divided by burst time. This is the number teams usually mean by BPS.
- **Per trigger second ≈ 3.6** is what you get per second of holding the shoot button. It includes spin-up (~0.2 s from cold, since the flywheel coasts to zero between bursts), turret settling, hub-inactive gating and an empty hopper. For planning ("how long to empty a full hopper"), use this one.
- The gap between them (≈ 1.2 BPS) is time spent with the trigger held and nothing coming out. For hub shooting, the average match had 61 s of trigger time:

| Trigger-held time, hub mode (28-match average) | s / match | Share |
|---|---|---|
| Balls flowing (gaps under 0.6 s between counted balls) | 41.8 | 68% |
| Feeder on, waiting for the first ball (flywheel spin-up from cold + ball travel) | 6.9 | 11% |
| Feeder on, no balls coming (empty hopper or jam) | 6.1 | 10% |
| Feeder held off, turret not on target | 5.6 | 9% |
| Feeder held off, turret on target (hub-inactive timing, debounce) | 0.7 | 1% |

  Per-match BPS per trigger second ranged 2.4–4.3 (median 3.6). Idling the flywheel instead of coasting to zero would recover part of the waiting-for-first-ball time. Spin-up is about 0.18 s of each roughly 0.35 s wait, at ~19 shooting windows per match, so up to about 3 s per match.
- These are **shots**, not scored balls. The counter can't see misses, so "how fast they actually score" also needs an accuracy figure from scouting or video.

October practice (roller floor, Oct 5) came out at 4.1–4.6 BPS flowing, slightly below the CMP numbers. Practice has more stop-start, so this isn't a like-for-like comparison yet.

## Code structure and impact on the rest of the robot

```
RobotContainer
 ├─ shooter::getVelocity ─────────────┐
 ├─ trajectorySolver::getShootSpeed ──┤
 ├─ this::isShooting ─────────────────┤
 ├─ this::onTargetRobot ──────────────┼──▶ ShotCounter (SubsystemBase, periodic only)
 ├─ trajectorySolver::getIsTargetingHub┤      └─ ShotDetector (plain Java, no WPILib)
 ├─ trajectorySolver::getIsFullField ─┤      └─ Logger.recordOutput("ShotCounter/...")
 └─ dashboard::getIsHubActive ────────┘
Robot.autonomousInit / teleopInit ──▶ shotCounter.onModeStart()  (match reset)
```

**Changes to existing files (27 lines added, 1 changed):**

- `Shooter.java`: `getVelocity()` goes from `private` to `public`. Its log key `Shooter/Velocity` is unchanged.
- `TrajectorySolver.java`: new `getIsFullField()` getter, also `@AutoLogOutput`, so future logs record the full-field flag directly.
- `RobotContainer.java`: constructs `ShotCounter` after the shooter, plus one pass-through method.
- `Robot.java`: one line each in `autonomousInit()` and `teleopInit()` to reset counts at match start.

**New files:** `subsystems/ShotCounter.java`, `util/ShotDetector.java`, `test/.../ShotDetectorTest.java` (7 tests, run with `./gradlew test`). The tests pass against the real ShotDetector. ShotCounter was compile-checked against stand-ins for the WPILib/AdvantageKit classes, because GradleRIO couldn't be downloaded here. **Run `./gradlew build` once before deploying.**

**Runtime impact:**

- **It can't affect robot behavior.** No motors, no commands, nothing requires it. It only reads values.
- **CAN bus:** no new signals. It reads the shooter velocity signal the code already reads every loop. That costs one extra non-blocking refresh, the same call AutoLog already makes.
- **CPU / memory:** a few dozen arithmetic operations and a 32-slot fixed array per loop. It allocates nothing per loop (log keys are built once), so it adds nothing to garbage collection, which is already logged as `LoggedRobot/GCTimeMS`.
- **Logging:** about 30 new values per loop. AdvantageKit writes them to the file only when they change, and most counts change a few times per second at most.
- **Order:** it must be constructed after `TrajectorySolver` and `Shooter`, so its `periodic()` sees this loop's setpoint. The patch places it there.
- **`onTargetRobot()` is called once more per loop.** The method's own comment says repeat calls are harmless, since its debouncer is time-based.

**What gets logged** (live in AdvantageScope/Elastic through NT, and in the log file):
`ShotCounter/Shot` (true on the loop a ball is detected), `ShotCounter/{Hub,ShuttleMid,ShuttleFull}/{Auto,Teleop,Total,FeedSeconds,TriggerSeconds,BPSFeed,BPSTrigger,BPSFlow}`, `ShotCounter/Total`, `ShotCounter/HubWhileInactive`, `ShotCounter/SinceBoot`, plus tuning aids `ShotCounter/TrackingError`, `Armed` and `LastDipDepth`.

**Resets:** counts reset at autonomous start, at a teleop start not preceded by auto within 10 s (practice), and from the `ShotCounter/Reset` dashboard button. `SinceBoot` ignores match resets, so it can feed the component-usage tracker's shooter-wheel wear count once that tracker persists values.

## Side findings

- **Full-field shuttles are commanded to an unreachable 100 rps.** The flywheel settles at 60–70 rps while feeding and stays at maximum effort the whole time. Shuttle distance is therefore set by whatever speed it reaches, not by the lookup. A reachable setpoint (or a real full-field lookup) would make those shuttles repeatable.
- **The feeder starts with the flywheel still spinning up, but that isn't costing hub shots.** 97% of counted hub balls left with the flywheel at ≥ 90% of its target (judged from the speed just before each dip), because balls take time to travel to the shooter. Shuttles are 71%, mostly because of the unreachable full-field setpoint.
- **Loop overruns limit how well this method can work.** A future version could run the detector in a 100 Hz thread fed straight from the velocity signal, like the drive odometry thread. Only worth doing if video calibration shows a real undercount.

## Possible uses

- BPS (flowing and per-trigger-second) for pre-match strategy, per event and per robot version.
- Hub shots vs FMS alliance fuel per period, as a ceiling on accuracy. True accuracy needs partner contributions from scouting.
- Hub shots fired while our hub is inactive (`HubWhileInactive`), which score nothing.
- Time with the trigger held but nothing coming out (TriggerSeconds vs flow), for spotting empty hopper and spin-up time.
- Shooter-wheel wear: count ball contacts instead of flywheel revolutions, through the component-usage tracker.
