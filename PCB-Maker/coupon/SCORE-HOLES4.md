# HOLES-4 — score sheet

## ✅ RUN 2026-08-24 — RESULT: power settled at 70%, diameter still one step short

**The ONLY cell that passed the pin was 70% / 0.65 drawn — and it is too tight**
(real mechanical force to seat). 85% and 100% at the same drawn sizes FAILED the pin:
extra energy chars/melts the hole SMALLER, not bigger. Power lever is now settled at
70%; diameter is the last variable. → HOLES-5 (`make_holes5.py`): drawn 0.68/0.72/0.76
ladder at the frozen 70% cell, 8 pins per size.

Date: 2026-08-24  Material: Qimoo FR4 1.6 mm  Air: ON  Board off bed: yes

Rows: drawn 0.60 (top) / 0.65 (bottom). Columns: 100 / 85 / 70 % power. Everything
else frozen: 8 passes, 400 mm/s, 40 kHz, 200 ns, wobble 0.10/0.02, pads 1.8 mm.
Pin reference: 2.54 header pin, 0.64 mm sq, ~0.91 mm diagonal -> target finished ~0.95.

| power | drawn | through? | pin fits? | back burn? | ring OK? | measured Ø |
|---|---|---|---|---|---|---|
| 100 | 0.60 |  |  |  |  |  |
| 100 | 0.65 |  |  |  |  |  |
| 85  | 0.60 |  |  |  |  |  |
| 85  | 0.65 |  |  |  |  |  |
| 70  | 0.60 |  |  |  |  |  |
| 70  | 0.65 |  |  |  |  |  |

Also, from the HOLES-3 coupon already on the bench:

| group | drawn | through? | pin fits? | back burn vs W8? |
|---|---|---|---|---|
| W6 | 0.70 |  |  |  |
| W6 | 0.55 |  |  |  |

What this decides:
* production drawn diameter = the LOWEST drawn where the pin fits at the winning power
* production power = the LOWEST power (or pass count, via the W6 rows) that is
  through + pin fits, because that is what kills the back-side burn
* winner becomes the HOLES layer default in lbrn.py/circuit2lbrn.py, --hole-kerf is
  recomputed as (0.91..0.95 target − drawn), and V4-60x40.lbrn2 is REGENERATED

HOLES-3 verdict for the record (2026-08-24): wobble recipe WINS over TRIBE-style.
W8 0.55 = clean + good rings but pin no-fit. W8 0.70 = pin fits, back a little burnt,
rings just good enough.
