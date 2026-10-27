# Web profile

Web apps and sites served to a browser: SPA, SSR or static. Measured with Lighthouse in headless Chrome.

## Detect

`package.json` with a web framework or bundler (Vite, Next, Nuxt, Astro, SvelteKit, Remix, webpack…), an `index.html` at the root or in `public/`, or a URL target. Requires Node (`npx`) and Google Chrome; Lighthouse is fetched on the first run.

## Recon

Read `package.json`, the lockfile, framework and bundler config, backend and ORM config. Note framework, bundler, rendering mode (SPA, SSR, static), data layer, tests, and existing monitoring (error-tracking or APM SDK, end-to-end test config). Note the public URL if the repo names one (config, README, hosting files).

## Release build

- Install dependencies from the lockfile first (`npm ci`, `pnpm install --frozen-lockfile`, `yarn install --immutable`, `bun install --frozen-lockfile`). Report any install script the package manager blocked.
- Run the project's build, then its production serve or preview command on a fixed host and port that fails instead of moving if the port is taken (Vite: `vite preview --host 127.0.0.1 --port 4173 --strictPort`). Never measure a dev server: dev builds are unminified and some frameworks render twice on purpose.
- Record the exact install, build and serve commands and the exact URLs.

## Baseline

- Targets: 1–3 key pages or flows. Default (with `--audit`, or no answer): the home page plus the route that recon shows to be heaviest (most image or JS weight).
- For each page: `python3 scripts/measure.py run --profile web <url> --runs 3 --dist <generated output folder> --out .perf/00-baseline-<page>.json`. Point `--dist` at the generated output only (Vite: `dist/assets`; Next: `.next/static`), not at a folder that also holds files copied from `public/`. The script keeps the full Lighthouse report of the median run as `.perf/00-baseline-<page>.lh.json`.
- Read `warnings` and `lcp_element` in each output file. If the simulated LCP is flagged as suspect, or the LCP element is not what a user would call the main content, report both simulated and observed LCP and base LCP findings on the observed value and the element.
- Area baselines when that area applies: render counts (`renders.md`; with `--audit`, only the no-code-change route it describes), query count and time per key endpoint (`db.md`). Save them in `.perf/`.
- `findings` are the failing Lighthouse audits with their top items; each area reference names the audit IDs that belong to it. Lighthouse savings are estimates: label them "est."

## Areas

| Area | Reference | Main metrics |
|---|---|---|
| renders | `references/web/renders.md` | TBT, render count, interaction time |
| bundle | `references/web/bundle.md` | Build JS (gzip), Transfer size JS, TBT, LCP |
| network | `references/web/network.md` | Requests, Transfer size total, LCP, caching headers |
| db | `references/web/db.md` | Query count and time per endpoint, server response time |
| assets | `references/web/assets.md` | LCP (simulated and observed), CLS, Transfer size total |

## Plan columns

- Measurement line: `Lighthouse <version>, preset <mobile|desktop>, <N> runs (median run)`
- Baseline table:

```markdown
| Page (URL) | Score | LCP sim. | LCP obs. | LCP element | TBT | CLS | JS transfer (gzip) | Build JS (gzip) | Requests |
|---|---|---|---|---|---|---|---|---|---|
```

## Profile rules

- Lab metrics are not field metrics. INP cannot be measured in a lab page load; use Total Blocking Time as the proxy and say so. Field data (real-user monitoring, error-tracking performance data, CrUX) only if the project already has it, and read only.
- Local serving does not show production caching, compression or CDN behaviour. Read-only `HEAD`/`GET` requests to the public site (for example `curl -sI`) are allowed to check headers; nothing else touches production. A change only that check can prove gets the after-deploy check, for example `curl -sI <public asset URL>`.
- Prefer platform and framework features (native lazy loading, the framework's image and font components, HTTP caching headers) over new dependencies.
- Lighthouse version is pinned in `scripts/profile_web.py`; override with `PERF_LIGHTHOUSE=lighthouse@<version>`. Audit IDs in the area references are those of Lighthouse 13; check them again when the pin changes.
