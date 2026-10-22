# `.raio` · the job file

One job, one file, JSON, extension `.raio`. Written 2026-10-21 (Edson: "a raio job file should be .raio and have our own data in the format we prefer"). Raio imports (`.lbrn2`, later `.svg`/`.dxf`) and writes `.raio`; it never writes `.lbrn2`. Raio does not draw: a `.raio` holds finished geometry plus how to cut it, like a `.3mf` for forno.

## Principles
- **Every field explicit.** No device defaults hide in the file (LightBurn drops any value equal to the device default; we learned the hard way).
- **One pass count.** `passes` is the total. An importer that meets `globalRepeat × numPasses` writes the product and notes it in `notes`.
- **Geometry is tessellated.** Shapes are polylines in mm (arcs and beziers already flattened at 0.01 mm). Optional `source` primitives may be kept for the preview, never for cutting.
- **Frame.** mm, field centre (0,0), +x machine right, +y toward the column (= LightBurn's frame, centre-relative). Imports from LightBurn subtract 78.75 on both axes.
- **Order is explicit.** `layers[].order` is the run order; lower first.
- **Text does not live here.** A `Text` shape in a source file is an import error with the message "outline the text in LightBurn first".

## Schema (v1)
```json
{
  "raio": 1,
  "name": "V5-70x45",
  "created": "2026-10-21T19:40:00",
  "source": {"file": "studio/instrument/.../V5-70x45.lbrn2", "kind": "lbrn2", "sha1": "…", "defaults_applied": ["QPulseWidth", "wobbleSize"]},
  "material": {"name": "FR4 Qimoo", "thickness_mm": 1.6},
  "notes": "BOARD OFF THE BED. AIR ON.",
  "layers": [
    {
      "id": "L2", "name": "HOLES_A", "order": 0, "output": true,
      "mode": "line",
      "power_pct": 70, "speed_mm_s": 400, "freq_khz": 40, "pulse_ns": 200, "passes": 8,
      "wobble": {"size_mm": 0.10, "step_mm": 0.02},
      "fill": null,
      "kerf_mm": 0,
      "delays": {"on_us": -300, "off_us": 100, "poly_us": 100, "jump_us": 500, "end_us": 300},
      "shapes": [
        {"type": "polyline", "closed": true, "pts": [[x, y], [x, y], "…"]}
      ]
    },
    {
      "id": "L1", "name": "CLEAR_1", "order": 2, "output": true,
      "mode": "fill",
      "power_pct": 75, "speed_mm_s": 1500, "freq_khz": 40, "pulse_ns": 200, "passes": 4,
      "fill": {"interval_mm": 0.05, "angle_deg": 0, "angle_per_pass_deg": 13, "bidir": true, "cross": false, "even_odd": true},
      "wobble": null,
      "shapes": ["…closed polylines; nested loops are holes (even-odd)…"]
    }
  ],
  "z": null,
  "log": []
}
```

### Fields
| Field | Meaning |
|---|---|
| `mode` | `line` (mark the outlines) or `fill` (hatch the closed regions) |
| `power_pct` · `speed_mm_s` · `freq_khz` · `pulse_ns` · `passes` | what the board gets, after raio's validation (pulse from the source's list, frequency inside the width's envelope) |
| `wobble` | `null` or `{size_mm, step_mm}`: raio turns the path into the wobble polyline in software |
| `fill` | `null` or `{interval_mm, angle_deg, angle_per_pass_deg, bidir, cross, even_odd}`: raio generates the hatch lines per pass in software |
| `kerf_mm` | outward/inward offset applied to closed outlines before marking (0 = none) |
| `delays` | laser on/off/polygon/jump/end, µs; defaults are LightBurn's B6 values |
| `output` | `false` = shown in the preview, never marked (trilha's COPPER_REF) |
| `shapes[].type` | `polyline` (open or closed) · `dot` (`{x, y, dwell_us}`) |
| `z` | `null` or a focus plan (`research/05-focus-z.md` §4): `{z0_source, step_mm, schedule: [{z_mm, passes}], xy_scale_per_mm}` |
| `log` | appended by raio at run time: when, by whom (go), per layer: started, passes done, seconds, aborted; Z moves |

### What raio shows before the go (from this file alone)
The layers **in run order** with their settings and total passes, the geometry on the bed (red frame + the camera photo), the material, the notes; the estimated time is shown small and comes only from past logs of similar layers (Edson: LightBurn's estimate was always off; log first, estimate later).

## Importer: `.lbrn2`
Reads trilha's dialect and LightBurn's saves (`research/01-studio-history.md` §4–5): `CutSetting` fields (`maxPower`, `speed`, `frequency` Hz, `numPasses`, `globalRepeat`, `QPulseWidth`, `interval`, `angle`, `anglePerPass`, `crossHatch`, `bidir`, `wobbleEnable/Size/Step`, `doOutput`, `priority`), shapes `Rect`, `Ellipse`, `Path` (`VertList`/`PrimList`, lines and beziers), `Group` with nested `XForm`, `Notes`. A defaults table fills what LightBurn omitted and lists it in `source.defaults_applied`. `MaterialHeight` is ignored. `Text` is an error.
