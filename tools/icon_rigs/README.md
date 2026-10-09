# Animated symbols (Spine rigs)

Every board symbol is a Spine 4.2 skeleton built from its icon art by `rigkit.py`:

- `recipes/<ID>.py` - one per symbol: the parts (masks over the 1000 px icon), pivots, parents,
  draw order, and the clips `idle` / `land` / `win` as keyframes. Read `rigkit.py`'s docstrings for
  the mask ops (`poly`, `disc`, `ellipse`, `rect`, `color`, `ink`, `along`, `grow`, `minus`, ...)
  and the channels (`x`, `y` in skeleton units, `r` degrees counter-clockwise, `sx`, `sy`;
  `alpha` per slot). Keys are `(time, value, ease)`; the ease shapes the run *into* that key
  (`in`, `out`, `inout`, `back`, `snap`, `drop`, `soft`, `linear`, `step`, or a bezier tuple).
- `python tools/icon_rigs/build.py --preview-only <ID>` - cut one rig and write preview sheets to
  `tools/icon_rigs/_preview/` (`<ID>_parts.png`, `<ID>_idle.png`, `<ID>_land.png`, `<ID>_win.png`).
- `python tools/icon_rigs/build.py` - build every rig into the game: `frontend/assets/icons/`
  (one atlas + `icons.json`, which the game loads) and `art/icons-spine/<ID>.json` (one skeleton per
  file, for the Spine editor).
- `python tools/icon_rigs/grid.py <ID>` - the icon with a labelled 50 px grid, for reading coordinates.

In the game (`frontend/index.html`, "animated symbols"), the Spine runtime evaluates every clip once
at load (30 fps, then thinned by `rigThin` to the keyframes the browser cannot blend its own way to,
within a quarter of a rig unit) and parses each part's track once into a `KeyframeEffect`. Each cell's
rig is a clone of a per-symbol template, and a play copies the prepared effects. Clips play as Web
Animations on the parts inside each cell: `idle` from the moment a tile starts to drop in (started by
`dropIn`, a few per frame) and now and then between rounds, `win` when its cluster lights up. `land`
is kept as the fallback for a rig with no `idle`.

Style rules for clips: every clip starts and ends on the rest pose; `idle` 2-3 s, `land` 0.45-0.6 s,
`win` 1.2-1.5 s; at most ~14 parts per symbol; motion stays within ~15 units of the icon's box.

Tips the first 20 rigs taught (see their recipes for worked examples):
- Hard seams between parts in flat paint: wrap a `poly`/`rect` in `("cc", mask, x, y)` to make it
  binary, or the antialiased edge leaves a see-through hairline where two parts meet.
- `("opaque",)` inside a part mask squares alpha at soft edges (the source is premultiplied); use
  `("grow", ("opaque",), 2)`.
- A part that only exists to repair a hole (cut with `fill`, left out of `draw`) costs no atlas
  space; neither do helper bones made from tiny hidden sprites.
- Large `fill` holes near the silhouette come out semi-transparent (the transparent outside counts
  as known pixels); keep such moves small or cover them with a copy part.
- The game plays transforms and opacity only (no shear preview, no blend modes): glints are sprites.
