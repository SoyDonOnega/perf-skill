# Assets: images, fonts, scripts

Goal: the largest visible element arrives first, nothing shifts, and third-party code does not block the page.

## Lighthouse audits (13.x)

`lcp-breakdown-insight` (LCP element and its time split), `lcp-discovery-insight` (LCP resource found late, lazy-loaded, or without `fetchpriority`), `image-delivery-insight` (size, format, compression, animated images), `unsized-images`, `cls-culprits-insight`, `layout-shifts`, `font-display-insight`, `third-parties-insight`, `non-composited-animations`.

## Measure first

- The audits above, from `findings` and `lcp_element` in the measurement file.
- **Check the LCP element before trusting LCP.** If `warnings` flags the simulated LCP as suspect, or the element is small chrome (a logo, a button) rather than main content, the simulated value is driven by other downloads competing for the network, not by that element. Report simulated and observed LCP side by side and rank image fixes by bytes saved and observed LCP.
- `python3 scripts/measure.py bundle <generated output>`: image and font weight that the build emits. Images served from `public/` are not in it; take their weight from `image-delivery-insight` and `network-requests`.
- Check recon's product constraints before proposing any change in image quality, resolution or format.

## Images

1. **Find the LCP image** and make it load first: not lazy, `fetchpriority="high"`, preloaded if it comes from CSS.
2. **Lazy-load the rest**: `loading="lazy"` on images below the fold.
3. **Right size**: `srcset` + `sizes`, or the framework's image component; never ship a 3000 px image into a 400 px slot. If a product rule forbids downscaling, keep the originals for full-size views and propose thumbnails only where the image is shown small; the user decides.
4. **Images all in the first viewport**: `loading="lazy"` does not help; lower `fetchpriority` on the non-LCP ones, or serve smaller versions.
5. **Modern formats**: AVIF or WebP with a fallback where needed. A large animated GIF or WebP is better as a muted looping video (`<video autoplay muted loop playsinline>`), unless it needs transparency or CSS effects that a video cannot take.
6. **Reserve space**: `width` and `height` attributes or `aspect-ratio`, so loading does not shift layout (CLS).
7. Inline SVG icons or a sprite instead of many small image requests.

## Fonts

1. Self-host or `preconnect` to the font origin; `preload` only the one or two files used above the fold.
2. `font-display: swap` (or `optional` when a layout shift is worse than the fallback font).
3. WOFF2 only; subset to the scripts the site uses; drop unused weights.
4. Match fallback metrics (`size-adjust`, `ascent-override`, or the framework's font tool) to cut the shift on swap.

## Third-party scripts

1. Inventory every third-party script and what it is for. Ask the user before removing any: analytics and consent tools may be legal or business requirements.
2. `defer` or `async`; load non-critical ones after load or on interaction.
3. Replace heavy embeds (video, maps, chat) with a lightweight facade that loads the real thing on click.
4. Move to a web worker (Partytown or similar) only with the user's OK: it can break the script.

## Pitfalls

- Lazy loading the LCP image is the most common regression this area causes.
- Image gains show on the mobile preset with throttling; on desktop they may be noise.
