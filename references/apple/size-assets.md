# Size and assets

Goal: the shipped app contains only what it runs, built with Release settings.

## Measure first

- `--mode size`: `app_bytes` (bundle) and `binary_bytes` (main executable).
- Largest items: `du -sh <.app>/Contents/Frameworks/* <.app>/Contents/Resources/* | sort -h` (iOS: `<.app>/Frameworks`, `<.app>/*`).
- Release flags from the build log (see the profile guide's Recon). Instrumentation also costs CPU at runtime, so measure `launch` and `idle` too when removing it.

## Common causes, by frequency

1. **Instrumentation left on in Release**: code coverage (`-profile-generate`, `-fprofile-instr-generate`), sanitizers, `ENABLE_TESTABILITY`. Often from a scheme's Test action or a scheme Xcode generated, not from the project file.
2. **Unused or duplicated frameworks and Swift packages.**
3. **Uncompressed or oversized assets**: PNGs where asset catalogs or HEIC would do, videos and Lottie files bigger than shown.
4. **Debug symbols inside the bundle** (`DEBUG_INFORMATION_FORMAT` should be `dwarf-with-dsym`, with the dSYM outside the app).
5. **Localizations and resources for features removed long ago.**

## Fixes

- Turn instrumentation off for Release: a shared scheme (`xcshareddata/xcschemes/<scheme>.xcscheme`) with code coverage only in the Test action, or `ENABLE_CODE_COVERAGE = NO` / `CLANG_COVERAGE_MAPPING = NO` for the Release configuration. Committing a shared scheme is a project change: show it and get the user's OK.
- Remove unused dependencies; prefer system frameworks.
- Asset catalogs with app thinning; compress media; drop unused resources.

## Pitfalls

- A smaller bundle that launches the same is a weak win on macOS; rank by what the user feels.
- Third-party binary frameworks (prebuilt `.framework`, `.xcframework`) cannot be shrunk from here; report them.
