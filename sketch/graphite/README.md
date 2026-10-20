# graphite ✏️ — the graphite engine

> **Moved 2026-10-20 17:10** from `studio/graphite/` into the sketch tool: `studio/sketch/graphite/`. The app (`../sheet.js`, `../app.js`) imports `engine/` from here. The test page is also served by the app's server: http://localhost:8880/graphite/test/ (iPad: http://edsons-macbook-pro.local:8880/graphite/test/), so `serve.sh` on 8890 is optional.

**Use when:** you need the pencil-on-paper feel in a browser on the iPad: an open-source, zero-dependency engine (plain ES modules, MIT) that turns Apple Pencil samples into graphite on paper, with pencil grades, a plastic and a kneaded eraser, and a finger smudge. No UI beyond a test page.

**Started 2026-10-20.** Edson's brief: research the technique behind https://minordaimyo.net/ (8bitpaint pencil, the reference feel: speed, pressure, 4B/HB/2H, finger smudge, eraser), understand its code with many agents, then build our own lighter, open-source version. Since the merge (17:10) it is the engine of `studio/sketch/`: `../sheet.js` tiles it and gives it one density layer per colour, `../app.js` binds the interface.

## Run

```bash
cd "/Users/edsonpavoni/Library/CloudStorage/Dropbox/0000 AI/studio/sketch/graphite"
./serve.sh                      # http://localhost:8890/test/   iPad: http://edsons-macbook-pro.local:8890/test/
node test/render.mjs            # draws the test sheet → test/render.png (+ render-4x.png), prints darkness tables
node test/bench.mjs             # µs per dab / per pointer event, per tool
node tools/ref-harness/compare.cjs reference/8bitpaint/8bitpaintpencil   # reference engine vs ours, same strokes
```

**Test page** (`test/index.html`, the only UI, kept minimal on purpose): Pencil draws with the chosen tool, one finger smudges ("finger draws" toggles that). Buttons: 4H…6B, eraser, kneaded, smudge, undo, redo, clear. The slider sets the size of the active tool (pencils 2–200, erasers and finger 10–800 document px, remembered per tool in localStorage, "reset size" restores the default). Keys: 1–6 grades, `e` eraser, `s` smudge, `z`/`y` undo/redo. URL options: `?ss=4` engine pixels per device pixel (1 = none), `?paper=noise|tooth|paper|smooth`. Bottom-right shows ms per pointer event. On the iPad turn off Settings › Safari › Advanced › Feature Flags › "Prefer Page Rendering Updates Near 60fps" for 120 Hz.

## How it works

```
pointer sample (x, y, pressure, altitude, azimuth)
   │  stroke.js   4 quadratic sub-samples per event · moving average over 2c+1 (c = 8)
   │              · whole-pixel dab step (0.2 × minor radius) · touchdown ramp · taper at lift
   ▼
dab geometry   the lead tip is a half-ellipsoid pressed into the sheet to depth p' = p^k
   │           (k from "hardness", 40 → 0.625); upright it is a spherical cap, below 32°
   │           it stretches along the azimuth and slides forward to the lead side
   ▼
dab.js         per pixel: v = tipDepth − (1 − p') − tooth·(1 − h)       h = paper height
   │           pencil   D += gain·v   up to the grade's cap (4B black · HB 0.88 · 2H 0.46)
   │           kneaded  D −= 255·max(0, p − tooth·(1 − h))             peaks lift first
   │           eraser   D  = 0 in a hard disc of diameter p^k·size      1 px soft rim (ours)
   │           smudge   D → mean under the finger, gated by contact; a carried load (ours)
   ▼
8-bit density layer  ──►  engine.js  gamma-1/2.2 colour LUT → RGBA, dirty rect → putImageData
                          tile-granular undo (64 px tiles copied on first touch)
```

The laws are the ones recovered from the reference app's WebAssembly (research 10–12, 13) and rewritten from scratch; `tools/ref-harness/compare.cjs` runs the reference engine and ours on identical strokes and the same paper: **mean darkness error 0.016 (0–1 scale), mean width error 0.7 px** across pressure ladders for 4B/HB/2H, tilt 90°→10°, build-up and event spacing (2026-10-20 16:10).

What we do better than the reference, on purpose: build-up is dithered instead of truncated, so faint 2H marks still accumulate; dabs sit at sub-pixel positions (smoother rims); a touchdown ramp; the finger carries graphite out of a patch (the reference smudge only flattens in place); the plastic eraser has a soft rim; every paper is procedural and tileable (`paper.js`: `tooth` default, `noise` = the reference's salt, `paper`, `smooth`), generated at load in ~80 ms; six grades 4H…6B instead of three.

Performance (Mac M-series, node, 2732×2048 sheet): ≈ 2 µs per pencil dab, 30–50 µs per 120 Hz pointer event for HB upright, 160–200 µs for a flat-tilted 4B, 0.4–0.5 ms for the finger smudge (radius 50 px). The sheet is one flat `Uint8Array`; `dab.js` takes a buffer, stride and origin, so a tiled unbounded sheet can call it per tile.

## Folder

- `engine/` — `engine.js` (public API: sheet, undo, colour, blit), `stroke.js` (input → dabs), `dab.js` (the per-pixel kernels), `paper.js` (procedural tileable tooth), `tools.js` (every tool as numbers)
- `serve.sh` — LAN server for the test page (port 8890) · `LICENSE` — MIT (not the `reference/` folder)
- `test/` — `index.html` (minimal test page), `render.mjs` (PNG test sheet + measurements), `bench.mjs`, `png.mjs`
- `tools/ref-harness/` — runs the reference wasm in Node and compares it with our engine (`compare.cjs`, `compare.png`)
- `research/` — the study reports, numbered from 10 (01–08 are in `studio/sketch/research/`):
  10 wasm stroke pipeline · 11 wasm dab, texture, grades · 12 wasm smudge and erasers · 13 JS host and Lua API (with measurements from the wasm run in Node) · 14 paper textures (+ `13-textures/` generated tiles) · 15 graphite rendering literature · 16 ground truth from the live app in Chrome
- `reference/8bitpaint/` — downloaded copies of the closed-source app for study only (© minordaimyo, no license). Never redistribute, never copy code from it.

## Status

### 2026-10-20 16:50 — "looks fantastic"; sizes, erasers, tidy-up
Edson's verdict on the 4× sheet: looks fantastic. Added since: a per-tool size slider on the test page (exponential, remembered per tool); the plastic eraser became a real eraser (240 ≈ 4 mm, width 55→100 % with pressure) and the kneaded one 320 ≈ 5 mm. Code tidied: `tools.js` has one shared INPUT block and no leftover parameters from the first model, `engine.js` documents the whole public surface, scratch renders and the reference's scratch files are gone (its raw inline script is `app.min.js`). Verified after the tidy-up: render test, benchmark, and the reference comparison unchanged (0.016 / 0.70 px). Open: kneaded eraser should leave a ghost (lift a fraction per pass), `tooth` paper rescaled for 4×, smudge cost on the device, a tiled unbounded sheet.

### 2026-10-20 16:40 — first iPad verdict, two fixes
Edson drew on both (`research/` screenshots in his message): the reference line is thin, crisp and tonal; ours was fat, uniform grey and broken into dashes, and the mark sat offset from the Pencil. Causes and fixes:
1. **Supersampling.** The reference's document is 4× the physical screen (host JS: `window_width · 4 / ratio`, shown fitted), so a size-16 pencil is 2 CSS px wide and every screen pixel averages a 4×4 block of engine pixels. That is the thin tonal line. The engine now has `blitDown(rect, out, outW, ss)` and the test page runs at `?ss=4` by default (sheet = 4× device pixels, 90 MB on the 12.9"; ≈ 1.8 ms per 60 Hz event on the Mac for a very fast HB stroke, blit negligible). Tool sizes are in reference document pixels; the page scales them by ss/4.
2. **Pen offset.** The page sized the backing store from `innerHeight` but the CSS box from `100vh` (Safari's toolbar makes them differ), so the mark drifted down the page. Now the CSS box follows the window and client coordinates map through the canvas's real bounding box, updated on resize.
3. **Texture.** Our `tooth` paper's deep clustered pits broke the line at 1×; default is now `noise` (the reference's statistics). `tooth` needs rescaling for the 4× sheet (its features are now 0.1 mm) and shallower pits before it comes back.

### 2026-10-20 — engine matches the reference; ready for the iPad feel test
Research done (seven Opus agents, reports 10–16). Engine written by the orchestrating session on the recovered laws, then fitted against the reference engine running in Node (numbers above). Not yet done: Edson's feel verdict on the iPad (`./serve.sh`, open the iPad URL in Safari, turn off the 60 fps flag), tuning of the `tooth` paper by eye, a tiled unbounded sheet (the sketch app has one; the kernels already take tile origins), and the smudge radius vs cost on the device.
