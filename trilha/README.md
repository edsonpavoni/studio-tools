# trilha

*(named PCB-Maker until 2026-08-25 and hand-route until 2026-10-20; same tool, same recipe. A* trilha *is what a PCB trace is called in Brazilian Portuguese, and a trail.)*

Make circuit boards on the ComMarker B6 MOPA, in the studio, the same way twice.

The point is not that it is cheaper than JLCPCB. The point is that a board can ship **inside a sculpture** on the studio's own schedule, and that the laser settings live in a file instead of in someone's memory. The Source lost its JLC order to a shipping date in August 2026; a board that can be made on a Tuesday does not have that failure mode.

**Status v0.1 (2026-08-24): PROVEN END TO END.** tscircuit source → iPad hand-routed
artwork → one laser file → a working board. V4 (The Source P1b, 60×40, 56 holes,
15 nets, 324 hand strokes) cut, continuity-verified, and populated. The recipe is
measured, not remembered: every number in `B6-PCB-RECIPE.md` came off a coupon, and
the converter's defaults produce it automatically.

The pipeline, in one line:

```
tsci build → trilha UI (iPad+Pencil over a ghost autoroute) → circuit2lbrn.py → LightBurn → B6
```

The autorouter's spacing is not cuttable on this process, so traces are drawn by hand:
**`server.py`** serves the board to the iPad, checks connections live, and an
independent verifier refuses incomplete or shorted drawings. The drawing saves as a
**`.handroute`** file (strokes + component moves) next to the board's circuit.json.
The result is a board that is also a drawing — V4 carries "the cave" written into
the copper.

**Open work lives in `BACKLOG.md`. Build history lives in `PLAN.md`. Where a
board's files live, and what Claude does when asked to open or start one, is
`FILES.md`.**

---

## What is here

| File | What it is |
|---|---|
| `B6-PCB-RECIPE.md` | **The settings.** Five laser layers, run order, powers, speeds, pass counts, the dialed hole cell (70%/8 passes/kerf 0.24), and how each number was measured. |
| `MATERIAL-QIMOO-FR4.md` | **The material log.** What Qimoo 1.6 mm FR4 does on the B6: proven settings, capability floors, recorded failures, open questions. Append every new bench result here. |
| `circuit2lbrn.py` | **The main converter.** tscircuit `circuit.json` in, one laser-ready `.lbrn2` out, preflight checks included. `--fit-test` makes the cardboard fit-check file. |
| `lbrn.py` | Writes `.lbrn2` files and carries the recipe as layer defaults. Pure standard library, no installs. Format reverse-engineered from the reference file. |
| `negative.py` | Computes the copper-clear region: rasterise copper, grow by the kerf pullback, subtract from the board, march the boundary back out to polygons. Rebuilds its own fill to catch structural mismatch. |
| `server.py` + `ui.html` | The iPad drawing app: ghost autoroute, live connection checklist, net focus, component moves. See **Drawing on the iPad** below. |
| `netmap.py` / `verify.py` | Pads + netlist out of circuit.json, and the independent checker the converter runs. Shared by UI and converter: one source of truth. |
| `gerber2lbrn.py` | The Gerber route, for boards that come from Flux or KiCad instead. |
| `make_holes5.py` / `make_mount_coupon.py` / `make_width_coupon.py` | The live coupon generators: the dialed hole cell, mount sizes + cutout squares, and the unrun 0.2 mm width proof. |
| `coupon/` | Generated coupons and their filled score sheets — the measurement record. |
| `archive/` | Superseded coupon generators, one line each in its README on what they answered. |
| `BACKLOG.md` | **What to do next**, ordered by value. |
| `PROBLEMS.md` | **What went wrong in the field**, symptoms only, no solutions — the raw material the backlog gets polished from. Started on The Source P2 build, 2026-08-27. |
| `PLAN.md` | The build phases and everything they taught. |
| `reference/ToR_008-*` | The last working LightBurn and drill files from the TRIBE board, May 2025. **Frozen. Do not edit.** |

---

## Running it

```bash
# a real board, from tscircuit source
cd your-board-project
tsci build                                    # writes dist/<name>/circuit.json
python3 /path/to/trilha/circuit2lbrn.py \
        dist/index/circuit.json --clear --manual-traces auto \
        -o board.lbrn2
# defaults already carry the measured recipe: 200 ns, 0.05 mm interval,
# holes at 70%/8 passes with 0.24 kerf compensation, cutout 100%/6.
```

Before cutting, the preflight (amended after V3, in `B6-PCB-RECIPE.md`): dimensions
have sources (see the project's PARTS.md pattern) → cardboard `--fit-test` on any new
layout → eyes on the file in LightBurn → board off the bed, air ON → **stand at the
machine for the cutout** (it releases on pass 6 with nothing to spare).

**That is one file with every pass in it**: holes first, copper clearing, board cutout
last, in the run order recovered from the 2025 board. Open it in LightBurn and press go.

For boards that came from Flux or KiCad rather than tscircuit, `gerber2lbrn.py` takes
the Gerber set instead and uses pcb2gcode for the isolation geometry.

---

## Drawing on the iPad

The autorouter connects things; it does not compose them. This replaces it with your
hand: the board's pads and netlist load into a canvas, you draw each connection with
the Apple Pencil, and a live checklist ticks nets off as they complete. The routing
becomes part of the object, the way the 2025 TRIBE board's big sweeping curve was.

The server is always on (`studio/ipad` runs it on **port 8481** from login; the
iPad icon **Trilha** → http://edsons-macbook-pro.local:8481). It serves the
board named in `current-board` beside this script. To switch boards, from any
session or terminal:

```bash
python3 "/Users/edsonpavoni/Library/CloudStorage/Dropbox/0000 AI/studio/trilha/server.py" /path/to/board/dist/index/circuit.json
```

That writes the pointer, adds the board to `recent-boards.json`, and the running
server shows it on the iPad's next load (no restart; a `tsci build` is picked up the
same way). With no board set, the page lists the recent boards to tap. Without a
running server the same command serves the board itself (`--port` to choose). Then:

The chrome is Figma-flavoured (2026-08-25): four floating icon islands at the
bottom of the canvas, deep green accent, no labels.

| island | holds |
|---|---|
| 1 | undo |
| 2 | pen (chevron beside it opens the size popover), smoothness (vertical slider), eraser, move a component |
| 3 | **the four views**: board · draw · schematic · 3D |
| 4 | overlays: copper, ghost autoroute |

**The right panel belongs to the view.** Draw view shows the connections —
status lines, net checklist, alerts. Board view shows the board's own
properties. Schematic keeps the connections panel, since that is what it is
reading out. 3D keeps the component legend on the canvas. The icon at the
panel's top left hides it; a floating button brings it back. Bottom right of
the canvas: fit the board to the screen, and the grid toggle. A millimetre grid
sits under everything (1 mm and 10 mm, each fading in when it becomes legible).

### Schematic view: the printable legend

The artwork for the face of the board that carries **no copper**. A drawing
sheet with the blank on it: footprints, port numbers, net names, a square
shoulder on pin 1, ⌀ on every mount hole, and + / − on the electrolytic taken
from the netlist rather than typed. It reads `/board` and edits nothing — the
pen pans instead of drawing.

**Bottom left, only in this view, is the flip.** It mirrors *positions* about
the board's centre line and nothing else: every glyph stays upright, because a
silkscreen whose numbers come out backwards is one you cannot print. The tag
beside the button says which face you are reading — `COPPER SIDE · as routed`
or `COMPONENT SIDE · mirrored`. Leaving the view resets it to copper side.

**`signals.json` — what each net actually carries.** `NET_3` tells you nothing
standing at a bench; `SDA` tells you everything. Drop a `signals.json` beside the
board's `circuit.json`, or in the project directory above it, and the view prints
the real names:

```json
{ "nets": { "NET_3": "SDA", "GND": "GND", "NET_1": "D+" },
  "pins": { "QA.pin1": "S", "QA.pin2": "D", "QA.pin3": "G" } }
```

`nets` maps a net id to what it carries; `pins` gives a part-level pin *function*
where the net name does not carry it — G/D/S on a MOSFET being the case that
matters, since a TO-220's physical lead order and a footprint's pin numbering
need not agree. Both are optional; anything missing falls back to the raw net id,
which is at least always true. **It is deliberately data and not names typed into
the renderer: a silkscreen label that has drifted from the netlist is worse than
no label.** The server re-reads it on every `/board`, so edit the file and refresh
the page — no restart. Cross-check with `python3 netmap.py <circuit.json>`.

Net names on a 2.54 row stand up and read along the pin: at that pitch there is
no width for them to lie down in. The sheet has a margin, and a deeper foot for
the title block, because the outermost parts sit 5 mm from the board edge and
their names need somewhere to land.

### The burn session

The green fire button at the panel's top right opens it: everything you need in
the minute before the laser runs. What this board **is** — outline size, shape,
material, hole count and diameters, drawn traces and total copper length, widths
used, and the live state of nets, shorts, gaps and board issues. The **measured
recipe** that will cut it. Then the files:

| export | what it is |
|---|---|
| **LightBurn job** | every layer, ready to cut |
| **Cardboard fit test** | cut this first on any new layout |
| **.handroute** | the drawing itself — strokes, moves, board |

Files are built by the converter on the spot and land in your Downloads, named
after the project rather than `index`. **A refusal is the answer, not an error:**
if the board is incomplete, shorted or unmanufacturable, nothing is written, the
reason is stated in the panel and in the toast, and the converter's whole log
follows underneath. Any unsaved change is flushed before the file is built, so
what you download is what is on screen.

**How the copper comes off** is chosen above the export buttons, because it
changes what the LightBurn job does:

- **Copper full clear** (default) — every piece of copper that is not a trace or
  a pad is removed. What V4 and V5 were cut with.
- **Minimal isolation clear** — only a 0.5 mm ring around each trace and pad;
  the rest stays as a ground plane. Far less laser time, but that copper is
  electrically connected and GND stops being a net you draw, so the board has to
  be designed for it.

There is no save button: every change autosaves 2 s after the pen lifts (with a
15 s retry heartbeat and a flush when the page hides); only a failure announces
itself.

| gesture | does |
|---|---|
| Pencil (pen tool) | draw a trace |
| one finger drag | pan |
| pinch | zoom |
| Pencil (eraser tool) | delete traces (slide to erase many) |
| Pencil drag (move tool) | reposition a component, pads and all |
| Pencil (board view) | draw the board's outline, place holes, drag a hole |
| tap a net in the checklist | focus it — everything else greys; tap again to release |
| ⌘Z / Ctrl+Z | undo, in any view — traces, component moves, outlines, holes |

### Board view: the object

Switch to **board view** and the canvas shows the object — outline, its holes,
and the component holes as bare drills. Copper recedes to a whisper: it is not
what you are working on. The side panel becomes the board's inspector:

- **Shape** — freehand, rectangle, circle, and a 0.5 mm snap toggle.
- **Size / Position** — the real numbers, typed. Width and height scale the
  shape about its centre; X and Y move it under the parts. Committed on Enter
  or blur, never mid-keystroke.
- **Holes** — the M2/M2.5/M3 standards (clearance and bite) in a picker, a list
  of every hole, and an inspector for the selected one with exact X, Y and Ø.
- Board problems are listed underneath; tap one to fly to it.

**Touching a hole always picks it up**, whatever shape tool is selected —
nudging holes is the commonest thing you do here, and the numbers count up in
the inspector as your hand moves. Selecting a hole and choosing a size from the
picker resizes it.

A freehand outline closes itself: the tool welds the ends and keeps a consistent
winding, so the cutout polygon never depends on which way your hand travelled.
Live width × height shows while you draw.

**This is the split that matters: tscircuit is the source of the circuit —
components, nets, pads. trilha is the source of the board — outline, free
holes, and all drawn copper.** An authored board lives in the `board` section of
`board.handroute` and overrides circuit.json's outline and free holes;
component holes are never touched, because those belong to footprints.

The board is checked as an object, live in the panel and again in `verify.py`
before any laser file is written: the outline may not cross itself, every pad
and trace must sit inside it with 0.5 mm to spare, and a hole must leave a
1.0 mm web to the rim (⚠️ that web is an **assumption** until the PLAN-BOARD
Phase 5 coupon measures where it actually tears — `--edge-web` overrides it).
Moving a shape never moves what is on it: the warnings tell you what is now
wrong, and fixing it by hand is the honest fix.

Stroke ends **snap to pads** within ~1 mm, and to existing traces for junctions.
Strokes are simplified and smoothed (RDP + Chaikin) so the line stays organic without
the jitter. Width buttons set the trace width for the next stroke.

**Focus** exists for the moment that matters: pick the net you are routing and see
only its pads, its ghost, and its copper in colour. Shorts stay red even in focus —
a short is never allowed to hide.

**Move** drags a whole component (its outline shows as a handle; orange = moved,
with the offset in mm). No auto rerouting, on purpose: strokes never move with the
part, the checklist unticks by itself when a pad leaves its drawn copper, and
redrawing the connection is the honest fix. Drag a part back over its design
position to zero the move.

**The checklist** shows every net. A net ticks green when all its pads are connected
through drawn copper. A stroke that bridges two different nets turns red and raises
a SHORT alert. A stroke that passes closer than **0.171 mm** to foreign copper gets
an orange halo and a gap warning.

The faint dashed lines are the autoroute, as a reference of what connects to what;
the Ghost button hides them, and a completed net's ghost disappears on its own.
Everything saves to **`board.handroute`** next to the circuit.json — strokes and
component moves in one JSON file — with a timestamped snapshot in
`handroute-history/` at most once a minute. (Boards drawn before 2026-08-25 had a
`traces.json`; it is read as a fallback and migrates to `.handroute` on the first
save.)

**The UI is not trusted.** The converter re-verifies the saved file independently
(`verify.py`): every net complete, no two nets bridged, no gap under `--floor`
(default 0.171 mm, the proven value), with any component moves applied identically
on both sides. It refuses to write a laser file otherwise. Two constants were tuned
the hard way and matter:

- contact tolerance is **0.08 mm** — it must be *below* the minimum clearance, or a
  trace passing legally close to a foreign pad reads as touching it
- hand-drawn widths are **never widened** by `--min-trace`; the verifier validated
  the drawn geometry and widening afterwards would invalidate it

### Why tscircuit rather than Gerber

`circuit.json` carries the board outline, every hole with its real diameter, every pad
and every routed trace in **one millimetre coordinate system centred on the board**. So
holes are exact rather than re-derived, the outline is a real polygon rather than
stitched from Gerber segments, and **there is no registration step at all**, because
nothing was ever in separate files.

### The negative

The one thing `circuit.json` does not hand you is where copper has to be *removed*.
`--clear` computes it: paint every pad and trace into a boolean raster, grow by the kerf
pullback, subtract from the board, then march the boundary back out to polygons and
simplify. Copper islands come out as their own loops, so LightBurn's even-odd fill
leaves them standing.

### Trace width

`--min-trace` (default **0.8 mm**) is a floor: any trace the router drew narrower gets
widened to it. A laser board has no plating and the kerf eats the edges, so fab-house
widths are too thin. For reference, the 2025 TRIBE board's Gerber has exactly one
stroked aperture, **0.508 mm (20 mil)**, and everything else is region fill.

`--trace-width` forces every trace to one width, ignoring the router. `--min-trace 0`
keeps the router's widths untouched.

⚠️ **tscircuit's autorouter drew 0.15 mm on the test board.** Whatever the router picks,
check it. The tool prints the router's widths and says how many it widened.

### The short check

Widening traces and pulling the clear region back both make copper grow, and growing
copper is how two nets become one. So the tool counts **connected copper regions** in
the design and requires that number to survive both operations.

It counts components, not boundary loops. Those are not the same thing and using loops
was wrong: one region with a hole in it has two loops, and two nested regions have two
loops as well. The failure message names which operation did the damage:

```
FAIL copper that is separate in the design gets fused: widening to 0.80 mm
     (6 regions -> 4) and the 0.05 mm pullback (4 -> 3). The finished board
     would be shorted.
```

**A 0.8 mm floor needs room.** On a tightly packed board it will short things and the
tool will refuse. The fix is to spread the placement, not to lower the floor.

⚠️ **`--pullback` is kerf compensation, not design clearance.** Copper survives that much
wider than drawn, so a large value fuses nearby traces into a short that looks
deliberate on the finished board. Default is 0.05 mm. The tool counts copper boundary
loops before and after the pullback and **fails the run if the count drops**, which is
what catches a fused pair before it reaches the laser.

### What it checks before you cut

Every hole inside the board outline · no duplicate holes · holes too small for a laser
the coupon has not yet qualified · multi-layer boards, which this single-sided process
cannot make · circuits with no routed traces · the fraction of board actually cleared ·
and the pullback merge check above.

**Registration is solved, not guessed.** The drill file and the SVG do not share an
origin, so the tool finds the offset by minimising the distance from every drill hole
to the nearest piece of copper. A pad is a ring around its hole, so at the right offset
that distance collapses to about the pad radius. On the 2025 board it lands at
**0.270 mm** and the naive bounding-box fit lands at 0.853 mm, which is how you can
tell the minimum is real. Above 0.45 mm the tool warns; above 0.9 mm it fails and tells
you to pass `--iso-offset` yourself.

---

## The pipeline

```
components decided
   ↓  design in Flux / KiCad / tscircuit
Gerber set:  TopCopper.gbr · edge_cuts.gbr · drill.drl
   ↓  pcb2gcode  (installed: /opt/homebrew/bin/pcb2gcode)
isolation geometry as SVG
   ↓  this tool  (Phase 2, not built yet)
one .lbrn2 — five layers, settings already applied
   ↓  LightBurn
B6 MOPA
```

**Input is a Gerber set, not a perfboard drawing.** A hole-grid layout like `board-v3-wiring-plan.html` has no copper geometry in it, so a board has to be drawn in a PCB editor before it can come through here. Going the other way, from a netlist to copper, means writing an autorouter, and the front-end tools already do that well.

---

## Before you run a board

**Run the test coupon first.** Two parameters in the recovered recipe are genuinely missing from the 2025 file, and one of them, pulse width, is the parameter that decides whether 1064 nm couples into copper at all. There is also an open question about whether hole circles are stored as radius or diameter, which is a 2× error waiting to happen. The coupon in `PLAN.md` Phase 1 settles all of it in one run on scrap.

Until that coupon exists, treat `B6-PCB-RECIPE.md` as **an archive of what worked once**, not as a recipe you can replay blind.

---

## What this does not do

- No autorouting. Copper geometry comes in from a real PCB editor.
- No double-sided boards. The 2025 board was single-sided top copper, and vias would need through-plating this shop does not have.
- No solder mask, no silkscreen ink. Text is laser-marked into the copper, which is how the TRIBE mark and the credit line were done.
- No fine-pitch SMD until the coupon says what the minimum reliable gap actually is.

---

## Machine

ComMarker B6 MOPA 60 W, driven by LightBurn 1.7.08, device name `B6 Mopa`. General material settings for engraving and cutting metal live in `tools/B6-Mopa/MATERIAL-SETTINGS.md`. **Those are for solid copper, brass and aluminium sheet.** PCB foil is 35 µm on FR4 and wants a different recipe, which is why it has its own file here.
