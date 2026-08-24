#!/usr/bin/env python3
"""
make_holes2.py — the pass-count and kerf coupon that V3 made necessary.

V3 (2026-08-23), the first real board, went through cleanly at 16 passes — and proved
16 is too much: holes finished oversize versus the TRIBE reference, with a burned halo
eating into the pad annulus. Every earlier coupon asked "does it go through?"; this one
asks "what is the LEAST that goes through, and what diameter does it actually leave?"

One variable per axis:

  * three pass counts: 8, 10, 12 — all at the proven 100% / 400 mm/s / wobble 0.10
  * two drawn diameters per count: 0.85 (the new --hole-kerf 0.15 compensation for a
    1.0 target) and 1.00 (uncompensated control)
  * four holes per cell at real 2.54 pitch, so neighbours heat each other as on a board

24 holes, ~75 s. With pads: each hole sits in a 1.5 mm copper pad ring left by a small
CLEAR frame, so the halo damage to the annulus is visible exactly as on a board.

    python3 make_holes2.py     -> coupon/B6-HOLES2-COUPON.lbrn2 + SCORE-HOLES2.md

Board OFF the bed. Air assist ON. Run groups in order; STOP after each and check
through-ness with a pin from the back before trusting the meter.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lbrn import LbrnDoc, Layer

PITCH = 2.54
PER = 4
PASSES = [8, 10, 12]
DIAS = [0.85, 1.00]

def build():
    doc = LbrnDoc(notes=(
        "HOLES-2: pass count x drawn diameter. Rows: top=0.85mm drawn (kerf-compensated"
        " for 1.0 target), bottom=1.00mm drawn (control). Columns: 8, 10, 12 passes,"
        " 4 holes each at 2.54 pitch. All 100%/400mm/s/40kHz/200ns/wobble 0.10/0.02."
        " A CLEAR ring frames each group so the pad annulus damage is visible."
        " BOARD OFF THE BED. AIR ON."))
    n = [0]
    labels = []
    x0 = 6.0
    rows = [(0.85, 30.0), (1.00, 18.0)]
    for i, ps in enumerate(PASSES):
        gx = x0 + i * (PER * PITCH + 6.0)
        L = Layer(n[0], "H_%02dx" % ps, "Cut", 100, 400, 40000, passes=ps,
                  priority=n[0], qpulse=200, wobble=1, wobble_size=0.10,
                  wobble_step=0.02)
        n[0] += 1
        doc.add_layer(L)
        for dia, y in rows:
            for k in range(PER):
                doc.add_circle(gx + k * PITCH, y, dia, L)
        labels.append((gx + 1.5 * PITCH, rows[0][1] + 5.5, "%d" % ps))
    # the fill frame: clears a band around each group so every hole keeps a ~1.5mm
    # copper pad, like on a real board. Same measured fill recipe as production.
    clear = doc.add_layer(Layer(n[0], "CLEAR", "Scan", 75, 1500, 40000, passes=4,
                                priority=n[0], qpulse=200, interval=0.05,
                                angle_per_pass=13))
    n[0] += 1
    for i in range(len(PASSES)):
        gx = x0 + i * (PER * PITCH + 6.0)
        for dia, y in rows:
            # outer rect and per-hole pad circles; even-odd leaves the pads copper
            doc.add_rect(gx + (PER - 1) * PITCH / 2, y,
                         (PER - 1) * PITCH + 4.4, 4.4, clear)
            for k in range(PER):
                doc.add_circle(gx + k * PITCH, y, 1.5, clear)
    mark = doc.add_layer(Layer(n[0], "LABELS", "Scan", 20, 1000, 40000, passes=1,
                               priority=n[0], qpulse=200, interval=0.05))
    for lx, ly, txt in labels:
        doc.add_text(lx, ly, txt, mark, height=2.6)
    doc.add_text(x0, 8.0, "top 0.85 drawn / bottom 1.00 drawn", mark, height=2.2)
    return doc

SCORE = """# HOLES-2 — score sheet

Date: ______  Material: Qimoo FR4 1.6 mm  Air: ON  Board off bed: yes/no

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
"""

if __name__ == "__main__":
    os.makedirs("coupon", exist_ok=True)
    doc = build()
    doc.save("coupon/B6-HOLES2-COUPON.lbrn2")
    open("coupon/SCORE-HOLES2.md", "w").write(SCORE)
    print("wrote coupon/B6-HOLES2-COUPON.lbrn2 and coupon/SCORE-HOLES2.md")
