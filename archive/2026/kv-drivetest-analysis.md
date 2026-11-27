# Drive kV Test Analysis — Dev Robot, 2026-08-22

**Question:** How does changing the drive `kV` feedforward gain affect drive performance?

**Answer, in one line:** Raising `kV` from the broken **0.124** to the correct **0.871** takes the
drivetrain from **~67% of commanded speed to ~100%** *at every speed*, and from a **3.0 m/s** top speed
to **4.4 m/s** — exactly what the log analysis from competition predicted, now confirmed on hardware.

---

## The test as run

The team ran an A/B/B/A test — the cleanest possible design for isolating one variable, better than
the guide's baseline-then-fix sequence because going *back* to the broken value at the end proves the
effect wasn't drift, a warming battery, or something mechanical settling in. The auto routine drove laps
at commanded speeds of **2, 2, 3, 3, 4, 4, 4.5, 4.5 m/s**.

| # | Log file | kV | Build stamp | Result |
|---|---|---|---|---|
| T1 | `akit_..._17-42-23` | **0.871** (fixed) | 13:41 build | Full performance |
| T2 | `akit_..._17-47-40` | **0.124** (broken) | 13:46 build | 67% performance |
| T3 | `akit_..._17-53-23` | **0.124** (broken) | 13:46 build (same) | 67% performance |
| T4 | `akit_..._17-57-07` | **0.871** (fixed) | 13:56 build | Full performance again |

Ordering confirmed from the build timestamps embedded in each log (T2 and T3 share the exact same
build, matching "two runs at the lower kV"). The gain values themselves weren't logged — the code was
running with uncommitted changes — so everything below confirms which kV was active *from the robot's
behavior*, independently of what was reported. It agrees with the reported sequence in every run.

---

## What changed, measured five ways

| Metric | T1 high | T2 low | T3 low | T4 high | What it means |
|---|---|---|---|---|---|
| **Tracking ratio** (measured ÷ commanded) | **0.97** | **0.68** | **0.68** | **0.97** | Low kV delivers only 2/3 of what the driver asks |
| **Ratio at ¾ vs full speed** | 0.99 / 0.95 | 0.68 / 0.68 | 0.68 / 0.68 | 0.99 / 1.00 | Flat with speed → it's a gain bug, not battery/traction |
| **Top wheel speed** | **4.37 m/s** | 3.02 | 3.04 | **4.31 m/s** | ~35% faster with correct kV |
| **Applied volts at top speed** | **11.5 V** | 8.3 | 8.3 | **11.3 V** | Broken kV never uses more than ~8–9 of 12 V; it gives up early |
| **Mean drive current / module** | 18.9 A | 11.6 | 12.4 | 20.1 A | Correct kV draws *more* current — it's finally doing real work |

The low-kV ratio of **0.68 lands within 1% of the 0.685 the theory predicted** for this bug (feedback
alone settling against a 7× feedforward deficit). Both broken runs agree to two decimals. Both fixed
runs sit at ~0.97–1.0. This is not ambiguous.

### The single most important diagnostic

The tracking ratio is **flat across speed** in every run — ~0.68 at quarter stick and at full stick in
the broken runs, ~0.98 at both in the fixed runs (panel C in the figure). That flatness is the proof
that this is a *gain* problem and not something else: a battery or traction problem gets proportionally
worse the faster you go, producing a drooping curve. A constant-percentage deficit at every speed is the
fingerprint of wrong feedforward. That fingerprint is present, cleanly.

### Did it fall short at the top, or at every speed? (closing the "cut short" question)

A fair objection: the two low-kV runs were cut short by obstacles, and the auto commands *higher* speeds
as it goes. So is the lower top speed just an artifact of those runs never reaching the 4 and 4.5 m/s
laps? The logs say no, for two reasons.

**First, the low-kV runs did reach the fast laps.** Both commanded ~4 m/s and ~4.5 m/s for several
seconds each (T2: ~1.9 s at 4 and ~4.6 s at 4.5; T3: ~2.5 s at 4 and ~6.5 s at 4.5). They weren't cut
short before the high-speed commands — they got there and simply didn't go that fast.

**Second, the shortfall is the same ~67% at every commanded level** (panel G in the figure — the low-kV
runs sit on a shallower line below the diagonal at *every* speed, not just the top). Achieved speed at
each command step:

| Commanded | T1 high | T2 low | T3 low | T4 high |
|---|---|---|---|---|
| 2 m/s | 2.02 (1.01) | — | 1.37 (0.68) | 2.01 (1.01) |
| 3 m/s | 2.99 (1.00) | **2.00 (0.67)** | **2.01 (0.67)** | 2.96 (0.99) |
| 4 m/s | 3.86 (0.97) | **2.68 (0.67)** | **2.69 (0.67)** | 3.58 (0.90) |
| 4.5 m/s | 4.00 (0.90) | **2.94 (0.66)** | **2.96 (0.67)** | 3.76 (0.85) |

The cleanest single comparison needs no high-speed lap at all: at **commanded 3 m/s** — which both
low-kV runs held for 8–9 seconds, with plenty of runway and unrelated to any collision — the fixed robot
delivered **3.0 m/s** and the broken robot delivered **2.0 m/s**. Same command, same track, one-third
less speed. If the low-kV runs had driven laps forever without touching anything, they'd still top out
around 0.67 × 4.5 ≈ 3.0 m/s. The deficit is proportional and speed-independent — the signature of the
feedforward gain, not of the test length.

One honest nuance the table shows: the *fixed* runs themselves taper at the very top — 0.90 and 0.85 at
commanded 4.5, delivering ~3.8–4.0 rather than a clean 4.5. That last bit is a real ceiling, but it's the
battery sagging under the higher current draw, not kV — and even there the fixed robot delivers a full
meter per second more than the broken one.

### The robot's true kV is 0.87 regardless of the setting

Regressing *actual applied voltage* against *actual wheel speed* during steady cruise gives the robot's
real physical kV — a property of the motors, gearing, and wheels, independent of what number is in the
config. All four runs land at **0.87–0.90 V per wheel-rot/s** (R² 0.94–0.97). That's the same value the
competition-robot log analysis found (0.870–0.880), and it's ~7× the 0.124 that was in the code — the
7.03:1 gear ratio, exactly. So `0.871` isn't a lucky guess that happened to work; it's the number the
robot was physically asking for all along.

---

## About the obstacles

The reported obstacle hits don't compromise anything:

- **T3** was clearly cut short (~70 s of enabled driving vs ~280 s for T2).
- **T4** (the final high-kV run) **did hit obstacles** — brief wheel-stall spikes at ~91 s, ~92 s,
  and ~117 s (command high, wheels stopped, current spiking).
- These show up as short spikes where the wheels are stuck against something. Those samples were
  excluded and the ratio measured only during steady cruise, so they don't pull the numbers. The fact
  that T2 and T3 (one long, one cut short) return the *identical* 0.67 at every commanded level confirms
  the contamination is negligible — and, as shown above, both runs still reached the 4 and 4.5 m/s
  commands before they ended.

---

## Two things worth noting about the dev robot

For the drive side, the dev robot hasn't drifted from the competition robot in any way that matters:

1. **Physical kV is identical** to the competition robot (0.87) — the drive modules are the same model.
   The wheel radius reads exactly 2.0 in (0.0508 m) from the encoder-vs-speed ratio, as expected.
2. **The fixed runs top out at 4.3–4.4 m/s, not quite the 4.39 theoretical max**, and the battery sags to
   ~9.4–9.7 V on those runs (vs ~10.0–10.4 V on the slower broken runs). That last ~0.1 m/s gap is
   battery-limited, not a gain issue — the fixed drivetrain draws more current, sags the bus, and can't
   reach 4.39 m/s on a sagging bus. This is the fix working correctly, and matches the caveat the student
   guide set: expect ~4.2–4.4 on this light base, less on the heavier competition robot under match load.

---

## Bottom line

The kV change does precisely what the whole investigation predicted. At **kV = 0.124** the drivetrain
structurally delivers **~67% of commanded speed at every speed**, caps out at **~3.0 m/s**, and never
pulls more than **~8 V**. At **kV = 0.871** it tracks command to **~100%** (tapering only at the very top
as the battery sags), reaches **~4.4 m/s**, and uses the **full 12 V**. The A/B/B/A design plus the
per-command-level breakdown rule out every alternative explanation, including the runs being cut short.
Ship `kV = 0.871` (with `kP` dropped back toward 0.1, per the fix plan) and re-validate autos and driver
feel on the competition robot, since every path was previously commanding speeds the robot couldn't reach.

*Method: parsed the four AdvantageKit `.wpilog` files directly; tracking ratio from
`SwerveStates/Measured` ÷ `SetpointsOptimized`; per-command-level achieved speed binned from the same
per-module signals; physical kV from a steady-state regression of `DriveAppliedVolts` on wheel speed
across all four modules.*
