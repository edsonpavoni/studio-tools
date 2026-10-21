# MOUNT + CUTOUT — score sheet

## ✅ RUN 2026-08-24 — RESULT

**CUTOUT: S100 released on pass 6.** The proven 100%/6-pass recipe is confirmed on
this sheet — but note it used ALL six passes, no spare, so keep attending it and
re-run with only CUTOUT enabled if a board ever doesn't drop.

**MOUNT: all three drawn sizes cut clean at 70%** — the dialed hole cell works at
Ø2-class diameters, kerf 0.24 carries. (Which rung the M2 gauged best was not
recorded; the standard table in PARTS.md / the tool README is the going-forward
authority on finished sizes.)

Studio decision made on the back of this run: **mount-hole standards are M2, M2.5,
M3** — see the table added to PARTS.md 2026-08-24. UI hole placement in handroute is
on the tool TODO (PLAN.md), post-V4.

Date: 2026-08-24  Material: Qimoo FR4 1.6 mm  Air: ON  Board off bed: yes

MOUNT: drawn 1.70 / 1.76 / 1.82 at the dialed hole cell (70%, 8 passes, wobble
0.10/0.02). Gauge = the real M2 screw. Target finished 2.0 (studio standard).

| drawn | through (3/3)? | M2: no / forced / slides / sloppy | back clean? |
|---|---|---|---|
| 1.70 |  |  |  |
| 1.76 |  |  |  |
| 1.82 |  |  |  |

CUTOUT squares — STAND THERE, count the pass each falls on:

| square | recipe | released on pass | edge char vs the other? |
|---|---|---|---|
| S100 | 100% x6, wobble 0.30 (proven) |  |  |
| S85  | 85% x8, wobble 0.30 (experiment) |  |  |

What this decides:
* MOUNT: smallest drawn where M2 slides = the number. If it matches target − 0.24,
  one --hole-kerf covers all sizes and nothing changes in the converter. If not,
  circuit2lbrn needs a size-dependent kerf before V4.
* S100 releasing on 5-6 re-confirms CUTOUT passes=6 on this sheet. If it needs all 6
  with nothing to spare, note it.
* S85: only interesting if it releases AND the edge is visibly cleaner. Then the
  CUTOUT default can drop to 85% with passes re-measured. Otherwise keep 100/6.

Context: HOLES-5 locked pin holes at 70%/8/wobble, drawn 0.76 for 1.0 finished
(kerf 0.24, measured at Ø1.0 — this coupon checks it at Ø2.0).
