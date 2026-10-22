# raio · board contract (page ↔ raio)

The board page (`index.html`, served on :8877 by `board/server.py`) never talks to the laser. It reads three JSON files that `raio.py` writes, and it writes two flag files that the running job watches. Written 2026-10-21 (Milestone 1 evening; forno's `board/` is the pattern).

## Files raio writes (all in `studio/raio/board/`)
- `next.json` · the job in red, waiting for the go. Written when `raio mark` puts the red on; `state` moves through `red` → `firing` → `done` | `stopped` | `error`.
  ```json
  {"state": "red", "job": "wobble-circle-raio", "file": "studio/raio/tests/sxs/wobble-circle-raio.raio",
   "material": {"name": "aluminium", "thickness_mm": 1.1}, "notes": "…",
   "layers": [{"order": 0, "name": "AL_WOBBLE", "mode": "line", "power_pct": 100, "speed_mm_s": 800, "freq_khz": 65, "pulse_ns": 350, "passes": 5, "wobble": "0.15/0.025", "fill": null, "path_mm": 31.4, "output": true}],
   "totals": {"passes": 5, "commands": 56551, "packets": 221, "marked_m": 2.9},
   "bbox": [-5, -17, 5, -7], "preview_svg": "board/preview.svg",
   "red_since": "2026-10-21T20:40:12", "go_at": null, "done_at": null, "seconds": null,
   "end_photo": null, "pid": 12345}
  ```
- `live.json` · during firing, rewritten at every packet: `{"state": "firing", "job": "…", "packets_sent": 57, "packets": 221, "layer": "AL_WOBBLE", "pass": 2, "passes": 5, "started": "…", "elapsed_s": 1.4}`. Removed or `state: idle` when nothing runs.
- `history.json` · a list of finished runs, newest first (job, go_at = the real GO time, seconds, est_s, state, end_photo path), appended by raio.
- `preview.svg` · raio's planner preview of the job in `next.json`, board version (`preview_svg(job, board=True)`): no ground, no legend; the page draws it on black and the layer table carries the settings. Each layer in `next.json` has `color`, the same colour as in the preview (`plan.layer_colors`).
- `stills.json` · the photos the session judged by, newest first: `[{"path", "time", "note"}]`. Written by `raio still --note "…"` (a full RaioEye still saved in `logs/`; never opens the laser). The page shows the newest of these and the end photo as "last photo".

## Since 2026-10-21 23:40 (UI pass, UI-BRIEF.md)
- `live.json` carries `layer`, `pass`, `passes`: from `plan()['marks']` (cmd index → layer/pass) at the last command *sent*; packets are queued ahead of the board, so this leads the beam a little. With pass order `shape`, the pass counter restarts at every shape. `started` is the GO time.
- `next.json` state `error` with `reason` (and `detail`): LightBurn holding the board (`lmc.Busy`), or an exception mid-run. The server also turns a `red`/`firing` next.json whose `pid` is dead into `error` ("raio ended without a word") and refuses GO for it.
- `/api/state` adds `stills` (url-mapped) and `cal` (`lmc/calibration.json`, read only: scale x/y, date).
- The camera is off on the page unless Edson turns it on ("live camera"); the session takes stills.

## Flags (`~/Library/Caches/raio/`)
- `go.flag` · the page's GO button (POST `/api/go`) touches it; the job in red fires at once. The page shows GO only while `next.json.state == "red"` and the file is younger than 10 min.
- `stop.flag` · the page's STOP (POST `/api/stop`) touches it; a job in red ends the preview; a job firing aborts (the driver polls it between packets and inside its busy-wait).
- `armed.flag` · written by the driver while the laser-enable bit is high (RaioEye reads it).

## Camera
RaioEye on :8878: `<img src="http://<host>:8878/live.mjpg">` for the live view, `/snap.jpg?full=1` for a still, `/state.json` for `{laser, camera, armed}`. The page embeds the stream directly; the server does not proxy it.

## Server (`board/server.py`, :8877)
Serves the raio folder (so `PLAN.html`, `LOG.html`, `MACHINE.html` stay reachable) with `index.html` at `/`; `GET /api/state` returns `{next, live, eye}` merged (eye = RaioEye's state.json or null); `POST /api/go`, `POST /api/stop` touch the flags; bound to 0.0.0.0 for the iPad. Run by `serve.sh` (replaces the plain http.server).

## Frame and Fire (Edson, 2026-10-21 23:47: "if I want to just fire what is in the screen right now, I need to always have 2 buttons. Frame and Fire")
- The page shows **frame** and **fire** (two taps) whenever a job is on screen (next.json with a `.raio` file), in every state but firing; while firing, **pause** (not wired yet) and **cancel** (stop.flag).
- `POST /api/frame` → the server starts `~/.venvs/raio/bin/python raio.py mark <file>` (red until fire or cancel). A red already on is stopped first, then re-framed.
- `POST /api/fire` → only while a frame (red) is on: touches go.flag and that red fires. No frame on → 409 (Edson, 23:55: "to make it safe, fire is disabled. It only gets enabled if I have clicked on frame and the frame is active"). The board never uses `raio mark --fire`.
- frame is a switch on the page: tap = red on (stays until tapped again or fire), tap again = stop.flag (the red ends).
- 409 while firing, or while a raio the server started is still planning. The started raio's output goes to `~/Library/Caches/raio/board-run.log`; if it exits non-zero before writing next.json, `/api/state.run` carries the last log line and the page shows it.
- The server drops `RAIO_NO_USB` for the raio it starts (serve.sh sets it for the server only). `RAIO_SPAWN_DRY=1` keeps it (tests).
- `raio load <job.raio>` (no laser) writes next.json `state: "ready"` + the preview: the way a session puts a job on the page for Edson to frame and fire.
- The frame (red) follows the job's **contour** since 2026-10-21 23:56 (Edson: "frame boundaried instead of contour"): every output shape's outline in turn, thinned to ≤ 3000 points; the red stays lit on the hops between shapes. `--box` gives the old bounding rectangle.
- Pause while firing is on the page but not wired (decision pending: research/04-safety.md #19, a BJJCZ pause once left the beam on).

## Pause (v0.1, 2026-10-22, measured with `lmc/pause_test.py`)
- `POST /api/pause` while `next.json` is `firing`: toggles `~/Library/Caches/raio/pause.flag` (exists = pause, removed = resume); 409 when nothing fires. `/api/state.pause_asked` = the flag exists.
- `raio mark` watches the flag: pause = `StopList` (only while the board is BUSY) + laser-enable bit low + MO closed; resume = bit + MO back + `RestartList` (only while the board still reports PAUSED), and the status must leave PAUSED within 1 s or the job is aborted (emission off, stop.flag). The board drops BUSY while paused (status 0x228; running 0x224; idle 0x220), so raio waits a pause out instead of ending the job.
- `live.json` while paused: `state: "paused"`, `paused_since`; `paused_s` = the pauses so far. The page's clock subtracts them.
- A still from RaioEye at every pause (`logs/raio-mark-…-pauseN.jpg`); `next.json.pause_photos` → `pause_photo_urls`. The end photo shows in the result.
