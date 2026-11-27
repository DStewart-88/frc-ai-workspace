# Health monitor: Oct 20 practice and Oct 21 STEAM day review

Follow-up to `claude/health-monitor-practice-1019-review.md`.

## Logs

| Folder | Logs | Enables (≥5 s) | Notes |
|---|---|---|---|
| `2026 Logs/20261020Practice` | 10 | 11 | Practice; two DS practice matches |
| `2026 Logs/steamday` | 15 | 24 | Demo day for students; teleop only |

- All 25 logs ran BaseComp `fc868cc` with uncommitted changes, redeployed several times on both days.
- No FMS was attached.
- Extracts and scripts are in `FRC Logs/health-steamday-1021/`. `rate.py` also reads the Oct 19 extracts.

## Headline: the roboRIO CAN chain fault is gone

- **No device dropped off either bus on either day**: zero presence faults in 25 logs. On Oct 19 there were 22 whole-bus dropouts, plus 13 smaller ones.
- **The intake was exercised.**
  - Oct 20–21: 51 crossings of the pivot's full travel, with no dropouts.
  - Oct 19: 61 crossings, with 22 dropouts (13 within 1.5 s of a stroke).
  - At Oct 19's rate, zero dropouts by chance is roughly 1 in 100,000.
- **No run ended ERROR** on either day. Every end-of-run display was WARNING or nothing.

Whether this was a deliberate repair or a connector that happened to settle needs confirming with the team.

## `CAN/BusErrors`: what's left after the fix

| | Oct 19 (wiring fault) | Oct 20–21 |
|---|---|---|
| Rate | ~13 per enabled minute | ~0.45 per enabled minute |
| Episodes per enable | median 30, max 98 | median 0, max 5; zero in 25 of 35 enables |
| Worst 60 s window in each log | 17–30 | 0–4 |
| `CAN/BusErrorsSevere` | 1 | 0 (counts never reached 96) |

**The remaining 22 episodes happen while driving.**
- 19 of the 22 occurred while the four drive motors were drawing more than 120 A combined. That is 42% of enabled time, so chance would predict about 9.
- Rate while driving hard: ~0.9 per minute. With the drive near idle: ~0.05 per minute.
- The rate is flat across 120–200 A (1.15, 0.87 and 0.88 per minute by band). It tracks the robot moving, not the size of the current spike.
- Not related to the roboRIO-bus mechanisms: they drew over 20 A for 78% of enabled time, with or without errors.
- Not related to intake strokes (pivot travel ≈0 in 21 of 22), the shooter, or brownouts (none within 1 s).
- Each episode lasts 1–2 loops (20–90 ms).

**Interpretation.** A small number of CAN error bursts while the drivetrain works hard is common in FRC. Likely causes are electrical noise or ground shift from the drive wiring, or vibration at a connector. The logs can't tell these apart. It is not causing dropouts and it never approached the severe threshold.

**Why it feels like "every enable".**
- It is the most frequent entry in end-of-run records: 10 of 23 records, ahead of brownouts (8) and back-camera faults (7).
- It was the only fault in 3 of them.
- Any single 20 ms burst latches it.

**Recommendation (not yet decided).** Make `CAN/BusErrors` rate-based: warn only when there are about 10 or more episodes within a rolling 60 s.
- On this data that flags every Oct 19 log (17–30 per 60 s) and nothing on Oct 20–21 (at most 4).
- Combine it with the once-per-loop `getCANStatus()` refactor and per-loop logging from the Oct 19 review, so the threshold can be checked against more days.

## Other results

- **The back Limelight (Camera0, `limelight-back`) was out across five sessions in a row.**
  - It started at Oct 20 22:06 UTC (64 s into that log) and continued through the first three STEAM-day logs (13:53–15:00 UTC).
  - Each time it ran through enables, so it latched a warning and showed in every boot replay.
  - It was back by the 15:23 UTC log.
  - In the 15:40 UTC log the cameras went out one at a time for 116–231 s while enabled, never all three at once.
  - Worth asking whether cameras were unplugged on purpose during the demo.
- **Saving the record through power-off:** 23 of 24 reboots replayed exactly what the previous log ended with. The exception shows **an unlogged session**. The first STEAM-day boot replayed "Brownout ×32, BatterySag ×17, CAN/BusErrors, Vision/Camera0", but the last Oct 20 log ended with only "Vision/Camera0". The robot was enabled at least once between them, and that log isn't in the folder. Check the roboRIO or the USB stick.
- **`Power/LowStartingBattery` fired for the first time.**
  - Oct 20: 12.28 V snapshot before a second enable, 15 s after a 140 s run.
  - Oct 21: 12.25 V and then 12.06 V on the 3rd and 4th enables of one battery.
  - Both are batteries being run down, as intended. Note that with no FMS the snapshot is taken after only a short rest, so it reads lower than a fully rested battery would.
- Fewer brownouts on the STEAM day (2–5 per run, versus up to 133 on Oct 19), consistent with gentler demo driving.
