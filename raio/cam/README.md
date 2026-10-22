# raio · cam

*The eye of raio: a camera over the B6's bed, the way the P2S has one. A picture of the work before a job, after it, and whenever a tool or a session needs to see what is under the head.* Phase 3 of `../PLAN.md`, re-scoped by Edson 2026-10-21 18:19. The research behind it is `../research/06-camera.md`; the earlier, larger design (focus gauge, mm-accurate placement) is kept in `BUILD.md` as a shelf, not a plan.

This session never talks to the laser board and never fires the laser.

**Scope (Edson, 2026-10-21 18:19):** "For now I just want that B6 have a camera the same way the P2S has a camera. So its tool can access important info about the work when it needs." No focus gauge, no dot laser, no calibration plate for now. One camera, one still on demand, a live view while placing material, the picture on raio's Next page before *go* and an end photo after, and `cam.py snap` for any session, exactly as `p2s.py snap` is used today.

**Status 2026-10-21 18:30:** **RaioEye is installed and running** (`~/Applications/RaioEye.app`, LaunchAgent `com.edsonpavoni.raio-eye`, port **8878**), on the MacBook camera until the ELP arrives. Tested: a still in 2 s, live MJPEG, a still during live in 0.1 s, `armed.flag` closes both (HTTP 423), the camera grant is credited to the bundle and inherited by ffmpeg. Buy list below, waiting for Edson's approval.

```
http://localhost:8878/            the eye: live view, laser/camera state, a still button (iPad: <your-mac>.local:8878)
GET /snap.jpg [?full=1]           a fresh still (from the live stream if one runs; ?full=1 stops it for a full capture); header X-Snap-Path = the saved file
GET /live.mjpg                    multipart MJPEG, 1280x720 at ~10 fps, one ffmpeg shared by all viewers, stops 10 s after the last leaves
GET /state.json                   {laser, camera, camera_name, armed, live, snap, snap_time, port, ts}
423 Locked                        on /snap.jpg and /live.mjpg while ~/Library/Caches/raio/armed.flag exists
```
Frames: `~/Library/Caches/raio/snaps/`. Log: `~/Library/Logs/raio-eye.log`. From any session: `curl -s localhost:8878/snap.jpg -o bed.jpg`, or `cam.py snap` from Terminal.

---

## 1. Buy list (for approval), reduced 2026-10-21 18:25

Prices as listed 2026-10-21, USD, before shipping; verify at checkout.

| # | Item | Exact pick | Link | ≈ USD |
|---|---|---|---|---|
| 1 | **Camera** | ELP 8 MP IMX179, **2.8–12 mm manual varifocal, manual focus**, USB 2.0 UVC, model `ELP-USB8MP02G-MFV(2.8-12)`. The zoom frames the bed from wherever the mount ends up; focus is set once and glued. | [ELP store](http://www.webcamerausb.com/elp-8mp-3264x2448p-sony-imx179-sensor-manual-focus-hd-usb-cctv-camera-for-industrial-machine-vision-webcam-with-cs-mount-zoom-lens-2812mm-p-375.html) · same model on Amazon ≈ $80–90, faster | 67 |
| 2 | **Mount** | ~~magic arm~~ Printed on the P2S and/or cut on the B6 (Edson, 18:41: "we can cut or print!"): a clamp on the Z column with a short boom and a cradle for the camera board, through cravado. Studio part `innomaker-u20cam-720p` on the shelf since 18:45; the column and the bracket wait for the caliper. | — | 0 |
| 3 | **1064 nm filter** | Schott KG3 Ø25 × 2 mm, Edmund #19-326, in front of the lens. Insurance against a specular hit from a polished part; cheap next to the camera. | [Edmund Optics](https://www.edmundoptics.com/p/schott-kg3-25mm-dia-2mm-thick-colored-glass-heat-absorbing-shortpass-filter/45801/) | 55 |
| 4 | USB 2.0 extension, 3 m, shielded, with a ferrite | To reach the Satechi hub or the Mac | Amazon | 9 |
| | **Total** | | | **≈ 131** with the ELP and filter · **≈ 64** with Edson's InnoMaker and the filter · **≈ 9** InnoMaker, no filter |

Dropped from the first list (2026-10-21 18:19): the green dot laser, the LED strips and channels, the polariser film, the powered hub (the Satechi carries the laser today; a hub returns only if a long job ever drops), the cover slips. They stay in `BUILD.md` if the gauge ever comes back.

Mount position to try first: clamped to the Z column's side or to the frame behind the bed, camera about 400 mm above the bed, looking down and forward so the head sits at the top of the frame and the bed fills the rest. The autofocusing head moves; the camera does not, so the view is of the bed, like the P2S's chamber camera.

## 2. Shelved 2026-10-21 18:19: the focus gauge (kept for the record)

**The gauge is laser triangulation read by the head camera. The red pilot is the check, not the measurement.** Camera and green dot module are both rigid on the head. The dot's position in the camera image is a monotonic function of the surface height under the head; one calibration against the staircase (`calib/gauge.json`: pixel → mm, plus the zero) turns it into focus in millimetres. That keeps the gauge independent of the laser board: raio never has to switch the pilot on to read focus, and the reading is live at camera frame rate. The pilot parked at the field centre is used once to confirm that the gauge's zero is the beam's point, and any day as a drift check.

Geometry, with the brief's figure of ≈ 0.17 mm of gap per 0.1 mm of height:
- that is tan θ ≈ 1.7, i.e. the dot module **≈ 30° above the work surface (≈ 60° from the beam axis)**. Steeper (closer to vertical) gives less sensitivity and more range; this angle is the right trade for ±3 mm of range on a 0.09 mm/px image: 0.1 mm of height = 1.7 mm on the surface ≈ 19 px, so with sub-pixel centroiding the gauge resolves ≈ 0.01 mm; the staircase's ±0.1 mm goal is comfortable.
- the dot lands on the beam point only at zero; off zero it walks along the module's azimuth, which is how the sign is read. Mount the module so that this walk is along the camera's long image axis.
- the module's focus is set so the dot is smallest at the working distance (≈ 250 mm from the head, measured at the machine); glue the ring after.
- a bright polished surface shows the dot as a specular smear: the reading uses the green channel minus red/blue, a threshold, and the centroid of the largest blob; the cross-polarised light test (item 7) tells whether a polariser in front of the camera helps.

**Calibration hook** (exposed for the raio session): `cam.py gauge --zero` records the current dot position as zero; `cam.py gauge --calib <staircase.json>` takes a list of `{z_mm, snap}` pairs from the staircase run and fits pixel → mm. Both write `calib/gauge.json` with date, camera name, mount version. (Code lands with the hardware.)

## 3. Experiment 1, reduced: what to do the next time Edson is at the machine

Camera not here yet, so the first pass uses the iPhone as Continuity Camera (it shows up in `cam.py list` as "Pavoni Camera"). It answers the two questions that do not depend on the ELP: what brass and copper look like at working distance under the bench light, and whether the red pilot is visible to a consumer camera with an IR-cut filter. The ELP repeats it when it arrives.

1. Head autofocused on a brass scrap, then a copper one, then a Witness-grade polished piece. Phone held ≈ 250 mm above the work, next to the lens housing, looking slightly inward. `cam.py snap --cam "Pavoni Camera" --out exp1/<material>-<light>.jpg`.
2. Same three with the two sides of the field shaded by a white card (a stand-in for the diffused strip).
3. **Red pilot:** the raio session parks the pointer at the field centre for 60 s (request below); `cam.py snap` of the dot, then `cam.py burst --seconds 1` while raio traces the 50 × 20 mm red rectangle: does the max-stack show the whole rectangle?
4. Pass: 200 × 200 mm fits the frame, the dot is visible on brass and copper, the stacked rectangle is readable.

Results and the photos go in `exp1/` with a line in the log at the bottom of this page.

## 4. Mount (a clamp arm first; cravado only if it creeps)

Two studio parts on the head: the camera cradle (lens as close to the F-theta housing as it allows, tilted ≈ 13° toward the field centre, KG3 + window in a slot in front of the lens) and the dot-module clamp (Ø12 mm, ≈ 30° above the surface, azimuth along the camera's long axis, both angles fixed by the print, not by a joint). Per `studio/cravado/PROTOCOL.md`: the head housing is measured with Edson's caliper first (width, depth, the lens ring diameter and height, the free faces and their screw holes), then designed in cravado, then printed by the 3dprinter session. Nothing is sliced before the mating dimensions are measured and anchored in the cravado ledger.

## 5. Plumbing (built 2026-10-21 18:23)

`RaioEye.app` in `~/Applications`: a Swift stub like `OracleEars.app`, `LSUIElement`, `NSCameraUsageDescription`, a menu-bar eye (plain = serving, red = laser armed, yellow = server down or camera missing). At launch it asks macOS for the camera once, then runs `cam.py serve --port 8878` from a copy in `~/Library/Application Support/RaioEye/` (a login app may not read Dropbox; `install.sh` copies `cam.py`, `index.html`, `studio.css`; the installed `config.json` is the live one and is never overwritten). The server owns the ffmpeg capture and answers the endpoints above; the raio Next page fetches `/snap.jpg` from it. **The eye stays open during jobs** (Edson, 2026-10-21 19:06: "should it be the opposite?"). The no-frames-while-firing rule was written for a camera on the head beside the lens (`06-camera.md` §2.4: a flat polished part reflects the beam back into the zone within about ±160 mm of the lens axis at head height). The bed camera sits on the frame, far and oblique, outside that cone, and watching the job is what it is for, as forno watches a print. `armed.flag` (written by the raio driver while the laser-enable bit is high, removed on `safe_idle`) is now shown as state, "laser firing", on the page and in `state.json`; `"shutter_when_armed": true` in `config.json` restores the old rule for a head-mounted camera. What stays: the camera image never replaces goggles, and no camera goes inside the reflection cone above the bed without the KG3 filter. A 1064 nm glint shows on this sensor as a white bloom: useful as "the laser is on", and it may drive the auto-exposure down for a moment. Frames stay out of Dropbox (`~/Library/Caches/raio/snaps`).

## 6. Requests to the raio session (reduced 18:19: only the red pilot test remains for now)

1. **Red pilot at the field centre, 60 s, on request** (for experiment 1 step 3 and for every gauge zero check later). And the 50 × 20 mm red rectangle traced for ≈ 3 s while `cam.py burst` runs.
2. **Engrave `jobs/calib-plate.json`** when the camera is mounted: 121 filled dots of 1.2 mm on a 13 mm pitch, three 2.5 mm orientation dots at three corners, on dark scrap, autofocused, and the plate not moved afterwards.
3. Later: the staircase run saved as `{z_mm, snap}` pairs so the gauge can be calibrated against it.

## 7. Files

| File | What |
|---|---|
| `cam.py` | `list` · `usb [--watch]` · `snap` · `burst` · `config`. Stdlib + ffmpeg; numpy/OpenCV only for `burst` and the calibration. Runs in `~/.venvs/raio` (numpy, opencv-python-headless, scipy added 2026-10-21 17:56, additive; pyusb verified after). |
| `config.json` | The camera's name (substring of the AVFoundation name, never an index), its USB vid/pid once known, capture size and fps. |
| `RaioEye.swift` · `install.sh` | The app stub and its installer (`./install.sh`, `./install.sh --uninstall`). The stub is recompiled only when the Swift changed, because a new binary re-asks the camera grant. |
| `index.html` | The eye's own page on jeitinho (console, nigredo): live view, state line, a still button. |
| `jobs/calib-plate.json` | The calibration grid as mm geometry; shelved with the gauge. |
| `exp1/` | Experiment 1 photos and notes. |
| `calib/` | `camera.json` (homography + residual warp, LOO-RMS) and `gauge.json` (pixel → mm, zero) once they exist. |

## 8. Log

- **2026-10-21 17:52** Session opened from the raio session's brief (`../HANDOFF-camera.md`).
- **2026-10-21 17:56** `cam.py` first run: five AVFoundation devices listed by name; USB poll sees the board (vendor 0x9588, pid 0x9899) behind the Satechi hub, read-only. A still from the MacBook camera needs the exact frame rate the device publishes (30 fps; ffmpeg matches it literally), so 30 is the default.
- **2026-10-21 18:05** Buy list written (§1), gauge design proposed as camera triangulation with the pilot as check (§2), calibration plate job written (`jobs/calib-plate.json`).
- **2026-10-21 18:00** A still from the MacBook camera run from the editor's terminal hangs forever: the responsible app holds no Camera grant, so macOS neither asks nor denies, and ffmpeg waits (`06-camera.md` §4.2, now seen). `cam.py` names the cause after its timeout. Experiment 1 runs from Terminal (one prompt) until `RaioEye.app` exists. The raio session was briefed by message (what was touched, the three requests, the gauge design).
- **2026-10-21 18:01** Raio session's answer: `armed.flag` adopted in the driver (see §5); venv additions fine; the three requests accepted (pilot at centre or traced rectangle on request, one command on its side; the calibration plate engraved once the camera is mounted; staircase pairs when Z exists). Coordinates confirmed: field centre at (0,0), +x = machine right, +y = toward the column, galvo field 157.5 mm square with 150 mm usable. Any dot a job asks for names its pulse width in ns; raio maps it to the source's table. Gauge design (triangulation of the green dot, pilot only for the zero) agreed.
- **2026-10-21 18:19** Edson re-scopes: no machine that changes the height of the base (the head moves), and the camera is "the same way the P2S has a camera", a view the tool reads when it needs. Gauge, dot laser, calibration plate, lights and hub dropped from the plan; buy list cut to camera + arm + filter + cable (≈ $151). `BUILD.md` kept as a shelf. The raio session told, with his words.
- **2026-10-21 18:23** `RaioEye.app` built and installed; Edson allowed the camera at the first prompt (3 s after launch). ffmpeg as its child inherits the grant: a still through `/snap.jpg` in 2.1 s (1280 × 720 from the MacBook camera), `/live.mjpg` 23 frames in 4 s, a still during live in 0.12 s, `armed.flag` → 423 on both. Port 8878 told to the raio session for its Next page. The experiment the research called "3" (the grant is credited to the bundle and inherited) is therefore done early; what remains of it is the hub replug and the long job, once the ELP is on the machine.
- **2026-10-21 18:25** Raio session confirms: its Next page embeds `/live.mjpg` and fetches `/snap.jpg`; at the end of every job it drops `armed.flag`, GETs `/snap.jpg?full=1` and copies the file into its run log. **Limit to remember:** the interlock exists only when raio drives the board. Under LightBurn nothing writes `armed.flag`, so the eye stays open; until LightBurn is retired, keep the camera off the bed's reflection paths (the filter is the other half of that answer) or stop the live view by hand before a LightBurn job.
- **2026-10-21 18:41** Edson has an InnoMaker U20CAM-720P in the studio (720p, 102° HFOV, UVC): compared in `CAMERAS.md`; it works with RaioEye as is, the ELP stays the pick if the bed must be read. "We can cut or print": no clamp arm bought. The camera is now a cravado studio part (`studio/cravado/parts/innomaker-u20cam-720p/`, model built, six low-confidence dims as cards K1–K5 + lens Ø); the bracket is a raio part once the column is measured.
- **2026-10-21 19:06** Edson: "Why do we stop it while laser is running, should it be the opposite?" Yes for this camera: the eye stays open during jobs; `shutter_when_armed` (default false) keeps the old rule available for a head-mounted camera. 19:00: the InnoMaker from its first perch sees the whole machine (head, panel, bed, vise); the touch panel's digits are 5–6 px tall and unreadable; the ELP at 6 mm or a second board camera on the head would read them.
- **2026-10-21 19:10** Two fixes after the flip: the installer raced its own bootout/bootstrap and left no server for a minute (now it waits, kills orphans on the port, retries the bootstrap); the USB parser merged every device into one because ioreg prefixes tree lines with `|` (now "laser ✓ camera ✓" is read from the real nodes: InnoMaker 0x0C45:0x6367, board 0x9588:0x9899). The board is back on USB.
- **2026-10-21 19:45** "camera is frozen": a test capture from the shell opened the InnoMaker while RaioEye's live stream held it; the stream broke and the page kept its last frame. Rule: **only RaioEye opens the camera**; every still and stream goes through :8878, never a second ffmpeg. The page now reconnects by itself when the stream dies. UVC control reads/writes (`uvc-util`, below) do not open the video stream and are safe while it runs.
- **2026-10-21 19:44** The InnoMaker's adjustments, read from its USB descriptors and `uvc-util` (built from jtfrey/uvc-util, MIT, vendored in `vendor/uvc-util/`, binary in `~/Library/Application Support/RaioEye/bin/`): manual = the M12 lens focus ring (the only mechanical one). Software (UVC) = auto-exposure mode, exposure time 1–5000 (now auto, 156), gain 0–100, brightness −64…64, contrast 0–64, saturation 0–128, sharpness 0–6, gamma 72–500, hue, white balance auto / 2800–6500 K, backlight compensation 0–192, power-line frequency 50/60. No focus, zoom, or flip controls. Modes: MJPEG 1280×720 / 800×600 / 640×480 at 30 fps, YUY2 1280×720 at only 10 fps (ffmpeg must ask for 30 at 720p to get the MJPEG mode).
- **2026-10-21 19:53** Exposure and white balance locked (Edson: "yes, let's do it"). `cam.py uvc lock` lets the camera settle in auto, reads what it chose, writes it as manual values into the installed `config.json` (`uvc` block, `uvc_locked_at`) and applies it; RaioEye applies the block at every start and again when the camera comes back after a replug. Locked now: exposure 156, gain 0, white balance 4600 K, power-line 60 Hz, the rest at defaults. The locked frame has no clipped highlights (the auto frame had 11 % blown on the bed). Caveat: this camera reports the default values while in auto, so the lock may not be exactly what auto was showing; if the bed looks dark or bright, `cam.py uvc show`, then edit `exposure-time-abs` (1–5000) in the installed config and `cam.py uvc apply`; `cam.py uvc auto` goes back. Redo the lock when the camera has its final place and light.
- **2026-10-21 20:16** From the raio session, for the day placement comes back: the field is calibrated (80 mm square measured 79.15 × 78.90 at autofocus height; raio now scales 1.0107 / 1.0139 from `lmc/calibration.json`; verification square 80.0 × 80.0). True galvo reach 155.8 × 155.3 mm, working field 150. Any mm overlay takes raio's frame as truth (centre-relative); the scale moves 0.5 % per mm of head height, so a calibration plate is engraved at autofocus height. Raio saves the RaioEye end photo of every job into `studio/raio/logs/`.
- **2026-10-21 21:03** InnoMaker's UVC-SW-Manual.pdf read (24 pages, generic for their UVC line): Windows AMCap/PotPlayer, Linux v4l2/qv4l2/OpenCV/GStreamer, nothing for macOS beyond "supported". Useful: it confirms MJPEG 720p30 vs YUY2 720p10; "Low Light Compensation" is a vendor control (the Sonix extension unit, not reachable from uvc-util); the "Focus" control doubles as external-trigger enable on their trigger models (ours has none). **Two identical InnoMakers cannot be told apart by serial: ours reports the placeholder `SN0001`**; a second unit would be found by its USB port (locationID), so a panel camera of the same model would be pinned to a hub port, or be a different model.
