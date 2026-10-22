# raio · board

The laser's page: the job on screen, frame and fire, and while it cuts, the camera, the progress, pause and cancel. Made for the Superset pane beside the Claude session (~780 px wide), and the iPad. jeitinho board, nigredo; aurum for the job and the frame/fire heroes. v0.1, 2026-10-22 (`../README.md`).

**http://localhost:8877/** (iPad: `http://<your-mac>.local:8877/`, or the hub tile *Raio*). Always on: the iPad runner (`studio/ipad`) starts `board/server.py` at login.

## Top to bottom
- **Header**: sigil, state (ready · red · firing · done · stopped · error), laser and camera dots (RaioEye `:8878/state.json`; tap camera = the live view), calibration stamp.
- **The job**: label, name, material and file, one line each (fixed height: the buttons never move).
- **The buttons**, sticky at the top when the page scrolls: **frame** (a switch) + **fire** (dead until the red is really on; one tap fires it); while cutting, **pause** (a switch: pausing → resume) + **cancel**, in the same place.
- **The live box**, only while framing or cutting: a small camera feed (tap = the whole column) beside "Framing" or the progress (clock without the pauses, layer, pass, packets sent, est small).
- **The drawing**: raio's preview on black, size and centre, the 150 × 150 field inset with the job's box.
- **Warnings**: laser off USB, LightBurn has the board, raio died, last mark stopped → a short red rectangle first.
- **Result** after a run: state, time vs est, go and end times, the end photo (tap = big), a still per pause.
- **Layers** in run order, one line each; path and wobble/fill small beneath. **Runs**: the last five, with their photos.

`?demo` shows nine made-up layers (frame and fire off) to judge the list.

## How it works
`CONTRACT.md` has the files, flags and endpoints. In short: raio writes `next.json` (the job and its state), `live.json` (progress, paused), `history.json`, `preview.svg`; the page polls `/api/state`. **frame** → the server starts `raio.py mark <file>` (red until the go); **fire** → `go.flag` for that red; **pause** → `pause.flag` (raio: StopList + emission off; removed → emission on + RestartList); **cancel** → `stop.flag`. `raio load <job>` puts a job on the page without the laser.

## Run and test
`studio/raio/serve.sh` asks the runner to restart the board (new code); without the runner it starts it by hand. Logs: `~/Library/Logs/ipad-raio.log`; the raio processes the page starts: `~/Library/Caches/raio/board-run.log`.
Test without the laser or the real flags:
`RAIO_NO_USB=1 RAIO_SPAWN_DRY=1 RAIO_BOARD_DATA=<fixtures dir> RAIO_FLAGS=<scratch flags dir> python3 board/server.py 8879` (fixtures: `samples/`).

Sigil: *best* (`studio/ipad/icons/best.png` → `board/icon-180.png` via `studio/ipad/make_icons.py`).
