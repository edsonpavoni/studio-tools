# trilha — backlog

One list, ordered by value. Grab the top item that fits the day. History lives in
`PLAN.md`; settings live in `B6-PCB-RECIPE.md`; nothing here is urgent — the tool
already makes working boards (V4, The Source P1b, 2026-08-24).

## Next

1. **🔴 BENCH DAY: prove a drawn board in copper** — the Board tool is BUILT
   (P1–P4, `PLAN-BOARD.md`) but nothing hand-shaped has been cut yet. One
   session, three questions: (a) does an organic perimeter ≥150 mm release
   clean on the proven cutout recipe, (b) where does the FR4 web between a hole
   and the rim actually tear — ladder 0.6/0.8/1.0/1.5 mm, which confirms or
   raises the assumed `--edge-web 1.0`, (c) **border burn on the cutout edge**,
   Edson's one critique of V4 — run the S85 square from `make_mount_coupon.py`
   (85%/8; the hole ladder proved less power = less char), compare edges.
   Then cut one real Pencil-drawn board. Score everything into
   `MATERIAL-QIMOO-FR4.md`.
2. **3D shows the board from the wrong side:** every part is drawn rising from
   the same face the copper is on (`ui.html`, `render3d`: pads at z +0.02, bodies
   from `box(..., 0, bd.z, ...)`), which is a board that cannot exist. This is
   single sided: copper underneath, every component pushed in from the bare FR4.
   Put the copper on the underside, bodies on top, and open 3D on the component
   side, because that is the side Edson assembles from. The mirroring is the
   point rather than decoration: read from the component side the whole layout
   flips, and that is exactly where a part goes in backwards. A flip control
   (copper side / part side) covers both, and it is the same control the back
   side art will need. The 2D draw view is the copper view, correct as it is,
   and stays put.
3. **A recipe for engraving the bare side:** `B6-PCB-RECIPE.md` covers copper
    clear, holes and cutout. Marking bare FR4 is a different material problem,
    epoxy and glass with no copper to absorb, and it has no numbers at all yet.
    Coupon ladder with the same discipline as the hole ladder: power x speed x
    frequency x passes, scored for contrast, for legibility at small text, and
    for how little it eats of the 1.6 mm. Two unknowns decide the whole thing
    and should be answered before any ladder is cut:
    - **Registration.** The back has to line up with holes cut from the front.
      Flipping the board is easy, landing it back in the same coordinate frame
      is not. Likely answer is a jig that pins the mount holes, which would make
      the Ø2.0 mount standard load bearing for a second reason. Half a mechanism
      exists already: `COPPER_REF` (`circuit2lbrn.py:393`) is a zero power, output
      off layer that exists only to be looked at in LightBurn. Mirrored onto the
      back job it gives you something to eyeball against, though it aligns the
      art to the file and not the file to the physical board.
    - **Order and heat.** Engrave before or after the copper side is cut, and
      does marking one face lift or discolour the copper on the other. Cheapest
      test is a coupon carrying copper on its reverse.
    Score into `B6-PCB-RECIPE.md` as its own cell, material behaviour into
    `MATERIAL-QIMOO-FR4.md`.
4. **Component tags on the bare side:** the reason to want any of this. V4 in
    hand is blank green on the side you populate, so every part is placed by
    counting holes against a screen. Generate from `circuit.json`: the
    designator next to each footprint, plus the marks that stop a part going in
    wrong. Get the mirror right, it has two halves that go opposite ways. The
    board is turned over to be engraved, so footprint POSITIONS mirror relative
    to the copper job, while the GLYPHS must still read normally on that face.
    Mirror the text and you have engraved it backwards.
    - `C1` polarity, + at the square pad, and the can outline
    - `QA`/`QB`, which way the TO-220 tab faces
    - `JP`/`JS` pin 1, and which end the XIAO's USB port sits at
    - `JU`, `PA`/`PB`, `LA`/`LB` pin 1, and net names on the pod and laser
      headers so a cable cannot go in backwards
    - **values on the axials**, `120R` and `10k`. RGA/RGB and RPA/RPB sit next
      to each other, look identical at arm's length, and swapping them is the
      easy mistake this item exists to prevent.
    Layout has to dodge holes and component bodies, and the minimum legible text
    size is an output of 3 (the bare-side recipe), not a guess.
5. **The bare side as artwork:** the copper side carries the cave, the other
    face is blank green. Same principle as the copper, drawn by hand here rather
    than generated. The structural implication is worth settling before anything
    is drawn: strokes carry only `{pts, w}` and have no side, so `.handroute`
    grows a per face stroke layer. Note that "layer" already means two other
    things nearby and neither is this one: `circuit.json` pads and segments
    carry a tscircuit `layer` that the converter filters to `top`
    (`circuit2lbrn.py:86,112,135`, with the num_layers warning at :534), and a
    LightBurn `Layer` is a cut pass (HOLES_A, CUTOUT, CLEAR_1) rather than a
    face. This is a third thing, and the converter grows a second output, mirrored and cut with
    3's numbers instead of the copper recipe. The tags from 11 and the drawing
    share one surface, so they want composing together rather than one being
    dropped on top of the other.

    *(2 stands alone. 3, 4 and 5 are one chain in that order: nothing gets
    tagged or drawn on the back until the recipe exists. All four asked for by
    Edson 2026-08-26, off the V4 board in hand. None of it is needed for a
    working sculpture, so it lands after the burn.)*

6. **`--pad-grow`** — fatten footprint pads in the negative when a footprint's
   annulus is too thin around the finished hole. V4's rings were saved by the hole
   dial-in; the next dense board may need the pad-side lever too.

## Later

7. **Cooling pauses between hot stages** — the hole interleave already cools per-hole;
   this would add dwell between layers (holes → clear → cutout). LightBurn has no
   native inter-layer pause, so it means a zero-power travel layer. Decide only if a
   board shows heat damage the interleave doesn't cover — V4 didn't.
8. **`--tabs`** — cutout tabs so a board can run unattended. Today's rule (6 passes +
   stand there) works; tabs only matter if unattended cutting ever becomes real.
9. **Width coupon** — `make_width_coupon.py` / `coupon/B6-WIDTH-COUPON.lbrn2`, unrun.
   Would prove 0.2 mm traces (0.3 is proven and is the current floor).
10. **Long perimeters** — cutout proven on 10–30 mm squares and one 60×40 board; a
   100 mm edge is still untested (recipe doc, known unknowns).

## Deferred by Edson (2026-08-25)

- **File management in the app** — opening, starting and naming boards. Parked
  until after the burn. Until then Edson asks Claude to open or start a board and
  Claude keeps the folders in order; the convention and the parked ideas are both
  in **`FILES.md`**. One idea in there is not really a feature and should jump the
  queue whenever this restarts: **two clients on one drawing overwrite each other
  silently**, which is the only way to lose an afternoon here.

## Considered and killed (2026-08-25, Edson's call — don't re-add without him)

- **Autoroute assist** (click a net, software finds a route around drawn copper) —
  killed. Against the point of the tool: the Pencil is the only thing that makes
  copper, and an obstacle-aware router is a lot of software for a tool that is lean.
- **Full bundle file format** (one file carrying circuit + traces + everything) —
  killed for now. The `.handroute` extension survives as the save file (strokes +
  moves), but circuit.json stays the design source.
- **Real 3D component models** (instead of the honest boxes) — not ours to build;
  it lives upstream in tscircuit's viewer and doesn't make a better board.
- **Name** — resolved: the project is **trilha** (was PCB-Maker), the save file
  is **`.handroute`**. "pcb-art-tool" rejected as generic.

## Done (highlights — details in PLAN.md)

- 2026-08-25: **the Board tool, P1–P4** — the board outline is drawn here now,
  freehand or as exact primitives, with mount holes, typed sizes, 0.5 mm snap,
  and copper fading while shaping. Verified as an object in the UI and again in
  `verify.py`. 3D extrudes the real shape. **Not yet cut in copper: P5.**
- 2026-08-25: UI restyled Figma-like per Edson's direction — deep green accent,
  three floating icon islands (drawing / views / undo+save), pencil-size and
  vertical-smoothness popovers, sidebar reduced to connections with a hide toggle.
- 2026-08-25: renamed PCB-Maker → hand-route, UI files flattened to the project
  root, save file is now `board.handroute` (legacy traces.json still read).
  Three UI features shipped: net **focus** (tap a net in the checklist, the rest
  greys), component **Move** (drag a part with its pads; strokes stay put and the
  checklist unticks — no auto rerouting, by design; moves applied identically in
  converter and verifier, unknown-component moves refuse), and a quieter hairline
  ghost dash.
- 2026-08-24: hole recipe dialed (70%/8/kerf 0.24), mount standards, V4 cut + working
- 2026-08-23: first real board V3; two board-killing converter bugs found and fixed
- 2026-08-18–22: recipe measured on six coupon runs; iPad hand-routing UI built
- 2026-08-17: 2025 settings recovered from ToR_008; converter + verifier built

---

## From the 2026-08-27 bench session (Edson's words, lightly ordered)

Context: the P2 laser board took an evening and a morning to bring up. USB, sensor and
motor all came good. **The two things that ate the hours were component ORIENTATION and,
once a part had to come out, LOSING TRACES to the rework.** A MOSFET went in the wrong
way round; taking it out to fix it damaged the copper; the repair needed a hand jumper
across the board. That is the loop this backlog exists to break.

### 1. Orientation is the #1 error source — design against it, BEFORE tracing

> *"Component orientation is a big thing for me. I'm not naturally good at it. So I need
> to create a way to not error. Visual clues, maybe a component tab with all the data
> that will help me orient the board. And this should happen before tracing."*

- A **component tab**: per part, everything needed to seat it right — pin functions, the
  physical lead order of the real package, which pad is pin 1, polarity, a photo or
  drawing of the part as it will sit.
- It has to come **before tracing**, not after. Today the orientation truth only exists
  once the netlist is routed; by then the board is committed.
- The schematic view's `pins` / `polarity` / `pins_legend` data (added 2026-08-27) is the
  seed of this. It is board-authored data, not typed labels — keep that property.
- ⚠️ Hard-won: for QA/QB the design's footprint is pin1=Source/pin3=Gate while the
  IRLZ44N is physically G-D-S, so **the part goes in reversed**. That fact belongs on
  screen next to the part, not in a log entry.

### 2. Study 3D model integration from tscircuit

> *"The integration with a possible 3D model coming from tscircuit should be studied."*

A real package model would make orientation self-evident rather than inferred — you would
see the tab, the printed face and the lead order in place. Relates directly to item 1 and
to the existing `render3d` view.

### 3. The interface is a TWO-PANE tool: hand-route + Claude Code side by side

> *"This interface should be designed to have my Claude Code open on the side when using
> on the computer, full screen when on the iPad."*

- **Desktop: assume roughly half the screen.** Chrome at ~1130 px wide with the sidebar
  is the real case, and the current layout is cramped there.
- **iPad: full screen**, unchanged.

### 4. Claude Code should be able to POINT AT THINGS on the canvas ✅ first cut done

> *"The main idea is that Claude Code could show me stuff on the screen. Like measure
> these 2 pins, and highlight them on the screen."*

Implemented 2026-08-27 as `probe()` in the schematic view:
`probe(["QB.pin3","QB.pin1"], "STEP 1 of 4 — POWER OFF, expect ~10k")` rings the pads,
tags them **A**, **B**, **C**…, frames them, and puts the instruction in a fixed banner.
`probeClear()` removes it. Born from spending an afternoon saying "measure between QB
pin 3 and pin 1" in chat while pads got counted by eye.

**Where to take it next:**
- probe by **net** and by **component**, not just pad
- an **expected value** field, and somewhere to record what was actually read, so a
  measurement session accumulates into the log instead of scrolling away in chat
- probe should work in the **draw** view too, so it can point at a trace, not just a pad
- a **"show me the path"** mode: highlight the copper between two pads, which is what you
  actually want when hunting a lost trace

### 5. Rework damages traces — the process problem underneath all of the above

> *"The problem happens because taking a component out of this board damages its traces.
> So I have to make that crazy jumper."*

Laser-cut copper on FR4 has no plated through-holes and no mask; a pad lifts easily and
there is nothing holding it. Worth considering: sockets for the parts most likely to be
wrong (the MOSFETs), bigger pads / more anchor area on any part that might be reworked,
and a documented repair convention for jumpers so a hand-wire is not a surprise later.

---

## Suggestions distilled from PROBLEMS.md (2026-08-27, untriaged — for after the project)

Each keyed to the problem entries it answers. These are candidates, not commitments.

**S1 · Component identity card, shown BEFORE tracing** *(A6, A7, C2 — the big one)*
Per part: the physical package drawing with its real lead order, which footprint pad is
pin 1, function letters, polarity, and an explicit "goes in reversed / normal" flag.
Authored as board data (like signals.json), rendered as a tab AND printed on the
schematic sheet. The orientation fact gets written down ONCE, at design time, and the
bench never re-derives it.

**S2 · Declare the copper face; make handedness a first-class board property** *(A2, A3)*
One line in the board source: which face is copper, which face parts insert from. The
schematic view already flips; the converter and 3D should consume the same declaration,
and asymmetric footprints authored un-mirrored should be a *warning*.

**S3 · tscircuit 3D package models in the 3D view** *(C2, A6 — Edson's own ask)*
A real TO-220 with its tab, a real XIAO with its USB port visible, in place, flippable.
Orientation becomes something you SEE. Study what tscircuit can export; even crude
extrusions with a marked pin 1 would beat abstract boxes.

**S4 · Fitted-vs-source divergence table** *(A8, A9, A1)*
PARTS.md holds this today as prose. Structured: spec value, fitted value, source of
truth, checked-when. Render it in the component tab so "the cap says 16V" is knowledge,
not archaeology. A "TYPED, unverified" flag on any dimension no one measured (A1).

**S5 · probe() grows into a measurement session** *(C1, C7 — first cut shipped)*
- expected value + a field to record the actual reading; the pair lands in a session log
- probe by net and by component, not just pad
- works in draw view too: highlight the copper path between two points ("show me the
  path" — what trace-hunting actually needs)
- readings that disagree with expectation get flagged loudly at entry time, killing the
  10Ω/10k class of relay error at the source

**S6 · WebSerial: the tool talks to the board directly** *(C4, C5, C6)*
Chrome has WebSerial; the board is right there on USB. Gate toggles, i2c scans, live
telemetry — driven from buttons in the UI instead of a Python script over chat. The
port-name dance (C4) gets automated in one place; the current drive state is *displayed*
so a reboot into a different mode (C5) is visible instead of mysterious.

**S7 · Bring-up checklist, generated from the netlist** *(B5, B6, C7)*
Before first power: the ordered continuity list (supply pairs first, then buses, then
actuators), each row probe-highlighted, each result recorded. The cold D− joint and the
crossed pod pair would both have fallen out of row one or two instead of hour three.

**S8 · Design-for-rework on the board itself** *(B1, B2)*
Teardrops / bigger annular area on parts flagged "likely to be reworked" (anything with
an orientation), and a socket option for TO-220s. The converter already grows pads once
(--pad-grow exists in backlog); this is the same idea aimed at rework survival.

**S9 · Repair layer: jumpers as first-class objects** *(B1, B3)*
When a trace dies and a hand jumper goes in, record it in the drawing (endpoints + "this
is now the net path"). The as-built board and the drawing stop diverging, and the next
person probing GND finds the jumper in the tool, not by surprise.

**S10 · Coating/masking map** *(B3, B4 — immediate, this board)*
A print view marking what must be masked before conformal spray: every header cavity,
the USB opening, mount holes. Derivable from the netlist (connectors) automatically.

**S11 · Split-screen layout as the designed-for case** *(C3)*
Breakpoint at ~1100 px: side panel collapsible to icons, islands compress, sheet fits.
iPad full-screen unchanged. This is the desk reality: Claude Code owns the other half.

**S12 · Firmware bench facts surfaced where the operator is** *(C6)*
Not a hand-route feature so much as a convention: boots-armed?, which keys bypass
safety, current duty cap — a `bench.json` next to the firmware that the tool (or the
assistant) shows before the first drive command. The ARMED surprise should cost a
glance, not a source dive.
