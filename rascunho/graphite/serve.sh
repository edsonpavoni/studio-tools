#!/bin/zsh
# Serve the graphite test page on the LAN (no cache) so the iPad can open it.
#   ./serve.sh            → http://localhost:8890/test/   and  http://edsons-macbook-pro.local:8890/test/
cd "$(dirname "$0")"
PORT=${1:-8890}
echo "graphite test page:"
echo "  Mac:   http://localhost:$PORT/test/"
echo "  iPad:  http://$(scutil --get LocalHostName).local:$PORT/test/"
exec python3 -c '
import http.server, sys
class H(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript", ".mjs": "text/javascript"}
    def end_headers(self):
        self.send_header("Cache-Control", "no-store"); super().end_headers()
    def log_message(self, *a): pass
http.server.ThreadingHTTPServer(("0.0.0.0", int(sys.argv[1])), H).serve_forever()
' "$PORT"
