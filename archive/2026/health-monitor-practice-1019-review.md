# Health monitor on the robot: Oct 19 2026 practice review

**Question:** the health monitor (PR #50, merged into BaseComp as `fc868cc`) ran on the robot for the first time at practice on Oct 19. Did it behave the way it was designed and tuned (see `claude/health-monitor-handoff.md` and `claude/health-monitor-nerd-replay.md`)? Should anything change before moving on?

## Logs

Logs are in `FRC Logs/2026 Logs/Practice20261019`. An identical copy (same checksums) is in `4-11/Practice20261019`. File names are in UTC; practice ran about 18:17–21:00 EDT.

| Log | Build | Notes |
|---|---|---|
| 22-17-19 | `51350d2` (Oct 10, no monitor) | 23 min, driven |
| 22-48-32 | `51350d2` | 2 min, never enabled |
| 22-49-20 | **`fc868cc`** (monitor) | 1 enable, 291 s |
| 23-02-12 | `fc868cc` | 2 enables (272 s, 162 s) |
| 00-12-59 | `fc868cc` | 4 enables, incl. one practice match |
| 00-33-54 | `fc868cc` | 2 enables = one practice match |
| 00-48-16 | `fc868cc` | 3 enables = one practice match + one teleop-only run |

- Both builds are flagged "Uncommitted changes", so the exact deployed code isn't known.
- The FMS was never attached, so every enable ran as `PER_ENABLE`.
- Three sessions were Driver Station practice matches: 20 s auto, ~3.5 s disabled gap, 140 s teleop.

**Method.** The monitor logs its own state (`Health/*`, 47 keys). Its output was compared with sources the monitor doesn't use:
- device presence: the subsystems' `IsHealthy` and `Shooter/IsMainConnected` flags;
- power: `SystemStats`;
- device activity: whether each motor's data kept arriving.

The scripts are in `FRC Logs/health-practice-1019/`:
- `extract.py` turns each `.wpilog` into a small `.pkl`;
- `lifecycle.py`, `faults.py`, `drops.py`, `canerr.py`, `timing.py`, `persist.py` and the others analyze those extracts;
- `silence.py`, `pivotcheck.py`, `pivmotion.py` and `pivbase.py` read the raw logs directly.

## What worked as designed

| Piece | Designed to | Observed |
|---|---|---|
| Presence faults (13 roboRIO-bus devices) | Catch real dropouts; ignore 20–40 ms blips (0.1 s debounce) | **Every** latched episode matches the independent `IsHealthy` flags. No false positives found. |
| Drive modules and gyro | Stay quiet unless the CANivore has trouble | Never fired. The CANivore was healthy all day. |
| `Power/Brownout` as a warning | Never force ERROR by itself | Fired 13–133 times per run (batteries were run until dead). It never set the display to ERROR. |
| `Power/BatterySag` | Warning | Fired 7–47 times per run |
| `CAN/HighUtilization` at 85% for 2 s | Stay off on the fixed bus | Never fired. **But see "CAN utilization readings" below: as written it may be unable to fire at all.** |
| 2 s startup grace | Ignore boot-time absence | Worked |
| Cameras while disabled (open question in the handoff) | Not read disconnected because of throttle=150 | **Answered: no false disconnects while disabled.** After boot the Limelights read disconnected for 5–16 s in one log; they start up more slowly than robot code. That was dashboard-only and never latched. There was one 0.1–0.3 s drop of all three cameras while enabled (23:02 log, t=1444 s), recorded as a warning. |
| End-of-run display | ERROR or WARNING for 5 s at each disable | Worked on every disable. A re-enable within 5 s ends it early, as designed. |
| Persistence through power-off | Replay the saved record at boot until the next enable | **4 of 4 reboots** replayed exactly the record saved before power-off. The first enable cleared it every time. |
| `Power/LowRestingBattery` | Dashboard-only queue check | Came on 20 s – 2 min after the last disable on each depleted battery |
| `Power/LowStartingBattery` | Warn when a run starts below 12.3 V | Never fired. The lowest snapshot was 12.303 V. |
| Mid-match restart | Log-only, FMS only | Not exercised (no FMS) |

## The monitor's first real catch: an intermittent break in the roboRIO CAN chain

Three of the five monitored logs show the same outage pattern. The pre-monitor 22:17 log shows it too. **All 12 roboRIO-bus devices except the intake pivot (ID 14) disconnect at once.**

| Log | Group outages | Longest |
|---|---|---|
| 22-17-19 (no monitor) | 10 | **188 s** (from t=1040 s) |
| 23-02-12 | 7 | 23.9 s; four more of 1–7.5 s |
| 00-12-59 | 2 | **Booted with the devices already missing.** They stayed out 118 s while disabled. The robot was then enabled with them missing. A second outage of 36.6 s followed. |
| 00-33-54 | 2 | 0.96 s |
| 00-48-16 | 2 (9 of 12 devices) | 0.7 s |

There were also 13 smaller drops of 1–4 devices, lasting 0.13–0.47 s.

What the evidence shows:
- **Not brownouts.** Only 1 of the 25 dropout clusters in the monitored logs overlapped a brownout. Several of the long outages started at 9.4–11.4 V.
- **The pivot really is still talking.** Its current (and its position, when it moves) keeps arriving during the outages, while the rollers' and shooter's data stops. It is the only device with an intact path to the roboRIO. So the fault is in the wiring that all 12 other devices depend on and the pivot doesn't: most likely the connection from the pivot (ID 14) to the next device on the chain.
- **It is triggered by intake motion.**
  - 13 of 22 group outages started within 1.5 s of a full ~27-rotation pivot stroke. Only 3% of enabled 1.7 s windows contain a stroke, so about 0.7 would be expected by chance.
  - Most started as the pivot was moving toward, or had just reached, position ≈0. Several recovered as it swung back toward ≈25–28.
  - In the 00:12 log the robot booted with the pivot at 0 and the devices missing. The bus came back at t=161.9 s, the moment the pivot first swung out to ~28.
  - This points to a wire or connector that is pulled or jolted at the pivot's zero end of travel (the power-on position, presumably stowed).
- **It is not new.** NERD Q15 and E11 had the identical "everything but the pivot" signature (`claude/health-monitor-nerd-replay.md`).

**Suggested check:** with the robot disabled and Phoenix Tuner open (or `Health/ActiveFaults` on the dashboard), move the intake by hand to the zero end. Flex the CAN wiring between the pivot motor and the next device.

## What behaved differently from the plan

### 1. Practice matches are split into two separate records
Without the FMS, every enable is its own record. That was intended for bench tests, but the team runs Driver Station practice matches with no FMS attached. In each of the three practice matches:
- The auto record's ERROR display showed for only ~3.5 s before the teleop enable ended it.
- The teleop enable then **erased the auto record**, including the copy saved through power-off.

In the 00:12 practice match, the devices were missing at the start of auto, but teleop only had warnings. The run ended showing **WARNING**, and the record replayed at the next boot (00:33 log) listed only brownout, sag and CAN-error warnings. A real FMS match with the same faults would have ended ERROR.

### 2. `CAN/BusErrors` fires far more than the NERD replay predicted
It came on in **every** enable: 35–140 separate episodes per run, each lasting 20–130 ms. The cause is how often each side samples the counters:
- AdvantageKit's logged CAN counters (`SystemStats/CANBus/*`) only change every ~0.5–0.7 s.
- The fault calls `RobotController.getCANStatus()` itself, every loop.
- The error counters drop by 1 with each clean frame, so a burst clears within milliseconds.

The per-loop check therefore catches roughly 20× more nonzero snapshots than the logged data shows. In the 00:33 log the logged counters never left 0, yet the fault fired 44 times.

Consequences:
- The NERD replay, built on the logged data, undercounted this fault. **The logs we have cannot be used to tune it.**
- Its `(xN)` count depends on the loop rate, so it isn't a meaningful number.
- `CAN/BusErrorsSevere` fired once, for one 20 ms loop, during the 23:02 outage period. The logged counters never showed anything above 13, so that can't be verified.
- The bus was never healthy today (see the CAN chain break above), so there is no clean-bus baseline yet. The noise floor is unknown.

### 3. Loop time rose 3–4 ms per loop, not "well under 1 ms"

| Build | `UserCodeMS` median (disabled) | `FullCycleMS` median (disabled) | `GCTimeMS` p90 (enabled) |
|---|---|---|---|
| `51350d2` (before) | 10.9–12.8 ms | 21.6–23.2 ms | 10 ms |
| `fc868cc` (after) | 15.1–16.3 ms | 26.4–28.0 ms | 12–17 ms |

- The merge also brought in the tread wear tracker (`util/usage/`), which runs every loop too, even while disabled. The logs can't split the cost between the two.
- Likely contributors in the monitor:
  - three `getCANStatus()` calls per loop (AdvantageKit makes its own as well);
  - 13 extra `isConnected()` calls (each refreshes a status signal through native code, and `IsHealthy` already makes the same calls);
  - the latched list and summary strings rebuilt every loop.

### 4. Nothing shows the result yet
The end-of-run display worked, but there is no LED subsystem to read it, so the dashboard Alerts widget was the only place to see it. In the 00:12 log, robot code had been reporting the 12 devices missing for about 2 minutes (disabled), and the robot was then enabled anyway.

### 5. The summary can't tell a blip from an outage
In the 23:02 summary, `Turret/Motor (x7)` covers everything from a 0.17 s blip to a 23.7 s outage. The 22:49 run ended ERROR only because of three single-device 0.16 s drops. That is correct by the rules, but nothing in the summary shows it was minor compared with the 23:02 outages.

### 6. CAN utilization readings (added after a follow-up question)
`SystemStats/CANBus/Utilization` showed many readings of exactly 1.000, and several stretches of 2–3 s where every logged value was above 0.85. `CAN/HighUtilization` never fired, not even on the dashboard.

- **AdvantageKit reads CAN status on exactly every 20th robot loop** (true in every log). Each logged point is one snapshot; the fault reads on every loop in between.
- **The monitor build made the reading noisier, not the bus busier.** Compare the robot sitting disabled before its first enable, same day:

  | Build | Median | Std dev | Readings ≥ 0.95 |
  |---|---|---|---|
  | `51350d2`, no monitor (today, NERD, Oct 8) | 0.49–0.51 | 0.06–0.07 | 0–0.6% |
  | `fc868cc`, with monitor (today) | 0.47–0.48 | 0.12–0.16 | 2.2–5.3% |

  The traffic didn't change; the measurement got noisier, and most of the 1.000 spikes are measurement noise.
- **Best explanation (inferred; NI's code is closed):** the roboRIO reports utilization for the interval since the previous `getCANStatus()` call by any code.
  - Before the monitor, AdvantageKit's call covered ~20 loops (~0.5 s).
  - The monitor calls `getCANStatus()` three times per loop. AdvantageKit's call now covers about one loop, so its readings are noisier.
  - The utilization check is the third of those calls, microseconds after the second. Its interval is so short its reading is close to meaningless, so "above 85% on every loop for 2 s" effectively can't happen.
  - The NERD replay set the 85% threshold from ~0.5 s-interval data, so it doesn't carry over to these readings.
  - A bench test on the home roboRIO (log utilization with and without extra `getCANStatus()` calls per loop) would confirm or refute this.
- **The traffic level itself is fine.**
  - Since the roller floor went on (Oct 5), the bus has run a steady ~0.50 disabled at boot, ~0.58 disabled after the first enable, and 0.56–0.66 median enabled. Today matched NERD and the Oct 5–9 practices.
  - That is below the ~0.77 enabled mean that preceded Newton's errors.
  - The transmit queue only overflowed at boot and the bus never went bus-off.
  - Device dropouts were not preceded by high readings: 11% of outages, versus a 13% base rate.
  - It is higher than the Aug 22 drive tests (~0.32 at boot, ~0.41 enabled). Those were run on the second robot, so that comparison may not be like-for-like.
- **One unexplained pattern, not caused by the monitor.**
  - In some sessions the disabled reading after a run sits at ~0.77 instead of ~0.58, and stays there until reboot.
  - It appears in Oct 5–9 practice logs and in NERD Q15, E8, E11, E13, E14 and E15, and today.
  - It is not device reboots: no device's position reset across any outage.
  - Worth watching once per-loop utilization is logged.

## Recommended changes, in priority order

1. **Find and fix the CAN wiring fault near the intake pivot.** This is hardware, not code. Afterwards, run a practice session to get a clean-bus baseline for `CAN/BusErrors`.
2. **Treat auto followed by teleop as one match even without the FMS.**
   - Continue the record when a teleop enable comes within ~5 s of an auto disable.
   - Show the auto-end display only if teleop doesn't follow within that gap.
   - Keep the FMS path unchanged.
3. **Measure and trim the loop cost.**
   - Log `Health/PeriodicMS` and `Usage/PeriodicMS` (handoff open item 4c).
   - Read `getCANStatus()` once per loop and share it across the three CAN checks. This also fixes the utilization reading (section 6).
   - Log what the check saw (`Health/CAN/*`) so future tuning uses per-loop data, not AdvantageKit's every-20th-loop snapshots.
   - Change `CAN/HighUtilization` from "above 85% on every loop for 2 s" to "the average over the last 2 s is above the threshold". Re-pick the threshold from the new per-loop data.
   - Rebuild summary strings only when the latch state changes (open item 4b).
4. **Add per-fault accumulated active time** to the summary and saved record (open item 8). Today's data is the clearest case for it.
5. **`CAN/BusErrors`: decide after the wiring fix.** If it still fires every enable on a healthy bus, change it to a rate-based check (e.g., errors seen in more than X% of loops over 5 s), tuned from the new per-loop log data.
6. **For the future LED subsystem:** also show live `kError` faults while disabled (`highestActive()` already exists), so a robot with devices missing at power-on doesn't get enabled.

No threshold or debounce change is indicated for the presence, power or drive faults. The utilization check needs the rework in item 3.
