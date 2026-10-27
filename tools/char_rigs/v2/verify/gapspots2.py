"""gapspots2.py <frame.png> <out.png> [exclude.png] [zoom]: like gapspots, with the drawing's own open space excluded and bigger crops"""
import sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
p, out = sys.argv[1], sys.argv[2]
EX = np.asarray(Image.open(sys.argv[3]).convert('L')) > 0 if len(sys.argv) > 3 and sys.argv[3] != '-' else None
Z = int(sys.argv[4]) if len(sys.argv) > 4 else 4
im = Image.open(p).convert('RGBA'); A = np.asarray(im)
a = A[..., 3].astype(np.float32) / 255
fig = a > .5; sil = ndimage.binary_fill_holes(fig)
gap = ndimage.binary_erosion(sil, iterations=3) & (a < .9)
holes = sil & ~fig
if EX is not None:
    lab0, _ = ndimage.label(sil & (a < .9)); hit = np.unique(lab0[EX & (lab0 > 0)])
    drop = np.isin(lab0, hit[hit > 0]); gap &= ~drop; holes &= ~drop
m = gap | holes
lab, n = ndimage.label(ndimage.binary_dilation(m, iterations=3))
spots = []
for i, s in enumerate(ndimage.find_objects(lab), 1):
    mm = (lab[s] == i) & m[s]; ys, xs = np.nonzero(mm)
    spots.append((int(mm.sum()), int(xs.mean() + s[1].start), int(ys.mean() + s[0].start)))
spots.sort(reverse=True); print('spots', spots[:12])
bg = Image.new('RGBA', im.size, (60, 60, 60, 255)); bg.alpha_composite(im)
arr = np.asarray(bg.convert('RGB')).copy(); arr[m] = (255, 0, 255)
tiles = []
for sz, x, y in spots[:6]:
    c = Image.fromarray(arr).crop((x - 30, y - 30, x + 30, y + 30)).resize((60 * Z, 60 * Z), Image.NEAREST)
    ImageDraw.Draw(c).text((2, 2), f'{x},{y} {sz}', fill=(255, 255, 0)); tiles.append(c)
if tiles:
    sh = Image.new('RGB', (60 * Z * len(tiles), 60 * Z))
    for i, t in enumerate(tiles): sh.paste(t, (i * 60 * Z, 0))
    sh.save(out)
