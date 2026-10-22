#!/usr/bin/env python3
"""raio · tests/sxs/make_sxs.py — side-by-side fixtures: the same shape from LightBurn and from raio, on one scrap.

    RAIO_NO_USB=1 ~/.venvs/raio/bin/python studio/raio/tests/sxs/make_sxs.py

For each fixture two LightBurn files are written with trilha's LbrnDoc (coordinates +78.75, LightBurn's frame):
  <name>-lightburn.lbrn2   run by LightBurn          (upper row, +y, toward the column)
  <name>-raio.lbrn2        the twin, moved           (lower row, −y) — imported by raio's own importer into
  <name>-raio.raio         ← this is what `raio mark` runs
so the importer is part of the test and the two marks land next to each other, not on top of each other.
"""
import re, sys
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
RAIO = HERE.parents[1]
sys.path.insert(0, str(RAIO)); sys.path.insert(0, str(RAIO.parent / "trilha"))
from job import lbrn as importer, model, plan  # noqa: E402
from lbrn import LbrnDoc, Layer  # noqa: E402   (trilha's writer)

O = 78.75


def write_pair(name, build, dy_lb, dy_raio, notes):
    """build(doc, dy) adds layers and shapes in raio mm (centre-relative); written +78.75 for LightBurn."""
    out = {}
    for who, dy in (("lightburn", dy_lb), ("raio", dy_raio)):
        doc = LbrnDoc(device="B6 Mopa", notes=f"raio side-by-side '{name}' ({who} copy, y {dy:+g} mm). {notes}")
        build(doc, dy)
        p = HERE / f"{name}-{who}.lbrn2"
        doc.save(p)
        out[who] = p
    job = importer.import_file(out["raio"], name=f"{name}-raio")
    model.save(job, HERE / f"{name}-raio.raio")
    return job


def fill_square(doc, dy):
    # (1) copper-engrave "Test 2" (MATERIAL-SETTINGS.md, LOCKED 2026-05-12): Fill 150 mm/s 100 % 20 kHz 350 ns,
    #     interval 0.020, bidir on, cross off, angle 0. The recipe is 3 global × 3 passes; the brief asks for 3.
    cu = doc.add_layer(Layer(index=1, name="CU_ENGRAVE", mode="Scan", power=100, speed=150, freq=20000, passes=3,
                             priority=0, qpulse=350, interval=0.02, angle=0))
    # (2) trilha CLEAR (B6-PCB-RECIPE.md): Scan 75 % 1500 mm/s 40 kHz 200 ns, interval 0.05, +13°/pass, 4 passes
    cl = doc.add_layer(Layer(index=2, name="CLEAR", mode="Scan", power=75, speed=1500, freq=40000, passes=4,
                             priority=1, qpulse=200, interval=0.05, angle_per_pass=13))
    doc.add_rect(O - 8, O + dy, 10, 10, cu)
    doc.add_rect(O + 8, O + dy, 10, 10, cl)


def wobble_circle(doc, dy):
    # aluminium 1.1 mm cut (MATERIAL-SETTINGS.md, LOCKED 2026-05-13): Line 800 mm/s 100 % 65 kHz 350 ns, wobble 0.15/0.025; 5 passes
    al = doc.add_layer(Layer(index=1, name="AL_WOBBLE", mode="Cut", power=100, speed=800, freq=65000, passes=5,
                             priority=0, qpulse=350, wobble=1, wobble_size=0.15, wobble_step=0.025))
    doc.add_circle(O, O + dy, 10.0, al)


def coupon_pair(src, name, dx_raio):
    """A real trilha coupon. 'As-is' is not possible: every coupon carries Text labels, which raio refuses
    (FORMAT.md). So both copies are the coupon with its Text shapes removed and NOTHING else changed;
    the raio twin wraps the shapes in a Group whose XForm moves it dx_raio mm (exercising Group transforms)."""
    tree = ET.parse(src)
    root = tree.getroot()
    texts = [s for s in root.findall("Shape") if s.get("Type") == "Text"]
    for s in texts:
        root.remove(s)
    removed = [s.get("Str") for s in texts]
    notes = root.find("Notes")
    if notes is not None:
        notes.set("Notes", f"[raio side-by-side: {len(texts)} Text labels removed: {removed}] " + notes.get("Notes", ""))
    lb = HERE / f"{name}-lightburn.lbrn2"
    tree.write(lb, encoding="UTF-8", xml_declaration=True)
    # twin: same file, shapes inside one Group moved by dx
    tree2 = ET.parse(lb)
    r2 = tree2.getroot()
    shapes = r2.findall("Shape")
    grp = ET.Element("Shape", {"Type": "Group"})
    ET.SubElement(grp, "XForm").text = f"1 0 0 1 {dx_raio:.6f} 0"
    ch = ET.SubElement(grp, "Children")
    for s in shapes:
        r2.remove(s); ch.append(s)
    r2.append(grp)
    tw = HERE / f"{name}-raio.lbrn2"
    tree2.write(tw, encoding="UTF-8", xml_declaration=True)
    job = importer.import_file(tw, name=f"{name}-raio")
    model.save(job, HERE / f"{name}-raio.raio")
    return job, removed


def main():
    jobs = {}
    jobs["fill-square"] = write_pair("fill-square", fill_square, +12, -12,
                                     "Left CU_ENGRAVE (copper Test 2, x3), right CLEAR (trilha, x4, +13 deg/pass). Compare depth, colour, line texture.")
    jobs["wobble-circle"] = write_pair("wobble-circle", wobble_circle, +12, -12,
                                       "Dia 10 circle, aluminium cut recipe, wobble 0.15/0.025, x5. STOPWATCH the LightBurn run.")
    jobs["trilha-coupon"], removed = coupon_pair(RAIO.parent / "trilha" / "coupon" / "B6-HOLES5-COUPON.lbrn2", "trilha-coupon", 50.0)
    for name, job in jobs.items():
        p = plan.plan(job)
        (HERE / f"{name}-raio.svg").write_text(plan.preview_svg(job))
        s = p["stats"]
        print(f"{name}: {s['commands']} commands, {s['packets']} packets, passes {s['total_passes']}, est {s['est_s']:.1f} s;",
              "defaults", job["source"]["defaults_applied"], "warnings", job["source"]["import_warnings"])
        for L in p["layers"]:
            alt = f" (if speed = advance: {L['est_s_if_speed_is_advance']:.1f} s)" if "est_s_if_speed_is_advance" in L else ""
            print(f"   {L['name']}: {L['mark_mm']:.0f} mm marked, est {L['est_s']:.1f} s{alt}")
    print("coupon text removed:", removed)


if __name__ == "__main__":
    main()
