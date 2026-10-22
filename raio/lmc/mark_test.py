#!/usr/bin/env python3
"""raio · lmc/mark_test.py — Phase 0.7: the first marks. THIS FIRES THE LASER.

    mark_test.py line  --len 1 --power 10 --speed 500 --freq 30 --pulse 200 --go
    mark_test.py abort --seconds 20 --power 10 --go        # long pattern, abort at 20 s, measure latency, verify MO closed
    mark_test.py squares --power 30 --go                    # phase 0.8: two 5×5 mm squares, 4 ns vs 200 ns (vendor layout)

Every run: red-light frame of the same shape for 5 s first (frame before fire), then a 3 s pause, then the mark.
Pre-flight (the script asks, Edson answers at the machine): goggles on · scrap steel focused · air assist on ·
extraction on · E-stop in reach · nothing flammable under the bed · LightBurn closed.
Pulse width uses the VENDOR layout [0x8026, 0, ns] (EZCAD's DLL). If 0.8 shows no difference, try --mk-layout.
"""
import argparse, json, sys, threading, time
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lmc import LMC, Busy, L, OP, LASER_BIT, RED_BIT, BUSY, GO_FLAG, STOP_FLAG

ap = argparse.ArgumentParser()
ap.add_argument("what", choices=["line", "abort", "squares", "pwrow", "square"])
ap.add_argument("--values", default="1,2,4,8,12,16,50,100,200,350,500")
ap.add_argument("--y", type=float, default=0, help="row offset in mm (+ = toward the column)")
ap.add_argument("--x", type=float, default=0, help="row centre x in mm (+ = machine right)")
ap.add_argument("--scale", type=float, default=1.0, help="scale the whole row (pitch, squares, markers)")
ap.add_argument("--markers", action="store_true", help="circle before the first square, triangle after the last (index 12)")
ap.add_argument("--len", type=float, default=1.0)
ap.add_argument("--power", type=float, default=10)
ap.add_argument("--speed", type=float, default=500)
ap.add_argument("--freq", type=float, default=30, help="kHz")
ap.add_argument("--pulse", type=int, default=200, help="ns")
ap.add_argument("--seconds", type=float, default=20)
ap.add_argument("--passes", type=int, default=5)
ap.add_argument("--mk-layout", action="store_true", help="meerk40t pulse-width layout [0x8026, ns, 0]")
ap.add_argument("--go", action="store_true", help="fire. Only after Edson's go for THIS job")
ap.add_argument("--swap", action="store_true"); ap.add_argument("--flipx", action="store_true"); ap.add_argument("--flipy", action="store_true")
ap.add_argument("--preview", type=float, default=60, help="seconds of red preview when there is no --go")
a = ap.parse_args()

def settings(power, freq, pulse, speed):
    pw = (L["PulseWidth"], pulse, 0) if a.mk_layout else (L["PulseWidth"], 0, pulse)
    return [pw, (L["QSwitchPeriod"], round(20000 / freq)), (L["MarkCurrent"], round(power * 0xFFF / 100)),
            (L["JumpSpeed"], m.spd(4000)), (L["MarkSpeed"], m.spd(speed)),
            (L["LaserOnDelay"], 300, 0x8000), (L["LaserOffDelay"], 100), (L["PolygonDelay"], 10)]   # LightBurn's B6 timings

def path_cmds(points, closed=False):
    """jump to the first point, mark through the rest (MO opened inside the list, 8 ms wait, as EZCAD)."""
    pts = [m.mm(*p) for p in points] + ([m.mm(*points[0])] if closed else [])
    c = [(L["JumpTo"], *pts[0], 0, m.dist((0x8000, 0x8000), pts[0])), (L["FiberOpenMO"], 1), (L["DelayTime"], 800)]
    prev = pts[0]
    for q in pts[1:]:
        c.append((L["MarkTo"], *q, 0, m.dist(prev, q))); prev = q
    c += [(L["DelayTime"], 30), (L["FiberOpenMO"], 0), (L["JumpTo"], 0x8000, 0x8000, 0, m.dist(prev, (0x8000, 0x8000)))]
    return c

FRAMED = False
def preflight(shape_pts, closed):
    if FRAMED:            # the live red preview already showed this job; fire now
        return
    print("PRE-FLIGHT: goggles · scrap steel focused · air · extraction · E-stop · nothing flammable below · LightBurn closed")
    print("red frame 5 s ...", flush=True); m.red_polyline(shape_pts + ([shape_pts[0]] if closed else []), seconds=5)
    print("marking in 3 s", flush=True); time.sleep(3)

def fire(cmds, timeout):
    """meerk40t's program_mode: enable bit on (immediate) → MO open (immediate 0x33) → list starts with
    the open-MO delay and an in-list WritePort of the same bits. EZCAD's in-list 0x8021 stays too."""
    m.bit(RED_BIT, False); m.bit(LASER_BIT, True); m.write_port()
    m.cmd(OP["Fiber_SetMo"], 1)
    cmds = [(L["DelayTime"], 800), (L["WritePort"], m.ports)] + cmds
    try:
        m.run_list(cmds, timeout=timeout)
    finally:
        m.safe_idle()

def verify_off():
    st, fib, port = m.status(), m.cmd(OP["Fiber_GetStMO_AP"]), m.cmd(OP["ReadPort"])
    print(f"after: status=0x{st:04x} busy={bool(st & BUSY)} fiber={['%04x'%w for w in fib]} port={['%04x'%w for w in port]} ports_out=0x{m.ports:04x}")
    return {"status": st, "fiber": list(fib), "port": list(port)}

try:
    m = LMC()
except Busy as e:
    sys.exit(str(e))
if a.swap: m.swap = not m.swap          # the flags toggle the driver's default frame (LightBurn's), they do not replace it
if a.flipx: m.sx = -m.sx
if a.flipy: m.sy = -m.sy
log = {"when": datetime.now().isoformat(timespec="seconds"), "what": a.what, "args": vars(a)}
try:
    ident = m.init(); log["ident"] = {k: list(v) for k, v in ident.items()}
    if not a.go:
        # RULE (Edson, 2026-10-21 18:05): without a go, only the red preview, so the material can be placed.
        h = a.len / 2
        shapes = {"line": [(-a.len/2, 0), (a.len/2, 0)], "abort": [(-15, -15), (15, -15), (15, 15), (-15, 15), (-15, -15)],
                  "square": [(a.x - h, a.y - h), (a.x + h, a.y - h), (a.x + h, a.y + h), (a.x - h, a.y + h), (a.x - h, a.y - h)],
                  "squares": [(-12.5, -2.5), (-7.5, -2.5), (-7.5, 2.5), (-12.5, 2.5), (-12.5, -2.5), (7.5, -2.5), (12.5, -2.5), (12.5, 2.5), (7.5, 2.5), (7.5, -2.5)]}
        if a.what == "pwrow":
            vals = [int(v) for v in a.values.split(",")]; pitch, w, y = 8.0 * a.scale, 5.0 * a.scale, a.y; x0 = a.x - (len(vals) - 1) * pitch / 2
            shapes["pwrow"] = sum([[(x0 + i*pitch - w/2, y - w/2), (x0 + i*pitch + w/2, y - w/2), (x0 + i*pitch + w/2, y + w/2), (x0 + i*pitch - w/2, y + w/2), (x0 + i*pitch - w/2, y - w/2)] for i in range(len(vals))], [])
            if a.markers:
                import math
                xe = x0 + len(vals) * pitch
                r = 2.5 * a.scale
                shapes["pwrow"] += [(x0 - pitch + r * math.cos(t), y + r * math.sin(t)) for t in [k * math.tau / 24 for k in range(25)]]
                shapes["pwrow"] += [(xe - r, y - r), (xe + r, y - r), (xe, y + r), (xe - r, y - r)]
        # RULE (Edson, 18:40): the red stays on until the go. The session touches GO_FLAG on his word; STOP_FLAG cancels.
        for f in (GO_FLAG, STOP_FLAG):
            if f.exists(): f.unlink()
        print("RED ON: place the material. Waiting for Edson's go (go.flag) or stop (stop.flag)...", flush=True)
        r = m.red_polyline(shapes[a.what], until=lambda: "go" if GO_FLAG.exists() else ("stop" if STOP_FLAG.exists() else None))
        for f in (GO_FLAG, STOP_FLAG):
            if f.exists(): f.unlink()
        if r != "go":
            print("preview stopped, nothing fired"); sys.exit(0)
        print("GO received: re-init, then firing", flush=True); m.init(); a.go = True; FRAMED = True
    if a.what == "line":
        pts = [(-a.len / 2, 0), (a.len / 2, 0)]
        preflight(pts, False)
        t0 = time.time(); fire(settings(a.power, a.freq, a.pulse, a.speed) + path_cmds(pts), timeout=30)
        log["mark_seconds"] = round(time.time() - t0, 3); print(f"marked in {log['mark_seconds']} s")
    elif a.what == "abort":
        # a 30 mm square marked over and over for ~a minute; abort() after --seconds; measure how long until idle
        pts = [(-15, -15), (15, -15), (15, 15), (-15, 15)]
        preflight(pts, True)
        cmds = [(L["DelayTime"], 800)] + settings(a.power, a.freq, a.pulse, 200) + sum([path_cmds(pts, True) for _ in range(40)], [])
        m.bit(RED_BIT, False); m.bit(LASER_BIT, True); m.write_port(); m.cmd(OP["Fiber_SetMo"], 1)
        cmds = [(L["WritePort"], m.ports)] + cmds
        t_abort = {}
        def stopper():
            time.sleep(a.seconds); t_abort["sent"] = time.time(); m.abort(); t_abort["idle"] = time.time()
        th = threading.Thread(target=stopper, daemon=True); th.start()
        try:
            m.run_list(cmds, timeout=600)
        except Exception as e:
            print("run_list ended:", e)
        th.join()
        log["abort_latency_s"] = round(t_abort["idle"] - t_abort["sent"], 3)
        print(f"abort: sent at {a.seconds} s, board idle {log['abort_latency_s']} s later")
        m.safe_idle()
    elif a.what == "squares":
        sq = lambda cx: [(cx - 2.5, -2.5), (cx + 2.5, -2.5), (cx + 2.5, 2.5), (cx - 2.5, 2.5)]
        preflight(sq(-10) + sq(10), False)
        cmds = []
        for cx, ns in ((-10, 4), (10, 200)):
            cmds += settings(a.power, a.freq, ns, a.speed) + sum([path_cmds(sq(cx), True) for _ in range(a.passes)], [])
        fire(cmds, timeout=60); print(f"left square 4 ns, right square 200 ns, {a.passes} passes each: do they differ?")
    elif a.what == "square":
        h = a.len / 2
        pts = [(a.x - h, a.y - h), (a.x + h, a.y - h), (a.x + h, a.y + h), (a.x - h, a.y + h)]
        preflight(pts, True)
        t0 = time.time(); fire(settings(a.power, a.freq, a.pulse, a.speed) + sum([path_cmds(pts, True) for _ in range(a.passes)], []), timeout=300)
        log["mark_seconds"] = round(time.time() - t0, 3); print(f"square {a.len} mm, {a.passes} passes, marked in {log['mark_seconds']} s. Measure both sides with the caliper.")
    elif a.what == "pwrow":
        vals = [int(v) for v in a.values.split(",")]
        pitch, w, y, r = 8.0 * a.scale, 5.0 * a.scale, a.y, 2.5 * a.scale
        x0 = a.x - (len(vals) - 1) * pitch / 2
        sq = lambda cx: [(cx - w/2, y - w/2), (cx + w/2, y - w/2), (cx + w/2, y + w/2), (cx - w/2, y + w/2)]
        import math
        circle = [(x0 - pitch + r * math.cos(t), y + r * math.sin(t)) for t in [k * math.tau / 24 for k in range(24)]]
        xe = x0 + (len(vals) - 1) * pitch + pitch
        tri = [(xe - r, y - r), (xe + r, y - r), (xe, y + r)]
        shapes = sum([sq(x0 + i * pitch) for i in range(len(vals))], []) + (circle + tri if a.markers else [])
        preflight(shapes, False)
        cmds = []
        if a.markers:
            cmds += settings(a.power, a.freq, 12, a.speed) + sum([path_cmds(circle, True) for _ in range(a.passes)], [])
        for i, v in enumerate(vals):
            cmds += settings(a.power, a.freq, v, a.speed) + sum([path_cmds(sq(x0 + i * pitch), True) for _ in range(a.passes)], [])
        if a.markers:
            cmds += settings(a.power, a.freq, 12, a.speed) + sum([path_cmds(tri, True) for _ in range(a.passes)], [])
        fire(cmds, timeout=600)
        print("left → right, pulse-width values:", vals, f"({a.passes} passes each)")
    log["after"] = verify_off()
finally:
    try: m.safe_idle()
    finally: m.close()
    out = Path(__file__).resolve().parent.parent / "logs" / f"mark-{datetime.now():%Y-%m-%d_%H-%M-%S}.json"
    out.write_text(json.dumps(log, indent=1, default=str)); print("logged:", out)
