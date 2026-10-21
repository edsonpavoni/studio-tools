# rascunho — UI spec (handoff)

The definitive description of the rascunho tool's interface, written so an engine session can implement it without reading `ui.js`. The prototype in this folder (`index.html`, `style.css`, `ui.js`, `palette.json`) is the reference implementation; open http://localhost:8880/design/ on the iPad. `send.html` is the record of the send-unit exploration (Edson chose variant e). Screenshots: `shot-landscape.png` (row, dot grid on), `shot-colours.png` (full colour list), `shot-grid.png` (all sheets), `shot-sent.png` (hamsa after a send).

## a · intent and laws

A sheet of warm paper with a graphite pencil, for an iPad 12.9" in both orientations. The interface is one row of marks along the bottom edge; everything else is paper. Laws: **no boxes** (no bars, panels, borders, pills, shadows, dialogs); controls are thin line glyphs, small lowercase words or plain dots sitting directly on the paper; one humanist sans (`-apple-system`), small, never bold; quiet grey for words and captions (`--ink-quiet #9a958c`), ink (`--ink #2a2a2a`) only where something is active or is *the thing* (the active tool word, the session name, the send arrow, the hamsa); captions appear and fade, nothing stays; feedback is a small dignified motion (a lift, a tick, a cross-fade), never a flash. Weight is allowed in exactly two places: the active tool's hairline and the send sentence's ink words.

Paper: `--paper #f5f2eb`, fresh sheet `--paper-clean #faf8f3`, grain = an SVG `feTurbulence` layer (`#grain`, z 50, 5.5 % multiply, `pointer-events: none`), no dot grid on the sheet itself.

## b · the row

One row along the bottom, a CSS grid `1fr auto 1fr` (`#row`), its centre line `--edge` (56 px) above the safe-area inset (`--sab`) and `--edge` in from both sides (glyph boxes overhang by 14 px so the drawn marks align to the inset). Height `--sab + 2·--edge`. Three groups: `#left` (justify start), `#centre` (justify centre: centred on the screen, whatever the side groups weigh), `#right` (justify end). Column gap `--gap-groups` 30 px.

| variable | landscape | portrait / ≤1200 px | ≤900 px |
|---|---|---|---|
| `--edge` side + bottom inset | 56 px | 56 | 56 |
| `--edge-top` (grid view) | 28 px | 28 | 28 |
| `--hit` control box | 48 px | 48 | 48 |
| `--glyph` drawn line glyph | 20 px, stroke `--stroke` 1.3 px | | |
| `--dot` / `--dot-on` colour dot | 17 / 22 px (ring: 3 px paper + 1 px own colour) | | |
| `--dot-hit` dot target width | 44 px | 40 | 36 |
| `--gap-groups` | 30 px | 22 | 14 |
| `--send-air` before the send unit | 40 px | 24 | 24 |
| `--fs` captions, `--fs-tool` tool words | 12.5 / 14 px | | |
| `.group` inner gap | 4 px | 0 | 0 |

Order, left to right: **left** undo `↶`, paper grid `#` · **centre** `2H HB 4B eraser`, five quick dots, the chosen dot (when present), the dotted ring · **right** new `+`, all sheets `::`, then after `--send-air` the sentence `send to book ↗`. In grid (gallery) mode the whole row fades out and a single `←` sits top-right at `--edge-top`.

## c · controls

| control | mark | where | tap | long-press (420 ms) | slide | double-tap | state / feedback | persisted |
|---|---|---|---|---|---|---|---|---|
| undo | `↶` line glyph | left | `onUndo()`; glyph flicks (−28°, 0.45 s) | | | | caption "or tap with two fingers" shown once, 1.2–5.2 s after first load | `rascunho.hint.undo` |
| paper grid | `#` hairlines; 3×3 dots in dot mode; `#` at 38 % when off | left | cycles off → dots → lines → off, `onGrid(mode)` | | | | `#aid` layer + the glyph itself change | — (engine may persist) |
| tool word | `2H` `HB` `4B` `eraser`, 14 px | centre | selects, `onTool(id)` | opens the hardness / grain / smoothing hairlines beside it (prototype only; drop if the engine has no such params) | up/down steps its size (see f), `onSize(id, step)` on release | resets size to M, `onSize(id, 1)` | active = ink + hairline whose thickness is its size; others 50 %; `.tick` dims the line for 160 ms on each step | `rascunho.sizes` |
| quick colour ×5 | plain dot | centre | picks, `onColour(hex)` | list closed: opens the full list; list open: assigns the current colour to this slot, `onQuickChange([hex×5])`, caption "saved to the row" | | | active = 22 px with a ring in its own colour | `rascunho.quick` |
| chosen colour | sixth dot, only after a pick from the full list | centre | picks it again | | | | ring while active; stays until replaced | — |
| all colours | dotted ring (SVG circle, 16 dots, quiet grey) | centre | opens / closes the full list | | | | ring darkens while open | — |
| new sheet | `+` | right | `onNew()` after a 220 ms wash of clean paper over the sheet | | | | | |
| all sheets | `::` | right | gallery fades in, row fades out | | | | | |
| back | `←` top-right, grid mode only | | returns to the sheet | | | | | |
| send to | the words, quiet | right | sends (see i) | | | | | |
| session name | ink word | right | the other running sessions rise above it as a list; tap one: `onSession(name)`, the word rewrites | | | | dims while sending | — (`rascunho.lastSession` is the server's suggestion) |
| send arrow | `↗` 13 px ink | right | sends | | | | sending 30 %; sent → hamsa 2 s | |
| past sheet | `<figure>` with a date | gallery | `onOpenSheet(id)`, back to the sheet | | | | edge darkens while pressed | |

Every control is ≥ 44 px tall; words shorter than 44 px get invisible `::before` extensions (overlapping, never visible spacing). Captions (`.caption`): "sent to book", "saved to the row", the undo hint; `toast(text)` lasts 1.8 s.

## d · gestures on the sheet, and how the row stays out of the way

The engine owns the sheet: Pencil draws, one finger smudges, two fingers pan/zoom, two-finger tap = undo, three-finger tap = redo (the row has no redo mark; redo is gesture-only). The row must never start a stroke or eat one:

- every control calls `setPointerCapture` on `pointerdown` (tool words do, because the size slide travels far); the sheet never sees the gesture;
- `#ui` is `pointer-events: none`; only the controls (`.ctl`, `.tool`, `.colour`, `.pdot`, `#sessions .item`, `#params.on .param`) are `auto`. **Bug to avoid:** a hidden panel whose children are `pointer-events: auto` swallows strokes in its area. The parameter rows were doing this (an invisible strip above the row ate taps) until the rule became `#params.on .param`;
- extended targets are pseudo-elements of the control, so they capture too;
- `touch-action: none` on body and the sheet, `-webkit-user-select: none`, `-webkit-touch-callout: none`, `contextmenu` prevented (long-press), no `<input>` anywhere (Scribble), `viewport-fit=cover`, `100dvh`;
- the two-finger-tap-undo listener in `ui.js` is attached to `#sheet` for the prototype only; the engine replaces it.

## e · colours

`palette.json` is the single source:

```json
{ "quick": ["black", "rich-azure", "soft-deep-teal", "soft-deep-violet", "shaded-red"],
  "black": { "name": "Graphite black", "hex": "#2A2A2A" },
  "palettes": [ { "name": "Industrial Carbon and Azure", "colours": [ { "id": "rich-azure", "name": "Rich Azure", "hex": "#165C7D" }, … ×5 ] }, … ×4 ] }
```

`ui.js` fetches it (`cache: no-store`), resolves every id to a hex (`rascunhoUI.colours`), and builds the quick row from `quick` (black first) unless `localStorage rascunho.quick` holds five hexes. `style.css` keeps five `--c-quick-*` fallbacks used only if the fetch fails. Hexes are compared lowercase; `onColour` always sends a lowercase `#rrggbb`.

Full list: four columns (`.pcol`, 110 px) of five `.pdot` (44×40 targets, 17 px dots), palette order, name beneath in 11 px quiet type; rises centred over the dots (`#palette`, absolute, `bottom: 100%`), fades in 0.3 s; a tap picks and closes; a tap elsewhere closes. A pick that is not one of the quick five becomes the **chosen** sixth dot (`#chosen.has`) with the ring; picking a quick dot moves the ring and leaves the sixth in place. Reassign: with the list open, long-press a quick dot → that slot takes the current colour, the sixth disappears if it was that colour, `rascunho.quick` is written, `onQuickChange` fires. `setQuick([five ids or hexes])` does the same without the hook.

## f · brush size

Four steps per tool, `state.sizes[id] ∈ 0..3` = S, M, L, XL, default 1 (M), kept in `rascunho.sizes`. Slide on the word: sliding starts after 8 px of mostly vertical travel (a mostly horizontal move > 14 px cancels), one step per 24 px (`FAKE.sizeStepPx`), up = bigger, clamped; the hairline thickness follows live (`SIZE_LINE = [1, 2, 3.5, 5]` px, `--line` on the word, the line is as wide as the word); an inactive word becomes active when the slide starts; release commits once (`onSize(id, step)`). Double-tap (two taps within 320 ms) resets to 1. Suggested engine mapping: multiply the tool's preset size by **0.6 / 1 / 1.6 / 2.4**. The engine reads `rascunhoUI.sizes` at startup.

## g · paper grid

`#aid`, a fixed layer between the sheet and the row (z 2, `pointer-events: none`), driven by `body[data-grid="off|dots|lines"]`, pure CSS gradients. Step `--aid-step` 19 px = 5 mm at the iPad's 1366 px width (make it 5 mm for real if the engine knows the DPI); a stronger mark every 5th. Lines: `--aid-line-minor` 4 % ink, `--aid-line-major` 8 %, 1 px. Dots: `--aid-dot-minor` 12 %, `--aid-dot-major` 18 %, radius `--aid-dot-r` 0.9 px (≈ 1.75 px). The grid is screen-space only: it does not pan or zoom with the sheet and **must not be exported** (it is not part of the drawing). Hidden in the gallery.

## h · all sheets

`setSheets(list)` with `[{ id, date: 'YYYY-MM-DD', src? }]`, newest first (the server's `GET /sheets` gives `updated` and `thumb`; map `thumb` → `src`). Each sheet is a `<figure data-id>` with `.page` (4:3, `--paper-clean`, a 1 px edge at 7 % ink) holding `<img>` (shown when `src` is set, `object-fit: cover`) and a fake SVG doodle (shown only without `src`), and a `<figcaption>` "20 oct". Columns: 5 at ≥ 1300 px landscape, 4 otherwise, 3 in portrait; the gallery scrolls (`touch-action: pan-y`). Tap a sheet → `onOpenSheet(id)` and the UI returns to draw mode; the engine loads it. `+` in the gallery also returns to draw mode and fires `onNew()`. Dates are shown lowercase, day + month only.

## i · the send unit, end to end

The sentence `send to` (quiet) `book` (ink) `↗` (ink), one word space apart (`gap: .28em`, measured 3.5 px), at the row's right end after `--send-air`. Targets: words 67×56 and 53×56, arrow 49×56 via `::before` extensions.

- **name** tap → `#sessions` rises above the word (column-reverse, 40 px rows, staggered 50 ms) with the other names; tap one → `onSession(name)`, the word rewrites, the list fades. The engine fills the names with `setSessions(names, connected?)` from `GET /sessions` (`[{name, status, …}]`); refresh them when the list opens or on a timer.
- **send** (tap "send to" or `↗`) → `onSend(session)`; the UI enters *sending* (`#sendgroup.sending`: arrow 30 %, name 50 %) and ignores further taps until `setSent`. The engine does `POST /send` with the PNG body and `X-Session: <name>` (optionally `X-Note`, `X-Sheet`), reply `{ok, id, path, session, delivered, detail}` (see `../README.md` → Server; `client.js` wraps it as `api.send(blob, session, {note, sheet})`).
- **success** (`setSent(true)` when `ok && delivered`) → `↗` cross-fades (150 ms) into the **hamsa**, the OracleEars menu-bar icon (inline SVG, 16 px, ink, the eye cut out with an SVG mask so paper shows through, 1 px pupil), stays 2 s, cross-fades back; caption "sent to <name>" fades.
- **failure** (`setSent(false, detail)`: `ok: false`, `delivered: false`, network error) → the arrow stays, the caption shows `detail` (e.g. "ambiguous", "book is not running") or "not sent to <name>".
- The later `seen` event from `/events` can reuse `toast("book saw your drawing")`.

With no `onSend` handler bound, the prototype fakes success 400 ms after the tap.

## j · `window.rascunhoUI`

Callbacks (each returns an unsubscribe function; several listeners allowed):

```
onTool(fn)        fn(id)            id: '2h' | 'hb' | '4b' | 'eraser'         on tap / when a slide activates a word
onColour(fn)      fn(hex)           lowercase '#rrggbb'                        quick dot, chosen dot or full-list pick
onSize(fn)        fn(id, step)      step 0..3                                   on release of a slide, on double-tap reset
onUndo(fn)        fn()                                                           undo glyph, two-finger tap (prototype)
onNew(fn)         fn()                                                           after the 220 ms wash
onSend(fn)        fn(session)       the connected name                          tap on "send to" or ↗ (already in sending state)
onSession(fn)     fn(name)                                                      a name picked from the list
onOpenSheet(fn)   fn(id)                                                        a gallery sheet tapped (UI already back in draw mode)
onGrid(fn)        fn(mode)          'off' | 'dots' | 'lines'                   paper-grid glyph tapped
onQuickChange(fn) fn([hex×5])                                                   a quick slot reassigned
```

Setters (visual only, never fire hooks): `setSessions(names[], connected?)`, `setSheets([{id,date,src?}])`, `setSending(bool)`, `setSent(ok, detail?)`, `setQuick([×5])`, `setSize(id, step)`, `setGrid(mode)`, `setTool(id)`, `setColour(hexOrId)`, `setMode('draw'|'grid')`, `openColours()`, `closeColours()`, `toast(text)`.

Getters: `state` (`{mode, tool, colour, quick, chosen, sizes, grid, session, sessions, sheets, sending, params}`), `quick`, `sizes`, `colours` (id → hex).

Startup order for an engine: (1) bind every `onX`; (2) `api.sessions()` → `setSessions(names, localStorage rascunho.lastSession)`; (3) `api.sheets()` → `setSheets(...)`; (4) read `state.tool`, `state.colour`, `sizes`, `state.grid` and configure the brush; (5) the UI has already restored quick colours and sizes from `localStorage` by then (`loadPalette()` resolves within the first frame; wait for `document.readyState` or a microtask before step 4).

## k · merge recipe

- Keep `#sheet` as the engine's root: a full-screen, empty `<div id="sheet">` with `touch-action: none`; replace or fill it with the engine's canvases. Everything the UI uses sits above it: `#aid` (z 2), `#wash` (the new-sheet veil), `#ui` (z 10, controls), `#grid` (z 5, gallery), `#grain` (z 50). Keep that order; do not put canvases above `#aid`.
- Delete the engine's placeholder bar (the pill bar) and any of its own colour/size controls; keep its gesture code.
- Copy `style.css` whole (the variables at the top are the only numbers), `index.html`'s `<body>` markup, `ui.js`, `palette.json`. `send.html` and the screenshots are not needed at runtime.
- Binding, roughly:

```js
import { api, subscribe } from '../client.js';
const ui = window.rascunhoUI;
ui.onTool(id => brush.setTool(id, ui.sizes[id]));
ui.onSize((id, step) => brush.setSize(id, [0.6, 1, 1.6, 2.4][step]));
ui.onColour(hex => brush.setColour(hex));
ui.onUndo(() => history.undo());            // three-finger tap → history.redo() stays in the engine
ui.onNew(() => sheet.create());  ui.onOpenSheet(id => sheet.load(id));
ui.onGrid(mode => aid.set(mode));           // or leave #aid to CSS; never draw it into the export
ui.onSession(name => localStorage.setItem('rascunho.lastSession', name));
ui.onSend(async name => { try { const r = await api.send(await sheet.png(), name, { sheet: sheet.id }); ui.setSent(r.ok && r.delivered, r.detail); } catch (e) { ui.setSent(false, e.message); } });
api.sessions().then(s => ui.setSessions(s.map(x => x.name), localStorage.getItem('rascunho.lastSession')));
api.sheets().then(s => ui.setSheets(s.map(x => ({ id: x.id, date: x.updated.slice(0, 10), src: x.thumb }))));
```

## l · known limitations

- Touch-only behaviours were verified with synthetic pointer events, not fingers: long-press timing (420 ms), the slide's 8 px start threshold, double-tap at 320 ms, two-finger tap. Tune on the iPad.
- `setPointerCapture` is wrapped in try/catch (synthetic events have no active pointer); real pointers capture.
- The hardness / grain / smoothing hairlines are placeholders with fake values (`FAKE.params`); drop them if the engine has nothing to bind.
- The paper grid is 19 CSS px, not a true 5 mm; it does not follow pan/zoom.
- The session list shows names only; `status` from `/sessions` (idle / busy) is not shown yet.
- The gallery's fake doodles are seeded SVG scribbles and vanish once `src` is set; no delete / rename in the UI (the server has both).
- First paint suppresses transitions until `body.ready` (set after the palette loads) so a page opened with `#dots`/`#colours` does not fade in; keep that if hash states are kept.
- Hash states are prototype conveniences only: `#grid #params #sessions #hint #dots #lines #colours #sent`.
