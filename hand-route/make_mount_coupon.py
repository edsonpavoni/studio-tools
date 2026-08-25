#!/usr/bin/env python3
"""
make_mount_coupon.py — mounting holes + cutout check, after HOLES-5 locked the recipe.

HOLES-5 (2026-08-24) settled the hole cell: 70% / 8 passes / wobble 0.10/0.02,
drawn = target − 0.24. That kerf was measured at Ø1.0. This coupon answers the two
remaining size classes before V4 cuts:

  MOUNT — does 0.24 hold at Ø2.0 (the studio-standard mount hole, PARTS.md)?
     Ladder: drawn 1.70 / 1.76 / 1.82 at the frozen hole cell, 3 holes each.
     Fit gauge: the actual M2 screw. Pick the smallest drawn it slides through.

  CUTOUT — NOT re-engineered (V3's damage was passes-after-release, already fixed by
     6 passes + attendance), but two squares:
       S100: the proven recipe, 100% / 6 passes / wobble 0.30 — COUNT THE RELEASE
             PASS on today's sheet. Confirms 6 is still right for this stock.
       S85:  85% / 8 passes, same wobble — does the HOLES finding (less power =
             less char) transfer to the board edge? If it releases and the edge is
             cleaner, it becomes a candidate; if it does not release by 8, forget it.

    python3 make_mount_coupon.py  -> coupon/B6-MOUNT-COUPON.lbrn2 + SCORE-MOUNT.md

Board OFF the bed. Air ON. ⚠️ STAND AT THE MACHINE for both squares — note the pass
each one falls on. The squares WILL drop; that is the point.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lbrn import LbrnDoc, Layer

MDIAS = [1.70, 1.76, 1.82]
PER = 3
PITCH = 5.0
SQ = 15.0

def build():
    doc = LbrnDoc(notes=(
        "MOUNT + CUTOUT coupon. MOUNT: drawn 1.70/1.76/1.82 at the dialed hole cell"
        " (70%, 8 passes, 400mm/s, 40kHz, 200ns, wobble 0.10/0.02), 3 holes each,"
        " M2 screw is the gauge. CUTOUT: S100 = proven 100%/6-pass recipe, count the"
        " release pass; S85 = 85%/8-pass char experiment. BOARD OFF THE BED, AIR ON,"
        " ATTEND THE SQUARES — they fall when released."))
    n = 0
    labels = []
    x0 = 8.0
    y_holes = 34.0
    L = Layer(n, "MOUNT", "Cut", 70, 400, 40000, passes=8, priority=n,
              qpulse=200, wobble=1, wobble_size=0.10, wobble_step=0.02)
    n += 1
    doc.add_layer(L)
    for i, dia in enumerate(MDIAS):
        gx = x0 + i * (PER * PITCH + 6.0)
        for k in range(PER):
            doc.add_circle(gx + k * PITCH, y_holes, dia, L)
        labels.append((gx + PITCH, y_holes + 4.5, "%.2f" % dia))
    s100 = Layer(n, "S100", "Cut", 100, 400, 40000, passes=6, priority=n,
                 qpulse=200, wobble=1, wobble_size=0.30, wobble_step=0.04)
    n += 1
    doc.add_layer(s100)
    doc.add_rect(x0 + SQ / 2, 14.0, SQ, SQ, s100)
    labels.append((x0 + SQ / 2, 14.0 + SQ / 2 + 2.5, "100/6"))
    s85 = Layer(n, "S85", "Cut", 85, 400, 40000, passes=8, priority=n,
                qpulse=200, wobble=1, wobble_size=0.30, wobble_step=0.04)
    n += 1
    doc.add_layer(s85)
    doc.add_rect(x0 + SQ + 12.0 + SQ / 2, 14.0, SQ, SQ, s85)
    labels.append((x0 + SQ + 12.0 + SQ / 2, 14.0 + SQ / 2 + 2.5, "85/8"))
    mark = doc.add_layer(Layer(n, "LABELS", "Scan", 20, 1000, 40000, passes=1,
                               priority=n, qpulse=200, interval=0.05))
    for lx, ly, txt in labels:
        doc.add_text(lx, ly, txt, mark, height=2.2)
    doc.add_text(x0, 44.0, "MOUNT drawn 1.70/1.76/1.82 - M2 gauge - ATTEND SQUARES",
                 mark, height=2.0)
    return doc

SCORE = """# MOUNT + CUTOUT — score sheet

Date: ______  Material: Qimoo FR4 1.6 mm  Air: ON  Board off bed: yes/no

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
"""

if __name__ == "__main__":
    os.makedirs("coupon", exist_ok=True)
    doc = build()
    doc.save("coupon/B6-MOUNT-COUPON.lbrn2")
    open("coupon/SCORE-MOUNT.md", "w").write(SCORE)
    print("wrote coupon/B6-MOUNT-COUPON.lbrn2 and coupon/SCORE-MOUNT.md")
