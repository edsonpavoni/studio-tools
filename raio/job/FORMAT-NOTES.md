# raio · FORMAT-NOTES: proposals for FORMAT.md (not applied)

Written 2026-10-21 by the phase-1 session. FORMAT.md is unchanged. Everything below works today *behind* schema v1, as extra keys that `model.validate()` ignores, or as planner options. Edson or the orchestrator decides what moves into FORMAT.md.

1. **`source` carries more than FORMAT lists.** The importer also writes:
   - `app_version`, `device` and `imported` (when).
   - `defaults_by_layer`: `{layer name: [fields]}`. The flat `defaults_applied` loses which layer took which default.
   - `import_warnings`: a list of strings. Examples: an Offset fill imported as a hatch, `endDelay` read as µs, shapes discarded off the field, `--centre` placement, reference layers off the field.

   Proposal: add the three to the `source` row of the Fields table.
2. **Pass order.** LightBurn's `numPasses` repeats each shape before the next shape on this galvo (trilha's HEADER-16 coupon). `globalRepeat` repeats the whole job. FORMAT folds both into one `passes` and writes the product, so the difference is lost: 3 global × 3 passes is not the same heat history as 9 passes per shape.
   - Today the planner has `pass_order: "shape" | "layer"`, chosen on the command line and defaulting to `shape`.
   - Proposal: an optional per-layer `pass_order`, with the importer writing `"layer"` when globalRepeat > 1. Or keep `global_passes` as its own field.
3. **Wobble kind.** Proposal: `wobble: {size_mm, step_mm, kind: "circle"}`. `kind` is optional; `circle` is the default and `zigzag` exists in `geom.WOBBLE`. It also needs a word on speed semantics once the side-by-side settles them: does mm/s apply to the beam's loop (raio today) or to the advance?
4. **Placement.** trilha writes boards centred on LightBurn's (0,0), which is off the workspace, and Edson moved them in LightBurn. Proposal: `source.placed: "file" | "centre"` plus the offset applied, so the preview can say "moved by …".
5. **Text with a `BackupPath`.** 38 Text shapes in the archive carry LightBurn's own outline. Proposal: an import flag `--text-backup` that uses it and records it in `import_warnings`. The default stays an error ("outline the text in LightBurn first").
6. **`delays.jump_us` application.** raio emits it as `DelayTime(jump_us/10)` after each hatch jump, because `0x800D` is not in `lmc.L` and was not used on 2026-10-21. Proposal: once a side-by-side shows a difference, record the opcode choice in MACHINE.md rather than in the job.
