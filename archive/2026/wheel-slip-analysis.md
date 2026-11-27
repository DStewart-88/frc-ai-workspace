# Wheel Slip: How Often It Happens, What It Does, and How to Detect It Live

*Analysis of 75 match logs (North Shore, Granite State, Newsom/NECMP, Newton, and NERD in October). Written as the first piece of a "drivetrain self-check": can the robot tell, in real time, that a drive wheel is slipping?*

## Summary

- **Yes, slip can be detected from signals the code already reads.** The four wheel speeds, the four module angles, and the gyro's rotation rate must all agree with one rigid-body motion of the robot. When one or more wheels disagree by more than 0.4 m/s for 80 ms or longer, a wheel is slipping. The check works at the normal 50 Hz loop rate, using the inputs the code already logs. It agrees with the 250 Hz version 85–90% of the time.
- **The flags are real.** Checked against the cameras (an independent sensor), odometry error roughly triples as slip increases: 0.18 m/s in 1-second windows with no slip flagged, 0.56 m/s in windows with slip flagged at least half the time. While wheels slip, odometry **over-counts** distance by up to ~23%, because the wheels spin faster than the ground passes under them.
- **It happens a lot.** In the spring events, a wheel is slipping about **a quarter of the time the robot is moving**. That works out to ~100 separate slip events per match, typically 0.3 s long, with ~10 per match lasting over a second. At NERD it was worse: **about half the moving time**, and events were twice as long.
- **The main driver is torque above what the tread can hold.** Slip rises steadily with drive current. Below 20 A it's flagged 3% of the time; that's the false-alarm floor. At 70–80 A it's ~20–24%, at 90–100 A ~51%, and above 120 A ~74%. The configured slip current (stator limit) was 90–120 A during the season. North Shore had the highest limit (120 A) and the most slip.
- **Effects:** corrupted odometry, which the cameras then have to yank back, adding to the pose shake from the vision analysis. Faster tread wear: about **6.5% of each wheel's travel is spent slipping** (14% at NERD). Current spent spinning the wheel instead of pushing the robot. And in auto, path-following breaks down. In Newton Q23 auto, the robot sat stuck near the red bump for ~2 s with wheels spinning, and the logged pose was off by up to ~1 m.
- **One limit to know:** a wheel-agreement check can't see **all four wheels slipping together**, or a sideways shove while all wheels point the same way. Catching those needs the Pigeon's accelerometer, which isn't logged today.

![Wheel slip vs current, and odometry error vs slip](wheel-slip-summary.png)
*(Chart file: `FRC Logs/wheel-slip/plots/wheel-slip-summary.png`)*

---

## How slip is detected

Each swerve wheel only "knows" one thing about the robot's motion: how fast the floor is passing under it **in the direction the wheel is pointing**. If the robot is a rigid body, all four of those numbers are tied together. They are set by just three quantities: the robot's sideways and forward speed, and its rotation rate. The gyro measures rotation directly. That leaves four wheel readings to explain with two unknowns.

So every loop:

1. Take each wheel's speed and angle, and the gyro's yaw rate.
2. Find the single robot velocity that best explains all four wheels (a small least-squares fit).
3. Each wheel's **residual** is its measured speed minus what that fitted motion says it should be. A positive residual means the wheel is turning faster than the ground is moving: it's spinning.
4. **Slip flag:** the largest residual is above 0.4 m/s for at least 80 ms.

This is the same math as odometry, run in reverse as a consistency check. It needs no new sensors.

**What it catches:** one or two wheels spinning or skidding (traction loss, a wheel unloaded on the bump, wheels fighting each other mid-turn). It also catches the robot rotating differently from what the wheels say, as when it's spun by a hit.

**What it can't catch:**
- **All four wheels spinning equally** (e.g., a hard straight-line launch). All four agree with each other, just not with reality.
- **A sideways shove while all wheels point the same direction.** No wheel can see motion perpendicular to itself.

Both need an independent measurement of translation, either the Pigeon 2's accelerometer or vision. There is a hint that the first case happens: windows with no flagged slip but sustained >75 A show 0.23 m/s odometry error vs. 0.16 m/s in quiet windows (87 windows, so a small sample).

**Detection floor:** at low current (below 20 A, away from walls and bumps), the check flags slip 3% of the time. That's the false-alarm rate, or genuine scrub during low-current steering; the two can't be told apart from the logs.

## How much it happens

| Event | Matches | Moving time with a wheel slipping | Slip events / moving minute | Moving time with a module > 75 A | Peak drive current (99.9th pct) |
|---|---|---|---|---|---|
| North Shore (Mar) | 15 | 34% | 53 | 52% | 147 A |
| Granite State (Mar) | 19 | 23% | 38 | 37% | 134 A |
| Newsom / NECMP (Apr) | 21 | 23% | 42 | 35% | 133 A |
| Newton (Apr–May) | 10 | 29% | 43 | 33% | 129 A |
| **NERD (Oct)** | 10 | **55%** | 46 | 25% | 91 A |

Event shape:

| | Spring events | NERD |
|---|---|---|
| Slip events per match | ~100 | ~90 |
| Typical (median) event length | 0.28 s | 0.57 s |
| Events longer than 1 s, per match | 10 | 27 |
| Events during auto, per match | 3.7 | 9.9 |
| Share of slip time on/next to a bump | 9% | 19% |

The peak-current column tracks the slip-current setting in `TunerConstants`:

- North Shore: 120 A
- Granite State and Newsom quals: 110 A
- Newsom playoffs and late Newton: 90 A (the "playoff power adjustments" commit)
- NERD: 90 A under TorqueCurrentFOC

The data independently confirms the config history.

All four modules slip about equally (FL slightly least). That rules out a single bad module or a loose wheel as the main story.

## What causes it

**1. Commanding more torque than the tread can hold (the big one).** Slip rises steadily with drive current. There's no single sharp cutoff, because weight shifts between wheels while accelerating and turning. But by 80–90 A, more than a third of the time a wheel is already slipping. The CTRE "slip current" setting is meant to be exactly the current where the wheels break loose. The robot ran at 90–120 A, well into the range where slip is common.

**2. Bumps.** About 7% of spring slip events (12% at NERD) happen on or next to a bump. Typically one end of the robot is unloaded and its wheels spin while the other end does the work. These run longer than average (median 0.4 s spring, 1.0 s NERD).

**3. Contact and walls.** A smaller share of events happen against the field wall or when the robot is spun without being asked to. Example: Newton Q23 at 214 s. The robot was driving straight at 3 m/s with all four wheels parallel and no rotation commanded, and it rotated ~95° in about a second. The cameras' own heading measurements confirm the spin. Being hit by another robot is the likely explanation.

**4. Auto commanding the impossible.** In spring autos, the path follower commanded chassis speeds of 10–24 m/s and spin rates up to 17 rad/s. The robot could only do ~3 m/s then, because of the drive kV issue. PathPlanner's max velocity is set to 4.58 m/s. Once the robot falls behind the path, the corrections saturate and the modules thrash. The Q23 auto stall near the red bump (186–188 s) came out of exactly this.

**Why NERD was worse.** NERD slipped more at *every* current level (chart, left). Two measured differences:

- The wheels themselves accelerate much harder: the 90th-percentile wheel acceleration was 13.6 m/s² at NERD vs. 9.1 m/s² in spring. Anything well above ~10 m/s² (1 g) is more than tread on carpet can deliver, so the wheel spins.
- The robot is faster (90th-percentile speed 3.4 vs. 2.9 m/s).

Both fit the September switch to **TorqueCurrentFOC with kP = 70**: the drive now pushes toward its setpoint as hard as the 90 A limit allows. The old voltage loop, with its kV error, was sluggish, and that sluggishness acted as an accidental traction limiter. Tread wear and that event's carpet could also contribute. One event's worth of logs can't separate these.

## What it does to the robot

**Odometry and pose.** Compared against the cameras in 1-second windows while moving (spring events, 9,072 windows):

| Window | Windows | Odometry speed error (median) | Wheel ÷ camera speed |
|---|---|---|---|
| No slip flagged, no module > 75 A | 691 | 0.16 m/s | 1.01 |
| Slip flagged 1–20% of the window | 3,312 | 0.29 m/s | 1.04 |
| Slip flagged 20–50% | 3,054 | 0.39 m/s | 1.08 |
| Slip flagged ≥ 50% | 1,179 | 0.56 m/s | 1.23 |

The 0.16 m/s floor is mostly camera noise. During slip, odometry runs ahead of the real robot. Vision then drags the pose back, which is part of the "vision jumps" in `claude/vision-analysis.md`. Less slip means steadier odometry, which is what lets vision be trusted less and smooths the pose.

**Correction to the vision report.** That report attributed the ~9% odometry over-count mainly to wheel radius, and suggested shrinking `kWheelRadius` 4–8%. With slip separated out, clean driving over-counts by only **~1–2%**. Most of the 9% is slip. Shrinking the radius 4–8% would make odometry *under*-count whenever the wheels aren't slipping. Correct the radius by the characterization result (~1–2%), and reduce slip instead.

**Tread wear.** About **15 m per wheel per match** is spent slipping in the spring events (6.5% of the ~243 m each wheel rolls). At NERD it was 36 m (14%). Slipping wears tread far faster than rolling, so the component-usage "odometer" should count slip distance separately from rolling distance. This detector provides it directly.

**Battery and current.** At least one drive module was above 75 A for a third to half of all moving time in spring. Current beyond what the tread can hold doesn't add push. It adds heat, tread wear, and battery sag. The drivetrain is already the dominant term in brownout peaks, per the shooter/feeder analyses.

**Auto reliability.** Spring autos averaged ~4 slip events per match, NERD ~10. In Newton Q23 auto, the pose estimate was ~1 m from where the cameras placed the robot while it was stuck near the bump.

## Detecting it live: what it would take

The check runs fine on the 50 Hz signals already in the module and gyro inputs:

- `driveVelocityRadPerSec` (×wheel radius → wheel speed)
- `turnPosition` (module angle)
- `yawVelocityRadPerSec` (gyro rate)

At 50 Hz it flags the same moments as the 250 Hz version 85–90% of the time (correlation 0.94). A sketch for `Drive.periodic()`, to preview only and not applied anywhere:

```java
// Wheel-slip check: do the four wheel speeds agree with one rigid-body motion?
double w = gyroInputs.yawVelocityRadPerSec;
double scc = 0, scs = 0, sss = 0, rc = 0, rs = 0;
double[] b = new double[4], c = new double[4], s = new double[4];
for (int i = 0; i < 4; i++) {
  SwerveModuleState st = modules[i].getState();          // speed (m/s) + angle
  Translation2d r = moduleTranslations[i];
  c[i] = st.angle.getCos(); s[i] = st.angle.getSin();
  // remove the part of this wheel's speed explained by the gyro's rotation
  b[i] = st.speedMetersPerSecond - w * (-c[i] * r.getY() + s[i] * r.getX());
  scc += c[i]*c[i]; scs += c[i]*s[i]; sss += s[i]*s[i]; rc += c[i]*b[i]; rs += s[i]*b[i];
}
// least-squares robot velocity (vx, vy); if all wheels are nearly parallel, only the
// along-wheel direction is observable, so fit just that
double tr = scc + sss, det = scc*sss - scs*scs;
double l1 = tr/2 + Math.sqrt(Math.max(tr*tr/4 - det, 0)), l2 = tr - l1;
double vx, vy;
if (l2 > 0.0025 * l1) { vx = ( sss*rc - scs*rs) / det; vy = (-scs*rc + scc*rs) / det; }
else { double ex = scs, ey = l1 - scc; double n = Math.hypot(ex, ey);
       if (n < 1e-9) { ex = 1; ey = 0; } else { ex /= n; ey /= n; }
       double k = (ex*rc + ey*rs) / l1; vx = k*ex; vy = k*ey; }
double maxResidual = 0;
for (int i = 0; i < 4; i++) {
  double res = b[i] - (c[i]*vx + s[i]*vy);   // + = wheel spinning faster than the floor
  maxResidual = Math.max(maxResidual, Math.abs(res));
}
boolean slipping = slipDebouncer.calculate(maxResidual > 0.4);  // Debouncer(0.08, kRising)
Logger.recordOutput("Drive/Slip/MaxResidual", maxResidual);
Logger.recordOutput("Drive/Slip/Slipping", slipping);
```

Once that's logged, it can feed three things, in increasing ambition:

1. **Health-monitor input and match stats:** slip count and slip time per match, slip distance per wheel for the tread odometer. An alert only for unusual cases, e.g., one module flagged far more than the others, or a flag lasting more than ~2 s.
2. **Odometry protection:** while slipping, trust vision more, or drop the slipping wheel from the odometry update.
3. **Traction control:** back off torque on the flagged wheel. That's a bigger project.

**Add to logging now:** the Pigeon 2's `AccelerationX/Y`. It's the only on-robot way to catch all-four-wheel slip and sideways shoves.

## Fixing the cause (not just detecting it)

In priority order:

1. **Measure the real traction current and set `kSlipCurrent` to it.** CTRE's procedure:
   - Push the robot squarely against a wall on carpet.
   - Slowly ramp drive voltage.
   - Read the stator current at the moment the wheels break loose.

   The logs suggest it's somewhere around 60–80 A with the tread as run, well under the 90–120 A used. Re-check as tread wears.
2. **Limit commanded acceleration**, especially now that the drive runs in torque-current mode. A setpoint generator, or a chassis acceleration limit near what the tread can deliver (~9–10 m/s²), keeps the wheels from being asked to accelerate faster than the robot can. This is the same acceleration-limiting idea that was tabled for shooting. Here it also protects odometry and tread.
3. **Set PathPlanner's max velocity and acceleration to what the robot actually achieves,** so autos don't command impossible chassis speeds.
4. Re-run this analysis on the next logs. The scripts take a folder of logs and print the per-match table above.

## Caveats

- The 0.4 m/s / 80 ms threshold is a judgment call. Moving it changes the absolute percentages: a different, equally defensible fit setting moved Granite State from 17% to 23%. The dose-response against the cameras holds either way.
- "Slip" here includes wheels scrubbing because they point the wrong way during fast direction changes. That's real slip, but not a hardware fault.
- Bump and wall locations come from the logged (vision-fused) pose and the field drawings in 6328's `FieldConstants`. They're approximate to ~0.5 m.
- NERD conclusions rest on 10 matches at one event, with several changes at once (control mode, speed, roller floor, end-of-season tread).
- Drive supply current wasn't logged in spring, so the battery impact is stated in stator current.

## Files

Scripts and outputs are in `FRC Logs/wheel-slip/`:

| File | What it does |
|---|---|
| `extract.py`, `batch_extract.py` | Pull 250 Hz odometry, gyro, currents, pose, and per-camera vision fixes from each log into `cache/*.npz` |
| `slipcore.py` | The slip math: rigid-body fit, residuals, field geometry |
| `analyze.py`, `batch_analyze.py` | Per-match metrics, slip events, and camera-comparison windows → `results4/*.json` |
| `pool.py`, `pool2.py`, `pool3.py` | The event tables, current curve, and camera-validation tables above |
| `scrub.py` | Slip distance per wheel (tread-wear numbers) → `scrub2/` |
| `figure.py` | The summary chart |
