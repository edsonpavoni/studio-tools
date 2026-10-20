# Open-source web sketch apps as a "fork and strip" base for an iPad/Pencil tool

Verified via GitHub API (stars/license/last push as of 2026-10-20), README, issues, code search.

### Candidate table

| App | Repo / license | Stars, last push | Stack | Pencil in Safari | Infinite canvas | Export | Verdict |
|---|---|---|---|---|---|---|---|
| **Klecks** (Kleki) | [bitbof/klecks](https://github.com/bitbof/klecks), MIT | 385, 2026-10-17 | TypeScript, Canvas2D + WebGL filters, ~2.1 MB of TS source | Yes: pressure + stabilizer, `PressureNormalizer`, uses `getCoalescedEvents` in pointer-listener.ts; touch gestures. iPad issues mostly closed (#6 Safari freeze, #25 iPadOS 480 MB canvas limit, #175 pixel brush on iPad open) | No: fixed raster canvas, zoom/pan only | `klecks.getPNG()`/`getPSD()` via the **embed build**, plus an `onSubmit` callback (examples/embed/example.html) | Best raster "feels like a drawing app" base; embed mode is already a 1-button "submit" app |
| **Excalidraw** | [excalidraw/excalidraw](https://github.com/excalidraw/excalidraw), MIT | 134k, 2026-10-20 | TS/React, perfect-freehand for freedraw | Works, but weak: no coalesced events today, so 3 of 4 Pencil samples are dropped ([PR #11496, open since 2026-06](https://github.com/excalidraw/excalidraw/pull/11496)); lag vs GoodNotes ([#11323](https://github.com/excalidraw/excalidraw/issues/11323)); parasitic strokes when two-finger panning in pen mode ([#4568, open since 2022](https://github.com/excalidraw/excalidraw/issues/4568)); palm rejection bugs (#6088) | Yes | `exportToBlob` / `exportToSvg` / `exportToCanvas` | Great infrastructure, mediocre ink; heavy React bundle |
| **tldraw** | [tldraw/tldraw](https://github.com/tldraw/tldraw), **"tldraw license" (not OSI)** | 51k | TS/React SDK | Good and actively tuned: coalesced events since v3.12, pen-mode palm rejection; pressure cannot be disabled (#9568) | Yes | `editor.toImage`/SVG | **Flag:** license forbids production use without a key; hobby license discretionary and watermarked ([license](https://tldraw.dev/legal/tldraw-license)) |
| **Quickdraw** | [quickdrawjs/quickdraw](https://github.com/quickdrawjs/quickdraw), MIT | 559, 2026-10-20 (created 2026-07-31) | Plain ESM JS, zero deps, core ≈176 KB source | Designed for it: pen mode, pressure, `getCoalescedEvents`. No iPad Safari issues filed yet, and no evidence of iPad testing either | Yes | `exportPng({scale})`; **no SVG export**; `watermark:false`; headless API with hidden toolbar | Young (3 months, no releases), but closest to the spec out of the box |
| **AFFiNE** (edgeless) | [toeverything/AFFiNE](https://github.com/toeverything/AFFiNE), MIT frontend | 74k | TS, BlockSuite | Poor: "Proper iPad pencil support" still open (#13782), lag (#14223), no stylus-only mode (#14187) | Yes | n/a | Far too heavy; reject |
| **whitebophir (WBO)** | [lovasoa/whitebophir](https://github.com/lovasoa/whitebophir), AGPL-3.0 | 2.7k | Node + vanilla JS, boards stored as SVG | **No pressure** (#298 open) | Large scrolling board | SVG endpoint on server | Flat ink; AGPL; reject for feel |
| **Drawpile (web)** | [drawpile/Drawpile](https://github.com/drawpile/Drawpile), GPL-3.0 | 1.3k | Qt/C++ → WASM | Works on iPad Safari after a Safari 18 workaround | No | Server session model | A full desktop painter in WASM; impossible to strip to 5 buttons |
| **miniPaint** / **JS Paint** / **Penpot** | MIT / MIT / MPL | 3.5k / 7.9k / 61k | – | no pressure / MS Paint / design tool | – | PNG/SVG | Wrong tool |
| **Lorien** / **Saber** / **Write (Stylus Labs)** | MIT / GPL / AGPL | 6.9k / 4.9k / 268 | Godot / Flutter / C++ | native only, no web build | – | – | Reject |
| **Mira** | [toshusai/mira](https://github.com/toshusai/mira), MIT | 46, 2024-09 | Vue, raster | Built for iPad+Pencil: size and opacity by pressure, [live demo](https://toshusai.github.io/mira/) | No | PNG | Tiny, unmaintained; reference only |
| **Inkboard** / **inknote** | MIT, created Oct 2026, 0 stars | – | Vanilla JS | Claim Pencil + stylus-only mode; untested, likely AI-generated | Yes / pages | PNG/SVG | Read for ideas only |

**Google ink / Chrome Canvas:** Chrome Canvas is closed. [google/ink](https://github.com/google/ink) (Apache-2.0) is C++ for Android, no web binding. [google/ink-stroke-modeler](https://github.com/google/ink-stroke-modeler) (Apache-2.0) is C++; the only JS route is the unofficial [WhiteboardCX/ink-stroke-modeler-ts](https://github.com/WhiteboardCX/ink-stroke-modeler-ts) (Apache-2.0, 4 stars, dependency-free TS with Kalman prediction).

**Ink & Switch:** nothing shippable. [inkling](https://github.com/inkandswitch/inkling) archived; [Etui](https://github.com/inkandswitch/Etui) no README. Useful finding: [inkandswitch/wrapper](https://github.com/inkandswitch/wrapper) (Unlicense): a tiny Swift WKWebView shell that forwards Pencil at 240 Hz and finger events to the page, because "on iPad, you can't get simultaneous input from fingers and Apple Pencil in the browser." In plain Safari you get pencil-draws-while-fingers-pan only via pointer-type gating, not true simultaneity.

### 1. Ranked "fork and strip" bases

1. **Quickdraw core**. MIT, zero deps, no build step, headless API, infinite canvas, pen mode with palm rejection, pressure + coalesced events. Stripping to 5 buttons = hide toolbar, ~40 lines of own buttons, `exportPng` → `fetch(POST)`. Risks: three months old, no releases, no SVG export, no public iPad testing evidence.
2. **Klecks embed build**. The most "pencil on paper" ink of the lot (stabilizer, pressure normalizer, sketchy/pen brushes), four years of iPad bug history mostly closed, and `onSubmit` + `getPNG()` is literally a send button. Cost: fixed raster canvas (no infinite canvas, no SVG), 2 MB of TypeScript with its own UI framework.
3. **Excalidraw package**. Safe MIT, infinite canvas, PNG+SVG export API, but the worst ink of the three on iPad until PR #11496 merges, and a React bundle for five buttons.

tldraw would rank first on ink quality but is excluded on license.

### 2. Fork an app vs build ~500 lines on a library

For this exact spec, **build** is the honest recommendation, with Quickdraw core as the fallback for free infinite-canvas scaffolding.

- Every forked app pays for features you must delete: layers, shapes, text, selection, collaboration.
- The three things that make Pencil feel good in Safari are small and library-shaped: coalesced + predicted events on `pointermove` when `pointerType === 'pen'`, a stroke modeler (ink-stroke-modeler-ts or perfect-freehand), and pointer-type gating so fingers only drive a transform.
- Export and send are trivial: `canvas.toBlob` for PNG, strokes-to-`<path>` for SVG, one `fetch`.
- What forking buys: infinite-canvas math, undo, touch pinch edge cases, and (Klecks) years of real iPad bug fixes.

### 3. Apps that already "send drawing to a server"

- **Klecks embed** is the only one built around it: `onSubmit(onSuccess, onError)` and `await klecks.getPNG()`; 2draw.net is the production user.
- **whitebophir** stores every board as SVG on the Node server; no pressure.
- Nothing found that POSTs to a LAN Mac out of the box.
