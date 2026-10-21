#!/usr/bin/env python3
"""
make_holes3.py — the coupon HOLES-2 made necessary.

HOLES-2 (2026-08-24) answered pass count: ALL cells through, even 8 passes. But every
cell finished oversize versus the TRIBE reference and the 1.5 mm pad ring came out too
thin. So the open question is no longer "does it go through" but "what drawn diameter
and what hole strategy finish at 1.0 mm with a ring that survives".

Two competing hypotheses, both on this coupon:

  A. WOBBLE cells — the current recipe (400 mm/s, wobble 0.10/0.02, 40 kHz) with the
     drawn diameter swept DOWN: 0.55 / 0.70, at 8 and 6 passes. If the true wobble
     kerf is ~0.3+, one of these lands on 1.0 finished.
  B. TRIBE cells — the 2025 reference recipe that produced the board we are comparing
     against: NO wobble, 40 mm/s, 37 kHz, 8 passes, drawn AT nominal (0.90 / 1.00).
     ToR_008 applied zero kerf compensation and its holes fit pins with fat rings.

All pads are 1.8 mm this time (HOLES-2 used 1.5 and the ring died; TRIBE-class rings
need the bigger pad AND a smaller finished hole — this coupon separates the two).

    python3 make_holes3.py     -> coupon/B6-HOLES3-COUPON.lbrn2 + SCORE-HOLES3.md

Board OFF the bed. Air assist ON. Run groups in order, cool between groups.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lbrn import LbrnDoc, Layer

PITCH = 2.54
PER = 4
PAD = 1.8

# (label, passes, wobble?, speed, freq, [drawn dias top->bottom])
GROUPS = [
    ("W8", 8, True, 400, 40000, [0.55, 0.70]),
    ("W6", 6, True, 400, 40000, [0.55, 0.70]),
    ("T8", 8, False, 40, 37000, [0.90, 1.00]),
]

ROW_Y = [30.0, 18.0]

def build():
    doc = LbrnDoc(notes=(
        "HOLES-3: finished-diameter hunt. W8/W6 = wobble recipe (400mm/s 40kHz"
        " wobble 0.10/0.02) at 8/6 passes, drawn 0.55 top / 0.70 bottom."
        " T8 = TRIBE 2025 reference recipe (NO wobble, 40mm/s, 37kHz, 8 passes),"
        " drawn 0.90 top / 1.00 bottom, zero compensation as on ToR_008."
        " All pads 1.8mm. Target: 1.0mm finished, pin fits, ring survives."
        " BOARD OFF THE BED. AIR ON. Cool between groups."))
    n = 0
    labels = []
    x0 = 6.0
    for i, (name, passes, wob, speed, freq, dias) in enumerate(GROUPS):
        gx = x0 + i * (PER * PITCH + 6.0)
        if wob:
            L = Layer(n, "H_%s" % name, "Cut", 100, speed, freq, passes=passes,
                      priority=n, qpulse=200, wobble=1, wobble_size=0.10,
                      wobble_step=0.02)
        else:
            L = Layer(n, "H_%s" % name, "Cut", 100, speed, freq, passes=passes,
                      priority=n, qpulse=200)
        n += 1
        doc.add_layer(L)
        for dia, y in zip(dias, ROW_Y):
            for k in range(PER):
                doc.add_circle(gx + k * PITCH, y, dia, L)
        labels.append((gx + 1.5 * PITCH, ROW_Y[0] + 5.5, name))
        # per-cell drawn-diameter marks, right of each row
        for dia, y in zip(dias, ROW_Y):
            labels.append((gx + (PER - 1) * PITCH + 2.6, y - 1.0, "%.2f" % dia))
    # CLEAR frame: same measured fill recipe as production, 1.8mm pads
    clear = doc.add_layer(Layer(n, "CLEAR", "Scan", 75, 1500, 40000, passes=4,
                                priority=n, qpulse=200, interval=0.05,
                                angle_per_pass=13))
    n += 1
    for i, (name, passes, wob, speed, freq, dias) in enumerate(GROUPS):
        gx = x0 + i * (PER * PITCH + 6.0)
        for dia, y in zip(dias, ROW_Y):
            doc.add_rect(gx + (PER - 1) * PITCH / 2, y,
                         (PER - 1) * PITCH + 4.4, 4.4, clear)
            for k in range(PER):
                doc.add_circle(gx + k * PITCH, y, PAD, clear)
    mark = doc.add_layer(Layer(n, "LABELS", "Scan", 20, 1000, 40000, passes=1,
                               priority=n, qpulse=200, interval=0.05))
    for lx, ly, txt in labels:
        doc.add_text(lx, ly, txt, mark, height=2.2)
    doc.add_text(x0, 8.0, "W=wobble drawn .55/.70  T=TRIBE no-wob drawn .90/1.00",
                 mark, height=2.0)
    return doc

SCORE = """# HOLES-3 — score sheet

Date: ______  Material: Qimoo FR4 1.6 mm  Air: ON  Board off bed: yes/no

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
"""

if __name__ == "__main__":
    os.makedirs("coupon", exist_ok=True)
    doc = build()
    doc.save("coupon/B6-HOLES3-COUPON.lbrn2")
    open("coupon/SCORE-HOLES3.md", "w").write(SCORE)
    print("wrote coupon/B6-HOLES3-COUPON.lbrn2 and coupon/SCORE-HOLES3.md")
