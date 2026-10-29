# High-resolution art pass

The flat UI art (HUD plates and buttons, panels, win headlines, the digit font, the board frame, the
logo...) is rebuilt from `art/ui-src/` into `frontend/assets/` by the commands below. Not the wall
or its tag any more: since the 2026-10-27 redesign they are tile-detailed 3840 px art in
`art/wall-src/` (an upscale of the 1600 px copy in art/ui-src would undo that detail), so their
rows are out of assets.json.

```
python tools/hires/upscale.py              # everything in assets.json
python tools/hires/upscale.py hud_bar      # one asset
python tools/hires/upscale.py --list
```

Run it with the art venv (`smukiez-slot/.venv`: Pillow, numpy, scipy). It needs
[realesrgan-ncnn-vulkan](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0)
(`REALESRGAN=<path to the .exe>`, default `../.tools/realesrgan/` beside the repo). It runs on any
Vulkan GPU, and the x4 results are cached by content hash.

## Why

The review marked the game down for low-quality assets. Measuring every picture as drawn
(`device px drawn / natural px`, on 1080p, 1440p, 1920x1080@2x, 1440x900@2x and a 390x844@3x
phone) showed two problems:

- **Stretched art.** On any 2x screen (Retina laptops, 4K) the symbols, board frame, win headlines,
  digits, panels and the wall were drawn at 1.5-2.7x their own pixels, so they looked soft. The
  wall was soft even on 1080p (1.2x).
- **Dithered art.** About 25 HUD/panel PNGs had been saved as 256-colour palettes with
  error-diffusion dither, which reads as grit and blotches at any size.

## What each asset goes through

1. De-dither (palette art only, `dd`): a premultiplied Gaussian of 0.5-0.7 px that melts the
   dither dots without moving an edge.
2. Colour bleed under transparent pixels, so nothing dark is dragged into the edges.
3. Real-ESRGAN x4 (`realesrgan-x4plus-anime`, which keeps line art and flat fills clean).
4. Lanczos to the output size (`scale` x the source) with premultiplied alpha. Scales come from
   the measurement: drawn at or under 1:1 on a 2x screen. Art that was already big enough comes
   back at 1-1.25x, the same size without the dither.
5. `kit: "plate"` (the grey plate / blue spray rim family): `platekit.py` splits the cleaned
   upscale into its paint layers (grey plate, blue rim, navy keylines, ink, accent), smooths the
   layer map and repaints each layer with anti-aliased borders, a neutral grey and fresh fine
   grain. The board frame skips this: its thin keylines don't survive the layer vote.
6. WebP (quality 88-90, lossless alpha). The JPEG wall and all PNGs became WebP. `index.html`
   names the `.webp` files.

Where the shipped file had been re-encoded lossy, the source is the older lossless PNG from git
history (`01e6c50^`). The wall tag starts from the 1101 px original cut-out (`8f50a0f`), not the
2202 px copy blown up from it.

## The 2026-10-27 re-theme (art/STYLE.md)

The UI moved off electric blue onto the wall's palette: charcoal concrete plates, violet sprayed
edges, neon-lime trim and fire, gold only for wins. Two kinds of change:

- **Redrawn** with `openai/gpt-image-2.5-sunburst` (OpenRouter Images API), each piece's old art as
  the reference image, one key light from the upper left: the HUD (bar, hexagon, the four slanted
  plates, the bet steppers, the spin arrows), the six live-rim panels (bonus panel, rules panel,
  feature box, auto play box, win box, volume frame). The HUD pieces were drawn together on one
  sprite sheet so they share one hand and one light; the panels used that sheet as a style sample.
  Each redraw was cut out and laid exactly over the art it replaces (box fit, then an ECC fit of
  the two silhouettes), any saturated blue pushed to violet. The new source is
  `art/ui-src/<name>.png`, the replaced art is kept beside it as `<name>_v1.png`, and the row says
  `"esrgan": false`: the source is clean, full-colour art, only resampled (Lanczos keeps its grain;
  the anime model smeared the concrete and the photo model polished it flat).
- **Recoloured** (their drawing kept, hue bands moved onto the palette; originals in `_v1` too):
  the BIG / MEGA / TOTAL WIN lettering, the tier splash, the banner box, the board frame fallback,
  the volume liquid, the replay Play pill, the Close box, the BONUS plate's tube
  (`bonus_btn_plate.png`, from `art/letters/BONUS_plate.png`), and the unused spin plate / ui box /
  bet box. These keep their old rows (de-dither, Real-ESRGAN).
- **Redrawn on 2026-10-29**, the same way (each recolour as the reference, fitted over it): the
  BIG / MEGA / XTREME / TOTAL WIN headlines, the tier and total splashes, the digit font
  (`num/`, drawn together on one sheet so the twelve glyphs share one hand), the BONUS plate
  (`bonus_btn_plate.png`) and lettering (`bonus_text.png`, a new row that now makes
  `bonus_btn_text.webp` instead of `tools/letter_art/make.py`), the banner box and the Close box.
  The old art is kept as `_v1` (`num/<glyph>_v1.png`; `bonus_btn_plate_v1.png` and
  `bonus_text_v1.png` are copies of `art/letters/BONUS_plate.png` and `BONUS_traced.png`). XTREME
  WIN is a little taller than the art it replaced (1800x402): its redrawn drips are shorter and its
  letters taller, so it is scaled evenly to the old width rather than squashed into the old frame.
  They ship at WebP quality 78-86.

The live-rim cut-outs (`frontend/assets/rim/`) still take the plate's shape from the `_v1` art, so
the distance fields and `rims.json` did not change (`tools/sprayrim/make_rims.py`). The big
charcoal plates ship at WebP quality 56-64 for the full art (only seen without WebGL) and 72-78
for the rim cut-outs: the concrete grain costs bytes and looks the same.

Related passes:

- The symbol atlas is now 6.4 px per rig unit, up from 3.2 (`tools/icon_rigs/rigkit.py`,
  `OUT_PX_PER_UNIT`). It ships as WebP q95 pages.
- The two scatter cards are 800 px flat icons (`tools/make_flat_icons.py`, which upscales their
  512 px sources first).
