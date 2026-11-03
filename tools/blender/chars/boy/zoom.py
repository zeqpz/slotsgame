"""zoom helper: python zoom.py out.png clip:frame:x:y[:size] ... -> crops at 3x on the wall colour, in a row"""
import os, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
REN = os.environ.get("BOY_RENDERS") or os.path.join(ROOT, "art", "blender", "chars", "boy", "renders")
out, specs = sys.argv[1], sys.argv[2:]
tiles = []
for s in specs:
    p = s.split(":")
    clip, f, x, y = p[0], int(p[1]), int(p[2]), int(p[3])
    sz = int(p[4]) if len(p) > 4 else 80
    sc = int(p[5]) if len(p) > 5 else 3
    im = Image.open(os.path.join(REN, clip, f"{f + 1:04d}.png")).convert("RGBA")
    bg = Image.new("RGBA", im.size, (58, 52, 74, 255)); bg.alpha_composite(im)
    t = bg.crop((x - sz, y - sz, x + sz, y + sz)).resize((2 * sz * sc, 2 * sz * sc), Image.LANCZOS).convert("RGB")
    ImageDraw.Draw(t).text((4, 4), s, fill=(255, 255, 0))
    tiles.append(t)
W = sum(t.size[0] for t in tiles); H = max(t.size[1] for t in tiles)
o = Image.new("RGB", (W, H)); x = 0
for t in tiles:
    o.paste(t, (x, 0)); x += t.size[0]
o.save(out)
