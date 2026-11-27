# Steer Draw in Real Matches — Newton Teleop (Q23/Q47/Q55/Q87)

The offseason drive tests could only show smooth auto-path steering. This applies the *validated*
supply-current estimate (`|stator| × |applied volts| / Vbat`, confirmed accurate to 0.6% against
the newly-logged supply current) to four real Newton teleop windows, to finally see the azimuths
under real driving — rotate-about-turret, shoot-on-move, driver corrections. No code changed around
the steer motors between these matches and now, so this still describes the current robot.

Matches: Q23, Q47, Q55, Q87 (four of the Newton brownout matches). Teleop only — enabled and not
autonomous, ~140–148s each.

## Headline

Teleop confirms and sharpens the auto finding: **steer is small on average but produces big
synchronized spikes, and those spikes land right on the brownout dips.** Average teleop steer draw
is ~10A total (all four motors, ~2.5A/motor); it briefly spikes to **186–208A**, and during the
sub-7V near-brownout moments the steer spikes reach **120–204A**. A 20A/motor supply cap clips only
3.8% of teleop samples yet removes those spikes — worth up to ~1–2V at the worst steer-driven
instant. It remains cheap insurance, not the primary brownout fix.

## What the azimuths draw in real teleop

| Match | Steer total mean | Steer per-motor mean | Steer total median | Steer p99 | Steer max | Steer % of drivetrain energy | Vbat min |
|---|---|---|---|---|---|---|---|
| Q23 | 10.0 A | 2.5 A | 2.2 A | 114 A | 186 A | 12.7% | 6.10 V |
| Q47 | 9.4 A | 2.3 A | 2.4 A | 108 A | 208 A | 10.1% | 5.99 V |
| Q55 | 11.4 A | 2.8 A | 3.0 A | 109 A | 190 A | 12.0% | 6.30 V |
| Q87 | 11.4 A | 2.9 A | 2.7 A | 120 A | 204 A | 13.0% | 6.03 V |

The shape matches the auto test but scaled up: a near-zero median (the azimuths are idle most of the
time), a modest mean, and a long spiky tail. Two differences from the auto path: teleop steer draws
about **2× more on average** (mean ~10A total vs ~3A in auto) and **spikes higher and more often**
(max ~200A vs ~170A; total steer exceeds 40A about 7–9% of teleop). That's the real driving — the
optimizer flipping modules on direction changes, plus rotate-about-turret keeping azimuths busy
while aiming. Still, steer is only **10–13% of drivetrain amp-seconds**; the drive motors are the
other ~87%.

### The spikes are synchronized, and they coincide with brownouts

Of the moments total steer exceeds 60A, **49–60% have three or more modules firing at once** — same
signature as the auto test: the four azimuths snap together, stacking into one transient. And these
spikes are not randomly timed. During the teleop samples where the bus is already below 7V, mean
steer draw *rises* (to 15–18A in Q23/Q55/Q87), and the worst steer spikes inside those <7V windows
reach **121A (Q23), 142A (Q55), and 204A (Q87)**. Azimuth work peaks at exactly the shoot-on-move
moments that also peak drive and shooter load — which is why it matters out of proportion to its
average (Panels B and C).

## What a 20A/motor steer supply cap actually buys — measured, honestly

**Cost — negligible.** Across all four teleop windows, a 20A/motor cap clips just **3.8%** of
per-motor steer samples and removes **0.46A** off the per-motor mean. The azimuths almost never
*need* more than 20A of battery power (median 0.36A), so normal driving is untouched. 15A would clip
5.0%, 25A only 2.8% — the whole 15–25A range is cheap.

**Benefit — real but uneven.** The cap's value is entirely at the spike instants:

| Match | <7V duration | worst steer spike during <7V | cap removes (worst instant) | volts recovered @16mΩ |
|---|---|---|---|---|
| Q23 | 3.0 s | 121 A | 41 A | ~0.7 V |
| Q47 | 6.8 s | 93 A | 35 A | ~0.6 V |
| Q55 | 2.4 s | 142 A | 62 A | ~1.0 V |
| Q87 | 5.4 s | 204 A | 124 A | **~2.0 V** |

At the worst steer-driven instant the cap is worth up to ~2V — potentially the difference between a
brownout and a survivable dip. But averaged over all the <7V time it only removes ~1–3A, because
most near-brownout moments are drive- and shooter-dominated, not steer. At the single worst
*combined* drive+steer instant of each match, steer's share ranged from 40A (Q47 — drive-dominated,
cap barely helps) to 101A (Q87 — cap takes 296A down to 260A). So the cap reliably kills the
steer-driven spikes, and sometimes that's decisive, but it can't fix a dip that drive alone caused.

## A correction worth flagging

Applying this method to the matches reproduces the July brownout analysis's per-match table
*exactly* — e.g. Q23 drive 69.16A (table: 69.1) and steer 10.02A (table: 10.0). That confirms the
table was right and the method is stable. But the July write-up's **prose** described steer as
"~10–11A each (≈43A total) continuously" — that was a ~4× overstatement: the "~10A" in its own table
is the **four-motor total**, not per-motor, and the draw is intermittent, not continuous (median
0.36A/motor). My earlier steer analysis repeated that "~10A/motor" figure in a caveat; the correct
number is **~2.5A/motor, ~10A total** (the earlier doc is now corrected). The recommendation doesn't
change — if anything the azimuths are even less of an *average* load than the July prose implied —
but the record should be accurate.

One consequence: the old "calm the azimuths / don't re-point at zero speed" idea will save very
little on the *brownout* side, because teleop steer is low-supply on average (it's the brief spikes,
not steady hunting, that draw current). That behavioral fix is worth doing for azimuth motor heat
and tread scrub — a *stator*-side and mechanical concern — but don't expect it to move brownouts.
The supply cap is the brownout lever.

## Bottom line

Real matches confirm the plan from the auto analysis: **add a ~20A/motor steer supply current
limit** (there's still none — only the 60A stator limit). It costs ~3.8% of steer samples, i.e.
effectively nothing in driver feel, and it removes the 120–204A synchronized azimuth spikes that
land squarely on the shoot-on-move brownout dips — up to ~2V recovered at the worst instant. Treat
it as the cheapest item on the brownout list: do it, but pair it with the bigger levers (drive
supply limit, idle-the-flywheel, and sequencing the shooting stack), which own the ~87% of
drivetrain load and the drive/shooter peaks that dominate these dips.

*Method: `|TurnCurrentAmps| × |TurnAppliedVolts| / BatteryVoltage` per module, zero-order-hold
resampled to 50 Hz over the teleop window (enabled & not autonomous). Estimate validated to 0.6%
against logged supply current in the offseason tests. Cross-checks reproduce the July brownout
table's drive and steer figures exactly. Matches: Newton Q23, Q47, Q55, Q87.*
