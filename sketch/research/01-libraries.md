# Open-source JS drawing libraries & ink engines for a Paper-like iPad sketch app

Research date: 2026-10-20. Stars/dates from the GitHub API today.

## Baseline: quickdrawjs/quickdraw

- https://github.com/quickdrawjs/quickdraw — MIT, 559 stars, pushed today, v0.3.0, zero deps, plain ESM. 5 open issues, none about pen/iPad.
- **What it is:** a tldraw-style whiteboard SDK (shapes, arrows, notes, sync diffs, palm rejection "pen mode"). Not an ink engine.
- **Ink:** `packages/core/src/freehand.js` is a verbatim port of perfect-freehand 1.2.3. Settings for pen: `size: width*1.2, thinning 0.6, smoothing 0.6, streamline 0.6, simulatePressure:false, easing: easeOutSine`; mouse: simulated pressure. Round caps, no taper.
- **Input:** `editor.js` reads `e.pressure`, uses `getCoalescedEvents()` when present, merges sub-pixel pen moves, gates touch to pan/pinch once a pen is seen. No tilt, no `getPredictedEvents`.
- **Rendering:** Canvas 2D. Each pointer move does `store.update` → `requestRender` → `renderScene` redraws **every shape** on one canvas; finished strokes are cached as `Path2D` but the live stroke's whole outline is recomputed each frame and the whole board repainted. No separate live-stroke layer, no incremental drawing, `desynchronized:true` only on the capture canvas.
- **Lacks for pen-on-paper feel:** tilt, texture, incremental live rendering, prediction, any paper/graphite look; its ink is the generic tldraw/excalidraw "vector blob". Good reference for pen-mode gestures and the perfect-freehand parameter set, nothing more.

## Candidates

| Library | License / stars / last push | Pressure · tilt | Smoothing & width | Render | Latency handling | iPad evidence | Size | Verdict |
|---|---|---|---|---|---|---|---|---|
| **perfect-freehand** https://github.com/steveruizok/perfect-freehand | MIT · 5,762 · 2026-04 (v1.2.3) | pressure in, no tilt | `streamline` lerp toward previous output point, `thinning`, `simulatePressure` from point spacing, start/end taper, round caps | returns polygon; you fill SVG path or `Path2D` | none; you re-run on whole point list each frame | #87 iPad PWA pencil issue (closed, CSS/pointer-capture fix); #36 "frayed lines" on canvas fixed by two canvases + `last:false` while drawing | 2.0 kB gz | The de-facto outline algorithm. Feel depends entirely on your rendering loop. |
| **tldraw freehand** https://github.com/tldraw/tldraw/tree/main/packages/tldraw/src/lib/shapes/shared/freehand | **tldraw License, not OSI**: watermark enforced · 51k | pressure (pen ×1.25); no tilt | own rewrite of perfect-freehand, `svgInk` cuts strokes at elbows; pen preset `thinning 0.62, streamline 0.62`, `PEN_EASING = t*0.65+sin(tπ/2)*0.35` | SVG | `useCoalescedEvents` **but disabled on iOS** ("sometimes getCoalescedEvents isn't present on iOS, ugh") | yes, in code | big | License kills it; read the code for parameter values. |
| **excalidraw freedraw** https://github.com/excalidraw/excalidraw (`packages/element/src/shape.ts`) | MIT · 134k · today | pressure, no tilt | perfect-freehand: `SIZE_FACTOR 4.25, THINNING 0.6, SMOOTHING 0.5`, easeOutSine | canvas, per-element bitmap cache | no coalesced events | users report "smoothing too strong" for iPad handwriting | app | Reference only. `@excalidraw/laser-pointer` (MIT) is a small standalone trail/outline generator. |
| **atrament** https://github.com/jakubfiala/atrament | MIT · 1,793 · 2026-03 | pressure (`pressureLow/High`, `pressureSmoothing`), no tilt | `smoothing` (default 0.85), "adaptive stroke" width from speed | Canvas 2D, draws **incrementally** direct to bitmap, no stroke storage | primary-pointer palm filter; no coalesced | #91 iPad QA done for v4 (2024), #53 pencil wrist bug fixed | 2.4 kB gz | Closest "just works on iPad" incremental inker; look is plain, no caps/taper control. |
| **signature_pad** https://github.com/szimek/signature_pad | MIT · 12,060 · 2026-10 | pressure (PR #880); no tilt | Bézier through midpoints, velocity-based width, `throttle 16 ms` | Canvas 2D incremental | throttled, no coalesced | #743 Apple-Pencil-only mode; #716 open: gaps at fast speed | 4.6 kB gz | Velocity-width idea in 300 lines; too signature-like for sketching. |
| **croquis.js** https://github.com/disjukr/croquis.js | Apache-2.0/MIT · 231 · **2021-12** | full `StylusState`: pressure, tilt, twist | stamp brush, `pulled-string` and `snake` stabilizers | Canvas 2D stamping | none | none | n/a | Only lib with tilt plumbing and a Photoshop-style stabilizer; unmaintained 4 years. |
| **lazy-brush** https://github.com/dulnan/lazy-brush | MIT · 1,385 · 2024-09 | none | pulled-string lazy radius; math only | none | none | none | tiny | Good stabilizer component, not an inker. |
| **stroke-stabilizer** https://github.com/usapopopooon/stroke-stabilizer | MIT · 5 · 2026-01 | pressure passed through | 9 filters incl. One-Euro, Catmull-Rom, velocity prediction | SVG path output | recommends `getCoalescedEvents` | none | n/a | One-Euro filter is the right tool (also https://github.com/casiez/OneEuroFilter). |
| **sumi** https://github.com/Aureliaar/sumi | MIT · 0 · 2026-09 | pressure yes, tilt "future" | speed/dwell/ink-remaining width, extrapolated tail on release | **WebGL2**, instanced dabs, wet-paper sim, procedural paper | coalesced events | demo sumi.aure.onl, untested on iPad | no build | Best open example of a GPU stamp-brush with paper texture; a one-person experiment. |
| **brushtips** https://github.com/darknoon/brushtips | MIT · 12 · 2019 | none | Catmull-Rom, incremental draw | WebGL | yes (incremental) | none | n/a | Educational only. |
| **p5.brush** https://github.com/acamposuribe/p5.brush | MIT · 1,122 · 2026-10 | pressure authored per point, live pointer pressure unverified | 11 brushes incl. 2B/HB/2H pencil, charcoal | WebGL2 | none | none | n/a | Pencil *look* is good; interactive pressure claim unverified. |
| paper.js / konva / fabric / pixi | MIT · all active | none built in | generic vector smoothing | canvas / WebGL | none | n/a | 89 / 56 / 92 / 265 kB gz | Scene graphs, not ink engines. |
| pressure.js | MIT · 2022 | Force/3D Touch wrapper | – | – | – | – | – | Obsolete; `PointerEvent.pressure` covers it. |
| literallycanvas / drawingboard.js | archived | – | – | – | – | – | – | Dead. |
| Ink & Switch | `Etui` (no license, 2025-01, "Opinionated Ink Physics"); `wrapper` (Unlicense, Swift, 2026-08) | – | – | – | wrapper: native WKWebView forwarding 240 Hz pencil + `predicted` events; measured 50–70 ms motion-to-photon, rAF capped at 60 Hz | yes | – | Etui is unlicensed research code; `wrapper` is the honest data point on what Safari can and cannot do. |

Platform facts: `pressure`/`tiltX` since Safari 13; `getCoalescedEvents`, `getPredictedEvents`, `altitudeAngle` since **Safari 18.2**; `pointerrawupdate` and the Ink API: not in Safari; `{desynchronized:true}` on 2D canvas: Safari 15+. Flutter hit missing `pointerId` on iOS 18.2 coalesced events; tldraw disables coalesced on iOS. `pointermove` already arrives at 240 Hz on iPad Pro (https://developer.apple.com/forums/thread/689375).

## Ranked shortlist

1. **perfect-freehand + hand-written two-layer Canvas 2D renderer** (MIT, 2 kB). Live stroke on an overlay canvas with `last:false`, committed strokes cached as `Path2D` on the base canvas, pen preset ≈ tldraw's (`thinning 0.62, streamline 0.5–0.62, PEN_EASING`), real `e.pressure`, `getCoalescedEvents` guarded for iOS. Fastest path to "Paper-fountain-pen" width breathing; proven on iPad by tldraw/excalidraw/quickdraw.
2. **GPU stamp brush (sumi-style) on WebGL2** with perfect-freehand's `getStrokePoints` (or a One-Euro filter) as the stabilizer: instanced textured dabs spaced by radius, pressure → size/opacity, tilt (`altitudeAngle`) → dab elongation, procedural paper grain multiplied in. Only route to a real graphite/pencil look; more work, nothing packaged.
3. **atrament** as-is (MIT, 2.4 kB, iPad-QA'd, incremental, pressure) when the budget is a day: tune `smoothing` down (~0.6). Caps and tapers are not controllable; it stays a smooth marker, not a pencil.

## Techniques that decide the feel (with evidence)

- **Streamline as lag/smoothness trade:** perfect-freehand lerps each point toward the previous output; tldraw and quickdraw settle at 0.5–0.62 for pens, excalidraw's higher default is what iPad hand-writers call "too strong". Keep it configurable.
- **Width from pressure *and* velocity:** `getStrokeRadius = size * easing(0.5 - thinning*(0.5 - pressure))` with a sine/`PEN_EASING` curve; `simulatePressure` is the velocity fallback. Paper's fountain pen got thicker with speed per [MIT TR 2012](https://www.technologyreview.com/s/427434/if-an-ipad-and-a-moleskine-had-a-child/); invert the sign if you want that.
- **Fat-start / end-noise guards:** `DEFAULT_FIRST_PRESSURE 0.25`, 10-point pressure seed, `END_NOISE_THRESHOLD 3` px.
- **Live stroke on its own layer, `last:false` until pointer-up:** maintainer's own fix for frayed canvas strokes (https://github.com/steveruizok/perfect-freehand/issues/36); quickdraw ignores this and repaints the whole board per move.
- **Coalesced events, guarded:** quickdraw and sumi use them; tldraw disables on iOS; Flutter patched missing `pointerId` on iOS 18.2. Fall back to raw `pointermove` (already 240 Hz on iPad).
- **Predicted events / extrapolated tail:** `getPredictedEvents` exists since Safari 18.2 but is unproven; sumi instead extrapolates a tail on release. Ink & Switch measured 50–70 ms even natively.
- **`{desynchronized:true}` 2D canvas, `touch-action:none`, `setPointerCapture`, disable Scribble, pen-mode gating by `pointerType`.**
- **End caps/corners:** sharp corners still weak in perfect-freehand (https://github.com/steveruizok/perfect-freehand/issues/113); tldraw's `svgInk` partitions at elbows.
- **Texture:** nobody packages a graphite shader; the pixiv [web.dev case study](https://web.dev/case-studies/pixiv) and sumi show the pattern (instanced quads + dry-brush texture).
