"""Small repaints of the delivered line art, done procedurally so they apply to every face pose.

The boy's head is drawn seven times (one per expression), each by hand, so the same flaw sits in a
slightly different place in each. Every fix here finds its shapes in the image itself, reshapes
the silhouette with signed-distance operations at 4x, and repaints only the pixels that change,
in the drawing's own colours: the outline in its own ink at its own weight, fills by the colour
the same distance in from the edge has elsewhere on that part. No blurs, no inpainting smears.
"""
import numpy as np
import cv2
from scipy import ndimage

SS = 4   # supersampling for shapes


def up(mask, s=SS):
    return cv2.resize(mask.astype(np.float32), (mask.shape[1] * s, mask.shape[0] * s), interpolation=cv2.INTER_LINEAR) > .5


def down(mask4, s=SS):
    h, w = mask4.shape[0] // s, mask4.shape[1] // s
    return cv2.resize(mask4.astype(np.float32), (w, h), interpolation=cv2.INTER_AREA)


def disk(r):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def inside_dist(mask4, s=SS):
    """distance (in 1x px) from each pixel centre to the outside of a 4x mask, at 1x resolution"""
    d4 = ndimage.distance_transform_edt(mask4) / s
    return cv2.resize(d4.astype(np.float32), (mask4.shape[1] // s, mask4.shape[0] // s), interpolation=cv2.INTER_AREA)


def grey(rgb, tol=18):
    r, g, b = rgb[..., 0].astype(int), rgb[..., 1].astype(int), rgb[..., 2].astype(int)
    return (np.abs(r - g) < tol) & (np.abs(g - b) < tol)


def profile(rgb, dist, sel, dmax=48):
    """median colour per whole px of distance-to-edge over the selected pixels"""
    prof = np.zeros((dmax + 1, 3), np.float32)
    have = np.zeros(dmax + 1, bool)
    di = np.floor(dist).astype(int)
    for d in range(dmax + 1):
        m = sel & (di == d)
        if m.sum() >= 3:
            prof[d] = np.median(rgb[m], 0); have[d] = True
    idx = np.nonzero(have)[0]
    for d in range(dmax + 1):                  # holes: nearest measured distance
        if not have[d]:
            prof[d] = prof[idx[np.argmin(np.abs(idx - d))]]
    return prof


def paint(img, where, rgb, alpha):
    """premultiplied-correct replace of pixels `where` with rgb (float 0..255) at coverage alpha"""
    out = img.astype(np.float32).copy()
    out[where, :3] = rgb[where]
    out[where, 3] = alpha[where] * 255
    return out.clip(0, 255).astype(np.uint8)


# ---------------------------------------------------------------- the beanie's hanging tip

def beanie_tip(img, zone=(625, 380, 769, 640), R=24):
    """The right end of the beanie's folded cuff hangs down past the cheek as a hook, with a
    wedge of wall between the hook and the cheek: the beanie's silhouette reads as chopped off
    there. On the other side of his head the same place shows his black hair between the cuff
    and the ear, so the wedge is filled the same way: hair, in the drawing's ink black, with a
    rounded lower edge (a morphological closing of the silhouette, radius R, at 4x) running from
    the hook's tip into the cheek's outline. The hook and the cheek are left exactly as drawn."""
    x0, y0, x1, y1 = zone
    sub = img[y0:y1, x0:x1].copy()
    A = sub[..., 3].astype(np.float32) / 255.
    rgb = sub[..., :3].astype(np.float32)
    M4 = up(A > .5)
    pad = (R + 4) * SS
    big = np.pad(M4, pad, constant_values=False)          # outside the zone counts as empty
    N4 = cv2.morphologyEx(big.astype(np.uint8), cv2.MORPH_CLOSE, disk(R * SS)).astype(bool)[pad:-pad, pad:-pad] | M4
    added4 = N4 & ~M4
    lab, n = ndimage.label(added4)
    if not n:
        return img, 0
    # the wedge: the biggest piece the closing added
    sizes = ndimage.sum(added4, lab, range(1, n + 1))
    wedge4 = lab == (1 + int(np.argmax(sizes)))
    if wedge4.sum() < 100 * SS * SS:
        return img, 0
    black = (rgb.mean(-1) < 60) & (A > .9)
    inkc = np.median(rgb[black], 0)
    # the hair lies under the drawing: where the two meet, its coverage tops the drawing's own
    # soft edge up to the new silhouette's, so no hairline of wall is left along the old edge
    covN = down(N4)
    near = ndimage.binary_dilation(down(wedge4) > 0, iterations=2)
    a0 = A[..., None]
    cov = np.where(near, np.clip((covN - A) / np.maximum(1 - A, 1e-4), 0, 1), 0)
    where = cov > 0
    c = cov[..., None]
    # hair goes under what is drawn: premultiplied "drawing over hair"
    out_a = a0 + c * (1 - a0)
    out_rgb = (rgb * a0 + inkc * c * (1 - a0)) / np.maximum(out_a, 1e-4)
    sub2 = sub.astype(np.float32)
    sub2[where, :3] = out_rgb[where]; sub2[where, 3] = out_a[where, 0] * 255
    out = img.copy(); out[y0:y1, x0:x1] = sub2.clip(0, 255).astype(np.uint8)
    return out, int(where.sum())


# ---------------------------------------------------------------- the jaw corner

def jaw_corner(img, zone=(580, 650, 716, 795), sigma=9.0, ink=6.5):
    """At the lower right of the face the outline broke: the cheek's outline stops in a square
    step and the jaw's outline fades into a soft grey smear before it reaches it. The silhouette
    there is rounded (the signed distance field smoothed, at 4x), the outline redrawn round the
    corner at the drawing's weight, and the face inside it filled from the face's own colours
    (nearest clean pixel - flat, as the art is)."""
    x0, y0, x1, y1 = zone
    sub = img[y0:y1, x0:x1].copy()
    A = sub[..., 3].astype(np.float32) / 255.
    rgb = sub[..., :3].astype(np.float32)
    M4 = up(A > .5)
    sd = ndimage.distance_transform_edt(M4) - ndimage.distance_transform_edt(~M4)
    sds = cv2.GaussianBlur(sd.astype(np.float32), (0, 0), sigma * SS)
    # blend back to the original shape at the zone's border so nothing moves there
    h4, w4 = M4.shape
    yy, xx = np.mgrid[0:h4, 0:w4]
    edge = np.minimum.reduce([xx, yy, w4 - 1 - xx, h4 - 1 - yy]).astype(np.float32) / SS
    t = np.clip((edge - 4) / 14, 0, 1)
    N4 = (sds * t + sd * (1 - t)) > 0
    covN = down(N4)
    dN = inside_dist(N4)
    black = rgb.mean(-1) < 70
    clean = (A > .97) & ~black & (inside_dist(M4) > ink + 2)    # face colours, away from the old edge
    _, (iy, ix) = ndimage.distance_transform_edt(~clean, return_indices=True)
    fill = rgb[iy, ix]
    changed = down(N4 ^ M4) > .02
    band = (dN < ink + 2.5) & (covN > 0)
    smear = (A > .02) & (A < .97)
    redo = (changed | smear | band) & ndimage.binary_dilation(down(N4 ^ M4) > .02, iterations=int(3 * ink))
    redo |= changed
    ink_a = np.clip(ink + .5 - dN, 0, 1)[..., None]         # 1 = ink, 0 = fill (AA across the inner edge)
    inkc = np.median(rgb[black & (A > .97)], 0) if (black & (A > .97)).any() else np.zeros(3)
    col = fill * (1 - ink_a) + inkc * ink_a
    sub2 = paint(sub, redo, col, np.clip(covN, 0, 1))
    out = img.copy(); out[y0:y1, x0:x1] = sub2
    return out, int(redo.sum())
