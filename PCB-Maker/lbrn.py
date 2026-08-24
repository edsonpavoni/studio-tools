"""
lbrn.py — write LightBurn .lbrn2 files for the ComMarker B6 MOPA.

Pure standard library. No pip installs, no virtualenv, nothing to rot.

The format was reverse-engineered from `reference/ToR_008-REFERENCE.lbrn2`, the last
working file from the 2025 TRIBE board. Facts that matter and were verified, not assumed:

  * Root element carries AppVersion and DeviceName. LightBurn reads a file with a
    different DeviceName fine, but keeping "B6 Mopa" means the layer settings land on
    the right machine profile.
  * Every geometry unit here is MILLIMETRES, because each shape carries its own XForm
    and we always write the identity transform `1 0 0 1 cx cy`. The reference file used
    a 0.0127 scale factor because it came in through an SVG import; we do not.
  * Ellipse `Rx` is a genuine RADIUS. In the reference, Rx=23.622 with an XForm scale of
    0.0127 resolves to 0.300 mm radius, i.e. a 0.600 mm hole, which matches drill tool
    T1C0.600 exactly. Writing Rx in mm with an identity transform is equivalent.
  * Rect carries W and H in mm and its XForm translate is the CENTRE of the rectangle.
  * `priority` on a CutSetting is the run order. Lower runs first.

Usage:

    doc = LbrnDoc()
    doc.add_layer(HOLES)
    doc.add_circle(10, 10, dia=0.9, layer=HOLES)
    doc.save("out.lbrn2")
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom


# ─────────────────────────────────────────────────────────────────────────────
# Layers
# ─────────────────────────────────────────────────────────────────────────────

class Layer:
    """One LightBurn cut layer.

    mode      "Cut" for vector, "Scan" for raster fill.
    power     max power %, 0-100
    speed     mm/s
    freq      Hz  (37000 for the archived PCB recipe)
    passes    number of passes; omitted from the file when 1, matching the reference
    priority  run order, lower first
    qpulse    Q-pulse width in ns, or None to leave the device default
    interval  scan line interval in mm, or None to leave the device default
    min_power min power %, LightBurn calls this maxPower2
    """

    def __init__(self, index, name, mode, power, speed, freq, passes=1,
                 priority=0, qpulse=None, interval=None, min_power=20,
                 angle=None, angle_per_pass=None, cross_hatch=None,
                 global_repeat=None, bidir=None,
                 wobble=None, wobble_size=None, wobble_step=None, output=None):
        self.index = index
        self.name = name
        self.mode = mode
        self.power = power
        self.speed = speed
        self.freq = freq
        self.passes = passes
        self.priority = priority
        self.qpulse = qpulse
        self.interval = interval
        self.min_power = min_power
        # Tag names confirmed 2026-08-18 by reading Edson's own LightBurn library
        # rather than guessing: angle, anglePerPass, crossHatch, globalRepeat, bidir.
        self.angle = angle                    # scan angle, degrees
        self.angle_per_pass = angle_per_pass  # rotate the hatch this much each pass
        self.cross_hatch = cross_hatch        # 1 = on
        self.global_repeat = global_repeat    # LightBurn "Global Passes", multiplies numPasses
        self.bidir = bidir                    # 1 = bi-directional fill
        # Wobble: the beam traces a small circle as it travels, widening the kerf and
        # spreading the heat instead of concentrating it at a point. Edson's 1.1 mm
        # copper cut recipe relies on it for melt evacuation. Tags confirmed from his
        # own library: wobbleEnable / wobbleSize / wobbleStep.
        self.wobble = wobble
        self.wobble_size = wobble_size
        self.wobble_step = wobble_step
        self.output = output                  # 0 = layer never fires (reference)

    def to_xml(self):
        cs = ET.Element("CutSetting", {"type": self.mode})
        def v(tag, value):
            ET.SubElement(cs, tag, {"Value": str(value)})
        v("index", self.index)
        v("name", self.name)
        v("maxPower", self.power)
        v("maxPower2", self.min_power)
        v("speed", self.speed)
        v("frequency", self.freq)
        if self.passes and self.passes != 1:
            v("numPasses", self.passes)
        if self.qpulse is not None:
            v("QPulseWidth", self.qpulse)
        if self.interval is not None:
            v("interval", self.interval)
        if self.angle is not None:
            v("angle", self.angle)
        if self.angle_per_pass is not None:
            v("anglePerPass", self.angle_per_pass)
        if self.cross_hatch is not None:
            v("crossHatch", self.cross_hatch)
        if self.global_repeat is not None:
            v("globalRepeat", self.global_repeat)
        if self.bidir is not None:
            v("bidir", self.bidir)
        if self.wobble is not None:
            v("wobbleEnable", self.wobble)
        if self.wobble_size is not None:
            v("wobbleSize", self.wobble_size)
        if self.wobble_step is not None:
            v("wobbleStep", self.wobble_step)
        if self.output is not None:
            v("doOutput", self.output)
        v("priority", self.priority)
        return cs

    def describe(self):
        bits = ["%s%%" % self.power, "%s mm/s" % self.speed, "%g kHz" % (self.freq / 1000.0)]
        if self.passes != 1:
            bits.append("%s passes" % self.passes)
        if self.qpulse is not None:
            bits.append("%s ns" % self.qpulse)
        if self.interval is not None:
            bits.append("interval %s mm" % self.interval)
        if self.angle_per_pass is not None:
            bits.append("hatch +%s deg/pass" % self.angle_per_pass)
        if self.global_repeat is not None:
            bits.append("global x%s" % self.global_repeat)
        if self.wobble:
            bits.append("wobble %s/%s" % (self.wobble_size, self.wobble_step))
        return "%-8s %-4s  %s" % (self.name, self.mode, " · ".join(bits))


# ─────────────────────────────────────────────────────────────────────────────
# The archived PCB recipe, recovered from ToR_008 on 2026-08-17.
# See B6-PCB-RECIPE.md. Do not reorder the priorities.
# ─────────────────────────────────────────────────────────────────────────────

def pcb_layers(qpulse=200, interval=0.05):
    """The five production layers.

    ⚠️ The FILL recipe below is MEASURED, not inherited. Coupon 4, 2026-08-18: of twelve
    power/speed combinations, the only three that read OPEN on a multimeter were 75 % at
    1000, 1500 and 2000 mm/s. Everything at 50 % and below read short, i.e. the copper
    only darkened. 1500 is the centre of that band, so it is the production value.

    The archive's 95 % at 200 mm/s, recovered from the 2025 file, chars the board black.
    It is kept in B6-PCB-RECIPE.md as history, not as a recipe.

    HOLES is also measured, in two stages. Run 5 showed wobble halves the passes.
    Run 6, the 30-hole line at real 2.54 mm header pitch, then showed that **speed, not
    passes, is what buys a clean exit**: five recipes went through, but only the two at
    400 mm/s came out clean on the underside.

    400 mm/s x16 and 200 mm/s x8 deposit identical energy (1.78 s per 0.9 mm hole at
    100 % power) but 400 does it at half the dwell per millimetre, so the peak
    temperature is lower. 53 seconds for a 30-pin header row.

    ⚠️ **Labels and any text must NEVER share a layer with holes.** In run 6 the group
    numbers were engraved with the hole recipe, i.e. 32 passes of a drilling setting on
    a character, and each number put more heat into the board than the three holes it
    was labelling.

    ⚠️ Wobble widens the kerf, so a hole finishes LARGER than drawn by roughly the wobble
    size. Measure it and subtract, or every hole on a real board is oversize.
    Confirmed on V3 (2026-08-23): holes drawn 1.0 mm finished visibly larger than the
    TRIBE reference with a burned halo around the pad. circuit2lbrn now defaults
    --hole-kerf to 0.15 as compensation; the HOLES-2 coupon measures the true number.

    CUTOUT is still the weakest number here. 16 passes did not release the strip, 32 is a
    guess, and 64 caught fire in run 3 without wobble. Try wobble on the cutout too.
    """
    hole = dict(qpulse=qpulse, wobble=1, wobble_size=0.10, wobble_step=0.02)
    fill = dict(qpulse=qpulse, interval=interval, angle_per_pass=13)
    return [
        # Holes are split across two layers on a checkerboard so that no hole is drilled
        # next to one that is still hot. Measured on the 16-pin header test, 2026-08-18:
        # both orders cut through cleanly, and the interleaved row showed visibly less
        # burn and copper discolouration. The difference is small but real, and it costs
        # nothing but the order the holes are written in.
        # 16 passes proved OVERKILL on the first real board (V3, 2026-08-23): every
        # hole went through, but finished oversize with a burned halo eating into the
        # pad annulus — compare against the TRIBE board and it is obvious.
        # DIALED IN on the HOLES-2..5 coupon ladder (2026-08-24): 70% power, 8 passes.
        # The counterintuitive finding that locked the power: at 85-100% a hole
        # finishes SMALLER and dirtier — surplus energy melts/chars the exit closed
        # instead of widening it. 70%/8 with drawn = target − 0.24 (the measured
        # wobble kerf at this cell) seats a 2.54 header pin with light pressure and
        # keeps a TRIBE-class pad ring. The risk is still asymmetric: a hole that is
        # not through can be re-lasered by running the HOLES layers again.
        Layer(2, "HOLES_A", "Cut",   70,  400, 40000, passes=8, priority=0, **hole),
        Layer(4, "HOLES_B", "Cut",   70,  400, 40000, passes=8, priority=1, **hole),
        Layer(1, "CLEAR_1", "Scan",  75, 1500, 40000, passes=4,  priority=2, **fill),
        Layer(3, "CLEAR_2", "Scan",  75, 1500, 40000, passes=4,  priority=3, **fill),
        Layer(7, "ISOLATE", "Scan",  75, 1500, 40000, passes=4,  priority=4, **fill),
        # CUTOUT, measured directly 2026-08-18 and repeated several times: the square
        # releases on pass 5, occasionally 6, at 400 mm/s with a 0.30 wobble. 8 passes
        # is that plus margin, because a board that is 90 % released is not released.
        #
        # ⚠️ An earlier value of 16 came from ME inferring pass counts out of LightBurn's
        # progress percentage. That inference was wrong: the % does not track path
        # length. Watching the job beats arithmetic about the job.
        #
        # Note also that Edson's tapered-wobble idea never actually ran. In the winning
        # test every square fell during the first, widest stage, so the taper is
        # untested rather than disproven. The wide 0.30 opening is the part that works.
        # 8 passes destroyed part of V3 (2026-08-23): the board released around pass
        # 5-6 exactly as measured, FELL to the machine floor, and the remaining passes
        # kept firing into it. "Margin" after release is not margin, it is damage.
        # 6 passes, and STAND AT THE MACHINE for the cutout — it is the last layer and
        # takes under a minute. If it does not release, run the file again with only
        # CUTOUT enabled.
        Layer(8, "CUTOUT",  "Cut",  100,  400, 40000, passes=6, priority=5,
              qpulse=qpulse, wobble=1, wobble_size=0.30, wobble_step=0.04),
        Layer(9, "LABELS",  "Scan",  20, 1000, 40000, passes=1,  priority=6,
              qpulse=qpulse, interval=interval),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Document
# ─────────────────────────────────────────────────────────────────────────────

class LbrnDoc:
    def __init__(self, device="B6 Mopa", app_version="1.7.08", notes=""):
        self.device = device
        self.app_version = app_version
        self.notes = notes
        self.layers = []
        self.shapes = []

    def add_layer(self, layer):
        self.layers.append(layer)
        return layer

    # -- geometry, all in mm ---------------------------------------------------

    @staticmethod
    def _xform(cx, cy):
        return "1 0 0 1 %.6f %.6f" % (cx, cy)

    def add_rect(self, cx, cy, w, h, layer, corner_radius=0):
        """Rectangle centred on (cx, cy)."""
        sh = ET.Element("Shape", {"Type": "Rect", "CutIndex": str(layer.index),
                                  "W": "%.6f" % w, "H": "%.6f" % h,
                                  "Cr": str(corner_radius)})
        ET.SubElement(sh, "XForm").text = self._xform(cx, cy)
        self.shapes.append(sh)
        return sh

    def add_circle(self, cx, cy, dia, layer):
        """Circle of the given DIAMETER, centred on (cx, cy).

        The reference board drew every hole at its nominal drill diameter with no
        kerf compensation, so passing the drill size straight through is correct.
        """
        r = dia / 2.0
        sh = ET.Element("Shape", {"Type": "Ellipse", "CutIndex": str(layer.index),
                                  "Rx": "%.6f" % r, "Ry": "%.6f" % r})
        ET.SubElement(sh, "XForm").text = self._xform(cx, cy)
        self.shapes.append(sh)
        return sh

    def add_polygon(self, points, layer, closed=True):
        """Polygon or polyline through a list of (x, y) points in mm."""
        sh = ET.Element("Shape", {"Type": "Path", "CutIndex": str(layer.index)})
        ET.SubElement(sh, "XForm").text = self._xform(0, 0)
        ET.SubElement(sh, "VertList").text = "".join(
            "V%.6f %.6f" % (x, y) for x, y in points)
        ET.SubElement(sh, "PrimList").text = (
            "LineClosed" if closed else "L" * (len(points) - 1))
        self.shapes.append(sh)
        return sh

    def add_text(self, x, y, text, layer, height=3.0, font="Arial,-1,100,5,50,0,0,0,0,0"):
        """Left-baseline text. LightBurn renders it from Str on open."""
        sh = ET.Element("Shape", {"Type": "Text", "CutIndex": str(layer.index),
                                  "Font": font, "Str": text,
                                  "H": "%.6f" % height,
                                  "LS": "0", "LnS": "0", "Ah": "0", "Av": "0",
                                  "Weld": "1"})
        ET.SubElement(sh, "XForm").text = self._xform(x, y)
        self.shapes.append(sh)
        return sh

    # -- output ---------------------------------------------------------------

    def to_xml(self):
        # Priorities are a run ORDER, and the only file known to work used a
        # contiguous 0..N-1 range. Renumber rather than emitting something like 90.
        for rank, layer in enumerate(sorted(self.layers, key=lambda l: l.priority)):
            layer.priority = rank

        root = ET.Element("LightBurnProject", {
            "AppVersion": self.app_version,
            "DeviceName": self.device,
            "FormatVersion": "1",
            "MaterialHeight": "0",
            "MirrorX": "False",
            "MirrorY": "False",
        })
        for layer in sorted(self.layers, key=lambda l: l.priority):
            root.append(layer.to_xml())
        for sh in self.shapes:
            root.append(sh)
        if self.notes:
            notes = ET.SubElement(root, "Notes",
                                  {"ShowOnLoad": "1", "Notes": self.notes})
        return root

    def save(self, path):
        raw = ET.tostring(self.to_xml(), encoding="utf-8")
        pretty = minidom.parseString(raw).toprettyxml(indent="    ", encoding="UTF-8")
        with open(path, "wb") as fh:
            fh.write(pretty)
        return path

    def to_svg(self, path):
        """Write the same geometry as a plain SVG, one <g> per layer.

        Insurance. If LightBurn ever refuses a generated .lbrn2, import this instead
        and assign the five layers by hand from the table in B6-PCB-RECIPE.md. Slower,
        but never a dead end.
        """
        xs, ys = [], []
        for sh in self.shapes:
            xf = sh.find("XForm")
            if xf is None:
                continue
            cx, cy = float(xf.text.split()[4]), float(xf.text.split()[5])
            r = float(sh.get("Rx") or 0)
            w = float(sh.get("W") or 0) / 2
            h = float(sh.get("H") or 0) / 2
            vl = sh.find("VertList")
            if vl is not None and vl.text:
                for v in vl.text.split("V")[1:]:
                    a, b = v.split()
                    xs.append(float(a)); ys.append(float(b))
            else:
                xs += [cx - max(r, w), cx + max(r, w)]
                ys += [cy - max(r, h), cy + max(r, h)]
        pad = 2.0
        x0, x1 = (min(xs) - pad, max(xs) + pad) if xs else (0, 10)
        y0, y1 = (min(ys) - pad, max(ys) + pad) if ys else (0, 10)

        PALETTE = ["#d33", "#39c", "#2a2", "#c72", "#93c", "#666", "#c39", "#3aa"]
        out = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<svg xmlns="http://www.w3.org/2000/svg" width="%.3fmm" height="%.3fmm" '
               'viewBox="%.3f %.3f %.3f %.3f">' % (x1 - x0, y1 - y0, x0, -y1, x1 - x0, y1 - y0)]
        for n, layer in enumerate(sorted(self.layers, key=lambda l: l.priority)):
            out.append('<g id="%s" data-priority="%d" stroke="%s" fill="none" '
                       'stroke-width="0.1">' % (layer.name, layer.priority,
                                                PALETTE[n % len(PALETTE)]))
            for sh in self.shapes:
                if sh.get("CutIndex") != str(layer.index):
                    continue
                xf = sh.find("XForm").text.split()
                cx, cy = float(xf[4]), float(xf[5])
                t = sh.get("Type")
                if t == "Ellipse":
                    out.append('<circle cx="%.3f" cy="%.3f" r="%s"/>'
                               % (cx, -cy, sh.get("Rx")))
                elif t == "Rect":
                    w, h = float(sh.get("W")), float(sh.get("H"))
                    out.append('<rect x="%.3f" y="%.3f" width="%.3f" height="%.3f"/>'
                               % (cx - w / 2, -cy - h / 2, w, h))
                elif t == "Path":
                    vs = [v.split() for v in sh.find("VertList").text.split("V")[1:]]
                    pts = " ".join("%.3f,%.3f" % (float(a), -float(b)) for a, b in vs)
                    closed = "Closed" in (sh.find("PrimList").text or "")
                    out.append('<%s points="%s"/>' % ("polygon" if closed else "polyline", pts))
                elif t == "Text":
                    out.append('<text x="%.3f" y="%.3f" font-size="%s" fill="%s" '
                               'stroke="none">%s</text>'
                               % (cx, -cy, sh.get("H"), PALETTE[n % len(PALETTE)],
                                  sh.get("Str", "")))
            out.append("</g>")
        out.append("</svg>")
        with open(path, "w") as fh:
            fh.write("\n".join(out))
        return path

    def summary(self):
        counts = {}
        for sh in self.shapes:
            key = (sh.get("CutIndex"), sh.get("Type"))
            counts[key] = counts.get(key, 0) + 1
        by_index = {str(l.index): l for l in self.layers}
        lines = []
        for layer in sorted(self.layers, key=lambda l: l.priority):
            n = sum(v for k, v in counts.items() if k[0] == str(layer.index))
            lines.append("  pri %d  %s   [%d shapes]" % (layer.priority, layer.describe(), n))
        return "\n".join(lines)
