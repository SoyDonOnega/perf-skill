# perf

Agent skill `/perf`: make a web app faster by measurement — baseline, one change at a time, re-measure, keep or revert. Part of OneStack.

## What it does

Reads the stack and the project's own constraints (README, handoff and agent notes), builds the app for production, serves it locally on a fixed port and takes a Lighthouse baseline (median of 3 runs, full report kept, failing audits summarised) plus build size. Audits five areas — unnecessary renders, bundle size and lazy loading, requests and caching, slow queries and N+1, images/fonts/third-party scripts — and returns ranked findings with evidence. After you choose which to apply, it makes one change at a time on a `perf/<date>` branch, rebuilds, runs the tests, re-measures, and keeps the change only if the targeted metric improved with no regression. Ends with a before/after report. It never deploys, pushes or touches production.

## Usage

```text
/perf ~/code/my-app
/perf --audit https://staging.example.com
/perf --area bundle,assets ~/code/my-app
```

Output: a *Plan* (stack, baseline table, ranked findings, skipped areas, proposed order), then — after your OK — a *Report* (baseline vs final, each change kept or reverted with its numbers, caveats).

## Install

From OneStack: `./sync-install.sh` — or copy this folder as `<skills dir>/perf/`.

## Requirements

- git, Node (`npx`), Google Chrome, Python 3.
- Lighthouse is fetched by `npx` on first run (pinned version; network needed once).
- Optional, used only if your agent already has them: Chrome DevTools, Playwright and Sentry MCP servers. The skill works without them.

## Layout

- `SKILL.md` — the skill: the measure → change → re-measure loop, rules, output templates.
- `scripts/measure.py` — `run` (Lighthouse, median run of N, full report kept as `.lh.json`, warnings, failing audits, observed LCP and LCP element), `bundle` (generated output size by type plus largest files), `compare` (before/after table; exit 1 on regression). Standard library only.
- `references/renders.md`, `bundle.md`, `network.md`, `db.md`, `assets.md` — per-area checklists: Lighthouse 13 audit IDs, how to measure, common causes, fixes, pitfalls.

## License

MIT — see `LICENSE`.
