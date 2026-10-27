# Network and data

Goal: fetch only what is shown, cache what does not change, and never block the main thread on I/O.

## Measure first

- Effects show as idle CPU and context switches (polling), launch CPU (eager fetches) and hitches (main-thread I/O).
- Requests: `xcrun xctrace record --template 'Network' --attach <pid>`; disk: `'File Activity'`; Core Data: `-com.apple.CoreData.SQLDebug 1` as a launch argument (findings only).
- Never point the app at production services you would not normally use; measure with the user's own normal setup, read only.

## Common causes, by frequency

1. **Polling remote APIs on a short interval**, or on every panel open, when the data changes rarely.
2. **No HTTP caching**: `URLCache` disabled, `reloadIgnoringLocalCacheData`, no `ETag`/`If-Modified-Since`.
3. **Main-thread disk I/O**: `Data(contentsOf:)`, `UserDefaults` with large blobs, synchronous Core Data fetches on the view context.
4. **Fetching whole objects or lists** where the UI shows a few fields.
5. **Keychain reads on every request** instead of once per session.

## Fixes

- Longer intervals with tolerance; refresh on demand (panel open) with a minimum age; back off on errors.
- Respect HTTP caching; conditional requests.
- Background contexts or actors for persistence; fetch limits and batch sizes.
- Read secrets once and keep them in memory for the session.

## Pitfalls

- Changing what an API returns or how often data refreshes can change what the user sees. That is a product decision: ask.
- Remote latency varies: judge network changes on CPU and context switches, not on wall time.
