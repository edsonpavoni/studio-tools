# raio · plan

*Raio is the studio's own software for the B6 MOPA fiber laser: the sheet under the head seen from above, the job drawn on it in millimetres, the focus plan beside it, and one word: go.* Written 2026-10-21 from six research reports in `research/` (studio history, protocol, machine, safety, focus/Z, camera) and a first live session at the machine the same afternoon. The parallel is forno: cravado designs, forno prints, raio cuts and engraves. LightBurn is retired the day raio reproduces the studio's locked recipes.

Sigil: *best* (Alchemy set, The Noun Project #556659). Port **8877**. Folder `studio/raio/`.

> **Milestone 1, 2026-10-21 20:16: phase 0 passed, every gate measured; the field calibrated; phase-1 software built. See `README.md`.**

---

## 0. What the research settled (one screen)

1. **The board is open to us.** The B6 is driven by a BJJCZ **LMC V4** USB galvo card (USB `9588:9899`, "USBLMCV4", serial 20200507, four bulk endpoints, no macOS driver claims it). Its protocol is reverse-engineered and public: 12-byte commands, 3072-byte job lists, one status word. The meerk40t/galvoplotter code is MIT and vendorable. Confirmed three ways: the open code, EZCAD's own DLLs on disk, and a captured EZCAD session. (`research/02-protocol.md`)
2. **ComMarker Studio is not a path.** Its Mac build only opens the Omni X controllers (`04B4:1004`, `7580:0101`); on our machine it says "Device is invalid". Verified in its binary and live on 2026-10-21. Its Z-per-pass and autofocus design (an external stepper axis pulsed by the galvo controller plus a sensor on a GPIO) is still the pattern to copy.
3. **The Z column is its own machine.** Stepper, 8 mm screw, 200 pulses per turn (0.04 mm per pulse, 12.5 mm/s), a triangulation sensor that works 120–280 mm and sits off-centre, a touch panel that stores the parameters "on the control board". Nothing documented lets a computer drive it, and LightBurn pulled its EZCad2 Z control from 2.1. The USB board does have an extended-axis motor channel (opcodes 0x26–0x2A), wired to the rear **Rotary** port. Whether the column listens to it is the one hardware unknown, and three emission-off tests settle it. (`research/03-machine.md` §3, `05-focus-z.md` §3)
4. **Focus is tighter than theory.** Computed spot ≈ 50 µm, Rayleigh range ≈ ±1.6 mm, but the studio's cuts behave as if the usable band were **±0.3–0.5 mm**: 0.4 mm out of focus visibly slowed the stainless slot; 2.5 mm aluminium needed a 1 mm drop by hand. The lens is not telecentric: lowering 1 mm shrinks the pattern by ≈ 0.5 %, enough to open a second kerf on a 90 mm part. Z-stepping must scale XY. (`05-focus-z.md` §2)
5. **Focus was never in a file.** None of the 103 `.lbrn2` files records focus per layer; 30 set LightBurn's project-level material height, which never moved the head. Every Z move in the studio's history was by hand and, at best, prose. Ring cut #1 moved Z twice with no record and cannot be reproduced. (`01-studio-history.md`)
6. **The recipes disagree with each other.** Copper 1.1 mm "LOCKED" exists as Global 80 / wobble 0.30 and as Global 100 / wobble 0.4; the saved stainless file holds 14 × 10 passes where the recipe says 100 × 1; 2.5 mm aluminium has five recipes. `research/materials.json` holds every recipe found, with status and source, for raio's library to start from.
7. **LightBurn saves only what differs from the device default**, so a missing field means "whatever the default was that day". Raio writes every field, always, and its importer carries a defaults table.
8. **Safety is software today.** Open frame, no enclosure, no door or stop input configured, the foot pedal set to start jobs under LightBurn/EZCAD, 0 % power still ≈ 100 mW at 1064 nm, and a documented LightBurn pause that left a beam on at 95 %. Raio is the main safety layer and must be stricter than LightBurn. (`04-safety.md`)
9. **Field is 157.5 mm in every config**, against a 150 mm lens, and LightBurn's correction-file path on this Mac is broken, so today's jobs may be running uncorrected. Raio uploads `jcz15.cor` itself and checks a 100 mm square.
10. **The camera is ours to build.** No vendor camera exists for the B6 and LightBurn's camera does not work on macOS. A UVC webcam on the head, a 1064 nm blocking filter, and a calibration grid the laser engraves itself give ≈ 0.1–0.2 mm placement. About $200–280 in parts. (`06-camera.md`)

---

## 1. What raio is, and is not

**Is.** One program on this Mac, pages on the iPad, in the forno pattern:

- **Next**: the job that is about to run. Material photo with the job outline on it, the recipe by name, the real total pass count, estimated time, the focus plan, the pre-flight list, and the red-light frame already traced. It waits for *go*.
- **Now**: the running job. Pass N of M per layer, time left, the camera frame between passes, the Z position, one Stop that is real.
- **The library**: every recipe with material, thickness, status (locked / proven / proposed / rejected), breakthrough pass count, focus note, removal curve, provenance.
- **The log**: every run as fired, including mid-run changes and every Z move.
- **Three doors in**: cravado (`make: cut | engrave` parts of an assembly), trilha (a board), and a file dropped in chat (`/raio <file>`: `.lbrn2`, `.svg`, `.dxf`).

**Is not.** A LightBurn replacement for the world. No node editing, no fonts beyond outlined text, no CO2, no rotary in v1 (the R5 comes back as a later phase on the same axis channel), no image engraving beyond one dithering mode, nothing it cannot prove safe.

**Naming (jeitinho).** Raio is a laser bench in the dark: nigredo, the camera frame is the only light, aurum for the job outline. The go page is a board (six vessels allowed); the placement page, where the job is dragged over the camera image with a finger, is an instrument (elements only, 44 px, its own face). `data-face="nigredo"` for both; the bench does not follow the sun.

---

## 2. Architecture

```
studio/raio/
  README.md  PLAN.md  BACKLOG.md  LOG.md         the tool's own record
  research/                                      the six reports + materials.json (2026-10-21)
  lmc/        probe.py                           the driver: pyusb; vendored galvoplotter (MIT)
              lmc.py      connect · init(cor) · lists · ports · axis · status · abort
              cor.py      jcz .cor reader → 65×65 table upload
  job/        model.py    a Job: layers → shapes (mm) + recipe ref + passes + stop conditions
              lbrn.py     importer for the studio's .lbrn2 dialect (trilha's writer + LightBurn's saves), with the defaults table
              svg.py dxf.py
              plan.py     Job → list commands: hatch, wobble, passes, per-pass Z schedule, XY scale per Z
  library/    materials.json (from research) · recipes.py (envelope checks, pulse-width list, freq cap)
  focus/      focusplan.py (the schedule) · actuator.py (board axis | rotary-port table | column) · curves/
  cam/        cam.py (find · snap · calibrate · ortho) · RaioEye.app source · calib.json
  safety/     gate.py   the rules of 04-safety.md as code: frame-before-start, arming, presence, stop-verify
  board/      server.py (:8877) · index.html (Next/Now) · place.html (instrument) · studio.css (synced)
  logs/       probe-*.json · run-*.json
  tests/      pulse-width discriminator, 100 mm square, staircase, removal curve: scripts + results
```

- **Driver.** `galvoplotter`'s controller vendored and trimmed (MIT notice kept); Balor (GPL) as reference only. EZCAD's real sequences from the captured session are the default: init tail `0x3A, 0x22(0x7FF), 0x3A`, `ExecuteList` after the second packet, MO switched inside the list around each shape with the 8 ms wait, abort = StopExecute → MO off → ResetList → dummy packet → verify.
- **Everything geometric is software.** Hatch fill, wobble (a polyline the board marks), passes, kerf offset, even-odd fill of nested loops (trilha's copper islands), XY scaling per Z step. The board gets only jumps, marks, speeds, delays, power, frequency, pulse width, port writes.
- **One pass concept.** A layer has `passes`. There is no second multiplier anywhere. The total is shown before go.
- **Job JSON is the native format.** `.lbrn2` is imported, never written. trilha gains a `--raio` output so it can express what LightBurn cannot: stop the cutout at release, pause between layers, cooling dwell, which layers are reference-only.
- **Z is an actuator interface**, not a feature of the board: `move_mm(dz) → wait → position`. Three implementations (board axis, rotary-port table, column takeover); the focus plan does not care which.
- **Camera is a separate process** (`RaioEye.app`, its own camera permission, like OracleEars) serving `/snap.jpg` and `/live.mjpg` to the board page. Capture is off while a job is armed or running.
- **Presence.** The board page asks "still here?" on the interval the material sets (5 min metals, 2 min FR4). No answer → stop.

---

## 3. Phases and gates

Every phase ends with a gate that is a measurement, not an opinion. Nothing fires before phase 0's gates.

### Phase 0 · Machine truth (this week, at the machine, laser mostly off)

| # | Test | Laser | Reads | Status |
|---|---|---|---|---|
| 0.0 | USB descriptors | off | board identity | ✅ 2026-10-21 16:19: USBLMCV4 9588:9899, EP 0x01/0x81/0x02/0x88 |
| 0.1 | `lmc/probe.py`: serial, version, list status, ReadPort, galvo pos, axis pos 0/1, source status | off | the board signature (compare `0000238409002002` from the forum), READY/BUSY bits, idle port word | ✅ 16:32: signature `0000218409002002` (sibling of the forum board), READY, galvo centred, axes at 0, idle port 0xC012 (`LOG.md`) |
| 0.2 | `probe.py --poll 20` while pressing the pedal | off | the pedal's word and bit | |
| 0.3 | Photos: back panel ports, head panel, column cable and its Type-C, source label, goggles marking | off | the Z wiring question, the JPT model and pulse-width list, OD rating | ✅ 16:31 back panel + column foot: the column runs on one Type-C into the base (path A still open). Source label and goggles: pending |
| 0.4 | `init()` with `jcz15.cor` → red-light rectangle 50 × 20 mm, then an L | red | X/Y mapping and sign, field scale, that framing draws a shape (not the forum's single line) | ✅ 17:24 rectangle drawn, L measures 40 × 20; **19:03 corrected by the side-by-side with LightBurn: raio's frame = LightBurn's (axes swapped vs the raw galvo words, no flips)** (`LOG.md`) |
| 0.5 | Red frame at ±70 mm corners | red | the .cor works, edges straight | ✅ 17:29: straight, ~140 mm, fits (`LOG.md`) |
| 0.6 | **Axis test**, R5 unplugged, LED or meter on the Rotary port: `MoveAxisTo` +200 pulses on axis 0, then axis 1 | off | **does the column move? does the Rotary port pulse?** → Z path A or B | ✅ 16:38: board moves both axes correctly (50 and 200 pulses, counted and timed); **the column never moved**. Path A closed. Rotary port not yet instrumented (`LOG.md`) |
| 0.7 | One 1 mm line on scrap steel at 10 %, 500 mm/s, 30 kHz, 200 ns; then a 20 s pattern and STOP | on, low | first mark; abort latency; MO closed afterwards | ✅ 17:42: the laser fires from raio, where the red frame is (seen on aluminium, no mark at 30 %); abort at 20 s → board idle in 7 ms, MO closed, port 0 (`LOG.md`) |
| 0.8 | Pulse-width discriminator: two 5 × 5 mm squares, 4 ns vs 200 ns, vendor layout first | on | which 0x8026 word layout the firmware honours | ✅ 19:12: **nanoseconds, vendor layout** `[0x8026, 0, ns]`, confirmed against LightBurn's 200 ns square side by side (after a detour caused by the rotated frame; `LOG.md`) |
| 0.9 | USB-disconnect test from LightBurn (long low-power hatch on steel, pull the cable at 1 min, E-stop ready) | on, low | what the board does with a buffered list when the host dies; stop latency | ✅ 17:47 (from raio, not LightBurn): **the board keeps marking its buffered list after the host vanishes**, until the list ends or the E-stop. Decision: send whole jobs anyway; E-stop is the backstop (`LOG.md`) |
| 0.10 | 100 mm calibration square | on | field scale 157.5 vs 150; kerf | ✅ 20:16: 80 mm square measured 79.15 × 78.90 → per-axis scale 1.0107 / 1.0139 (`lmc/calibration.json`); verification square 80.0 × 80.0. True reach 155.8 × 155.3 mm; every LightBurn part was 1.1–1.4 % small (`LOG.md`) |

**Gate 0:** ✅ **passed 2026-10-21 20:16.** Signature read; red frame correct in LightBurn's frame; pulse width = ns; abort 7 ms; host loss = board finishes its buffer; E-stop cuts main power; the column is not on the board (Z path: button lines or hardware in the tower); field calibrated per axis.

### Phase 1 · Driver and CLI (started 2026-10-21 evening)

*Edson's decisions, 2026-10-21 19:35:* learn fill, wobble and the rest by writing LightBurn files, reading them, implementing, and comparing raio's mark with LightBurn's on the same scrap (LightBurn's mark is the source of truth); an agent goes as far as it can with the least interaction. The job file is **`.raio`** (`FORMAT.md`). **Fill and wobble first. Layer order and settings are what the preview shows before the go.** Text and drawing tools do not live in raio: like forno, it receives a finished drawing and makes the adjustments needed to cut it (text must arrive outlined). Progress and pause: minimal. **Time: only logged for now, shown small; estimates come later from the logs.** Images and the rotary: backlog.

`raio frame <job>`, `raio mark <job> --go`, `raio stop`, `raio status`. Imports trilha's `.lbrn2` and LightBurn's saves. The safety gate in code from day one: no mark without a frame of the same job; arming confirmation shows material, recipe, total passes, time; pulse width from the source's list only; frequency capped per width; every run logged.

**Gate 1:** three locked recipes reproduced side by side with LightBurn on the same scrap (copper engrave fill, aluminium 1.1 mm cut, a trilha coupon) and judged equal or better by Edson. A hatch, a wobble cut, and a 100-pass job through the same code path.

### Phase 2 · The board page (:8877, iPad)

forno's skeleton: Next (outline on the material photo or on a grid until the camera exists, recipe, passes, time, focus plan, checklist, frame-done stamp, *go*) and Now (pass counter, time, Stop, presence prompt). `/raio <file>` from chat puts a job on Next. Registered in `studio/ipad/tools.json`, sigil on the hub.

**Gate 2:** Edson runs one real job (a wall label or a Witness lid engrave) from the iPad without opening LightBurn.

### Phase 3 · The camera (re-scoped by Edson, 2026-10-21 18:19)

*"For now I just want that B6 have a camera the same way the P2S has a camera, so its tool can access important info about the work when it needs."* A fixed view of the bed from a clamp arm on the frame (not the head): `RaioEye.app` with its own camera permission, `/snap.jpg` and `/live.mjpg`, `cam.py snap` for any session; the photo on the Next page before go and an end photo after, exactly as forno uses the P2S camera. No focus gauge, no dot laser, no calibration plate, no lights, no hub for now (the larger design is shelved in `cam/BUILD.md`). `armed.flag`: no frames while the laser-enable bit is high. Owned by the camera session (`HANDOFF-camera.md`, `cam/README.md`).

**Gate 3:** a photo of the bed on the Next page before every go, and one after the job, from the iPad, with the laser connected through the same Mac.

### Phase 4 · Focus and Z (the reason raio exists)

Depends on the path from gate 0:

- **A. Column on the board.** ❌ Closed 2026-10-21 16:38: both axis channels move on the board, the column never moves.
- **A2. The base's button lines (new, from a Reddit teardown photo of the base board `Laser_SW_V05`, 2026-10-21 16:48).** The base's Up/Down buttons enter that board as switch contacts (UP_KEY / DOWN_KEY / GND) and leave it as two 5 V lines (UPLD / DWLD with 5 V and GND), almost certainly the Type-C to the column. Raio presses the buttons electrically: an optocoupler on each line, timed, from the laser board's output port or a $5 microcontroller; the panel reading (and the phase-3 focus gauge) verify each move. ≈ 0.1 mm at 12.5 mm/s. Reversible, nothing cut. **Confirm first with a USB-C breakout and a multimeter on the Type-C: which pins are power, which go high on Up/Down.** The two lines carry no position back, so the focus number stays on the panel (hence the gauge).
- **B. Table on the Rotary port.** ❌ Dropped (Edson, 2026-10-21 18:19: not convinced by a machine that changes the height of the base when the laser already has a moving head). Z stays with the column: A2 or C.
- **C. Column takeover.** A relay on the column stepper's four wires between the panel driver and an external driver, or a small board of ours inside the tower. **Edson, 2026-10-21 18:21: "to achieve Z we will need to make a small hardware and put inside the tower, or find out if the tower USB does carry data."** So the order is: breakout test on the Type-C first (data? button lines?), then A2 if the lines are there, else C.

Then the focus plan (`05-focus-z.md` §4): z0 from the panel or a gauge, a schedule of `{z, passes}` blocks, XY scale `1 + |z|/210` per block, Z moves only between lists with the laser verified off, soft limits, return to z0 from above, every move logged. Experiments in order: sign check (fills the blank in `METAL-RING-LASER-CUT.md`), staircase +0.5 → −1.0 mm in 0.24 mm steps at centre and at r = 45 mm, removal curve d(N), telecentricity square, then the A/B of 2.5 mm aluminium discs: the old "150 @ 0 / 50 @ −1 by hand" against a raio plan.

**Gate 4:** a 2.5 mm aluminium 20 mm disc released by a raio plan with fewer passes than the hand recipe, and a 304 ring slot cut with no hand Z move.

### Phase 5 · Handoffs and retirement

- cravado: a part with `make: cut | engrave` whose rows are green exports a raio job (outline + engrave layers + material + thickness) to raio's Next, stamped with the ledger hash; raio refuses an unstamped job the way forno refuses an unstamped STL.
- trilha: `circuit2lbrn.py --raio` writes the job JSON with its stop conditions; the five human checks in LightBurn become raio checks (layer table vs recipe, open loops, labels on hole layers, holes interleaved, board off the bed in the checklist).
- `/raio` skill: `/raio <file>`, `/raio status`, `/raio stop`, `/raio library <material>`.
- Retire LightBurn: parity list ticked (fill, wobble, passes, text outlines, variable text for numbered editions, rotary as phase 6), `.lbrn2` archive importable, the prefs and the material library exported to `research/` for the record. Then the licence lapses.

### Phase 6 · Later
R5 rotary on the same axis channel (never together with a Z table). Hardware interlock: a bench stop button on an LMC input and a contactor on the source's 48 V that works when the Mac is dead; an enclosure with a door switch (the largest single risk is the open frame). A triangulation height sensor for warped sheet. A coaxial view of the kerf.

---

## 4. The safety rules raio enforces (summary; full text `research/04-safety.md` §2)

1. **Red first, then Edson's go, then fire** (Edson's rule, 2026-10-21 18:05: "only send laser after a go; before a go you always just send the red marks so I can fit the material; a button I press or a GO here"). Raio does everything up to the red preview on its own and holds it as long as needed; the laser fires only on a go given for this job, by the GO button or the word in chat. A general permission earlier does not carry over. No test-fire button; a test is a small job through the same gate.
2. **Arming is explicit.** One deliberate confirmation showing material, recipe, total passes, time, focus state. No shortcut fires.
3. **Parameters are validated.** Pulse width from the source's discrete list; frequency capped per width and the real average power shown; power, speed and passes inside the material's envelope unless a reason is typed.
4. **Stop is real.** Abort the list, MO off, laser bit low, then read back and show STOPPED only when the board confirms; otherwise, in red: press the E-stop. Pause never leaves a job loaded; a checkpoint resumes as a new job from a pass index.
5. **Z never moves while the laser can fire.** Between lists only, after the board reports idle; soft limits; logged.
6. **Nobody leaves.** Presence prompt per material; breakthrough checkpoints (stainless at 40–50, PCB cutouts at pass 5); no job over 30 min without checkpoints.
7. **Environment declared.** Material from the list (PVC, vinyl, PTFE, unknown plastics blocked); air assist and extraction confirmed; extraction mandatory for stainless, brass, FR4, plastics; lens cap check per session; the pedal off unless the session says otherwise.
8. **The whole job is sent, as LightBurn does** (Edson, 2026-10-21 17:50, after the USB-pull test showed the board finishes its buffer alone: "always send the whole job; lasers need caution and we always have the emergency button; raio is not to be made far safer than the standard software"). The E-stop is the backstop for a dead host (tested 2026-10-21 19:42: it cuts main power to everything, board included); the operator stays at the machine; the Mac holds a no-sleep assertion during jobs.

---

## 5. Decisions for Edson

1. **Z path preference if the column is not on the board:** a table under the work on the Rotary port (clean, no opening the machine, but the rings in the vise need the room), or taking over the column motor (one relay, the head opened, autofocus lost in raio mode)?
2. **Buy the camera kit now** (≈ $250) so phase 4 can start as soon as the bracket is measured?
3. **The open frame.** An enclosure with a door switch, or at least a bench stop button and a source-power contactor, is the only stop that works when the Mac is dead. Is that a purchase this quarter?
4. **Field size:** keep 157.5 mm (parts come out right today) or recalibrate to the lens's 150 after the square test?
5. **Presence interval:** 5 min for metals and 2 min for FR4 as proposed?

## 6. Open questions only Edson can answer (from `01-studio-history.md` §6, the ones that change the library)

The 12 rings: 100 × 1 or 14 × 10? Copper 1.1 mm: G80 / 0.30 or G100 / 0.4? Which of the five 2.5 mm aluminium recipes is real? Was pulse width actually being sent in 2025? The aluminium engrave settings "you have working" (OW6/OW9: 300 mm/s, 100 ns, ×9, 0.03?). Whether 0.7 mm brass was ever cut. Air assist: by hand or by an output bit? Which fume extractor?

---

*Research base, all 2026-10-21: `research/01-studio-history.md` (timeline, 103 files, pains), `02-protocol.md` (board, commands, test plan, skeleton), `03-machine.md` (spec, controls, Z, source, lens), `04-safety.md` (hazards, rules, checklist), `05-focus-z.md` (physics, Z paths, focus plan), `06-camera.md` (hardware, calibration, plumbing), `materials.json` (every recipe found), `tap/` (a parked USB tap).*
