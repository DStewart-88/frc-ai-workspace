# Shooting while driving: Oct 29–30 practice vs River Rage

*Source: `2026 Logs/20261029_logs` (10 logs; 6 with driving, build `658a297d`) and `2026 Logs/20261030_PRAC` (27 logs; 7 with shooting, build `e05fd5ee`), compared with the 10 full River Rage matches (`b2e88a99`). Teleop only. Robot speed is the mean wheel speed of the four drive modules. Scripts are in `FRC Logs/shoot-drive-practice-1029-1030/`: `extract.py`, `overview.py`, `shoot_drive.py`, `steer_shooting.py`, `bo_practice.py`, `extra.py` and `steer_still_check.py`.*

## Code differences that matter (not just the driver)
| | River Rage `b2e88a99` | Oct 29 `658a297d` | Oct 30 `e05fd5ee` | BaseComp now `4c190e5` |
|---|---|---|---|---|
| Stick x/y while shooting at the hub | ×0.25 | ×0.25 | **×0.5** | ×0.5 |
| Rotation stick | ×0.625 always | ×0.625 always | **×1.0 always** | ×0.75 shooting / ×1.0 otherwise |
| On-target debounce | 0.2 s | 0 s | 0 s | 0 s |
| Drive supply limit | 45 A | 45 A | 45 A | 45 A |

## Findings
**1. More of the shooting happens on the move, but at lower speed.**

| | River Rage | Oct 29 | Oct 30 |
|---|---|---|---|
| Shooting time moving > 0.5 m/s | 37% | 38% | **59%** |
| Shooting time moving > 1.5 m/s | 21% | 12% | 18% |
| Speed while moving and shooting, median | 1.68 m/s | 1.19 m/s | 1.20 m/s |
| Shooting time rotating > 1 rad/s | 5% | 8% | 14% |

**2. Peak total draw while shooting is higher on Oct 30.** All figures are battery-independent current.

| | River Rage | Oct 29 | Oct 30 |
|---|---|---|---|
| Total while shooting, p50 / p99 / max | 108 / 355 / 549 A | 130 / 374 / 486 A | 160 / 405 / 656 A |
| Seconds above 400 A per minute of shooting | 0.1 | 0.2 | **0.7** |
| Seconds above 300 A per minute of *moving* shooting | 8.4 | 9.0 | 9.0 |

Per moment of moving-shooting, the load is about the same across all three. What changed is how much of the shooting is on the move, plus the steer spikes in finding 4.

**3. The drive is pinned at its supply ceiling during shooting moves, whatever the stick scaling.**
- Drive-sum p99 while shooting: 177 / 172 / 173 A, which is the 4 × 45 A ceiling.
- Stick scaling of ×0.25 vs ×0.5 made no difference to drive peaks, because acceleration, not speed, sets the current.
- Conclusion: stick scaling is not a current lever; the supply limit is.

**4. Steer is the new contributor.**
- Oct 30 steer sum while shooting: p99 188 A (River Rage 120 A), max 300 A.
- At the top 1% of shooting instants: steer 143 A, against 59 A at River Rage and 42 A on Oct 29.
- Spikes happen even with the robot nearly still: p99 208 A, and 4.8% of that time above 100 A.
- Joystick check, Oct 30 shooting with the robot nearly still and steer > 100 A (353 samples): within 200 ms, left-stick translation in 230, right-stick rotation in 96, X button in 0. So the spikes are all four modules swinging to a new direction when the driver starts a move from rest. They aren't the X-lock.
- The steer still has no team-set supply limit (Phoenix default 70 A each).

**5. Brownouts while shooting on the move are now the most common case.**

| | River Rage | Oct 29 | Oct 30 |
|---|---|---|---|
| Brownout episodes: shooting & moving / shooting & still / not shooting | 8 / 8 / 9 | 11 / 7 / 4 | **24** / 11 / 11 |
| In shooting-and-moving episodes: drive / steer / stack / total (median) | 169 / 7 / 141 / 336 A | 145 / 4 / 142 / 339 A | 133 / 18 / 149 / 346 A |

When shooting on the move, the drive and the shooting stack are roughly equal halves of the load. Brownout *rates* aren't comparable with River Rage, because practice runs each battery until it's dead.

**6. Effect of limits on shooting-time peaks.** Instantaneous clipping only, not a battery model.

| | River Rage | Oct 29 | Oct 30 |
|---|---|---|---|
| p99 / max total while shooting, as logged | 350 / 549 A | 374 / 486 A | 415 / 656 A |
| Drive 35 A | 330 / 543 A | 355 / 479 A | 399 / 653 A |
| Drive 35 A + steer 25 A | 326 / 534 A | 354 / 454 A | **359 / 552 A** |

On Oct 30, the steer limit takes off more than the drive limit: about −40 A at p99 and −100 A at the max, against about −16 A for the drive. At 11 mΩ that's about 0.4–1.1 V at the worst moments.

## What changes from the River Rage conclusions
- **Revised:** "in shooting brownouts the stack, not the drive, is most of the load". That was a median across two cases. When shooting on the move (River Rage too), the drive is about half. When shooting still, the stack dominates.
- **Revised:** the steer limit goes from optional to recommended alongside the 35 A drive limit, for this driver and build.
- **Unchanged:** the 35 A whole-match drive limit is still the main charge saver. The drive peak while shooting is bounded by the supply limit (180 A → 140 A at 35 A). A shooting-only drive cap still saves little charge. Stick scaling doesn't limit current.
- **New:** the rotation scaling went from ×0.625 to ×1.0 on Oct 30. That likely contributes to the extra rotation and steer activity, but this data can't separate it from the driver's style.
