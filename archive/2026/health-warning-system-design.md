# Robot Health Warning + LED Annunciator — Design Sketch

*A framework to spin out as a separate side project later. This is deliberately a design sketch, not an implementation — it captures the shape of the system, the decisions already made, and the open questions, so it can be picked up cold. Motivated by the CAN over-utilization issue (see `can-bus-analysis.md`): the bus crept from ~30% to ~70% over a full season with nobody watching the number, and the failure at Newton was invisible to anyone just watching the robot play. The goal here is to make that class of slow, invisible problem announce itself.*

*Updated 2026-09-23: added the fault taxonomy ("ladder of failure depth"), the detection primitives, and a staged implementation priority. The taxonomy is meant to be the checklist the code is written against — it deliberately generalizes over "what can fail on any robot" rather than cataloguing the specific bugs we hit last season (history calibrates thresholds and priorities within a category; it should not be what generates the categories).*

*Updated 2026-09-23 (later): severity vocabulary changed from RED / YELLOW to WPILib's own `AlertType.kError` / `AlertType.kWarning`, matching the draft code on the `alerts` branch. Colors describe how a fault is **shown**, which is the LED code's decision; the fault itself should only say how urgent it is. See "Severity model" below.*

*Updated 2026-09-23 (later still): the lights now **ask** the health system what to show, instead of the health system **pushing** to the lights. The `Annunciator` interface (and its log-only stand-in) was removed from the draft code; `HealthMonitor.getEndOfMatchDisplay()` replaces it. The health system produces the data; the LED subsystem takes it in and decides what to do with it. See Layer 3.*

## What it's for

Some robot problems are invisible from the stands. A CAN bus filling up, a motor that isn't spinning when commanded, a sensor that dropped off — none of these necessarily look wrong during a match. The logs capture the details, but nobody reads logs between every match. This system's job is narrow: **surface an otherwise-invisible problem to the humans, at a moment they'll see it, so they can decide whether to act before the next match.** It is an attention-getter, not a diagnostic tool — the logs remain the source of truth for *what* happened.

## The core principle: detect, aggregate, annunciate — kept separate

The one architectural idea that makes this survive multiple build/competition seasons is keeping three concerns decoupled:

1. **Detection** — code that decides "this specific thing is wrong right now" and raises a warning.
2. **Aggregation** — a central place that collects all active warnings, tracks severity, and remembers whether anything fired this match.
3. **Annunciation** — the lights (and dashboard) that show a warning is present.

If these are tangled, every new warning next year means editing the lights code, and every change to how the lights behave means touching detection. Kept apart, each side grows on its own: adding a warning is "write a detector and register it," and the LED behavior comes along for free.

## Layer 1 — Detection (the warning value)

Most of this already exists in the codebase for free: the robot uses WPILib `Alert`s (they log under `/RealOutputs/Alerts`). An `Alert` *is* the monitorable warning value — set it true, and it surfaces on the dashboard/Elastic and gets logged automatically. So a detector's job is just to watch its signal and flip an `Alert`.

Design rules for detectors, so they stay lightweight and honest:

- **Don't trigger on raw noise.** Grounded in the offseason data: the CAN utilization signal shows isolated single-sample spikes to ~84% that mean nothing. A raw threshold would false-alarm constantly. Trigger on *sustained* conditions (utilization above a threshold for a debounced window — WPILib's `Debouncer` is one line) or on signals that are already noise-free. For CAN specifically, **any receive/transmit error count climbing off zero** is the cleanest possible trigger — the bus reporting its own distress.
- **Each detector owns one concern** and produces a warning carrying a `name` and an `AlertType`. It knows nothing about lights.

See the fault taxonomy below for the full generalized catalog of *what* to detect, and the detection primitives for the handful of reusable detector shapes those all reduce to.

## Layer 2 — Aggregation (with severity and a per-match latch)

A small central collector answers two questions:

- **"Is anything wrong right now?"** (and at what highest severity) — for live dashboard use.
- **"Did anything go wrong at any point this match?"** — this needs a **latch**: a sticky flag that remembers a warning occurred even after it clears, so the end-of-match display still fires if the bus spiked and recovered mid-match.

The aggregator is **generic** — it collects warnings by name + `AlertType` and knows nothing about CAN. That genericness is the durability payoff: next year's battery warning, low-pressure warning, or dropped-camera warning registers here and inherits the whole annunciation path with no new wiring.

### Severity model (decided)

Severity uses WPILib's existing `AlertType` directly — no separate vocabulary:

- **`AlertType.kWarning` = mid urgency.** A real problem worth knowing about, but not worth interrupting the team for. On a tight match turnaround you'd leave the team alone and look at it when there's time. *CAN over-utilization is the canonical warning.*
- **`AlertType.kError` = high urgency.** Something you'd stop the normal between-match process to investigate. Examples to grow into: a motor that isn't running when commanded, a key sensor missing.
- **`AlertType.kInfo` is not a fault level.** It stays available for ordinary status messages. (The draft code treats a fault declared as `kInfo` as `kWarning` and prints a Driver Station warning, rather than crashing at boot.)

**Why not colors:** an earlier draft named the levels RED and YELLOW. That put display vocabulary into the detection layer, against the core principle above — a fault would be declaring how it should be *shown* rather than how urgent it *is*. `kError` / `kWarning` are also the words the dashboard's Alerts widget and the logs already use, so code, dashboard and log all say the same thing. Which color (or pattern) an error or warning gets is decided only by the LED code.

This is explicitly a **"know it when I see it"** vocabulary — the type gets assigned per-trigger as detectors are added, not by a rigid rulebook. Two levels is the starting point. Error outranks warning whenever the aggregator has to pick the most urgent one.

### Reset scope (decided, with a noted nuance)

- **Per match** is the working default. The question the system answers is "do we need to fix anything before the next match," so the latch should span the whole match (auto + teleop as one unit) and reset at the start of the next one.
- **Per enable** is worth considering for **bench/testing** outside match scenarios, where each enable is a discrete test and you'd want a fresh state each time. Open nuance to resolve when building: because the warning *display* is intended for end-of-match (while disabled), mid-match enable transitions wouldn't show lights anyway — so per-enable mostly matters for the testing workflow, not competition. Possibly fine to make the reset scope a mode-dependent setting (per-match in a real match, per-enable on the bench).

## Layer 3 — Annunciation (the display asks; the monitor answers)

The health monitor does not command the lights. It **publishes** what it thinks should be shown, and the lights subsystem **reads** it:

- `HealthMonitor.getEndOfMatchDisplay()` returns `kError` or `kWarning` for a few seconds after a match ends with a latched fault, and nothing (`null`) the rest of the time. The same value is logged as `Health/EndOfMatchDisplay`.
- The LED subsystem calls it every loop in its own `periodic()` and decides *how* to show it (which color, flashing or solid). This is the only place in the system where colors are chosen.

The dependency points the natural way: the display depends on the thing it displays. The health system knows nothing about LEDs; the LED code knows about health (and about whatever else it shows). An earlier draft had the monitor push to the lights through an `Annunciator` interface (`indicate(type)` / `clear()`). With no LED subsystem yet, that interface had one log-only stand-in and duplicated a log key the monitor already wrote, and it left "who wins the LEDs" unsolved. Having the lights ask fixes both.

Note: there is no lights/LED subsystem in the current code, so the health result is visible today only in the log (`Health/EndOfMatchDisplay`) and the dashboard summary alert. When an LED subsystem is built, it reads the method above — no change to the health code needed.

**When it fires:** the end of a match is a clean lifecycle edge — the robot is disabled when the match ends, so the trigger is "on transition to disabled, if the match latch is set, run the warning routine for a few seconds." It's also a good moment because nothing else is competing for the LEDs (no alliance-color or game-piece pattern to fight).

**Arbitration** (who wins when two things want the LEDs) is the part that gets messy as LED uses accumulate over the years. Because the LED subsystem is the one asking, arbitration lives in exactly one place: its `periodic()` checks its inputs in priority order (e.g. e-stopped → health error → health warning → alliance color → idle) and shows the first that applies. Mechanical Advantage's 2026 `Leds` subsystem (in this project's reference code) is built this way. Within health, an error outranks a warning — the monitor already reports only the more urgent of the two.

## The MVP vs. the framework

The point of all the above is that the *first version is small* — roughly one `Alert`, one `Debouncer`, one latch boolean, and one method the lights subsystem reads. What earns its keep over multiple seasons is the *shape*: **detect → aggregate (severity + latch) → intent-based display.** That shape is what lets new warnings and new indicator behaviors snap in later without rework.

---

## The fault taxonomy — a ladder of failure depth

This is the generalized answer to "what should we detect." It is built on purpose *not* from last season's bug list but from the ways any component on any robot can fail. History still matters — but for a narrower job: it validates that a category is worth covering and it calibrates the thresholds *inside* a category. It should not be the thing that generates the categories, or the system will only ever be good at re-fighting the last failure.

The organizing idea: stop thinking about *mechanisms* (shooter, drive, arm) and think about *how far a component has fallen*. Any device sits on a ladder, and each rung down is deeper, harder to detect, and more prone to false positives than the one above it:

1. Is it there?
2. Is it well enough to work?
3. Is it telling the truth?
4. Is it doing what it's told?

Plus two families that aren't *devices* but sit underneath all of them: did the robot start up correctly, and is the platform (code, loop, comms) healthy. Almost every alert we will ever want is an instance of one of these six. A new alert next year becomes "which rung, which device" rather than a blank page. The rungs also happen to be ordered by increasing detection difficulty and false-positive risk, which is why the staged rollout below builds them bottom-up.

### Rung 1 — Presence / connectivity  *(build first · mostly kError)*
*Is every device that should be on the bus actually there?* The `isConnected()` / `isAlive()` check already present in every subsystem, generalized to a complete roster: every TalonFX, every CANcoder, the Pigeon, the PDH, the pneumatics hub, a second CANivore bus if run. Detector is a debounced boolean — trivial, which is exactly why it should be *exhaustive*: the value is coverage, not cleverness. A CANcoder that falls off is invisible from the stands until the robot drives sideways.
- **Detection shape:** debounced threshold (boolean).
- **Gotcha:** needs a **startup grace period** — everything reads disconnected for the first ~1–2 s after boot; don't annunciate during it.

### Rung 2 — Power & thermal (the enabling conditions)  *(build first · brownout kError, rest kWarning)*
*Is the device well enough to do its job, even if it's present?* Two sub-families, both threshold-on-a-slow-signal.
- **Power budget:** battery voltage sag, the brownout flag, total current vs. budget, and per-channel current off the PDH. The per-channel check is general and underused: a channel near its breaker rating is an *impending trip* you can warn about before it happens; a channel reading ~0 when its mechanism is commanded is a *blown breaker or disconnected lead* downstream of a controller that still looks healthy — a failure Rung 1 cannot see. (See `brownout-analysis.md` for thresholds.)
- **Thermal:** motor / controller / RIO temperatures. Slow-moving, so light debounce, but **latch** so a mid-match peak is remembered even if it cools before anyone looks.
- **Detection shape:** debounced threshold; thermal also latched.
- **Gotcha 1 — inrush:** everything spikes ~200 ms on every enable and every mechanism start, so every detector here must be *sustained*, never single-sample.
- **Gotcha 2 — signal rate:** under `optimizeBusUtilization`, a temp/current signal won't refresh unless given an explicit `setUpdateFrequency`, or the alert reads a stale zero and silently never fires. (Hit exactly this in the shooter review.)

### Rung 3 — Sensor plausibility & cross-check  *(build second · kError for control-critical sensors, else kWarning)*
*The device is present and reporting — is it lying?* "Connected" says nothing about whether the number is real. Three patterns:
- **Range check** — value physically impossible (NaN, encoder outside its mechanical band, an impossible current). Cheap, zero false positives, worth doing everywhere.
- **Stuck check** — value *not changing* while the mechanism is known to be moving (a dead encoder often reports a frozen valid-looking number, not a disconnect). Needs a "should be moving" gate.
- **Redundancy / disagreement** — two sources that should agree, diverge: relative vs. absolute encoder on one shaft (adjacent to the kV work), Pigeon yaw drifting while known-stationary, vision pose vs. wheel odometry beyond tolerance, a limit switch that never toggles across a full sweep.
- **Detection shape:** range = threshold; stuck = intent-gated (delta over a window while commanded to move); disagreement = cross-signal comparison.
- **Gotcha:** highest-effort category, most valuable; disagreement thresholds need tuning and "stuck" needs the moving-gate to avoid firing at rest.

### Rung 4 — Command vs. response (closed-loop divergence)  *(build second · almost always kError)*
*Did the robot do what it was told?* Commanded a speed / position / heading and the measured value didn't get there within a settling window. The deepest rung and the highest value: it catches a stripped gear, a thrown chain, a slipping belt, a seized bearing — the controller is healthy, the sensor is truthful, and the mechanism *still isn't moving*, which nothing above this rung can see. (The shooter "commanded but not at speed" idea is one instance; a drive module not reaching commanded velocity, or an arm not reaching setpoint, are others.)
- **Detection shape:** intent-gated cross-signal — `|commanded − measured|` large for a sustained time, armed only when enabled AND actively commanding AND past a settling window.
- **Gotcha:** the false-positive minefield. Divergence is only a fault if you were *actually commanding* the mechanism, and that intent usually lives in the coordinator (RobotContainer / superstructure), not the subsystem — exactly the wall the shooter hit, where `targetVelocity` is set every loop but the motor is only driven while shooting. Get the gates right and it's the most powerful thing in the system; get them wrong and the team learns to ignore the lights within a week.

### Cross-cutting A — Startup / configuration  *(build first · one-shot, latched · kError/kWarning)*
*Did the robot come up correctly?* Checked once at boot/init and latched: config-apply returned an error, a device on the wrong firmware, a required preference or auto path that failed to load, calibration incomplete. The sneaky-valuable member is **mid-match reboot detection**: a device that browns out and reboots comes back with *default config* unless re-applied, so a Talon that reset mid-match is a live device reporting garbage gains — watch each device's reset/uptime counter for a jump during the match.
- **Detection shape:** one-shot check, latched; reboot = latched transient on a reset counter.

### Cross-cutting B — Platform / software / comms health  *(build first · mostly kWarning, comms-loss kError)*
*Is the code and its plumbing healthy?* The "slow, invisible, nobody's watching the number" class this whole project was born from: loop overruns (periodic > 20 ms), CAN utilization sustained high **and CAN error counts off zero** (cleanest trigger in the system — the bus reporting its own distress), uncaught-exception counters, RIO CPU/RAM, DS/FMS comms drops and packet loss.
- **Detection shape:** counters-off-zero (latched transient) and debounced threshold.

## Detection primitives (the reusable shapes)

Cutting across all six categories there are only ~four detector shapes; every alert is one of them with different signals plugged in. This is what makes the system "build off of" rather than a list — the code side is these primitives, not N bespoke checks.

1. **Debounced threshold** — a condition that must persist (power, thermal, connectivity, sustained current). `Fault` with a nonzero debounce.
2. **Latched transient** — a single sample matters and should be *remembered*, not required to persist (a follower-current spike, a device reset-counter jump, a brownout blip, a CAN error count leaving zero). `Fault` with zero debounce, relying on the latch. *Sustained conditions → debounce; rare transients → latch. Reversing the two is how you either miss the spike or drown in false alarms.*
3. **Cross-signal / disagreement** — two signals compared to a tolerance (redundant sensors; commanded vs. measured). Same helper, the condition is just a comparison.
4. **Intent-gated** — any of the above, but armed only when the robot is enabled / actively commanding / past a settling window. **This is the one primitive the current `Fault` helper lacks, and it is what unlocks Rungs 3 and 4.** Concretely: add an "arming" `BooleanSupplier` to the detector, so a check can be *defined* in a subsystem but *gated* by state the coordinator owns.

## Implementation priority (where to start)

Bottom-up, because the lower rungs are cheap, universal, and near-zero false positives, and they're all shapes the `Fault` helper already supports:

- **Wave 1 (first event):** Rung 1 (presence), Rung 2 (power/brownout/thermal), Cross-cutting A (config + mid-match reboot), Cross-cutting B (CAN errors, loop overruns). A complete, trustworthy annunciator built entirely from debounced-threshold and latched-transient detectors. No intent-gating required.
- **Wave 2 (once the intent-gating primitive exists):** Rung 3 (plausibility / cross-check) and Rung 4 (command-vs-response). Highest value, but the false-positive discipline has to be earned, and the arming gates need coordinator state.

History re-enters here in its correct role: it doesn't pick the categories, it prioritizes and tunes *within* them — the CAN work says error-counts-off-zero belongs in Wave 1, `brownout-analysis.md` sets the voltage threshold, the shooter review supplies the follower-current number and the thermal signal-rate warning.

## How the `Fault` helper maps to this framework

The prototype `Fault` helper (bundles an `Alert` + `Debouncer` + `Logger.recordOutput` + a self-registry) is already most of Layers 1–2:
- Each `Fault` **is a detector** (Layer 1): one concern, a name + `AlertType`, knows nothing about lights.
- `Fault`'s static registry is the **seed of the aggregator** (Layer 2): `Fault.all()` is the collection; `hasEverBeenActive()` is the **per-match latch**.
- Still to add: a `resetLatch()` / `Fault.resetAll()` called on the autonomous-init edge to realize the decided per-match reset scope; the **intent-gating** arming supplier (primitive #4); and the end-of-match roll-up that the lights read through `getEndOfMatchDisplay()` (Layer 3).

## Illustrative interfaces (sketch only — not final)

```
// A detector produces warnings; knows nothing about lights.
// Urgency is WPILib's AlertType: kError (high) or kWarning (mid). kInfo is not a fault level.
record Warning(String name, AlertType type, boolean active)

interface HealthCheck {
    Warning check();                 // called periodically
}

// Central aggregator: generic, collects by name+type, tracks latch.
class HealthMonitor {
    void register(HealthCheck check);
    boolean anyActive();             // right now
    AlertType highestActive();       // kError outranks kWarning
    boolean latchedThisMatch();      // did anything fire since last reset
    void resetLatch();               // called on match/enable start per scope
    AlertType getEndOfMatchDisplay(); // kError / kWarning for a few s after the match, else null
}

// Lights (future LED subsystem): asks every loop, owns every LED decision including color.
class Leds {
    void periodic() {
        AlertType health = HealthMonitor.getInstance().getEndOfMatchDisplay();
        if (estopped)                          showEstopPattern();
        else if (health == AlertType.kError)   showHealthError();    // color chosen here
        else if (health == AlertType.kWarning) showHealthWarning();
        else                                   showAllianceColor();  // ...other uses, in priority order
    }
}
```

## Open questions to settle when building

- **Reset scope mechanics** — per-match in competition, per-enable on the bench? Make it a setting, or pick one?
- **Debounce/threshold values** for the CAN detector specifically — what sustained utilization %, over what window, counts as a warning; confirm error-count-based trigger is preferred.
- **Intent-gating source** — where the "actively commanding" signal for Rung 4 detectors comes from (per-subsystem flag, or a superstructure state the monitor reads), and how a subsystem-defined detector receives it cleanly.
- **LED priority order** — the mechanism is settled (the LED subsystem's own priority chain, see Layer 3); still open is where the health display sits relative to other LED uses (e-stop, alliance color, game-piece indication).
- **Display duration** at end of match, and whether it should repeat/persist until acknowledged or the robot is re-enabled.

*(The taxonomy above supersedes the earlier short "first detectors" list: Rung 1 = device disconnected, Rung 4 = motor commanded but not moving, Cross-cutting B = CAN over-utilization, Rung 2 = battery/brownout — each now placed on its rung with a detection shape, severity default, and gating notes.)*
