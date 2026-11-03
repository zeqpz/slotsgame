# L5 - A pair of dice: what Blender's cut changes from the rig recipe (tools/icon_rigs/recipes/L5.py).
# The dice rock on their corners and tumble apart, so each needs a whole sticker border of its own. In the art the
# two dice almost touch: their borders run together into one white band, 3-5 px wide where they come closest, and
# the recipe cuts the pair apart along a line read off the old drawing (it clips both dice's ink). Here each die is
# its own two pieces on one bone: its body (the die and its ink outline, exactly the art's pixels, split from the
# other die where the two outlines nearly meet) and its border as a "rim" drawn behind both dice. A rim carries
# the art's own border all round its die and the band between the dice (both rims hold the same band pixels, so at
# rest they lie back exactly), and behind the other die's body it carries the rest of its own border from a clean
# plate of that die alone (plates "a" and "b"), so the gap that opens as the dice rock shows each die whole.
# The pieces: top_die and low_die (the upper-left and lower-right die), each with its _rim. anim_L5.py draws
# both rims behind both bodies (the cut's draw order puts low_die's rim in front of top_die).
#
# The "art" plate is the icon itself, run through tools/blender/plate.py --fit-only (a copy of
# art/icons-src/L5.png as art/blender/plates/L5_art_raw.png; no generation, the fit is the identity, pixel for
# pixel): FILLS from it put the art's own pixels into a piece where the recipe's masks leave them out - the border
# past SPLIT's 17 px reach (this sticker's border is ~22 px with its dark edge), the far half of the band, and the
# few px of each die's ink the recipe's line gave to the other die.
import os
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PLATES = {
    "a": ("1. Remove the lower-right red die completely. Nothing of it is left.\n"
          "2. Keep the upper-left red die exactly as it is, and complete its sticker border where the other die was: the "
          "plain white border follows this die's own black outline all the way round, the same width as everywhere else "
          "on it, with the same soft dark outer edge, and transparent beyond."),
    "b": ("1. Remove the upper-left red die completely. Nothing of it is left.\n"
          "2. Keep the lower-right red die exactly as it is, and complete its sticker border where the other die was: the "
          "plain white border follows this die's own black outline all the way round, the same width as everywhere else "
          "on it, with the same soft dark outer edge, and transparent beyond."),
}
A_C, B_C = (304, 340), (700, 640)            # the dice's centres (recipe)


def _cores():
    """Each die's body: the art's non-white pixels (as SPLIT finds a core), shared out between the dice by a flood
    from each die's centre that grows one px a step through them - where the two outlines nearly touch, the split
    falls half way across the few px that join them. The pips and glints (white) are holes, filled."""
    src = np.asarray(Image.open(os.path.join(ROOT, "art", "icons-src", "L5.png")).convert("RGBA")).astype(np.float32) / 255
    rgb, al = src[..., :3], src[..., 3]
    white = (rgb.min(-1) > .80) & (rgb.max(-1) - rgb.min(-1) < .10)
    body = (al > .5) & ~white & (ndimage.distance_transform_edt(al > .5) > 7)
    a, b = np.zeros_like(body), np.zeros_like(body)
    a[A_C[1] - 10:A_C[1] + 10, A_C[0] - 15:A_C[0] + 15] = True
    b[B_C[1] - 10:B_C[1] + 10, B_C[0] - 10:B_C[0] + 10] = True
    a &= body; b &= body
    cross = ndimage.generate_binary_structure(2, 1)
    for _ in range(2000):
        na = ndimage.binary_dilation(a, cross) & body & ~b
        nb = ndimage.binary_dilation(b, cross) & body & ~na
        if (na == a).all() and (nb == b).all():
            break
        a, b = na, nb
    a, b = ndimage.binary_fill_holes(a), ndimage.binary_fill_holes(b)
    return a, b & ~a, al


CORE_A, CORE_B, _al = _cores()
_DA = ndimage.distance_transform_edt(~CORE_A)
_DB = ndimage.distance_transform_edt(~CORE_B)


def _fit_die_plates():
    """The clean plates of each die alone (plate.py L5 a / b) keep their die in place, but plate.py fits a plate by
    the whole sticker's silhouette, and one die cannot match two: its fit is wrong. Each is fitted here by the same
    fit (tools/icon_redraw/install.py) on that die's own part of the art -> art/blender/plates/L5_<a|b>_fit.png
    (remade whenever its _raw.png is newer)."""
    import sys
    sys.path.insert(0, os.path.join(ROOT, "tools", "icon_redraw"))
    from install import arr, fit, warp
    plates = os.path.join(ROOT, "art", "blender", "plates")
    old = None
    for name, core in (("a", CORE_A), ("b", CORE_B)):
        raw, out = os.path.join(plates, f"L5_{name}_raw.png"), os.path.join(plates, f"L5_{name}_fit.png")
        if not os.path.exists(raw) or (os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(raw)):
            continue
        old = arr(Image.open(os.path.join(ROOT, "art", "icons-src", "L5.png"))) if old is None else old
        new = arr(Image.open(raw))
        o = old.copy()
        o[..., 3] *= ndimage.binary_dilation(core, iterations=24)      # the art of this die alone
        p, score = fit(o, new)
        pm = new.copy(); pm[..., :3] *= pm[..., 3:4]
        w = np.clip(warp(pm, p, old.shape[:2], order=3), 0, 1)
        a = w[..., 3:4]
        rgb = np.where(a > 1e-3, w[..., :3] / np.maximum(a, 1e-3), 0)
        a = np.where(ndimage.binary_dilation(a[..., 0] > .12, iterations=3)[..., None] & (a > .03), a, 0)
        Image.fromarray((np.concatenate([np.clip(rgb, 0, 1), a], -1) * 255).round().astype(np.uint8), "RGBA").save(out)
        print(f"L5 plate {name} fitted on its die: scale {p[0]:.4f}, turn {np.degrees(p[1]):.2f} deg, shift ({p[2]:.1f}, {p[3]:.1f}), score {score:.3f}")


_fit_die_plates()


FRINGE = 4            # px round a die's outline that still carry its ink's soft edge and shadow
_bright = (_al > .98) & (np.asarray(Image.open(os.path.join(ROOT, "art", "icons-src", "L5.png")).convert("RGB")).min(-1) > 215)


def _body(d_own, d_other):
    """A die's body: its core and the soft edge of its outline (on its own side of the band's middle)."""
    return ((d_own <= FRINGE) & (d_own <= d_other)).astype(np.float32)


# The sticker's concave notch at either end of the band, where the two borders meet, belongs to neither die alone:
# each rim carries its own side of it (from the art, so the rest pose is exact). When the dice part, the notch
# opens to the outside and each border keeps a slight pinch at that corner - tried both ways round: giving one
# rim the whole notch, or a plate border there, drew a grey edge inside the other die's white as they moved.


def _from_art(d_own, d_other, front=False):
    """Where a die's rim takes the art: its border out to 26 px on its own side of the band's middle; across the
    middle only the opaque white band, out to 16 px (past that it would be the other die's own border) - never
    the soft edge of the other die's outline, which would ride along as a grey ghost line."""
    out = (d_own > 0) & (d_other > FRINGE) & (((d_own <= d_other) & (d_own <= 26)) | ((d_own > d_other) & (d_own <= 16) & _bright))
    return out.astype(np.float32)


def _from_plate(d_own, d_other, front=False):
    """Where it takes its clean plate: behind the other die's body, as far as its border reaches."""
    out = (d_own > 0) & (d_own <= 26) & (d_other <= FRINGE)
    return out.astype(np.float32)


_EVERYWHERE = [(-10, -10), (1010, -10)]      # a cut line above the icon: the whole die is the one piece
SPLIT = {
    "die_a": [{"name": "top_die", "side": "below", "line": _EVERYWHERE, "rim": True, "chain": [A_C, (A_C[0], A_C[1] - 100)]}],
    "die_b": [{"name": "low_die", "side": "below", "line": _EVERYWHERE, "rim": True, "chain": [B_C, (B_C[0], B_C[1] - 100)]}],
}
FILLS = [
    {"part": "top_die", "region": _body(_DA, _DB), "plate": "art"},
    {"part": "low_die", "region": _body(_DB, _DA), "plate": "art"},
    {"part": "top_die_rim", "region": _from_art(_DA, _DB, False), "plate": "art"},      # drawn behind everything
    {"part": "low_die_rim", "region": _from_art(_DB, _DA, True), "plate": "art"},
    {"part": "top_die_rim", "region": _from_plate(_DA, _DB, False), "plate": "a_fit"},
    {"part": "low_die_rim", "region": _from_plate(_DB, _DA, True), "plate": "b_fit"},
]
CLEAR = [   # nothing of one die on the other's body
    {"part": "top_die", "region": ndimage.binary_dilation(CORE_B, iterations=1).astype(np.float32)},
    {"part": "low_die", "region": ndimage.binary_dilation(CORE_A, iterations=1).astype(np.float32)},
]
