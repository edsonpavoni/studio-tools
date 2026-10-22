#!/usr/bin/env python3
"""raio · tests/test_job.py — model, importer, fill/wobble/kerf, planner, CLI dry run. Never opens the laser.

    RAIO_NO_USB=1 ~/.venvs/raio/bin/python -m unittest studio/raio/tests/test_job.py -v
"""
import io, math, os, sys, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

os.environ["RAIO_NO_USB"] = "1"                       # belt and braces: lmc.LMC() refuses to open the board
RAIO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIO)); sys.path.insert(0, str(RAIO / "lmc")); sys.path.insert(0, str(RAIO.parent / "trilha"))

from job import geom, model, lbrn, plan  # noqa: E402
import lmc  # noqa: E402
from lbrn import LbrnDoc, Layer as LbLayer  # noqa: E402  (trilha's writer)
import raio  # noqa: E402

SQ = [(-5, -5), (5, -5), (5, 5), (-5, 5)]
HOLE = [(-2, -2), (2, -2), (2, 2), (-2, 2)]


def seglen(segs):
    return sum(math.dist(a, b) for a, b in segs)


class Geom(unittest.TestCase):
    def test_hatch_square_with_hole(self):
        for ang in (0, 13, 45, 90, 137):
            segs = geom.hatch([SQ, HOLE], 0.05, ang)
            self.assertAlmostEqual(seglen(segs), (100 - 16) / 0.05, delta=(100 - 16) / 0.05 * 0.01, msg=f"angle {ang}")
            # nothing inside the hole
            for a, b in segs:
                m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                self.assertFalse(abs(m[0]) < 1.99 and abs(m[1]) < 1.99)

    def test_hatch_circle_area(self):
        c = geom.ellipse(0, 0, 5, 5)
        segs = geom.hatch([c], 0.02, 0)
        self.assertAlmostEqual(seglen(segs), geom.evenodd_area([c]) / 0.02, delta=geom.evenodd_area([c]) / 0.02 * 0.005)

    def test_line_count_and_grid(self):
        lines = geom.scanlines([SQ], 0.02, 0)
        self.assertEqual(len(lines), 500)                 # 10 mm / 0.02
        self.assertAlmostEqual(lines[0][1], -4.99)        # global grid (k + .5)·interval

    def test_bidir_serpentine(self):
        segs = geom.hatch([SQ], 1.0, 0, bidir=True)
        self.assertGreater(segs[0][1][0], segs[0][0][0]); self.assertLess(segs[1][1][0], segs[1][0][0])
        uni = geom.hatch([SQ], 1.0, 0, bidir=False)
        self.assertTrue(all(b[0] > a[0] for a, b in uni))
        jumps = sum(math.dist(segs[i][1], segs[i + 1][0]) for i in range(len(segs) - 1))
        self.assertLess(jumps, 10 * 1.01)                 # serpentine: one interval per line change

    def test_cross_and_angle_per_pass(self):
        f = {"interval_mm": 0.1, "angle_deg": 0, "angle_per_pass_deg": 13, "bidir": True, "cross": False, "even_odd": True}
        p0, p1 = geom.fill_pass([SQ], f, 0), geom.fill_pass([SQ], f, 1)
        d0 = math.degrees(math.atan2(p0[0][1][1] - p0[0][0][1], p0[0][1][0] - p0[0][0][0])) % 180
        d1 = math.degrees(math.atan2(p1[0][1][1] - p1[0][0][1], p1[0][1][0] - p1[0][0][0])) % 180
        self.assertAlmostEqual(d0, 0, places=6); self.assertAlmostEqual(d1, 13, places=6)
        fc = dict(f, cross=True)
        self.assertAlmostEqual(seglen(geom.fill_pass([SQ], fc, 0)), 2 * seglen(p0), delta=2)

    def test_wobble_circle(self):
        line = [(0, 0), (10, 0)]
        w = geom.wobble(line, False, 0.3, 0.03)
        # size is LightBurn's RADIUS (measured 2026-10-21 22:29, geom.WOBBLE_SIZE_IS_RADIUS): every point within 0.3 of the path
        r = 0.3 if geom.WOBBLE_SIZE_IS_RADIUS else 0.15
        self.assertTrue(all(abs(y) <= r + 1e-9 for _, y in w))
        self.assertAlmostEqual(max(y for _, y in w), r, delta=0.01)   # a sampled circle peaks just under r
        # length ≈ revolutions × circumference (helix-like): 10/0.03 × 2π·r
        self.assertAlmostEqual(geom.length(w), 10 / 0.03 * 2 * math.pi * r, delta=10 / 0.03 * 2 * math.pi * r * 0.05)
        self.assertEqual(geom.wobble(SQ, True, 0, 0.03)[-1], SQ[0])   # size 0: the path itself, closed

    def test_kerf(self):
        grown = geom.kerf([SQ], 0.15)
        self.assertAlmostEqual(geom.evenodd_area(grown), 10.3 ** 2 - (4 - math.pi) * 0.15 ** 2, delta=0.01)
        self.assertAlmostEqual(geom.evenodd_area(geom.kerf([SQ, HOLE], -0.1)), 9.8 ** 2 - 4.2 ** 2, delta=0.05)

    def test_bezier_flatten_tolerance(self):
        pts = geom.flatten_cubic((0, 0), (0, 0.5523), (0.4477, 1), (1, 1))
        r = [math.hypot(x - 1, y) for x, y in pts]       # quarter circle radius 1 around (1, 0)
        self.assertLess(max(abs(v - 1) for v in r), 0.011)


class Importer(unittest.TestCase):
    def test_bezier_semantics(self):
        # OW4_poem.lbrn2 line 72: an ellipse rx 1, ry 2 around (341, 10)
        v = lbrn.parse_vertlist("V340 10c0x340c0y8.8999996c1x340c1y11.1V341 8c0x341.54999c0y8c1x340.45001c1y8"
                                "V342 10c0x342c0y11.1c1x342c1y8.8999996V341 12c0x340.45001c0y12c1x341.54999c1y12")
        (pts, closed), = lbrn.path_polylines(v, lbrn.parse_primlist("B0 1B1 2B2 3B3 0", 4), geom.IDENTITY)
        self.assertTrue(closed)
        e = [(x - 341) ** 2 + ((y - 10) / 2) ** 2 for x, y in pts]
        self.assertLess(max(abs(x - 1) for x in e), 0.01)

    def test_primlist_dialects(self):
        self.assertEqual(lbrn.parse_primlist("LineClosed", 3), [("L", 0, 1), ("L", 1, 2), ("L", 2, 0)])
        self.assertEqual(lbrn.parse_primlist("LL", 3), [("L", 0, 1), ("L", 1, 2)])
        self.assertEqual(lbrn.parse_primlist("L0 1B1 2", 3), [("L", 0, 1), ("B", 1, 2)])
        v = [(0, 0, None, None), (1, 0, None, None), (1, 1, None, None), (5, 5, None, None), (6, 5, None, None)]
        got = lbrn.path_polylines(v, lbrn.parse_primlist("L0 1L1 2L2 0L3 4", 5), geom.IDENTITY)
        self.assertEqual([c for _, c in got], [True, False])          # two sub-paths: a closed triangle, an open line

    def test_compose(self):
        m = geom.compose((2, 0, 0, 2, 10, 0), (1, 0, 0, 1, 1, 1))     # parent scale 2 + shift; child shift
        self.assertEqual(geom.apply_xform(m, [(0, 0)]), [(12, 2)])

    def _doc(self, tmp, **kw):
        doc = LbrnDoc(device="B6 Mopa", notes="unit test")
        lay = doc.add_layer(LbLayer(index=1, name="CUT", mode="Cut", power=50, speed=400, freq=40000, passes=3, priority=0, **kw))
        doc.add_rect(78.75 + 10, 78.75 - 5, 4, 2, lay)
        doc.add_circle(78.75, 78.75, 2.0, lay)
        doc.add_polygon([(78.75 - 20, 78.75), (78.75 - 15, 78.75 + 5)], lay, closed=False)
        p = Path(tmp) / "t.lbrn2"; doc.save(p)
        return p, doc, lay

    def test_trilha_roundtrip_and_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, _, _ = self._doc(tmp, global_repeat=2)
            job = lbrn.import_file(p)
            L = job["layers"][0]
            self.assertEqual((L["mode"], L["power_pct"], L["speed_mm_s"], L["freq_khz"], L["passes"]), ("line", 50, 400, 40, 6))
            self.assertEqual(L["pulse_ns"], 200)                       # omitted → LightBurn default
            self.assertEqual(job["source"]["defaults_applied"], ["QPulseWidth"])
            self.assertIn("globalRepeat 2 × numPasses 3 = 6", job["notes"])
            rect = L["shapes"][0]["pts"]
            self.assertAlmostEqual(min(x for x, _ in rect), 8.0, places=4); self.assertAlmostEqual(max(y for _, y in rect), -4.0, places=4)
            circ = L["shapes"][1]["pts"]
            self.assertTrue(all(abs(math.hypot(x, y) - 1.0) < 1e-4 for x, y in circ))
            self.assertFalse(L["shapes"][2]["closed"])

    def test_text_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = LbrnDoc(); lay = doc.add_layer(LbLayer(0, "T", "Scan", 20, 1000, 40000, interval=0.05, qpulse=200))
            doc.add_text(78, 78, "hi", lay); p = Path(tmp) / "t.lbrn2"; doc.save(p)
            with self.assertRaises(lbrn.LbrnError) as cm:
                lbrn.import_file(p)
            self.assertIn("outline the text in LightBurn first", str(cm.exception))

    def test_shared_vertid(self):
        xml = """<LightBurnProject AppVersion="2.1.04" DeviceName="B6 Mopa" FormatVersion="1">
        <CutSetting type="Cut"><index Value="0"/><name Value="C00"/><maxPower Value="10"/><maxPower2 Value="20"/>
        <speed Value="100"/><frequency Value="30000"/><QPulseWidth Value="100"/><priority Value="0"/></CutSetting>
        <Shape Type="Path" CutIndex="0" VertID="7" PrimID="2"><XForm>1 0 0 1 78.75 78.75</XForm>
          <VertList>V0 0V1 0V1 1</VertList><PrimList>L0 1L1 2L2 0</PrimList></Shape>
        <Shape Type="Path" CutIndex="0" VertID="7" PrimID="2"><XForm>1 0 0 1 88.75 78.75</XForm></Shape>
        </LightBurnProject>"""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "s.lbrn2"; p.write_text(xml)
            job = lbrn.import_file(p)
            sh = job["layers"][0]["shapes"]
            self.assertEqual(len(sh), 2); self.assertEqual(sh[1]["pts"][0], [10.0, 0.0]); self.assertTrue(sh[1]["closed"])
            self.assertEqual(job["source"]["defaults_applied"], [])


class Model(unittest.TestCase):
    def job(self):
        L1 = model.new_layer("L1", "FILL", 1, "fill", 100, 150, 20, 350, 3,
                             fill={"interval_mm": 0.1, "angle_deg": 0, "angle_per_pass_deg": 13, "bidir": True, "cross": False, "even_odd": True},
                             shapes=[model.polyline(SQ, True)])
        L0 = model.new_layer("L0", "LINE", 0, "line", 50, 400, 40, 200, 2, wobble={"size_mm": 0.1, "step_mm": 0.02},
                             shapes=[model.polyline(SQ, True), model.polyline([(20, 0), (25, 0)], False)])
        return model.new_job("t", [L1, L0])

    def test_validate_and_roundtrip(self):
        j = self.job()
        self.assertEqual(model.validate(j), [])
        with tempfile.TemporaryDirectory() as tmp:
            model.save(j, Path(tmp) / "t.raio")
            self.assertEqual(model.load(Path(tmp) / "t.raio"), j)
        self.assertEqual([L["name"] for L in model.run_order(j)], ["LINE", "FILL"])
        t = model.totals(j)
        self.assertAlmostEqual(t[0]["outline_mm"], 45.0); self.assertAlmostEqual(t[1]["area_mm2"], 100.0)

    def test_validate_errors(self):
        j = self.job()
        j["layers"][1]["power_pct"] = 120; j["layers"][0]["fill"] = {"interval_mm": 0.1}   # [0] = FILL, [1] = LINE
        j["layers"][1]["shapes"].append(model.polyline([(90, 0), (91, 0)], False))
        errs = " | ".join(model.validate(j))
        for frag in ("power_pct", "fill is missing", "outside the ±78.75"):
            self.assertIn(frag, errs)


class Planner(unittest.TestCase):
    def test_galvo_parity_with_driver(self):
        g = plan.Galvo()
        drv = SimpleNamespace(swap=True, sx=1, sy=1, u_per_mm=65535 / 157.5, cal_x=g.cal_x, cal_y=g.cal_y)   # the per-axis calibration
        for x, y in ((0, 0), (10, -5), (-70.3, 33.3), (74.9, -74.9)):   # inside the field after calibration
            self.assertEqual(g.mm(x, y), lmc.LMC.mm(drv, x, y))
        self.assertEqual(g.spd(1500), lmc.LMC.spd(drv, 1500))
        self.assertEqual(g.dist((0, 0), (300, 400)), lmc.LMC.dist((0, 0), (300, 400)))

    def test_no_device(self):
        with self.assertRaises(RuntimeError):
            lmc.LMC()

    def test_settings_and_entities(self):
        j = Model().job()
        p = plan.plan(j)
        c = p["cmds"]
        L = lmc.L
        self.assertEqual(c[0], (L["PulseWidth"], 0, 200))
        self.assertIn((L["QSwitchPeriod"], 500), c[:8])               # 40 kHz
        self.assertIn((L["MarkCurrent"], round(50 * 0xFFF / 100)), c[:8])
        self.assertIn((L["LaserOnDelay"], 300, 0x8000), c[:8]); self.assertIn((L["PolygonDelay"], 10), c[:8])
        self.assertIn((L["MarkSpeed"], int(400 * 65535 / 157.5 / 1000)), c[:8])
        # first entity: JumpTo, MO open, 8 ms, MarkTo…, end delay 30, MO close (mark_test.path_cmds)
        self.assertEqual(c[8][0], L["JumpTo"]); self.assertEqual(c[9], (L["FiberOpenMO"], 1)); self.assertEqual(c[10], (L["DelayTime"], 800))
        self.assertEqual(c[11][0], L["MarkTo"])
        opens = [i for i, x in enumerate(c) if x == (L["FiberOpenMO"], 1)]
        closes = [i for i, x in enumerate(c) if x == (L["FiberOpenMO"], 0)]
        self.assertEqual(len(opens), len(closes))
        self.assertTrue(all(c[i - 1] == (L["DelayTime"], 30) for i in closes))
        # line layer: 2 shapes × 2 passes; fill: 3 passes → 7 entities
        self.assertEqual(len(opens), 7)
        self.assertEqual(c[-1][:3], (L["JumpTo"], 0x8000, 0x8000))
        # settings change for the fill layer: pulse 350, 20 kHz → 1000, power 4095
        for want in ((L["PulseWidth"], 0, 350), (L["QSwitchPeriod"], 1000), (L["MarkCurrent"], 4095)):
            self.assertEqual(c.count(want), 1)
        self.assertEqual(sum(1 for x in c if x[0] == L["JumpSpeed"]), 1)   # unchanged settings are not repeated
        self.assertEqual(p["stats"]["total_passes"], 5)
        self.assertEqual(p["stats"]["packets"], math.ceil(p["stats"]["commands"] / 256))

    def test_fill_marked_length(self):
        L = model.new_layer("L1", "F", 0, "fill", 100, 150, 20, 350, 3,
                            fill={"interval_mm": 0.02, "angle_deg": 0, "angle_per_pass_deg": 0, "bidir": True, "cross": False, "even_odd": True},
                            shapes=[model.polyline(SQ, True)])
        p = plan.plan(model.new_job("f", [L]))
        # mark_mm is counted in the calibrated galvo frame: x lines carry the x scale (lmc/calibration.json)
        want = 3 * 100 / 0.02 * plan.Galvo().cal_x
        self.assertAlmostEqual(p["layers"][0]["mark_mm"], want, delta=want * 0.01)

    def test_preview(self):
        svg = plan.preview_svg(Model().job())
        self.assertIn('viewBox="', svg); self.assertIn("0. LINE", svg); self.assertIn("1. FILL", svg)
        with tempfile.TemporaryDirectory() as tmp:
            plan.preview_png(Model().job(), Path(tmp) / "p.png")
            self.assertGreater((Path(tmp) / "p.png").stat().st_size, 1000)


class Cli(unittest.TestCase):
    def test_mark_dry_run_stops_before_laser(self):
        with tempfile.TemporaryDirectory() as tmp:
            j = Path(tmp) / "t.raio"; model.save(Model().job(), j)
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(raio.main(["mark", str(j)]), 0)
                self.assertEqual(raio.main(["frame", str(j)]), 0)
                self.assertEqual(raio.main(["show", str(j)]), 0)
                self.assertEqual(raio.main(["plan", str(j), "--svg", str(Path(tmp) / "p.svg")]), 0)
            self.assertEqual(buf.getvalue().count("would open the laser"), 2)


if __name__ == "__main__":
    unittest.main()
