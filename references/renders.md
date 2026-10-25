# Renders

Goal: components render only when their visible output changes.

## Measure first

- React: React DevTools Profiler (record a flow, read commit count and render time per component), or wrap the suspect tree in `<Profiler id onRender>` and log counts to the console. Run against a production build with profiling enabled (`react-dom/profiling`, or the framework's profiling flag).
- Vue: Vue DevTools performance timeline; `app.config.performance = true`.
- Any framework: a Performance trace of the interaction (long tasks, scripting time). In the lab, Total Blocking Time is the proxy.
- Save counts as `.perf/renders-<flow>.json` (component → renders per interaction) before and after.

## Common causes, by frequency

1. **Unstable props**: new objects, arrays or functions created on every render and passed to children (`style={{...}}`, `onClick={() => ...}`, `options={[...]}`) defeat memoization.
2. **Context too wide**: one context value with many fields; every consumer renders when any field changes. Split contexts, or select slices (store selectors).
3. **State too high**: state lifted to a parent that many children share; typing in one input renders the whole page. Move state down to where it is used.
4. **Derived state in effects**: `useEffect` that sets state from props causes a second render. Compute during render instead.
5. **Unkeyed or index-keyed lists** that reorder: remounts and lost state.
6. **Large lists rendered in full**: virtualize above a few hundred rows.
7. **Global store subscriptions** that read the whole store instead of a selector.

## Fixes

- Stabilize: `useMemo` / `useCallback` only where a memoized child or an effect dependency needs a stable identity. Memoization everywhere costs memory and readability without benefit.
- `React.memo` (or the framework's equivalent) on expensive leaf components with stable props.
- If the project uses the React Compiler, check it is on before adding manual memoization.
- Split context; colocate state; use selectors.
- Virtualize long lists.
- Debounce or defer expensive work on input (`useDeferredValue`, `startTransition`).

## Pitfalls

- Dev mode renders twice in Strict Mode by design. Do not count those.
- A lower render count that does not move a user-facing metric is a weak win. Report it, but the verdict rests on interaction time or TBT.
