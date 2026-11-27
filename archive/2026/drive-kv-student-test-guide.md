# Testing the Drive `kV` Bug on the Practice Field

**Who this is for:** students running the test on the new drive base.
**How long:** about 2 hours, most of it logging and swapping constants.
**What you need:** the drive base, two good batteries, ~40 ft of clear practice field,
a laptop with AdvantageScope, and someone taking notes.

---

## The short version of what we're testing

Our drive motors are told to hit a speed. Two things work together to make that happen:

- **Feedforward (`kV`)** calculates the voltage that should produce that speed and sends
  it immediately. It's supposed to do ~95% of the work.
- **Feedback (`kP`)** looks at the leftover error and nudges. ~5% of the work.

We think `kV` in `TunerConstants.java` is **7× too small** — it's a number measured at the
*motor*, but our loop runs in *wheel* units, and there's a 7.03:1 gearbox between them.
When feedforward is that far off, `kP` has to do all the work, and `kP` can only produce
output when there's error. So the wheel **settles at about 68% of the speed we ask for and
just stays there.**

Log analysis from seven matches says this is what happened all season. Your job is to
prove it on real hardware and measure the fix.

**The thing to hold onto:** you're looking for a number to go from **0.68 to about 1.0**.
That number is measured wheel speed divided by commanded wheel speed. Everything below is
in service of measuring that cleanly.

---

## Step 1 — Carry the drive code over as-is

This is the most important setup step and it's easy to get wrong by being helpful.

**Copy the main robot's drive code onto the drive base without "fixing" anything.** We want
the drive base to reproduce the bug first. If you tidy up constants on the way over, you
lose the baseline and the whole test becomes an argument.

Copy over unchanged:

| File | What matters |
|---|---|
| `TunerConstants.java` | `driveGains` — must still be `kP=1.5, kI=0, kD=0, kS=0, kV=0.124` |
| | `kSpeedAt12Volts = 4.39`, wheel radius, `kDriveGearRatio = 7.03125` |
| | Steer gains — leave these completely alone, they were characterized properly |
| `ModuleIOTalonFX.java` | `driveConfig.Feedback.SensorToMechanismRatio = constants.DriveMotorGearRatio` |
| `Module.java` | the setpoint conversion — don't touch it |
| AdvantageKit logging setup | so the log keys match and our analysis scripts still run |
| The `Drive Simple FF Characterization` auto routine | you'll need it in Step 3 |

**One thing to verify before you go to the field.** Open `ModuleIOTalonFX.java` and find
what control request the drive motor uses. It should be **`VelocityVoltage`** (or
`VelocityDutyCycle`).

> If it says **`VelocityTorqueCurrentFOC`**, stop and tell a mentor. That mode measures
> gains in amps instead of volts, and this whole test would be built on the wrong
> assumption. It's worth the 60 seconds to check.

Also confirm your CAN IDs and module offsets are correct for the *new* base. Wrong offsets
will make modules fight each other and every number you collect will be garbage.

---

## Step 2 — Set up your two views

You'll watch things live and record them for later. Both matter.

### Live dashboard (so you know a run was good before you walk back)

Publish these four numbers so you can see them during a run. Add to `Drive.java` or
wherever is convenient:

```java
double measured = modules[0].getDriveVelocityRadPerSec() / (2 * Math.PI);  // wheel rot/s
double command  = setpointStates[0].speedMetersPerSecond
                  / (2 * Math.PI * TunerConstants.kWheelRadius);           // wheel rot/s

SmartDashboard.putNumber("kVtest/measured rot per s", measured);
SmartDashboard.putNumber("kVtest/commanded rot per s", command);
SmartDashboard.putNumber("kVtest/ratio", Math.abs(command) > 1 ? measured / command : 0);
SmartDashboard.putNumber("kVtest/bus volts", RobotController.getBatteryVoltage());
```

**`kVtest/ratio` is the whole experiment.** Watch it while someone drives at a steady
speed. Ignore it during acceleration and while stopped — it's only meaningful when the
robot is holding a speed.

### Logs (so the numbers are defensible)

Make sure AdvantageKit logging is running and writing to the USB stick. After each run,
pull the `.wpilog` and give it an obvious name — `baseline_run1.wpilog`, not
`akit_26-08-02_14-22-01.wpilog`.

In AdvantageScope you'll plot:

- `/RealOutputs/SwerveStates/Measured`
- `/RealOutputs/SwerveStates/SetpointsOptimized`
- `/SystemStats/BatteryVoltage`
- `/Drive/Module0/DriveAppliedVolts`

---

## Step 3 — The four runs

Do these in order. **Don't skip Run 1** — without a baseline you can't prove anything
changed.

Each run is the same three maneuvers, so they're comparable:

- **A — Slow steady:** drive straight at about ¼ stick, hold it for 5 seconds.
- **B — Medium steady:** about ⅔ stick, hold 5 seconds.
- **C — Full send:** full stick straight down the field, at least 3 full seconds at top
  speed before you brake. You need a long run for this — the robot has to actually settle
  at its top speed, not just be accelerating toward it.

Fresh battery every two runs. A tired battery will muddy your numbers in a way that's
easy to mistake for a bad result.

### Run 1 — Baseline (broken gains, as inherited)

```java
new Slot0Configs().withKP(1.5).withKI(0).withKD(0).withKS(0).withKV(0.124);
```

**What you should see:** `kVtest/ratio` sitting around **0.65** during the steady parts of
all three maneuvers. Top speed in maneuver C around **9.4–9.6 wheel rot/s (~3.0 m/s)**.

If the ratio is near 1.0 already, something didn't carry over — stop and check that the
gains actually reached the motor controller before continuing.

### Run 2 — Measure the real numbers

1. Put the drive base in open space with room to roll forward ~15 ft.
2. Select the **"Drive Simple FF Characterization"** auto routine.
3. Enable in autonomous. The robot accelerates slowly forward.
4. Disable after 5–10 seconds.
5. Read `kS` and `kV` off the driver station console. **Write them down.**

**Expected: `kV` between 0.85 and 0.90. `kS` between 0.10 and 0.22.**

`kS` will probably come out lower than the 0.19 we measured on the competition robot —
that's fine and expected, because this base is much lighter and there's less friction to
overcome. We'll re-measure `kS` on the real robot later.

**Stop and ask a mentor if you get any of these:**

| You got | What probably happened |
|---|---|
| ~0.124 | The routine printed the config value instead of measuring something |
| ~0.139 | Somebody's math used radians instead of rotations. **Watch for this one** — it's close enough to 0.124 that it can look like "no bug found" |
| ~6.1 | The gear ratio got applied twice |
| bigger than 1.2 | A wheel size or gear ratio constant is wrong somewhere |

Don't just paste in 0.87 because this guide says so. Use *your* measured number. The
predicted value is there so you can tell whether the routine ran correctly.

### Run 3 — Feedforward only (leave `kP` alone)

```java
new Slot0Configs().withKP(1.5).withKI(0).withKD(0)
    .withKS(<your measured kS>).withKV(<your measured kV>);
```

**Turn the driver speed limit down to about 50% for this run.** You now have correct
feedforward *and* a `kP` that's 15× larger than it should be. It will be twitchy. That's
expected and it's temporary.

We do this run because the drivetrain also has a current oscillation problem, and we're not
sure whether feedforward or `kP` causes it. Running them separately is the only way to
find out. If we changed both at once we'd fix the robot and still not know why.

**What you should see:** ratio jumps to roughly **0.95–1.0**. Possibly some buzz or
harshness. Log it either way.

### Run 4 — Final configuration

```java
new Slot0Configs().withKP(0.1).withKI(0).withKD(0)
    .withKS(<your measured kS>).withKV(<your measured kV>);
```

Speed limit back to 100%. Run all three maneuvers.

**What you should see:** ratio **0.95–1.0**, and the robot should feel smooth rather than
buzzy. This is the configuration we're hoping to keep.

---

## Step 4 — Check your results

### The five numbers that decide it

| | What to check | Baseline (Run 1) | Fixed (Run 4) |
|---|---|---|---|
| 1 | Ratio at steady speed | 0.64 – 0.68 | **0.95 – 1.00** |
| 2 | Ratio at slow vs. full speed | flat ~0.65 at both | **flat ~0.98 at both** |
| 3 | Top wheel speed, maneuver C | 9.4 – 9.6 rot/s | **13.2 – 13.8 rot/s** |
| 4 | Top speed in m/s | ~3.0 m/s | **4.2 – 4.4 m/s** |
| 5 | Applied volts at top speed | ~8.2 V | **~11.5 – 12 V** |

Number 5 surprises people. Before the fix the drivetrain never used more than about 8–9 V
even at full stick — it just gave up early. After the fix it should be pushing right up
against what the battery can supply at top speed. **That's correct.** Running out of
voltage at full speed is what a healthy drivetrain does.

Number 2 is your best check that you fixed the right thing. A gain problem produces a
deficit that's the *same percentage* at every speed. A battery or traction problem gets
*worse* the faster you go. If your ratio is flat, you fixed a gain problem.

### One optional 5-minute check worth doing

Everything above is measured by the drive encoders. Encoders can't catch a wrong
**wheel radius** constant — the numbers would all look perfect and the robot would still be
going a different speed than the code thinks.

So once, on Run 4: tape a start and finish line a measured distance apart (30 ft is
plenty), drive it at full speed, and time it with a phone stopwatch. If the stopwatch says
roughly what the log says, your wheel radius constant is fine. If it's off by more than
~10%, measure your actual wheel diameter with calipers — worn wheels are smaller than new
ones.

### If it didn't go as expected

| What you saw | What it means | What to do |
|---|---|---|
| Ratio near 1.0 at low speed, drooping at full stick | You're running out of battery, not out of feedforward | Check `kVtest/bus volts` at top speed. If it's under ~10 V, this is normal. Not a failure. |
| Ratio still ~0.68 after Run 4 | The new gains probably never reached the motor | Read the gains back off the Talon in Tuner X. Check you edited the slot that's actually being used. |
| Ratio ~1.0 but the robot buzzes or sounds harsh | `kP` is still too high now that feedforward works | Try `kP = 0.05`. With good feedforward you need very little. |
| Ratio overshoots, 1.05 – 1.15 | Measured `kV` came out a little high, or wheel radius is wrong | Do the tape-measure check above **before** you touch `kV`. |
| Top speed under 4.2 m/s but ratio is 0.98 | Working correctly, just battery-limited | Note the bus voltage and move on. |
| Modules fighting each other, robot crabs sideways | Module offsets are wrong for this base | Re-zero the modules. Not a `kV` issue. |

---

## Things that will happen that are **not** about `kV`

The most likely way this test goes wrong is somebody measures the wrong thing and declares
it a failure. If you see any of these, note it and keep going:

- **The drive base draws less current than the competition robot.** Of course it does — it
  weighs a fraction as much. You cannot learn anything about our brownout problem on this
  base. That's a separate investigation on the real robot.
- **A ~2 Hz current oscillation that doesn't go away.** We have a second, possibly
  unrelated problem where drive current flips direction about twice a second. It might be
  `kP`, it might be mechanical. If it persists through Run 4, that's *useful information*,
  not a failed test — it tells us the cause is mechanical.
- **The wheels slip more on hard acceleration.** Expected. The drivetrain can finally
  deliver the torque it was always asking for. That's a current-limit conversation for
  later, not evidence the fix is wrong.
- **The robot feels harder to drive.** Also expected. It's ~35% faster on this base and
  responds differently. The driver needs practice time before it matters in a match.
- **Autonomous paths behave oddly.** Meaningless on a bare drive base — path following
  depends on the real robot's weight and balance.
- **Steering feels the same.** It should. We didn't touch the steer gains and they were
  already correct.

---

## One expectation to set now

On **this drive base** you should see about **4.2–4.4 m/s** after the fix.

On the **competition robot in a real match**, expect closer to **3.6–3.9 m/s.** The real
robot is much heavier and its battery sags to around 10 V under load, and you can't reach
4.4 m/s on a 10 V bus no matter how good your gains are.

Both of those are the fix working correctly. If somebody later measures 3.8 m/s on the
competition robot and says "the guide promised 4.4," this is why.

---

## What to report back

Bring these to the next software meeting:

1. All four `.wpilog` files, clearly named.
2. Your measured `kV` and `kS` from Run 2.
3. The five numbers from the Step 4 table, baseline vs. fixed.
4. Bus voltage at top speed on Run 4.
5. Whether the 2 Hz current buzz was present in Run 1, Run 3, and Run 4 (this is the part
   only you can answer, and it decides where we look next).
6. Anything that surprised you, even if you think it's unrelated. Especially then.

---

## Field card — tear this off

```
RUN 1  BASELINE      kP=1.5   kS=0      kV=0.124        expect ratio ~0.65, top ~3.0 m/s
RUN 2  CHARACTERIZE  "Drive Simple FF Characterization" expect kV 0.85-0.90, kS 0.10-0.22
                                                        STOP if kV reads 0.124 / 0.139 / 6.1
RUN 3  FF ONLY       kP=1.5   kS=meas   kV=meas         50% speed limit. expect ratio ~0.95-1.0
RUN 4  FINAL         kP=0.1   kS=meas   kV=meas         expect ratio 0.95-1.0, top 4.2-4.4 m/s

EVERY RUN:  A) quarter stick 5s   B) two-thirds stick 5s   C) full stick 3s+ at top speed
            fresh battery every 2 runs, save + rename the log

WATCH:      kVtest/ratio  (only meaningful at steady speed)
            kVtest/bus volts  (if under 10 V at top speed, you're battery limited)

THE ANSWER: ratio goes 0.68 -> 1.0 and stays flat across speeds.
```
