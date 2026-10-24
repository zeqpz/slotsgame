"""Pull the shapes out of a grungy spray-paint lettering piece (art/ui-src/bonus_btn_text.png,
art/icons-src/BS.png / ES.png): the letter bodies, the drips hanging from them and the loose
droplets, as clean masks at K times the source size. cartoon.py repaints them in the icon style.

The pieces are built the same way: paint-coloured letter bodies (with black cracks), a black
outline, a paint-coloured outer rim, drips in the paint colour, and loose spatter.
"""
import numpy as np
import cv2
from PIL import Image


def load(path, K):
    im = Image.open(path).convert("RGBA")
    big = im.resize((im.width * K, im.height * K), Image.LANCZOS)
    return np.asarray(big).astype(np.float32) / 255.0


def disc(r):
    r = max(1, int(round(r)))
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def keep_big(mask, min_area):
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    out = np.zeros_like(mask, bool)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] >= min_area:
            out |= lab == i
    return out


def fill_holes(mask, max_area):
    """Fill enclosed holes smaller than max_area (cracks, specks), keep the real counters."""
    inv = (~mask).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(inv, 4)
    out = mask.copy()
    h, w = mask.shape
    for i in range(1, n):
        x, y, bw, bh, a = st[i]
        touches = x == 0 or y == 0 or x + bw == w or y + bh == h
        if not touches and a <= max_area:
            out |= lab == i
    return out


def smooth(mask, sigma):
    """A mask with its edge smoothed: blur, re-threshold (corners round off a little)."""
    f = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigma)
    return f > .5


def segment(path, K=4, ink_lum=.26, scale_px=1.0):
    """-> dict of bool masks at K x the source: body, drips, dots, piece (everything)."""
    a = load(path, K)
    rgb, al = a[..., :3], a[..., 3]
    lum = rgb @ np.array([.3, .59, .11])
    sat = rgb.max(-1) - rgb.min(-1)
    vis = al > .5
    ink = vis & (lum < ink_lum)
    paint = vis & ~ink & (sat > .18)
    u = K * scale_px   # one source pixel at the working size
    # the outer rim of paint is whatever paint the outside reaches without crossing ink: flood
    # from the edge of the canvas through non-ink pixels
    free = (~ink).astype(np.uint8)
    n, lab = cv2.connectedComponents(free, connectivity=4)
    outside = np.zeros_like(vis)
    border_labels = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    for l in border_labels:
        outside |= lab == l
    inside = vis & ~outside & ~ink          # enclosed paint: the letter bodies (cut up by cracks)
    body = inside | (ink & ~outside)        # bodies with their cracks and outline
    # the bodies alone: take the enclosed paint, close the cracks, fill small holes, and pull
    # back to the inner edge of the black outline
    core = cv2.morphologyEx(inside.astype(np.uint8), cv2.MORPH_CLOSE, disc(2.5 * u)).astype(bool)
    core = fill_holes(core, (12 * u) ** 2)
    core = keep_big(core, (14 * u) ** 2)
    core = smooth(core, 1.2 * u)
    # the drips: everything visible below a body that isn't the body or its outline ring,
    # long and thin, hanging down
    ring = cv2.dilate(core.astype(np.uint8), disc(7 * u)).astype(bool)
    rest = vis & ~ring
    rest = cv2.morphologyEx(rest.astype(np.uint8), cv2.MORPH_OPEN, disc(1.2 * u)).astype(bool)
    n, lab, st, cen = cv2.connectedComponentsWithStats(rest.astype(np.uint8), 8)
    drips = np.zeros_like(vis); dots = np.zeros_like(vis)
    for i in range(1, n):
        x, y, bw, bh, area = st[i]
        if area < (2.0 * u) ** 2:
            continue
        comp = lab == i
        if bh > 2.2 * bw and bh > 10 * u:          # tall and thin: a drip
            drips |= comp
        elif area < (14 * u) ** 2 and bh < 3 * bw:  # small and round: a droplet
            dots |= comp
    return {"core": core, "drips": drips, "dots": dots, "vis": vis, "u": u, "K": K,
            "rgb": rgb, "alpha": al}
