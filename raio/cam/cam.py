#!/usr/bin/env python3
"""cam: raio's eye, phase 3.  Stdlib + ffmpeg; numpy/OpenCV only for `burst` and the calibration (later).

  cam.py list                       video devices AVFoundation publishes (name, never trust the index)
  cam.py usb [--watch]              "laser ✓ camera ✓" from the USB tree (laser = vendor 0x9588, camera = config)
  cam.py snap [--cam NAME] [--out F] [--size WxH] [--warm N]      one still, p2s.snap() pattern
  cam.py burst [--cam NAME] [--seconds S] [--out F]               per-pixel max over S seconds (red-frame capture)
  cam.py config                     print config.json (camera name / vid / pid / size)
  cam.py uvc show|lock|apply|auto   UVC controls via uvc-util: show = values · lock = freeze the current auto exposure/WB into
                                    config "uvc" and apply · apply = write config "uvc" to the camera · auto = back to auto
  cam.py serve [--port 8878]        RaioEye's server: /snap.jpg  /live.mjpg  /state.json  /  (runs inside RaioEye.app)

Never talks to the laser board.  `armed.flag` (written by raio's driver while the laser-enable bit is high) is shown as state; the eye
stays OPEN during jobs (Edson, 2026-10-21 19:06: the bed camera is on the frame, far from the lens, and watching the job is its point).
`"shutter_when_armed": true` in config.json brings the old rule back for a camera mounted on the head.
Frames live outside Dropbox by default (~/Library/Caches/raio/snaps).  2026-10-21.
"""
import argparse, json, os, re, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = Path.home() / "Library/Caches/raio"
SNAPS = CACHE / "snaps"
CONFIG = HERE / "config.json"
ARMED = CACHE / "armed.flag"          # written by lmc.py write_port while the laser-enable bit is high; removed on safe_idle (raio session, 2026-10-21 18:01)
STATE = CACHE / "state.json"          # usb watch writes {laser, camera, ts}
LASER_VENDOR = 0x9588                 # BJJCZ; match the vendor only (PID changes with firmware state)
FFMPEG = "/opt/homebrew/bin/ffmpeg" if Path("/opt/homebrew/bin/ffmpeg").exists() else "ffmpeg"

DEFAULT_CONFIG = {
    "camera": {"name": "MacBook Pro Camera", "vid": None, "pid": None, "size": "1280x720", "fps": 30},
    "note": "name = substring of the AVFoundation device name; vid/pid = the USB camera's ids (decimal or 0x…), for the usb poll",
}


def die(msg):
    print("cam:", msg, file=sys.stderr)
    sys.exit(1)


def config():
    if not CONFIG.exists():
        CONFIG.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n")
    return json.loads(CONFIG.read_text())


def atomic_write(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    os.replace(tmp, path)


# ---------- devices ----------

def devices():
    """[(index, name)] of AVFoundation video devices, in ffmpeg's current order."""
    r = subprocess.run([FFMPEG, "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
                       capture_output=True, text=True)
    out, vids = [], False
    for line in r.stderr.splitlines():
        if "AVFoundation video devices" in line:
            vids = True; continue
        if "AVFoundation audio devices" in line:
            break
        m = re.search(r"\[(\d+)\] (.+)$", line) if vids else None
        if m:
            out.append((int(m.group(1)), m.group(2).strip()))
    return out


def find(name=None):
    """The one device whose name contains `name` (case-insensitive). Index is resolved now, used once."""
    name = name or config()["camera"]["name"]
    hits = [d for d in devices() if name.lower() in d[1].lower()]
    if not hits:
        die(f"no video device matching {name!r}; have: {[n for _, n in devices()]}")
    if len(hits) > 1:
        die(f"{name!r} is ambiguous: {hits}")
    return hits[0]


def shutter():
    return bool(config().get("shutter_when_armed", False))


def refuse_if_armed():
    if shutter() and ARMED.exists():
        die(f"no frames while the laser can fire: {ARMED} exists (the driver writes it while the laser-enable bit is high, "
            "removes it on safe_idle). If no job is running, the driver crashed: ask Edson before removing it")


# ---------- capture ----------

def snap(cam=None, out=None, size=None, warm=20, fps=None, timeout=25):
    refuse_if_armed()
    c = config()["camera"]
    idx, name = find(cam)
    size = size or c.get("size"); fps = fps or c.get("fps", 30)
    out = Path(out) if out else SNAPS / time.strftime("%Y-%m-%d_%H-%M-%S.jpg")
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-f", "avfoundation", "-framerate", str(fps)]
    if size:
        cmd += ["-video_size", size]
    cmd += ["-i", str(idx), "-vf", f"select=gte(n\\,{warm})", "-frames:v", 1 and "1", "-update", "1", str(out)]
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    try:
        _, err = p.communicate(timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        err = ("timeout: ffmpeg never got a frame. On macOS this is the camera permission gate: the responsible app "
               "(Terminal, VS Code, RaioEye.app) must hold Camera access; a bare process is neither asked nor answered "
               "(06-camera.md §4.2). Run from Terminal once, or through RaioEye.app.")
    if not out.exists() or out.stat().st_size == 0:
        die(f"no frame from {name!r} ({err.strip()[:400]})")
    return out


def burst(cam=None, seconds=1.0, out=None, size=None, fps=None):
    """Per-pixel maximum over `seconds`: the galvo's moving red dot becomes the whole outline."""
    refuse_if_armed()
    import numpy as np
    c = config()["camera"]
    idx, name = find(cam)
    size = size or c.get("size") or "1280x720"; fps = fps or c.get("fps", 30)
    w, h = (int(x) for x in size.split("x"))
    out = Path(out) if out else SNAPS / time.strftime("%Y-%m-%d_%H-%M-%S_burst.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [FFMPEG, "-loglevel", "error", "-f", "avfoundation", "-framerate", str(fps), "-video_size", size,
           "-i", str(idx), "-t", str(seconds + 1.0), "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True, timeout=seconds + 30).stdout
    n = len(raw) // (w * h * 3)
    if n < 2:
        die(f"burst got {n} frames from {name!r}")
    frames = np.frombuffer(raw[: n * w * h * 3], dtype=np.uint8).reshape(n, h, w, 3)
    skip = min(fps, n - 1)                      # warm-up
    mx = frames[skip:].max(axis=0)
    import cv2
    cv2.imwrite(str(out), cv2.cvtColor(mx, cv2.COLOR_RGB2BGR))
    return out, n - skip


# ---------- usb ----------

def usb_devices():
    """[{vid, pid, name}] from ioreg (read-only; the board is never opened)."""
    r = subprocess.run(["ioreg", "-p", "IOUSB", "-l", "-w0"], capture_output=True, text=True)
    devs, cur = [], {}
    for line in r.stdout.splitlines():
        if re.match(r"[\s|]*\+-o ", line):
            if cur.get("vid") is not None:
                devs.append(cur)
            cur = {}
        for key, field in (("idVendor", "vid"), ("idProduct", "pid")):
            m = re.search(rf'"{key}" = (\d+)', line)
            if m:
                cur[field] = int(m.group(1))
        m = re.search(r'"USB Product Name" = "([^"]*)"', line)
        if m:
            cur["name"] = m.group(1)
    if cur.get("vid") is not None:
        devs.append(cur)
    return devs


def _num(v):
    return int(v, 0) if isinstance(v, str) else v


def usb_state():
    c = config()["camera"]
    devs = usb_devices()
    laser = any(d.get("vid") == LASER_VENDOR for d in devs)
    vid, pid = _num(c.get("vid")), _num(c.get("pid"))
    if vid:
        cam_usb = any(d.get("vid") == vid and (pid is None or d.get("pid") == pid) for d in devs)
    else:
        cam_usb = None                       # no USB camera configured yet
    cam_av = any(c["name"].lower() in n.lower() for _, n in devices())
    return {"laser": laser, "camera_usb": cam_usb, "camera": cam_av and (cam_usb is not False),
            "laser_pid": next((d.get("pid") for d in devs if d.get("vid") == LASER_VENDOR), None),
            "ts": time.strftime("%Y-%m-%d %H:%M:%S")}


def fmt_state(s):
    tick = lambda b: "✓" if b else "✗"
    pid = f" (pid 0x{s['laser_pid']:04x})" if s.get("laser_pid") else ""
    return f"laser {tick(s['laser'])}{pid}  camera {tick(s['camera'])}  {s['ts']}"


def usb_watch(period=2.0):
    last = None
    while True:
        s = usb_state()
        key = (s["laser"], s["camera"])
        if key != last:
            print(fmt_state(s), flush=True)
            atomic_write(STATE, s)
            last = key
        time.sleep(period)


# ---------- uvc (exposure, white balance, …) ----------

UVC_UTIL = next((p for p in (Path.home() / "Library/Application Support/RaioEye/bin/uvc-util", HERE / "bin/uvc-util") if p.exists()), None)
UVC_CONTROLS = ["auto-exposure-mode", "exposure-time-abs", "gain", "auto-white-balance-temp", "white-balance-temp", "brightness",
                "contrast", "saturation", "sharpness", "gamma", "hue", "backlight-compensation", "power-line-frequency"]

def _uvc_target():
    c = config()["camera"]
    vid, pid = _num(c.get("vid")), _num(c.get("pid"))
    if not UVC_UTIL:
        die("uvc-util not installed (cam/vendor/uvc-util, build with clang -fno-objc-arc …)")
    if not vid or not pid:
        die("config.json camera.vid/pid missing: uvc-util selects the camera by them")
    return [str(UVC_UTIL), "-k", "-V", f"0x{vid:04x}:0x{pid:04x}"]

def uvc_get(name):
    r = subprocess.run(_uvc_target() + ["-o", name], capture_output=True, text=True, timeout=10)
    v = r.stdout.strip()
    return v if r.returncode == 0 and v else None

def uvc_show():
    return {n: uvc_get(n) for n in UVC_CONTROLS}

def uvc_apply(settings=None, quiet=False):
    """Write config["uvc"] (or `settings`) to the camera, in an order the camera accepts: modes first, then values."""
    settings = settings if settings is not None else config().get("uvc") or {}
    if not settings:
        return {}
    order = ["auto-exposure-mode", "auto-white-balance-temp"] + [k for k in settings if k not in ("auto-exposure-mode", "auto-white-balance-temp")]
    done = {}
    for k in order:
        if k not in settings:
            continue
        r = subprocess.run(_uvc_target() + ["-s", f"{k}={settings[k]}"], capture_output=True, text=True, timeout=10)
        done[k] = "ok" if r.returncode == 0 else (r.stderr or r.stdout).strip()[:80]
    if not quiet:
        for k, v in done.items():
            print(f"  {k:26s} {settings[k]!s:8s} {v}")
    return done

def uvc_lock():
    """Freeze what auto exposure / auto white balance settled on, under the light of this moment, and remember it."""
    uvc_apply({"auto-exposure-mode": 8, "auto-white-balance-temp": "true"}, quiet=True)   # let the camera settle in auto first
    time.sleep(2.5)
    now = uvc_show()
    locked = {"auto-exposure-mode": 1, "exposure-time-abs": int(now["exposure-time-abs"]), "gain": int(now["gain"]),
              "auto-white-balance-temp": "false", "white-balance-temp": int(now["white-balance-temp"]),
              "power-line-frequency": 2}                                                      # 2 = 60 Hz (Brooklyn)
    for k in ("brightness", "contrast", "saturation", "sharpness", "gamma", "backlight-compensation"):
        if now.get(k) is not None:
            locked[k] = int(now[k])
    cfg = config(); cfg["uvc"] = locked
    cfg["uvc_locked_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"locked from auto at {cfg['uvc_locked_at']}: exposure {locked['exposure-time-abs']}, gain {locked['gain']}, WB {locked['white-balance-temp']} K, 60 Hz")
    return uvc_apply(locked)

def uvc_auto():
    cfg = config(); cfg.pop("uvc", None); cfg.pop("uvc_locked_at", None)
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
    return uvc_apply({"auto-exposure-mode": 8, "auto-white-balance-temp": "true", "power-line-frequency": 2})


# ---------- serve (RaioEye) ----------

import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

class Live:
    """One ffmpeg MJPEG capture shared by every /live.mjpg client; runs only while someone watches and the laser is not armed."""
    def __init__(self):
        self.lock = threading.Condition()
        self.frame = None; self.seq = 0; self.clients = 0
        self.proc = None; self.thread = None; self.error = None

    def _reader(self, proc):
        buf = b""; got = 0
        try:
            while True:
                chunk = proc.stdout.read(65536)
                if not chunk:
                    break
                buf += chunk
                while True:
                    a = buf.find(b"\xff\xd8")
                    b = buf.find(b"\xff\xd9", a + 2) if a >= 0 else -1
                    if a < 0 or b < 0:
                        if a > 0:
                            buf = buf[a:]
                        break
                    jpg = buf[a:b + 2]; buf = buf[b + 2:]
                    got += 1
                    with self.lock:
                        self.frame = jpg; self.seq += 1; self.lock.notify_all()
        finally:
            err = proc.stderr.read().decode(errors="replace")[-400:] if proc.stderr else ""
            with self.lock:
                if self.proc is proc:
                    self.proc = None
                # ffmpeg prints format warnings on stderr and streams anyway; only a run with no frames is an error
                if got == 0 and err.strip():
                    self.error = err.strip()
                self.lock.notify_all()

    def start(self):
        with self.lock:
            if self.proc:
                return
            c = config()["camera"]
            idx, _ = find(c["name"])
            size = c.get("live_size", "1280x720"); fps = c.get("fps", 30)
            cmd = [FFMPEG, "-loglevel", "error", "-f", "avfoundation", "-framerate", str(fps), "-video_size", size,
                   "-i", str(idx), "-r", str(c.get("live_fps", 10)), "-q:v", "6", "-f", "mjpeg", "-"]
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.error = None
            self.thread = threading.Thread(target=self._reader, args=(self.proc,), daemon=True); self.thread.start()

    def stop(self):
        with self.lock:
            p, self.proc = self.proc, None
        if p:
            p.kill()

    def wait_frame(self, seq, timeout=5.0):
        with self.lock:
            self.lock.wait_for(lambda: self.seq != seq or self.proc is None, timeout)
            return self.frame, self.seq


LIVE = Live()
LAST = {"snap": None, "snap_time": None}


def guard_loop():
    """Every second: if armed.flag appears, kill the live capture; every 2 s refresh the usb state file and re-apply the UVC
    settings when the camera comes back."""
    n = 0; was = None
    while True:
        if shutter() and ARMED.exists() and LIVE.proc:
            LIVE.stop()
        n += 1
        if n % 2 == 0:
            try:
                st = usb_state(); atomic_write(STATE, st)
                if st["camera"] and was is False and config().get("uvc"):
                    time.sleep(2); uvc_apply(quiet=True); print("uvc settings re-applied (camera back)", flush=True)
                was = st["camera"]
            except Exception:
                pass
        time.sleep(1)


def page():
    return (HERE / "index.html").read_text() if (HERE / "index.html").exists() else "<pre>RaioEye</pre>"


class H(BaseHTTPRequestHandler):
    server_version = "RaioEye/0.1"
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json", extra=()):
        self.send_response(code)
        self.send_header("Content-Type", ctype); self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        for k, v in extra:
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        q = dict(kv.split("=", 1) if "=" in kv else (kv, "1") for kv in self.path.split("?")[1].split("&")) if "?" in self.path else {}
        try:
            if path == "/":
                self._send(200, page().encode(), "text/html; charset=utf-8")
            elif path == "/studio.css" and (HERE / "studio.css").exists():
                self._send(200, (HERE / "studio.css").read_bytes(), "text/css")
            elif path == "/state.json":
                s = usb_state()
                s.update({"armed": ARMED.exists(), "shutter_when_armed": shutter(), "live": LIVE.proc is not None, "live_clients": LIVE.clients,
                          "live_error": LIVE.error, "snap": LAST["snap"], "snap_time": LAST["snap_time"],
                          "camera_name": config()["camera"]["name"], "port": PORT,
                          "uvc_locked_at": config().get("uvc_locked_at")})
                self._send(200, json.dumps(s).encode())
            elif path == "/snap.jpg":
                if shutter() and ARMED.exists():
                    self._send(423, json.dumps({"error": "armed: no frames while the laser can fire"}).encode()); return
                if LIVE.proc is not None and "full" not in q:
                    frame, _ = LIVE.wait_frame(LIVE.seq)      # a fresh frame from the running stream
                    if frame:
                        out = SNAPS / time.strftime("%Y-%m-%d_%H-%M-%S.jpg"); out.parent.mkdir(parents=True, exist_ok=True)
                        out.write_bytes(frame)
                        LAST.update(snap=str(out), snap_time=time.strftime("%Y-%m-%d %H:%M:%S"))
                        self._send(200, frame, "image/jpeg", [("X-Snap-Path", str(out))]); return
                    self._send(503, json.dumps({"error": "live stream gave no frame", "detail": LIVE.error}).encode()); return
                was_live = LIVE.proc is not None
                if was_live:
                    LIVE.stop(); time.sleep(0.5)
                try:
                    out = snap()
                finally:
                    if was_live and LIVE.clients:
                        LIVE.start()
                LAST.update(snap=str(out), snap_time=time.strftime("%Y-%m-%d %H:%M:%S"))
                self._send(200, out.read_bytes(), "image/jpeg", [("X-Snap-Path", str(out))])
            elif path == "/live.mjpg":
                if shutter() and ARMED.exists():
                    self._send(423, json.dumps({"error": "armed: no frames while the laser can fire"}).encode()); return
                LIVE.start()
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.send_header("Cache-Control", "no-store"); self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with LIVE.lock:
                    LIVE.clients += 1
                seq = 0
                try:
                    while True:
                        frame, seq2 = LIVE.wait_frame(seq)
                        if frame is None or seq2 == seq:
                            if LIVE.proc is None:
                                break           # shuttered, or ffmpeg died
                            continue
                        seq = seq2
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(frame))
                        self.wfile.write(frame); self.wfile.write(b"\r\n"); self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    with LIVE.lock:
                        LIVE.clients -= 1
                        last = LIVE.clients == 0
                    if last:
                        threading.Timer(10, lambda: LIVE.stop() if LIVE.clients == 0 else None).start()
            else:
                self._send(404, b'{"error":"not found"}')
        except SystemExit as e:            # die() inside snap/find
            self._send(503, json.dumps({"error": "capture failed; see server log"}).encode())
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)[:300]}).encode())


PORT = 8878

def serve(port=PORT):
    global PORT
    PORT = port
    CACHE.mkdir(parents=True, exist_ok=True)
    threading.Thread(target=guard_loop, daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", port), H)
    srv.daemon_threads = True
    print(f"RaioEye on http://0.0.0.0:{port}  camera={config()['camera']['name']!r}  frames={SNAPS}", flush=True)
    if config().get("uvc"):
        try:
            r = uvc_apply(quiet=True); print("uvc settings applied:", ", ".join(f"{k}={v}" for k, v in r.items() if v != "ok") or "all ok", flush=True)
        except SystemExit:
            print("uvc settings NOT applied (see cam.py uvc)", flush=True)
    try:
        srv.serve_forever()
    finally:
        LIVE.stop()


# ---------- cli ----------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list"); sub.add_parser("config")
    u = sub.add_parser("usb"); u.add_argument("--watch", action="store_true")
    sv = sub.add_parser("serve"); sv.add_argument("--port", type=int, default=8878)
    uv = sub.add_parser("uvc"); uv.add_argument("what", choices=["show", "lock", "apply", "auto"])
    for name in ("snap", "burst"):
        s = sub.add_parser(name)
        s.add_argument("--cam"); s.add_argument("--out"); s.add_argument("--size"); s.add_argument("--fps", type=int)
        if name == "snap":
            s.add_argument("--warm", type=int, default=20)
        else:
            s.add_argument("--seconds", type=float, default=1.0)
    a = ap.parse_args()
    if a.cmd == "list":
        for i, n in devices():
            print(f"[{i}] {n}")
    elif a.cmd == "config":
        print(json.dumps(config(), indent=2))
    elif a.cmd == "usb":
        usb_watch() if a.watch else print(fmt_state(usb_state()))
    elif a.cmd == "serve":
        serve(a.port)
    elif a.cmd == "uvc":
        if a.what == "show":
            for k, v in uvc_show().items():
                print(f"  {k:26s} {v}")
        else:
            {"lock": uvc_lock, "apply": uvc_apply, "auto": uvc_auto}[a.what]()
    elif a.cmd == "snap":
        print(snap(a.cam, a.out, a.size, a.warm, a.fps))
    elif a.cmd == "burst":
        out, n = burst(a.cam, a.seconds, a.out, a.size, a.fps)
        print(f"{out}  ({n} frames max-stacked)")


if __name__ == "__main__":
    main()
