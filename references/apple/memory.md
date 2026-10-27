# Memory

Goal: footprint stays flat over time and drops when content is closed.

## Measure first

- `settled_footprint_mb` (`--mode launch`) and `idle_footprint_mb` (`--mode idle`, after the window). A rise between them while idle is a leak or a growing cache.
- Detail: `footprint -v <pid>` (regions by category), `leaks <pid>` (needs `MallocStackLogging=1` in the environment for stacks), `xcrun xctrace record --template 'Allocations'` or `'Leaks'` (findings only).

## Common causes, by frequency

1. **Retain cycles**: closures that capture `self` strongly in timers, observers, Combine sinks and tasks.
2. **Unbounded caches**: dictionaries of images or responses with no limit; `NSCache` without a cost limit.
3. **Full-size images kept for thumbnails.**
4. **Observers never removed**, keeping their owners alive.
5. **Large models loaded whole** where a page or a query would do.

## Fixes

- `[weak self]` in long-lived closures; cancel tasks and sinks on teardown.
- `NSCache` with `countLimit`/`totalCostLimit`; purge on memory warning or when the panel closes.
- Downsample to the displayed size.

## Pitfalls

- Footprint includes memory the system can reclaim later; compare the same mode and moment only.
- The Simulator shares the Mac's memory: compare before and after, never against device limits.
