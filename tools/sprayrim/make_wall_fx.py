"""The live wall: the SMUKIEZ tag's neon outline and its light on the bricks, and the wet paint that oozes
out of the holes in the wall and out of the tag's letters.

  python tools/sprayrim/make_wall_fx.py            # tag glow / sheen / spill, the paint pools and drip data
  python tools/sprayrim/make_wall_fx.py --bonus    # ... and the BONUS button's neon (bonus_glow.webp)

Reads frontend/assets/bonus_wall.webp (the wall, 3840x2160) and frontend/assets/wall_tag.webp (the wordmark
cut-out, 3303x1674). Both were redrawn 2026-10-27 with openai/gpt-image-2.5-sunburst (art/STYLE.md):
art/wall-src/bonus_wall_master.png is the wall's 16:9 composition, redrawn again tile by tile (3x3
overlapping tiles, each aligned back onto the master and given its tone) into bonus_wall_3840.jpg;
wall_tag_gen.png is the tag, fitted onto the old tag's silhouette so it keeps its size and place.
art/ui-src/bonus_wall.jpg and wall_tag.webp are the same art at the old source sizes (the originals
are kept beside them as *_v1). Writes frontend/assets/wallfx/:
  tag_glow.webp     the tag's neon-green outline as a neon tube (the tag's box padded by GLOW_PAD, half size)
  tube_<k>.webp     the same glow cut into NSEG stretches along the outline, each cropped to where it shows
                    (wallfx.js lays them in #tagglow instead of the whole tube, so one can drop out)
  tag_sheen.webp    the same tube brightened (brightness 1.3, saturate .8) for the sheen that sweeps along it
  tag_spill.webp    the tube's light thrown on the wall round it (the box padded by SPILL_PAD) - shown only
                    where wallfx.js cannot light the wall itself (no WebGL)
  wall_height.webp  the wall's relief, 1600x900 grey: bricks raised, mortar, cracks and pits sunk, the wet
                    paint domed (wallfx.js bakes the tube's light on it, #walllight)
  wall_wet.png      where the wet paint is on the wall (800x450): it shines in the tube's light
  bonus_glow.webp   (--bonus) the BONUS button's outline as a neon-lime tube (the plate padded by BTN_PAD)
  blob_<i>.webp     each pool of paint in the wall's holes, cut out with its dark rim (wallfx.js swells it
                    as paint gathers for a drip)
  wallfx.json       {art: [w, h], floor (the pavement line, fraction of the height),
                     blobs: [{x, y, w, h (the sprite's box, fractions of the art), colour,
                              paint: {base, deep, hi, line} (RGB: the paint's body, its shadow side, its
                              highlight, the dark rim round it), tips: [[x, y, w], ...] (a drip's end:
                              the bottom of its round drop and the drip's width, fractions of the art)}],
                     tag: {size: [w, h], tips: [{x, y, w (fractions of the tag's box), paint}]},
                     tube: {n, segs: [{box: [x, y, w, h] (fractions of the tag's box), share (of the tube)}],
                            pts: [[x, y, weight, stretch], ...] (the tube as NPTS points, fractions of the
                            tag's box; the weights add up to 1)},
                     relief: {size: [w, h]}, spillPad, glowPad}
The drips themselves are drawn live by frontend/wallfx.js in those colours.
"""
import json, os, sys
import numpy as np
import cv2
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
A = os.environ.get("WALLFX_ASSETS") or os.path.join(ROOT, "frontend", "assets")   # WALLFX_ASSETS: work on a copy
OUT = os.path.join(A, "wallfx")
SPILL_PAD = .22
GLOW_PAD = .06
BTN_PAD = .14
NSEG = 7          # the tube's stretches, each its own glow, so one can drop out like a tired neon tube
NPTS = 64         # the tube as this many weighted points, for the light it throws (wallfx.js)
RELIEF = (1600, 900)
LIME, HOT = np.array([110, 255, 70], np.float32), np.array([225, 255, 200], np.float32)   # the tube's neon and its white-hot core


def save(arr, name, q=88):
    Image.fromarray(np.asarray(arr).clip(0, 255).astype(np.uint8), "RGBA").save(os.path.join(OUT, name), "WEBP", quality=q, alpha_quality=100, method=6)


def hsv(rgb8):
    return cv2.cvtColor(rgb8.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.int16)


# ------------------------------------------------------------------ the tag's neon
def tube_mask(im):
    """the tag's outer outline: the saturated neon green (hue ~114 deg) round the whole piece. The lime of
    the letters (hue ~72 deg) and the pale highlights are not it."""
    rgb, al = im[..., :3], im[..., 3]
    h, s, v = np.moveaxis(hsv(rgb), -1, 0)
    return (al > 128) & (h >= 48) & (h <= 68) & (s > 110) & (v > 110)


def glow_of(m):
    """the neon glow of a tube mask m (0..1, padded so the halo fits): its colour (the line itself lit
    near white, lime round it) and alpha (0..1) - a tight bright halo and a wide soft one"""
    g1 = cv2.GaussianBlur(m, (0, 0), 3); g2 = cv2.GaussianBlur(m, (0, 0), 11); g3 = cv2.GaussianBlur(m, (0, 0), 26)
    a = np.clip(m * .9 + g1 * 1.1 + g2 * .9 + g3 * .7, 0, 1)
    t = np.clip(m * 1.2 + g1 * .5, 0, 1)[..., None]
    return LIME[None, None] * (1 - t) + HOT[None, None] * t, a


def segments(green):
    """The tube cut into NSEG stretches along its outer outline (equal lengths, from its left end); every
    pixel of it, the inner loops between the letters too, goes with the stretch nearest it. Each stretch's
    glow is saved cropped to where it shows (tube_<k>.webp). Returns their boxes and shares, and the tube
    as NPTS weighted points (k-means of its pixels) with the stretch each belongs to."""
    H, W = green.shape
    t8 = cv2.morphologyEx(green.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    cnts, _ = cv2.findContours(t8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cnts, key=lambda q: cv2.arcLength(q, True))[:, 0, :]
    c = np.roll(c, -int(np.argmin(c[:, 0])), axis=0)
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(c, axis=0).T))]
    sid = np.minimum((d / d[-1] * NSEG).astype(int), NSEG - 1)
    # the stretch of the nearest outline point, for every pixel: a distance transform labelled by the
    # outline's own pixels (numbered in scan order)
    sid_img = np.zeros((H, W), np.int32); sid_img[c[:, 1], c[:, 0]] = sid
    zero = np.ones((H, W), np.uint8); zero[c[:, 1], c[:, 0]] = 0
    _, labels = cv2.distanceTransformWithLabels(zero, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    zy, zx = np.nonzero(zero == 0)
    lab2sid = np.zeros(len(zy) + 1, np.int32); lab2sid[1:] = sid_img[zy, zx]
    seg = lab2sid[labels]
    k = .5
    hw, hh = int(W * k), int(H * k)
    py, px = int(hh * GLOW_PAD), int(hw * GLOW_PAD)
    out = []
    for s in range(NSEG):
        m = cv2.resize((green & (seg == s)).astype(np.float32), (hw, hh), interpolation=cv2.INTER_AREA)
        m = np.pad(m, ((py, py), (px, px)))
        col, a = glow_of(m)
        ys, xs = np.nonzero(a > 1.5 / 255)
        x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
        save(np.dstack([col[y0:y1, x0:x1], a[y0:y1, x0:x1] * 255]), f"tube_{s}.webp")
        out.append({"box": [round((x0 - px) / hw, 5), round((y0 - py) / hh, 5), round((x1 - x0) / hw, 5), round((y1 - y0) / hh, 5)],
                    "share": round(float((green & (seg == s)).sum() / green.sum()), 4)})
    # the tube as weighted points: each stretch clustered on its own, its share of the points, so a
    # stretch that goes dark takes its own share of the light with it
    sub = (green & True)[::4, ::4]
    sseg = seg[::4, ::4]
    total = float(sub.sum())
    cv2.setRNGSeed(7)
    tp = []
    for s in range(NSEG):
        ys, xs = np.nonzero(sub & (sseg == s))
        if not len(xs):
            continue
        pts = np.float32(np.c_[xs * 4 + 2, ys * 4 + 2])
        n = int(max(3, min(len(pts), round(NPTS * len(pts) / total))))
        _, lab, cen = cv2.kmeans(pts, n, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 60, .25), 3, cv2.KMEANS_PP_CENTERS)
        cnt = np.bincount(lab[:, 0], minlength=n)
        for j in range(n):
            if cnt[j]:
                tp.append([round(float(cen[j, 0] / W), 5), round(float(cen[j, 1] / H), 5), round(float(cnt[j] / total), 5), s])
    return {"n": NSEG, "segs": out, "pts": tp}


def relief():
    """The wall's relief for the tube's light (wallfx.js bakes it, #walllight): wall_height.webp, the
    height of every point of the wall - bricks raised, mortar, cracks and pits sunk (the local brightness
    of the art, its faces flattened), the wet paint in the holes domed - and wall_wet.png, where the wet
    paint is (it shines)."""
    art = np.asarray(Image.open(os.path.join(A, "bonus_wall.webp")).convert("RGB")).astype(np.float32) / 255
    W, H = RELIEF
    a = cv2.resize(art, (W, H), interpolation=cv2.INTER_AREA)
    lum = a @ np.array([.3, .59, .11], np.float32)
    hp = lum - cv2.GaussianBlur(lum, (0, 0), 14 * W / 1920)
    lo, hi = np.percentile(hp, [3, 97])
    hp = np.clip((hp - lo) / (hi - lo), 0, 1).astype(np.float32)
    face = cv2.morphologyEx(hp, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    face = cv2.medianBlur((face * 255).astype(np.uint8), 3).astype(np.float32) / 255
    hgt = cv2.GaussianBlur(face, (0, 0), 1.0)
    hs = hsv(a * 255)
    wet = ((hs[..., 1] > 110) & (hs[..., 2] > 110)).astype(np.uint8)
    wet = cv2.morphologyEx(wet, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    wet = cv2.morphologyEx(wet, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    dome = np.sqrt(np.clip(cv2.distanceTransform(wet, cv2.DIST_L2, 5) / 5.0, 0, 1)).astype(np.float32)
    hgt = np.where(wet > 0, .55 + .45 * cv2.GaussianBlur(dome, (0, 0), 1.0), hgt)
    Image.fromarray((np.clip(hgt, 0, 1) * 255 + .5).astype(np.uint8), "L").convert("RGB").save(
        os.path.join(OUT, "wall_height.webp"), "WEBP", quality=72, method=6)
    w2 = cv2.resize(wet.astype(np.float32), (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    Image.fromarray((w2 * 255 + .5).astype(np.uint8), "L").save(os.path.join(OUT, "wall_wet.png"), optimize=True)
    return {"size": [W, H]}


def tag():
    im = np.asarray(Image.open(os.path.join(A, "wall_tag.webp")).convert("RGBA"))
    H, W = im.shape[:2]
    green = tube_mask(im)
    k = .5
    m = cv2.resize(green.astype(np.float32), (int(W * k), int(H * k)), interpolation=cv2.INTER_AREA)
    # padded, so the halo fades out before the picture ends (cut at the tag's own box, it left a
    # straight edge of light on the wall)
    m = np.pad(m, ((int(m.shape[0] * GLOW_PAD), int(m.shape[0] * GLOW_PAD)), (int(m.shape[1] * GLOW_PAD), int(m.shape[1] * GLOW_PAD))))
    col, a = glow_of(m)
    glow = np.dstack([col, a * 255])
    save(glow, "tag_glow.webp")
    # the sheen's light: the same tube, brighter and a little paler (CSS brightness(1.3) saturate(.8))
    c = np.clip(col * 1.3, 0, 255)
    kk = .8
    M = np.array([[.213 + .787 * kk, .715 - .715 * kk, .072 - .072 * kk],
                  [.213 - .213 * kk, .715 + .285 * kk, .072 - .072 * kk],
                  [.213 - .213 * kk, .715 - .715 * kk, .072 + .928 * kk]], np.float32)
    save(np.dstack([np.clip(c @ M.T, 0, 255), a * 255]), "tag_sheen.webp")
    # the spill: the outline's light thrown wide over the wall
    k2 = .2
    ms = cv2.resize(green.astype(np.float32), (int(W * k2), int(H * k2)), interpolation=cv2.INTER_AREA)
    ph, pw = int(ms.shape[0] * SPILL_PAD), int(ms.shape[1] * SPILL_PAD)
    mp = np.pad(ms, ((ph, ph), (pw, pw)))
    s = cv2.GaussianBlur(mp, (0, 0), 14) * 2.2 + cv2.GaussianBlur(mp, (0, 0), 40) * 3.2
    s = np.clip(s, 0, 1) ** .8
    # no floor and nothing at the image's edge: the light must fade out before the box ends
    hh, ww = s.shape
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    edge = np.minimum(np.minimum(xx, ww - 1 - xx) / (pw * .9), np.minimum(yy, hh - 1 - yy) / (ph * .9))
    s = np.clip((s - .04) / .96, 0, 1) * np.clip(edge, 0, 1) ** 1.5
    sc = np.zeros(mp.shape + (3,), np.float32); sc[:] = (120, 255, 90)
    save(np.dstack([sc, s * 255]), "tag_spill.webp", q=85)
    return im, green


def bonus_glow():
    """bonus_glow.webp: the BONUS button's outline as a neon-lime tube (#6CFC54) - the line itself lit near
    white, a tight halo and a wide soft one - padded by BTN_PAD on every side. The plate's tube is painted
    neon lime (about 165,240,48; it was cyan before the 2026-10-27 re-theme, which is still found)."""
    im = np.asarray(Image.open(os.path.join(A, "bonus_btn_bg.webp")).convert("RGBA")).astype(np.float32) / 255
    H, W = im.shape[:2]
    r, g, b, al = im[..., 0], im[..., 1], im[..., 2], im[..., 3]
    lime = (al > .5) & (g > .6) & (b < .45) & (r < .8) & (g > r + .1)
    cyan = (al > .5) & (b > .7) & (g > .6) & (r < .5)
    line = lime | cyan
    if line.sum() < 1000:
        raise SystemExit(f"bonus_glow: the plate's tube was not found ({int(line.sum())} px) - bonus_glow.webp left as it was")
    py, px = int(H * BTN_PAD), int(W * BTN_PAD)
    m = np.pad(line.astype(np.float32), ((py, py), (px, px)))
    g1 = cv2.GaussianBlur(m, (0, 0), 4); g2 = cv2.GaussianBlur(m, (0, 0), 14); g3 = cv2.GaussianBlur(m, (0, 0), 34)
    a = np.clip(m + g1 * 1.8 + g2 * 1.9 + g3 * 1.6, 0, 1)
    t = np.clip(m * 1.2 + g1 * .9, 0, 1)[..., None]
    col = np.array([108, 252, 84], np.float32) * (1 - t) + np.array([228, 255, 214], np.float32) * t
    save(np.dstack([col, a * 255]), "bonus_glow.webp")


# ------------------------------------------------------------------ the paint's colours
HUES = {"violet": (125, 162), "lime": (28, 52)}


def drip_paint(a, h, s, v, colour, tips):
    """The paint of a pool's drips - the live runs extend them, so they take their paint, not the pool's:
    in a window just above each drip's end, base is the body's middle tones, deep its dark shadow band
    (the art paints a crisp dark band down the shadow side), hi the white streak down it and line the ink
    round it; the medians over the pool's drips. a: the wall art (int RGB), h, s, v: its HSV; tips: the
    drips' ends [(x, y, width)] in art px."""
    h0, h1 = HUES[colour]
    lum = a.astype(np.float32) @ np.array([.3, .59, .11], np.float32)
    H, W = lum.shape
    got = {"base": [], "deep": [], "hi": [], "line": []}
    for x, y, w in tips:
        x0, x1, y0, y1 = max(0, int(x - w)), min(W, int(x + w)), max(0, int(y - 2.4 * w)), int(y)
        if x1 - x0 < 4 or y1 - y0 < 4:
            continue
        win, L = a[y0:y1, x0:x1].reshape(-1, 3).astype(np.float32), lum[y0:y1, x0:x1].reshape(-1)
        paint = ((h[y0:y1, x0:x1] >= h0) & (h[y0:y1, x0:x1] <= h1) & (s[y0:y1, x0:x1] > 70) & (v[y0:y1, x0:x1] > 35))
        near = cv2.dilate(paint.astype(np.uint8), np.ones((5, 5), np.uint8)).reshape(-1) > 0
        paint = paint.reshape(-1)
        if paint.sum() < 40:
            continue
        pl = L[paint]
        q = np.percentile(pl, [5, 18, 35, 80])
        got["base"].append(np.median(win[paint][(pl >= q[2]) & (pl <= q[3])], 0))
        got["deep"].append(np.median(win[paint][(pl >= q[0]) & (pl <= q[1])], 0))
        got["hi"].append(win[near & (L > np.percentile(L[near], 97))].mean(0))
        ink = near & ~paint & (L < 28)
        if ink.sum() > 10:
            got["line"].append(np.median(win[ink], 0))
    if not got["base"]:
        return None
    out = {k: [int(round(float(c))) for c in np.median(np.array(vs), 0)] for k, vs in got.items() if vs}
    out.setdefault("line", [int(c * .3) for c in out["deep"]])
    return out


def paint_colours(rgb, body, ring):
    """rgb: int RGB; body: the paint's pixels; ring: the pixels just outside it. base: the paint's own
    colour (its middle tones), deep: its shadow side, hi: its highlight, line: the dark rim round it."""
    px = rgb[body].astype(np.float32)
    lum = px @ np.array([.3, .59, .11], np.float32)
    q = np.percentile(lum, [8, 22, 35, 70, 97])
    base = np.median(px[(lum >= q[2]) & (lum <= q[3])], 0)
    deep = np.median(px[(lum >= q[0]) & (lum <= q[1])], 0)
    hi = px[lum >= q[4]].mean(0)
    rp = rgb[ring].astype(np.float32)
    if len(rp) > 20:
        rl = rp @ np.array([.3, .59, .11], np.float32)
        line = np.median(rp[rl <= np.percentile(rl, 30)], 0)
    else:
        line = deep * .35
    return {k: [int(round(float(c))) for c in v] for k, v in (("base", base), ("deep", deep), ("hi", hi), ("line", line))}


def drip_tips(mask, x0, y0, min_drop, span):
    """the ends of the drips hanging off a shape: column by column the lowest pixel, where it stands below
    its neighbours (a drip's end). Returns [(x, y, width)] in mask px (+ x0, y0)."""
    Hm, Wm = mask.shape
    low = np.array([np.nonzero(mask[:, c])[0].max() if mask[:, c].any() else -1 for c in range(Wm)])
    tips = []
    for c in range(Wm):
        v = low[c]
        if v < 0:
            continue
        lo, hi = max(0, c - span), min(Wm, c + span + 1)
        if v != low[lo:hi].max() or v < min_drop:
            continue
        if tips and c - tips[-1][0] <= span:
            continue
        # the drip's width: the widest of its round end, walking up from the bottom until the run of
        # paint suddenly widens (the pool it hangs from)
        ws = []
        for d in range(2, 70):
            y = v - d
            if y < 0 or not mask[y, c]:
                break
            row = mask[y]
            l = c
            while l > 0 and row[l - 1]:
                l -= 1
            r = c
            while r < Wm - 1 and row[r + 1]:
                r += 1
            wd_ = r - l + 1
            if ws and d > 8 and wd_ > 1.6 * max(ws):
                break
            ws.append(wd_)
        wd = float(np.clip(max(ws) if ws else span, 12, 44))
        # the drip's centre at its end: the middle of the bottom rows
        cols = np.nonzero(mask[max(0, v - 3):v + 1, lo:hi].any(0))[0] + lo
        cx = float(cols.mean()) if len(cols) else c
        tips.append((c, v, wd, cx))
    return [(cx + x0, v + y0, wd) for c, v, wd, cx in tips]


# ------------------------------------------------------------------ the pools in the wall
def wall():
    im = Image.open(os.path.join(A, "bonus_wall.webp")).convert("RGB")
    a = np.asarray(im).astype(np.int16)
    H, W = a.shape[:2]
    h, s, v = np.moveaxis(hsv(a), -1, 0)
    # the pavement line: where the dark wall gives way to the paler pavement, low on the picture - the
    # biggest step up in brightness, taken at the dark grimy band at the wall's foot just above it
    rows = (a @ np.array([.3, .59, .11])).mean(1)
    lo, hi = int(H * .78), int(H * .96)
    step = [rows[y + 8:y + 48].mean() - rows[y - 48:y - 8].mean() for y in range(lo, hi)]
    ys = lo + int(np.argmax(step))
    floor = (ys - 24 + int(np.argmin(rows[ys - 24:ys + 8]))) / H
    violet = (s > 110) & (v > 120) & (h > 125) & (h < 162)
    lime = (s > 140) & (v > 130) & (h > 28) & (h < 52)
    out = []
    for name, m in (("violet", violet), ("lime", lime)):
        m8 = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
        n, lab, st, _ = cv2.connectedComponentsWithStats(m8, 8)
        comps = [i for i in range(1, n) if st[i, 4] > 4000]
        # a drip that the colour split off its pool joins the pool it hangs under
        groups = []
        for i in sorted(comps, key=lambda i: -st[i, 4]):
            x, y, w, hh, area = st[i]
            for gp in groups:
                gx, gy, gw, gh = gp["box"]
                if x < gx + gw + 40 and x + w > gx - 40 and y < gy + gh + 40 and y + hh > gy - 40:
                    gp["ids"].append(i)
                    gp["box"] = (min(gx, x), min(gy, y), max(gx + gw, x + w) - min(gx, x), max(gy + gh, y + hh) - min(gy, y))
                    break
            else:
                groups.append({"ids": [i], "box": (x, y, w, hh)})
        # the small ones fall off too: a drip on its own, near a pool
        for i in range(1, n):
            if i in comps or st[i, 4] < 600:
                continue
            x, y, w, hh, area = st[i]
            for gp in groups:
                gx, gy, gw, gh = gp["box"]
                if x < gx + gw + 30 and x + w > gx - 30 and y < gy + gh + 60 and y + hh > gy - 30:
                    gp["ids"].append(i)
                    gp["box"] = (min(gx, x), min(gy, y), max(gx + gw, x + w) - min(gx, x), max(gy + gh, y + hh) - min(gy, y))
                    break
        for gp in groups:
            comp = np.isin(lab, gp["ids"])
            # the paint with its highlights (holes in the colour mask) filled, and its dark rim (the
            # paint's own darker edge and its shadow on the bricks) grown on
            ys, xs = np.nonzero(comp)
            pad = 28
            x0, y0 = max(0, xs.min() - pad), max(0, ys.min() - pad)
            x1, y1 = min(W, xs.max() + 1 + pad), min(H, ys.max() + 1 + pad)
            c0 = cv2.morphologyEx(comp[y0:y1, x0:x1].astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)))
            ff = np.pad(c0, 1); fm = np.zeros((ff.shape[0] + 2, ff.shape[1] + 2), np.uint8)
            cv2.floodFill(ff, fm, (0, 0), 2)
            body = (ff[1:-1, 1:-1] != 2)
            sub = a[y0:y1, x0:x1]
            ring = cv2.dilate(body.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))).astype(bool) & ~body
            keep = cv2.dilate(body.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))).astype(np.float32)
            alpha = cv2.GaussianBlur(keep, (0, 0), 1.5)
            idx = len(out)
            sprite = np.dstack([sub.astype(np.uint8), (alpha * 255).astype(np.uint8)])
            Image.fromarray(sprite, "RGBA").save(os.path.join(OUT, f"blob_{idx}.webp"), "WEBP", quality=90, alpha_quality=95, method=6)
            bh = ys.max() - ys.min() + 1
            tips = drip_tips(body, x0, y0, min_drop=(ys.min() - y0) + bh * .45, span=max(10, int((xs.max() - xs.min()) / 9)))
            tips = sorted(tips, key=lambda t: -t[1])[:3]
            paint = drip_paint(a, h, s, v, name, tips) or paint_colours(sub, body & (comp[y0:y1, x0:x1] | body), ring)
            out.append({"x": x0 / W, "y": y0 / H, "w": (x1 - x0) / W, "h": (y1 - y0) / H, "colour": name, "paint": paint,
                        "tips": [[round(tx / W, 5), round(ty / H, 5), round(tw / W, 5)] for tx, ty, tw in tips]})
    return {"art": [W, H], "floor": round(floor, 4), "blobs": out}


# ------------------------------------------------------------------ the drips off the tag's letters
# Besides the drips painted into the tag (found below), a few runs start straight off a letter's lower
# edge where the tag shows beside the board on a desktop screen: (x, y) a point inside the letter's face
# (fractions of the tag), the run starts at the face's lower edge straight below it.
EDGE_TIPS = [(.10, .53), (.905, .235)]


def tag_tips(im, green):
    H, W = im.shape[:2]
    rgb, al = im[..., :3].astype(np.int16), im[..., 3]
    h, s, v = np.moveaxis(hsv(rgb), -1, 0)
    # the face of the letters: their bright paint, not the black lines, the outline or the dark extrusion
    face = (al > 128) & ~green & (v > 135)
    face = cv2.morphologyEx(face.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))) > 0
    # the painted drips: thin upright strips of paint that the letters' bodies are too wide to be
    thin = face & ~(cv2.morphologyEx(face.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (61, 61))) > 0)
    thin = cv2.morphologyEx(thin.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(thin, 8)
    tips = []
    for i in range(1, n):
        x, y, w, hh, area = st[i]
        if hh < 60 or area < 700 or hh < 1.8 * w:
            continue
        comp = lab == i
        ys, xs = np.nonzero(comp)
        # upright: the strip's middle wanders little from row to row
        cx = np.array([xs[ys == r].mean() for r in range(y, y + hh) if (ys == r).any()])
        if cx.std() > .45 * max(8, np.median(comp[y:y + hh].sum(1)[comp[y:y + hh].sum(1) > 0])) + 2:
            continue
        widths = comp[y:y + hh].sum(1)
        wmid = float(np.median(widths[int(hh * .25):int(hh * .7)]))
        wlow = float(widths[int(hh * .7):].max())
        if wlow < .85 * wmid:             # a drip ends in a round drop at least as wide as its neck
            continue
        yb = ys.max()
        xb = float(xs[ys >= yb - 4].mean())
        # the drop's end is inked: right under it a dark line or the bare wall, not more of a letter (a
        # stroke that only narrows there would carry on in its own colour)
        under = im[min(H - 1, yb + 2):min(H, yb + 7), int(xb)]
        if len(under) and ((under[:, 3] > 128) & (under[:, :3].max(1) > 90)).all():
            continue
        tips.append((xb, yb, wmid, comp))
    for fx, fy in EDGE_TIPS:
        x, y = int(fx * W), int(fy * H)
        if not face[y, x]:
            continue
        while y < H - 1 and face[y + 1, x]:
            y += 1
        row = face[max(0, y - 20)]
        l = x
        while l > 0 and row[l - 1]:
            l -= 1
        r = x
        while r < W - 1 and row[r + 1]:
            r += 1
        comp = np.zeros_like(face)
        comp[max(0, y - 40):y + 1, max(0, x - 18):x + 19] = face[max(0, y - 40):y + 1, max(0, x - 18):x + 19]
        tips.append((float(x), y, float(min(46, max(26, (r - l) * .35))), comp))
    out = []
    for xb, yb, wd, comp in sorted(tips, key=lambda t: t[0]):
        # its paint: the face's colours in the bottom of the drip
        sel = comp.copy(); sel[:max(0, int(yb - 2.5 * wd))] = False
        ring = cv2.dilate(sel.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))).astype(bool) & ~face & (al > 128)
        out.append({"x": round(xb / W, 5), "y": round((yb + 1) / H, 5), "w": round(wd / W, 5), "paint": paint_colours(rgb, sel, ring)})
    return {"size": [W, H], "tips": out}


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if (f.startswith("blob_") or f.startswith("tube_")) and f.endswith(".webp"):
            os.remove(os.path.join(OUT, f))
    im, green = tag()
    if "--bonus" in sys.argv:
        bonus_glow()
    meta = wall()
    meta["tag"] = tag_tips(im, green)
    meta["tube"] = segments(green)
    meta["relief"] = relief()
    meta["spillPad"] = SPILL_PAD
    meta["glowPad"] = GLOW_PAD
    text = json.dumps(meta, indent=1)
    with open(os.path.join(OUT, "wallfx.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("floor", meta["floor"])
    for b in meta["blobs"]:
        print(b["colour"], round(b["x"], 3), round(b["y"], 3), "tips", b["tips"], b["paint"])
    for t in meta["tag"]["tips"]:
        print("tag tip", t["x"], t["y"], t["w"], t["paint"])


if __name__ == "__main__":
    main()
