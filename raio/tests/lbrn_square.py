#!/usr/bin/env python3
"""raio · tests/lbrn_square.py — a LightBurn file with one square (line layer), for side-by-side tests with raio's `mark_test.py square`.
    python3 studio/raio/tests/lbrn_square.py --len 100 --power 70 --speed 200 --khz 20 --ns 200 --passes 1
raio coordinates (centre 0,0) → LightBurn's bottom-left origin (+78.75)."""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "trilha"))
from lbrn import LbrnDoc, Layer
ap = argparse.ArgumentParser()
ap.add_argument("--len", type=float, default=100); ap.add_argument("--x", type=float, default=0); ap.add_argument("--y", type=float, default=0)
ap.add_argument("--power", type=float, default=70); ap.add_argument("--speed", type=float, default=200)
ap.add_argument("--khz", type=float, default=20); ap.add_argument("--ns", type=int, default=200); ap.add_argument("--passes", type=int, default=1)
ap.add_argument("--out", default=None)
a = ap.parse_args()
out = a.out or str(Path(__file__).resolve().parent / f"square{a.len:g}-p{a.power:g}-s{a.speed:g}-lightburn.lbrn2")
doc = LbrnDoc(device="B6 Mopa", notes=f"raio side-by-side: {a.len} mm square, {a.power}% {a.speed}mm/s {a.khz}kHz {a.ns}ns x{a.passes}")
layer = doc.add_layer(Layer(index=0, name=f"SQ_{a.power:g}pct", mode="Cut", power=a.power, speed=a.speed, freq=int(a.khz * 1000), passes=a.passes, priority=0, qpulse=a.ns))
doc.add_rect(78.75 + a.x, 78.75 + a.y, a.len, a.len, layer)
print("wrote", doc.save(out))
