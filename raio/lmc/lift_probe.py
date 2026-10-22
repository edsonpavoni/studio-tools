#!/usr/bin/env python3
"""raio · lmc/lift_probe.py — which board command freezes the lift? One immediate command per run, no lists, no emission.

    lift_probe.py read            # read-only queries (control)
    lift_probe.py port 0000       # WritePort(bits) — hex
    lift_probe.py op 3a           # a single opcode, no args (3a = vendor DisableZ, 39 = vendor EnableZ)
After each run Edson taps Up/Down on the panel and reports. Power cycle resets everything.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lmc import LMC, Busy, OP

what, arg = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
try:
    m = LMC()
except Busy as e:
    sys.exit(str(e))
try:
    if what == "read":
        print("version", ["%04x" % w for w in m.cmd(OP["GetVersion"], 0)], "port", ["%04x" % w for w in m.cmd(OP["ReadPort"])],
              "fiber", ["%04x" % w for w in m.cmd(OP["Fiber_GetStMO_AP"])])
    elif what == "port":
        bits = int(arg, 16)
        assert not (bits & 1), "bit 0 is the laser-enable bit: never set it here"
        m.ports = bits; m.write_port(); print(f"WritePort(0x{bits:04x}) sent")
    elif what == "op":
        op = int(arg, 16)
        assert op in (0x39, 0x3A), "only 0x39 / 0x3a here"
        print(f"op 0x{op:02x} ->", ["%04x" % w for w in m.cmd(op)])
    else:
        sys.exit("read | port <hex> | op <hex>")
finally:
    m.close()      # no safe_idle here on purpose: it would write the port again
