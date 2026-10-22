#!/bin/zsh
# RaioEye: build ~/Applications/RaioEye.app (camera permission holder), copy cam.py out of Dropbox, install the LaunchAgent.
# Rerun after editing cam.py / config.json / index.html (copies only). The Swift stub is recompiled only when RaioEye.swift
# changed, because a new binary invalidates the camera grant (re-allow when macOS asks).
#   ./install.sh            install or update
#   ./install.sh --uninstall
set -e
HERE="${0:A:h}"
A="$HOME/Applications/RaioEye.app"
S="$HOME/Library/Application Support/RaioEye"
L="$HOME/Library/LaunchAgents/com.edsonpavoni.raio-eye.plist"
LABEL="com.edsonpavoni.raio-eye"

if [[ "$1" == "--uninstall" ]]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$L"; rm -rf "$A" "$S"
  echo "RaioEye removed (log ~/Library/Logs/raio-eye.log and frames ~/Library/Caches/raio kept)"; exit 0
fi

mkdir -p "$A/Contents/MacOS" "$A/Contents/Resources" "$S" "$HOME/Library/Caches/raio/snaps"
BIN="$A/Contents/MacOS/RaioEye"
if [[ ! -x "$BIN" || "$HERE/RaioEye.swift" -nt "$BIN" ]]; then
  echo "compiling RaioEye.swift (the camera grant will be asked again)"
  swiftc -O "$HERE/RaioEye.swift" -o "$BIN"
  cat > "$A/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleExecutable</key><string>RaioEye</string>
  <key>CFBundleIdentifier</key><string>com.edsonpavoni.raio-eye</string>
  <key>CFBundleName</key><string>RaioEye</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>0.1</string>
  <key>LSUIElement</key><true/>
  <key>NSCameraUsageDescription</key><string>Raio looks at the laser bed before a job, and after it.</string>
</dict></plist>
EOF
  codesign --force --sign - "$A"
else
  echo "stub unchanged (grant kept)"
fi

# the server and its page, copied out of Dropbox (a login app may not read CloudStorage)
cp "$HERE/cam.py" "$S/cam.py"
[[ -f "$S/config.json" ]] || cp "$HERE/config.json" "$S/config.json"     # the installed config is the live one; never overwritten
cp "$HERE/index.html" "$S/index.html" 2>/dev/null || true
cp "$HERE/studio.css" "$S/studio.css" 2>/dev/null || true

cat > "$L" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>$BIN</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ProcessType</key><string>Interactive</string>
</dict></plist>
EOF
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
for i in 1 2 3 4 5; do launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || break; sleep 1; done   # wait for the bootout
pkill -f "RaioEye/cam.py serve" 2>/dev/null || true                                                   # no orphan may keep the port
sleep 1
for i in 1 2 3 4 5; do launchctl bootstrap "gui/$(id -u)" "$L" 2>/dev/null && break; sleep 1; done
launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || { echo "LaunchAgent did not load"; exit 1; }
launchctl kickstart -k "gui/$(id -u)/$LABEL"
sleep 3
echo "RaioEye: $(launchctl print gui/$(id -u)/$LABEL 2>/dev/null | grep -E '^\s*state' | head -1)"
curl -s --max-time 3 "http://127.0.0.1:8878/state.json" || echo "(server not answering yet; tail -f ~/Library/Logs/raio-eye.log)"
echo
echo "http://localhost:8878/"
