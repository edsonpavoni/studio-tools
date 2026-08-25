# hand-route — backlog

One list, ordered by value. Grab the top item that fits the day. History lives in
`PLAN.md`; settings live in `B6-PCB-RECIPE.md`; nothing here is urgent — the tool
already makes working boards (V4, The Source P1b, 2026-08-24).

## Next

1. **⭐ The Board tool** — draw the board OUTLINE with the Pencil (or exact
   primitives), place mount holes, live measurements, copper fades while shaping.
   This is the feature that makes hand-route the expressive art tool. Full plan,
   phases and gates: **`PLAN-BOARD.md`** (2026-08-25). Absorbs the old "UI hole
   placement" item.
2. **Border burn on the cutout edge** — Edson's one critique of V4. Candidate: lower
   cutout power (the S85 square on `make_mount_coupon.py` tests 85%/8; the hole
   ladder proved less power = less char). Run the square, compare edges, decide.
   Pairs naturally with the Board tool's P5 perimeter coupon — one bench session.
3. **`--pad-grow`** — fatten footprint pads in the negative when a footprint's
   annulus is too thin around the finished hole. V4's rings were saved by the hole
   dial-in; the next dense board may need the pad-side lever too.

## Later

5. **Cooling pauses between hot stages** — the hole interleave already cools per-hole;
   this would add dwell between layers (holes → clear → cutout). LightBurn has no
   native inter-layer pause, so it means a zero-power travel layer. Decide only if a
   board shows heat damage the interleave doesn't cover — V4 didn't.
6. **`--tabs`** — cutout tabs so a board can run unattended. Today's rule (6 passes +
   stand there) works; tabs only matter if unattended cutting ever becomes real.
7. **Width coupon** — `make_width_coupon.py` / `coupon/B6-WIDTH-COUPON.lbrn2`, unrun.
   Would prove 0.2 mm traces (0.3 is proven and is the current floor).
8. **Long perimeters** — cutout proven on 10–30 mm squares and one 60×40 board; a
   100 mm edge is still untested (recipe doc, known unknowns).

## Considered and killed (2026-08-25, Edson's call — don't re-add without him)

- **Autoroute assist** (click a net, software finds a route around drawn copper) —
  killed. Against the point of the tool: the Pencil is the only thing that makes
  copper, and an obstacle-aware router is a lot of software for a tool that is lean.
- **Full bundle file format** (one file carrying circuit + traces + everything) —
  killed for now. The `.handroute` extension survives as the save file (strokes +
  moves), but circuit.json stays the design source.
- **Real 3D component models** (instead of the honest boxes) — not ours to build;
  it lives upstream in tscircuit's viewer and doesn't make a better board.
- **Name** — resolved: the project is **hand-route** (was PCB-Maker), the save file
  is **`.handroute`**. "pcb-art-tool" rejected as generic.

## Done (highlights — details in PLAN.md)

- 2026-08-25: UI restyled Figma-like per Edson's direction — deep green accent,
  three floating icon islands (drawing / views / undo+save), pencil-size and
  vertical-smoothness popovers, sidebar reduced to connections with a hide toggle.
- 2026-08-25: renamed PCB-Maker → hand-route, UI files flattened to the project
  root, save file is now `board.handroute` (legacy traces.json still read).
  Three UI features shipped: net **focus** (tap a net in the checklist, the rest
  greys), component **Move** (drag a part with its pads; strokes stay put and the
  checklist unticks — no auto rerouting, by design; moves applied identically in
  converter and verifier, unknown-component moves refuse), and a quieter hairline
  ghost dash.
- 2026-08-24: hole recipe dialed (70%/8/kerf 0.24), mount standards, V4 cut + working
- 2026-08-23: first real board V3; two board-killing converter bugs found and fixed
- 2026-08-18–22: recipe measured on six coupon runs; iPad hand-routing UI built
- 2026-08-17: 2025 settings recovered from ToR_008; converter + verifier built
