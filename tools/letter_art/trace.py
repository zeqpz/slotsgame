"""Trace the letter shapes out of an existing grungy lettering piece, so cartoon.py can repaint
the SAME lettering in the icon style.

The pieces are built alike: paint-coloured letter faces (cracked, speckled), a black outline,
an outer paint rim, drips, loose spatter. A letter face is the paint that lies deeper than the
rim and outline from the edge of the piece (distance transform), with its cracks closed. The
counters (O, B, the XX diamond, the S's mouths) are black ink deep inside, so they stay open.
"""
import numpy as np
import cv2
from PIL import Image


def disc(r):
    r = max(1, int(round(r)))
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def trace(path, scale, t_src, crack_src=2.5, hole_src=14, min_src=18, grow_src=0.0, smooth_src=3.0):
    """-> (faces bool mask at `scale` x the source, list of drips (x, y_top, y_bottom, width) in
    the same px, the source size). t_src: rim + outline thickness in source px."""
    im = Image.open(path).convert("RGBA")
    W, H = im.size
    big = np.asarray(im.resize((round(W * scale), round(H * scale)), Image.LANCZOS)).astype(np.float32) / 255
    rgb, al = big[..., :3], big[..., 3]
    vis = al > .5
    lum = rgb @ np.array([.3, .59, .11], np.float32)
    sat = rgb.max(-1) - rgb.min(-1)
    paint = vis & (lum > .2) & (sat > .15)
    dist = cv2.distanceTransform(vis.astype(np.uint8), cv2.DIST_L2, 5)
    face = paint & (dist > t_src * scale)
    s = scale
    face = cv2.morphologyEx(face.astype(np.uint8), cv2.MORPH_CLOSE, disc(crack_src * s)).astype(bool)
    # fill specks and cracks left inside a face (small enclosed holes), keep the counters
    inv = (~face).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(inv, 4)
    hh, ww = face.shape
    for i in range(1, n):
        x, y, bw, bh, a = st[i]
        if x > 0 and y > 0 and x + bw < ww and y + bh < hh and a < (hole_src * s) ** 2:
            # a real counter is mostly black ink in the source; a speck hole is paint/grunge
            comp = lab == i
            if (lum[comp] < .2).mean() < .7 or a < (hole_src * s * .45) ** 2:
                face |= comp
    n, lab, st, _ = cv2.connectedComponentsWithStats(face.astype(np.uint8), 8)
    keep = np.zeros_like(face)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] >= (min_src * s) ** 2:
            keep |= lab == i
    # cartoon-smooth edges: the grunge bites and bumps blur away
    face = cv2.GaussianBlur(keep.astype(np.float32), (0, 0), smooth_src * s) > .5
    if grow_src:
        face = cv2.dilate(face.astype(np.uint8), disc(grow_src * s)).astype(bool)
    # drips: tall thin visible runs below the faces
    ring = cv2.dilate(face.astype(np.uint8), disc(t_src * 1.1 * s)).astype(bool)
    rest = vis & ~ring
    rest = cv2.morphologyEx(rest.astype(np.uint8), cv2.MORPH_OPEN, disc(1.2 * s)).astype(bool)
    n, lab, st, _ = cv2.connectedComponentsWithStats(rest.astype(np.uint8), 8)
    drips = []
    for i in range(1, n):
        x, y, bw, bh, a = st[i]
        if bh > 2.2 * bw and bh > 12 * s:
            drips.append((x + bw / 2, y, y + bh, bw))
    return face, drips, (W, H)


def letters(face, min_area):
    """Split the faces into letters, left to right (connected pieces; pieces that touch stay one)."""
    n, lab, st, cen = cv2.connectedComponentsWithStats(face.astype(np.uint8), 8)
    out = []
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] >= min_area:
            out.append((st[i, cv2.CC_STAT_LEFT], lab == i))
    return [m for _, m in sorted(out, key=lambda p: p[0])]
