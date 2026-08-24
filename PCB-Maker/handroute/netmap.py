"""
netmap.py — extract the netlist and pad positions from a tscircuit circuit.json.

The drawing UI needs to know, for every pad on the board: where it is, what net it
belongs to, and what to call it ("PA.pin3"). circuit.json stores that across five
element types, joined by ids:

    source_component --- source_port --- pcb_port --- pcb_smtpad / pcb_plated_hole
                              \
                          source_trace --- source_net

Connectivity is a union-find over source ports and nets, using each source_trace's
connected id lists. The same extraction is used by the CONVERTER to independently
verify a hand-routed board, so the UI and the checker share one source of truth.
"""

import json


class Find:
    def __init__(self):
        self.p = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def extract(circuit_json_path):
    """-> dict with pads, nets, outline, holes, and the autoroute for background.

    pads: [{x, y, d, name, net}]          d = drill or pad size, mm
    nets: {net_name: [pad_index, ...]}     only pads that belong to a named net
    """
    cj = json.load(open(circuit_json_path))
    by = lambda t: [e for e in cj if e.get("type") == t]

    comp_name = {c["source_component_id"]: c.get("name", "?")
                 for c in by("source_component")}
    port = {p["source_port_id"]: p for p in by("source_port")}
    net_name = {n["source_net_id"]: n.get("name", n["source_net_id"])
                for n in by("source_net")}

    uf = Find()
    for t in by("source_trace"):
        ids = ([("p", i) for i in t.get("connected_source_port_ids", [])] +
               [("n", i) for i in t.get("connected_source_net_ids", [])])
        for a in ids[1:]:
            uf.union(ids[0], a)

    # name each connected component: a real net name if one is in the group,
    # otherwise a synthetic NET_<n>
    root_label = {}
    for nid, nm in net_name.items():
        root_label[uf.find(("n", nid))] = nm
    anon = [0]

    def label_of(pid):
        r = uf.find(("p", pid))
        if r not in root_label:
            anon[0] += 1
            root_label[r] = "NET_%d" % anon[0]
        return root_label[r]

    pcb_port = {p["pcb_port_id"]: p.get("source_port_id")
                for p in by("pcb_port")}

    pads, nets = [], {}
    for e in by("pcb_plated_hole") + by("pcb_smtpad"):
        x, y = e["x"], e["y"]
        # d is the COPPER outer size, because every clearance and contact check
        # runs against copper, not against the drill. Hole-diameter-first sized
        # round pads 0.25 mm too small and hid a weld from every vector check
        # while the raster (which uses true pad copper) kept failing the build.
        d = (max(e.get("rect_pad_width", 0) or 0, e.get("rect_pad_height", 0) or 0)
             or e.get("outer_diameter")
             or max(e.get("width", 0) or 0, e.get("height", 0) or 0)
             or ((e.get("hole_diameter") or 0.6) + 0.5))
        spid = pcb_port.get(e.get("pcb_port_id"))
        if spid and spid in port:
            p = port[spid]
            nm = "%s.%s" % (comp_name.get(p.get("source_component_id"), "?"),
                            p.get("name", "?"))
            net = label_of(spid)
        else:
            nm, net = "npth", None
        idx = len(pads)
        shape = "rect" if (e.get("rect_pad_width") or
                           e.get("shape") in ("rect", "rotated_rect", "pill")) else "circle"
        pads.append({"x": round(x, 3), "y": round(y, 3), "d": round(d, 2),
                     "shape": shape,
                     "name": nm, "net": net,
                     "pad_w": round(e.get("rect_pad_width") or e.get("width") or d, 2),
                     "pad_h": round(e.get("rect_pad_height") or e.get("height") or d, 2)})
        if net:
            nets.setdefault(net, []).append(idx)

    # nets with a single pad need no trace (they exist only through the pour or
    # are simply unconnected); drop them from the to-draw list
    nets = {k: v for k, v in nets.items() if len(v) > 1}

    boards = by("pcb_board")
    outline = None
    if boards:
        b = boards[0]
        if b.get("outline"):
            outline = [[p["x"], p["y"]] for p in b["outline"]]
        else:
            cx = b.get("center", {}).get("x", 0)
            cy = b.get("center", {}).get("y", 0)
            w, h = b["width"], b["height"]
            outline = [[cx - w/2, cy - h/2], [cx + w/2, cy - h/2],
                       [cx + w/2, cy + h/2], [cx - w/2, cy + h/2]]

    # autoroute background, tagged with its net so the UI can colour it as a guide
    st_net = {}
    for t in by("source_trace"):
        pids = t.get("connected_source_port_ids", [])
        if pids:
            st_net[t.get("source_trace_id")] = label_of(pids[0])
    auto = []
    for e in by("pcb_trace"):
        pts = [[round(s["x"], 3), round(s["y"], 3)]
               for s in e.get("route", []) if s.get("route_type") == "wire"]
        if len(pts) > 1:
            auto.append({"pts": pts,
                         "net": st_net.get(e.get("source_trace_id"))})

    holes = [{"x": e["x"], "y": e["y"], "d": e.get("hole_diameter", 1)}
             for e in by("pcb_hole")]

    comps = []
    for e in by("pcb_component"):
        c = e.get("center") or {}
        comps.append({"name": comp_name.get(e.get("source_component_id"), "?"),
                      "x": round(c.get("x", 0), 2), "y": round(c.get("y", 0), 2),
                      "w": round(e.get("width") or 2, 2),
                      "h": round(e.get("height") or 2, 2),
                      "rot": e.get("rotation") or 0})

    return {"pads": pads, "nets": nets, "outline": outline,
            "holes": holes, "auto": auto, "comps": comps}


if __name__ == "__main__":
    import sys
    d = extract(sys.argv[1])
    print("pads   :", len(d["pads"]))
    print("outline:", len(d["outline"] or []), "points")
    print("auto   :", len(d["auto"]), "background traces")
    print("nets to draw (%d):" % len(d["nets"]))
    for k, v in sorted(d["nets"].items()):
        names = [d["pads"][i]["name"] for i in v]
        print("   %-8s %d pads: %s" % (k, len(v), ", ".join(names)))
