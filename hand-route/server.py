#!/usr/bin/env python3
"""
server.py — serve the hand-routing UI to the iPad.

    python3 server.py /path/to/dist/index/circuit.json

Then open the printed URL in Safari on the iPad (same WiFi). Draw with the Pencil,
pan and zoom with fingers. Every save writes board.handroute NEXT TO the
circuit.json (strokes + component moves), which is where the converter looks:

    python3 circuit2lbrn.py circuit.json --manual-traces auto --moat -o board.lbrn2

A legacy traces.json (pre-2026-08-25 boards) is read if no .handroute file exists
yet; the first save migrates it. Pure standard library, no installs. Saves are
atomic and every save also writes a timestamped copy under handroute-history/ so
a slip of the Pencil can't destroy an afternoon of drawing.
"""

import http.server
import json
import os
import shlex
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse

import netmap

HERE = os.path.dirname(os.path.abspath(__file__))


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    args = list(sys.argv[1:])
    port = 8477
    if "--port" in args:
        i = args.index("--port")
        port = int(args[i + 1])
        del args[i:i + 2]
    if not args:
        sys.exit(__doc__)
    cj_path = os.path.abspath(args[0])
    out_path = os.path.join(os.path.dirname(cj_path), "board.handroute")
    legacy_path = os.path.join(os.path.dirname(cj_path), "traces.json")
    hist_dir = os.path.join(os.path.dirname(cj_path), "handroute-history")

    hist_last = {"t": 0.0}
    # Name exports after the PROJECT, walking up past the build folders. A file
    # called "index.lbrn2" or "dist.lbrn2" is unrecognisable in a Downloads list
    # a week later; "pcb-v3.lbrn2" is the board you cut.
    base_name = "board"
    d = os.path.dirname(cj_path)
    while d and d != "/":
        nm = os.path.basename(d)
        if nm and nm.lower() not in ("index", "dist", "build", "out", "output"):
            base_name = nm
            break
        d = os.path.dirname(d)
    board = netmap.extract(cj_path)
    board["min_gap"] = 0.171          # proven floor; the UI warns below this
    board["default_width"] = 0.5
    # GND is a net like any other: it appears in the checklist, its ghost shows,
    # and completeness is required. Only the converter's --moat mode treats GND
    # as a pour, and that decision belongs there, not here. (Edson, 2026-08-22:
    # the board is the full-clear style, GND is drawn by hand.)
    board["pour_net"] = None

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="application/json", filename=None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            if filename:
                self.send_header("Content-Disposition",
                                 'attachment; filename="%s"' % filename)
            self.end_headers()
            self.wfile.write(body if isinstance(body, bytes) else body.encode())

        def _export(self, query):
            """Build a file for the burn session and hand it back as a download.

            The converter IS the verification: it refuses incomplete, shorted or
            unmanufacturable boards. So a refusal is not an error to swallow -
            it is the answer, and its whole log goes back to be read on screen."""
            kind = query.get("kind", ["lbrn"])[0]
            if kind == "handroute":
                path = out_path if os.path.exists(out_path) else legacy_path
                if not os.path.exists(path):
                    self._send(404, json.dumps({"ok": False,
                                                "log": "nothing drawn yet"}))
                    return
                self._send(200, open(path, "rb").read(), "application/json",
                           filename="%s.handroute" % base_name)
                return

            fit = kind == "fittest"
            tmpd = tempfile.mkdtemp(prefix="handroute-export-")
            suffix = "-FITTEST" if fit else ""
            out_file = os.path.join(tmpd, "%s%s.lbrn2" % (base_name, suffix))
            cmd = [sys.executable, os.path.join(HERE, "circuit2lbrn.py"), cj_path,
                   "--manual-traces", "auto", "-o", out_file]
            if fit:
                cmd.append("--fit-test")
            else:
                # --clear is what the two working boards were cut with (V4 and
                # V5 both carry a populated CLEAR_1 and an empty ISOLATE).
                cmd.append("--moat" if query.get("mode", [""])[0] == "moat"
                           else "--clear")
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            except subprocess.TimeoutExpired:
                self._send(500, json.dumps({"ok": False,
                                            "log": "the converter took over 5 minutes"}))
                return
            log = (r.stdout or "") + (r.stderr or "")
            if r.returncode != 0 or not os.path.exists(out_file):
                self._send(422, json.dumps({"ok": False, "log": log,
                                            "cmd": " ".join(shlex.quote(c) for c in cmd)}))
                return
            self._send(200, open(out_file, "rb").read(),
                       "application/octet-stream",
                       filename=os.path.basename(out_file))

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._send(200, open(os.path.join(HERE, "ui.html"), "rb").read(),
                           "text/html; charset=utf-8")
            elif self.path == "/board":
                self._send(200, json.dumps(board))
            elif self.path.startswith("/export"):
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                self._export(q)
            elif self.path == "/traces":
                if os.path.exists(out_path):
                    self._send(200, open(out_path, "rb").read())
                elif os.path.exists(legacy_path):
                    self._send(200, open(legacy_path, "rb").read())
                else:
                    self._send(200, json.dumps({"strokes": []}))
            else:
                self._send(404, "{}")

        def do_POST(self):
            if self.path != "/save":
                self._send(404, "{}")
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
            # The UI autosaves every stroke; a history snapshot per save would
            # bury the folder. At most one snapshot per minute still recovers
            # any slip of the Pencil, and the live file is always current.
            now = time.time()
            if now - hist_last["t"] > 60:
                hist_last["t"] = now
                os.makedirs(hist_dir, exist_ok=True)
                stamp = time.strftime("%Y%m%d-%H%M%S")
                open(os.path.join(hist_dir, "board-%s.handroute" % stamp), "wb").write(data)
            tmp = out_path + ".tmp"
            open(tmp, "wb").write(data)
            os.replace(tmp, out_path)
            self._send(200, json.dumps({"ok": True,
                                        "strokes": len(parsed["strokes"]),
                                        "moves": len(parsed.get("moves", {}))}))

    srv = http.server.ThreadingHTTPServer(("0.0.0.0", port), H)
    print("Hand-route server for: %s" % cj_path)
    print("Saves to             : %s" % out_path)
    print()
    print("  On the iPad (same WiFi):  http://%s:%d" % (lan_ip(), port))
    print("  On this Mac           :  http://localhost:%d" % port)
    print()
    print("Ctrl-C to stop.")
    srv.serve_forever()


if __name__ == "__main__":
    main()
