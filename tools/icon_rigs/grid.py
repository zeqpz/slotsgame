"""Overlay a labelled coordinate grid on an icon, for reading recipe coordinates off the art.
   python tools/icon_rigs/grid.py L10 [step=50]   -> tools/icon_rigs/_preview/<ID>_grid.png"""
import os, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(HERE, "..", "..", "art", "icons-src", sys.argv[1] + ".png")
step = int(sys.argv[2]) if len(sys.argv) > 2 else 50
im = Image.open(src).convert("RGBA"); W, H = im.size
bg = Image.new("RGBA", im.size, (90, 90, 100, 255)); bg.alpha_composite(im)
d = ImageDraw.Draw(bg)
for x in range(0, W, step):
    d.line([(x, 0), (x, H)], fill=(255, 0, 80, 150 if x % (step * 2) == 0 else 70), width=1)
    if x % (step * 2) == 0: d.text((x + 2, 2), str(x), fill=(255, 255, 0, 255))
for y in range(0, H, step):
    d.line([(0, y), (W, y)], fill=(0, 200, 255, 150 if y % (step * 2) == 0 else 70), width=1)
    if y % (step * 2) == 0: d.text((2, y + 2), str(y), fill=(0, 255, 255, 255))
os.makedirs(os.path.join(HERE, "_preview"), exist_ok=True)
out = os.path.join(HERE, "_preview", sys.argv[1] + "_grid.png"); bg.convert("RGB").save(out); print(out)
