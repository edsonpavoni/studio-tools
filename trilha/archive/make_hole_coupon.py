#!/usr/bin/env python3
"""
make_hole_coupon.py — holes only. Written 2026-08-18 at Edson's request.

The fill recipe is settled (75 %, 1500 mm/s, 4 passes — measured with a meter, coupon 4).
Holes are not, and they are the dangerous part: every run so far has produced its flame
and most of its smoke during the hole layers. Getting them right matters more than
getting them fast.

Edson's suggestion drives this coupon: **wobble**. When cutting thick metal he uses it
routinely, and his own 1.1 mm copper recipe depends on it for melt evacuation. The beam
traces a small circle as it advances, so the energy is smeared along a wider kerf instead
of being dumped into one spot. For a 0.6 mm hole in 1.6 mm FR4, where the beam is
essentially standing still and drilling, that is exactly the problem worth attacking.

    python3 make_hole_coupon.py

Four hole sizes per cell: 0.6, 1.0, 2.4, 6.6 mm.
Three wobble settings x three pass counts, plus two slow-and-gentle variants.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lbrn import LbrnDoc, Layer

SIZES = [0.6, 1.0, 2.4, 6.6]
# (label, wobble on, size mm, step mm)
WOBBLE = [("none", None, None, None),
          ("w10",  1,   0.10, 0.02),
          ("w20",  1,   0.20, 0.03)]
PASSES = [8, 16, 24]

def build():
    doc = LbrnDoc(notes=(
        "HOLE COUPON. Rows: no wobble / wobble 0.10 / wobble 0.20. Columns: 8 / 16 / 24 "
        "passes. Each cell has 0.6, 1.0, 2.4 and 6.6 mm holes. Bottom row: gentler, "
        "100 mm/s and 60 % power with wobble. All 40 kHz, 200 ns, air assist ON. "
        "Record WHERE the flame happens, not just what went through."))
    n = [0]
    def layer(name, power, speed, passes, wob):
        lbl, on, size, step = wob
        L = Layer(n[0], name, "Cut", power, speed, 40000, passes=passes,
                  priority=n[0], qpulse=200,
                  wobble=on, wobble_size=size, wobble_step=step)
        n[0] += 1
        return doc.add_layer(L)

    def group(cx, cy, L):
        x = cx
        for d in SIZES:
            doc.add_circle(x + d / 2, cy, d, L)
            x += d + 2.2

    y = 62.0
    for wob in WOBBLE:
        x = 10.0
        for ps in PASSES:
            L = layer("%s-%dx" % (wob[0], ps), 100, 40, ps, wob)
            group(x, y, L)
            doc.add_text(x, y + 5.5, "%s %dx" % (wob[0], ps), L, height=2.2)
            x += 24.0
        y -= 14.0

    # gentler variants: more speed, less power, wobble on. Fewer flames, more passes.
    y -= 4.0
    for i, (spd, pwr, ps) in enumerate([(100, 60, 32), (100, 60, 64)]):
        L = layer("slow%d-%dx" % (pwr, ps), pwr, spd, ps, WOBBLE[1])
        group(10.0 + i * 34.0, y, L)
        doc.add_text(10.0 + i * 34.0, y + 5.5, "%d%% %dmm/s %dx" % (pwr, spd, ps),
                     L, height=2.2)
    return doc

SCORE = """# Hole coupon — score sheet

Date: ______  Material: Qimoo FR4  Thickness: ______ mm  Air assist: ON

Fill recipe is already settled: 75 %, 1500 mm/s, 4 passes, 40 kHz, 0.05 mm, hatch +13.
This coupon is only about holes, which is where every flame so far has happened.

---

## Through, per size

Mark `-` not through · `OK` through and clean · `C` through but charred · `F` flame seen.

| | 0.6 mm | 1.0 mm | 2.4 mm | 6.6 mm |
|---|---|---|---|---|
| no wobble, 8x |  |  |  |  |
| no wobble, 16x |  |  |  |  |
| no wobble, 24x |  |  |  |  |
| wobble 0.10, 8x |  |  |  |  |
| wobble 0.10, 16x |  |  |  |  |
| wobble 0.10, 24x |  |  |  |  |
| wobble 0.20, 8x |  |  |  |  |
| wobble 0.20, 16x |  |  |  |  |
| wobble 0.20, 24x |  |  |  |  |
| 60 % 100 mm/s 32x |  |  |  |  |
| 60 % 100 mm/s 64x |  |  |  |  |

## The two questions this coupon exists to answer

**1. Does wobble reduce the fire?** Compare the no-wobble rows against the wobble rows at
the same pass count. Watch the job, not just the result.

**2. Does wobble let you use fewer passes?** If wobble 0.10 at 8 passes matches no-wobble
at 16, that halves the time and the heat.

## Hole diameter, measured

Wobble widens the kerf, so a wobbled hole comes out larger than drawn. Measure a few and
work out the offset, because that number has to be subtracted from the drawn diameter in
`circuit2lbrn.py` or every hole on a real board will be oversize.

| drawn | 0.6 | 1.0 | 2.4 | 6.6 |
|---|---|---|---|---|
| measured, no wobble |  |  |  |  |
| measured, wobble 0.10 |  |  |  |  |
| measured, wobble 0.20 |  |  |  |  |

**Kerf offset to apply: ______ mm**

## Winner

Setting: ______________________  Passes: ______  Wobble: ______
Flame? ______  Char? ______
"""

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("-o","--outdir",default="coupon")
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, a.outdir); os.makedirs(out, exist_ok=True)
    doc = build()
    p = doc.save(os.path.join(out, "B6-HOLE-COUPON.lbrn2"))
    doc.to_svg(os.path.join(out, "B6-HOLE-COUPON.svg"))
    open(os.path.join(out, "SCORE-HOLES.md"), "w").write(SCORE)
    xs=[(float(s.find("XForm").text.split()[4]),float(s.find("XForm").text.split()[5])) for s in doc.shapes]
    print("Hole coupon: %s" % p)
    print("layers %d   extent x %.1f..%.1f  y %.1f..%.1f mm"
          % (len(doc.layers), min(v[0] for v in xs), max(v[0] for v in xs),
             min(v[1] for v in xs), max(v[1] for v in xs)))
    print()
    for l in doc.layers: print("   " + l.describe())
    print("\nScore sheet: %s" % os.path.join(out, "SCORE-HOLES.md"))

if __name__ == "__main__":
    main()
