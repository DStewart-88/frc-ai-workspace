# CAN Bus Over-Utilization on ARTEMIS — What Happened, Why, and What to Watch For

Companion analysis to `brownout-analysis.md`. Built from AdvantageKit match logs across all four 2026 events (MAREA/Northshore Mar 14–15, MABOS Mar 27–29, NECMP2/Newsom Apr 16–18, Newton/World Champs Apr 29–May 1) and the `frc-88/2026-Robot` codebase (main branch).

## The one-paragraph version

The robot has **two separate CAN buses**. The drivetrain sits on a CANivore (a high-bandwidth CAN FD bus) and is set up correctly — it is not the problem. Everything else — shooter, hot tub, intake, hood, turret, feeder, and the power hub — sits on the roboRIO's built-in CAN bus, which is the older, slower kind (1 Mbit/s), and that bus was chronically overloaded. It grew from roughly **30–50% busy in March to ~70–77% busy on average (92% at the peaks, hitting a full 100% saturation) by World Champs**, and at Newton it finally crossed the line into real errors: the bus controller went into a fault state (error-passive), its transmit buffer overflowed, and mechanisms briefly dropped off the network mid-match. Crucially, this was **baked into the software configuration, not caused by the brownouts** — the bus was already ~70% full even sitting still on a full battery. The brownouts and the CAN overload are two different problems that made each other worse.

---

## Part 1 — How CAN bus utilization actually works (the background you asked for)

**What CAN is.** CAN (Controller Area Network) is the shared "party line" that lets the roboRIO talk to motor controllers, encoders, the gyro, and the power distribution hub over just two wires. Every device is wired onto the same pair of wires in a daisy chain, with a terminating resistor at each end.

**It's a broadcast bus, one talker at a time.** Only one device can transmit at any instant. Each message is a "frame" — an ID plus up to 8 bytes of data. On the roboRIO's built-in bus the wire runs at **1 Mbit/s (1,000,000 bits per second)**. With all the addressing and error-checking overhead, one frame is about **130–150 bits long**, so it takes roughly **0.13–0.15 milliseconds** to send. That means the bus can physically carry only about **7,000 frames per second** before it is completely full.

**"Utilization" is just how busy the wire is.** 40% utilization means the wire is occupied 40% of the time and idle the other 60%. It's not about how much *current* the motors draw — a bus can be electrically fine and still be 100% full of messages.

**Where the traffic comes from.** Here's the part that surprises most people: devices don't only talk when you command them. Every motor controller *continuously broadcasts* "status frames" — its position, velocity, applied voltage, current, temperature, fault flags, and so on — each at its own repeating rate, whether or not you're using that information. So the traffic on the bus is set by three things multiplied together:

- how many devices are on the bus,
- how many signals each one broadcasts, and
- how fast each signal repeats (its update rate, in Hz).

Add a device, or turn up a signal's rate, and you permanently add frames-per-second to the bus — 24 hours a day, enabled or disabled.

**Why a full bus is dangerous.** When the wire is nearly always busy, a new frame has to wait for a gap. If the gap doesn't come in time, the frame is delayed or dropped. Two bad things follow:

1. **Control gets laggy or lost.** A motor controller that stops hearing from the roboRIO looks *disconnected*, and there's a safety watchdog: if a controller doesn't get a valid command within ~100 ms, it shuts itself off. So a saturated bus can literally make mechanisms cut out.
2. **The bus starts reporting errors.** Every CAN controller keeps two tallies — a **Receive Error Count (REC)** and a **Transmit Error Count (TEC)**. When either climbs past **127**, the controller enters a state called **error-passive**: it's still attached but is struggling and backs off. If the *transmit* count passes 255, it goes fully **bus-off** and drops off the network until it's reset. Rising error counts are the bus telling you, in its own words, that it's drowning.

**The rules of thumb the FRC community uses:** under about **70%** utilization is comfortable; once you push past roughly **85%** you should expect lost frames and errors. For calibration, a classic setup of 16 Talon motor controllers plus a pneumatics module and a power distribution panel already lands around **70%** — so it does not take many devices to fill a 1 Mbit/s bus.

**The escape hatch: CAN FD / CANivore.** CAN FD ("flexible data-rate") is a newer version of CAN that sends the data portion of each frame much faster and packs more data per frame, giving a bus many times the effective capacity. A CTRE **CANivore** is a USB-to-CAN-FD adapter that creates a *second, separate* high-bandwidth bus. Your drivetrain is on one of these, which is exactly why the drivetrain — 13 devices, the most on any bus — is the one bus that's healthy.

---

## Part 2 — The two buses on ARTEMIS

| | **Drivetrain bus (CANivore)** | **roboRIO bus ("rio")** |
|---|---|---|
| Type | CAN FD (high bandwidth) | Classic CAN, 1 Mbit/s |
| Devices | 4 drive + 4 steer Krakens, 4 CANcoders, Pigeon 2 = **13** | shooter ×2, hot tub spinner, intake ×4, hood, turret ×2, turret CANcoder, feeder, power hub ≈ **12** |
| Bus management in code | **Optimized** — `optimizeBusUtilizationForAll(...)` on the drive/steer motors, `pigeon.optimizeBusUtilization()`, only the odometry signals turned up | **None** — not a single `optimizeBusUtilization()` call, *and* several signals turned up far past what's needed |
| Health in the logs | Fine — CAN FD has ample headroom | **Chronically 70–92% full, saturating to 100%, throwing errors by Newton** |

The AdvantageKit logs record utilization for the **roboRIO bus only** (`/SystemStats/CANBus/Utilization`), which is convenient because that's the bus that actually had the problem. The CANivore's own utilization lives in the `.hoot` files; given how it's configured and that CAN FD has several times the bandwidth, it is not a concern.

One clarification worth stating plainly: **this is a different problem from the brownouts**, even though they showed up in the same matches. Brownouts are about *volts* (too much current pulling the battery down). CAN over-utilization is about *messages* (too many frames filling the wire). They interact — more on that below — but you could fix one and still have the other.

---

## Part 3 — What the logs actually show

### The season-long trend

Every value below is roboRIO-bus utilization as a fraction (0.70 = 70% full). "Disabled baseline" is the bus load while the robot is *disabled and sitting still* — this strips out gameplay and shows the load that's hard-wired into the configuration. "Enabled mean/p95" is during the match.

| Event (date) | Disabled baseline | Enabled mean | Enabled p95 | Peak | REC max | Notes |
|---|---|---|---|---|---|---|
| MAREA Q19 (Mar 14) | 48% | 51% | 66% | 98% | 0 | clean |
| MAREA Q28 (Mar 14) | 27% | 28% | 63% | 100% | 0 | clean |
| MAREA Q55 (Mar 15) | 41% | 51% | 67% | 100% | 0 | clean |
| MABOS Q12 (Mar 28) | 52% | 58% | 73% | 97% | 0 | clean |
| MABOS Q36 (Mar 28) | 49% | 57% | 74% | 100% | 0 | clean |
| NECMP2 Q28 (Apr 16) | 72% | 77% | 91% | 100% | 0 | at the edge |
| NECMP2 Q52 (Apr 17) | 70% | 79% | 92% | 100% | 0 | at the edge |
| **NEWTON Q23 (Apr 30)** | **70%** | **77%** | **92%** | **100%** | **128** | **error-passive; shooter dropped off bus** |
| NEWTON Q99 (May 1) | 76% | 76% | 91% | 100% | 0 | TEC to 4 |
| NEWTON Q115 (May 1) | 67% | 77% | 93% | 100% | 7 | receive errors appearing |

The story reads top to bottom: the bus load **roughly doubled over the season**. In March the bus sat around a third to a half full and never threw an error. By NECMP2 the *disabled* baseline had climbed to ~70% — meaning before a match even started, on a full battery, the wire was already at the "getting uncomfortable" threshold. At Newton it tipped over into actual faults.

### The smoking gun: Newton Q23

Q23 is the match `brownout-analysis.md` flagged for "every mechanism on the RIO CAN bus momentarily disconnected." Here's the CAN side of it:

- **Utilization hit 100%** repeatedly, and averaged **77%** through the match.
- **The receive error count climbed to 128** — past the 127 threshold — so the roboRIO's CAN controller entered **error-passive**: it was failing to cleanly receive frames. (It did *not* reach bus-off; `OffCount` stayed 0 in every log, so no device was formally kicked off — the dropouts were momentary missed-frame timeouts, not a hard bus-off.)
- **The transmit buffer overflowed** (`TxFullCount` ticked up) — the roboRIO was trying to queue frames faster than the full bus could send them.
- **The shooter (both main and follower) logged a disconnect** — `IsMainConnected`/`IsFollowerConnected` flipped false and back. On a bus this full, a device that misses its heartbeat window reads as gone.

### The key insight: it's the configuration, not the battery

This is the most important single result, so it gets its own spotlight. In Q23, the bus hit **100% utilization at t≈160 s while the robot was disabled, on a 12.72 V battery** — full charge, no load, nothing browning out. High-utilization samples appear throughout the log at healthy voltages (12.7 V, 10.8 V, 11.4 V). The bus was full because of the *fixed schedule of status frames the devices were told to broadcast*, not because the battery sagged.

The brownouts then made it worse in a second, separate way: when the battery dips low enough to reset a device, that device re-announces itself and dumps a burst of frames onto a bus that already has no room — which is how a power problem turns into a comms problem. But the underlying overload was there on a full battery.

There's corroborating evidence in the earlier events: MAREA had **worse brownouts than Newton in some matches** (Q19 and Q55 both dipped to ~5.9 V) yet threw **zero CAN receive errors** — because the bus was only ~50% full and had headroom to absorb the disruption. The CAN errors didn't appear because the brownouts got worse; they appeared because the bus lost its **headroom**.

---

## Part 4 — Root causes, from the code

**1. No `optimizeBusUtilization()` on any roboRIO-bus device.** This is the big one. By default, every Phoenix 6 device broadcasts its *entire* set of status signals at default rates. `optimizeBusUtilization()` turns off every signal you haven't explicitly asked for, typically cutting a device's traffic dramatically. The drivetrain code calls it on every module and the Pigeon. **None of the mechanism subsystems do.** So ~11 devices are each streaming their full default signal set, all match, most of it never logged or used.

**2. A handful of signals turned up far past what's needed.** From the subsystem code:

- `Hood.java`: `hood.getRawPulseWidthPosition().setUpdateFrequency(1000)` — **1000 Hz**. A single 1000 Hz signal is about **1000 frames/s ≈ 13% of the entire bus**, from one sensor reading.
- `Shooter.java`: `shooterMain.getMotorVoltage().setUpdateFrequency(500)` — **500 Hz** (a comment notes this is to tighten the hardware follower's tracking).
- `Intake.java`: `intakeRollerFollowerRight.getMotorVoltage().setUpdateFrequency(500)` — **500 Hz**, same follower reasoning.
- `Shooter.java` and `Feeder.java`: velocity at **100 Hz** each.

Those three high-rate signals (one at 1000 Hz, two at 500 Hz) alone account for **roughly a quarter of the bus's entire capacity** — and none of them need to be that fast. A follower motor tracks perfectly well at 100–200 Hz; a hood angle at 1000 Hz is ~4–10× more than any control loop can use.

**3. Device count and features grew all season.** The same layering that pushed the *power* draw up (MABOS → NECMP2 → Newton) pushed the *bus* load up in lockstep — every subsystem added is another unoptimized device broadcasting its full default signal set. That's the doubling you see in the table.

**4. (Interaction) brownouts on a bus with no slack.** Covered above — the power problem and the bus problem compounded specifically because there was no headroom left to absorb device resets.

---

## Part 5 — What to look out for in future designs

Ordered by impact. The first two are near-free and would have prevented every symptom above.

**1. Call `optimizeBusUtilization()` on every device, then turn *up* only what you need.** Make "optimize, then explicitly enable" the default pattern for every motor/sensor on the roboRIO bus, exactly as the drivetrain already does. This alone likely takes the disabled baseline from ~70% back toward ~30–40%.

**2. Stop over-cranking signal rates. Budget them.** Set each signal only as fast as something actually consumes it: control loops and logging rarely need more than 100 Hz, followers 100–200 Hz, and anything you only watch on a dashboard can sit at 10–50 Hz. Drop the hood's 1000 Hz to ~100–250 Hz and the two 500 Hz follower-voltage signals to ~100–200 Hz — that's ~20%+ of the bus recovered for the cost of four numbers. Motor-safety heartbeats should stay under ~45 ms (≥22 Hz) so nothing false-triggers a watchdog shutdown.

**3. Keep steady-state utilization under ~50–60%, and treat ~70% as a hard ceiling.** Headroom is the entire lesson of Newton vs. MAREA: the same disturbances were harmless at 50% and caused dropouts at 77%. Design the bus so a normal match sits near half-full, leaving room for faults, reconnects, and brownout-induced bursts.

**4. Balance the two buses.** You already own a CANivore and it's barely stressed. Moving some mechanism devices onto the CANivore (or adding a second CANivore for the mechanisms) splits the load across two buses and gives everything CAN FD's extra bandwidth. As a rule, don't pile a dozen devices onto the 1 Mbit/s roboRIO bus if a CAN FD bus is available.

**5. Instrument it so you see this coming.** You have the data — start watching it live. Log and dashboard `SystemStats/CANBus/Utilization` and the error counts, and put an alert on the driver dashboard (Elastic) when utilization crosses ~70% or when the receive/transmit error counts start climbing off zero. The bus was screaming for two events (NECMP2 at 91% p95) before it broke at Newton; a dashboard number would have caught it in the pit.

**6. Don't forget the physical layer.** None of the above matters if the wiring is marginal. A loose CAN connector, a missing/!damaged terminating resistor, or noisy routing next to power wiring will spike the error counts independently of how well you've budgeted frames. When error counts rise, check wiring and termination *first*, then look at frame rates. (The dead PDH logging noted in the brownout analysis — 24 channels then never updating — is worth a look here too: a device that init's on CAN and then goes quiet can indicate a wiring or termination issue on that leg of the bus.)

---

## Methodology & confidence

Utilization, error counters, brownout flags, battery voltage, enable state, and shooter connection status were read directly from the AdvantageKit `.wpilog` files (`/SystemStats/CANBus/*`, `/SystemStats/BrownedOut`, `/SystemStats/BatteryVoltage`, `/DriverStation/Enabled`, `/RealOutputs/Shooter/Is*Connected`) using a from-scratch WPILOG parser. Ten matches were sampled across all four events; the disabled-baseline figure is computed only from disabled-mode samples to isolate configuration load from gameplay. The utilization signal is logged on a 0–1 scale at ~2 Hz. CAN theory figures (1 Mbit/s, ~130–150 bits/frame, ~7,000 frames/s ceiling, error-passive at REC/TEC > 127, bus-off at TEC > 255) and the 70%/85% community thresholds are cross-checked against CTRE Phoenix and FRC community documentation. Frame-cost percentages (e.g. "1000 Hz ≈ 13% of the bus") are approximate — they depend on exact frame length and bit-stuffing — but are good enough to rank the offenders. Relative comparisons between matches and events are solid; treat the absolute percentages as ±a few points. Raw parsing/analysis scripts available on request.

---

# Addendum — Bus Cleanup Implementation Guide

*Added August 2026. A practical, code-level companion to the analysis above: exactly what to change, in what order, and how to verify nothing broke. Two independent changes — turning down the over-cranked rates, and enabling bus optimization — are best done as separate, testable steps.*

The guiding rule for the whole cleanup: **a status-frame rate only matters if something actually consumes the signal at that rate.** There are only two kinds of consumer — a software loop in the robot code that reads the value (which runs at 50 Hz), or a hardware follower that listens to its leader. All closed-loop *control* (Velocity, MotionMagic, TorqueCurrentFOC) runs on the device off its local sensor and consumes no bus frames at all. Cuts that respect this rule are safe; the only signals you must not starve are the ones a software loop or a follower actually reads.

## Step 1 — Turn down the over-cranked rates (low risk, ~¼ of the bus)

This step alone reclaims most of the bandwidth and touches no logic. Note the deliberate contrast: the velocity signals stay, the voltage/pulse-width boosts go.

| Device | Signal | Now | Change to | Why |
|---|---|---|---|---|
| Hood | `RawPulseWidthPosition` | **1000 Hz** | 50–100 Hz | Read only in software for calibration/homing (`getPulseWidthDeg`, offset). Hood MotionMagic uses the internal Minion rotor, not this frame — so the rate never affected control. Biggest single win (~13% of the bus). |
| Shooter (leader `shooterMain`) | `MotorVoltage` | **500 Hz** | 100 Hz | Feeds the hardware follower and the logged voltage. Measured follower tracking is already tight far below 500 Hz. |
| Intake (`intakeRollerFollowerRight`) | `MotorVoltage` | **500 Hz** | 50–100 Hz (or move to the leader) | This is set on the *follower*, which does not feed follower sync — the follower listens to the *leader's* frame. The intake follower already tracks its leader to 0.27 V RMS with the leader at default rate, so this boost has been doing nothing. |
| Shooter (leader) | `Velocity` | 100 Hz | **keep 100 Hz** | Read by `isReady()` (the at-speed gate). A real software consumer — cutting this delays shot timing. |
| Feeder | `Velocity` | 100 Hz | **keep 100 Hz** (50 OK) | Read in software. |

Rough saving: hood 1000→100 ≈ −12% of the bus, the two 500→100 ≈ −11% combined. About a quarter of the bus recovered before you even touch optimization.

## Step 2 — `optimizeBusUtilization()` per device, then re-enable what your code reads

Optimization is opt-in: after the call, every signal you haven't explicitly given a rate goes silent, and reading a silent signal returns a **stale value with no error**. So the work is: call `optimizeBusUtilization()` on each roboRIO-bus device, then add a `setUpdateFrequency(...)` for every signal your code actually consumes. The table below is that list, from a read-audit of the mechanism code. "Must" = something breaks if it's missing; "recommended" = keeps your logs valid.

| Device | Enable these signals | Rate | Priority — why |
|---|---|---|---|
| `shooterMain` (leader) | `Velocity` | 100 | **Must** — `isReady()` at-speed gate |
| | `MotorVoltage`, `DutyCycle`, `TorqueCurrent` | 100 | **Must** — CTRE requires the follower's leader to keep these enabled |
| | `Position` | 25–50 | Recommended — `@AutoLogOutput` telemetry |
| `shooterFollower` | `MotorVoltage`, `TorqueCurrent` | 25–50 | Recommended — logged (`FollowerVoltage`, `getFollowerCurrent`) |
| `m_spinner` (HotTub) | `StatorCurrent` **and** `Velocity` | 100 | **Must** — both feed `isStalled()`; without them the anti-jam stops firing. (Nothing is enabled on this device today.) |
| `intakeRollerMainLeft` (leader) | `MotorVoltage`, `DutyCycle`, `TorqueCurrent` | 100 | **Must** — follower's leader signals |
| `intakePivot` | `Position` | 25–50 | Recommended — telemetry; keeps `isConnected()` valid |
| `intakeRollerFollowerRight` | `MotorVoltage` | 25–50 | Recommended — logged |
| `hood` | `RawPulseWidthPosition` | 50–100 | **Must** — software calibration/homing |
| | `Position`, `TorqueCurrent` | 25–50 | Recommended — telemetry; keeps `isConnected()` valid |
| `m_turret` | `Position` | 100 | **Must** — feeds `getFacing()`, on-target, tether, and circumnavigation logic |
| | `TorqueCurrent` | 25–50 | Recommended — telemetry |
| `m_CANcoder` (turret) | `AbsolutePosition` | 100 | **Must** — turret homing/zeroing and the facing-sync check |
| | `MagnetHealth` | 10 | Recommended — health check |
| `m_retractomatic` | `TorqueCurrent` | 25–50 | Recommended — telemetry; keeps `isConnected()` valid |
| `m_feeder` | `Velocity` | 100 | **Must** — read in software (already enabled) |
| | `TorqueCurrent` | 25–50 | Recommended — telemetry |

Two notes. First, every `isConnected()`/`isAlive()` health check needs *at least one* signal still arriving from that device — the "recommended" rows cover the devices that would otherwise have nothing enabled. Second, a caution specific to this project: most of these getters are `@AutoLogOutput`, so AdvantageKit calls them every loop and writes the result to the log. If the underlying signal is silenced, the logged value silently freezes — which would quietly break the very kind of log analysis this report is built on. That's why telemetry signals are worth re-enabling at ~25–50 Hz, not just the control-critical ones.

Even so, this is still a large net reduction: enabling five to eight named signals per device at these modest rates is a small fraction of the full default signal set every device broadcasts today.

## Step 3 — Verify (bench, ~30 min per mechanism)

Because control still runs on-device, a mistake here shows up as a specific, visible feature failure — not an intermittent fault — so a short checklist catches everything:

1. **Shooter** reaches speed and shot timing feels unchanged (`isReady`).
2. **Hood** homes to its hard stop and hits commanded angles.
3. **Turret** zeros on enable, tracks a target, and the sync check passes.
4. **Anti-jam** still fires on the hot tub — stall a ball and confirm it reverses (this is the one most likely to regress, since it depends on `StatorCurrent` + `Velocity`).
5. **Both follower pairs** spin together — watch the logged `MainVoltage` vs `FollowerVoltage` track, the same check used in this analysis.
6. No `isHealthy()`/`isConnected()` check falsely trips at boot.

Then confirm the payoff from a fresh log: `/SystemStats/CANBus/Utilization` disabled baseline should fall from ~70% toward **~30–40%**, the enabled p95 should sit well under the 70% comfort line, and the receive/transmit error counts should stay at 0. That headroom is the goal — enough slack that a brownout or a device reset can no longer tip the bus into frame loss.
