# Health Monitor — Session Handoff (2026-10-01, updated 2026-10-19)

*Written so a new chat (on a different computer) can pick this work up cold. Read this first, then `claude/health-warning-system-design.md` for the design rationale. A copy of an earlier `HealthMonitor.java` is saved alongside this doc at `claude/health-monitor-code/HealthMonitor.java`. As of 2026-10-19 the code is merged into **BaseComp** (`fc868cc`), which is now the source of truth.*

## How to resume

1. On the new computer, clone `frc-88/2026-Robot` (or pull) and check out **`BaseComp`**.
2. Start a new chat in the **FRC 2026 Robot** project and connect the repo folder.
3. Tell Claude: *"Read `claude/health-monitor-handoff.md` and continue the health monitor work."*

## What the system is (one paragraph)

The health monitor is an observe-only warning system layered on top of the existing robot code. It never commands hardware and adds no CAN traffic. It has two parts:

- **`Fault`** (`util/health/Fault.java`) is one concern: a WPILib `Alert` plus a condition, an optional debounce, and a per-match memory (latch + occurrence count). Faults register themselves when created.
- **`HealthMonitor`** (`util/health/HealthMonitor.java`) is the single aggregator. It runs once per loop from `Robot.robotPeriodic()`, after the scheduler. It polls all faults and owns the match lifecycle (when records start, continue and end). It produces "worst now / worst this match", the end-of-match display value, the dashboard summary, and the saved record that survives power-off.

Severity is WPILib's own `AlertType.kError` / `kWarning`. There is no RED/YELLOW vocabulary; color is the LED code's decision. Displays **pull** from the monitor (`getEndOfMatchDisplay()`, `getPreviousRunDisplay()`). There is no annunciator interface and no LED subsystem yet.

## Where the code is

| Piece | Location | Status |
|---|---|---|
| Framework (`Fault`, `HealthMonitor` v1), Rung 1 presence faults in all subsystems, drive/gyro/vision Alerts converted to Faults, `Robot.java` hook | `alerts` branch, commit **"initial creation" (9279d07)** | Committed, built clean |
| Rung 2 step 1 power faults + low-starting-battery + `onScopeStart` hook | `RobotContainer.java`, `HealthMonitor.java` | Committed as **"Brownout and battery alerts" (d29adb4)**, 2026-09-24 |
| Persistence through power-off (saved record, boot replay, mid-match restart logging, record labels) | `HealthMonitor.java` | Committed as **527cc60**, 2026-10-02. **Tested on the robot 2026-10-19: 4 of 4 reboots replayed the saved record correctly.** |
| roboRIO CAN bus faults | `util/health/CanBusFaults.java` + 1 line and 1 import in `RobotContainer.configureHealthFaults()` | Committed as **"CAN bus warnings" (8101514)** |
| NERD 2026 tuning: disconnect debounce 0.1 s, Brownout → kWarning, CAN/HighUtilization 85% | `Fault.java`, `RobotContainer.java`, `CanBusFaults.java` | **566dfa8**, plus comment cleanup in **1d807cf**. Evidence in `claude/health-monitor-nerd-replay.md`. |
| Merge into BaseComp | **PR #50**, merge commit **fc868cc** | Merged 2026-10-19, deployed and run at practice that day. Review: `claude/health-monitor-practice-1019-review.md`. |

Unrelated work that came in with the same merge: the wheel tread wear tracker (`util/usage/`, commit 5cbfb6d).

Builds: Claude can't run GradleRIO (no WPILib/CTRE maven access, including through the computer bridge). Logic was verified against API stubs with scenario tests, against the NERD logs with the replay script, and on the robot at the Oct 19 practice. Always run `./gradlew build` locally. The build runs spotless (google-java-format), which may rewrap comments; that's expected.

### Files touched overall
- New: `util/health/Fault.java`, `util/health/HealthMonitor.java`, `util/health/CanBusFaults.java`.
- `Robot.java`: 1 call.
- `RobotContainer.java`: the power section.
- `Shooter`, `Turret`, `Hood`, `Feeder`, `HotTub`, `Intake`: one `Fault.disconnected(...)` line per device in the constructors.
- `drive/Module.java`, `drive/Drive.java`, `vision/Vision.java`: existing Alerts converted to Faults, same text and type.

## Current behavior (as of fc868cc)

**Faults (36 on the real robot):**
- **Rung 1 – presence (`kError`):**
  - **13 mechanism devices** via `Fault.disconnected(key, desc, device)`, using Phoenix `isConnected()` (0.5 s Version-frame latency) **plus a 0.1 s debounce** (`Fault.DISCONNECT_DEBOUNCE_SECONDS`). At NERD, `isConnected()` read false for single 20–40 ms loops with the device otherwise fine. Real robot only.
  - **Drive modules ×4** (drive/turn/encoder) from the IO-layer `connected` flags. These already carry a 0.5 s falling-edge debounce in `ModuleIOTalonFX`, so nothing extra is added.
  - **Gyro:** 0.25 s debounce added.
  - **Cameras ×3:** `kWarning`.
- **Rung 2 step 1 – power** (in `RobotContainer.configureHealthFaults()`; real robot only):
  - `Power/Brownout`: `RobotController.isBrownedOut()`, **`kWarning`** (was kError until 566dfa8), no debounce. Brownouts happened in 8 of 10 NERD matches and would have made every end-of-match result an error, hiding device dropouts.
  - `Power/BatterySag`: < 7.0 V for 0.1 s, `kWarning`. Doug chose 7 V deliberately: dipping below it every match was a real problem.
  - `Power/LowRestingBattery`: disabled and < 12.3 V for 2 s, `kWarning`. A dashboard-only queue check; it never latches.
  - `Power/LowStartingBattery`: the resting voltage snapshotted when a new record starts (auto start) is < 12.3 V, `kWarning`. Recorded once per match. The snapshot is logged as `Health/MatchStartBatteryVolts`.
- **CAN (roboRIO bus):**
  - `CAN/BusErrors` (kWarning): any receive/transmit error, or TxFull went up.
  - `CAN/BusErrorsSevere` (kError): error count ≥ 96, or bus-off went up.
  - `CAN/HighUtilization` (kWarning): **> 85% for 2 s** (was 70%). At 85% it fired in no NERD match (post CAN fix) and in 9 of 10 Newton matches (pre fix). At 70% it fired in every full NERD match.
  - **Sampling caveat (found 2026-10-19):** AdvantageKit's logged `SystemStats/CANBus/*` values only change every ~0.5–0.7 s, but the faults read `getCANStatus()` every loop. The error counts decay within milliseconds, so the live check sees far more nonzero samples than the log shows. The NERD replay undercounted `CAN/BusErrors` for this reason; logged data can't be used to tune it.

**Lifecycle rules (HealthMonitor):**
- 2 s startup grace after the first loop.
- Faults only **record (latch)** while enabled. Occurrence count = the number of inactive→active transitions while enabled. It is shown as `(xN)` in the summary, `Health/LatchedFaults` and the saved record. Duration is not reported.
- **New record:**
  - With FMS attached (`PER_MATCH`), a new record starts at the auto enable. The teleop enable after auto **continues** the same match.
  - Without FMS (`PER_ENABLE`, bench), every enable starts a new record. **This includes Driver Station practice matches**, which are split into separate auto and teleop records (see the Oct 19 review).
- **End of record** (any disable except the auto→teleop pause):
  - `getEndOfMatchDisplay()` returns the worst latched type for 5 s.
  - The dashboard summary alert "Faults this match (LABEL): …" stays up.
- **Persistence:**
  - The record is saved to WPILib `Preferences` (`Health/SavedRecord`, `Health/SavedRecordType`) each time it changes, labeled e.g. "NECMP2 Q23: …" or "bench: …".
  - At boot, a saved record is replayed via `getPreviousRunDisplay()` plus a dashboard alert ("Before last power-off/restart - …") **until the next enable**, which clears it. Nothing stale carries into a new run.
  - Disabled during log replay.
- **Mid-match restart:**
  - First enable within 5 s of code start, with FMS attached → `Health/RestartedMidMatch` = true.
  - The pre-restart record is in `Health/PreviousRun`.
  - Log-only by Doug's choice: that failure is obvious from the stands.

**Log keys:** `Health/Faults/<key>`, `Health/ActiveFaults`, `Health/LatchedFaults`, `Health/HighestActive`, `Health/HighestLatched`, `Health/EndOfMatchDisplay`, `Health/PreviousRunDisplay`, `Health/PreviousRun`, `Health/RestartedMidMatch`, `Health/ResetScope`, `Health/InStartupGrace`, `Health/MatchStartBatteryVolts`.

## Decisions made (and why)

- Use WPILib `AlertType` directly; dropped `Severity` (RED/YELLOW put display language into detection).
- Dropped the `Annunciator` interface. LEDs will **pull** from `HealthMonitor` and arbitrate in their own `periodic()` priority chain, as Mechanical Advantage's 2026 `Leds` does. Color lives only in LED code.
- Keep Javadoc HTML tags in `util/health` (they render nicely on hover). Keep **RobotContainer comments short**; it serves many purposes.
- Existing Alerts were converted to Faults (same text/type) rather than duplicated.
- The robot has a **PDP 2.0 with no data**, so there are no PDH checks. Each motor is alone on its channel, so motor supply current can stand in for per-channel current later. A blown breaker already shows as a Rung 1 disconnect (integrated controllers).
- `RobotController.setBrownoutVoltage(6.5)` left untouched: changing it changes robot behavior and is a separate decision.
- Low-battery threshold 12.3 V = the lowest pre-match resting voltage in last season's logs.
- Thresholds and timings are tuned from real log data, not guessed.
- **CAN error escalation to `kError` at an error count of 96** (Doug, 2026-10-02; 25 and 128 were also considered).
  - 128 is where the controller is already failing (error-passive), and a dropped device already latches its own presence error, so an error at 128 adds little.
  - 96 is the "error warning" limit many CAN controllers use (a common controller convention, not part of the CAN standard). It is close to failing, which is what "fix before next match" should mean.
  - 25 was rejected: transmit errors count 8 each, so 25 is only 3–4 net transmit errors.
  - The end-of-match display appears after the match whatever the threshold, so a lower number gives no earlier warning. The early signal is the warning tier (any errors, high utilization), not the error tier.
  - Last season's logs can't separate thresholds between ~10 and 128 (every count was 0, single digits or 128), so this was a judgment call. One number covers both counts.
- **NERD 2026 tuning (Doug, 2026-10-17)**, from the log replay in `claude/health-monitor-nerd-replay.md`:
  - 0.1 s disconnect debounce.
  - Brownout → kWarning.
  - CAN utilization warning at 85%.

  With these, ERROR after a NERD match always meant a device actually left a bus.

## Open items / next steps

1. ~~Get the code onto a computer and build/commit it.~~ Done 2026-10-02.
2. ~~Build and push 566dfa8; retarget PR #50 to BaseComp.~~ Merged into BaseComp 2026-10-19 (`fc868cc`).
3. **Robot test checklist** (Oct 19 practice results in `claude/health-monitor-practice-1019-review.md`):
   - ~~Boot and sit disabled: all `Health/Faults/*` false after the grace period.~~ Yes, except when the bus was actually down.
   - ~~Camera faults while disabled~~: no false disconnects while disabled. The Limelights read disconnected for 5–16 s after boot (they boot slower than robot code); dashboard only.
   - ~~Device dropout while enabled → ERROR for 5 s~~: happened for real many times (see the CAN chain break below).
   - ~~Power-cycle replay~~: 4 of 4 correct.
   - **Still open:** `CAN/*` faults on a healthy bus. The roboRIO bus was never healthy on Oct 19.
4. **Hardening offered, not yet decided:**
   - (a) try/catch around each fault's check so a buggy check can't crash robot code;
   - (b) rebuild summary strings only when something changes (GC churn);
   - (c) a `Health/PeriodicMS` timing output.

   **Measured 2026-10-19:** `UserCodeMS` rose 3–4 ms per loop with the merge (disabled median 10.9–12.8 → 15.1–16.3 ms), not "well under 1 ms". The tread tracker came in with the same merge, so the cost can't be split yet. (b) and (c) are now recommended, along with reading `getCANStatus()` once per loop instead of three times.
5. ~~Log-tuning script~~: done for NERD as `FRC Logs/nerd-review/healthsim.py`. For runs where the monitor was deployed, use its own `Health/*` outputs instead (`FRC Logs/health-practice-1019/`).
6. ~~Brownout cascade~~: did not appear at NERD or at the Oct 19 practice.
7. **Rung 2 later steps:** motor temperatures and supply-current "about to trip" checks need `setUpdateFrequency` on those signals. That adds CAN load: measure utilization before and after, and log an event's worth before setting thresholds.
8. **Per-fault accumulated active time** so the summary can say how long something was out. Now recommended: on Oct 19, `Turret/Motor (x7)` covered everything from a 0.17 s blip to a 23.7 s outage.
9. **Design doc cleanup** (`claude/health-warning-system-design.md`):
   - fix the generic "warning" vs `kWarning` wording;
   - update the outdated "How the Fault helper maps" section;
   - add Rung 2 progress, the PDP 2.0 note, persistence/replay, mid-match restart, the CAN faults and the NERD tuning.
10. **Future LED subsystem:**
    - Read `getEndOfMatchDisplay()` (just happened) and `getPreviousRunDisplay()` (carried over). Show the two distinguishably, e.g. a slower flash for carried-over.
    - Also show live `kError` faults while disabled (`highestActive()`): on Oct 19 the robot was enabled with 12 devices already missing at power-on.
    - Decide where health sits in the LED priority order.
11. **Wave 2** (Rungs 3–4) needs the intent-gating ("arming") primitive. Not started.
12. **Remaining checks:**
    - **CANivore (drive bus):** Phoenix 6 `CANBus.getStatus()`, probably polled at ~1 Hz. NERD E15 had a 0.5 s CANivore-wide dropout; it was caught by the module faults.
    - **Loop overrun:** not yet written. WPILib only prints "Loop time of 0.02s overrun" to the Driver Station console. At NERD, ~90% of enabled cycles were over 20 ms (mean ~29 ms), so a per-cycle threshold at 20 ms would fire constantly. Pick the threshold from the `FullCycleMS` distribution, or fix the overruns first.
13. **New 2026-10-19:**
    - **Practice-match continuity:** without the FMS, auto and teleop are separate records, so an auto-period dropout can be erased by the teleop enable. Proposed fix: continue the record when teleop enables within ~5 s of an auto disable, and hold the auto-end display until that gap has passed. Not yet decided.
    - **`CAN/BusErrors` rework:** fired 35–140 times in every enable. Decide after the roboRIO CAN wiring is fixed and a clean-bus baseline exists. Log the per-loop values the check sees (`Health/CAN/*`) so it can be tuned.
    - **Hardware (not code):** an intermittent break in the roboRIO CAN chain drops every device except the intake pivot (ID 14). It is linked to the pivot reaching its zero end. Same signature as NERD Q15/E11.

## Working notes for the next session

- Doug's code background is light: explain in plain terms and keep answers precise. He catches inconsistencies.
- He prefers questioning abstractions that don't earn their place (Severity and Annunciator were removed for that reason). He wants short comments in shared files like `RobotContainer`.
- Pattern that worked: change code first, verify, then update the design doc to match.
- Git workflow: preview changes first; branch or commit only after Doug says so.
- If the computer bridge is used:
  - Read-only git commands must use `git --no-optional-locks`. A plain `git status` once left a stale `.git/index.lock` that needed deletion.
  - The bridge shell has no git identity. Commits use `-c user.name="Doug" -c user.email="141052403+DStewart-88@users.noreply.github.com"`, matching his earlier commits.
