# archive — the coupons that built the recipe

Superseded one-off generators, kept for provenance. Each one answered a question that
is now closed and recorded in `../B6-PCB-RECIPE.md`; their outputs and score sheets
live in `../coupon/`. They all expect to run from the tool root (`sys.path` trick for
`lbrn.py`), so move one back up a level if it ever needs to run again.

| script | question it answered | answer |
|---|---|---|
| make_coupon.py … coupon4.py | pulse width, interval, moat floor, fill recipe | 200 ns · 0.05 mm · 0.171 mm proven · 75%/1500/4x |
| make_material_test.py | which FR4 stock behaves | Qimoo 1.6 mm, 35 µm |
| make_hole_coupon.py / hole_line.py / header_test.py | do holes go through, interleave value | yes; interleave = less burn |
| make_cut_test.py | cutout passes | releases pass 5–6 |
| make_holes2.py | least passes that penetrate | 8 (all of 8/10/12 through) |
| make_holes3.py | wobble vs TRIBE no-wobble strategy | wobble wins; bracket 0.55–0.70 |
| make_holes4.py | least power that penetrates | 70% — MORE power chars holes SMALLER |
| RESULTS.html | visual log of the 2026-08-17 recovery | superseded by B6-PCB-RECIPE.md |

Still live in the tool root: `make_holes5.py` (defines the dialed hole cell),
`make_mount_coupon.py` (mount sizes + cutout squares), `make_width_coupon.py` (unrun,
would prove 0.2 mm traces — see BACKLOG.md).
