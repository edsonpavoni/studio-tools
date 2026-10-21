# hand-route — backlog

One list, ordered by value. Grab the top item that fits the day. History lives in
`PLAN.md`; settings live in `B6-PCB-RECIPE.md`; nothing here is urgent — the tool
already makes working boards (V4, The Source P1b, 2026-08-24).

## Next

1. **🔴 BENCH DAY: prove a drawn board in copper** — the Board tool is BUILT
   (P1–P4, `PLAN-BOARD.md`) but nothing hand-shaped has been cut yet. One
   session, three questions: (a) does an organic perimeter ≥150 mm release
   clean on the proven cutout recipe, (b) where does the FR4 web between a hole
   and the rim actually tear — ladder 0.6/0.8/1.0/1.5 mm, which confirms or
   raises the assumed `--edge-web 1.0`, (c) **border burn on the cutout edge**,
   Edson's one critique of V4 — run the S85 square from `make_mount_coupon.py`
   (85%/8; the hole ladder proved less power = less char), compare edges.
   Then cut one real Pencil-drawn board. Score everything into
   `MATERIAL-QIMOO-FR4.md`.
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

## Deferred by Edson (2026-08-25)

- **File management in the app** — opening, starting and naming boards. Parked
  until after the burn. Until then Edson asks Claude to open or start a board and
  Claude keeps the folders in order; the convention and the parked ideas are both
  in **`FILES.md`**. One idea in there is not really a feature and should jump the
  queue whenever this restarts: **two clients on one drawing overwrite each other
  silently**, which is the only way to lose an afternoon here.

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

- 2026-08-25: **the Board tool, P1–P4** — the board outline is drawn here now,
  freehand or as exact primitives, with mount holes, typed sizes, 0.5 mm snap,
  and copper fading while shaping. Verified as an object in the UI and again in
  `verify.py`. 3D extrudes the real shape. **Not yet cut in copper: P5.**
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
