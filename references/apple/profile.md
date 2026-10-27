# Apple profile

Native apps for macOS and iOS (UIKit, SwiftUI, AppKit), built with Xcode. iOS apps are measured in the iOS Simulator; macOS apps on this Mac. Measured with `ps`, `top` and `footprint` through `scripts/profile_apple.py`: no sudo, no Instruments needed.

## Detect

`*.xcodeproj`, `*.xcworkspace`, or a `Package.swift` with an app target. Requires a Mac with Xcode (not only the Command Line Tools): `xcodebuild -version`. An iOS app also needs a simulator runtime: `xcrun simctl list runtimes`.

## Recon

- Targets, schemes and configurations: `xcodebuild -list -project <proj>` (or `-workspace`).
- Platform and kind, from the app target's build settings and Info.plist:
  - **iOS app** → measured in the Simulator. Main metrics: CPU time until settled (launch cost), memory, size.
  - **macOS app with windows** → launch cost, memory, responsiveness.
  - **macOS agent app** (`LSUIElement = YES`: menu bar, notch, login item) → **idle CPU and idle context switches first**: it runs all day, so its resident cost matters more than its launch.
- The project's own build recipe: scripts that build, re-sign or install (for example a `scripts/install-*.sh`). Reuse its build and signing steps; never its install step.
- Release compiler flags, read from a Release build log (not from the project file alone: schemes Xcode generates can add settings): `grep -c -- "-profile-generate\|-fprofile-instr-generate" <log>` (code coverage instrumentation), `-sanitize=`, `-Onone`, `ENABLE_TESTABILITY`. Any of these in Release is a finding (area `size-assets`).
- Timers, polling and observers: `Timer.scheduledTimer`, `Timer.publish`, `DispatchSourceTimer`, `Task.sleep` loops, `CADisplayLink`, `NotificationCenter` and KVO observers. Note each interval: the idle window must be longer than the longest poll.
- Existing instrumentation and field data: `os_signpost` / `OSSignposter`, MetricKit (`MXMetricManager`), performance tests (`measure(metrics:)`) in test targets.

## Release build

- `xcodebuild -project <proj> -scheme <scheme> -configuration Release -destination <dest> -derivedDataPath .perf/DerivedData build > .perf/build-<NN>.log 2>&1`. Destination: `'platform=macOS'`, or `'platform=iOS Simulator,id=<UDID>'`. Never a Debug build.
- Keep the derived data in `.perf/` so the project's own build folder and the user's installed copy are untouched.
- Signing: if the project has its own re-sign step (ad hoc, extra entitlements), run it on a copy in `.perf/` (`ditto <built .app> .perf/<NN>.app`). Never change the signing team or entitlements as a performance fix.
- Each new signature can make macOS ask again for Keychain items, Calendar or other permissions the app uses. Tell the user before the first launch: they have to click Allow each time.
- One build per measured state, built before the measurement starts: never build while measuring.

## Baseline

- **Quit the user's running copy first, with their OK.** `profile_apple.py` refuses to start while a process with the same executable name runs; two copies of an agent app also fight over the same menu bar or notch. Relaunch the user's copy at the end (`open <installed .app>`), and say so in the Report.
- Targets are modes, not pages: `size` always; `launch` always; `idle` for any app that stays open (always for an agent app).
  - `python3 scripts/measure.py run --profile apple <.app> --mode size --out .perf/00-baseline-size.json`
  - `python3 scripts/measure.py run --profile apple <.app> --mode launch --runs 3 --settle 10 --out .perf/00-baseline-launch.json`
  - `python3 scripts/measure.py run --profile apple <.app> --mode idle --runs 3 --settle 15 --window 60 --out .perf/00-baseline-idle.json`
  - iOS: add `--device <simulator UDID>`; boot it first (`xcrun simctl boot <UDID>`). The script installs and launches the app.
- Noise check (A/A) on `idle` (or `launch` for an app that does not stay open). An app that polls the network can move between runs: raise `--window` past its poll interval before raising `--runs`.
- Interactions (opening a panel, scrolling, a hover animation) are not scripted here. Record them by hand for findings only: `xcrun xctrace record --template 'Animation Hitches'` (or `'SwiftUI'`, `'Time Profiler'`) `--attach <pid> --time-limit 20s --output .perf/<flow>.trace` while the user performs the flow; open the trace in Instruments. Their numbers never decide keep or revert.

## Areas

| Area | Reference | Main metrics |
|---|---|---|
| launch | `references/apple/launch.md` | CPU time until settled, memory footprint settled |
| idle | `references/apple/idle.md` | Idle CPU, idle context switches |
| responsiveness | `references/apple/responsiveness.md` | Hitches and hangs (traces, findings only), CPU time |
| memory | `references/apple/memory.md` | Memory footprint, settled and after idle |
| network-data | `references/apple/network-data.md` | Idle CPU and context switches, launch CPU |
| size-assets | `references/apple/size-assets.md` | App bundle size, main binary size, CPU time |

## Plan columns

- Measurement line: `ps/top/footprint, <macOS | iOS Simulator <runtime> on <device>>, <N> runs (median run), settle <s> s, idle window <s> s`
- Baseline table:

```markdown
| Mode | CPU until settled | Footprint settled | Idle CPU | Idle ctx switches | Footprint after idle | App size | Binary size |
|---|---|---|---|---|---|---|---|
```

## Profile rules

- Simulator numbers run on the Mac's CPU and memory, without thermal limits: valid for before/after, not as device numbers. A physical device only with the user's OK.
- Never install into `/Applications`, replace the user's installed app, or relaunch it from the build folder. Never upload to TestFlight or the App Store, notarize, or create a release.
- Never quit a running app without the user's OK; relaunch it when done.
- Field data (Xcode Organizer, MetricKit payloads) only if the project already collects it, and read only.
- A change that only a hand-recorded trace can show (a hitch, a hang) is kept only with the user's OK, like a change `compare` cannot verify.
