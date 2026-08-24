#!/usr/bin/env python3
"""
make_hole_line.py — 30 holes in a row at 2.54 mm pitch, ten recipes, three holes each.

Written 2026-08-18. Run 5 proved wobble halves the passes (8 with, 16 without) but the
coupon was thermally crowded and slow. This one fixes both problems:

  * ONE hole size, 0.9 mm, which is what a 2.54 mm pin header actually needs and is the
    size the 2025 TRIBE board used for 38 of its 59 holes.
  * Real header pitch, so consecutive holes heat each other exactly as they will on a
    board. That is the condition that matters, not an isolated hole with 20 mm of copper
    around it.
  * Fast recipes only. The 64-pass survivor from run 5 is excluded on purpose: it works
    and it is eight times slower for no benefit.
  * Every recipe draws the SAME diameter, so measuring the finished holes gives the kerf
    per setting directly.

    python3 make_hole_line.py

Lift the board off the bed before running this. The exit-side charring in run 5 is at
least partly the beam bouncing off the fixture.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lbrn import LbrnDoc, Layer

DIA   = 0.9       # a 2.54 mm header pin wants ~0.9-1.0 mm
PITCH = 2.54
PER   = 3

# (label, power, speed, passes, wobble size, wobble step)  wobble size None = off
# Ordered fastest-first. The run-5 winner is included as the control, at the end.
RECIPES = [
    ("400/16 w10",  100, 400, 16, 0.10, 0.02),
    ("400/32 w10",  100, 400, 32, 0.10, 0.02),
    ("200/8 w10",   100, 200,  8, 0.10, 0.02),
    ("200/16 w10",  100, 200, 16, 0.10, 0.02),
    ("200/16 w20",  100, 200, 16, 0.20, 0.03),
    ("100/8 w10",   100, 100,  8, 0.10, 0.02),
    ("100/16 w10",  100, 100, 16, 0.10, 0.02),
    ("100/8 w05",   100, 100,  8, 0.05, 0.02),
    ("100/16 none", 100, 100, 16, None, None),
    ("40/8 w10",    100,  40,  8, 0.10, 0.02),   # run 5 winner, the control
]

def build():
    doc = LbrnDoc(notes=(
        "30 holes, 0.9 mm, 2.54 mm pitch. Ten recipes, three holes each, left to right "
        "in the order listed in SCORE-HOLELINE.md. Fastest first; the run-5 winner "
        "(40 mm/s, 8x, wobble 0.10) is the LAST group, as the control. "
        "LIFT THE BOARD OFF THE BED. Air assist ON."))
    n = [0]
    labels = []
    x0, y = 6.0, 26.0
    for i, (lbl, pwr, spd, ps, ws, wst) in enumerate(RECIPES):
        L = Layer(n[0], "%02d_%s" % (i + 1, lbl.replace(" ", "_")), "Cut",
                  pwr, spd, 40000, passes=ps, priority=n[0], qpulse=200,
                  wobble=(1 if ws else None), wobble_size=ws, wobble_step=wst)
        n[0] += 1
        doc.add_layer(L)
        for k in range(PER):
            doc.add_circle(x0 + (i * PER + k) * PITCH, y, DIA, L)
        # Label goes on its own FEATHER-LIGHT layer, created below. Putting it on the
        # hole layer, as run 6 did, engraves the character with a drilling recipe and
        # dumps more heat beside the group than the group itself.
        labels.append((x0 + i * PER * PITCH - 1.0,
                       y + (5.0 if i % 2 == 0 else 10.0), "%d" % (i + 1)))
    # One light marking layer for every label on the sheet. 20 %, fast, single pass:
    # enough to read, nowhere near enough to heat the board.
    mark = doc.add_layer(Layer(n[0], "LABELS", "Scan", 20, 1000, 40000,
                               passes=1, priority=n[0], qpulse=200, interval=0.05))
    n[0] += 1
    for lx, ly, txt in labels:
        doc.add_text(lx, ly, txt, mark, height=2.6)

    # a ruler line under the row so the pitch can be checked against a real header
    ruler = doc.add_layer(Layer(n[0], "REF_pitch", "Cut", 100, 40, 40000,
                                passes=8, priority=n[0], qpulse=200,
                                wobble=1, wobble_size=0.10, wobble_step=0.02))
    for k in (0, 29):
        doc.add_circle(x0 + k * PITCH, y - 8.0, DIA, ruler)
    doc.add_text(x0 + 12 * PITCH, y - 13.0,
                 "ends of a 30-pin 2.54mm header", mark, height=2.4)
    return doc

SCORE = """# Hole line — score sheet

Date: ______  Material: Qimoo FR4 1.6 mm  Air assist: ON
**Board lifted off the bed?** yes / no  ← if no, stop and lift it

30 holes, all drawn at **0.9 mm**, at **2.54 mm** pitch. Three holes per recipe, groups
numbered 1-10 left to right. Same diameter everywhere, so the measured hole minus 0.9 mm
IS the kerf for that recipe.

| # | recipe | through? | clean? | measured Ø | kerf | header pin fits? |
|---|---|---|---|---|---|---|
| 1 | 400 mm/s · 16x · wobble 0.10 |  |  |  |  |  |
| 2 | 400 mm/s · 32x · wobble 0.10 |  |  |  |  |  |
| 3 | 200 mm/s · 8x · wobble 0.10 |  |  |  |  |  |
| 4 | 200 mm/s · 16x · wobble 0.10 |  |  |  |  |  |
| 5 | 200 mm/s · 16x · wobble 0.20 |  |  |  |  |  |
| 6 | 100 mm/s · 8x · wobble 0.10 |  |  |  |  |  |
| 7 | 100 mm/s · 16x · wobble 0.10 |  |  |  |  |  |
| 8 | 100 mm/s · 8x · wobble 0.05 |  |  |  |  |  |
| 9 | 100 mm/s · 16x · NO wobble |  |  |  |  |  |
| 10 | 40 mm/s · 8x · wobble 0.10 — **run 5 control** |  |  |  |  |  |

All at 100 %, 40 kHz, 200 ns.

## What each comparison answers

**1 vs 2** — does doubling passes at 400 mm/s matter, or is 400 simply too fast?
**3 vs 6 vs 10** — 8 passes at 200 / 100 / 40 mm/s. How fast can the winner go?
**4 vs 5** — wobble 0.10 against 0.20 at the same speed and passes.
**6 vs 8** — wobble 0.10 against a tighter 0.05. Smaller wobble should mean a tighter
hole; does it still get through?
**7 vs 9** — the wobble question again, at speed. Run 5 answered it at 40 mm/s.

## The two numbers that decide it

**Kerf.** Measured Ø minus 0.9. Wobble widens the hole, and that offset has to go into
`circuit2lbrn.py` or every hole on a real board is oversize. If wobble 0.20 gives a much
larger kerf than 0.10, that is a reason to prefer 0.10 beyond speed.

**Fit.** Push a real 2.54 mm pin header into the holes. Through and clean is not the same
as usable.

## Also worth writing down

Did the row char progressively from left to right as heat accumulated? On a real header
the holes are this close together, so if group 10 looks worse than group 1 purely from
position, that is a spacing problem the recipe cannot fix and the answer is a pause
between holes rather than a different setting.

Fastest recipe that is through, clean and fits: ______________________
"""

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("-o","--outdir",default="coupon")
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, a.outdir); os.makedirs(out, exist_ok=True)
    doc = build()
    p = doc.save(os.path.join(out, "B6-HOLE-LINE.lbrn2"))
    doc.to_svg(os.path.join(out, "B6-HOLE-LINE.svg"))
    open(os.path.join(out, "SCORE-HOLELINE.md"), "w").write(SCORE)
    xs=[(float(s.find("XForm").text.split()[4]),float(s.find("XForm").text.split()[5])) for s in doc.shapes]
    print("Hole line: %s" % p)
    print("30 holes of %.1f mm at %.2f mm pitch, %d recipes, %d layers"
          % (DIA, PITCH, len(RECIPES), len(doc.layers)))
    print("extent x %.1f..%.1f  y %.1f..%.1f mm"
          % (min(v[0] for v in xs), max(v[0] for v in xs),
             min(v[1] for v in xs), max(v[1] for v in xs)))
    print()
    for l in doc.layers[:-1]: print("   " + l.describe())
    print("\nScore sheet: %s" % os.path.join(out, "SCORE-HOLELINE.md"))
    print("\n*** LIFT THE BOARD OFF THE BED before running. ***")

if __name__ == "__main__":
    main()
