#!/bin/zsh
# Renders the Markdown docs to HTML and serves this folder on http://localhost:8880
# then starts server.py on port 8880 (the app server; see README → Server).
cd "$(dirname "$0")" || exit 1
CSS='<style>:root{color-scheme:light dark}body{max-width:860px;margin:40px auto;padding:0 20px;font:16px/1.55 -apple-system,Helvetica,sans-serif;color:#222;background:#fff}pre,code{font-size:13px}pre{background:#f4f4f4;padding:12px;overflow:auto}table{border-collapse:collapse}td,th{border:1px solid #ddd;padding:6px 8px;vertical-align:top}th{background:#f4f4f4}a{color:#1a5fb4}@media (prefers-color-scheme:dark){body{color:#e6e6e6;background:#1c1c1e}pre,th{background:#2a2a2d}td,th{border-color:#444}a{color:#8ab4f8}}</style>'
for f in HANDOFF.md PLAN.md README.md design/UI-SPEC.md research/*.md; do
  pandoc -s --from gfm --to html5 --metadata pagetitle="$(head -1 "$f" | sed 's/^# //')" "$f" -o "${f%.md}.html" 2>/dev/null
  # inject the small stylesheet
  python3 - "${f%.md}.html" "$CSS" <<'EOF'
import sys
p, css = sys.argv[1], sys.argv[2]
s = open(p).read()
if css not in s:
    s = s.replace("</head>", css + "</head>", 1)
    open(p, "w").write(s)
EOF
done
# the app server (static files + /sessions + /send + sheet tiles), one instance on 8880
if lsof -nP -iTCP:8880 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "port 8880 already in use (server.py running?) — not starting another"
else
  nohup python3 "$(pwd)/server.py" --port 8880 >> "$(pwd)/server.log" 2>&1 &
  sleep 1
fi
echo "http://localhost:8880/            (iPad: http://edsons-macbook-pro.local:8880)"
echo "http://localhost:8880/PLAN.html"
