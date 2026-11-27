# Feeder power baseline (2026 season, pre-modification)

**Purpose:** fixed reference numbers for the *old* feeder (TalonFX `FEEDER_MAIN`, CAN 4) so the modified
post-season feeder can be compared against it. Companion to `feeder-power-analysis.md` (behavior/tuning).

**Method:** `FRC Logs/feeder-power-baseline/feeder_power.py` over every FMS-attached match log 130–180 s
enabled (78 matches across 4 events). 50 Hz sample-and-hold grid, enabled time only.
Supply power is **estimated** as `P = Feeder/Voltage × Feeder/Current` (motor voltage × torque current);
season logs have no `Feeder/SupplyCurrent`. Est. supply current = P / V_batt.
Check of the estimator on the Aug 22 drive-test logs (turret + retractomatic, where supply current *is*
logged): the estimate reads **~0–15% low** on energy (typically ~7%). Treat baseline numbers as slightly low.

## Headline baseline — final competition config (NECMP + CMP, 40 matches; 40 A stator limit, 105 rps)

| Metric | Median | p10–p90 | Max |
|---|---|---|---|
| Energy per match | **2.6 Wh** | 2.2–3.0 | 3.3 |
| Mean power, whole match (≈160 s enabled) | **58 W** | 49–67 | 74 |
| Time motor running per match | 66 s | 53–76 | 86 |
| Mean power **while running** | **140 W** | 132–151 | 156 |
| Median power while running | 129 W | 125–141 | 149 |
| p95 power while running | 261 W | 246–279 | 291 |
| Peak power, 1 s average | 200 W | 191–215 | 245 |
| Peak power, 100 ms average | **320 W** | 293–348 | 374 |
| Peak power, single 20 ms sample | 375 W | 356–430 | 480 |
| Est. supply current while running (mean) | 13.9 A | 13.2–14.7 | 15.3 |
| Est. supply current peak | 37 A | 33–40 | 44 |
| Battery voltage while running (median) | 10.3 V | 9.7–10.7 | — |
| Feeder speed while running (median) | 97 rps | 88–101 | — |

Regen is negligible (~0.02 Wh/match). Representative match plotted: Newton Q99 (2.59 Wh, 138 W running mean,
311 W 100 ms peak) — `feeder_power_newton_q99.png`.

## By event

| Event | n | Wh/match | Mean W while running | 100 ms peak W | Notes |
|---|---|---|---|---|---|
| North Shore (Mar 14–15) | 16 | 2.0 | 176 | 444 | **before the 40 A stator limit** (added Mar 24); stator peaks 70–106 A |
| MA Boston (Mar 27–29) | 22 | 2.9 | 148 | 337 | 40 A limit in place |
| NECMP / Newsom (Apr 16–18) | 23 | 2.5 | 140 | 311 | |
| CMP / Newton (Apr 29–May 1) | 17 | 2.7 | 141 | 327 | |

## Comparing against the new feeder

- RollerDev (Oct 1, "updates from testing") raises the feeder **stator limit 40 → 60 A** and HotTub speeds 90 → 100.
  The old feeder's peaks were bounded by the 40 A limit; North Shore (no limit) shows what unbounded spin-up looked like.
- Compare **mean power while running** and **100 ms peak** first — they describe the mechanism. Wh/match and
  whole-match mean mostly track how much the robot shot.
- New logs carry `Feeder/SupplyCurrent`. For like-for-like, compute the new feeder **both** ways
  (`V_batt × SupplyCurrent` and the `Voltage × Current` estimator); compare estimator to estimator.
- For context, HotTub (old) drew ~5.2 Wh/match, ~117 W whole-match mean at NECMP+CMP — about 2× the feeder.
