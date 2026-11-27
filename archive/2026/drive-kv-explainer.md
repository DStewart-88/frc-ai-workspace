# The Drive Feedforward Bug: What It Is, How to Fix It, What Changes

**Audience:** anyone on the software team. Assumes you know what a PID loop is. Does not
assume you know what feedforward is.

---

## The one-sentence version

One number in `TunerConstants.java` is 7× too small, and because of it our robot could
only ever reach about **68% of its top speed** — all season, at every event.

---

## Part 1 — What feedforward is, and why we have it

When we tell a swerve module "spin the wheel at 3 m/s," something has to decide how many
volts to send the motor. There are two ways to decide, and we use both at once.

**Feedback (the PID part).** Look at how fast the wheel is *actually* going, subtract it
from how fast we *want* it to go, and send voltage proportional to that error. The gain
`kP` sets how aggressive this is. Feedback is reactive — it can only respond to an error
that already exists.

**Feedforward (the `kV` part).** Skip the guessing. A motor's speed is roughly
proportional to the voltage you give it, so if we know we want 3 m/s, we can *calculate*
the voltage that produces 3 m/s and send it immediately. `kV` is that conversion factor:
**volts per unit of speed.**

The two are meant to split the work like this:

- `kV` does ~95% of it. It supplies the voltage needed to hold the speed we asked for.
- `kP` does the last ~5%. It cleans up whatever `kV` didn't predict — carpet, a defense
  bot pushing us, battery sag.

**That split is the whole point.** Feedforward is supposed to carry the load so that
feedback only has to nudge. When feedforward is wrong, feedback has to carry the load
instead — and feedback can only produce output when there is *error*, so a permanent
error is the only way it can do that.

## Part 2 — The bug: `kV` was in the wrong units

Here is the line, in `TunerConstants.java`:

```java
private static final Slot0Configs driveGains =
    new Slot0Configs().withKP(1.5).withKI(0).withKD(0).withKS(0).withKV(0.124);
```

`kV = 0.124` is **volts per rotation per second of the motor**. But our control loop is
measured in **rotations per second of the wheel**. Between the motor and the wheel is a
7.03:1 gearbox.

So the number is correct for one thing and wrong by 7.03× for the thing we actually
plugged it into.

```
                        kV must be expressed in the
                        SAME units the loop measures
                              |
   [ MOTOR ] --7.03:1 gearbox--> [ WHEEL ]
    94 rot/s                     13.4 rot/s        at 12 V
    kV = 0.124  <-- what's in our code
                                 kV = 0.872  <-- what the loop actually needs
```

**Why this happened, and why it's nobody's fault.** `0.124` is the *default value* that
CTRE's Tuner X generator writes into `TunerConstants.java`. It is correct for CTRE's own
swerve library, which runs its drive loop in motor units. We don't use CTRE's swerve
library — we use **AdvantageKit's** template, which runs the drive loop in *wheel* units.
AdvantageKit's own documentation says so explicitly, twice:

> "The AdvantageKit template requires different feedforward gains than CTRE's default
> swerve code, because it applies the swerve gear ratio using the TalonFX(S) firmware and
> not on the RIO."

> "The drive `kS` and `kV` gains should **always** be characterized."

The template ships with a routine to measure these for us — **"Drive Simple FF
Characterization"** — and it was never run. So the generator's placeholder stayed in.

You can see the two conventions right next to each other in `ModuleIOTalonFX.java`:

```java
driveConfig.Feedback.SensorToMechanismRatio = constants.DriveMotorGearRatio;  // WHEEL units
turnConfig.Feedback.RotorToSensorRatio      = constants.SteerMotorGearRatio;  // azimuth units
```

The **steer** gains were properly characterized — they have a real `kS`, a real `kD`, a
tuned `kV`. Only the drive side was left on defaults.

## Part 3 — What went wrong as a result

With feedforward supplying only 1/7 of the voltage needed, `kP` had to supply the rest.
And feedback can only produce output from error. So the loop settles at a permanent gap:

```
  feedforward voltage  +  kP × error  =  voltage needed to hold actual speed
     0.124 × target    +  1.5 × (target − actual)  =  0.872 × actual

  solve:   actual = 0.685 × target
```

**The wheel settles at 68% of whatever we ask for, forever.** Not a transient. Not a
tuning roughness. A structural property of having the wrong feedforward.

Someone noticed the symptom: `kP` was raised from the generator default of **0.1 to 1.5**,
a 15× increase. That's a rational response to "the drive won't reach commanded speed" —
it just treats the symptom instead of the cause, and a large `kP` brings its own
problems (harsh response, current spikes on direction changes).

### Confirmed in seven matches across three events

Measured directly from our own AdvantageKit logs — GB (March), Newsom (April), Newton
(May), five different code builds:

| What we measured | Result | Expected if the bug is real |
|---|---|---|
| True `kV` in wheel units | **0.870 – 0.880** | 0.872 |
| Ratio to what's in our code | **7.0×** | 7.03 (the gear ratio) |
| Velocity tracking (actual ÷ commanded) | **0.63 – 0.67** | 0.685 |
| Top wheel speed reached | **3.1 – 3.3 m/s** | 4.39 m/s available |
| Drive voltage ever used | **max ~9.2 V** | 12 V available |

The `kV` measurement has an R² of 0.997+ and lands within 1% of theory. This is not
ambiguous.

**The cost, in plain terms:** when our driver pushed the stick all the way forward, the
robot went 3.2 m/s instead of 4.4 m/s. We never used more than 9.2 of our 12 volts. We
left about a third of our drivetrain unused in every match we played this season.

---

## Part 4 — How to fix it

**Do these in order.** Order matters: `kP = 1.5` is a *symptom*. If you lower `kP` first,
the robot gets even slower and it'll look like you made things worse.

### Step 1 — Measure the real values (30 minutes, on the field or a practice carpet)

Do **not** just paste in 0.872. Run the routine the template provides, so the number
belongs to our robot with our wheels on our carpet.

1. Make sure steering is tuned first (it already is).
2. Put the robot in an open space.
3. Select the **"Drive Simple FF Characterization"** auto routine.
4. Enable in autonomous. The robot accelerates slowly forward.
5. Disable after 5–10 seconds.
6. Read `kS` and `kV` off the console.

Expect roughly `kV ≈ 0.87` and `kS ≈ 0.19`. **If you get ~0.12, something is wrong with
the test — stop and ask.** Our log analysis already predicts what this test should say, so
it doubles as a check that the routine ran correctly.

### Step 2 — Install feedforward, and drop `kP` back to the default

```java
private static final Slot0Configs driveGains =
    new Slot0Configs()
        .withKP(0.1)      // back to generator default -- kV does the work now
        .withKI(0)
        .withKD(0)
        .withKS(<measured>)   // ~0.19
        .withKV(<measured>);  // ~0.87
```

### Step 3 — Verify tracking before touching anything else

Drive around. In AdvantageScope, plot `/RealOutputs/SwerveStates/Measured` against
`/RealOutputs/SwerveStates/SetpointsOptimized`.

**They should now sit on top of each other.** Before the fix, Measured sat ~35% below
Setpoints at all times. That single plot is your pass/fail.

### Step 4 — Only now, re-tune `kP` if you need to

With correct feedforward, `kP` should only need to be large enough to reject disturbances
(getting shoved, carpet seams). Raise it from 0.1 gradually and stop as soon as tracking
is crisp. If you find yourself heading back toward 1.5, something else is wrong — come
back and re-check Step 3.

### Step 5 — Re-check the things that were tuned around the broken drivetrain

This is the part that's easy to forget. Anything calibrated while the drivetrain was
running 32% slow may now be wrong:

- **`kSpeedAt12Volts = 4.39`** — re-measure with the "Max Speed Measurement" procedure.
- **Autonomous paths** — PathPlanner was commanding speeds the robot couldn't reach. Every
  auto will now actually hit its setpoints and will run *differently*. Re-test all of them
  before competition.
- **Shot-on-the-move compensation** — if it was calibrated against actual robot velocity
  it's probably fine, but verify.
- **Driver feel** — tell the driver first. The robot will be noticeably faster and will
  respond differently. Give them practice time before a match matters.

---

## Part 5 — What to expect after the fix

**Confident:**

- Top speed goes from ~3.2 m/s to ~4.4 m/s — about **35% faster**.
- Commanded speed and actual speed match, so the robot does what the driver asks.
- Autonomous becomes more repeatable, because paths were previously asking for speeds the
  robot never delivered.
- Odometry and pose estimation get a little better for the same reason.

**Not promised:** this is *not* a fix for our brownout problem. We measured that
separately and the drivetrain's high current is mostly real propulsion work, not wasted
control effort. See `power-analysis.md` — the power problem is largely mechanical drag and
always-on mechanisms, and it needs its own fix.

Be aware the robot may draw *slightly more* current after this change, because it will
actually accelerate to speeds it never reached before. That's a real effect and worth
watching, though it should be modest.

---

## The general lesson worth keeping

**A generated default is not a measured value.** `kV = 0.124`, `kP = 0.1`, `kS = 0` were
placeholders that Tuner X wrote for us. They looked like real constants because they were
specific numbers sitting in a config file, and they survived a whole season because
nothing in the build process distinguishes "measured" from "not yet measured."

Worth doing next season: keep a checklist of every constant that is supposed to be
*measured*, with the date it was last measured and by whom. `kV`, `kS`, `kSpeedAt12Volts`,
`kSlipCurrent`, wheel radius. If a value has no date next to it, it isn't trustworthy.

Related trap: **a physically correct constant can be wrong for its context.** `0.124` is a
real, accurate property of a Kraken X60. It was wrong only because of where it was used.
When you copy a constant between frameworks, the question isn't "is this number right?"
but "right in which units, measured at which shaft?"
