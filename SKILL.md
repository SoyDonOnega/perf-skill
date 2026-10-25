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

Make an app faster with evidence. The skill is the loop **measure → change one thing → measure again → keep or revert**. The five areas are where to look; the loop is what makes a change count. It does not deploy, does not write to production, and does not keep a change that the numbers do not support.

Paths in this file are relative to the skill root (the folder that contains this SKILL.md).

## When invoked

1. **Parse the input.** Target: a repo path, a URL, or both. `--audit` = stop after the plan (step 6) and change no project file. `--area` = only those areas. No target → ask once. A URL without a repo → audit-only (nothing to change).
2. **Recon the project.**
   - Stack: read the manifest files (`package.json`, lockfile, framework and bundler config, backend and ORM config). Note framework, bundler, rendering mode (SPA, SSR, static), data layer, tests, and existing monitoring (error-tracking or APM SDK, end-to-end test config).
   - Constraints: read `README*`, `HANDOFF*`, `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING*` and any design or product notes in the repo root. List every product rule that limits a fix (for example "never downscale images", "keep this font"). A finding that breaks one goes to the user as a decision, never as a default fix.
   - Areas: mark each one applicable or not, with the reason (for example, no data layer → skip `db`).
   - Deployment: note the public URL if the repo names one (config, README, hosting files).
3. **Production build, local serve.**
   - Install dependencies from the lockfile first (`npm ci`, `pnpm install --frozen-lockfile`, `yarn install --immutable`, `bun install --frozen-lockfile`). Report any install script the package manager blocked.
   - Run the project's build, then its production serve or preview command on a fixed host and port that fails instead of moving if the port is taken (Vite: `vite preview --host 127.0.0.1 --port 4173 --strictPort`). Never measure a dev server: dev builds are unminified and some frameworks render twice on purpose.
   - Record the exact install, build and serve commands and the exact URLs. Every later measurement uses the same ones.
4. **Baseline.**
   - Create `.perf/` in the repo and exclude it locally: `echo .perf/ >> "$(git rev-parse --git-path info/exclude)"` (works in worktrees; that file is shared by every worktree of the repo, so say so in the Plan). Never commit `.perf/`.
   - Pages: pick 1–3 key pages or flows with the user. With `--audit`, or when the user does not answer, take the home page plus the route that recon shows to be heaviest (most image or JS weight), and say why in the Plan.
   - For each page: `python3 scripts/measure.py run <url> --runs 3 --dist <generated output folder> --out .perf/00-baseline-<page>.json`. Point `--dist` at the generated output only (Vite: `dist/assets`; Next: `.next/static`), not at a folder that also holds files copied from `public/`. The script also keeps the full Lighthouse report of the median run as `.perf/00-baseline-<page>.lh.json`.
   - **Noise check (A/A):** measure the first page a second time into `.perf/00-noise-<page>.json`, unchanged, and run `compare` on the pair. It must report `NO CHANGE`. If it does not, the machine is too noisy: check the load (`uptime`), ask the user to close heavy apps or other agents' builds, raise `--runs` to 5 for every measurement, and repeat. Report the result in the Plan. Skip this only in a pure URL audit with no later changes.
   - Read `warnings` and `lcp_element` in each output file. If the simulated LCP is flagged as suspect, or the LCP element is not what a user would call the main content, report both simulated and observed LCP and base LCP findings on the observed value and the element.
   - Area baselines when that area applies: render counts (`references/renders.md`; with `--audit`, only the no-code-change route it describes), query count and time per key endpoint (`references/db.md`). Save them in `.perf/`.
5. **Audit.** For each applicable area, read its reference file. Start from `findings` in the baseline files (failing Lighthouse audits with their top items; each reference names the audit IDs that belong to it), then confirm in the code. Each finding has evidence (file:line, a metric, or a request), the expected effect on a named metric with a size (from Lighthouse savings, bytes, or a measured value), effort (S/M/L), risk, any product rule it conflicts with, and whether `compare` can verify it locally. Rank by expected effect divided by effort; findings that need a user decision go after the ones that do not.
6. **Show the plan and stop.** Output the *Plan* template. Wait for the user to choose which changes to apply. With `--audit`, end here with the *Plan* template only.
7. **Apply, one change at a time,** on a new branch `perf/<YYYY-MM-DD>`:
   1. Make one change (one finding).
   2. Rebuild, run the tests, check the main flow still works.
   3. Measure into `.perf/<NN>-<slug>-<page>.json` and run `python3 scripts/measure.py compare <last kept>.json <new>.json`. Use the same page, preset and run count as the baseline.
   4. **Keep** if the metric the finding targeted improved and compare reports no regression (exit 0): commit with the before/after numbers in the message. **Revert** if a metric regressed, the tests fail, the flow breaks, or nothing changed beyond noise. A change with no effect stays only if the user wants it for another reason; ask.
   5. A change that `compare` cannot verify locally (for example caching headers): keep it only with the user's OK, and give the read-only check that will prove it after the user deploys (for example `curl -sI <public asset URL>`).
   6. Next change starts from the last kept state.
8. **Report.** Output the *Report* template. Leave the branch unpushed; tell the user it exists.

## Rules

- No change without a baseline. No baseline from a dev server.
- One change per measurement. Two changes in one measurement cannot be attributed: split them.
- Every number in the output comes from a file in `.perf/` or a command you ran. Never estimate a metric and present it as measured. Lighthouse savings are estimates: label them "est."
- Same machine, same install, build and serve commands, same URL, preset and run count, before and after. Lab numbers are noisy: trust `compare`, not a single run. Close heavy apps while measuring.
- Lab metrics are not field metrics. INP cannot be measured in a lab page load; use Total Blocking Time as the proxy and say so. Field data (real-user monitoring, error-tracking performance data, CrUX) only if the project already has it, and read only.
- Local serving does not show production caching, compression or CDN behaviour. Read-only `HEAD`/`GET` requests to the public site (for example `curl -sI`) are allowed to check headers; nothing else touches production.
- Behaviour must not change. A change that alters output, UX or API contracts, or breaks a product rule from recon, is not a performance fix; flag it and let the user decide.
- With `--audit`, change no project file. The only write is `.perf/` and its local exclude line.
- Prefer platform and framework features (native lazy loading, the framework's image and font components, HTTP caching headers) over new dependencies. A new dependency needs the user's OK and its size.
- Never deploy, push, merge, change production config, or write to monitoring tools.
- Answer in the user's language.

## Areas

| Area | Reference | Main metrics |
|---|---|---|
| renders | `references/renders.md` | TBT, render count, interaction time |
| bundle | `references/bundle.md` | Build JS (gzip), Transfer size JS, TBT, LCP |
| network | `references/network.md` | Requests, Transfer size total, LCP, caching headers |
| db | `references/db.md` | Query count and time per endpoint, server response time |
| assets | `references/assets.md` | LCP (simulated and observed), CLS, Transfer size total |

## Output

**Plan** (step 6):

```markdown
## Stack
- Framework / bundler / rendering / data layer / tests / monitoring
- Install: `<command>` · Build: `<command>` · Serve: `<command>`
- Lighthouse <version>, preset <mobile|desktop>, <N> runs (median run)

## Product constraints
- <rule> — <file>  (or "None found")

## Baseline
| Page (URL) | Score | LCP sim. | LCP obs. | LCP element | TBT | CLS | JS transfer (gzip) | Build JS (gzip) | Requests |
|---|---|---|---|---|---|---|---|---|---|
- Warnings: <from the measurement files, or "none">
- Noise check: <NO CHANGE with N runs | what moved, and the run count used>
- Why these pages: <reason>

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
| Page | Metric | Baseline | Final | Delta |
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

- `scripts/measure.py` — `run` (Lighthouse, median run of N, full report kept as `.lh.json`, warnings, failing audits as `findings`, observed LCP and LCP element, optional build size), `bundle` (generated output size by type plus largest files), `compare` (before/after table; a metric moves only past a relative threshold, an absolute floor and with non-overlapping run ranges; exit 1 on regression).
- `references/renders.md` — detect and remove unnecessary renders.
- `references/bundle.md` — shrink the bundle: code splitting, lazy loading, dependency weight.
- `references/network.md` — fewer and cheaper requests: caching, deduplication, waterfalls.
- `references/db.md` — slow queries and N+1.
- `references/assets.md` — images, fonts and third-party scripts.

## Harness notes

- Claude Code desktop app: use the built-in browser to check flows and read the Performance API (`performance.getEntriesByType(...)`) when a metric needs a real interaction.
- Optional MCP servers, used only if already configured in the session; the skill never installs them: Chrome DevTools MCP (performance traces, INP on a scripted interaction), Playwright MCP (scripted flows), Sentry MCP (field performance and slow transactions, read only).
- Lighthouse version is pinned in `scripts/measure.py`; override with `PERF_LIGHTHOUSE=lighthouse@<version>`. Audit IDs in `references/` are those of Lighthouse 13; check them again when the pin changes.
