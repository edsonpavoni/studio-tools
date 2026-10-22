"""raio · job/plan.py — `.raio` job → the board's list commands. Pure: never opens the device.

    p = plan.plan(job)                    # {"cmds": [(op, v1..), …], "layers": [...], "stats": {...}, "frame": [...]}
    svg = plan.preview_svg(job)           # mm viewBox, layers in run order, legend
    plan.preview_png(job, "out.png")      # raster of the same (OpenCV)

Command sequence (studio/raio/lmc/mark_test.py, which marked correctly on 2026-10-21):
  per layer, settings only when they change, in mark_test.settings() order:
      PulseWidth [0x8026, 0, ns] · QSwitchPeriod round(20000/kHz) · MarkCurrent round(pct·0xFFF/100)
      JumpSpeed spd(4000) · MarkSpeed spd(mm/s) · LaserOnDelay (|µs|, 0x8000 if negative) · LaserOffDelay
      PolygonDelay µs/10
  per ENTITY (one shape-pass in line mode; one whole hatch pass in fill mode), as mark_test.path_cmds():
      JumpTo first point · FiberOpenMO 1 · DelayTime 800 (8 ms) · MarkTo … · DelayTime end/10 · FiberOpenMO 0
  inside a fill entity each hatch line starts with JumpTo + DelayTime(jump_us/10) (LightBurn's 500 µs jump
  delay; 0x8004 is in 10 µs units, 02-protocol §3.2; 0x800D JumpDelay is not in lmc.L and was not used today).
  The job ends with a jump to the centre. lmc.run_list() adds ReadyMark 0x8051 first and EndOfList 0x8002 last;
  raio.py's fire() adds the 8 ms open-MO wait and the in-list WritePort, as mark_test.fire().
Differences from path_cmds, on purpose: no return to the centre after every shape (only at the end), and
hatch lines do not each get their own MO open/close + 8 ms (that would add 8 ms × thousands of lines).
"""
import math, sys
from pathlib import Path

from . import geom, model

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lmc"))
from lmc import L, FIELD_MM  # noqa: E402  (the opcodes; importing lmc does not open the device)

U_PER_MM = 65535 / FIELD_MM          # 416.0952 = jcz15.cor's scale (02-protocol §4.5)
CENTRE = (0x8000, 0x8000)
JUMP_SPEED = 4000                    # LightBurn Default_JumpSpeed (prefs.ini, device "B6 Mopa"); mark_test settings()
MO_OPEN_WAIT = 800                   # DelayTime units of 10 µs = 8 ms (Laser_OpenMODelay 8000 µs)
PACKET = 256                         # commands per 3072-byte packet (lmc.run_list)


class PlanError(ValueError):
    pass


class Galvo:
    """The same arithmetic as lmc.LMC.mm/spd/dist, with LightBurn's frame (swap=True, no flips)."""

    def __init__(self, u_per_mm=U_PER_MM, swap=True, sx=1, sy=1, cal=None):
        self.u_per_mm, self.swap, self.sx, self.sy = u_per_mm, swap, sx, sy
        # measured per-axis scale, the same file the driver reads (lmc/calibration.json); 1.0 = none
        self.cal_x = self.cal_y = 1.0
        if cal is None:
            try:
                import json, pathlib
                c = json.loads((pathlib.Path(__file__).resolve().parents[1] / "lmc" / "calibration.json").read_text())
                self.cal_x, self.cal_y = float(c.get("scale_x", 1)), float(c.get("scale_y", 1))
            except Exception:
                pass
        else:
            self.cal_x, self.cal_y = cal

    def mm(self, x, y):
        x, y = x * self.cal_x, y * self.cal_y             # as lmc.LMC.mm: calibration in raio's frame, before the galvo mapping
        if self.swap: x, y = y, x
        u = int(round(0x8000 + self.sx * x * self.u_per_mm)); v = int(round(0x8000 + self.sy * y * self.u_per_mm))
        if not (0 <= u <= 0xFFFF and 0 <= v <= 0xFFFF):
            raise PlanError(f"({x},{y}) mm is outside the field")
        return u, v

    def spd(self, mm_s):
        return min(0xFFFF, int(round(mm_s * self.u_per_mm / 1000)))   # as lmc.LMC.spd

    @staticmethod
    def dist(a, b):
        return min(0xFFFF, int(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5))


def _signed(us):
    return (abs(int(us)), 0x8000 if us < 0 else 0)


def layer_settings(layer, jump_speed=JUMP_SPEED, g=None):
    """The settings commands for a layer, as (key, cmd) pairs in mark_test.settings() order."""
    g = g or Galvo()
    d = layer["delays"]
    return [("pw", (L["PulseWidth"], 0, int(layer["pulse_ns"]))),
            ("qs", (L["QSwitchPeriod"], round(20000 / layer["freq_khz"]))),
            ("mc", (L["MarkCurrent"], round(layer["power_pct"] * 0xFFF / 100))),
            ("js", (L["JumpSpeed"], g.spd(jump_speed))),
            ("ms", (L["MarkSpeed"], g.spd(layer["speed_mm_s"]))),
            ("on", (L["LaserOnDelay"], *_signed(d["on_us"]))),
            ("off", (L["LaserOffDelay"], *_signed(d["off_us"]))),
            ("poly", (L["PolygonDelay"], int(round(d["poly_us"] / 10))))]


def layer_paths(layer, pass_index=0, wobble_kind="circle"):
    """The marked polylines (mm) of one pass of a layer, grouped as entities: [[polyline, …], …]."""
    polys = [s for s in layer["shapes"] if s.get("type") == "polyline"]
    if any(s.get("type") == "dot" for s in layer["shapes"]):
        raise PlanError(f"{layer['name']}: dots need LaserOnPoint 0x8003, not proven on this board yet")
    k = layer.get("kerf_mm") or 0
    if layer["mode"] == "fill":
        loops = [[tuple(p) for p in s["pts"]] for s in polys if s.get("closed")]
        if k:
            loops = geom.kerf(loops, k)
        segs = geom.fill_pass(loops, layer["fill"], pass_index)
        return [[[a, b] for a, b in segs]] if segs else []
    items = []
    closed = [[tuple(p) for p in s["pts"]] for s in polys if s.get("closed")]
    if k and closed:
        closed = geom.kerf(closed, k)
    items = [(l, True) for l in closed] + [([tuple(p) for p in s["pts"]], False) for s in polys if not s.get("closed")]
    ents = []
    for pts, cl in items:
        if layer.get("wobble"):
            w = layer["wobble"]
            ents.append([geom.wobble(pts, cl, w["size_mm"], w["step_mm"], kind=wobble_kind)])
        else:
            ents.append([list(pts) + ([pts[0]] if cl else [])])
    return ents


def plan(job, jump_speed=JUMP_SPEED, pass_order="shape", jump_delay=True, only=None, wobble_kind="circle", g=None, frame_kind="contour"):
    """Build the full command list. pass_order: 'shape' = every pass of a shape before the next shape (what
    LightBurn's numPasses does on this galvo: trilha's 16-pin header coupon drilled each hole fully in turn) or
    'layer' = the whole layer once per pass. Fill layers are always pass by pass (each pass has its own angle)."""
    errs = model.validate(job)
    if errs:
        raise PlanError("job is invalid: " + "; ".join(errs))
    g = g or Galvo()
    cmds, cache, pos = [], {}, CENTRE
    layers_out = []
    marks = []                                               # (first cmd index, layer name, pass 1.., passes): the board's "where are we"

    def at(name, p, n):
        if not marks or marks[-1][1:] != (name, p, n):
            marks.append((len(cmds), name, p, n))
    for layer in model.run_order(job, include_hidden=False):
        if only and layer["id"] not in only and layer["name"] not in only:
            continue
        st = {"id": layer["id"], "name": layer["name"], "mode": layer["mode"], "passes": layer["passes"],
              "mark_mm": 0.0, "jump_mm": 0.0, "jumps": 0, "marks": 0, "entities": 0, "first_cmd": len(cmds)}
        for key, c in layer_settings(layer, jump_speed, g):
            if cache.get(key) != c:
                cmds.append(c); cache[key] = c
        d = layer["delays"]
        jd = int(round(d["jump_us"] / 10))
        ed = int(round(d["end_us"] / 10))

        def entity(paths):
            nonlocal pos
            first = True
            opened = False
            for path in paths:
                q = [g.mm(*p) for p in path]
                # drop repeats that round to the same galvo point
                q = [q[0]] + [b for a, b in zip(q, q[1:]) if a != b]
                if len(q) < 2:
                    continue
                if first:
                    if q[0] != pos:                      # pass 2+ of a closed shape starts where the head already is
                        cmds.append((L["JumpTo"], *q[0], 0, g.dist(pos, q[0])))
                    cmds.append((L["FiberOpenMO"], 1)); cmds.append((L["DelayTime"], MO_OPEN_WAIT))
                    opened, first = True, False
                elif q[0] != pos:
                    cmds.append((L["JumpTo"], *q[0], 0, g.dist(pos, q[0])))
                    if jump_delay and jd:
                        cmds.append((L["DelayTime"], jd))
                st["jump_mm"] += math.dist(pos, q[0]) / g.u_per_mm; st["jumps"] += 1
                prev = q[0]
                for b in q[1:]:
                    cmds.append((L["MarkTo"], *b, 0, g.dist(prev, b)))
                    st["mark_mm"] += math.dist(prev, b) / g.u_per_mm; st["marks"] += 1
                    prev = b
                pos = prev
            if opened:
                cmds.append((L["DelayTime"], ed)); cmds.append((L["FiberOpenMO"], 0))
                st["entities"] += 1

        n_pass = layer["passes"]
        if layer["mode"] == "fill":
            for p in range(n_pass):
                at(layer["name"], p + 1, n_pass)
                for ent in layer_paths(layer, p, wobble_kind):
                    entity(ent)
        else:
            ents = layer_paths(layer, 0, wobble_kind)        # the same geometry every pass
            if pass_order == "shape":                        # pass numbers restart at every shape
                for ent in ents:
                    for p in range(n_pass):
                        at(layer["name"], p + 1, n_pass)
                        entity(ent)
            else:
                for p in range(n_pass):
                    at(layer["name"], p + 1, n_pass)
                    for ent in ents:
                        entity(ent)
            if layer.get("wobble"):
                outline = sum(geom.length(s["pts"], s.get("closed")) for s in layer["shapes"])
                st["advance_mm"] = outline * layer["passes"]
        st["n_cmds"] = len(cmds) - st["first_cmd"]
        st["est_s"] = _estimate(st, layer, jump_speed)
        # upper bound: if the board also waits the polygon delay at every MarkTo vertex
        st["est_s_hi"] = st["est_s"] + st["marks"] * layer["delays"]["poly_us"] * 1e-6
        if layer.get("wobble"):
            # if LightBurn's speed applied to the forward advance instead of the beam's loop path
            st["est_s_if_speed_is_advance"] = st["advance_mm"] / layer["speed_mm_s"] + st["entities"] * 0.008
        layers_out.append(st)
    if not layers_out:
        raise PlanError("nothing to mark (no output layer selected)")
    cmds.append((L["JumpTo"], *CENTRE, 0, g.dist(pos, CENTRE)))
    n = len(cmds) + 2                                        # + ReadyMark + EndOfList added by run_list
    stats = {"commands": n, "packets": math.ceil(n / PACKET), "layers": len(layers_out),
             "total_passes": sum(s["passes"] for s in layers_out),
             "mark_mm": sum(s["mark_mm"] for s in layers_out), "jump_mm": sum(s["jump_mm"] for s in layers_out),
             "est_s": sum(s["est_s"] for s in layers_out), "est_s_hi": sum(s["est_s_hi"] for s in layers_out),
             "max_packet_s": max_packet_seconds(cmds, g, jump_speed)}
    return {"cmds": cmds, "layers": layers_out, "stats": stats, "frame": frame_outline(job, only, frame_kind), "marks": marks}


def where(marks, i):
    """The (layer, pass, passes) the i-th planned command belongs to, from plan()['marks']; None before the first."""
    lo, hi = 0, len(marks)
    while lo < hi:
        mid = (lo + hi) // 2
        if marks[mid][0] <= i: lo = mid + 1
        else: hi = mid
    return marks[lo - 1][1:] if lo else None


def layer_colors(job):
    """{layer id: colour} exactly as preview_svg paints them (the board's table swatches)."""
    return {L["id"]: (PALETTE[i % len(PALETTE)] if L["output"] else "#9a9a9a") for i, L in enumerate(model.run_order(job))}


def _estimate(st, layer, jump_speed):
    """Rough seconds: marking + jumps + MO waits + jump/end delays (polygon delay per vertex NOT included;
    whether the board applies it at every MarkTo vertex is an open question)."""
    d = layer["delays"]
    return (st["mark_mm"] / layer["speed_mm_s"] + st["jump_mm"] / jump_speed
            + st["entities"] * (MO_OPEN_WAIT * 10 + d["end_us"]) * 1e-6
            + max(0, st["jumps"] - st["entities"]) * d["jump_us"] * 1e-6)


def max_packet_seconds(cmds, g=None, jump_speed=JUMP_SPEED):
    """Longest run time of any 256-command packet (polygon delay excluded). lmc.run_list waits at most 10 s for
    READY before sending the next packet, so a packet that keeps the board busy longer than that would time out."""
    g = g or Galvo()
    ms = js = None
    t = []
    for c in [(L["ReadyMark"],)] + list(cmds):
        op = c[0]
        if op == L["MarkSpeed"]: ms = c[1]
        elif op == L["JumpSpeed"]: js = c[1]
        if op == L["MarkTo"] and ms:
            t.append(c[4] / ms / 1000)                  # distance (units) / (units per ms)
        elif op == L["JumpTo"]:
            t.append(c[4] / (js or g.spd(jump_speed)) / 1000)
        elif op == L["DelayTime"]:
            t.append(c[1] * 10e-6)
        else:
            t.append(0.0)
    return max((sum(t[i:i + PACKET]) for i in range(0, len(t), PACKET)), default=0.0)


FRAME_MAX_PTS = 3000                    # the red loop's size; longer contours are thinned (the red is a guide, not the cut)


def frame_outline(job, only=None, kind="contour"):
    """The red frame. contour (default, Edson 2026-10-21 23:56: "frame boundaried instead of contour"): every output shape's
    outline, one after another (the red stays lit on the hops between shapes); box: the bounding rectangle (LightBurn's Frame)."""
    shapes = [s for L in model.run_order(job, include_hidden=False)
              if not only or L["id"] in only or L["name"] in only
              for s in L["shapes"] if s.get("type") == "polyline" and len(s.get("pts", [])) >= 2]
    if not shapes:
        return []
    if kind == "box":
        x0, y0, x1, y1 = geom.bbox([[p for s in shapes for p in s["pts"]]])
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    total = sum(len(s["pts"]) for s in shapes)
    k = max(1, math.ceil(total / FRAME_MAX_PTS))
    out = []
    for s in shapes:
        pts = [tuple(p) for p in s["pts"]]
        thin = pts[::k] + ([pts[-1]] if (len(pts) - 1) % k else [])
        if s.get("closed") and thin[-1] != thin[0]:
            thin.append(thin[0])
        out += thin
    return out


def describe_cmd(c):
    names = {v: k for k, v in L.items()}
    return f"{names.get(c[0], hex(c[0])):14s} " + " ".join(str(v) for v in c[1:])


# ───────────────────────────── preview ─────────────────────────────

PALETTE = ["#d1495b", "#2e86ab", "#3a9d23", "#e08e0b", "#8e44ad", "#16a085", "#c0392b", "#2c3e50"]


def _layer_preview_paths(layer, max_lines=6000):
    """Polylines to draw for a layer and a caption: hatch of pass 0 for fills (thinned), outlines otherwise."""
    polys = [s["pts"] for s in layer["shapes"] if s.get("type") == "polyline"]
    shown = ""
    hatch = []
    if layer["mode"] == "fill" and layer["output"]:
        loops = model.loops_of(layer)
        if loops:
            segs = geom.fill_pass(loops, layer["fill"], 0)
            step = max(1, math.ceil(len(segs) / max_lines))
            hatch = [[a, b] for a, b in segs[::step]]
            if step > 1:
                shown = f" (1 in {step} hatch lines shown)"
    return polys, hatch, shown


def legend_lines(job):
    out = []
    for i, L in enumerate(model.run_order(job)):
        s = (f"{L['order']}. {L['name']} · {L['mode']} · {L['power_pct']:g}% {L['speed_mm_s']:g} mm/s "
             f"{L['freq_khz']:g} kHz {L['pulse_ns']} ns · ×{L['passes']}")
        if L.get("wobble"):
            s += f" · wobble {L['wobble']['size_mm']:g}/{L['wobble']['step_mm']:g}"
        if L.get("fill"):
            f = L["fill"]
            s += f" · int {f['interval_mm']:g} ∠{f['angle_deg']:g}+{f['angle_per_pass_deg']:g}/pass" + \
                 (" bidir" if f["bidir"] else "") + (" cross" if f["cross"] else "")
        if not L["output"]:
            s += " · NOT MARKED"
        out.append(s)
    return out


def preview_svg(job, margin=4.0, field=False, board=False):
    """SVG string, units mm, +y up (toward the column) as on LightBurn's screen.
    board=True: the board page's version: no ground (the page is black), no title or legend (the page has the table)."""
    layers = model.run_order(job)
    allpts = [p for L in layers for s in L["shapes"] if s.get("type") == "polyline" for p in s["pts"]]
    if field or not allpts:
        x0, y0, x1, y1 = -model.HALF_FIELD, -model.HALF_FIELD, model.HALF_FIELD, model.HALF_FIELD
    else:
        x0, y0, x1, y1 = geom.bbox([allpts])
    x0 -= margin; y0 -= margin; x1 += margin; y1 += margin
    w, h = x1 - x0, y1 - y0
    fs = max(w, h) / 45
    leg = [] if board else legend_lines(job)
    head = [] if board else [job["name"]] + ([job["notes"].splitlines()[0][:120]] if job.get("notes") else [])
    lh = fs * 1.5 * (len(leg) + len(head) + 1) if not board else 0
    sw = max(w, h) / 900
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.2f}mm" height="{h + lh:.2f}mm" '
           f'viewBox="{x0:.3f} {-y1:.3f} {w:.3f} {h + lh:.3f}" font-family="Helvetica, Arial, sans-serif">',
           ("" if board else f'<rect x="{x0:.3f}" y="{-y1:.3f}" width="{w:.3f}" height="{h + lh:.3f}" fill="#fafaf7"/>'),
           '<g transform="scale(1,-1)">',
           f'<rect x="{-model.HALF_USABLE}" y="{-model.HALF_USABLE}" width="{2 * model.HALF_USABLE}" height="{2 * model.HALF_USABLE}" '
           f'fill="none" stroke="#bbb" stroke-dasharray="{sw * 6:.3f}" stroke-width="{sw:.3f}"/>',
           f'<path d="M{-fs} 0H{fs}M0 {-fs}V{fs}" stroke="#999" stroke-width="{sw:.3f}"/>']
    for i, L in enumerate(layers):
        col = PALETTE[i % len(PALETTE)] if L["output"] else "#9a9a9a"
        polys, hatch, _ = _layer_preview_paths(L)
        dash = "" if L["output"] else f' stroke-dasharray="{sw * 4:.3f}"'
        out.append(f'<g id="{L["id"]}" data-name="{L["name"]}" data-order="{L["order"]}" fill="none" stroke="{col}">')
        if hatch:
            out.append(f'<path stroke-width="{sw * 0.6:.4f}" opacity="0.7" d="' +
                       "".join(f"M{a[0]:.3f} {a[1]:.3f}L{b[0]:.3f} {b[1]:.3f}" for a, b in hatch) + '"/>')
        if L.get("wobble") and L["output"]:
            out.append(f'<g stroke-width="{L["wobble"]["size_mm"]:.3f}" opacity="0.25" stroke-linejoin="round">')
            for pts, s in zip(polys, [s for s in L["shapes"] if s.get("type") == "polyline"]):
                out.append(f'<path d="M' + "L".join(f"{x:.3f} {y:.3f}" for x, y in pts) + ("Z" if s["closed"] else "") + '"/>')
            out.append("</g>")
        for s in L["shapes"]:
            if s.get("type") != "polyline":
                continue
            out.append(f'<path stroke-width="{sw * 1.2:.4f}"{dash} d="M' + "L".join(f"{x:.3f} {y:.3f}" for x, y in s["pts"]) +
                       ("Z" if s["closed"] else "") + '"/>')
        out.append("</g>")
    out.append("</g>")
    y = h - y1 + fs * 1.6
    for n, t in enumerate(head):
        out.append(f'<text x="{x0 + fs * 0.5:.3f}" y="{-y1 + y:.3f}" font-size="{fs * (1.15 if n == 0 else 0.9):.3f}" '
                   f'fill="#222" font-weight="{"bold" if n == 0 else "normal"}">{_esc(t)}</text>')
        y += fs * 1.5
    for i, (L, t) in enumerate(zip(layers, leg)):
        col = PALETTE[i % len(PALETTE)] if L["output"] else "#9a9a9a"
        out.append(f'<rect x="{x0 + fs * 0.5:.3f}" y="{-y1 + y - fs * 0.8:.3f}" width="{fs * 0.9:.3f}" height="{fs * 0.9:.3f}" fill="{col}"/>')
        out.append(f'<text x="{x0 + fs * 1.8:.3f}" y="{-y1 + y:.3f}" font-size="{fs * 0.85:.3f}" fill="#222">{_esc(t)}</text>')
        y += fs * 1.5
    out.append("</svg>")
    return "\n".join(out)


def _esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def preview_png(job, path, px=1400, margin=4.0):
    """Raster preview with OpenCV (no cairo needed): same geometry, legend underneath."""
    import cv2, numpy as np
    layers = model.run_order(job)
    allpts = [p for L in layers for s in L["shapes"] if s.get("type") == "polyline" for p in s["pts"]]
    x0, y0, x1, y1 = geom.bbox([allpts]) if allpts else (-75, -75, 75, 75)
    x0 -= margin; y0 -= margin; x1 += margin; y1 += margin
    sc = px / max(x1 - x0, y1 - y0)
    W, H = int((x1 - x0) * sc) + 1, int((y1 - y0) * sc) + 1
    leg = [job["name"]] + legend_lines(job)
    img = np.full((H + 26 * len(leg) + 16, max(W, 900), 3), 250, np.uint8)
    P = lambda p: (int(round((p[0] - x0) * sc)), int(round((y1 - p[1]) * sc)))
    hexc = lambda c: tuple(int(c[i:i + 2], 16) for i in (5, 3, 1))
    for i, L in enumerate(layers):
        col = hexc(PALETTE[i % len(PALETTE)]) if L["output"] else (154, 154, 154)
        polys, hatch, _ = _layer_preview_paths(L, max_lines=20000)
        for a, b in hatch:
            cv2.line(img, P(a), P(b), col, 1, cv2.LINE_AA)
        for s in L["shapes"]:
            if s.get("type") != "polyline":
                continue
            arr = np.array([P(p) for p in s["pts"]], np.int32)
            if L.get("wobble") and L["output"]:
                ov = img.copy()
                cv2.polylines(ov, [arr], s["closed"], col, max(1, int(L["wobble"]["size_mm"] * sc)), cv2.LINE_AA)
                img[:] = cv2.addWeighted(ov, 0.3, img, 0.7, 0)
            cv2.polylines(img, [arr], s["closed"], col, 1, cv2.LINE_AA)
    for n, t in enumerate(leg):
        col = (40, 40, 40) if n == 0 else (hexc(PALETTE[(n - 1) % len(PALETTE)]) if layers[n - 1]["output"] else (120, 120, 120))
        t = t.replace("·", "|").replace("×", "x").replace("∠", "angle ").replace("²", "2")
        cv2.putText(img, t.encode("ascii", "replace").decode(), (10, H + 22 + 26 * n), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 1, cv2.LINE_AA)
    cv2.imwrite(str(path), img)
    return path
