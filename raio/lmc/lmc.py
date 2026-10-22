"""raio · lmc/lmc.py — the driver core for the B6's BJJCZ LMC V4 board.

Protocol: research/02-protocol.md (meerk40t balormk + galvoplotter, MIT; EZCAD's own
sequences from the captured session). This file holds only what phase 0 needs:
connect, single commands, status, ports, extended axis, safe idle, abort.
Lists (red light, marking) are added when phase 0.4 starts.

Safety posture: nothing here enables emission. `safe_idle()` closes the MO and drops
the laser-enable port bit; every caller wraps motion in try/finally safe_idle().
LightBurn must be closed: one process owns the interface.
"""
import os, struct, threading, time
from pathlib import Path
import usb.core, usb.util

ARMED_FLAG = Path.home() / "Library/Caches/raio/armed.flag"
GO_FLAG = Path.home() / "Library/Caches/raio/go.flag"       # Edson's go for the job being previewed; touched by the session on his word
STOP_FLAG = Path.home() / "Library/Caches/raio/stop.flag"   # cancel the preview   # exists while the laser may fire; the camera session never captures while it exists

VID, PID = 0x9588, 0x9899
EP_OUT, EP_IN = 0x02, 0x88
READY, BUSY, AXIS = 0x20, 0x04, 0x40
PAUSED = 0x08                                   # status bit while StopList holds the list (measured 2026-10-22 01:22: 0x228 paused, 0x224 running)
PAUSE_FLAG = Path.home() / "Library/Caches/raio/pause.flag"   # exists = Edson asked to pause (board page); removed = resume
LASER_BIT, RED_BIT = 0, 8                       # port bits (documented in balor/meerk40t; unconfirmed on this board)

# immediate opcodes used here (02-protocol.md §3.1)
OP = dict(DisableLaser=0x02, EnableLaser=0x04, GetVersion=0x07, GetSerialNo=0x09, GetListStatus=0x0A,
          GetPositionXY=0x0C, GotoXY=0x0D, ResetList=0x12, StopExecute=0x1F, WritePort=0x21, ReadPort=0x25,
          SetAxisMotionParam=0x26, SetAxisOriginParam=0x27, AxisGoOrigin=0x28, MoveAxisTo=0x29, GetAxisPos=0x2A,
          Fiber_SetMo=0x33, Fiber_GetStMO_AP=0x34, Reset=0x40, SetEndOfList=0x19, ExecuteList=0x05,
          WriteCorLine=0x10, WriteCorTable=0x15, SetControlMode=0x16, SetDelayMode=0x17, SetLaserMode=0x1B,
          SetTiming=0x1C, SetStandby=0x1D, SetFirstPulseKiller=0x1A, SetPwmHalfPeriod=0x1E, SetPwmPulseWidth=0x06,
          SetFpkParam2=0x2E, SetFlyRes=0x32, WriteAnalogPort1=0x22, Op3A=0x3A, StopList=0x20, RestartList=0x13)
# list opcodes (02-protocol.md §3.2)
L = dict(JumpTo=0x8001, EndOfList=0x8002, DelayTime=0x8004, MarkTo=0x8005, JumpSpeed=0x8006, LaserOnDelay=0x8007,
         LaserOffDelay=0x8008, MarkSpeed=0x800C, PolygonDelay=0x800F, WritePort=0x8011, MarkCurrent=0x8012,
         QSwitchPeriod=0x801B, FiberOpenMO=0x8021, PulseWidth=0x8026, ReadyMark=0x8051)
NOP = struct.pack("<6H", L["EndOfList"], 0, 0, 0, 0, 0)
FIELD_MM = 157.5                                  # every config on this machine (markcfg7, LightBurn, jcz15.cor)
# The lens correction table of YOUR machine: the .cor file EZCAD uses (on the B6, jcz15.cor in the EZCAD folder the
# vendor ships). It is the vendor's file and machine-specific, so it is not in git: copy it to lmc/jcz15.cor or point
# RAIO_COR at it. Without it raio refuses to start (an uncorrected field puts every mark in the wrong place).
COR_PATH = os.environ.get("RAIO_COR") or str(Path(__file__).resolve().parent / "jcz15.cor")


class Busy(Exception): pass
class Stopped(Exception): pass          # the stop flag ended a job; the driver has already aborted and is idle


class LMC:
    def __init__(self, timeout_ms=300):
        if os.environ.get("RAIO_NO_USB"):
            raise RuntimeError("RAIO_NO_USB is set: this process must not open the laser (agents and dry runs)")
        self.t = timeout_ms
        d = usb.core.find(idVendor=VID, idProduct=PID)
        if d is None:
            raise IOError("no board on USB (9588:9899). Is the B6 on and plugged in?")
        try:
            d.set_configuration()
            usb.util.claim_interface(d, 0)
        except usb.core.USBError as e:
            if "busy" in str(e).lower() or getattr(e, "errno", None) == 16:
                raise Busy("another program holds the board (LightBurn?)")
            raise
        self.d = d
        self.ports = 0
        self.lock = threading.RLock()                  # one USB transaction at a time (abort may come from another thread)
        self.drain()                                    # a stale reply can survive in the board's IN pipe across processes
        self.u_per_mm = 65535 / FIELD_MM
        self.swap, self.sx, self.sy = True, 1, 1         # raio's mm frame = LightBurn's B6 frame (centre-relative): axes swapped vs the raw galvo words, no flips (2026-10-21 19:03)
        self.cal_x = self.cal_y = 1.0                     # measured per-axis scale (lmc/calibration.json), 1.0 = none
        try:
            import json
            c = json.loads((Path(__file__).with_name("calibration.json")).read_text())
            self.cal_x, self.cal_y = float(c.get("scale_x", 1)), float(c.get("scale_y", 1))
        except Exception:
            pass

    # ---- single commands ----
    def cmd(self, op, *args, read=True):
        a = list(args) + [0] * (5 - len(args))
        with self.lock:
            self.d.write(EP_OUT, struct.pack("<6H", op, *a), self.t)
            if not read:
                return None
            try:
                return struct.unpack("<4H", bytes(self.d.read(EP_IN, 8, self.t)))
            except usb.core.USBTimeoutError:
                # a late reply would misalign every later read by one: wait for it, then drain anything extra
                r = struct.unpack("<4H", bytes(self.d.read(EP_IN, 8, 2000)))
                self.drain()
                return r

    def drain(self):
        """Read and discard any stale replies sitting on the IN endpoint (call after a timeout or a reconnect)."""
        with self.lock:
            for _ in range(8):
                try:
                    self.d.read(EP_IN, 8, 20)
                except usb.core.USBTimeoutError:
                    return

    def status(self):
        return self.cmd(OP["GetVersion"], 0)[3]

    def wait(self, bit, want=False, timeout=30, on_timeout=None, stop_flag=None, hold=None):
        """Poll until the status bit is `want`. If `stop_flag` (a Path) appears meanwhile, abort and raise Stopped.
        hold(): True while the job is paused on purpose; the timeout does not run then (a pause is not a stall)."""
        t0 = time.time()
        while bool(self.status() & bit) != want:
            if hold is not None and hold():
                t0 = time.time()
            if stop_flag is not None and stop_flag.exists():
                try: stop_flag.unlink()
                except OSError: pass
                self.abort()
                raise Stopped("stop flag")
            if time.time() - t0 > timeout:
                if on_timeout: on_timeout()
                raise TimeoutError(f"bit 0x{bit:02x} did not become {want} in {timeout}s")
            time.sleep(0.01)

    # ---- ports / emission ----
    def write_port(self):
        self.cmd(OP["WritePort"], self.ports, 0)
        try:                                              # the armed flag follows the laser-enable bit
            if self.ports & (1 << LASER_BIT):
                ARMED_FLAG.parent.mkdir(parents=True, exist_ok=True); ARMED_FLAG.touch()
            elif ARMED_FLAG.exists():
                ARMED_FLAG.unlink()
        except OSError:
            pass

    def bit(self, n, on):
        self.ports = (self.ports | (1 << n)) if on else (self.ports & ~(1 << n))

    def safe_idle(self):
        """MO closed, laser-enable bit low. Called after every action, success or not."""
        self.cmd(OP["Fiber_SetMo"], 0)
        self.bit(LASER_BIT, False); self.bit(RED_BIT, False)
        self.write_port()

    def abort(self):
        """Stop whatever runs: StopExecute → MO off → ResetList → dummy list → verify idle → centre."""
        self.cmd(OP["StopExecute"]); self.cmd(OP["Fiber_SetMo"], 0); self.cmd(OP["ResetList"])
        with self.lock:
            self.d.write(EP_OUT, struct.pack("<6H", 0x8051, 0, 0, 0, 0, 0) + NOP * 255, 1000)
        self.cmd(OP["SetEndOfList"], 0); self.cmd(OP["ExecuteList"])
        self.safe_idle()
        self.wait(BUSY, False, timeout=5)
        self.cmd(OP["GotoXY"], 0x8000, 0x8000)

    # ---- extended axis (02-protocol.md §5; vendor format verified from Lmc1.dll) ----
    def axis_pos(self, axis=0):
        w = self.cmd(OP["GetAxisPos"], axis)
        p = w[1] | (w[2] << 16)
        return -(p & 0x7FFFFFFF) if p & 0x80000000 else p

    def axis_move_to(self, pulses, axis=0, vmin=50, vmax=200, acc_ms=100, timeout=10):
        """Absolute move in pulses, sign-magnitude. MO closed first, as EZCAD does. Blocks until the AXIS bit clears."""
        assert abs(pulses) <= 0x7FFFFF
        p = abs(pulses) | (0x80000000 if pulses < 0 else 0)
        self.cmd(OP["Fiber_SetMo"], 0)
        self.cmd(OP["SetAxisMotionParam"], max(1, vmin), max(vmin, vmax))
        self.cmd(OP["SetAxisOriginParam"], acc_ms, 0)
        self.cmd(OP["MoveAxisTo"], p & 0xFFFF, (p >> 16) | (0x4000 if axis else 0))
        self.wait(AXIS, False, timeout=timeout, on_timeout=lambda: self.cmd(OP["Reset"]))

    # ---- init (EZCAD's order, values from the captured session; 02-protocol.md §2.5) ----
    def init(self, cor_path=COR_PATH):
        ident = dict(serial=self.cmd(OP["GetSerialNo"]), version=self.cmd(OP["GetVersion"], 1))
        self.cmd(OP["Fiber_GetStMO_AP"])
        self.cmd(OP["Reset"])
        if cor_path:
            if not Path(cor_path).exists():
                raise FileNotFoundError(f"lens correction file not found: {cor_path}. Copy your machine's EZCAD .cor "
                                        f"(B6: jcz15.cor) to lmc/jcz15.cor or set RAIO_COR (README: Setup)")
            self.upload_cor(cor_path)
        else:
            self.cmd(OP["WriteCorTable"], 0)          # run uncorrected (comparison only)
        self.cmd(OP["EnableLaser"])
        # Two start-up value sets. "capture" = meerk40t/Balor defaults, taken from an EZCAD session on a Raycus machine
        # (marked correctly here at 100 %). "ezcad" = this machine's own markcfg7: PWMTICKPERIOD=5000, PWMTICKPULSEWIDTH=1,
        # FPK=40 (LightBurn: tickle 5 kHz / 1 µs). The unit of SetStandby's words is not documented; "ezcad" passes the
        # markcfg numbers through as meerk40t would its own. Select with RAIO_INIT=ezcad for an A/B on the machine.
        standby, fpk = ((5000, 1), 40) if os.environ.get("RAIO_INIT") == "ezcad" else ((2000, 20), 200)
        for op, *a in [("SetControlMode", 0), ("SetLaserMode", 1), ("SetDelayMode", 1), ("SetTiming", 1),
                       ("SetStandby", *standby), ("SetFirstPulseKiller", fpk), ("SetPwmHalfPeriod", 125),
                       ("SetPwmPulseWidth", 125), ("Fiber_SetMo", 0), ("SetFpkParam2", 0xFFB, 1, 409, 100),
                       ("SetFlyRes", 0, 99, 1000, 25)]:
            self.cmd(OP[op], *a)
        self.ports = 0; self.write_port()
        self.cmd(OP["Op3A"]); self.cmd(OP["WriteAnalogPort1"], 0x7FF); self.cmd(OP["Op3A"])   # EZCAD's exact tail
        return ident

    def upload_cor(self, path):
        """jcz .cor: magic JCZ_COR_2_1, scale double at 0x1C, 65×65 int32 (dx,dy) pairs at 0x24; 16-bit sign-magnitude on the wire."""
        b = open(path, "rb").read()
        if b[:11] != b"JCZ_COR_2_1":
            raise ValueError("not a JCZ_COR_2_1 file")
        self.u_per_mm = struct.unpack_from("<d", b, 0x1C)[0] or self.u_per_mm
        vals = struct.unpack_from("<8450i", b, 0x24)
        sm = lambda v: (v if v >= 0 else (-v + 0x8000)) & 0xFFFF
        self.cmd(OP["WriteCorTable"], 1)
        for i in range(4225):
            self.cmd(OP["WriteCorLine"], sm(vals[2 * i]), sm(vals[2 * i + 1]), 0 if i == 0 else 1, read=False)

    # ---- geometry ----
    def mm(self, x, y):
        """mm (field centre = 0,0; +x right, +y up on the drawing) → galvo units, through the axis mapping."""
        x, y = x * self.cal_x, y * self.cal_y             # measured scale, in raio's frame, before the galvo mapping
        if self.swap: x, y = y, x
        u = int(round(0x8000 + self.sx * x * self.u_per_mm)); v = int(round(0x8000 + self.sy * y * self.u_per_mm))
        if not (0 <= u <= 0xFFFF and 0 <= v <= 0xFFFF):
            raise ValueError(f"({x},{y}) mm is outside the field")
        return u, v

    def spd(self, mm_s):
        return min(0xFFFF, int(round(mm_s * self.u_per_mm / 1000)))   # round, not truncate (50 mm/s was sent as 48.1)

    @staticmethod
    def dist(a, b):
        return min(0xFFFF, int(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5))

    # ---- lists ----
    def run_list(self, cmds, timeout=60, progress=None, stop_flag=None, hold=None):
        """cmds: iterable of (op, v1..v5). Streams 3072-byte packets as EZCAD does; blocks until the board is idle.
        progress(sent, total) is called after each packet; stop_flag (Path) aborts the job when it appears.
        hold(): True while paused (StopList); the waits do not time out then. NB the board drops BUSY while paused
        (status 0x228, measured 2026-10-22), so this returns at a pause: the caller waits out the pause (raio.py)."""
        self.wait(BUSY, False, timeout=5)
        self.cmd(OP["ResetList"])
        cmds = [(L["ReadyMark"],)] + list(cmds) + [(L["EndOfList"],)]
        total = (len(cmds) + 255) // 256
        started = False
        for n in range(0, len(cmds), 256):
            chunk = cmds[n:n + 256]
            pkt = b"".join(struct.pack("<6H", *(list(c) + [0] * (6 - len(c)))) for c in chunk) + NOP * (256 - len(chunk))
            self.wait(READY, True, timeout=10, stop_flag=stop_flag, hold=hold)
            with self.lock:
                self.d.write(EP_OUT, pkt, 1000)
            self.cmd(OP["SetEndOfList"], 0)
            if n // 256 == 1:
                self.cmd(OP["ExecuteList"]); started = True
            if progress:
                try: progress(n // 256 + 1, total)
                except Exception: pass
        if not started:
            self.cmd(OP["ExecuteList"])
        self.cmd(OP["SetControlMode"], 1)
        self.wait(BUSY, False, timeout=timeout, on_timeout=self.abort, stop_flag=stop_flag, hold=hold)

    def red_polyline(self, points_mm, seconds=10, speed=3000, until=None):
        """Trace a closed path with the red pilot (port bit 8), laser bit low, MO closed, for `seconds`,
        or until `until()` returns a truthy value (checked between loops, ~every 0.1–0.5 s)."""
        self.cmd(OP["Fiber_SetMo"], 0)
        self.bit(LASER_BIT, False); self.bit(RED_BIT, True); self.write_port()
        pts = [self.mm(*p) for p in points_mm]
        cmds = [(L["JumpSpeed"], self.spd(speed)), (L["MarkSpeed"], self.spd(speed))]
        prev = pts[-1]
        for q in pts:
            cmds.append((L["JumpTo"], q[0], q[1], 0, self.dist(prev, q))); prev = q
        t0 = time.time()
        result = None
        try:
            while True:
                if until is not None:
                    result = until()
                    if result:
                        break
                elif time.time() - t0 >= seconds:
                    break
                self.run_list(cmds, timeout=10)
        finally:
            self.safe_idle()
            self.cmd(OP["GotoXY"], 0x8000, 0x8000)
        return result

    def close(self):
        try:
            usb.util.release_interface(self.d, 0)
        finally:
            usb.util.dispose_resources(self.d)
