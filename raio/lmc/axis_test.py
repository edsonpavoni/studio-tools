#!/usr/bin/env python3
"""raio · lmc/axis_test.py — Phase 0.6: does the Z column (or the Rotary port) follow the board's axis channel?

Moves one extended axis by a few pulses and back, with the MO closed and the laser bit low.
No list, no emission. Watch the column with your eyes and the Rotary port with an LED/meter.

    ~/.venvs/raio/bin/python studio/raio/lmc/axis_test.py --axis 0 --pulses 50 --go
    ~/.venvs/raio/bin/python studio/raio/lmc/axis_test.py --axis 1 --pulses 50 --go

Without --go it only reads the axis positions. 50 pulses = 2 mm if the column (200 pulses per
8 mm turn) were on this channel, at 200 pulses/s = 0.25 s. The R5 rotary must be UNPLUGGED.
Keep a hand near the E-stop: a column with no end-stops must never be driven far.
"""
import argparse, json, sys, time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lmc import LMC, Busy, AXIS

ap = argparse.ArgumentParser()
ap.add_argument("--axis", type=int, choices=[0, 1], default=0)
ap.add_argument("--pulses", type=int, default=50, help="relative move, then the same back")
ap.add_argument("--vmax", type=int, default=200, help="pulses per second")
ap.add_argument("--go", action="store_true")
a = ap.parse_args()
if abs(a.pulses) > 200:
    sys.exit("refusing more than 200 pulses (one turn, 8 mm on the column) in a test")

try:
    m = LMC()
except Busy as e:
    sys.exit(str(e))
log = {"when": datetime.now().isoformat(timespec="seconds"), "axis": a.axis, "pulses": a.pulses, "steps": []}
try:
    p0, p1 = m.axis_pos(0), m.axis_pos(1)
    print(f"axis positions before: axis0={p0}  axis1={p1}  status=0x{m.status():04x}")
    log["before"] = [p0, p1]
    if not a.go:
        print("read-only (add --go to move)"); sys.exit(0)
    start = m.axis_pos(a.axis)
    for target in (start + a.pulses, start):
        print(f"moving axis {a.axis} to {target} pulses ...", end="", flush=True)
        t0 = time.time()
        m.axis_move_to(target, axis=a.axis, vmax=a.vmax)
        dt = time.time() - t0
        now = m.axis_pos(a.axis)
        print(f" done in {dt:.2f}s, board reports {now}")
        log["steps"].append({"target": target, "reported": now, "seconds": round(dt, 3)})
        time.sleep(0.5)
    print("did the COLUMN move?  did the ROTARY port pulse?  write the answer in LOG.md")
finally:
    try: m.safe_idle()
    finally: m.close()
    out = Path(__file__).resolve().parent.parent / "logs" / f"axis-{datetime.now():%Y-%m-%d_%H-%M-%S}.json"
    out.write_text(json.dumps(log, indent=1)); print("logged:", out)
