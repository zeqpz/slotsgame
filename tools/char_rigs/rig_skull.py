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

BODY = ["shoe_left", "shoe_right", "leg_left", "leg_right", "torso", "arm_left", "arm_right", "pocket"]
OUTLINE_REACH = 22                # px: the drawing's thickest outlines between parts
BOX = (-430, -20, 350, 1000)      # world rect holding the whole body (x0, y0, x1, y1)

# Rough part areas (world units, y up) used only to say which painted area belongs to what.
# Each area's exact edge comes from the drawing's own black outlines.
HEM_Y = 486                                  # the hoodie's hem band sits above this
INSEAM = [(-12, 486), (-14, 360), (-22, 300), (-26, 240)]            # between the trouser legs
CUFF_L = [(-430, 1000), (-186, 1000), (-182, 300), (-150, 288), (-60, 276), (-26, 272)]   # bottom of the left leg
CUFF_R = [(-26, 262), (40, 252), (120, 246), (190, 252), (350, 262)]       # bottom of the right leg
SHOES = [(-26, 272), (-22, 200), (-14, 120), (-6, 0)]                 # between the two shoes


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


def segment(cv, comp, black_lum=24, min_comp=40):
    """Per-pixel part labels (-1 = empty) following the drawing's outlines."""
    rgba = mk.unpremul(comp)
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
    # the soft outer edge of the sticker border counts as border too
    border |= (rgba[..., 3] > 0) & (rgba[..., 3] < 255) & (lum > 200)
    # The delivered sticker outline steps and thins where the old rectangle cuts crossed it (the
    # left cuff corner: black showed straight onto the wall). Re-run it at an even width round
    # the drawing, owned by the nearest part.
    core = (rgba[..., 3] > 127) & ~border
    d = cv2.distanceTransform((~core).astype(np.uint8), cv2.DIST_L2, 5)
    wy = cv.oy - (np.arange(cv.h)[:, None] + .5) * np.ones((1, cv.w))
    ring = (d <= BORDER_W) & ~core & ((rgba[..., 3] < 250) | border) & (wy < HEM_Y)   # legs and shoes only
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


def weight_field(cv, layers, n_bones):
    """Per pixel, the weights of whatever slot is drawn on top there (barycentric within its
    triangle); pixels nothing covers take the nearest covered pixel's weights."""
    from scipy import ndimage
    H, Wd = cv.h, cv.w
    field = np.zeros((H, Wd, n_bones), np.float32)
    have = np.zeros((H, Wd), bool)
    for s in BODY:                            # bottom to top: later slots overwrite
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


def hood_backing(j, atlas, pages, W, cv, comp):
    """The inside of the hood: wherever the hoodie art was cut away for the face. The face
    covers it in the setup pose, but a turn of the head opened slivers of wall between the jaw
    and the hood (worst beside the cigar). A dark backing filling exactly that opening, a few px
    under the hood's edge, hangs on the torso behind everything. Returns (mask, RGBA image,
    pixel offset of the image on the canvas)."""
    from scipy import ndimage
    _, _, lay = master(j, atlas, pages, W, slots=["face"])
    body = comp[..., 3] > .5
    face = lay["face"][0][..., 3] > .3
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
    closed = cv2.morphologyEx((body | face).astype(np.uint8), cv2.MORPH_CLOSE, k).astype(bool)
    filled = ndimage.binary_fill_holes(closed)
    wy = cv.oy - (np.arange(cv.h)[:, None] + .5) * np.ones((1, cv.w))
    inner = filled & ~body & (wy > 640)
    inner = cv2.dilate(inner.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))).astype(bool) & filled
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
        # its own sticker outline, under its own pixels, only where the drawing had outline or nothing
        core = m & ~border & (rgba[..., 3] > 127)
        d = cv2.distanceTransform((~core).astype(np.uint8), cv2.DIST_L2, 5)
        sa = np.clip(BORDER_W + .5 - d, 0, 1) * border_ok * (~core)
        if p == 0:
            sa *= (wy > HEM_Y - 30)          # the hoodie's outline stops at its hem
        sa = (sa * 255).astype(np.float32)
        base = img.astype(np.float32)
        a0 = base[..., 3:4] / 255.; s = sa[..., None] / 255.
        out_a = a0 + s * (1 - a0)
        out_rgb = (base[..., :3] * a0 + 255. * s * (1 - a0)) / np.maximum(out_a, 1e-4)
        img = np.concatenate([out_rgb, out_a * 255.], -1).clip(0, 255).astype(np.uint8)
        parts[p] = img
    return parts


def crotch_fill(cv):
    """Dark cloth behind the crotch, so the inseam can never open onto the wall."""
    img = np.zeros((cv.h, cv.w, 4), np.uint8)
    poly = np.array([(-60, HEM_Y + 10), (40, HEM_Y + 10), (30, 330), (-50, 330)], float)
    m = np.zeros((cv.h, cv.w), np.uint8)
    cv2.fillPoly(m, [np.round(cv.to_px(poly)).astype(np.int32)], 255)
    m = cv2.GaussianBlur(m, (9, 9), 0)
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


# ---------------------------------------------------------------- the re-cut

def fix(j, atlas, pages, extra_regions=None):
    """Re-cut the body. Returns the new page images {page_name: PIL} (atlas updated in place),
    per-part vertex counts and debug data. extra_regions: {name: PIL} packed onto the page too."""
    bones = [b["name"] for b in j["bones"]]
    bidx = {n: i for i, n in enumerate(bones)}
    W = mk.setup_world(j["bones"])
    cv, comp, layers = master(j, atlas, pages, W)
    lab, rgba, border = segment(cv, comp)
    field = weight_field(cv, layers, len(bones))
    hood, hood_img, (hx, hy) = hood_backing(j, atlas, pages, W, cv, comp)
    # the hood's opening is not the figure's edge: no part lays a sticker outline along it
    parts = build_parts(cv, rgba, lab, border, hood)
    parts[5] = crotch_fill(cv)
    # the hood backing replaces the delivered ellipse (neck_fill): same slot, behind everything
    if "neck_fill" in j["skins"][0]["attachments"]:
        hh, hw = hood_img.shape[:2]
        cx, cy = cv.to_world(np.array([[hx + hw / 2, hy + hh / 2]]))[0]
        tb = W["torso"]
        assert abs(tb[2]) < 1e-6 and abs(tb[0] - 1) < 1e-6
        lx, ly = mk.to_local(tb, (cx, cy))
        j["skins"][0]["attachments"]["neck_fill"] = {"neck_fill": {"x": round(lx, 2), "y": round(ly, 2), "width": hw, "height": hh}}
        extra_regions = dict(extra_regions or {}, neck_fill=Image.fromarray(hood_img, "RGBA"))

    def field_at(world):
        px = np.clip(np.floor(cv.to_px(world)).astype(int), 0, [cv.w - 1, cv.h - 1])
        return field[px[:, 1], px[:, 0]]

    def weights_for(p):
        side = {1: "left", 2: "right", 3: "right", 4: "left"}.get(p)
        cuff_y = {1: 286, 2: 256}.get(p)

        def f(world):
            F = field_at(world); out = []
            for (x, y), fw in zip(world, F):
                if p in (0, 5):
                    out.append(top_bones(fw, bones)); continue
                if p in (3, 4):
                    out.append({f"foot_{side}": 1.0}); continue
                s = float(mk.smoothstep(HEM_Y - 55, HEM_Y - 135, y))      # 0 under the hem -> 1 down the leg
                c = float(mk.smoothstep(cuff_y + 95, cuff_y + 20, y))     # 1 at the cuff
                own = np.zeros(len(bones), np.float32)
                own[bidx[f"leg_{side}"]] = 1 - c; own[bidx[f"foot_{side}"]] = c
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
