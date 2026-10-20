#!/bin/zsh
# Installs the sketch server as an always-on LaunchAgent (port 8880).
# Safe to rerun: rewrites the plist, unloads the old job, loads the new one.
# Undo: see README -> Always on.
# launchd itself may not open paths under ~/Library/CloudStorage (it exits
# EX_CONFIG), so no WorkingDirectory/StandardOutPath key points into Dropbox:
# zsh cd's into this folder (passed as $0, so the space in the path is safe)
# and appends to server.log itself. launchd's own output: ~/Library/Logs/sketch-launchd.log
set -e
DIR=${0:A:h}
LABEL=art.edsonpavoni.sketch
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG="$DIR/server.log"
DOMAIN=gui/$(id -u)

mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array>
    <string>/bin/zsh</string><string>-c</string>
    <string>cd "\$0" &amp;&amp; exec /usr/bin/env python3 server.py --port 8880 &gt;&gt; server.log 2&gt;&amp;1</string>
    <string>$DIR</string>
  </array>
  <key>EnvironmentVariables</key><dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>PYTHONUNBUFFERED</key><string>1</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>5</integer>
  <key>StandardOutPath</key><string>$HOME/Library/Logs/sketch-launchd.log</string>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/sketch-launchd.log</string>
</dict></plist>
PL
plutil -lint "$PLIST" >/dev/null

launchctl bootout $DOMAIN/$LABEL 2>/dev/null || true
# a server.py started by hand (serve.sh) would hold the port: stop it
for pid in $(lsof -tnP -iTCP:8880 -sTCP:LISTEN 2>/dev/null); do
  [[ $(ps -o command= -p $pid) == *server.py* ]] && kill $pid && echo "stopped hand-started server.py ($pid)"
done
sleep 1
launchctl bootstrap $DOMAIN "$PLIST"
sleep 2
if curl -sf -o /dev/null http://localhost:8880/sessions; then
  echo "sketch server running under launchd: http://localhost:8880 (iPad: http://edsons-macbook-pro.local:8880)"
  exit 0
fi
# failed: unload + remove the plist (no respawn loop, not even at next login) and
# bring the hand-started server back
launchctl bootout $DOMAIN/$LABEL 2>/dev/null || true
rm -f "$PLIST"
if grep -qiE "operation not permitted|deadlock" "$HOME/Library/Logs/sketch-launchd.log" 2>/dev/null; then
  echo "launchd jobs may not touch Dropbox (~/Library/CloudStorage) yet."
  echo "One-time grant: System Settings > Privacy & Security > Full Disk Access > + > /bin/zsh"
  echo "(Cmd+Shift+G in the file picker, type /bin/zsh), then rerun this script."
else
  echo "did not start; see ~/Library/Logs/sketch-launchd.log and $LOG"
fi
nohup /usr/bin/env python3 "$DIR/server.py" --port 8880 >> "$LOG" 2>&1 < /dev/null &
echo "started server.py by hand instead (pid $!), as before."
exit 1
