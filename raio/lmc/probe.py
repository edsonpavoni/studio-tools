#!/usr/bin/env python3
"""raio · lmc/probe.py — read-only identification of the B6's BJJCZ LMC V4 board.

Step 1 of the machine test plan (research/02-protocol.md §9.2). It sends ONLY query
commands and logs the raw reply words. It never enables the laser, never writes a
port, never uploads a list, never moves an axis. Opcodes from research/02-protocol.md
§3.1 (meerk40t balormk, MIT; confirmed against EZCAD's LMCMIO.dll exports).

    ~/.venvs/raio/bin/python studio/raio/lmc/probe.py            # one pass
    ~/.venvs/raio/bin/python studio/raio/lmc/probe.py --poll 20  # + ReadPort at 10 Hz for 20 s (pedal test)
    ~/.venvs/raio/bin/python studio/raio/lmc/probe.py --watch 10 # + status at 2 Hz for 10 s

Written 2026-10-21. LightBurn must be closed (one process owns the interface).
"""
import argparse, json, struct, sys, time
from datetime import datetime
from pathlib import Path

import usb.core, usb.util

VID, PID = 0x9588, 0x9899
EP_OUT, EP_IN = 0x02, 0x88          # commands + lists out; 8-byte status in
TIMEOUT_MS = 300

# name: (opcode, args, what it is). READ-ONLY queries only.
QUERIES = {
    "GetSerialNo":      (0x0009, (),       "4 words; LightBurn's 'board signature' is probably this or GetVersion"),
    "GetVersion":       (0x0007, (0,),     "poll form; w3 = status flags (0x20 READY, 0x04 BUSY, 0x40 AXIS)"),
    "GetListStatus":    (0x000A, (),       "w3 0x04 running, 0x08 paused"),
    "ReadPort":         (0x0025, (),       "input port word; pedal bit to be found with --poll"),
    "GetPositionXY":    (0x000C, (),       "galvo position (0x8000,0x8000 = centre)"),
    "GetAxisPos0":      (0x002A, (0,),     "extended axis 0 position in pulses (sign-magnitude w1|w2<<16)"),
    "GetAxisPos1":      (0x002A, (1,),     "extended axis 1 position"),
    "Fiber_GetStMO_AP": (0x0034, (),       "fiber source status (MO / AP)"),
    "GetMarkCount":     (0x002D, (),       "mark counter"),
}
READY, BUSY, AXIS = 0x20, 0x04, 0x40


def flags(w3):
    f = []
    if w3 & READY: f.append("READY")
    if w3 & BUSY:  f.append("BUSY")
    if w3 & AXIS:  f.append("AXIS")
    return "|".join(f) or "-"


class Probe:
    def __init__(self):
        d = usb.core.find(idVendor=VID, idProduct=PID)
        if d is None:
            sys.exit("no board on USB (want 9588:9899 'USBLMCV4'). Is the B6 on and plugged in?")
        self.desc = dict(product=usb.util.get_string(d, d.iProduct), vendor=usb.util.get_string(d, d.iManufacturer),
                         serial=usb.util.get_string(d, d.iSerialNumber), bcdDevice=hex(d.bcdDevice))
        try:
            d.set_configuration()
            usb.util.claim_interface(d, 0)
        except usb.core.USBError as e:
            if "busy" in str(e).lower() or getattr(e, "errno", None) == 16:
                sys.exit("board is busy: another program holds it (LightBurn?). Close it and retry.")
            raise
        self.d = d

    def query(self, op, *args):
        a = list(args) + [0] * (5 - len(args))
        pkt = struct.pack("<6H", op, *a)
        self.d.write(EP_OUT, pkt, TIMEOUT_MS)
        raw = bytes(self.d.read(EP_IN, 8, TIMEOUT_MS))
        return raw, struct.unpack("<4H", raw)

    def close(self):
        usb.util.release_interface(self.d, 0)
        usb.util.dispose_resources(self.d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--poll", type=float, default=0, help="seconds to poll ReadPort at 10 Hz (press the pedal)")
    ap.add_argument("--watch", type=float, default=0, help="seconds to poll GetVersion status at 2 Hz")
    a = ap.parse_args()

    p = Probe()
    out = {"when": datetime.now().isoformat(timespec="seconds"), "usb": p.desc, "replies": {}}
    print("board:", p.desc)
    try:
        for name, (op, args, what) in QUERIES.items():
            try:
                raw, w = p.query(op, *args)
                line = f"{name:18s} 0x{op:04X}{'' if not args else args} -> {raw.hex()}  w={['%04x' % x for x in w]}"
                if name == "GetVersion":
                    line += f"  status={flags(w[3])}"
                if name.startswith("GetAxisPos"):
                    pos = w[1] | (w[2] << 16)
                    line += f"  pos={-(pos & 0x7FFFFFFF) if pos & 0x80000000 else pos} pulses"
                print(line)
                out["replies"][name] = {"op": op, "args": list(args), "raw": raw.hex(), "words": list(w), "what": what}
            except usb.core.USBError as e:
                print(f"{name:18s} 0x{op:04X} -> USB error: {e}")
                out["replies"][name] = {"op": op, "args": list(args), "error": str(e)}
        sig = out["replies"].get("GetSerialNo", {}).get("raw")
        ver = out["replies"].get("GetVersion", {}).get("raw")
        print(f"\ncompare with the forum's B6 signature 0000238409002002: serial={sig} version={ver}")

        if a.poll:
            print(f"\npolling ReadPort for {a.poll:.0f} s — press and release the foot pedal now")
            last = None; t0 = time.time(); changes = []
            while time.time() - t0 < a.poll:
                raw, w = p.query(0x0025)
                if w != last:
                    t = round(time.time() - t0, 2)
                    print(f"  t={t:6.2f}s  {raw.hex()}  w0=0x{w[0]:04x} w1=0x{w[1]:04x}")
                    changes.append({"t": t, "words": list(w)}); last = w
                time.sleep(0.1)
            out["port_poll"] = changes
        if a.watch:
            print(f"\nstatus for {a.watch:.0f} s")
            t0 = time.time()
            while time.time() - t0 < a.watch:
                raw, w = p.query(0x0007, 0)
                print(f"  t={time.time()-t0:5.1f}s  {raw.hex()}  {flags(w[3])}")
                time.sleep(0.5)
    finally:
        p.close()
    log = Path(__file__).resolve().parent.parent / "logs" / f"probe-{datetime.now():%Y-%m-%d_%H-%M-%S}.json"
    log.write_text(json.dumps(out, indent=1))
    print("\nlogged:", log)


if __name__ == "__main__":
    main()
