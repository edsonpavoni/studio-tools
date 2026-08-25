#!/usr/bin/env python3
"""
make_coupon2.py — the second coupon, written after run 1 on 2026-08-18.

Run 1 found that one set of numbers was simultaneously far too hot for an area fill
(the 6 mm field burned clean through the FR4) and far too cold for a cut (the 6.6 mm
hole and the board outline were only scribed). So this coupon stops testing pulse width
and ladders the two things that were actually wrong, in opposite directions.

    python3 make_coupon2.py                    # defaults below
    python3 make_coupon2.py --ns 350           # at the pulse width run 1 favoured

LEFT   field energy ladder  — six 6 mm squares at descending power. Find the highest
                              power that removes copper and leaves the FR4 intact.
RIGHT  cut depth ladder     — the same 1.0 mm hole and 6.6 mm circle at rising pass
                              counts. Find what it actually takes to get through.
BOTTOM cutout ladder        — short strips at rising pass counts, for the board edge.

Everything else is held at the archive values: 200 mm/s, 37 kHz, interval 0.1 mm.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lbrn import LbrnDoc, Layer

FIELD_POWERS = [95, 70, 50, 35, 25, 15]        # %, the thing that burned through
HOLE_PASSES  = [8, 16, 32, 64]                 # the thing that would not go through
CUT_PASSES   = [12, 24, 48]                    # board outline
FIELD = 6.0

def build(ns, interval, speed):
    doc = LbrnDoc(notes=(
        "Coupon 2, after the 2026-08-18 run. LEFT: field power ladder, find the highest "
        "power that clears copper WITHOUT burning the FR4 (check the BACK of the board). "
        "RIGHT: hole pass ladder. BOTTOM: cutout pass ladder. All at %d ns, %g mm/s, "
        "interval %g mm." % (ns, speed, interval)))
    W, H = 92.0, 76.0
    idx = 0
    def nxt():
        nonlocal idx; idx += 1; return idx

    # ---- LEFT: field power ladder -------------------------------------------
    x = 8.0
    for row, p in enumerate(FIELD_POWERS):
        col, r = row % 2, row // 2
        cx = x + col * 14.0
        cy = H - 12.0 - r * 14.0
        L = doc.add_layer(Layer(nxt(), "F%d" % p, "Scan", p, speed, 37000,
                                passes=1, priority=idx, qpulse=ns, interval=interval))
        doc.add_rect(cx, cy, FIELD, FIELD, L)
        doc.add_text(cx - 5.0, cy - 5.6, "%d%%" % p, L, height=2.4)

    # ---- RIGHT: hole pass ladder --------------------------------------------
    x = 46.0
    for i, n in enumerate(HOLE_PASSES):
        cx = x + (i % 2) * 18.0
        cy = H - 12.0 - (i // 2) * 20.0
        L = doc.add_layer(Layer(nxt(), "H%dx" % n, "Cut", 100, 40, 37000,
                                passes=n, priority=idx, qpulse=ns))
        doc.add_circle(cx, cy, 1.0, L)
        doc.add_circle(cx + 6.0, cy, 6.6, L)
        doc.add_text(cx - 3.0, cy - 6.0, "%dx" % n, L, height=2.4)

    # ---- BOTTOM: cutout pass ladder -----------------------------------------
    for i, n in enumerate(CUT_PASSES):
        cy = 12.0
        cx = 12.0 + i * 26.0
        L = doc.add_layer(Layer(nxt(), "C%dx" % n, "Cut", 100, 40, 37000,
                                passes=n, priority=idx, qpulse=ns))
        doc.add_rect(cx, cy, 14.0, 8.0, L)
        doc.add_text(cx - 6.0, cy - 7.0, "cut %dx" % n, L, height=2.4)

    # NOTE: deliberately no board cutout layer. Run 1 could not cut the outline anyway,
    # and leaving the coupon attached to the stock keeps it registered for a second run.
    return doc, W, H

SCORE = """# Coupon 2 — score sheet

Run date: ____________   FR4 thickness: ______   Pulse width used: ______ ns
Line interval: ______ mm

## 1. Field power ladder — THE question

**Look at the BACK of the board for each square, not the front.**

| Power | 95 % | 70 % | 50 % | 35 % | 25 % | 15 % |
|---|---|---|---|---|---|---|
| copper gone on the front? |  |  |  |  |  |  |
| FR4 scorched on the back? |  |  |  |  |  |  |
| resistance across the square |  |  |  |  |  |  |

**Highest power where copper is gone AND the back is clean: ______ %.**
That number is the production fill power. Write it into `B6-PCB-RECIPE.md` with today's date.

If NO power satisfies both, the full-field clear is off the table on this machine and the
pipeline switches to isolation moats only. That is not a defeat — run 1 already proved the
moats cut cleanly at every width from 0.10 to 0.40 mm, and moats are far faster anyway.

## 2. Hole pass ladder

| Passes | 8 | 16 | 32 | 64 |
|---|---|---|---|---|
| 1.0 mm hole through? |  |  |  |  |
| 6.6 mm circle through? |  |  |  |  |

**Passes needed for a clean 1.0 mm hole: ______   for 6.6 mm: ______**

If the big circle needs far more than the small hole, holes should be sized into
separate layers by diameter rather than all sharing one recipe the way the 2025 file did.

## 3. Cutout pass ladder

| Passes | 12 | 24 | 48 |
|---|---|---|---|
| released from the stock? |  |  |  |
| edge quality |  |  |  |

**Passes for a clean board edge: ______**

## 4. Anything that caught fire, smoked badly, or surprised you
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", type=int, default=350, help="pulse width, ns")
    ap.add_argument("--interval", type=float, default=0.1, help="line interval, mm")
    ap.add_argument("--speed", type=float, default=200.0, help="scan speed, mm/s")
    ap.add_argument("-o", "--outdir", default="coupon")
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, a.outdir); os.makedirs(out, exist_ok=True)
    doc, w, h = build(a.ns, a.interval, a.speed)
    p = doc.save(os.path.join(out, "B6-PCB-COUPON2.lbrn2"))
    doc.to_svg(os.path.join(out, "B6-PCB-COUPON2.svg"))
    open(os.path.join(out, "SCORE2.md"), "w").write(SCORE)
    print("Coupon 2: %s" % p)
    print("Board %.0f x %.0f mm, %d layers\n" % (w, h, len(doc.layers)))
    print(doc.summary())
    print("\nScore sheet: %s" % os.path.join(out, "SCORE2.md"))
    print("\n*** Check the BACK of the board for each field square. That is the whole test. ***")

if __name__ == "__main__":
    main()
