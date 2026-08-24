#!/usr/bin/env python3
"""
make_holes4.py — the dial-in coupon after HOLES-3 bracketed the answer.

HOLES-3 (2026-08-24): the WOBBLE recipe wins. At 8 passes, drawn 0.55 = clean, good
rings, but the standard header pin does NOT pass (finished under ~0.9). Drawn 0.70 =
pin fits, but back-side burn a touch heavy and rings only just OK. A 2.54 header pin
is 0.64 mm square = ~0.91 mm across the diagonal, so target finished is ~0.95.

Two axes, one variable each:

  * drawn diameter BETWEEN the bracket: 0.60 (top) / 0.65 (bottom)
  * power ladder at fixed 8 passes: 100 / 85 / 70 % — hunting the least energy that
    still penetrates, to kill the back-side burn without touching geometry

Everything else frozen at the proven cell: 400 mm/s, 40 kHz, 200 ns, wobble
0.10/0.02, 8 passes, 1.8 mm pads, production CLEAR recipe.

NOTE: HOLES-3's W6 cells (6 passes at 100%) are already cut on that coupon — pin-test
W6 0.70 too, since fewer passes is the OTHER way to burn less and it costs nothing.

    python3 make_holes4.py     -> coupon/B6-HOLES4-COUPON.lbrn2 + SCORE-HOLES4.md

Board OFF the bed. Air assist ON. Run groups in order, cool between groups.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lbrn import LbrnDoc, Layer

PITCH = 2.54
PER = 4
PAD = 1.8
PASSES = 8
POWERS = [100, 85, 70]
DIAS = [0.60, 0.65]   # top, bottom
ROW_Y = [30.0, 18.0]

def build():
    doc = LbrnDoc(notes=(
        "HOLES-4: dial-in between HOLES-3's 0.55 (pin no-fit) and 0.70 (fits, burnt)."
        " Rows: drawn 0.60 top / 0.65 bottom. Columns: 100 / 85 / 70 % power, all"
        " 8 passes, 400mm/s, 40kHz, 200ns, wobble 0.10/0.02, pads 1.8mm."
        " Target: pin fits (finished ~0.95), clean back, TRIBE-class ring."
        " BOARD OFF THE BED. AIR ON. Cool between groups."))
    n = 0
    labels = []
    x0 = 6.0
    for i, pw in enumerate(POWERS):
        gx = x0 + i * (PER * PITCH + 6.0)
        L = Layer(n, "H_P%03d" % pw, "Cut", pw, 400, 40000, passes=PASSES,
                  priority=n, qpulse=200, wobble=1, wobble_size=0.10,
                  wobble_step=0.02)
        n += 1
        doc.add_layer(L)
        for dia, y in zip(DIAS, ROW_Y):
            for k in range(PER):
                doc.add_circle(gx + k * PITCH, y, dia, L)
        labels.append((gx + 1.5 * PITCH, ROW_Y[0] + 5.5, "%d%%" % pw))
        for dia, y in zip(DIAS, ROW_Y):
            labels.append((gx + (PER - 1) * PITCH + 2.6, y - 1.0, "%.2f" % dia))
    clear = doc.add_layer(Layer(n, "CLEAR", "Scan", 75, 1500, 40000, passes=4,
                                priority=n, qpulse=200, interval=0.05,
                                angle_per_pass=13))
    n += 1
    for i in range(len(POWERS)):
        gx = x0 + i * (PER * PITCH + 6.0)
        for dia, y in zip(DIAS, ROW_Y):
            doc.add_rect(gx + (PER - 1) * PITCH / 2, y,
                         (PER - 1) * PITCH + 4.4, 4.4, clear)
            for k in range(PER):
                doc.add_circle(gx + k * PITCH, y, PAD, clear)
    mark = doc.add_layer(Layer(n, "LABELS", "Scan", 20, 1000, 40000, passes=1,
                               priority=n, qpulse=200, interval=0.05))
    for lx, ly, txt in labels:
        doc.add_text(lx, ly, txt, mark, height=2.2)
    doc.add_text(x0, 8.0, "8 passes wobble - drawn .60 top / .65 bottom", mark,
                 height=2.0)
    return doc

SCORE = """# HOLES-4 — score sheet

Date: ______  Material: Qimoo FR4 1.6 mm  Air: ON  Board off bed: yes/no

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
"""

if __name__ == "__main__":
    os.makedirs("coupon", exist_ok=True)
    doc = build()
    doc.save("coupon/B6-HOLES4-COUPON.lbrn2")
    open("coupon/SCORE-HOLES4.md", "w").write(SCORE)
    print("wrote coupon/B6-HOLES4-COUPON.lbrn2 and coupon/SCORE-HOLES4.md")
