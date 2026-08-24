# HOLES-2 — score sheet

## ✅ RUN 2026-08-24 — RESULT

**ALL SIX CELLS THROUGH, including 8 passes at 0.85 drawn.** Pass count is settled:
8 is enough (6 untested here, on HOLES-3). But **every cell finished OVERSIZE versus
the TRIBE reference and the 1.5 mm pad ring is too thin everywhere** — side by side
with ToR_008 the difference is obvious (photos in the 2026-08-24 session). So the
0.15 kerf compensation is NOT confirmed; the true wobble kerf is larger, and/or
wobble itself is the wrong hole strategy (TRIBE ran no-wobble 40 mm/s 37 kHz, drawn
at nominal, zero compensation, and its holes are the good ones).

No caliper numbers were taken — the eyeball verdict was unambiguous. → HOLES-3
(`make_holes3.py`) hunts the finished diameter: wobble cells drawn 0.55/0.70 at
8/6 passes vs TRIBE-recipe control cells drawn 0.90/1.00, all with 1.8 mm pads.

Date: 2026-08-24  Material: Qimoo FR4 1.6 mm  Air: ON  Board off bed: yes

Three columns = 8 / 10 / 12 passes. Two rows per column: TOP drawn 0.85 mm
(--hole-kerf 0.15 compensation, target 1.0 finished), BOTTOM drawn 1.00 mm (control).
All 100% / 400 mm/s / 40 kHz / 200 ns / wobble 0.10/0.02.

| passes | row | through? | clean exit? | measured Ø | pin fits? | halo into pad? |
|---|---|---|---|---|---|---|
| 8  | 0.85 |  |  |  |  |  |
| 8  | 1.00 |  |  |  |  |  |
| 10 | 0.85 |  |  |  |  |  |
| 10 | 1.00 |  |  |  |  |  |
| 12 | 0.85 |  |  |  |  |  |
| 12 | 1.00 |  |  |  |  |  |

What this decides:
* production pass count = the LOWEST row that is through + clean exit
* true kerf = measured Ø minus drawn Ø  ->  becomes --hole-kerf
* if 0.85-drawn fits the header pin, kerf compensation 0.15 is confirmed

V3 context: 16 passes = through but oversize + halo. If even 8 is through and clean,
consider a follow-up at 6.
