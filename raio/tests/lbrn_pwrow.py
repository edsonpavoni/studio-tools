#!/usr/bin/env python3
"""raio · tests/lbrn_pwrow.py — a LightBurn file with a row of 5 mm squares, one pulse width per square.
For side-by-side tests against raio's `mark_test.py pwrow`. Uses trilha's writer (studio/trilha/lbrn.py).

    python3 studio/raio/tests/lbrn_pwrow.py --ns 50,100,200,350,500 --y 30 --out studio/raio/tests/pw-row-lightburn.lbrn2
Open the file in LightBurn (device B6 Mopa), check the layer table, Frame, Start. Coordinates here are raio's (mm, field centre = 0,0, +y toward the column); the file is written in LightBurn's frame for the B6 Mopa device (origin bottom-left, 157.5 workspace), i.e. +78.75 on both axes.
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "trilha"))
from lbrn import LbrnDoc, Layer

ap = argparse.ArgumentParser()
ap.add_argument("--ns", default="50,100,200,350,500")
ap.add_argument("--y", type=float, default=30.0, help="row centre, mm (+ = toward the column)")
ap.add_argument("--pitch", type=float, default=8.0); ap.add_argument("--size", type=float, default=5.0)
ap.add_argument("--power", type=float, default=100); ap.add_argument("--speed", type=float, default=100)
ap.add_argument("--khz", type=float, default=20); ap.add_argument("--passes", type=int, default=20)
ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "pw-row-lightburn.lbrn2"))
a = ap.parse_args()
ns = [int(v) for v in a.ns.split(",")]
x0 = -(len(ns) - 1) * a.pitch / 2
doc = LbrnDoc(device="B6 Mopa", notes=f"raio pulse-width row: {ns} ns left→right, {a.power}% {a.speed}mm/s {a.khz}kHz x{a.passes}. Same aluminium as raio's rows.")
for i, v in enumerate(ns):
    layer = doc.add_layer(Layer(index=i, name=f"PW_{v}ns", mode="Cut", power=a.power, speed=a.speed, freq=int(a.khz * 1000),
                                passes=a.passes, priority=i, qpulse=v))
    doc.add_rect(78.75 + x0 + i * a.pitch, 78.75 + a.y, a.size, a.size, layer)   # LightBurn origin = bottom-left of the 157.5 field
print("wrote", doc.save(a.out)); print("layers:", [f"{v} ns" for v in ns], "at y =", a.y)
