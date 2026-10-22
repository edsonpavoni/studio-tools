# 06 · Camera: a view of the work area for Raio

*Research 2026-10-21 for Raio, the studio's own control tool for the ComMarker B6 MOPA (60 W JPT, galvo, f = 210 mm F-theta, 150 × 150 mm field, electric Z, open frame, no camera today).*
*Goal: forno already shows a photo of the plate before Edson says "go". Raio should do the same for the laser: show the material under the head with the job outline drawn on top, let him drag the job to where it belongs, and confirm placement and focus before firing. One powered USB hub, one cable: laser and camera come up together.*

Tags used: **VERIFIED** (checked here, on this Mac or in a file), **WEB** (a source says so, linked), **INFERRED** (reasoned, not tested), **COMPUTED** (arithmetic shown).

---

## 0. The answer in eight lines

1. **Nobody sells us a camera for this.** ComMarker sells no camera for the B6 (WEB). LightBurn's own camera does not work on macOS (WEB). We build it from a UVC webcam.
2. **Buy:** an **ELP 8 MP IMX179 USB camera with a 2.8–12 mm manual varifocal lens** (≈ $80–90). Upgrade path: **Arducam 12 MP IMX477P USB 3 UVC, M12 manual focus** (≈ $150). Add a **Schott KG3 2 mm filter**, a sacrificial glass window, a diffused LED strip and a **powered multi-TT USB hub**. About **$200–280 in all**.
3. **Mount it on the moving head**, as close to the F-theta lens as you can, tilted about 13° toward the field centre. The B6 autofocuses the head onto the material's top surface, so a head-mounted camera always sees the work from the same distance. **One calibration then holds at every Z.**
4. **Calibrate by engraving, not by printing.** Laser a grid of dots at known galvo coordinates onto black-anodised scrap. OpenCV finds the dots. Fit a homography plus a smooth residual warp, so camera pixels map straight to *commanded* galvo mm. That mapping absorbs lens distortion, perspective and any error in the galvo correction file. ComMarker's own Mac app does the same thing (libCyclops `NPointsFFDCameraCalibrator`, see §1.2).
5. **What the iPad shows:** the camera frame, warped into machine mm (a top-down "orthophoto" at 0.1 mm/px). The job outline is plain SVG in mm on top of it, and dragging the job moves it in mm. Expect **≈ 0.1–0.2 mm** placement accuracy with the material at focus, getting worse by about **0.25 mm per mm** of height error (COMPUTED, §3.4).
6. **Capture with ffmpeg's AVFoundation input, selecting the camera by name/model, never by index.** This Mac already lists four video devices (VERIFIED). The capture runs inside a small app bundle, **RaioEye.app**, with `NSCameraUsageDescription`, built the same way as OracleEars.app.
7. **Hot-plug:** poll `ioreg` every 2 s for USB vendor **0x9588** (the laser; match on the vendor only, because the product ID changes with firmware state) and for the camera's VID/PID. The page shows "laser ✓ camera ✓".
8. **Safety rule:** the camera does not watch the beam. By default no frames are taken while the laser fires. A flat polished part can reflect the beam straight into a head-mounted camera (§2.4). KG3 plus the window make the camera a cheap consumable, not a protected instrument. A physical shutter is v2.

---

## 1. What exists

### 1.1 ComMarker hardware

- **No camera accessory exists for the B6, B4 or Omni X.** ComMarker's site search for "camera" returns nothing camera-related; the closest features are Omni X "LiDAR Focus" and "ImagePlus" (WEB: [commarker.com/search?q=camera](https://commarker.com/search?q=camera)). A B6 review says the machine, "rather than employing a camera, has a red dot and framing for positioning" (WEB: [makerhacks B6 review](https://www.makerhacks.com/commarker-b6-60w-mopa/)).
- **The B6 has one-touch autofocus.** You put the material down, press autofocus, and the head sets its own height (WEB: [B6 manual, manuals.plus](https://manuals.plus/asin/B0DL56J56C)). This matters a great deal in §3.5. Our own notes also record the panel reading "Real focal length 255.15 mm", to be treated as relative (VERIFIED: `studio/B6-Mopa/MATERIAL-SETTINGS.md` l.172).
- People who add cameras to ComMarker galvos do it themselves. One Omni X owner fitted a Waveshare IMX378 12 MP USB camera on the galvo head behind the lens. Lens calibration came out below 0.5 and the four-dot alignment went smoothly, but the overlay was only right "in the 'neighbourhood' of my corrected place". The thread has no fix (WEB: [Camera on Galvo Problem](https://forum.lightburnsoftware.com/t/camera-on-galvo-problem/184364)). **Lesson for Raio:** an error that varies with position cannot be fixed with an offset. It needs a dense mapping across the whole field (§3).

### 1.2 ComMarker Studio for Mac: it has a camera pipeline (VERIFIED by `strings`, app not touched)

`/Applications/ComMarker_Studio.app`, v1.0.42, bundle id `com.yourcompany.ComMarker_Studio`.
- **Info.plist declares `NSCameraUsageDescription`** and the app bundles **QtMultimedia**. Strings `CameraMgr::onImageCaptured`, `QCameraImageCapture::Error`, `Camera is not available`. **So it expects a generic UVC/AVFoundation webcam through Qt Multimedia, not a proprietary camera** (INFERRED from the Qt classes).
- **UI and workflow strings:** `pageCamera`, `widgetCamera`, `pushButton_CameraCal`, `CameraCorrection`, `label_CameraLocate`, `label_CameraLocate_Help`, `MarkSet::on_pushButton_CameraLocate_Refresh_clicked` ("camera locate": place the job using the camera), `pushButton_calib_start / _continue / _retry`, `leCalibSize`, `"Please perform a nine point correction first"`, `"Start calibration from 3x3 and clear all existing calibration"`, `Multi Point Calibration Files(*.gcor)`, `Box Calibration Files(*.bcor)`.
- **Camera-assisted focus:** `MarkSet::Vision_AutoFocus`, `AdjustHeightThreadDlg::visionAutoFocus`, `VisionAdjustHeightThread`, `focusOffsetX/focusOffsetY`. The camera appears to help set Z, perhaps by checking where the red dot or a spot lands. INFERRED; the strings alone don't say how.
- **Vision libraries.** `libCyclops 4.8.14` is a calibration library built on its own OpenCV ("lpOpenCV"). Its classes include `ShelteredChessBoardDetector`, `ShelteredCircleBoardDetector`, `CrossMarkDetector`, `CircleDetector`, `PinHoleCameraCalibrator`, `NPointsCameraCalibrator`, **`NPointsFFDCameraCalibrator`** (source `Calibration/FFD.cpp`: FFD = free-form deformation), `FlatFieldCalibrator`, `BinocularCalibrator` and `MultiViewCalibrator`. `libvision_3d_wzj` is OpenCV 4.6.0. `libBSL3DMark`/`libBslCal` look like BSL marking/calibration libraries.
- **What this tells us** (INFERRED): ComMarker's camera flow most likely runs like this:
  1. Run the galvo's 3×3 nine-point correction first.
  2. Engrave or place a chessboard, circle board or cross marks at N known points.
  3. Detect them (`CrossMarkDetector`/`CircleDetector`).
  4. Fit an N-point free-form deformation from camera pixels to field mm.
  5. Use "Camera Locate" to place the job on the live image.

  That is exactly the pipeline proposed in §3. The vendor arrived at the same design, which is good evidence for it.
- **What Studio is, and whether it drives our B6:**
  - Studio is ComMarker's **Omni X software**. Today's log shows defaults from `ComMarker_Studio_omnix_win_v1.0.21_20251119`. It is built on an **"LCS" SDK 2.1.8595** (`liblcsDI`, `LcsLmcParam`). Its `libtransfer.dylib` has `UsbTransfer` (libusb), `TcpTransfer` and `UdpTransfer`, and the main binary has `Board Type` and `Failed to query board network information` (all VERIFIED).
  - **Whether it opens the B6's BJJCZ USB board is not verified.** There is no `0x9588`/`BJJCZ` string in the binaries (VERIFIED by grep); the VID/PID is probably read from config.
  - No ComMarker page documents a Studio camera (WEB search: nothing).
  - **Borrow the method, not the app.**

### 1.3 EZCAD2 (the Windows install in `studio/B6-Mopa/files/install/…/EZCAD for ComMarker B6 MOPA/`)

- **`MVCAPI.dll`** has the version info *Company: Microview, "MVC-F Series USB Camera", MVC-F DLL 1.0.3.8, ©2014*, and exports `MV_Usb2Init`, `MV_Usb2GetRgbData`, `MV_Usb2SetTriggerMode`, … **`MVBayerDec.dll`** is also from Microview (Bayer-to-RGB conversion, ©2009). **This is Beijing Microview's industrial camera SDK. It is not Hikvision or MindVision** (VERIFIED for `MVCAPI.dll` and `MVBayerDec.dll` by their version resources). **`MVAPI.dll`** (`MV_OpenDevice`, `MV_CaptureSingle`, `MV_LabView_*`) and **`MVParm.dll`** (`MVInstall/MVUNInstall`) have no version resource. That they are Microview's older capture-card API and installer is INFERRED from the `MV_` prefix and from shipping together.
- **EzCad2.exe contains a `CCamera` class** (`SetExposure`, `SetMirror`, `LoadParameter`, `GetGrayBit`) and supports three camera backends: Microview `MVCAPI.dll`, a **`Pc2visiondll.dll`** frame grabber (PC2-Vision, a Coreco/DALSA board: INFERRED from memory), and Windows **VFW** (`capCreateCaptureWindowW`, i.e. a generic webcam). It also has the strings `CAMERACALI` and `CameraCalibration.cal` (VERIFIED).
- **`res/param.ini`** (VERIFIED):
  ```
  CAMERA=0
  CAMERATYPE=IDS            ; alternatives commented: MVC1000, MVC5001F, MVC3000F
  CAMERACORNER1X/Y=-25,-25  CAMERACORNER2X/Y=25,25   ; camera view = a 50×50 mm window
  CAMERACALI=0  CAMERACALIFILENAME=CameraCalibration.cal
  ```
- **`lan/CameraMarkLang.ini`** (GB18030; VERIFIED) is the language file of a **"CameraMark" plugin**: define an image template per station ("定义工位1A图像模板"), match it ("匹配图像模板成功 / 匹配分数", match score, lowest match rate), three video test points, 1 to 4 stations, A/B faces. That is classic **CCD visual positioning**: find the part by template matching and correct the mark position. **The `.plg` itself is not in `plug/`** (VERIFIED). So the feature is **dormant: `CAMERA=0`, plugin absent, Windows-only, industrial cameras, template matching rather than a live overlay.** Nothing to reuse except the idea.
- Industry context: Chinese "CCD visual positioning" fiber markers quote ±0.03 to ±0.1 mm with a fixed industrial camera over a small field (WEB: [findlight listings](https://www.findlight.net/laser-material-processing/laser-engravers/laser-marking-machines/vipin-fsd-xy20fb-laser-marking-machine-20w-ccd-positioning)). Omron's MX-Z2000H "finder" does the same for workpiece position (WEB: [Omron](https://www.ia.omron.com/products/family/3634/)).

### 1.4 LightBurn

- **Galvo cameras are supported.** *Laser Tools › Calibrate Camera Alignment* takes galvo users straight to the **Overhead Camera Alignment Wizard** (WEB: [LB 1.7 Calibrate Camera Alignment](https://docs.lightburnsoftware.com/1.7/Reference/CalibrateCameraAlignment/)). The steps:
  1. Calibrate the camera lens first.
  2. Focus on material at least 200 × 200 mm.
  3. **Engrave a target pattern** (100 % scale = 200 mm square, or "Fit Workspace"); "Don't move the target marker pattern after engraving it!"
  4. Capture, and double-click the four targets in order.
  5. Choose *Update Overlay*.
- **Lens calibration** uses a printed **AprilTag** (recommended) or circles pattern. The card is moved through about 9 positions (centre, 4 edges, 4 corners), and the target score is "0.5 pixels of error" (WEB: [LB 2.0 Calibrate Camera Lens](https://docs.lightburnsoftware.com/2.0/Reference/CalibrateCameraLens/)).
- **On a Mac, LightBurn's own 8 MP camera is out:** "Please note: this camera does not work on MacOS" (WEB: [LightBurn 8MP 4K-N](https://lightBurnSoftware.com/products/8mp-camera-4k-n)). A generic UVC camera will be listed by LightBurn on macOS, so **the camera we buy also works with LightBurn's galvo wizard.** That is a free cross-check of Raio's calibration (INFERRED).
- Forum views: "sub-millimeter accuracy is possible with a camera" with careful calibration and a camera that keeps its exact position. A camera moving with the galvo head helps (WEB: [Adding a camera to my Galvo Fiber Laser](https://forum.lightburnsoftware.com/t/adding-a-camera-to-my-galvo-fiber-laser/180607)). Red-light framing "works great until you need … less than a mm". **"Your camera will only function at the plane that it's been calibrated in"** (WEB: [Omni X camera thread](https://forum.lightburnsoftware.com/t/do-you-have-any-ideas-on-how-to-connect-a-camera-to-commarker-omni-x/184548/2)).

### 1.5 Other galvo makers

- **xTool F2 Ultra:** dual 48 MP cameras for alignment. The retailer spec gives **0.2 mm positioning precision** (WEB: [3D Universe](https://shop3duniverse.com/products/xtool-f2-ultra-60w-mopa-40w-diode-dual-laser-engraver), [TechRadar](https://www.techradar.com/pro/xtool-f2-ultra-laser-cutter-review)). F1 Ultra: a "smart camera" (16 MP per a retailer table; sources disagree). xTool's own note on the M1 fisheye camera says the error grows when material is farther from the camera or not at baseplate height, and is typically within 1.5 mm (WEB: [xTool support 617](https://support.xtool.com/article/617)). **Take 0.2 mm as the commercial benchmark.**
- **Chinese "CCD visual positioning" markers (EZCAD/BJJCZ-based):** the industrial pattern of §1.3, a fixed or coaxial camera with template matching over a small field (WEB: the findlight listings above). That the specific brands Cloudray and Monport sell such an option was not checked (INFERRED/open).
- **Open source:** the **meerk40t-camera** plugin (OpenCV via `opencv-python-headless`) works with meerk40t's Balor galvo driver (WEB: [PyPI meerk40t-camera](https://pypi.org/project/meerk40t-camera/0.1.8)). OpenCV itself provides everything we need: `findCirclesGrid`, ArUco/ChArUco, `findHomography`, `calibrateCamera`/`fisheye.calibrate`, `warpPerspective`, `remap` (WEB: [OpenCV fisheye](https://docs.opencv.org/4.8.0/db/d58/group__calib3d__fisheye.html)).

---

## 2. Hardware

### 2.1 Geometry (COMPUTED)

The camera lens sits at roughly the height of the F-theta lens, **H ≈ 250 mm above the focal plane** (INFERRED from f = 210 mm and the panel's ~255 mm; measure it). We want to see the 150 mm field plus a margin, about **200 × 200 mm**.

| Camera, lens | Covers at H = 250 | mm / px | HFOV |
|---|---|---|---|
| ELP IMX179 (1/3.2", 3264×2448) @ 2.8 mm | 408 × 306 mm | **0.125** | 78° |
| ELP IMX179 @ 4.0 mm (zoomed) | 286 × 214 mm | **0.088** | 60° |
| Arducam IMX477P (4056×3040), 88° DFOV M12 (f ≈ 4.1) | 386 × 289 mm | **0.095** | 75° |
| Arducam OV9281 global shutter, 1280×800, 70° | 350 × 219 mm | 0.27 | 70° |
| Logitech C920, 1920 px, ~70° | ~353 mm wide | 0.18 | 70° |

- **Offset:** a camera beside the lens, d = 40–80 mm off-axis and looking straight down, would need a half-angle of 29–36° toward the far side (COMPUTED), wasting half the sensor. **Tilt it toward the field centre instead: atan(d/H) ≈ 9–18°** (13.5° at d = 60 mm), and let the homography remove the perspective.
- A varifocal lens means we can zoom to just cover 200 × 200 mm and gain resolution.

### 2.2 The options (prices WEB, dated; verify at purchase)

| | Camera | Why | Price |
|---|---|---|---|
| **A · buy this first** | **ELP-USB8MP02G-MFV (2.8–12 mm)**: Sony IMX179 8 MP, USB 2.0 UVC, manual varifocal and manual focus, IR-cut at 650 nm, "UVC… Windows, Linux, Android, and Mac" | Manual focus and zoom set once and locked with a dab of glue. 0.09–0.125 mm/px. macOS stated by the seller. | ≈ $80–90 ([eBay ELP](https://www.ebay.com/str/globalselp), [VXB equivalent](https://vxb.com/products/ultra-hd-8mp-usb-camera-with-28-to-12mm-varifocal)) |
| **B · better** | **Arducam 12 MP IMX477P USB 3.0 UVC, M12 manual focus, 88° DFOV "minimal distortion"** (SKU B0459, with enclosure B0459C) | 1/2.3" sensor (bigger pixels, better on dark metal), 4056×3040, low-distortion M12. Arducam lists Windows/Linux only; **macOS is UVC-standard but untested** (INFERRED). | ≈ $150–165 ([Arducam](https://www.arducam.com/arducam-12mp-imx477p-usb-3-0-camera-with-m12-manual-focus-lens-without-enclosure.html)) |
| C · not for this | Logitech C920/Brio: autofocus hunts and is hard to lock from macOS (INFERRED). Arducam OV9281 global shutter ($50, [Arducam/RobotShop](https://www.robotshop.com/products/arducam-120fps-global-shutter-usb-camera-board-1mp-ov9281-uvc-m12-lens)): global shutter buys nothing on a still scene, and 1 MP mono is 0.27 mm/px. LightBurn 8 MP-N: not on macOS. | | |

**Rolling vs global shutter:** this doesn't matter for a still workpiece. It matters only when photographing the red framing light, which the galvo draws as a moving dot. Fix that in software: take a 0.5–1 s burst and keep the **per-pixel maximum** to get the whole outline (INFERRED). The ELP's 650 nm IR-cut may dim the ~650 nm red dot; test it in experiment 1.

### 2.3 Filter

- Silicon sensors respond out to about 1100 nm. The camera's built-in **IR-cut** (hot mirror) is designed for visible-light colour rendering and is not rated as laser protection. **Add a Schott KG3, 2 mm**: Schott guarantees an internal transmittance τi(1060 nm) ≤ 0.001 at 2 mm, i.e. **OD ≥ 3 internal** (WEB: [Schott KG3](https://www.schott.com/shop/advanced-optics/en/Matt-Filter-Plates/KG3/c/glass-KG3); OD COMPUTED). Stacked with the camera's IR-cut that should give more than OD 4 at 1064 nm (INFERRED: the IR-cut's density at 1064 nm is unknown), and the visible image is barely tinted (KG3 is a heat-absorbing glass). A 25 mm disc costs about $40–60 (Edmund/UQG; price INFERRED).
- In front of the KG3, add a **sacrificial window** (a microscope cover slip or thin glass) against fume and spatter. Replace it when cloudy.

### 2.4 The specular hazard: the rule, not a damage figure

- A non-telecentric F-theta sends the beam to field point x at about θ ≈ x/f (up to 20.5° at the 75 mm edge; COMPUTED). Off a **flat mirror-like** surface (polished brass, the Witnesses' gold) the beam reflects back up at θ and reaches the camera's height at about 2.2·x from the axis. **So anywhere within about ±160 mm of the lens at camera height is hit by a specular reflection for some field position**. A camera 60 mm off-axis is hit when the beam passes near x ≈ 27 mm on its side (COMPUTED, order of magnitude). Curved work (the OW rings, the R5 rotary) spreads the reflection into a fan that can sweep through the camera from many positions.
- Order of magnitude (COMPUTED, rough): the reflected beam is about 12 mm wide at the camera and carries most of the 60 W. A 2 mm camera aperture catches a few percent of that, and focuses it onto the sensor. Damage to CMOS sensors is documented as colour-filter discoloration first, then dead pixels and lines (WEB: [Korean CW NIR study](https://koreascience.kr/journal/GSGGBW/v19n6.page?lang=en), [pulsed 1064 thresholds ~38–76 mJ/cm²](https://m.researching.cn/articles/OJ20c3ad7aa950ddc7), [Sony warning](https://ymcinema.com/?p=10496)). KG3 + IR-cut cut the transmitted power by >10⁴, but the KG3 itself absorbs the heat and can crack under repeated hits.
- **Rules for Raio:**
  1. **No frames while firing, by default.** The camera is for *before* (placement, focus) and *after* (inspection), never for watching the beam.
  2. KG3 + window always on. **Treat the camera as a consumable** (that is one reason option A is the first buy).
  3. **v2: a physical shutter**, a small servo flap over the lens that is closed whenever the laser is armed. The BJJCZ LMC board has general-purpose outputs (EZCAD's "Output port" / LightBurn's I/O). Driving the flap from an LMC output would tie it to the job in hardware. Check which output is free on the B6 (INFERRED; not verified on this board).
  4. **Never point the camera at a firing laser without the filter.** The camera image does not replace goggles: the B6 is open-frame Class 4.

### 2.5 Lighting

- Polished brass and copper show the lamp, not the surface. Use **diffuse light**: an LED strip (high CRI, 5000–5600 K) behind an opal diffuser or a white tent on the two sides away from the camera. Keep it on a fixed brightness so exposure stays repeatable. Lock the camera's exposure and white balance once the light is fixed.
- **Experiment (cheap):** **cross-polarisation**, with linear polariser film on the LED and a polariser in front of the camera turned 90°. Metal preserves polarisation in its specular reflection, so that glare is cancelled and the diffuse light (engraved marks, scratches, oxide) remains: a mirror plate goes dark and **the engraved calibration dots and previous marks stand out** (INFERRED; standard machine-vision trick).
- The B6's red pointer is a free light source for the framing check (§3.6).

### 2.6 Mount

- **On the head, beside the F-theta lens, as close to its axis as the housing allows, tilted ~13° toward the field centre.** Material: a P2S print. **Per the cravado print gate, the bracket is a studio part: measure the head housing first (caliper + photo), then design it in cravado. No slice without measured mating dims.**
- Mount the camera rigidly. The calibration is only as stable as the mount: an M12 lens nudged by a fingertip, or a bracket that creeps, makes the overlay wrong. Glue the focus ring and the zoom ring after setting them.
- Route the USB cable down the Z column with a service loop for the full Z travel. Fit a ferrite at the camera end (EMI from the Q-switched source; INFERRED).

---

## 3. Calibration math

### 3.1 What we calibrate

We want **M: camera pixel (u, v) → commanded galvo coordinate (X, Y) in mm**, the coordinates Raio sends to the board. Measuring against *commanded* coordinates (not true mm) means the mapping already includes the F-theta distortion left over after the `.cor` correction table. What you see is where the beam goes.

### 3.2 The engraved plate

- Use **black-anodised aluminium** (white marks, highest contrast), or any scrap that marks dark-on-light. Fix it with tape or magnets and autofocus on it.
- Engrave an **11 × 11 grid of 1.2 mm filled dots at 13 mm pitch** (galvo −65…+65 mm). Add an **orientation key**: three dots of 2.5 mm at three corners (asymmetric), plus a **ChArUco or AprilTag** marker or two in a corner for unambiguous IDs if part of the grid is hidden.
- That is 121 points, enough for a dense fit. Engraving takes about a minute. **Don't move the plate between engraving and capture** (the same rule as LightBurn). After the fit the plate can be thrown away. Keep it anyway as the **check plate** (§3.7).
- Detect with `cv2.SimpleBlobDetector` + `cv2.findCirclesGrid` (or ChArUco corners). Dot centroids are accurate to **≈ 0.1 px ≈ 0.01 mm** (INFERRED, typical for blob centroids).

### 3.3 The fit

1. Optional and once: **camera intrinsics** (`cv2.calibrateCamera`, or `cv2.fisheye` for wide lenses) from 10–15 frames of a ChArUco card held at different angles. This is only worth doing for a lens wider than about 90°, because the dense fit below absorbs mild distortion anyway.
2. **Homography** `H = cv2.findHomography(px, galvo_mm, cv2.RANSAC)`. This handles perspective (tilt) and scale.
3. **Residual warp**: what H cannot explain (lens radial distortion, F-theta residuals). Fit a smooth correction on the 121 residuals, using a thin-plate spline (`scipy.interpolate.RBFInterpolator`) or a bicubic B-spline grid. That is the "N-points FFD" of ComMarker's libCyclops.
4. Report the **leave-one-out RMS** in mm. The target is **< 0.05 mm**. Save `calib.json` (camera model/serial, mount version, H, residual grid, RMS, date).

Rendering for the iPad:
- **Orthophoto:** precompute a `cv2.remap` grid that turns each camera frame into a top-down image in galvo mm, e.g. **1600 × 1600 px for −80…+80 mm (0.1 mm/px)**.
- **Overlay:** the job outline is SVG in the same mm space, so no projection math is needed on the iPad.
- **Drag-to-place:** a drag of the outline on the iPad is a translate/rotate in mm. Raio applies it to the job before framing.
- **The reverse direction** (galvo mm → pixel) is only needed to draw on the raw frame. Invert H and iterate the residual.

### 3.4 Precision at this geometry (COMPUTED)

| Error source | Size |
|---|---|
| Image resolution (option A at 4 mm zoom / option B) | 0.09–0.1 mm/px. A human drag is good to ~1 px, the fit is sub-pixel. |
| Fit residual after the warp | ~0.03–0.05 mm (target) |
| **Material height ≠ calibrated plane (Δz)** | See below; the dominant term |
| Mount creep, thermal | Unknown. Experiment 2 measures it. |

**Height error, including the laser's own walk.** Let the material top be Δz above the plane we calibrated on.
- The **beam** to command x travels at θ ≈ x/f, so it lands about **x·Δz/f inward**.
- The **camera**, at lateral position x_c and height H, sees a feature at X displaced about **(X − x_c)·Δz/H outward** from itself.
- Placing by camera and firing gives a net error of about **X·Δz·(1/H − 1/f) − x_c·Δz/H**.

With H ≈ 250 and f = 210, the first term is at most 75·(−0.00076) ≈ **−0.06 mm per mm Δz**. The second is **0.24 mm per mm Δz at x_c = 60 mm** (0.16 at 40 mm). So **the error is mostly a uniform shift along the camera's offset direction, ≈ 0.2–0.3 mm per mm of height error**, which is why the camera goes **as close to the lens axis as possible**. With autofocus putting the surface at the calibrated plane (Δz ≈ 0 ± 0.2 mm), expect **≈ 0.1–0.2 mm overall**. That matches the xTool F2 Ultra's 0.2 mm and beats red-light framing for whole-field placement.

### 3.5 Z: why the camera goes on the head

- **Head-mounted (recommended).** The galvo field is defined relative to the head. Camera, galvo and lens move together on the Z column, so their geometry is rigid. The B6's autofocus brings the head to the material top every time. **So the camera always looks at the focal plane from the same pose, and one calibration holds for 1 mm copper and a 50 mm block alike.** The scale does not change with Z, because the distance to the *focused surface* is constant.
  - **Caveat 1:** deliberate **focus drops** for cutting (the brass hole recipe lowers focus across passes). Capture and place **at focus, before** the drop.
  - **Caveat 2:** a non-flat or curved part (rings on the R5): only the part of the surface at the autofocus height is correct; the rest walks by ~0.25 mm/mm.
- **Base-mounted (rejected).**
  - The material top moves with thickness, so the mapping changes with every job's height. You would need H(z) from two calibrations at different heights, interpolated, plus a reliable z for every job.
  - The head moving down into the frame hides the work.
  - A base-mounted camera would also need a stand of its own on an open-frame machine.

### 3.6 Preflight = red light + camera

1. Edson places the material, autofocuses, and Raio grabs a frame. The **orthophoto + outline** shows on the iPad, and he drags the job into place.
2. Raio runs **red-light framing** of the placed job. The camera takes a 0.5–1 s max-stack burst of the framing (§2.2). The page shows the **captured red outline over the intended outline**: two independent checks agreeing (the red pointer passes through the same galvo; the camera checks it lands where the overlay said).
3. A **focus check**: compare the pixel sharpness of the material texture (Laplacian variance) against the value at calibration. A drop flags "not at focus?". Small but useful (INFERRED).
4. Edson says go. **Camera stops**, laser fires. After the job: **one frame** for the record (the "end photo" of forno).

### 3.7 Re-checks

- **Daily check, 10 s:** the red pointer jumps to 5 known points while the camera finds the dot. If the residual is above 0.15 mm, warn "recalibrate". The red pointer has its own small offset from the IR beam on BJJCZ boards, so it is a drift check, not the calibration. The engraved grid stays the ground truth (INFERRED).
- **Closed loop for free:** after any job, the camera can measure where the marks landed against where Raio commanded. That is a running accuracy log.

---

## 4. macOS plumbing

### 4.1 Finding the camera (VERIFIED on this Mac)

```
$ ffmpeg -f avfoundation -list_devices true -i ""
[0] MacBook Pro Camera   [1] Pavoni Camera   [2] MacBook Pro Desk View Camera
[3] Pavoni Desk View Camera   [4] Capture screen 0
$ system_profiler SPCameraDataType   → MacBook Pro Camera, Pavoni Camera (iPhone17,3, Continuity)
```

Four video devices are already present before the USB camera arrives, and the iPhone's Continuity Camera comes and goes. **Never open a camera by index.**
- `AVCaptureDevice.uniqueID` for a UVC camera is **`0x<locationID><VID><PID>`**. It follows the USB port and can even change across reboots (WEB: [Apple dev forums 836729](https://developer.apple.com/forums/thread/836729); SecuritySpy users hit the same thing). So **match on name + `modelID`** (e.g. `UVC Camera VendorID_xxxx ProductID_yyyy`), which carries VID/PID, and treat the uniqueID as session-only. With one camera of a model in the studio, VID/PID is unique enough. The USB serial (via IOKit) is the tiebreaker if we ever have two.
- **Capture path (recommended): ffmpeg's avfoundation input by name**, e.g. `ffmpeg -f avfoundation -framerate 15 -video_size 3264x2448 -i "ELP USB Camera" …`. ffmpeg accepts the device *name*, it is already installed (`/opt/homebrew/bin/ffmpeg`), and p2s already uses it. OpenCV's `VideoCapture(i, cv2.CAP_AVFOUNDATION)` only takes an index, so mapping name to index needs pyobjc `AVCaptureDeviceDiscoverySession`, and the orders are not guaranteed to agree (WEB: [OpenCV forum](https://forum.opencv.org/t/how-to-specify-exact-camera-by-id-to-prevent-two-usb-cameras-from-being-switched-around-macos/12351)). Keep OpenCV for the maths, not for capture. OpenCV is not installed yet (VERIFIED). Put `opencv-python-headless` + `numpy` + `scipy` in a `~/.venvs/raio`.
- **Warm-up:** the first frames from a UVC camera are dark or off-colour while auto-exposure settles. Drop 15–30 frames (`-vf "select=gte(n\,20)" -frames:v 1`) or lock exposure.
- **Exposure/WB/focus lock:** UVC controls on macOS need a UVC-control tool (e.g. the open-source `uvc-util`) or pyobjc/IOKit UVC requests, because AVFoundation does not expose them for external cams (INFERRED). With a manual-focus lens, only exposure and WB matter.

### 4.2 Camera permission (TCC)

- TCC credits a camera request to the **responsible process**: the nearest app bundle up the process tree. **If that bundle has no `NSCameraUsageDescription`, macOS doesn't even ask; access is just denied** (WEB: [claude-code issue 82543](https://github.com/anthropics/claude-code/issues/82543), [OpenLogi TCC notes](https://instagit.com/AprilNEA/OpenLogi/openlogi-macos-tcc-permission-checks-no-user-prompts.md)).
- **Run by hand from Terminal:** Terminal gets the camera prompt once. Fine for experiments.
- **Run as a tool:** the iPad runner `iPadTools.app` (`art.edsonpavoni.ipad`) **has no `NSCameraUsageDescription`** (VERIFIED: its Info.plist has only `LSUIElement`). Adding the key reseals the bundle. `studio/ipad/README.md` says that recompiling the stub invalidates the Dropbox "Files and Folders" grant. That an Info.plist edit does the same is INFERRED but likely, since both change the code signature. Both prompts would then have to be re-allowed in one sitting.
- **Recommendation:** give Raio its own tiny capture helper, **`~/Applications/RaioEye.app`**: a Swift stub, `LSUIElement`, `NSCameraUsageDescription = "Raio looks at the laser bed before a job"`. It starts ffmpeg, keeps frames **outside Dropbox** (`~/Library/Caches/raio/`), and serves `/snap.jpg` + `/live.mjpg` on localhost. Raio, under the iPad runner, proxies them. This is exactly the **OracleEars.app** pattern (VERIFIED: `LSUIElement` + `NSMicrophoneUsageDescription`). The iPad runner's Dropbox grant stays untouched, and the camera grant belongs to a bundle that never changes. That ffmpeg as a child inherits the helper's grant is INFERRED, so test it in experiment 3.

### 4.3 One frame vs. a stream; latency

- **Placement:** one full-res still (8–12 MP) → orthophoto → iPad. About 1 s from button to picture (INFERRED). This is the main mode, like forno's bed photo.
- **Live:** MJPEG at ~1280×960, 10–15 fps, served as `multipart/x-mixed-replace`. iPad Safari shows that in a plain `<img>`. Expect about 150–300 ms glass-to-glass on the LAN (INFERRED). Use it while sliding material around, and freeze to a still for the precise drag.
- **Stop the stream when the laser is armed** (§2.4).

### 4.4 Hot-plug: "laser ✓ camera ✓"

- **Simplest, robust:** Raio polls every 2 s.
  - Laser: `ioreg -p IOUSB -l -w0` → any device with **`idVendor = 38280` (0x9588)**. **Match the vendor only**: BJJCZ boards report **0x9899** (WEB: [balor-meerk40t README](https://github.com/tatarize/balor-meerk40t)), or **0x9990 before firmware load / 0x9999 after** (WEB: [LightBurn forum](https://forum.lightburnsoftware.com/t/device-not-found-bjjcz-device-laser-mark-control-board-v1/137554/51)). The laser is not plugged in right now (VERIFIED: no 0x9588 in `ioreg`), so read the B6's real PID the first time it is connected.
  - Camera: its VID/PID in the same `ioreg` output, **and** its name in the AVFoundation list (the USB device can be present while AVFoundation hasn't published it yet).
- **Event-driven alternatives:** pyobjc + IOKit `IOServiceAddMatchingNotification`, `AVCaptureDeviceWasConnectedNotification`, or libusb hotplug via `python-libusb1` (works on darwin; pyusb has no hotplug API). All need a run loop or thread. Polling `ioreg` costs ~20 ms per call and is easier to make correct.
- **On appear:** the laser driver opens the board (and, if its firmware needs loading, does so). RaioEye starts capture, and the page flips to "connected".
- **On disappear:** close everything cleanly, and **never leave a job half-sent**. A device that vanishes mid-job is an ALERT, as in forno's watch.

### 4.5 Powered hub + BJJCZ board

- **Bandwidth (INFERRED):** the LMC board is USB 2.0 with bulk transfers of modest bandwidth. A UVC camera uses **isochronous** bandwidth that the host reserves first. A full-res 8 MP MJPEG stream at 15 fps (~10–20 MB/s) on the same USB 2.0 path could squeeze the laser's bulk traffic.
  - Run live preview at ~1 MP, take full-res only as single stills, and stop the camera during the job anyway (§2.4).
  - Prefer a **powered USB 3 hub with multi-TT**, and with option B put the camera on the hub's SuperSpeed lane.
- **Disconnects (WEB):** LightBurn users report random BJJCZ disconnects that turned out to be a **faulty board USB connector** (wiggle test), a bad controller, or cables, across Mac and PC ([forum 191015](https://forum.lightburnsoftware.com/t/intermittent-ready-disconnected-cycling-on-new-omtech-60w-jpt-mopa-usblmcv4-board-signature-0000809802102402/191015), [forum 111196](https://forum.lightburnsoftware.com/t/lightburn-galvo-latest-version-laser-random-disconnects/111196)). No source blames hubs as such. Mitigations (INFERRED):
  - short, shielded cables with ferrites;
  - the hub's PSU on the same power strip as the laser (avoids ground-loop offsets);
  - the laser on the hub's port nearest the upstream;
  - a fallback: plug the laser directly if a long job ever drops.

  Experiment 3 runs a long job through the hub on purpose.

---

## 5. What forno (p2s) gives us to reuse

Read: `studio/equipment/tools/p2s/p2s.py` (l.234–253, `snap`; l.179–220, board writers; l.444–503, watch) and `board/board.py` (85 lines).

| Piece | What it does | Reuse for Raio |
|---|---|---|
| `p2s.snap(out)` | `ffmpeg -rtsp_transport tcp -i rtsps://… -frames:v 1 out.jpg`, 20 s timeout, `die()` on an empty file, default name `snaps/YYYY-MM-DD_HH-MM-SS.jpg` | **Take it almost verbatim.** Swap the input for `-f avfoundation -framerate 15 -video_size WxH -i "<camera name>"`, add a warm-up skip. Same timeout and empty-file guard. |
| `board_write()` | Atomic JSON write (`.tmp` → `replace`) | Reuse as is for `raio/board/live.json`, `job.json`. |
| `board_live(s, snap=…)` | Keeps the latest `snap` path + `snap_time` in `live.json` | Same fields for Raio: `snap`, `snap_time`, plus `calib_rms`, `laser_connected`, `camera_connected`. |
| `next.json` `bed_photo`/`bed_time` (index.html l.84) | Bed photo shown beside the slicer render before "go" | **The exact UX Raio wants**: "Material" photo (orthophoto + outline) beside "Job" render before go. |
| `board.py` | `ThreadingHTTPServer` on `0.0.0.0` for the iPad; `/data` JSON; `/f/<path>` serving only whitelisted dirs (`SERVE_DIRS`) and image types; `Cache-Control: no-store`; page polls every 15 s; secrets (camera URL/code) never reach the page | Copy the skeleton. **Add:** a `/live.mjpg` multipart endpoint (proxy from RaioEye), a `/snap` POST that triggers a capture, and a `/place` POST for the drag result. 15 s polling is too slow for the placement screen: poll at 1 s or use the MJPEG. |
| `watch --snap-every` | Periodic frames during a print, `snap failed` never ends the watch | Only *after* a job or between passes for Raio (no frames while firing). Keep the rule "a missed frame never ends the job". |

**Not reusable:** the RTSP/LAN-liveview specifics, and anything Bambu-MQTT.

---

## 6. Recommendation

### Buy (≈ $200–280)

| Item | Pick | ≈ USD |
|---|---|---|
| Camera | **ELP 8 MP IMX179, 2.8–12 mm manual varifocal** (listings show both `-MFV` and `-SFV` suffixes: confirm the manual-focus varifocal variant at purchase) (option A). Later, if needed: Arducam IMX477P B0459C (≈ $165). | 85 |
| Filter | **Schott KG3, 2 mm, Ø25 mm** + cover-slip window | 50 |
| Light | High-CRI 5000 K LED strip + opal diffuser (+ two sheets of linear polariser film for the cross-pol test) | 25 |
| Hub | Powered USB 3 hub, multi-TT, own PSU | 40 |
| Mount | P2S-printed bracket on the head, through **cravado** (measure the head first) | ~0 |

### Calibration plate
Black-anodised aluminium (or a dark-marking scrap), 150 × 150 mm. Engrave an 11 × 11 grid of 1.2 mm dots at 13 mm pitch, plus 3 orientation dots and 1–2 ChArUco markers. Keep it as the check plate.

### Software pipeline
1. **RaioEye.app**: camera grant, ffmpeg capture by name, `/snap.jpg`, `/live.mjpg`, frames in `~/Library/Caches/raio/`.
2. **`raio/cam.py`**: `find()` (ioreg + AVFoundation by name/model), `snap()` (the p2s pattern), `calibrate()` (dots → H + TPS residual → `calib.json`, LOO-RMS), `ortho()` (remap to 0.1 mm/px), `framing_capture()` (max-stack burst).
3. **`raio/board.py`**: the forno skeleton. Material photo + job outline in SVG mm, drag/rotate to place, "laser ✓ camera ✓" chips, the preflight checklist (focus check, red-frame vs outline), and **go**.
4. **Interlock:** capture is off whenever a job is armed or running.

### First three experiments
1. **See the bed.** Hand-hold or tape the camera on the head, run from Terminal, and grab stills with `ffmpeg -f avfoundation` by name.
   - Check: the field of view at 250 mm, focus set by hand, how brass and copper look under diffused light vs cross-polarised light, and whether the 650 nm IR-cut hides the red pointer.
   - *Pass:* 200 × 200 mm visible at ≤ 0.125 mm/px, red framing visible in a max-stack burst.
2. **Calibrate and measure.** Print the bracket and mount the camera. Engrave the dot plate, fit, and read the LOO-RMS (target < 0.05 mm).
   - Then place 9 small crosses *by camera* on a fresh scrap, engrave them, and let the camera and a caliper measure the miss (target ≤ 0.2 mm).
   - **Height test:** shim the plate up 2 mm *without* re-autofocusing and engrave the same crosses again. Two predictions (§3.4):
     - **The caliper** (laser only) should read the marks walking **radially inward by ≈ X·Δz/f**, about 0.7 mm at the 75 mm edge and 0 at the centre.
     - **The camera** placement error should be a near-uniform **≈ 0.5 mm shift along the camera's offset axis**.

     Both matching confirms the model.
   - Repeat the check-plate read the next morning to see whether the mount drifts.
3. **One plug, long job.** Laser + camera on the powered hub, Raio running under the iPad runner with RaioEye.app.
   - Confirm the one-time camera prompt is credited to RaioEye. Unplug and replug the hub and watch "laser ✓ camera ✓" come back by itself.
   - Run a 20-minute engrave with the camera idle and look for any USB drop.
   - *Pass:* no disconnect, the grant survives a reboot, and capture stays blocked while armed.

---

*Sources are linked inline. Local evidence:*
- *`studio/B6-Mopa/files/install/B6 MOPA/EZCAD for ComMarker B6 MOPA/` (`MVCAPI.dll`, `MVBayerDec.dll`, `MVAPI.dll`, `EzCad2.exe`, `res/param.ini`, `lan/CameraMarkLang.ini`, `plug/`);*
- *`/Applications/ComMarker_Studio.app` (Info.plist, main binary, `libCyclops`, `libvision_3d_wzj`, `libBSL*`);*
- *`studio/equipment/tools/p2s/p2s.py`, `board/board.py`, `board/index.html`;*
- *`studio/ipad/README.md`, `~/Applications/iPadTools.app` and `OracleEars.app` Info.plists;*
- *`ffmpeg -list_devices`, `system_profiler SPCameraDataType` and `ioreg` on this Mac, 2026-10-21.*
