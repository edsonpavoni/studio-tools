# raio

**Open-source control software for galvo fiber lasers with a BJJCZ LMC board, written for the ComMarker B6 MOPA.** Raio talks to the laser's controller over USB from Python, turns a LightBurn file into a job, frames it in red on the material, and fires it from a web page you keep beside your work: **frame, fire, pause, cancel**, with the camera and the progress while it cuts.

*Raio* is Portuguese for a ray of light, or lightning. It was built in Edson Pavoni's studio in São Paulo to replace LightBurn for the studio's own jobs, because the studio needed things LightBurn cannot do (Z moves between passes, a true-size field, the rules of the bench written as code). It is shared so other people with these machines can drive them with code they can read.

> **Status: v0.1 (2026-10-22).** Works every day on one machine: a ComMarker B6 MOPA 60 W (JPT MOPA source, 1064 nm, f = 210 mm lens, BJJCZ LMC V4 board, board signature `0000218409002002`), driven from a Mac. Other BJJCZ LMC V4 fiber boards speak the same protocol and will likely work, but have **not** been tested. Read the safety section before you plug anything in.

## ⚠️ Safety first
A fiber laser is a **Class 4** laser. Its 1064 nm beam is **invisible** and burns eyes and skin, directly or by reflection, long before you notice. Raio is not a safety device.

- Wear goggles rated for 1064 nm (OD 6+), keep the E-stop in reach, run extraction, and never leave a job unattended.
- **0 % power is not off**: some sources still emit around 100 mW at 0 %. Only emission *disabled* is off.
- **The board cannot prove the beam fired.** A job can report "done" while the source emitted nothing (it happened here). Watch the material.
- The red pilot is not the beam. Some machines carry another always-on red dot (the B6's autofocus sensor); do not mistake it for the frame.
- Pausing a galvo job is a known hazard: on one BJJCZ machine a LightBurn pause left the beam on and burned a line. Raio's pause switches emission off itself and checks the board resumed (below), but test it on scrap metal first.
- Raio's own rules: the job is framed in red first; **fire only works while the frame is on**; cancel aborts the board at once; every action is logged.

The full analysis, with sources: [`research/04-safety.md`](research/04-safety.md). You use this software at your own risk (see the license).

## What it does
- **Drives the board directly**: connect, initialise with your lens-correction table, red framing, streaming whole jobs in 256-command packets, abort, ports, axes. The protocol is documented in [`research/02-protocol.md`](research/02-protocol.md), each fact marked measured, documented or inferred.
- **Imports LightBurn files** (`.lbrn2`): layers, line and fill modes, power, speed, frequency, pulse width (ns), passes, wobble, fill interval, angle and angle per pass, bidirectional scanning, kerf. Checked side by side against LightBurn on metal: wobble and fill match ([`LOG.md`](LOG.md)).
- **Plans** a job into board commands with an estimate, and draws a preview ([`job/`](job/)).
- **A true-size field**: a per-axis calibration from one measured square (on our machine LightBurn's parts were 1.1–1.4 % small; raio's are 80.0 × 80.0 mm when asked for 80).
- **The board page** (`:8877`): the job on screen; **frame** (the red traces the job's contour, on until you tap again or fire); **fire** (dead until the frame is on); while cutting, **pause** and **cancel** in the same place; a live box with the bed camera and the progress; the result with a photo of the bed; the layers in run order.
- **Pause that is safe on this board**, measured on the machine: `StopList` holds the list, raio drops the laser-enable bit and closes the source itself, and on resume restores them and sends `RestartList`; the board's status word says paused (`0x228`) or running (`0x224`). If the board does not resume within a second, the job is aborted.
- **A bed camera** helper for macOS (`cam/`, RaioEye): live view and stills, used by the page.

**Not yet:** text and bitmap engraving (convert text to paths first), Z moves (the B6's column is its own controller), rotary, a door interlock. Ideas and their order: [`BACKLOG.md`](BACKLOG.md).

## Setup
Tested on macOS (Apple silicon) with Python 3.11+. The driver uses pyusb, so Linux should work with the right udev rule; Windows would need a libusb driver for the board (Zadig) and is untested.

```bash
brew install libusb                         # macOS; Linux: your distribution's libusb-1.0
python3 -m venv ~/.venvs/raio
~/.venvs/raio/bin/pip install -r requirements.txt
```

1. **Close LightBurn and EZCAD.** One program owns the board; raio says so if another one has it.
2. **Your lens-correction file.** The board needs your machine's correction table, the `.cor` file EZCAD uses (on the B6: `jcz15.cor` in the EZCAD folder the vendor ships). Copy it to `lmc/jcz15.cor` or set `RAIO_COR=/path/to/file.cor`. It is the vendor's file and machine-specific, so it is not in this repository. Raio refuses to start without it.
3. **Your field.** `FIELD_MM = 157.5` in `lmc/lmc.py` and `job/plan.py` is the B6's lens (f = 210 mm). Use your lens's field from EZCAD or LightBurn.
4. **Your calibration.** `lmc/calibration.json` holds *our* machine's per-axis scale. Make your own: mark the 80 mm square (`lmc/mark_test.py square --len 80`, on metal, with the go described below), measure both sides with a caliper, and set `scale_x = 80 / measured_x`, `scale_y = 80 / measured_y`. Until then, set both to 1.0.
5. **Look before you fire.** `RAIO_NO_USB=1` makes every entry point stop before opening the laser: use it to try everything first.

## Quick start
```bash
PY=~/.venvs/raio/bin/python
$PY raio.py import my-file.lbrn2 -o my-job.raio     # LightBurn → .raio (refuses text, bitmaps, shapes off the field)
$PY raio.py show my-job.raio                         # layers in run order, settings, totals
$PY raio.py plan my-job.raio --svg preview.svg       # board commands, estimate, preview (no USB)
$PY raio.py load my-job.raio                         # put the job on the board page (no laser)
python3 board/server.py                              # the page: http://localhost:8877
```
On the page: place the material, **frame**, check the red sits where it should, **fire**. Pause or cancel at any time.

From the command line instead: `raio.py mark my-job.raio` puts the red on and waits; `touch ~/Library/Caches/raio/go.flag` fires it, `stop.flag` cancels (the flags live in `~/Library/Caches/raio/` on every OS for now).

## How it fits together
```
LightBurn .lbrn2 ──import──▶ .raio job ──plan──▶ board commands ──lmc──▶ USB ▶ BJJCZ LMC board ▶ galvos + source
                                   │                                  ▲
                         raio load │          frame / fire / pause / cancel (flags)
                                   ▼                                  │
                         board/server.py (:8877) ◀──── the page (browser, iPad)
                                   ▲
                         cam/ RaioEye (:8878): live view + stills of the bed
```
- [`lmc/`](lmc/): the driver (`lmc.py`) and the measured test scripts (`probe.py` read-only, `frame_test.py`, `mark_test.py`, `pause_test.py`, …).
- [`job/`](job/): the `.raio` model, the LightBurn importer, geometry (fill, wobble, kerf), the planner.
- [`raio.py`](raio.py): the command line (`import`, `show`, `plan`, `frame`, `mark`, `load`, `still`).
- [`board/`](board/): the page and its server; [`board/CONTRACT.md`](board/CONTRACT.md) is the contract between them (files, flags, endpoints).
- [`FORMAT.md`](FORMAT.md): the `.raio` job file. [`MACHINE.md`](MACHINE.md): what the machine can and cannot be told. [`PLAN.md`](PLAN.md): architecture, phases and their gates. [`LOG.md`](LOG.md): every live action on the machine with its raw result.

## Credits
- The BJJCZ protocol was reverse-engineered by others before us: **[meerk40t](https://github.com/meerk40t/meerk40t)** (`balormk`, MIT), **[Balor](https://gitlab.com/bryce15/balor)** and **[galvoplotter](https://github.com/meerk40t/galvoplotter)**. Raio checked it against this machine and the vendor's library; [`research/02-protocol.md`](research/02-protocol.md) says which facts came from where.
- `cam/vendor/uvc-util`: Jeffrey Frey's UVC control utility (MIT, its own `LICENSE`).
- The sigil (`board/icon-180.png`): *best* from the *Alchemy* set by chinnan, [The Noun Project](https://thenounproject.com/icon/best-556659/) (CC BY 3.0).
- Built by Edson Pavoni with Claude (Anthropic) as a pair, October 2026.

Not affiliated with ComMarker, BJJCZ, JPT or LightBurn. Their names are used only to say what this works with.

## License
MIT, see [`LICENSE`](LICENSE).

---

# The studio's record
## v0.1 · 2026-10-22 · "the bench in the dark"
Raio cuts from its own page. Built with Edson in the Superset pane beside the session, 2026-10-21 23:20 → 2026-10-22 02:12, tested on the machine at each step.

- **The board page** (http://localhost:8877, iPad tile *Raio*, always on through the iPad runner): the job on screen (name, material), **frame** (a switch: the red traces the job's *contour* until tapped again or fire) and **fire** (dead until the frame is on, then one tap); while cutting, **pause** (a switch) and **cancel** in the same place. The buttons sit under the name and stay at the top of the pane when it scrolls.
- **The live box** under the buttons while framing or cutting: a small camera feed (tap = the whole column) beside the progress (cutting clock that stops while paused, layer, pass, packets sent, est small). After the run, the **result** with the camera's end photo and a still from every pause.
- **The drawing** on black with the 150 × 150 field inset; **layers** in run order, one line each (value + faint unit), path and wobble/fill small beneath (`?demo` shows nine made-up layers).
- **Pause, measured** (`lmc/pause_test.py`, three runs 01:21–01:25): `StopList` holds the list, raio switches emission off itself, resume puts it back and `RestartList` continues in place; the board's status word says paused (0x228) or running (0x224). Tested from the page with resume and with cancel.
- **New commands**: `raio load <job>` (puts a job on the page, no laser), `raio still --note …` (a camera still). Contract between page and raio: `board/CONTRACT.md`.
- Warnings on the page: laser off USB, LightBurn holding the board, raio died, "after a stop a short red rectangle first".

## Milestone 1 · 2026-10-21 · "raio talks to the laser"
One day: research in the afternoon, the machine in the evening. **Phase 0 passed, every gate measured** (`PLAN.md` → Phase 0; `LOG.md` for the raw record):

- The board (BJJCZ LMC V4) identified, driven over USB from Python; the open protocol fits it.
- Red framing in LightBurn's frame; the laser fires on Edson's go and aborts in 7 ms; six-packet jobs streamed.
- Pulse width is nanoseconds, settled against a LightBurn mark side by side.
- **The field calibrated**: a commanded 80 mm measured 79.15 × 78.90; with raio's per-axis scale the next square measured 80.0 × 80.0. Every LightBurn part from this machine was 1.1–1.4 % small.
- The Z column is its own controller (the board's axis channels do not move it); the E-stop cuts the machine's main power; a host that disappears leaves the board finishing its buffer (whole jobs are sent anyway, by Edson's rule).
- Phase-1 software built the same night, without touching the laser: the `.raio` format, the LightBurn importer, fill, wobble, kerf, the planner, a preview, the CLI, and three side-by-side fixtures.
- A fixed bed camera (RaioEye, :8878) by the camera session.

**Rules in force** (Edson, 2026-10-21): red first, then his go, then fire; the red stays on until the go; whole jobs; the E-stop is the backstop; raio no safer than the standard software; text and drawing do not live in raio; time only logged.

## The folder

| | |
|---|---|
| `PLAN.md` | what raio is, architecture, phases with measured gates, safety rules, decisions |
| `LOG.md` | every live action on the machine, newest first, with its raw result |
| `MACHINE.md` | the B6 as raio sees it: what it can send, read, and not reach |
| `FORMAT.md` | the `.raio` job file |
| `BACKLOG.md` | later, by value (Z hardware, focus gauge, fans, door, rotary…) |
| `lmc/` | **the driver**: `lmc.py` (connect, init + lens correction, lists, ports, axes, abort, pause-aware waits, go/stop/pause/armed flags, per-axis `calibration.json`); test scripts: `probe.py` (read-only), `frame_test.py` (red), `mark_test.py` (line, abort, squares, pwrow, square: red until go, then fire), `pause_test.py` (pause/resume, measured), `axis_test.py`, `lift_probe.py`, `usbpull_test.py` |
| `job/` | **the software between a drawing and the board**: `model.py` (`.raio`), `lbrn.py` (LightBurn importer + defaults table), `geom.py` (fill, wobble, kerf, flattening), `plan.py` (job → board packets, stats, SVG/PNG preview); `README.md` explains each |
| `raio.py` | the CLI: `import` · `show` · `plan` · `frame` · `mark` (red until the go; pause/cancel from the page) · `load` (a job onto the page) · `still` (a camera still) |
| `board/` | **the page** (:8877): `index.html`, `server.py` (frame/fire start `raio.py mark`, pause/stop flags), `CONTRACT.md` (files, flags, endpoints), `UI-BRIEF.md` (how the page is used and why), `samples/` (fixtures for testing) |
| `tests/` | unit tests, `import_report.py` (run it over your own LightBurn files), LightBurn test-file generators (`lbrn_square.py`, `lbrn_pwrow.py`), `sxs/` the side-by-side fixtures, `ui/` the many-layer low-power job for testing the page (`make_many_layers.py`) |
| `cam/` | the bed camera: RaioEye.app, `cam.py`, notes |
| `research/` | the reports (protocol, machine, safety, focus and Z, camera), the teardown notes, the parked USB tap |
| `logs/` | one JSON per probe and run, end photos (local only, not in git) |
| `serve.sh` | renders the md pages and asks the iPad runner to restart the board on **:8877** (by hand when the runner is down) |
