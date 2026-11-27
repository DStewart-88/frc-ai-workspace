# New-floor practice logs: pre-competition review (Oct 5, 8, 9)

**Scope:** all 54 logs in `newfloorPractice`, about 83 min enabled in total.

| Session | Builds | Enabled |
|---|---|---|
| Oct 5 | `a365ec3` / `c0acec7` | 26 min |
| Oct 8 | `c0acec7` | 51 min |
| Oct 9 | `51350d2` (BaseComp, the competition build) | 6 min |

Every build is marked `GitDirty = Uncommitted changes` except the first five Oct 9 deploys.

**Caveats**
- The Oct 9 build has only 6 enabled minutes, and few balls went through it (0–17 shots per log). The roller-floor results below therefore use **Oct 8 as the loaded-condition proxy**.
- In the Oct 5 and Oct 8 builds only the floor's motor 19 was logged. Roof and funnel were not.

## Check before the first match

### 1. The turret's two position sources disagree by ~365°. Check the tether by hand.
- The code zeroes the turret motor at boot and assumes the turret is centered. The CANcoder sync is commented out.
- Through Oct 8 ~5:57 pm EDT, the CANcoder agreed with that zero within 3–10°. That matches the season's 7–15°.
- From the **6:22 pm EDT boot on Oct 8 onward, every boot reads −363° to −372°** on the CANcoder. That includes all of today's.
- Two possibilities:
  - **(a)** The turret is being powered on wound one full turn. The ±260° soft limits would then sit on a false zero, and the turret may travel to a true ~−630°. That is a tether risk.
  - **(b)** The CANcoder offset or mounting shifted by ~0.29 CANcoder rotations.
- A turret 360° off looks centered by eye, so only the tether shows which it is.
- **Action:** with the robot off, check that the tether is in its neutral, unwound state at center.
  - If it is wound: unwind it.
  - If it is not wound: the CANcoder offset is stale. Re-run `Turret/CalibrateEncoderZero` with the turret centered.
- Two other boots started with the turret 111° and 139° off center (Oct 6 00:13 UTC and Oct 8 21:32 UTC). The first was enabled for 12 s that way.
- A disabled-mode dashboard alert on |`Turret/SyncError`| > 15° would catch both cases. The signal is already logged.

### 2. Brownouts

| Session | Brownout onsets | Rate | Time browned out | Min battery |
|---|---|---|---|---|
| Oct 5 | 258 | 9.9 per enabled minute | 32 s | 5.95 V |
| Oct 8 | 93 | 1.8 per minute | 11.5 s | 6.10 V |
| Oct 9 | 0 | — | — | 8.2 V (light use) |

What was happening at each of the 334 onsets:

| State | Share of onsets |
|---|---|
| Driving hard, not shooting (drive supply > 100 A for the 4 motors; median command 4.1 m/s, i.e. full stick) | 44% |
| Shooting while nearly stationary (drive < 40 A) | 35% |
| Both | 19% |

- The stationary case is the shooting stack alone. A clear example is Oct 8 22:56 UTC: the battery fell from 11.3 V to 6.5 V the instant shooting started. In the first 50 ms the logged currents were:
  - shooter ~45 A (from cold)
  - feeder ~25 A
  - floor motor 19 ~35 A (roof and funnel not logged)
  - intake ~20 A
- After that the system oscillates between brownout and recovery.
- **Battery depletion vs. match-level draw.** Batteries were run until dead in practice, so I rebuilt each battery's stint from the logs. A new battery is inferred where the resting voltage jumps at boot.
  - On normally charged batteries, **82% of brownout onsets came after the battery had already delivered more than a match's worth of charge.** A match is ~4.5 Ah per the season measurement in `brownout-analysis.md`. The logged Ah figures undercount (roof and funnel were unlogged before Oct 9, and roboRIO/radio/Limelight draw isn't logged), so the true share is higher. Most practice brownouts are therefore the familiar late-match pattern, made more frequent by long stints.
  - The draw rate itself is at or above match pace. The heaviest stints averaged 110–134 A logged, against 120–160 A in season matches. That is why a battery reached a match's worth of charge in ~100–180 s of enabled time.
  - **18% (57 onsets) came before 4.5 Ah**, which is inside one match's charge. These came from stacked peaks of roughly 350–450 A logged: ~160–180 A of full-stick drive plus a shooter cold start, intake, floor and feeder all at once. Example: Oct 8 5:23 pm EDT, a brownout 37 s into a battery that rested at 12.75 V, with only 1.8 Ah drawn. **This can happen in a match.**
  - **26 onsets came from a battery that was swapped in already low** (11.4–11.5 V resting, Oct 8 ~6:56 pm EDT). These are a practice artifact.
  - One stint looks like a weak battery: Oct 5 ~8:08–8:20 pm EDT, 27 brownouts during drive-only use at ~1.2 Ah, with ~23 mΩ apparent resistance against 12–17 mΩ for the others. Pull that battery if it can be identified.
  - Oct 5 batteries all started at 12.41–12.45 V resting and had 9.9 brownouts per minute. Oct 8 batteries started at 12.57–12.96 V and had 1.8 per minute. Builds also differed, so this is suggestive, not proof. Still, load fully charged batteries tomorrow.
- The shooter still starts **cold in most shoot windows** (e.g. 16 of 21, 24 of 43 per log). The idle-at-ready-speed fix is not in the code yet.

## Drive parameters (TorqueCurrentFOC, kP 70 / kS 5.5 / kV 20)

### 3. Drive kV = 20 A/(wheel rps) makes the robot run ~27% faster than commanded at partial stick
- In torque-current control, kV multiplies the *target* velocity in amps. The motor's back-EMF is already handled by the current loop, so kV only needs to cover viscous drag.
- Steady state is reached where `kS + kV·target + kP·(target − actual) = current needed`, which solves to `actual ≈ target·(1 + kV/kP) = 1.29 × target`.
  - This is the same structural-error equation as the old 0.124 V bug, in the opposite direction.
- **Measured:**
  - Steady-state wheel speed / setpoint was **1.25–1.29** in every session with usable data (n = 15–166 windows each).
  - Independent check from the gyro: yaw rate / commanded omega was **1.16–1.20** (slightly lower because turning scrubs).
- **Measured holding current:** cruising at 0.3–1.3 m/s takes only **~5–10 A** per motor, which fits ≈ 2 A + 2.2 A/rps. The current gains command 25–90 A for the same speeds.
- **Fix:** kV ≈ 1–2 A/rps (Nashoba runs 1.2 on the same template). Keep kS for now. Expected effect:
  - At partial stick the robot slows to what is commanded, ~22% less than drivers feel today.
  - Full stick is unchanged, because the motors are at battery voltage there anyway.
  - Acceleration is unchanged, because kP still saturates the 90 A torque limit on any real step.
- **Risk:** this changes driver feel. Only make it if drivers can practice on it.
- Auto is not hurt by the overspeed, since the path PID corrects it, but auto lags badly in the sprints:
  - PathPlanner `maxVel` is 4.58 m/s and `maxAccel` is 9.3 m/s².
  - The robot delivers ~3.5 m/s, sagging toward 9 V.
  - Setpoint error reaches 1.6–2.0 m mid-path and recovers to within ~10 cm at the end.

### 4. Steer under TorqueCurrentFOC tracks much worse than the season's voltage steer

| Metric | Newton Q23/Q64 (Voltage, kP 100) | Oct FOC (kP 130 A/rot, kS 6 A) |
|---|---|---|
| Heading error while moving, median | 4.6–4.8° | **11–16°** |
| Heading error while moving, p95 | 34–36° | **48–62°** |
| Error with setpoint steady ≥ 0.3 s, p95 | ~2° | **13–31°** |
| Holding current / sign flips | 1.3 A / 2.5–4 per s | **3.5–4.7 A / 7–15 per s** |

- kP of 130 A per rotation is only 0.36 A per degree, so the steer is soft.
- kS of 6 A with `UseClosedLoopSign` flips the full 6 A each time the error crosses zero. That is a dither.
- **Lowest-risk fix for tomorrow:** set `kSteerClosedLoopOutput` back to `Voltage` with the season gains (kP 100, kD 0.5, kS 0.1, kV 2.49). The commented values are already in `TunerConstants`. Steer and drive output types are independent, so drive can stay on FOC.
- There is still no steer supply limit. The earlier recommendation of 20 A per motor stands.

## Roller floor

### 5. The floor itself is healthy (Oct 9, all three motors logged)

| Motor | Applied voltage | Speed | Steady supply current |
|---|---|---|---|
| Spinner | 11.1 V | ~91 rps | ~8 A |
| Roof | 11.1 V | ~92 rps | ~5.5 A |
| Funnel | 11.1 V | ~110 rps | ~6 A |

- 11.1 V on all three means "100" is the stored preference.
- Total steady draw is ~19–20 A. No stall flags fired, and stator current peaked at 49 A.
- The funnel overshoots the "100" setpoint because the loop is open (kP 0, shared kV 0.11).
- Direction is consistent across all three motors.
- **Spin-up peaks:** 55–100 A total when all three start together. The ramp config is still `DutyCycleClosedLoopRampPeriod` and does nothing for `VelocityVoltage`. Use `VoltageClosedLoopRampPeriod` 0.1–0.2 s.

### 6. The feed-gate debounce works in the competition build
- In the one Oct 9 log with turret flicker, 33 raw `Turret/OnTarget` toggles became **2 gate toggles**.
- The Oct 5 and Oct 8 builds lacked the debounce. Their floor restarted 40–90 times per minute of shooting.

### 7. The feeder is the choke point, and the 60 → 120 A change bought nothing

| Session | Stator limit | Feeder speed (target 105 rps) | Stator mean | Balls per second while feeding | Feeder energy per ball |
|---|---|---|---|---|---|
| Oct 5 | 60 A | 67–78 rps | 42–49 A | 3.2–3.9 | ~90–115 J |
| Oct 8 | 120 A | **26–50 rps** | **60–78 A** (p95 85–105 A) | 3.0–3.8 | ~130–160 J |

- On Oct 8 the feeder sat above 55 A stator for up to 118 s per log.
- Anti-jam (full −1.0 duty on the floor and feeder) fired up to **51 times in one log** on Oct 8. Each reversal put the spinner at its 60 A stator limit.
- **Interpretation:** balls are binding at the floor-to-feeder handoff. More current does not raise throughput; it only adds heat and battery load.
- **Suggest:**
  - Go back to ~60 A stator with a 40–50 A supply limit.
  - Inspect the handoff for compression.
  - Watch feeder speed under a full load on the competition build.
  - The loaded data is from Oct 8, so this is unverified on Oct 9 code.

### 8. Intake rollers stall briefly when the hopper is full
- Both rollers sit at 60 A and 0 rps in bursts of 2 s or less, totalling up to 38 s per log.
- Battery impact is small (~6 A supply). The cost is heat and wear.

## Software hygiene
- **Commit the competition build.** All nine of today's last deploys were dirty, so logs from tomorrow won't map to code.
- **Loop overruns are unchanged from the season.**
  - Disabled median is 21–25 ms. Enabled median is 24–30 ms with p95 50–90 ms.
  - Today's dirty builds read 30–48 ms, but those logs are all short and right after a deploy (JIT warm-up). Re-check the first competition log.
- **Still open from earlier reviews:**
  - The shooter follower has no current limit.
  - CAN ID constants 16 and 19 still collide on paper.
  - Drive supply limit is 45 A with `SupplyCurrentLowerTime = 0`. The `foc-vs-voltage` doc's "50 → 35 A" is stale.

## Method notes
- Python parser over the native AdvantageKit cycle timestamps.
- Steady-state windows: setpoint within ±8% for ≥ 0.5 s, voltage ≥ 1.5 V below battery, supply < 35 A.
- Shots: shooter-speed dips of ≥ 1.5 rps while the feeder runs.
- Electrical energy per meter, estimated from |I·V|, matched the logged supply current within ~7%.
