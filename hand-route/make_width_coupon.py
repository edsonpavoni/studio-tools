#!/usr/bin/env python3
"""
make_width_coupon.py — how narrow can a KEPT trace be?

The gap question was answered long ago (0.171 mm cleared cleanly). This is the other
side, never measured: a copper line of width W with the field cleared on both sides,
at the production fill recipe. The kerf eats both edges, so what survives is narrower
than what was drawn — and below some width, nothing survives at all.

Seven bars, 15 mm long: 0.15 / 0.2 / 0.25 / 0.3 / 0.4 / 0.5 / 0.8 mm, each with fat
probe pads at both ends. Meter end-to-end: continuity = that width lives.

    python3 make_width_coupon.py     ->  coupon/B6-WIDTH-COUPON.lbrn2  (~50 x 42 mm)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lbrn import LbrnDoc, Layer

BARS = [0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.8]
LEN, CLR = 15.0, 2.5          # bar length, cleared band above/below

doc = LbrnDoc(notes=("Trace-width coupon. Meter each bar END TO END across the pads. "
                     "The narrowest bar with continuity is the minimum trace width. "
                     "Production fill recipe, air assist ON, board off the bed."))
fill = doc.add_layer(Layer(1, "CLEAR", "Scan", 75, 1500, 40000, passes=4,
                           priority=0, qpulse=200, interval=0.05, angle_per_pass=13))
mark = doc.add_layer(Layer(9, "LABELS", "Scan", 20, 1000, 40000, passes=1,
                           priority=1, qpulse=200, interval=0.05))
x0, y = 12.0, 3.0
for w in BARS:
    yc = y + CLR + w / 2
    # two cleared bands leave a bar of exactly w between them
    doc.add_rect(x0 + LEN/2, yc + w/2 + CLR/2, LEN, CLR, fill)
    doc.add_rect(x0 + LEN/2, yc - w/2 - CLR/2, LEN, CLR, fill)
    doc.add_text(x0 + LEN + 2.0, yc - 1.0, "%.2f" % w, mark, height=2.2)
    y += 2*CLR + w + 0.8
doc.add_text(x0 - 9.0, y + 1.0, "meter each bar", mark, height=2.4)
here = os.path.dirname(os.path.abspath(__file__))
p = doc.save(os.path.join(here, "coupon", "B6-WIDTH-COUPON.lbrn2"))
doc.to_svg(os.path.join(here, "coupon", "B6-WIDTH-COUPON.svg"))
print("Width coupon: %s" % p)
print("7 bars, %.0f x %.0f mm, a couple of minutes of laser time" % (x0+LEN+12, y+6))
print("\nScore: narrowest bar with end-to-end continuity = ______ mm")
print("Also measure a surviving bar with calipers: drawn minus measured = kerf per side x2.")
