# PCB-Maker — build plan (history)

> **This file is the build history. The live to-do list is `BACKLOG.md`.**
> Superseded coupon generators moved to `archive/` (2026-08-24 cleanup).

**Goal:** from *components decided* to *a file the B6 can run*, repeatably, with the laser settings versioned instead of remembered.

**Written 2026-08-17, updated the same evening.** Phases 0, 1 and 2 are built and tested against the 2025 board data. Phase 3 folded into the converter. **The only thing left is running the coupon on the laser**, which needs the machine and a piece of FR4 scrap.

---

## The input contract, stated plainly

**Primary input is tscircuit `circuit.json`. Gerber is the secondary route. Neither is a perfboard drawing.**

`board-v3-wiring-plan.html` is a placement plan on a 14 × 20 hole grid. There is no netlist a fabricator reads, no copper geometry, no board outline in machine form. To put V3 through this tool it has to be **redrawn in a PCB editor first** (Flux, KiCad, or tscircuit, all three of which are already in use here).

That is not a limitation worth engineering around. Turning a netlist into copper artwork is writing an autorouter, and the front-end tools already do it well. Keeping the input at Gerber also means the tool never cares which editor was used.

**Input, preferred:** `dist/<name>/circuit.json` from `tsci build`
**Input, alternative:** `TopCopper.gbr` · `edge_cuts.gbr` · `drill.drl`
**Output:** one `.lbrn2`, five layers, settings already applied, ready to open and run.

The tscircuit route turned out to be strictly better and it is now the main path. See
the README for why: one coordinate system, exact holes, no registration step.

---

## Phase 0 — Settings archive ✅ DONE 2026-08-17

Recovered from `ToR_008.lbrn2` rather than from memory. Five layers, run order, powers, speeds, frequency, pass counts, and the full drill-diameter mapping. Two parameters found missing and recorded as unknown rather than guessed. Reference files frozen in `reference/`.

→ `B6-PCB-RECIPE.md`

---

## Phase 1 — The test coupon ✅ GENERATOR BUILT 2026-08-17, not yet run on the laser

A small FR4 board whose only job is to answer the open questions. **Nothing else in this plan is trustworthy until this runs.**

**What goes on it:**
- Trace and gap pairs at **0.20 / 0.25 / 0.30 / 0.40 / 0.50 mm**, so the minimum reliable isolation width is measured rather than assumed
- One hole of each drill size in the archive: 0.6, 0.9, 1.0, 1.3, 2.4, 6.6 mm — **this is what settles the radius-versus-diameter question**
- A 10 × 10 mm cleared field, to time the raster fill and see whether the copper actually leaves
- Three identical strips run at **200 / 350 / 500 ns** pulse width, everything else held constant
- Half the coupon scuffed matte with maroon Scotch-Brite, half left bright, to measure how much surface prep matters

**What it answers:** pulse width, line interval, minimum trace and gap, hole size truth, whether to scuff, and how long a real board takes.

`python3 make_coupon.py` writes `coupon/B6-PCB-COUPON.lbrn2` (78 × 58 mm) and a score sheet. Three blocks, one per pulse width, identical geometry, plus 18 holes covering every drill size on the 2025 board.

**Gate:** a continuity check across every moat, and a caliper on every hole. Write the measured values into `B6-PCB-RECIPE.md` with the date.

---

## Phase 2 — The converter ✅ BUILT AND TESTED 2026-08-17

A single script: Gerber set in, `.lbrn2` out.

Built as `gerber2lbrn.py`. Tested end to end on the real ToR_008 export: 59 holes across 6 diameters, a 100 × 70 mm outline, 74 isolation polylines, in 0.8 s.

Registration turned out to be the interesting problem. The drill file and pcb2gcode's SVG do not share an origin, and nothing in either file records the offset. Fitting bounding boxes gets it wrong, because the copper extends past the holes. **The solve: minimise the mean distance from every drill hole to the nearest copper vertex.** A pad is a ring around its hole, so the correct offset is a sharp minimum. On the 2025 board the bounding-box fit gives 0.853 mm and the solve gives **0.270 mm**, and that gap is what proves the minimum is real rather than a shrug.

One development note worth keeping: a grid-hash nearest-neighbour index was tried for speed and quietly returned a worse optimum (0.648 mm). It was replaced with an exact vectorised search, which runs in under a second anyway. **An approximate index is a bad trade when the number it produces is the one you are trusting.**

Deliberately not doing: writing a Gerber parser, writing an isolation router, or improving on the 2025 layer order. `pcb2gcode` is installed and did this exact job.

---

## Phase 3 — The check ✅ FOLDED INTO THE CONVERTER

The same discipline the V3 perfboard got: a script that reads the generated `.lbrn2` back and verifies it before it reaches the laser.

- Every hole in the `.drl` has exactly one circle, right size, right layer
- All five layers present, correct priorities, correct powers and speeds
- Board outline is one closed path on the cutout layer
- Nothing sits outside the board outline
- Minimum isolation gap is not below the Phase 1 measured floor

Then the number that matters: **a continuity test between every pair of nets on the finished board, before a single component is soldered.**

---

## Phase 4 — The tscircuit route ✅ BUILT AND PROVEN 2026-08-17

`circuit2lbrn.py` + `negative.py`. Proven end to end on a real single-layer routed board
built with `tsci build`: 6 holes, 4 traces, 10 pads, board outline, copper negative,
all five layers, 0.13 s, every check green.

The negative is computed on a raster rather than with a polygon clipper, because trace
outlines self-intersect and a clipper that is subtly wrong produces a board that looks
right. Marching squares brings the boundary back out to polygons.

**A real bug was caught here during the build and is worth remembering.** The first
version applied a 0.3 mm dilation and called it "clearance". That is backwards: the
clear region is everything *outside* the dilated copper, so every trace survives 0.3 mm
wider than drawn and any two traces under 0.6 mm apart fuse into a short. Renamed to
`pullback`, defaulted to 0.05 mm, and the tool now counts copper boundary loops before
and after and fails the run if any two merged.

---

## What is left

**Run the coupon.** That is the whole remaining list. It needs the B6, a piece of FR4 scrap, twenty minutes, and a multimeter. Everything downstream is already written and waiting for the two numbers it produces.

Until that happens, treat the recipe as an archive of what worked once rather than something you can replay blind, and do not commit a board that matters to it.

---

## Phase 5 — Coupons run, hand-routing built, FIRST REAL BOARD CUT ✅ 2026-08-18 → 2026-08-23

Everything "left" above happened, and then some. Six coupon runs produced the measured
recipe now in `B6-PCB-RECIPE.md` (75%/1500 fill, 400 mm/s holes with wobble,
interleaved checkerboarding, labels on a feather layer). The tscircuit autorouter's
hardcoded 0.100 mm clearance forced the build of `handroute/`: iPad+Pencil drawing
over a ghost autoroute, live connection checking, and an independent verifier that
refuses incomplete or shorted boards. Edson drew the whole board as artwork.

**V3, the first real board (60×40, 56 holes, 324 hand strokes, 72% cleared), was cut
2026-08-23.** Full first-article review in
`projects/the-source-burning-man-2026/pcb-v3/LOG.md`. Score for the tool:

- Fill recipe, interleaved holes, labels layer: all behaved exactly as measured.
- **0.3 mm drawn traces proven conductive** (7.4 mm runs). UI floor updated.
- Two board-killing bugs were caught by EYES IN LIGHTBURN, not by the checkers:
  the interval leak (argparse None → device default 0.1) and the contour stitcher's
  float-key collisions that silently dropped 94/147 fill loops. Both fixed; the
  converter now rebuilds the even-odd fill from its own output polygons and refuses
  to build on structural mismatch (`negative.fill_check`). Lesson encoded: never
  key floats when you can key integers, and verify the FILE, not just the mask.
- First-article corrections to defaults: HOLES 16→12, CUTOUT 8→6 (attend it),
  --hole-kerf 0.15. `make_holes2.py` → `coupon/B6-HOLES2-COUPON.lbrn2` measures the
  final numbers.
- New failure class discovered: typed footprint dimensions (XIAO rows 10 mm vs real
  15.24). No software check can catch it, so the tool grew `--fit-test`: cardboard
  holes+outline+labels to push real parts through before FR4. Dimension provenance
  registry pattern: `PARTS.md` in the project folder.

## Phase 6 — Holes DIALED IN ✅ 2026-08-24 (coupon ladder HOLES-2→5 + MOUNT)

One morning, five coupons, recipe closed: **70% / 8 passes / wobble 0.10, drawn =
target − 0.24** (pin-verified at Ø1.0, carries to Ø2-class). Key physics: above
~70% power a hole finishes SMALLER — surplus energy chars the exit closed. Cutout
re-confirmed: S100 released on pass 6 exactly (no spare — keep attending). Mount
standards decided: M2 / M2.5 / M3, bite + clearance table in the project PARTS.md.

## Phase 7 — V4 CUT AND WORKING ✅ 2026-08-24 — v0.1

The first fully successful board through the whole pipeline: V4 (The Source P1b) cut
with the dialed recipe, rings healthy, holes at size, continuity good, the hand
drawing intact. Edson: "it looks amazing." One critique — border burn on the cutout
edge — parked in the backlog, deliberately not engaged the same day.

## What is left now

→ **`BACKLOG.md`** (moved there in the v0.1 cleanup, same day).
