"""Re-render the grey-plate / blue-spray-rim family (HUD buttons, the long HUD plate, panels, boxes).

The x4 pass cleans the palette dither out of these, but what was blocky in the source (the dark
keyline that runs inside and outside the blue rim, the black glyphs) comes back as wobbly blobs.
Here the cleaned upscale is split into its paint layers - grey plate, blue rim, navy keylines,
glyph ink, accent paint - the layer map is smoothed (a majority vote over a small disc), and every
layer is painted again at the output size:

  - each layer keeps the cleaned upscale's own large-scale light and shade (a normalised blur inside
    the layer, so colours never bleed across a border) ...
  - ... and gets fresh fine detail at the output resolution: long vertical streaks and pits in the
    grey, spray grain in the blue, a faint grain in the ink;
  - the layers are blended with soft, sub-pixel masks, so every border is anti-aliased and sharp.

The silhouette (alpha) is the cleaned upscale's own, so the outline, the overspray and the shape
are exactly the art's.
"""
import numpy as np
from scipy import ndimage as nd

LAYERS = ("grey", "blue", "navy", "ink", "accent")


def _noise(shape, sx, sy, seed, octaves=3):
    """Smooth value noise, stretched sx by sy px (sy >> sx gives vertical streaks), in -1..1."""
    rng = np.random.default_rng(seed)
    h, w = shape
    out = np.zeros(shape, np.float32); amp = 1.0; tot = 0.0
    for o in range(octaves):
        gx, gy = max(2, int(w / sx) + 3), max(2, int(h / sy) + 3)
        g = rng.standard_normal((gy, gx)).astype(np.float32)
        up = nd.zoom(g, (h / (gy - 3), w / (gx - 3)), order=3, mode="grid-wrap", grid_mode=True)[:h, :w]
        if up.shape != shape:
            up = np.pad(up, ((0, h - up.shape[0]), (0, w - up.shape[1])), mode="edge")
        out += amp * up; tot += amp
        amp *= 0.5; sx /= 2; sy /= 2
    out /= tot
    return np.clip(out / (out.std() * 2.5 + 1e-6), -1, 1)


def _disc(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return (x * x + y * y) <= r * r + 0.5


def classify(rgb, alpha, accent=None):
    """Per-pixel layer scores from colour. Returns {layer: bool mask}."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    lum = .3 * r + .59 * g + .11 * b
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = mx - mn
    vis = alpha > 127
    blue_hue = (b > r + 25) & (b >= g)
    m = {}
    m["navy"] = vis & blue_hue & (lum < 62)
    m["blue"] = vis & blue_hue & (lum >= 62) & (sat > 55)
    m["ink"] = vis & (lum < 52) & ~blue_hue
    m["accent"] = np.zeros_like(vis)
    if accent:   # e.g. the yellow bolt, the pink/blue splats: anything saturated and not rim-blue
        m["accent"] = vis & (sat > 70) & ~blue_hue & (lum >= 52)
    m["grey"] = vis & ~(m["navy"] | m["blue"] | m["ink"] | m["accent"])
    return m


def majority(masks, radius):
    """Smooth the layer map: each pixel takes the layer most of its disc neighbourhood has."""
    k = _disc(radius).astype(np.float32); k /= k.sum()
    names = [n for n in LAYERS if masks[n].any()]
    votes = np.stack([nd.convolve(masks[n].astype(np.float32), k, mode="nearest") for n in names], 0)
    win = votes.argmax(0)
    vis = np.any(np.stack([masks[n] for n in names]), 0)
    vis = nd.convolve(vis.astype(np.float32), k, mode="nearest") > 0.5
    return {n: (win == i) & vis for i, n in enumerate(names)}, vis


def soft(mask, sigma):
    return nd.gaussian_filter(mask.astype(np.float32), sigma)


def within(img, mask, sigma):
    """Blur img inside mask only (normalised convolution): the layer's own light and shade."""
    w = nd.gaussian_filter(mask.astype(np.float32), sigma)
    out = np.stack([nd.gaussian_filter(img[..., c] * mask, sigma) for c in range(img.shape[-1])], -1)
    return out / np.maximum(w[..., None], 1e-4)


def render(base, scale, seed=7, accent=False, grain=1.0, streak=1.0):
    """base: HxWx4 uint8, the cleaned upscale at the output size. scale: output px per source px."""
    a = base.astype(np.float32)
    rgb, alpha = a[..., :3], a[..., 3]
    shape = alpha.shape
    masks = classify(rgb, alpha, accent)
    rad = max(1, int(round(0.9 * scale)))          # about one source pixel: below it is dither
    masks, vis = majority(masks, rad)
    sig_soft = 0.45 * max(1.0, scale / 2)            # AA width of the borders between layers
    out = np.zeros_like(rgb); wsum = np.zeros(shape, np.float32)
    s = max(1.0, scale)
    # fine detail, shared by the layers that want it
    streaks = _noise(shape, 2.2 * s, 46 * s, seed) * .6 + _noise(shape, 0.9 * s, 14 * s, seed + 1) * .4
    pits = _noise(shape, 1.1 * s, 1.1 * s, seed + 2, octaves=2)
    grain_n = _noise(shape, 0.7, 0.7, seed + 3, octaves=1)
    for n, m in masks.items():
        if not m.any():
            continue
        if n == "grey":
            # the cleaned upscale already carries the plate's scratches and streaks crisply: keep
            # it, drain the colour noise the dither left (the plates are neutral grey), add a
            # whisper of streak and grain at the output resolution
            col = rgb.copy()
            lum = col.mean(-1, keepdims=True)
            col = lum + (col - lum) * .35
            col += (streaks[..., None] * 4 + grain_n[..., None] * 2.5 * grain) * streak
        elif n == "blue":
            col = within(rgb, m, 0.6 * s)
            spray = _noise(shape, 1.3 * s, 1.3 * s, seed + 4, octaves=2)
            col *= (1 + spray[..., None] * .10 + grain_n[..., None] * .05 * grain)
        elif n == "navy":
            col = within(rgb, m, 2.0 * s)
            col = col * .7 + np.median(rgb[m], 0) * .3
        elif n == "ink":
            col = within(rgb, m, 1.0 * s)
            col = col * .55 + np.median(rgb[m], 0) * .45
            col += grain_n[..., None] * 3 * grain
        else:   # accent paint: keep its own colour, crisp
            col = within(rgb, m, 0.8 * s)
        w = soft(m, sig_soft)
        out += col * w[..., None]; wsum += w
    out = out / np.maximum(wsum[..., None], 1e-4)
    # alpha: the art's own silhouette (overspray, glow), cleaned of stray dither specks
    al = alpha.copy()
    al[al < 6] = 0
    return np.dstack([out.clip(0, 255), al]).round().astype(np.uint8)
