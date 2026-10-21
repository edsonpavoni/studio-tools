#!/usr/bin/env python3
"""make_icons.py — the two home-screen icons, 180×180 PNG, pure standard library.
    python3 make_icons.py            writes icon-180.png here and in ../trilha/
Hub: a 2×2 of rounded tiles on the dark chrome. Hand Route: a copper trace with two
pads on FR4. Re-run after changing the numbers below; the iPad picks the icon up the
next time the page is added to the Home Screen."""
import math, os, struct, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
N = 180


def png(path, pix):
    raw = b"".join(b"\x00" + bytes(v for px in row for v in px) for row in pix)
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", N, N, 8, 2, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def hexc(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def rrect_sd(x, y, cx, cy, hw, hh, r):
    dx, dy = abs(x - cx) - hw + r, abs(y - cy) - hh + r
    return math.hypot(max(dx, 0), max(dy, 0)) + min(max(dx, dy), 0) - r


def seg_sd(x, y, ax, ay, bx, by):
    vx, vy, wx, wy = bx - ax, by - ay, x - ax, y - ay
    t = max(0, min(1, (wx * vx + wy * vy) / (vx * vx + vy * vy)))
    return math.hypot(wx - t * vx, wy - t * vy)


def paint(pix, shape_sd, colour, feather=1.0):
    for y in range(N):
        for x in range(N):
            d = shape_sd(x + .5, y + .5)
            if d < feather:
                t = 1 if d <= -feather else (feather - d) / (2 * feather)
                pix[y][x] = mix(pix[y][x], colour, t)


def canvas(colour):
    return [[colour] * N for _ in range(N)]


# --- hub: four tiles ---------------------------------------------------------
pix = canvas(hexc("#1E1E1E"))
tiles = [("#FCFBF8", 56, 56), ("#D0865A", 124, 56), ("#0E6B45", 56, 124), ("#B3B3B3", 124, 124)]
for col, cx, cy in tiles:
    paint(pix, lambda x, y, cx=cx, cy=cy: rrect_sd(x, y, cx, cy, 27, 27, 9), hexc(col))
png(os.path.join(HERE, "icon-180.png"), pix)

# --- hand route: copper trace + pads on FR4 -----------------------------------
pix = canvas(hexc("#2A211B"))
cu = hexc("#D0865A")
pts = [(40, 132), (40, 90), (76, 54), (110, 54), (140, 84), (140, 48)]
for (ax, ay), (bx, by) in zip(pts, pts[1:]):
    paint(pix, lambda x, y, a=(ax, ay), b=(bx, by): seg_sd(x, y, *a, *b) - 7, cu)
for cx, cy in (pts[0], pts[-1]):
    paint(pix, lambda x, y, cx=cx, cy=cy: math.hypot(x - cx, y - cy) - 17, cu)
    paint(pix, lambda x, y, cx=cx, cy=cy: math.hypot(x - cx, y - cy) - 6, hexc("#2A211B"))
png(os.path.join(HERE, "..", "trilha", "icon-180.png"), pix)
print("icons written")
