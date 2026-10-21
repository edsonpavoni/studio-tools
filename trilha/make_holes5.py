#!/usr/bin/env python3
"""
make_holes5.py — final diameter ladder at the HOLES-4 winning energy.

HOLES-4 (2026-08-24): the ONLY cell that passed the pin was 70% / 0.65 drawn — and it
is too tight, real mechanical force to seat the pin. Higher power (85/100) FAILED the
pin at the same drawn size: extra energy goes into melt/char that narrows the finished
hole, not into widening it. So power is settled at 70% and diameter is the last lever.

One layer, one variable: drawn 0.68 / 0.72 / 0.76 at the frozen winning cell
(70%, 8 passes, 400 mm/s, 40 kHz, 200 ns, wobble 0.10/0.02). Two identical rows per
diameter = 8 pins per size, because "slides in without force" is a feel test and one
sample lies. Pads 1.8 mm, production CLEAR.

Target: the SMALLEST drawn where the pin seats with light finger pressure. That
becomes the production number for 1.0 mm finished holes and sets --hole-kerf.

    python3 make_holes5.py     -> coupon/B6-HOLES5-COUPON.lbrn2 + SCORE-HOLES5.md

Board OFF the bed. Air assist ON. Single hole layer, ~35 s.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lbrn import LbrnDoc, Layer

PITCH = 2.54
PER = 4
PAD = 1.8
POWER = 70
PASSES = 8
DIAS = [0.68, 0.72, 0.76]
ROW_Y = [30.0, 18.0]

def build():
    doc = LbrnDoc(notes=(
        "HOLES-5: diameter ladder at the HOLES-4 winner (70%, 8 passes, 400mm/s,"
        " 40kHz, 200ns, wobble 0.10/0.02). Columns: drawn 0.68 / 0.72 / 0.76,"
        " two identical rows of 4 per column, pads 1.8mm."
        " Pick the SMALLEST drawn where the pin seats with light finger pressure."
        " BOARD OFF THE BED. AIR ON."))
    n = 0
    labels = []
    x0 = 6.0
    L = Layer(n, "H_P070", "Cut", POWER, 400, 40000, passes=PASSES,
              priority=n, qpulse=200, wobble=1, wobble_size=0.10, wobble_step=0.02)
    n += 1
    doc.add_layer(L)
    for i, dia in enumerate(DIAS):
        gx = x0 + i * (PER * PITCH + 6.0)
        for y in ROW_Y:
            for k in range(PER):
                doc.add_circle(gx + k * PITCH, y, dia, L)
        labels.append((gx + 1.5 * PITCH, ROW_Y[0] + 5.5, "%.2f" % dia))
    clear = doc.add_layer(Layer(n, "CLEAR", "Scan", 75, 1500, 40000, passes=4,
                                priority=n, qpulse=200, interval=0.05,
                                angle_per_pass=13))
    n += 1
    for i in range(len(DIAS)):
        gx = x0 + i * (PER * PITCH + 6.0)
        for y in ROW_Y:
            doc.add_rect(gx + (PER - 1) * PITCH / 2, y,
                         (PER - 1) * PITCH + 4.4, 4.4, clear)
            for k in range(PER):
                doc.add_circle(gx + k * PITCH, y, PAD, clear)
    mark = doc.add_layer(Layer(n, "LABELS", "Scan", 20, 1000, 40000, passes=1,
                               priority=n, qpulse=200, interval=0.05))
    for lx, ly, txt in labels:
        doc.add_text(lx, ly, txt, mark, height=2.2)
    doc.add_text(x0, 8.0, "all 70% 8pass wobble - both rows same drawn", mark,
                 height=2.0)
    return doc

SCORE = """# HOLES-5 — score sheet

Date: ______  Material: Qimoo FR4 1.6 mm  Air: ON  Board off bed: yes/no

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
"""

if __name__ == "__main__":
    os.makedirs("coupon", exist_ok=True)
    doc = build()
    doc.save("coupon/B6-HOLES5-COUPON.lbrn2")
    open("coupon/SCORE-HOLES5.md", "w").write(SCORE)
    print("wrote coupon/B6-HOLES5-COUPON.lbrn2 and coupon/SCORE-HOLES5.md")
