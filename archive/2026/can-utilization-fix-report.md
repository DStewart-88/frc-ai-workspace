# CAN Bus Over-Utilization — Problem & Resolution Report

*A summary of the roboRIO CAN over-utilization issue and its fix, confirmed against offseason test data. For the deep analysis and the code-level cleanup steps, see `can-bus-analysis.md`; this doc is the shorter "what broke, what we did, and did it work" writeup for the team.*

## Summary

The roboRIO CAN bus was chronically overloaded through the 2026 season and crossed into real errors at World Champs (Newton), where mechanisms briefly dropped off the network mid-match. The cause was a software configuration problem, not hardware: devices were broadcasting far more status traffic than needed. The fix — enabling bus optimization and turning down a handful of over-cranked signal rates — was applied in the offseason. **Drive-test logs from Aug 22, 2026 confirm it worked: bus utilization dropped by roughly half and all CAN error counts are back to zero, with ample headroom restored.**

## The problem

The robot runs two CAN buses. The drivetrain sits on a CANivore (CAN FD, high bandwidth) and was always healthy. Everything else — shooter, hot tub, intake, hood, turret, feeder, power hub — sits on the roboRIO's built-in 1 Mbit/s bus, and that bus was the problem.

Over the season the roboRIO bus load roughly doubled, from ~30–50% busy in March to ~70–77% by Newton, saturating to 100% at the peaks. The load grew because every added mechanism device was broadcasting its **full default set of status frames**, and a few signals had been turned up far past what any control loop or logger consumed (notably the hood's pulse-width position at 1000 Hz — about 13% of the entire bus from one sensor — and two follower motor-voltage signals at 500 Hz each).

Critically, this was **baked into the configuration, not caused by the brownouts**: the bus was already ~70% full while the robot sat disabled on a full battery. At Newton it ran out of headroom and tipped over:

| Symptom at Newton (Q23) | What it means |
|---|---|
| Utilization averaged 77%, hit 100% repeatedly | Bus chronically full |
| Receive Error Count climbed to **128** (past the 127 threshold) | CAN controller went **error-passive** — failing to cleanly receive frames |
| Transmit buffer overflowed | roboRIO queuing frames faster than a full bus could send them |
| Shooter (main + follower) logged a disconnect | A device on a saturated bus missed its heartbeat window and read as gone |

The earlier events confirmed it was a headroom problem, not a bad-luck problem: MAREA had *worse* brownouts than Newton in some matches yet threw **zero** CAN errors, because the bus was only ~50% full and could absorb the disruption. The errors appeared at Newton not because conditions got worse, but because the bus had no slack left.

## The fix

Two independent, low-risk changes, both grounded in one rule: *a status-frame rate only matters if something actually consumes the signal at that rate.*

1. **Turned down the over-cranked signal rates.** The hood's 1000 Hz pulse-width position and the two 500 Hz follower voltage signals were dropped to ~100 Hz — none of them fed a control loop that needed the higher rate. This alone reclaims roughly a quarter of the bus.

2. **Enabled `optimizeBusUtilization()` per device, then re-enabled only the signals the code actually reads.** By default every Phoenix 6 device streams its entire signal set; optimization silences everything not explicitly requested. The drivetrain already did this — the mechanism subsystems did not. Applying the same "optimize, then explicitly enable" pattern to the roboRIO-bus devices cut each device's traffic to the handful of signals its control logic, followers, and logging genuinely use.

## The results (Aug 22, 2026 drive tests)

Four drive-test logs were analyzed the same way as the match logs (roboRIO-bus utilization and error counters read straight from the AdvantageKit `.wpilog` files). Every measure improved by roughly half, and every error count is zero.

| Metric (roboRIO bus) | Newton (Apr 30–May 1) | Offseason (Aug 22) |
|---|---|---|
| Disabled baseline | ~70% | **~40%** (39–41%) |
| Enabled mean | ~77% | **~41%** (41–42%) |
| Enabled p95 | ~92% | **~48–51%** |
| Peak | 100% (saturating) | **65–84%** (rare, transient) |
| Receive Error Count | up to **128** (error-passive) | **0** |
| Transmit Error Count | rising | **0** |
| Bus-off count | 0 | 0 |

The disabled baseline is the cleanest before/after comparison because it strips out gameplay and shows the hard-wired configuration load — it fell from ~70% to ~40%, essentially the target the cleanup predicted. Across a full log the bus now sits at a **~39% median (p90 45%, p99 59%)** with only a handful of isolated single-sample spikes, versus a bus previously pinned near saturation.

Three checks confirm the result is real and clean, not an artifact of the test:

- **Same devices, apples-to-apples.** All the mechanism subsystems (shooter, hood, hot tub, intake, turret, feeder) are present and broadcasting in these logs, so the drop is per-device traffic coming down — not fewer devices on the bus.
- **The spikes are harmless.** The transient peaks (up to 84%) occur while *disabled on a full ~12.7 V battery* and last a single ~0.5 s sample; the dashboard clients all connect once at startup, so these aren't reconnect storms. With zero error counts, they cost nothing.
- **No telemetry was accidentally silenced.** The cleanup's main risk is that optimization freezes a logged signal at a stale value. A scan of every numeric mechanism telemetry channel across all four logs found **zero frozen signals** — the fix re-enabled everything the code and logs actually read.

## Status and remaining follow-ups

The CAN over-utilization problem is **resolved**. Two light follow-ups remain, neither blocking:

1. **Confirm under match load.** These are drive tests, not full matches — the disabled baseline is fully representative, but the enabled figure comes from sparse driving samples with mechanisms lightly exercised. One real competition log (autonomous + sustained mechanism use) should confirm the enabled mean/p95 hold in this range under game load.
2. **Add a dashboard alert as regression insurance.** The bus crept from ~30% to ~70% over a season by accretion, with nobody watching the number. A utilization + error-count readout on Elastic with an alert around 70% would catch any recurrence early as devices and features are added in future seasons. (This is also the motivating case for the health-warning system sketched in `health-warning-system-design.md`.)

## Methodology

Utilization and error counters (`/SystemStats/CANBus/Utilization`, `ReceiveErrorCount`, `TransmitErrorCount`, `OffCount`, `TxFullCount`), enable state (`/DriverStation/Enabled`), and battery voltage were read directly from the AdvantageKit `.wpilog` files with a from-scratch WPILOG parser. The disabled-baseline figure uses only disabled-mode samples to isolate configuration load from gameplay. Utilization is logged on a 0–1 scale at ~2 Hz. Newton figures are from `can-bus-analysis.md`. Absolute percentages are good to within a few points; the relative before/after comparison is solid.
