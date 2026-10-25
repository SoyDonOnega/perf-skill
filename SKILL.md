---
name: perf
description: >-
  Makes a web app faster by measurement: takes a baseline, audits five areas (unnecessary
  renders, bundle size and lazy loading, requests and caching, slow queries and N+1,
  images/fonts/scripts), then applies one change at a time, re-measures, and keeps or
  reverts each change. Use when the user runs /perf <repo path or URL>.
license: MIT
compatibility: Requires git, Node (npx), Google Chrome and Python 3 (or uv). Network on the first run to fetch Lighthouse.
argument-hint: "[--audit] [--area renders,bundle,network,db,assets] <repo path or URL>"
disable-model-invocation: true
---

# Perf

Make an app faster with evidence. The skill is the loop **measure → change one thing → measure again → keep or revert**. The five areas are where to look; the loop is what makes a change count. It does not deploy, does not touch production, and does not keep a change that the numbers do not support.

Paths in this file are relative to the skill root (the folder that contains this SKILL.md).

## When invoked

1. **Parse the input.** Target: a repo path, a URL, or both. `--audit` = stop after the plan (step 6). `--area` = only those areas. No target → ask once. A URL without a repo → audit-only (nothing to change).
2. **Recon the stack.** Read the manifest files (`package.json`, lockfile, framework and bundler config, backend and ORM config). Note: framework, bundler, rendering mode (SPA, SSR, static), data layer, existing tests, and existing monitoring (error-tracking or APM SDK, end-to-end test config). Mark each area applicable or not, with the reason (for example, no data layer → skip `db`).
3. **Production build, local serve.** Run the project's own build and its production serve or preview command. Never measure a dev server: dev builds are unminified and some frameworks render twice on purpose. Record the exact commands; every later measurement uses the same ones.
4. **Baseline.** Create `.perf/` in the repo and add it to `.git/info/exclude` (local only, never committed). Then:
   - `python3 scripts/measure.py run <url> --runs 3 --dist <build dir> --out .perf/00-baseline.json`
   - Pick 1–3 key pages or flows with the user if the app has more than one. Measure each one under its own file name.
   - Area baselines when that area applies: render counts (`references/renders.md`), query count and time per key endpoint (`references/db.md`). Save them in `.perf/` as well.
5. **Audit.** For each applicable area, read its reference file and collect findings. Each finding has evidence (file:line, a metric, or a request), the expected effect on a named metric, effort (S/M/L) and risk. Rank by expected effect divided by effort.
6. **Show the plan and stop.** Output the *Plan* template. Wait for the user to choose which changes to apply. With `--audit`, end here with the *Plan* template only.
7. **Apply, one change at a time,** on a new branch `perf/<YYYY-MM-DD>`:
   1. Make one change (one finding).
   2. Rebuild, run the tests, check the main flow still works.
   3. Measure into `.perf/<NN>-<slug>.json` and run `python3 scripts/measure.py compare <last kept>.json <new>.json`. Use the same page, preset and run count as the baseline.
   4. **Keep** if the metric the finding targeted improved and compare reports no regression (exit 0): commit with the before/after numbers in the message. **Revert** if a metric regressed, the tests fail, the flow breaks, or nothing changed beyond noise. A change with no effect stays only if the user wants it for another reason; ask.
   5. Next change starts from the last kept state.
8. **Report.** Output the *Report* template. Leave the branch unpushed; tell the user it exists.

## Rules

- No change without a baseline. No baseline from a dev server.
- One change per measurement. Two changes in one measurement cannot be attributed: split them.
- Every number in the output comes from a file in `.perf/` or a command you ran. Never estimate a metric and present it as measured.
- Same machine, same build and serve commands, same preset, same run count, before and after. Lab numbers are noisy: trust `compare`, not a single run.
- Lab metrics are not field metrics. INP cannot be measured in a lab page load; use Total Blocking Time as the proxy and say so. Field data (real-user monitoring, error-tracking performance data, CrUX) only if the project already has it, and read only.
- Behaviour must not change. A change that alters output, UX or API contracts is not a performance fix; flag it and let the user decide.
- Prefer platform and framework features (native lazy loading, the framework's image and font components, HTTP caching headers) over new dependencies. A new dependency needs the user's OK and its size.
- Never deploy, push, merge, change production config, or write to monitoring tools.
- Answer in the user's language.

## Areas

| Area | Reference | Main metrics |
|---|---|---|
| renders | `references/renders.md` | TBT, render count, interaction time |
| bundle | `references/bundle.md` | Build JS (gzip), Transfer size JS, TBT, LCP |
| network | `references/network.md` | Requests, Transfer size total, LCP |
| db | `references/db.md` | Query count and time per endpoint, server response time |
| assets | `references/assets.md` | LCP, CLS, Transfer size total |

## Output

**Plan** (step 6):

```markdown
## Stack
- Framework / bundler / rendering / data layer / tests / monitoring

## Baseline
| Page | Score | LCP | TBT | CLS | JS (gzip) | Requests |
|---|---|---|---|---|---|---|

## Findings (ranked)
| # | Area | Finding | Evidence | Target metric | Effort | Risk |
|---|---|---|---|---|---|---|

## Skipped areas
- <area>: <reason>

## Proposed order
1. #… — why first
```

**Report** (step 8):

```markdown
## Result
| Page | Metric | Baseline | Final | Delta |
|---|---|---|---|---|

## Changes
| # | Change | Commit | Target metric before → after | Verdict |
|---|---|---|---|---|
(kept / reverted: reason)

## Not done
- Findings not applied and why

## Caveats
- Lab vs field; noise; anything not measured

## Branch
- perf/<date>: N commits, not pushed. Measurements in .perf/ (not committed).
```

## Resources

- `scripts/measure.py` — `run` (Lighthouse, median of N runs, optional build-folder size), `bundle` (build output size by type), `compare` (before/after table; exit 1 on regression).
- `references/renders.md` — detect and remove unnecessary renders.
- `references/bundle.md` — shrink the bundle: code splitting, lazy loading, dependency weight.
- `references/network.md` — fewer and cheaper requests: caching, deduplication, waterfalls.
- `references/db.md` — slow queries and N+1.
- `references/assets.md` — images, fonts and third-party scripts.

## Harness notes

- Claude Code desktop app: use the built-in browser to check flows and read the Performance API (`performance.getEntriesByType(...)`) when a metric needs a real interaction.
- Optional MCP servers, used only if already configured in the session; the skill never installs them: Chrome DevTools MCP (performance traces, INP on a scripted interaction), Playwright MCP (scripted flows), Sentry MCP (field performance and slow transactions, read only).
- Lighthouse version is pinned in `scripts/measure.py`; override with `PERF_LIGHTHOUSE=lighthouse@<version>`.
