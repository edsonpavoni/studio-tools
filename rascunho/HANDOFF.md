# rascunho — handoff (2026-10-20, 17:00) · **merged at 17:10, see README → Page**

> The merge described below is done: `index.html` + `ui.js` + `style.css` + `palette.json` (from `design/`) over `app.js` + `sheet.js` on `graphite/engine/`. The first engine page is in `legacy-v1/`. This page stays as the record of the three pieces.

Start here. This page says what exists in `studio/rascunho/`, who made it, what is verified, and what the next session does to put the finished interface on a drawing engine. Everything is served by one local server: http://localhost:8880/ on the Mac, http://edsons-macbook-pro.local:8880/ on the iPad (fallback http://192.168.204.92:8880/).

## The tool in one paragraph

An iPad web page with a graphite pencil feel (Pencil draws, one finger smudges, two fingers pan and zoom) on an unbounded sheet, and a **send** that drops the drawing into a running Claude Code session chosen by name. The session receives it through the inbox socket every Claude Code session already has, reads the PNG and can reply to the iPad. Edson's reference for the feel is the closed-source *8bitpaint pencil* (studied, not copied); his reference for the look is a minimal phone mock-up (`design/reference.jpg`).

## Three pieces, three states

| Piece | Where | State | Made by |
|---|---|---|---|
| **Server** | `server.py`, `client.js`, `tools/`, `install.sh` | Done and verified. Sessions list, inbox, socket post, tile autosave, thumbnails, sheets rename/delete, send status, replies and a long-poll event stream. See `README.md` → Server, Always on, Replying, client.js. | This session (first version), then extended by the *sketch inbox* session (replies, events, launchd). |
| **Engine page** | `index.html`, `sketch.js`, `brush.js`, `style.css`, `manifest.webmanifest`, `icon-180.png` | Working, used by Edson on the iPad since 15:15. Software-rasterised graphite into 256 px RGBA tiles, tilt ellipse, paper grain, smudge, eraser, undo, autosave, grid overlay, send. Its UI is a **placeholder bar**. See `README.md` → Page. | This session. |
| **Interface** | `design/` | **Done** (Edson, 16:48: "after this the interface is done"). A standalone clickable prototype with no engine, plus the spec `design/UI-SPEC.md`. | This session. |

Not merged yet: the interface sits beside the engine page, by Edson's instruction ("here just the UI, we merge later"). A second graphite engine is being built by another session in `studio/graphite/`; either engine can take this interface.

## What the next session does (the merge)

Read `design/UI-SPEC.md` end to end (≈2,500 words, sections a–l). It is written so an engine can implement the interface without reading `ui.js`: laws, row measurements, every control with its tap / long-press / slide / double-tap behaviour, colours and `palette.json`, brush-size steps, the paper grid, the gallery contract, the send unit end to end, the full `window.rascunhoUI` API, and a merge recipe (section k) with the binding pseudo-code. Then:

1. Copy `design/index.html`, `style.css`, `ui.js`, `palette.json` beside the engine, replace the empty `#sheet` div with the engine's canvases (z-order in section k), delete the engine's placeholder bar.
2. Bind `window.rascunhoUI` callbacks to the engine: `onTool`, `onSize`, `onColour`, `onUndo`, `onNew`, `onGrid`, `onOpenSheet`, `onSession`, `onSend`. Feed it `setSessions` (from `client.js` `api.sessions()`), `setSheets` (from `api.sheets()`, thumbnails via `api.thumbUrl`), `setSending` / `setSent` around `api.send`.
3. Use `client.js` for every server call (never raw `fetch`); subscribe to `/events` for `seen` and `reply`, which the spec's send unit and the README's "behaviours the server already supports" describe.
4. Test on the iPad the touch-only behaviours no desktop test reaches (section l): long-press timings, double-tap reset, two-finger tap undo, slide-to-size with the Pencil.

## Verified facts the merge can rely on

- Send path: a session named with `/rename` receives the drawing within milliseconds and reads it without any prompt. Verified twice on throwaway sessions, including bypass-permissions mode with `"crossSessionInbound": "accept"` in `~/.claude/settings.json` (set 2026-10-20 with Edson's approval, backup beside it).
- Engine cost: well under 0.1 ms per Pencil event at default size on the Mac; grid overlay costs nothing while drawing; export never contains the grid.
- iPad: Pro 12.9" 5th gen (M1, 120 Hz, Pencil 2: pressure and tilt, no hover). For 120 Hz page updates turn off Settings › Safari › Advanced › Feature Flags › "Prefer Page Rendering Updates Near 60fps". Safari and Chrome on iPad are the same engine.
- Platform limits that shaped the code are in `research/03-ipad-safari.md` (Do / Don't list at the end).

## Decisions Edson made today (so nobody re-asks)

- Graphite is the entire point; vector pens (perfect-freehand, tldraw, Excalidraw, Quickdraw) are out. Hokusai (MyPaint in wasm) is the fallback engine, not the core.
- Gestures: Pencil draws, one finger smudges, two fingers pan and zoom.
- Row along the bottom, no boxes: undo and grid on the left; 2H HB 4B eraser as words plus the five colour dots centred; new sheet, all sheets and "send to book ↗" on the right. Pencil silhouettes were tried and dropped for words.
- Colours: `design/palette.json` is the single source. Quick five: black, Rich Azure, Soft Deep Teal, Soft Deep Violet, Shaded Red. A dotted ring opens the full list of twenty.
- Brush size: slide up or down on the tool word, four steps (S M L XL), hairline shows it; double-tap resets.
- Send: sentence "send to book ↗", tap the name to switch session, tap the arrow to send; on success the arrow becomes the Oracle hamsa for 2 s.
- Grid on the paper: off / dots / lines, 5 mm, lines soft (4 % / 8 %), dots stronger (12 % / 18 %).
- Edge insets 56 px, send a step smaller than first tried.

## Folder map

```
studio/rascunho/
  HANDOFF.md          this page
  README.md           how to run; Server, Always on, Replying, client.js, Page sections
  PLAN.md             the research-to-build plan (v1 vector pen → v2 Hokusai → v3 own graphite engine)
  serve.sh            renders the docs to HTML and starts server.py on 8880 (skips if running)
  install.sh          always-on LaunchAgent (needs Full Disk Access for /bin/zsh, not granted yet)
  server.py           the Mac side, Python stdlib
  client.js           the page's contract with the server
  index.html sketch.js brush.js style.css manifest.webmanifest icon-180.png   the engine page
  test-drawing.png    desktop export of the engine (mouse, synthetic pressure and tilt)
  design/             the finished interface: UI-SPEC.md, index.html, style.css, ui.js, palette.json,
                      send.html (send-unit exploration, e chosen), reference.jpg, shot-*.png
  research/           eight reports: libraries, apps, iPad Safari, send-to-session, graphite brushes,
                      graphite demos, Hokusai latency, 8bitpaint technique
  tools/              test_send.py (socket post), reply.py, stitch_sheet.py, render tests
  inbox/<session>/    every drawing sent (history, git-ignored); inbox/log.jsonl
  sheets/<id>/        autosaved tiles and thumbnails
  replies/            replies from sessions to the iPad
```

Rendered copies of every Markdown page: http://localhost:8880/HANDOFF.html, `/README.html`, `/PLAN.html`, `/design/UI-SPEC.html`, `/research/*.html`.
