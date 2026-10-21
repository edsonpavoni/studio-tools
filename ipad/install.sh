#!/bin/zsh
# Installs the iPad tools runner: an app bundle (~/Applications/iPadTools.app) started by
# the LaunchAgent art.edsonpavoni.ipad at login and kept alive. The app runs
# supervisor.py (copied to ~/Library/Application Support/iPadTools/), which starts every
# tool in tools.json and serves the hub on port 8888. Safe to rerun: recompiles the stub
# only when iPadTools.swift changed (a recompile invalidates the app's privacy grant),
# always refreshes supervisor.py, reloads the agent.
# Undo: ./install.sh --uninstall
set -e
SRC=${0:A:h}
LABEL=art.edsonpavoni.ipad
APP="$HOME/Applications/iPadTools.app"
BIN="$APP/Contents/MacOS/iPadTools"
SUPPORT="$HOME/Library/Application Support/iPadTools"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG="$HOME/Library/Logs/ipad-tools.log"
DOMAIN=gui/$(id -u)

if [[ $1 == --uninstall ]]; then
  launchctl bootout $DOMAIN/$LABEL 2>/dev/null || true
  rm -f "$PLIST"; rm -rf "$APP" "$SUPPORT"
  echo "removed the agent, $APP and $SUPPORT (logs in ~/Library/Logs/ipad-*.log kept)"
  exit 0
fi

mkdir -p "$APP/Contents/MacOS" "$SUPPORT" "$HOME/Library/LaunchAgents"
HASH=$(shasum "$SRC/iPadTools.swift" | cut -d' ' -f1)
REBUILT=0
if [[ ! -x $BIN || $(cat "$SUPPORT/stub.sha" 2>/dev/null) != $HASH ]]; then
  swiftc -O "$SRC/iPadTools.swift" -o "$BIN"
  cat > "$APP/Contents/Info.plist" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleIdentifier</key><string>$LABEL</string>
  <key>CFBundleName</key><string>iPadTools</string>
  <key>CFBundleExecutable</key><string>iPadTools</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>LSUIElement</key><true/>
</dict></plist>
PL
  codesign --force -s - "$APP"
  echo $HASH > "$SUPPORT/stub.sha"
  REBUILT=1
fi
cp "$SRC/supervisor.py" "$SUPPORT/supervisor.py"

cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>$BIN</string></array>
  <key>EnvironmentVariables</key><dict>
    <key>IPAD_TOOLS</key><string>$SRC/tools.json</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>5</integer>
  <key>ProcessType</key><string>Interactive</string>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict></plist>
PL
plutil -lint "$PLIST" >/dev/null

launchctl bootout $DOMAIN/$LABEL 2>/dev/null || true
# Servers started by hand (a tool's serve.sh) hold their ports; stop them so the runner
# owns them from here on. Only python server.py processes from tools.json's folders.
python3 - "$SRC/tools.json" <<'PY'
import json, os, signal, subprocess, sys
cfg = json.load(open(sys.argv[1]))
for t in cfg["tools"]:
    pids = subprocess.run(["lsof", "-tnP", "-iTCP:%d" % t["port"], "-sTCP:LISTEN"],
                          capture_output=True, text=True).stdout.split()
    for pid in pids:
        cmd = subprocess.run(["ps", "-o", "command=", "-p", pid], capture_output=True, text=True).stdout
        if "server.py" in cmd:
            os.kill(int(pid), signal.SIGTERM)
            print("stopped hand-started %s server (pid %s)" % (t["id"], pid))
PY
sleep 1
launchctl bootstrap $DOMAIN "$PLIST"
# first start reads tools.json through Dropbox, which can take a few seconds
for i in {1..20}; do
  curl -sf -m 3 http://localhost:8888/status -o /tmp/ipad-status.json && break
  sleep 1
done
if [[ ! -s /tmp/ipad-status.json ]]; then
  echo "the runner did not come up in 20 s; see $LOG"; tail -5 "$LOG"; exit 1
fi
ACCESS=$(python3 -c 'import json;print(json.load(open("/tmp/ipad-status.json"))["access"])')
echo "runner up: http://localhost:8888  (iPad: http://$(scutil --get LocalHostName | tr 'A-Z' 'a-z').local:8888)"
if [[ $ACCESS != ok ]]; then
  echo
  echo "⚠️  It cannot read the Dropbox folder yet (access: $ACCESS). One time, on the Mac:"
  echo "   System Settings › Privacy & Security › Full Disk Access › + › Cmd+Shift+G › $APP › switch it on."
  echo "   Nothing to restart: the runner retries every 10 s and the hub page recovers by itself."
elif [[ $REBUILT == 1 ]]; then
  echo "stub recompiled: if the folder stops being readable, re-add $APP in Full Disk Access."
fi
