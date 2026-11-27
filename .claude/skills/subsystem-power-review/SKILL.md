---
name: subsystem-power-review
description: Log-based power and behavior review of one robot subsystem (or a whole event's power budget) from WPILOG/AdvantageKit match logs, ending in ranked findings and a team-facing summary in amps. Use when asked to analyze a mechanism's current draw, brownout contribution, or efficiency from logs.
---

# Subsystem power review

The repeatable method behind the 2026 shooter, feeder, HotTub, turret and BOB event reviews (`archive/2026/shooter-power-analysis.md`, `feeder-power-analysis.md`, `bob-power-review.md`). Use it on one mechanism, or on the whole robot for an event.

Follow `CLAUDE.md` throughout, especially the analysis standards: falsify before settling, brownout metrics, current (A) for the team, and no blaming batteries.

## 0. Scope it first

Before parsing anything, state:
- **The subsystem**, its motors (CAN IDs and bus), and how they are coupled (follower? opposed?).
- **The question.** For an open-ended dig, the question is "where does the power go, and what's worth changing."
- **The matches.** Use the same match set across subsystems so numbers line up. In 2026 that was Newton Q23/Q34/Q64 plus Newsom Q14. Include at least one weak-battery and one healthy-battery match.
- **The build in use** for each log: git SHA, dirty flag, and gains if logged (`knowledge/logging.md` §1). If two logs could be different tunes and you can't tell, say so.

## 1. Read the code that commands it

Read the subsystem and its callers before the logs. The code explains the numbers. Record:
- **Control mode** (Voltage / TorqueCurrentFOC / duty / open loop), gains, and **feedforward ceiling**. Needed voltage = kV·v + kS; compare it with 12 V and with the sagged bus voltage.
- **Default command**, and when it runs: coast? hold? idle?
- **What starts it, and what else starts at the same moment** (parallel command groups, shared gates).
- **Current limits on every motor, including followers.** Check the limits are actually applied, and that ramp and limit fields match the control mode. Wrong-mode fields fail silently (lessons #11–#15).
- **Status-signal rates**, and whether supply current is logged at all.

## 2. Load and resample

- Parse with `scripts/wpilog_reader.py`, or Pitwall's reader.
- **Resample onto a uniform 50 Hz grid** with sample-and-hold. AdvantageKit logs on change, so raw-sample averages over-weight busy periods.
- **Slice by enabled** (`/DriverStation/Enabled` in 2026), then by the gates that drive the mechanism (2026: `IsShooting`, `OnTargetRobot`). Report time in each slice.
- List the exact signals used and their units. Say whether velocities are motor-shaft or mechanism (2026 logged motor-shaft rps).

## 3. Get supply current right

- Prefer **measured supply current**.
- Where it isn't logged, **estimate it** as Σ|V_motor · I_motor| / V_batt, and label every such figure "estimated".
- When measured and estimated both exist, compare them. In 2026 the estimate matched at r = 0.9985 for drive, but read ~7% low on feeder energy.
- Remember status-frame sampling under-reads short spikes (lessons #43). Infer spikes from the battery dip if the current signal is slow.
- The 2026 robot had a PDP 2.0 and no power-distribution data. If the robot now logs per-channel current, use that and cross-check.

## 4. Decompose the behavior

For each motor, and combined:
- **Hold:** at setpoint and stable. This is what it costs to sit there.
- **Recovery:** dipped below setpoint and re-accelerating, e.g. after a ball.
- **Spin-up:** starting from far below setpoint or cold. Count spin-ups per match, and the share of windows that start cold.
- **Idle:** what happens between uses. Coast to zero? Hold?

For each state give: time share; mean, p95 and max current; applied voltage or duty; tracking error; time to setpoint.

Also measure:
- **Saturation:** fraction of time at ≥97% duty or at the voltage ceiling. A saturated loop has no authority.
- **Chatter:** how often the gate or setpoint toggles, and the mechanism reversals per match. If the setpoint reverses more often than the mechanism should, the input is the problem.
- **Protection gaps:** samples above each limit, and anything on a motor with no limit.
- **Energy per match** (Wh), and charge (Ah) for event-level work.

## 5. Tie it to brownouts

- Use the team's metrics: **matches with a brownout**, and **match time remaining when the first brownout starts**. Not summed seconds below threshold.
- Look at the battery drop in the ~0.3 s after each start event, and at what else starts at the same instant.
- **Decide which kind of brownout this is:**
  - stacked transients: spikes coinciding
  - late-match depletion: onsets clustered in the last quarter
- Spike-shaping helps the first kind. Only charge savings move the first onset of the second kind (lessons #17–#18).
- Put the subsystem in proportion. In 2026 the drivetrain was 47–57% of match energy, so a mechanism fix rarely beats a drive fix.

## 6. Falsify before you rank

- Re-derive the key finding from first principles (back-EMF, kV·v + kS, energy = ∫P dt) and check the units.
- Try to break it: does it hold on the healthy-battery match? On a different event? With the other build?
- Compare against `lessons/2026-baselines.md` where the mechanism is comparable.

## 7. Write it up

Use this structure (the 2026 reviews followed it):

1. **What this is:** the subsystem, motors, why it's being looked at.
2. **Method:** the logs used; signals with units; the resample and slices; which figures are estimated.
3. **Headline:** two or three sentences: the dominant behavior and the single best change, with its key number.
4. **Measured characteristics:** a table per match. Rows are metrics, and each row says what it means.
5. **How it's commanded:** the code facts from step 1.
6. **Core finding:** the physics, step by step.
7. **Findings, ranked by value:** each with the evidence, the change, its effort, and how to validate it on the practice field.
8. **What could go wrong:** for each proposed change, the failure symptoms it could cause and how the team would notice. Examples: a ready idle that changes shot quality; a supply cap that drivers feel; a debounce that feeds while the turret is still settling (2026).
9. **What's already good:** keep it.
10. **Plan / status:** each item as proposed, decided or applied.

Save it as `analyses/YYYY-MM-DD-<subsystem>-power.md` with frontmatter (`status: proposed`). Add any decisions to `knowledge/decisions.md`, and update `INDEX.md`.

**Team-facing version:**
- current in **amps**, not watts
- brownout match counts, with time left at the first brownout
- no blaming battery quality
- plain language, with one chart per point

Recommend that a fresh session check the numbers before it goes to the team.

## Checks before you finish

- [ ] Every number names its match, log and signal.
- [ ] Estimated figures are labeled.
- [ ] Units and shaft reference are stated for every velocity and gain.
- [ ] Follower and secondary motors were checked, not just the main.
- [ ] Each finding was tested on at least one other match.
- [ ] The "what could go wrong" section exists for every proposed change.
