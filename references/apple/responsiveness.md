# Responsiveness

Goal: no hitch while animating or scrolling, and no hang on the main thread.

## Measure first

- Interactions are not scripted by `profile_apple.py`. Record the key flow by hand while the user (or a UI test) performs it: `xcrun xctrace record --template 'Animation Hitches' --attach <pid> --time-limit 20s --output .perf/<flow>.trace`; `'SwiftUI'` for view body updates; `'Time Profiler'` for hangs. Findings only.
- SwiftUI body churn, as a temporary code change in step 7 only: `let _ = Self._printChanges()` in the suspect view's `body`, read the console, remove it after.
- For a number `compare` can verify: a UI test with `XCTOSSignpostMetric.scrollDecelerationMetric` or a custom `OSSignposter` interval (needs a test target: step 7, with the user's OK).

## Common causes, by frequency

1. **Work on the main thread during a gesture or animation**: decoding, file I/O, synchronous network or XPC calls.
2. **SwiftUI views that update too often**: a whole `ObservableObject` observed where one property is used, `@Published` values that change every tick, unstable identities in `ForEach`.
3. **Expensive `body`**: formatting, sorting or filtering inside `body` instead of in the model.
4. **Offscreen rendering**: shadows without a path, masks, blur, `drawingGroup` misuse.
5. **Large images decoded on the main thread at display time.**

## Fixes

- Move work off the main actor; hop back only to assign results.
- Observation (`@Observable`) or smaller observable objects so only the views that read a value update; stable `id`s.
- Precompute in the model; cache formatters.
- `shadowPath`, fewer masks; pre-decode or downsample images (`CGImageSourceCreateThumbnailAtIndex`).

## Pitfalls

- Debug builds hitch more than Release. Trace a Release build only.
- A hand-recorded trace is one sample: confirm a finding with two recordings before ranking it high.
