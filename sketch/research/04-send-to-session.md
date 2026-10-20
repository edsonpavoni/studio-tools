# Sending an iPad drawing into a named, running Claude Code session — findings

Scope: read-only investigation on this Mac (Claude Code 2.1.304, Superset 1.38.0) plus the official docs at code.claude.com. Nothing under `~/.claude` was modified.

## 1. Where session names live, and what a running session exposes

**Live registry (the one to use):** `~/.claude/sessions/<pid>.json`, one file per running process. Example for the session Edson renamed today:

```
{"pid":18992,"sessionId":"e414e144-199b-4cd3-8328-2fc25413c75a",
 "cwd":"/Users/edsonpavoni/Library/CloudStorage/Dropbox/0000 AI",
 "kind":"interactive","status":"idle","version":"2.1.304",
 "messagingSocketPath":"/tmp/cc-socks/18992.sock",
 "name":"today","nameSource":"user","nameSince":1792519685445,
 "formerNames":[{"name":"daily-priorities-triage","until":1792519678167,...}]}
```

`nameSource` is `"user"` after `/rename` or `--name`, `"derived"` otherwise (derived names like `0000-ai-20` are auto-generated and **collide**). Right now the user-named sessions are `today`, `book`, `oracle`. A sibling `<pid>.<hash>.key` holds a `peerToken`. `claude agents --json` prints the same list officially (pid, sessionId, name, status).

**Persisted copy:** `~/.claude/projects/<project-dir>/<sessionId>/custom-title.json` (`{"customTitle":"today"}`) and a `{"type":"custom-title",...}` line in the transcript jsonl.

**Name → socket:** read every `~/.claude/sessions/*.json`, pick `name == <wanted> && nameSource == "user"`, check the pid is alive (`kill -0`) and `messagingSocketPath` exists. That is exactly what `ListAgents`/`SendMessage` use.

**What a running session exposes:** a Unix domain socket `/tmp/cc-socks/<pid>.sock` (owner-only), newline-delimited JSON. Documented in "The session's inbox socket" at code.claude.com/docs/en/cross-session-messaging ("when you want a script or hook to post into a session"). Wire format:

- optional first line `{"type":"auth","token":"<CLAUDE_CODE_MESSAGING_TOKEN>"}` — optional on macOS;
- message line `{"type":"user","message":{"content":"<text>"},"from":"<reply address>","msg_id":"<id>","priority":"next"}`;
- `{"type":"control","action":"rename"|"notify_when_idle"|"peer_message_status",...}` for other actions.

The receiver queues the text as a prompt with `skipAttachments: true` — an `@path` attaches nothing; Claude must `Read` the file itself. Delivery: idle session → starts a new turn immediately; busy session → read between tool calls. The connection must send a complete line within 30 s.

**The one gate that matters:** every interactive session here runs with bypassed permissions. A bypass-mode receiver **holds** a cross-session message and shows an approval dialog that expires after 5 min. Fix is one line in `~/.claude/settings.json`: `"crossSessionInbound": "accept"` (not currently set). With it, delivery is unattended.

No other IPC: the socket is the only inbound channel.

## 2. Official CLI / docs

- `claude --help` (2.1.304): no `send`/`message` subcommand. `-n/--name` and `/rename` set names; `--resume <name>` resolves them. `--bg` sessions accept a prompt via `claude --resume <bg-session> "text"`, but Edson's sessions are interactive terminals.
- `claude -p --resume <id>` on an interactive session: not an injection; messages interleave into one transcript and the live session never sees it. Avoid.
- Remote Control: outbound-only relay through claude.ai; no local API to post into a session by name.
- Channels: the official "push external events into a running session" feature, but research preview, allowlisted plugins, and every session must be restarted with `--channels`. Heavy.
- `RemoteTrigger`: manages cloud scheduled tasks. Unrelated.
- Hooks: `FileChanged` cannot start a turn. `UserPromptSubmit` can inject text (no images) at the next prompt. Existing hooks: `UserPromptSubmit` → timestamp + heic2jpg; `Stop` → voice speak hook; Superset's notify.sh.

## 3. Monitor tool, and the claude-shot precedent

**Monitor**: per-session, a shell command whose stdout lines become events; max 30 min, must be re-armed; not restored on resume. An inbox-folder design works but Edson must ask each session to arm it, and it lapses every 30 min. Fine as opt-in, not as default.

**claude-shot**: a launchd Swift app that runs `screencapture`, puts the path on the clipboard, re-activates the frontmost app, posts Cmd+V. Targets **only the frontmost app**; no session targeting.

**Which terminal:** 21 interactive `claude` processes; 18 under Superset's pty-daemon, 3 under a zellij server. No VS Code hosts any session today. Targeting a Superset pane by keystroke would be fragile.

## 4. Superset route

`superset terminals send --local --workspace <id> --terminal <id> --text "..." [--no-submit]` types text into a named terminal's pty, no focus needed. Claude session → terminal mapping lives in `~/.superset/host/<host-id>/host.db`, table `terminal_agent_bindings(terminal_id, workspace_id, agent_session_id, ...)` (confirmed for `today`). Limits: Superset-hosted sessions only; whether pty-typed text gets the `[Image #N]` treatment is **unconfirmed**; the safe payload is "Read <path>".

## Ranking

1. **Inbox socket (official, every session, no arming)** — best.
2. **Superset `terminals send`** — clean fallback, Superset-only.
3. Inbox folder + Monitor — opt-in only (re-arm every 30 min).
4. claude-shot-style keystroke — frontmost only, no targeting.
5. `claude -p --resume` (unsafe), channels (restart everything), Remote Control (no local API), hooks (passive).

### Design A (recommended): socket post
- Sketch server saves `studio/<tool>/inbox/<session-name>/sketch-YYYY-MM-DD_HH-MM-SS.png` (keep history, like claude-shot's `shots/`).
- Resolve name: scan `~/.claude/sessions/*.json` for `name==X && nameSource=="user"`, pid alive, socket present; the iPad picker list comes from the same scan.
- Connect to `messagingSocketPath`, write one line: `{"type":"user","message":{"content":"New iPad sketch: <abs path>\nRead it and treat it as my drawing for the current work."},"from":"sketch-server","msg_id":"<uuid>","priority":"next"}` + `\n`, close.
- One-time: `"crossSessionInbound": "accept"` in `~/.claude/settings.json` (else a 5-minute approval dialog per drawing).
- What the session sees: a dim `› Message from …` line; Claude starts a turn (if idle), `Read`s the PNG (Read renders images), continues. Unverified until tried: whether a non-`uds:` `from` string is accepted. Test first on a throwaway session.

### Design B: Superset typed prompt
- Same inbox file. name → sessionId → `sqlite3 -readonly host.db` → `superset terminals send --local --workspace … --terminal … --text "Read <path> — my new iPad sketch"`.
- No settings change; appears in the pane as if Edson typed it. Fails for non-Superset sessions.
