# PCB-Maker

Make circuit boards on the ComMarker B6 MOPA, in the studio, the same way twice.

The point is not that it is cheaper than JLCPCB. The point is that a board can ship **inside a sculpture** on the studio's own schedule, and that the laser settings live in a file instead of in someone's memory. The Source lost its JLC order to a shipping date in August 2026; a board that can be made on a Tuesday does not have that failure mode.

**Status v0.1 (2026-08-24): PROVEN END TO END.** tscircuit source → iPad hand-routed
artwork → one laser file → a working board. V4 (The Source P1b, 60×40, 56 holes,
15 nets, 324 hand strokes) cut, continuity-verified, and populated. The recipe is
measured, not remembered: every number in `B6-PCB-RECIPE.md` came off a coupon, and
the converter's defaults produce it automatically.

The pipeline, in one line:

```
tsci build → handroute (iPad+Pencil over a ghost autoroute) → circuit2lbrn.py → LightBurn → B6
```

The autorouter's spacing is not cuttable on this process, so traces are drawn by hand:
**`handroute/`** serves the board to the iPad, checks connections live, and an
independent verifier refuses incomplete or shorted drawings. The result is a board
that is also a drawing — V4 carries "the cave" written into the copper.

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
| `handroute/` | The iPad hand-routing server: ghost autoroute, live connection checklist, independent verifier. See its README. |
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
python3 /path/to/PCB-Maker/circuit2lbrn.py \
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
