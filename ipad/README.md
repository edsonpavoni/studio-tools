# ipad 📱

**Use when:** you pick up the iPad and want to draw (rascunho) or route a board (trilha) without opening a terminal or asking a session to start anything. One app on the Mac keeps every iPad tool running from login, restarts one that dies, and serves a hub page that is the one icon that always works.

**Status 2026-10-20, 22:05: installed and running.** `art.edsonpavoni.ipad` (LaunchAgent) → `~/Applications/iPadTools.app` → `supervisor.py` → rascunho on 8880 and trilha (hand-route until tonight) on 8481; hub on **8888**. Verified from launchd: the servers list and write inside Dropbox, the iPad reconnected to rascunho by itself, the hub answers on the LAN, restart from the hub works.

## On the iPad

| Icon | Address | What |
|---|---|---|
| **Tools** (hub) | http://edsons-macbook-pro.local:8888 | Every iPad tool as a tile, green when it answers. Tap to open; *restart* on a tile if one is stuck. |
| **Rascunho** | http://edsons-macbook-pro.local:8880 | Graphite on the iPad → a Claude Code session. `studio/rascunho/README.md`. |
| **Trilha** | http://edsons-macbook-pro.local:8481 | Hand-route the board a session last opened (hand-route until 2026-10-20). `studio/trilha/README.md`. |

Each one: open the address in Safari, Share › **Add to Home Screen** › Add. The icon opens full screen (every page ships the Apple meta tags, a manifest and `icon-180.png`). Fallback when `.local` does not resolve (venue Wi-Fi with client isolation): the Mac's LAN IP, shown on the hub.

**The Mac must be awake, on the same Wi-Fi.** On power with the lid open it never sleeps (pmset `sleep 0` on AC). Lid closed: Amphetamine (installed) › Quick Settings › untick *Allow closed-display sleep*, and keep a session running while on AC. On battery the Mac sleeps after a minute and the tools go with it.

## How it runs

```
launchd  art.edsonpavoni.ipad  (RunAtLoad, KeepAlive)
  └─ ~/Applications/iPadTools.app/Contents/MacOS/iPadTools      Swift stub, 20 lines
       └─ python3 ~/Library/Application Support/iPadTools/supervisor.py   copy of ./supervisor.py
            ├─ reads  studio/ipad/tools.json          (re-read when it changes)
            ├─ runs   studio/rascunho/server.py --port 8880   log ~/Library/Logs/ipad-rascunho.log
            ├─ runs   studio/trilha/server.py --port 8481 log ~/Library/Logs/ipad-trilha.log
            └─ serves the hub on 8888 from this folder (index.html, /status, /restart, /log)
```

**Why an app bundle and not a plain LaunchAgent.** macOS gates `~/Library/CloudStorage` (Dropbox) with a per-app permission, *Files and Folders › Dropbox* (`kTCCServiceFileProviderDomain`), not with Full Disk Access. A launchd job that is just `/bin/zsh` or `python3` can never hold it (the `/bin/zsh` Full Disk Access attempt of 2026-10-20 never even registered in the privacy database, and `ls` inside Dropbox from such a job dies with `operation not permitted`). An app bundle with its own identifier gets it, and the grant covers every process it starts, the way Terminal's grant covers what you run in it. The privacy database shows `art.edsonpavoni.ipad` allowed at 22:00:04, the second the runner first read `tools.json`. If macOS ever asks *"iPadTools would like to access files in Dropbox"*, answer Allow. Same pattern as `claude-shot` and `voice` (OracleEars.app).

The Swift stub never changes when `supervisor.py` changes, so updates keep the grant. `install.sh` only recompiles the stub when `iPadTools.swift` changed, and says so, because that invalidates the grant (re-allow when asked, or re-add the app under System Settings › Privacy & Security › Files and Folders / Full Disk Access).

## Files

| File | What |
|---|---|
| `tools.json` | **The registry of iPad tools.** `hub_port` and one entry per tool: `id`, `name`, `emoji`, `what` (one sentence for the tile), `dir` (relative to this folder), `cmd`, `port`, `path`. Edit, save: the runner picks it up within 10 s, starts new tools, stops removed ones, restarts a changed one. |
| `supervisor.py` | The runner and the hub server. Stdlib only. `python3 supervisor.py [tools.json]` runs it by hand. |
| `index.html` · `manifest.webmanifest` · `icon-180.png` | The hub page. Links are built from the address the iPad used (`.local` or IP), so they always point back at the same Mac. |
| `iPadTools.swift` | The app stub (see above). |
| `install.sh` | Builds the app, copies `supervisor.py`, writes the LaunchAgent, stops hand-started servers on the tools' ports so the runner owns them, loads the agent, prints the result. Rerun after editing `supervisor.py`. `./install.sh --uninstall` removes everything (logs stay). |
| `serve.sh` | The runner by hand, without launchd, same ports. For a Mac where the agent is not installed. |
| `make_icons.py` | Draws `icon-180.png` here and in `../trilha/` (pure stdlib). |

## Adding an iPad tool

1. The tool serves on a fixed port, bound to `0.0.0.0`, from its own folder in `studio/`, with the Apple meta tags + a manifest + `icon-180.png` in its page (copy the head of `trilha/ui.html`).
2. Add its entry to `tools.json`. Done: the runner starts it, the hub shows it.
3. Add it to the table above and to the `/tools` list.

A tool started by hand (`serve.sh` in its folder) while the runner is up shows as **blue / started by hand** on the hub: the runner leaves it alone and takes over the next time the port is free.

## Check, logs, undo

```bash
curl -s localhost:8888/status | python3 -m json.tool          # access, host, every tool's state
launchctl print gui/$(id -u)/art.edsonpavoni.ipad | grep -E "state|pid"
tail -f ~/Library/Logs/ipad-tools.log                           # the runner
tail -f ~/Library/Logs/ipad-rascunho.log ~/Library/Logs/ipad-trilha.log
curl -X POST "localhost:8888/restart?id=trilha"             # what the hub's button does
"/Users/edsonpavoni/Library/CloudStorage/Dropbox/0000 AI/studio/ipad/install.sh" --uninstall
```

The runner itself: `launchctl kickstart -k gui/$(id -u)/art.edsonpavoni.ipad` restarts it (and, through it, every tool).

**Trust model: the studio Wi-Fi.** No authentication anywhere, like the tools themselves; the hub can restart a tool and trilha accepts a board path. Keep it on a network you trust (the travel router counts).

## Not done / ideas

- **Away from the studio network.** Tailscale on Mac + iPad would give the same tools stable `https://…ts.net` addresses from anywhere (and a secure origin, so a service worker could cache the pages). Not installed; the travel router covers venues.
- **Waking the Mac from the iPad.** Possible with Bonjour Sleep Proxy (needs an Apple TV / HomePod on the network and the servers registered with `dns-sd`). Not worth it while "plugged in + Amphetamine" works.
- Shorter addresses: `sudo scutil --set LocalHostName studio` would make every URL `http://studio.local:…`. Edson's call; the hub, rascunho and hand-route all print whatever the name is.
