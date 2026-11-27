# Steer / Azimuth Supply Current — Deeper Analysis (offseason drive tests, 2026-08-22)

Follow-up to the drivetrain supply-current analysis, focused on the four steer (azimuth) motors:
what they actually draw from the battery, why they spike, and what to do about it without hurting
swerve responsiveness. Same four AdvantageKit drive-test logs; per-module
`TurnSupplyCurrentAmps`, `TurnCurrentAmps`, `TurnVelocityRadPerSec`, resampled to 100 Hz.

> **Update (match data):** the teleop follow-up in `claude/steer-match-analysis.md` confirms this
> analysis on four real Newton matches — the same spiky pattern, scaled up (mean ~10A total, spikes
> to ~200A that land on the brownout dips). It also corrected one number quoted in the caveats below
> (see the struck-through note): real teleop steer draw is ~2.5A/motor / ~10A total, not the
> "~10A/motor" the July prose implied. The 20A/motor recommendation stands.

## The one-line answer

On the battery, the steer motors are **cheap on average but spiky** — median draw is ~0.1A per
motor, yet all four occasionally snap their azimuths at the same instant and stack into a
**90–170A** transient. There is **no steer supply current limit configured today** (only a 60A
*stator* limit). Adding a **~20A per-motor supply limit** clips those synchronized spikes almost
for free — it touches under 1% of steer samples and about 9% of the fastest slews, and cuts the
worst-case 4-module spike from ~170A to ~80A. That's the whole recommendation; everything below is
the evidence and the nuance.

## What the steer motors actually draw

| Quantity (fixed-kV runs) | Per motor | 4-module total |
|---|---|---|
| Median | ~0.1 A | ~0.4 A |
| Mean | 0.3–1.1 A | 1.2–3.2 A |
| 95th percentile | 2–4 A | ~10–15 A |
| 99th percentile | 11–14 A | 40–45 A |
| Peak | **50–53 A** | **93–170 A** |
| Share of drivetrain energy (amp-seconds) | — | **~5%** (auto) / ~10–13% (teleop) |

The distribution is even peakier than the drive motors': the median azimuth pulls essentially
nothing from the battery, but the tail runs all the way to ~53A on a single module. On *average*
the azimuths are a rounding error next to the drive motors (~5% of total drivetrain amp-seconds in
this auto test; ~10–13% in real teleop) — so this is not a "steer is eating your battery" story.
It's a "steer adds a sharp transient at exactly the wrong moment" story.

## Why the spikes happen: fast, *simultaneous* slewing

Steer supply current is almost entirely a function of **azimuth slew rate**, not holding torque
(Panel A):

| Azimuth slew rate | Mean per-motor steer supply |
|---|---|
| < 0.5 rad/s (holding) | ~0.1 A |
| 2–5 rad/s | ~1 A |
| 5–10 rad/s | ~3.5–5 A |
| > 10 rad/s (hard slew) | ~13–18 A (peaks 50–53 A) |

This is expected: an azimuth *holding* position needs torque but almost no speed, so applied
voltage — and therefore battery-side (supply) current — is tiny. Battery draw only appears when a
module is actively rotating fast. The big spikes are the moments the path optimizer flips several
modules 90–180° at once (e.g., a coordinated direction reversal at a waypoint). In the worst
observed spike (Panel C), all four modules peaked within the same ~0.1s window; across the fixed-kV
runs, **65% of the >50A total-steer spikes had three or more modules firing simultaneously.** They
are brief — total time above 50A is under 1% of the enabled window — but that's the nature of a
transient brownout trigger.

### The part that actually matters: it stacks

A 170A steer spike on its own wouldn't brown out a fresh battery. The concern is coincidence with
drive load. In run T4, a steer spike landed on top of the drive motors and the **combined
instantaneous drive + steer supply hit 241A** (vs a 193A worst case in T1, which had no big steer
spike). At the competition robot's ~16 mΩ source resistance, 241A is roughly **3.9V of
instantaneous sag** — and that's before any shooter or intake load. When the July brownout analysis
found the bus diving below 7V on "shoot-on-the-move" events, a synchronized azimuth flip is exactly
the kind of extra 90A that turns a survivable dip into a brownout. **The match analysis confirms
this directly:** in the four Newton matches, steer draw was *elevated* during the sub-7V moments and
its spikes there reached 121–204A.

## Current config (from `TunerConstants.java`)

```
steer stator current limit = 60 A   (StatorCurrentLimitEnable = true)
steer supply current limit = NONE   (not configured)
steer gains: kP = 100, kD = 0.5, kV = 2.49, kS = 0.1, ClosedLoopOutput = Voltage
```

The code comment next to the stator limit already says *"Swerve azimuth does not require much
torque output, so we can set a relatively low stator current limit to help avoid brownouts without
impacting performance."* That logic is right — it's just applied to the wrong limit. The **stator**
limit governs torque/heat; the **supply** limit governs battery draw, and it's the supply side that
feeds brownouts. There's no supply limit at all right now, which is why the spikes run free to
50A+/motor.

## Recommendation

**1. Add a steer supply current limit — this is the whole win.** Set roughly:

```
SupplyCurrentLimit      = 20 A     (per steer motor)
SupplyCurrentLowerLimit = 20 A
SupplyCurrentLowerTime  = 0        (or: peak 30 A, lower 20 A, time 0.2s if you want snap headroom)
```

The tradeoff modeled directly on the data (auto test; match teleop gives ~3.8% clipped at 20A —
same conclusion):

| Per-motor supply limit | 4-module spike ceiling | % of *all* steer samples clipped | % of *fast-slew* (>5 rad/s) clipped | Mean draw removed/motor |
|---|---|---|---|---|
| none (today) | ~170 A (auto) / ~200 A (teleop) observed | — | — | — |
| 25 A | 100 A | 0.30% | 4.7% | 0.03 A |
| **20 A** | **80 A** | **0.60%** | **8.7%** | **0.05 A** |
| 15 A | 60 A | 0.88% | 12.0% | 0.09 A |

A 20A cap removes essentially nothing from normal operation (0.6% of auto samples / 3.8% of teleop
samples, ~0.05–0.5A off the mean) because the azimuths almost never *need* more than 20A of battery
power — they only briefly *pull* it during the fastest slews. What it does remove is the top of the
synchronized spikes: the worst-case 4-module transient drops from ~170–200A to ~80A. If you want to
be conservative about azimuth snappiness, 25A is even safer; I'd start at 20A and only back off if a
driver actually feels lazy module response.

**Why performance barely moves:** at kV = 2.49, holding or slowly correcting an azimuth needs only
a couple of volts, well under a 20A supply draw. The limit only engages during the hardest
reorientations, and even then the module still slews — just a hair slower for a fraction of a
second. Swerve responsiveness is dominated by the wheel reaching approximately the right heading,
which still happens fast.

**2. (Optional, secondary) Lower the steer *stator* limit from 60A toward ~35–40A.** This doesn't
help brownouts much — stator draw at low azimuth speed barely reaches the battery — but it reduces
motor heating and the tread-scrubbing torque during azimuth hunting, which the July analysis
flagged as a tread-wear source. Their own comment endorses a low stator limit; 60A is generous for
a motor that "does not require much torque." Test that azimuths still track after lowering.

**3. (Optional) Soften the slew slam.** kP = 100 with Voltage output means a setpoint jump commands
near-full authority for a cycle, which is what makes several modules spike together. A small steer
`VoltageClosedLoopRampPeriod` (~0.05–0.1s) or a modest kP reduction would spread the same
reorientation over more time and lower the peak current — but this trades against azimuth
crispness, and the supply limit already solves the brownout problem more directly. Do the supply
limit first; only reach for this if spikes persist.

## Two honest caveats

1. **This auto data under-represents teleop azimuth activity** — now filled in by the match analysis
   (`claude/steer-match-analysis.md`). These are smooth auto-path runs; real teleop has
   rotate-about-turret and driver corrections that keep the azimuths busier. The match data shows
   teleop steer draws about 2× more on average and spikes higher (~200A) and more often than this
   auto test. ~~The July analysis found the azimuths drawing ~10A/motor in teleop.~~ **Correction:**
   the real teleop figure is **~2.5A/motor (~10A total for all four)** — the July write-up's prose
   ("~10–11A each") mislabeled its own table's four-motor total as per-motor. The draw is
   intermittent, not continuous (teleop median ~0.36A/motor). The 20A/motor supply limit still
   applies and is confirmed cheap in teleop (3.8% of samples clipped).

2. **Supply vs stator — keep them straight.** The azimuths' *stator* current is real and not tiny
   (mean 3–6A/motor, peaks to 60A) — that's torque, heat, and tread scrub. But their *supply*
   (battery) current is small except during fast slews. Brownouts are a supply-side problem, so the
   supply limit is the right lever; the stator limit is about thermals and mechanical wear. Because
   teleop steer supply is low on average, the "calm the azimuths / don't re-point at zero speed"
   idea saves little on *brownouts* — its value is stator heat and tread wear. Don't let the healthy
   average steer supply number talk you out of the tread/thermal concern, and don't expect the
   stator limit (or hunting fixes) to fix brownouts.

## Bottom line

Steer isn't where your big power savings live — it's ~5% of drivetrain energy in auto, ~10–13% in
teleop. But it's currently the one drivetrain load with **no supply limit at all**, and it produces
90–200A synchronized transients that stack onto drive peaks (241A combined observed in auto; steer
spikes to 121–204A during the actual Newton brownout dips). A 20A/motor steer supply limit is about
as close to free as a brownout mitigation gets: near-zero performance cost, one config line per
module, and it removes the worst steer spike from your instantaneous stack — worth up to ~1–2V at
the worst steer-driven instant (see match analysis). Pair it with the drive supply limit and the
shooting-stack fixes, which own the bigger share of the load.

*Method: per-module steer supply/stator/velocity from the four `.wpilog` files, zero-order-hold
resampled to 100 Hz over the enabled window; supply-vs-slew relationship binned by |azimuth
velocity|; simultaneity measured as modules >15A during total-steer >50A spikes; supply-limit model
caps per-motor steer supply and recomputes clip fractions and 4-module peak. Config read from
`frc-88/2026-Robot` `TunerConstants.java`. Teleop match confirmation in `steer-match-analysis.md`.*
