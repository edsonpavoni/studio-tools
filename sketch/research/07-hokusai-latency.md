# Why the Hokusai demo feels laggy with Apple Pencil (iPad Pro M1, Chrome = WKWebView)

Source read at `reearth/hokusai@main` (v0.3.0, pushed 2026-10-11, 17 stars). The live page at reearth.github.io/hokusai is byte-identical to `crates/hokusai-wasm/demo/index.html` on main.

## 1. Repo layout and glue

- Engine: `crates/hokusai-core/src/stroke.rs` (libmypaint stroke math), `brushmodes.rs` (dab compositing), `tile.rs` (64×64 RGBA fix15 tiles), `crates/hokusai-tile-mem/src/lib.rs` (HashMap of tiles, so the surface is unbounded).
- Browser glue: `crates/hokusai-wasm/src/lib.rs`, plain wasm-bindgen, built by `wasm-pack build --target web --release`. **No npm package, no bundler**; the demo is one static `demo/index.html` importing `./pkg/hokusai_wasm.js`.
- Brush: `.myb` JSON fetched as text → `new HokusaiBrush(json)`. Shipped brushes: `charcoal`, `calligraphy`, `brush`, `marker_fat` only. **No pencil preset ships.**
- Stroke API: `canvas.strokeTo(brush, x, y, pressure, xtilt, ytilt, dt_seconds)`, plus `finishStroke` to flush slow-tracking lag on pointer-up.

## 2. Input path (mostly good)

Pointer Events, `touch-action: none`, `setPointerCapture`, `getCoalescedEvents()` replayed with per-sub-event timestamps, real `e.pressure` and tilt. **No** rAF throttling, **no** `getPredictedEvents`, no `pointerType` filter (fingers draw too). Drawing is per pointermove dispatch.

## 3. Render path (the structural problem)

`flush()` runs on **every pointermove dispatch**: `canvas.pixels()` → `putImageData` of the whole canvas. `pixels()` rewrites the entire RGBA buffer to white, walks every tile, does 3 divides + 3 `powf` (linear→sRGB) per painted pixel, clones the Vec, wasm-bindgen copies it into JS, then `putImageData` copies again. A zero-copy `pixelsPtr/flush_pixels` path exists but the demo doesn't use it. `MemSurface` tracks dirty tiles but `begin_atomic/end_atomic` are never called, so **no dirty-rect information reaches JS**.

Surface size: fixed `720×480` with **no devicePixelRatio scaling**, so it is a 345 k-pixel full-surface rebuild per pointer dispatch, upscaled 2× and blurry on the iPad. A naive full-res version would be ~16× worse.

## 4. Brush-level lag (biggest *felt* cause)

`stroke.rs`: `approach = 1 − exp(−100·dt / slow_tracking)`, a first-order lag with τ = `slow_tracking/100` s; the trailing distance is `velocity × τ`.

| brush | slow_tracking | τ | trail at 1000 px/s | slow_tracking_per_dab |
|---|---|---|---|---|
| brush | 4.47 | 45 ms | ~45 px | 2.48 |
| marker_fat | 3.0 | 30 ms | ~30 px | 0 |
| charcoal | 2.0 | 20 ms | ~20 px | 0 |
| calligraphy | 0.65 | 6.5 ms | ~6 px | 0.8 |

libmypaint's settings doc: slow_tracking "0 disables it". Pencils from mypaint-brushes: deevad 2B `1.03 / per_dab 1.5`, classic pencil `1.0`, deevad 4H, ramon 2B, ramon B, tanda 2B all `0`. Setting both to 0 makes the dab centre equal the raw event position. `HokusaiBrush` has no setter, so patch the JSON before construction.

## 5. Issues, benchmarks, build flags

No issues, no benchmarks. Build: `opt-level=3, lto="thin", codegen-units=1`; no SIMD, no threads; 190 KB `.wasm`.

## 6. Per event vs per frame

The engine paints dabs synchronously per `strokeTo`. On WebKit (Safari and Chrome on iPad, both WKWebView), pointermove is dispatched about once per rendering frame with the 240 Hz Pencil samples inside `getCoalescedEvents()`; rAF is 60 Hz by default. So effective cadence ≈ 60 Hz plus a ~2-frame present pipeline ≈ 33–50 ms base latency the demo cannot remove.

## Ranked causes and what our page does instead

1. **slow_tracking in every shipped brush** (45 ms trail on "brush"). → ship pencil presets with both at 0; offer smoothing as a toggle.
2. **Full-surface flatten + 3 copies + powf per dispatch.** → `begin_atomic/end_atomic` around each batch, expose dirty tiles from wasm, flatten only those 64 px tiles via a precomputed fix15→sRGB LUT, upload with `putImageData(..., dirtyRect)` or `texSubImage2D`. This is what makes a full-res 2732×2048 canvas affordable.
3. **WebKit's 60 Hz frame-aligned dispatch + present pipeline.** → unavoidable; mask it with `getPredictedEvents()` drawn as a light tail on an overlay canvas (never committed to the engine), and turn off the 60 fps feature flag in Safari.
4. **No DPR scaling** (blurry, brush radius 2× in device px). → backing store at `css × devicePixelRatio`; only viable with (2).
5. Minor: filter `pointerType === "pen"`; use `pixelsPtr` zero-copy.

**Unverified:** not profiled on the device; estimates come from reading the code.
