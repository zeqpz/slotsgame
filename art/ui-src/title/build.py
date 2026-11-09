# The title logo asset from the chosen take (r1/a.png: SMUKIEZ over & SKELLY): stray specks (small
# islands of alpha) removed, trimmed to its alpha with a small margin, saved as WebP with alpha.
#   python build.py  -> frontend/assets/title_logo.webp + preview.png here
import os
import numpy as np
from PIL import Image
from PIL import ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
im = Image.open(os.path.join(HERE, 'r1', 'a.png')).convert('RGBA')
px = np.array(im)
a = px[..., 3]
# white sparkles the model left on the outside of the outline (between the lines): near-white pixels
# within a few px of the empty background - the gloss inside the letters is ringed by colour instead
bgnd = np.asarray(Image.fromarray(np.where(a < 16, 255, 0).astype(np.uint8), 'L').filter(ImageFilter.MaxFilter(21))) > 0
white = (px[..., :3].min(axis=2) > 185) & (px[..., :3].max(axis=2) - px[..., :3].min(axis=2) < 50)
grow = white & bgnd
for _ in range(10):   # take the whole sparkle, not just its rim: grow through connected white
    grow = (np.asarray(Image.fromarray((grow * 255).astype(np.uint8), 'L').filter(ImageFilter.MaxFilter(5))) > 0) & white
a = np.where(grow, 0, a).astype(np.uint8)
# and one hand retouch: the sparkle star in the gap between the S and the & (r1/a.png only)
box = np.zeros(a.shape, bool); box[548:598, 556:614] = True; box[552:582, 600:648] = True
pale = (px[..., :3].min(axis=2) > 110) & (px[..., :3].max(axis=2) - px[..., :3].min(axis=2) < 70)
a = np.where(box & pale, 0, a).astype(np.uint8)
print('sparkle px', int(grow.sum()))
# islands by flood fill (no scipy here): each unvisited foreground pixel floods its island with a mark
mask = Image.fromarray(np.where(a > 24, 255, 0).astype(np.uint8), 'L')
keep = np.zeros(a.shape, bool)
n = kept = 0
while True:
    m = np.asarray(mask)
    ys, xs = np.nonzero(m == 255)
    if not len(ys):
        break
    ImageDraw.floodfill(mask, (int(xs[0]), int(ys[0])), 128)
    isl = np.asarray(mask) == 128
    n += 1
    if isl.sum() >= a.size * .002:
        keep |= isl; kept += 1
    mask.paste(0, mask=Image.fromarray((isl * 255).astype(np.uint8), 'L'))
keep = np.asarray(Image.fromarray((keep * 255).astype(np.uint8), 'L').filter(ImageFilter.MaxFilter(7))) > 0   # keep the soft edge
px[..., 3] = np.where(keep, a, 0)
out = Image.fromarray(px)
x0, y0, x1, y1 = out.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox()
m = 12
out = out.crop((max(0, x0 - m), max(0, y0 - m), min(out.width, x1 + m), min(out.height, y1 + m)))
out.save(os.path.join(ROOT, 'frontend', 'assets', 'title_logo.webp'), 'WEBP', quality=90, method=6)
bg = Image.open(os.path.join(ROOT, 'frontend', 'assets', 'bonus_wall.webp')).convert('RGBA').resize(out.size)
bg.alpha_composite(out)
bg.convert('RGB').save(os.path.join(HERE, 'preview.png'))
print('islands', n, 'kept', kept, 'size', out.size)
