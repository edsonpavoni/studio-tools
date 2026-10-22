#!/usr/bin/env python3
"""raio — the studio's software for the ComMarker B6 MOPA (README.md, FORMAT.md).

    raio import <file.lbrn2> [-o job.raio] [--centre] [--discard-outside]   LightBurn → .raio (refuses Text, Bitmap, off-field)
    raio show   <job.raio>                                 layers in run order, settings, totals
    raio plan   <job.raio> [--svg out.svg] [--png out.png] [--dump N]   board commands + stats + preview, no USB
    raio frame  <job.raio> [--seconds 20] [--box]          red frame of the job's contour (--box: its bounding box) (opens the laser)
    raio load   <job.raio>                                 put the job on the board page (no laser): then frame / fire there
    raio mark   <job.raio> [--only L2,L3]                  red until Edson's go, then fire (opens the laser)
    raio still  [--note "…"]                               a full still from RaioEye → logs/, shown on the board (board/stills.json)

`frame` and `mark` build everything first; with RAIO_NO_USB=1 they stop at "would open the laser".
The go: the session touches ~/Library/Caches/raio/go.flag on Edson's word; stop.flag cancels (lmc.GO_FLAG/STOP_FLAG).
"""
import argparse, json, math, os, sys, threading, time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from job import model, lbrn, plan as planner  # noqa: E402


def cmd_import(a):
    try:
        job = lbrn.import_file(a.file, place="centre" if a.centre else "file", discard_outside=a.discard_outside)
    except lbrn.LbrnError as e:
        print("import refused:"); [print("  ·", r) for r in e.reasons]
        return 2
    out = Path(a.o) if a.o else Path(a.file).with_suffix(".raio")
    model.save(job, out)
    print(f"wrote {out}")
    src = job["source"]
    if src["defaults_applied"]:
        print("LightBurn omitted these; raio filled its defaults (job/README.md):")
        for k, v in src["defaults_by_layer"].items():
            print(f"  · {k}: " + ", ".join(f"{f}={lbrn.DEFAULTS[f][0]}" for f in v))
    for w in src["import_warnings"]:
        print("  !", w)
    _show(job)
    return 0


def _show(job):
    print(f"\n{job['name']}" + (f"  ·  {job['material'].get('name')}" if job.get("material", {}).get("name") else ""))
    if job.get("notes"):
        print("NOTES:", job["notes"])
    rows = model.totals(job)
    print(f"\n{'#':>2} {'layer':14s} {'mode':4s} {'pow%':>5} {'mm/s':>6} {'kHz':>6} {'ns':>4} {'pass':>4} "
          f"{'shapes':>6} {'path mm':>9}  extra")
    for L, r in zip(model.run_order(job), rows):
        extra = []
        if L.get("wobble"):
            extra.append(f"wobble {L['wobble']['size_mm']:g}/{L['wobble']['step_mm']:g}")
        if L.get("fill"):
            f = L["fill"]
            extra.append(f"int {f['interval_mm']:g} ∠{f['angle_deg']:g}+{f['angle_per_pass_deg']:g}" +
                         (" bidir" if f["bidir"] else " unidir") + (" cross" if f["cross"] else ""))
            extra.append(f"area {r['area_mm2']:.1f} mm²")
        if L.get("kerf_mm"):
            extra.append(f"kerf {L['kerf_mm']:+g}")
        if not L["output"]:
            extra.append("NOT MARKED")
        print(f"{L['order']:>2} {L['name'][:14]:14s} {L['mode']:4s} {L['power_pct']:5g} {L['speed_mm_s']:6g} {L['freq_khz']:6g} "
              f"{L['pulse_ns']:4d} {L['passes']:4d} {r['shapes']:6d} {r['outline_mm']:9.1f}  " + " · ".join(extra))
    bb = planner.frame_outline(job)
    if bb:
        print(f"\nbounding box (output layers): x {bb[0][0]:.2f} … {bb[1][0]:.2f}, y {bb[0][1]:.2f} … {bb[2][1]:.2f} mm "
              f"(field centre 0,0; +y toward the column)")
    for w in model.warnings(job):
        print("  !", w)


def cmd_show(a):
    _show(model.load(a.job))
    return 0


def _plan(a, job):
    only = set(a.only.split(",")) if getattr(a, "only", None) else None
    return planner.plan(job, pass_order=a.pass_order, jump_delay=not a.no_jump_delay, only=only,
                        frame_kind="box" if getattr(a, "box", False) else "contour")


def _print_plan(p):
    s = p["stats"]
    print(f"\n{'layer':14s} {'mode':4s} {'pass':>4} {'entities':>8} {'marks':>8} {'mark mm':>10} {'jump mm':>9} {'est s':>7}")
    for L in p["layers"]:
        alt = f"   (if speed = forward advance: {L['est_s_if_speed_is_advance']:.1f} s)" if "est_s_if_speed_is_advance" in L else ""
        print(f"{L['name'][:14]:14s} {L['mode']:4s} {L['passes']:4d} {L['entities']:8d} {L['marks']:8d} "
              f"{L['mark_mm']:10.1f} {L['jump_mm']:9.1f} {L['est_s']:7.1f}{alt}")
    print(f"\ncommands {s['commands']} · packets {s['packets']} · total passes {s['total_passes']} · "
          f"marked {s['mark_mm'] / 1000:.2f} m · estimate {s['est_s']:.1f} s, up to {s['est_s_hi']:.1f} s if the polygon "
          f"delay applies at every vertex (rough; logs decide, FORMAT.md)")
    print(f"longest packet {s['max_packet_s']:.1f} s of board time" +
          ("  ! over 8 s: lmc.run_list waits only 10 s for READY between packets" if s["max_packet_s"] > 8 else ""))


def cmd_plan(a):
    job = model.load(a.job)
    p = _plan(a, job)
    _print_plan(p)
    if a.dump:
        print(f"\nfirst {a.dump} commands:")
        for c in p["cmds"][:a.dump]:
            print("  ", planner.describe_cmd(c))
    if a.svg:
        Path(a.svg).write_text(planner.preview_svg(job)); print("preview:", a.svg)
    if a.png:
        planner.preview_png(job, a.png); print("preview:", a.png)
    return 0


def _timeout(p):
    return max(60, int(p["stats"]["est_s_hi"] * 3 + 60))


def _open_laser(on_busy=None):
    """The one place raio opens the board. RAIO_NO_USB=1 (agents, dry runs) stops here.
    on_busy(message): called before exiting when another program (LightBurn) holds the board."""
    if os.environ.get("RAIO_NO_USB"):
        print("RAIO_NO_USB is set: would open the laser here. Stopping (dry run complete).")
        return None
    sys.path.insert(0, str(HERE / "lmc"))
    import lmc
    try:
        m = lmc.LMC()
    except lmc.Busy as e:
        if on_busy:
            on_busy(str(e))
        sys.exit(str(e))
    return m


def _check_driver(m, g):
    if (abs(m.u_per_mm - g.u_per_mm) > 1e-3 or m.swap != g.swap or m.sx != g.sx or m.sy != g.sy
            or abs(m.cal_x - g.cal_x) > 1e-6 or abs(m.cal_y - g.cal_y) > 1e-6):
        raise SystemExit(f"driver frame differs from the plan (u/mm {m.u_per_mm} vs {g.u_per_mm}, swap {m.swap}, "
                         f"cal {m.cal_x:.6f}/{m.cal_y:.6f} vs {g.cal_x:.6f}/{g.cal_y:.6f}); refusing")


def cmd_load(a):
    """The board's job without the laser: next.json "ready" + preview; Edson frames and fires from the page."""
    job = model.load(a.job)
    for w in model.warnings(job):
        print("  !", w)
    p = _plan(a, job)
    _print_plan(p)
    _board_next(job, p, a, "ready", red_since=None, go_at=None, done_at=None, seconds=None, end_photo=None, reason=None, detail=None)
    print("on the board: http://localhost:8877/")
    return 0


def cmd_frame(a):
    job = model.load(a.job)
    p = _plan(a, job)
    fr = p["frame"]
    print(f"red frame: {fr[0][0]:.2f},{fr[0][1]:.2f} → {fr[2][0]:.2f},{fr[2][1]:.2f} mm for {a.seconds} s")
    m = _open_laser()
    if m is None:
        return 0
    try:
        m.init(); _check_driver(m, planner.Galvo())
        m.red_polyline(fr, seconds=a.seconds)
    finally:
        try: m.safe_idle()
        finally: m.close()
    return 0


def _end_photo(kind="mark", suffix="-end"):
    """One full-resolution frame from RaioEye after a job; the bed as it was left. Never fails the run."""
    import urllib.request
    try:
        stamp = f"{datetime.now():%Y-%m-%d_%H-%M-%S}"
        dest = HERE / "logs" / f"raio-{kind}-{stamp}{suffix}.jpg"
        with urllib.request.urlopen("http://127.0.0.1:8878/snap.jpg?full=1", timeout=15) as r:
            dest.write_bytes(r.read())
        return str(dest)
    except Exception as e:
        return f"no photo: {e}"


BOARD = HERE / "board"

def _board_next(job, p, a, state, **extra):
    """Publish the job the page shows (board/CONTRACT.md next.json + preview.svg)."""
    try:
        BOARD.mkdir(exist_ok=True)
        try:
            (BOARD / "preview.svg").write_text(planner.preview_svg(job, board=True))
        except Exception:
            pass
        st = p["stats"]
        planned = {L_.get("id"): L_ for L_ in p["layers"]}
        colors = planner.layer_colors(job)
        layers = []
        for jl in sorted(job.get("layers", []), key=lambda l: l.get("order", 0)):
            pl = planned.get(jl.get("id"), {})
            w, fl = jl.get("wobble"), jl.get("fill")
            layers.append({"order": jl.get("order"), "name": jl.get("name"), "mode": jl.get("mode"),
                           "power_pct": jl.get("power_pct"), "speed_mm_s": jl.get("speed_mm_s"), "freq_khz": jl.get("freq_khz"),
                           "pulse_ns": jl.get("pulse_ns"), "passes": jl.get("passes"),
                           "wobble": f"{w['size_mm']}/{w['step_mm']}" if w else None,
                           "fill": f"{fl['interval_mm']} mm @ {fl.get('angle_deg', 0)}°" + (f" +{fl['angle_per_pass_deg']}°/pass" if fl.get("angle_per_pass_deg") else "") if fl else None,
                           "path_mm": round(pl.get("mark_mm", 0), 1) if pl else None, "output": jl.get("output", True),
                           "planned": bool(pl), "color": colors.get(jl.get("id"))})
        try:
            from job import geom
            pts = [pt for jl in job.get("layers", []) if jl.get("output", True) for sh in jl.get("shapes", []) for pt in sh.get("pts", [])]
            bbox = [round(v, 2) for v in geom.bbox([pts])] if pts else None
        except Exception:
            bbox = None
        d = {"state": state, "job": job.get("name"), "file": str(a.job), "material": job.get("material"), "notes": job.get("notes"),
             "layers": layers, "totals": {"passes": st.get("total_passes"), "commands": st.get("commands"), "packets": st.get("packets"),
                                          "marked_m": round(st.get("mark_mm", 0) / 1000, 2), "est_s": round(st.get("est_s") or 0, 1)},
             "bbox": bbox, "preview_svg": "board/preview.svg", "pid": os.getpid()}
        prev = {}
        f = BOARD / "next.json"
        if f.exists():
            try: prev = json.loads(f.read_text())
            except Exception: prev = {}
        for k in ("red_since", "go_at", "done_at", "seconds", "end_photo"):
            d[k] = prev.get(k) if prev.get("job") == d["job"] else None
        if state == "red":                                   # how the previous mark ended (any job): a stop or a crash → the page suggests a red rectangle first
            d["after"], d["after_at"] = prev.get("state"), prev.get("done_at")
        else:
            d["after"], d["after_at"] = prev.get("after"), prev.get("after_at")
        d.update(extra)
        f.write_text(json.dumps(d, indent=1, default=str))
    except Exception as e:
        print("board: could not write next.json:", e)

def _board_live(**d):
    try:
        BOARD.mkdir(exist_ok=True)
        tmp = BOARD / f".live.{threading.get_ident()}.tmp"   # two threads write it (progress, pause): never a torn read
        tmp.write_text(json.dumps(d, default=str)); os.replace(tmp, BOARD / "live.json")
    except Exception:
        pass

def _board_still(path, note=""):
    """The pictures the session judged by (board/stills.json, newest first), so Edson sees what the session saw."""
    try:
        f = BOARD / "stills.json"
        h = json.loads(f.read_text()) if f.exists() else []
        h.insert(0, {"path": path, "time": datetime.now().isoformat(timespec="seconds"), "note": note})
        f.write_text(json.dumps(h[:30], indent=1))
    except Exception:
        pass


def cmd_still(a):
    """raio still --note "…": one full still from RaioEye (never opens the laser) → logs/ + the board."""
    path = _end_photo("still", "")
    if path.startswith("no photo"):
        print(path); return 1
    _board_still(path, a.note or "")
    print(path); return 0


def _board_history(entry):
    try:
        f = BOARD / "history.json"
        h = json.loads(f.read_text()) if f.exists() else []
        h.insert(0, entry); f.write_text(json.dumps(h[:50], indent=1, default=str))
    except Exception:
        pass


def cmd_mark(a):
    """mark_test.py's flow: red frame until Edson's go (GO_FLAG) or stop (STOP_FLAG); on the go init() again,
    then fire(): red off, laser-enable bit on, MO open (immediate), list = DelayTime 800 + WritePort + job."""
    job = model.load(a.job)
    for w in model.warnings(job):
        print("  !", w)
    p = _plan(a, job)
    _print_plan(p)
    timeout = _timeout(p)
    if p["stats"]["max_packet_s"] > 9.5 and not a.allow_long_packets:
        print(f"refusing: one packet keeps the board busy {p['stats']['max_packet_s']:.1f} s; lmc.run_list would time out "
              f"waiting for READY (10 s) mid-job, if the board holds only one packet ahead (unknown). "
              f"--allow-long-packets overrides.")
        return 2
    print(f"run_list timeout {timeout} s (3 × upper estimate + 60; on timeout the driver aborts)")
    def busy(msg):
        _board_next(job, p, a, "error", reason="LightBurn has the laser: close it, then mark again", detail=msg,
                    red_since=None, go_at=None, done_at=datetime.now().isoformat(timespec="seconds"), seconds=None, end_photo=None)
    m = _open_laser(on_busy=busy)
    if m is None:
        return 0
    sys.path.insert(0, str(HERE / "lmc"))
    from lmc import L, OP, LASER_BIT, RED_BIT, BUSY, GO_FLAG, STOP_FLAG
    log = {"when": datetime.now().isoformat(timespec="seconds"), "what": "raio mark", "job": str(a.job),
           "name": job["name"], "stats": p["stats"], "layers": [{k: v for k, v in L_.items()} for L_ in p["layers"]]}
    try:
        log["ident"] = {k: list(v) for k, v in m.init().items()}
        _check_driver(m, planner.Galvo())
        for f in (GO_FLAG, STOP_FLAG):
            if f.exists(): f.unlink()
        print("PRE-FLIGHT: goggles · material focused · air · extraction · E-stop · nothing flammable below · LightBurn closed")
        print("RED ON: place the material. Waiting for Edson's go (go.flag) or stop (stop.flag)...", flush=True)
        _board_next(job, p, a, "red", red_since=datetime.now().isoformat(timespec="seconds"), go_at=None, done_at=None, seconds=None,
                    end_photo=None, reason=None, detail=None)
        _board_live(state="idle")
        r = m.red_polyline(p["frame"], until=lambda: "go" if GO_FLAG.exists() else ("stop" if STOP_FLAG.exists() else None))
        for f in (GO_FLAG, STOP_FLAG):
            if f.exists(): f.unlink()
        log["preview"] = r
        if r != "go":
            print("preview stopped, nothing fired"); _board_next(job, p, a, "stopped", done_at=datetime.now().isoformat(timespec="seconds")); return 0
        print("GO received: re-init, then firing", flush=True)
        go_at = datetime.now().isoformat(timespec="seconds")
        _board_next(job, p, a, "firing", go_at=go_at)
        m.init(); _check_driver(m, planner.Galvo())
        m.bit(RED_BIT, False); m.bit(LASER_BIT, True); m.write_port()
        m.cmd(OP["Fiber_SetMo"], 1)
        cmds = [(L["DelayTime"], 800), (L["WritePort"], m.ports)] + p["cmds"]
        t0 = time.time()
        total_packets = p["stats"].get("packets")
        from lmc import Stopped, PAUSED, PAUSE_FLAG
        if PAUSE_FLAG.exists(): PAUSE_FLAG.unlink()
        pz = {"paused": False, "since": 0.0, "paused_s": 0.0, "pauses": 0, "failed": None, "last": {}}
        ended = threading.Event()

        def live():
            _board_live(state="paused" if pz["paused"] else "firing", job=job.get("name"), started=go_at,
                        elapsed_s=round(time.time() - t0, 1), paused_s=round(pz["paused_s"], 1),
                        paused_since=datetime.fromtimestamp(pz["since"]).isoformat(timespec="milliseconds") if pz["paused"] else None,
                        **pz["last"])

        def progress(sent, total):
            # packets are queued, not yet executed: the layer/pass is that of the last command sent (+3: ReadyMark, DelayTime, WritePort)
            w = planner.where(p["marks"], sent * 256 - 3 - 1) or (None, None, None)
            pz["last"] = {"packets_sent": sent, "packets": total, "layer": w[0], "pass": w[1], "passes": w[2]}
            live()

        def pauser():
            """The board page's pause (pause.flag). Measured 2026-10-22 01:21–01:25 (lmc/pause_test.py, 3 runs):
            StopList, then laser-enable bit low + MO closed, never trusting the board's pause with emission
            (04-safety.md §1); resume = bit + MO back, RestartList, and the status must leave PAUSED within 1 s or the job is aborted."""
            while not ended.is_set():
                want = PAUSE_FLAG.exists()
                try:
                    if want and not pz["paused"]:
                        if not m.status() & BUSY:            # only a list that is executing is paused; before ExecuteList or after the
                            time.sleep(0.05); continue        # end StopList is unmeasured: the request waits for the board to run
                        m.cmd(OP["StopList"]); m.bit(LASER_BIT, False); m.write_port(); m.cmd(OP["Fiber_SetMo"], 0)
                        pz.update(paused=True, since=time.time()); pz["pauses"] += 1
                        pz.setdefault("at", []).append({"t": round(time.time() - t0, 2), **pz["last"]})   # was it still streaming? (lmc hold)
                        k = pz["pauses"]
                        threading.Thread(target=lambda: pz.setdefault("photos", []).append(_end_photo("mark", f"-pause{k}")), daemon=True).start()
                        print(f"PAUSED at {time.time() - t0:.1f} s: list held, emission off", flush=True); live()
                    elif not want and pz["paused"]:
                        if ended.is_set():
                            break
                        if not m.status() & PAUSED:          # nothing held any more (aborted, ended): never re-arm, let the main loop read it
                            pz["paused_s"] += time.time() - pz["since"]; pz["paused"] = False; live(); continue
                        m.bit(LASER_BIT, True); m.write_port(); m.cmd(OP["Fiber_SetMo"], 1); time.sleep(0.01)
                        m.cmd(OP["RestartList"])
                        t_chk, ok = time.time() + 1.0, False
                        while time.time() < t_chk:
                            if not m.status() & PAUSED:
                                ok = True; break
                            time.sleep(0.05)
                        pz["paused_s"] += time.time() - pz["since"]
                        if not ok:
                            pz["failed"] = "the board did not resume within 1 s: aborted, emission off"
                            print(pz["failed"], flush=True); m.abort(); m.safe_idle()
                            STOP_FLAG.write_text("pauser abort")   # the main thread may still be streaming: its next wait aborts and stops
                        pz["paused"] = False
                        print(f"RESUMED at {time.time() - t0:.1f} s" if ok else "", flush=True); live()
                except Exception as e:
                    pz["failed"] = f"pause/resume broke: {e!r}"
                    try: m.abort(); m.safe_idle()
                    finally:
                        pz["paused"] = False
                        STOP_FLAG.write_text("pauser abort")
                    return
                time.sleep(0.05)

        th = threading.Thread(target=pauser, daemon=True)
        th.start()
        held = lambda: pz["paused"]
        outcome = "done"
        try:
            try:
                m.run_list(cmds, timeout=timeout, progress=progress, stop_flag=STOP_FLAG, hold=held)
                # the board drops BUSY while paused, so run_list returns at a pause: wait it out until the list is really done
                while not pz["failed"]:
                    st = m.status()
                    if st & BUSY:
                        m.wait(BUSY, False, timeout=timeout, on_timeout=m.abort, stop_flag=STOP_FLAG, hold=held)
                        continue
                    if pz["paused"] or st & PAUSED:
                        if STOP_FLAG.exists():
                            STOP_FLAG.unlink(); m.abort(); raise Stopped("stop flag")
                        time.sleep(0.05)
                        continue
                    break
                if pz["failed"]:
                    raise RuntimeError(pz["failed"])
            except Stopped:
                if pz["failed"]:
                    raise RuntimeError(pz["failed"])        # the pauser aborted: an error, not Edson's cancel
                outcome = "stopped"; print("STOPPED by the stop flag; board aborted and idle")
        except Exception as e:                               # the page must not stay on "firing" forever
            _board_next(job, p, a, "error", reason=f"the run broke: {e}", done_at=datetime.now().isoformat(timespec="seconds"),
                        seconds=round(time.time() - t0, 3))
            _board_live(state="idle")
            raise
        finally:
            ended.set()                                  # the pauser may no longer touch the bit or the source
            th.join(timeout=3)
            if pz["paused"]:                             # ended while paused (cancel): count that hold too
                pz["paused_s"] += time.time() - pz["since"]
            if PAUSE_FLAG.exists(): PAUSE_FLAG.unlink()
            m.safe_idle()
        log["mark_seconds"] = round(time.time() - t0, 3); log["outcome"] = outcome
        log["paused_s"], log["pauses"], log["pause_at"] = round(pz["paused_s"], 2), pz["pauses"], pz.get("at", [])
        print(f"{outcome} in {log['mark_seconds']} s")
        st, fib, port = m.status(), m.cmd(OP["Fiber_GetStMO_AP"]), m.cmd(OP["ReadPort"])
        log["after"] = {"status": st, "fiber": list(fib), "port": list(port)}
        print(f"after: status=0x{st:04x} busy={bool(st & BUSY)} fiber={['%04x' % w for w in fib]}")
        done_at = datetime.now().isoformat(timespec="seconds")
        _board_next(job, p, a, outcome, done_at=done_at, seconds=log["mark_seconds"])   # the page stops its clock now, not after the photo
        _board_live(state="idle")
        log["end_photo"] = _end_photo()                      # RaioEye (:8878), after the armed flag is down
        log["pause_photos"] = [x for x in pz.get("photos", []) if not str(x).startswith("no photo")]
        _board_next(job, p, a, outcome, end_photo=log["end_photo"], pause_photos=log["pause_photos"])
        _board_history({"job": job.get("name"), "file": str(a.job), "go_at": go_at, "done_at": done_at, "est_s": round(p["stats"]["est_s"], 1),
                        "seconds": log["mark_seconds"], "state": outcome, "end_photo": log["end_photo"]})
    finally:
        try: m.safe_idle()
        finally: m.close()
        out = HERE / "logs" / f"raio-mark-{datetime.now():%Y-%m-%d_%H-%M-%S}.json"
        out.write_text(json.dumps(log, indent=1, default=str)); print("logged:", out)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="raio", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("import"); s.add_argument("file"); s.add_argument("-o")
    s.add_argument("--centre", action="store_true", help="place the job's output layers at the field centre")
    s.add_argument("--discard-outside", action="store_true", help="drop shapes outside the field (LightBurn's DiscardOutOfBoundsShapes)")
    s.set_defaults(fn=cmd_import)
    s = sub.add_parser("show"); s.add_argument("job"); s.set_defaults(fn=cmd_show)
    for name, fn in (("plan", cmd_plan), ("frame", cmd_frame), ("mark", cmd_mark), ("load", cmd_load)):
        s = sub.add_parser(name); s.add_argument("job"); s.set_defaults(fn=fn)
        s.add_argument("--only", help="comma list of layer ids or names")
        s.add_argument("--pass-order", choices=["shape", "layer"], default="shape")
        s.add_argument("--no-jump-delay", action="store_true", help="omit DelayTime(jump_us/10) after hatch jumps")
        s.add_argument("--box", action="store_true", help="frame the bounding box instead of the contour")
        if name == "plan":
            s.add_argument("--svg"); s.add_argument("--png"); s.add_argument("--dump", type=int, default=0)
        if name == "mark":
            s.add_argument("--allow-long-packets", action="store_true")
        if name == "frame":
            s.add_argument("--seconds", type=float, default=20)
    s = sub.add_parser("still"); s.add_argument("--note"); s.set_defaults(fn=cmd_still)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except (model.JobError, planner.PlanError) as e:
        print(e); return 2


if __name__ == "__main__":
    sys.exit(main())
