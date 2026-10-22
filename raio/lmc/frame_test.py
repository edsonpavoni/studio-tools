#!/usr/bin/env python3
"""raio · lmc/frame_test.py — Phase 0.4/0.5: red-light framing. No emission: MO closed, laser bit low, red bit high.

    ~/.venvs/raio/bin/python studio/raio/lmc/frame_test.py rect --w 50 --h 20 --seconds 15
    ~/.venvs/raio/bin/python studio/raio/lmc/frame_test.py L --seconds 15          # 40 mm arm along +x, 20 mm along +y
    ~/.venvs/raio/bin/python studio/raio/lmc/frame_test.py corners --seconds 15    # square at ±70 mm
Mapping flags once 0.4 tells us: --swap --flipx --flipy.  Put a sheet of paper on the bed and a ruler beside it.
"""
import argparse, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lmc import LMC, Busy

ap = argparse.ArgumentParser()
ap.add_argument("shape", choices=["rect", "L", "corners", "centre"])
ap.add_argument("--w", type=float, default=50); ap.add_argument("--h", type=float, default=20)
ap.add_argument("--seconds", type=float, default=15)
ap.add_argument("--swap", action="store_true"); ap.add_argument("--flipx", action="store_true"); ap.add_argument("--flipy", action="store_true")
ap.add_argument("--no-cor", action="store_true", help="skip the correction table (compare straightness)")
a = ap.parse_args()

shapes = {
    "rect":    [(-a.w/2, -a.h/2), (a.w/2, -a.h/2), (a.w/2, a.h/2), (-a.w/2, a.h/2)],
    "L":       [(0, 0), (40, 0), (40, 2), (2, 2), (2, 20), (0, 20)],
    "corners": [(-70, -70), (70, -70), (70, 70), (-70, 70)],
    "centre":  [(-2, 0), (2, 0), (0, 0), (0, -2), (0, 2), (0, 0)],
}
try:
    m = LMC()
except Busy as e:
    sys.exit(str(e))
m.swap, m.sx, m.sy = a.swap, (-1 if a.flipx else 1), (-1 if a.flipy else 1)
try:
    t0 = time.time()
    ident = m.init(cor_path=None if a.no_cor else __import__("lmc").COR_PATH)
    print(f"init ok in {time.time()-t0:.1f}s  serial={['%04x'%w for w in ident['serial']]} version={['%04x'%w for w in ident['version']]}  units/mm={m.u_per_mm:.3f}")
    print(f"red light: {a.shape} for {a.seconds:.0f} s — look at the bed")
    m.red_polyline(shapes[a.shape], seconds=a.seconds)
    print("red off, galvo centred. Measure on the paper and report: width, height, which way the long arm points.")
finally:
    try: m.safe_idle()
    finally: m.close()
