# Bundle

Goal: the first page loads only the code it needs.

## Measure first

- `python3 scripts/measure.py bundle <build dir>`: JS and CSS size, raw and gzip.
- What is inside: the bundler's analyzer (`vite-bundle-visualizer` / `rollup-plugin-visualizer`, `@next/bundle-analyzer`, `webpack-bundle-analyzer`, `source-map-explorer` on the built JS). Use `npx` for a one-off run; do not add it as a dependency unless the user wants it.
- Lighthouse audits in the saved report: unused JavaScript, legacy JavaScript, duplicated modules.

## Common causes, by frequency

1. **Everything in one entry chunk**: routes, modals, editors, charts loaded on first paint.
2. **Heavy dependencies for small jobs**: full `lodash`, `moment`, icon packs imported whole, a chart or editor library on a page that rarely shows it.
3. **Barrel imports** (`import { x } from './components'`) that pull a whole folder and defeat tree shaking.
4. **Duplicated packages**: two versions of the same library in the lockfile.
5. **Polyfills and legacy transpilation** for browsers the project does not support.
6. **Server-only code shipped to the client** (SSR frameworks): secrets aside, it is weight.

## Fixes

- Route-level code splitting: dynamic `import()`, `React.lazy` + `Suspense`, the framework's `dynamic()`; most routers do it per route already, so check before adding it.
- Lazy-load below-the-fold and on-interaction components (modals, editors, maps, charts).
- Replace or narrow heavy dependencies: per-function imports, native APIs (`Intl`, `structuredClone`, `fetch`), smaller equivalents. State the size saved.
- Import directly from the module file instead of a barrel when the bundler cannot tree-shake it.
- Deduplicate (`npm dedupe`, align versions).
- Set the browser target to what the project supports.

## Pitfalls

- Over-splitting makes many small requests and a waterfall. Check Requests and LCP, not only bytes.
- Lazy loading something visible on first paint makes LCP worse.
- Gzip size is what users download; raw size is what the browser parses. Report both.
