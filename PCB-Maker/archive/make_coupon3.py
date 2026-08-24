#!/usr/bin/env python3
"""
make_coupon3.py — the dense coupon. One board, every open question.

Written 2026-08-18 after run 1 burned through the FR4 and after reading ComMarker's own
PCB recommendation, which is nothing like the recipe recovered from the 2025 file:

    ComMarker "marking":  100 %, 1000 mm/s, 40 kHz, 200 ns, line space 0.05, 4 passes
    ComMarker "cleaning":  20 %, 1500 mm/s, 100 kHz, 200 ns, line space 0.01, 2 passes
    2025 TRIBE file:        95 %,  200 mm/s, 37 kHz, (default ns), (default space), 1 pass

The important difference is not the numbers, it is the SHAPE: four fast thin passes
instead of one slow heavy one. Same energy, delivered with time to cool, which is
precisely what run 1 lacked when the fill kept cutting after the copper was gone.

    python3 make_coupon3.py

LightBurn allows 30 layers. This uses 28. Every cell is its own layer so the parameter
set is readable in the file afterwards rather than remembered.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lbrn import LbrnDoc, Layer

CELL   = 5.0      # test square, mm
PITCH  = 10.0

# A. the main matrix: speed x passes, spanning our recipe and ComMarker's
SPEEDS = [200, 500, 1000, 1500]
PASSES = [1, 2, 4, 8]
# B. frequency, at ComMarker's centre point
FREQS  = [40, 100]          # trimmed to two, to make room for the hatch-angle test
ANGLE_INC = [0, 13, 45, 90] # ComMarker: rotate the hatch between passes
# C. holes
HOLE_PASSES = [8, 24, 48]
# D. board cutout
CUT_PASSES  = [32, 64]      # run 1 proved 12 is nowhere near enough


def build():
    doc = LbrnDoc(notes=(
        "Coupon 3, dense. A: speed x passes matrix (100%, 40kHz, 200ns, 0.05mm) - the "
        "main question, judge from the BACK. B: frequency. C: hole pass ladder. "
        "D: cutout ladder. E: cleaning pass over an already-cleared square. "
        "No board cutout, the coupon stays attached to the stock."))
    n = [0]
    def layer(name, mode, power, speed, freq, passes=1, ns=200, interval=None,
              angle_per_pass=None):
        L = Layer(n[0], name, mode, power, speed, freq * 1000, passes=passes,
                  priority=n[0], qpulse=ns, interval=interval,
                  angle_per_pass=angle_per_pass)
        n[0] += 1
        return doc.add_layer(L)

    # ---- A. speed x passes, the main matrix -------------------------------
    x0, y0 = 9.0, 66.0
    for r, p in enumerate(PASSES):
        for c, s in enumerate(SPEEDS):
            cx, cy = x0 + c * PITCH, y0 - r * PITCH
            L = layer("%dx%d" % (s, p), "Scan", 100, s, 40, passes=p, interval=0.05)
            doc.add_rect(cx, cy, CELL, CELL, L)
    for c, s in enumerate(SPEEDS):
        doc.add_text(x0 + c * PITCH - 4.5, y0 + 4.5, "%d" % s, doc.layers[c], height=2.2)
    for r, p in enumerate(PASSES):
        doc.add_text(x0 - 8.5, y0 - r * PITCH - 1.0, "%dx" % p,
                     doc.layers[r * len(SPEEDS)], height=2.2)

    # ---- B2. hatch angle rotation between passes ---------------------------
    #    ComMarker's tip: rotating the hatch each pass stops the beam retracing the
    #    same lines and is what makes multi-pass copper removal come out uniform.
    xb = x0 + 4 * PITCH + 5.0
    for r, inc in enumerate(ANGLE_INC):
        cy = y0 - r * PITCH
        L = layer("hatch+%d" % inc, "Scan", 100, 1000, 40, passes=4, interval=0.05,
                  angle_per_pass=inc)
        doc.add_rect(xb, cy, CELL, CELL, L)
        doc.add_text(xb + 3.6, cy - 1.0, "+%d" % inc, L, height=2.2)

    # ---- B. frequency, at ComMarker's centre point -------------------------
    xf = xb + 11.0
    for r, f in enumerate(FREQS):
        cy = y0 - r * PITCH
        L = layer("%dkHz" % f, "Scan", 100, 1000, f, passes=4, interval=0.05,
                  angle_per_pass=13)
        doc.add_rect(xf, cy, CELL, CELL, L)
        doc.add_text(xf + 3.6, cy - 1.0, "%dk" % f, L, height=2.2)

    # ---- E. the cleaning pass, run over its own square ---------------------
    #    20 %, 1500 mm/s, 100 kHz, 0.01 mm, 2 passes. First clear it the ComMarker way,
    #    then clean. Two layers on the same square, in run order.
    xe, ye = xf, y0 - 2 * PITCH
    Lc = layer("clr-base", "Scan", 100, 1000, 40, passes=4, interval=0.05,
               angle_per_pass=13)
    doc.add_rect(xe, ye, CELL, CELL, Lc)
    Ln = layer("CLEAN", "Scan", 20, 1500, 100, passes=2, interval=0.01)
    doc.add_rect(xe, ye, CELL, CELL, Ln)
    doc.add_text(xe - 4.0, ye + 4.5, "clean", Ln, height=2.2)

    # ---- C. hole pass ladder ----------------------------------------------
    yc = y0 - 4 * PITCH - 6.0
    for i, p in enumerate(HOLE_PASSES):
        cx = 12.0 + i * 22.0
        L = layer("H%dx" % p, "Cut", 100, 40, 40, passes=p)
        doc.add_circle(cx, yc, 1.0, L)
        doc.add_circle(cx + 5.0, yc, 2.4, L)
        doc.add_circle(cx + 12.0, yc, 6.6, L)
        doc.add_text(cx - 3.0, yc - 6.0, "hole %dx" % p, L, height=2.2)

    # ---- D. cutout ladder ---------------------------------------------------
    yd = yc - 15.0
    for i, p in enumerate(CUT_PASSES):
        cx = 15.0 + i * 24.0
        L = layer("C%dx" % p, "Cut", 100, 40, 40, passes=p)
        doc.add_rect(cx, yd, 16.0, 7.0, L)
        doc.add_text(cx - 7.0, yd - 6.5, "cut %dx" % p, L, height=2.2)

    return doc, 92.0, 78.0


SCORE = """# Coupon 3 — score sheet

Run date: ______   FR4 thickness: ______   Copper: 35 um / other: ______
Surface: bright / scuffed matte

## ⚠️ AIR ASSIST ON. Run 1 had it off.

Run 1 was done without air assist and produced heavy soot plumes and charring. Air assist
blows the vaporised copper and resin out of the beam path instead of letting it sit there
absorbing the next pulse. **This alone may change the result more than any number below**,
which is exactly why it must be on for every cell here: one variable at a time.

Also: fume extraction. Vaporised copper plus heated epoxy is not something to breathe.

---

## A. Speed x passes — THE question

All at 100 %, 40 kHz, 200 ns, line space 0.05 mm. **Judge from the BACK of the board.**
A cell passes only if the copper is gone on the front AND the FR4 is unscorched behind it.

|            | 200 mm/s | 500 | 1000 | 1500 |
|------------|---|---|---|---|
| **1 pass**  |   |   |   |   |
| **2 passes**|   |   |   |   |
| **4 passes**|   |   |   |   |
| **8 passes**|   |   |   |   |

Mark each cell: `-` copper still there · `OK` clean copper removal, FR4 intact ·
`B` burned into the FR4 · `X` through the board.

**Best cell: ______ mm/s x ______ passes.** That is the production fill recipe.

Run 1 sat at 200 mm/s x 1 pass and went straight to `X`. ComMarker's own PCB
recommendation is the 1000 x 4 cell. If the whole 200 column is `X` and the 1000 column
is `OK`, the lesson is that **four fast passes beat one slow one**, which is the thing
worth writing down.

## B2. Hatch rotation between passes — the ComMarker tip

All at 1000 mm/s, 4 passes, 40 kHz, 0.05 mm. Only the rotation per pass changes.
Without rotation every pass retraces the same lines and leaves ridges between them.

| +0 deg | +13 deg | +45 deg | +90 deg |
|---|---|---|---|
| copper gone? |  |  |  |
| uniform, or striped? |  |  |  |
| FR4 clean behind? |  |  |  |

**Best rotation: ______ deg.** If +0 is visibly striped and the others are not, hatch
rotation becomes a permanent part of the fill recipe.

## B. Frequency, at 1000 mm/s x 4 with +13 deg

| 40 kHz | 100 kHz |
|---|---|
|  |  |

## E. Cleaning pass

The square marked `clean` is cleared the same way as the 40 kHz cell, then given
ComMarker's cleaning pass (20 %, 1500 mm/s, 100 kHz, 0.01 mm, 2 passes).

Compared with the plain 40 kHz square, is it: cleaner / the same / worse? ______
Does it measure open where the plain one does? ______

## C. Holes — 1.0, 2.4 and 6.6 mm at rising passes

| Passes | 8 | 24 | 48 |
|---|---|---|---|
| 1.0 mm through? |  |  |  |
| 2.4 mm through? |  |  |  |
| 6.6 mm through? |  |  |  |

**Passes needed: 1.0 mm ______ · 2.4 mm ______ · 6.6 mm ______**

If big holes need far more passes than small ones, holes must be split into layers by
diameter instead of sharing one recipe the way the 2025 file did.

## D. Cutout

| Passes | 32 | 64 |
|---|---|---|
| released? |  |  |
| edge quality |  |  |

Run 1's 12 passes did not come close, so the ladder starts higher.

## The measurement that decides everything

Meter across every cleared square. **Copper looking gone is not copper being gone.**
A square that reads short still has a conductive film on it.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--outdir", default="coupon")
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, a.outdir); os.makedirs(out, exist_ok=True)
    doc, w, h = build()
    p = doc.save(os.path.join(out, "B6-PCB-COUPON3.lbrn2"))
    doc.to_svg(os.path.join(out, "B6-PCB-COUPON3.svg"))
    open(os.path.join(out, "SCORE3.md"), "w").write(SCORE)
    xs = []
    for sh in doc.shapes:
        xf = sh.find("XForm").text.split()
        xs.append((float(xf[4]), float(xf[5])))
    print("Coupon 3: %s" % p)
    print("layers: %d of the 30 LightBurn allows" % len(doc.layers))
    print("extent: x %.1f..%.1f   y %.1f..%.1f mm"
          % (min(a[0] for a in xs), max(a[0] for a in xs),
             min(a[1] for a in xs), max(a[1] for a in xs)))
    print("\n%d test cells in the speed x passes matrix, %d frequencies, "
          "1 cleaning pair, %d hole groups, %d cutout strips"
          % (len(SPEEDS) * len(PASSES), len(FREQS), len(HOLE_PASSES), len(CUT_PASSES)))
    print("\nScore sheet: %s" % os.path.join(out, "SCORE3.md"))
    print("\n*** Judge the fill cells from the BACK of the board. ***")

if __name__ == "__main__":
    main()
