#!/usr/bin/env python3
"""
make_coupon.py — generate the B6 PCB test coupon.

This is the gate. Two parameters in the recovered 2025 recipe are genuinely missing
from the file (Q-pulse width and scan line interval), and pulse width is the parameter
that decides whether 1064 nm couples into copper at all. Until this coupon runs on
scrap, B6-PCB-RECIPE.md is an archive of what worked once, not a recipe.

The coupon runs the SAME geometry three times, once per candidate pulse width, so the
comparison is controlled. Everything else is held constant.

    python3 make_coupon.py                  # default: 200/350/500 ns
    python3 make_coupon.py --ns 150 250 350 # a narrower bracket on a second run

Output: coupon/B6-PCB-COUPON.lbrn2 plus a printable score sheet next to it.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lbrn import LbrnDoc, Layer  # noqa: E402


# What the coupon measures ----------------------------------------------------

# Isolation gap widths, mm. The ladder starts at 0.10 rather than 0.20 because the
# 2025 TRIBE board was measured on 2026-08-17 and its tightest copper-to-copper gap is
# 0.171 mm, which the laser cleared successfully. Starting the ladder above a gap that
# is already proven would have measured nothing.
MOATS = [0.10, 0.125, 0.15, 0.175, 0.20, 0.25, 0.30, 0.40]
DRILLS = [0.6, 0.9, 1.0, 1.3, 2.4, 6.6]     # the six sizes on the 2025 board
FIELD = 6.0                                  # cleared square, mm, for raster timing

BLOCK_W = 24.0
MARGIN = 6.0


def build(pulse_widths, interval):
    n = len(pulse_widths)
    board_w = MARGIN * 2 + BLOCK_W * n
    board_h = 66.0

    doc = LbrnDoc(notes=(
        "B6 PCB test coupon. One block per pulse width: " +
        ", ".join("%d ns" % p for p in pulse_widths) +
        ". Run on FR4 scrap. Scuff the LEFT half matte before running, leave the "
        "RIGHT half bright, then compare. Score sheet is in SCORE.md."))

    # Scan layers, one per pulse width. Everything except QPulseWidth is the
    # archived CLEAR_1 recipe: 95 %, 200 mm/s, 37 kHz.
    scan_layers = []
    for i, ns in enumerate(pulse_widths):
        scan_layers.append(doc.add_layer(Layer(
            index=i, name="CLR_%dns" % ns, mode="Scan",
            power=95, speed=200, freq=37000, passes=1, priority=1 + i,
            qpulse=ns, interval=interval)))

    holes = doc.add_layer(Layer(index=10, name="HOLES", mode="Cut",
                                power=100, speed=40, freq=37000, passes=8,
                                priority=0))
    cutout = doc.add_layer(Layer(index=11, name="CUTOUT", mode="Cut",
                                 power=100, speed=40, freq=37000, passes=12,
                                 priority=90))

    # Board outline, drawn last in run order so the coupon stays registered.
    doc.add_rect(board_w / 2, board_h / 2, board_w, board_h, cutout)

    for i, layer in enumerate(scan_layers):
        x0 = MARGIN + i * BLOCK_W
        cx = x0 + BLOCK_W / 2 - 3.0

        # 1. Isolation moats. These are the cleared gaps between traces.
        #    After the run, probe ACROSS each moat: it must read open.
        y = board_h - 10.0
        for w in MOATS:
            doc.add_rect(cx, y, 12.0, w, layer)
            y -= 3.0

        # 2. Cleared field, for raster timing and to confirm copper actually leaves.
        y -= 3.0
        doc.add_rect(cx, y - FIELD / 2, FIELD, FIELD, layer)

        # 3. A label so the blocks cannot be confused after the fact.
        doc.add_text(x0 + 1.0, 4.0, "%dns" % pulse_widths[i], layer, height=3.0)

        # 4. Holes, one of every drill size on the 2025 board. Same recipe for all,
        #    which is what the reference board did.
        hy = y - FIELD - 6.0
        hx = x0 + 3.0
        for d in DRILLS:
            doc.add_circle(hx, hy, d, holes)
            hx += 3.4
            if d >= 2.0:          # the big two need their own row
                hx = x0 + 5.0
                hy -= 8.0

    return doc, board_w, board_h


SCORE = """# B6 PCB coupon — score sheet

Run date: ____________   FR4 thickness: ______   Copper: 35 µm / other: ______

**Line interval this coupon was generated at: %s mm.**  Record it, because it changes
the energy per unit area by the same factor. Half the point of the exercise is
comparing 0.1 mm (the device default, and almost certainly what the 2025 board used)
against something finer.

Left half scuffed matte with maroon Scotch-Brite before the run: yes / no

## 1. Pulse width — the question this coupon exists to answer

| Block | Copper fully cleared in the 6 mm field? | Field time | Edge quality | Verdict |
|---|---|---|---|---|
| %s |  |  |  |  |

**Winner: ________ ns.** Write it into `B6-PCB-RECIPE.md` with today's date.

## 2. Minimum isolation gap

Probe ACROSS each moat with a multimeter. It must read **open**.

%s

**Smallest gap that reads open on every block: ________ mm.** That is the floor for
every design from here on. **The 2025 TRIBE board already proves 0.171 mm works**, so
anything above that is a regression and worth re-running before accepting.

## 3. Holes

Caliper each one. The drawn circle is the nominal drill diameter with no kerf
compensation, so the finished hole will come out slightly LARGER by roughly one kerf.

| Drawn | 0.6 | 0.9 | 1.0 | 1.3 | 2.4 | 6.6 |
|---|---|---|---|---|---|---|
| measured |  |  |  |  |  |  |
| through? |  |  |  |  |  |  |

If the measured hole is consistently larger by a fixed amount, that amount is the kerf.
Subtract it from future drawn diameters.

## 4. Surface prep

Did the scuffed half clear noticeably better than the bright half?  yes / no / no difference

If yes, scuffing becomes a required step in the pipeline, not an option.

## 5. Time

Field of 6 × 6 mm took ______ s. A 50 × 50 mm board is about 70 fields, so a full
clear is roughly ______ min. If that number is unreasonable, switch from
clear-the-whole-field to isolation-moats-only and re-time.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", nargs="+", type=int, default=[200, 350, 500],
                    help="pulse widths to compare, in ns")
    ap.add_argument("--interval", type=float, default=0.02,
                    help="scan line interval in mm (2025 value unknown; 0.02 is the "
                         "copper-engrave value from material-settings.md)")
    ap.add_argument("-o", "--outdir", default="coupon")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(here, args.outdir)
    os.makedirs(outdir, exist_ok=True)

    doc, w, h = build(args.ns, args.interval)
    tag = ("-i%g" % args.interval).replace(".", "p")
    path = doc.save(os.path.join(outdir, "B6-PCB-COUPON%s.lbrn2" % tag))
    doc.to_svg(os.path.join(outdir, "B6-PCB-COUPON%s.svg" % tag))

    rows = " | ".join("%d ns" % p for p in args.ns)
    moat_tbl = ("| Moat | " + " | ".join("%.3g mm" % m for m in MOATS) + " |\n"
                + "|---|" + "---|" * len(MOATS) + "\n"
                + "| open? | " + " | ".join(" " for _ in MOATS) + " |")
    with open(os.path.join(outdir, "SCORE%s.md" % tag), "w") as fh:
        fh.write(SCORE % (args.interval, rows, moat_tbl))

    print("Coupon written: %s" % path)
    print("Board size: %.1f x %.1f mm\n" % (w, h))
    print(doc.summary())
    print("\nScore sheet: %s" % os.path.join(outdir, "SCORE%s.md" % tag))
    print("\nBefore running: scuff the LEFT half matte, leave the RIGHT half bright.")


if __name__ == "__main__":
    main()
