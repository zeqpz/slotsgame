"""Flat icon pictures for everything that is not the animated board: the paytable, the
loading-screen icon rain, the feature plates, the bonus cards and the shards of a blown-out tile.

  python tools/make_flat_icons.py

art/icons-src/<ID>.png (the full-size icon art, also the rig sources) -> frontend/assets/flat/<ID>.webp
at 400 px on the long side (sharp at 2x DPR wherever they appear), WebP quality 95 with lossless alpha.
The two scatters are 800 px: the bonus-buy cards show them up to 790 device px wide on a phone. They
come from their 1024 px renders in art/letters/ (tools/letter_art/make.py); any other source smaller
than its size goes through the Real-ESRGAN x4 pass first (tools/hires).
"""
import os, sys
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "hires"))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "art", "icons-src")
OUT = os.path.join(ROOT, "frontend", "assets", "flat")
SIZE = 400
BIG = {"BS": 800, "ES": 800}

os.makedirs(OUT, exist_ok=True)
total = 0
for f in sorted(os.listdir(SRC)):
    if not f.endswith(".png"):
        continue
    im = Image.open(os.path.join(SRC, f)).convert("RGBA")
    size = BIG.get(f[:-4], SIZE)
    # (the scatters used to come from their traced letter renders in art/letters/; since the
    # 2026-10-27 redraw art/icons-src holds the new art for every icon, scatters included)
    if max(im.size) < size:
        import upscale
        im = upscale.esrgan(upscale.bleed(im), upscale.A)
    s = size / max(im.size)
    if s < 1:
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    dst = os.path.join(OUT, f[:-4] + ".webp")
    im.save(dst, "WEBP", quality=95, method=6, alpha_quality=100)
    total += os.path.getsize(dst)
print(f"wrote {len(os.listdir(OUT))} flat icons, {total // 1024} KB")
