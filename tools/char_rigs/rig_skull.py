"""SMOKE SKULL: body re-cut. Called from enhance.py on the delivered rig.

What was wrong: the skull is one flat illustration that had been sliced into rectangles - torso,
two arms, a pocket, two trouser legs and two shoes - with straight cuts through the drawing, all
skinned as one rubber sheet. Nothing could ever separate cleanly: when a foot tapped or the body
hopped, the sheet stretched between the shoes and the cuffs (white wedges opened between the
legs and at the ankles), shoes sheared, and every straight cut showed as a faint line once the
texture was filtered (worse with mipmaps).

What it is now, cut along the drawing's own outlines with hidden parts painted in underneath:
- UPPER: the hoodie (hood, chest, both sleeves, the pocket with the hands in it, the hem band)
  as one mesh - these always moved as one continuous sheet, so one mesh keeps them seamless.
  Weighted from the delivered skin, so it moves exactly as before.
- LEG_L / LEG_R: each trouser leg whole, with its own cuff and outline. Under the hem each leg
  runs on, painted, so the waistband never shows a gap; the top follows the hoodie, the middle
  its leg bone, the cuff its foot.
- SHOE_L / SHOE_R: each shoe whole and rigid on its foot bone, painted on under the cuff (dark
  sock) and, for the back shoe, under the front one.
- a dark backing behind the crotch, like the neck backing behind the jaw.
"""
import math
import os
import numpy as np
import cv2
from PIL import Image
import meshkit as mk
import atlaskit as ak
import outline as ol

BODY = ["shoe_left", "shoe_right", "leg_left", "leg_right", "torso", "arm_left", "arm_right", "pocket"]
# The outline round the figure. The delivered art is a sticker: heavy black ink with a white band
# round it. The owner wants a thin black line like the boy's instead (2026-10-25), so the band
# goes and the ink is re-stroked at OUTLINE_W (outline.py). "white" builds the sticker look.
OUTLINE = "black"
OUTLINE_W = 5.0          # units: the boy's ~5.5-unit line, at the skull's 1.1x larger on-screen scale
FX_OUTLINE = .4          # the ash flakes are drawn far denser than the body: their line is this share of their own ink
OUTLINE_REACH = 22                # px: the drawing's thickest outlines between parts
BOX = (-430, -20, 350, 1000)      # world rect holding the whole body (x0, y0, x1, y1)

# Rough part areas (world units, y up) used only to say which painted area belongs to what.
# Each area's exact edge comes from the drawing's own black outlines.
HEM_Y = 486                                  # the hoodie's hem band sits above this
INSEAM = [(-12, 486), (-14, 360), (-22, 300), (-26, 240)]            # between the trouser legs
CUFF_L = [(-430, 1000), (-186, 1000), (-182, 300), (-150, 288), (-60, 276), (-26, 272)]   # bottom of the left leg
CUFF_R = [(-26, 262), (40, 252), (120, 246), (190, 252), (350, 262)]       # bottom of the right leg
SHOES = [(-26, 272), (-22, 200), (-14, 120), (-6, 0)]                 # between the two shoes
# Under the crotch the sticker band shows between the trouser legs in two pockets, walled in by
# the legs and the shoes (y ~320-355 and ~200-285, just right of the inseam). Everything light in
# here is band: the shoes' white and the laces lie outside it.
LEG_GAP = [(-25, 365), (12, 365), (30, 290), (30, 205), (-25, 205)]


def master(j, atlas, pages, W, slots=BODY):
    """The setup pose drawn at 1 px per unit: composite + per-slot layers (premultiplied)."""
    bn = [b["name"] for b in j["bones"]]
    cv = mk.Canvas(*BOX, 1.0)
    layers = {}
    for s in slots:
        an, att = next(iter(j["skins"][0]["attachments"][s].items()))
        tex = mk.premul(ak.crop(pages, atlas, att.get("path", an)))
        h, w = tex.shape[:2]
        uv = np.array(att["uvs"]).reshape(-1, 2) * [w, h]
        world = mk.mesh_world(att, bn, W)
        tris = np.array(att["triangles"]).reshape(-1, 3)
        layers[s] = (mk.raster_mesh(cv, world, uv, tris, tex), world, uv, tris, att)
    comp = np.zeros_like(cv.img)
    for s in slots:
        mk.over(comp, layers[s][0])
    return cv, comp, layers


def below(poly, x, y):
    """True where (x, y) lies below a line given left to right."""
    P = np.array(poly, float)
    return y < np.interp(x, P[:, 0], P[:, 1])


def right_of(poly, x, y):
    """True where (x, y) lies right of a line given top to bottom (or bottom to top)."""
    P = np.array(sorted(poly, key=lambda p: p[1]), float)
    return x > np.interp(y, P[:, 1], P[:, 0])


def rough_part(x, y):
    """0 UPPER, 1 LEG_L, 2 LEG_R, 3 SHOE_R, 4 SHOE_L (vectorised over arrays)"""
    x = np.asarray(x, float); y = np.asarray(y, float)
    part = np.full(x.shape, -1)
    upper = y >= HEM_Y
    right = right_of(INSEAM, x, y)
    below_l = below(CUFF_L, x, y)
    below_r = below(CUFF_R, x, y)
    shoe_r = right_of(SHOES, x, y)
    part[upper] = 0
    leg_l = ~upper & ~right & ~below_l
    leg_r = ~upper & right & ~below_r
    part[leg_l] = 1; part[leg_r] = 2
    rest = (part < 0)
    part[rest & shoe_r] = 3; part[rest & ~shoe_r] = 4
    return part


SHOE_W = 11.0        # units: the shoes keep their drawn ink up to this far from their paint (the boy's shoe lines are ~13 at this scale)


def shoe_area(cv):
    """Where the shoes and their laces are drawn (rough_part's shoe area, kept off the trouser legs'
    outer edges; the dangling laces either side reach higher)."""
    ys, xs = np.mgrid[0:cv.h, 0:cv.w]
    wx, wy = cv.to_world(np.stack([xs.ravel() + .5, ys.ravel() + .5], 1)).T
    part = rough_part(wx, wy).reshape(cv.h, cv.w)
    wx = wx.reshape(cv.h, cv.w); wy = wy.reshape(cv.h, cv.w)
    return (np.isin(part, (3, 4)) & (wy < 300)) | ((wx < -200) & (wy < 420)) | ((wx > 205) & (wy < 330))


def segment(cv, comp, black_lum=24, min_comp=40, no_ring=None):
    """Per-pixel part labels (-1 = empty) following the drawing's outlines."""
    rgba = mk.unpremul(comp)
    line = None
    if OUTLINE == "black":   # the white band off, the ink re-stroked thin (never along the hood's opening)
        holes = np.zeros(rgba.shape[:2], np.uint8)
        cv2.fillPoly(holes, [np.round(cv.to_px(np.array(LEG_GAP, float))).astype(np.int32)], 1)
        rgba, line = ol.restroke(rgba, OUTLINE_W, keep=no_ring, holes=holes.astype(bool), bold=shoe_area(cv), bold_w=SHOE_W)
    A = rgba[..., 3] > 127
    lum = rgba[..., :3].astype(np.float32).mean(-1)
    black = A & (lum < black_lum)
    body = (A & ~black).astype(np.uint8)
    # the two trouser legs' cloth runs together over the crotch: split it along the inseam
    cut = cv.to_px(np.array(INSEAM, float))
    cv2.polylines(body, [np.round(cut).astype(np.int32)], False, 0, 2)
    n, lab, stats, cen = cv2.connectedComponentsWithStats(body, connectivity=4)
    H, Wd = A.shape
    label = np.full((H, Wd), -1, np.int32)
    border = np.zeros((H, Wd), bool)
    trans = ~A
    near_trans = cv2.dilate(trans.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    for k in range(1, n):
        area = stats[k, cv2.CC_STAT_AREA]
        if area < min_comp: continue
        m = lab == k
        # the white sticker border runs round the outside, touching the transparent surround
        if (m & near_trans).any() and lum[m].mean() > 225:
            border |= m; continue
        ys, xs = np.nonzero(m)
        wx, wy = cv.to_world(np.stack([xs + .5, ys + .5], 1)).T
        votes = np.bincount(rough_part(wx, wy) + 1, minlength=6)[1:]
        label[m] = int(np.argmax(votes))
    # everything else (outlines, the sticker border, specks): front-most part close by, else nearest
    PRIORITY = [0, 1, 2, 3, 4]          # front to back
    dist = []
    for p in range(5):
        core = (label == p).astype(np.uint8)
        dist.append(cv2.distanceTransform(1 - core, cv2.DIST_L2, 5))
    dist = np.stack(dist)
    nearest = np.argmin(dist, 0)
    dmin = dist.min(0)
    todo = (rgba[..., 3] > 0) & (label < 0)
    out = label.copy()
    out[todo] = nearest[todo]
    # An outline between two parts belongs to the one in front, all the way across: a back part
    # left holding part of its neighbour's outline showed it as a ragged black edge whenever the
    # two moved apart (the shoes in big_win). The back part runs on, painted, beneath instead.
    blk = todo & black
    for p in PRIORITY[::-1]:          # back first, so the front-most claim wins
        claim = blk & (dist[p] <= np.minimum(dmin + 20, OUTLINE_REACH))
        out[claim] = p
    # ...and so does the anti-aliased rim where the back part's paint meets that outline (left
    # with the back part it read as a dark hairline along the old boundary)
    from scipy import ndimage
    deep = (out >= 0) & ~black & (cv2.distanceTransform((~black).astype(np.uint8), cv2.DIST_L2, 5) > 3)
    _, (iy, ix) = ndimage.distance_transform_edt(~deep, return_indices=True)
    paint_lum = lum[iy, ix]
    for q in PRIORITY:
        qb = (out == q) & black
        if not qb.any(): continue
        near_q = cv2.distanceTransform((~qb).astype(np.uint8), cv2.DIST_L2, 5) <= 2.5
        rim = near_q & (out > q) & ~black & (lum < paint_lum - 20)
        out[rim] = q
    if line is not None:
        # the new black line plays the part the sticker played: every part lays its own (build_parts)
        return out, rgba, border | line
    # the soft outer edge of the sticker border counts as border too
    border |= (rgba[..., 3] > 0) & (rgba[..., 3] < 255) & (lum > 200)
    # The delivered sticker outline steps and thins where the old rectangle cuts crossed it (the
    # left cuff corner: black showed straight onto the wall). Re-run it at an even width round
    # the drawing, owned by the nearest part.
    core = (rgba[..., 3] > 127) & ~border
    d = cv2.distanceTransform((~core).astype(np.uint8), cv2.DIST_L2, 5)
    wy = cv.oy - (np.arange(cv.h)[:, None] + .5) * np.ones((1, cv.w))
    ring = (d <= BORDER_W) & ~core & ((rgba[..., 3] < 250) | border)
    if no_ring is not None:      # never along the hood's opening (it is not the figure's edge)
        ring &= ~no_ring
    if ring.any():
        from scipy import ndimage
        _, (iy, ix) = ndimage.distance_transform_edt(~core, return_indices=True)
        cov = np.clip(BORDER_W + .5 - d, 0, 1)
        a_old = rgba[..., 3].astype(np.float32) / 255.
        a_new = np.maximum(a_old, cov)
        w_new = np.where(ring, (a_new - a_old) / np.maximum(a_new, 1e-4), 0)[..., None]
        rgba = rgba.copy()
        rgba[..., :3] = (rgba[..., :3] * (1 - w_new) + 255 * w_new).clip(0, 255).astype(np.uint8)
        rgba[..., 3] = np.where(ring, a_new * 255, rgba[..., 3]).clip(0, 255).astype(np.uint8)
        grown = ring & (out < 0)
        out[grown] = out[iy[grown], ix[grown]]
        border |= ring
    return out, rgba, border


# ---------------------------------------------------------------- the delivered skin as a field

def vertex_weights(att, n_bones):
    """(n_verts, n_bones) weight matrix of a weighted mesh."""
    v = att["vertices"]; n_uv = len(att["uvs"]) // 2
    Wm = np.zeros((n_uv, n_bones), np.float32); i = 0; k = 0
    while k < n_uv:
        n = int(v[i]); i += 1
        for _ in range(n):
            Wm[k, int(v[i])] += v[i + 3]; i += 4
        k += 1
    return Wm


def weight_field(cv, layers, n_bones, slots=BODY):
    """Per pixel, the weights of whatever slot is drawn on top there (barycentric within its
    triangle); pixels nothing covers take the nearest covered pixel's weights."""
    from scipy import ndimage
    H, Wd = cv.h, cv.w
    field = np.zeros((H, Wd, n_bones), np.float32)
    have = np.zeros((H, Wd), bool)
    for s in slots:                           # bottom to top: later slots overwrite
        layer, world, uv, tris, att = layers[s]
        Wv = vertex_weights(att, n_bones)
        P = cv.to_px(world)
        idx = np.full((H, Wd), -1, np.int32)
        for k, t in enumerate(tris):
            pts = np.round(P[list(t)] * 16).astype(np.int32)
            cv2.fillConvexPoly(idx, pts, int(k), lineType=cv2.LINE_8, shift=4)
        m = (idx >= 0) & (layer[..., 3] > .5)
        ys, xs = np.nonzero(m)
        T = tris[idx[ys, xs]]
        a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
        q = np.stack([xs + .5, ys + .5], 1)
        v0, v1, v2 = b - a, c - a, q - a
        d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1)
        d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
        den = d00 * d11 - d01 * d01; den = np.where(np.abs(den) < 1e-9, 1e-9, den)
        l1 = (d11 * d20 - d01 * d21) / den; l2 = (d00 * d21 - d01 * d20) / den; l0 = 1 - l1 - l2
        field[ys, xs] = Wv[T[:, 0]] * l0[:, None] + Wv[T[:, 1]] * l1[:, None] + Wv[T[:, 2]] * l2[:, None]
        have |= m
    _, (iy, ix) = ndimage.distance_transform_edt(~have, return_indices=True)
    return field[iy, ix]


# ---------------------------------------------------------------- parts

NAMES = {0: "torso", 1: "leg_left", 2: "leg_right", 3: "shoe_right", 4: "shoe_left", 5: "crotch_fill"}
SOCK = (33, 33, 36)        # what shows if a cuff ever lifts off its shoe: the dark inside of the trouser


def shift_union(mask, dx, dy, n):
    out = np.zeros_like(mask)
    for k in range(1, n + 1):
        out |= np.roll(np.roll(mask, k * dy, 0), k * dx, 1)
    return out


def nearest_fill(rgb, known):
    from scipy import ndimage
    _, (iy, ix) = ndimage.distance_transform_edt(~known, return_indices=True)
    return rgb[iy, ix].copy()


BORDER_W = 10.0           # the white sticker outline round the figure, px (measured median 11)


HOOD_RGB = (26, 26, 30)
HOOD_GAP = 40        # px: the face reaching down to within this of the hoodie's top edge = the opening
HOOD_UNDER = 70      # px: the backing runs this far up under the face
HOOD_EDGE_Y = 735    # world y of the hood's opening: the backing follows the hoodie below, the head above


def hood_backing(j, atlas, pages, W, cv, comp):
    """The inside of the hood: wherever the hoodie art was cut away for the face. The face
    covers it in the setup pose, but a turn of the head opened slivers of wall between the jaw
    and the hood (worst beside the cigar). A dark backing filling exactly that opening, a few px
    under the hood's edge, hangs on the torso behind everything. Returns (mask, RGBA image,
    pixel offset of the image on the canvas)."""
    _, _, lay = master(j, atlas, pages, W, slots=["face"])
    body = comp[..., 3] > .5
    face = lay["face"][0][..., 3] > .3
    # per column: from the hoodie's top edge (scanning up from the chest) to HOOD_UNDER px
    # above the face's lowest point - wherever the face comes down to the hood (the opening)
    row_chest = int(round(cv.oy - 650 * cv.s))
    inner = np.zeros_like(body)
    for x in range(cv.w):
        if not body[row_chest, x]: continue
        r = row_chest
        while r > 0 and body[r - 1, x]: r -= 1          # r: top-most row of the chest run
        fr = np.nonzero(face[:, x])[0]
        if not len(fr): continue
        f_low = fr.max()                                 # lowest face pixel (largest row)
        if f_low < r - HOOD_GAP: continue                # the face stops well above: not the opening
        top = max(0, min(r, f_low) - HOOD_UNDER)
        col = np.zeros(cv.h, bool)
        col[top: r + 6] = True                           # 6 px tucked under the hood's edge
        col[:min(r, f_low)] &= face[:min(r, f_low), x]   # above the gap: only under the face itself
        inner[:, x] = col
    inner = cv2.morphologyEx(inner.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((1, 9), np.uint8)).astype(bool)
    a = cv2.GaussianBlur(inner.astype(np.float32), (0, 0), 1.2)
    ys, xs = np.nonzero(a > .01)
    x0, y0 = max(0, xs.min() - 2), max(0, ys.min() - 2)
    x1, y1 = min(cv.w, xs.max() + 3), min(cv.h, ys.max() + 3)
    img = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
    img[..., :3] = HOOD_RGB; img[..., 3] = (a[y0:y1, x0:x1] * 255).astype(np.uint8)
    return inner, img, (x0, y0)


def head_cover(j, atlas, pages, W, cv, grow=14):
    """Where the face (and the hood backing behind it) covers the body in the setup pose: the
    hood's opening is not an outline, so no part lays a sticker outline there."""
    cover = np.zeros((cv.h, cv.w), np.float32)
    try:
        _, _, lay = master(j, atlas, pages, W, slots=["face"])
        cover = np.maximum(cover, lay["face"][0][..., 3])
    except Exception:
        pass
    att = j["skins"][0]["attachments"].get("neck_fill", {}).get("neck_fill")
    if att:
        tb = W["torso"]
        cx, cy = mk.to_world(tb, (att["x"], att["y"]))
        m = np.zeros((cv.h, cv.w), np.uint8)
        c = cv.to_px(np.array([[cx, cy]]))[0]
        cv2.ellipse(m, (int(c[0]), int(c[1])), (att["width"] // 2, att["height"] // 2), 0, 0, 360, 1, -1)
        cover = np.maximum(cover, m)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * grow + 1, 2 * grow + 1))
    return cv2.dilate((cover > .3).astype(np.uint8), k).astype(bool)


def build_parts(cv, rgba, lab, border, no_sticker=None):
    """RGBA image (canvas-sized) per part: its own pixels, a 2 px bleed of the true drawing past
    each cut, and the hidden part painted in where it runs on under the parts in front of it.
    Every part also carries its own white sticker outline all the way round wherever the drawing
    had one, so when parts part, no outline ends in a straight cut."""
    from scipy import ndimage
    A = rgba[..., 3] > 0
    border_ok = border | ~A                    # where a part may lay its own sticker outline
    if no_sticker is not None:
        border_ok &= ~(no_sticker & ~border)
    masks = {p: lab == p for p in range(5)}
    rgb = np.ascontiguousarray(rgba[..., :3])
    wy = cv.oy - (np.arange(cv.h)[:, None] + .5) * np.ones((1, cv.w))   # world y of each pixel
    k5 = np.ones((5, 5), np.uint8)
    parts = {}
    lum = rgb.astype(np.float32).mean(-1)
    for p in range(5):
        m = masks[p]
        src = m & ~border                     # run on from the drawing itself, not its sticker outline
        front = np.zeros_like(m)
        for q in range(p): front |= masks[q]
        if p == 0:
            ext = np.zeros_like(m)
        elif p in (1, 2):
            # up under the hem band, keeping the leg's own width; leg_right also runs on under
            # leg_left along the inseam
            ext = shift_union(src, 0, -1, 44) & front & (wy < HEM_Y + 60)
            if p == 2:
                ext |= shift_union(src, -1, 0, 26) & masks[1] & (wy > 300)
        else:
            # up under the cuffs; the back shoe also runs on under the front one (and under its
            # sticker outline, which leaves with it)
            ext = shift_union(src, 0, -1, 34) & (masks[1] | masks[2])
            if p == 4:
                ext |= (shift_union(src, 1, 0, 34) | shift_union(src, 1, -1, 24)) & masks[3]
        if p:   # whatever the direction, a back part always runs on a little under the parts in front
            ext |= (ndimage.distance_transform_edt(~m) <= 7) & front
        # its own pixels, and the true drawing for 2 px past each cut, anti-aliased (a hard-edged
        # bleed showed as a jagged staircase whenever the part moved off its neighbour)
        # - but only the drawing's outline ink: a neighbour's paint carried along on the edge
        # showed as a ragged rim once the parts moved apart; elsewhere the part's own edge colour
        # fades out over one pixel
        d_m = ndimage.distance_transform_edt(~m)
        ink = lum < 80
        cut_a = np.where(ink, np.clip(2.5 - d_m, 0, 1), np.clip(1.2 - d_m, 0, 1))
        own = (cut_a > 0) & A & (m | ~front)     # never into a part in front (it runs on under that)
        img = np.zeros((cv.h, cv.w, 4), np.uint8)
        edge_rgb = np.where((ink | m)[..., None], rgb, nearest_fill(rgb, m))
        img[own, :3] = edge_rgb[own]; img[own, 3] = (rgba[own, 3] * cut_a[own]).astype(np.uint8)
        e = ext & ~own
        if e.any():
            if p == 4:   # the hidden heel: the shoe's own canvas tones, never its black lines
                fill = nearest_fill(rgb, src & (rgba[..., 3] > 200) & (lum > 120))
            else:
                fill = nearest_fill(rgb, src & (rgba[..., 3] > 200))
            if p in (3, 4):
                fill[ext & (masks[1] | masks[2])] = SOCK     # under a cuff: dark sock
            fill = cv2.GaussianBlur(fill, (5, 5), 0)
            # under the front part's outline the run-on is that outline's ink: if the parts drift
            # apart, black meets black instead of opening a line of paint between them
            under_ink = ext & (lum < 80) & A
            fill[under_ink] = rgb[under_ink]
            # the run-on fades out over its last few px instead of ending in a hard edge
            d_out = cv2.distanceTransform((ext | own).astype(np.uint8), cv2.DIST_L2, 5)
            fade = np.clip(d_out / 7., 0, 1)
            # under the soft cut edge the run-on lies beneath the part's own fading pixels
            ea = (255 * fade).astype(np.float32)
            a0 = img[..., 3].astype(np.float32)
            em = ext & (a0 < 255)
            a_new = a0 + ea * (1 - a0 / 255.)
            rgb_new = (img[..., :3].astype(np.float32) * a0[..., None] + fill.astype(np.float32) * (ea * (1 - a0 / 255.))[..., None]) / np.maximum(a_new, 1e-3)[..., None]
            img[em, :3] = rgb_new[em].clip(0, 255).astype(np.uint8); img[em, 3] = a_new[em].clip(0, 255).astype(np.uint8)
        # its own outline (the thin black line, or the white sticker), under its own pixels, only
        # where the drawing had outline or nothing
        black = OUTLINE == "black"
        core = m & ~border & (rgba[..., 3] > 127)
        d = cv2.distanceTransform((~core).astype(np.uint8), cv2.DIST_L2, 5)
        sa = np.clip((OUTLINE_W if black else BORDER_W) + .5 - d, 0, 1) * border_ok * (~core)
        if p == 0:
            sa *= (wy > HEM_Y - 30)          # the hoodie's outline stops at its hem
        sa = (sa * 255).astype(np.float32)
        base = img.astype(np.float32)
        a0 = base[..., 3:4] / 255.; s = sa[..., None] / 255.
        out_a = a0 + s * (1 - a0)
        line_rgb = np.array(ol.INK_RGB if black else (255, 255, 255), np.float32)
        out_rgb = (base[..., :3] * a0 + line_rgb * s * (1 - a0)) / np.maximum(out_a, 1e-4)
        img = np.concatenate([out_rgb, out_a * 255.], -1).clip(0, 255).astype(np.uint8)
        parts[p] = img
    return parts


CROTCH_Y = 368       # with the black outline the space between the legs is open from just under here


def crotch_fill(cv):
    """Dark cloth behind the crotch, so the inseam can never open onto the wall. With the sticker
    look the space between the legs was white band and the cloth ran down behind it to y=330; with
    the black outline that space is open, so the cloth stops at the crotch, where it opens."""
    img = np.zeros((cv.h, cv.w, 4), np.uint8)
    bottom, blur = (CROTCH_Y, 3) if OUTLINE == "black" else (330, 9)
    poly = np.array([(-60, HEM_Y + 10), (40, HEM_Y + 10), (30, bottom), (-50, bottom)], float)
    m = np.zeros((cv.h, cv.w), np.uint8)
    cv2.fillPoly(m, [np.round(cv.to_px(poly)).astype(np.int32)], 255)
    m = cv2.GaussianBlur(m, (blur, blur), 0)
    img[..., :3] = SOCK; img[..., 3] = m
    return img


def crop_part(img, pad=4):
    ys, xs = np.nonzero(img[..., 3])
    x0, y0 = max(0, xs.min() - pad), max(0, ys.min() - pad)
    x1, y1 = min(img.shape[1], xs.max() + 1 + pad), min(img.shape[0], ys.max() + 1 + pad)
    return np.ascontiguousarray(img[y0:y1, x0:x1]), (x0, y0)


def part_mesh(img_c, off, cv, weights_at, bone_index, W, grid=26):
    """Contour mesh over a cropped part image; weights_at(world (N,2)) -> list of {bone: w}."""
    alpha = img_c[..., 3]
    h, w = alpha.shape
    poly = mk.outline(alpha, pad=2, step=grid, tol=1.0, thresh=2)
    poly = np.clip(poly, 0, [w, h])
    inner = mk.interior(poly, spacing=grid, margin=.5)
    P, T, nh = mk.triangulate(poly, inner)
    world = cv.to_world(P + np.array(off, float))
    weights = weights_at(world)
    verts, uvs = mk.weighted_mesh(P, (w, h), world, weights, bone_index, W)
    return {"type": "mesh", "uvs": uvs, "triangles": [int(i) for i in T.flatten()], "vertices": verts,
            "hull": nh, "width": w, "height": h}, len(P)


def top_bones(wvec, names, k=4):
    idx = np.argsort(wvec)[::-1][:k]
    d = {names[i]: float(wvec[i]) for i in idx if wvec[i] > .01}
    s = sum(d.values()) or 1
    return {b: v / s for b, v in d.items()}


# ---------------------------------------------------------------- atlas

def pack(images, size=(2048, 2048), pad=10):
    """Shelf-pack {name: PIL image} into one page; returns {name: (x, y)} and the page."""
    PW, PH = size
    order = sorted(images, key=lambda n: (-images[n].size[1], -images[n].size[0]))
    # skyline, bottom-left: each region goes where its top edge lands highest on the page
    sky = np.zeros(PW, int)
    pos = {}
    for n in order:
        w, h = images[n].size
        W2 = w + pad
        best = None
        for x in range(pad, PW - W2 + 1, 2):
            y = int(sky[x - pad: x + W2].max()) + pad if x >= pad else 0
            if y + h + pad > PH: continue
            if best is None or y < best[1]: best = (x, y)
        if best is None:
            raise RuntimeError(f"atlas page full at {n}")
        x, y = best
        sky[x: x + w + pad] = y + h
        pos[n] = (x, y)
    page = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    for n, (px, py) in pos.items():
        page.paste(images[n], (px, py))
    return pos, page


FACE_SCALE = 1.45    # faces: 0.70 -> 1.02 atlas px per unit (the skull is drawn at up to 0.95
                     # device px per unit on a 2x screen, so they were upscaled 1.36x there);
                     # 1.45 is the most at which all five still share one 2048 page
ESRGAN = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                      ".tools", "realesrgan", "realesrgan-ncnn-vulkan.exe")
HIRES = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                     "art", "characters-src", "hires", "smoke-skull")


def hires_faces(faces):
    """The faces at FACE_SCALE: Real-ESRGAN (x4, anime model) once, cached as source art under
    art/characters-src/hires/ (so the pass runs without a GPU afterwards), then Lanczos down in
    premultiplied space so the transparent edge keeps no fringe."""
    import subprocess
    os.makedirs(HIRES, exist_ok=True)
    out = {}
    for n, im in faces.items():
        cache = os.path.join(HIRES, f"{n}@4x.png")
        if not os.path.exists(cache):
            src = os.path.join(HIRES, f"{n}.png")
            im.save(src)
            subprocess.run([ESRGAN, "-i", src, "-o", cache, "-n", "realesrgan-x4plus-anime", "-f", "png"],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        big = mk.premul(Image.open(cache).convert("RGBA"))
        w, h = im.size
        tw, th = int(round(w * FACE_SCALE)), int(round(h * FACE_SCALE))
        small = cv2.resize(big, (tw, th), interpolation=cv2.INTER_AREA)
        out[n] = Image.fromarray(mk.unpremul(small), "RGBA")
    return out


def drop_slots(j, names):
    j["slots"] = [s for s in j["slots"] if s["name"] not in names]
    for sk in j["skins"]:
        for n in names: sk["attachments"].pop(n, None)
    for a in j["animations"].values():
        for n in names: a.get("slots", {}).pop(n, None)
        for key in a.get("drawOrder", []):
            key["offsets"] = [o for o in key.get("offsets", []) if o["slot"] not in names]


# ---------------------------------------------------------------- jointed legs

KNEE_REST = 10.0     # deg: each knee is bent this much in the setup pose, outward (the boy's are 10-14)
KNEE_BLEND_K = .75   # half-width of the thigh -> knee -> shin weight blend, as a share of the thigh


def joint_legs(j):
    """The legs move with the body (owner, 2026-10-25: "it seems off that they aren't").

    Each trouser leg hung on a free leg bone, a child of `motion`, while the body bobbed and swayed
    on the torso: the legs stood still and only their tops stretched under the hem. Now each leg is
    a limb hung from the pelvis, built like the boy's: the old leg bone is the thigh, a shin hangs
    from it, a two-bone IK reaches the planted foot, and the knees rest bent a little outward, so
    when the hips dip the knees bend out and when the hips sway the legs lean. A half-angle knee
    helper keeps the bend smooth, and a cuff bone turns with the shin but stays on the shoe.
    Setup-pose world positions of everything else are unchanged. Returns the knee helpers in
    mk.setup_world's form."""
    B = {b["name"]: b for b in j["bones"]}
    W0 = mk.setup_world(j["bones"])
    pel = W0["pelvis"]
    rot_p = math.degrees(math.atan2(pel[2], pel[0]))
    ik, tf = j.setdefault("ik", []), j.setdefault("transform", [])
    order = len(ik) + len(tf)
    r = lambda v: round(float(v), 4)
    norm = lambda a: (a + 180) % 360 - 180
    made, knees, cuffs = [], [], []
    for side, out in (("left", -1), ("right", 1)):
        H = np.array(W0[f"leg_{side}"][4:6]); F = np.array(W0[f"foot_{side}"][4:6])
        d = float(np.hypot(*(F - H))); u = (F - H) / d
        n = np.array([-u[1], u[0]])
        if n[0] * out < 0: n = -n                                      # the knee goes outward
        L = d / (2 * math.cos(math.radians(KNEE_REST / 2)))
        K = H + u * d / 2 + n * L * math.sin(math.radians(KNEE_REST / 2))
        a_th = math.degrees(math.atan2(K[1] - H[1], K[0] - H[0]))
        a_sh = math.degrees(math.atan2(F[1] - K[1], F[0] - K[0]))
        hx, hy = mk.to_local(pel, H)
        leg = B[f"leg_{side}"]
        for k in ("scaleX", "scaleY", "shearX", "shearY"): leg.pop(k, None)
        leg.update({"parent": "pelvis", "x": r(hx), "y": r(hy), "rotation": r(norm(a_th - rot_p)), "length": r(L)})
        rel = norm(a_sh - a_th)
        made += [{"name": f"shin_{side}", "parent": f"leg_{side}", "x": r(L), "y": 0, "rotation": r(rel), "length": r(L)},
                 {"name": f"knee_{side}", "parent": f"leg_{side}", "x": r(L), "y": 0, "length": 40},
                 {"name": f"cuff_{side}", "parent": f"shin_{side}", "x": r(L), "y": 0, "length": 30}]
        ik.append({"name": f"leg_{side}", "order": order, "bones": [f"leg_{side}", f"shin_{side}"], "target": f"foot_{side}",
                   "mix": 1, "bendPositive": rel > 0, "stretch": True})
        order += 1
        knees.append(side); cuffs.append(side)
    # appended after every existing bone: the indices the delivered weights use stay valid
    j["bones"] += made
    for side in knees:
        tf.append({"name": f"knee_{side}", "order": order, "bones": [f"knee_{side}"], "target": f"shin_{side}",
                   "mixRotate": 0.5, "mixX": 0, "mixY": 0, "mixScaleX": 0, "mixScaleY": 0, "mixShearY": 0})
        order += 1
    for side in cuffs:
        tf.append({"name": f"cuff_{side}", "order": order, "bones": [f"cuff_{side}"], "target": f"foot_{side}",
                   "mixRotate": 0, "mixX": 1, "mixY": 1, "mixScaleX": 0, "mixScaleY": 0, "mixShearY": 0})
        order += 1
    return [(f"knee_{s}", f"shin_{s}", 0.5) for s in knees]


# ---------------------------------------------------------------- the re-cut

def fix(j, atlas, pages, extra_regions=None):
    """Re-cut the body. Returns the new page images {page_name: PIL} (atlas updated in place),
    per-part vertex counts and debug data. extra_regions: {name: PIL} packed onto the page too."""
    bones = [b["name"] for b in j["bones"]]
    bidx = {n: i for i, n in enumerate(bones)}
    W = mk.setup_world(j["bones"])
    cv, comp, layers = master(j, atlas, pages, W)
    hood, hood_img, (hx, hy) = hood_backing(j, atlas, pages, W, cv, comp)
    lab, rgba, border = segment(cv, comp, no_ring=hood)
    field = weight_field(cv, layers, len(bones))
    # the hood's opening is not the figure's edge: no part lays a sticker outline along it
    parts = build_parts(cv, rgba, lab, border, hood)
    parts[5] = crotch_fill(cv)
    # The hood backing replaces the delivered ellipse (neck_fill): same slot, behind everything,
    # now a mesh that bridges the opening - its top half rides the head, its bottom the hoodie -
    # so however the head turns, the gap between jaw and hood is lined with the hood's inside.
    if "neck_fill" in j["skins"][0]["attachments"]:
        # the upper part follows the face exactly as the face moves (head, and the jaw where the
        # jaw carries the face), the lower part the hoodie
        _, _, flay = master(j, atlas, pages, W, slots=["face"])
        ffield = weight_field(cv, flay, len(bones), slots=["face"])

        def neck_weights(world):
            out = []
            px = np.clip(np.floor(cv.to_px(world)).astype(int), 0, [cv.w - 1, cv.h - 1])
            for (x, y), (qx, qy) in zip(world, px):
                h = float(mk.smoothstep(HOOD_EDGE_Y, HOOD_EDGE_Y + 55, y))
                fw = ffield[qy, qx] * h
                fw[bidx["torso"]] += 1 - h
                out.append(top_bones(fw, bones))
            return out
        m, _ = part_mesh(hood_img, (hx, hy), cv, neck_weights, bidx, W, grid=22)
        m["path"] = "neck_fill"
        j["skins"][0]["attachments"]["neck_fill"] = {"neck_fill": m}
        extra_regions = dict(extra_regions or {}, neck_fill=Image.fromarray(hood_img, "RGBA"))

    # From here on the setup pose is the jointed-leg rig's. Every bone the parts above were cut and
    # weighted against keeps its setup-pose world matrix; the new bones come after them all.
    helpers = joint_legs(j)
    bones = [b["name"] for b in j["bones"]]
    bidx = {n: i for i, n in enumerate(bones)}
    W = mk.setup_world(j["bones"], helpers)

    def field_at(world):
        px = np.clip(np.floor(cv.to_px(world)).astype(int), 0, [cv.w - 1, cv.h - 1])
        F = field[px[:, 1], px[:, 0]]
        return np.pad(F, ((0, 0), (0, len(bones) - F.shape[1])))   # the delivered skin knows none of the new bones

    def weights_for(p):
        side = {1: "left", 2: "right", 3: "right", 4: "left"}.get(p)
        cuff_y = {1: 286, 2: 256}.get(p)
        if p in (1, 2):
            # the knee's axis: half-way between the thigh's and the shin's directions (the boy's scheme)
            th, sh = W[f"leg_{side}"], W[f"shin_{side}"]
            K = np.array(sh[4:6])
            ut = np.array([th[0], th[2]]); ut /= np.hypot(*ut)
            us = np.array([sh[0], sh[2]]); us /= np.hypot(*us)
            ax = (ut + us) / np.hypot(*(ut + us))
            kb = KNEE_BLEND_K * j["bones"][bidx[f"leg_{side}"]]["length"]

        def f(world):
            F = field_at(world); out = []
            for (x, y), fw in zip(world, F):
                if p in (0, 5):
                    out.append(top_bones(fw, bones)); continue
                if p in (3, 4):
                    out.append({f"foot_{side}": 1.0}); continue
                s = float(mk.smoothstep(HEM_Y - 55, HEM_Y - 135, y))      # 0 under the hem -> 1 down the leg
                c = float(mk.smoothstep(cuff_y + 95, cuff_y + 20, y))     # 1 at the cuff: it rides the cuff bone, on the shoe
                z = float((np.array([x, y]) - K) @ ax)
                w_th = float(mk.smoothstep(0, kb, -z)); w_sh = float(mk.smoothstep(0, kb, z)); w_kn = 1 - w_th - w_sh
                own = np.zeros(len(bones), np.float32)
                own[bidx[f"leg_{side}"]] = (1 - c) * w_th; own[bidx[f"knee_{side}"]] = (1 - c) * w_kn
                own[bidx[f"shin_{side}"]] = (1 - c) * w_sh; own[bidx[f"cuff_{side}"]] = c
                out.append(top_bones((1 - s) * fw + s * own, bones))
            return out
        return f

    images, meshes, stats = {}, {}, {}
    for p, img in parts.items():
        name = NAMES[p]
        c, off = crop_part(img)
        images[name] = Image.fromarray(c, "RGBA")
        meshes[name], stats[name] = part_mesh(c, off, cv, weights_for(p), bidx, W)
    # everything else stays as drawn; the faces come back at FACE_SCALE (see hires_faces)
    faces = {}
    for pg in atlas.pages:
        for n, r in pg["regions"]:
            if n in BODY: continue
            (faces if n.startswith("face_") else images)[n] = ak.crop(pages, atlas, n)
    images.update(extra_regions or {})
    faces = hires_faces(faces)
    if OUTLINE == "black":
        # the delivered pictures carry the white sticker band too: the faces (at their own density,
        # px per unit), the cigar, the painted plume (shown under reduced motion) and the ash
        skin = j["skins"][0]["attachments"]
        for n in faces:
            dens = faces[n].size[0] / skin["face"][n]["width"]   # ~1.02 (FACE_SCALE x the delivered .70)
            faces[n] = Image.fromarray(ol.restroke(np.asarray(faces[n]), OUTLINE_W * dens)[0], "RGBA")
        for n in list(images):
            if n.startswith("ash_"):
                images[n] = Image.fromarray(ol.restroke(np.asarray(images[n]), None, ratio=FX_OUTLINE)[0], "RGBA")
            elif n == "cigar_clean":   # bold, like the shoes: only the white band goes
                im = np.asarray(images[n])
                images[n] = Image.fromarray(ol.restroke(im, OUTLINE_W, bold=np.ones(im.shape[:2], bool), bold_w=99)[0], "RGBA")
            elif n in ("smoke", "smoke_wisp"):
                images[n] = Image.fromarray(ol.restroke(np.asarray(images[n]), OUTLINE_W)[0], "RGBA")
    page_name = atlas.pages[0]["name"]; header = atlas.pages[0]["header"]
    face_page = page_name.replace(".png", "-2.png")
    out_pages = {}
    atlas.pages = []
    for pname, imgs, sizes in ((page_name, images, ((2048, 1024), (2048, 2048))), (face_page, faces, ((2048, 2048),))):
        for k, size in enumerate(sizes):
            try:
                pos, page = pack(imgs, size)
                break
            except RuntimeError:
                if k == len(sizes) - 1: raise
        hdr = [(k, f"{size[0]}, {size[1]}" if k == "size" else v) for k, v in header]
        atlas.pages.append({"name": pname, "header": hdr, "regions": []})
        out_pages[pname] = page
        for n, (x, y) in sorted(pos.items(), key=lambda kv: (kv[1][1], kv[1][0])):
            w, h = imgs[n].size
            atlas.add(pname, n, x, y, w, h)
    # slots: the arms and the pocket now live in the hoodie mesh
    drop_slots(j, ["arm_left", "arm_right", "pocket"])
    skin = j["skins"][0]["attachments"]
    for name, m in meshes.items():
        m["path"] = name
        skin[name] = {name: m}
    order = ["shoe_left", "shoe_right", "leg_right", "leg_left", "torso"]
    S = {s["name"]: s for s in j["slots"]}
    rest = [s for s in j["slots"] if s["name"] not in order]
    back = [s for s in rest if s["name"] == "neck_fill"]
    others = [s for s in rest if s["name"] != "neck_fill"]
    j["slots"] = back + [{"name": "crotch_fill", "bone": "root", "attachment": "crotch_fill"}] + [S[n] for n in order] + others
    return out_pages, stats, (cv, comp, lab, parts)
