#!/usr/bin/env python3
"""raio · tests/import_report.py — run the .lbrn2 importer over every .lbrn2 under ROOT, write import-report.md.

    RAIO_NO_USB=1 ~/.venvs/raio/bin/python studio/raio/tests/import_report.py
"""
import collections, os, sys, time
from datetime import datetime
from pathlib import Path

os.environ["RAIO_NO_USB"] = "1"
RAIO = Path(__file__).resolve().parents[1]
ROOT = RAIO.parents[1]
sys.path.insert(0, str(RAIO))
from job import lbrn  # noqa: E402


def category(reason):
    for key, label in (("Text shape", "Text (outline it in LightBurn)"), ("Bitmap", "Bitmap / raster"),
                       ("Image (raster) layer", "Bitmap / raster"), ("outside the", "off LightBurn's workspace"),
                       ("no shapes", "no shapes"), ("PrimList", "geometry"), ("VertID", "geometry")):
        if key in reason:
            return label
    return "other"


def main():
    files = sorted(p for p in ROOT.rglob("*.lbrn2") if "node_modules" not in p.parts and "sxs" not in p.parts)
    rows, cats, fail_cats, dflt = [], collections.Counter(), collections.Counter(), collections.Counter()
    t0 = time.time()
    for f in files:
        rel = f.relative_to(ROOT)
        try:
            job = lbrn.import_file(f)
            src = job["source"]
            d = src["defaults_applied"]
            c = "with defaults" if d else "clean"
            for k in d:
                dflt[k] += 1
            rows.append((c, rel, src.get("app_version"), len(job["layers"]),
                         ", ".join(f"{k}: {v}" for k, v in src["defaults_by_layer"].items()) or "—",
                         "; ".join(src["import_warnings"]) or "—"))
        except lbrn.LbrnError as e:
            c = "failed"
            kinds = sorted({category(r) for r in e.reasons})
            for k in kinds:
                fail_cats[k] += 1
            hint = ""
            if kinds == ["off LightBurn's workspace"]:
                for kw, h in (({"place": "centre"}, "--centre"), ({"discard_outside": True}, "--discard-outside")):
                    try:
                        lbrn.import_file(f, **kw); hint = f" → imports with `{h}`"; break
                    except lbrn.LbrnError:
                        pass
            import xml.etree.ElementTree as ET
            try:
                ver = ET.parse(f).getroot().get("AppVersion")
            except ET.ParseError:
                ver = "?"
            rows.append((c, rel, ver, "", " / ".join(kinds) + hint, "; ".join(e.reasons)))
        cats[c] += 1
    dt = time.time() - t0
    out = [f"# raio · import report: every `.lbrn2` under `0000 AI/`",
           "",
           f"Generated {datetime.now():%Y-%m-%d %H:%M} by `studio/raio/tests/import_report.py` with `studio/raio/job/lbrn.py` "
           f"({len(files)} files, {dt:.1f} s; the side-by-side fixtures in `tests/sxs/` are left out). Re-run it after any importer change.",
           "",
           f"**{cats['clean']} clean · {cats['with defaults']} with defaults · {cats['failed']} failed** (of {len(files)}).",
           "",
           "- *clean*: every field that changes the mark is stored in the file.",
           "- *with defaults*: LightBurn omitted a field that matters for that layer (it drops values equal to its own default); raio filled "
           "it from the defaults table in `job/README.md` and lists it in `source.defaults_applied`. The defaults counted: "
           + ", ".join(f"`{k}` ×{v}" for k, v in dflt.most_common()) + ".",
           "- *failed*: raio refuses the file and says why. By reason: "
           + ", ".join(f"{k} ×{v}" for k, v in fail_cats.most_common()) + ".",
           "",
           "Notes on the failures:",
           "- **Text**: FORMAT.md rule, \"outline the text in LightBurn first\". Every trilha coupon carries Text labels, so every coupon fails "
           "as-is; 38 Text shapes in the archive carry a `BackupPath` (LightBurn's own outline) that raio could use if Edson allows it (open question).",
           "- **Off LightBurn's workspace**: the trilha boards (V3–V6) are written centred on LightBurn's (0,0), i.e. off the 157.5 mm workspace; "
           "Edson moved them in LightBurn before cutting. `raio import --centre` places the output layers at the field centre. "
           "Others carry a few stray shapes off the workspace on a marking layer; LightBurn's prefs have `DiscardOutOfBoundsShapes: true`, "
           "so LightBurn skipped them silently; `raio import --discard-outside` does the same, with a warning. Reference layers "
           "(doOutput 0) out of the field only warn.",
           "- **Bitmap**: raster engraving is not in phase 1.",
           "",
           "| result | file | LB | layers | defaults filled / failure kind | warnings / reasons |",
           "|---|---|---|---|---|---|"]
    order = {"clean": 0, "with defaults": 1, "failed": 2}
    for r in sorted(rows, key=lambda r: (order[r[0]], str(r[1]))):
        cells = [str(x).replace("|", "\\|") for x in r]
        cells[1] = f"`{cells[1]}`"
        out.append("| " + " | ".join(cells) + " |")
    (RAIO / "tests" / "import-report.md").write_text("\n".join(out) + "\n")
    print(dict(cats), dict(fail_cats), dict(dflt), f"{dt:.1f}s")


if __name__ == "__main__":
    main()
