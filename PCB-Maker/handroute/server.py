#!/usr/bin/env python3
"""
server.py — serve the hand-routing UI to the iPad.

    python3 server.py /path/to/dist/index/circuit.json

Then open the printed URL in Safari on the iPad (same WiFi). Draw with the Pencil,
pan and zoom with fingers. Every save writes traces.json NEXT TO the circuit.json,
which is where the converter looks for it:

    python3 circuit2lbrn.py circuit.json --manual-traces auto --moat -o board.lbrn2

Pure standard library, no installs. Saves are atomic and every save also writes a
timestamped copy under traces-history/ so a slip of the Pencil can't destroy an
afternoon of drawing.
"""

import http.server
import json
import os
import socket
import sys
import time

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
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cj_path = os.path.abspath(sys.argv[1])
    out_path = os.path.join(os.path.dirname(cj_path), "traces.json")
    hist_dir = os.path.join(os.path.dirname(cj_path), "traces-history")

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

        def _send(self, code, body, ctype="application/json"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body if isinstance(body, bytes) else body.encode())

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._send(200, open(os.path.join(HERE, "ui.html"), "rb").read(),
                           "text/html; charset=utf-8")
            elif self.path == "/board":
                self._send(200, json.dumps(board))
            elif self.path == "/traces":
                if os.path.exists(out_path):
                    self._send(200, open(out_path, "rb").read())
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
            except Exception:
                self._send(400, json.dumps({"ok": False, "err": "bad payload"}))
                return
            os.makedirs(hist_dir, exist_ok=True)
            stamp = time.strftime("%Y%m%d-%H%M%S")
            open(os.path.join(hist_dir, "traces-%s.json" % stamp), "wb").write(data)
            tmp = out_path + ".tmp"
            open(tmp, "wb").write(data)
            os.replace(tmp, out_path)
            self._send(200, json.dumps({"ok": True,
                                        "strokes": len(parsed["strokes"])}))

    port = 8477
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
