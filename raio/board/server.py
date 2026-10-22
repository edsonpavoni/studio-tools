#!/usr/bin/env python3
"""raio board: http://<host>:8877/ — the laser's page (board/CONTRACT.md).

Serves the raio folder (PLAN.html, LOG.html, MACHINE.html, research/... stay reachable) with board/index.html at /.
GET  /api/state  → {next, live, history (last 10), stills (last 8), eye, cal, now, go_ok, go_why}
POST /api/go     → touches ~/Library/Caches/raio/go.flag, only while next.json is red and red_since < 10 min (else 409)
POST /api/frame  → the red for the job on screen: starts `raio mark <file>` (a red already waiting is replaced)
POST /api/fire   → the go for the red that is on; refused (409) when no frame is on (Edson, 23:55: "fire is disabled. It only gets enabled if I have clicked on frame and the frame is active")
POST /api/pause  → while firing: toggles ~/Library/Caches/raio/pause.flag (exists = pause; removed = resume; raio.py does StopList + emission off)
POST /api/stop   → touches ~/Library/Caches/raio/stop.flag, always
Never talks to the laser itself (no usb import, no shell): frame and fire start raio.py, which does. Python 3 stdlib only.
RAIO_SPAWN_DRY=1 keeps RAIO_NO_USB=1 for the raio it starts (tests).
"""
import json, os, subprocess, sys, threading, time, urllib.request
from datetime import datetime
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

BOARD = Path(__file__).resolve().parent
RAIO = BOARD.parent
# RAIO_BOARD_DATA / RAIO_FLAGS: for testing against board/samples/ without touching the real flags (a stray go fires)
DATA = Path(os.environ.get("RAIO_BOARD_DATA") or BOARD)
FLAGS = Path(os.environ.get("RAIO_FLAGS") or Path.home() / "Library" / "Caches" / "raio")
EYE = "http://127.0.0.1:8878/state.json"
PORT = 8877
RED_WINDOW_S = 600
ROOT = RAIO.parent.parent                                   # "0000 AI": next.json's file is relative to it
PY = Path.home() / ".venvs" / "raio" / "bin" / "python"
RUN_LOG = FLAGS / "board-run.log"
run = {"proc": None, "at": 0.0, "what": None}                # the raio this server started last
run_lock = threading.Lock()


def load(name):
    try:
        return json.loads((DATA / name).read_text())
    except Exception:
        return None


def url_for(p):
    """An end photo path raio wrote (absolute, under studio/raio/) → a URL this server serves; else None."""
    if not p or not isinstance(p, str) or p.startswith("no photo"):
        return None
    try:
        rel = Path(p).resolve().relative_to(RAIO)
    except Exception:
        return None
    return "/" + "/".join(rel.parts)


def eye():
    try:
        with urllib.request.urlopen(EYE, timeout=1) as r:
            return json.loads(r.read())
    except Exception:
        return None


def red_age(nxt):
    """Seconds since the red went on (red_since; next.json's mtime if missing)."""
    try:
        return (datetime.now() - datetime.fromisoformat(nxt["red_since"])).total_seconds()
    except Exception:
        try:
            return time.time() - (DATA / "next.json").stat().st_mtime
        except Exception:
            return None


def alive(pid):
    """Is the raio process that wrote next.json still running? (None: unknown.)"""
    if not isinstance(pid, int):
        return None
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def calibration():
    """lmc/calibration.json, read only: the page's "calibrated" stamp."""
    try:
        c = json.loads((RAIO / "lmc" / "calibration.json").read_text())
        return {"x": c.get("scale_x"), "y": c.get("scale_y"), "date": (c.get("measured") or {}).get("date")}
    except Exception:
        return None


def go_check(nxt):
    if not nxt:
        return False, "nothing in red: next.json is missing"
    if nxt.get("state") != "red":
        return False, f"nothing in red: next.json state is {nxt.get('state')!r}"
    if alive(nxt.get("pid")) is False:
        return False, "raio is no longer running: the red is gone, run raio mark again"
    age = red_age(nxt)
    if age is None:
        return False, "red_since unreadable"
    if age > RED_WINDOW_S:
        return False, f"the red went on {int(age // 60)} min ago (window 10 min): run raio mark again"
    return True, "red, fresh"


def state():
    nxt, live = load("next.json"), load("live.json")
    hist = load("history.json")
    hist = hist[:10] if isinstance(hist, list) else []
    for h in hist:
        if isinstance(h, dict):
            h["end_photo_url"] = url_for(h.get("end_photo"))
    stills = load("stills.json")
    stills = [dict(x, url=url_for(x.get("path"))) for x in stills[:8] if isinstance(x, dict)] if isinstance(stills, list) else []
    if isinstance(nxt, dict):
        nxt["end_photo_url"] = url_for(nxt.get("end_photo"))
        nxt["pause_photo_urls"] = [u for u in map(url_for, nxt.get("pause_photos") or []) if u]
        nxt["red_age_s"] = red_age(nxt) if nxt.get("state") == "red" else None
        # a raio that died while red or firing never says so: the page says it instead
        if nxt.get("state") in ("red", "firing") and alive(nxt.get("pid")) is False:
            nxt["reason"] = ("raio ended mid-run without a word (crash or killed): the material may be partly marked; check the log"
                             if nxt["state"] == "firing" else "raio ended without a word while in red (crash or killed): nothing fired; mark again")
            nxt["state"] = "error"
    ok, why = go_check(nxt)
    return {"next": nxt, "live": live, "history": hist, "stills": stills, "eye": eye(), "cal": calibration(),
            "busy": busy(nxt), "run": run_note(), "pause_asked": (FLAGS / "pause.flag").exists(),
            "now": datetime.now().isoformat(timespec="seconds"), "go_ok": ok, "go_why": why}


def job_file(nxt):
    f = (nxt or {}).get("file")
    if not f:
        return None
    for p in ([Path(f)] if Path(f).is_absolute() else [ROOT / f, RAIO / f]):   # raio was run from "0000 AI" or from studio/raio
        if p.suffix == ".raio" and p.exists():
            return p
    return None


def busy(nxt):
    """Why raio cannot be started now (None: free)."""
    pr = run["proc"]
    if pr is not None and pr.poll() is None and (nxt or {}).get("pid") != pr.pid:
        return "raio is starting (planning the job)"
    if (nxt or {}).get("state") == "firing" and alive(nxt.get("pid")) is not False:
        return "firing: wait or STOP"
    return None


def spawn(path, fire):
    env = dict(os.environ)
    if not os.environ.get("RAIO_SPAWN_DRY"):
        env.pop("RAIO_NO_USB", None)                       # serve.sh sets it for the server; the raio it starts may open the laser
    FLAGS.mkdir(parents=True, exist_ok=True)
    log = open(RUN_LOG, "a")
    log.write(f"\n== {datetime.now():%H:%M:%S} {'fire' if fire else 'frame'} {path}\n"); log.flush()
    try:
        rel = str(Path(path).relative_to(ROOT))              # next.json keeps the short path (raio writes the argument as given)
    except ValueError:
        rel = str(path)
    cmd = [str(PY if PY.exists() else sys.executable), str(RAIO / "raio.py"), "mark", rel] + (["--fire"] if fire else [])
    run["proc"] = subprocess.Popen(cmd, cwd=str(ROOT), env=env, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                   start_new_session=True)
    run["at"], run["what"] = time.time(), "fire" if fire else "frame"
    return run["proc"].pid


def end_red(nxt):
    """A red already waiting: stop it and wait (≤ 6 s) for its raio to let go of the board."""
    pid = nxt.get("pid")
    touch("stop.flag")
    t0 = time.time()
    while time.time() - t0 < 6 and alive(pid):
        time.sleep(0.1)
    return not alive(pid)


def start(fire):
    with run_lock:
        nxt = load("next.json")
        why = busy(nxt)
        if why:
            return 409, {"ok": False, "reason": why}
        path = job_file(nxt)
        if not path:
            return 409, {"ok": False, "reason": "no job on screen (next.json has no .raio file that exists)"}
        red_on = nxt.get("state") == "red" and alive(nxt.get("pid")) is not False
        if fire:                                             # fire only through an active frame, never from cold
            if not red_on:
                return 409, {"ok": False, "reason": "fire needs the frame on: tap frame first"}
            touch("go.flag")
            return 200, {"ok": True, "did": "go"}
        if red_on and not end_red(nxt):
            return 409, {"ok": False, "reason": "the red that is on did not end; try STOP"}
        return 200, {"ok": True, "did": "fire" if fire else "frame", "pid": spawn(path, fire)}


def run_note():
    """The last raio this server started, if it ended badly before it could write next.json (laser off USB, …)."""
    pr = run["proc"]
    if pr is None or pr.poll() in (None, 0):
        return None
    try:
        if (DATA / "next.json").stat().st_mtime > run["at"] + 0.5:
            return None
    except Exception:
        pass
    try:
        tail = [l for l in RUN_LOG.read_text().splitlines() if l.strip()][-1]
    except Exception:
        tail = ""
    return {"what": run["what"], "code": pr.returncode, "line": tail[-240:]}


def touch(name):
    FLAGS.mkdir(parents=True, exist_ok=True)
    f = FLAGS / name
    f.write_text(datetime.now().isoformat(timespec="seconds"))
    return f


class H(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *a):
        sys.stderr.write(f"{datetime.now():%H:%M:%S} {self.address_string()} {fmt % a}\n")

    def json(self, code, obj):
        body = json.dumps(obj, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        # the board's own files change under us (next.json, preview.svg): never let the iPad cache them
        if self.path.split("?")[0].startswith("/board/") or self.path.split("?")[0] in ("/", "/index.html"):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self.path = "/board/index.html"
        elif path == "/studio.css":
            self.path = "/board/studio.css"
        elif path == "/api/state":
            return self.json(200, state())
        return super().do_GET()

    def do_POST(self):
        path = self.path.split("?")[0]
        n = int(self.headers.get("Content-Length") or 0)
        if n:
            self.rfile.read(n)
        if path == "/api/go":
            ok, why = go_check(load("next.json"))
            if not ok:
                return self.json(409, {"ok": False, "reason": why})
            f = touch("go.flag")
            return self.json(200, {"ok": True, "flag": str(f)})
        if path in ("/api/frame", "/api/fire"):
            code, body = start(path == "/api/fire")
            return self.json(code, body)
        if path == "/api/pause":
            nxt = load("next.json")
            if not nxt or nxt.get("state") != "firing" or alive(nxt.get("pid")) is False:
                return self.json(409, {"ok": False, "reason": "nothing is firing"})
            f = FLAGS / "pause.flag"
            if f.exists():
                f.unlink()
                return self.json(200, {"ok": True, "paused": False})
            touch("pause.flag")
            return self.json(200, {"ok": True, "paused": True})
        if path == "/api/stop":
            f = touch("stop.flag")
            return self.json(200, {"ok": True, "flag": str(f)})
        return self.json(404, {"ok": False, "reason": "no such endpoint"})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    srv = ThreadingHTTPServer(("0.0.0.0", port), partial(H, directory=str(RAIO)))
    sys.stderr.write(f"raio board on http://0.0.0.0:{port}/ (root {RAIO}, data {DATA}, flags {FLAGS})\n")
    srv.serve_forever()
