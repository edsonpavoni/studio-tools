# rascunho — iPad graphite, Claude Code inbox

> **v7, 21:45.** Renamed `sketch` → `rascunho` (folder, `/rascunho` command, page title, server messages `New rascunho from the iPad:`, inbox files `rascunho-<stamp>.png`, LaunchAgent `art.edsonpavoni.rascunho`).
>
> **v6, 18:30 (reviewed, pictures to draw over, in git).** Review fixes: autosave could mark a layer saved while a newer stroke on it was uploading; switching sheets did not wait for a save in flight; a smudge lifted toward the sheet's corner (streak); a third finger in a pinch made the view jump; strokes drawn before a tile loaded were wiped; a server restart made the page miss events; the palette highlight and the drawn colour disagreed after a reload; no save when the page went to the background. New: `POST /underlay` + `tools/place.py` + `/rascunho place`: a session puts a picture under a sheet and the iPad opens it to draw over; sends include the picture. Published in github.com/edsonpavoni/studio-tools (the 8bitpaint reference copies and anything derived from them stay out).
>
> **17:00: interface done.** Edson closed the design at 16:48 after the hamsa change. Handoff for the merge: `HANDOFF.md` + `design/UI-SPEC.md`.
>
> **15:27: built.** Engine page live at http://edsons-macbook-pro.local:8880 (graphite rasteriser, smudge, undo, autosave, send verified end to end). UI prototype, separate, at http://localhost:8880/design/ (one bottom row, no boxes). Next: Edson's feel verdict on the iPad, the three design calls in `design/NOTES.md`, then merge the UI onto the engine.
>
> **v5, 17:10 (merged).** The three pieces are one app: the `design/` interface, the `graphite/` engine (moved inside the tool from `studio/graphite/`), and this session's server and loop. `sheet.js` tiles the engine and gives it one density layer per colour; `app.js` binds everything. See README → Page.

> **v4, 16:05.** Edson stopped the brush work here (v2 of our brush was "way worse"): the pencil engine now belongs to the `studio/graphite/` session and the UI to the `design/` session. This session owns the rest: `server.py`, the send → seen → reply loop (`client.js`, `/events`, `tools/reply.py`, the `/rascunho` command for every session), sheet history and thumbnails, the always-on install (`install.sh`, blocked on one macOS permission, see README → Always on).

> **v3, 14:50 (build started).** Edson tested the candidates: *8bitpaint pencil* is the feel ("pencils, eraser and finger to smudge, and runs fast. We want that."). It is closed source, so we studied its technique (`research/08-8bitpaint-pencil-study.md`) and are building our own engine the same way: a per-pixel software rasteriser into RGBA tiles, tilt-ellipse dabs, a procedural paper height map fixed to the sheet, multiply build-up, dirty-rect `putImageData` per pointer event, all in plain JavaScript. **Hokusai is now the fallback**, not the core. Gestures decided: Pencil draws, one finger smudges, two fingers pan and zoom. Two agents are building: `server.py` (sessions, inbox, socket post, tile autosave) and the page (`index.html`, `sketch.js`, `brush.js`). The sections below describe the v2 (Hokusai) plan; Architecture › Sending and the Build order still hold.

**Status 2026-10-20 (v2, graphite first): research done, plan written, nothing built.** Seven research reports are in `research/` (links at the end). Edson's call, 14:37: *the experience of graphite, like the one I have on paper, is the entire point.* The v1 plan (clean vector pen first) is superseded by this one.

## What it is

A web page served from the Mac to Safari on the iPad Pro 12.9" 5th gen (M1, 120 Hz, Pencil 2). Pencil draws graphite, fingers pan and zoom. Pencil, a few colors, eraser, undo, an unbounded sheet of paper. One button: **send to a Claude Code session**, picked by the session's name (the one `/rename` gives). The drawing lands in that session's conversation as an image, and the session reads it.

Target feel: the Pencil tool in Paper by FiftyThree. Grain, darkness from pressure, side-of-the-lead shading from tilt, strokes that build up where they overlap, no visible lag.

## The recommendation in one paragraph

**Build on Hokusai, MyPaint's brush engine in the browser.** Hokusai (MIT/Apache-2.0) is a Rust port of libmypaint compiled to WebAssembly: the same graphite brushes MyPaint and Krita paint with, pressure and tilt included, 188 of 196 stock brushes matching the original. Its surface is a hash map of 64 px tiles, so the sheet is unbounded by design. Its demo already looked right to Edson; its lag is in the demo page and the brush presets, not in the engine, and both are ours to change (see *Latency*). Around the engine: a page of plain JavaScript (no bundler), a 150-line Python server, and **the inbox socket every running Claude Code session already has** for sending.

Fallback if Hokusai fails the feel spike on the device: a WebGL2 stamp brush of our own (textured dabs, pressure to size and darkness, tilt to dab width, paper grain). More work, nothing packaged, but fully under control.

## Why Hokusai and not the others

Six candidates could be tested today (`research/06-graphite-demos.md`). Only two are open source and graphite-capable: Hokusai and Drawpile's browser build (GPL, a full desktop painter in WASM, impossible to strip to five buttons). Everything else is a textured stamp without tilt (Kleki, Chrome Canvas), closed source (8bitpaint pencil, pixiv Rascunho), or not real-time (p5.brush). The libmypaint JavaScript ports from 2013 to 2022 are dead or unlicensed. Vector pens (perfect-freehand, tldraw, Excalidraw, Quickdraw) make clean ink, not graphite; they were the v1 plan and remain documented in `research/01-libraries.md` and `research/02-apps.md`.

## Latency: what the demo does wrong and what we do instead

From the demo's source (`research/07-hokusai-latency.md`), ranked by felt impact:

1. **Brush lag is deliberate.** Every brush the demo ships has MyPaint's `slow_tracking` on (the "brush" preset trails 45 px behind the pen at 1000 px/s; charcoal 20 px). Pencil presets from MyPaint's own library (ramon 2B, ramon B, tanda 2B, deevad 4H) ship with it at 0. We ship pencils with `slow_tracking` and `slow_tracking_per_dab` at 0 and offer smoothing as a toggle.
2. **The demo rebuilds the whole picture on every pointer event.** It converts every painted pixel from linear to sRGB with three `powf` calls, copies the buffer three times, and `putImageData`s the entire canvas. We call the engine's `begin_atomic/end_atomic`, read back only the dirty 64 px tiles, convert through a lookup table, and upload only those tiles. This is what makes a full-resolution 2732 by 2048 sheet affordable.
3. **WebKit dispatches pointer events once per frame, 60 Hz by default.** Unavoidable, with two mitigations: draw `getPredictedEvents()` as a light tail on an overlay canvas (never committed to the engine), and turn off Settings › Safari › Advanced › Feature Flags › "Prefer Page Rendering Updates Near 60fps" on the iPad for 120 Hz. Chrome on iPad is the same WebKit engine, so test in Safari.
4. **The demo runs at 720 by 480 with no device-pixel scaling**, blurry and with the brush twice as large as intended. We size the backing store at CSS pixels × devicePixelRatio.
5. Minor: filter `pointerType === "pen"` (the demo lets fingers draw), use the zero-copy pixel pointer.

Ink & Switch measured 50 to 70 ms motion-to-photon even from a native wrapper around Safari; the floor is the platform's, the rest is ours.

## Architecture

```
iPad Safari (home-screen web app)            Mac
┌──────────────────────────────┐   http    ┌──────────────────────────────────┐
│ index.html + sketch.js       │ ───────▶  │ server.py  :8880  (0.0.0.0)      │
│ hokusai_wasm.{js,wasm}       │           │  GET  /            the page      │
│ brushes/*.myb (pencils)      │           │  GET  /sessions    named sessions│
│ pencil · colors · eraser     │           │  POST /send        png + json    │
│ undo · unbounded tiled sheet │           │  POST /autosave    tiles         │
│ SEND ▸ picks a session       │           └──────┬───────────────────────────┘
└──────────────────────────────┘                  │ writes inbox/<session>/<stamp>.png
                                                  │ writes one JSON line into
                                                  ▼ /tmp/cc-socks/<pid>.sock
                                           ┌──────────────────────────────────┐
                                           │ Claude Code session "book"       │
                                           │  › message: New rascunho from the iPad: …   │
                                           │  Read(png) → sees the drawing    │
                                           └──────────────────────────────────┘
```

URL on the iPad: `http://edsons-macbook-pro.local:8880` (Bonjour name, resolves from iPadOS). Plain http is enough for pointer events, canvas, WebAssembly, fetch and home-screen install.

### Engine and page

- **Toolchain.** `rustup` is installed on the Mac but no toolchain is active and `wasm-pack` is missing. Setup is `rustup default stable`, `rustup target add wasm32-unknown-unknown`, `brew install wasm-pack`. The built `hokusai_wasm.js` + `.wasm` (190 KB) are committed into `studio/rascunho/engine/`, so the tool runs without Rust afterwards; Rust is only needed to rebuild.
- **Our fork of the wasm crate.** One small Rust change: expose dirty tiles (the engine tracks them, the wrapper never reports them) and a tile read-back through a linear-to-sRGB lookup table. Everything else is the upstream crate untouched.
- **Brushes.** Three or four MyPaint pencils vendored as `.myb` with lag settings zeroed: ramon 2B (soft), tanda 2B, deevad 4H (hard), plus one charcoal. A long press on the pencil button opens the few sliders that matter (size, hardness, grain), the way FiftyThree tuned Paper with in-app sliders.
- **Sheet.** The engine's tile map is unbounded; the page keeps a viewport (offset, zoom) over tile space. Tiles are drawn as textures into a WebGL canvas (or `drawImage` of per-tile bitmaps), only re-uploaded when dirty. Zoom is raster, like Paper.
- **Input.** Pointer Events, `pointerType === "pen"` draws, `"touch"` only pans and zooms (two fingers). `touch-action: none`, non-passive `touchstart/touchmove/gesturestart` preventDefault, no inputs near the sheet (Scribble). Coalesced events are read for x, y, pressure, tilt and time only (iOS 18.2 ships them without `pointerId`). Tilt from `tiltX/Y`; `altitudeAngle` is available on 18.2+.
- **Eraser.** A MyPaint brush in eraser mode: real partial erasing, like rubbing graphite off.
- **Undo.** Raster undo the MyPaint way: snapshot the tiles a stroke touches before it starts, restore on undo. Memory stays bounded by a stroke count.
- **Persistence.** Dirty tiles autosave to the server as PNG tiles; reload restores the sheet. A "new sheet" button archives the old one.
- **Colors.** Graphite black plus four: the brush takes any color; Paper's palette is the reference.
- **Export.** PNG of the drawn region (bounding box of painted tiles + margin, white sheet) composed on the page from the tiles, plus a JSON of the raw input points per stroke for the record.

### Sending

1. Tap **Send**. The page fetches `/sessions`: the server scans `~/.claude/sessions/*.json`, keeps entries whose `nameSource` is `user` (renamed sessions only; auto-derived names collide), whose pid is alive and whose socket exists. Names like `book`, `today`, `oracle`.
2. Tap a name. The page POSTs the PNG (+ json).
3. The server writes `inbox/<session>/rascunho-YYYY-MM-DD_HH-MM-SS.png` (history kept, like claude-shot's `shots/`), connects to the session's `messagingSocketPath` and writes one line:
   `{"type":"user","message":{"content":"New rascunho from the iPad: <abs path>.png. Read it."},"from":"rascunho","msg_id":"<uuid>","priority":"next"}`
4. The session shows a dim "message from rascunho" line, starts a turn if idle (or picks it up between tool calls), reads the PNG and sees the drawing.

**One-time setting.** Sessions here run with permissions bypassed, and a bypass-mode session *holds* a cross-session message behind an approval dialog that expires in 5 minutes. `"crossSessionInbound": "accept"` in `~/.claude/settings.json` makes delivery unattended. The socket is owner-only on Edson's own machine.

**Fallback (Superset-only).** `superset terminals send --local --workspace … --terminal … --text "Read <path>"` types into the pane the session lives in. Works without the setting; fails for sessions not started from Superset.

Rejected: Monitor on a folder (each session must arm it, lapses every 30 min), claude-shot-style paste (frontmost window only), `claude -p --resume` (forks the transcript), channels (research preview, every session restarted with a flag). Details in `research/04-send-to-session.md`.

## Build order

| Step | What | Done when |
|---|---|---|
| 0 | **Socket spike.** 20 lines of Python post a line into a throwaway session's socket. | A test session shows the message and reads a PNG. Confirms wire format, `from` field, the settings gate. |
| 1 | **Feel spike.** Toolchain set up, Hokusai demo page patched: pencil presets with lag zeroed, DPR-scaled canvas, pen-only input, dirty-tile read-back. Served to the iPad. | Edson draws for ten minutes in Safari (60 fps flag off) and says whether it is graphite. Decides Hokusai vs own WebGL brush. |
| 2 | Sheet: viewport over tiles, two-finger pan/zoom, undo, autosave. | Reload the page, the drawing is still there. |
| 3 | Tools: pencils, colors, eraser, new sheet. Home-screen manifest, icon, safe areas. | Works as a home-screen app, no Safari chrome. |
| 4 | Send: `/sessions`, `/send`, inbox files, socket post. | A drawing made on the iPad is read by a named session within seconds. |
| 5 | README, `/tools` entry, studio registry. | Same turn as step 4. |

Step 0 is half an hour. Step 1 is a day, most of it the Rust change and the read-back. Steps 2 to 4 are two days.

## Decisions open (Edson)

1. **The setting:** OK to add `crossSessionInbound: accept` to `~/.claude/settings.json`? Without it every drawing waits behind a 5-minute approval dialog in the target session.
2. **Session list:** renamed sessions only (recommended), or every running session.
3. **Folder name:** `studio/rascunho/` is provisional. `paper` and `graphite` were the other candidates.
4. **iPadOS version** on the 5th gen 12.9: 18.2 or newer is needed for coalesced events and Pencil angles.

## Test these now (Safari on the iPad)

- 8bitpaint pencil, https://minordaimyo.net/8bitpaintpencil/ : closed source, but the closest graphite feel found on the web (paper texture, tilt shading). The feel reference.
- Hokusai demo, http://reearth.github.io/hokusai/ : pick *charcoal*; the shipped brushes all carry the tracking lag described above.
- Drawpile Web, https://web.drawpile.net/ : host a passworded session, brush category Tanda, *2B pencil*. What MyPaint's pencil looks like on this iPad.

## Research reports

- `research/01-libraries.md` drawing libraries and ink engines (vector pens)
- `research/02-apps.md` full open-source apps as fork bases
- `research/03-ipad-safari.md` iPad Safari and Pencil constraints, do/don't list
- `research/04-send-to-session.md` how to post into a named Claude Code session
- `research/05-graphite-brushes.md` graphite engines: p5.brush, ink-stroke-modeler, libmypaint ports, Paper's history
- `research/06-graphite-demos.md` what can be tested today
- `research/07-hokusai-latency.md` the demo's lag, from its source
