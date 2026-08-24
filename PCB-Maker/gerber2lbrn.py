#!/usr/bin/env python3
"""
gerber2lbrn.py — turn a single-layer PCB export into one LightBurn job for the B6 MOPA.

    python3 gerber2lbrn.py /path/to/export -o board.lbrn2

Reads, in order of how much it trusts them:

  drill.drl        Excellon. Exact hole positions and diameters, in mm. Parsed directly,
                   never round-tripped through SVG, because a hole in the wrong place is
                   the one error you cannot fix after the fact.
  *edge_cuts.gbr   The board outline. Parsed directly.
  --iso <file.svg> Isolation geometry from pcb2gcode. Optional. See REGISTRATION below.

Writes one .lbrn2 with the archived five-layer recipe from B6-PCB-RECIPE.md, in the
run order that came off a board that worked: holes first, copper clearing, isolation
outline, board cutout last.

REGISTRATION, read this before trusting an isolation import
-----------------------------------------------------------
The drill and outline files share the PCB editor's origin. pcb2gcode's SVG does not:
it is cropped to the copper extent, so its origin is offset by an amount nothing in
the file records. This tool therefore reports both bounding boxes and, when it can,
solves the offset by fitting the SVG box to the copper box. **Check the reported
numbers before you cut.** If the offset looks wrong, pass --iso-offset X,Y yourself.

Without --iso you still get a complete, correct holes-and-outline job, which is the
half where mistakes are unrecoverable.
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lbrn import LbrnDoc, pcb_layers  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Excellon drill files
# ─────────────────────────────────────────────────────────────────────────────

def parse_excellon(path):
    """-> list of (x_mm, y_mm, diameter_mm). Handles the metric decimal form that
    KiCad, Flux and tscircuit all emit."""
    text = open(path, "r", errors="replace").read()
    if "METRIC" not in text.upper():
        raise ValueError("%s is not metric. Inch drill files are not supported; "
                         "re-export in mm." % os.path.basename(path))

    tools = {t: float(d) for t, d in re.findall(r"^T(\d+)C([\d.]+)", text, re.M)}
    if not tools:
        raise ValueError("no tool definitions (T..C..) found in %s" % path)

    holes, current = [], None
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"^T(\d+)$", line)
        if m:
            current = m.group(1)
            continue
        m = re.match(r"^X(-?[\d.]+)Y(-?[\d.]+)$", line)
        if m and current:
            holes.append((float(m.group(1)), float(m.group(2)), tools[current]))
    return holes, tools


# ─────────────────────────────────────────────────────────────────────────────
# Gerber outline
# ─────────────────────────────────────────────────────────────────────────────

def parse_gerber_outline(path):
    """-> list of polylines [[(x_mm, y_mm), ...], ...] from a profile/edge-cuts layer.

    Supports the %FSLAX<i><d>Y<i><d>*% integer/decimal format with %MOMM*%, which is
    what every modern exporter writes. D02 lifts, D01 draws."""
    text = open(path, "r", errors="replace").read()

    m = re.search(r"%FSLAX(\d)(\d)Y(\d)(\d)\*%", text)
    if not m:
        raise ValueError("no coordinate format (%%FSLAX..) in %s" % os.path.basename(path))
    dec_x, dec_y = int(m.group(2)), int(m.group(4))

    if "%MOIN*%" in text:
        unit = 25.4
    elif "%MOMM*%" in text:
        unit = 1.0
    else:
        raise ValueError("no unit directive (%%MOMM/%%MOIN) in %s" % os.path.basename(path))

    polys, cur, pen = [], [], None
    for m in re.finditer(r"X(-?\d+)Y(-?\d+)D0(1|2)\*", text):
        x = int(m.group(1)) / (10.0 ** dec_x) * unit
        y = int(m.group(2)) / (10.0 ** dec_y) * unit
        d = m.group(3)
        if d == "2":                       # move: start a new polyline
            if len(cur) > 1:
                polys.append(cur)
            cur = [(x, y)]
            pen = (x, y)
        else:                              # draw
            if not cur:
                cur = [pen] if pen else []
            cur.append((x, y))
    if len(cur) > 1:
        polys.append(cur)
    return stitch(polys)


def stitch(polys, tol=1e-4):
    """Join polylines that share endpoints. Edge-cuts layers are usually emitted as
    a pile of disconnected segments; a laser wants one closed loop per outline."""
    remaining = [list(p) for p in polys]
    out = []
    while remaining:
        chain = remaining.pop(0)
        changed = True
        while changed:
            changed = False
            for i, seg in enumerate(remaining):
                if near(chain[-1], seg[0], tol):
                    chain += seg[1:]; remaining.pop(i); changed = True; break
                if near(chain[-1], seg[-1], tol):
                    chain += seg[::-1][1:]; remaining.pop(i); changed = True; break
                if near(chain[0], seg[-1], tol):
                    chain = seg[:-1] + chain; remaining.pop(i); changed = True; break
                if near(chain[0], seg[0], tol):
                    chain = seg[::-1][:-1] + chain; remaining.pop(i); changed = True; break
        out.append(chain)
    return out


def near(a, b, tol):
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol


# ─────────────────────────────────────────────────────────────────────────────
# pcb2gcode SVG
# ─────────────────────────────────────────────────────────────────────────────

def parse_svg_polylines(path):
    """-> (polylines_in_svg_user_units, mm_per_unit).

    pcb2gcode writes <polyline points="x,y x,y ..."> in viewBox units, with the real
    size on the <svg> element. We derive mm-per-unit from those two rather than
    assuming, because the assumption is exactly the kind of thing that silently
    scales a board by 2 %."""
    text = open(path, "r", errors="replace").read()

    m = re.search(r"<svg[^>]*>", text, re.S)
    if not m:
        raise ValueError("no <svg> element in %s" % os.path.basename(path))
    head = m.group(0)

    vb = re.search(r'viewBox="([-\d.eE]+)\s+([-\d.eE]+)\s+([-\d.eE]+)\s+([-\d.eE]+)"', head)
    wd = re.search(r'width="([\d.eE]+)(\w*)"', head)
    if not (vb and wd):
        raise ValueError("cannot read width/viewBox from %s" % os.path.basename(path))

    vb_w = float(vb.group(3))
    val, unit = float(wd.group(1)), (wd.group(2) or "px")
    width_mm = {"mm": val, "cm": val * 10, "in": val * 25.4,
                "pt": val * 25.4 / 72.0, "px": val * 25.4 / 96.0, "": val * 25.4 / 96.0}[unit]
    mm_per_unit = width_mm / vb_w

    polys = []
    for m in re.finditer(r"<polyline[^>]*points=\"([^\"]+)\"", text):
        pts = []
        for pair in m.group(1).split():
            if "," in pair:
                x, y = pair.split(",")
                pts.append((float(x), float(y)))
        if len(pts) > 1:
            polys.append(pts)
    return polys, mm_per_unit



def auto_register(holes, svg_pts_mm, seed):
    """Solve the isolation SVG offset by minimising the distance from every drill hole
    to the nearest piece of copper geometry.

    This works because a pad is a ring of copper around its hole. At the correct offset
    every hole sits at the centre of a ring and the mean hole-to-copper distance
    collapses to roughly the pad radius. At a wrong offset it does not, so the minimum
    is sharp and meaningful rather than a shrug.

    Exact nearest-neighbour, vectorised with numpy. No spatial index: an approximate
    index quietly returned a worse optimum during development, which is a bad trade
    for a couple of seconds.

    Returns (offset_x, offset_y, mean_residual_mm).
    """
    import numpy as np

    P = np.asarray(svg_pts_mm, dtype=float)          # copper vertices, mm
    H = np.asarray([(x, y) for x, y, _ in holes], dtype=float)
    px, py = P[:, 0][None, :], P[:, 1][None, :]
    hx, hy = H[:, 0][:, None], H[:, 1][:, None]

    def score(ox, oy):
        dx = (px + ox) - hx
        dy = (oy - py) - hy
        return float(np.sqrt((dx * dx + dy * dy).min(axis=1)).mean())

    cx, cy = seed
    best = (score(cx, cy), (cx, cy))
    step = 1.0
    for _ in range(7):                                # 1 mm down to ~0.5 um
        for i in range(-6, 7):
            for j in range(-6, 7):
                ox, oy = cx + i * step, cy + j * step
                s = score(ox, oy)
                if s < best[0]:
                    best = (s, (ox, oy))
        cx, cy = best[1]
        step /= 3.0
    return best[1][0], best[1][1], best[0]


def bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


# ─────────────────────────────────────────────────────────────────────────────
# Build
# ─────────────────────────────────────────────────────────────────────────────

def find(folder, *patterns):
    for name in sorted(os.listdir(folder)):
        low = name.lower()
        if any(re.search(p, low) for p in patterns):
            return os.path.join(folder, name)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", help="folder holding drill.drl and *edge_cuts.gbr")
    ap.add_argument("-o", "--out", default=None, help="output .lbrn2")
    ap.add_argument("--iso", default=None,
                    help="pcb2gcode SVG carrying the isolation geometry")
    ap.add_argument("--iso-offset", default=None, metavar="X,Y",
                    help="manual mm offset for the isolation SVG, overriding the fit")
    ap.add_argument("--qpulse", type=int, default=None,
                    help="Q-pulse width in ns, from the coupon. Omitted = device default.")
    ap.add_argument("--interval", type=float, default=None,
                    help="scan line interval in mm, from the coupon")
    args = ap.parse_args()

    folder = os.path.abspath(args.folder)
    out = args.out or os.path.join(folder, "b6-board.lbrn2")

    drill_path = find(folder, r"\.drl$", r"drill.*\.(txt|xln)$")
    edge_path = find(folder, r"edge.?cuts.*\.gbr$", r"profile.*\.gbr$", r"\.gm1$")
    if not drill_path:
        sys.exit("No drill file found in %s" % folder)

    print("drill   : %s" % os.path.basename(drill_path))
    holes, tools = parse_excellon(drill_path)
    print("          %d holes, %d tool sizes: %s"
          % (len(holes), len(tools), ", ".join("%.3f" % d for d in sorted(set(tools.values())))))

    outline = []
    if edge_path:
        print("outline : %s" % os.path.basename(edge_path))
        outline = parse_gerber_outline(edge_path)
        print("          %d loop(s)" % len(outline))
    else:
        print("outline : none found, the board will have no cutout layer")

    resid = None
    layers = {l.name: l for l in pcb_layers(qpulse=args.qpulse, interval=args.interval)}
    doc = LbrnDoc(notes="Generated by PCB-Maker from %s" % os.path.basename(folder))
    for l in layers.values():
        doc.add_layer(l)

    for x, y, d in holes:
        doc.add_circle(x, y, d, layers["HOLES"])

    for loop in outline:
        closed = near(loop[0], loop[-1], 1e-4)
        doc.add_polygon(loop[:-1] if closed else loop, layers["CUTOUT"], closed=closed)

    # -- isolation, the part with a registration seam --------------------------
    if args.iso:
        polys, mm_per_unit = parse_svg_polylines(args.iso)
        print("iso     : %s" % os.path.basename(args.iso))
        print("          %d polylines, %.6f mm per svg unit" % (len(polys), mm_per_unit))

        flat = [p for poly in polys for p in poly]
        sx0, sy0, sx1, sy1 = bbox(flat)
        svg_mm = ((sx1 - sx0) * mm_per_unit, (sy1 - sy0) * mm_per_unit)

        hx0, hy0, hx1, hy1 = bbox([(x, y) for x, y, _ in holes])
        print("          svg extent  %.2f x %.2f mm" % svg_mm)
        print("          hole extent %.2f x %.2f mm  (x %.2f..%.2f, y %.2f..%.2f)"
              % (hx1 - hx0, hy1 - hy0, hx0, hx1, hy0, hy1))

        if args.iso_offset:
            ox, oy = (float(v) for v in args.iso_offset.split(","))
            print("          offset  : %.3f, %.3f mm (manual)" % (ox, oy))
            resid = None
        else:
            seed = (hx0 - sx0 * mm_per_unit, hy1 + sy0 * mm_per_unit)
            pts_mm = [(x * mm_per_unit, y * mm_per_unit) for poly in polys for x, y in poly]
            ox, oy, resid = auto_register(holes, pts_mm, seed)
            print("          offset  : %.3f, %.3f mm (solved)" % (ox, oy))
            print("          residual: %.3f mm mean hole-to-copper" % resid)

        for poly in polys:
            pts = [(x * mm_per_unit + ox, oy - y * mm_per_unit) for x, y in poly]
            closed = near(pts[0], pts[-1], 1e-3)
            doc.add_polygon(pts[:-1] if closed else pts, layers["ISOLATE"], closed=closed)
    else:
        print("iso     : skipped (no --iso). Holes and outline only.")

    doc.save(out)
    print("\nwrote %s\n" % out)
    print(doc.summary())

    # -- checks ----------------------------------------------------------------
    print("\nchecks:")
    problems = 0
    if outline:
        ox0, oy0, ox1, oy1 = bbox([p for loop in outline for p in loop])
        print("  board %.2f x %.2f mm" % (ox1 - ox0, oy1 - oy0))
        stray = [(x, y) for x, y, _ in holes
                 if not (ox0 - 0.01 <= x <= ox1 + 0.01 and oy0 - 0.01 <= y <= oy1 + 0.01)]
        if stray:
            print("  FAIL %d hole(s) fall outside the board outline" % len(stray))
            problems += 1
        else:
            print("  OK   every hole is inside the board outline")
    if args.iso and not args.iso_offset:
        if resid is None:
            pass
        elif resid > 0.9:
            print("  FAIL isolation registration residual %.3f mm. That is too large to "
                  "trust; the SVG is probably not from this board. Pass --iso-offset." % resid)
            problems += 1
        elif resid > 0.45:
            print("  WARN isolation registration residual %.3f mm. Eyeball the holes "
                  "against the pads in LightBurn before cutting." % resid)
        else:
            print("  OK   isolation registered, residual %.3f mm" % resid)
    if len(set((round(x, 3), round(y, 3)) for x, y, _ in holes)) != len(holes):
        print("  WARN duplicate hole coordinates in the drill file")
    else:
        print("  OK   no duplicate holes")
    print("  %s" % ("PROBLEMS ABOVE" if problems else "nothing blocking"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
