#!/usr/bin/env python3
"""tests/ui/many-layers.raio: a board test with many layers at very low power (Edson, 2026-10-22 00:23:
"a work on the bed that has many layers, with a very low power work so I can actually fire to test, and to see the UI").
5–8 % power on a metal offcut: a faint mark, the UI's progress through layers and passes is the point. 0 % is not off
(04-safety.md): this still emits. Run: python3 tests/ui/make_many_layers.py → tests/ui/many-layers.raio"""
import json, math
from datetime import datetime
from pathlib import Path

DELAYS = {"on_us": -300, "off_us": 100, "poly_us": 100, "jump_us": 500, "end_us": 300}
rect = lambda x0, y0, x1, y1: [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
circle = lambda cx, cy, r, n=72: [[round(cx + r * math.cos(2 * math.pi * k / n), 4), round(cy + r * math.sin(2 * math.pi * k / n), 4)] for k in range(n)]
poly = lambda pts, closed=True: {"type": "polyline", "closed": closed, "pts": pts}


def layer(i, name, mode, power, speed, freq, ns, passes, shapes, wobble=None, fill=None, output=True):
    return {"id": f"L{i}", "name": name, "order": i, "output": output, "mode": mode, "power_pct": float(power), "speed_mm_s": float(speed),
            "freq_khz": float(freq), "pulse_ns": ns, "passes": passes, "wobble": wobble, "fill": fill, "kerf_mm": 0,
            "delays": dict(DELAYS), "shapes": shapes}


fill = lambda interval, angle=0.0, per_pass=0.0: {"interval_mm": interval, "angle_deg": angle, "angle_per_pass_deg": per_pass,
                                                   "bidir": True, "cross": False, "even_odd": True}
layers = [
    layer(0, "BORDER", "line", 5, 150, 30, 200, 4, [poly(rect(-15, -10, 15, 10))]),
    layer(1, "CROSS", "line", 5, 100, 30, 200, 4, [poly([[-3, 0], [3, 0]], False), poly([[0, -3], [0, 3]], False)]),
    layer(2, "RING_WOBBLE", "line", 6, 600, 65, 200, 3, [poly(circle(-8, 3, 3.5))], wobble={"size_mm": 0.15, "step_mm": 0.025}),
    layer(3, "SQUARE_FILL", "fill", 6, 500, 40, 200, 4, [poly(rect(4, 1, 12, 7))], fill=fill(0.1, 0.0, 45.0)),
    layer(4, "DOT_FILL", "fill", 5, 500, 60, 100, 2, [poly(circle(-8, -5, 2.5, 48))], fill=fill(0.08, 45.0)),
    layer(5, "TRIANGLE", "line", 8, 100, 30, 200, 8, [poly([[4, -7], [12, -7], [8, -2]])]),
    layer(6, "INNER_RING", "line", 5, 100, 30, 200, 8, [poly(circle(0, 0, 6))]),
    layer(7, "GUIDE", "line", 5, 1000, 30, 200, 1, [poly(rect(-16, -11, 16, 11))], output=False),
]
job = {"raio": 1, "name": "many-layers-ui-test", "created": datetime.now().isoformat(timespec="seconds"),
       "source": {"file": "studio/raio/tests/ui/make_many_layers.py", "kind": "script", "defaults_applied": [], "defaults_by_layer": {},
                  "import_warnings": [], "imported": datetime.now().isoformat(timespec="seconds")},
       "material": {"name": "metal offcut (steel or aluminium)", "thickness_mm": None},
       "notes": "UI test: 7 output layers at 5–8 % power, about 30 × 20 mm at the field centre. A faint mark on metal; never card.",
       "layers": layers}
out = Path(__file__).with_name("many-layers.raio")
out.write_text(json.dumps(job, indent=1))
print(out)
