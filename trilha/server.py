#!/usr/bin/env python3
"""
server.py — serve the trilha (hand-routing) UI to the iPad.

Always on (studio/ipad keeps it running on port 8481):

    python3 server.py --port 8481

serves whatever board the file `current-board` (beside this script) points at, and
re-reads that pointer on every request, so a board is switched without a restart:

    python3 server.py /path/to/board/dist/index/circuit.json

writes the pointer, adds the board to `recent-boards.json`, and, if a server already
answers on the port, just says so and exits (the iPad shows the new board on its next
load). Without a running server it serves the board itself, as it always did.
With no board set, the page lists the recent boards to tap.

Every save writes board.handroute NEXT TO the circuit.json (strokes + component
moves), which is where the converter looks:

    python3 circuit2lbrn.py circuit.json --manual-traces auto --moat -o board.lbrn2

A legacy traces.json (pre-2026-08-25 boards) is read if no .handroute file exists
yet; the first save migrates it. Pure standard library, no installs. Saves are
atomic and every save also writes a timestamped copy under handroute-history/ so
a slip of the Pencil can't destroy an afternoon of drawing. One server per port,
one board at a time: two clients on one drawing overwrite each other.
"""

import html
import http.server
import json
import os
import shlex
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

import netmap

HERE = os.path.dirname(os.path.abspath(__file__))
POINTER = os.path.join(HERE, "current-board")
RECENTS = os.path.join(HERE, "recent-boards.json")
DEFAULT_PORT = 8481


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def local_name():
    n = socket.gethostname().lower()
    return n if n.endswith(".local") else n + ".local"


# ------------------------------------------------------------------ the pointer

def read_pointer():
    try:
        p = open(POINTER).read().strip()
    except OSError:
        return None
    return p or None


def read_recents():
    try:
        r = json.load(open(RECENTS))
        return r if isinstance(r, list) else []
    except (OSError, ValueError):
        return []


def project_name(cj_path):
    """Name the board after the PROJECT, walking up past the build folders. A file
    called "index.lbrn2" or "dist.lbrn2" is unrecognisable in a Downloads list a
    week later; "pcb-v3.lbrn2" is the board you cut."""
    base, proj = "board", os.path.dirname(cj_path)
    d = os.path.dirname(cj_path)
    while d and d != "/":
        nm = os.path.basename(d)
        if nm and nm.lower() not in ("index", "dist", "build", "out", "output"):
            base, proj = nm, d
            break
        d = os.path.dirname(d)
    return base, proj


def set_pointer(cj_path):
    cj_path = os.path.abspath(cj_path)
    if not os.path.isfile(cj_path) or not cj_path.endswith(".json"):
        raise FileNotFoundError("not a circuit.json: %s" % cj_path)
    tmp = POINTER + ".tmp"
    open(tmp, "w").write(cj_path + "\n")
    os.replace(tmp, POINTER)
    name, _ = project_name(cj_path)
    rec = [r for r in read_recents() if r.get("path") != cj_path]
    rec.insert(0, {"path": cj_path, "project": name, "opened": time.time()})
    tmp = RECENTS + ".tmp"
    json.dump(rec[:12], open(tmp, "w"), indent=1)
    os.replace(tmp, RECENTS)
    return cj_path


# ------------------------------------------------------------------ a board

class Board:
    def __init__(self, cj_path):
        self.cj_path = cj_path
        self.mtime = os.stat(cj_path).st_mtime
        d = os.path.dirname(cj_path)
        self.out_path = os.path.join(d, "board.handroute")
        self.legacy_path = os.path.join(d, "traces.json")
        self.hist_dir = os.path.join(d, "handroute-history")
        self.hist_last = 0.0
        self.base_name, self.proj_dir = project_name(cj_path)
        # What each net actually carries, if the board says so. Optional file, and it
        # lives beside the SOURCE (next to circuit.json, else the project dir found
        # above) rather than in dist/, which a rebuild wipes. Re-read on every /board
        # so you can rename a signal and just refresh the page.
        self.sig_dirs = [d, self.proj_dir]
        self.board = netmap.extract(cj_path)
        self.board["min_gap"] = 0.171          # proven floor; the UI warns below this
        self.board["default_width"] = 0.5
        # GND is a net like any other: it appears in the checklist, its ghost shows,
        # and completeness is required. Only the converter's --moat mode treats GND
        # as a pour, and that decision belongs there, not here. (Edson, 2026-08-22:
        # the board is the full-clear style, GND is drawn by hand.)
        self.board["pour_net"] = None
        self.board["project"] = self.base_name
        self.board["path"] = cj_path

    def stale(self):
        try:
            return os.stat(self.cj_path).st_mtime != self.mtime
        except OSError:
            return True

    def load_signals(self):
        empty = {"nets": {}, "pins": {}, "polarity": {}, "pins_legend": ""}
        for d0 in self.sig_dirs:
            f = os.path.join(d0, "signals.json")
            if os.path.exists(f):
                try:
                    raw = json.load(open(f))
                    return {"nets": raw.get("nets") or {},
                            "pins": raw.get("pins") or {},
                            "polarity": raw.get("polarity") or {},
                            "pins_legend": raw.get("pins_legend") or ""}
                except Exception as e:
                    print("signals.json ignored (%s): %s" % (f, e))
                    return empty
        return empty

    def payload(self):
        self.board["signals"] = self.load_signals()   # re-read: edit the file, refresh the page
        return self.board

    def traces(self):
        for p in (self.out_path, self.legacy_path):
            if os.path.exists(p):
                return open(p, "rb").read()
        return json.dumps({"strokes": []}).encode()

    def stroke_count(self):
        try:
            return len(json.loads(self.traces()).get("strokes", []))
        except ValueError:
            return 0

    def save(self, data, parsed):
        # The UI autosaves every stroke; a history snapshot per save would bury the
        # folder. At most one snapshot per minute still recovers any slip of the
        # Pencil, and the live file is always current.
        now = time.time()
        if now - self.hist_last > 60:
            self.hist_last = now
            os.makedirs(self.hist_dir, exist_ok=True)
            stamp = time.strftime("%Y%m%d-%H%M%S")
            open(os.path.join(self.hist_dir, "board-%s.handroute" % stamp), "wb").write(data)
        tmp = self.out_path + ".tmp"
        open(tmp, "wb").write(data)
        os.replace(tmp, self.out_path)
        return {"ok": True, "strokes": len(parsed["strokes"]),
                "moves": len(parsed.get("moves", {}))}

    def export(self, query):
        """Build a file for the burn session and hand it back as a download.

        The converter IS the verification: it refuses incomplete, shorted or
        unmanufacturable boards. So a refusal is not an error to swallow -
        it is the answer, and its whole log goes back to be read on screen.
        Returns (status, body, content-type, filename)."""
        kind = query.get("kind", ["lbrn"])[0]
        if kind == "handroute":
            path = self.out_path if os.path.exists(self.out_path) else self.legacy_path
            if not os.path.exists(path):
                return 404, json.dumps({"ok": False, "log": "nothing drawn yet"}), "application/json", None
            return 200, open(path, "rb").read(), "application/json", "%s.handroute" % self.base_name

        fit = kind == "fittest"
        tmpd = tempfile.mkdtemp(prefix="handroute-export-")
        suffix = "-FITTEST" if fit else ""
        out_file = os.path.join(tmpd, "%s%s.lbrn2" % (self.base_name, suffix))
        cmd = [sys.executable, os.path.join(HERE, "circuit2lbrn.py"), self.cj_path,
               "--manual-traces", "auto", "-o", out_file]
        if fit:
            cmd.append("--fit-test")
        else:
            # --clear is what the two working boards were cut with (V4 and
            # V5 both carry a populated CLEAR_1 and an empty ISOLATE).
            cmd.append("--moat" if query.get("mode", [""])[0] == "moat" else "--clear")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            return 500, json.dumps({"ok": False, "log": "the converter took over 5 minutes"}), "application/json", None
        log = (r.stdout or "") + (r.stderr or "")
        if r.returncode != 0 or not os.path.exists(out_file):
            return 422, json.dumps({"ok": False, "log": log,
                                    "cmd": " ".join(shlex.quote(c) for c in cmd)}), "application/json", None
        return 200, open(out_file, "rb").read(), "application/octet-stream", os.path.basename(out_file)


_cache = {"path": None, "board": None, "error": None}


def current_board():
    """The board the pointer names, parsed once and re-parsed when circuit.json
    changes (a `tsci build` shows up on the next page load)."""
    p = read_pointer()
    if p is None:
        _cache.update(path=None, board=None, error=None)
        return None
    b = _cache["board"]
    if b is not None and b.cj_path == p and not b.stale():
        return b
    try:
        b = Board(p)
        _cache.update(path=p, board=b, error=None)
        return b
    except Exception as e:
        _cache.update(path=p, board=None, error="%s: %s" % (type(e).__name__, e))
        print("cannot load %s: %s" % (p, _cache["error"]))
        return None


# ------------------------------------------------------------------ the pages

WAIT_PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Trilha">
<link rel="manifest" href="/manifest.webmanifest"><link rel="apple-touch-icon" href="/icon-180.png">
<title>Trilha</title>
<style>body{background:#1E1E1E;color:#fff;font:17px/1.5 Inter,-apple-system,sans-serif;max-width:640px;margin:0 auto;padding:60px 24px}
h1{font-size:26px;font-weight:600;margin:0 0 6px}p{color:#B3B3B3;margin:0 0 24px}
ul{list-style:none;padding:0;margin:0}li{margin:0 0 10px}
a.b{display:block;background:#2C2C2C;border:1px solid #383838;border-radius:14px;padding:14px 18px;color:#fff;text-decoration:none}
a.b small{display:block;color:#7A7A7A;font-size:12px;margin-top:2px;word-break:break-all}
.err{color:#E0705C}code{font:13px ui-monospace,Menlo,monospace;color:#B3B3B3}</style></head><body>
<h1>Trilha</h1>
%s
<ul>%s</ul>
<p style="margin-top:28px;font-size:14px">In a session: <code>open trilha on &lt;board&gt;</code>, or
<code>python3 studio/trilha/server.py &lt;path/to/circuit.json&gt;</code>.</p>
<script>document.querySelectorAll('a.b').forEach(a=>a.addEventListener('click',async e=>{e.preventDefault();
await fetch('/open?path='+encodeURIComponent(a.dataset.path),{method:'POST'});location.reload();}));</script>
</body></html>"""


def wait_page():
    err = _cache["error"]
    p = read_pointer()
    if err:
        head = '<p class="err">The current board cannot be loaded.<br><code>%s</code><br><code>%s</code></p>' % (
            html.escape(p or ""), html.escape(err))
    elif p:
        head = '<p class="err">The current board is gone: <code>%s</code></p>' % html.escape(p)
    else:
        head = "<p>No board is open. Tap one you worked on recently:</p>"
    items = "".join(
        '<li><a class="b" href="#" data-path="%s">%s<small>%s</small></a></li>' % (
            html.escape(r["path"], quote=True), html.escape(r.get("project", "board")),
            html.escape(r["path"]))
        for r in read_recents() if os.path.exists(r.get("path", "")))
    if not items:
        items = "<li><p>No recent boards yet.</p></li>"
    return WAIT_PAGE % (head, items)


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json", filename=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        if filename:
            self.send_header("Content-Disposition", 'attachment; filename="%s"' % filename)
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else body.encode())

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path in ("/", "/index.html"):
            b = current_board()
            if b is None:
                self._send(200, wait_page(), "text/html; charset=utf-8")
            else:
                self._send(200, open(os.path.join(HERE, "ui.html"), "rb").read(),
                           "text/html; charset=utf-8")
        elif u.path in ("/icon-180.png", "/manifest.webmanifest"):
            f = os.path.join(HERE, u.path.lstrip("/"))
            if os.path.exists(f):
                ctype = "image/png" if f.endswith(".png") else "application/manifest+json"
                self._send(200, open(f, "rb").read(), ctype)
            else:
                self._send(404, "{}")
        elif u.path == "/current":
            b = current_board()
            self._send(200, json.dumps({"path": read_pointer(), "project": b.base_name if b else None,
                                        "strokes": b.stroke_count() if b else None,
                                        "error": _cache["error"]}))
        elif u.path == "/recents":
            self._send(200, json.dumps(read_recents()))
        elif u.path == "/board":
            b = current_board()
            if b is None:
                self._send(503, json.dumps({"ok": False, "err": _cache["error"] or "no board open"}))
            else:
                self._send(200, json.dumps(b.payload()))
        elif u.path == "/export":
            b = current_board()
            if b is None:
                self._send(503, json.dumps({"ok": False, "log": "no board open"}))
            else:
                code, body, ctype, fn = b.export(q)
                self._send(code, body, ctype, filename=fn)
        elif u.path == "/traces":
            b = current_board()
            self._send(200, b.traces() if b else json.dumps({"strokes": []}))
        else:
            self._send(404, "{}")

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == "/open":
            # Same trust model as the rest: the studio Wi-Fi. Any existing circuit.json.
            try:
                p = set_pointer(q.get("path", [""])[0])
                self._send(200, json.dumps({"ok": True, "path": p}))
            except (OSError, ValueError) as e:
                self._send(400, json.dumps({"ok": False, "err": str(e)}))
            return
        if u.path != "/save":
            self._send(404, "{}")
            return
        b = current_board()
        if b is None:
            self._send(503, json.dumps({"ok": False, "err": "no board open"}))
            return
        n = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(n)
        try:
            parsed = json.loads(data)
            assert isinstance(parsed.get("strokes"), list)
            mv = parsed.get("moves", {})
            assert isinstance(mv, dict)
            for v in mv.values():
                assert isinstance(v, list) and len(v) == 2
        except Exception:
            self._send(400, json.dumps({"ok": False, "err": "bad payload"}))
            return
        self._send(200, json.dumps(b.save(data, parsed)))


# ------------------------------------------------------------------ main

def running_server(port):
    """The /current of a trilha server on this port, or None."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/current" % port, timeout=2) as r:
            return json.load(r)
    except (urllib.error.URLError, ValueError, OSError):
        return None


def main():
    args = list(sys.argv[1:])
    port = DEFAULT_PORT
    if "--port" in args:
        i = args.index("--port")
        port = int(args[i + 1])
        del args[i:i + 2]
    if args:
        cj = set_pointer(args[0])
        name, _ = project_name(cj)
        cur = running_server(port)
        if cur is not None:
            b = Board(cj)
            print("Trilha server already up on port %d: switched it to %s" % (port, name))
            print("  %s (%d strokes drawn)" % (cj, b.stroke_count()))
            print("  On the iPad:  http://%s:%d   (or http://%s:%d)" % (local_name(), port, lan_ip(), port))
            print("  On this Mac:  http://localhost:%d" % port)
            return
    elif running_server(port) is not None:
        sys.exit("a trilha server already answers on port %d" % port)

    srv = http.server.ThreadingHTTPServer(("0.0.0.0", port), H)
    b = current_board()
    print("Trilha server; current board: %s" % (b.cj_path if b else "none (%s)" % (_cache["error"] or "pointer empty")))
    if b:
        print("Saves to                : %s" % b.out_path)
    print("Board pointer           : %s" % POINTER)
    print()
    print("  On the iPad (same WiFi):  http://%s:%d   (or http://%s:%d)" % (local_name(), port, lan_ip(), port))
    print("  On this Mac           :  http://localhost:%d" % port)
    print()
    print("Ctrl-C to stop.")
    srv.serve_forever()


if __name__ == "__main__":
    main()
