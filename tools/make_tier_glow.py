"""The paying tiers' neon glow (art/STYLE.md, "Symbol tiers"): a neon tube that hugs each premium
symbol's sticker edge, and a soft halo round it, as two pictures the game animates on their own
(the tube flickers like a neon sign, the halo breathes).

  python tools/make_tier_glow.py

art/icons-src/<ID>.png (the sticker's silhouette) -> frontend/assets/glow/<ID>_tube.webp, <ID>_halo.webp

Each picture is the icon's own canvas padded by PAD of its size on every side, so the game draws
it centred on the symbol at (1 + 2 * PAD) times the symbol's size and the two line up.
"""
import os
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "art", "icons-src")
OUT = os.path.join(ROOT, "frontend", "assets", "glow")
PAD = .22          # of the icon's size, each side (the game's --tglow-k is 1 + 2 * PAD)
SIZE = 420         # px on a side: the glow is drawn at ~1.4x a ~100 css px symbol, up to 3x DPR, and it is soft

hexrgb = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255
TIERS = {
    # top: a neon-lime tube with a white-hot core, its own lime light round it, and a violet halo beyond
    1: dict(ids=("H1", "H2", "H3"), tube=hexrgb("#6CFC54"), core=hexrgb("#F2FFC8"), spill=hexrgb("#6CFC54"), halo=hexrgb("#B454E4"), halo_a=.95),
    # premium: a violet tube, its violet light, and a deeper violet halo, quieter
    2: dict(ids=("H4", "H5", "H6", "H7"), tube=hexrgb("#C77DFF"), core=hexrgb("#F3DEFF"), spill=hexrgb("#B454E4"), halo=hexrgb("#6C24B4"), halo_a=.8),
}
# Sizes in icon units (1000 = the icon's side). A tile draws the icon ~72-100 css px across, so
# 14 units is about a css px: the tube is ~3-4 px wide and sits ~1-2 px off the white edge, the
# light it throws spreads ~12 px.
TUBE_AT, TUBE_HALF, CORE_HALF = 30, 20, 8
SPILL_FALL, HALO_FALL = 34, 95


def rgba(col, a):
    return Image.fromarray((np.dstack([np.broadcast_to(col, a.shape + (3,)), a]) * 255).clip(0, 255).round().astype(np.uint8), "RGBA")


def main():
    os.makedirs(OUT, exist_ok=True)
    for tier, t in TIERS.items():
        for sid in t["ids"]:
            al = np.asarray(Image.open(os.path.join(SRC, sid + ".png")).getchannel("A")).astype(np.float32) / 255
            n = al.shape[0]
            p = int(round(n * PAD))
            sil = np.pad(al > .5, p)
            d = ndimage.distance_transform_edt(~sil) * (1000 / n)          # icon units outside the sticker edge
            tube = np.exp(-((d - TUBE_AT) / TUBE_HALF) ** 4) * (d > 0)      # a flat-topped band just off the white edge
            core = np.exp(-((d - TUBE_AT) / CORE_HALF) ** 2) * (d > 0)
            col = t["tube"][None, None] * (1 - core[..., None] * .85) + t["core"][None, None] * (core[..., None] * .85)
            tube_im = Image.fromarray((np.dstack([col, tube]) * 255).clip(0, 255).round().astype(np.uint8), "RGBA")
            # the halo: the tube's own light close in, the deeper colour further out (premultiplied mix)
            out = np.maximum(d - TUBE_AT, 0) * (d > 0)
            spill = np.exp(-out / SPILL_FALL) * (d > 0) * .9
            far = np.exp(-out / HALO_FALL) * (d > 0) * t["halo_a"]
            a = np.clip(spill + far * (1 - spill), 0, 1)
            hcol = (t["spill"][None, None] * spill[..., None] + t["halo"][None, None] * (far * (1 - spill))[..., None]) / np.maximum(a, 1e-4)[..., None]
            # the blur spreads the halo's alpha in under the sticker, where it has no colour of its own:
            # give it the tube's light there, or the halo carries a black inner rim that shows the moment
            # it is drawn larger than the sticker (its win flare, its landing bloom, the burst's strain)
            hcol[d <= 0] = t["spill"]
            a = ndimage.gaussian_filter(a, 8 * n / 1000)
            halo_im = Image.fromarray((np.dstack([hcol, a]) * 255).clip(0, 255).round().astype(np.uint8), "RGBA")
            for name, im in (("tube", tube_im), ("halo", halo_im)):
                im = im.resize((SIZE, SIZE), Image.LANCZOS)
                im.save(os.path.join(OUT, f"{sid}_{name}.webp"), "WEBP", quality=90, alpha_quality=100, method=6)
    print("wrote", len(os.listdir(OUT)), "glow pictures to", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
