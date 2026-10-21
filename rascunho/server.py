#!/usr/bin/env python3
"""rascunho server: serves the iPad page, saves drawings, posts them into a named Claude Code session,
watches for the session reading them, and carries replies from sessions back to the iPad.

    python3 server.py [--port 8880]

Routes
  GET  /                          index.html (and any other static file in this folder)
  GET  /sessions[?all=1]          running Claude Code sessions (user-named only unless all=1)
  POST /send                      PNG body; headers X-Session (required), X-Note, X-Sheet (optional)
                                  -> inbox/<session>/rascunho-<stamp>.png, one line into the session's socket
  GET  /send-status?id=           one send: {..., "delivered", "seen": time or null}
  GET  /sends[?limit=20]          recent sends, newest first (from inbox/log.jsonl)
  POST /reply                     JSON {"from", "sheet", "text", "image"}: a session answering the iPad
  GET  /replies[?limit=20]        recent replies, newest first
  GET  /events?since=<seq>        long-poll (<= 25 s): events after seq: sent / seen / reply
  POST /tile?sheet=&tx=&ty=       PNG body -> sheets/<sheet>/<tx>_<ty>.png
  GET  /tile?sheet=&tx=&ty=       that PNG (404 if missing)
  DELETE /tile?sheet=&tx=&ty=     remove one tile
  GET  /sheet?sheet=              {"tiles": [[tx, ty], ...], "updated": mtime, "name", "thumb"}
  GET  /sheets                    [{"id", "name", "tiles", "updated", "thumb"}, ...], newest first
  POST /thumb?sheet=              PNG body -> sheets/<sheet>/thumb.png (served at /sheets/<sheet>/thumb.png)
  POST /sheet-meta?sheet=         JSON {"name": "..."} -> sheets/<sheet>/meta.json
  DELETE /sheet?sheet=            moves the sheet to sheets/_trash/
  POST /underlay[?sheet=]         PNG/JPEG body (headers X-From, X-Note): a picture to draw over.
                                  -> sheets/<sheet>/underlay.png|jpg (a new sheet unless sheet= is given),
                                  pushes an "underlay" event so the iPad opens it

Python 3 stdlib only.
"""
import argparse
import json
import os
import re
import shutil
import socket
import sys
import threading
import time
import uuid
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

TOOL_DIR = Path(__file__).resolve().parent
INBOX_DIR = TOOL_DIR / "inbox"
SHEETS_DIR = TOOL_DIR / "sheets"
REPLIES_DIR = TOOL_DIR / "replies"
LOG_PATH = INBOX_DIR / "log.jsonl"
SESSIONS_DIR = Path.home() / ".claude" / "sessions"
PROJECTS_DIR = Path.home() / ".claude" / "projects"
REPLY_SCRIPT = TOOL_DIR / "tools" / "reply.py"
MAX_BODY = 64 * 1024 * 1024
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"
TILE_RE = re.compile(r"^(-?\d+)_(-?\d+)_([0-9a-f]{6})\.png$")   # tx_ty_<colour hex>.png, one density layer per colour
IMAGE_ROOTS = (Path.home(), Path("/tmp"), Path("/private/tmp"))   # where /reply may read an image from
SEEN_WATCH_SECONDS = 15 * 60
LONG_POLL_SECONDS = 25


def sanitize(name):
    """Keep [A-Za-z0-9._-]; anything else becomes '_'. Empty or dot-only names are rejected."""
    clean = re.sub(r"[^A-Za-z0-9._-]", "_", (name or "").strip())[:80]
    if not clean or set(clean) <= {"."}:
        raise ValueError("bad name")
    return clean


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def stamp():
    return f"{datetime.now():%Y-%m-%d_%H-%M-%S}"


# ---------------------------------------------------------------- events (long-poll bus)

class EventBus:
    """In-memory list of events with a growing seq; clients long-poll /events?since=seq."""

    def __init__(self, keep=200):
        self.events, self.seq, self.keep = [], 0, keep
        self.cond = threading.Condition()

    def push(self, event):
        with self.cond:
            self.seq += 1
            event = {"seq": self.seq, "time": now_iso(), **event}
            self.events.append(event)
            del self.events[:-self.keep]
            self.cond.notify_all()
        return event

    def after(self, since, timeout):
        with self.cond:
            if since > self.seq:          # the server restarted since the client last polled: resync, don't wait
                return [], self.seq
            deadline = time.monotonic() + timeout
            while True:
                fresh = [e for e in self.events if e["seq"] > since]
                if fresh or timeout <= 0:
                    return fresh, self.seq
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return [], self.seq
                self.cond.wait(remaining)


BUS = EventBus()


# ---------------------------------------------------------------- sessions

def list_sessions(include_derived=False):
    """Running interactive Claude Code sessions from ~/.claude/sessions/*.json."""
    found = []
    for path in sorted(SESSIONS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text())
            pid = int(data["pid"])
            sock = data.get("messagingSocketPath") or ""
            if data.get("kind") != "interactive" or not sock:
                continue
            os.kill(pid, 0)  # raises if the process is gone
            if not os.path.exists(sock):
                continue
            source = data.get("nameSource", "derived")
            if source != "user" and not include_derived:
                continue
            found.append({
                "name": data.get("name") or "",
                "pid": pid,
                "sessionId": data.get("sessionId", ""),
                "cwd": data.get("cwd", ""),
                "status": data.get("status", ""),
                "nameSource": source,
                "socket": sock,
            })
        except Exception:
            continue  # malformed file, dead pid, anything: skip it
    found.sort(key=lambda s: s["name"])
    return found


def public(session):
    return {k: v for k, v in session.items() if k != "socket"}


def resolve_session(name):
    """All user-named, alive sessions carrying this name (0, 1 or more)."""
    return [s for s in list_sessions() if s["name"] == name]


def post_line(socket_path, content, sender="rascunho"):
    """Write one JSON line to a session's inbox socket. Returns (delivered, detail)."""
    line = json.dumps({
        "type": "user",
        "message": {"content": content},
        "from": sender,
        "msg_id": str(uuid.uuid4()),
        "priority": "next",
    }) + "\n"
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(3)
    try:
        client.connect(socket_path)
        client.sendall(line.encode("utf-8"))  # the socket never answers; don't wait for it
        return True, "posted"
    except OSError as err:
        return False, f"socket error: {err}"
    finally:
        client.close()


def transcript_path(session):
    """~/.claude/projects/<cwd with non-alphanumerics as '-'>/<sessionId>.jsonl"""
    folder = re.sub(r"[^A-Za-z0-9]", "-", session["cwd"])
    return PROJECTS_DIR / folder / f"{session['sessionId']}.jsonl"


# ---------------------------------------------------------------- send log + seen watcher

LOG_LOCK = threading.Lock()


def log_append(entry):
    with LOG_LOCK:
        INBOX_DIR.mkdir(exist_ok=True)
        with LOG_PATH.open("a") as handle:
            handle.write(json.dumps(entry) + "\n")


def log_read(limit=None):
    if not LOG_PATH.is_file():
        return []
    entries = {}
    with LOG_LOCK:
        for line in LOG_PATH.read_text().splitlines():
            try:
                entry = json.loads(line)
                entries[entry["id"]] = {**entries.get(entry["id"], {}), **entry}  # later lines update
            except Exception:
                continue
    items = sorted(entries.values(), key=lambda e: e.get("time", ""), reverse=True)
    return items[:limit] if limit else items


def transcript_offset(session):
    """Where the transcript ends right now; taken BEFORE posting, so a fast Read is not missed."""
    path = transcript_path(session)
    return path.stat().st_size if path.is_file() else 0


def watch_seen(entry, session, offset):
    """Background: poll the session transcript from `offset` until a Read of the PNG appears (or give up)."""
    path = transcript_path(session)
    needle = entry["path"]
    deadline = time.monotonic() + SEEN_WATCH_SECONDS
    while time.monotonic() < deadline:
        time.sleep(2)
        if not path.is_file():
            continue
        with path.open("rb") as handle:
            handle.seek(offset)
            chunk = handle.read()
        chunk = chunk[:chunk.rfind(b"\n") + 1]   # whole lines only; a half-written line is read again next time
        offset += len(chunk)
        for raw in chunk.split(b"\n"):
            if b'"tool_use"' in raw and b'"Read"' in raw and needle.encode() in raw:
                seen = now_iso()
                log_append({"id": entry["id"], "seen": seen})
                BUS.push({"type": "seen", "id": entry["id"], "session": entry["session"], "seen": seen})
                return


# ---------------------------------------------------------------- sheets

def tile_path(query):
    sheet = sanitize(query.get("sheet", [""])[0])
    tx, ty = int(query["tx"][0]), int(query["ty"][0])
    layer = query.get("layer", ["2a2a2a"])[0].lower().lstrip("#")
    if not re.fullmatch(r"[0-9a-f]{6}", layer):
        raise ValueError("layer must be a colour hex")
    return SHEETS_DIR / sheet / f"{tx}_{ty}_{layer}.png"


def sheet_dir_from(query):
    return SHEETS_DIR / sanitize(query.get("sheet", [""])[0])


def sheet_info(sheet_dir):
    tiles, updated = [], 0.0
    if sheet_dir.is_dir():
        for entry in sheet_dir.iterdir():
            match = TILE_RE.match(entry.name)
            if match:
                tiles.append([int(match.group(1)), int(match.group(2)), match.group(3)])
                updated = max(updated, entry.stat().st_mtime)
    tiles.sort()
    meta = {}
    meta_path = sheet_dir / "meta.json"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            meta = {}
    underlay = next((f"/sheets/{sheet_dir.name}/{n}" for n in ("underlay.png", "underlay.jpg") if (sheet_dir / n).is_file()), None)
    if underlay:
        updated = max(updated, (sheet_dir / underlay.rsplit("/", 1)[1]).stat().st_mtime)
    return {
        "id": sheet_dir.name,
        "name": meta.get("name", ""),
        "tiles": tiles,
        "updated": updated,
        "thumb": (sheet_dir / "thumb.png").is_file(),
        "underlay": underlay,
    }


def underlay_store(query, data, sender, note):
    """Put a picture under a sheet (a new one unless ?sheet= is given). Returns the event dict."""
    if data.startswith(PNG_MAGIC):
        ext = ".png"
    elif data.startswith(JPEG_MAGIC):
        ext = ".jpg"
    else:
        raise ValueError("body must be a PNG or JPEG")
    wanted = query.get("sheet", [""])[0].strip()
    if wanted:
        sheet_dir = SHEETS_DIR / sanitize(wanted)
    else:
        sheet_dir = SHEETS_DIR / stamp()
        if sheet_dir.exists():
            sheet_dir = SHEETS_DIR / f"{stamp()}-{uuid.uuid4().hex[:4]}"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    for old in ("underlay.png", "underlay.jpg"):       # one underlay per sheet
        (sheet_dir / old).unlink(missing_ok=True)
    write_atomic(sheet_dir / f"underlay{ext}", data)
    meta_path = sheet_dir / "meta.json"
    meta = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            meta = {}
    if note and not meta.get("name"):
        meta["name"] = note[:120]
    meta["underlayFrom"] = sender[:80]
    write_atomic(meta_path, json.dumps(meta, indent=1).encode("utf-8"))
    event = {"type": "underlay", "sheet": sheet_dir.name, "from": sender[:80], "note": note[:400],
             "url": f"/sheets/{sheet_dir.name}/underlay{ext}"}
    BUS.push(event)
    return event


def write_atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


# ---------------------------------------------------------------- replies

def reply_store(payload):
    """Store a reply from a session; copy its image (if any) under replies/. Returns the reply dict."""
    text = str(payload.get("text") or "").strip()
    image = payload.get("image")
    if not text and not image:
        raise ValueError("reply needs text or image")
    reply_id = f"{stamp()}-{uuid.uuid4().hex[:4]}"
    REPLIES_DIR.mkdir(exist_ok=True)
    image_url = None
    if image:
        src = Path(str(image)).expanduser().resolve()
        if not any(src.is_relative_to(root) for root in IMAGE_ROOTS) or any(p.startswith(".") for p in src.parts):
            raise ValueError("image must be under your home folder or /tmp (not a dot folder)")   # the server is open to the LAN
        if not src.is_file():
            raise ValueError(f"image not found: {src}")
        data = src.read_bytes()
        if data.startswith(PNG_MAGIC):
            ext = ".png"
        elif data.startswith(JPEG_MAGIC):
            ext = ".jpg"
        else:
            raise ValueError("image must be PNG or JPEG")
        (REPLIES_DIR / f"{reply_id}{ext}").write_bytes(data)
        image_url = f"/replies/{reply_id}{ext}"
    reply = {
        "id": reply_id,
        "time": now_iso(),
        "from": str(payload.get("from") or "claude")[:80],
        "sheet": (str(payload["sheet"])[:80] if payload.get("sheet") else None),
        "text": text[:4000],
        "image": image_url,
    }
    (REPLIES_DIR / f"{reply_id}.json").write_text(json.dumps(reply, indent=1))
    BUS.push({"type": "reply", **reply})
    return reply


def replies_list(limit=20):
    items = []
    if REPLIES_DIR.is_dir():
        for path in sorted(REPLIES_DIR.glob("*.json"), reverse=True)[:limit]:
            try:
                items.append(json.loads(path.read_text()))
            except Exception:
                continue
    return items


# ---------------------------------------------------------------- http

class Handler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
        ".mjs": "text/javascript",
        ".wasm": "application/wasm",
        ".json": "application/json",
        ".webmanifest": "application/manifest+json",
        ".html": "text/html; charset=utf-8",
        ".css": "text/css",
        ".png": "image/png",
        ".jpg": "image/jpeg",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(TOOL_DIR), **kwargs)

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {self.address_string()} {fmt % args}\n")

    def end_headers(self):
        if self.path.split("?")[0].endswith((".js", ".mjs", ".css", ".html", "/")):
            self.send_header("Cache-Control", "no-cache")  # the iPad must see new code on reload
        super().end_headers()

    # helpers
    def send_json(self, obj, code=200):
        body = json.dumps(obj, indent=1).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(self, data, mime, code=200):
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY:
            raise ValueError(f"body must be 1..{MAX_BODY} bytes")
        return self.rfile.read(length)

    def read_png(self):
        data = self.read_body()
        if not data.startswith(PNG_MAGIC):
            raise ValueError("body is not a PNG")
        return data

    def read_json(self):
        try:
            return json.loads(self.read_body().decode("utf-8"))
        except json.JSONDecodeError as err:
            raise ValueError(f"bad JSON: {err}")

    def route(self):
        parts = urlsplit(self.path)
        return parts.path, parse_qs(parts.query)

    def query_int(self, query, key, default):
        try:
            return int(query.get(key, [default])[0])
        except ValueError:
            return default

    # GET
    def do_GET(self):
        path, query = self.route()
        try:
            if path == "/sessions":
                sessions = list_sessions(include_derived=query.get("all", ["0"])[0] == "1")
                return self.send_json([public(s) for s in sessions])
            if path == "/sends":
                return self.send_json(log_read(self.query_int(query, "limit", 20)))
            if path == "/send-status":
                wanted = query.get("id", [""])[0]
                found = [e for e in log_read() if e.get("id") == wanted]
                if not found:
                    return self.send_json({"ok": False, "detail": "no such send"}, 404)
                return self.send_json(found[0])
            if path == "/replies":
                return self.send_json(replies_list(self.query_int(query, "limit", 20)))
            if path == "/events":
                since = self.query_int(query, "since", 0)
                timeout = min(self.query_int(query, "timeout", LONG_POLL_SECONDS), LONG_POLL_SECONDS)
                events, seq = BUS.after(since, timeout)
                return self.send_json({"seq": seq, "events": events})
            if path == "/sheets":
                items = []
                if SHEETS_DIR.is_dir():
                    for sheet_dir in SHEETS_DIR.iterdir():
                        if sheet_dir.is_dir() and not sheet_dir.name.startswith("_"):
                            info = sheet_info(sheet_dir)
                            info["tiles"] = len(info["tiles"])
                            items.append(info)
                items.sort(key=lambda s: s["updated"], reverse=True)
                return self.send_json(items)
            if path == "/sheet":
                return self.send_json(sheet_info(sheet_dir_from(query)))
            if path == "/tile":
                tile = tile_path(query)
                if not tile.is_file():
                    return self.send_json({"ok": False, "detail": "no such tile"}, 404)
                return self.send_bytes(tile.read_bytes(), "image/png")
        except (ValueError, KeyError) as err:
            return self.send_json({"ok": False, "detail": f"bad request: {err}"}, 400)
        return super().do_GET()  # static files

    # POST
    def do_POST(self):
        path, query = self.route()
        try:
            if path == "/send":
                return self.handle_send()
            if path == "/reply":
                return self.send_json({"ok": True, "reply": reply_store(self.read_json())})
            if path == "/tile":
                tile = tile_path(query)
                write_atomic(tile, self.read_png())
                return self.send_json({"ok": True, "path": str(tile)})
            if path == "/thumb":
                thumb = sheet_dir_from(query) / "thumb.png"
                write_atomic(thumb, self.read_png())
                return self.send_json({"ok": True, "url": f"/sheets/{thumb.parent.name}/thumb.png"})
            if path == "/underlay":
                event = underlay_store(query, self.read_body(),
                                       self.headers.get("X-From", "").strip() or "claude",
                                       self.headers.get("X-Note", "").strip())
                self.log_message("underlay -> sheet %s from %s", event["sheet"], event["from"])
                return self.send_json({"ok": True, **{k: v for k, v in event.items() if k != "type"}})
            if path == "/sheet-meta":
                sheet_dir = sheet_dir_from(query)
                payload = self.read_json()
                sheet_dir.mkdir(parents=True, exist_ok=True)
                meta_path = sheet_dir / "meta.json"
                meta = json.loads(meta_path.read_text()) if meta_path.is_file() else {}
                meta["name"] = str(payload.get("name", ""))[:120]
                write_atomic(meta_path, json.dumps(meta, indent=1).encode("utf-8"))
                return self.send_json({"ok": True, "meta": meta})
        except (ValueError, KeyError) as err:
            return self.send_json({"ok": False, "detail": f"bad request: {err}"}, 400)
        self.send_json({"ok": False, "detail": "not found"}, 404)

    def do_DELETE(self):
        path, query = self.route()
        try:
            if path == "/tile":
                tile = tile_path(query)
                existed = tile.is_file()
                if existed:
                    tile.unlink()
                return self.send_json({"ok": True, "removed": existed})
            if path == "/sheet":
                sheet_dir = sheet_dir_from(query)
                if not sheet_dir.is_dir():
                    return self.send_json({"ok": False, "detail": "no such sheet"}, 404)
                trash = SHEETS_DIR / "_trash"
                trash.mkdir(exist_ok=True)
                shutil.move(str(sheet_dir), str(trash / f"{sheet_dir.name}-{stamp()}"))
                return self.send_json({"ok": True, "removed": True})
        except (ValueError, KeyError) as err:
            return self.send_json({"ok": False, "detail": f"bad request: {err}"}, 400)
        self.send_json({"ok": False, "detail": "not found"}, 404)

    def handle_send(self):
        session_name = self.headers.get("X-Session", "").strip()
        if not session_name:
            raise ValueError("X-Session header required")
        note = self.headers.get("X-Note", "").strip()
        sheet = self.headers.get("X-Sheet", "").strip()
        data = self.read_png()

        folder = INBOX_DIR / sanitize(session_name)
        folder.mkdir(parents=True, exist_ok=True)
        png = folder / f"rascunho-{stamp()}.png"
        if png.exists():  # two sends in the same second
            png = folder / f"rascunho-{stamp()}-{uuid.uuid4().hex[:4]}.png"
        png.write_bytes(data)

        entry = {
            "id": png.stem, "time": now_iso(), "session": session_name, "sessionId": None,
            "path": str(png), "sheet": sheet or None, "note": note or None, "delivered": False, "seen": None,
        }
        matches = resolve_session(session_name)
        result = {"ok": True, "id": entry["id"], "path": str(png), "session": None, "delivered": False, "detail": ""}
        if len(matches) == 0:
            result["detail"] = f"no running user-named session called {session_name!r}; saved only"
        elif len(matches) > 1:
            result.update(ok=False, detail="ambiguous", sessions=[public(m) for m in matches])
        else:
            session = matches[0]
            reply_hint = (f'To answer on the iPad: python3 "{REPLY_SCRIPT}" --from {session_name}'
                          + (f" --sheet {sheet}" if sheet else "") + ' "your text" (add --image <png> to send a picture back).')
            content = (f"New rascunho from the iPad: {png}\n" + (f"{note}\n" if note else "")
                       + "Read the PNG to see it.\n" + reply_hint)
            offset = transcript_offset(session)
            delivered, detail = post_line(session["socket"], content)
            self.log_message("send -> %s (pid %s): delivered=%s %s", session_name, session["pid"], delivered, detail)
            entry.update(sessionId=session["sessionId"], delivered=delivered)
            result.update(session=public(session), delivered=delivered, detail=detail)
            if delivered:
                threading.Thread(target=watch_seen, args=(entry, session, offset), daemon=True).start()
        log_append(entry)
        BUS.push({"type": "sent", "id": entry["id"], "session": session_name, "delivered": entry["delivered"]})
        self.send_json(result, 200 if result["ok"] else 409)


# ---------------------------------------------------------------- main

def lan_urls(port):
    urls = [f"http://{socket.gethostname().lower().removesuffix('.local')}.local:{port}"]
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))  # no packets sent; just picks the LAN interface
        urls.append(f"http://{probe.getsockname()[0]}:{port}")
        probe.close()
    except OSError:
        pass
    urls.append(f"http://localhost:{port}")
    return urls


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8880)
    args = parser.parse_args()
    for folder in (INBOX_DIR, SHEETS_DIR, REPLIES_DIR):
        folder.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    server.daemon_threads = True
    print(f"rascunho server  folder={TOOL_DIR}", flush=True)
    for url in lan_urls(args.port):
        print(f"  {url}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
