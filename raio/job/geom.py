"""raio · job/geom.py — polylines, fill (hatch), wobble, kerf. Pure functions, mm, no device.

Conventions: a point is (x, y) in mm; a polyline is a list of points; a "loop" is a closed
polyline given WITHOUT the repeated first point. Regions are even-odd over all loops given
(nested loops are holes; trilha's copper islands rely on this, research/01-studio-history.md §4).
"""
import math
import numpy as np

TOL = 0.01          # chord deviation for flattening, mm (EZCAD markcfg ARCTOL=0.01; FORMAT.md "flattened at 0.01 mm")


# ───────────────────────────── basics ─────────────────────────────

def length(pts, closed=False):
    if len(pts) < 2:
        return 0.0
    a = np.asarray(pts, float)
    if closed:
        a = np.vstack([a, a[:1]])
    return float(np.hypot(*np.diff(a, axis=0).T).sum())


def bbox(polys):
    xs = [p[0] for pl in polys for p in pl]
    ys = [p[1] for pl in polys for p in pl]
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def apply_xform(m, pts):
    """LightBurn XForm 'a b c d e f': x' = a x + c y + e, y' = b x + d y + f."""
    a, b, c, d, e, f = m
    return [(a * x + c * y + e, b * x + d * y + f) for x, y in pts]


def compose(parent, child):
    """world = parent ∘ child (child applied first)."""
    a1, b1, c1, d1, e1, f1 = parent
    a2, b2, c2, d2, e2, f2 = child
    return (a1 * a2 + c1 * b2, b1 * a2 + d1 * b2,
            a1 * c2 + c1 * d2, b1 * c2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1, b1 * e2 + d1 * f2 + f1)


IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def segs_for_arc(radius, sweep=2 * math.pi, tol=TOL, nmin=8):
    """Segments needed so the chord of an arc of `radius` deviates at most `tol`."""
    if radius <= tol:
        return nmin
    step = 2 * math.acos(max(-1.0, 1 - tol / radius))
    return max(nmin if sweep >= 2 * math.pi - 1e-9 else 1, int(math.ceil(abs(sweep) / step)))


def flatten_cubic(p0, p1, p2, p3, tol=TOL):
    """Adaptive subdivision of a cubic bezier until flat within `tol` (points after p0, p3 included)."""
    out = []

    def rec(p0, p1, p2, p3, depth):
        # flatness: max distance of the control points from the chord
        dx, dy = p3[0] - p0[0], p3[1] - p0[1]
        n = math.hypot(dx, dy)
        if n < 1e-12:
            d = max(math.hypot(p1[0] - p0[0], p1[1] - p0[1]), math.hypot(p2[0] - p0[0], p2[1] - p0[1]))
        else:
            d = max(abs((p1[0] - p0[0]) * dy - (p1[1] - p0[1]) * dx),
                    abs((p2[0] - p0[0]) * dy - (p2[1] - p0[1]) * dx)) / n
        if d <= tol or depth > 18:
            out.append(p3)
            return
        m01 = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
        m12 = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        m23 = ((p2[0] + p3[0]) / 2, (p2[1] + p3[1]) / 2)
        a = ((m01[0] + m12[0]) / 2, (m01[1] + m12[1]) / 2)
        b = ((m12[0] + m23[0]) / 2, (m12[1] + m23[1]) / 2)
        c = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        rec(p0, m01, a, c, depth + 1)
        rec(c, b, m23, p3, depth + 1)

    rec(p0, p1, p2, p3, 0)
    return out


def ellipse(cx, cy, rx, ry, tol=TOL):
    n = segs_for_arc(max(rx, ry), tol=tol, nmin=12)
    return [(cx + rx * math.cos(2 * math.pi * k / n), cy + ry * math.sin(2 * math.pi * k / n)) for k in range(n)]


def rounded_rect(cx, cy, w, h, r=0.0, tol=TOL):
    """Closed loop (no repeated point), counter-clockwise, centred on (cx, cy)."""
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    r = max(0.0, min(r, w / 2, h / 2))
    if r <= 1e-9:
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    n = segs_for_arc(r, sweep=math.pi / 2, tol=tol)
    pts = []
    for (ccx, ccy, a0) in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(n + 1):
            t = math.radians(a0 + 90 * k / n)
            pts.append((ccx + r * math.cos(t), ccy + r * math.sin(t)))
    return pts


def signed_area(loop):
    a = np.asarray(loop, float)
    x, y = a[:, 0], a[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def evenodd_area(loops):
    """Area of the even-odd region of the loops (shapely)."""
    return region(loops).area


# ───────────────────────────── fill (hatch) ─────────────────────────────

def _rot(pts, ang):
    c, s = math.cos(ang), math.sin(ang)
    a = np.asarray(pts, float)
    return np.column_stack([a[:, 0] * c - a[:, 1] * s, a[:, 0] * s + a[:, 1] * c])


def scanlines(loops, interval, angle_deg=0.0):
    """Even-odd scan segments at `interval` mm, lines at `angle_deg` (0 = along +x).

    Returns a list of lines; each line is a list of (x_start, x_end) pairs in the ROTATED
    frame, plus the rotated y of each line: [(k, y, [(xa, xb), ...]), ...].
    Lines sit on a global grid y = (k + 0.5)·interval in the rotated frame, so the same
    region always gets the same lines (and a 10 mm square gets exactly 10/interval lines).
    Crossings use the half-open rule (ymin <= y < ymax) so a vertex on a line counts once.
    """
    if interval <= 0:
        raise ValueError("fill interval must be > 0")
    ang = -math.radians(angle_deg)                       # rotate the drawing so hatch lines are horizontal
    ks, xs = [], []
    for loop in loops:
        if len(loop) < 3:
            continue
        a = _rot(loop, ang)
        b = np.roll(a, -1, axis=0)
        y0, y1, x0, x1 = a[:, 1], b[:, 1], a[:, 0], b[:, 0]
        lo, hi = np.minimum(y0, y1), np.maximum(y0, y1)
        k0 = np.ceil(lo / interval - 0.5).astype(np.int64)            # first k with (k+.5)i >= lo
        k1 = np.ceil(hi / interval - 0.5).astype(np.int64)            # first k with (k+.5)i >= hi (excluded)
        cnt = np.maximum(k1 - k0, 0)
        if cnt.sum() == 0:
            continue
        idx = np.repeat(np.arange(len(a)), cnt)
        kk = np.concatenate([np.arange(s, e) for s, e in zip(k0[cnt > 0], k1[cnt > 0])])
        yy = (kk + 0.5) * interval
        t = (yy - y0[idx]) / (y1[idx] - y0[idx])
        ks.append(kk)
        xs.append(x0[idx] + t * (x1[idx] - x0[idx]))
    if not ks:
        return []
    k = np.concatenate(ks)
    x = np.concatenate(xs)
    order = np.lexsort((x, k))
    k, x = k[order], x[order]
    out = []
    bounds = np.flatnonzero(np.diff(k)) + 1
    for kk, xx in zip(np.split(k, bounds), np.split(x, bounds)):
        n = len(xx) - len(xx) % 2                          # an odd count can only come from an open/degenerate loop
        pairs = [(float(xx[i]), float(xx[i + 1])) for i in range(0, n, 2) if xx[i + 1] - xx[i] > 1e-9]
        if pairs:
            out.append((int(kk[0]), float((kk[0] + 0.5) * interval), pairs))
    return out


def _blocks(lines):
    """Group scan segments into blocks a serpentine can walk without long jumps: a segment joins
    the block of the one segment above it when the overlap is one-to-one (boustrophedon cells)."""
    blocks = []                    # each: list of (y, xa, xb)
    prev = []                      # [(xa, xb, block_index)] of the previous line
    prev_k = None
    for k, y, pairs in lines:
        cur = []
        if prev_k is None or k != prev_k + 1:
            prev = []
        for xa, xb in pairs:
            over = [j for j, (pa, pb, _) in enumerate(prev) if pa < xb and xa < pb]
            bi = None
            if len(over) == 1:
                pa, pb, pbi = prev[over[0]]
                # one-to-one: the previous segment must overlap only this segment on the current line
                n_back = sum(1 for qa, qb in pairs if pa < qb and qa < pb)
                if n_back == 1:
                    bi = pbi
            if bi is None:
                blocks.append([])
                bi = len(blocks) - 1
            blocks[bi].append((y, xa, xb))
            cur.append((xa, xb, bi))
        prev, prev_k = cur, k
    return blocks


def hatch(loops, interval, angle_deg=0.0, bidir=True):
    """Hatch segments for one direction, ordered to keep jumps short.

    Returns a list of ((x0, y0), (x1, y1)) in the drawing frame, in marking order and direction.
    bidir=True: serpentine inside each block (alternate direction line to line).
    bidir=False: every segment marked in the same direction (+x of the hatch frame).
    Blocks are visited greedily: next = the block whose start is nearest the current position.
    """
    lines = scanlines(loops, interval, angle_deg)
    if not lines:
        return []
    blocks = _blocks(lines)
    # per block, the ordered segments in the rotated frame
    walked = []
    for bl in blocks:
        segs, flip = [], False
        for y, xa, xb in bl:
            if bidir and flip:
                segs.append(((xb, y), (xa, y)))
            else:
                segs.append(((xa, y), (xb, y)))
            flip = not flip
        walked.append(segs)
    # greedy block order (vectorised distances); a block may also be walked from its last line backwards
    starts = np.array([w[0][0] for w in walked])
    ends_rev = np.array([w[-1][1] if bidir else w[-1][0] for w in walked])
    todo = np.ones(len(walked), bool)
    pos = starts[0]
    order = []
    for _ in range(len(walked)):
        if not order:
            i, rev = 0, False
        else:
            d1 = np.where(todo, np.hypot(*(starts - pos).T), np.inf)
            d2 = np.where(todo, np.hypot(*(ends_rev - pos).T), np.inf) if bidir else np.full(len(walked), np.inf)
            i1, i2 = int(np.argmin(d1)), int(np.argmin(d2))
            i, rev = (i1, False) if d1[i1] <= d2[i2] else (i2, True)
        todo[i] = False
        segs = walked[i]
        if rev:                     # walk the block bottom-up: reverse line order and each segment's direction
            segs = [(b, a) for a, b in reversed(segs)]
        order.append(segs)
        pos = np.array(segs[-1][1])
    ang = math.radians(angle_deg)
    c, s = math.cos(ang), math.sin(ang)
    rot = lambda p: (p[0] * c - p[1] * s, p[0] * s + p[1] * c)
    return [(rot(a), rot(b)) for segs in order for a, b in segs]


def fill_pass(loops, fill, pass_index=0):
    """All hatch segments for one pass of a `fill` dict (FORMAT.md): angle + angle_per_pass × pass,
    plus a second set at +90° when `cross`."""
    ang = fill.get("angle_deg", 0.0) + fill.get("angle_per_pass_deg", 0.0) * pass_index
    segs = hatch(loops, fill["interval_mm"], ang, fill.get("bidir", True))
    if fill.get("cross"):
        segs += hatch(loops, fill["interval_mm"], ang + 90.0, fill.get("bidir", True))
    return segs


# ───────────────────────────── wobble ─────────────────────────────

WOBBLE_SIZE_IS_RADIUS = True


def wobble_circle(pts, closed, size_mm, step_mm, tol=0.005, nmin=8):
    """The beam circles (diameter `size_mm`) while its centre advances `step_mm` along the path
    per revolution: p(s) = c(s) + r·(cos 2πs/step, sin 2πs/step), s = arc length along the path.

    This is the circular wobble of LightBurn's galvo "Wobble" (Size = diameter, Step = advance per
    loop), as also described in research/02-protocol.md §4.3. Samples per revolution are chosen so the
    chord deviates at most `tol` from the true circle (min `nmin`). Corners: the centre follows the
    polyline, so the circle sweeps around the corner. Returns an open polyline (the beam path).
    """
    # LightBurn's galvo Wobble "Size" behaves as the RADIUS on this machine: under the microscope (2026-10-21 22:29)
    # LightBurn's 0.15 line was about twice as wide as raio's when raio used size/2. WOBBLE_SIZE_IS_RADIUS selects.
    r = size_mm if WOBBLE_SIZE_IS_RADIUS else size_mm / 2.0
    if r <= 0 or step_mm <= 0:
        return list(pts) + ([pts[0]] if closed else [])
    a = np.asarray(list(pts) + ([pts[0]] if closed else []), float)
    seg = np.hypot(*np.diff(a, axis=0).T)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    total = cum[-1]
    n = segs_for_arc(r, tol=tol, nmin=nmin)
    ds = step_mm / n
    m = max(2, int(math.ceil(total / ds)) + 1)
    s = np.linspace(0.0, total, m)
    cx = np.interp(s, cum, a[:, 0])
    cy = np.interp(s, cum, a[:, 1])
    ph = 2 * math.pi * s / step_mm
    return list(zip((cx + r * np.cos(ph)).tolist(), (cy + r * np.sin(ph)).tolist()))


def wobble_zigzag(pts, closed, size_mm, step_mm, **_):
    """Alternative generator: a triangle wave of peak-to-peak `size_mm`, one period per `step_mm`."""
    a = np.asarray(list(pts) + ([pts[0]] if closed else []), float)
    seg = np.hypot(*np.diff(a, axis=0).T)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    s = np.arange(0.0, cum[-1] + 1e-12, step_mm / 2)
    cx, cy = np.interp(s, cum, a[:, 0]), np.interp(s, cum, a[:, 1])
    i = np.clip(np.searchsorted(cum, s, side="right") - 1, 0, len(seg) - 1)
    d = a[i + 1] - a[i]
    nrm = np.column_stack([-d[:, 1], d[:, 0]]) / np.maximum(seg[i], 1e-12)[:, None]
    sign = np.where(np.arange(len(s)) % 2 == 0, 1.0, -1.0) * size_mm / 2
    return list(zip((cx + nrm[:, 0] * sign).tolist(), (cy + nrm[:, 1] * sign).tolist()))


WOBBLE = {"circle": wobble_circle, "zigzag": wobble_zigzag}


def wobble(pts, closed, size_mm, step_mm, kind="circle", **kw):
    return WOBBLE[kind](pts, closed, size_mm, step_mm, **kw)


# ───────────────────────────── regions / kerf (shapely) ─────────────────────────────

def region(loops):
    """Even-odd region of the loops as a shapely geometry (XOR of the rings)."""
    from shapely.geometry import Polygon
    from shapely.validation import make_valid
    g = None
    for l in loops:
        if len(l) < 3:
            continue
        p = make_valid(Polygon(l))
        g = p if g is None else g.symmetric_difference(p)
    if g is None:
        from shapely.geometry import GeometryCollection
        return GeometryCollection()
    return g


def _loops_of(geom):
    out = []
    polys = getattr(geom, "geoms", [geom])
    for p in polys:
        if p.geom_type == "Polygon":
            if p.is_empty:
                continue
            out.append([tuple(c) for c in list(p.exterior.coords)[:-1]])
            out += [[tuple(c) for c in list(i.coords)[:-1]] for i in p.interiors]
        elif p.geom_type in ("MultiPolygon", "GeometryCollection"):
            out += _loops_of(p)
    return out


def kerf(loops, d_mm, join="round"):
    """Offset the even-odd region by d_mm (+ = grow outward, − = shrink). Returns loops."""
    if not d_mm:
        return [list(l) for l in loops]
    js = {"round": 1, "mitre": 2, "bevel": 3}[join]
    g = region(loops).buffer(d_mm, quad_segs=16, join_style=js)
    return _loops_of(g)
