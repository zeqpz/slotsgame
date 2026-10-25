"""Re-stroke a sticker-style drawing with a thin black outline (owner, 2026-10-25: the skull's
white sticker outline goes; he gets a thin black line like the boy's).

The skull was drawn as a sticker: a heavy black ink contour (~13 units) with a white band
(~10 units) round the outside of it. The boy has one black line of ~5.5 units and nothing else.
restroke() takes a picture of the first kind to the second:

1. The white band goes. Everything light that can be reached from the transparent surround
   without crossing ink is the band (the ink is grown by a couple of px first, so a hairline gap
   in the contour cannot let the flood into the white of the skull or the shoes), plus the
   anti-aliased fringe where the band met the ink.
2. The heavy outer contour goes: the ink reachable from the outside through ink, no deeper than
   `band_max` px (deep enough for the thickest stretch of contour, too shallow to follow an inner
   line far into the drawing).
3. One even line of `width` px is laid round what is left, anti-aliased by distance.

`keep` marks pixels to leave exactly as they were (the hood's opening, which the face covers and
which was never an outline). Returns (rgba, line), `line` = where the new outline is.
"""
import numpy as np
import cv2
from scipy import ndimage

INK_LUM = 28        # the art's ink sits at lum 0-16; the darkest paint (hoodie, beanie) starts near 40
LIGHT_LUM = 150     # the white band, and the light side of its anti-aliasing
INK_RGB = (14, 14, 16)


def disk(r):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def contour_width(rgba, outside=None):
    """Median thickness (px) of the ink contour along the drawing's edge."""
    a = rgba[..., 3]
    lum = rgba[..., :3].astype(np.float32).mean(-1)
    ink = (lum < INK_LUM) & (a > 127)
    if outside is None:
        outside = a < 8
    dE = ndimage.distance_transform_edt(~outside)
    band = ndimage.binary_propagation(ink & (dE <= 2), mask=ink & (dE <= 24))
    paint = ~outside & ~band & (a > 127) & (lum >= INK_LUM)
    inner = band & cv2.dilate(paint.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    return float(np.median(dE[inner])) if inner.any() else 0.0


def find_outside(rgba, sticker=True, holes=None):
    """The transparent surround, grown over the white sticker band and its anti-aliased fringe.
    `holes`: where the drawing encloses a pocket of the band (it showed between the skull's legs,
    walled in by the legs and the shoes, out of the flood's reach) - every light pixel in it is
    band too."""
    a = rgba[..., 3]
    lum = rgba[..., :3].astype(np.float32).mean(-1)
    out0 = a < 8
    if not sticker:
        return out0
    ink = (lum < INK_LUM) & (a > 127)
    barrier = cv2.dilate(ink.astype(np.uint8), disk(3)).astype(bool)
    passable = out0 | ((lum > LIGHT_LUM) & ~barrier)
    lab, _ = ndimage.label(passable)
    keep = np.unique(lab[out0 & (lab > 0)])
    outside = out0 | np.isin(lab, keep[keep > 0])
    if holes is not None:
        outside |= passable & holes
    # the fringe where the band met the ink: within 4 px of it and not ink itself
    fringe = cv2.dilate(outside.astype(np.uint8), disk(4)).astype(bool) & ~ink
    return outside | fringe


def restroke(rgba, width, band_max=24, keep=None, sticker=True, ratio=None, holes=None, bold=None, bold_w=11.0):
    """rgba: straight-alpha uint8 (H, W, 4). width: the new line in px, or None with `ratio` (the
    new line as a share of the old contour's measured thickness). holes: see find_outside.
    bold: where the drawing's own heavy ink stays the outline (the shoes, the cigar - the owner
    wanted those bolder than the clothes): only the white band goes there, and any black that runs
    on further than `bold_w` px from the paint it outlines and out to the open (a solid shadow the
    sticker hid between the shoes). Returns (rgba, line mask)."""
    rgba = np.ascontiguousarray(rgba)
    a = rgba[..., 3]
    lum = rgba[..., :3].astype(np.float32).mean(-1)
    ink = (lum < INK_LUM) & (a > 127)
    outside = find_outside(rgba, sticker, holes)
    if width is None:
        width = max(1.0, ratio * (contour_width(rgba, outside) or 8.0))
    dE = ndimage.distance_transform_edt(~outside)
    band = ndimage.binary_propagation(ink & (dE <= 2), mask=ink & (dE <= band_max))
    if bold is not None:
        band &= ~bold
    inner = ~outside & ~band & (a > 0)
    if bold is not None:
        paint = ~outside & (a > 127) & (lum >= INK_LUM)
        far = bold & ink & (ndimage.distance_transform_edt(~paint) > bold_w)
        touch = far & cv2.dilate((outside | band).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        inner &= ~ndimage.binary_propagation(touch, mask=far)
    # specks - anti-aliasing left stranded between the white band and the ink - would each get a
    # ring of their own and show as black dots off the figure
    lab, n = ndimage.label(inner)
    if n:
        sizes = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1))
        inner &= np.isin(lab, np.nonzero(sizes >= max(60, 3 * width * width))[0] + 1)
    solid = inner & (a > 127)
    # a few px of padding so the new line never runs off the picture's edge
    pad = int(np.ceil(width)) + 2
    P = lambda m, v=0: np.pad(m, ((pad, pad), (pad, pad)) + (((0, 0),) if m.ndim == 3 else ()), constant_values=v)
    rgba_p, inner_p, solid_p = P(rgba), P(inner), P(solid)
    dI = ndimage.distance_transform_edt(~solid_p)
    line_a = np.clip(width + .5 - dI, 0, 1)
    if bold is not None:   # the drawing's ink is the line there: just a soft pixel past its edge
        line_a = np.where(P(bold), np.clip(1.5 - dI, 0, 1), line_a)
    line_a[solid_p] = 0
    out = np.zeros_like(rgba_p, dtype=np.float32)
    out[..., :3] = INK_RGB
    out[..., 3] = line_a
    # the drawing's own pixels over the line
    src_a = np.where(inner_p, rgba_p[..., 3] / 255., 0)[..., None]
    out_a = src_a + out[..., 3:4] * (1 - src_a)
    out_rgb = (rgba_p[..., :3] * src_a + out[..., :3] * out[..., 3:4] * (1 - src_a)) / np.maximum(out_a, 1e-4)
    res = np.concatenate([out_rgb, out_a * 255], -1).clip(0, 255).astype(np.uint8)
    line = (line_a > 0) & ~solid_p
    if keep is not None:
        # left as drawn - but never the white band itself (it showed as a white flick by the cigar)
        keep_p, out_p = P(keep), P(outside)
        res[keep_p & ~out_p] = rgba_p[keep_p & ~out_p]
        res[keep_p & out_p] = 0
        line &= ~keep_p
    return res[pad:-pad, pad:-pad], line[pad:-pad, pad:-pad]
