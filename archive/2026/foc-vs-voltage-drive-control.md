# FOC vs. Voltage Drive Control — Analysis & Recommendation

*Comparison of Team 88's (TJ²) drive control against Team 1768's (Nashoba) FOC approach, with guidance for future robots. Both teams run the same AdvantageKit TalonFX swerve template, so this comes down to one configuration choice — not two different codebases.*

## Bottom line up front

The two robots are running **the same swerve code**. The only meaningful difference in how the drive motors are commanded is a single enum in `TunerConstants`:

- **Team 88 (you):** `ClosedLoopOutputType.Voltage` for both drive and steer.
- **Team 1768 (Nashoba):** `ClosedLoopOutputType.TorqueCurrentFOC` — this is the "FOC" you found.

Neither is universally "better." FOC gives a real but modest performance ceiling (~15% more peak power) plus a cleaner, more physically-honest way to do traction control — at the cost of a paid per-motor license and a hardware lock to Kraken/Falcon (TalonFX). Voltage control is free, simpler for students, and works on any motor you might switch to, including the Minion/TalonFXS modules you already keep code for. For a team that wants the absolute best drivetrain and is happy to buy and manage licenses, FOC is the better ceiling. For a team that values simplicity, cost, and hardware flexibility, voltage is the safer default.

Two important nuances that most teams get wrong are covered below: "FOC" and "torque-current control" are **not the same thing**, and your *current* voltage setup may already be running FOC commutation without you realizing it — or may be silently falling back to non-FOC. Which one depends entirely on whether your controllers are Pro-licensed.

## What each team actually runs (from the code)

Both teams use the Littleton Robotics / AdvantageKit `ModuleIOTalonFX`. That file drives the motors through a `switch` on the control-output type that comes straight from `TunerConstants`:

```java
// setDriveVelocity(...) — identical in both repos
switch (constants.DriveMotorClosedLoopOutput) {
  case Voltage -> velocityVoltageRequest.withVelocity(velocityRotPerSec);
  case TorqueCurrentFOC -> velocityTorqueCurrentRequest.withVelocity(velocityRotPerSec);
}
```

So the behavior is decided entirely by these two lines in `TunerConstants.java`:

| | Team 88 (yours) | Team 1768 (Nashoba) |
|---|---|---|
| `kDriveClosedLoopOutput` | `Voltage` | `TorqueCurrentFOC` |
| `kSteerClosedLoopOutput` | `Voltage` | `TorqueCurrentFOC` |
| Drive gains | `KP=1.5`, `KS=0`, `KV=0.871` (**volts**) | `KP=32.5`, `KS=3.18`, `KV=1.2` (**amps**) |
| Steer gains | `KP=100`, `KV=2.49` (**volts**) | `KP=3750`, `KD=50`, `KV=1.94` (**amps**) |
| Slip / stator current | 90 A | 80 A |
| Drive motor type | `TalonFX_Integrated` (Kraken/Falcon) | `TalonFX_Integrated` (Kraken/Falcon) |
| Supply current limits | **Yes** — 50 A → 35 A after 0.5 s (drive), 20 A (steer) | **None** — stator/slip limit only |
| Phoenix Pro license | Not required for Voltage | **Required** per device |

I've now confirmed both configs directly from the code. The gain rows above are the single clearest illustration of the "different currency" point: the numbers aren't different because one team tuned better — they're in **different units entirely**. Your drive `KP=1.5` is volts-per-error; theirs is `32.5` amps-per-error. Your `KS=0` (you don't compensate static friction at all); their `KS=3.18` means they characterized ~3.18 A of torque-current to break friction, which is natural to express when you command torque. None of these numbers transfer between the two approaches — switching output type means re-tuning the drivetrain from scratch.

Also worth noting: Nashoba runs **no supply-current limiting anywhere** — their only ceiling is the 80 A stator/slip limit. That's actually coherent with torque-current control: because they command amps directly, the slip-current limit *is* the command ceiling, so traction limiting falls out of the control method itself. You accomplish a similar goal on the voltage side by explicitly adding supply-current limits (50→35 A) in `ModuleIOTalonFX`. (A few other differences — their 6.23 drive ratio and 4.75 m/s top speed vs. your 7.03 / 4.39, and their `kCoupleRatio=0` vs. your 4.5 — are unrelated gearing/characterization choices, not control-method differences.)

One thing worth flagging: your `ModuleIOTalonFX` has been customized with **supply-current limits** (50 A rolling back to 35 A on the drive motors, 20 A on steer) that the stock template — and, by extension, Nashoba's file — does not have. That's a power-management decision that is arguably *more* relevant to your brownout concerns than the commutation method, and it's independent of FOC.

## The part most teams conflate: two separate knobs

When people say "we use FOC," they're usually collapsing two different things into one:

**1. Commutation mode — how the motor windings are actually energized.**
FOC (Field-Oriented Control) commutation drives the three phases with sinusoidal, rotor-angle-aware currents instead of the simpler trapezoidal scheme. CTRE's own docs put the benefit at **"~15% peak power on supported devices,"** plus smoother low-speed behavior, less torque ripple, and slightly lower heat. This is a Phoenix Pro (licensed) feature.

**2. Control currency — what quantity your closed loop commands.**
- **Voltage control** commands volts. Your feedforward gains (`KS`, `KV`, `KA`) are in volts, which maps directly to WPILib's SysId tooling that students already learn.
- **Torque-current control** (`TorqueCurrentFOC`) commands *amps*, i.e., torque (torque ≈ kt · current). CTRE describes it as directly controlling the **acceleration** of the motor rather than its velocity.

Here's the subtlety that changes the whole picture:

> In Phoenix 6, the plain voltage requests (`VoltageOut`, `VelocityVoltage`, `PositionVoltage`) have an `EnableFOC` flag that **defaults to `true`**. `TorqueCurrentFOC` requests *require* FOC and have no such fallback.

That means:

- If your controllers **are** Pro-licensed, your existing `Voltage` setup is *already using FOC commutation* — you're getting the ~15% — you just aren't doing torque-current control.
- If your controllers are **not** licensed, those same voltage requests silently fall back to trapezoidal (non-FOC) commutation, no error, and you're leaving the 15% on the table.
- Nashoba's `TorqueCurrentFOC` choice **forces** the licensed path: it gives them FOC commutation *and* torque-based control, but if a license ever lapses or an unlicensed spare controller goes on the robot, that motor **disables its output and throws an `UnlicensedFeatureInUse` fault** — a hard failure at an event, not a graceful degrade.

So the real question for future projects isn't "FOC yes/no." It's: *do we want to command torque (amps) instead of voltage, and are we willing to hard-depend on a paid license to do it?*

## Benefits of FOC / torque-current control (why 1768 does it)

- **~15% more peak power.** Quicker acceleration off the line, more push in a shoving match, a touch more top-end. Real, but it only shows up at the extremes of the motor's capability.
- **Torque-current control makes traction limiting exact.** When you command amps, you're commanding torque directly. Wheel-slip prevention and slip-current limiting become a native, precise thing rather than something you approximate through a voltage loop. This is the single most compelling reason to switch.
- **Acceleration is invariant to battery voltage.** A voltage command means less torque at 11 V than at 13 V; a current command delivers the same torque regardless of pack sag. Late-match and during high-draw moments, the robot accelerates consistently — and it makes your motion profiles and autos more repeatable.
- **Physically honest feedforward.** `KS`/`KA` in amps map cleanly to motor physics, which can make model-based control and simulation more accurate.
- **Smoother, quieter, cooler at low speed** thanks to sinusoidal commutation — a minor but nonzero efficiency/thermal win that compounds over a match.

## Costs of FOC

- **Phoenix Pro license, per device, per season.** Licensing is per-motor-controller (CTRE store currently lists it "from $10" per device). A swerve drive is 4 drive motors, and if you FOC the steer motors too, 8 controllers. That's a recurring seasonal cost and one more thing to track and renew.
- **Hard failure mode if unlicensed.** `TorqueCurrentFOC` doesn't degrade gracefully. An expired license or an unlicensed swapped-in controller = dead motor + fault at the worst possible time. Voltage's silent fallback is much friendlier operationally.
- **Hardware lock-in to TalonFX (Kraken/Falcon).** **The TalonFXS does not support `TorqueCurrentFOC` at all.** You maintain a `ModuleIOTalonFXS` variant (Minion motors) — if you ever standardize on Minion + TalonFXS, torque-current FOC is simply off the table. This is a genuine constraint on future motor choices.
- **Steeper learning curve.** Torque-current control is an acceleration loop with gains in amps — less intuitive for students than volts, and disconnected from the SysId/WPILib feedforward workflow most people learn first.
- **Modest real-world delta.** For the majority of driving, a well-tuned voltage drivetrain (like yours, with a retuned `KV` of 0.871) is very hard to tell apart from an FOC one. The 15% is a peak-capability figure, not a 15%-everywhere figure.

## Benefits of voltage control (your current approach)

- **Free and license-independent.** No per-device cost, no renewals, no lapse-at-an-event risk.
- **Motor-agnostic.** Works identically on TalonFX and TalonFXS/Minion. Your drivetrain code doesn't care what motor you bolt in next year — a real advantage given you already keep a Minion module implementation.
- **Simpler mental model for students.** Volts, `KV`, `KS`, and the standard SysId workflow. Easier to teach, easier to debug.
- **Graceful degradation.** If a licensed feature isn't available, voltage requests just fall back — the robot still drives.
- **You've already tuned it and paired it with real power management.** Your retuned `KV` plus the supply-current limits you added (50→35 A drive, 20 A steer) address the brownout/power side directly. That current-limit work is arguably the higher-leverage move for your stated concerns, and it's fully compatible with voltage control.

## Recommendation for future projects

Think of it as a decision tree, not a verdict:

**Choose FOC / `TorqueCurrentFOC` if** you're committed to Kraken/Falcon (TalonFX) drive motors, you're willing to buy and manage Pro licenses on every drive controller, and you specifically want exact traction/slip-current control and voltage-sag-invariant acceleration. This is the right call for a team chasing the best possible drivetrain ceiling — which is exactly why 1768 chose it.

**Stay on voltage if** you value cost, simplicity, and hardware flexibility — especially if there's any chance you move toward Minion + TalonFXS, where FOC isn't even available. A well-tuned voltage drivetrain with good current limits (which you already have) is more than competitive for the vast majority of match play.

**The middle path most teams overlook:** if you buy Pro licenses but *keep* `ClosedLoopOutputType.Voltage`, your voltage requests get FOC commutation automatically (`EnableFOC` defaults true) — you capture the ~15% peak-power benefit while keeping volt-based tuning, the SysId workflow, and graceful fallback. You give up torque-current control (the exact-traction part), but you keep everything simple. This is a very reasonable "80% of the benefit, 20% of the complexity" option.

**A concrete first step you can take today, for free:** check whether your drive controllers are currently Pro-licensed (Phoenix Tuner X will show it). If they are, you're already getting FOC commutation on your voltage requests and the only thing 1768 has that you don't is torque-current control. If they aren't, you now know exactly what the 15% would cost to unlock and can decide whether it's worth it — without changing a line of code either way.

## Appendix — where this lives in the code

- **Control switch:** `src/main/java/frc/robot/subsystems/drive/ModuleIOTalonFX.java` → `setDriveVelocity`, `setDriveOpenLoop`, `setTurnPosition` (the `Voltage` vs `TorqueCurrentFOC` switch).
- **The actual choice:** `TunerConstants.java` → `kDriveClosedLoopOutput`, `kSteerClosedLoopOutput`. Yours is `frc/robot/generated/TunerConstants.java`; Nashoba's is under `.../drive/generated/`.
- **Your added power management:** supply-current limits in `ModuleIOTalonFX.java` (drive `SupplyCurrentLimit=50`, `SupplyCurrentLowerLimit=35`, `SupplyCurrentLowerTime=0.5`; steer `SupplyCurrentLimit=20`).
- **TalonFXS caveat:** `ModuleIOTalonFXS.java` uses only voltage requests — by design, since TalonFXS can't do `TorqueCurrentFOC`.

### Key facts (CTRE Phoenix 6, verified Aug 2026)
- FOC commutation increases peak power by ~15% on supported devices.
- `TorqueCurrentFOC` directly controls motor acceleration/torque (commands amps), and **requires** a Phoenix Pro license — output disables + `UnlicensedFeatureInUse` fault if unlicensed.
- Voltage/duty-cycle requests have `EnableFOC` (default `true`); they silently fall back to trapezoidal commutation when unlicensed.
- **TalonFXS does not support `TorqueCurrentFOC`.**
- Phoenix Pro is licensed per device (CTRE store: "from $10" per device), renewed per season.
