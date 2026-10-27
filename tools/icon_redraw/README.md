# Icon redraw (2026-10-27)

The 20 board symbols were redrawn with `openai/gpt-image-2.5-sunburst` (OpenRouter Images API,
quality high, transparent background) from the old icons, to the art direction in `art/STYLE.md`:
the same drawings with far more detail and the shared lighting (key light upper left, cool rim
lower right), plain white sticker edges. The pay tiers are told apart by the game's animated neon
glow (`tools/make_tier_glow.py`), not by the art.

## Redo one icon (or all)

```
python tools/icon_redraw/redraw.py v5 H3            # raw model output -> %TEMP%/icon_redraw/v5/H3.png (~$0.06 each)
python tools/icon_redraw/install.py v5 H3 --dry     # fit only: prints the fit, writes an ink overlay to .../v5/align/
python tools/icon_redraw/install.py v5 H3           # fit + install -> art/icons-src/H3.png
python tools/icon_rigs/build.py                     # re-cut every rig into the atlas (all densities)
python tools/make_flat_icons.py                     # the flat pictures (paytable, loading rain, burst pieces)
python tools/make_tier_glow.py                      # the premium tiers' glow follows the new silhouette
```

The key is read from `%USERPROFILE%\.smukiez\openrouter-key.txt` (never printed, never committed).

## Why the old drawings stay (art/icons-src/geom/)

Every rig recipe (`tools/icon_rigs/recipes/`) cuts its parts with masks measured on the old drawing,
some of them by colour or by the black ink. `install.py` fits each new picture onto the old one (a
scale, turn and shift that lines up the silhouettes and the ink lines) and keeps the old drawing in
`art/icons-src/geom/`; `rigkit.Rig` reads the masks off `geom/` and cuts the pixels out of the new
art at the same spots. The fit prints `ink_old_to_new` (mean / 90th percentile px from each old ink
line to the nearest new one): under ~2 px mean the cuts land on the new lines. The redraw prompt
uses `geom/` as its reference too, so redrawing an icon again never drifts further from the rig.

The model leaves a faint alpha haze over its whole canvas; `install.py` keeps only the sticker's own
antialiased edge, or every rig part's box would spread to the canvas edge.
