# Verification report: graphite-pencil ink engines for a Safari/iPad rascunho app

Research date: 2026-10-20.

## 1. p5.brush (acamposuribe/p5.brush, MIT)

- Active: v2.2.2 released 2026-08-25, last commit 2026-10-10, 1.1k stars.
- **Standalone build exists**: `dist/brush.js`, "needs nothing beyond a WebGL2-capable browser"; but you must call `brush.render()` every frame ([docs/standalone.md](https://raw.githubusercontent.com/acamposuribe/p5.brush/main/docs/standalone.md)).
- **No live-pointer API.** README never mentions pointer events or device pressure. The incremental path is `brush.beginStroke(type,x,y)` → `brush.move(angle,length,pressure)` → `brush.endStroke(angle,pressure)`, and `endStroke` "triggers its rendering": nothing appears while the pen moves. `brush.spline()` accepts `[x,y,pressure]` points, so a captured stroke with per-point pressure can be re-rendered.
- **What the pencils actually are:** `src/stroke/stroke.js` defines 2B/HB/2H/charcoal as parameter tuples `[weight, scatter, sharpness, grain, opacity, spacing, pressure]`. The dab is a **randomly scattered, randomly skipped circle**; "pressure" is a simulated profile along the stroke, not device pressure.
- Rendering: circles batched as `gl.POINTS` sprites; the fragment shader is a plain smoothstep disc, **no texture, no noise**. An `image` tip type draws instanced textured quads.

**Verdict:** not a live ink engine. Usable only as a committed-stroke re-renderer on pointer-up. No tilt concept. iPad Safari performance unverified.

## 2. WhiteboardCX/ink-stroke-modeler-ts (Apache-2.0)

- Confirmed port of Google's Ink Stroke Modeler ("created by Codex"): `wobble_smoother.ts`, `position_modeler.ts`, `stylus_state_modeler.ts`, `prediction/kalman_predictor.ts` (~70 KB of TS) ([repo](https://github.com/WhiteboardCX/ink-stroke-modeler-ts)).
- API: `new StrokeModeler()`, `reset(defaultStrokeModelParams())`, `update({eventType, position, time, pressure}, results)`, `predict(results)`.
- **Not on npm**; install from GitHub; ships raw `.ts` (needs a TS-aware bundler or a one-off `tsc` to vendor a JS build).
- Single author, 8 commits (Feb 2026), 4 stars. Safari/iPad usage: **unverified**.
- Alternatives: upstream [google/ink-stroke-modeler](https://github.com/google/ink-stroke-modeler) (C++, active), [flxzt/ink-stroke-modeler-rs](https://github.com/flxzt/ink-stroke-modeler-rs) (Rust).

## 3. Other engines found

| Repo | License | Last commit | Pressure/tilt | Rendering | iPad | Verdict |
|---|---|---|---|---|---|---|
| [yapcheahshen/brushlib.js](https://github.com/yapcheahshen/brushlib.js) | ISC-style header, no LICENSE file | 2013-04 | `stroke_to(surface,x,y,pressure,xtilt,ytilt,dtime)` | Canvas 2D bezier-ellipse dabs + radialGradient | none | Dead, but a readable 800-line MyPaint port; real graphite via `.myb` settings. Slow. |
| [vitalipe/libmypaint.js](https://github.com/vitalipe/libmypaint.js) | ISC | 2016-01 | pressure + tilt | Emscripten libmypaint | none | Dead. |
| [eliot-akira/brushlib-wasm](https://github.com/eliot-akira/brushlib-wasm) | **none stated** | 2022-12 | pressure + tilt | libmypaint 1.3 → 61 KB wasm | none | Unlicensed. |
| [reearth/hokusai](https://github.com/reearth/hokusai) | MIT/Apache-2.0 | 2026-06 (crate 0.3.0) | pressure + tilt; parity with 188/196 stock MyPaint brushes | Rust → wasm-bindgen, [live demo](https://reearth.github.io/hokusai/) | unverified | **Most promising** for real libmypaint graphite/charcoal in the browser; needs Rust toolchain; Safari perf unverified. |
| [mrdoob/harmony](https://github.com/mrdoob/harmony) | GPL-3 | 2026-07 | none | Canvas 2D; `sketchy` links each point to earlier nearby points with low alpha | none | GPL + no pressure + O(n²): idea source only. |
| [DQLean/Easy-Brush](https://github.com/DQLean/Easy-Brush) | MIT | 2025-04 | pressure as a parameter, no tilt | Canvas 2D stamp engine, spacing/scatter/jitter, PNG tips, texture pattern (beta) | none | Photoshop-style stamp engine; closest JS stamp base. |
| [Oletus/glbrush.js](https://github.com/Oletus/glbrush.js) | MIT | 2019-05 | not mentioned | WebGL/2D airbrush, layers, undo | none | Dead. |
| [darkly-art/darkly](https://github.com/darkly-art/darkly) | AGPL-3.0 | 2026-10 | pressure yes | Rust/wgpu, wasm | unverified | AGPL; heavy. |

Non-OSS reference: pixiv Rascunho's WebGL point-sprite pencil ([web.dev case study](https://web.dev/case-studies/pixiv)).

## 4. Why Paper's ink felt good (published sources)

- FiftyThree called it the "Expressive Ink Engine"; speed changes the stroke ("a faster swipe will give you a thicker line") — [MIT Tech Review, 2012](https://www.technologyreview.com/2012/04/05/186872/if-an-ipad-and-a-moleskine-had-a-child/).
- Co-founder account: ink was "first built in javascript in an HTML canvas and then in OpenGL", "hundreds of prototypes… thousands of iterations", Draw tool "thin line when moving slow and thick when fast", with in-app tuning sliders — [notbor.ing "Paper at 10"](https://notbor.ing/words/paper-at-10).
- Even-rate rendering: "strokes [should] appear at an even speed and even rate… If you hit the CPU or GPU at an even rate, the results end up being very smooth" — [MacStories quoting The Verge](https://www.macstories.net/news/paper-1-1-now-available-with-faster-ink-move-duplicate-and-easy-add-features/).
- Surface Pressure (Sept 2014): width from how much of the Pencil tip touches; the edge gives "wide textured strokes that resemble charcoal or graphite", wide strokes fade dark-to-light across the width — [Wikipedia](https://en.wikipedia.org/wiki/FiftyThree), [Made Mistakes guide](https://mademistakes.com/mastering-paper/pencil/).
- Palm rejection: "a set of heuristics… run through a bayesian model" — [Pocket-lint interview](https://www.pocket-lint.com/gadgets/news/microsoft/125357-fiftythree-interview-from-microsoft-courier-roots-to-paper-and-pencil).
- Patent US10269143 ("stamp always under the stylus tip", paper + noise textures) is **Microsoft's**, not FiftyThree's ([Google Patents](https://patents.google.com/patent/US10269143B2/en)).

## Bottom line

No open-source JS engine does live, textured, pressure+tilt graphite out of the box. Best path: PointerEvents → a stroke modeler → your own WebGL stamp shader (paper texture × noise); or Hokusai/libmypaint via wasm if real MyPaint graphite is wanted and Rust tooling is acceptable. p5.brush fits only as an optional pointer-up re-renderer.
