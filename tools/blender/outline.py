"""The icon's silhouette as one closed path (icon px), a few px outside its sticker edge: the line the neon rim is
drawn along in Blender. Writes art/blender/parts/<ID>/<name>.json. Only measures the art; makes no animation.
usage: python tools/blender/outline.py <ID> [grow px] [--plate]
  --plate  trace the clean plate (art/blender/plates/<ID>.png: the icon without its moving front parts, e.g. the
           sack without its rope ends) -> outline_plate.json, so the rim hugs what stays put"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
args = [a for a in sys.argv[1:] if not a.startswith("--")]
sid = args[0]
grow = int(args[1]) if len(args) > 1 else 7
plate = "--plate" in sys.argv
src = os.path.join(ROOT, "art", "blender", "plates", sid + ".png") if plate else os.path.join(ROOT, "art", "icons-src", sid + ".png")
a = np.asarray(Image.open(src).convert("RGBA").getchannel("A"))
m = Image.fromarray(((a > 128) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(2 * grow + 1))
m = np.asarray(m.filter(ImageFilter.MedianFilter(9))) > 127          # grown, and its small notches smoothed
H, W = m.shape
pad = np.zeros((H + 2, W + 2), bool); pad[1:-1, 1:-1] = m
# Moore-neighbour tracing of the outer boundary, from the top-most, left-most pixel
ys, xs = np.nonzero(pad)
start = (ys.min(), xs[ys == ys.min()].min())
nb = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
path, cur, back = [start], start, 6
for _ in range(400000):
    for k in range(8):
        d = (back + 1 + k) % 8
        ny, nx = cur[0] + nb[d][0], cur[1] + nb[d][1]
        if pad[ny, nx]:
            back = (d + 4) % 8
            cur = (ny, nx)
            break
    if cur == start:
        break
    path.append(cur)
pts = [(x - 1.0, y - 1.0) for y, x in path]

def rdp(p, eps):                       # Ramer-Douglas-Peucker: keep the shape, drop the stair-steps
    if len(p) < 3:
        return p
    (x0, y0), (x1, y1) = p[0], p[-1]
    dx, dy = x1 - x0, y1 - y0
    n = math.hypot(dx, dy) or 1e-9
    d = [abs(dy * (x - x0) - dx * (y - y0)) / n for x, y in p[1:-1]]
    i = int(np.argmax(d)) + 1
    if d[i - 1] > eps:
        return rdp(p[:i + 1], eps)[:-1] + rdp(p[i:], eps)
    return [p[0], p[-1]]

half = len(pts) // 2
simple = rdp(pts[:half + 1], 1.6)[:-1] + rdp(pts[half:] + [pts[0]], 1.6)[:-1]
name = "outline_plate" if plate else "outline"
out = os.path.join(ROOT, "art", "blender", "parts", sid, name + ".json")
json.dump({"id": sid, "grow": grow, "source": "plate" if plate else "art", "points": [[round(x, 1), round(y, 1)] for x, y in simple]}, open(out, "w"))
print(sid, name + ":", len(path), "boundary px ->", len(simple), "points ->", out)
