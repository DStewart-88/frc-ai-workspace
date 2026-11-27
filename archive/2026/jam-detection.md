# Jam detection: telling a jam from an empty hopper

**Status:** watch-only detector on branch `jam-detector` (commit `773148d`, stacked on `shot-counter`). It logs only and takes no action. Offline replay: `FRC Logs/shot-counter/jam_scan.py`.

## The signatures (from logged anti-jam presses)

Anti-jam drives the feeder at full reverse, so every press marks a moment the operator saw a jam. The 2026 logs have 32 press episodes, 19 of them during shooting.

| Robot | Where it jammed | Ball-path motors just before the press |
|---|---|---|
| NECMP / CMP (old feeder + HotTub spinner) | HotTub spinner | Spinner **0 rps at ~60 A** (its stator limit). Feeder **free at ~105 rps, ~10 A**. No balls out |
| October practice (modified feeder + roller floor) | Feeder | Feeder **15–45 rps at 55–90 A**. Floor spinner free at 70–90 rps. No balls out |

An empty hopper looks different: every ball-path motor runs near its commanded speed on low current. In the no-ball sessions on Oct 9, the feeder ran at 82–90 rps and 15–24 A.

## The rule

The detector checks this every loop while the shoot command runs:

- **Starved:** the feeder gate is open and the shot counter has seen no ball for **0.6 s of feeding**. Gate flicker doesn't restart that clock.
- **Bogged stage:** a motor is below its bog speed *and* above its bog current for **0.3 s**.
  - Feeder: < 55 rps and > 25 A.
  - Spinner: < 20 rps and > 40 A.
  - The current condition keeps a dead or unpowered motor (0 rps, 0 A) from counting as a jam. That case belongs to the health monitor.
- **Jammed** = starved + a bogged stage. The stage bogged longest gets the blame. The jam **latches until a ball comes out or shooting stops**, so a motor hovering near its threshold can't flip the state between jammed and empty.
- **Empty** = starved with every stage running free.
- **Bogged alone is not a jam.** The October feeder runs bogged during normal feeding (26–50 rps at 60–78 A on Oct 8) while balls still flow. That's why the shot counter is the key input.

## How well it matches the presses

| Starve threshold | NECMP/CMP presses caught | Oct presses caught | NECMP/CMP jam episodes | Oct jam episodes |
|---|---|---|---|---|
| **0.6 s (default)** | **5/7** | **11/12** | 29 (21 s total) | 132 (266 s) |
| 1.0 s | 4/7 | 10/12 | 12 | 80 |
| 1.5 s | 0/7 | 6/12 | 3 | 62 |

- **Misses:**
  - Newton Q12: the feeder wasn't powered (0 rps, 0 A).
  - Newton Q23: the press came 0.1 s after a ball came out.
  - Oct 8 22:36 t = 176 s: the feeder wasn't powered.
  - None of the misses shows a jam signature in the data.
- **Operators are faster than a long threshold.** At NECMP/CMP they pressed within about 1–1.5 s of balls stopping, so a 1.5 s threshold misses every press.
- **Most detected jams clear by themselves.** At 0.6 s, 18 of the 29 NECMP/CMP jam episodes and 80 of the 132 October ones ended with balls coming out again within 1.5 s, without an anti-jam press. Those are real binding events that cleared themselves. That's useful for evaluating the mechanism, but **automatic anti-jam would need a longer threshold** and should probably allow one self-clear attempt first.
- **There's no ground truth beyond anti-jam presses.** Video of a session with known jams is the way to check the episodes nobody pressed for.

## What it says about the robots

- **October practice:** the feeder was jammed for 266 s out of 1,152 s of feeding (23%). Every October jam was at the feeder. This matches the pre-competition review's finding that balls bind at the floor-to-feeder handoff. `FeedPath/JamSeconds` per match is a direct measure for comparing handoff fixes.
- **NECMP/CMP:** jams were rare (21 s out of 1,741 s of feeding) and all at the HotTub spinner.

## Code

- **New files:**
  - `util/FeedJamDetector.java`: pure logic, with a `Stage` list so future robots can describe their own ball path.
  - `subsystems/FeedPathMonitor.java`: wiring, per-match counts and logging.
  - `test/.../FeedJamDetectorTest.java`: 10 tests covering flowing, empty, jams at each stage, bogged-while-flowing, latching, dead motor, gate flicker and idle.
- **Edits to existing code:**
  - `ShotCounter.shotThisLoop()`.
  - Plain-double velocity and torque-current getters on Feeder and HotTub (spinner). These aren't logged.
  - Construction in `RobotContainer` after `shotCounter`.
- **Runtime cost:** four extra signal reads per loop, and only while the feeder gate is open. About 13 `recordOutput` calls per loop.
- **Logged keys:**
  - `FeedPath/State`, `JammedStage`, `StarvedSeconds`.
  - `FeederBogged`, `SpinnerBogged`.
  - `FeederJams`, `SpinnerJams`, `JamCount`, `JamSeconds`, `EmptyCount`, `EmptySeconds`.
- **Not watched yet:** the roof and funnel motors. Each can be added as another stage with one getter pair. The intake rollers aren't watched either.
