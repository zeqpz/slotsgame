"""Cartoon sticker lettering in the style of the symbol icons (art/icons-src): bold black ink
outline, flat paint with one shade tone and a highlight, a darker 3D block behind, clean round
drips, a few white gloss strokes, and the thin white sticker edge every icon has.

Everything is drawn as masks at SS times the output size and downsampled, so every edge is
anti-aliased. Each letter (with its drips) is kept as its own layer too, so the rigs can animate
the letters separately (make.py writes both).
"""
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

SS = 3   # supersampling


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


def dil(m, r):
    return cv2.dilate(m.astype(np.uint8), disc(r)).astype(bool) if r > 0 else m.copy()


def ero(m, r):
    return cv2.erode(m.astype(np.uint8), disc(r)).astype(bool) if r > 0 else m.copy()


def shift(m, dx, dy):
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(m.astype(np.uint8), M, (m.shape[1], m.shape[0]), flags=cv2.INTER_NEAREST).astype(bool)


def rounded(m, r):
    """Round every corner off by about r (open then close with a disc)."""
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, disc(r))
    return cv2.morphologyEx(m, cv2.MORPH_CLOSE, disc(r)).astype(bool)


def bubble(m, r):
    """A bubble letter's swollen, soft shape: every corner and stroke end rounded off by about
    2r (blur by r, cut at half), the counters left open."""
    return cv2.GaussianBlur(m.astype(np.float32), (0, 0), r) > .5


def smooth_noise(shape, cell, rng):
    """A smooth random field in [-1, 1]: a random value every `cell` px, bicubic in between."""
    H, W = shape
    cell = max(2, int(round(cell)))
    gh, gw = H // cell + 4, W // cell + 4
    g = rng.uniform(-1, 1, (gh, gw)).astype(np.float32)
    n = cv2.resize(g, (gw * cell, gh * cell), interpolation=cv2.INTER_CUBIC)[cell:cell + H, cell:cell + W]
    return n / max(1e-6, float(np.abs(n).max()))


def bumpy(m, octaves, rng):
    """Lumpy, hand-drawn edges: every edge pushed out or in along smooth random fields, each
    octave (bump spacing px, amplitude px) laid over the last - big lumps with small bumps on them."""
    inside = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5)
    outside = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
    sdf = inside - outside
    for cell, amp in octaves:
        sdf = sdf + amp * smooth_noise(m.shape, cell, rng)
    return sdf > 0


def fill_enclosed(m):
    """Fill the regions enclosed by m (for hollow outline fonts), keeping real counters open is
    not possible from the outline alone - callers pass counters to re-open separately."""
    h, w = m.shape
    ff = np.pad(m.astype(np.uint8), 1)
    mask = np.zeros((h + 4, w + 4), np.uint8)
    cv2.floodFill(ff, mask, (0, 0), 2)
    return (ff[1:-1, 1:-1] != 2)


def glyph(ch, font_path, px, hollow=False):
    """One character as a bool mask (tight box), px tall-ish."""
    f = ImageFont.truetype(font_path, px)
    l, t, r, b = f.getbbox(ch)
    pad = px // 6
    im = Image.new("L", (r - l + 2 * pad, b - t + 2 * pad), 0)
    ImageDraw.Draw(im).text((pad - l, pad - t), ch, font=f, fill=255)
    m = np.asarray(im) > 127
    if hollow:
        m = fill_enclosed(m)
    ys, xs = np.nonzero(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def place(canvas_hw, mask, cx, cy, angle=0.0, scale=1.0):
    """Paste a glyph mask into a canvas-sized mask, rotated/scaled about its centre at (cx, cy)."""
    H, W = canvas_hw
    h, w = mask.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, scale)
    M[0, 2] += cx - w / 2
    M[1, 2] += cy - h / 2
    out = cv2.warpAffine(mask.astype(np.uint8) * 255, M, (W, H), flags=cv2.INTER_LINEAR)
    return out > 127


def add_drips(letter, xs, lengths, width, rng):
    """Clean cartoon drips hanging from the bottom of a letter at the given x positions: a stem
    that narrows as it runs and ends in a round drop, melted into the letter with a smooth fillet
    (a closing of letter + stem, kept near the stem). Returns (drips_mask, spots)."""
    H, W = letter.shape
    stems = np.zeros_like(letter)
    spots, widths = [], []
    for x, L in zip(xs, lengths):
        x = int(x)
        col = np.nonzero(letter[:, max(0, x - 2):x + 3].any(1))[0]
        if not len(col) or L < width:
            continue
        y0 = int(col.max()) - int(width * .8)     # start well inside the letter
        y1 = int(col.max()) + int(L)
        w0 = width * rng.uniform(.8, 1.2)
        im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
        steps = 60
        for k in range(steps + 1):
            t = k / steps
            y = y0 + (y1 - y0) * t
            w = w0 * (1 - .32 * t ** .7)
            d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=255)
        rb = w0 * .52
        d.ellipse([x - rb, y1 - rb, x + rb, y1 + rb * 1.15], fill=255)
        stems |= np.asarray(im) > 127
        spots.append((x, y0, y1 + rb * 1.15)); widths.append(w0)
    if not spots:
        return stems, spots
    wm = float(np.mean(widths))
    union = letter | stems
    closed = cv2.morphologyEx(union.astype(np.uint8), cv2.MORPH_CLOSE, disc(wm * .75)).astype(bool)
    near = dil(stems & ~letter, wm * .9)
    out = (stems | (closed & near)) & ~letter
    return out, spots


def clean(m, r):
    """Drop slivers thinner than about 2r from a paint mask."""
    return cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, disc(r)).astype(bool) if r >= 1 else m


def shade_band(body, dx, dy):
    """The part of `body` that a copy of itself shifted by (dx, dy) does not cover: an inner band
    along the edges facing away from (dx, dy)."""
    return body & ~shift(body, dx, dy)


def render(letters, P, out_size):
    """letters: list of dicts {body, drips} (bool masks at the working size, SS x out_size).
    P: palette/geometry dict. Returns (RGBA uint8 at out_size, per-letter RGBA layers)."""
    H, W = letters[0]["body"].shape
    ink, stick, depth = P["ink"], P["sticker"], P["depth"]
    ang = np.deg2rad(P.get("light", 225))
    ddx, ddy = -np.cos(ang), np.sin(ang)          # extrusion goes away from the light
    def paint_one(L, with_sticker=True):
        body = L["body"] | L["drips"]
        # 3D block: the body swept down-right by `depth`
        block = np.zeros_like(body)
        n = max(1, int(depth / 2))
        for k in range(1, n + 1):
            block |= shift(body, ddx * depth * k / n, ddy * depth * k / n)
        block &= ~body
        solid = body | block
        line = dil(solid, ink) & ~solid
        inner_line = dil(body, ink * .45) & block       # the ink between letter face and block
        sticker = dil(solid, ink + stick) & ~dil(solid, ink)
        rgba = np.zeros((H, W, 4), np.float32)
        def put(mask, col, a=1.0):
            c = np.array(list(col) + [a], np.float32)
            rgba[mask] = c
        if with_sticker:
            put(sticker, (1, 1, 1))
        put(line, (0, 0, 0))
        put(block, P["block"])
        put(inner_line, (0, 0, 0))
        put(body, P["fill"])
        # the griddy texture: a fine diamond grid laid over the paint in a darker tone of it, kept
        # off the edges (inside the face by the ink line's width), so the letter reads as a
        # printed sticker with detail in it rather than a flat fill
        g = P.get("grid")
        if g:
            yy, xx = np.ogrid[0:H, 0:W]
            sp, lw = g["spacing"], g["width"]
            lines = (((xx + yy) % sp) < lw) | (((xx - yy) % sp) < lw)
            inner = ero(body, g.get("inset", ink * .6))
            tone = tuple(f * (1 - g["dark"]) + sd * g["dark"] for f, sd in zip(P["fill"], P["shade"]))
            put(lines & inner, tone)
            if g.get("dots"):   # a halftone dot in each cell's middle, smaller toward the light
                cy = ((yy + sp // 2) % sp - sp / 2) ** 2 + ((xx) % sp - sp / 2) ** 2
                put(inner & (cy < (lw * .9) ** 2) & ~lines, tone)
        sh = clean(shade_band(body, -ddx * P["shade_w"], -ddy * P["shade_w"]), P["shade_w"] * .3)
        put(sh, P["shade"])
        hi = clean(shade_band(ero(body, P["hi_inset"]), ddx * P["hi_w"], ddy * P["hi_w"]), P["hi_w"] * .35)
        put(hi, P["hi"])
        # shine: a curved white streak hugging the top-left inside edge of the letter, then a dot,
        # the way the icons catch the light
        if P.get("gloss", True):
            core = ero(L["body"], P["hi_inset"] * 2.0)
            ys, xs = np.nonzero(L["body"])
            if len(xs):
                bx0, by0, bx1, by1 = xs.min(), ys.min(), xs.max(), ys.max()
                bw, bh = bx1 - bx0, by1 - by0
                band = shade_band(core, ddx * P["hi_w"] * 1.6, ddy * P["hi_w"] * 1.6)
                yy, xx = np.ogrid[0:H, 0:W]
                zone = (yy < by0 + bh * .34) & (xx < bx0 + bw * .62)
                shine = band & zone
                shine = cv2.morphologyEx(shine.astype(np.uint8), cv2.MORPH_OPEN, disc(P["hi_w"] * .35)).astype(bool)
                put(shine, (1, 1, 1))
                cy, cx = np.nonzero(core & (yy > by0 + bh * .36) & (yy < by0 + bh * .5) & (xx < bx0 + bw * .4))
                if len(cx):
                    i = int(np.argmin(cx)); r = P["hi_w"] * .75
                    im = Image.new("L", (W, H), 0)
                    ImageDraw.Draw(im).ellipse([cx[i] + r * .4, cy[i] - r, cx[i] + r * 2.4, cy[i] + r], fill=255)
                    put((np.asarray(im) > 127) & core, (1, 1, 1))
        # each drip: a soft highlight line down its left side and a glint on the drop
        dr = L["drips"] & ~L["body"]
        if dr.any():
            dhi = clean(shade_band(ero(dr, P["hi_inset"] * .9), P["hi_w"] * .9, 0) & dr, P["hi_w"] * .3)
            put(dhi, P["hi"])
        return rgba
    plain = [paint_one(L, with_sticker=False) for L in letters]
    # the whole piece: one sticker under everything, letters painted left to right on top
    allbody = np.zeros((H, W), bool)
    for L in letters:
        allbody |= L["body"] | L["drips"]
    full = np.zeros((H, W, 4), np.float32)
    # sticker for the union (so overlapping letters share one sticker edge)
    blockall = np.zeros_like(allbody)
    n = max(1, int(depth / 2))
    for k in range(1, n + 1):
        blockall |= shift(allbody, ddx * depth * k / n, ddy * depth * k / n)
    solid_all = allbody | blockall
    st = dil(solid_all, ink + stick) & ~dil(solid_all, ink)
    full[st] = (1, 1, 1, 1)
    for no_sticker in plain:
        a = no_sticker[..., 3:4]
        full = no_sticker * a + full * (1 - a)
    def down(x):
        im = (x * 255).clip(0, 255).astype(np.uint8)
        a = im[..., 3:4].astype(np.float32) / 255
        pm = im.astype(np.float32); pm[..., :3] *= a
        sm = cv2.resize(pm, out_size, interpolation=cv2.INTER_AREA)
        al = sm[..., 3:4]
        rgb = np.where(al > 1e-3, sm[..., :3] / np.maximum(al / 255, 1e-3) / 255 * 255, 0)
        return np.concatenate([rgb, al], -1).clip(0, 255).round().astype(np.uint8)
    out = down(full)
    del full
    # each letter's own layer (for the rigs): the letter painted alone, with a sticker edge of its own
    layers = []
    for L in letters:
        layers.append(down(paint_one(L)))
    return out, layers
