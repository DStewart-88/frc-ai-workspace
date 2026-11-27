# Component Usage Tracker ("Wheel Odometer") — Design Sketch

*This is a design sketch, not an implementation. It records the shape of the system, the decisions made, and the open questions, so someone can pick it up without having been in the discussion. The goal is an odometer for wear parts. The robot counts how much each part has been used, tells the team when it's time to inspect, and records what the inspection found. Over time those records show how far a part lasts, and whether one design lasts longer than another. Swerve wheel tread comes first because it's a wear part on every robot. The turret tether, shooter wheels and other parts come later, using the same structure.*

*Updated 2026-09-29: **implemented** on the `alerts` branch (not yet committed or tested on a robot). See "Implementation (2026-09-29)" near the end for the classes, dashboard keys and where to tune values. The storage format changed during implementation, from JSON to a plain `key=value` properties file plus a CSV service log; the sections below reflect that.*

*Related: `health-warning-system-design.md`. This system **reuses the dashboard's Alerts display but is deliberately not part of the health system**. See "Relationship to the health system" below.*

## What it's for

The team already inspects tread and decides when to replace it. What's missing is the number that goes with that decision: how far had that tread travelled? This system supplies it:

1. **Count** how far each module's wheel has travelled, continuously, on the robot.
2. **Prompt** an inspection when a module passes its interval, as a dashboard warning.
3. **Record** each inspection's result and each replacement, with the distance at that moment.

Items 1 and 3 together are the calibration data. After a season, the team can say how far tread typically lasts before it's graded Poor or replaced, and set intervals from that instead of from guesses. The same records let the team compare tread or wheel designs by durability.

## Background data (2026 log backfill, 2026-09-28)

A one-time sweep of the 2026 log archive (177 `.wpilog` files) checked that the signal exists and gave typical usage rates:

- **About 240 m of tread travel per module per match** (median 243 m, range 85–290 m, 78 FMS matches).
- **About 16–17 km per module** over the logged 2026 comp season: 62 matches and 206 enabled minutes on roboRIO `0327BA0E` (FL 17.0 / FR 17.0 / BL 16.3 / BR 15.8 km). This is an **undercount**, because build-season and shop practice aren't in the archive.
- **Front modules ran about 7% more distance than back-right.** This matters for design comparisons (below).
- **The roboRIO moved between robots.** North Shore ran on roboRIO `03223846`, which later shows up in the offseason drive tests. Counters stored on a roboRIO follow the roboRIO, not the wheels (see "Known limitations").

The sweep also measured wheel **scrub** (wheel motion that the chassis's actual motion doesn't account for). It averaged about 16% of tread travel. **Decision: count plain distance only for now.** Inspections, not a physics model, will decide what "worn" means. Scrub can always be computed later from logs if distance turns out to predict wear poorly.

## Decisions made

| Topic | Decision |
|---|---|
| What is counted | Wheel travel distance per module position (FL, FR, BL, BR). Distance only. |
| Where it lives | On the roboRIO, in a small file. Always counting, even if logs aren't saved. |
| Team actions | Two dashboard actions: **Inspected** (with a condition grade) and **Replaced** (with a tread/wheel design label). |
| Inspection snooze | The grade sets how much further the module can go before the next inspection warning. |
| Snooze reference point | Counted from the **distance at the moment of inspection**, not added to the old threshold. |
| How warnings are shown | Dashboard Alerts only (`kWarning`). **Not** on the LEDs and **not** in the health system's per-match latch. |

## Layer 1 — Counting

Each loop, for each module position:

```
distanceThisLoop = |wheelPosition(now) − wheelPosition(last loop)| × wheel radius
```

- **Source signal:** the wheel position the drive already reads every loop. `Drive.getWheelRadiusCharacterizationPositions()` already returns all four, in radians. **This adds no new CAN signals**, which matters given the bus-utilization history.
- **Absolute value:** driving forward and backward both wear tread, so direction doesn't matter.
- **Counts while disabled too.** Pushing the robot around wears tread as well, although it's negligible: about 10 m over the whole 2026 archive.
- **Controller-reboot guard:** if a drive Talon reboots, its position snaps back to zero. Any single-loop jump larger than about 1 m is ignored rather than counted. (At the robot's ~4.4 m/s top speed, one 20 ms loop covers about 0.09 m.)
- **First loop after boot:** records the starting position only and adds no distance.
- **Known small biases (acceptable because they're consistent):**
  - **Wheel radius:** the conversion uses the configured 2.0 in radius. Worn tread has a smaller real radius, so distance reads slightly high as tread wears.
  - **Steer coupling:** the drive position isn't compensated for steer coupling. That adds at most about 2% of phantom distance.

Each module position keeps two counters:

- **`lifetimeMeters`**: never reset. Used for cross-checks and recovery.
- **`sinceReplacementMeters`**: zeroed by **Replaced**. All warnings and inspection records use this one.

## Layer 2 — Persistence on the roboRIO

**Storage:** a small text file on the roboRIO, `/home/lvuser/usage/usage.properties` (one `key=value` per line, readable and hand-editable over SFTP), **not** WPILib Preferences. A properties file needs nothing beyond plain Java, so the storage code is unit-tested on a laptop.

- Preferences are editable from any dashboard, so a counter could be changed by accident.
- Every change to a Preference rewrites the saved NetworkTables file, and these counters change every loop.
- Files in `/home/lvuser` outside the `deploy/` folder survive reboots and code deploys.

**When it saves:**
- on each transition to disabled (the natural end of every match and test);
- every ~60 s while enabled, so a crash or power loss mid-session costs at most a minute;
- immediately after any Inspected or Replaced action.

**How it saves (power-loss safe):**
- Write `usage.properties.tmp` and force it onto the flash, then rename it over `usage.properties`. The rename is atomic, so a power cut mid-save leaves the previous file intact.
- Keep the prior version as `usage.properties.bak`.
- Do the write on a background thread from a copy of the current values, so a slow flash write can never stretch a robot loop.

**On boot:** load `usage.properties`. If it's missing or unreadable, fall back to `usage.properties.bak`, and show a `kInfo` note that the backup was used. If both are gone (for example after a roboRIO reimage), start from zero **and raise a `kWarning`**: *"Tread usage data was not found on the roboRIO, so the counters started from zero."* This warning also appears once on the very first boot. Losing the data should never go unnoticed. A failed save also raises a `kWarning`.

**Service history:** each Inspected or Replaced action also appends one row per module to an append-only CSV file, `/home/lvuser/usage/service-log.csv`, which opens directly in a spreadsheet. The same rows are recorded in the log as `Usage/ServiceRecords`. Columns:

`timestamp, robot_serial, event, match, module, action, grade, since_replacement_m, lifetime_m, next_inspection_at_m, old_label, new_label`

- `since_replacement_m` and `lifetime_m` are the distances **at the moment of the action**. For a replacement, that's how far the old tread got.
- `next_inspection_at_m` is the due point **after** the action.
- `event` and `match` are filled only when connected to FMS.

This file *is* the calibration dataset. It can be pulled off the roboRIO over SFTP. Timestamps are valid once the Driver Station has connected, since the Driver Station sets the roboRIO's clock. The same mechanism gives AdvantageKit log files their dated names.

**Logging (backup and cross-check):** every loop, each position logs `LifetimeMeters`, `SinceReplacementMeters`, `NextInspectionAtMeters`, `InspectionDue`, `Label` and `LastGrade` under `/RealOutputs/Usage/Tread/<FL|FR|BL|BR>/...`. Each service action is logged as `Usage/ServiceRecords`, and the dashboard status line as `Usage/LastAction`. If the file is ever lost, the last values are in the most recent log, and an offline log sweep can check that the on-robot count is right.

**Sim and log replay:**
- File reads and writes happen **only on the real robot** (`Constants.currentMode == Mode.REAL`).
- **Simulation** counts and the dashboard actions work, but everything is kept in memory and nothing is saved. That's useful for practicing the pit workflow.
- **Log replay** leaves the tracker completely inactive. The saved values aren't AdvantageKit inputs, so reading them during replay would make replays differ from the real run.

## Layer 3 — Team actions (dashboard)

Everything is done from the dashboard, following the existing pattern (e.g. `SmartDashboard.putData("Hood/Calibrate", calibrate().ignoringDisable(true))` in `Hood.java`).

**Inputs**
- **Module** chooser: *(select)*, FL, FR, BL, BR, All four. It defaults to *(select)*, so a stray button press does nothing.
- **Grade** chooser: Good / Worn / Poor.
- **Tread label** text field, used by Replaced. A replacement is **refused if the label is blank**, since an unlabeled replacement is useless for comparing designs.

**Buttons**. Both only act while the robot is **disabled**:

- **Record Inspection**
  - Stores the grade.
  - Sets `nextInspectionAtMeters = sinceReplacementMeters + snooze(grade)`. This clears the warning until then.
  - Does **not** touch `sinceReplacementMeters`.
- **Record Replacement**
  - Logs the removal: final `sinceReplacementMeters` and the old label.
  - Zeroes `sinceReplacementMeters` and stores the new label.
  - Sets `nextInspectionAtMeters = initialInterval`.

After either action, a status line on the dashboard confirms what happened, e.g. *"Inspected FL: Worn at 2.61 km. Next inspection at 3.61 km."* That way a wrong module selection is caught right away.

### Grade-based snooze (starting values; the team replaces these once data exists)

| Grade | Meaning | Next inspection after | ≈ matches |
|---|---|---|---|
| Good | No visible wear concern | +2.0 km | ~8 |
| Worn | Visible wear, fine for now | +1.0 km | ~4 |
| Poor | Should be replaced; deferring on purpose | +0.25 km | ~1 |
| *(after Replaced)* | New tread | first inspection at 2.0 km | ~8 |

**Why the snooze counts from the inspection point.** Suppose the warning fires at 2.0 km, the team gets to it at 2.6 km, and grades it Good.
- Counting from the inspection point, the next warning is at 2.6 + 2.0 = **4.6 km**. That's a full 2.0 km of use.
- Adding the snooze to the old threshold would put it at 2.0 + 2.0 = 4.0 km, only 1.4 km later. The later the inspection, the shorter the real snooze, which isn't what "Good" means.

**Grading consistency matters more than any code detail.** The grades are the calibration data, and different people will grade across a season. A one-page reference card with photos of Good, Worn and Poor tread should live in the pit.

## Layer 4 — Warnings

When `sinceReplacementMeters ≥ nextInspectionAtMeters`, raise a WPILib `Alert` at `kWarning`, for example:

> *FL tread: inspection due — 2.13 km since replacement (last graded Good at 0.00 km)*

- **Each module has its own alert**, so the dashboard shows which modules are due.
- **Separate Alerts group:** use WPILib's group constructor, `new Alert("Maintenance", text, AlertType.kWarning)`, so maintenance items show in their own dashboard widget, apart from health faults.
- **Always visible:** the dashboard also shows each module's distance since replacement and distance to its next inspection, so nobody has to wait for the warning.

### Relationship to the health system

Maintenance alerts are **plain `Alert`s, not `Fault`s**, and are **not registered with `HealthMonitor`**. This is intentional:

- **Different urgency.** A health fault means "look at this before the next match." An inspection being due can reasonably wait several matches, even when the tread is Poor. Mixing the two would teach the team to ignore the health signal.
- **The latch would misbehave.** An inspection-due condition stays true every loop until someone acts. As a `Fault`, it would latch and fire `getEndOfMatchDisplay()` after **every** match until serviced, which is the alarm fatigue the health design warns about.
- **Result:** maintenance alerts never reach the per-match latch or the end-of-match LED display. They share only the dashboard's Alerts display, in their own group.

## Comparing wheel and tread designs

The label entered at Replaced is what makes comparison possible. For it to mean anything:

- **Use a fixed, short code per design** (agreed list, no free-text variations), so records group cleanly.
- **Account for module position.** In 2026 the front modules ran about 7% more distance than back-right. Distance by itself favors whichever design sat in the back.
- **The strongest comparison runs two designs at once** on the same robot: the new design on one diagonal pair (e.g. FL + BR) and the current design on the other (FR + BL). Same matches, same drivers and same carpet mean any difference comes from the wheels.
- **What to compare:** the distance at which each design first reaches Worn and Poor, and the distance at Replaced. All of it comes straight from `service-log.csv`.

## Known limitations

- **Counters belong to the roboRIO's module slots, not to physical parts.**
  - If a module moves between robots or positions, or the roboRIO is swapped (as happened in 2026), the numbers no longer match the hardware.
  - Record a Replaced with a label that says what happened. The service log keeps the history either way.
  - A proper **Transfer** action is an open question.
- **A roboRIO reimage erases the file.** The boot warning makes this visible. Recovery means rewriting `usage.properties` from the last logged `/RealOutputs/Usage/...` values.
- **Distance is a stand-in for wear, not a measurement of it.** Defense-heavy or pushing-heavy matches wear tread faster per meter. That variation is exactly what the inspection grades capture.

## Generalizing later (not in the first build)

Each tracked part is one **usage meter**:
- a name;
- how much usage is added each loop;
- a unit;
- a first-inspection interval;
- a grade → snooze table.

Tread is the first meter, instantiated four times. Candidates to develop later, each with the usage measure matched to what actually wears the part:

- **Turret tether:** bending cycles (direction reversals, total degrees travelled), not time.
- **Shooter wheels:** shots fired (ball contacts), not flywheel revolutions.

The persistence, the two team actions, the service log and the Maintenance alerts carry over unchanged.

## Implementation (2026-09-29)

Built on the `alerts` branch, uncommitted at the time of writing. Package `frc.robot.util.usage`:

| File | Role |
|---|---|
| `Grade.java` | `GOOD` / `WORN` / `POOR`, with the dashboard label for each. |
| `UsageMeter.java` | One odometer (e.g. `Tread/FL`): the two totals, due point, label, last grade; `inspected()`, `replaced()`, save/restore. Plain Java. |
| `UsageStore.java` | The files: power-safe save with backup, fallback load, append-only CSV service log. Plain Java. |
| `TreadUsageTracker.java` | The robot side: counts the four wheels, background saves, dashboard actions, Maintenance alerts, logging. |
| `src/test/.../UsageMeterTest.java`, `UsageStoreTest.java` | 21 JUnit tests of the plain-Java parts, including the 2.6 km late-inspection example above. Run with `./gradlew test`. |

**Hookup:** 9 lines in `RobotContainer`. The tracker is created after the drive, fed `drive::getWheelRadiusCharacterizationPositions` and `TunerConstants.FrontLeft.WheelRadius`. It is a `SubsystemBase`, so the command scheduler runs its `periodic()` every loop, enabled or disabled. It does not touch `Robot.java` or the health code.

**Dashboard** (SmartDashboard folder `Usage/`): `Module` chooser, `Grade` chooser, `New Tread Label` text, `Record Inspection` and `Record Replacement` buttons, `Last Action` status line, and one summary line per module (`FL`, `FR`, `BL`, `BR`), e.g. *"1.23 km since replacement; inspect at 2.00 km; tread-A"*. Warnings appear in a separate Alerts widget, `Maintenance`.

**Where to tune:** the inspection distances (`TREAD_SCHEDULE`), the reboot-jump limit (`MAX_STEP_METERS`) and the save period (`SAVE_PERIOD_SECONDS`) are constants at the top of `TreadUsageTracker.java`.

**Verification so far:**
- The four new classes compile against the real WPILib 2026.2.1 and AdvantageKit 26.0.2 method signatures.
- All 21 unit tests pass.
- A scripted run of the counting loop behaved correctly: the first reading after boot adds nothing, forward and reverse both count, and a motor-reboot jump and a NaN reading are skipped.
- A full `./gradlew build` and on-robot testing are still to do (build order below).

## Test plan on the drive base

*All four stages were built together. Test them in this order.*

1. **Counting and logging only.**
   - No file, no dashboard.
   - Drive a session, then check `/RealOutputs/Usage/...` against an offline log sweep of the same session. They should agree within about 1%.
2. **Persistence.**
   - Add load/save and the missing-data warning.
   - Test: reboot, redeploy, and power-cut mid-session; the counts must survive.
3. **Team actions.**
   - Add the dashboard choosers, buttons and the service log.
   - Test that a press does nothing while enabled or with no module selected.
4. **Maintenance alerts.**
   - Set a temporarily low interval (e.g. 20 m) to see the warning appear, snooze by grade, and clear on replacement.
   - Confirm the health end-of-match display never fires because of it.

## Open questions

- **Grade words and snooze values.** The table above is a placeholder, and three grades may or may not be enough.
- **First-inspection interval.** 2.0 km is a starting guess, about 8 matches. At ~240 m per match, a full event is roughly 3–4 km including practice matches.
- **Transfer action** for modules that move between robots or positions: build it, or just record through Replaced?
- **Undo last action**: worth having for a mis-click, or is the service log enough to fix one by hand?
- **Where the Maintenance group sits in the dashboard layout**, e.g. its own pit tab.
- **Seeding the current test-base tread.** Estimate its distance, or record a Replaced now and start from zero?
