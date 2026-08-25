#!/usr/bin/env python3
"""
make_coupon4.py — the low-energy coupon. Written 2026-08-18 after run 3.

Run 3 held power at 100 % for every one of its 26 cells, which in hindsight was the one
knob that should not have been fixed. What it did prove is the direction:

    200 mm/s  charred black at every pass count
    1500 mm/s the best column on the board
    1500 x 4  copper gone, glass weave visible, the closest thing to a real result
    100 kHz   worse than 40 kHz
    24 / 48 pass holes and 32 / 64 pass cuts: flames, and craters of char

So this coupon goes **faster and weaker**, and starts the hole and cut ladders far below
anything that caught fire.

    python3 make_coupon4.py

Held constant: 40 kHz, 200 ns, 0.05 mm line space, hatch +13 deg per pass, 4 passes on
the fills. Only power and speed move.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lbrn import LbrnDoc, Layer

POWERS = [25, 50, 75]                  # never tested before. 100 % was always assumed.
SPEEDS = [1000, 1500, 2000, 3000]      # run 3's best column was 1500, so push past it
MOATS  = [0.15, 0.25, 0.40]
HOLE_PASSES = [4, 8, 16]               # 24 and 48 caught fire
CUT_PASSES  = [8, 16]                  # 32 and 64 caught fire
CELL, PITCH = 5.0, 10.0

def build():
    doc = LbrnDoc(notes=(
        "Coupon 4, low energy. Fills: power x speed at 4 passes, 40kHz, 200ns, 0.05mm, "
        "hatch +13. Run 3 showed 100% power is far too much and that speed is the "
        "dominant variable. Holes and cuts start much lower: run 3 caught fire at 24 "
        "passes. Air assist ON. Judge the fills from the BACK and with a meter."))
    n = [0]
    def layer(name, mode, power, speed, passes=1, interval=None, apc=None, freq=40):
        L = Layer(n[0], name, mode, power, speed, freq * 1000, passes=passes,
                  priority=n[0], qpulse=200, interval=interval, angle_per_pass=apc)
        n[0] += 1
        return doc.add_layer(L)

    x0, y0 = 12.0, 60.0
    # ---- power x speed matrix ------------------------------------------------
    for r, p in enumerate(POWERS):
        for c, s in enumerate(SPEEDS):
            cx, cy = x0 + c * PITCH, y0 - r * PITCH
            L = layer("P%dS%d" % (p, s), "Scan", p, s, passes=4, interval=0.05, apc=13)
            doc.add_rect(cx, cy, CELL, CELL, L)
    for c, s in enumerate(SPEEDS):
        doc.add_text(x0 + c * PITCH - 4.5, y0 + 4.8, "%d" % s, doc.layers[c], height=2.2)
    for r, p in enumerate(POWERS):
        doc.add_text(x0 - 10.0, y0 - r * PITCH - 1.0, "%d%%" % p,
                     doc.layers[r * len(SPEEDS)], height=2.4)

    # ---- moats at the middle of the matrix -----------------------------------
    Lm = layer("moats", "Scan", 50, 1500, passes=4, interval=0.05, apc=13)
    for j, w in enumerate(MOATS):
        doc.add_rect(x0 + 1.5 * PITCH, y0 - 3 * PITCH - j * 3.0, 22.0, w, Lm)
    doc.add_text(x0 - 10.0, y0 - 3 * PITCH - 3.0, "moat", Lm, height=2.4)

    # ---- holes, starting far lower -------------------------------------------
    yh = y0 - 4 * PITCH - 4.0
    for i, ps in enumerate(HOLE_PASSES):
        L = layer("H%dx" % ps, "Cut", 100, 40, passes=ps)
        y = yh - i * 9.0
        doc.add_circle(10.0, y, 1.0, L)
        doc.add_circle(15.0, y, 2.4, L)
        doc.add_circle(22.0, y, 6.6, L)
        doc.add_text(1.0, y - 1.0, "%dx" % ps, L, height=2.4)

    # ---- cuts ----------------------------------------------------------------
    for i, ps in enumerate(CUT_PASSES):
        L = layer("C%dx" % ps, "Cut", 100, 40, passes=ps)
        cx = 38.0 + i * 22.0
        doc.add_rect(cx, yh - 9.0, 16.0, 7.0, L)
        doc.add_text(cx - 7.0, yh - 15.0, "cut %dx" % ps, L, height=2.2)

    return doc

SCORE = """# Coupon 4 — score sheet

Run date: ______   Material: Qimoo FR4   Thickness: ______ mm   Air assist: ON

Everything below is at 40 kHz, 200 ns, 0.05 mm line space, hatch +13 deg/pass,
4 passes on the fills. **Only power and speed move.**

---

## The matrix — power x speed

Mark each cell: `-` copper still there · `OK` copper gone, substrate clean ·
`B` substrate browned · `X` burned through.

|        | 1000 mm/s | 1500 | 2000 | 3000 |
|--------|---|---|---|---|
| **25 %** |  |  |  |  |
| **50 %** |  |  |  |  |
| **75 %** |  |  |  |  |

Then the measurement that actually decides it — **meter across each square**:

|        | 1000 | 1500 | 2000 | 3000 |
|--------|---|---|---|---|
| **25 %** |  |  |  |  |
| **50 %** |  |  |  |  |
| **75 %** |  |  |  |  |

**Best cell: ______ % at ______ mm/s.**

For reference, run 3 at 100 % gave: 200 mm/s charred at every pass count, 1500 x 4 the
best of a bad set. If the whole of this coupon reads `-` because it is now too weak, the
answer sits between this and run 3 and we bracket again. **That is a good outcome, not a
failure — it means the window has been found from both sides.**

## Moats, at 50 % / 1500

| 0.15 mm | 0.25 mm | 0.40 mm |
|---|---|---|
| reads open? |  |  |  |

## Holes — 1.0 / 2.4 / 6.6 mm

Run 3 used 24 and 48 passes and produced flames and char craters.

| Passes | 4 | 8 | 16 |
|---|---|---|---|
| 1.0 mm through? |  |  |  |
| 2.4 mm through? |  |  |  |
| 6.6 mm through? |  |  |  |
| char around the hole? |  |  |  |

**Fewest passes that goes through cleanly: 1.0 ____ · 2.4 ____ · 6.6 ____**

## Cuts

| Passes | 8 | 16 |
|---|---|---|
| released? |  |  |
| char? |  |  |

## Did anything catch fire this time?

If yes, at which layer: ______________  If no, say so — that is a result too.
"""

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("-o","--outdir",default="coupon")
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, a.outdir); os.makedirs(out, exist_ok=True)
    doc = build()
    p = doc.save(os.path.join(out, "B6-PCB-COUPON4.lbrn2"))
    doc.to_svg(os.path.join(out, "B6-PCB-COUPON4.svg"))
    open(os.path.join(out, "SCORE4.md"), "w").write(SCORE)
    xs=[(float(s.find("XForm").text.split()[4]),float(s.find("XForm").text.split()[5])) for s in doc.shapes]
    print("Coupon 4: %s" % p)
    print("layers %d   extent x %.1f..%.1f  y %.1f..%.1f mm"
          % (len(doc.layers), min(v[0] for v in xs), max(v[0] for v in xs),
             min(v[1] for v in xs), max(v[1] for v in xs)))
    print("\n12 fill cells (3 powers x 4 speeds), 3 moats, 3 hole groups, 2 cut strips")
    print("Score sheet: %s" % os.path.join(out, "SCORE4.md"))

if __name__ == "__main__":
    main()
