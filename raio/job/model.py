"""raio · job/model.py — the `.raio` job file (FORMAT.md, schema v1): load, validate, save, totals.

A job is a plain dict exactly as FORMAT.md shows it; this module adds no classes on purpose,
so a `.raio` read by hand, by trilha or by a test is the same object raio plans from.

    job = model.load("x.raio")          # raises JobError with readable messages if invalid
    errs = model.validate(job)          # [] when good; warnings via model.warnings(job)
    model.save(job, "x.raio")
    for row in model.totals(job): ...   # run order, passes, path length per layer
"""
import json, math
from datetime import datetime
from pathlib import Path

from . import geom

SCHEMA = 1
FIELD_MM = 157.5                    # lmc.FIELD_MM
HALF_FIELD = FIELD_MM / 2           # ±78.75: the galvo can reach it
HALF_USABLE = 75.0                  # usable 150 mm (MACHINE.md)
MAX_SPEED = 7000                    # LightBurn device "B6 Mopa" MaxSpeed (prefs.ini)
FREQ_KHZ = (1, 4000)                # Laser_MinFreq / Laser_MaxFreq (prefs.ini); 02-protocol §4.4
# pulse widths: meerk40t's JPT list (02-protocol §4.4) + 350/500 used by the studio's locked recipes
KNOWN_PULSES = {1, 2, 4, 6, 9, 13, 20, 30, 45, 55, 60, 80, 100, 150, 200, 250, 350, 500}
# LightBurn's B6 timing (prefs.ini, device "B6 Mopa": Default_LaserOn_TC −300, LaserOff 100, Polygon 100,
# Min/MaxJumpDelay 500, End 300)
DELAYS_DEFAULT = {"on_us": -300, "off_us": 100, "poly_us": 100, "jump_us": 500, "end_us": 300}
FILL_KEYS = ("interval_mm", "angle_deg", "angle_per_pass_deg", "bidir", "cross", "even_odd")


class JobError(ValueError):
    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("invalid .raio job:\n  " + "\n  ".join(self.errors))


# ───────────────────────────── construction ─────────────────────────────

def new_job(name, layers=None, notes="", material=None, source=None):
    return {"raio": SCHEMA, "name": name, "created": datetime.now().isoformat(timespec="seconds"),
            "source": source, "material": material or {"name": "", "thickness_mm": None},
            "notes": notes, "layers": layers or [], "z": None, "log": []}


def new_layer(id, name, order, mode, power_pct, speed_mm_s, freq_khz, pulse_ns, passes,
              wobble=None, fill=None, kerf_mm=0, output=True, delays=None, shapes=None):
    return {"id": id, "name": name, "order": order, "output": output, "mode": mode,
            "power_pct": power_pct, "speed_mm_s": speed_mm_s, "freq_khz": freq_khz, "pulse_ns": pulse_ns,
            "passes": passes, "wobble": wobble, "fill": fill, "kerf_mm": kerf_mm,
            "delays": dict(DELAYS_DEFAULT if delays is None else delays), "shapes": shapes or []}


def polyline(pts, closed):
    return {"type": "polyline", "closed": bool(closed), "pts": [[round(x, 5), round(y, 5)] for x, y in pts]}


# ───────────────────────────── validation ─────────────────────────────

def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def validate(job):
    """Every problem that would make raio refuse the job, as readable sentences."""
    e = []
    if not isinstance(job, dict):
        return ["the file is not a JSON object"]
    if job.get("raio") != SCHEMA:
        e.append(f"'raio' must be {SCHEMA} (schema version), got {job.get('raio')!r}")
    if not isinstance(job.get("name"), str) or not job.get("name"):
        e.append("'name' must be a non-empty string")
    for k in ("created", "notes"):
        if k in job and job[k] is not None and not isinstance(job[k], str):
            e.append(f"'{k}' must be a string")
    if not isinstance(job.get("material", {}), dict):
        e.append("'material' must be an object {name, thickness_mm}")
    if job.get("z") is not None and not isinstance(job["z"], dict):
        e.append("'z' must be null or a focus plan object")
    if not isinstance(job.get("log", []), list):
        e.append("'log' must be a list")
    layers = job.get("layers")
    if not isinstance(layers, list) or not layers:
        e.append("'layers' must be a non-empty list")
        return e
    ids = set()
    for i, L in enumerate(layers):
        tag = f"layer {i} ({L.get('name', '?') if isinstance(L, dict) else '?'})"
        if not isinstance(L, dict):
            e.append(f"{tag}: not an object"); continue
        if not isinstance(L.get("id"), str) or not L["id"]:
            e.append(f"{tag}: 'id' must be a non-empty string")
        elif L["id"] in ids:
            e.append(f"{tag}: duplicate id {L['id']!r}")
        ids.add(L.get("id"))
        if not isinstance(L.get("name"), str):
            e.append(f"{tag}: 'name' must be a string")
        if not isinstance(L.get("order"), int) or isinstance(L.get("order"), bool):
            e.append(f"{tag}: 'order' must be an integer (run order, lower first)")
        if not isinstance(L.get("output"), bool):
            e.append(f"{tag}: 'output' must be true or false")
        mode = L.get("mode")
        if mode not in ("line", "fill"):
            e.append(f"{tag}: 'mode' must be 'line' or 'fill', got {mode!r}")
        p = L.get("power_pct")
        if not _num(p) or not 0 <= p <= 100:
            e.append(f"{tag}: power_pct must be 0–100, got {p!r}")
        s = L.get("speed_mm_s")
        if not _num(s) or not 0 < s <= MAX_SPEED:
            e.append(f"{tag}: speed_mm_s must be >0 and ≤{MAX_SPEED}, got {s!r}")
        f = L.get("freq_khz")
        if not _num(f) or not FREQ_KHZ[0] <= f <= FREQ_KHZ[1]:
            e.append(f"{tag}: freq_khz must be {FREQ_KHZ[0]}–{FREQ_KHZ[1]}, got {f!r}")
        pw = L.get("pulse_ns")
        if not isinstance(pw, int) or isinstance(pw, bool) or not 1 <= pw <= 500:
            e.append(f"{tag}: pulse_ns must be an integer 1–500 ns, got {pw!r}")
        n = L.get("passes")
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            e.append(f"{tag}: passes must be an integer ≥1, got {n!r}")
        w = L.get("wobble")
        if w is not None:
            if not isinstance(w, dict) or not _num(w.get("size_mm")) or not _num(w.get("step_mm")) \
                    or w["size_mm"] <= 0 or w["step_mm"] <= 0:
                e.append(f"{tag}: wobble must be null or {{size_mm>0, step_mm>0}}, got {w!r}")
        fl = L.get("fill")
        if mode == "fill":
            if not isinstance(fl, dict):
                e.append(f"{tag}: mode 'fill' needs a fill object {{{', '.join(FILL_KEYS)}}}")
            else:
                miss = [k for k in FILL_KEYS if k not in fl]
                if miss:
                    e.append(f"{tag}: fill is missing {miss} (every field explicit)")
                elif not _num(fl["interval_mm"]) or not 0.001 <= fl["interval_mm"] <= 10:
                    e.append(f"{tag}: fill.interval_mm must be 0.001–10, got {fl['interval_mm']!r}")
                if isinstance(fl, dict) and fl.get("even_odd") is False:
                    e.append(f"{tag}: fill.even_odd=false (non-zero winding) is not implemented")
            if w is not None:
                e.append(f"{tag}: wobble on a fill layer is not supported")
        elif fl is not None:
            e.append(f"{tag}: 'fill' must be null on a line layer")
        k = L.get("kerf_mm", 0)
        if not _num(k) or abs(k) > 5:
            e.append(f"{tag}: kerf_mm must be a number within ±5 mm, got {k!r}")
        d = L.get("delays")
        if not isinstance(d, dict) or any(not isinstance(d.get(x), int) or isinstance(d.get(x), bool) for x in DELAYS_DEFAULT):
            e.append(f"{tag}: delays must hold integer µs for {list(DELAYS_DEFAULT)}")
        else:
            if d["poly_us"] < 0 or d["off_us"] < 0 or d["jump_us"] < 0 or d["end_us"] < 0:
                e.append(f"{tag}: only on_us may be negative")
            if any(abs(d[x]) > 0x7FFF for x in DELAYS_DEFAULT):
                e.append(f"{tag}: a delay is beyond 32767 µs")
        shapes = L.get("shapes")
        if not isinstance(shapes, list):
            e.append(f"{tag}: 'shapes' must be a list"); continue
        for j, sh in enumerate(shapes):
            st = f"{tag} shape {j}"
            if not isinstance(sh, dict):
                e.append(f"{st}: not an object"); continue
            if sh.get("type") == "polyline":
                pts = sh.get("pts")
                if not isinstance(pts, list) or len(pts) < 2:
                    e.append(f"{st}: a polyline needs ≥2 points"); continue
                if sh.get("closed") and len(pts) < 3:
                    e.append(f"{st}: a closed polyline needs ≥3 points")
                bad = [p for p in pts if not (isinstance(p, (list, tuple)) and len(p) == 2 and _num(p[0]) and _num(p[1]))]
                if bad:
                    e.append(f"{st}: {len(bad)} malformed point(s), e.g. {bad[0]!r}"); continue
                out = [p for p in pts if abs(p[0]) > HALF_FIELD or abs(p[1]) > HALF_FIELD]
                if out and L.get("output") is not False:
                    e.append(f"{st}: {len(out)} point(s) outside the ±{HALF_FIELD} mm field, e.g. {out[0]}")
            elif sh.get("type") == "dot":
                if not all(_num(sh.get(x)) for x in ("x", "y", "dwell_us")):
                    e.append(f"{st}: a dot needs x, y, dwell_us")
            else:
                e.append(f"{st}: unknown shape type {sh.get('type')!r} (polyline | dot)")
    return e


def warnings(job):
    """Things raio will do but Edson should see before the go."""
    w = []
    for L in run_order(job):
        tag = f"{L['name']}"
        pw = L.get("pulse_ns")
        if pw not in KNOWN_PULSES:
            w.append(f"{tag}: pulse {pw} ns is not in the known JPT list {sorted(KNOWN_PULSES)}; the source may round it")
        pts = [p for s in L["shapes"] if s.get("type") == "polyline" for p in s["pts"]]
        out = [p for p in pts if abs(p[0]) > HALF_USABLE or abs(p[1]) > HALF_USABLE]
        far = [p for p in pts if abs(p[0]) > HALF_FIELD or abs(p[1]) > HALF_FIELD]
        if far and not L.get("output", True):
            w.append(f"{tag}: reference layer (never marked) has {len(far)} point(s) outside the field")
        elif out:
            w.append(f"{tag}: {len(out)} point(s) beyond the usable ±{HALF_USABLE} mm (inside the field, at the lens edge)")
        if L["mode"] == "fill":
            opn = sum(1 for s in L["shapes"] if s.get("type") == "polyline" and not s.get("closed"))
            if opn:
                w.append(f"{tag}: {opn} open polyline(s) on a fill layer are not filled")
        if not L["shapes"]:
            w.append(f"{tag}: no shapes")
    return w


# ───────────────────────────── order and totals ─────────────────────────────

def run_order(job, include_hidden=True):
    """Layers sorted by `order` (stable on the file order); output=false kept unless include_hidden=False."""
    ls = sorted(enumerate(job["layers"]), key=lambda t: (t[1]["order"], t[0]))
    return [L for _, L in ls if include_hidden or L.get("output", True)]


def loops_of(layer):
    return [[tuple(p) for p in s["pts"]] for s in layer["shapes"] if s.get("type") == "polyline" and s.get("closed")]


def totals(job):
    """Per layer, in run order: passes, shapes, outline length (one pass), area for fills, bbox."""
    rows = []
    for L in run_order(job):
        polys = [s for s in L["shapes"] if s.get("type") == "polyline"]
        outline = sum(geom.length(s["pts"], s.get("closed")) for s in polys)
        row = {"id": L["id"], "name": L["name"], "order": L["order"], "output": L["output"], "mode": L["mode"],
               "passes": L["passes"], "shapes": len(L["shapes"]), "outline_mm": outline,
               "bbox": geom.bbox([s["pts"] for s in polys])}
        if L["mode"] == "fill":
            area = geom.evenodd_area(loops_of(L))
            row["area_mm2"] = area
            iv = L["fill"]["interval_mm"]
            row["hatch_mm_est"] = area / iv * (2 if L["fill"].get("cross") else 1)
        rows.append(row)
    return rows


# ───────────────────────────── load / save ─────────────────────────────

def load(path, check=True):
    job = json.loads(Path(path).read_text())
    if check:
        errs = validate(job)
        if errs:
            raise JobError(errs)
    return job


def dumps(job):
    """JSON with one shape per line (readable, diff-able, not one number per line)."""
    def enc(o):
        return json.dumps(o, ensure_ascii=False, separators=(",", ":"))
    head = {k: v for k, v in job.items() if k != "layers"}
    out = ["{"]
    keys = list(job.keys())
    for n, k in enumerate(keys):
        comma = "," if n < len(keys) - 1 else ""
        if k != "layers":
            out.append(f'  {json.dumps(k)}: {json.dumps(job[k], ensure_ascii=False)}{comma}')
            continue
        out.append('  "layers": [')
        for li, L in enumerate(job["layers"]):
            out.append("    {")
            lk = list(L.keys())
            for m, kk in enumerate(lk):
                c2 = "," if m < len(lk) - 1 else ""
                if kk == "shapes":
                    out.append('      "shapes": [')
                    for si, s in enumerate(L["shapes"]):
                        out.append("        " + enc(s) + ("," if si < len(L["shapes"]) - 1 else ""))
                    out.append("      ]" + c2)
                else:
                    out.append(f'      {json.dumps(kk)}: {json.dumps(L[kk], ensure_ascii=False)}{c2}')
            out.append("    }" + ("," if li < len(job["layers"]) - 1 else ""))
        out.append("  ]" + comma)
    out.append("}")
    del head
    return "\n".join(out) + "\n"


def save(job, path, check=True):
    if check:
        errs = validate(job)
        if errs:
            raise JobError(errs)
    Path(path).write_text(dumps(job))
    return path
