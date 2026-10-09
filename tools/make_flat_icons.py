"""Flat icon pictures for everything that is not the animated board: the paytable, the
loading-screen icon rain, the feature plates, the bonus cards and the shards of a blown-out tile.

  python tools/make_flat_icons.py

art/icons-src/<ID>.png (the full-size icon art, also the rig sources) -> frontend/assets/flat/<ID>.webp
at 400 px on the long side (sharp at 2x DPR wherever they appear), WebP quality 95 with lossless alpha.
"""
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "art", "icons-src")
OUT = os.path.join(ROOT, "frontend", "assets", "flat")
SIZE = 400

os.makedirs(OUT, exist_ok=True)
total = 0
for f in sorted(os.listdir(SRC)):
    if not f.endswith(".png"):
        continue
    im = Image.open(os.path.join(SRC, f)).convert("RGBA")
    s = SIZE / max(im.size)
    if s < 1:
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    dst = os.path.join(OUT, f[:-4] + ".webp")
    im.save(dst, "WEBP", quality=95, method=6, alpha_quality=100)
    total += os.path.getsize(dst)
print(f"wrote {len(os.listdir(OUT))} flat icons, {total // 1024} KB")
