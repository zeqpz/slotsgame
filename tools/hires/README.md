# High-resolution art pass

The flat UI art (HUD plates and buttons, panels, win headlines, the digit font, the wall, the board
frame, the wall tag, the logo...) is rebuilt from `art/ui-src/` into `frontend/assets/` by

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

Related passes:

- The symbol atlas is now 6.4 px per rig unit, up from 3.2 (`tools/icon_rigs/rigkit.py`,
  `OUT_PX_PER_UNIT`). It ships as WebP q95 pages.
- The two scatter cards are 800 px flat icons (`tools/make_flat_icons.py`, which upscales their
  512 px sources first).
