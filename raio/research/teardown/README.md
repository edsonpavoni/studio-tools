# raio · teardown research (2026-10-21)

Hunting for how the ComMarker B6 MOPA's Z column lift is wired and controlled, and for photos of the base's internals. Started after we proved the BJJCZ board's extended-axis channel does not move the column. Downloads are untrusted data; nothing here was executed.

## What is in this folder

| file | what |
|---|---|
| `reddit-1krev0z_broken-b6-jpt-mopa_laser-sw-v05.png` + `.md` | **B6 JPT MOPA**: the Laser_SW_V05 button board inside the front housing. The only B6-confirmed internals photo. |
| `reddit-1krev0z_post.md` | The post's text could not be retrieved; it records every route that refused. |
| `reddit-3f53_base-internals-omni1-like.jpg` + `.md` | A full base interior from i.redd.it, post unknown. It matches the **ComMarker Omni 1** base in the video, so do NOT read it as a B6. |
| `lightburn_b6-manual-p-focus-and-marking-test.jpeg` + `.md` | Not internals: a B6/B6 Pro manual page covering focus buttons, the focal length, and EzCad defaults. |
| `crops/` | Zoomed crops cited below (`b6-laser-sw-v05_*`, `3f53_*`). |
| `youtube/` | Video lJA3W2xlzow (AlivePixel Creations, 2025-06-05, **Omni 1** rotary fix): `transcript.txt`, raw `.vtt`, `frames.md`, and 17 hardware frames in `frames/`. |

Provenance warning: only two sources are B6. Those are the Laser_SW_V05 photo and the manual page. The 3f53 photo and the video are Omni 1. They show what ComMarker puts in a base, not what is in ours.

## Synthesis for raio

### (a) Z lift: wiring and control
- **VERIFIED (B6):** the B6 has a board silkscreened `Laser_SW_V05` screwed inside a vented black plastic housing (that the housing is the front panel is INFERRED, from the UP/DOWN keys) (`crops/b6-laser-sw-v05_overview.jpg`). Its white connectors are labelled `GND 5V`, `DWLD UPLD GND 5V`, `GND UP_KEY`, `GND DOWN_KEY` (`crops/b6-laser-sw-v05_connectors.jpg`).
  - UP_KEY wires: yellow and green.
  - DOWN_KEY wires: dark/black and red.
  - The 6-pin group's wires run roughly dark grey, red, blue, white, salmon, grey. The pin-to-colour mapping is uncertain.
- **VERIFIED (B6):** the board has an unpopulated 4-pad header `J7` marked `- D R +` (`crops/b6-laser-sw-v05_mcu-J7.jpg`), a TSSOP-20 IC `U2` with an unreadable marking, a crystal, and SOT-23 transistors Q3/Q4.
- **VERIFIED (B6):** it has two 2-pin screw terminals with heavy red/black wire. A silkscreen fragment near the left one reads "24…". A TO-220 part sits on a finned heatsink (`crops/b6-laser-sw-v05_terminals-heatsink.jpg`).
- **VERIFIED (B6 manual):** on the non-Pro B6 you move the head with up/down buttons on the front of the base. On the B6 Pro, an "Auto" button on the head runs autofocus.
- **INFERRED:** `UP_KEY`/`DOWN_KEY` are the front-panel buttons (2 wires each, key to GND), read by the U2 MCU.
- **INFERRED, two competing readings of `UPLD`/`DWLD`.** The silkscreen does not say which way they go:
  1. **Lift-drive outputs** (the brief's working assumption). These would be up/down command lines sent with 5V/GND toward the column's lift controller, probably over the Type-C. The lift would then be commanded by two level lines, not step/dir and not serial.
  2. **Limit-detect inputs.** The labels can be read as two 3-wire triplets, `GND 5V DWLD` and `UPLD GND 5V` (V+, GND, signal), which is how opto or hall endstops are wired. In that case UPLD/DWLD are up-limit and down-limit signals coming back from the column, and the motor drive is somewhere else. The most likely place is the heavy red/black second screw terminal, which runs out of frame. Open question: does this board drive the lift motor directly?
  - Either way the BJJCZ board is not involved. That fits today's result that its extended axis does not move the column.
  - The 24V screw terminal likely powers the board. The TO-220 is either a regulator or a switch on the motor side.
- **INFERRED:** J7 `- D R +` is a programming/debug header (SWD DIO/RST or a UART). It is a firmware port on the button board. Nothing shows it carries anything to the column.
- **NOT FOUND:** no source shows the Type-C connector, its pinout, or the column-side lift controller. No photo of the B6 base's own main area (PSU, BJJCZ board) was found.
- Omni 1 for comparison (VERIFIED, video 01:51 and `youtube/frames/f15_010.jpg`): the base holds a DM542 stepper driver, and the owner says it drives the **rotary**. A small relay board (SONGLE relay, TO-220 + heatsink, white JST with red/black wires) sits beside it (`youtube/frames/f15_014.jpg`). Its function is not stated; it could be the lift motor or the enclosure interlock (INFERRED).

### (b) Main board model and labels
- B6: no source shows our BJJCZ board.
- Omni 1 / 3f53 (VERIFIED):
  - BJJCZ silkscreen, FPGA-type QFP, USB-B, DB25 (source), two DB15s, a 2x5 header with a rainbow ribbon on a blue IDC, a QC PASSED sticker and a holographic sticker (`youtube/frames/f15_012.jpg`, `crops/3f53_bjjcz-board.jpg`).
  - The model silkscreen is only partly legible, as "MODEL: LMC-Digi-LV…" (`crops/3f53_bjjcz-board-label.jpg`). It is too small to confirm. If it does say Digi, it is a different variant from the B6's LMCV4 fiber board (INFERRED).

### (c) Source model and pulse widths
- B6 post title says **JPT MOPA** (title only). No source label or pulse-width list appears in any source.
- B6 manual (VERIFIED): EzCad2.14.11 for ComMarker. Defaults are 1000 mm/s, 75 %, 20 kHz, Start TC -300, Laser Off TC 150, End TC 300, Polygon TC 100 µs. The handwritten focal distance is **233 mm** for the 150x150 lens on that owner's unit.

### (d) Rotary port pinout
- Not visible in any source.
- Omni 1 (VERIFIED, `youtube/frames/f15_010.jpg`, `crops/3f53_dm542.jpg`): the rotary runs through a DM542.
  - Motor side: GND, +V (red/black), A+, A-, B+, B- (yellow, green, blue, red).
  - Signal side: PUL+/PUL-/DIR+/DIR-/ENA+/ENA- with yellow jumper loops.
  - The DIP settings are unreadable.
  - Round panel sockets on the base wall carry the motor out.
- Which BJJCZ pins drive PUL/DIR, and the socket pin numbers, are not visible.

### (e) Power supplies and fans
- B6: nothing visible.
- Omni 1 / 3f53 (VERIFIED, `crops/3f53_fyd-400qlt-s-psu.jpg`, `youtube/frames/f15_017.jpg`):
  - **Tohun FYD-400QLT-S**, a "laser marking series" PSU. Input is 220VAC 4.0A / 110VAC 6.3A, with a 110/220 switch.
  - Outputs: **V1 +12V 29A** (adjustable), **V2 +5V 5A**, **V3 ±15V 3A**.
  - It has an internal fan behind a grille at one end. **Fan model, size and voltage are not readable.**
  - A second, meshed PSU with no readable label sits beside it.
- **INFERRED:** if the B6 base uses the same Tohun unit, its fan is internal to the PSU. The likely quiet-fan targets are the PSU fan and any source fan, but we need a photo of our own base to size them.

### (f) Safety wiring
- B6 manual (VERIFIED): there is a red button on the front of the base next to the up/down buttons, apparently the E-stop. Its wiring is not shown.
- Omni 1 (VERIFIED):
  - A red mushroom E-stop-style button on the base wall, wired red/black (3f53).
  - A grey foot pedal (3f53).
  - A "Special Attention" grounding label on the DB25 source cable (`youtube/frames/f15_013.jpg`).
  - The owner says the **enclosure** cable was soldered into the cable going to the "main driver". He had to cut it and land it in a screw terminal (video 02:58-03:26).
  - Pin assignments are not visible for any of these.

## Next for raio
1. Photograph our own base open. Get the Type-C socket at both ends, the BJJCZ model sticker, the PSU label, every fan, and where the Laser_SW_V05 board's heavy second screw terminal goes.
2. Tell the two UPLD/DWLD readings apart with a multimeter or logic probe on those pins and on the Type-C, with the machine powered:
   - **If they are outputs**, they change while UP or DOWN is held and sit idle otherwise.
   - **If they are limit inputs**, they sit at a pulled level and change only when the column reaches the end of its travel. Pressing UP/DOWN alone does not change them.
   - Also measure the heavy second screw terminal while pressing UP/DOWN. If its polarity reverses, this board drives the lift motor itself.
3. Only if they are drive outputs could raio command the lift by switching UPLD/DWLD from a BJJCZ output port through an opto. If they are limit inputs, do NOT drive them, because that fakes the endstops. raio would read them as end-of-travel instead, and drive the motor wherever test 2 shows the drive is.
