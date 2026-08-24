# HOLES-5 — score sheet

## ✅ RUN 2026-08-24 — RESULT: **0.76 IS THE RECIPE**

Drawn 0.76 at 70% / 8 passes / wobble 0.10/0.02 seats the 2.54 header pin correctly.
True wobble kerf at this cell = **0.24 mm** (1.00 target − 0.76 drawn). Defaults
updated in lbrn.py (HOLES 70%/8) and circuit2lbrn.py (--hole-kerf 0.24) same day.
Kerf measured at Ø1.0; B6-MOUNT-COUPON checks it holds at Ø2.0 before V4 cuts.

Date: 2026-08-24  Material: Qimoo FR4 1.6 mm  Air: ON  Board off bed: yes

Columns: drawn 0.68 / 0.72 / 0.76. Both rows identical (8 pins per size).
All at the HOLES-4 winner: 70%, 8 passes, 400 mm/s, 40 kHz, 200 ns, wobble
0.10/0.02, pads 1.8 mm.

| drawn | through (8/8)? | pin: force / snug / easy? | back clean? | ring OK? |
|---|---|---|---|---|
| 0.68 |  |  |  |  |
| 0.72 |  |  |  |  |
| 0.76 |  |  |  |  |

What this decides:
* production drawn = SMALLEST size where the pin seats snug with light pressure
  (0.65 at this cell = force-fit, from HOLES-4 — so the answer is one of these three,
  and if even 0.68 is still forced, the ladder continues 0.80+)
* --hole-kerf = 1.00 target − winning drawn; HOLES layer default becomes
  70% / 8 passes / wobble 0.10/0.02
* then V4-60x40.lbrn2 is REGENERATED with the new defaults and V4 can finally cut

Ladder context (all 2026-08-24): HOLES-2: 8 passes enough, 0.85+ oversize.
HOLES-3: wobble beats TRIBE-style; 0.55 pin no-fit / 0.70 fits but burnt.
HOLES-4: only 70%/0.65 passed the pin, too tight; 85/100% char holes SMALLER.
