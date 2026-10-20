# 8bitpaint pencil — technique study (v1.5.0.0, 2026-10-20)

Closed source ((c) minordaimyo, no license, no repo). Studied for the technique only; nothing copied. Edson's verdict on the app: "this is perfect: pencils, eraser and finger to smudge, and runs fast. We want that."

**Headline finding:** the pencil is not a JS/canvas brush. The engine is C++ compiled with Emscripten to WebAssembly (916 KB, stripped) with an embedded Lua 5.4 interpreter, libpng and nlohmann/json. JS only forwards pointer events and blits pixels. The dab math lives in the wasm and could not be read; the pipeline below is evidenced by the JS↔wasm API, UI, assets and strings.

## Pipeline recipe (as implemented)

1. **One 2D view canvas** (`getContext("2d")`) plus two overlay canvases (selection, brush ghost). No WebGL/WebGPU/OffscreenCanvas. On iPad the viewport meta is rewritten to `initial-scale=0.5`, so the canvas backing store equals physical pixels (DPR 2 for free).
2. **Document model:** up to 9 layers, one colour per layer, each stored as an 8-bit density map (the "8bit" in the name). Layer modes normal / **multiply** / add; the pencil app defaults every layer to multiply, opacity 255.
3. **Paper texture:** nine 512×512 grey height-map PNGs (none, noise, paper, cotman, langton, …; mean R ≈180–234). Loaded once into the wasm; grain is fixed to the paper (canvas coordinates), not to the brush. Modulation happens per pixel on the dab (classic density × paper method). Default = `noise`.
4. **Input → wasm:** every pointerdown/move calls `TabletEvent(x, y, pressure, altitudeAngle, azimuthAngle)` synchronously; x,y in canvas pixels. The wasm does its own smoothing ("brush correction", 0–99, default 8) and spacing.
5. **Dab:** inferred from the ghost cursor the wasm asks JS to draw: an **ellipse with semi-axes a,b rotated by `angle` and offset by `shift`**. The footprint elongates along azimuth as altitude drops (tilt = wider, shifted toward the lead side). Per-brush params: size (1–500, slider is `500^t`; 4B/HB/2H default 16), hardness (0–100; 4B/HB 40, 2H 50). Pressure arrives raw (0–1); iOS applies a stroke-start ramp: for the first 10 pen events `p *= counter/10`.
6. **Blit:** the wasm composites layers and calls back `DrawCanvasRectFromArray(ptr, len, w, h, dst_x, dst_y, src_x, src_y, dirty_w, dirty_h)` → `ImageData` over the wasm heap → `putImageData` of the dirty rect. **No requestAnimationFrame; redraw per pointer event, dirty-rect only.** Zoom/rotate rendered by the wasm; during a pinch the JS applies a CSS transform preview, then commits on release.
7. **Stroke end:** pointerup sends four events with pressure 0 to flush; an undo snapshot is taken before the first dab of a stroke.

## Answers

- **Rendering:** 2D canvas + wasm software rasteriser; Workers only for auto-save PNG encoding and time-lapse.
- **Dab model:** no stamped tips, no `drawImage` loops, no shaders: per-pixel into the density map. "Tilt correction" (0–20) is purely a position offset compensating Pencil tip parallax; it does not change the mark.
- **Build-up:** 8-bit density, multiply with the layer colour; darkness accumulates per dab, caps at full colour. No `globalCompositeOperation` in JS.
- **Smudge:** a tool you pick (icon finger.svg), same tilt ellipse ghost as the pencil. A finger only draws when "Draw with touch" is on (pressure 0.5, altitude 90°). There is no automatic finger → smudge branch. (Our build: one finger = smudge, Edson's decision.)
- **Eraser:** "Kneaded eraser" and a round "Eraser", done in the wasm on the density map; texture-awareness unverified.
- **Input:** Pointer Events, `passive:false`, `preventDefault`, `touch-action:none`, contextmenu disabled, `touchmove` prevented on iOS. **No `getCoalescedEvents`/`getPredictedEvents`, no `setPointerCapture`.** "Disable touch" ignores all touch pointers. Two fingers = pan/zoom/rotate; two-finger tap = undo, three-finger tap = redo.
- **Libraries:** jQuery, Bootstrap, i18next, Pickr, FileSaver, SortableJS, JSZip (UI/IO only). App JS ≈ 206 KB, libs ≈ 383 KB, wasm 916 KB.
- **Terms:** "(c) minordaimyo", cooperation HALVAL Ltd., no license, no source. Twitter https://twitter.com/minordaimyo. The main app has a Lua brush-script API (`bs_width, bs_distance, bs_circle, bs_ellipse, bs_stylus_tilt…`) with sample scripts, still copyrighted, documenting the dab vocabulary (spacing check `distance < width → skip`, ellipse dab from tilt).

## Unverified (inside the stripped wasm)

Exact pressure→opacity and hardness curves, dab spacing, the texture modulation formula, 4B/HB/2H differences, smudge and eraser kernels.

## What it proves for our build

A per-pixel software rasteriser with dirty-rect `putImageData` per pointer event, at physical resolution, is fast enough on this iPad for a convincing graphite pencil. No WebGL needed, no coalesced events needed. The feel comes from: tilt ellipse, paper height map fixed to the sheet, multiply build-up, hardness, a pressure ramp on touchdown.
