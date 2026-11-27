# Camera Mounting Poses Estimated from Match Logs

*Each Limelight's position and orientation on the robot, worked out purely from 2026 match data: the 21 competition matches at Granite State, Newsom and Newton. This is an experiment in whether camera calibration can be recovered from normal robot use. These values should be compared against manual measurements and the current Limelight web-UI settings once those are taken (comparison table at the bottom).*

## Method

Each camera logs `tx` and `ty`, the horizontal and vertical angles from its crosshair to the tag it is tracking (`Vision/CameraN/LatestTargetObservation`). The logs also record:

- which tags were in view (`RealOutputs/Vision/CameraN/TagPoses`, with full 3D tag positions from the field layout)
- the robot's pose (`RealOutputs/Odometry/Robot`)

I kept only moments when a camera saw exactly one tag and the robot was nearly still (under 0.3 m/s, under 0.2 rad/s), giving 5,106 samples in total. For each camera, a least-squares fit finds the six mounting values (forward, side, height, roll, pitch, yaw) that best predict every logged `tx`/`ty`. Uncertainty comes from a leave-one-match-out jackknife and from fitting each event separately.

Conventions: robot centre = centre of the four swerve modules, on the floor. **Forward** is +ahead, **left** is +left, **height** is above the carpet. **Yaw** is measured counter-clockwise from robot-forward, seen from above. **Tilt up** is degrees above horizontal. Limelight's own sign conventions aren't documented, so translate signs to the web UI's existing convention when comparing.

## Results

| | limelight-back (cam 0) | limelight-right (cam 1) | limelight-left (cam 2) |
|---|---|---|---|
| Forward | −8.8 in (−0.223 m) | −9.3 in (−0.237 m) | −9.8 in (−0.250 m) |
| Left (+) / right (−) | +5.3 in (+0.135 m) | −15.2 in (−0.386 m) | +14.9 in (+0.378 m) |
| Height above floor | 9.9 in (0.252 m) | 13.2 in (0.335 m) | 7.6 in (0.193 m) |
| Tilt up | 13.4° | 13.6° | 14.9° |
| Yaw | ≈180° (180.8°) | −90.7° (points right) | +91.7° (points left) |
| Roll | ≈0 (−0.5°) * | ≈0 (+1.2°) * | ≈0 (−1.0°) * |
| Samples | 1,646 | 2,147 | 1,313 |
| Fit residual (tx / ty) | 1.31° / 0.50° | 0.38° / 0.28° | 0.42° / 0.37° |

\* Roll can only be stated relative to the image orientation the Limelight reports, so it could be ≈0° or ≈180° depending on how the camera is physically mounted and set up. The direction the camera points (yaw, tilt) is unaffected by this.

### How much to trust each number

| | limelight-back | limelight-right | limelight-left |
|---|---|---|---|
| Jackknife ±1 SE: forward / side / height | 0.9 / 1.4 / 0.5 in | 0.6 / 0.5 / 0.5 in | 0.4 / 0.4 / 0.3 in |
| Jackknife ±1 SE: roll / tilt / yaw | 0.2° / 0.2° / 0.6° | 0.2° / 0.2° / 0.3° | 0.2° / 0.3° / 0.2° |
| Spread between events: forward / side / height | **6.9 / 12.9** / 2.0 in | **5.6** / 2.3 / 1.5 in | 0.1 / 1.4 / 0.4 in |
| Spread between events: roll / tilt / yaw | 1.6° / 1.0° / **3.4°** | 1.3° / 1.2° / **3.1°** | 0.5° / 1.2° / 0.2° |

- **limelight-left is very consistent:** within about 1.4" and 1.2° across all three events. It's the best test case for comparing against manual measurements.
- **limelight-right and limelight-back look different at Newton** (forward position about 5" further forward, yaw about 3° different) than at the other two events. Newton had the fewest samples (about 235 per camera), but two cameras shifting at the same event is also what a camera knocked or remounted between events would look like. Worth asking the team whether anything was done to those mounts before Worlds.
- **The back camera's position is the least reliable value** (12.9" event spread side to side).

## Known limitations of the method

1. **Circular reference for position.** The robot pose used as the reference comes from the pose estimator, which is fed by these same cameras with their *current* configured mountings. A camera's estimated position is therefore partly pulled toward its configured position. Yaw and tilt are much less affected, because the gyro and the other cameras anchor heading. **If the manual measurement disagrees with these positions but matches the current Limelight settings, this is the likely reason.**
2. **Distance along the camera's line of sight is weakly determined.** For the side cameras that is the left/right coordinate; for the back camera it is forward/back. An earlier, simpler fit (horizontal angle only, ignoring height and tilt) put the side cameras at about 12" from centre instead of 15". Treat the side cameras' left/right values as about ±3".
3. **The robot is assumed flat.** Robot tilt (bumps, acceleration) isn't logged, so it shows up as noise in pitch and height. Using only near-stationary samples limits this.
4. **The tag layout is the WPILib welded field.** If an event used the AndyMark field variant, tag positions differ by up to a few cm.

A cleaner version of this method for next season: park the robot at a few surveyed spots on a field with the pose *reset* to the known spot, then let each camera see tags. That removes limitation 1, because the reference pose no longer comes from the cameras.

## Comparison (to fill in)

| Value | Camera | From logs | Manual measurement | Current Limelight UI setting |
|---|---|---|---|---|
| Forward | back | −8.8 in | | |
| | right | −9.3 in | | |
| | left | −9.8 in | | |
| Left/right | back | +5.3 in | | |
| | right | −15.2 in | | |
| | left | +14.9 in | | |
| Height | back | 9.9 in | | |
| | right | 13.2 in | | |
| | left | 7.6 in | | |
| Tilt up | back | 13.4° | | |
| | right | 13.6° | | |
| | left | 14.9° | | |
| Yaw | back | 180.8° | | |
| | right | −90.7° | | |
| | left | +91.7° | | |
| Roll | all | ≈0 (±1°) | | |

Scripts: `FRC Logs/vision-analysis/cam_mount6.py` (sample extraction) and `mount_fit6.py` (fit).
