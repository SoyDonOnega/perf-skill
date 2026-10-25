# Assets: images, fonts, scripts

Goal: the largest visible element arrives first, nothing shifts, and third-party code does not block the page.

## Measure first

- The saved Lighthouse report: LCP element (which one it is), image audits (properly sized, modern formats, offscreen images), font display, layout shift sources, third-party summary.
- `python3 scripts/measure.py bundle <build dir>`: image and font weight in the build.

## Images

1. **Find the LCP image** and make it load first: not lazy, `fetchpriority="high"`, preloaded if it comes from CSS.
2. **Lazy-load the rest**: `loading="lazy"` on images below the fold.
3. **Right size**: `srcset` + `sizes`, or the framework's image component; never ship a 3000 px image into a 400 px slot.
4. **Modern formats**: AVIF or WebP with a fallback where needed.
5. **Reserve space**: `width` and `height` attributes or `aspect-ratio`, so loading does not shift layout (CLS).
6. Inline SVG icons or a sprite instead of many small image requests.

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
