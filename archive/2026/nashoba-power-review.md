# Nashoba (FRC 1768's neighbor) — Power-Conservation Code Review

**What this is:** an initial, targeted read of the `Nashoba-Robotics/2026NashobaRobotics`
public repo, looking specifically for power-saving and brownout-mitigation techniques we could
learn from. They're a dumper/flywheel team like us but with a different shooter, and they run the
same AdvantageKit + CTRE stack we do, which makes the comparison clean.

**Important caveat up front:** this is a *static code read*, not a log-measured analysis. We do
not have Nashoba's power logs, so every "saves power" claim below is about a design *technique* and
its expected effect, not a measured number on their robot. Where we can, the right next step is to
try the technique on our robot and measure it the way we measured the drive-kV fix. Treat this as a
menu of ideas, ranked by how much I think they'd help us given what our own brownout / supply-current
analyses already found.

---

## The headline: their whole robot is "off by default"

The single biggest pattern isn't one config line — it's an architecture. Every mechanism defaults
to *doing nothing*, and only draws current while a button is actively held. From
`Superstructure.java`:

```java
shooter.setDefaultCommand(shooter.stopCommand());       // -> NeutralOut(), coast
entryRoller.setDefaultCommand(entryRoller.stopCommand());
rollerFloor.setDefaultCommand(rollerFloor.stopCommand());
intakeRoller.setDefaultCommand(intakeRoller.stopCommand());
hood.setDefaultCommand(hood.runPositionCommand(TUCK_ANGLE)); // tuck & hold, then idle
```

Nothing free-spins "just in case." This is the discipline that makes all the individual tricks
below actually matter, and it's worth checking on our own robot: **is anything on our side spinning,
holding, or PID-fighting when no one asked it to?** That's the cheapest power to get back.

---

## 1. The dumper flywheel does NOT idle-spin — on-demand only *(biggest single lesson)*

Their shooter is four TalonFX (`leader` + 3 `Follower`s, 2 aligned / 2 opposed —
`ShooterIOTalonFX.java:66-71`) on a common flywheel. The power-relevant choices:

- **`NeutralMode = Coast`** (`ShooterIOTalonFX.java:81`)
- **`stop()` issues `NeutralOut()`** (`:274`), and stop is the *default command*.

So when they aren't actively aiming, all four shooter motors output **zero** and the flywheel
coasts down on its own inertia. They spin it up (closed-loop velocity, torque-current) only inside
`aimCommand` while the driver holds the right trigger. Between shots in a burst, `Coast` lets the
wheel keep its momentum so re-engaging is cheap, but a genuine idle costs nothing.

**Why this is the big one for us:** a four-motor flywheel held at an idle RPM continuously is one of
the largest avoidable always-on loads a dumper robot can have, and our own `power-analysis` /
brownout work flagged "always-on mechanisms" as a real chunk of our draw. If we currently idle-spin
our flywheel to cut spin-up latency, this is the trade to re-examine: Nashoba bet that coast-down +
on-demand spin-up (backed by a strong feedforward so spin-up is fast) is cheaper than paying idle
current all match. Worth measuring both ways on our robot.

**The tension to be honest about:** on-demand spin-up means the *spin-up transient* is a current
spike right when you want to shoot. They bound it with a per-motor supply limit (next section); we'd
want to confirm the spike doesn't itself cause a brownout at the moment of shooting — which is
exactly the "shooting stack" event our brownout analysis already worries about.

---

## 2. Every mechanism has BOTH a stator AND a supply current limit

This is the discipline our steer-current analysis found *missing* on our drivetrain. Nashoba sets
both limits on every non-drivetrain motor (`Constants.java`, applied in each `*IOTalonFX`):

| Mechanism | Stator limit (A) | Supply limit (A) | Neutral mode |
|---|---|---|---|
| Shooter (×4) | 120 | **60** | Coast |
| Intake roller (×2) | 80 | **60** | Coast |
| Roller floor (×2) | 80 | **40** | Brake |
| Entry roller | 80 | **40** | Brake |
| Hood | 60 | **40** | Brake |
| Intake deploy | 60 | **40** | Brake |
| **Drive (×4)** | 80 (= slip) | **none** | Brake |
| **Steer (×4)** | 60 | **none** | Brake |

Two takeaways. First, the **supply limit is consistently well below the stator limit** (40–60 vs
60–120) — the correct relationship, because supply (battery-side) current is what feeds brownouts,
and it's lower than stator at low mechanism speed. This is precisely the lever our steer analysis
recommended we add. Second, and in fairness: **they don't supply-limit the drivetrain either.**
Drive and steer get no supply limit (drive leans on the torque-current peak instead, §4; steer on
motion profiling, §3). So our steer supply limit — already pushed — and a matching drive supply
limit put us *ahead* of them on the drivetrain, not just catching up.

**Actionable:** the mechanism-side supply limits are close to free insurance and we should confirm
we have equivalents on our shooter/intake/rollers. The drivetrain supply limit remains our own
original idea and is still worth doing.

---

## 3. Steer azimuth moves are motion-profiled (MotionMagicExpo) — but this is largely redundant with the steer supply limit we already shipped

**Bottom line first: skip this unless a specific symptom appears. It attacks the same
synchronized-spike/brownout problem our steer supply current limit already addresses, and it's the
*weaker, more expensive* of the two levers for that job. We already shipped the stronger one.**

What Nashoba does — profile every azimuth move (`ModuleIOTalonFX.java:132-136`):

```java
turnConfig.MotionMagic.MotionMagicCruiseVelocity = 100.0 / SteerMotorGearRatio;
turnConfig.MotionMagic.MotionMagicAcceleration   = CruiseVelocity / 0.100; // reach cruise in 0.1s
turnConfig.MotionMagic.MotionMagicExpo_kV        = 0.12 * SteerMotorGearRatio;
turnConfig.MotionMagic.MotionMagicExpo_kA        = 0.1;
```

The module accelerates along a profile instead of stepping to the setpoint, spreading the current
over ~0.1 s and lowering the peak — the "soften the slew slam" idea our steer analysis listed as
optional item #3.

**Why it's redundant with our supply cap.** Both changes target the same quantity — the peak steer
current during a synchronized flip — but from opposite ends:

- Our **supply limit is a hard ceiling.** 20 A/motor caps the four-module contribution to the stack
  at ~80 A, no matter what the controller asks for.
- Motion profiling is **demand-shaping.** It stops the controller from *asking* for the instantaneous
  spike, lowering the peak and the di/dt.

Whichever sets the lower ceiling is the one that matters, and the cap has already set it. Layering a
profile underneath our 20 A cap reduces the *typical* spike and how often we hit the ceiling, but it
**cannot push the worst case below the ~80 A the cap already enforces** — so the incremental
worst-case brownout benefit is close to zero. In the numbers from `steer-current-analysis.md`:
going from no limit to the 20 A cap moves the worst four-module transient from ~170–200 A to ~80 A
(≈ **1.4–1.9 V recovered** at the worst steer-driven instant). Adding the profile on top moves that
worst case from 80 A to… still 80 A. It buys maybe a few tenths of a volt on *average* busy moments,
not at the worst one. Our own analysis said as much before we ever looked at Nashoba: *"the supply
limit already solves the brownout problem more directly. Do the supply limit first; only reach for
[slew softening] if spikes persist."* Nashoba leans on the profile precisely *because* they never
added a steer supply limit — it's their substitute for the cap, not a complement to it.

**The one thing profiling adds that the cap can't: control feel, not power.** When the 20 A cap
clips a fast slew (it clips ~9% of them), that module is current-starved mid-slew — it still gets
there, just a hair slower and a bit abruptly. Profiling makes the module approach the ceiling
gracefully and often stay under it, so azimuth motion is smoother and fewer slews hit the cap. That's
a responsiveness benefit, not a brownout benefit.

**Decision rule (measure before building):** get a match of logs with the supply cap live and check
two things —

1. **Does steer still show up in our brownout dips despite the cap?** (Our 20 A → ~80 A worst case is
   *modeled*, not yet measured on-robot. Confirm it first.) If brownouts are clean, profiling has
   nothing left to fix on the power side → **don't build it.**
2. **Do the modules now feel laggy from clip-starving?** If yes, that's the only reason to act — and
   the cheap fix is a small `VoltageClosedLoopRampPeriod` (~0.05–0.1 s), a one-line change on our
   existing voltage + PID steer, not a re-architecture. Full MotionMagicExpo (switch the control
   request to `MotionMagicExpoVoltage`, tune `Expo_kV`/`kA`, re-validate azimuth feel with a driver)
   is only warranted if steer *still* shows in the dips after the cap, which the model says is
   unlikely.

**So: is it worth the effort? Default answer is no.** If the supply limit shows good results in
logs, leave it as is. Keep MotionMagic/ramp in the back pocket as a contingency for the two symptoms
above, not as planned work.

---

## 4. Torque-current drive with peak current = slip current

Covered in depth in the drive-gains comparison, but it belongs here too as a power/brownout lever.
Their drive commands torque-current and clips it at the slip current
(`ModuleIOTalonFX.java:107-109`):

```java
driveConfig.TorqueCurrent.PeakForwardTorqueCurrent =  SlipCurrent;   // 80 A
driveConfig.TorqueCurrent.PeakReverseTorqueCurrent = -SlipCurrent;
driveConfig.CurrentLimits.StatorCurrentLimit       =  SlipCurrent;
```

Because current *is* torque *is* traction force, this is a hard "never command more force than the
wheels can transmit" cap, applied natively by the control mode. It bounds drive stator draw to 80 A
per module and kills the wasted current of spinning wheels during a push or a wall-slam. We get a
similar effect in voltage mode only by adding explicit limits; theirs falls out of the control
choice. Not a reason to switch modes wholesale, but it's the power argument *for* torque-current
that complements the traction argument.

---

## 5. Trickle-voltage holds instead of stiff PID holds

Small but clever. Once the intake reaches its hard stop, they don't hold it with a stiff position
loop — they hold it with a trickle voltage (`Superstructure.java:90-104`):

```java
// deploy: drive out at 8 V until past 130°, then just:
intakeDeploy.runVoltageCommand(() -> 0.40);   // hold against the stop
// retract: drive in at -8 V until under 25°, then:
intakeDeploy.runVoltageCommand(() -> -0.30);  // hold in
```

A 0.3–0.4 V hold against a hard stop draws far less than a position controller actively defending a
setpoint, and it can't hunt. Anywhere we hold a mechanism against a hard stop or gravity, a tuned
trickle voltage (or a low stator limit on the hold) is cheaper than a full PID hold.

---

## 6. Robot-level: brownout threshold lowered to 6.0 V

`Robot.java:79` — `RobotController.setBrownoutVoltage(6.0)`. This lowers the roboRIO's protective
brownout cutoff from the ~6.3 V default, giving the bus more room to sag before the RIO starts
shedding the 6 V / PWM rails. For a robot that our logs show diving toward 7 V (and below) on
shooting stacks, buying headroom here means more of those dips survive without a protective
brownout event.

**Treat this one with care — it's a trade, not a freebie.** Lowering the threshold means the RIO
tolerates deeper sags before protecting itself; go too low and you risk the RIO/radio actually
resetting instead of gracefully braking. 6.0 V is a common, defensible choice on a modern roboRIO,
but it's a band-aid over the current spikes, not a fix for them. Do the spike-reduction items first;
consider the threshold as belt-and-suspenders, and only with the team's electrical lead bought in.

---

## Smaller notes

- **`SignalLogger.enableAutoLogging(false)`** (`Robot.java:64`) — disables CTRE's hoot signal
  logger. This is a CPU/flash/CAN-overhead saving, not really battery power, but it's a small
  reliability win worth knowing.
- **Coast on the free-spinning things, brake on the positioned things** — a consistent rule across
  the robot: flywheel and intake rollers coast (don't fight momentum / don't waste energy braking a
  wheel you'll respin), while positioned mechanisms (hood, deploy, feed rollers) brake. Sensible and
  worth mirroring deliberately rather than by accident.

---

## What I'd actually pull into our robot, in priority order

1. **Audit our "always-on" loads, starting with the flywheel idle policy (§1).** Potentially the
   biggest single power win if we currently idle-spin; needs an A/B measurement.
2. **Confirm supply current limits on all our mechanisms (§2)**, and keep our drivetrain supply
   limit idea — it puts us ahead of Nashoba there.
3. **Trickle-voltage holds (§5)** wherever we PID-hold against a stop.
4. **Brownout threshold (§6)** — only after the spike-reduction items, and with electrical sign-off.
5. **Steer motion profiling (§3) — contingency only, not planned work.** Largely redundant with the
   steer supply limit we already shipped; revisit only if post-cap logs still show steer in the
   brownout dips, or if modules feel laggy from clip-starving (and then start with a cheap
   closed-loop ramp, not full MotionMagic). If the supply limit shows good results, leave it as is.

**Method:** read of `Nashoba-Robotics/2026NashobaRobotics` @ main —
`Constants.java`, `Superstructure.java`, `Robot.java`, `RobotContainer.java`, and the drive /
shooter / hood / intake `*IOTalonFX` files. No power logs available, so effects are expected, not
measured. Cross-referenced against our own `steer-current-analysis.md`, `brownout-analysis.md`, and
`supply-current-analysis.md`.
