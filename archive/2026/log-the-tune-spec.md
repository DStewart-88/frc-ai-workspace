# Spec: make each log self-describe its tune

Goal: never again have to reverse-engineer which kP/kS/control-mode produced a log. Every `.wpilog`
should carry the actual gains that were live when it was recorded.

## What already works (don't rebuild it)

`Robot.java` already records build identity before `Logger.start()`:

```java
Logger.recordMetadata("GitSHA",   BuildConstants.GIT_SHA);
Logger.recordMetadata("GitBranch",BuildConstants.GIT_BRANCH);
Logger.recordMetadata("GitDate",  BuildConstants.GIT_DATE);
Logger.recordMetadata("BuildDate",BuildConstants.BUILD_DATE);
Logger.recordMetadata("GitDirty", BuildConstants.DIRTY == 1 ? "Uncommitted changes" : "All changes committed");
```

`build.gradle` generates `BuildConstants` via the `gversion` task on every build. This lands in the
log under `/RealMetadata/*`. It already gives you **BuildDate**, which is unique per deploy — that
alone reconstructed the six-build deploy order for the Aug 28 session.

## Why it wasn't enough on Aug 28

1. **Dirty builds share a SHA.** All nine logs read `GitSHA = e85757e2…`, `GitDirty = Uncommitted
   changes`. The kP/kS edits were never committed, so the SHA can't tell two tunes apart.
2. **The gain values aren't logged at all.** Nothing in the log says `kP` was 15 vs 0.5, or that the
   drive loop was Voltage vs TorqueCurrentFOC. That's the real gap.

## Fix 1 — log the gains at boot (primary, ~15 min)

`Slot0Configs` fields (`kP,kI,kD,kS,kV,kA`) are public doubles. Add two summary methods to
`TunerConstants.java`:

```java
public static String driveGainsSummary() {
  return String.format("kP=%.4f kI=%.4f kD=%.4f kS=%.4f kV=%.4f kA=%.4f out=%s slip=%.0fA",
      driveGains.kP, driveGains.kI, driveGains.kD, driveGains.kS, driveGains.kV, driveGains.kA,
      kDriveClosedLoopOutput, kSlipCurrent.in(Amps));
}
public static String steerGainsSummary() {
  return String.format("kP=%.2f kI=%.2f kD=%.2f kS=%.3f kV=%.3f kA=%.3f out=%s",
      steerGains.kP, steerGains.kI, steerGains.kD, steerGains.kS, steerGains.kV, steerGains.kA,
      kSteerClosedLoopOutput);
}
```

Then in the `Robot` constructor, **before `Logger.start()`** (metadata must precede start):

```java
Logger.recordMetadata("DriveGains", TunerConstants.driveGainsSummary());
Logger.recordMetadata("SteerGains", TunerConstants.steerGainsSummary());
```

Every log now carries `/RealMetadata/DriveGains = kP=0.5000 … out=TorqueCurrentFOC …`. Done —
runs are unambiguously identified regardless of git state.

## Fix 2 — log the *applied* gains (ground truth, optional)

Fix 1 logs what the source says. If gains are ever changed live (Tuner X, a dashboard, a
`LoggedTunableNumber`), read them back from the motor so the log reflects reality. After module
configuration (e.g. end of the `Drive`/`Module` constructor), read slot 0 off module 0's drive
TalonFX:

```java
var applied = new Slot0Configs();
driveTalon.getConfigurator().refresh(applied);   // reads the config actually on the motor
Logger.recordOutput("Drive/AppliedDriveGains",
    String.format("kP=%.4f kD=%.4f kS=%.4f kV=%.4f", applied.kP, applied.kD, applied.kS, applied.kV));
```

Use `recordOutput` (not metadata) since it's read after `Logger.start()`. Log it once at boot, or
each loop if you tune live.

## Fix 3 — a human label per run (cheap, high value)

Let whoever's testing name the run from the dashboard. AdvantageKit's `LoggedNetworkString`
publishes an NT entry *and* logs it:

```java
private final LoggedNetworkString testLabel = new LoggedNetworkString("/Tuning/TestLabel", "");
```

Type "P=15" or "FOC converted" in the dashboard before a run; it's in the log. Pair this with a
brief written test plan and the reconstruction becomes trivial.

## Fix 4 — make dirty builds unique (process, no new code)

`build.gradle` already has an `eventDeploy` task that auto-commits all working changes when the
current branch name starts with `event`. Tonight was on branch `BaseComp`, so nothing committed.
**Deploy tuning sessions from an `event/tuning-…` branch** and every deploy becomes a real commit
with a unique SHA — the whole config diff is captured for free, no code change. (Alternative: log a
hash of `TunerConstants.java` content as metadata, but committing is cleaner and reversible.)

## Recommended minimum

Fix 1 + Fix 3. Two metadata lines + one dashboard string turns every future log into a
self-labeling record. Fix 4 is a free bonus if tuning happens on an `event/` branch.

## How the analysis reads it back

The log-reader already exposes these: `WPILog.series("/RealMetadata/DriveGains")`,
`/RealMetadata/BuildDate`, `/RealOutputs/Tuning/TestLabel`. With Fix 1 in place, runs can be
auto-grouped by exact tune instead of inferred from tracking fingerprints — turning the "best-effort
mapping" in `drivetests2-tuning-runs-0828.md` into an exact lookup.
