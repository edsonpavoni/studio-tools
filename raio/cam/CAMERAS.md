# raio · cam · the cameras considered

*Which eye for the bed: the board camera already in the studio against the ones on the list, each judged by one thing, what it sees of the 150 mm bed from a clamp above it.* 2026-10-21 18:30. Scope: a view of the work like the P2S's (`README.md`), not a measuring instrument.

## The numbers that matter

Coverage and millimetres per pixel at two plausible clamp heights above the bed (300 mm ≈ level with the top of the head; 450 mm ≈ a clamp high on the column). Rectilinear estimate; a wide lens like the InnoMaker's bends more at the edges than this says. "Bed" = how many pixels the 150 mm field occupies across.

| Camera | Sensor · lens | at 300 mm | at 450 mm | Price | |
|---|---|---|---|---|---|
| **InnoMaker U20CAM-720P** (in the studio) | 1280 × 720, fixed 120° DFOV, M12, USB 2 UVC, 32 × 32 mm board | 900 mm wide · 0.71 mm/px · **bed 213 px** | 1355 mm wide · 1.06 mm/px · bed 142 px | owned ($16, Amazon, innomaker store, bought 2025-09-04) | **plug in tonight** |
| **ELP 8 MP IMX179, 2.8–12 mm varifocal** `USB8MP02G-MFV` | 3264 × 2448, zoom set by hand once | @ 2.8 mm: 486 mm · 0.15 mm/px · bed 1007 px — **@ 6 mm: 227 mm · 0.07 mm/px · bed 2157 px** — @ 12 mm: 114 mm (too tight) | @ 6 mm: 340 mm · 0.10 mm/px · bed 1438 px — @ 12 mm: 170 mm · 0.05 mm/px · bed 2876 px | $67 [ELP](http://www.webcamerausb.com/elp-8mp-3264x2448p-sony-imx179-sensor-manual-focus-hd-usb-cctv-camera-for-industrial-machine-vision-webcam-with-cs-mount-zoom-lens-2812mm-p-375.html) · ≈ $85 Amazon | the pick: the zoom makes the bed fill the frame from wherever the clamp lands |
| ELP 8 MP IMX179, 100° fixed "no distortion" `USB8MP02G-BL100` | 3264 × 2448, fixed wide | 715 mm · 0.22 mm/px · bed 685 px | 1073 mm · 0.33 mm/px · bed 456 px | $58 [ELP](https://www.webcamerausb.com/elp-imx179-8mp-surveillance-usb-camera-undistortion-lens-high-definition-uvc-free-driver-webcam-for-industrial-machine-p-342.html) | sees the whole machine, the bed a quarter of the frame; a room camera more than a bed camera |
| Arducam 12 MP IMX477P, M12 ≈ 75°, USB 3 | 4056 × 3040, 1/2.3" (bigger pixels, better on dark metal) | 460 mm · 0.11 mm/px · bed 1321 px | 691 mm · 0.17 mm/px · bed 881 px | ≈ $160 [Arducam](https://www.arducam.com/arducam-12mp-imx477p-usb-3-0-camera-with-m12-manual-focus-lens-without-enclosure.html) | the upgrade if the ELP's image on dark anodised parts disappoints; macOS untested |
| iPhone (Continuity Camera) | 12 MP, autofocus | fills the frame from anywhere | | owned | experiments only; cannot be clamped and left |

## Lower budget, still good (Edson's question, 2026-10-21 19:13)

Same measure, 300 mm above the bed. Prices as listed today, before shipping.

| Camera | Sensor · lens | Bed in the frame | Price | |
|---|---|---|---|---|
| **Waveshare IMX179 8 MP USB Camera (B)** | 3264 × 2448, 3.8 mm f/2.0, 75° FOV, distortion < 1.5 %, autofocus, USB 2, 9 × 62 mm stick board | ≈ 360 mm wide · 0.11 mm/px · **bed ≈ 1360 px** | **$29–33** [Waveshare](https://www.waveshare.com/product/ai/cameras/imx179-8mp-usb-camera-b.htm) · [RobotShop US $33](https://www.robotshop.com/products/waveshare-imx179-8mp-usb-camera-fixed-focus-auto-focusing) | the budget pick: the ELP's sensor, a lens that already frames the bed, half the price |
| Arducam 8 MP IMX179, 115° M12 (B0446) | 3264 × 2448, very wide | ≈ 940 mm · 0.29 mm/px · bed 520 px | $43–60 [Arducam](https://www.arducam.com/arducam-8mp-imx179-usb-camera-module-with-wide-angle-115-h-m12-lens.html) | too wide, the InnoMaker's problem at 8 MP |
| ELP 5 MP OV5640, 60° autofocus (`AFC60K`) | 2592 × 1944 | ≈ 346 mm · 0.13 mm/px · bed 1120 px | $48 Newegg | fewer pixels than the Waveshare for more money |
| ELP 8 MP IMX179, 75° fixed M12 (`KL75`) | 3264 × 2448, focus ring | ≈ 460 mm · 0.14 mm/px · bed 1060 px | $57.50 [ELP](http://www.webcamerausb.com/elp-no-distortion-lens-8mp-usb-camera-imx179-sensor-hd-webcam-uvc-compatible-with-windows-linux-android-mac-l75-lens-p-374.html) | the Waveshare idea on a 32 × 32 board with a manual ring; Mac stated by the seller |

Caveats on the Waveshare: the lens is autofocus (good: it settles at any clamp height and stays; a risk: it may hunt when the head crosses the frame, and macOS gives no focus lock over UVC); the seller lists Windows and Linux, but it is UVC (MJPEG/YUY2) like every other board here; the stick form needs its own cradle, not the InnoMaker's square one. For the panel digits it does what the ELP at 6 mm would do only from closer in.

## What this says

- **Your InnoMaker works with RaioEye now**, unchanged: UVC, Mac listed by the seller, one line in `config.json` to pick it by name. At 300 mm the bed is a 213-pixel square in the middle of a wide, slightly fish-eyed frame: you see what is on the bed, where the part sits, whether the vise is in the way, whether the job finished. You do not read a 2 mm engraving. Bringing it down to 150 mm above the bed doubles that (≈ 425 px), with the head then taking a corner of the frame.
- **The ELP varifocal is the one on the list because of the zoom.** At 6 mm from 300 mm the bed fills the frame at 0.07 mm/px: engraved text readable, a burr visible, the end photo worth keeping. The focus and zoom rings are set once and glued. Same USB 2, same UVC, same RaioEye.
- The 100° ELP and the InnoMaker are the same idea at two resolutions; neither frames the bed.
- The Arducam is a better sensor for dark metal at twice the price; not now.

**Suggested order:** plug the InnoMaker into the Satechi hub tonight, clamp it over the bed with anything that holds (tape and a bracket, the magic arm later), and look at `localhost:8878` for a few jobs. If the view is enough for "important info about the work", the buy is a $20 arm. If you find yourself wanting to read the part, the ELP is $67 and swaps in by name.

One unknown on the InnoMaker: whether its M12 lens carries an IR-cut filter (most do, some board cameras ship "no IR" for night use). Without one the camera also sees the 1064 nm scatter as a glow, which is harmless for a view and even useful as a "the laser is on" cue; the KG3 filter question is the same for both cameras.

*The InnoMaker's field: 120° diagonal on 16:9 taken as ≈ 113° horizontal. Sensor width for the ELP IMX179 (1/3.2") taken as 4.54 mm. The numbers are estimates; the first frame on the machine replaces them.*
