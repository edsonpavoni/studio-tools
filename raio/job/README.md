# raio · job/ — from a drawing to board commands

Phase 1 software, written 2026-10-21. It covers the `.raio` format, the LightBurn importer, fill and wobble, the planner, and the preview. **Nothing in this folder opens the laser.** Only `raio.py frame|mark` does, through `lmc.LMC`, and it stops at "would open the laser" when `RAIO_NO_USB=1`.

| module | what it does |
|---|---|
| `model.py` | Loads, validates and saves `.raio` (FORMAT.md v1, plain dicts).<br>`validate()` returns readable sentences; `warnings()` lists what Edson should see before the go.<br>`run_order()` and `totals()` give passes, shapes, path length, fill area and bbox per layer.<br>Shapes are written one per line. |
| `lbrn.py` | `.lbrn2` → `.raio`: CutSetting (Cut / Scan / Offset; Tool skipped; Image refused) and Rect / Ellipse / Path / Group with composed XForms.<br>Resolves VertID/PrimID sharing, reads all three PrimList dialects, flattens beziers to a 0.01 mm chord deviation in world mm, and subtracts 78.75.<br>Has `--centre` and `--discard-outside`, and fills defaults (table below). |
| `geom.py` | Polylines, bezier/ellipse/rounded-rect flattening, even-odd **fill**, **wobble** (pluggable), **kerf** (shapely buffer). |
| `plan.py` | `.raio` → the board command list (`lmc.L` opcodes, mark_test's sequence) plus stats; `preview_svg()` and `preview_png()`. Pure functions. |
| `../raio.py` | CLI: `import`, `show`, `plan`, `frame`, `mark`. |
| `../tests/test_job.py` | 22 unit tests: `RAIO_NO_USB=1 ~/.venvs/raio/bin/python -m unittest studio/raio/tests/test_job.py` |
| `../tests/import_report.py` | Runs the importer over every `.lbrn2` under `0000 AI/` and writes `tests/import-report.md`. |
| `../tests/sxs/` | Side-by-side fixtures, LightBurn against raio (see its README). |

## Defaults for fields LightBurn leaves out

LightBurn drops every CutSetting value equal to **its own built-in default** when it saves.

prefs.ini's `DefaultCutSetting` is **not** that default. It is the template for new layers, and today it holds the copper cut recipe: globalRepeat 50, doOutput false, wobble on, 500 ns. Applying it would multiply passes by 50. Each value below therefore comes from a field LightBurn *dropped on save*, or from one that is only ever stored as a non-default.

| field | default | confidence | evidence |
|---|---|---|---|
| `frequency` | **20 kHz** | high | `tests/lbrn_pwrow.py` writes `frequency 20000` on all five layers and `QPulseWidth` on all five. LightBurn 2.1.00 opened `tests/pw-row-lightburn.lbrn2` and **re-saved it on 2026-10-21 at 19:01**. The file on disk now has no `frequency` at all, and no `QPulseWidth` on the 200 ns layer. prefs.ini's CutList shows the same. `testEngrave.lbrn2` and `usb-c_cutout.lbrn2` store no frequency, and both recipes are 20 kHz. |
| `QPulseWidth` | **200 ns** | high | The same re-save dropped 200 and kept 50/100/350/500. `V5-70x45_backup.lbrn2` (a 2.1.04 re-save) dropped 200. B6-PCB-RECIPE: LightBurn shows 200 when the field is absent. |
| `interval` | **0.1 mm** | medium | B6-PCB-RECIPE: LightBurn 2.1.04 *displayed* 0.1000 for a Scan layer without the tag. This is a UI observation, not a dropped pair. |
| `wobbleSize` | **0.1 mm** | high | The V5 backup dropped 0.1 and kept step 0.02. `usb-c_cutout` has wobble on and no size; its recipe says 0.10. |
| `wobbleStep` | **0.05 mm** | medium | `usb-c_cutout` has wobble on and no step; its proven recipe says 0.05 (MATERIAL-SETTINGS, 2026-09-21). The V5 backup *kept* 0.02, so 0.02 is not the default. |
| `wobbleEnable` · `crossHatch` · `doOutput` | 0 · 0 · 1 | high | Only ever stored as the other value (wobbleEnable 1 ×106, crossHatch 1 ×26, doOutput 0 ×112). |
| `bidir` | **on** | high | Only ever stored as 0 (vendor files). testEngrave's recipe is "bi-directional on" and the file stores nothing. |
| `numPasses` · `globalRepeat` · `angle` · `anglePerPass` | 1 · 1 · 0 · 0 | high | Stored only when they differ. |
| `maxPower` · `speed` | 20 % · 100 mm/s | low | LightBurn's fresh layers (C05… in the CutList). In practice these are always written. |

**Delays** are not in the files. They come from the device in prefs.ini (`B6 Mopa`): on −300 µs, off 100, polygon 100, jump 500, end 300. A layer's `endDelay` (2 files, value 1000) is read as µs into `delays.end_us`, with a warning that the unit is assumed.

A default is listed in `source.defaults_applied` only if it changes the mark for that layer's mode, and only on output layers. That covers frequency, pulse, power and speed for every mode, interval for fills, and size/step when wobble is on. Per-layer detail is in `source.defaults_by_layer`.

## Fill (hatch): `geom.hatch`, `geom.fill_pass`

```
 rotate the drawing by −angle           scan lines y=(k+½)·interval        even-odd pairs per line
 ┌────────────┐                         ─ ─ ┌────────────┐ ─ ─              ┌────────────┐
 │  ┌──────┐  │                         ─ ─ │━━━━━━━━━━━━│ ─ ─              │━━━━━━━━━━━━│  block A (serpentine)
 │  │ hole │  │      →                  ─ ─ │━━┐      ┌━━│ ─ ─      →       │━━┐      ┌━━│  B ↓   C ↓  (cells split
 │  └──────┘  │                         ─ ─ │━━┘      └━━│ ─ ─              │━━┘      └━━│   at the hole)
 └────────────┘                         ─ ─ │━━━━━━━━━━━━│ ─ ─              │━━━━━━━━━━━━│  block D
```

1. **Region.** The region is even-odd over *every* closed polyline on the layer, so trilha's copper islands survive (verified on V5-70x45). Open polylines on a fill layer are skipped, with a warning.
2. **Scan lines.**
   - The polygons are rotated so the hatch is horizontal.
   - Lines sit on a global grid at y = (k+½)·interval, so a 10 mm square gets exactly 10/interval lines, and the same region always gets the same lines.
   - All edge crossings are computed at once with numpy, using the half-open rule so a vertex on a line counts once. They are sorted, and consecutive pairs become segments.
3. **Order.**
   - Segments are grouped into boustrophedon *blocks*: a segment joins the block of the segment above it when the overlap is one-to-one.
   - Within a block the walk is a serpentine (`bidir`) or always +x (`bidir: false`).
   - Blocks are visited greedily, nearest start first. A block can also be walked bottom-up, from its end.
4. **Per pass.**
   - Each pass is generated at angle = `angle_deg + angle_per_pass_deg × pass`. `cross` adds a second set at +90° in the same pass.
   - Sanity: total hatch length = area / interval to within 1 %. This is tested on a square with a square hole, a circle, and 13°/45°/137°.

## Wobble: `geom.wobble` (pluggable: `WOBBLE = {"circle", "zigzag"}`)

```
  path ──────────────────────────────►        beam: p(s) = c(s) + r·(cos 2πs/step, sin 2πs/step)
        ◯◯◯◯◯◯◯◯◯◯◯◯◯◯◯◯◯◯◯◯               r = size/2, s = arc length along the path, one turn per `step`
        └step┘  ⌀ = size                      samples per turn: chord within 0.005 mm of the circle (min 8)
```

- **The model.** The beam traces a circle whose diameter is `size_mm`, while the centre advances `step_mm` along the path for each revolution. That is LightBurn's galvo wobble as described in 02-protocol §4.3. At corners the centre follows the polyline, so the circle sweeps around the corner.
- **What the board does.** It marks the dense polyline at the layer's mark speed. So the marked length is about π·size/step times the path: ×18.8 at 0.15/0.025, ×15.7 at 0.10/0.02.
- **Choosing at plan time.** `plan(..., wobble_kind="zigzag")` switches to the triangle-wave generator.
- **Kerf: `geom.kerf`.** It buffers the even-odd region by `kerf_mm` with round joins, + outward. The planner applies it to closed shapes before fill or marking.

## Planner: `plan.plan(job)`

1. **Layers.** Output layers run in `order`. Settings are sent only when they change, in `mark_test.settings()` order:
   - `[0x8026, 0, ns]`
   - `round(20000/kHz)`
   - `round(pct·0xFFF/100)`
   - jump `spd(4000)`
   - mark `spd(mm/s)`
   - on (`|µs|`, `0x8000` if negative)
   - off
   - polygon µs/10
2. **Entities.** Each entity follows `mark_test.path_cmds`: JumpTo first point → `FiberOpenMO 1` → `DelayTime 800` (8 ms) → MarkTo… → `DelayTime end/10` → `FiberOpenMO 0`.
   - In line mode, an entity is one shape-pass.
   - In fill mode, an entity is one whole hatch pass. Inside it, each line starts with JumpTo + `DelayTime(jump_us/10)`.
3. **The end.** The job ends with a jump to the centre. Pass 2 and later of a closed shape start where the head already is, so no JumpTo is sent, but MO open and the 8 ms wait still are.
4. **What raio.py adds.** `raio.py mark` puts `DelayTime 800` and `WritePort` in front, exactly as `mark_test.fire()` does. `lmc.run_list` adds `0x8051` … `0x8002`.
5. **Passes.**
   - `pass_order="shape"` (the default): every pass of a shape before the next shape. That is LightBurn's numPasses on this galvo, as the trilha 16-pin header coupon shows: each hole was drilled fully in turn.
   - `"layer"`: the whole layer per pass.
6. **Galvo arithmetic.** `plan.Galvo` is the same arithmetic as `LMC.mm/spd/dist` (swap = True, 65535/157.5 units/mm). A test checks it against the driver's own methods. `raio mark` refuses to run if the driver's frame after `init()` differs.
7. **Stats.** Commands, packets (256 per packet), marked and jump mm, entities, and a rough time estimate.
   - An upper estimate adds the polygon delay at every MarkTo vertex. `run_list`'s timeout is 3 × that + 60 s.
   - For wobble layers there is also the estimate "if LightBurn's speed means forward advance".
   - The **longest packet** in seconds: `lmc.run_list` waits at most 10 s for READY between packets, so `mark` refuses anything above 9.5 s unless given `--allow-long-packets`. CU_ENGRAVE comes to 5.8 s.

## Known gaps (phase 1)

- **Not imported:**
  - Text (refused; 38 Text shapes in the archive have a `BackupPath` that could be used).
  - Bitmap / raster.
  - Tabs, perforation and flood-fill modes.
  - LightBurn's *offset* fill, which is imported as a hatch with a warning.
  - `dot` shapes, which are planned as an error until 0x8003 is proven.
- **Unknowns to settle on the machine (sxs README):**
  - Whether wobble speed applies along the loop or along the advance.
  - Whether wobble **Size** is a diameter (raio) or a radius. The archive conflicts.
  - How many packets the board buffers ahead (the READY wait).
  - Whether the board applies the polygon delay at every MarkTo vertex (wobble polylines have about 13–25 vertices per turn). The estimate leaves it out.
  - `DelayTime` against `0x800D` for the jump delay.
  - Mark speed is truncated to whole galvo units per ms: 50 mm/s → 20 units = 48.1 mm/s. This is the driver's `int()`, kept for parity.
- **Not built:**
  - Overscan, and LightBurn's hatch line inset at edges.
  - Optimising order across shapes (shapes run in file order).
  - Z steps (FORMAT `z`).
  - Run-time `log` writing into the `.raio` (logs go to `logs/` today).
