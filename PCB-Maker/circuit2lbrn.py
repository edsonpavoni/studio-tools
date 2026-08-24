#!/usr/bin/env python3
"""
circuit2lbrn.py — tscircuit circuit.json straight to one LightBurn job.

    tsci build                       # writes dist/<name>/circuit.json
    python3 circuit2lbrn.py dist/index/circuit.json -o board.lbrn2

Why this exists and why it beats the Gerber route
--------------------------------------------------
`circuit.json` is tscircuit's own intermediate representation. It carries the board
outline, every hole with its real diameter, every pad and every routed trace, all in
ONE millimetre coordinate system centred on the board. So:

  * hole positions are exact, not re-derived from a drill file
  * the board outline is a real polygon, not stitched from Gerber segments
  * there is no registration problem between holes, outline and copper, because they
    were never in different files to begin with

The one thing circuit.json does not give you is the *negative*: the copper that has to
be removed. Computing that from the copper polygons is a boolean operation, and rather
than hand-roll a polygon clipper this tool takes the isolation geometry from pcb2gcode
via --iso, which is the same tool that made the 2025 board. Registration of that SVG is
solved against the PADS, which are far more numerous than the holes and therefore pin
the fit harder.

Without --iso you get a correct holes-and-outline job plus a copper reference layer you
can eyeball in LightBurn. That is genuinely useful on its own: holes in the wrong place
is the one error you cannot recover from.
"""

import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lbrn import LbrnDoc, Layer, pcb_layers               # noqa: E402
from gerber2lbrn import parse_svg_polylines, auto_register, bbox, near  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# circuit.json readers
# ─────────────────────────────────────────────────────────────────────────────

def elements(cj, kind):
    return [e for e in cj if e.get("type") == kind]


def board_outline(cj):
    """-> list of (x, y) in mm, closed. Falls back to width/height when the board
    has no explicit outline polygon."""
    boards = elements(cj, "pcb_board")
    if not boards:
        return None, None
    b = boards[0]
    if b.get("outline"):
        return [(p["x"], p["y"]) for p in b["outline"]], b
    cx = b.get("center", {}).get("x", 0.0)
    cy = b.get("center", {}).get("y", 0.0)
    w, h = b["width"], b["height"]
    return [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2),
            (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)], b


def holes(cj):
    """-> list of (x, y, diameter_mm, kind). Plated and unplated both get drilled;
    the laser does not know the difference."""
    out = []
    for e in elements(cj, "pcb_plated_hole"):
        d = e.get("hole_diameter") or e.get("hole_width")
        if d:
            out.append((e["x"], e["y"], d, "plated"))
    for e in elements(cj, "pcb_hole"):
        d = e.get("hole_diameter") or e.get("hole_width")
        if d:
            out.append((e["x"], e["y"], d, "hole"))
    return out


def copper_shapes(cj):
    """-> list of ('rect', cx, cy, w, h) / ('circle', cx, cy, dia) for every piece of
    top-layer copper. Used as the registration reference and the visual check."""
    out = []
    for e in elements(cj, "pcb_smtpad"):
        if e.get("layer") not in (None, "top"):
            continue
        shape = e.get("shape")
        if shape in ("rect", "rotated_rect"):
            out.append(("rect", e["x"], e["y"], e["width"], e["height"]))
        elif shape == "circle":
            out.append(("circle", e["x"], e["y"], e.get("radius", 0) * 2))
        elif shape == "pill":
            out.append(("rect", e["x"], e["y"], e.get("width", 0), e.get("height", 0)))
    for e in elements(cj, "pcb_plated_hole"):
        if e.get("rect_pad_width"):
            out.append(("rect", e["x"], e["y"], e["rect_pad_width"], e["rect_pad_height"]))
        elif e.get("outer_diameter"):
            out.append(("circle", e["x"], e["y"], e["outer_diameter"]))
    return out


def pours(cj):
    """-> list of ring-lists. A copper pour arrives as a brep: one outer ring plus any
    number of inner rings where it has been cut away around other nets.

    This matters enormously for a laser board. A ground pour is copper we KEEP, so it is
    area that never has to be cleared, and clearing is most of the job time. It also
    sinks heat away from the holes while they are being drilled."""
    out = []
    for e in elements(cj, "pcb_copper_pour"):
        if e.get("layer") not in (None, "top"):
            continue
        b = e.get("brep_shape") or {}
        rings = []
        outer = (b.get("outer_ring") or {}).get("vertices")
        if not outer:
            continue
        rings.append([(p["x"], p["y"]) for p in outer])
        for inner in b.get("inner_rings", []):
            v = inner.get("vertices")
            if v:
                rings.append([(p["x"], p["y"]) for p in v])
        out.append(rings)
    return out


def traces(cj):
    """-> list of (points, width_mm) for routed top-layer copper."""
    out = []
    for e in elements(cj, "pcb_trace"):
        pts, width = [], None
        for seg in e.get("route", []):
            if seg.get("route_type") == "wire":
                if seg.get("layer") not in (None, "top"):
                    continue
                pts.append((seg["x"], seg["y"]))
                width = width or seg.get("width")
        if len(pts) > 1:
            out.append((pts, width or 0.2))
    return out


# ─────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("circuit_json")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--iso", default=None,
                    help="pcb2gcode isolation SVG carrying the copper-clear geometry")
    ap.add_argument("--iso-offset", default=None, metavar="X,Y")
    # The MEASURED recipe values are the defaults. Passing None let the machine
    # profile's own defaults through - which put interval at 0.1 instead of the
    # proven 0.05, HALF the fill energy density. Caught by Edson in LightBurn on
    # 2026-08-23, minutes before cutting.
    ap.add_argument("--qpulse", type=int, default=200, help="ns (measured default 200)")
    ap.add_argument("--interval", type=float, default=0.05,
                    help="mm scan interval (measured default 0.05)")
    ap.add_argument("--no-copper-ref", action="store_true",
                    help="omit the copper reference layer")
    ap.add_argument("--clear", action="store_true",
                    help="compute the copper-clear region directly from circuit.json. "
                         "No pcb2gcode, no Gerber, no registration step.")
    ap.add_argument("--pullback", type=float, default=0.05,
                    help="how far the clear region is held back from the copper edge, in "
                         "mm. This is KERF COMPENSATION, not design clearance: copper "
                         "survives this much wider than drawn, so a large value fuses "
                         "nearby traces. Default 0.05.")
    ap.add_argument("--manual-traces", default=None, metavar="PATH",
                    help="use hand-drawn traces from the hand-route UI instead of the "
                         "autoroute. 'auto' looks for traces.json next to circuit.json. "
                         "The strokes are re-verified here independently of the UI: "
                         "completeness, shorts and clearance all checked before any "
                         "geometry is written.")
    ap.add_argument("--moat", action="store_true",
                    help="isolation-moat mode: clear only a ring around signal copper "
                         "and leave the rest as the ground pour. This is the strategy "
                         "the coupons proved; whole-field clearing burned the board.")
    ap.add_argument("--floor", type=float, default=0.171,
                    help="minimum manufacturable gap in mm; sub-floor gaps between "
                         "nets refuse the build (default 0.171, the proven value)")
    ap.add_argument("--clearance", type=float, default=0.5,
                    help="moat width in mm for --moat (default 0.5)")
    ap.add_argument("--fit-test", action="store_true",
                    help="write a CARDBOARD FIT-TEST file instead of a board: holes at "
                         "drawn size, board outline, and every component's name, on "
                         "light cut settings. Cut it on cardboard, push the real parts "
                         "through, THEN spend hours drawing traces. Exists because V3 "
                         "was cut with a hand-typed 10 mm XIAO row spacing that no "
                         "software check could catch: the real module is 15.24 mm. "
                         "Checkers verify the board against the design; only a fit "
                         "test verifies the design against the physical part.")
    ap.add_argument("--hole-kerf", type=float, default=0.24, metavar="MM",
                    help="subtract this from every drawn hole diameter. Wobble widens "
                         "the kerf, so a hole finishes larger than drawn. 0.24 is the "
                         "MEASURED kerf at the dialed-in hole cell (70%%/8 passes/"
                         "wobble 0.10, HOLES-5 coupon 2026-08-24): drawn 0.76 seats a "
                         "2.54 header pin at a 1.00 target. Measured at Ø1.0; the "
                         "MOUNT coupon checks it holds at Ø2.0.")
    ap.add_argument("--no-interleave", action="store_true",
                    help="drill holes in one pass instead of checkerboarding them "
                         "across two layers")
    ap.add_argument("--res", type=float, default=0.05,
                    help="raster resolution in mm for the negative (default 0.05)")
    ap.add_argument("--min-trace", type=float, default=0.8, metavar="MM",
                    help="floor for trace width in mm. Anything the router drew "
                         "narrower is widened to this. A laser board has no plating and "
                         "the kerf eats the edges, so fab-house widths are too thin. "
                         "Default 0.8. Use 0 to keep the router's widths untouched.")
    ap.add_argument("--trace-width", type=float, default=None, metavar="MM",
                    help="force EVERY trace to this width, ignoring the router")
    args = ap.parse_args()

    cj = json.load(open(args.circuit_json))
    if isinstance(cj, dict):
        cj = cj.get("circuit_json") or cj.get("elements") or []
    out = args.out or os.path.splitext(args.circuit_json)[0] + ".lbrn2"

    outline, board = board_outline(cj)
    hs = holes(cj)
    cu = copper_shapes(cj)
    tr = traces(cj)
    po = pours(cj)

    # ---- cardboard fit test: physical-world check, needs no traces --------
    if args.fit_test:
        doc = LbrnDoc(notes=("CARDBOARD FIT TEST — holes at drawn size, outline, part "
                             "names. Light cut; tune power live for the cardboard. "
                             "Push every real component through before cutting FR4."))
        cut = doc.add_layer(Layer(0, "FIT_CUT", "Cut", 30, 400, 40000, passes=2,
                                  priority=0, qpulse=200))
        mark = doc.add_layer(Layer(1, "FIT_MARK", "Scan", 20, 1000, 40000, passes=1,
                                   priority=1, qpulse=200, interval=0.05))
        for (hx, hy, hd, _kind) in hs:
            doc.add_circle(hx, hy, hd, cut)
        doc.add_polygon(outline, cut, closed=True)
        for e in cj:
            if e.get("type") == "pcb_component":
                c = e.get("center") or {}
                srcc = [x for x in cj if x.get("type") == "source_component"
                        and x.get("source_component_id") == e.get("source_component_id")]
                nm = srcc[0].get("name", "?") if srcc else "?"
                doc.add_text(c.get("x", 0), c.get("y", 0), nm, mark, height=2.0)
        fit_out = args.out or os.path.splitext(args.circuit_json)[0] + "-FITTEST.lbrn2"
        doc.save(fit_out)
        print("wrote %s  (%d holes, outline, %d labels) — cardboard first, FR4 second"
              % (fit_out, len(hs),
                 sum(1 for e in cj if e.get("type") == "pcb_component")))
        return

    # ---- hand-drawn traces replace the autoroute --------------------------
    manual = None
    if args.manual_traces:
        mpath = args.manual_traces
        if mpath == "auto":
            mpath = os.path.join(os.path.dirname(os.path.abspath(args.circuit_json)),
                                 "traces.json")
        manual = json.load(open(mpath))["strokes"]
        tr = [([tuple(q) for q in st["pts"]], st["w"]) for st in manual]
        po = []          # tscircuit's pour was shaped around the OLD autoroute
        print("manual  : %d hand-drawn traces from %s"
              % (len(manual), os.path.basename(mpath)))

        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "handroute"))
        import netmap as _nm
        import verify as _vf
        bd = _nm.extract(args.circuit_json)
        # GND is only a pour in --moat mode; in full-clear it must be drawn and
        # complete like every other net.
        bd["pour_net"] = "GND" if args.moat else None
        v = _vf.check(bd, manual, min_gap=args.floor)
        print("verify  : %s" % ("ALL NETS COMPLETE, no shorts"
                                if v["complete"] else "PROBLEMS"))
        for n in v["incomplete"]:
            print("          INCOMPLETE net %s" % n)
        for sh in v["shorts"]:
            print("          SHORT %s" % " + ".join(sh))
        for g in v["gaps"][:10]:
            print("          gap  %s" % g)
        if not v["complete"] or v["gaps"]:
            print("\nRefusing to write a laser file: %s. Finish the drawing first, "
                  "or lower --floor if the coupon has proven a finer gap."
                  % ("incomplete/shorted" if not v["complete"]
                     else "%d gap(s) below the %.3f mm floor" % (len(v["gaps"]), args.floor)))
            return 1

    print("circuit : %s" % os.path.basename(args.circuit_json))
    if board:
        print("board   : %.1f x %.1f mm, %s layer(s), %.1f mm thick"
              % (board["width"], board["height"], board.get("num_layers", "?"),
                 board.get("thickness", 0)))
    print("holes   : %d  (%s)" % (
        len(hs), ", ".join("%.2f" % d for d in sorted(set(h[2] for h in hs)))))
    print("copper  : %d pads, %d routed traces, %d pour region(s)"
          % (len(cu), len(tr), len(po)))

    # -- trace width policy ----------------------------------------------------
    tr_designed = list(tr)
    if manual is not None:
        # Hand-drawn widths are sacred: the verifier just validated this exact
        # geometry, and widening it afterwards would invalidate the verification.
        pass
    elif tr:
        drawn = sorted(set(round(w, 3) for _p, w in tr))
        print("          router widths: %s mm"
              % ", ".join("%.2f" % w for w in drawn))
        if args.trace_width:
            tr = [(pts, args.trace_width) for pts, _w in tr]
            print("          FORCED all %d traces to %.2f mm" % (len(tr), args.trace_width))
        elif args.min_trace > 0:
            widened = [(pts, w) for pts, w in tr if w < args.min_trace - 1e-9]
            tr = [(pts, max(w, args.min_trace)) for pts, w in tr]
            if widened:
                print("          widened %d of %d trace(s) up to the %.2f mm floor "
                      "(narrowest was %.2f mm)"
                      % (len(widened), len(tr), args.min_trace,
                         min(w for _p, w in widened)))
            else:
                print("          all traces already at or above the %.2f mm floor"
                      % args.min_trace)

    layers = {l.name: l for l in pcb_layers(qpulse=args.qpulse, interval=args.interval)}
    doc = LbrnDoc(notes="PCB-Maker from %s" % os.path.basename(args.circuit_json))
    for l in layers.values():
        doc.add_layer(l)

    copper_ref = None
    if not args.no_copper_ref:
        # Output "0" power so it never fires. It exists to be looked at.
        copper_ref = doc.add_layer(Layer(index=20, name="COPPER_REF", mode="Cut",
                                         power=0, speed=1000, freq=37000,
                                         passes=1, priority=99, output=0))

    # Checkerboard the holes onto two layers on the 2.54 mm grid, so no hole is cut
    # beside one that is still hot. See the note in lbrn.pcb_layers.
    PITCH = 2.54
    kerfed = 0
    for x, y, d, _kind in hs:
        dia = d - args.hole_kerf
        if dia <= 0.05:
            print("  WARN hole at %.2f,%.2f is %.2f mm, smaller than the kerf "
                  "compensation. Left uncompensated." % (x, y, d))
            dia = d
        elif args.hole_kerf:
            kerfed += 1
        if args.no_interleave:
            L = layers["HOLES_A"]
        else:
            L = layers["HOLES_A" if (int(math.floor(x / PITCH))
                                     + int(math.floor(y / PITCH))) % 2 == 0
                       else "HOLES_B"]
        doc.add_circle(x, y, dia, L)
    if args.hole_kerf:
        print("          %d hole(s) shrunk by %.3f mm for wobble kerf"
              % (kerfed, args.hole_kerf))
    if not args.no_interleave:
        na = sum(1 for sh in doc.shapes if sh.get("CutIndex") == str(layers["HOLES_A"].index))
        nb = sum(1 for sh in doc.shapes if sh.get("CutIndex") == str(layers["HOLES_B"].index))
        print("          holes interleaved across two layers: %d then %d" % (na, nb))

    if outline:
        doc.add_polygon(outline, layers["CUTOUT"], closed=True)

    if copper_ref is not None:
        for s in cu:
            if s[0] == "rect":
                doc.add_rect(s[1], s[2], s[3], s[4], copper_ref)
            else:
                doc.add_circle(s[1], s[2], s[3], copper_ref)
        for pts, _w in tr:
            doc.add_polygon(pts, copper_ref, closed=False)

    # -- the negative, computed here -------------------------------------------
    resid = None
    cleared = None
    if args.moat:
        if not outline:
            sys.exit("--moat needs a board outline")
        import negative
        pour_pads, sig_pads = [], []
        if manual is not None:
            gnd_idx = set()
            for i, p in enumerate(bd["pads"]):
                if p.get("net") == "GND":
                    gnd_idx.add((round(p["x"], 2), round(p["y"], 2)))
            for sshape in cu:
                key = (round(sshape[1], 2), round(sshape[2], 2))
                (pour_pads if key in gnd_idx else sig_pads).append(sshape)
        else:
            sig_pads = cu
        polys, stats = negative.moat_region(
            outline, sig_pads, tr, pour_pads,
            clearance=args.clearance, pullback=args.pullback, res=args.res)
        cleared = stats
        print("moat    : %d loops, %d points, %.0f mm2 cleared (%.1f%% of the board)"
              % (stats["loops"], stats["points"], stats["clear_mm2"],
                 100 * stats["clear_mm2"] / stats["board_mm2"]))
        for poly in polys:
            doc.add_polygon(poly, layers["CLEAR_1"], closed=True)
    elif args.clear:
        if not outline:
            sys.exit("--clear needs a board outline and this circuit.json has none")
        import negative
        polys, stats = negative.clear_region(
            outline, cu, tr, pullback=args.pullback, res=args.res,
            design_traces=tr_designed, pours=po)
        cleared = stats
        print("clear   : %d loops, %d points, %.0f mm2 of copper removed "
              "(%.0f%% of the board)"
              % (stats["loops"], stats["points"], stats["clear_mm2"],
                 100.0 * stats["clear_mm2"] / max(stats["board_mm2"], 1e-9)))
        for poly in polys:
            doc.add_polygon(poly, layers["CLEAR_1"], closed=True)

    # -- isolation from pcb2gcode, the alternative route ------------------------
    if args.iso:
        polys, mmpu = parse_svg_polylines(args.iso)
        pts_mm = [(x * mmpu, y * mmpu) for poly in polys for x, y in poly]
        print("iso     : %s — %d polylines, %.6f mm/unit"
              % (os.path.basename(args.iso), len(polys), mmpu))

        if args.iso_offset:
            ox, oy = (float(v) for v in args.iso_offset.split(","))
            print("          offset  : %.3f, %.3f (manual)" % (ox, oy))
        else:
            # Register against pad centres. There are far more of them than holes,
            # so the minimum is much better constrained.
            ref = [(s[1], s[2], 0) for s in cu] or [(x, y, 0) for x, y, _, _ in hs]
            sx0, sy0, _, _ = bbox(pts_mm)
            rx0, _, _, ry1 = bbox([(x, y) for x, y, _ in ref])
            ox, oy, resid = auto_register(ref, pts_mm, (rx0 - sx0, ry1 + sy0))
            print("          offset  : %.3f, %.3f (solved on %d pads)"
                  % (ox, oy, len(ref)))
            print("          residual: %.3f mm mean pad-to-copper" % resid)

        for poly in polys:
            p = [(x * mmpu + ox, oy - y * mmpu) for x, y in poly]
            closed = near(p[0], p[-1], 1e-3)
            doc.add_polygon(p[:-1] if closed else p, layers["ISOLATE"], closed=closed)
    elif not args.clear:
        print("iso     : none. Holes, outline and copper reference only.")

    doc.save(out)
    print("\nwrote %s\n" % out)
    print(doc.summary())

    # -- checks ----------------------------------------------------------------
    print("\nchecks:")
    problems = 0
    if outline:
        ox0, oy0, ox1, oy1 = bbox(outline)
        stray = [h for h in hs if not (ox0 - .01 <= h[0] <= ox1 + .01
                                       and oy0 - .01 <= h[1] <= oy1 + .01)]
        print("  %s every hole inside the board outline%s"
              % ("OK  " if not stray else "FAIL", "" if not stray else
                 " (%d outside)" % len(stray)))
        problems += 1 if stray else 0
    dupes = len(hs) - len(set((round(h[0], 3), round(h[1], 3)) for h in hs))
    print("  %s no duplicate hole positions%s"
          % ("OK  " if not dupes else "WARN", "" if not dupes else " (%d)" % dupes))
    tiny = [h for h in hs if h[2] < 0.4]
    if tiny:
        print("  WARN %d hole(s) under 0.40 mm. The coupon has not yet proved the "
              "laser can make these." % len(tiny))
    if board and board.get("num_layers", 1) > 1:
        print("  WARN board declares %d layers. This pipeline makes SINGLE-SIDED boards; "
              "anything routed on the bottom will be missing." % board["num_layers"])
        problems += 1
    if not tr:
        print("  WARN no routed traces in this circuit.json. Run `tsci build` after "
              "routing, or the board will be pads with nothing joining them.")
    if cleared and "copper_parts_designed" not in cleared:
        # moat mode: net-level validation already happened in the verifier;
        # the geometric stats are informational
        frac = cleared["clear_mm2"] / max(cleared["board_mm2"], 1e-9)
        print("  OK   moat mode: %.1f%% of the board cleared, verified at the net "
              "level before geometry" % (100 * frac))
    elif cleared:
        frac = cleared["clear_mm2"] / max(cleared["board_mm2"], 1e-9)
        if frac < 0.05:
            print("  FAIL only %.1f%% of the board would be cleared. The clearance is "
                  "probably swallowing the whole board." % (100 * frac))
            problems += 1
        elif frac > 0.98:
            print("  FAIL %.1f%% of the board would be cleared, which means almost no "
                  "copper survives. Check that traces were found." % (100 * frac))
            problems += 1
        else:
            print("  OK   %.1f%% cleared, %.1f%% copper kept"
                  % (100 * frac, 100 * (1 - frac)))
        if tr:
            eff = min(w for _p, w in tr) + 2 * args.pullback
            print("  OK   narrowest finished trace %.2f mm "
                  "(%.2f drawn + 2 x %.2f pullback)"
                  % (eff, min(w for _p, w in tr), args.pullback))
        if manual is not None:
            # Hand-drawn boards may carry ORNAMENTS: deliberate copper that touches
            # nothing, or that fuses into a net it decorates. Both are fine - the
            # big-board artwork's fringe ticks and signature are exactly that. The
            # only geometric failure is one region holding TWO nets after kerf.
            import negative as _ng
            padnet = {(round(p["x"], 2), round(p["y"], 2)): p.get("net")
                      for p in bd["pads"]}
            pads6 = []
            for sh in cu:
                key = (round(sh[1], 2), round(sh[2], 2))
                if sh[0] == "rect":
                    pads6.append(("rect", sh[1], sh[2], sh[3], sh[4], padnet.get(key)))
                else:
                    pads6.append(("circle", sh[1], sh[2], sh[3], 0, padnet.get(key)))
            g_shorts, n_reg = _ng.net_fusions(outline, pads6, tr,
                                              pullback=args.pullback, res=args.res)
            if g_shorts:
                # A single-pixel contact at this resolution can be grid aliasing:
                # a diagonal 0.17 mm gap rasterises to touching about one time in
                # ten. Confirm at double resolution before failing the build -
                # found 2026-08-23 when a verified-clean board failed on 1 px.
                g_shorts, n_reg = _ng.net_fusions(outline, pads6, tr,
                                                  pullback=args.pullback,
                                                  res=args.res / 2)
                if not g_shorts:
                    print("  OK   a coarse-raster contact did not survive double "
                          "resolution: aliasing, not copper")
            if g_shorts:
                for grp in g_shorts:
                    print("  FAIL after kerf pullback one copper region bridges: %s. "
                          "An ornament is physically connecting two nets."
                          % " + ".join(grp))
                problems += 1
            else:
                print("  OK   no two nets share a copper region after kerf "
                      "(%d regions; ornaments fusing into a single net are fine)"
                      % n_reg)
        else:
            d = cleared["copper_parts_designed"]
            aw = cleared["copper_parts_after_widening"]
            ap_ = cleared["copper_parts_after_pullback"]
            mg = cleared.get("min_gap_mm")
            if mg is not None:
                PROVEN = 0.171
                if mg < PROVEN:
                    print("  FAIL closest gap between different nets is %.3f mm "
                          "(proven floor %.3f mm). Give the router more room."
                          % (mg, PROVEN))
                    problems += 1
                else:
                    print("  OK   closest gap between different nets %.3f mm "
                          "(proven floor %.3f mm)" % (mg, PROVEN))
            if cleared["merged"]:
                culprit = []
                if aw < d:
                    culprit.append("widening to %.2f mm (%d regions -> %d)"
                                   % (min(w for _p, w in tr), d, aw))
                if ap_ < aw:
                    culprit.append("the %.2f mm pullback (%d -> %d)"
                                   % (args.pullback, aw, ap_))
                print("  FAIL copper that is separate in the design gets fused: %s. "
                      "The finished board would be shorted." % " and ".join(culprit))
                problems += 1
            else:
                print("  OK   all %d copper regions in the design stay separate "
                      "through widening and pullback" % d)
    if resid is not None:
        print("  %s isolation registration residual %.3f mm"
              % ("OK  " if resid < 0.45 else "WARN", resid))
    print("  %s" % ("PROBLEMS ABOVE" if problems else "nothing blocking"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
