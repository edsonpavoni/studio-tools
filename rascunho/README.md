# rascunho ✏️

**Use when:** you want to draw on the iPad with the Pencil, with the feel of graphite on paper, and hand the drawing to a Claude Code session on the Mac by the session's name. Or the other way round: a session puts a picture under a sheet and you draw over it.

One web page, served from the Mac over the studio Wi-Fi. No app store, no account, no cloud: the drawings are PNG files in this folder, and the "send" goes through the inbox socket every running Claude Code session already has.

**Status 2026-10-20, 18:30: v1 complete.** Server, graphite engine and interface merged into one app, reviewed and fixed (autosave races, smudge lift, three-finger pinch, load-while-drawing), pictures to draw over added. Start here; `HANDOFF.md` is the record of the three pieces before the merge; `PLAN.md` the research-to-build history; `research/` the eight reports behind it; `design/UI-SPEC.md` the interface spec; `graphite/README.md` the engine.

## Run

```bash
cd "/Users/edsonpavoni/Library/CloudStorage/Dropbox/0000 AI/studio/rascunho"
./serve.sh        # renders the docs, starts server.py on 8880 (once; rerunning is harmless)
```

Mac: http://localhost:8880 · iPad: **http://edsons-macbook-pro.local:8880** (fallback: the Mac's LAN IP, printed on start).

**Home-screen icon.** On the iPad open that address in Safari, tap Share › *Add to Home Screen* › Add. The icon opens Rascunho full screen with no browser bars (the page ships a manifest and `icon-180.png`). For 120 Hz drawing turn off Settings › Safari › Advanced › Feature Flags › *Prefer Page Rendering Updates Near 60fps*. The icon only works while the Mac is awake on the same network with the server running: see *Always on*.

## Drawing

Pencil draws with the active tool (pressure = darkness and a little width, tilt = the side of the lead). One finger smudges (after 5 px of travel, so two-finger gestures start clean). Two fingers pan and pinch-zoom (a third finger joining or leaving re-anchors, no jump). Two-finger tap undo, three-finger tap redo (also the ↶ in the row). The Pencil wins over a finger already resting on the glass.

The row along the bottom: tool words **2H · HB · 4B · eraser** (tap selects, slide up or down sets the size S M L XL, double-tap resets), colour dots (tap; the dotted ring opens the full palette; each colour is its own layer, graphite multiplies over the others), `+` new sheet, `::` all sheets, and the sentence **send to *name* ↗**: tap the name to pick a session, the arrow to send. The hamsa shows for 2 s when the session has it, a caption says when the session *saw* it, and a reply from the session appears as a quiet card top-right (tap to dismiss).

Desktop: mouse draws, shift+mouse is a finger, arrows pan, +/- zoom, z/y undo/redo. `?debug=1` shows ms per pointer event.

**Drawing over a picture.** Any session (or you, in Terminal) can put a PNG/JPEG under a sheet:

```bash
python3 tools/place.py picture.png --note "the chapel, north wall"          # a new sheet; the iPad opens it
python3 tools/place.py picture.png --sheet 2026-10-20_17-50-10              # under an existing sheet
```

The picture sits at the sheet's origin, fitted to the same size on every device, and the graphite multiplies over it like pencil on a print. Sending the sheet back sends the picture with your lines on it. If a hand is on the glass when a picture arrives, the iPad does not switch sheets: a caption says it is waiting in `::`. In a session: `/rascunho place <image> [note]`.

## Sending, seen, replies

Sessions appear by the name you gave them (`/rename name` or `claude --name name`). A send saves `inbox/<name>/rascunho-<stamp>.png` and posts one line into the session's socket: the session reads the PNG without a prompt and answers in its own conversation; it can also reply to the iPad (`tools/reply.py`, or `/rascunho reply <text>`), with a picture if it wants. The server watches the session's transcript and marks the send **seen** when the Read happens.

**Prerequisite, verified 2026-10-20.** Sessions in bypass-permissions mode need `"crossSessionInbound": "accept"` in `~/.claude/settings.json` (set that day, backup `settings.json.bak-2026-10-20-sketch`); without it the message waits behind a 5-minute approval dialog. In default permission mode the Read of a file outside the session's folder asks once.

The `/rascunho` command (`0000 AI/.claude/commands/rascunho.md`) gives every session `latest`, `list`, `reply <text>` and `place <image> [note]`. `tools/test_send.py <session-name> [text]` posts one test line to check a session before drawing.

## Server

`server.py` is the Mac side: one Python 3 stdlib file, no dependencies. `./serve.sh` renders the docs then starts it; or `python3 server.py [--port 8880]`. It binds `0.0.0.0`, prints the LAN URLs and logs one line per request to stderr (`serve.sh` sends that to `server.log`).

| Route | What |
|---|---|
| `GET /` and any file | Static files from this folder. JS/CSS/HTML are sent `Cache-Control: no-cache` so a reload on the iPad always gets the current code. |
| `GET /sessions` | Running Claude Code sessions with a user-given name: `[{name, pid, sessionId, cwd, status, nameSource}]`, sorted by name. `?all=1` adds the auto-named ones. Read from `~/.claude/sessions/*.json`, kept only if the pid is alive and the socket exists. |
| `POST /send` | Body = PNG bytes. Headers `X-Session: <name>` (required), `X-Note`, `X-Sheet` (optional). Saves `inbox/<name>/rascunho-YYYY-MM-DD_HH-MM-SS.png`, logs it in `inbox/log.jsonl`, writes one JSON line into the session's socket (`/tmp/cc-socks/<pid>.sock`). Reply `{ok, id, path, session, delivered, detail}`. No such session: saved, `delivered: false`. Two sessions with the same name: `409`, `detail: "ambiguous"` plus the list. After a delivery the server watches that session's transcript for up to 15 min; when the session `Read`s the PNG the send is marked **seen** and a `seen` event goes out. |
| `GET /send-status?id=` · `GET /sends?limit=` | One send (`{id, time, session, path, sheet, note, delivered, seen}`) · the recent ones, newest first. |
| `POST /reply` | JSON `{"from", "sheet", "text", "image"}` from a session (`tools/reply.py` wraps it). `image` is an absolute path to a PNG/JPEG under your home folder or `/tmp`; it is copied under `replies/` and served at `/replies/<id>.png`. Stored as `replies/<id>.json`, pushed as a `reply` event. |
| `GET /replies?limit=` | Recent replies, newest first: `[{id, time, from, sheet, text, image}]`. |
| `POST /underlay[?sheet=]` | Body = PNG or JPEG bytes, headers `X-From`, `X-Note`. A picture to draw over: `sheets/<sheet>/underlay.png|jpg` (one per sheet; a new sheet named after the note unless `sheet=` is given), pushed as an `underlay {sheet, from, note, url}` event so the iPad opens it. `tools/place.py` wraps it. |
| `GET /events?since=<seq>&timeout=<s>` | Long-poll (≤ 25 s). `{seq, events: [{seq, time, type, …}]}` with every event after `since`: `sent`, `seen`, `reply`, `underlay`. The server keeps the last 200; `since=0&timeout=0` returns the current `seq`; a `since` from before a server restart returns at once so the page resyncs. |
| `POST /tile?sheet=&tx=&ty=&layer=` | PNG body → `sheets/<sheet>/<tx>_<ty>_<colour hex>.png` (atomic write): one density layer per colour. `DELETE` removes one, `GET` returns it (404 if missing). |
| `GET /sheet?sheet=` | `{id, name, tiles: [[tx, ty, layer], …], updated, thumb, underlay}` (`underlay` is a URL or null). |
| `GET /sheets` | `[{id, name, tiles (count), updated, thumb, underlay}]`, newest first. Folders starting with `_` (trash, the v1 sheets) are skipped. |
| `POST /thumb?sheet=` | PNG body → `sheets/<sheet>/thumb.png`, served at `/sheets/<sheet>/thumb.png`. The page saves one on every send, before switching sheets, and when it goes to the background. |
| `POST /sheet-meta?sheet=` | JSON `{"name": "…"}` → `sheets/<sheet>/meta.json`. |
| `DELETE /sheet?sheet=` | Moves the sheet folder to `sheets/_trash/<id>-<stamp>/`. |

Names (sessions, sheets) are reduced to `[A-Za-z0-9._-]`. Max body 64 MB. No CORS (same origin). **Trust model: the studio Wi-Fi.** There is no authentication; anything on the network can send a drawing and a note into a session, or place a picture. Keep it on a network you trust (the travel router counts).

**What the session receives.** `{"type":"user","message":{"content":"New rascunho from the iPad: <abs path>\n<note>\nRead the PNG to see it.\nTo answer on the iPad: python3 .../tools/reply.py …"},"from":"rascunho","msg_id":"<uuid>","priority":"next"}` and a newline. The session shows it as a message from another session, starts a turn if idle and `Read`s the PNG. The socket sends nothing back, so "delivered" means the line was written (a few ms).

## Always on

`./install.sh` installs the LaunchAgent `~/Library/LaunchAgents/art.edsonpavoni.rascunho.plist`: `python3 server.py --port 8880` from this folder at login, restarted if it dies, appending to `server.log`. Safe to rerun. It stops a hand-started server first; if the agent does not come up it removes itself, restarts the server by hand and says why.

**One-time prerequisite (2026-10-20, 21:45: Full Disk Access given to `/bin/zsh`, still not enough).** macOS does not let launchd jobs touch `~/Library/CloudStorage` freely. After the grant, a launchd-started zsh could create new files in this folder but was still denied `ls` of it and appending to the existing `server.log`, so `install.sh` falls back to a hand-started server (what `serve.sh` does). Until a launchd job proves it can list this folder and overwrite a synced file, always-on means: keep the Mac awake and run `serve.sh` after a reboot. One-shot test: a LaunchAgent running `/bin/zsh -c 'cd <this folder> && ls && echo x >> server.log'` must print the listing with no `operation not permitted`.

Check: `launchctl print gui/$(id -u)/art.edsonpavoni.rascunho | grep -E "state|pid"` and `curl -s localhost:8880/sessions`. Undo: `launchctl bootout gui/$(id -u)/art.edsonpavoni.rascunho && rm ~/Library/LaunchAgents/art.edsonpavoni.rascunho.plist`.

## The page

No build step, no libraries, three layers of code:

| File | What |
|---|---|
| `index.html` | The interface markup (one row along the bottom) with the sheet's canvas inside `#sheet`; manifest and icon for the home screen. |
| `ui.js`, `style.css`, `palette.json` | The interface (spec: `design/UI-SPEC.md`; prototype: `design/`). Exposes `window.rascunhoUI` (hooks `onTool/onSize/onColour/onUndo/onNew/onOpenSheet/onGrid/onSession/onSend`, setters `setSessions/setSheets/setSent/toast/…`). |
| `app.js` | The app: canvas and view (pan, zoom), gestures, tool/colour/size binding, the underlay, autosave and load, gallery, send → seen → reply. `window.rascunho = {sheet, state, api, redrawAll, undo, redo, send, underlay}` for tests. |
| `sheet.js` | The sheet: `graphite/engine/` kernels wrapped into an unbounded sheet of 1024 px tiles (256 device px: the engine draws at **4 sheet px per device px**, the supersampling that makes the line thin and tonal), **one 8-bit density layer per colour**, composited with multiply through the engine's gamma LUT; undo per 128 px block (40 strokes or 160 MB); per-tile canvases drawn through the view transform; PNG round-trips for autosave; export of the drawn region (with the underlay). |
| `client.js` | The page's only contact with the server: `api.sessions/send/sendStatus/sends/replies/sheets/sheet/tileUrl/putTile/deleteTile/putThumb/thumbUrl/renameSheet/deleteSheet` (promises; failures throw the server's `detail`) and `subscribe(handler)`, a long-poll on `/events` that backs off while the server is down. |
| `graphite/` | The engine and its study (own README, MIT). `engine/`: `stroke.js` (samples → dabs), `dab.js` (pencil, kneaded, eraser, smudge kernels), `paper.js` (procedural tooth), `tools.js` (every tool as numbers). Test page: http://localhost:8880/graphite/test/. |
| `legacy-v1/` | The first engine page (own rasteriser), kept for reference, not served as the app. |
| `tools/` | `reply.py`, `place.py`, `test_send.py`, `stitch_sheet.py` (tiles → one PNG without a browser), `render_test.mjs`; `shots/` test screenshots, `reference/` feel comparisons (not in git). |

**Storage.** `sheets/<id>/<tx>_<ty>_<colour>.png`: one density PNG per tile per colour (the R channel is the density, 0 = paper), autosaved 3 s after the last stroke, before switching sheets and when the page goes to the background; a layer touched again while its PNG is uploading stays unsaved; strokes drawn before a tile has loaded are merged into it. `thumb.png` and `underlay.png|jpg` beside them, `meta.json` for the name. Sheets from the first engine are parked in `sheets/_v1/` (different format). Inbox, sheets, replies and the log are data, not in git.

**Tuning.** Everything about the feel is numbers in `graphite/engine/tools.js` (sizes in reference document px, hardness, floors, tooth) and `graphite/engine/paper.js`; `sheet.js` only maps them. `SS` (4) and `TILE` (1024) at the top of `sheet.js`; `UNDERLAY_FIT` (2180 × 1640 device px) in `app.js`.

**Not verified on the device yet (2026-10-20):** tool-word slide and long-press timings with the Pencil, the smudge-versus-pan threshold, memory with many tiles (each tile holds 1 MB per colour used).
