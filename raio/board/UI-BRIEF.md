# raio · UI brief (for the next session that works on the board page)

Written 2026-10-21 23:12 by the raio session before clearing its context. Read this, then `studio/raio/README.md` (milestone 1), then the files named below. Edson's words are quoted; everything else is what we learned on the machine today.

## How the page is used (Edson, 2026-10-21 23:11)
- **Side by side with the Claude session**, in the Superset browser pane at about **half the screen width (~780 px wide, ~1100 px tall)**, nigredo. Not primarily the iPad. Design for that column first; the iPad is second.
- The session drives raio (`raio.py mark …`), the page is where Edson **looks and decides**: placement, layers, GO, progress, result.
- **"The camera can be on for the user only when needed."** Default: camera OFF on the page (no stream). A small toggle shows it. **The session takes stills itself** (`curl http://127.0.0.1:8878/snap.jpg?full=1`) to check placement before a cut and the result after; those stills can appear on the page as the "last photo", not as a live stream.
- **"I have to be able to see the layers, the line cuts, the progress, the expected time, etc."**
  - **Layers in run order**: name, mode (line/fill), power %, speed, kHz, ns, passes, wobble or fill (interval, angle, +angle/pass), path length, output on/off.
  - **The line cuts**: the preview of the geometry (raio's SVG, `board/preview.svg`), big enough to read, layers coloured, on black.
  - **Progress**: packets sent / total, current layer and pass (raio's `live.json` does not send layer/pass yet: add it in `raio.py` `cmd_mark` progress callback; the planner knows which packet belongs to which layer/pass), elapsed seconds.
  - **Expected time**: shown, but small ("time has small importance"; LightBurn's estimates were always off). Raio's plan estimate is now good: the wobble circle plans 7.5 s vs LightBurn's ~7 s measured; the light fill planned 4.3 s and ran 5.8 s.

## What exists (built 2026-10-21, keep the contract)
- `board/server.py` (:8877, stdlib) · `board/index.html` (three states NEXT/NOW/IDLE, polls `/api/state` 2 s hot / 15 s idle, two-tap GO, Stop) · `board/CONTRACT.md` (next.json, live.json, history.json, preview.svg; go.flag / stop.flag in `~/Library/Caches/raio/`) · `board/samples/` · sigil `board/icon-180.png` (*best*, Alchemy #556659).
- `raio.py` writes next/live/history and the preview (`_board_next`, `_board_live`, `_board_history`), takes the end photo from RaioEye after each job (`_end_photo`, saved in `logs/`; the server maps it to a URL).
- jeitinho: load the `jeitinho` skill first; board kind, nigredo, aurum only for GO / the job outline, 1 px rules, four sizes, 44 px targets, `studio.css` synced copy (never edit), `augury.py` at the end.

## What today taught that the UI must show or prevent
1. **The board cannot prove emission.** At 21:53 a job reported "done" while the source emitted nothing (no pilot, no laser) until a power cycle. The page must make "did the red appear?" a human (or camera) check before GO, and after a stop/abort/USB change suggest a short red rectangle first.
2. **The autofocus sensor's red dot is always on** (off-centre). It is not raio's pilot. Never treat a dot on the camera as the frame.
3. **LightBurn holds the board.** If LightBurn is open, raio cannot open the device: show "LightBurn has the laser" plainly (`raio.py` gets `Busy`).
4. **The laser drops off USB when Edson switches it off for the noise** (often). Show laser ✓/✗ from RaioEye's `state.json` (`laser` field) prominently; a red that never appears often just means the machine is off.
5. **GO safety**: two taps; GO only while `next.state == red` and younger than 10 min (server enforces, 409 otherwise). The quiet "stop" next to GO was hit by accident once (21:51): make it clearly separate from GO.
6. **Same-place comparisons**: side-by-side tests are run at the same field position on different sheets (the periphery distorts). Not a UI item, but the preview should show where on the field the job sits (field outline 150 × 150, centre cross).
7. **Calibration** is in force (`lmc/calibration.json`, per-axis 1.0107 / 1.0139): parts are true size. A small "calibrated" stamp with the date is honest.
8. **Wobble size is LightBurn's radius** (fixed 22:29). Display "wobble r 0.15 / step 0.025" so the number means the same as in LightBurn.

## Proposed layout for the ~780 px column (top to bottom)
1. Header: sigil · raio · state pill (IDLE / RED / FIRING / DONE / STOPPED) · laser ✓/✗ · camera ✓/✗ · updated time.
2. **Job card** (NEXT/NOW): name (serif), material, notes; the **preview** full column width; under it the **layer table** in run order; totals line (passes · marked m · est time small).
3. **Action strip**: in RED: a big two-tap GO, and far from it a small "cancel red"; in FIRING: progress bar (packets), layer + pass, elapsed, big STOP.
4. **Photos**: "last photo" (the still the session took, with its time) and, behind a toggle, the live camera.
5. IDLE: last run (name, time, seconds, state, end photo), history list (last 5), links to PLAN / LOG / MACHINE.

## Open data work for the UI
- `live.json`: add `layer`, `pass`, `passes` (plan → packet ranges per layer/pass).
- A `stills.json` (or `next.json.photos[]`) the session appends to when it snaps (path, time, note), so the page shows the pictures the session used to judge.
- Measured time per layer into `history.json` (estimates later come from logs).

Do not touch `lmc/` or the machine from the UI work; test with `RAIO_NO_USB=1` and `board/samples/`.

## Done 2026-10-21 23:40 (UI session)
One column (max 860 px); header with state pill, laser ✓/✗, camera ✓/✗, calibration stamp; warnings (laser off USB, LightBurn busy, raio dead, "red rectangle first" after a stop); job card with the dark preview, field inset (150 × 150, centre cross, job box), size + centre, coloured layer table (current layer lit while firing), totals with a faint estimate; GO two taps ("red on the bed? GO"), cancel red at the top of the card; firing: elapsed (from GO), layer, pass, bar of packets sent, STOP above the job; result block; last photo (stills + end photos) with a live-camera toggle, off by default; last 5 runs. Data: `live.json` layer/pass, `stills.json` + `raio still`, real go time in history, Busy/crash → error. Contract updated. Still open: measured time per layer in history.json.
