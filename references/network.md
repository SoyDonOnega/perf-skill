# Network

Goal: fewer requests, smaller responses, nothing fetched twice, nothing waiting on something it does not need.

## Lighthouse audits (13.x)

`network-dependency-tree-insight` (request chains), `render-blocking-insight`, `cache-insight`, `document-latency-insight` (redirects, server response, compression of the document), `modern-http-insight`, `redirects`, `server-response-time`. Raw list: `network-requests` in the `.lh.json` report.

## Measure first

- The audits above, from `findings` in the measurement file or the `.lh.json` report.
- In a browser: the network log of the key flow. Count requests, find duplicates (same URL or same query fired twice), and draw the waterfall (which request waits on which).
- Server response time (TTFB) for the document and the main API calls.
- **Caching and compression are a deployment property.** Local preview servers usually send `no-cache` and their own compression, so `cache-insight` passes or finds nothing on localhost. Check the public site read-only: `curl -sI <public URL of a hashed asset>` and `curl -sI -H 'Accept-Encoding: br, gzip' <public URL>`. Findings from this are marked "Verifiable by compare: no" and get an after-deploy check instead.
  - Protected preview deployments (for example Vercel Authentication, Netlify password protection) answer with a redirect or `401` to the login page, so their headers are not the asset's. A `3xx` or `401` from `curl -sI` means the check cannot run there: do not bypass the protection; give the check for production, after the user merges and deploys.

## Common causes, by frequency

1. **Request waterfalls**: component A fetches, renders B, B fetches. Each level adds a round trip.
2. **Duplicate fetches**: the same data requested by several components or on every mount, with no client cache.
3. **Over-fetching**: endpoints return whole objects or unpaginated lists when the page shows a few fields.
4. **No caching headers** on hashed static assets, or `no-store` on data that could be cached briefly.
5. **Render-blocking CSS and JS** in the document head.
6. **No compression** (gzip or brotli) on text responses.
7. **Polling** where an event or a longer interval would do.

## Fixes

- Fetch in parallel; hoist fetches to the route loader or server component; preload critical data.
- A client data cache with request deduplication (the project's existing one first: TanStack Query, SWR, Apollo, RTK Query, or framework loaders).
- Paginate, select fields, or add a lighter endpoint (needs the user's OK: it changes an API).
- `Cache-Control: public, max-age=31536000, immutable` for hashed assets; `stale-while-revalidate` for data that may be slightly stale.
- `preconnect` to required third-party origins; `preload` the LCP resource.
- Turn on compression in the server or CDN config the repo controls (for example `headers` in `vercel.json`, `_headers` on Netlify, the server's config).
- `cache: "no-store"` or cache-busting query strings in fetch calls may be deliberate (content published from elsewhere must show at once). Ask before changing them.

## Pitfalls

- Caching user-specific data publicly is a security bug. Check `private` vs `public` and `Vary`.
- Local serving hides latency. If the gain depends on round trips, also measure with Lighthouse's default throttling (mobile preset) and say so.
