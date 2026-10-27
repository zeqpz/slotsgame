# fit each generated icon onto the drawing the rigs were measured on, and install it:
#   python tools/icon_redraw/install.py <tag> <icon,..|all> [--dry]
# The old drawing is kept as art/icons-src/geom/<ID>.png (the rigs cut along its outlines); the aligned
# new art replaces art/icons-src/<ID>.png. The fit is a similarity transform (scale, turn, shift)
# that lines up the silhouettes AND the black ink lines; it reports how far the new ink sits from
# the old ink (mean / 90th percentile, in icon px), the number that decides if a rig still cuts clean.
import os, sys, shutil, json
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage, optimize

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from redraw import ALL, OUT
REPO = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(REPO, 'art', 'icons-src')
GEOM = os.path.join(SRC, 'geom')


def arr(im):
    return np.asarray(im.convert('RGBA')).astype(np.float32) / 255


def ink(a):
    return ((a[..., :3].max(-1) < .3) & (a[..., 3] > .5)).astype(np.float32)


def warp(img_arr, p, out_shape, order=1):
    """img (h, w[, c]) in new-image px -> old frame. p = (s, th, tx, ty): x_old = s R(th) x_new + t."""
    s, th, tx, ty = p
    c, sn = np.cos(th), np.sin(th)
    # inverse map for affine_transform works in (row, col) = (y, x)
    Rinv = np.array([[c, sn], [-sn, c]]) / s          # R(-th)/s in (x, y)
    M = np.array([[Rinv[1, 1], Rinv[1, 0]], [Rinv[0, 1], Rinv[0, 0]]])   # to (y, x)
    off = -M @ np.array([ty, tx])
    if img_arr.ndim == 2:
        return ndimage.affine_transform(img_arr, M, offset=off, output_shape=out_shape, order=order)
    return np.stack([ndimage.affine_transform(img_arr[..., k], M, offset=off, output_shape=out_shape, order=order)
                     for k in range(img_arr.shape[-1])], -1)


def fit(old, new):
    """Best (s, th, tx, ty) at quarter scale, refined by Nelder-Mead on silhouette IoU + ink overlap."""
    q = 4
    oa = old[::q, ::q, 3]; oi = ndimage.gaussian_filter(ink(old)[::q, ::q], 1.2)
    na = new[::q, ::q, 3]; ni = ndimage.gaussian_filter(ink(new)[::q, ::q], 1.2)
    ys, xs = np.nonzero(oa > .5); yn, xn = np.nonzero(na > .5)
    s0 = np.sqrt(len(xs) / max(len(xn), 1))
    p0 = np.array([s0, 0.0, xs.mean() - s0 * xn.mean(), ys.mean() - s0 * yn.mean()])

    def cost(p):
        wa = warp(na, p, oa.shape); wi = warp(ni, p, oa.shape)
        iou = np.minimum(oa, wa).sum() / max(np.maximum(oa, wa).sum(), 1e-6)
        ov = (oi * wi).sum() / max(np.sqrt((oi * oi).sum() * (wi * wi).sum()), 1e-6)
        return -(iou + ov)
    r = optimize.minimize(cost, p0, method='Nelder-Mead',
                          options=dict(xatol=1e-3, fatol=1e-5, maxiter=600, initial_simplex=[
                              p0, p0 + [.03, 0, 0, 0], p0 + [0, .02, 0, 0], p0 + [0, 0, 4, 0], p0 + [0, 0, 0, 4]]))
    s, th, tx, ty = r.x
    return (s, th, tx * q, ty * q), -r.fun


def install(icon, tag, dry=False):
    geom = os.path.join(GEOM, icon + '.png')
    old_path = geom if os.path.exists(geom) else os.path.join(SRC, icon + '.png')
    old_im = Image.open(old_path).convert('RGBA'); old = arr(old_im)
    new_im = Image.open(os.path.join(OUT, tag, icon + '.png')).convert('RGBA'); new = arr(new_im)
    p, score = fit(old, new)
    H, W = old.shape[:2]
    # premultiplied, cubic, so the edges never pick up dark fringes
    pm = new.copy(); pm[..., :3] *= pm[..., 3:4]
    w = np.clip(warp(pm, p, (H, W), order=3), 0, 1)
    a = w[..., 3:4]
    rgb = np.where(a > 1e-3, w[..., :3] / np.maximum(a, 1e-3), 0)
    # the model leaves a faint alpha haze over its whole canvas (thousands of 1-9/255 pixels): keep
    # the sticker's own antialiased edge (within 3 px of its solid body), drop the rest, or every
    # rig part's box spreads to the canvas edge
    body = ndimage.binary_dilation(a[..., 0] > .12, iterations=3)
    lab, n = ndimage.label(body)
    if n > 1:                                       # specks the haze left in clumps, well away from the sticker
        sizes = ndimage.sum(np.ones_like(a[..., 0]), lab, range(1, n + 1))
        body = np.isin(lab, 1 + np.nonzero(sizes >= max(400, sizes.max() * .002))[0])
    a = np.where(body[..., None] & (a > .03), a, 0)
    out = np.concatenate([np.clip(rgb, 0, 1), a], -1)
    # how well it lines up: silhouette IoU, and ink-to-ink distance both ways
    A, B = old[..., 3] > .5, out[..., 3] > .5
    iou = (A & B).sum() / max((A | B).sum(), 1)
    oi, wi = ink(old) > .5, ink(out) > .5
    d_old = ndimage.distance_transform_edt(~oi); d_new = ndimage.distance_transform_edt(~wi)
    a2b = d_old[wi]; b2a = d_new[oi]
    stats = dict(icon=icon, scale=round(p[0], 4), turn_deg=round(np.degrees(p[1]), 2), shift=(round(p[2], 1), round(p[3], 1)),
                 iou=round(float(iou), 3), ink_new_to_old=(round(float(a2b.mean()), 2), round(float(np.percentile(a2b, 90)), 1)),
                 ink_old_to_new=(round(float(b2a.mean()), 2), round(float(np.percentile(b2a, 90)), 1)))
    # overlay for the eye: old ink red, new ink cyan, where both agree white
    ov = np.full((H, W, 3), 40, np.uint8)
    ov[oi] = (230, 40, 40); ov[wi] = (40, 220, 230); ov[oi & wi] = (255, 255, 255)
    os.makedirs(os.path.join(OUT, tag, 'align'), exist_ok=True)
    Image.fromarray(ov).save(os.path.join(OUT, tag, 'align', icon + '.png'))
    if not dry:
        os.makedirs(GEOM, exist_ok=True)
        if not os.path.exists(geom):
            shutil.copy2(os.path.join(SRC, icon + '.png'), geom)        # the drawing the rig was measured on
        Image.fromarray((out * 255).round().astype(np.uint8), 'RGBA').save(os.path.join(SRC, icon + '.png'))
    return stats


if __name__ == '__main__':
    tag = sys.argv[1]
    icons = ALL if sys.argv[2] == 'all' else sys.argv[2].split(',')
    dry = '--dry' in sys.argv
    res = [install(i, tag, dry) for i in icons]
    for s in res:
        print(json.dumps(s))
    json.dump(res, open(os.path.join(OUT, tag, 'align', 'stats.json'), 'w'), indent=1)
