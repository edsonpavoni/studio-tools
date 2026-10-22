#!/usr/bin/env python3
"""raio · lmc/pause_test.py — can raio pause like LightBurn, safely? THIS FIRES THE LASER.

    pause_test.py --plan                          # no USB: the job, its length, when the pause falls
    pause_test.py                                 # red preview of the job until go.flag (Edson's go) or stop.flag
    pause_test.py --go                            # fire: safe pause at --at s, hold --hold s, resume
    pause_test.py --mode plain --go               # the board's pause alone (what LightBurn sends): does the beam stop by itself?

The question (Edson, 2026-10-22 00:05): LightBurn has a pause button; is there a board command for it? Yes:
StopList 0x20 (pause) / RestartList 0x13 (resume); the state is in the status word (measured 01:22: 0x08 paused, 0x04 busy)
(research/02-protocol.md). The risk (research/04-safety.md §1): on a BJJCZ board a LightBurn pause once left the
beam on at 95 % and burned a line. So the default mode does not trust the board to turn the beam off:
    safe  · pause: StopList, then laser-enable bit low + MO closed; read back list status + fiber state
            resume: bit high + MO open, then RestartList
    plain · pause: StopList only; resume: RestartList only (run it only after safe, to learn what the board does alone)

The job: 20 horizontal lines, 30 mm long, 0.5 mm apart, marked slowly (20 mm/s, ~1.5 s per line, ~35 s in all),
10 % power, so the pause lands mid-line. What to look at, under the camera or the loupe after the run:
    · during the hold: a growing glowing dot = the beam stayed on (E-stop if it lasts)
    · the paused line: continuous through the pause point = the board resumed in place;
      a gap = it skipped; a dark blob = it dwelt with the beam on; a doubled stretch = it replayed
    · the lines after: all there = the list continued to the end
Target: steel or anodised aluminium offcut, never card (04-safety.md §3.1). Pre-flight as always. Run safe first, plain after.
If no line appears at all, the source did not emit (the 21:53 case): that says nothing about pause; power-cycle and rerun.
If RestartList does not take within 1 s (list not running), the test aborts and switches emission off: a result, logged as did_not_resume.
The go comes from Edson's word in chat (the session touches go.flag); the board page's fire button cannot give it (it fires only
a red that raio mark put on). The page's cancel works (stop.flag). While this holds the USB, frame on the page reports "busy".
The log (logs/pause-*.json) has the list status polled every 0.2 s through the hold, the fiber state and timings.
"""
import argparse, json, sys, threading, time
from datetime import datetime
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

ap = argparse.ArgumentParser()
ap.add_argument("--mode", choices=["safe", "plain"], default="safe")
ap.add_argument("--at", type=float, default=8.0, help="seconds after the start to pause (default lands mid line 6)")
ap.add_argument("--hold", type=float, default=None, help="seconds paused (safe 5, plain 2: a beam left on must not dwell past the 3 s E-stop rule)")
ap.add_argument("--power", type=float, default=10)
ap.add_argument("--speed", type=float, default=20, help="mm/s: slow, so the pause point is easy to find")
ap.add_argument("--freq", type=float, default=30, help="kHz")
ap.add_argument("--pulse", type=int, default=200, help="ns")
ap.add_argument("--lines", type=int, default=20)
ap.add_argument("--len", type=float, default=30.0)
ap.add_argument("--pitch", type=float, default=0.5)
ap.add_argument("--x", type=float, default=0); ap.add_argument("--y", type=float, default=0)
ap.add_argument("--go", action="store_true", help="fire. Only after Edson's go for THIS test")
ap.add_argument("--plan", action="store_true", help="no USB: print the job and stop")
a = ap.parse_args()
if a.hold is None:
    a.hold = 5.0 if a.mode == "safe" else 2.0

OP_STOPLIST, OP_RESTARTLIST = 0x20, 0x13            # 02-protocol.md §3.1 (VERIFIED opcodes), not in lmc.OP yet
x0, x1 = a.x - a.len / 2, a.x + a.len / 2
ys = [a.y + (i - (a.lines - 1) / 2) * a.pitch for i in range(a.lines)]
lines = [((x0, y), (x1, y)) for y in ys]
frame = [(x0, ys[0]), (x1, ys[0]), (x1, ys[-1]), (x0, ys[-1]), (x0, ys[0])]
per_line = a.len / a.speed

if a.plan:
    k = int(a.at // (per_line + 0.02))
    print(f"{a.lines} lines × {a.len} mm at {a.speed} mm/s ≈ {per_line:.2f} s each, ≈ {a.lines * per_line:.0f} s in all "
          f"({a.power} %, {a.freq} kHz, {a.pulse} ns); field box {x0:.1f},{ys[0]:.2f} → {x1:.1f},{ys[-1]:.2f} mm")
    print(f"pause at {a.at} s ≈ line {k + 1}, {min(100, 100 * (a.at - k * per_line) / per_line):.0f} % along; hold {a.hold} s; mode {a.mode}")
    sys.exit(0)

from lmc import LMC, Busy, L, OP, LASER_BIT, RED_BIT, BUSY, GO_FLAG, STOP_FLAG, Stopped  # noqa: E402


def settings():
    return [(L["PulseWidth"], 0, a.pulse), (L["QSwitchPeriod"], round(20000 / a.freq)), (L["MarkCurrent"], round(a.power * 0xFFF / 100)),
            (L["JumpSpeed"], m.spd(4000)), (L["MarkSpeed"], m.spd(a.speed)),
            (L["LaserOnDelay"], 300, 0x8000), (L["LaserOffDelay"], 100), (L["PolygonDelay"], 10)]   # as mark_test.py (LightBurn's B6 timings)


def line_cmds(p, q, pos):
    s, e = m.mm(*p), m.mm(*q)
    return [(L["JumpTo"], *s, 0, m.dist(pos, s)), (L["FiberOpenMO"], 1), (L["DelayTime"], 800),
            (L["MarkTo"], *e, 0, m.dist(s, e)), (L["DelayTime"], 30), (L["FiberOpenMO"], 0)], e


def snap(tag):
    """List status, fiber state, ports: the facts the log keeps at every step."""
    t = time.time()
    ls, fib, port, st = m.cmd(OP["GetListStatus"]), m.cmd(OP["Fiber_GetStMO_AP"]), m.cmd(OP["ReadPort"]), m.status()
    # measured 2026-10-22 01:22: the status word says it. paused 0x228 (0x08 on, BUSY 0x04 off) · running again 0x224 · idle 0x220.
    # GetListStatus word 2 stays 9 in every state: not a pause flag.
    return {"tag": tag, "t": round(t - T0, 3), "list": list(ls), "paused": bool(st & 0x08), "running": bool(st & BUSY),
            "fiber": list(fib), "port": list(port), "status": st, "busy": bool(st & BUSY), "ports_out": m.ports}


def pauser():
    """Never touches the bit or the source once `ended` is set (run_list returned, raised or was cancelled:
    lmc.wait() deletes stop.flag before it aborts, so the flag cannot be the signal)."""
    try:
        while time.time() - T0 < a.at:
            if ended.is_set():
                ev["pause_skipped"] = "the job ended before the pause"; return
            time.sleep(0.05)
        if ended.is_set():
            return
        print("PAUSE now: a growing glowing dot = the beam is on → E-STOP", flush=True)
        ev["pause_sent"] = round(time.time() - T0, 3)
        pausing.set()                            # the board drops BUSY while paused (01:21): run_list will return; that is not the end
        m.cmd(OP_STOPLIST)
        if a.mode == "safe":                     # never trust the pause to stop emission (04-safety.md rule 18.2)
            m.bit(LASER_BIT, False); m.write_port(); m.cmd(OP["Fiber_SetMo"], 0)
        ev["pause_done"] = round(time.time() - T0, 3)
        t_end = time.time() + a.hold
        while time.time() < t_end:
            if ended.is_set():
                return                           # cancelled during the hold: stay disarmed
            polls.append(snap("hold"))
            time.sleep(0.2)
        if ended.is_set():
            return
        if a.mode == "safe":
            m.bit(LASER_BIT, True); m.write_port(); m.cmd(OP["Fiber_SetMo"], 1); time.sleep(0.01)
        ev["resume_sent"] = round(time.time() - T0, 3)
        m.cmd(OP_RESTARTLIST)
        # did it take? a list still paused with the laser re-armed is the burned-line state: abort at once
        t_chk = time.time() + 1.0
        while time.time() < t_chk:
            p = snap("resume-check"); polls.append(p)
            if p["running"] and not p["paused"]:
                ev["resumed"] = True; resumed.set(); return
            time.sleep(0.1)
        ev["resumed"] = False; ev["did_not_resume"] = round(time.time() - T0, 3)
        print("did NOT resume within 1 s: aborting, emission off", flush=True)
        m.abort(); m.safe_idle()
    except Exception as e:
        ev["pauser_error"] = repr(e)
        try: m.safe_idle()
        except Exception: pass


try:
    m = LMC()
except Busy as e:
    sys.exit(str(e))
log = {"when": datetime.now().isoformat(timespec="seconds"), "what": "pause_test", "args": vars(a)}
ev, polls = {}, []
try:
    log["ident"] = {k: list(v) for k, v in m.init().items()}
    if not a.go:
        # RULE (Edson, 2026-10-21): red first, the laser only after his go; the red stays on until go.flag or stop.flag
        for f in (GO_FLAG, STOP_FLAG):
            if f.exists(): f.unlink()
        print("RED ON: the test's box. Place a steel or aluminium offcut. Waiting for Edson's go (go.flag) or stop (stop.flag)...", flush=True)
        r = m.red_polyline(frame, until=lambda: "go" if GO_FLAG.exists() else ("stop" if STOP_FLAG.exists() else None))
        for f in (GO_FLAG, STOP_FLAG):
            if f.exists(): f.unlink()
        if r != "go":
            print("preview stopped, nothing fired"); sys.exit(0)
        print("GO received: re-init, then firing", flush=True); m.init()
    print("PRE-FLIGHT: goggles · offcut focused · air · extraction · E-stop · nothing flammable below · LightBurn closed")
    cmds, pos = [(L["DelayTime"], 800)] + settings(), (0x8000, 0x8000)
    for p, q in lines:
        c, pos = line_cmds(p, q, pos); cmds += c
    cmds.append((L["JumpTo"], 0x8000, 0x8000, 0, m.dist(pos, (0x8000, 0x8000))))
    m.bit(RED_BIT, False); m.bit(LASER_BIT, True); m.write_port(); m.cmd(OP["Fiber_SetMo"], 1)
    cmds = [(L["WritePort"], m.ports)] + cmds
    T0 = time.time()
    ended, pausing, resumed = threading.Event(), threading.Event(), threading.Event()
    th = threading.Thread(target=pauser, daemon=True); th.start()
    outcome = "done"
    try:
        tmo = a.lines * per_line * 3 + a.hold + 60
        m.run_list(cmds, timeout=tmo, stop_flag=STOP_FLAG)
        if pausing.is_set() and th.is_alive():   # returned because the pause dropped BUSY: let the pauser hold and resume
            ev["run_list_returned_in_pause"] = round(time.time() - T0, 3)
            th.join(timeout=a.hold + 5)
            if resumed.is_set():                 # running again: now wait for the real end (stop.flag still aborts)
                m.wait(BUSY, False, timeout=tmo, on_timeout=m.abort, stop_flag=STOP_FLAG)
            else:
                outcome = "did_not_resume"
    except Stopped:
        outcome = "stopped"
    except Exception as e:
        outcome = f"error: {e!r}"
    finally:
        ended.set()                              # first: the pauser may no longer arm anything
        th.join(timeout=3)
        m.safe_idle()                            # last word on the bit and the source
    log.update(outcome=outcome, seconds=round(time.time() - T0, 3), events=ev, polls=polls, after=snap("after"))
    held = [p for p in polls if p["tag"] == "hold"]
    print(f"{outcome} in {log['seconds']} s · pause sent {ev.get('pause_sent')} s, resume {ev.get('resume_sent')} s, resumed {ev.get('resumed')}")
    print(f"during the hold: paused bit {sum(p['paused'] for p in held)}/{len(held)} polls, busy {sum(p['busy'] for p in held)}/{len(held)}, "
          f"fiber {sorted({tuple(p['fiber']) for p in held})}")
    print("now look at the paused line (≈ line", int(a.at // (per_line + 0.02)) + 1, "): continuous, gap, blob or doubled?")
finally:
    try: m.safe_idle()
    finally: m.close()
    out = HERE.parent / "logs" / f"pause-{datetime.now():%Y-%m-%d_%H-%M-%S}.json"
    out.write_text(json.dumps(log, indent=1, default=str)); print("logged:", out)
