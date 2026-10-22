# reddit-1krev0z_broken-b6-jpt-mopa_laser-sw-v05.png

- **Source:** https://preview.redd.it/received-a-broken-commarker-b6-jpt-mopa-v0-y15llwhvfk2f1.png?width=2528&format=png&auto=webp&s=89dbf441663c74b8de053b65709574974d9c7a9b
- **Post:** https://www.reddit.com/r/ComMarker_Engravers/comments/1krev0z/received_a_broken_commarker_b6_jpt_mopa/ — "Received a broken ComMarker B6 JPT MOPA". Post text could not be fetched (see reddit-1krev0z_post.md).
- **Downloaded:** 2026-10-21, curl, 2528x1330 PNG, original kept. Crops in `crops/b6-laser-sw-v05_*`.
- **Which machine:** ComMarker B6 JPT MOPA (per the post title) — the one B6-confirmed internals photo here.

## What it shows (VERIFIED unless marked)
- Inside of a vented black plastic housing (that it is the front panel is INFERRED) (vent slots), photographed from behind; a green PCB screwed to it with two Phillips screws.
- **Silkscreen "Laser_SW_V05"** (mirrored-read orientation, right half of board).
- **Top-right white JST-style (likely XH/PH, INFERRED) connectors**, labels left to right: `GND 5V` | `DWLD UPLD GND 5V` (these first six pins appear to be one wide housing plus a short one) | `GND UP_KEY` | `GND DOWN_KEY`. Crop: crops/b6-laser-sw-v05_connectors.jpg.
  - Wire colours into the 6-pin group (left to right, approximate, pin-to-wire mapping NOT certain): dark grey/black, red, blue, white, salmon-red, grey.
  - UP_KEY pair: yellow + green. DOWN_KEY pair: black/grey + red.
- **J7**: 4 through-hole pads in a row, silkscreen `- D R +` read left to right (square pad at "+"). A programming or debug header; meaning of D/R not certain (INFERRED: SWD-style DIO/RST, or UART). Not populated. Crop: crops/b6-laser-sw-v05_mcu-J7.jpg.
- **U2**: TSSOP-20 microcontroller-size IC; marking unreadable at this resolution. Small ceramic 4-pad crystal/oscillator to its right (C12/C13 near it), metal-can crystal/part to its left. Q3, Q4 SOT-23 transistors near J7 and the connectors; many 0603 resistors R14-R27.
- **Left**: 2-pin green screw terminal with thick black + red (taped/bodged, circled in yellow/magenta by the poster; this bodged terminal may be the fault being reported, INFERRED), silkscreen next to it partly hidden — a "24…" fragment is visible, so possibly "24V" (INFERRED). Next to it a TO-220 part bolted to a finned aluminium heatsink (regulator or switch; marking not visible) and an electrolytic capacitor.
- **Middle**: second 2-pin green screw terminal with thick red + black wires running up out of frame.
- Top: a large black cable loops across; the yellow circle marks a broken/bent plastic tab of the housing (what the post is about — damage on arrival, INFERRED from title).
- Bottom: Chinese handwriting in marker on the housing (unreadable).
- No Type-C connector is visible on this board or in the frame.
