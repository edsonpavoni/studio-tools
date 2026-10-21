#!/bin/zsh
# Run the runner by hand (no launchd): same hub on 8888, same tools.json. Use install.sh
# for always-on. Harmless if the agent already runs: the hub port is simply busy.
cd "$(dirname "$0")" || exit 1
if lsof -nP -iTCP:8888 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "port 8888 already answers (the agent?): http://localhost:8888"; exit 0
fi
nohup python3 "$(pwd)/supervisor.py" "$(pwd)/tools.json" >> "$HOME/Library/Logs/ipad-tools.log" 2>&1 &
sleep 1; echo "http://localhost:8888   (iPad: http://edsons-macbook-pro.local:8888)"
