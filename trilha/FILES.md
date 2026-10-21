# Where a board lives

*Set 2026-08-25. There is no file management in the app yet, and that is a
deliberate choice, not an oversight: Edson asks Claude to open or start a board,
and Claude keeps the folders in order. Ideas for building it properly are parked
at the bottom, unscheduled.*

## What a board is

Two files, and only one of them matters if the machine burns down:

| file | what it is | precious? |
|---|---|---|
| `dist/index/circuit.json` | the circuit: components, nets, pads. Built by `tsci build` from the `.tsx` source. | no, rebuildable |
| `dist/index/board.handroute` | **the drawing**: strokes, component moves, outline, holes. Made by hand, in hours. | **yes, irreplaceable** |
| `dist/index/handroute-history/` | timestamped snapshots, at most one a minute | the safety net |

Everything else in a board folder is source, exports, or notes.

## The layout

```
projects/<project>/<board>/
├── index.circuit.tsx          the circuit, in code
├── PARTS.md                   what the real components are, with sources
├── LOG.md                     what happened, dated
├── dist/index/
│   ├── circuit.json           built
│   ├── board.handroute        THE DRAWING
│   └── handroute-history/     snapshots
└── laser/
    ├── V5-70x45.lbrn2         what was cut, named for the version and the size
    └── V5-70x45-FITTEST.lbrn2 the cardboard test that preceded it
```

`laser/` is the one addition to what grew organically: exported `.lbrn2` files
belong in their own folder rather than loose at the board root, where they
currently mix with source. Old drawings (`traces-*.json` from before the
`.handroute` format) are history and stay put until Edson says otherwise.

## What Claude does when asked

**"Open trilha on \<board\>"** *(since 2026-10-20 the server is always on,
port **8481**, kept up by `studio/ipad`; it serves whatever `trilha/current-board`
points at and re-reads that pointer on every request)*
1. Find the board's `circuit.json`; run `tsci build` first if it is stale.
2. `python3 studio/trilha/server.py <that circuit.json>`: it writes the pointer
   and tells the running server (it prints the board, the stroke count and both
   URLs). Never start a second server on another port for the same drawing.
3. Say which board is open and how many strokes it already has. The iPad shows it
   on its next load (the **Trilha** icon, or http://edsons-macbook-pro.local:8481).

**"Start a new board in \<project\>"**
1. Ask which it is: a **copy** of an existing board (the usual case, V5 → V6), or
   a **blank** one.
2. Make the folder to the layout above, with `PARTS.md` and `LOG.md` stubs.
3. Build, serve, hand over the URLs.

**Always**
- One server at a time. Two clients on one drawing overwrite each other silently,
  and that is the only way to lose an afternoon's work here.
- Exports get filed into `laser/` with a version name, not left in Downloads.
- Never delete a `.handroute`, a `traces-*.json`, or anything in a history
  folder. They are drawings.

---

## Ideas for later — NOT scheduled

Raised 2026-08-25, deferred by Edson until after the burn. Written down so the
thinking is not lost, not because any of it is agreed.

**Cheap and worth doing first regardless**
- **Say which board is open.** The header reads "Hand Route" and nothing else,
  although the app knows the path. Project · variant · `saved 12s ago`. That
  last part also closes a gap opened when the Save button went away: right now
  there is no evidence at all that autosave is working.

**The safety one**
- **Guard stale writes.** Two clients on one board silently overwrite each other
  every two seconds. The `.handroute` already carries a `saved` timestamp, so the
  server could refuse a write whose base is older than the file on disk and let
  the UI offer to reload. This is the only idea here that prevents lost work.

**Loading**
- Point the server at a **workspace root** instead of one `circuit.json`; scan
  for boards (skipping `node_modules`), group build variants under their project,
  put a switcher in the header. Measured 2026-08-25: 102 `circuit.json` files on
  this machine collapse to **2 real board projects**, so the scan is small.
  The real win is not having to walk back to the Mac to change board.

**Starting**
- **Duplicate** a board (V5 → V6). Matches how Edson already works by hand.
- **Blank board, no circuit**: an outline and holes, no components, no copper.
  The converter only *warns* about a circuit with no traces, it does not refuse,
  so this nearly works today. It would make trilha a way to cut FR4 objects
  (brackets, spacers, panels) and not only circuits.
- **New from tscircuit** (`tsci init` + `tsci build` run by the server). The
  complete answer, but it drags node and the tsci toolchain into a server that
  touches neither. Probably never: circuits get written in code, in a terminal.

**Naming**
- **Versions in the app.** Edson already keeps them by hand (V3-60x40,
  V4-60x40, V5-70x45). A "save as version" that snapshots `board-V6.handroute`,
  switches to it, and names the burn session's exports after it, so the drawing
  and the laser file finally share a name.
