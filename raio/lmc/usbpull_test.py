#!/usr/bin/env python3
"""raio · lmc/usbpull_test.py — Phase 0.9: what does the board do when the host disappears mid-job? FIRES THE LASER.

    usbpull_test.py --power 30 --loops 150 --go
Frame 5 s, pause 3 s, then a 30 mm square × loops at 200 mm/s (≈ 0.6 s per loop). Edson pulls the USB cable
at the Mac end about a minute in, with the E-stop in reach. The script records when the board vanished,
waits for it to re-enumerate, reconnects, reads its state and forces safe idle.
"""
import argparse, json, sys, time
from datetime import datetime
from pathlib import Path
import usb.core
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lmc import LMC, Busy, L, OP, LASER_BIT, RED_BIT, BUSY, READY, VID, PID

ap = argparse.ArgumentParser()
ap.add_argument("--power", type=float, default=30); ap.add_argument("--loops", type=int, default=150)
ap.add_argument("--go", action="store_true")
a = ap.parse_args()
if a.power > 30: sys.exit("phase 0 caps power at 30 %")

m = LMC()
log = {"when": datetime.now().isoformat(timespec="seconds"), "loops": a.loops, "power": a.power}
pts = [(-15, -15), (15, -15), (15, 15), (-15, 15)]
def square():
    q = [m.mm(*p) for p in pts] + [m.mm(*pts[0])]
    c = [(L["JumpTo"], *q[0], 0, m.dist((0x8000, 0x8000), q[0])), (L["FiberOpenMO"], 1), (L["DelayTime"], 800)]
    prev = q[0]
    for p in q[1:]:
        c.append((L["MarkTo"], *p, 0, m.dist(prev, p))); prev = p
    return c + [(L["DelayTime"], 30), (L["FiberOpenMO"], 0)]
try:
    m.init()
    if not a.go: sys.exit("dry: initialised only")
    print("red frame 5 s ...", flush=True); m.red_polyline(pts + [pts[0]], seconds=5)
    print("marking in 3 s — pull the cable about a minute in", flush=True); time.sleep(3)
    cmds = [(L["DelayTime"], 800), (L["PulseWidth"], 0, 200), (L["QSwitchPeriod"], round(20000 / 30)),
            (L["MarkCurrent"], round(a.power * 0xFFF / 100)), (L["JumpSpeed"], m.spd(4000)), (L["MarkSpeed"], m.spd(200)),
            (L["LaserOnDelay"], 300, 0x8000), (L["LaserOffDelay"], 100), (L["PolygonDelay"], 10)]
    m.bit(RED_BIT, False); m.bit(LASER_BIT, True); m.write_port(); m.cmd(OP["Fiber_SetMo"], 1)
    cmds = [(L["WritePort"], m.ports)] + cmds + sum([square() for _ in range(a.loops)], [])
    t0 = time.time()
    try:
        m.run_list(cmds, timeout=600)
        print(f"job finished normally after {time.time()-t0:.1f} s (cable not pulled?)")
        m.safe_idle(); log["result"] = "finished"
    except usb.core.USBError as e:
        t_lost = time.time() - t0
        print(f"*** board lost at {t_lost:.1f} s into the job: {e}", flush=True)
        log["lost_at_s"] = round(t_lost, 2)
        try: m.close()
        except Exception: pass
        m = None
        while m is None:                       # libusb's device list can be stale right after the pull: just keep trying to open
            time.sleep(0.5)
            try:
                m = LMC()
            except Exception:
                m = None
        t_back = time.time() - t0
        print(f"board back and open at {t_back:.1f} s", flush=True)
        st = m.status(); fib = m.cmd(OP["Fiber_GetStMO_AP"]); pos = m.cmd(OP["GetPositionXY"])
        print(f"state after reconnect: status=0x{st:04x} busy={bool(st & BUSY)} fiber={['%04x'%w for w in fib]} galvo={['%04x'%w for w in pos]}")
        log.update(back_at_s=round(t_back, 2), status=st, fiber=list(fib), galvo=list(pos))
        m.abort(); print("abort + safe idle sent after reconnect")
finally:
    try: m.safe_idle()
    finally: m.close()
    out = Path(__file__).resolve().parent.parent / "logs" / f"usbpull-{datetime.now():%Y-%m-%d_%H-%M-%S}.json"
    out.write_text(json.dumps(log, indent=1, default=str)); print("logged:", out)
