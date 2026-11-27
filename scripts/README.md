# scripts

Reusable analysis code. Each script says where it came from.

| Script | What it does | Origin |
|---|---|---|
| `wpilog_reader.py` | Dependency-free reader for WPILOG / AdvantageKit logs, including struct decoding. Usage guide: `archive/2026/wpilog-reader-guide.md`. | 2026 Project (Aug 2026), struct decoding adapted from tervay/log_reader |

## Before relying on these in 2027

- Pitwall (`DStewart-88/frc-pitwall`) has its own reader, `pitwall/wpilog.py`, and another copy lives in `FRC Logs/nerd-review/wpilog.py`. Which one is newest isn't recorded. Pick one and keep a single copy.
- Confirm the `.wpilog` format and AdvantageKit key names still hold under WPILib 2027 and its new telemetry APIs (`knowledge/control-system.md`).
