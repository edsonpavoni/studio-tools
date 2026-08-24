"""
verify.py — independent verification of a hand-routed board.

The drawing UI ticks connections live, but the UI is not trusted: this reimplements
the connectivity and clearance checks from the pad/net data and the saved strokes,
and it is what the converter runs before writing a laser file. If the two disagree,
this one wins.
"""

import math


def _dist_pt_seg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = ((px - ax) * dx + (py - ay) * dy) / L2 if L2 else 0.0
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _dist_pt_stroke(px, py, pts):
    return min(_dist_pt_seg(px, py, pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1])
               for i in range(len(pts) - 1))


def _seg_seg(ax, ay, bx, by, cx, cy, dx, dy):
    """Distance between segments AB and CD. Vertex-to-segment alone is NOT enough:
    two long segments crossing near mid-span have their closest point far from any
    vertex, and that blindness let six real welds through on 2026-08-22."""
    # if they intersect, distance is zero
    def ccw(px, py, qx, qy, rx, ry):
        return (qx - px) * (ry - py) - (qy - py) * (rx - px)
    d1 = ccw(cx, cy, dx, dy, ax, ay)
    d2 = ccw(cx, cy, dx, dy, bx, by)
    d3 = ccw(ax, ay, bx, by, cx, cy)
    d4 = ccw(ax, ay, bx, by, dx, dy)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return 0.0
    return min(_dist_pt_seg(ax, ay, cx, cy, dx, dy),
               _dist_pt_seg(bx, by, cx, cy, dx, dy),
               _dist_pt_seg(cx, cy, ax, ay, bx, by),
               _dist_pt_seg(dx, dy, ax, ay, bx, by))


def _dist_strokes(a, b):
    m = 1e9
    for i in range(len(a) - 1):
        for j in range(len(b) - 1):
            m = min(m, _seg_seg(a[i][0], a[i][1], a[i+1][0], a[i+1][1],
                                b[j][0], b[j][1], b[j+1][0], b[j+1][1]))
    return m


def _pad_r(p):
    return max(p["d"], p.get("pad_w") or 0, p.get("pad_h") or 0) / 2.0


def _seg_rect(ax, ay, bx, by, cx, cy, hw, hh):
    """Distance from segment AB to an axis-aligned rect centred (cx,cy), half-size
    (hw,hh). A circle model under-reaches a square pad's CORNER by 0.41r - more
    than the whole clearance floor - which hid six real welds on 2026-08-22."""
    if (abs(ax - cx) <= hw and abs(ay - cy) <= hh) or        (abs(bx - cx) <= hw and abs(by - cy) <= hh):
        return 0.0
    corners = [(cx - hw, cy - hh), (cx + hw, cy - hh),
               (cx + hw, cy + hh), (cx - hw, cy + hh)]
    m = 1e18
    for i in range(4):
        x1, y1 = corners[i]
        x2, y2 = corners[(i + 1) % 4]
        m = min(m, _seg_seg(ax, ay, bx, by, x1, y1, x2, y2))
    return m


def _stroke_pad_surf(s, p):
    """Surface distance between a stroke and a pad's real footprint."""
    pts = s["pts"]
    if p.get("shape") == "rect":
        hw = (p.get("pad_w") or p["d"]) / 2.0
        hh = (p.get("pad_h") or p["d"]) / 2.0
        m = min(_seg_rect(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1],
                          p["x"], p["y"], hw, hh)
                for i in range(len(pts) - 1))
        return m - s["w"] / 2.0
    return _dist_pt_stroke(p["x"], p["y"], pts) - s["w"] / 2.0 - _pad_r(p)


def check(board, strokes, min_gap=0.171):
    """board: netmap.extract() output. strokes: [{'pts':[[x,y]..],'w':mm}].
    -> dict(complete, incomplete=[net..], shorts=[[netA,netB]..], gaps=[msg..])"""
    pads = board["pads"]
    pour = board.get("pour_net")
    n_p, n_s = len(pads), len(strokes)

    parent = list(range(n_p + n_s))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for si, s in enumerate(strokes):
        for pi, p in enumerate(pads):
            # Contact tolerance MUST be below the minimum clearance (0.08 < 0.171),
            # or passing legally close reads as touching. Segment- and rect-accurate:
            # vertex sampling and circle pads both hid real contacts (2026-08-22).
            if _stroke_pad_surf(s, p) <= 0.08:
                union(n_p + si, pi)
    for i in range(n_s):
        for j in range(i + 1, n_s):
            if _dist_strokes(strokes[i]["pts"], strokes[j]["pts"]) <= \
               (strokes[i]["w"] + strokes[j]["w"]) / 2.0 + 0.05:
                union(n_p + i, n_p + j)

    # completeness per net (through drawn copper only)
    incomplete = []
    for net, idxs in board["nets"].items():
        if net == pour:
            continue
        if any(find(i) != find(idxs[0]) for i in idxs):
            incomplete.append(net)

    # shorts: any component containing pads of two different nets
    group_nets = {}
    for pi, p in enumerate(pads):
        if p.get("net"):
            group_nets.setdefault(find(pi), set()).add(p["net"])
    shorts = sorted(sorted(v) for v in group_nets.values() if len(v) > 1)

    # stroke net assignment for the gap check
    snet = []
    for si in range(n_s):
        nets = group_nets.get(find(n_p + si), set())
        snet.append(next(iter(nets)) if len(nets) == 1 else None)

    gaps = []
    for si, s in enumerate(strokes):
        if snet[si] is None:
            continue
        for p in pads:
            if not p.get("net") or p["net"] == snet[si]:
                continue
            surf = _stroke_pad_surf(s, p)
            if -0.01 < surf < min_gap:
                gaps.append("%s to %s (%s): %.3f mm"
                            % (snet[si], p["name"], p["net"], surf))
        for oj in range(si + 1, n_s):
            if snet[oj] is None or snet[oj] == snet[si]:
                continue
            surf = _dist_strokes(s["pts"], strokes[oj]["pts"]) \
                - s["w"]/2.0 - strokes[oj]["w"]/2.0
            if -0.01 < surf < min_gap:
                gaps.append("%s to %s: %.3f mm" % (snet[si], snet[oj], surf))

    return {"complete": not incomplete and not shorts,
            "incomplete": sorted(incomplete), "shorts": shorts, "gaps": gaps,
            "stroke_nets": snet}
