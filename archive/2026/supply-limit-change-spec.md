# Supply Current Limit — Change Spec + As-Built (2026-08-24)

> **STATUS: IMPLEMENTED** on branch `current-limits` (commit pending your build/test). Both edits
> landed in **`src/main/java/frc/robot/subsystems/drive/ModuleIOTalonFX.java`** — not TunerConstants
> (see the corrected locations below). Scope was **power/brownout only**; the steer *stator* change
> stays parked.

## What was changed — two edits, both in `ModuleIOTalonFX.java`

### 1. Drive motors — tiered supply limit (replaced the flat 45A)

In the drive-config block (was `SupplyCurrentLimit = 45`, `SupplyCurrentLowerTime = 0`):

```java
driveConfig.CurrentLimits.SupplyCurrentLimitEnable = true;
driveConfig.CurrentLimits.SupplyCurrentLimit = 50.0;       // brief launch peak
driveConfig.CurrentLimits.SupplyCurrentLowerLimit = 35.0;  // sustained after 0.5s
driveConfig.CurrentLimits.SupplyCurrentLowerTime = 0.5;
```

Behavior (confirmed against current CTRE docs): `SupplyCurrentLimit` is the peak ceiling;
after the limiter is active for `SupplyCurrentLowerTime`, the ceiling drops to
`SupplyCurrentLowerLimit`. So: 50A peak, 35A sustained after 0.5s. Cruise/top-speed need is
~13A/motor, so 35A never touches normal driving; worst-case 4-motor sustained draw drops from
180A toward ~140A.

### 2. Steer motors — added a supply limit (there was none)

In the `turnConfig` block (after `ContinuousWrap`):

```java
turnConfig.CurrentLimits.SupplyCurrentLimitEnable = true;
turnConfig.CurrentLimits.SupplyCurrentLimit = 20.0;   // flat (LowerTime = 0 => no lower tier)
turnConfig.CurrentLimits.SupplyCurrentLowerTime = 0.0;
```

Flat 20A per steer motor. Caps the synchronized azimuth spikes (measured up to ~170–200A across
four modules) that stack onto drive peaks during brownouts, at negligible performance cost.

## Two important corrections to the original spec (found in the code)

1. **Both edits belong in `ModuleIOTalonFX.java`, not `TunerConstants.java`.** The template's
   `ModuleIOTalonFX` builds the **turn** config from a fresh `new TalonFXConfiguration()` and
   **never applies `constants.SteerMotorInitialConfigs`**. So the steer supply limit had to go into
   `turnConfig` there to take effect. The drive limit was already in `ModuleIOTalonFX` (that's the
   45A we measured), edited in place.

2. **The 60A steer *stator* limit in TunerConstants was never actually applied.** Because
   `turnConfig` ignores `steerInitialConfigs`, the azimuths have been running with Phoenix default
   current limits (stator limiting disabled) — which is exactly why the logs showed steer stator
   spikes to ~108A, well over the nominal 60A. This is now noted in a code comment. It doesn't
   change the parked decision, but when the stator limit is revisited it must be **set in
   `turnConfig`** (or `steerInitialConfigs` must actually be applied) to have any effect.

## Not changed (parked / out of scope)

- Steer **stator** limit — left at hardware default (effectively unlimited today, as found above).
  The 60→40A idea is deferred; revisit by setting it in `turnConfig`.
- Drive stator limit (`SlipCurrent`, 90A) — unchanged.
- Instrumentation (PDH total-current logging still dead), brownout-threshold restore, flywheel
  idle, shooting-stack sequencing — separate items.

## Next steps for you

1. **Build/deploy** to confirm it compiles (`SupplyCurrentLowerLimit` is valid in the installed
   2025+ Phoenix vendordep, which uses the `...LowerLimit`/`...LowerTime` naming — verified).
2. **Validation loop** (same measure → change → re-measure as the kV fix): re-log with supply
   current on and confirm — (a) drive supply clamps ~35A sustained / 50A brief, steer supply stays
   ≤20A and the 170–200A steer spikes are gone; (b) no performance regression — top speed, 0–4 m/s
   accel feel, azimuth crispness (ask the driver); (c) min bus voltage and time-below-8V improve.

## Estimated savings (from match-log simulation, for reference)

- Total power: drivetrain average draw down ~9–14% (~7–9% of full-robot draw) — modest by design.
- Peak: drivetrain instantaneous peaks down ~15–21%.
- Brownout: at sub-8V moments the caps remove ~30A avg (up to ~120–130A at worst spikes) → ~0.5V
  typical lift, up to ~2V at the worst instants. Turns many marginal dips survivable; won't
  eliminate brownouts alone (shooting-stack loads, untouched here, dominate the worst dips).
