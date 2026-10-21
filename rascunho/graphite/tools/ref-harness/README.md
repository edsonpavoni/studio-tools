# ref-harness — run the reference engine in Node

Runs the closed-source 8bitpaint pencil WebAssembly (from `reference/8bitpaint/8bitpaintpencil/`) inside a Node `vm` sandbox with stubbed host imports, so strokes can be fed with `TabletEvent` and the resulting pixels read back. No browser, no network, no file access inside the sandbox. Written by our study agent on 2026-10-20; the vendor files are only loaded at run time and stay in `reference/`.

- `run.js` — loads the glue + wasm into a vm context; `node <script> <DIR>` where DIR is the vendor folder.
- `common.js` — `setup(gray, view, doc)`: InitData, a flat paper of the given grey (or call `loadMaterial(rgba)`), the pencil app's tool table, correction 8.
- `frame.js` — captures every dirty-rect `putImageData` into a frame; `lum(x, y)` reads the displayed grey.
- `png.cjs` — tiny PNG decoder to feed the real paper textures to `LoadMaterialEvent`.
- `compare.cjs` — draws the same strokes in the reference and in our engine (same paper) and prints profiles side by side, writes `compare.png`.

Usage: `node tools/ref-harness/compare.cjs reference/8bitpaint/8bitpaintpencil`
