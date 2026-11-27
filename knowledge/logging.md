---
title: Logging contract
status: proposed
date: 2026-11-27
source: archive/2026/log-the-tune-spec.md; lessons/lessons-2026.md #15, #16, #43, #46, #47; 2026 Pitwall and power reviews
superseded_by:
---

# Logging contract (proposed)

What every Team 88 robot should log, so analysis, Pitwall and the health monitor work without reconstruction. It's written to be robot-agnostic: each item names the kind of signal, not a specific subsystem.

The 2026 rule this comes from: **if it isn't logged, you'll be estimating it.** Several 2026 analyses had to rebuild supply current, setpoints and tunes from other signals.

**Status: proposed.** Nothing here is agreed with the team yet. Items marked ⚠ depend on Systemcore and WPILib 2027 and need checking against the real APIs (`knowledge/control-system.md`).

## 1. Identity: which code, which tune, which battery

Every log must answer "what was running, on which battery, for what purpose" without anyone's memory.

| Item | How (2026 AdvantageKit terms) | Why |
|---|---|---|
| Build identity | Metadata before logging starts: git SHA, branch, build date, dirty flag. Already in the 2026 template. | Baseline |
| **Gains at boot** | Metadata strings for each closed loop: kP, kI, kD, kS, kV, kA, control mode (Voltage / TorqueCurrentFOC / duty), current limits | Dirty builds share a SHA, so the SHA alone can't tell two tunes apart (2026 Aug 28 session) |
| Applied gains | Read the config back off one motor per mechanism after configuration and log it once | Catches live edits and configs that were built but never applied (lessons #12) |
| Preferences in use | Log every robot Preference value the code reads, at boot and on change | roboRIO Preferences overrode code defaults unseen in 2026 (lessons #16) |
| **Run label** | A dashboard text entry that is also logged (2026: `LoggedNetworkString` at `/Tuning/TestLabel`) | Lets testers name a run ("P=15", "new feeder belt") |
| **Battery ID** | A dashboard chooser or text entry set in the pit before each match or run, logged (e.g. `/Match/BatteryId`) | Battery state decided whether the same transient browned out (Q23: 32 vs Q14: 0). Late-match voltage separates batteries better than Ah used (lessons #24). |
| Match identity | Event name, match type and number from the FMS, plus whether an FMS was attached | Pitwall groups by these; practice matches are told apart from events |
| Deploy discipline | Tuning sessions deploy from an `event/…` branch, so the build auto-commits | Every deploy gets a unique SHA, with no new code |

## 2. Power

| Item | Notes |
|---|---|
| **Power distribution total and per-channel current** ⚠ | Needs a PDH or another data-capable power distribution board. The 2026 PDP 2.0 reported nothing, so whole-robot current was synthesized. Log it through AdvantageKit's power-distribution support, or its 2027 equivalent. |
| Battery voltage, brownout flag, brownout threshold in use | Brownout metrics (matches with a brownout, time left at the first) are computed from these |
| **Supply current for every motor** | Battery side. In 2026, April logs lacked it for the shooter and supply had to be estimated as V·I / V_batt. |
| Stator / torque current for every motor | Motor side: heat, torque, stall and jam detection (supply misses full stalls, lessons #29) |
| Applied output (volts or duty) for every motor | Shows saturation: a loop at 97–98% duty has no authority (lessons #7) |

**Rate caveat (lessons #43):** status-frame values are sampled. In 2026, rio-bus supply current arrived at 4 Hz in hoot logs and 50 Hz in wpilog, so short spikes were under-read. Either raise the rate for the signals that matter, or infer spikes from the battery dip. Decide this per signal.

## 3. Control: commanded vs measured

For every closed loop whose setpoint changes during a match:

- the setpoint actually sent (after any clamping)
- the measured value, in the **same units and shaft reference** as the setpoint (state whether it's motor shaft or mechanism)
- the control mode in use

Constant-speed mechanisms don't need this. In 2026 the shooter and hood had dynamic setpoints with nothing logged.

**Gates:** log every boolean that starts or stops a mechanism, such as "is shooting", "on target" and "pre-aiming", *after* any debounce, and the raw input too if it's debounced. 2026 couldn't analyze the pre-aim idle option because `isPreAiming` wasn't logged.

## 4. Loop timing

- Total cycle time and user-code time per loop.
- A timing breakdown by subsystem (a LoggedTracer-style utility), so the loop's cost is visible without a profiler.
- Logging's own cost. In 2026 `@AutoLogOutput` alone was ~7.5 ms of a ~26 ms loop.

## 5. CAN ⚠

Systemcore has **multiple CAN buses**, so log per bus:
- utilization
- receive and transmit error counts, and bus-off events
- dropped devices (from the health monitor)

**Rate caveat (lessons #43):** AdvantageKit logged CAN status every 20th loop in 2026, which undercounted fast-decaying error counts ~20×. Compute rates on the robot (e.g. episodes per minute) and log the rate. Read the CAN status once per loop, because each call's utilization covers the time since the previous call.

## 6. Health and wear

- Active fault list and the error-active boolean (health monitor).
- Wear counters, such as tread distance, plus inspection events and grades, so thresholds can be calibrated (lessons #37).

## Cost rules for logging

- Batch Phoenix signal reads (`refreshAll`); avoid method-level `@AutoLogOutput` getters that each trigger a native refresh (lessons #44).
- Under `optimizeBusUtilization`, give every signal you log or alert on an explicit update frequency. Otherwise it reads a stale value with no error (lessons #42).
- Budget signal rates. A status rate matters only if something consumes it.
- Add timing outputs for anything new, including "observe-only" code (lessons #39).

## Key names

Pitwall robot profiles map these signals to log keys per robot, so a key rename breaks a profile silently. Pick key names early in build season, write them in `knowledge/robot-2027.md`, and treat renames as a breaking change.

## To check for 2027 ⚠

- Whether AdvantageKit has a 2027 release for Systemcore, and how its metadata, `LoggedNetworkString` and power-distribution logging map onto it.
- What the new WPILib telemetry API logs by default, and whether `.wpilog` and key paths change. This affects Pitwall and `scripts/wpilog_reader.py`.
- Where Systemcore stores logs, and how they're fetched. Pitwall's 2026 fetch used SFTP to the roboRIO.
- Which power distribution hardware the 2027 robot uses (`knowledge/robot-2027.md`).
