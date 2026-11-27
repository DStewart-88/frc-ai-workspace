# Vision System Analysis: Why the Robot Pose Shakes, and How to Tune It

*An analysis of the 2026 vision/pose-estimation system (3 Limelights → WPILib pose estimator) using all 21 competition match logs (Granite State, NE Championship/Newsom, Worlds/Newton). The goal is to explain why the reported robot position shakes and jumps, and to identify changes that make it steadier without making it less accurate, since this vision setup carries into next season.*

## Summary

The shaking is real and measurable, and most of it is **not** the vision system "keeping up with a fast-changing robot." It is the code's tuning. When the robot is sitting completely still, the logged position still wanders **about 11 cm peak-to-peak (worst case 79 cm)** and heading wanders about 1°. During matches, vision yanks the pose by more than 10 cm in a single loop about **83 times per minute**.

Three things combine to cause this:

1. **The code trusts every camera frame far too much.** The noise values in `VisionConstants` assume close-range fixes are accurate to a few millimetres. They are actually accurate to about 8–10 cm. So each frame drags the pose most of the way to whatever that one camera said, about 30 times a second.
2. **The three cameras disagree with each other by about 15 cm,** even though each one is steady to about 2 cm on its own. With per-frame trust that high, the pose hops between camera opinions. Part of the disagreement is a measurable **2–3° yaw error in the configured mounting of both side cameras** (opposite directions).
3. **Wheel odometry is weak, which is why vision is leaned on so hard.** The Pigeon's rotation scale is off by up to 1% (5–15° of heading drift per match), and the wheels over-report distance by about 9%. Left alone, odometry drifts as much as **20 m** over a match.

Also: **the MegaTag2 filter typo (`maxY - minX`) is still in the code**, on both `main` and `BaseComp` (checked against GitHub, BaseComp as of Oct 3, 2026). Fixing it by itself makes the shaking *worse* (83 → 317 jumps/min), because MegaTag2 is currently weighted as if it were ~1 cm accurate and is the mode most hurt by the side-camera yaw error.

Every proposed change was re-run through an exact replica of the robot's pose estimator on all 21 matches. The recommended package (calibrate first, then four code changes) gives these results:

| | As run | Recommended |
|---|---|---|
| Pose wobble while robot is still (peak-to-peak) | 10.4 cm | **7.0 cm** |
| Heading wobble while still | 0.97° | **0.36°** |
| Vision jumps > 10 cm per minute | 83 | **43** |
| Position error vs. an independent camera, typical / worst 10% | 11.5 / 37.5 cm | **11.5 / 32.1 cm** |
| Heading error, typical / worst 10% | 2.2° / 4.7° | **1.2° / 3.0°** |

So: less shake, the same typical accuracy, better worst-case accuracy, and heading error roughly halved.

---

## What the shaking looks like in the data

The cleanest test: find moments when the robot is physically stationary (wheels and gyro not moving for at least 1.4 s while enabled). There were 46 such stretches, 159 s in total. During those moments the position should not change at all, so any movement is caused purely by vision.

| While the robot is still | Median | Worst |
|---|---|---|
| Logged pose peak-to-peak | 10.9 cm | 79 cm |
| Logged heading peak-to-peak | 1.0° | 6.4° |
| Largest single-loop pose jump | 6 cm | 41 cm |
| One camera's own frame-to-frame scatter | **2.4 cm** | |
| Disagreement *between* cameras (same moment) | **15.6 cm** | 52 cm |

How many cameras see tags matters a lot. With only one camera seeing tags, the still-robot wobble is 6.9 cm. With two or three, it is 13.2 cm. Each camera is individually steady, but they don't agree, and the estimator keeps switching between them.

## Why it shakes

### 1. Every camera frame is trusted far too much

Each time a camera reports a pose, the code blends it into the position estimate. How far the estimate moves toward the camera's answer depends on how noisy the code *believes* that camera is. That belief comes from `VisionConstants`:

- MegaTag1: noise = 0.02 m × distance² ÷ tag count
- MegaTag2: one-tenth of that

Measured against an independent reference built from the *other* two cameras plus wheel odometry, the real noise is:

| Observation type | Distance | Measured noise (1σ) | Code assumes |
|---|---|---|---|
| MegaTag1, 2+ tags | under 1.5 m | 7.6 cm | 0.4 cm |
| | 1.5–2.5 m | 7.9 cm | 3.2 cm |
| | 2.5–3.5 m | 8.8 cm | 7.2 cm |
| | 3.5–5 m | 11.4 cm | 14.5 cm |
| MegaTag1, 1 tag | 1.5–2.5 m | 8.9 cm | 8.0 cm |
| | 3.5–5 m | 15.8 cm, plus 18% wild (>0.5 m) | 36 cm |
| MegaTag2, any | 1.5–2.5 m | 9–11 cm | **0.3–0.8 cm** |
| | 3.5–5 m | 16–18 cm | **1.4–3.6 cm** |

The big miss is the **error floor**. Even at close range, no camera beats about 7–8 cm, but the d² formula drives the assumed error toward zero as distance shrinks. For MegaTag2 the assumption is at least 10× too optimistic at every distance, and far more up close.

The result: in the matches checked, the median accepted frame moves the pose **42% of the way** to what that one camera said, and heading 20% of the way. That happens 20–30 times per second across three cameras, so the estimate is effectively just "the last frame that arrived."

### 2. The three cameras disagree, and the side cameras have a yaw error

Fixed position offsets per camera (a camera mounted a few cm from where its config says) are small: **1–5 cm**, consistent from match to match. That isn't the problem.

The **configured yaw (rotation) of both side cameras is off by roughly 2–3°, in opposite directions.** Two independent measurements agree:

| Camera | MegaTag2 sideways error vs. distance | MegaTag1 heading vs. other cameras |
|---|---|---|
| limelight-back (cam 0) | ~0° (0.0 to +0.8°) | +0.6 to +1.0° |
| limelight-right (cam 1) | **−2.1 to −2.5°** | **−2.1 to −2.8°** |
| limelight-left (cam 2) | **+2.2 to +3.1°** | **+1.1 to +2.1°** |

(Ranges cover the three events; the same pattern appeared at every one.) Interpreted physically: **limelight-right is actually pointed about 2.2° further clockwise (seen from above) than its configured yaw, and limelight-left about 2.5° further counter-clockwise.** Both side cameras point slightly further outward than the configuration says.

Why it matters:

- **MegaTag1** (full 3D solve from the tags) barely notices a yaw error in position. It does notice it in *heading*, so the side cameras pull the robot's heading ±2–3° in opposite directions. That is the 1° heading wobble while still.
- **MegaTag2** takes the robot's heading as given and uses the camera's configured yaw to work out where the tag is. A 2.5° yaw error at 4 m is a 17 cm sideways position error. Left and right cameras err in opposite directions, so at 4–6 m their MegaTag2 answers disagree by **about 30 cm or more**.

After removing the yaw error and the fixed offsets, the cameras still disagree by about 8 cm, in ways that depend on where the robot is and which tags it sees. The logs can't pin down the cause. Plausible ones are lens calibration (intrinsics) and small real-world tag placement differences. It is the floor this tuning works around rather than removes.

### 3. Odometry is weak, so vision has to be trusted heavily

Rebuilding pure wheel-plus-gyro odometry from the logs shows it drifting **up to 20 m over a match** (Newton Q99). Two separate causes:

**Pigeon rotation scale error.** Comparing gyro heading with the three cameras' consensus heading:

- At Granite State, every match showed the gyro over-counting rotation by about 1%: CCW turns read ~3.2° too much per revolution, CW turns ~4.0°.
- At Newsom and Newton, it flipped sign and shrank to about 0.3% (under-counting ~1° per revolution).
- This robot spins about **7,000° total per match**, so even 1% adds up to **5–15° of heading drift by the end of a match.**
- The gyro is rock-solid when the robot is still (0.01–0.04°/min), so this is a scale error, not a bias or boot-calibration problem.
- The scale change between events has no matching code change (no Pigeon config is applied at all), so something physical likely changed: a remount or replacement. Worth asking the team.

CTRE provides a setting for exactly this: `Pigeon2Configuration.GyroTrim.GyroScalarZ`, in degrees per rotation.

**Wheel distance over-reported.** With the heading error removed, odometry still reports **about 9% more distance than the robot actually travels** (median vision/odometry ratio 0.914; 0.92–0.96 in clean matches). That is consistent with the 2.0" wheel radius in `TunerConstants` being a nominal value, plus tread wear. On top of that is a long tail of slip events where odometry is off by 20–40% over a second or two.

This is the trade-off that limits tuning. Trusting vision less removes the shake, but the estimate then lags whenever odometry slips. Better odometry is what unlocks smoother vision.

## The MegaTag2 typo: still there, and fixing it alone backfires

`Vision.java` still computes `new Translation2d(maxX - minX, maxY - minX)` (line 120 on `BaseComp` and `main`; the vision filtering and noise code is identical on both branches as of Oct 3, 2026). The August software-performance report showed this throws away ~99% of MegaTag2 frames. But with today's noise settings, the newly accepted MegaTag2 frames come in assumed to be accurate to under a centimetre, and the side-camera yaw error is largest in MegaTag2. Replayed:

| | Still wobble | Jumps >10 cm / min | Worst-10% position error |
|---|---|---|---|
| As run | 10.4 cm | 83 | 37.5 cm |
| Typo fixed, nothing else | **16.4 cm** | **317** | 32.6 cm |

Fixing the typo alone improves worst-case accuracy but nearly quadruples the jumping. **Fix it together with the noise-model change and speed-scheduled trust, ideally after the side-camera yaw is corrected.**

### What MegaTag2 needs before it helps

The variance gate was meant to throw out bad poses. Because of the typo, it threw out nearly all MegaTag2 instead. Letting that data back in only helps if it is also *weighted* correctly and *correct* in the first place. Each fix below was stacked onto the previous one and replayed on all 21 matches:

| Step (cumulative) | Still wobble | Jumps >10 cm/min | Position error typ / worst-10% | Heading error typ |
|---|---|---|---|---|
| As run (MegaTag2 effectively off) | 10.4 cm | 83 | 11.5 / 37.5 cm | 2.2° |
| 1. Fix the typo | 16.4 cm | 317 | 13.4 / 32.6 cm | 2.2° |
| 2. + correct side-camera yaw | 16.2 cm | 263 | 12.3 / 36.3 cm | 1.5° |
| 3. + measured noise model, heading from multi-tag MegaTag1 only | 13.9 cm | 175 | 11.4 / **31.5** cm | 1.4° |
| 4. + speed-scheduled trust | **7.0 cm** | 57 | 12.1 / 34.3 cm | 1.4° |
| 5. + skip MegaTag2 while spinning > 2 rad/s | 7.0 cm | 52 | 12.2 / 33.8 cm | 1.4° |
| 6. + gyro scale and wheel radius calibration (= recommended) | 7.0 cm | **43** | 11.5 / 32.1 cm | **1.2°** |
| Code only: steps 1, 3, 4, 5, no calibration | 7.2 cm | 58 | 12.0 / 35.9 cm | 2.2° |

What each step contributes:

- **Correcting camera yaw (step 2)** makes MegaTag2 *correct*. It cuts jumps by about a sixth and is the biggest heading improvement. By itself it doesn't stop the shaking, because the frames are still over-trusted. The replay can only approximate this step: it rotates each logged MegaTag2 frame about its tags after the fact, and its worst-case number moved the wrong way. A log taken after recalibration is the real test.
- **The measured noise model (step 3)** makes MegaTag2 *weighted correctly*. This is where the new data turns into accuracy: the best worst-case error of any configuration tested (31.5 cm vs. 37.5 cm today). It is still jumpy, because even correctly weighted, each frame moves the pose about halfway at 20–30 frames per second.
- **Speed-scheduled trust (step 4)** is what stops the shaking, and it costs a few cm of worst-case accuracy.
- **The spin gate (step 5)** is a small, roughly neutral improvement. Optional.
- **Gyro and wheel calibration (step 6)** win back the accuracy that step 4 costs, and further improve heading.

The minimum for the new MegaTag2 data to be a net improvement over today is the code-only row. That's less shake than today, a better worst-case, and typical accuracy within a centimetre of today's. The calibrations are what turn it from "no worse" into clearly better.

A second, smaller bug sits in the same block. The min/max trackers start at `minX = 16, minY = 8`, but the field is 17.55 m long. Within about 1.3 m of the red alliance wall (x > 16.2 m), every MegaTag2 frame gets rejected as "high variance" even when the frames agree perfectly.

## What was tested

I rebuilt WPILib's `SwerveDrivePoseEstimator` vision logic offline and fed it the exact odometry and camera frames from each log. **Validation:** with the robot's real settings, the replica reproduces the logged `Odometry/Robot` pose to a median of 0.0 mm and a worst case of 3 cm over full matches (three matches checked). So it can be trusted to predict what the robot would have done with different settings.

Each configuration was scored on all 21 matches:

- **Shake:** still-robot wobble, and vision-induced jumps > 10 cm per minute.
- **Accuracy:** run the estimator with one camera removed, and score it against that held-out camera's multi-tag fixes (< 3.5 m), rotating through all three cameras. Scoring against cameras the estimator is listening to would reward copying them, which is exactly the shake.

Accuracy numbers have a floor of about 10 cm, because the held-out camera has its own ~8 cm geometry errors. Differences between configurations are meaningful; the absolute values are conservative.

| Configuration (median of 21 matches) | Still wobble | Still heading | Jumps >10 cm/min | Position error typ / worst-10% | Heading error typ / worst-10% |
|---|---|---|---|---|---|
| A. As run | 10.4 cm | 0.97° | 83 | 11.5 / 37.5 cm | 2.2 / 4.7° |
| B. Typo fix only | 16.4 cm | 0.90° | 317 | 13.4 / 32.6 cm | 2.2 / 4.7° |
| C. Heavy smoothing (trust ÷16, calibrated) | 5.8 cm | 0.75° | 5 | 14.6 / 45.8 cm | 1.2 / 2.9° |
| D. Code changes only, no calibration, typo *not* fixed | 6.4 cm | 0.39° | 34 | 12.7 / 41.9 cm | 2.2 / 4.5° |
| **E. Recommended (calibrate + all code changes)** | **7.0 cm** | **0.36°** | **43** | **11.5 / 32.1 cm** | **1.2 / 3.0°** |
| F. Same, with stronger smoothing when still (16/4/1.5) | 5.5 cm | 0.36° | 60 | 11.4 / 32.0 cm | 1.2 / 3.0° |

What the comparison shows:

- **Uniform smoothing (C)** kills the shake but makes worst-case accuracy much worse, because the estimate lags after wheel slips.
- **Speed-scheduled trust (E, F)** gets most of the smoothing where it's free (robot still, so odometry is perfect) and keeps trusting vision while driving, when odometry slips.
- **Calibration is where the accuracy comes from.** Code-only changes (D) reduce shake but cost some worst-case accuracy and do nothing for heading.
- F is the better choice if being steady *while stopped to shoot* matters most. E is the more balanced default.
- **Don't add a "reject single-tag beyond 3.5 m" filter.** It was tested and made worst-case accuracy noticeably worse (32.1 → 38.6 cm) by leaving the robot blind when only distant tags are visible. The existing ambiguity filter already catches most bad far single-tag frames.

For comparison, 6328's 2026 code trusts odometry far more: state standard deviations of 0.003 m / 0.002 rad versus WPILib's default 0.1, giving per-frame vision trust roughly 15–30× lower than ours. They can afford that with their camera setup and odometry quality. Copying their numbers directly onto this robot (tested) loses accuracy, because our odometry slips too much. Their structure (vision heading only from multi-tag frames) is reflected in the recommendation.

## Recommendations, in order

### Step 1: Calibrate (no code changes)

These values are specific to *this* robot. On next year's robot, redo them once the cameras and gyro are mounted.

**a. Side-camera yaw.** In each Limelight's web UI, adjust the robot-space camera pose yaw:

- **limelight-right:** turn its configured yaw ~2.2° clockwise (as seen from above).
- **limelight-left:** turn it ~2.5° counter-clockwise.
- **limelight-back:** leave as is.

Limelight's sign convention for yaw should be checked before entering numbers. Make the change, then confirm that camera's MegaTag1 heading moves *toward* the other cameras' headings. The definitive check is the verification log in Step 3; the analysis scripts measure each camera's yaw error directly from any log where the robot drives around in view of tags.

**b. Pigeon rotation scale (`GyroScalarZ`).** Spin test:

1. Square the robot against a wall or field line and reset heading.
2. Spin 10 full turns one way, re-square, and read the heading error.
3. Repeat the other way.
4. Error ÷ 10 is the degrees-per-rotation trim.

Enter it in `GyroIOPigeon2` via a `Pigeon2Configuration` (currently `pigeonConfigs = null`, so nothing is applied). Re-check after any Pigeon remount, since the scale appears to have changed between Granite State and Newsom.

**c. Wheel radius.** Run the existing **"Drive Wheel Radius Characterization"** auto routine (already on the chooser), and put the result in `kWheelRadius` in `TunerConstants`. The logs suggest the true effective radius is ~4–8% under 2.0". Repeat periodically as tread wears; this ties directly to the tread-wear tracker.

### Step 2: Code changes (after Step 1a)

All four go in `Vision.java` / `VisionConstants.java`. Vision also needs the robot's speed and spin rate; `Drive` already has `getSpeed()` and `getRate()`.

**1. Replace the noise model** with the measured one: an error floor plus distance growth, trust scaled by robot speed, and heading only from multi-tag MegaTag1.

```java
// VisionConstants.java: measured from 2026 match logs
public static double linearStdDevFloor = 0.07;   // m: no camera beats ~7 cm, even up close
public static double linearStdDevCoeff = 0.005;  // m per m^2, divided by tag count
public static double angularStdDevFloor = 0.035; // rad (~2 deg)
public static double angularStdDevCoeff = 0.01;  // rad per m^2, divided by tag count
public static double angularStdDevScale = 30.0;  // lean on the (calibrated) gyro for heading
// Trust vision less when odometry is trustworthy (robot still/slow)
public static double stillStdDevMultiplier = 8.0; // robot speed < 0.2 m/s
public static double slowStdDevMultiplier = 4.0;  // 0.2 - 1.5 m/s
public static double fastStdDevMultiplier = 2.0;  // > 1.5 m/s
public static double mt2MaxYawRateRadPerSec = 2.0;
```

```java
// Vision.java: replaces the "Calculate standard deviations" block
double d = observation.averageTagDistance();
int n = observation.tagCount();
double speed = speedSupplier.getAsDouble();
double speedMult =
    speed < 0.2 ? stillStdDevMultiplier
        : speed < 1.5 ? slowStdDevMultiplier : fastStdDevMultiplier;
double linearStdDev = speedMult * (linearStdDevFloor + linearStdDevCoeff * d * d / n);
double angularStdDev =
    (observation.type() == PoseObservationType.MEGATAG_1 && n >= 2)
        ? angularStdDevScale * (angularStdDevFloor + angularStdDevCoeff * d * d / n)
        : Double.POSITIVE_INFINITY; // no heading from single-tag MT1 or from MT2
if (cameraIndex < cameraStdDevFactors.length) {
  linearStdDev *= cameraStdDevFactors[cameraIndex];
  angularStdDev *= cameraStdDevFactors[cameraIndex];
}
```

`linearStdDevMegatag2Factor` and `angularStdDevMegatag2Factor` are no longer used. MegaTag2 is measured to be no more accurate than MegaTag1 on this robot, so it gets the same model. Also add a third entry to `cameraStdDevFactors` (it has two for three cameras).

**2. Fix the variance check** (the typo plus the start values):

```java
double maxX = Double.NEGATIVE_INFINITY, minX = Double.POSITIVE_INFINITY;
double maxY = Double.NEGATIVE_INFINITY, minY = Double.POSITIVE_INFINITY;
// ... same min/max loop ...
double variance = (maxX >= minX) ? Math.hypot(maxX - minX, maxY - minY) : 0.0;
```

**3. Skip MegaTag2 while spinning fast.** MegaTag2 error grows with spin rate (σ 12.6 cm when steady → 19 cm above 3 rad/s), because it relies on the heading at the exact frame time.

```java
|| (observation.type() == PoseObservationType.MEGATAG_2
    && (variance > 0.2 || Math.abs(yawRateSupplier.getAsDouble()) > mt2MaxYawRateRadPerSec))
```

**4. Wire the suppliers** in `RobotContainer`: pass `drive::getSpeed` and `drive::getRate` into the `Vision` constructor (stored as `DoubleSupplier speedSupplier, yawRateSupplier`).

Also worth logging for next time: each accepted frame's standard deviation **per camera** (today a single `LinearStddev` key gets overwritten by whichever frame came last), and the speed multiplier in use.

### Step 3: Verify with one drive-test log

Drive for ~2 minutes in view of tags, including several 3–5 second full stops and a few in-place spins in each direction. Re-run the analysis scripts on that log. Targets:

- Each camera's measured yaw error under ±0.5°.
- Gyro scale residual under ~0.3° per revolution.
- Odometry/vision distance ratio within ±2% of 1.0.
- Still-robot pose wobble under ~8 cm.
- Cameras' MegaTag2 answers agreeing within ~10 cm at 3 m.

## Caveats

- **The calibration values were fitted from the same logs used to score them,** so the "Recommended" row is somewhat optimistic. The code changes alone (row D) involve no fitting.
- **The replica is exact for the estimator, but the camera frames are fixed inputs.** In reality, a better heading also makes each MegaTag2 frame better (the Limelight uses the robot's heading). The predicted MegaTag2 improvement is therefore conservative. The yaw correction was applied to logged MegaTag2 frames approximately, by rotating each frame about its tags. (A first version of this report had a replay bug that applied the correction to only some frames. It was fixed on Oct 3, and all affected numbers above were re-run.)
- **The remaining ~8 cm camera-to-camera disagreement isn't explained.** Re-running each Limelight's lens calibration and confirming the field map matches each event's field are the next things to try, and the same scripts would measure the effect.
- **Speed comes from the wheels.** A robot being shoved sideways with its wheels not turning looks "still" and is corrected from vision more slowly. At the ×8 setting, a 3 m single-tag frame still moves the pose about 10% of the way, so a shove is corrected within about a quarter second at normal frame rates.
- **Timestamps look fine.** No camera is more than ~15 ms out of step with the others, and latency isn't a meaningful source of the shake.

## Methodology

All analysis was done on the AdvantageKit `.wpilog` files with a from-scratch WPILOG parser (no replay of robot code needed). Inputs:

- 250 Hz odometry samples (`Drive/ModuleN/OdometryDrivePositionsRad`, `OdometryTurnPositions`, `Drive/Gyro/OdometryYawPositions`)
- every raw camera frame (`Vision/CameraN/PoseObservations`)
- the tags each camera saw (`RealOutputs/Vision/CameraN/TagPoses`)
- the robot's fused pose (`RealOutputs/Odometry/Robot`)

Pure odometry was rebuilt exactly as `SwerveDriveOdometry` does. The estimator replica follows WPILib's `PoseEstimator.addVisionMeasurement` step for step and was validated against the logged pose. 211,699 tag-bearing frames across 21 matches were each scored against a reference built from the *other* two cameras' good fixes (±0.5 s) carried by odometry.

Scripts are in `FRC Logs/vision-analysis/`:

| Script | What it does |
|---|---|
| `vis_common.py` | Loader, odometry rebuild, estimator replica |
| `replay.py`, `validate.py` | Replica and its validation against the logged pose |
| `odo_scale.py`, `gyro_dir.py`, `gyro_still.py` | Odometry and gyro checks |
| `vision_noise.py`, `noise_report.py` | Per-frame noise |
| `cam_bias.py`, `los.py` | Camera offsets and yaw |
| `still.py` | Still-robot wobble |
| `tune.py`, `tune_report.py` | Configuration sweep |
