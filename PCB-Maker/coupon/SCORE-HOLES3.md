# HOLES-3 — score sheet

## ✅ RUN 2026-08-24 — RESULT: wobble recipe wins, bracket found

**W8 0.55: through, clean, good rings — but the standard header pin does NOT fit**
(finished under the ~0.91 pin diagonal). **W8 0.70: pin FITS, but back side a little
too burnt and rings only just good enough.** So the answer sits between 0.55 and
0.70 drawn, and the excess energy needs trimming. → HOLES-4 (`make_holes4.py`):
drawn 0.60/0.65 × power 100/85/70 at fixed 8 passes. W6 and T8 rows on this coupon
still worth pin-testing (W6 = the fewer-passes route to less burn).

Date: 2026-08-24  Material: Qimoo FR4 1.6 mm  Air: ON  Board off bed: yes

Three groups. W8 / W6 = wobble recipe (400 mm/s, 40 kHz, wobble 0.10/0.02) at
8 / 6 passes, drawn 0.55 (top) and 0.70 (bottom). T8 = TRIBE 2025 reference recipe
(NO wobble, 40 mm/s, 37 kHz, 8 passes), drawn 0.90 (top) and 1.00 (bottom) with zero
compensation, exactly as ToR_008 ran. All pads 1.8 mm.

| group | drawn | through? | measured Ø | pin fits? | ring OK vs TRIBE? | char/halo? |
|---|---|---|---|---|---|---|
| W8 | 0.55 |  |  |  |  |  |
| W8 | 0.70 |  |  |  |  |  |
| W6 | 0.55 |  |  |  |  |  |
| W6 | 0.70 |  |  |  |  |  |
| T8 | 0.90 |  |  |  |  |  |
| T8 | 1.00 |  |  |  |  |  |

What this decides, in order:
* If a T8 row = pin fits + TRIBE-class ring: the HOLES layer goes back to the 2025
  recipe (no wobble, 40 mm/s, 37 kHz) and --hole-kerf goes to ~0 — drawn at target.
  Watch for charring; TRIBE never charred but this stock is not 2025's stock.
* Else: true wobble kerf = measured Ø − drawn, per W cell → new --hole-kerf default,
  and production drawn = 1.0 − that kerf. W6 through = production passes drop to 6.
* Either way: pad annulus needs the fix on the BOARD side too — 1.8 mm pads gave
  ring = (1.8 − finished)/2. Production pads come from the footprint; if the winner
  still reads thin here, circuit2lbrn grows pads (--pad-grow) before the next board.

HOLES-2 context (2026-08-24): 8/10/12 all through at 0.85 and 1.00 drawn; ALL
oversize vs TRIBE; 1.5 mm pad ring too thin everywhere. Pass count is settled — 8
works — so this coupon only hunts diameter and ring.
