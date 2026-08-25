# hand-route

*(named PCB-Maker until 2026-08-25; same tool, same recipe)*

Make circuit boards on the ComMarker B6 MOPA, in the studio, the same way twice.

The point is not that it is cheaper than JLCPCB. The point is that a board can ship **inside a sculpture** on the studio's own schedule, and that the laser settings live in a file instead of in someone's memory. The Source lost its JLC order to a shipping date in August 2026; a board that can be made on a Tuesday does not have that failure mode.

**Status v0.1 (2026-08-24): PROVEN END TO END.** tscircuit source → iPad hand-routed
artwork → one laser file → a working board. V4 (The Source P1b, 60×40, 56 holes,
15 nets, 324 hand strokes) cut, continuity-verified, and populated. The recipe is
measured, not remembered: every number in `B6-PCB-RECIPE.md` came off a coupon, and
the converter's defaults produce it automatically.

The pipeline, in one line:

```
tsci build → hand-route UI (iPad+Pencil over a ghost autoroute) → circuit2lbrn.py → LightBurn → B6
```

The autorouter's spacing is not cuttable on this process, so traces are drawn by hand:
**`server.py`** serves the board to the iPad, checks connections live, and an
independent verifier refuses incomplete or shorted drawings. The drawing saves as a
**`.handroute`** file (strokes + component moves) next to the board's circuit.json.
The result is a board that is also a drawing — V4 carries "the cave" written into
the copper.

**Open work lives in `BACKLOG.md`. Build history lives in `PLAN.md`.**

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
| `PLAN.md` | The build phases and everything they taught. |
| `reference/ToR_008-*` | The last working LightBurn and drill files from the TRIBE board, May 2025. **Frozen. Do not edit.** |

---

## Running it

```bash
# a real board, from tscircuit source
cd your-board-project
tsci build                                    # writes dist/<name>/circuit.json
python3 /path/to/hand-route/circuit2lbrn.py \
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

```bash
cd tools/hand-route
python3 server.py /path/to/board/dist/index/circuit.json
```

Open the printed URL in Safari on the iPad (same WiFi). Then:

The chrome is Figma-flavoured (2026-08-25): four floating icon islands at the
bottom of the canvas, deep green accent, no labels.

| island | holds |
|---|---|
| 1 | undo |
| 2 | pen (chevron beside it opens the size popover), smoothness (vertical slider), eraser, move a component |
| 3 | **the three views**: board · draw · 3D |
| 4 | overlays: copper, ghost autoroute |

**The right panel belongs to the view.** Draw view shows the connections —
status lines, net checklist, alerts. Board view shows the board's own
properties. 3D keeps the component legend on the canvas. The icon at the panel's
top hides it; a floating button brings it back. A millimetre grid sits under
everything (1 mm and 10 mm, each fading in when it becomes legible).

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
components, nets, pads. hand-route is the source of the board — outline, free
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

ComMarker B6 MOPA 60 W, driven by LightBurn 1.7.08, device name `B6 Mopa`. General material settings for engraving and cutting metal live in `projects/B6 Mopa Laser/material-settings.md`. **Those are for solid copper, brass and aluminium sheet.** PCB foil is 35 µm on FR4 and wants a different recipe, which is why it has its own file here.
