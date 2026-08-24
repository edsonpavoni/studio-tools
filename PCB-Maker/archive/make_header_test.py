#!/usr/bin/env python3
"""
make_header_test.py — a real 16-pin header row with the winning recipe.

The recipe is settled: 0.9 mm holes, 100 %, 400 mm/s, 40 kHz, 200 ns, 16 passes,
wobble 0.10/0.02. Run 6 proved it goes through 1.6 mm FR4 with a clean underside, and
that speed rather than passes is what buys the clean exit.

This asks the only remaining question about holes: **does it stay clean for sixteen of
them in a row at real header pitch**, where each hole sits 2.54 mm from the last one's
heat.

Two rows, same recipe, differing ONLY in the order the holes are drilled:

  A  sequential   1,2,3...16, straight along the row. What a normal job does.
  B  interleaved  the odd holes first, then the even ones. Every hole is 5.08 mm from
                  its neighbour while it is being cut, and the even holes only start
                  once the odd ones have had the whole first pass to cool.

If A chars and B does not, the fix for heat accumulation is free: it is ordering, not
power. If both are clean, ignore all of this and use the simple one.

    python3 make_header_test.py

LIFT THE BOARD OFF THE BED. Air assist ON.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lbrn import LbrnDoc, Layer

DIA, PITCH, N = 0.9, 2.54, 16

def hole_layer(doc, idx, name, priority):
    return doc.add_layer(Layer(idx, name, "Cut", 100, 400, 40000, passes=16,
                               priority=priority, qpulse=200,
                               wobble=1, wobble_size=0.10, wobble_step=0.02))

def build():
    doc = LbrnDoc(notes=(
        "16-pin header test, 0.9 mm at 2.54 mm pitch. Both rows use the SAME recipe "
        "(100%, 400 mm/s, 16 passes, wobble 0.10). Row A drills them in order. Row B "
        "drills the odd holes then the even ones, so each hole has 5.08 mm of cool "
        "board beside it while it is cut. LIFT THE BOARD OFF THE BED. Air assist ON."))
    x0 = 8.0
    yA, yB = 24.0, 12.0

    # --- row A: straight through, one layer ---------------------------------
    A = hole_layer(doc, 0, "A_sequential", 0)
    for k in range(N):
        doc.add_circle(x0 + k * PITCH, yA, DIA, A)

    # --- row B: odd holes, then even holes ----------------------------------
    B1 = hole_layer(doc, 1, "B_odd", 1)
    B2 = hole_layer(doc, 2, "B_even", 2)
    for k in range(N):
        doc.add_circle(x0 + k * PITCH, yB, DIA, B1 if k % 2 == 0 else B2)

    # --- labels, feather-light, last -----------------------------------------
    mark = doc.add_layer(Layer(9, "LABELS", "Scan", 20, 1000, 40000, passes=1,
                               priority=9, qpulse=200, interval=0.05))
    doc.add_text(x0 - 6.0, yA + 4.5, "A  in order", mark, height=2.4)
    doc.add_text(x0 - 6.0, yB - 6.0, "B  odds first, then evens", mark, height=2.4)
    return doc

SCORE = """# 16-pin header test — score sheet

Date: ______   Material: Qimoo FR4 1.6 mm   Air assist: ON
**Board lifted off the bed?** yes / no

Recipe, both rows identical: 0.9 mm · 100 % · 400 mm/s · 40 kHz · 200 ns · 16 passes ·
wobble 0.10/0.02. The only difference is drilling order.

## Row A — drilled in order

| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| through? |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| clean back? |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |

**Does it get worse left to right?** yes / no  ← this is the accumulation question

## Row B — odds first, then evens

| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| through? |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| clean back? |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |

**Is B cleaner than A?** yes / no / same

If B is cleaner, interleaving becomes the default in `circuit2lbrn.py` for every board:
it costs nothing but the order the holes are written in.

## Measurements

Hole diameter, three of them: ______ / ______ / ______ mm
**Kerf = measured − 0.900 = ______ mm** ← this goes into the converter

**Does a real 16-pin 2.54 mm header drop in?** yes / tight / no

## Time

Row A took ______ s. Predicted 28 s for 16 holes at 1.78 s each.
"""

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("-o","--outdir",default="coupon")
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, a.outdir); os.makedirs(out, exist_ok=True)
    doc = build()
    p = doc.save(os.path.join(out, "B6-HEADER-16.lbrn2"))
    doc.to_svg(os.path.join(out, "B6-HEADER-16.svg"))
    open(os.path.join(out, "SCORE-HEADER16.md"), "w").write(SCORE)
    xs=[(float(s.find("XForm").text.split()[4]),float(s.find("XForm").text.split()[5])) for s in doc.shapes]
    print("Header test: %s" % p)
    print("2 rows x %d holes of %.1f mm at %.2f mm pitch  (row span %.1f mm)"
          % (N, DIA, PITCH, (N-1)*PITCH))
    print("extent x %.1f..%.1f  y %.1f..%.1f mm"
          % (min(v[0] for v in xs), max(v[0] for v in xs),
             min(v[1] for v in xs), max(v[1] for v in xs)))
    print()
    for l in doc.layers: print("   " + l.describe())
    print("\nEstimated: 1.78 s per hole, so ~28 s per row, ~57 s total.")
    print("Score sheet: %s" % os.path.join(out, "SCORE-HEADER16.md"))
    print("\n*** LIFT THE BOARD OFF THE BED. ***")

if __name__ == "__main__":
    main()
