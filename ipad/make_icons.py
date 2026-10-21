#!/usr/bin/env python3
"""make_icons.py — the home-screen icons, 180×180 PNG, pure standard library.
    python3 make_icons.py
Takes the Noun Project glyphs in icons/ (black on transparent, 512 px; see icons/README.md),
inverts them to bone white, scales them to fit a 108 px square, and sets them on black:
  icons/delight.png    → ./icon-180.png            (the hub)
  icons/strategy.png   → ../rascunho/icon-180.png
  icons/understand.png → ../trilha/icon-180.png
Re-run after changing a glyph; the iPad picks the icon up when the page is re-added to
the Home Screen."""
import os, struct, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
N, GLYPH = 180, 108
BG, INK = (0, 0, 0), (232, 228, 220)
JOBS = [("delight.png", HERE), ("strategy.png", os.path.join(HERE, "..", "rascunho")),
        ("understand.png", os.path.join(HERE, "..", "trilha"))]


def read_png(path):
    """8-bit RGBA or RGB or grey(+alpha), non-interlaced → (w, h, [[(r,g,b,a)…]])."""
    data = open(path, "rb").read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", path
    pos, idat, w = 8, b"", 0
    while pos < len(data):
        ln, = struct.unpack(">I", data[pos:pos + 4]); typ = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]; pos += 12 + ln
        if typ == b"IHDR":
            w, h, depth, ctype, _, _, inter = struct.unpack(">IIBBBBB", body)
            assert depth == 8 and inter == 0, "need 8-bit non-interlaced"
            bpp = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
        elif typ == b"IDAT":
            idat += body
    raw = zlib.decompress(idat)
    stride = w * bpp
    rows, prev = [], bytearray(stride)
    p = 0
    for _ in range(h):
        f = raw[p]; line = bytearray(raw[p + 1:p + 1 + stride]); p += 1 + stride
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if f == 1: line[i] = (line[i] + a) & 255
            elif f == 2: line[i] = (line[i] + b) & 255
            elif f == 3: line[i] = (line[i] + (a + b) // 2) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        px = []
        for i in range(0, stride, bpp):
            v = line[i:i + bpp]
            if bpp == 4: px.append(tuple(v))
            elif bpp == 3: px.append((v[0], v[1], v[2], 255))
            elif bpp == 2: px.append((v[0], v[0], v[0], v[1]))
            else: px.append((v[0], v[0], v[0], 255))
        rows.append(px); prev = line
    return w, h, rows


def write_png(path, pix):
    raw = b"".join(b"\x00" + bytes(v for px in row for v in px) for row in pix)
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", N, N, 8, 2, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def coverage(rows):
    """The glyph as an alpha map: dark, opaque pixels count. Trim to the drawn box."""
    h, w = len(rows), len(rows[0])
    a = [[(px[3] / 255) * (1 - (px[0] + px[1] + px[2]) / 765) for px in row] for row in rows]
    ys = [y for y in range(h) if any(v > .05 for v in a[y])]
    xs = [x for x in range(w) if any(a[y][x] > .05 for y in range(h))]
    y0, y1, x0, x1 = ys[0], ys[-1] + 1, xs[0], xs[-1] + 1
    return [row[x0:x1] for row in a[y0:y1]]


def box_scale(a, size):
    """Area-average the alpha map so its longer side becomes `size`."""
    h, w = len(a), len(a[0])
    s = size / max(h, w)
    nw, nh = max(1, round(w * s)), max(1, round(h * s))
    out = []
    for oy in range(nh):
        y0, y1 = oy / s, (oy + 1) / s
        row = []
        for ox in range(nw):
            x0, x1 = ox / s, (ox + 1) / s
            tot = area = 0.0
            for y in range(int(y0), min(h, int(math_ceil(y1)))):
                wy = min(y + 1, y1) - max(y, y0)
                for x in range(int(x0), min(w, int(math_ceil(x1)))):
                    wx = min(x + 1, x1) - max(x, x0)
                    tot += a[y][x] * wx * wy; area += wx * wy
            row.append(tot / area if area else 0)
        out.append(row)
    return out


def math_ceil(v):
    return int(-(-v // 1))


for name, dest in JOBS:
    w, h, rows = read_png(os.path.join(HERE, "icons", name))
    g = box_scale(coverage(rows), GLYPH)
    gh, gw = len(g), len(g[0])
    pix = [[BG] * N for _ in range(N)]
    oy, ox = (N - gh) // 2, (N - gw) // 2
    for y in range(gh):
        for x in range(gw):
            t = g[y][x]
            if t > 0:
                pix[oy + y][ox + x] = tuple(round(BG[i] + (INK[i] - BG[i]) * t) for i in range(3))
    out = os.path.join(dest, "icon-180.png")
    write_png(out, pix)
    print("wrote", os.path.normpath(out), "from", name)
