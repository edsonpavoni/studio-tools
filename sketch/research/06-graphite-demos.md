# Graphite-pencil test list for iPad Safari + Apple Pencil (2026-10-20)

Best first.

**1. 8bitpaint pencil — https://minordaimyo.net/8bitpaintpencil/** (closed source, free, by minordaimyo)
- A dedicated *pencil-only* paint tool, separate from the main 8bitpaint web app (https://minordaimyo.net/8bitpaintweb/). The official page lists Safari on iPad as supported and says tilt detection works with Apple Pencil (https://minordaimyo.net/).
- Code evidence (page source): reads `pointerType`, `pressure`, `tiltX/tiltY` and Safari's `altitudeAngle`/`azimuthAngle`, has a "Paper texture" window and a "tilt correction" slider. Gigazine's iPad Air + Pencil review: pressure changes shade, tilting gives a lighter, wider side-of-lead stroke (https://gigazine.net/gsc_news/en/20210101-8bitpaint-web).
- Setup: open, tap Start, pick a paper texture in the texture window. License: copyright only, no OSS license.
- Verdict: closest thing to a real graphite feel on the web (tilt shading + paper grain); reference only, can't build on it.

**2. Hokusai demo — https://reearth.github.io/hokusai/** (open source, MIT/Apache-2.0; https://github.com/reearth/hokusai)
- Rust port of libmypaint compiled to wasm; 188/196 stock MyPaint brushes match libmypaint. Loads real `.myb` files.
- Demo exposes only four brushes: **charcoal, calligraphy, brush, marker fat** (no 2B_pencil). Charcoal is the one to test: grainy, builds up on overlap.
- Pointer handling (demo index.html): PointerEvents with `getCoalescedEvents`, `touch-action:none`, pressure used only when `pointerType === "pen"`, `tiltX/Y` converted to MyPaint tilt. No iPad/Safari issues or notes in the repo.
- Setup to build on: `wasm-pack build crates/hokusai-wasm`, copy any MyPaint `.myb` (e.g. `deevad/2B_pencil.myb`) into `demo/brushes/`, add it to the `BRUSHES` array.
- Verdict: best open-source base; graphite needs a swap-in pencil brush, a 2-line change.

**3. Drawpile Web — https://web.drawpile.net/** (open source, GPLv3; https://drawpile.net/)
- Full Drawpile client in wasm; "works on all platforms, including iPads." A Safari 18 WebKit bug broke it on iPad; the 2.2.2 beta worked around it (https://drawpile.net/news/release-2.2.2-beta.5). The browser can host its own passworded session so you can draw solo.
- Brushes: MyPaint brush engine with pressure/tilt/velocity inputs (https://docs.drawpile.net/help/draw/mypaint). Ships a "Tanda" category with a **2B pencil**; 2.3.0 adds "Pencil 1" (https://docs.drawpile.net/devblog/2025/11/16/dev-update.html).
- Pressure/tilt in the browser build: unverified.
- Verdict: real MyPaint pencil presets on iPad today; heavy app, not a base.

**4. Kleki — https://kleki.com** (open source MIT as Klecks)
- Nearest to pencil: Pen brush → "Chalk" tip (textured) with pressure on size/opacity (https://help.kleki.com/brushes/). No tilt (https://help.kleki.com/input-devices/).
- Verdict: a textured stamp, not graphite.

**5. Chrome Canvas — https://canvas.apps.chrome/** (closed source, free, Google)
- Pencil and chalk are pressure-sensitive. iPad status unverified (one launch-era report said iOS Safari unsupported). No tilt.

**6. pixiv Sketch — https://sketch.pixiv.net/** (closed source, free with account)
- WebGL brushes with a textured pencil; reads pressure and tilt (https://web.dev/case-studies/pixiv). iPad Safari unverified.

**7. sumi — https://sumi.aure.onl** — unverified (host unreachable from the agent's network).

**Not worth opening:** PencilToP5 (plain p5 line), p5.brush (not real-time), no libmypaint.js/brushlib.js demo exists. Hokusai is the only MyPaint-in-browser engine found.

**Recommendation:** open 1 (feel target), 2 (base to build on; charcoal brush), 3 (Tanda 2B pencil) in that order.
