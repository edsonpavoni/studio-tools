# handroute — draw the traces yourself, iPad + Pencil

The autorouter connects things; it does not compose them. This replaces it with your
hand: the board's pads and netlist load into a canvas, you draw each connection with
the Apple Pencil, and a live checklist ticks nets off as they complete. The routing
becomes part of the object, the way the 2025 TRIBE board's big sweeping curve was.

## Run

```bash
cd tools/PCB-Maker/handroute
python3 server.py /path/to/board/dist/index/circuit.json
```

Open the printed URL in Safari on the iPad (same WiFi). Then:

| gesture | does |
|---|---|
| Pencil | draw a trace |
| one finger drag | pan |
| pinch | zoom |
| Erase button + Pencil tap | delete a trace |

Stroke ends **snap to pads** within ~1 mm, and to existing traces for junctions.
Strokes are simplified and smoothed (RDP + Chaikin) so the line stays organic without
the jitter. Width buttons set the trace width for the next stroke: 0.4 / 0.5 / 0.8 /
1.2 mm.

**The checklist** on the right shows every net except GND (GND is the pour; its pads
join the plane automatically and are drawn dark). A net ticks green when all its pads
are connected through drawn copper. A stroke that bridges two different nets turns
red and raises a SHORT alert. A stroke that passes closer than **0.171 mm** to
foreign copper gets an orange halo and a gap warning.

The faint copper lines are the autoroute, as a reference of what connects to what.
The Ghost button hides them. Saves are automatic every 20 s and on the Save button;
every save also keeps a timestamped copy in `traces-history/`.

## Making the board

```bash
python3 ../circuit2lbrn.py circuit.json --manual-traces auto --moat -o board.lbrn2
```

`--moat` clears only a 0.5 mm ring around the signal copper; everything else stays
as the ground pour. That is the strategy the coupons proved, and it is 10-20x less
laser time than clearing fields.

**The UI is not trusted.** The converter re-verifies the saved strokes independently
(`verify.py`): every net complete, no two nets bridged, no gap under `--floor`
(default 0.171 mm, the proven value). It refuses to write a laser file otherwise.
Two constants were tuned the hard way and matter:

- contact tolerance is **0.08 mm** — it must be *below* the minimum clearance, or a
  trace passing legally close to a foreign pad reads as touching it
- hand-drawn widths are **never widened** by `--min-trace`; the verifier validated
  the drawn geometry and widening afterwards would invalidate it

## Files

| file | role |
|---|---|
| `server.py` | serves the UI, saves `traces.json` next to circuit.json |
| `ui.html` | the whole drawing app, one file, no dependencies |
| `netmap.py` | pads + netlist out of circuit.json (shared with the converter) |
| `verify.py` | the independent checker the converter runs |
