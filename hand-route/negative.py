"""
negative.py — compute the copper-clear region for a single-layer board.

The problem: circuit.json tells you where copper must STAY. A laser needs to know where
copper must GO. That is a boolean subtraction, and hand-rolling a polygon clipper for
self-intersecting trace outlines is a good way to ship a subtly wrong board.

So this does it on a raster instead, which is exact at the chosen resolution and has no
degenerate cases:

    1. paint every pad and trace into a boolean grid          (union is just OR)
    2. grow that by the isolation clearance                   (binary dilation)
    3. clear = inside the board AND NOT grown copper
    4. march the boundary of that region back out to polygons (marching squares)
    5. simplify the polygons so LightBurn is not asked to fill 40 000 points

Nested contours come out naturally: a copper island inside a cleared field produces its
own loop, and LightBurn's even-odd fill leaves it alone. That is the behaviour we want
and it falls out of the mask rather than being arranged by hand.

Needs numpy, which ships with the system Python here.
"""

import math

import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# 1-3. build the mask
# ─────────────────────────────────────────────────────────────────────────────

class Raster:
    def __init__(self, x0, y0, x1, y1, res):
        pad = 2 * res
        self.x0, self.y0 = x0 - pad, y0 - pad
        self.res = res
        self.w = int(math.ceil((x1 - x0 + 2 * pad) / res)) + 1
        self.h = int(math.ceil((y1 - y0 + 2 * pad) / res)) + 1
        self.g = np.zeros((self.h, self.w), dtype=bool)
        ys, xs = np.mgrid[0:self.h, 0:self.w]
        self.X = self.x0 + xs * res
        self.Y = self.y0 + ys * res

    def to_mm(self, col, row):
        return self.x0 + col * self.res, self.y0 + row * self.res

    def add_rect(self, cx, cy, w, h, rot_deg=0.0):
        if abs(rot_deg) < 1e-9:
            self.g |= ((np.abs(self.X - cx) <= w / 2) & (np.abs(self.Y - cy) <= h / 2))
        else:
            t = math.radians(rot_deg)
            dx, dy = self.X - cx, self.Y - cy
            u = dx * math.cos(t) + dy * math.sin(t)
            v = -dx * math.sin(t) + dy * math.cos(t)
            self.g |= ((np.abs(u) <= w / 2) & (np.abs(v) <= h / 2))

    def add_circle(self, cx, cy, dia):
        r = dia / 2.0
        self.g |= ((self.X - cx) ** 2 + (self.Y - cy) ** 2) <= r * r

    def add_capsule(self, x1, y1, x2, y2, width):
        """A trace segment: a rectangle with round ends. Painted as a distance test,
        so overlapping segments simply union instead of self-intersecting."""
        r = width / 2.0
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        if L2 < 1e-12:
            self.add_circle(x1, y1, width)
            return
        t = ((self.X - x1) * dx + (self.Y - y1) * dy) / L2
        t = np.clip(t, 0.0, 1.0)
        px, py = x1 + t * dx, y1 + t * dy
        self.g |= ((self.X - px) ** 2 + (self.Y - py) ** 2) <= r * r

    def add_polygon(self, pts):
        """Even-odd fill of a single ring."""
        inside = self._scanline([pts])
        self.g |= inside
        return inside

    def _scanline(self, rings):
        """Even-odd fill of a set of rings, one row at a time.

        The obvious implementation tests every edge against every pixel, which is
        O(edges x pixels). A copper pour has thousands of vertices and a 104 mm board
        has millions of pixels, so that multiplies out to billions of operations and
        simply never finishes. This walks each raster row instead and only computes
        where the edges cross it: O(rows x edges).
        """
        edges = []
        for pts in rings:
            n = len(pts)
            for i in range(n):
                x1, y1 = pts[i]
                x2, y2 = pts[(i + 1) % n]
                if y1 != y2:
                    edges.append((x1, y1, x2, y2))
        if not edges:
            return np.zeros_like(self.g)
        E = np.asarray(edges, dtype=float)
        x1, y1, x2, y2 = E[:, 0], E[:, 1], E[:, 2], E[:, 3]
        ylo, yhi = np.minimum(y1, y2), np.maximum(y1, y2)

        out = np.zeros_like(self.g)
        for row in range(self.h):
            yy = self.y0 + row * self.res
            hit = (ylo <= yy) & (yy < yhi)
            if not hit.any():
                continue
            xs = x1[hit] + (yy - y1[hit]) * (x2[hit] - x1[hit]) / (y2[hit] - y1[hit])
            xs.sort()
            cols = np.floor((xs - self.x0) / self.res + 0.5).astype(int)
            for a, b in zip(cols[0::2], cols[1::2]):
                a = max(a, 0); b = min(b, self.w)
                if b > a:
                    out[row, a:b] = True
        return out

    def add_rings(self, rings):
        """Fill a shape made of an outer ring and any number of inner rings (holes).

        One even-odd crossing test over ALL the rings at once gives outer-minus-inner
        for free, which is exactly what a copper pour with cut-outs is.
        """
        inside = self._scanline(rings)
        self.g |= inside
        return inside

    def polygon_mask(self, pts):
        keep = self.g.copy()
        self.g = np.zeros_like(self.g)
        m = self.add_polygon(pts)
        self.g = keep
        return m


def _shift(mask, dy, dx):
    """Shift with ZERO fill. np.roll wraps around the array edges, which welded
    copper on one side of the board to copper on the other side - a false short
    that survived every vector check because it only exists in wrapped raster
    space. Found 2026-08-23 after a verified-clean board kept failing."""
    out = np.zeros_like(mask)
    h, w = mask.shape
    ys0, ys1 = max(dy, 0), h + min(dy, 0)
    xs0, xs1 = max(dx, 0), w + min(dx, 0)
    out[ys0:ys1, xs0:xs1] = mask[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return out


def dilate(mask, radius_px):
    """Binary dilation by a disc via zero-filled shifts."""
    if radius_px <= 0:
        return mask
    r = int(math.ceil(radius_px))
    out = mask.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > radius_px * radius_px:
                continue
            out |= _shift(mask, dy, dx)
    return out



# ─────────────────────────────────────────────────────────────────────────────
# connected components, for short detection
# ─────────────────────────────────────────────────────────────────────────────

def count_nets(mask, pour_mask=None):
    """Number of electrically distinct regions, treating the whole copper pour as one.

    A pour arrives as many separate polygons that all belong to the same net. Counting
    them as separate regions makes the short check scream about a board that is fine,
    and worse, hides a real short behind the noise. So: count the components, collapse
    every component that touches the pour into a single one, and keep the rest.

    A trace that genuinely shorts to the pour still gets caught, because it stops being
    its own component and joins the pour's set, which lowers the count.
    """
    lab, n = label_components(mask)
    if pour_mask is None or not pour_mask.any():
        return n
    touching = set(np.unique(lab[pour_mask & mask]).tolist()) - {0}
    others = set(np.unique(lab[mask]).tolist()) - {0} - touching
    return len(others) + (1 if touching else 0)


def label_components(mask):
    """-> (labels array, count). Run-length union-find, 8-connected.

    Labels in the returned array are 1-based; 0 means background. The parent list is
    strictly 0-based, and keeping those two numbering schemes apart is the whole trick.
    """
    h, w = mask.shape
    parent = []

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    lab = np.zeros(mask.shape, dtype=np.int32)
    prev = []
    for y in range(h):
        idx = np.flatnonzero(np.diff(np.concatenate(([0], mask[y].view(np.int8), [0]))))
        runs = []
        for i in range(0, len(idx), 2):
            x0, x1 = int(idx[i]), int(idx[i + 1])
            me = len(parent)                 # 0-based index into parent
            parent.append(me)
            for (px0, px1, pidx) in prev:
                if px0 <= x1 and x0 <= px1:  # 8-connected: spans that touch or abut
                    union(me, pidx)
            lab[y, x0:x1] = me + 1           # 1-based in the label image
            runs.append((x0, x1, me))
        prev = runs

    if not parent:
        return lab, 0
    roots = np.array([find(i) for i in range(len(parent))], dtype=np.int32)
    remap = np.zeros(len(parent) + 1, dtype=np.int32)
    remap[1:] = roots + 1
    return remap[lab], len(set(roots.tolist()))


def count_components(mask):
    """Number of 8-connected regions in a boolean mask.

    Counting boundary loops is NOT the same thing and was wrong: one region with a
    hole in it has two loops, and two regions that merely nest have two loops as well.
    For "did these two nets just become one net" you need components.

    Run-length union-find, so the cost scales with the number of horizontal runs
    rather than the number of pixels. A 2000 x 1400 board is milliseconds.
    """
    h, w = mask.shape
    parent = []

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    prev_runs = []
    for y in range(h):
        row = mask[y]
        idx = np.flatnonzero(np.diff(np.concatenate(([0], row.view(np.int8), [0]))))
        runs = []
        for i in range(0, len(idx), 2):
            x0, x1 = int(idx[i]), int(idx[i + 1])          # [x0, x1)
            label = len(parent)
            parent.append(label)
            # 8-connectivity: touch a previous-row run if the spans are adjacent
            for (px0, px1, plabel) in prev_runs:
                if px0 <= x1 and x0 <= px1:
                    union(label, plabel)
            runs.append((x0, x1, label))
        prev_runs = runs

    roots = set(find(i) for i in range(len(parent)))
    return len(roots)


# ─────────────────────────────────────────────────────────────────────────────
# 4. marching squares
# ─────────────────────────────────────────────────────────────────────────────

def contours(mask, raster, simplify_mm=0.02):
    """-> list of closed polygons in mm tracing the boundary of `mask`."""
    m = mask.astype(np.uint8)
    a = m[:-1, :-1]      # top-left
    b = m[:-1, 1:]       # top-right
    c = m[1:, 1:]        # bottom-right
    d = m[1:, :-1]       # bottom-left
    case = a * 8 + b * 4 + c * 2 + d * 1

    # Edge midpoints in HALF-CELL INTEGER units, so endpoints are exact lattice
    # points and stitching matches them exactly. The old code emitted mm floats
    # and re-keyed them with round(p / (res * 0.51)): key spacing worked out to
    # 0.98 per grid step, so about every 50th grid line two DIFFERENT points
    # collapsed onto one key. The stitcher then hopped between two unrelated
    # boundaries passing within one pixel of each other, splicing loops and
    # orphaning the rest — on the V3 60x40 board that turned ~143 island
    # boundaries into 53 loops, and the even-odd fill would have lasered off
    # 231 mm2 of kept copper. Caught by Edson in LightBurn, 2026-08-23,
    # minutes before cutting. Never key floats when you can key integers.
    T, R, B, L = (1, 0), (2, 1), (1, 2), (0, 1)
    TABLE = {
        1: [(L, B)], 2: [(B, R)], 3: [(L, R)], 4: [(T, R)],
        5: [(L, T), (B, R)], 6: [(T, B)], 7: [(L, T)],
        8: [(T, L)], 9: [(T, B)], 10: [(T, R), (B, L)], 11: [(T, R)],
        12: [(L, R)], 13: [(B, R)], 14: [(L, B)],
    }

    segs = []
    for code, pairs in TABLE.items():
        rows, cols = np.nonzero(case == code)
        for row, col in zip(rows.tolist(), cols.tolist()):
            for (p, q) in pairs:
                segs.append(((2 * col + p[0], 2 * row + p[1]),
                             (2 * col + q[0], 2 * row + q[1])))
    half = raster.res / 2.0
    loops = [[(raster.x0 + ix * half, raster.y0 + iy * half) for (ix, iy) in l]
             for l in stitch_segments(segs)]
    return simplify_all(loops, simplify_mm)


def stitch_segments(segs):
    """Join marching-squares segments into closed loops. Endpoints are integer
    lattice points, so matching is exact; every lattice point touches at most
    two segments, which guarantees every chain closes. An open chain therefore
    means broken geometry, and this raises rather than return it — a force-
    closed polygon scrambles the even-odd fill of everything around it."""
    ends = {}
    for i, (p, q) in enumerate(segs):
        ends.setdefault(p, []).append((i, 0))
        ends.setdefault(q, []).append((i, 1))

    used = [False] * len(segs)
    loops = []
    for i in range(len(segs)):
        if used[i]:
            continue
        used[i] = True
        chain = [segs[i][0], segs[i][1]]
        while chain[-1] != chain[0]:
            nxt = None
            for (j, side) in ends.get(chain[-1], ()):
                if not used[j]:
                    nxt = (j, side)
                    break
            if nxt is None:
                raise RuntimeError(
                    "marching squares produced an open boundary chain of %d "
                    "points — refusing to emit broken fill geometry" % len(chain))
            j, side = nxt
            used[j] = True
            chain.append(segs[j][1 - side])
        if len(chain) > 4:
            loops.append(chain[:-1])          # drop the duplicated closing point
    return loops


def fill_check(polys, intended, raster):
    """Reconstruct the even-odd fill LightBurn will actually produce from the
    emitted polygons and diff it against the mask we meant.

    A half-pixel band of jitter along every boundary is inherent to marching
    squares plus simplification, so mismatches WITHIN one pixel of the intended
    boundary are noise and only reported. A mismatch DEEPER than that means a
    loop was lost, spliced, or force-closed — the failure that nearly lasered
    off 231 mm2 of the V3 board — and that raises. The stats it feeds are the
    honest answer to "will LightBurn cut what we verified?", which none of the
    mask-level checks can see: they all run before the polygons exist.

    Returns (overfill_mm2, underfill_mm2), band jitter included."""
    acc = np.zeros_like(intended)
    for poly in polys:
        acc ^= raster._scanline([poly])
    res2 = raster.res * raster.res
    over = float((acc & ~intended).sum()) * res2
    under = float((intended & ~acc).sum()) * res2
    over_deep = (acc & ~intended) & ~dilate(intended, 1)
    under_deep = (intended & ~acc) & ~dilate(~intended, 1)
    if over_deep.any() or under_deep.any():
        raise RuntimeError(
            "emitted fill polygons do not reproduce the intended region: "
            "%.2f mm2 of kept copper would be filled over, %.2f mm2 of clear "
            "missed, beyond boundary jitter. Refusing to build."
            % (float(over_deep.sum()) * res2, float(under_deep.sum()) * res2))
    return over, under


# ─────────────────────────────────────────────────────────────────────────────
# 5. simplify
# ─────────────────────────────────────────────────────────────────────────────

def simplify_all(loops, tol):
    return [rdp(l, tol) for l in loops if len(rdp(l, tol)) > 2]


def rdp(points, tol):
    """Ramer-Douglas-Peucker, iterative so a 40 000-point loop cannot blow the stack."""
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        x1, y1 = points[i]
        x2, y2 = points[j]
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy) or 1e-12
        best, bi = -1.0, None
        for k in range(i + 1, j):
            px, py = points[k]
            dist = abs(dy * px - dx * py + x2 * y1 - y2 * x1) / norm
            if dist > best:
                best, bi = dist, k
        if best > tol and bi is not None:
            keep[bi] = True
            stack.append((i, bi))
            stack.append((bi, j))
    return [p for p, k in zip(points, keep) if k]


# ─────────────────────────────────────────────────────────────────────────────

def clear_region(outline, pads, traces, pullback=0.05, res=0.05, simplify=0.02,
                 border=0.0, design_traces=None, pours=None):
    """The whole job. -> (polygons_in_mm, stats dict)

    outline   board polygon [(x, y), ...] in mm
    pads      [('rect', cx, cy, w, h) | ('circle', cx, cy, dia), ...]
    traces    [(points, width), ...]
    pullback  how far the CLEAR region is held back from the copper edge, in mm.
    design_traces  the traces at the widths the ROUTER chose, before any widening.
              This is the reference the short check measures against. Without it the
              check can only see damage done by the pullback, and will happily pass a
              board that `--min-trace` already shorted.

    ⚠️ `pullback` is kerf compensation, NOT design clearance, and the difference is a
    board-killer. The clear region is everything outside `dilate(copper, pullback)`, so
    every piece of copper survives `pullback` wider than drawn. Set it to half the laser
    kerf, which is small. Set it to something like a design clearance of 0.3 mm and any
    two traces closer than 0.6 mm will fuse into one — a short that looks perfectly
    deliberate on the finished board.

    The returned stats include `merged`, which is True when the pullback closed a gap
    that existed in the drawn copper. Treat that as a hard stop.
    """
    xs = [p[0] for p in outline]
    ys = [p[1] for p in outline]
    r = Raster(min(xs), min(ys), max(xs), max(ys), res)

    board = r.polygon_mask(outline)
    if border > 0:
        board &= ~(dilate(~board, border / res))

    for s in pads:
        if s[0] == "rect":
            r.add_rect(s[1], s[2], s[3], s[4])
        else:
            r.add_circle(s[1], s[2], s[3])
    for pts, width in traces:
        for i in range(len(pts) - 1):
            r.add_capsule(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], width)
    for rings in (pours or []):
        r.add_rings(rings)

    copper = r.g.copy()

    # The reference: copper exactly as the router drew it. Every net that is separate
    # here must still be separate at the end.
    pour_mask = None
    if pours:
        pr = Raster(min(xs), min(ys), max(xs), max(ys), res)
        for rings in pours:
            pr.add_rings(rings)
        pour_mask = pr.g

    if design_traces is not None:
        ref = Raster(min(xs), min(ys), max(xs), max(ys), res)
        for sp in pads:
            if sp[0] == "rect":
                ref.add_rect(sp[1], sp[2], sp[3], sp[4])
            else:
                ref.add_circle(sp[1], sp[2], sp[3])
        for pts, width in design_traces:
            for i in range(len(pts) - 1):
                ref.add_capsule(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], width)
        for rings in (pours or []):
            ref.add_rings(rings)
        parts_designed = count_nets(ref.g, pour_mask)
    else:
        parts_designed = None

    grown = dilate(copper, pullback / res) if pullback > 0 else copper
    clear = board & ~grown

    # Did anything fuse? Count actual connected regions, not boundary loops.
    parts_before = count_nets(copper, pour_mask)
    parts_after = count_nets(grown, pour_mask)
    baseline = parts_designed if parts_designed is not None else parts_before
    merged = parts_after < baseline

    # Minimum gap between different nets, measured rather than assumed: grow the copper
    # a little at a time and see how much it takes to fuse two nets. The gap is twice
    # that. This is the design rule the process actually has to meet, and the number to
    # compare against is 0.171 mm, the tightest gap on the 2025 TRIBE board that worked.
    min_gap = None
    step = max(res, 0.01)
    grow = step
    while grow <= 0.6:
        if count_nets(dilate(copper, grow / res), pour_mask) < baseline:
            min_gap = 2 * grow
            break
        grow += step

    polys = contours(clear, r, simplify)
    over, under = fill_check(polys, clear, r)
    stats = {
        "resolution_mm": res,
        "fill_overshoot_mm2": round(over, 3),
        "fill_undershoot_mm2": round(under, 3),
        "pullback_mm": pullback,
        "copper_parts_designed": baseline,
        "copper_parts_after_widening": parts_before,
        "copper_parts_after_pullback": parts_after,
        "merged": merged,
        "min_gap_mm": min_gap,
        "copper_mm2": float(copper.sum()) * res * res,
        "clear_mm2": float(clear.sum()) * res * res,
        "board_mm2": float(board.sum()) * res * res,
        "loops": len(polys),
        "points": sum(len(p) for p in polys),
    }
    return polys, stats


def moat_region(outline, signal_pads, signal_traces, keep_pads, clearance=0.5,
                pullback=0.05, res=0.05, simplify=0.02):
    """Isolation-moat mode: clear only a ring of width `clearance` around every piece
    of signal copper. Everything else stays copper and becomes the ground pour.

    This is the strategy the coupons proved: moats cut clean at every width tested,
    while clearing whole fields burned through the board. It is also 10-20x less
    laser time, and the surviving plane sinks heat away from the holes.

        moat = dilate(signal, clearance) - dilate(signal, pullback) - keep_pads

    The inner edge sits `pullback` off the copper (kerf compensation, same meaning as
    everywhere else). keep_pads are pour-net pads: the moat must not cut around them,
    that is how they join the plane.
    """
    xs = [p[0] for p in outline]
    ys = [p[1] for p in outline]
    r = Raster(min(xs), min(ys), max(xs), max(ys), res)
    board = r.polygon_mask(outline)

    for s in signal_pads:
        if s[0] == "rect":
            r.add_rect(s[1], s[2], s[3], s[4])
        else:
            r.add_circle(s[1], s[2], s[3])
    for pts, width in signal_traces:
        for i in range(len(pts) - 1):
            r.add_capsule(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], width)
    signal = r.g.copy()

    kp = Raster(min(xs), min(ys), max(xs), max(ys), res)
    for s in keep_pads:
        if s[0] == "rect":
            kp.add_rect(s[1], s[2], s[3], s[4])
        else:
            kp.add_circle(s[1], s[2], s[3])

    outer = dilate(signal, clearance / res)
    inner = dilate(signal, pullback / res) if pullback > 0 else signal
    clear = outer & ~inner & ~kp.g & board

    polys = contours(clear, r, simplify)
    over, under = fill_check(polys, clear, r)
    stats = {
        "fill_overshoot_mm2": round(over, 3),
        "fill_undershoot_mm2": round(under, 3),
        "clear_mm2": float(clear.sum()) * res * res,
        "board_mm2": float(board.sum()) * res * res,
        "loops": len(polys),
        "points": sum(len(q) for q in polys),
    }
    return polys, stats


def net_fusions(outline, pads_with_nets, traces, pullback=0.05, res=0.05):
    """Net-aware fusion check for hand-drawn boards with ornaments.

    Ornamental copper that fuses into ONE net is harmless decoration - the big-board
    artwork's fringe ticks did exactly that. The only geometric failure is a region
    that, after kerf pullback, contains pads of TWO OR MORE nets: that is a short the
    logical verifier cannot see, because a floating ornament belongs to no net until
    the laser physically merges it with something.

    pads_with_nets: [('rect'|'circle', x, y, w, h_or_dia, net_or_None), ...]
    -> (shorted_net_groups, n_regions)
    """
    xs = [p[0] for p in outline]
    ys = [p[1] for p in outline]
    r = Raster(min(xs), min(ys), max(xs), max(ys), res)
    for s in pads_with_nets:
        if s[0] == "rect":
            r.add_rect(s[1], s[2], s[3], s[4])
        else:
            r.add_circle(s[1], s[2], s[3])
    for pts, width in traces:
        for i in range(len(pts) - 1):
            r.add_capsule(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], width)
    grown = dilate(r.g, pullback / res) if pullback > 0 else r.g
    lab, n = label_components(grown)

    region_nets = {}
    for s in pads_with_nets:
        net = s[5]
        if not net:
            continue
        col = int(round((s[1] - r.x0) / res))
        row = int(round((s[2] - r.y0) / res))
        if 0 <= row < lab.shape[0] and 0 <= col < lab.shape[1] and lab[row, col]:
            region_nets.setdefault(int(lab[row, col]), set()).add(net)
    shorts = sorted(sorted(v) for v in region_nets.values() if len(v) > 1)
    return shorts, n
