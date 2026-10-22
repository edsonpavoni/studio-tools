# YouTube lJA3W2xlzow — frames index

- **Video:** "Laser Engraving Issues - ComMarker Rotary Issues and Fixes - Laser Engraving with a Rotary - Rotary"
- **Channel:** AlivePixel Creations · **Uploaded:** 2025-06-05 · **Length:** 811 s (13:31)
- **URL:** https://www.youtube.com/watch?v=lJA3W2xlzow
- **Machine:** ComMarker **Omni 1** (he says "Omni1" at 00:03), NOT the B6. Unibody base with rotary. Useful for us only as a look at ComMarker's BJJCZ/base wiring conventions.
- Method (2026-10-21): yt-dlp 720p, ffmpeg one frame every 15 s (`f15_NNN.jpg`, time ≈ (NNN-1) x 15 + 7.5 s (ffmpeg fps filter samples mid-interval; checked against the x_ frames)) plus extra frames at the driver/board/PSU talk (`x_SSSS.jpg`, SSSS = seconds). 78 frames pulled; talking-head, screen and outro frames deleted, 17 hardware frames kept; video file deleted. Transcript = YouTube English subtitles, deduped in `transcript.txt` (raw `lJA3W2xlzow.en.vtt`).

| file | time | what it shows |
|---|---|---|
| f15_008.jpg | ~01:52.5 | DM542 driver, BJJCZ board (left), PSU terminal strip (right). He calls the DM542 "the stepper driver… that goes for the rotary" (01:51). |
| f15_009.jpg | ~02:07.5 | Same, finger on DM542 signal block. |
| f15_010.jpg | ~02:22.5 | Best DM542 view: motor/power block wired yellow, green, blue, red (phases) + red, black (+V/GND); signal block PUL/DIR/ENA with yellow jumper loops and a red wire; red 8-way DIP (positions unreadable). Lower-left: small green relay board (blue SONGLE relay, TO-220 on a finned heatsink, white JST connector). BJJCZ board top-left. |
| f15_011.jpg | ~02:37.5 | New BJJCZ board, unwired: DB25 female, DB15 female, red/green LEDs, white QC dot. |
| f15_012.jpg | ~02:52.5 | Clear BJJCZ board shot: DB15 (top-left), USB-B (top), large QFP (FPGA-type), "BJJCZ" silkscreen next to a sticker and barcode, 2x5 pin header, DB25 (bottom-left), second DB15 (bottom-right), blue "101" inductor, LEDs. Model text not readable at 720p. Two round panel connectors on the wall left, wired red/yellow/blue. |
| f15_013.jpg | ~03:07.5 | DB25 male plug (source cable) with white heat-shrink, yellow "Special Attention" grounding label, Tohun PSU label ("V3 ±15V 3A", "V2 5V 5A", "110VAC (100-130VAC)…"), relay board with TO-220 + heatsink. |
| f15_014.jpg | ~03:22.5 | Relay board close: SONGLE relay (blue), TO-220, heatsink, white 4-pin JST with red/black wires, 2-pin green terminal; rainbow ribbon on BJJCZ IDC (blue). |
| f15_015.jpg / f15_016.jpg | ~03:37.5 / ~03:52.5 | DM542 close-ups. These come just after he describes the enclosure cable soldered into the driver's cable (02:58-03:26). Around 03:37 he is explaining the separate 'bridge' loop cable. |
| f15_017.jpg | ~04:07.5 | Overview: Tohun PSU label "Type FYD-400QLT-S… 220VAC (180-240VAC) 4.0A / 110VAC (100-130VAC) 6.3A", relay board, DM542, BJJCZ with ribbon, DB25 plug. |
| f15_018.jpg | ~04:22.5 | BJJCZ board installed: rainbow ribbon on top-edge IDC, USB-B, DB25, DB15, QC sticker; two round 4-pin(?) panel sockets on left wall. |
| f15_019.jpg | ~04:37.5 | Whole base: Tohun FYD-400QLT-S (fan grille visible at its end, fan not identifiable), second meshed PSU with CAUTION label, DM542, relay board, BJJCZ — same layout as `../reddit-3f53_base-internals-omni1-like.jpg`. Two panel buttons/sockets on the right wall wired red/black. |
| f15_020.jpg | ~04:52.5 | Spare parts bag (yellow-labelled cable, bracket); edge of base. |
| f15_043.jpg | ~10:37.5 | Assembled Omni 1: large perforated base, rotary chuck lying on it, tall black column with a scale strip, galvo head on an arm, source/driver box at the back of the column, cables at the base rear. |
| x_0145.jpg | 02:25 | Relay board + DM542 motor wires (yellow/green/blue/red) close up; BJJCZ DB25/DB15. |
| x_0185.jpg | 03:05 | DB25 plug, relay board, cable bundle. |
| x_0245.jpg | 04:05 | DM542 labelled "Microstep Driver DM542", relay board with heatsink, Tohun label "FYD-400QLT-S". |
