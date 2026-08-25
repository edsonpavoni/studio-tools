# The Board tool — drawing the board itself

*Planned 2026-08-25 with Edson. Confidence: medium (software is low-risk, the
physics of organic cutouts is the open bet). Status: not started.*

## Why this exists

Today the circuit is drawn by hand but the board is a rectangle typed into
tscircuit. That is backwards for an art tool: the outline is the most visible,
most sculptural property of the object. V4 carries "the cave" in its copper but
sits inside a 60×40 box.

**End state:** in hand-route, a Board tool lets the Pencil draw the outline the
way it draws traces — or drop exact primitives when the sculpture needs a
measured fit — and place mount holes from a standards palette. Measurements are
visible and typable. The authored board saves into `board.handroute`, flows into
the same one-file laser job, and the same independent verifier refuses anything
unmanufacturable. The split becomes clean and permanent: **tscircuit is the
source of the circuit (components, nets, pads); hand-route is the source of the
board (outline, free holes, and all drawn copper).**

## What was checked before planning (Stage 0)

- **Downstream is already shape-agnostic.** `board_outline()` returns a point
  list; `lbrn.add_polygon` cuts any closed polyline; `--clear` computes copper
  removal against whatever outline it is given; the fit-test inherits the
  outline for free. Freeform outlines are cheap in software.
- **The risk is physical, and it is measured elsewhere.** Cutout is proven on
  10–30 mm squares and one 60×40 board; a long organic perimeter is a known
  unknown (BACKLOG "long perimeters"). The web of FR4 between a hole and the
  board edge has never been measured. Both become coupons in Phase 5.
- **A laser has no tool radius.** Unlike a mill, inner corners and tight
  concavities cost nothing. The real geometric limits are acute slivers (fragile
  FR4) and total perimeter length (heat + the pass-6 release).
- **Alternatives considered.** Typing outlines into tscircuit (rejected: that is
  coordinates in code, not drawing). Importing SVG from Illustrator (deferred to
  Phase 6 as an import, not the flow — the iPad is the flow).
- **Absorbed:** old backlog item "UI: hole placement" folds into Phase 3.

## Decisions (made 2026-08-25, revisit only with Edson)

1. **The authored board lives in `board.handroute`** as a `board` section:
   `{outline: [[x,y]…], holes: [{x,y,d}]}`. When present it OVERRIDES the
   circuit.json board and `pcb_hole` set, applied in `netmap.py` exactly like
   component moves, so UI, converter and verifier see one geometry.
2. **Move stays; Board is a new tool.** [Edson proposed maybe replacing the
   move icon. Recommendation: keep both — moving components is how a drawn
   outline gets its parts arranged. If island 1 feels crowded, Board can live
   left of the pen.]
3. **While the Board tool is active, copper fades** to a faint ghost: the canvas
   shows board, board holes and component holes — the filter Edson asked for,
   done by context instead of another global view.
4. **Freeform closes itself.** An outline stroke snaps end-to-start and runs the
   same RDP + Chaikin smoothing as traces. Primitives (rect, circle, stadium)
   take typed dimensions. One outline at a time; drawing a new one replaces the
   old (undoable).
5. **The verifier stays the trust anchor.** New refusals, all in `verify.py` so
   the converter enforces them independently of the UI.

## Phases

**P1 — plumbing.** `board` section round-trips `.handroute`; `netmap` applies
it; converter cuts it; verifier gains: outline closed + simple (no
self-intersection), every pad inside with ≥0.5 mm margin.
*Gate:* a hand-edited `.handroute` with a triangle outline yields a `.lbrn2`
whose CUTOUT is that triangle; a pad outside the outline refuses the build.

**P2 — drawing the outline.** Board tool + sub-island (outline pen / rect /
circle). Live W×H readout while drawing. Undo. Copper fades in board mode.
*Gate:* an organic outline drawn on the iPad autosaves, converts, and verifies;
the fit-test file carries the same shape.

**P3 — holes.** Palette: M2 / M2.5 / M3 (bite + clearance, from The Source
`pcb-v3/PARTS.md`) + custom Ø. Place, drag, delete. Verifier gains: hole vs
copper clearance ≥ floor, hole vs edge web ≥ 1.0 mm (assumption — see below),
unproven diameters warn like they already do.
*Gate:* verifier refuses a hole 0.2 mm from a trace and accepts a legal one;
hole kerf compensation applies to authored holes identically.

**P4 — measurements.** Typed exact sizes and positions (tap a dimension to
edit), optional 0.5 mm grid snap, two-point measure.
*Gate:* a rect requested 60×40 lands 60.00×40.00 in the `.lbrn2`.

**P5 — physical proof (bench day).** One coupon: organic perimeter ≥150 mm +
edge-web ladder (0.6/0.8/1.0/1.5 mm webs). Then cut one real Pencil-drawn board.
*Gate:* the freeform board releases clean on the proven cutout recipe, webs
intact. Results go to `MATERIAL-QIMOO-FR4.md`.

**P6 — polish.** 3D view extrudes the real outline (today: bbox slab). Warnings
for acute slivers. Maybe SVG outline import.

## Assumptions

- **1.0 mm edge web is safe** → VALIDATE BY: P5 ladder → IF WRONG: raise the
  verifier floor; layouts get roomier, nothing breaks.
- **The proven cutout recipe (100%/6 passes) holds on long organic perimeters**
  → VALIDATE BY: P5 coupon → IF WRONG: more passes / pauses; worst case the
  FAILED condition below.
- **Autosave-every-change is safe for outline edits too** → VALIDATE BY: P2 use;
  history snapshots already cap at one per minute.

## FAILED conditions

- Freeform cutouts still char or warp after two coupon iterations → the Board
  tool ships primitives-with-fillets only, and freeform waits for a recipe.
- P1+P2 not landed after two bench-adjacent software days → stop, re-scope with
  Edson; the tool must stay lean.

## Verification

Automated: the P1/P3 refusal cases become permanent test fixtures (a
known-bad `.handroute` per rule, converter must exit non-zero). Manual: LightBurn
preview eyeballed before any cut (existing preflight). Physical: P5 coupon +
first real board, scored in the material log.
