"""The boy's parts laid back together at rest (no bills) vs the master, and every part alone on magenta ->
art/blender/chars/boy/qa/parts_rest.png, parts_sheet.png. Run with the project venv python."""
import json, os
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
BOY = os.path.join(ROOT, "art", "blender", "chars", "boy")
PARTS = os.path.join(BOY, "parts")
spec = json.load(open(os.path.join(PARTS, "parts.json")))
W, H = spec["size"]
os.makedirs(os.path.join(BOY, "qa"), exist_ok=True)
can = np.zeros((H, W, 4), np.float32)
tiles = []
for p in spec["parts"]:
    n = "head_idle" if p["name"] == "head" else p["name"]
    if n == "bills":
        continue
    im = np.asarray(Image.open(os.path.join(PARTS, n + ".png")).convert("RGBA")).astype(np.float32) / 255.
    x0, y0, x1, y1 = p["box"]
    a = im[..., 3:4]
    can[y0:y1, x0:x1, :3] = im[..., :3] * a + can[y0:y1, x0:x1, :3] * (1 - a)
    can[y0:y1, x0:x1, 3:] = a + can[y0:y1, x0:x1, 3:] * (1 - a)
    t = Image.new("RGBA", (x1 - x0, y1 - y0), (255, 0, 255, 255)); t.alpha_composite(Image.fromarray((im * 255).astype(np.uint8)))
    tiles.append(t.convert("RGB"))
M = np.asarray(Image.open(os.path.join(ROOT, "art", "characters-src", "v2", "boy", "master.webp")).convert("RGBA")).astype(np.float32) / 255.
def wall(x):
    return (x[..., :3] * x[..., 3:] + np.array([.23, .2, .29]) * (1 - x[..., 3:]))
d = np.abs(wall(can) - wall(M)).max(-1)
cash = np.zeros((H, W), bool); cash[700:1030, 470:770] = True
print("rest vs master (outside the cash): mean %.2f/255, p99.5 %.1f" % (d[~cash].mean() * 255, np.percentile(d[~cash], 99.5) * 255))
out = np.concatenate([wall(can), wall(M), np.repeat(np.clip(d * 4, 0, 1)[..., None], 3, -1)], 1)
Image.fromarray((out * 255).astype(np.uint8)).save(os.path.join(BOY, "qa", "parts_rest.png"))
w = sum(t.size[0] for t in tiles); h = max(t.size[1] for t in tiles)
sheet = Image.new("RGB", (w, h)); x = 0
for t in tiles:
    sheet.paste(t, (x, 0)); x += t.size[0]
sheet.save(os.path.join(BOY, "qa", "parts_sheet.png"))
