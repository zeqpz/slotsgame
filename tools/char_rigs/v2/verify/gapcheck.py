"""gapcheck.py <filmdir> [out.json] [--sheet]: gaps between parts, per frame.

A gap is wall showing through the figure: inside the figure's outer silhouette (holes filled,
eroded 3 px so the outline's own anti-aliased edge never counts), a pixel less than 90% opaque.
Reported per clip: the worst frame's gap px, the total over frames, and enclosed holes (see-through
regions of 6+ px fully surrounded by the figure). With --sheet, the worst frames with gaps marked."""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

D = sys.argv[1]
M = json.load(open(os.path.join(D, 'meta.json')))
res = {}
worst = []
EX = None; EXP = None
if '--exclude' in sys.argv:
    ex = sys.argv[sys.argv.index('--exclude') + 1]
    if ex.endswith('.npy'): EXP = np.load(ex)
    else: EX = np.asarray(Image.open(ex).convert('L')) > 0
import cv2
def ex_mask(f, shape):
    if EXP is None: return EX
    a_, b_, c_, d_, wx, wy = f.get('motion', [1, 0, 0, 1, 0, 0])
    X = EXP[:, 0]; Y = EXP[:, 1]                        # local y up; the bone matrix flips into the y-down world
    QX = a_ * X + b_ * Y + wx; QY = c_ * X + d_ * Y + wy
    S = M.get('scale', .5); cy = M.get('cy', 740)
    px = np.round(500 + QX * S).astype(int); py = np.round(500 + cy * S + QY * S).astype(int)
    m = np.zeros(shape, np.uint8); ok = (px >= 0) & (px < shape[1]) & (py >= 0) & (py < shape[0])
    m[py[ok], px[ok]] = 1
    return cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (29, 29))) > 0
for f in M['frames']:
    a = np.asarray(Image.open(os.path.join(D, f['tag'] + '.png')).convert('RGBA'))[..., 3].astype(np.float32) / 255
    fig = a > .5
    sil = ndimage.binary_fill_holes(fig)
    core = ndimage.binary_erosion(sil, iterations=3)
    gap = core & (a < .9)
    holes_m = sil & ~fig
    if EX is not None or EXP is not None:   # the drawing's own open space (between the legs) is not a gap
        E_ = ex_mask(f, a.shape)
        lab0, n0 = ndimage.label(sil & (a < .9))
        hit = np.unique(lab0[E_ & (lab0 > 0)])
        drop = np.isin(lab0, hit[hit > 0])
        gap &= ~drop; holes_m &= ~drop
    lab, n = ndimage.label(holes_m)
    sizes = ndimage.sum(holes_m, lab, range(1, n + 1)) if n else []
    holes = int(sum(s for s in sizes if s >= 6))
    r = res.setdefault(f['anim'], {'frames': 0, 'gap_px_max': 0, 'gap_px_sum': 0, 'hole_px_max': 0, 'worst_t': None})
    r['frames'] += 1
    g = int(gap.sum())
    r['gap_px_sum'] += g
    if g > r['gap_px_max']: r['gap_px_max'] = g; r['worst_t'] = round(f['t'], 3)
    r['hole_px_max'] = max(r['hole_px_max'], holes)
    if g or holes: worst.append((g + holes, f['tag'], gap | (holes_m & (lab > 0))))
for k, v in res.items():
    print(f"  {k:14s} frames {v['frames']:3d}  gap px worst {v['gap_px_max']:5d} (t={v['worst_t']})  total {v['gap_px_sum']:6d}  enclosed-hole px worst {v['hole_px_max']:5d}")
out = os.path.join(D, 'gaps.json')
json.dump(res, open(out, 'w'), indent=1)
if '--sheet' in sys.argv and worst:
    worst.sort(key=lambda w: -w[0])
    tiles = []
    for s, tag, mask in worst[:8]:
        im = Image.open(os.path.join(D, tag + '.png')).convert('RGBA')
        bg = Image.new('RGBA', im.size, (40, 40, 40, 255)); bg.alpha_composite(im)
        arr = np.asarray(bg.convert('RGB')).copy()
        dil = ndimage.binary_dilation(mask, iterations=3)
        arr[dil] = (255, 0, 255)
        t = Image.fromarray(arr); ImageDraw.Draw(t).text((5, 5), f'{tag} gap {s}', fill=(255, 255, 0))
        tiles.append(t)
    W, H = tiles[0].size
    sheet = Image.new('RGB', (W * min(4, len(tiles)), H * ((len(tiles) + 3) // 4)))
    for i, t in enumerate(tiles): sheet.paste(t, ((i % 4) * W, (i // 4) * H))
    sheet.save(os.path.join(D, 'gaps_worst.png')); print('sheet', os.path.join(D, 'gaps_worst.png'))
