# PCB-Maker — backlog

One list, ordered by value. Grab the top item that fits the day. History lives in
`PLAN.md`; settings live in `B6-PCB-RECIPE.md`; nothing here is urgent — the tool
already makes working boards (V4, The Source P1b, 2026-08-24).

## Next

1. **Border burn on the cutout edge** — Edson's one critique of V4. Candidate: lower
   cutout power (the S85 square on `make_mount_coupon.py` tests 85%/8; the hole
   ladder proved less power = less char). Run the square, compare edges, decide.
2. **handroute UI: hole placement** — palette to drop mount holes (M2/M2.5/M3
   standard table, bite + clearance, see The Source `pcb-v3/PARTS.md`) onto the
   board in the iPad UI; saved like manual traces, merged by circuit2lbrn.
3. **`--pad-grow`** — fatten footprint pads in the negative when a footprint's
   annulus is too thin around the finished hole. V4's rings were saved by the hole
   dial-in; the next dense board may need the pad-side lever too.

## Later

4. **Cooling pauses between hot stages** — the hole interleave already cools per-hole;
   this would add dwell between layers (holes → clear → cutout). LightBurn has no
   native inter-layer pause, so it means a zero-power travel layer. Decide only if a
   board shows heat damage the interleave doesn't cover — V4 didn't.
5. **`--tabs`** — cutout tabs so a board can run unattended. Today's rule (6 passes +
   stand there) works; tabs only matter if unattended cutting ever becomes real.
6. **Width coupon** — `make_width_coupon.py` / `coupon/B6-WIDTH-COUPON.lbrn2`, unrun.
   Would prove 0.2 mm traces (0.3 is proven and is the current floor).
7. **Long perimeters** — cutout proven on 10–30 mm squares and one 60×40 board; a
   100 mm edge is still untested (recipe doc, known unknowns).

## Done (highlights — details in PLAN.md)

- 2026-08-24: hole recipe dialed (70%/8/kerf 0.24), mount standards, V4 cut + working
- 2026-08-23: first real board V3; two board-killing converter bugs found and fixed
- 2026-08-18–22: recipe measured on six coupon runs; handroute/ built (iPad hand-routing)
- 2026-08-17: 2025 settings recovered from ToR_008; converter + verifier built
