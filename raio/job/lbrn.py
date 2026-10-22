"""raio · job/lbrn.py — LightBurn `.lbrn2` → `.raio` (FORMAT.md "Importer: .lbrn2").

    job = lbrn.import_file("V5-70x45.lbrn2")       # raises LbrnError with readable reasons
    model.save(job, "V5-70x45.raio")

What it reads (research/01-studio-history.md §4–§5, checked against all 104 files on disk 2026-10-21):
  * CutSetting type Cut → mode line; Scan → mode fill (even-odd over every closed shape on the layer);
    Offset → fill with a warning (LightBurn's offset fill is approximated by hatch); Tool layers skipped;
    Image layers / Bitmap shapes → error (no raster in phase 1).
  * Shapes Rect (W, H, Cr, centre = XForm), Ellipse (Rx, Ry radii), Path (VertList + PrimList with
    L and B primitives, trilha's bare "LLL…" and "LineClosed"), Group (nested XForm, composed), Text → error.
  * LightBurn de-duplicates geometry: a Path may carry only VertID/PrimID and reuse the list another
    shape in the same file defined under that id (19 344 + 2 038 of 26 595 Paths do). Resolved in two passes.
  * Bezier B i j: P0 = v_i, P1 = v_i.c0, P2 = v_j.c1, P3 = v_j (checked: OW4_poem's 4-bezier path is a
    circle of radius 1). Flattened in WORLD mm to 0.01 mm chord deviation (after the XForm).
  * LightBurn frame → raio frame: subtract 78.75 on both axes (bottom-left origin on the 157.5 workspace).
  * Omitted fields → DEFAULTS below; the material-relevant ones are listed in source.defaults_applied.
"""
import hashlib, math, re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from . import geom, model

OFFSET_MM = 78.75

# ─── Defaults for fields LightBurn omits when they equal its own default ────────────────────────────────
# NOT prefs.ini "DefaultCutSetting": that is the template for new layers (it holds the copper cut recipe:
# globalRepeat 50, doOutput false, wobble on, 500 ns) and would silently multiply passes by 50.
# Each value comes from a field LightBurn DROPPED on save, or one that is only ever stored as a non-default.
DEFAULTS = {
    # field: (value, confidence, evidence)
    "frequency":    (20000, "high", "tests/lbrn_pwrow.py writes frequency 20000 on all five layers; LightBurn 2.1.00 re-saved "
                                    "tests/pw-row-lightburn.lbrn2 on 2026-10-21 19:01 without any frequency (and prefs.ini CutList "
                                    "likewise), while 30000 is kept elsewhere (prefs.ini.old); "
                                    "testEngrave.lbrn2 stores none and its recipe is 20 kHz (MATERIAL-SETTINGS 'Test 2'); "
                                    "usb-c_cutout.lbrn2 stores none and its recipe is 20 kHz"),
    "QPulseWidth":  (200, "high", "same re-save of pw-row-lightburn.lbrn2: PW_200ns lost QPulseWidth, 50/100/350/500 kept; V5-70x45_backup.lbrn2 "
                                  "(LightBurn 2.1.04 re-save) dropped 200; B6-PCB-RECIPE.md: LightBurn shows 200 ns when absent"),
    "interval":     (0.1, "medium", "B6-PCB-RECIPE.md: LightBurn 2.1.04 displayed Interval 0.1000 mm for a Scan layer without the tag "
                                    "(UI observation, not a dropped-on-save pair)"),
    "wobbleSize":   (0.1, "high", "V5-70x45_backup.lbrn2 dropped wobbleSize 0.1 (kept step 0.02); usb-c_cutout.lbrn2 has wobble on, "
                                  "no size, recipe size 0.10 (MATERIAL-SETTINGS stainless)"),
    "wobbleStep":   (0.05, "medium", "usb-c_cutout.lbrn2: wobbleEnable 1, no wobbleStep, proven recipe says step 0.05 "
                                     "(MATERIAL-SETTINGS stainless, 2026-09-21); V5 backup KEPT 0.02, so 0.02 is not the default"),
    "wobbleEnable": (0, "high", "only ever stored as 1 in 106 settings"),
    "numPasses":    (1, "high", "trilha omits it when 1 (lbrn.py), LightBurn likewise"),
    "globalRepeat": (1, "high", "only stored when >1"),
    "angle":        (0, "high", "testEngrave.lbrn2 stores none, recipe Scan Angle 0°"),
    "anglePerPass": (0, "high", "stored as 13/45/5/90 when used"),
    "crossHatch":   (0, "high", "only ever stored as 1 (26 settings); testEngrave recipe Cross-Hatch off, not stored"),
    "bidir":        (1, "high", "only ever stored as 0 (vendor test files); testEngrave recipe Bi-directional on, not stored"),
    "doOutput":     (1, "high", "only ever stored as 0"),
    "maxPower":     (20, "low", "LightBurn's fresh layers C05… in prefs.ini CutList carry maxPower 20 (always written in practice)"),
    "speed":        (100, "low", "LightBurn's fresh layers C05… in prefs.ini CutList carry speed 100 (always written in practice)"),
}
# a default "matters" (goes to source.defaults_applied and makes the file "imported with defaults") when
# it changes what the laser does on that layer's mode
MATTERS = {"line": {"frequency", "QPulseWidth", "maxPower", "speed"},
           "fill": {"frequency", "QPulseWidth", "interval", "maxPower", "speed"}}
MATTERS_WOBBLE = {"wobbleSize", "wobbleStep"}


class LbrnError(Exception):
    def __init__(self, reasons):
        self.reasons = list(reasons)
        super().__init__("; ".join(self.reasons))


def _f(s):
    return float(s)


def _xform(sh):
    xf = sh.find("XForm")
    if xf is None or not (xf.text or "").strip():
        return geom.IDENTITY
    v = [float(t) for t in xf.text.split()]
    return tuple(v) if len(v) == 6 else geom.IDENTITY


_VTOK = re.compile(r"V\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)((?:c[01][xy][-+0-9.eE]+)*)")
_CTOK = re.compile(r"c([01])([xy])([-+0-9.eE]+)")


def parse_vertlist(text):
    """[(x, y, c0 or None, c1 or None)]"""
    out = []
    for m in _VTOK.finditer(text or ""):
        c = {}
        for k, ax, val in _CTOK.findall(m.group(3)):
            c.setdefault(k, [None, None])[0 if ax == "x" else 1] = float(val)
        c0 = tuple(c["0"]) if "0" in c and None not in c["0"] else None
        c1 = tuple(c["1"]) if "1" in c and None not in c["1"] else None
        out.append((float(m.group(1)), float(m.group(2)), c0, c1))
    return out


def parse_primlist(text, nverts):
    """[(kind 'L'|'B', i, j)]. Dialects: indexed 'L0 1B1 2', trilha's 'LineClosed', bare 'LLL' (open, sequential)."""
    t = (text or "").strip()
    if not t:
        return [("L", i, i + 1) for i in range(nverts - 1)] + ([("L", nverts - 1, 0)] if nverts > 2 else [])
    if t == "LineClosed":
        return [("L", i, (i + 1) % nverts) for i in range(nverts)]
    if re.fullmatch(r"L+", t):
        return [("L", i, i + 1) for i in range(min(len(t), nverts - 1))]
    prims = []
    for kind, i, j in re.findall(r"([LB])\s*(\d+)\s+(\d+)", t):
        prims.append((kind, int(i), int(j)))
    if not prims:
        raise LbrnError([f"unknown PrimList dialect: {t[:40]!r}"])
    return prims


def path_polylines(verts, prims, m, tol=geom.TOL):
    """Chain primitives into world-space polylines; returns [(pts, closed)]."""
    W = lambda p: geom.apply_xform(m, [p])[0]
    out, cur, start_i, last_j = [], None, None, None
    for kind, i, j in prims:
        if i >= len(verts) or j >= len(verts):
            raise LbrnError([f"PrimList refers to vertex {max(i, j)} of {len(verts)}"])
        if cur is None or i != last_j:
            if cur:
                out.append((cur, start_i == last_j and len(cur) > 2))
            cur, start_i = [W(verts[i][:2])], i
        p0 = W(verts[i][:2]); p3 = W(verts[j][:2])
        if kind == "B":
            c0 = verts[i][2] or verts[i][:2]
            c1 = verts[j][3] or verts[j][:2]
            cur += geom.flatten_cubic(p0, W(c0), W(c1), p3, tol)
        else:
            cur.append(p3)
        last_j = j
    if cur:
        out.append((cur, start_i == last_j and len(cur) > 2))
    res = []
    for pts, closed in out:
        if closed and len(pts) > 1 and math.dist(pts[0], pts[-1]) < 1e-9:
            pts = pts[:-1]
        # drop consecutive duplicates
        clean = [pts[0]] + [q for p, q in zip(pts, pts[1:]) if math.dist(p, q) > 1e-7]
        if len(clean) >= 2:
            res.append((clean, closed and len(clean) >= 3))
    return res


def _scale(m):
    a, b, c, d, _, _ = m
    return max(math.hypot(a, b), math.hypot(c, d))


def _cut_settings(root):
    """index → dict(type, fields{tag: str}, pos)"""
    cs = {}
    for pos, el in enumerate(list(root.iter("CutSetting")) + list(root.iter("CutSetting_Img"))):
        f = {c.tag: c.get("Value") for c in el}
        try:
            idx = int(f.get("index"))
        except (TypeError, ValueError):
            continue
        typ = el.get("type") or ("Image" if el.tag == "CutSetting_Img" else "Cut")
        if el.tag == "CutSetting_Img":
            typ = "Image"
        cs.setdefault(idx, {"type": typ, "f": f, "pos": pos})
    return cs


def read_shapes(root, tol=geom.TOL):
    """Walk the shape tree. Returns ({cut_index: [(pts, closed), …]}, problems{kind: count}, text_backup_count)."""
    vdefs, pdefs = {}, {}
    for sh in root.iter("Shape"):
        if sh.get("Type") != "Path":
            continue
        vl, pl = sh.find("VertList"), sh.find("PrimList")
        if vl is not None and sh.get("VertID") is not None:
            if vdefs.setdefault(sh.get("VertID"), vl.text) != vl.text:
                raise LbrnError([f"VertID {sh.get('VertID')} defined twice with different lists"])
        if pl is not None and sh.get("PrimID") is not None:
            if pdefs.setdefault(sh.get("PrimID"), pl.text) != pl.text:
                raise LbrnError([f"PrimID {sh.get('PrimID')} defined twice with different lists"])
    by_idx, problems = {}, {}
    text_backup = 0

    def add(idx, pl):
        by_idx.setdefault(idx, []).extend(pl)

    def walk(sh, parent):
        nonlocal text_backup
        m = geom.compose(parent, _xform(sh))
        t = sh.get("Type")
        idx = sh.get("CutIndex")
        idx = int(idx) if idx is not None and idx.lstrip("-").isdigit() else None
        if t == "Group":
            ch = sh.find("Children")
            for c in (ch if ch is not None else []):
                if c.tag == "Shape":
                    walk(c, m)
        elif t == "Rect":
            w, h, cr = _f(sh.get("W", 0)), _f(sh.get("H", 0)), _f(sh.get("Cr", 0) or 0)
            loop = geom.rounded_rect(0, 0, w, h, cr, tol=tol / max(_scale(m), 1e-9))
            add(idx, [(geom.apply_xform(m, loop), True)])
        elif t == "Ellipse":
            rx, ry = _f(sh.get("Rx", 0)), _f(sh.get("Ry", 0))
            loop = geom.ellipse(0, 0, rx, ry, tol=tol / max(_scale(m), 1e-9))
            add(idx, [(geom.apply_xform(m, loop), True)])
        elif t == "Path":
            vl = sh.find("VertList")
            vt = vl.text if vl is not None else vdefs.get(sh.get("VertID"))
            pl = sh.find("PrimList")
            pt = pl.text if pl is not None else pdefs.get(sh.get("PrimID"))
            if vt is None:
                problems["Path without geometry (unresolved VertID)"] = problems.get("Path without geometry (unresolved VertID)", 0) + 1
                return
            if pt is None and sh.get("PrimID") is not None:
                problems["Path with unresolved PrimID"] = problems.get("Path with unresolved PrimID", 0) + 1
                return
            verts = parse_vertlist(vt)
            if len(verts) < 2:
                return
            add(idx, path_polylines(verts, parse_primlist(pt, len(verts)), m, tol))
        elif t == "Text":
            problems["Text"] = problems.get("Text", 0) + 1
            if sh.find("BackupPath") is not None:
                text_backup += 1
        elif t == "Bitmap":
            problems["Bitmap"] = problems.get("Bitmap", 0) + 1
        else:
            problems[f"shape type {t}"] = problems.get(f"shape type {t}", 0) + 1

    for sh in root.findall("Shape"):
        walk(sh, geom.IDENTITY)
    return by_idx, problems, text_backup


def _val(f, key, used):
    """Field value with LightBurn's omitted-default; records which defaults were applied."""
    if f.get(key) is not None and f.get(key) != "":
        return f[key]
    v = DEFAULTS[key][0]
    used.append(key)
    return v


def import_file(path, name=None, offset=OFFSET_MM, tol=geom.TOL, strict=True, place="file", discard_outside=False):
    """Parse a .lbrn2 and return a .raio job dict (validated). Raises LbrnError on anything raio cannot mark."""
    path = Path(path)
    raw = path.read_bytes()
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        raise LbrnError([f"not valid XML: {e}"])
    if root.tag != "LightBurnProject":
        raise LbrnError([f"root element is {root.tag}, not LightBurnProject"])
    cs = _cut_settings(root)
    by_idx, problems, text_backup = read_shapes(root, tol)
    errors, warns = [], []
    if problems.get("Text"):
        msg = f"{problems['Text']} Text shape(s): outline the text in LightBurn first"
        if text_backup:
            msg += f" ({text_backup} carry a BackupPath outline that raio does not use)"
        errors.append(msg)
    if problems.get("Bitmap"):
        errors.append(f"{problems['Bitmap']} Bitmap shape(s): raster images are not supported in phase 1")
    for k, v in problems.items():
        if k not in ("Text", "Bitmap"):
            errors.append(f"{v} × {k}")

    layers, defaults_applied, defaults_by_layer, pass_notes = [], set(), {}, []
    order_keys = []
    for idx in sorted(by_idx, key=lambda i: (i is None, i if i is not None else 0)):
        polys = by_idx[idx]
        if not polys:
            continue
        c = cs.get(idx)
        if c is None:
            warns.append(f"{len(polys)} shape(s) on cut index {idx} which has no CutSetting: LightBurn default layer values used")
            c = {"type": "Cut", "f": {"name": f"C{idx:02d}" if idx is not None else "C??"}, "pos": 10_000 + (idx or 0)}
        typ, f = c["type"], c["f"]
        lname = f.get("name") or f"C{idx:02d}"
        if typ == "Tool":
            warns.append(f"layer {lname}: Tool layer skipped ({len(polys)} shapes)")
            continue
        if typ == "Image":
            errors.append(f"layer {lname}: Image (raster) layer is not supported in phase 1")
            continue
        if typ not in ("Cut", "Scan", "Offset"):
            errors.append(f"layer {lname}: CutSetting type {typ!r} unknown")
            continue
        mode = "line" if typ == "Cut" else "fill"
        if typ == "Offset":
            warns.append(f"layer {lname}: Offset fill imported as a hatch fill (LightBurn's offset fill is not reproduced)")
        used = []
        g = lambda k: _val(f, k, used)
        power = float(g("maxPower")); speed = float(g("speed"))
        freq_khz = float(g("frequency")) / 1000.0
        pulse = int(round(float(g("QPulseWidth"))))
        num = int(float(g("numPasses"))); rep = int(float(g("globalRepeat")))
        passes = max(1, num) * max(1, rep)
        if rep > 1:
            pass_notes.append(f"{lname}: globalRepeat {rep} × numPasses {num} = {passes} passes")
        out = int(float(g("doOutput"))) != 0
        wob = None
        if int(float(g("wobbleEnable"))):
            wob = {"size_mm": float(g("wobbleSize")), "step_mm": float(g("wobbleStep"))}
            if mode == "fill":
                warns.append(f"layer {lname}: wobble on a fill layer ignored")
                wob = None
        fill = None
        if mode == "fill":
            fill = {"interval_mm": float(g("interval")), "angle_deg": float(g("angle")),
                    "angle_per_pass_deg": float(g("anglePerPass")), "bidir": int(float(g("bidir"))) != 0,
                    "cross": int(float(g("crossHatch"))) != 0, "even_odd": True}
        delays = dict(model.DELAYS_DEFAULT)
        if f.get("endDelay"):
            delays["end_us"] = int(round(float(f["endDelay"])))
            warns.append(f"layer {lname}: endDelay {f['endDelay']} read as µs (LightBurn's per-layer end delay; unit assumed)")
        for k, why in (("tabsEnabled", "tabs"), ("perforate", "perforation"), ("floodFill", "flood fill")):
            if f.get(k) not in (None, "0", ""):
                warns.append(f"layer {lname}: {why} is on in LightBurn and NOT reproduced by raio")
        if f.get("hide") == "1":
            warns.append(f"layer {lname}: hide=1 in LightBurn (hidden on screen; raio follows doOutput)")
        matters = MATTERS[mode] | (MATTERS_WOBBLE if wob else set())
        applied = sorted(k for k in used if k in matters)
        if applied and out:
            defaults_applied.update(applied)
            defaults_by_layer[lname] = applied
        shapes = []
        for pts, closed in polys:
            q = [(x - offset, y - offset) for x, y in pts]
            shapes.append(model.polyline(q, closed))
        if mode == "fill" and not any(s["closed"] for s in shapes):
            warns.append(f"layer {lname}: fill layer has only open shapes; nothing to fill")
        prio = f.get("priority")
        if prio is None:
            warns.append(f"layer {lname}: no priority in the file; run order = file order")
        order_keys.append((int(float(prio)) if prio is not None else 10_000, c["pos"]))
        layers.append(model.new_layer(f"L{idx}", lname, 0, mode, power, speed, freq_khz, pulse, passes,
                                      wobble=wob, fill=fill, kerf_mm=0, output=out, delays=delays, shapes=shapes))
    if not layers and not errors:
        errors.append("no shapes on any output layer")
    # order: priority, then position in the file; renumbered 0..N-1
    for rank, i in enumerate(sorted(range(len(layers)), key=lambda i: order_keys[i])):
        layers[i]["order"] = rank
    # placement: "file" keeps LightBurn's position (−78.75); "centre" moves the output layers' bbox centre to (0,0)
    if place == "centre" and layers:
        bb = geom.bbox([s["pts"] for L in layers if L["output"] for s in L["shapes"]])
        if bb:
            dx, dy = -(bb[0] + bb[2]) / 2, -(bb[1] + bb[3]) / 2
            for L in layers:
                for s in L["shapes"]:
                    s["pts"] = [[round(x + dx, 5), round(y + dy, 5)] for x, y in s["pts"]]
            warns.append(f"placed with --centre: moved by ({dx:+.3f}, {dy:+.3f}) mm from LightBurn's position")
    # LightBurn's prefs.ini has DiscardOutOfBoundsShapes=true: it silently skips shapes off the workspace.
    # raio refuses by default; discard_outside=True does what LightBurn does, loudly.
    if discard_outside:
        for L in layers:
            keep = [s for s in L["shapes"] if all(abs(p[0]) <= model.HALF_FIELD and abs(p[1]) <= model.HALF_FIELD for p in s["pts"])]
            if len(keep) != len(L["shapes"]):
                warns.append(f"layer {L['name']}: {len(L['shapes']) - len(keep)} shape(s) outside the field DISCARDED "
                             f"(as LightBurn's DiscardOutOfBoundsShapes does)")
                L["shapes"] = keep
        if not any(L["shapes"] for L in layers if L["output"]):
            errors.append("every output shape is outside the field: nothing left to mark")
    # field check after the shift (reference layers never fire: a warning, not an error)
    for L in layers:
        out = sum(1 for s in L["shapes"] for p in s["pts"] if abs(p[0]) > model.HALF_FIELD or abs(p[1]) > model.HALF_FIELD)
        if out and L["output"]:
            errors.append(f"layer {L['name']}: {out} point(s) outside the ±{model.HALF_FIELD} mm field after the −{offset} shift "
                          f"(drawn off LightBurn's workspace; `raio import --centre` places the job at the field centre, "
                          f"`--discard-outside` drops off-field shapes as LightBurn does)")
        elif out:
            warns.append(f"layer {L['name']} (output off): {out} point(s) outside the field, kept for the preview only")
    if errors and strict:
        raise LbrnError(errors)
    notes_el = root.find("Notes")
    notes = (notes_el.get("Notes") or "") if notes_el is not None else ""
    if pass_notes:
        notes = (notes + "\n" if notes else "") + "Passes: " + "; ".join(pass_notes) + "."
    mh = root.get("MaterialHeight")
    if mh not in (None, "0", "0.0"):
        warns.append(f"MaterialHeight {mh} mm in the file is ignored (FORMAT.md)")
    try:
        rel = str(path.resolve().relative_to(Path(__file__).resolve().parents[3]))
    except ValueError:
        rel = str(path)
    source = {"file": rel, "kind": "lbrn2", "sha1": hashlib.sha1(raw).hexdigest(),
              "app_version": root.get("AppVersion"), "device": root.get("DeviceName"),
              "defaults_applied": sorted(defaults_applied), "defaults_by_layer": defaults_by_layer,
              "import_warnings": warns, "imported": datetime.now().isoformat(timespec="seconds")}
    job = model.new_job(name or path.stem, layers, notes=notes, source=source)
    errs = model.validate(job)
    if errs and strict:
        raise LbrnError(errs)
    return job
