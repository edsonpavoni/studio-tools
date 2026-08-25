#!/usr/bin/env python3
"""
make_cut_test.py — the board cutout, tested properly, with cooling designed in.

CUTOUT is the last unmeasured layer. It sits at 40 mm/s, which is the slowest and most
heat-concentrating setting left on the board, and everything learned today says that is
the wrong direction. 16 passes did not release the strip, 64 caught fire without wobble.

Two of Edson's ideas drive this:

**Tapered wobble.** His manual technique for thick metal: start wide so the kerf opens
up and the vapour has somewhere to go, then narrow it progressively so the energy
concentrates at the bottom of the trench as it deepens. A wide wobble that never narrows
wastes energy on the walls; a narrow one that never widens chokes on its own debris.

**Cooling between tests.** Every coupon so far has been partly invalidated by the board
being hot from the previous test. So this generates ONE FILE PER TEST, each with its
square already positioned. Run one, wait, run the next. The board cools in between and
nothing contaminates anything.

    python3 make_cut_test.py

Six files plus a preview of all six together.
"""
import argparse, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lbrn import LbrnDoc, Layer

SQ = 10.0          # square side, mm
COLS, PITCH_X, PITCH_Y = 3, 26.0, 30.0
X0, Y0 = 16.0, 44.0

# (id, label, speed, [(wobble_size, wobble_step, passes), ...])
# A single tuple in the list = fixed wobble. Several = a taper, run in order.
TESTS = [
    ("01", "taper 40",    40, [(0.30, 0.04, 8), (0.20, 0.03, 8),
                               (0.10, 0.02, 8), (0.05, 0.02, 8)]),
    ("02", "taper 400",  400, [(0.30, 0.04, 16), (0.20, 0.03, 16),
                               (0.10, 0.02, 16), (0.05, 0.02, 16)]),
    ("03", "w20 40",      40, [(0.20, 0.03, 32)]),
    ("04", "w10 400",    400, [(0.10, 0.02, 64)]),
    ("05", "w10 40",      40, [(0.10, 0.02, 32)]),   # the current guess, as control
    ("06", "none 40",     40, [(None, None, 32)]),   # no wobble, as control
]

def pos(i):
    return X0 + (i % COLS) * PITCH_X, Y0 - (i // COLS) * PITCH_Y

def est_seconds(speed, stages):
    per = 4 * SQ
    t = 0.0
    for ws, wst, ps in stages:
        mult = (math.pi * ws / wst) if ws else 1.0
        t += per * mult * ps / speed
    return t

def add_test(doc, i, tid, label, speed, stages, with_label=True):
    cx, cy = pos(i)
    n = 0
    for j, (ws, wst, ps) in enumerate(stages):
        nm = "%s_%s" % (tid, ("w%.2f" % ws).replace("0.", ".") if ws else "nowob")
        L = doc.add_layer(Layer(len(doc.layers), nm, "Cut", 100, speed, 40000,
                                passes=ps, priority=len(doc.layers), qpulse=200,
                                wobble=(1 if ws else None),
                                wobble_size=ws, wobble_step=wst))
        doc.add_rect(cx, cy, SQ, SQ, L)
        n += 1
    if with_label:
        mk = doc.add_layer(Layer(20 + i, "%s_lbl" % tid, "Scan", 20, 1000, 40000,
                                 passes=1, priority=90 + i, qpulse=200, interval=0.05))
        doc.add_text(cx - SQ / 2, cy - SQ / 2 - 4.0, "%s %s" % (tid, label), mk, height=2.4)
    return n

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("-o","--outdir",default="coupon/cut")
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, a.outdir); os.makedirs(out, exist_ok=True)

    print("%-4s %-12s %7s %8s %10s" % ("id", "recipe", "speed", "passes", "est time"))
    lines = []
    for i, (tid, label, speed, stages) in enumerate(TESTS):
        d = LbrnDoc(notes=("Cut test %s: %s. ONE TEST PER FILE ON PURPOSE. Run it, then "
                           "LET THE BOARD COOL before the next file. Air assist ON, "
                           "board lifted off the bed." % (tid, label)))
        add_test(d, i, tid, label, speed, stages)
        d.save(os.path.join(out, "B6-CUT-%s.lbrn2" % tid))
        t = est_seconds(speed, stages)
        tot = sum(s[2] for s in stages)
        print("%-4s %-12s %5d/s %6d %8.0f s" % (tid, label, speed, tot, t))
        lines.append((tid, label, speed, tot, t))

    allv = LbrnDoc(notes="PREVIEW ONLY of all six cut tests. Do not run this file; run "
                         "B6-CUT-01 .. 06 one at a time, cooling in between.")
    for i, (tid, label, speed, stages) in enumerate(TESTS):
        add_test(allv, i, tid, label, speed, stages)
    allv.save(os.path.join(out, "B6-CUT-ALL-preview.lbrn2"))
    allv.to_svg(os.path.join(out, "B6-CUT-ALL-preview.svg"))

    readme = """# Cut test — six files, run one at a time

The board cutout is the last unmeasured layer. These six squares, 10 x 10 mm, are
positioned so that all six land on one board without overlapping, **but each lives in its
own file**.

## Why one file per test

Every coupon so far has been partly spoiled by the board still being hot from the
previous test. Separate files put the cooling under your control instead of LightBurn's.

**Run B6-CUT-01, then stop. Let the board come back to room temperature. Then 02.**
Touch it: if it is warm anywhere near the next square, wait longer. Two minutes is
usually plenty on 1.6 mm FR4 with air assist. Blowing compressed air across it helps.

The squares are 26 mm apart in X and 30 mm in Y, which is far enough that a cooled
neighbour stays cooled.

## The six

| file | recipe | speed | total passes | est. time |
%s

**01 and 02 are the tapered ones**, Edson's thick-metal technique: start at 0.30 mm
wobble so the kerf opens and the vapour escapes, then narrow through 0.20 and 0.10 to
0.05 so the energy concentrates at the bottom of the trench as it deepens.

**03, 05 and 06** are fixed-wobble and no-wobble controls at the current 40 mm/s.

**04** asks whether the hole lesson transfers: 400 mm/s did the clean work on holes, so
does it cut too, given enough passes.

## What to record

For each: **did the square fall out**, how clean is the edge, how much charring on the
underside, and how long it actually took.

The winner is the fastest one that releases the square with an edge you would put on a
sculpture. Speed matters less here than on the fills, because a board has one outline and
dozens of holes.

## Other cooling strategies worth using

- **Lift the board off the bed.** Already advised. Stops the beam reflecting off the
  fixture back into the exit side.
- **Interleave.** Already automatic for holes: no hole is drilled beside one still hot.
- **Order the job gentlest-first.** Fills at 75 %% / 1500 mm/s barely warm the board;
  holes and the outline are the hot parts. The outline is already last, because after it
  the board is loose.
- **Air across the work between layers**, not just air assist at the nozzle.
- One that cuts both ways: **a metal backing sinks heat but reflects the beam.** Good
  under a fill, which never punches through. Bad under holes and the outline, which do.
""" % "\n".join("| `B6-CUT-%s.lbrn2` | %s | %d mm/s | %d | %.0f s |"
                % (t, l, s, p, e) for t, l, s, p, e in lines)
    open(os.path.join(out, "README.md"), "w").write(readme)
    print("\nwrote 6 test files + a preview + README into %s" % out)

if __name__ == "__main__":
    main()
