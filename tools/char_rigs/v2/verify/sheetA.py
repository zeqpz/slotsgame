"""sheetA.py <filmdir> <out.png> [rowheight] [every]: alpha films composited on dark grey, one row per clip"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw
D, out = sys.argv[1], sys.argv[2]
H = int(sys.argv[3]) if len(sys.argv) > 3 else 260; every = int(sys.argv[4]) if len(sys.argv) > 4 else 2
M = json.load(open(os.path.join(D, 'meta.json')))
rows = {}
for f in M['frames']:
    if f['i'] % every == 0: rows.setdefault(f['anim'], []).append(f)
ims = {}; x0 = y0 = 10 ** 9; x1 = y1 = 0
for a, fs in rows.items():
    for f in fs:
        im = Image.open(os.path.join(D, f['tag'] + '.png')).convert('RGBA'); ims[f['tag']] = im
        bb = im.getbbox()
        if bb: x0 = min(x0, bb[0]); y0 = min(y0, bb[1]); x1 = max(x1, bb[2]); y1 = max(y1, bb[3])
x0 -= 4; y0 -= 4; x1 += 4; y1 += 4
w, h = x1 - x0, y1 - y0; s = H / h; tw = int(w * s)
ncol = max(len(fs) for fs in rows.values())
sheet = Image.new('RGB', (110 + tw * ncol, H * len(rows)), (45, 45, 52)); d = ImageDraw.Draw(sheet)
for r, (a, fs) in enumerate(rows.items()):
    d.text((4, r * H + 4), a, fill=(255, 255, 0))
    for c, f in enumerate(fs):
        t = ims[f['tag']].crop((x0, y0, x1, y1)).resize((tw, H), Image.LANCZOS)
        bg = Image.new('RGBA', t.size, (45, 45, 52, 255)); bg.alpha_composite(t)
        sheet.paste(bg.convert('RGB'), (110 + c * tw, r * H))
sheet.save(out); print(out, sheet.size)
