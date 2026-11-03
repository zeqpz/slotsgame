# L4 - Hangtags: what Blender's cut changes from the rig recipe (tools/icon_rigs/recipes/L4.py).
# The two tags hang on the string loop and swing on it each to its own spring, twisting, so the back tag shows
# more or less of itself beside the front one. Its part hidden behind the front tag must be real art, not the
# recipe's blur: it comes from the clean plate (the back tag alone), and since that plate came back re-composed - a
# single tag, upright and centred, though in the back tag's own dark card and faint lettering - it is laid onto the
# back tag here by its three visible corners (top right, bottom right, bottom left) -> art/blender/plates/
# L4_back_fit.png, and only where the front tag hides it. The front tag is cut again from the new art: the recipe's
# mask was read off the old drawing, which left the new art's border on the tag's left and bottom edges out, and
# the recipe blurred the tag under its grommet. The logo and the grommet are printed on the front tag: they move
# with it, so they are not parts of their own (the front tag carries them, the art's own pixels).
# The "art" plate is the icon itself through tools/blender/plate.py --fit-only (a copy of art/icons-src/L4.png as
# art/blender/plates/L4_art_raw.png; no generation, the fit is the identity).
import os, sys
import numpy as np
from PIL import Image
from scipy import ndimage
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, "tools", "icon_rigs", "recipes"))
from L4 import FRONT, EDGE, BACK, STRING_AREA      # noqa: E402

PLATE_PROMPT = (
    "This sticker shows TWO hangtags, one in front of the other, hanging on a string loop. Make it show ONE tag only:\n"
    "1. Delete the FRONT tag entirely - the left one, the tag with the big bright white graffiti lettering, its metal "
    "grommet and everything on it. Do not redraw it or replace it with another tag: it is simply gone.\n"
    "2. Delete the string loop at the top and its little black clip too.\n"
    "3. What remains is the BACK tag alone, the darker tag on the right with the faint grey graffiti lettering. Keep its "
    "visible right part exactly as it is - same place, same size, same tilt, same right edge and bottom corner. Paint "
    "the rest of it that the front tag was hiding: the back tag is a plain dark worn card the same size and shape as "
    "the front tag was, so its straight top edge, its left edge and its rounded corners continue up and to the left, "
    "with its faint grey lettering carrying on and a small grommet hole near the middle of its top edge.\n"
    "4. The plain white sticker border follows this single tag's own outline all the way round.")

BACK_CORNERS = [(663, 284), (893, 872), (589, 939)]      # the back tag's top right, bottom right, bottom left (art)
BACK_TL = (305, 258)       # its top left, hidden under the front tag: the tag is fanned (in perspective), so the
                           # plate is laid on by all four corners, its top edge meeting the art's where it shows


def _tag_core(a):
    rgb, al = a[..., :3], a[..., 3]
    white = (rgb.min(-1) > .8) & (rgb.max(-1) - rgb.min(-1) < .1)
    c = (al > .5) & ~white & (ndimage.distance_transform_edt(al > .5) > 6)
    c = ndimage.binary_fill_holes(ndimage.binary_closing(c, iterations=2))
    lab, n = ndimage.label(c)
    return lab == 1 + np.argmax(ndimage.sum(c, lab, range(1, n + 1)))


def _fit_back_plate():
    """The plate's one tag laid onto the back tag: an affine map taking its top right, bottom right and bottom left
    corners (its core's bounding rectangle) onto the back tag's -> L4_back_fit.png (remade when L4_raw.png is newer)."""
    import cv2
    plates = os.path.join(ROOT, "art", "blender", "plates")
    raw, out = os.path.join(plates, "L4_raw.png"), os.path.join(plates, "L4_back_fit.png")
    if os.path.exists(out) and os.path.getmtime(out) >= max(os.path.getmtime(raw), os.path.getmtime(__file__)):
        return np.asarray(Image.open(out).convert("RGBA")).astype(np.float32) / 255
    pl = np.asarray(Image.open(raw).convert("RGBA")).astype(np.float32) / 255
    cnts, _ = cv2.findContours(_tag_core(pl).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    box = cv2.boxPoints(cv2.minAreaRect(cnts[0]))
    tr = max(box, key=lambda p: p[0] - .3 * p[1])            # the corners by where they lie
    br = max(box, key=lambda p: p[0] + p[1])
    bl = max(box, key=lambda p: p[1] - p[0])
    tl = min(box, key=lambda p: p[0] + p[1])
    M = cv2.getPerspectiveTransform(np.float32([tl, tr, br, bl]), np.float32([BACK_TL] + BACK_CORNERS))
    pm = pl.copy(); pm[..., :3] *= pm[..., 3:4]
    w = np.clip(cv2.warpPerspective(pm, M, (1000, 1000), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT), 0, 1)
    a = w[..., 3:4]
    rgb = np.where(a > 1e-3, w[..., :3] / np.maximum(a, 1e-3), 0)
    res = np.concatenate([np.clip(rgb, 0, 1), a], -1)
    Image.fromarray((res * 255).round().astype(np.uint8), "RGBA").save(out)
    print("L4 plate laid onto the back tag by its corners:", [tuple(np.round(p, 1)) for p in (tr, br, bl)], "->", BACK_CORNERS)
    return res


_back = _fit_back_plate()
_ys = np.arange(1000)[:, None]
_xs = np.arange(1000)[None, :]
_edge_x = np.interp(np.arange(1000), [y for x, y in EDGE], [x for x, y in EDGE])[:, None]
def _front_new():
    """The front tag on the new art (the recipe's mask read off the new art, not the old drawing)."""
    sys.path.insert(0, os.path.join(ROOT, "tools", "icon_rigs"))
    import rigkit
    from build import load_recipe
    cv = rigkit.Rig(load_recipe(os.path.join(ROOT, "tools", "icon_rigs", "recipes", "L4.py"))).cv
    return cv.eval(("art", FRONT)) > .5


HIDDEN = ndimage.binary_erosion(_front_new(), iterations=2) & (_xs < _edge_x + 6)  # where the front tag hides the back tag (inside the front, left of its edge)
BACK_TAG = ndimage.binary_erosion(_back[..., 3] > .5, iterations=2) & _tag_core(_back)
BACK_TAG = ndimage.binary_dilation(BACK_TAG, iterations=4) & (_back[..., 3] > .5)    # the card and its ink edge

BACK_BORDER = (_back[..., 3] > .03) & ~BACK_TAG              # the plate tag's white border round it
# The plate tag is laid on by an affine, but the back tag in the art is fanned (in perspective): along its top edge
# under the front tag's border the plate's border lands ~25 px low. There the back tag takes the white band just
# above its own top edge from the art (the front tag's border: plain white, the same as its own would be).
_art = np.asarray(Image.open(os.path.join(ROOT, "art", "icons-src", "L4.png")).convert("RGBA")).astype(np.float32) / 255
_xl = np.arange(1000)[None, :]
_top = 259 + (_xl - 548) * (284 - 259) / (663 - 548)        # the back card's top edge (art), y at each x
TOP_BAND = ((_ys >= _top - 20) & (_ys <= _top + 8) & (_xl >= 545) & (_xl <= 668) & (_art[..., :3].min(-1) > .8)
            & (_art[..., 3] > .9))
DROP = ["logo", "knot"]
FILLS = [
    # the front tag on the new art, grown 3 px into the empty outside only (its soft outer edge whole)
    {"part": "front", "region": ("art", ("or", FRONT, ("minus", ("grow", FRONT, 3), ("or", BACK, STRING_AREA, ("grow", STRING_AREA, 4))))), "plate": "art"},
    {"part": "back", "region": (BACK_TAG & HIDDEN).astype(np.float32), "plate": "back_fit", "blend": "matched"},
    # and its own sticker border there (white, the plate's): when it swings out from behind the front tag its top
    # edge keeps its border instead of opening a dark wedge
    {"part": "back", "region": (BACK_BORDER & HIDDEN).astype(np.float32), "plate": "back_fit"},
    {"part": "back", "region": (TOP_BAND & HIDDEN).astype(np.float32), "plate": "art"},
]
CLEAR = [   # the recipe's blur behind the front tag, wherever the back tag is not
    {"part": "back", "region": (HIDDEN & ~BACK_TAG & ~BACK_BORDER & ~TOP_BAND).astype(np.float32)},
]
