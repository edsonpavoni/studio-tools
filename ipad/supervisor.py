#!/usr/bin/env python3
"""
supervisor.py — keeps the iPad tools running and serves the hub page.

    python3 supervisor.py [tools.json]            (default: the tools.json beside this file,
                                                   or $IPAD_TOOLS)

Reads tools.json (re-read when it changes), starts every tool listed there in its own
folder, restarts one that dies (5 s, then doubling to 60 s), and serves the hub on the
hub port:

    GET  /            the hub page (index.html beside tools.json)
    GET  /status      JSON: access to the Dropbox folder, the Mac's name, one entry per tool
    GET  /log?id=     the last lines of a tool's log (~/Library/Logs/ipad-<id>.log)
    POST /restart?id= stop a tool; the loop starts it again within 2 s
    GET  /<file>      any other file beside tools.json (icon, manifest)

A tool whose port already answers when the supervisor looks (started by hand with its
serve.sh) is left alone and shown as "external". Pure standard library.
Installed as an app bundle + LaunchAgent by install.sh; see README.md.
"""
import http.server
import json
import os
import pathlib
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_TOOLS = pathlib.Path(
    "/Users/edsonpavoni/Library/CloudStorage/Dropbox/0000 AI/studio/ipad/tools.json")


def pick_tools_path():
    for a in sys.argv[1:]:
        if not a.startswith("--"):
            return pathlib.Path(a).expanduser().resolve()
    if os.environ.get("IPAD_TOOLS"):
        return pathlib.Path(os.environ["IPAD_TOOLS"]).expanduser().resolve()
    local = HERE / "tools.json"
    return local if local.exists() else DEFAULT_TOOLS


TOOLS_PATH = pick_tools_path()
FOLDER = TOOLS_PATH.parent
LOG_DIR = pathlib.Path.home() / "Library" / "Logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
ENV_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


def log(msg):
    sys.stderr.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    sys.stderr.flush()


def port_open(port, host="127.0.0.1", timeout=0.3):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def local_name():
    n = socket.gethostname().lower()
    if not n.endswith(".local"):
        n += ".local"
    return n


class Tool:
    def __init__(self, spec):
        self.spec = spec
        self.id = spec["id"]
        self.proc = None
        self.started = 0.0
        self.restarts = 0
        self.failures = 0            # consecutive quick exits, drives the backoff
        self.next_try = 0.0
        self.last_exit = None
        self.external = False
        self.error = None
        self.log_path = LOG_DIR / ("ipad-%s.log" % self.id)

    @property
    def port(self):
        return int(self.spec["port"])

    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def cwd(self):
        return (FOLDER / self.spec["dir"]).resolve()

    def start(self):
        cwd = self.cwd()
        env = dict(os.environ, PATH=ENV_PATH, PYTHONUNBUFFERED="1")
        try:
            lf = open(self.log_path, "ab")
            lf.write(("\n--- %s start: %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"),
                                              " ".join(self.spec["cmd"]))).encode())
            self.proc = subprocess.Popen(self.spec["cmd"], cwd=str(cwd), env=env,
                                         stdin=subprocess.DEVNULL, stdout=lf, stderr=lf)
            lf.close()
            self.started = time.time()
            self.error = None
            self.external = False
            log("%s: started pid %d in %s" % (self.id, self.proc.pid, cwd))
        except Exception as e:                       # folder denied, python missing…
            self.error = "%s: %s" % (type(e).__name__, e)
            self.proc = None
            self.failures += 1
            self.next_try = time.time() + min(60, 5 * 2 ** min(self.failures, 4))
            log("%s: could not start (%s); retry in %ds" % (self.id, self.error,
                                                            self.next_try - time.time()))

    def reap(self):
        """Called when the process has exited."""
        code = self.proc.returncode
        up = time.time() - self.started
        self.last_exit = {"code": code, "time": time.time(), "uptime": round(up)}
        self.proc = None
        self.restarts += 1
        self.failures = 0 if up > 600 else self.failures + 1
        self.next_try = time.time() + min(60, 5 * 2 ** min(self.failures, 4))
        log("%s: exited %s after %ds; retry in %ds" % (self.id, code, up,
                                                        self.next_try - time.time()))

    def stop(self):
        if self.alive():
            self.proc.terminate()
            try:
                self.proc.wait(3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(3)
            log("%s: stopped" % self.id)
        self.proc = None

    def tick(self):
        if self.proc is not None and self.proc.poll() is not None:
            self.reap()
        if self.alive():
            return
        if port_open(self.port):
            if not self.external:
                log("%s: port %d already answers; leaving it alone (external)" % (self.id, self.port))
            self.external = True
            return
        self.external = False
        if time.time() >= self.next_try:
            self.start()

    def status(self):
        up = self.alive() or self.external or port_open(self.port)
        state = ("external" if self.external else
                 "up" if (self.alive() and up) else
                 "starting" if self.alive() else
                 "down")
        s = dict(self.spec)
        s.update({"state": state, "up": bool(up), "pid": self.proc.pid if self.alive() else None,
                  "restarts": self.restarts, "last_exit": self.last_exit, "error": self.error,
                  "since": self.started or None})
        return s


class Supervisor:
    def __init__(self):
        self.tools = {}
        self.config = {"hub_port": 8888, "tools": []}
        self.config_mtime = None
        self.config_error = None
        self.access = "unknown"
        self.lock = threading.Lock()
        self.stopping = False

    def check_access(self):
        try:
            os.listdir(FOLDER)
            self.access = "ok"
        except PermissionError as e:
            self.access = "denied"
        except FileNotFoundError:
            self.access = "missing"
        return self.access

    def load_config(self):
        try:
            m = TOOLS_PATH.stat().st_mtime
        except OSError as e:
            self.config_error = str(e)
            return
        if m == self.config_mtime:
            return
        try:
            cfg = json.loads(TOOLS_PATH.read_text())
            assert isinstance(cfg.get("tools"), list)
        except Exception as e:
            self.config_error = "%s: %s" % (type(e).__name__, e)
            log("tools.json not usable (%s); keeping the last good one" % self.config_error)
            self.config_mtime = m
            return
        self.config_error = None
        self.config_mtime = m
        self.config = cfg
        with self.lock:
            seen = set()
            for spec in cfg["tools"]:
                seen.add(spec["id"])
                t = self.tools.get(spec["id"])
                if t is None:
                    self.tools[spec["id"]] = Tool(spec)
                elif t.spec != spec:
                    log("%s: definition changed; restarting" % spec["id"])
                    t.stop()
                    self.tools[spec["id"]] = Tool(spec)
            for tid in [k for k in self.tools if k not in seen]:
                self.tools[tid].stop()
                del self.tools[tid]
        log("tools.json loaded: %s" % ", ".join(t["id"] for t in cfg["tools"]))

    def loop(self):
        n = 0
        while not self.stopping:
            if n % 5 == 0:
                self.check_access()
                self.load_config()
            with self.lock:
                for t in list(self.tools.values()):
                    try:
                        t.tick()
                    except Exception as e:
                        log("%s: tick failed: %s" % (t.id, e))
            n += 1
            time.sleep(2)

    def shutdown(self, *_):
        if self.stopping:
            return
        self.stopping = True
        log("stopping")
        with self.lock:
            for t in self.tools.values():
                t.stop()
        os._exit(0)

    def status(self):
        with self.lock:
            tools = [t.status() for t in self.tools.values()]
        return {"access": self.access, "folder": str(FOLDER), "config_error": self.config_error,
                "host": local_name(), "hub_port": self.config.get("hub_port", 8888),
                "time": time.time(), "tools": tools}


SUP = Supervisor()

FALLBACK_HTML = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>iPad tools</title><body style="font:18px/1.5 -apple-system,sans-serif;max-width:640px;margin:60px auto;padding:0 20px;color:#eee;background:#1e1e1e">
<h1>iPad tools</h1><p>The runner is up but cannot read its folder in Dropbox:</p><pre style="white-space:pre-wrap">%s</pre>
<p>On the Mac: System Settings › Privacy &amp; Security › Full Disk Access › + › <code>~/Applications/iPadTools.app</code> (Cmd+Shift+G to type the path), switch it on. This page recovers by itself within 10 s.</p>
<p>Status: <a href="/status" style="color:#8ab4f8">/status</a></p></body>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == "/status":
            self._send(200, json.dumps(SUP.status()))
        elif u.path == "/log":
            tid = q.get("id", [""])[0]
            t = SUP.tools.get(tid)
            if not t:
                self._send(404, json.dumps({"error": "no such tool"}))
                return
            n = int(q.get("n", ["80"])[0])
            try:
                lines = t.log_path.read_text(errors="replace").splitlines()[-n:]
            except OSError:
                lines = []
            self._send(200, "\n".join(lines), "text/plain; charset=utf-8")
        else:
            rel = "index.html" if u.path in ("", "/") else u.path.lstrip("/")
            p = (FOLDER / rel)
            try:
                p = p.resolve()
                if FOLDER.resolve() not in p.parents or not p.is_file():
                    raise FileNotFoundError(rel)
                data = p.read_bytes()
            except PermissionError as e:
                self._send(503, FALLBACK_HTML % e, "text/html; charset=utf-8")
                return
            except (FileNotFoundError, NotADirectoryError):
                if rel == "index.html":
                    self._send(503, FALLBACK_HTML % ("index.html not found in %s" % FOLDER),
                               "text/html; charset=utf-8")
                else:
                    self._send(404, "not found", "text/plain")
                return
            ext = p.suffix.lower()
            ctype = {".html": "text/html; charset=utf-8", ".json": "application/json",
                     ".webmanifest": "application/manifest+json", ".png": "image/png",
                     ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml",
                     ".md": "text/markdown; charset=utf-8"}.get(ext, "application/octet-stream")
            self._send(200, data, ctype)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == "/restart":
            tid = q.get("id", [""])[0]
            t = SUP.tools.get(tid)
            if not t:
                self._send(404, json.dumps({"ok": False, "error": "no such tool"}))
                return
            with SUP.lock:
                if t.external:
                    # started by hand elsewhere: stop whatever holds the port, then adopt it
                    out = subprocess.run(["lsof", "-tnP", "-iTCP:%d" % t.port, "-sTCP:LISTEN"],
                                         capture_output=True, text=True).stdout.split()
                    for pid in out:
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                        except OSError:
                            pass
                    t.external = False
                else:
                    t.stop()
                t.next_try = 0
            self._send(200, json.dumps({"ok": True}))
        else:
            self._send(404, json.dumps({"ok": False}))


def main():
    log("iPad tools runner; tools.json = %s" % TOOLS_PATH)
    SUP.check_access()
    SUP.load_config()
    if SUP.access != "ok":
        log("folder not readable (%s): the hub will say so and keep trying" % SUP.access)
    signal.signal(signal.SIGTERM, SUP.shutdown)
    signal.signal(signal.SIGINT, SUP.shutdown)
    threading.Thread(target=SUP.loop, daemon=True).start()
    port = int(SUP.config.get("hub_port", 8888))
    for a in sys.argv[1:]:
        if a.startswith("--port="):
            port = int(a.split("=", 1)[1])
    srv = http.server.ThreadingHTTPServer(("0.0.0.0", port), Handler)
    srv.daemon_threads = True
    log("hub: http://localhost:%d  (iPad: http://%s:%d)" % (port, local_name(), port))
    try:
        srv.serve_forever()
    finally:
        SUP.shutdown()


if __name__ == "__main__":
    main()
