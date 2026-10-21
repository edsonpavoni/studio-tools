#!/usr/bin/env python3
"""
make_material_test.py — a small strip to run on EVERY material, unchanged.

Written 2026-08-18, after the back of the coupon came out charred and blistered while
the back of the 2025 TRIBE board is clean with crisp through-holes. Same laser, same
operator, wildly different substrate behaviour. Before another parameter is tuned, the
material has to be pinned down.

The coupon was run on a board Edson has no more of. The TRIBE board was made on a
different stock he still has. That is a confound big enough to invalidate everything
else, so this strip is deliberately SMALL, about 52 x 34 mm, cheap to repeat, and
identical every time.

    python3 make_material_test.py

Run it once on each material. Same file, same settings, air assist on. Then the
difference between the results IS the material, because nothing else moved.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lbrn import LbrnDoc, Layer

# The three fill recipes worth carrying forward: ComMarker's, a heavier version of it,
# and something between it and the 2025 file.
FILLS = [("A", 1000, 4), ("B", 1000, 8), ("C", 500, 4)]
MOATS = [0.15, 0.25, 0.40]

def build():
    doc = LbrnDoc(notes=(
        "MATERIAL TEST. Run unchanged on every board type, air assist ON, and label the "
        "back of each piece with a marker before you start. A/B/C are fill recipes at "
        "100%, 40kHz, 200ns, 0.05mm, hatch +13 deg/pass. Then moats, then holes at two "
        "pass counts, then a cut strip. Judge the fills and holes from the BACK."))
    n = [0]
    def layer(name, mode, power, speed, freq, passes=1, interval=None, apc=None):
        L = Layer(n[0], name, mode, power, speed, freq * 1000, passes=passes,
                  priority=n[0], qpulse=200, interval=interval, angle_per_pass=apc)
        n[0] += 1
        return doc.add_layer(L)

    # fills, top row
    for i, (tag, spd, ps) in enumerate(FILLS):
        cx, cy = 8.0 + i * 11.0, 27.0
        L = layer("fill%s" % tag, "Scan", 100, spd, 40, passes=ps,
                  interval=0.05, apc=13)
        doc.add_rect(cx, cy, 5.0, 5.0, L)
        doc.add_text(cx - 4.5, cy - 4.5, tag, L, height=2.4)

    # moats, top right
    Lm = layer("moats", "Scan", 100, 1000, 40, passes=4, interval=0.05, apc=13)
    for j, w in enumerate(MOATS):
        doc.add_rect(44.0, 29.0 - j * 2.6, 12.0, w, Lm)
    doc.add_text(37.0, 20.5, "moat", Lm, height=2.2)

    # holes, two pass counts
    for i, ps in enumerate([24, 48]):
        L = layer("hole%d" % ps, "Cut", 100, 40, 40, passes=ps)
        y = 15.0 - i * 7.0
        doc.add_circle(9.0, y, 1.0, L)
        doc.add_circle(14.0, y, 2.4, L)
        doc.add_circle(21.0, y, 6.6, L)
        doc.add_text(1.5, y - 1.0, "%dx" % ps, L, height=2.4)

    # cut strip
    Lc = layer("cut48", "Cut", 100, 40, 40, passes=48)
    doc.add_rect(40.0, 10.0, 16.0, 8.0, Lc)
    doc.add_text(33.0, 4.0, "cut 48x", Lc, height=2.2)
    return doc

SCORE = """# Material test — one sheet per board type

Fill in one of these for EACH material. Everything is identical between runs, so any
difference in the results is the material and nothing else.

**Material:** 1 / 2 / 3 / 4  ·  **What it is:** ______________________
**Thickness (calipers):** ______ mm   **Copper side(s):** one / both
**Colour of the substrate at a cut edge:** ______________
**Air assist:** ON   **Date:** ______

---

## The one measurement that matters most

**Substrate thickness.** Measure it with calipers before you run. 0.8 mm and 1.6 mm FR4
behave completely differently under a drilling pass, and it is the single easiest thing
to get wrong when comparing two boards by eye. The 2025 board and the coupon may simply
not be the same thickness.

---

## Fills — judge from the BACK

| | A · 1000 mm/s x4 | B · 1000 x8 | C · 500 x4 |
|---|---|---|---|
| copper gone, front? |  |  |  |
| substrate clean, back? |  |  |  |
| reads open on a meter? |  |  |  |

## Moats — 0.15 / 0.25 / 0.40 mm

| 0.15 | 0.25 | 0.40 |
|---|---|---|
| reads open? |  |  |  |

## Holes — through, and how clean

| | 1.0 mm | 2.4 mm | 6.6 mm |
|---|---|---|---|
| 24 passes: through? |  |  |  |
| 24 passes: charring? |  |  |  |
| 48 passes: through? |  |  |  |
| 48 passes: charring? |  |  |  |

**Compare directly against the TRIBE board's holes**, which are clean and crisp on the
back with no charring. That is the standard. If a material cannot reach it at any pass
count, that material is wrong for this process, not the settings.

## Cut strip, 48 passes

Released? ______  Edge quality: ______

---

## Verdict for this material

Usable / marginal / no.  Why: ______________________________________
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--outdir", default="coupon")
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, a.outdir); os.makedirs(out, exist_ok=True)
    doc = build()
    p = doc.save(os.path.join(out, "B6-MATERIAL-TEST.lbrn2"))
    doc.to_svg(os.path.join(out, "B6-MATERIAL-TEST.svg"))
    open(os.path.join(out, "SCORE-MATERIAL.md"), "w").write(SCORE)
    xs = [(float(sh.find("XForm").text.split()[4]),
           float(sh.find("XForm").text.split()[5])) for sh in doc.shapes]
    print("Material test: %s" % p)
    print("layers: %d   extent: x %.1f..%.1f  y %.1f..%.1f mm"
          % (len(doc.layers), min(a[0] for a in xs), max(a[0] for a in xs),
             min(a[1] for a in xs), max(a[1] for a in xs)))
    print("\nRun it UNCHANGED on each material. Air assist ON. Label the back first.")
    print("Score sheet (one copy per material): %s"
          % os.path.join(out, "SCORE-MATERIAL.md"))

if __name__ == "__main__":
    main()
