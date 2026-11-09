# The loading ident's letters (owner, 2026-11-08: letters drop in and bounce): the intro wordmark
# (frontend/assets/intro_wordmark.webp, white brush SMUKIEZ) cut into its letters, the swash under
# them and the seal, each saved trimmed with its place on the 2736x1160 wordmark so the page can
# stack them back exactly. The strokes run into each other, so the cut follows the strokes'
# own islands where they are separate (U, E, Z, the seal, the i's dot) and hand-set lines where
# they join (S|M, the swash below the letters, K|i).
#   python slice.py -> frontend/assets/intro_letters/<piece>.webp + pieces.json (+ check.png here)
import json, os
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
SRC = os.path.join(ROOT, 'frontend', 'assets', 'intro_wordmark.webp')
OUT = os.path.join(ROOT, 'frontend', 'assets', 'intro_letters')
im = Image.open(SRC).convert('RGBA')
px = np.array(im); A = px[..., 3]; H, W = A.shape
on = A > 60   # the islands at a firm threshold (the faint edges join strokes that only touch); the edges are grown back in below

# islands (flood fill on the mask; PIL does the fill)
mask = Image.new('L', (W, H), 0); mask.paste(Image.fromarray(np.where(on, 255, 0).astype(np.uint8), 'L'))   # a writable image of its own
lab = np.zeros(A.shape, np.int32); n = 0; info = []
while True:
    m = np.asarray(mask); ys, xs = np.nonzero(m == 255)
    if not len(ys): break
    ImageDraw.floodfill(mask, (int(xs[0]), int(ys[0])), 128)
    isl = np.asarray(mask) == 128
    n += 1; lab[isl] = n
    yy, xx = np.nonzero(isl)
    info.append(dict(id=n, size=int(isl.sum()), box=(int(xx.min()), int(yy.min()), int(xx.max()), int(yy.max())), cx=float(xx.mean()), cy=float(yy.mean())))
    mask.paste(0, mask=Image.fromarray((isl * 255).astype(np.uint8), 'L'))
info.sort(key=lambda d: -d['size'])
def find(x0, x1, y0, y1):   # the biggest island whose box starts in this window
    for d in info:
        bx = d['box']
        if x0 <= bx[0] <= x1 and y0 <= bx[1] <= y1: return d['id']
big = info[0]['id']
U = find(1080, 1160, 230, 340); E = find(1700, 1760, 300, 350); Z = find(1920, 1960, 150, 200)
SEAL = find(2200, 2230, 830, 860); DOT = find(1590, 1660, 300, 360)
for d in info[:10]: print(d['id'], d['size'], d['box'])
print('islands', n, 'big', info[0]['box'], 'U', U, 'E', E, 'Z', Z, 'seal', SEAL, 'dot', DOT)

yy, xx = np.mgrid[0:H, 0:W]
# the swash's upper edge: below this line (from x 800) a stroke is the swash, not a letter
LX = [800, 1250, 1500, 1700, 1940, 2600]; LY = [800, 745, 722, 735, 745, 885]
line = np.interp(xx, LX, LY)
below = (yy > line) & (xx >= 800)
I_REG = (xx >= 1640) & (xx <= 1795) & (yy >= 450)

piece = np.full(A.shape, '', dtype=object)
bigm = lab == big
piece[bigm & (xx < 765)] = 'S'
piece[bigm & (xx >= 765) & (xx < 1250) & ~below] = 'M'
piece[bigm & (xx >= 1250) & ~below & ~I_REG] = 'K'
piece[bigm & (xx >= 1250) & ~below & I_REG] = 'i'
piece[bigm & below & (xx >= 765)] = 'swash'
piece[lab == U] = 'U'
piece[lab == E] = 'E'
piece[(lab == Z) & ~below] = 'Z'
piece[(lab == Z) & below] = 'swash'
piece[lab == SEAL] = 'seal'
piece[lab == DOT] = 'i'
# every other speck goes with the piece nearest its middle
ORDER = ['S', 'M', 'U', 'K', 'i', 'E', 'Z', 'swash', 'seal']
named = piece != ''
cent = {}
for k in ORDER:
    ys_, xs_ = np.nonzero(piece == k); cent[k] = (xs_, ys_)
for d in info:
    isl = (lab == d['id']) & ~named
    if not isl.any(): continue
    ys_, xs_ = np.nonzero(isl); cx, cy = xs_.mean(), ys_.mean()
    best = min(ORDER, key=lambda k: np.min((cent[k][0][::50] - cx) ** 2 + (cent[k][1][::50] - cy) ** 2) if len(cent[k][0]) else 1e18)
    piece[isl] = best
# soft edges below the island threshold (alpha 1..10) go with their nearest assigned neighbour column-wise
rest = (A > 0) & (piece == '')
os.makedirs(OUT, exist_ok=True)
meta = {}
chk = Image.new('RGB', (W, H), (0, 0, 0))
COL = dict(S=(255, 80, 80), M=(255, 180, 60), U=(240, 240, 60), K=(80, 230, 80), i=(60, 230, 230), E=(80, 120, 255), Z=(200, 90, 255), swash=(255, 255, 255), seal=(255, 120, 200))
for k in ORDER:
    sel = piece == k
    # grow the selection by a couple of px into the faint edge so no hairline gap shows between pieces
    selg = np.asarray(Image.fromarray((sel * 255).astype(np.uint8), 'L').filter(__import__('PIL.ImageFilter', fromlist=['x']).MaxFilter(9))) > 0
    selg &= (piece == '') | sel
    out = px.copy(); out[..., 3] = np.where(selg, A, 0)
    ys_, xs_ = np.nonzero(out[..., 3] > 0)
    x0, y0, x1, y1 = int(xs_.min()), int(ys_.min()), int(xs_.max()) + 1, int(ys_.max()) + 1
    Image.fromarray(out[y0:y1, x0:x1]).save(os.path.join(OUT, f'{k}.webp'), 'WEBP', quality=92, method=6)
    meta[k] = [x0, y0, x1 - x0, y1 - y0]
    c = np.zeros((H, W, 3), np.uint8); c[sel] = COL[k]
    chk = Image.fromarray(np.maximum(np.asarray(chk), c))
json.dump(dict(size=[W, H], pieces=meta), open(os.path.join(OUT, 'pieces.json'), 'w'), indent=1)
chk.resize((W // 2, H // 2)).save(os.path.join(HERE, 'check.png'))
print(json.dumps(meta))
