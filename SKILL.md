---
name: perf
description: >-
  Makes an app faster by measurement: detects the platform, picks the matching measurement
  profile (web: Lighthouse), takes a baseline, audits that profile's areas, then applies one
  change at a time, re-measures, and keeps or reverts each change. Use when the user runs
  /perf <repo path or URL>.
license: MIT
compatibility: Requires git and Python 3 (or uv). Each profile adds its own tools; web needs Node (npx), Google Chrome and network on the first run to fetch Lighthouse.
argument-hint: "[--audit] [--area <areas>] <repo path or URL>"
disable-model-invocation: true
---

# Perf

Make an app faster with evidence. The skill is the loop **measure → change one thing → measure again → keep or revert**. A *profile* says how to build, measure and audit one kind of platform; the loop and the rules are the same for every profile. It does not deploy, does not write to production, and does not keep a change that the numbers do not support.

Paths in this file are relative to the skill root (the folder that contains this SKILL.md).

## Profiles

| Profile | Covers | Guide |
|---|---|---|
| web | Web apps and sites (SPA, SSR, static), measured in a browser | `references/web/profile.md` |

Read only the guide of the profile in use. A project that matches no profile: tell the user which platform recon found and that no profile covers it yet, and stop. Never force a profile onto a platform it does not describe (for example web metrics on a native app).

## When invoked

1. **Parse the input.** Target: a repo path, a URL, or both. `--audit` = stop after the plan (step 6) and change no project file. `--area` = only those areas of the profile. No target → ask once. A URL without a repo → audit-only (nothing to change).
2. **Recon the project.**
   - Platform: match the repo or URL against each profile's *Detect* section. A repo with several platforms (for example a web app and a native app): ask which one; one run measures one profile. Read that profile's guide and do its *Recon*.
   - Prerequisites: check the tools the profile needs. If one is missing, say which and stop; never install system tools.
   - Constraints: read `README*`, `HANDOFF*`, `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING*` and any design or product notes in the repo root. List every product rule that limits a fix (for example "never downscale images", "keep this font"). A finding that breaks one goes to the user as a decision, never as a default fix.
   - Areas: mark each area of the profile applicable or not, with the reason (for example, no data layer → skip `db`).
3. **Release build.** Follow the profile's *Release build*. Never measure a debug or development build. Record the exact install, build and run commands and the exact targets; every later measurement uses the same ones.
4. **Baseline.**
   - Create `.perf/` in the repo and exclude it locally: `echo .perf/ >> "$(git rev-parse --git-path info/exclude)"` (works in worktrees; that file is shared by every worktree of the repo, so say so in the Plan). Never commit `.perf/`.
   - Targets: pick 1–3 key pages, screens or flows with the user. With `--audit`, or when the user does not answer, take the profile's default targets and say why in the Plan.
   - For each target, run the profile's measurement into `.perf/00-baseline-<target>.json` (`python3 scripts/measure.py run --profile <profile> …`, exact form in the profile guide).
   - **Noise check (A/A):** measure the first target a second time into `.perf/00-noise-<target>.json`, unchanged, and run `python3 scripts/measure.py compare` on the pair. It must report `NO CHANGE`. If it does not, the machine is too noisy: check the load (`uptime`), ask the user to close heavy apps or other agents' builds, raise `--runs` to 5 for every measurement, and repeat. Report the result in the Plan. Skip this only in a pure URL audit with no later changes.
   - Read `warnings` in each output file and the profile's baseline checks before trusting a number. Take the area baselines the profile lists.
5. **Audit.** For each applicable area, read its reference file. Start from `findings` in the baseline files, then confirm in the code. Each finding has evidence (file:line, a metric, or a request), the expected effect on a named metric with a size (from the tool's estimated savings, bytes, or a measured value), effort (S/M/L), risk, any product rule it conflicts with, and whether `compare` can verify it locally. Rank by expected effect divided by effort; findings that need a user decision go after the ones that do not.
6. **Show the plan and stop.** Output the *Plan* template. Wait for the user to choose which changes to apply. With `--audit`, end here with the *Plan* template only.
7. **Apply, one change at a time,** on a new branch `perf/<YYYY-MM-DD>`:
   1. Make one change (one finding).
   2. Rebuild, run the tests, check the main flow still works.
   3. Measure into `.perf/<NN>-<slug>-<target>.json` and run `python3 scripts/measure.py compare <last kept>.json <new>.json`. Use the same target, settings and run count as the baseline.
   4. **Keep** if the metric the finding targeted improved and compare reports no regression (exit 0): commit with the before/after numbers in the message. **Revert** if a metric regressed, the tests fail, the flow breaks, or nothing changed beyond noise. A change with no effect stays only if the user wants it for another reason; ask.
   5. A change that `compare` cannot verify locally (for example caching headers): keep it only with the user's OK, and give the read-only check that will prove it after the user deploys or releases.
   6. Next change starts from the last kept state.
8. **Report.** Output the *Report* template. Leave the branch unpushed; tell the user it exists.

## Rules

- No change without a baseline. No baseline from a debug or development build.
- One change per measurement. Two changes in one measurement cannot be attributed: split them.
- Every number in the output comes from a file in `.perf/` or a command you ran. Never estimate a metric and present it as measured. Tool savings are estimates: label them "est."
- Same machine, same install, build and run commands, same target, settings and run count, before and after. Lab numbers are noisy: trust `compare`, not a single run. Close heavy apps while measuring.
- Lab metrics are not field metrics. Field data only if the project already has it, and read only.
- Behaviour must not change. A change that alters output, UX or API contracts, or breaks a product rule from recon, is not a performance fix; flag it and let the user decide.
- With `--audit`, change no project file. The only write is `.perf/` and its local exclude line.
- Prefer platform and framework features over new dependencies. A new dependency needs the user's OK and its size.
- Never deploy, release, push, merge, change production config, or write to monitoring tools. Production gets read-only checks only.
- The profile guide adds rules for its platform; follow them too.
- Answer in the user's language.

## Output

**Plan** (step 6):

```markdown
## Stack
- Profile: <profile>
- Framework / build tool / runtime / data layer / tests / monitoring
- Install: `<command>` · Build: `<command>` · Run: `<command>`
- <measurement line from the profile guide>

## Product constraints
- <rule> — <file>  (or "None found")

## Baseline
<baseline table from the profile guide>
- Warnings: <from the measurement files, or "none">
- Noise check: <NO CHANGE with N runs | what moved, and the run count used>
- Why these targets: <reason>

## Findings (ranked)
| # | Area | Finding | Evidence | Expected effect | Effort | Risk | Conflicts with | Verifiable by compare |
|---|---|---|---|---|---|---|---|---|

## Skipped areas
- <area>: <reason>

## Proposed order
1. #… — why first

## Side effects
- `.perf/` excluded in <path> (shared by all worktrees of this repo)
```

**Report** (step 8):

```markdown
## Result
| Target | Metric | Baseline | Final | Delta |
|---|---|---|---|---|

## Changes
| # | Change | Commit | Target metric before → after | Verdict |
|---|---|---|---|---|
(kept / reverted: reason)

## To verify after deploy
- <change>: `<read-only check>` — expected result

## Not done
- Findings not applied and why

## Caveats
- Lab vs field; noise; anything not measured

## Branch
- perf/<date>: N commits, not pushed. Measurements in .perf/ (not committed).
```

## Resources

- `scripts/measure.py` — `run --profile <profile>` (median run of N, warnings, findings; contract in `references/core/metrics.md`), `bundle` (generated output size by type plus largest files), `compare` (before/after table; a metric moves only past a relative threshold, an absolute floor and with non-overlapping run ranges; exit 1 on regression).
- `scripts/profiles.py` — profile registry; `scripts/profile_<name>.py` — one measurement module per profile (`profile_web.py`: Lighthouse).
- `references/core/metrics.md` — result file contract, metric registry, how to add a profile.
- `references/web/profile.md` — web profile: detect, recon, release build, baseline, areas, plan columns, rules.
- `references/web/renders.md`, `bundle.md`, `network.md`, `db.md`, `assets.md` — web areas.

## Harness notes

- Claude Code desktop app: use the built-in browser to check web flows and read the Performance API (`performance.getEntriesByType(...)`) when a metric needs a real interaction.
- Optional MCP servers, used only if already configured in the session; the skill never installs them: Chrome DevTools MCP (performance traces, INP on a scripted interaction), Playwright MCP (scripted flows), Sentry MCP (field performance and slow transactions, read only).
