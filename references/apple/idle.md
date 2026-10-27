# Idle

Goal: an app that is open but not used costs close to nothing.

## Measure first

- `--mode idle`: `idle_cpu_pct` (CPU time over the window) and `idle_csw_s` (context switches per second: how often the process wakes up). Each wakeup keeps the CPU from deep idle and costs battery even when the CPU % rounds to zero.
- The window must cover the longest poll interval found in recon; otherwise a poll lands in some runs and not others, and the A/A check fails.
- What wakes it: `xcrun xctrace record --template 'Time Profiler' --attach <pid> --time-limit 60s` with the app idle, or `'System Trace'` for wakeups and thread states (findings only).

## Common causes, by frequency

1. **Timers that run while nothing is visible**: `Timer.publish(...).autoconnect()` in views that stay alive, `Timer.scheduledTimer` never invalidated, short `Task.sleep` loops.
2. **Polling** where an event exists (distributed notifications, `NSWorkspace` notifications, KVO, `DispatchSource` on files, push).
3. **Animations running off-screen**: SwiftUI `repeatForever`, Lottie, `CADisplayLink` in a hidden view or window.
4. **Visualizers and meters** (audio levels, progress) updating while the panel is closed.
5. **Observers that fire on every system change** (all `NSWorkspace` or media notifications) and do work each time.

## Fixes

- Stop timers and animations when the view or panel is hidden (`onDisappear`, `scenePhase`, window occlusion `NSWindow.occlusionState`), start them when it shows.
- Replace polling with notifications; when polling is unavoidable, use a longer interval and timer `tolerance` so the system can coalesce wakeups.
- `.background`/`.utility` QoS for periodic work.

## Pitfalls

- An agent app's panel is "hidden" most of the day: its idle cost is its real cost.
- Lower CPU but more context switches can be worse for battery. Report both.
