#!/bin/zsh
# raio: http://localhost:8877/ — the board (board/server.py: the job on screen, frame + fire, the layers, the live box)
# + the plan and research as reading pages (jeitinho render.py).
# The iPad runner (studio/ipad, hub :8888) starts the board from login and restarts it if it dies; this script
# re-renders the docs and asks the runner for a restart (new code). Without the runner it starts the board by hand.
HERE="${0:A:h}"
cd "$HERE"
python3 "$HERE/../jeitinho/render.py" PLAN.md README.md research/*.md >/dev/null 2>&1
if curl -s -m 2 http://127.0.0.1:8888/status >/dev/null 2>&1; then
  # a board started by hand would keep the runner out: stop it, then let the runner own the port
  if curl -s -m 2 http://127.0.0.1:8888/status | python3 -c "import json,sys; t=[t for t in json.load(sys.stdin)['tools'] if t['id']=='raio']; sys.exit(0 if t and t[0]['state']=='external' else 1)"; then
    kill $(lsof -nP -t -iTCP:8877 -sTCP:LISTEN) 2>/dev/null; sleep 0.5
  fi
  curl -s -m 5 -X POST "http://127.0.0.1:8888/restart?id=raio" >/dev/null
  sleep 2
  echo "http://localhost:8877/ (iPad runner)"
  exit 0
fi
if lsof -nP -iTCP:8877 -sTCP:LISTEN >/dev/null 2>&1; then
  kill $(lsof -nP -t -iTCP:8877 -sTCP:LISTEN) 2>/dev/null; sleep 0.5
fi
mkdir -p "$HOME/.cache/studio-raio"
nohup python3 "$HERE/board/server.py" >/dev/null 2>"$HOME/.cache/studio-raio/server.err" &
sleep 1
echo "http://localhost:8877/ (by hand: the iPad runner is not up)"
