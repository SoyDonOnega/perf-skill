# Launch

Goal: the app does only what its first screen needs before it settles.

## Measure first

- `--mode launch`: `launch_cpu_ms` (CPU time from launch until `--settle` seconds later) and `settled_footprint_mb`. CPU time, not wall time: it does not depend on how busy the rest of the machine is.
- Where the time goes: `xcrun xctrace record --template 'Time Profiler' --launch -- <.app> --time-limit 10s --output .perf/launch.trace`, then open it in Instruments (findings only).
- For a wall-clock launch time that `compare` can verify, a UI test with `measure(metrics: [XCTApplicationLaunchMetric()])` run through `xcodebuild test -resultBundlePath .perf/<NN>.xcresult`, read with `xcrun xcresulttool`. It needs a test target: a code change, so only in step 7, with the user's OK.

## Common causes, by frequency

1. **Eager singletons and managers**: every service created in `init` of the app or the root view, even for screens the user has not opened.
2. **Synchronous work on the main thread at start**: file and database reads, JSON decoding, Keychain reads, image decoding.
3. **Network calls started at launch** whose results the first screen does not show.
4. **Many dynamic frameworks**: each one adds dyld time. Static linking or merging helps.
5. **Heavy `+load`, static initializers or large `@AppStorage`/`UserDefaults` reads.**

## Fixes

- Create services lazily, on first use; start background work after the first frame (a Swift task with `.utility` priority, `DispatchQueue.global(qos: .utility)`).
- Move file, database and decoding work off the main thread.
- Defer network refreshes until the screen that shows them appears.
- Mergeable libraries or static linking for frameworks only the app uses.

## Pitfalls

- A login item launches once a day: on an agent app, a launch win matters less than an idle win. Rank by that.
- Moving work later can raise idle CPU if it then repeats. Check both modes.
