"""Segment a master into rig parts, following the drawing's own outlines.

label prior: the model's flat-colour part map (classified to its palette), corrected by manual
polygons (CFG['force']) and split by manual cut lines (CFG['cuts']: a part's region is divided
between two parts on either side of a polyline).
- non-ink regions of the master (split by its black lines) take the majority prior label;
- ink (outline) pixels go to the front-most part with paint within REACH px, else to the prior.
Writes seg/<who>_labels.npy (int16, -1 = empty) and a colour preview.
usage: seg.py boy|skull
"""
import json, os, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import segcfg
import paths

REACH = 9.0


def load_rgba(p):
    a = np.asarray(Image.open(p).convert('RGBA')).astype(np.float32)
    a[..., 3] = np.clip((a[..., 3] - 2) / (250 - 2), 0, 1) * 255   # the model's opaque is 253
    return a


def hexrgb(h):
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)


def classify_map(mp, parts):
    names = [p[0] for p in parts]; cols = np.stack([hexrgb(p[1]) for p in parts])
    rgb = mp[..., :3]; a = mp[..., 3] > 127
    d = np.linalg.norm(rgb[:, :, None, :] - cols[None, None], axis=-1)
    lab = np.argmin(d, -1).astype(np.int16); dist = d.min(-1)
    lab[~a | (dist > 70) | (rgb.mean(-1) < 40)] = -1
    return lab, names


def mode_fill(lab, n, k=7):
    """majority filter over known labels; unknown pixels take the local majority"""
    votes = np.stack([cv2.blur((lab == i).astype(np.float32), (k, k)) for i in range(n)])
    best = np.argmax(votes, 0).astype(np.int16)
    best[votes.max(0) < 1e-3] = -1
    return best


def poly_mask(shape, pts):
    m = Image.new('L', (shape[1], shape[0]), 0)
    ImageDraw.Draw(m).polygon([tuple(map(float, p)) for p in pts], fill=255)
    return np.asarray(m) > 127


def side_of(shape, line):
    """+1 / -1 for every pixel: which side of a polyline (extended at its ends) it lies on."""
    H, W = shape
    L = np.array(line, float)
    # extend the ends far along their directions
    d0 = L[0] - L[1]; d0 /= np.hypot(*d0); d1 = L[-1] - L[-2]; d1 /= np.hypot(*d1)
    P = np.vstack([L[0] + d0 * 4000, L, L[-1] + d1 * 4000])
    # the polygon closed on the 'left' side (relative to direction of travel)
    n = P[-1] - P[0]; n = np.array([-n[1], n[0]]) / np.hypot(*n)
    poly = np.vstack([P, P[-1] + n * 8000, P[0] + n * 8000])
    return np.where(poly_mask(shape, poly), 1, -1)


def run(who):
    cfg = segcfg.CFG[who]
    import pk
    M = pk.fix_alpha(load_rgba(cfg['master']))
    H, W = M.shape[:2]
    alpha = M[..., 3] / 255.
    lum = M[..., :3].mean(-1)
    fig = alpha > .5
    ink = fig & (lum < cfg.get('ink_lum', 48))
    mp = load_rgba(cfg['map'])
    lab0, names = classify_map(mp, cfg['palette'])
    n = len(names)
    prior = mode_fill(lab0, n, 9)
    # parts that the map does not have (split later by cuts) are added to the name list
    for nm in cfg.get('extra', []):
        if nm not in names: names.append(nm)
    idx = {nm: i for i, nm in enumerate(names)}
    # manual polygons override the prior
    for nm, pts in cfg.get('force', []):
        prior[poly_mask((H, W), pts)] = idx[nm]
    # cut lines: [part, line, part_on_left, part_on_right]
    for src, line, left, right in cfg.get('cuts', []):
        s = side_of((H, W), line)
        m = prior == idx[src]
        prior[m & (s > 0)] = idx[left]; prior[m & (s < 0)] = idx[right]
    # thick polylines (laces, strings) override the prior where it is one of `allowed`
    import cv2
    for nm, line, r, allowed in cfg.get('force_lines', []):
        mm = np.zeros((H, W), np.uint8)
        cv2.polylines(mm, [np.round(np.array(line)).astype(np.int32)], False, 1, int(2 * r))
        sel = (mm > 0) & fig
        if allowed: sel &= np.isin(prior, [idx[a] for a in allowed])
        prior[sel] = idx[nm]
    # fill unknown prior inside the figure from the nearest known
    known = prior >= 0
    _, (iy, ix) = ndimage.distance_transform_edt(~known, return_indices=True)
    prior = prior[iy, ix]
    # components of paint (non-ink) split by the master's lines
    paint = fig & ~ink
    comp, nc = ndimage.label(paint)
    lab = np.full((H, W), -1, np.int16)
    for c in range(1, nc + 1):
        m = comp == c
        v = np.bincount(prior[m], minlength=len(names))
        best = int(np.argmax(v))
        straddles = any(v[idx[a]] > .03 * m.sum() and v[idx[b]] > .03 * m.sum() for _, _, a, b in cfg.get('cuts', []))
        if m.sum() < 60:
            continue                             # specks take their surroundings' label (below)
        if v[best] >= .7 * m.sum() and not straddles:
            lab[m] = best
        else:                                    # a region the prior splits (cut lines): per pixel
            lab[m] = prior[m]
    small = paint & (lab < 0)
    if small.any():
        k0 = lab >= 0
        _, (iy0, ix0) = ndimage.distance_transform_edt(~k0, return_indices=True)
        lab[small] = lab[iy0, ix0][small]
    # ink: the front-most part with paint within REACH, else the prior
    order = cfg['order']                         # back -> front
    rank = {nm: k for k, nm in enumerate(order)}
    dist = {}
    for nm in order:
        if nm not in idx: continue
        core = lab == idx[nm]
        dist[nm] = ndimage.distance_transform_edt(~core) if core.any() else np.full((H, W), 1e9)
    out = lab.copy()
    todo = fig & (lab < 0)
    best_r = np.full((H, W), -1); best = np.full((H, W), -1, np.int16)
    for nm in order:
        if nm not in dist: continue
        near = todo & (dist[nm] <= cfg.get('reach', {}).get(nm, REACH))
        # also only parts the prior allows nearby (thin lines between two parts)
        better = near & (rank[nm] > best_r)
        best[better] = idx[nm]; best_r[better] = rank[nm]
    got = best >= 0
    out[todo & got] = best[todo & got]
    rest = todo & ~got
    # interior ink (pupils, hair, eye sockets): the label of the paint around it
    k2 = out >= 0
    _, (iy2, ix2) = ndimage.distance_transform_edt(~k2, return_indices=True)
    out[rest] = out[iy2, ix2][rest]
    # manual final overrides (ink-level) if any
    for nm, pts in cfg.get('force_final', []):
        m = poly_mask((H, W), pts) & fig
        out[m] = idx[nm]
    import cv2
    for nm, line, r in cfg.get('bands', []):
        mm = np.zeros((H, W), np.uint8)
        cv2.polylines(mm, [np.round(np.array(line)).astype(np.int32)], False, 1, int(2 * r))
        band = (mm > 0) & fig
        was = (out == idx[nm]) & ~band
        out[band & np.isin(out, [idx[a] for a in cfg['band_from'][nm]])] = idx[nm]
        if was.any():                     # what it held outside its band goes to its neighbours
            keep = (out >= 0) & (out != idx[nm])
            _, (iy3, ix3) = ndimage.distance_transform_edt(~keep, return_indices=True)
            out[was] = out[iy3, ix3][was]
    for src_l, line, left, right in cfg.get('final_cuts', []):
        sd = side_of((H, W), line); mm = out == idx[src_l]
        out[mm & (sd > 0)] = idx[left]; out[mm & (sd < 0)] = idx[right]
    os.makedirs(os.path.join(paths.WORK, 'seg'), exist_ok=True)
    np.save(os.path.join(paths.WORK, 'seg', f'{who}_labels.npy'), out)
    json.dump(names, open(os.path.join(paths.WORK, 'seg', f'{who}_names.json'), 'w'))
    # preview: tinted master + label colours
    rng = np.random.RandomState(3)
    cols = (rng.rand(len(names), 3) * 200 + 55).astype(np.uint8)
    prev = np.zeros((H, W, 3), np.uint8); prev[:] = (255, 0, 255)
    for i in range(len(names)):
        prev[out == i] = cols[i]
    base = M[..., :3].astype(np.float32)
    mix = (base * .45 + prev.astype(np.float32) * .55)
    mix[~fig] = (255, 0, 255)
    img = Image.fromarray(mix.astype(np.uint8))
    d = ImageDraw.Draw(img)
    for i, nm in enumerate(names):
        ys, xs = np.nonzero(out == i)
        if len(xs):
            d.text((int(np.median(xs)) - 10, int(np.median(ys))), nm, fill=(255, 255, 255))
    img.save(os.path.join(paths.WORK, 'seg', f'{who}_labels.png'))
    print(who, {nm: int((out == i).sum()) for i, nm in enumerate(names)})


if __name__ == '__main__':
    run(sys.argv[1])
