# raio · cam · build options, and how it works

**Shelved 2026-10-21 18:19 (Edson): the camera is a view of the work like the P2S's, not a gauge; see `README.md`.** What follows is the larger design, kept for the day it is wanted. *The drawing board of raio's eye: how the camera and the focus gauge would work, and every choice with its trade.* 2026-10-21. Buy list and log: `README.md`. Research: `../research/06-camera.md`.

---

## 1. How it works

One camera on the moving head does three jobs: it reads **how high** the surface is (the focus gauge), it shows **where** the job will land (placement), and with the USB poll it says **who is here** (laser ✓ camera ✓).

### 1.1 The focus gauge

<svg viewBox="0 0 760 330" width="100%" style="max-width:760px;display:block;margin:1.2em auto;font-family:var(--mono);font-size:11px" role="img" aria-label="Side view of the head: beam straight down, camera beside it tilted inward, green dot module at 30 degrees above the surface; the dot meets the beam point only at focus">
  <!-- head -->
  <rect x="300" y="20" width="160" height="60" fill="none" stroke="var(--fg)" stroke-width="1"/>
  <text x="380" y="55" text-anchor="middle" fill="var(--fg)">head · F-theta</text>
  <!-- camera -->
  <rect x="470" y="40" width="34" height="40" fill="none" stroke="var(--fg)" stroke-width="1" transform="rotate(13 487 60)"/>
  <text x="520" y="50" fill="var(--quiet)">camera, 13° in</text>
  <!-- camera view cone -->
  <line x1="487" y1="80" x2="330" y2="260" stroke="var(--quiet)" stroke-width="1" stroke-dasharray="3 3"/>
  <line x1="487" y1="80" x2="440" y2="260" stroke="var(--quiet)" stroke-width="1" stroke-dasharray="3 3"/>
  <!-- beam -->
  <line x1="380" y1="80" x2="380" y2="260" stroke="#c0392b" stroke-width="1.5"/>
  <text x="386" y="170" fill="#c0392b">1064 nm + red pilot</text>
  <!-- dot module -->
  <g transform="translate(150 150) rotate(30)">
    <rect x="0" y="-6" width="40" height="12" fill="none" stroke="var(--fg)" stroke-width="1"/>
  </g>
  <text x="60" y="140" fill="var(--quiet)">520 nm dot, 30° above the work</text>
  <!-- green ray -->
  <line x1="185" y1="170" x2="380" y2="260" stroke="#2e8b57" stroke-width="1.5"/>
  <!-- surfaces -->
  <line x1="120" y1="260" x2="640" y2="260" stroke="var(--fg)" stroke-width="1"/>
  <text x="648" y="264" fill="var(--fg)">z = 0 · focus</text>
  <line x1="120" y1="225" x2="640" y2="225" stroke="var(--quiet)" stroke-width="1" stroke-dasharray="4 4"/>
  <text x="648" y="229" fill="var(--quiet)">+2 mm high</text>
  <!-- the dot on each surface -->
  <circle cx="380" cy="260" r="4" fill="#2e8b57"/>
  <circle cx="304" cy="225" r="4" fill="#2e8b57"/>
  <line x1="304" y1="232" x2="380" y2="232" stroke="var(--accent)" stroke-width="1"/>
  <text x="342" y="246" text-anchor="middle" fill="var(--accent)">gap = Δz · tan 60° ≈ 3.5 mm</text>
  <text x="120" y="300" fill="var(--quiet)">The dot's place in the camera image is the height. 0.1 mm of height = 0.17 mm of gap ≈ 2 px at 0.09 mm/px; sub-pixel centroid → ≈ 0.01 mm.</text>
  <text x="120" y="316" fill="var(--quiet)">Above focus the dot walks toward the module, below it walks away: the sign is free.</text>
</svg>

Camera and dot module are rigid on the head, so the dot's position in the image depends on one thing: the height of the surface under the head. The camera finds the green dot (green channel minus red and blue, threshold, centroid of the largest blob) and a once-made table turns pixels into millimetres. The page shows **focus: −0.3 mm**, live, for whatever is under the head. Zero is set against the staircase test, so zero means true 1064 nm focus, not the panel's number.

The red pilot sits at the beam's own point. At zero the green dot sits on it; the pilot is the daily check of the zero and never needed for a reading.

What the operator does with it today: autofocus or tap the column until the number reads 0.0. What raio does with it once it owns Z (phase 4): taps itself to zero and re-checks between pass blocks, and the focus drops of a cutting recipe become numbers on a plan instead of a hand on a button.

### 1.2 Placement

1. **Once:** the laser engraves `jobs/calib-plate.json` on dark scrap, 121 dots at known galvo coordinates. The camera photographs the plate without anyone touching it. OpenCV finds the dot centres; a homography plus a smooth residual warp maps camera pixels straight to *commanded* galvo millimetres. That absorbs the camera's tilt, its lens, and whatever the F-theta correction left over. Written to `calib/camera.json` with its leave-one-out error (target under 0.05 mm).
2. **Every job:** material down, autofocus (the gauge confirms 0.0). One still → warped into a top-down **orthophoto at 0.1 mm/px**, the field in machine millimetres. The job's outline is drawn on it in aurum. On the iPad, a drag or a two-finger turn moves the job in millimetres; raio applies the move before framing.
3. **Check:** raio traces the red frame; the camera max-stacks a one-second burst, so the moving red dot becomes a whole outline; the page shows the captured red outline over the intended one. Two independent paths agreeing.
4. **Go:** the driver raises the laser-enable bit and writes `armed.flag`; the camera is blind until the bit drops. After the job, one end photo for the record, and the camera measures where the marks landed against where raio sent them: a running accuracy log for free.

Why one calibration holds at every height: the B6 autofocuses the head onto the surface, so camera, lens and surface keep the same geometry for 1 mm copper and a 50 mm block alike. The error budget with the material at focus is about 0.1–0.2 mm; each millimetre of height error adds about 0.25 mm, which the gauge now catches before the job.

### 1.3 Who is here, and the plumbing

<svg viewBox="0 0 760 250" width="100%" style="max-width:760px;display:block;margin:1.2em auto;font-family:var(--mono);font-size:11px" role="img" aria-label="Process diagram: iPad to raio board page to RaioEye app to ffmpeg to camera; raio driver to laser board; armed flag between driver and RaioEye; one powered hub under laser and camera">
  <g fill="none" stroke="var(--fg)" stroke-width="1">
    <rect x="20" y="30" width="120" height="44"/>
    <rect x="200" y="30" width="150" height="44"/>
    <rect x="420" y="30" width="150" height="44"/>
    <rect x="630" y="30" width="110" height="44"/>
    <rect x="200" y="150" width="150" height="44"/>
    <rect x="630" y="150" width="110" height="44"/>
    <rect x="420" y="205" width="320" height="30" stroke-dasharray="4 4"/>
  </g>
  <g fill="var(--fg)" text-anchor="middle">
    <text x="80" y="56">iPad · Safari</text>
    <text x="275" y="50">raio board :8877</text><text x="275" y="64" fill="var(--quiet)">Next · Now · place</text>
    <text x="495" y="50">RaioEye.app</text><text x="495" y="64" fill="var(--quiet)">camera grant · cam.py serve</text>
    <text x="685" y="56">ELP camera</text>
    <text x="275" y="170">raio driver</text><text x="275" y="184" fill="var(--quiet)">lmc.py</text>
    <text x="685" y="176">LMC board</text>
    <text x="580" y="224" fill="var(--quiet)">one powered hub · polled every 2 s · laser = vendor 0x9588</text>
  </g>
  <g stroke="var(--quiet)" stroke-width="1" fill="none">
    <line x1="140" y1="52" x2="200" y2="52"/>
    <line x1="350" y1="52" x2="420" y2="52"/>
    <line x1="570" y1="52" x2="630" y2="52"/>
    <line x1="350" y1="172" x2="630" y2="172"/>
    <line x1="685" y1="74" x2="685" y2="205" stroke-dasharray="3 3"/>
    <line x1="685" y1="194" x2="685" y2="205" stroke-dasharray="3 3"/>
    <line x1="275" y1="74" x2="275" y2="150"/>
    <line x1="350" y1="160" x2="495" y2="74" stroke="var(--accent)"/>
  </g>
  <g fill="var(--quiet)" font-size="10">
    <text x="385" y="44" text-anchor="middle">/snap.jpg /live.mjpg</text>
    <text x="385" y="90" text-anchor="middle">/state.json /gauge.json</text>
    <text x="600" y="44" text-anchor="middle">ffmpeg, by name</text>
    <text x="490" y="128" text-anchor="middle" fill="var(--accent)">~/Library/Caches/raio/armed.flag</text>
    <text x="490" y="142" text-anchor="middle" fill="var(--accent)">written while the laser-enable bit is high</text>
    <text x="490" y="186" text-anchor="middle">USB bulk · whole job sent</text>
  </g>
</svg>

`RaioEye.app` is the small bundle that owns the camera permission (the way OracleEars owns the microphone and iPadTools owns Dropbox). It runs the capture and serves frames and the gauge number on localhost; the raio board page proxies them to the iPad. Frames never enter Dropbox. The poll reads the USB tree every two seconds: the board as vendor 0x9588, the camera by its own ids and by its name in AVFoundation. Unplug the hub and both chips go grey; plug it back and both come back by themselves. Nothing is ever opened by index.

---

## 2. The build options

Each line: the options, the trade, the pick. ✓ = picked · ○ = open for Edson · later = a real option, not now.

### A. Where the camera lives
| Option | Trade | |
|---|---|---|
| **On the head, beside the F-theta, tilted ≈ 13° to the field centre** | One calibration holds at every Z because autofocus fixes the distance to the surface. Sees the whole field. Takes the specular hit (hence the filter). | ✓ |
| On the base, looking at the bed | Mapping changes with every material thickness; the head hides the work when it comes down; needs its own stand on an open frame. | ✗ |
| Coaxial through the F-theta (beam splitter) | True kerf view, zero parallax. Needs a dichroic in the beam path and a different head. | later, phase 6 |

### B. Which camera
| Option | Trade | |
|---|---|---|
| **ELP 8 MP IMX179, 2.8–12 mm manual varifocal, USB 2** | 0.09–0.125 mm/px, zoom and focus set once and glued, UVC on macOS stated by the seller, ≈ $67. Cheap enough to be the consumable in front of a 60 W beam. | ✓ first |
| Arducam 12 MP IMX477P, M12 low-distortion, USB 3 | Bigger pixels (better on dark metal), ≈ $160, macOS untested. | later, if the ELP limits the fit |
| iPhone as Continuity Camera | Already here. Fine for experiment 1 (what brass looks like, is the pilot visible). Cannot be mounted or locked. | experiments only |
| Logitech-class webcam | Autofocus hunts and cannot be locked from macOS. | ✗ |

### C. How focus is read
| Option | Trade | |
|---|---|---|
| **Green dot triangulation read by the head camera** | Live number at frame rate, ≈ 0.01 mm resolution, ±3 mm range, needs the board for nothing. One $19 module and the camera already there. | ✓ agreed with the raio session 18:01 |
| Two dots that must coincide (pilot + green), read by eye | The brief's first picture. Works, but needs the pilot on, and the eye reads a gap, not a number. | kept as the zero check |
| Texture sharpness (Laplacian variance) | Free, but polished metal has no texture and the camera's own focus depth is forgiving. | backup flag only |
| A triangulation height sensor on the head (own USB) | Reads warped sheets point by point, $100–300, and one more thing on the head. | later, backlog 6 |
| The gauge block / the panel's number | What the studio does today. Nothing to read. | the thing being replaced |

### D. The dot's angle
| Angle above the work | Sensitivity (gap per mm of height) | Range in a 10 mm window | |
|---|---|---|---|
| 20° | 2.7 mm | ±1.8 mm | too little range for a 2.5 mm step |
| **30°** | **1.7 mm** | **±3 mm** | ✓ the brief's figure; 0.1 mm = 2 px |
| 45° | 1.0 mm | ±5 mm | fine if the bracket wants it |
| 60° | 0.6 mm | ±8 mm | more range, 0.1 mm = 0.7 px, needs sub-pixel work |

The bracket fixes the angle; a different angle is a different print and a new staircase zero, nothing else.

### E. Protecting the camera
| Option | Trade | |
|---|---|---|
| **Schott KG3 2 mm + sacrificial cover slip + no frames while the laser can fire** | OD > 4 at 1064 nm stacked with the camera's IR-cut; the slip takes the fume and spatter; the rule takes the direct hit. The camera stays a consumable. | ✓ |
| A servo flap over the lens, driven from a free LMC output | The hardware version of the rule. Needs a free output bit confirmed on this board. | v2 |
| Nothing | A polished part can send 60 W into a 2 mm aperture. | ✗ |

### F. Light
| Option | Trade | |
|---|---|---|
| **Diffused 5000 K strips on the two sides away from the camera, fixed brightness, exposure locked** | Repeatable frames; brass and copper show their surface, not the lamp. | ✓ |
| Cross-polarised (film on the strip, film on the lens at 90°) | Kills the specular glare on polished metal, so engraved dots and old marks stand out. Two sheets, $15, worth the test. | test in experiment 1 |
| Ring light around the lens | Maximum glare on exactly the metals we cut. | ✗ |

### G. The bracket
| Option | Trade | |
|---|---|---|
| **One printed part holding camera and dot module together, clamped to the head housing** | The gauge is only as good as the fixed relation between camera and dot; one rigid print keeps it. One cravado part, one measurement session. | ○ my recommendation |
| Two brackets, one each (the brief) | Easier to iterate the dot angle alone; two mounts that can creep against each other. | ○ |
| Drilling the head housing | Rigid, final, and voids a $5k machine. | ✗ |

Either way, per cravado's gate: caliper first (housing width, depth, lens ring diameter and height, the free faces, any existing holes), design in cravado, print by the 3dprinter session, no slice before the mating dimensions are anchored.

### H. The camera permission
| Option | Trade | |
|---|---|---|
| **`RaioEye.app`: own bundle, own `NSCameraUsageDescription`, like OracleEars** | One prompt, once, to a bundle that never changes. iPadTools' Dropbox grant stays untouched. | ✓ |
| Add the camera key to iPadTools.app | Reseals the bundle, which drops its Dropbox grant; both prompts again in one sitting, every time it changes. | ✗ |
| Run from Terminal | Terminal already holds a camera grant after one prompt. | experiments only (today's hang from the editor terminal is the proof) |

### I. The hub
| Option | Trade | |
|---|---|---|
| Anker 7-port powered USB 3, now | One upstream cable brings laser, camera, light and dot laser up together, with power for all four; the hub-unplug test at gate 3 needs one hub. ≈ $45. | ○ |
| Keep the Satechi until it drops | It carries the laser today without complaint; the camera, light and dot module can hang off it for the experiments. | ○ |

### J. What the page shows
| Mode | Use | |
|---|---|---|
| **Full-res still → orthophoto** | The precise drag. About a second from tap to picture. | ✓ |
| **Live MJPEG at ≈ 1280 × 960, 10–15 fps** | Sliding the material around; the gauge number updates from this stream. | ✓ |
| Burst max-stack, one second | Capturing the red frame as a whole outline. | ✓ |
| Frames during the job | Never. | rule |

---

## 3. Decided, and open

**Decided** (with the raio session, 2026-10-21 18:01): the gauge is camera triangulation of the green dot, pilot only for the zero; `armed.flag` is the interlock, written by the driver while the laser-enable bit is high; coordinates are the galvo's, centre (0,0), +x right, +y toward the column, 150 mm usable.

**Open for Edson:** the buy list (`README.md` §1, ≈ $228 core); one bracket or two (G); the hub now or later (I); the dot angle if the bracket prefers 45° (D).

## 4. Order of work

1. Buy. 2. Experiment 1 with the iPhone, at the machine (brass, copper, a polished piece, the pilot). 3. Measure the head; the bracket in cravado; print. 4. `RaioEye.app` and `cam.py serve`; "laser ✓ camera ✓" on the board page. 5. Mount, engrave the plate, fit, nine crosses by camera, measure the miss. 6. Staircase with the raio session; gauge zero and scale. 7. Gate 3: zero within 0.1 mm on brass and steel, crosses within 0.2 mm, hub replug comes back alone, 20-minute engrave with no drop.
