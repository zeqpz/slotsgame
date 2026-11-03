# ES - the extreme scatter ("XFS" in purple dripping graffiti): what Blender's cut changes from the rig recipe
# (tools/icon_rigs/recipes/ES.py). The recipe cut each letter's drips as one run below a straight line; on the new art
# the drips leave their letters at different heights. Here every drip is its own bendy piece, so each swings and
# oozes on its own spring:
#   X   x_a off the left leg; x_b and x_c, the two fingers the right leg splits into
#   F   f_a and f_b, the two fingers under the stem
#   S   s_a (with the blob it curls into), s_b the thin one, s_c, and s_d the short one at the bottom-right
# Each drip is found by its paint (the colour, not the black: two drips whose outlines touch stay apart) below its
# junction (where it leaves its letter); it owns the pixels there nearer its own paint than its letter's or another
# drip's - so every black outline and white border goes with the paint it rings - and 4 px past that line, where
# its neighbour also carries the art (no seam at rest). It runs 3 px above the junction and 12 px up under its letter
# across its own neck (the "tuck"), so it can swing and stretch from its root without opening a gap.
# X is a sticker of its own; F and S are one: the F's middle bar runs into the S, and the white and black between
# them are shared. That join is the "weld": one piece drawn over both, its mesh weighted F-to-S across it
# (anim_ES.py), so when the letters bounce in turn the paint between them stretches like wet paint instead of
# tearing. Nothing a part uncovers needs painting (behind it all is air), so no clean plate: the pieces' pixels come
# from art/blender/plates/ES_art.png, the art itself (a copy of art/icons-src/ES.png, made here when it is missing) -
# FILLS can only take pixels from a plate. Coordinates are the art's own px (840x604, the recipe's 2x).
import json, os, shutil, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
sys.path.insert(0, os.path.join(_ROOT, "tools", "icon_rigs"))
sys.path.insert(0, os.path.join(_ROOT, "tools", "icon_rigs", "recipes"))
import rigkit                                      # noqa: E402
from build import load_recipe                      # noqa: E402

SID = "ES"
_ART = os.path.join(_ROOT, "art", "icons-src", SID + ".png")
_COPY = os.path.join(_ROOT, "art", "blender", "plates", SID + "_art.png")
if not os.path.exists(_COPY):
    os.makedirs(os.path.dirname(_COPY), exist_ok=True)
    shutil.copyfile(_ART, _COPY)

_rig = rigkit.Rig(load_recipe(os.path.join(_ROOT, "tools", "icon_rigs", "recipes", SID + ".py")))
_rig.cut()
W, H = _rig.cv.W, _rig.cv.H


def _area(names):
    a = np.zeros((H, W), np.float32)
    for n in names:
        p = _rig.parts[n]
        x0, y0, x1, y1 = p["box"]
        a[y0:y1, x0:x1] = np.maximum(a[y0:y1, x0:x1], np.asarray(p["img"])[..., 3] / 255)
    return a > 0


_src = np.asarray(_rig.src).astype(np.float32) / 255
_rgb, _al = _src[..., :3], _src[..., 3]
_white = (_rgb.min(-1) > .80) & (_rgb.max(-1) - _rgb.min(-1) < .12)
_ink = (_al > .5) & (_rgb.max(-1) < .3)
# paint and ink, not the sticker border (nor the grey fringe at the sticker's outer edge: more than 6 px in)
CORE = (_al > .5) & ~_white & (ndimage.distance_transform_edt(_al > .5) > 6)
_mx = _rgb.max(-1)
PAINT = CORE & (_mx > .1) & ((_mx - _rgb.min(-1)) / np.maximum(_mx, 1e-3) > .35)   # the colour (its dark shade too), no ink
_alpha = _al > 0
yy, xx = np.mgrid[0:H, 0:W]


def _out(region):
    """A region carried 4 px out into the transparent air round it: a fill is feathered at its edge, so this keeps
    the feather off the art's own soft outer edge."""
    return region | (ndimage.binary_dilation(region, iterations=4) & ~_alpha)


def _harmonic(Z, one, zero):
    """A smooth field over Z (bool HxW): 1 where Z touches `one`, 0 where it touches `zero`, and between them the
    solution of Laplace's equation - the smoothest blend there is, no kinks, no jumps; where Z meets the air it is
    free. Outside Z: 1 on `one`, 0 on `zero`, elsewhere the nearest value."""
    from scipy.sparse import csr_matrix
    from scipy.sparse.linalg import spsolve
    n = int(Z.sum())
    idx = -np.ones(Z.shape, np.int64)
    idx[Z] = np.arange(n)
    ys, xs = np.nonzero(Z)
    diag, rhs = np.full(n, 1e-6), np.full(n, .5e-6)      # (a piece touching neither letter settles at one half)
    rows, cols = [], []
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        qy, qx = ys + dy, xs + dx
        ok = (qy >= 0) & (qy < Z.shape[0]) & (qx >= 0) & (qx < Z.shape[1])
        qy, qx = np.clip(qy, 0, Z.shape[0] - 1), np.clip(qx, 0, Z.shape[1] - 1)
        inz = ok & Z[qy, qx]
        is1 = ok & ~inz & one[qy, qx]
        is0 = ok & ~inz & ~one[qy, qx] & zero[qy, qx]
        diag += inz + is1 + is0
        rhs += is1
        rows.append(np.nonzero(inz)[0])
        cols.append(idx[qy[inz], qx[inz]])
    r = np.concatenate(rows + [np.arange(n)])
    c = np.concatenate(cols + [np.arange(n)])
    v = np.concatenate([-np.ones(len(q)) for q in rows] + [diag])
    u = spsolve(csr_matrix((v, (r, c)), shape=(n, n)), rhs)
    out = np.full(Z.shape, np.nan)
    out[zero] = 0.0
    out[one] = 1.0
    out[Z] = np.clip(u, 0, 1)
    _, (iy, ix) = ndimage.distance_transform_edt(np.isnan(out), return_indices=True)
    return out[iy, ix]


# ------------------------------------------------------------------ whose is what
_ax = _area(["letter_x", "drip_x"])
_af = _area(["letter_f", "drip_f"])
_as = _area(["letter_s", "drip_s"])
_col = (_al > .5) & ~_white & ~_ink                 # the purple paint
_lab, _ = ndimage.label(_col)
_FS = _lab == _lab[300, 440]                        # F and S are one body of paint (the F's middle bar runs into the S)
# where the paint crosses from F's side of the recipe's seam to S's: the bridge, and 26 px round it
_cross = _FS & ndimage.binary_dilation(_af, iterations=2) & ndimage.binary_dilation(_as, iterations=2)
BRIDGE = _FS & (ndimage.distance_transform_edt(~_cross) <= 30)
F_PAINT = _FS & _af & ~BRIDGE
S_PAINT = _FS & _as & ~BRIDGE
_dF = ndimage.distance_transform_edt(~F_PAINT)
_dS = ndimage.distance_transform_edt(~S_PAINT)
# the join (JBOX: from the top down to where the two stickers part): everything there is the weld's, and how much
# of each pixel goes with F (the rest with S) is a smooth field over the box - all F where the box meets F, all S
# where it meets S, Laplace's equation between - so the paint bends as the letters move apart and never tears
JBOX = (xx > 478) & (xx < 612) & (yy < 420)
WELD_F = _harmonic(JBOX & _alpha, _af & ~JBOX & _alpha, _as & ~JBOX & _alpha)
AREA = {"x": _ax,
        "f": np.where(JBOX, _alpha & (WELD_F >= .5) & ~_ax, _af),
        "s": np.where(JBOX, _alpha & (WELD_F < .5) & ~_ax, _as)}

# ------------------------------------------------------------------ the drips
# name: (letter, recipe run it is split from, divider window [x0, x1), junction y)
DRIPS = {
    "x_a": ("x", "drip_x", (108, 188), 440),
    "x_b": ("x", "drip_x", (225, 270), 428),
    "x_c": ("x", "drip_x", (270, 332), 428),
    "f_a": ("f", "drip_f", (408, 447), 432),
    "f_b": ("f", "drip_f", (447, 494), 432),
    "s_a": ("s", "drip_s", (565, 621), 452),
    "s_b": ("s", "drip_s", (621, 638), 478),
    "s_c": ("s", "drip_s", (638, 676), 462),
    "s_d": ("s", "drip_s", (694, 746), 418),
}
SKIRT = 16
TUCK, OVERLAP, LIP, ROOT = 12, 4, 3, 22
REGION, CHAIN, BELOW = {}, {}, {}
for L in ("x", "f", "s"):
    names = [n for n, d in DRIPS.items() if d[0] == L]
    paints, info = {}, {}
    for name in names:
        _, run, (x0, x1), yj = DRIPS[name]
        win = AREA[L] & (yy >= yj) & (xx >= x0) & (xx < x1)
        # the drip's paint (colour only: two drips whose black outlines touch stay apart): the piece of paint below
        # the junction that hangs from the neck (the widest run of paint on the junction's row) ...
        row = PAINT[yj] & (np.arange(W) >= x0) & (np.arange(W) < x1)
        lab1, n1 = ndimage.label(row)
        k = 1 + int(np.argmax(ndimage.sum(row, lab1, range(1, n1 + 1))))
        neck = np.nonzero(lab1 == k)[0]
        lab, _ = ndimage.label(PAINT & win)
        comp = lab == lab[yj, int(neck.mean())]
        # ... and the bits of it a highlight cuts off (within 8 px, twice over)
        for _k in range(2):
            comp |= PAINT & win & ndimage.binary_dilation(comp, iterations=8)
        paints[name] = comp
        info[name] = (neck, yj)
    # the letter's own paint: not a drip's, nor any paint just beside a drip below its junction
    zones = [ndimage.binary_dilation(paints[n], iterations=14) & (yy >= info[n][1] + 2) for n in names]
    base = PAINT & AREA[L] & ~np.any([paints[n] for n in names], 0) & ~np.any(zones, 0)
    dist = {n: ndimage.distance_transform_edt(~paints[n]) for n in names}
    dbase = ndimage.distance_transform_edt(~base)
    for name in names:
        neck, yj = info[name]
        comp = paints[name]
        others = np.min([dbase] + [dist[n] for n in names if n != name], 0)
        own = AREA[L] & _alpha & (dist[name] <= others + OVERLAP) & (yy >= yj - LIP)
        # where two fingers touch (their black outlines run together), each carries the shared outline SKIRT px on
        # under its neighbour, so when they swing apart the black stays whole instead of opening a slit
        sibs = [dist[n] for n in names if n != name]
        # near its root the drip runs 12 px on under its letter's edge (it is drawn behind the letter): a big squash of
        # the word stretches the letter but not the drip, and the letter's black must not pull off the drip's side
        sib_ = np.min(sibs, 0) if sibs else np.full((H, W), np.inf)
        own |= AREA[L] & _alpha & (dist[name] <= dbase + 12) & (dist[name] <= sib_ + OVERLAP) & (yy >= yj) & (yy < yj + 40)
        if sibs:
            sib = np.min(sibs, 0)
            own |= AREA[L] & (_al > .5) & (dist[name] <= sib + SKIRT) & (sib < dbase) & (yy >= yj + 6)
        cols = (xx >= neck.min() - 10) & (xx <= neck.max() + 10)       # (and the black beside it)
        tuck = CORE & cols & (yy >= yj - TUCK) & (yy < yj) & ndimage.binary_erosion(CORE, iterations=2)
        REGION[name] = _out(own | tuck)
        nearest = AREA[L] & _alpha & (dist[name] <= others) & (yy >= yj + 2)      # (a tie: both drips carry it)
        BELOW[name] = nearest & ~((yy < yj + ROOT) & (dbase <= dist[name] + 4))
        # the chain down the middle of the drip's paint: root on the junction, 2 or 3 bones to the drop at its tip
        ys = np.nonzero(comp.any(1))[0]
        tip = int(ys.max())
        nb = 3 if tip - yj > 95 else 2
        pts = []
        for i in range(nb + 1):
            y = yj + (tip - 3 - yj) * i / nb
            xs = np.nonzero(comp[int(round(y))])[0]
            pts.append((round(float(xs.mean()), 1) if len(xs) else round(float(neck.mean()), 1), round(float(y), 1)))
        pts[0] = (round(float(neck.mean()), 1), float(yj))
        CHAIN[name] = pts

# ------------------------------------------------------------------ the weld: the join between F and S
# everything round the join that moves partly with each letter; it ends only where its pixels go wholly with one
# letter, so where it meets the letters both move alike and nothing tears or is left standing. It runs 4 px on
# past that edge (both carry the art there); the letters give up its inside.
WELD_CORE = JBOX & _alpha
WELD = ndimage.binary_dilation(WELD_CORE, iterations=4) & _alpha & ~_ax
# what the letters give up: the whole box but a 1 px rim where it meets them (both carry the art there); nothing of
# its edge to the air stays on a letter (a frozen strip of fringe would hang in the air when the weld moves)
_WELD_TAKEN = ndimage.binary_erosion(WELD_CORE | ~_alpha, iterations=1) & WELD_CORE
_ys, _xs = np.nonzero(WELD)
_box = [int(_xs.min()) - 8, int(_ys.min()) - 8, int(_xs.max()) + 9, int(_ys.max()) + 9]
_step = 4
_grid = [[round(float(WELD_F[min(H - 1, max(0, y)), min(W - 1, max(0, x))]), 3) for x in range(_box[0], _box[2] + 1, _step)]
         for y in range(_box[1], _box[3] + 1, _step)]
_pdir = os.path.join(_ROOT, "art", "blender", "parts", SID)
os.makedirs(_pdir, exist_ok=True)
json.dump({"box": _box, "step": _step, "f": _grid}, open(os.path.join(_pdir, "weld_weights.json"), "w"))

# ------------------------------------------------------------------ the cut
# every drip piece (and the weld) is split off a recipe drip run, so it rides that run's letter; it starts empty
# and takes exactly its region's pixels from the art
_NOWHERE = [(0, H + 50), (W, H + 50)]
SPLIT = {}
for name, (L, run, _, _) in DRIPS.items():
    SPLIT.setdefault(run, []).append({"name": name, "side": "below", "line": _NOWHERE, "chain": CHAIN[name]})
SPLIT["drip_s"].append({"name": "weld", "side": "below", "line": _NOWHERE})
FILLS = [{"part": name, "region": REGION[name], "plate": "art"} for name in DRIPS]
FILLS.append({"part": "weld", "region": _out(WELD), "plate": "art"})
CLEAR = []
for L in ("x", "f", "s"):
    drips = np.zeros((H, W), bool)
    for name, (LL, _, _, _) in DRIPS.items():
        if LL == L:
            drips |= BELOW[name]
    keep = AREA[L] & _alpha & ~drips & ~_WELD_TAKEN
    FILLS.append({"part": "letter_" + L, "region": _out(keep), "plate": "art"})
    # (carried out into the air: the clear is feathered, and its fall-off there would leave a ghost of the drips'
    # outer edge on the letter - the recipe's letter part holds the new art's pixels just outside the old drawing)
    CLEAR.append({"part": "letter_" + L, "region": _out(drips | _WELD_TAKEN)})
# the weld's mesh bends: a grid weighted between two bones (anim_ES.py reweights it, F to S across the join)
ANCHOR = {"weld": {"bone": "letter_f", "y0": 300, "y1": 20}}


# ------------------------------------------------------------------ the glow's path, per letter
# X and FS are two stickers: the glow runs round each one, 9 px outside its edge (art/blender/parts/ES/halo.json),
# every point owned by the letter whose paint is nearest, so each stretch of it rides its own letter in anim_ES.py
def _trace(mask):
    """Moore-neighbour trace of a blob's outer boundary (as tools/blender/outline.py does), simplified."""
    pad = np.zeros((mask.shape[0] + 2, mask.shape[1] + 2), bool)
    pad[1:-1, 1:-1] = mask
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
    return [(x - 1.0, y - 1.0) for y, x in path[::3]]


_stickers, _n = ndimage.label(_al > .5)
_X_PAINT = _col & _ax
_d = np.stack([ndimage.distance_transform_edt(~m) for m in (_X_PAINT, _FS & _af, _FS & _as)])
_loops = []
for _i in range(1, _n + 1):
    _m = _stickers == _i
    if _m.sum() < 5000:
        continue
    _g = ndimage.binary_dilation(_m, iterations=9)
    _g = ndimage.binary_closing(_g, iterations=4)
    _pts = _trace(_g)
    _mine = [k for k, m in enumerate((_X_PAINT, _FS & _af, _FS & _as)) if (m & _m).any()]      # the letters on this sticker
    _own = ["xfs"[_mine[int(np.argmin([_d[k, min(H - 1, int(y)), min(W - 1, int(x))] for k in _mine]))]] for x, y in _pts]
    _loops.append({"pts": [[round(x, 1), round(y, 1)] for x, y in _pts], "owner": _own})
json.dump({"loops": _loops}, open(os.path.join(_pdir, "halo.json"), "w"))
