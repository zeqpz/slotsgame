# L1 - Spray can, standing upright and idle (art redrawn 2026-11-03: the same can, upright, no paint coming out;
# the old art is art/icons-src/L1.orig.png, its cut tools/blender/cuts/L1.orig.py.txt). The paint is no longer in
# the picture: anim_L1.py tilts the can over and sprays the jet and the cloud in Grease Pencil.
# Two pieces, cut from the new art:
#   can    the body, both silver rings, the green dome and the valve stem, with their sticker border
#   cap    the cream actuator with its nozzle hole and its own sticker border (round its sides and top) - it is
#          pressed straight down onto the stem (it moves down and squashes, never up, so it uncovers nothing but
#          the empty air above it)
# The recipe's parts (tools/icon_rigs/recipes/L1.py) were measured on the old drawing: the jet and the cloud are
# dropped, and the can and the cap take the new art's own pixels (plate "upright" = art/blender/plates/
# L1_upright.png, a copy of art/icons-src/L1.png) over exactly their regions here, the rest cleared.
import os
import numpy as np
from PIL import Image
from scipy import ndimage
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_a = np.asarray(Image.open(os.path.join(ROOT, "art", "icons-src", "L1.png")).convert("RGBA")).astype(np.float32) / 255
_rgb, _al = _a[..., :3], _a[..., 3]
_yy, _xx = np.mgrid[0:1000, 0:1000]
_white = (_rgb.min(-1) > .78) & (_rgb.max(-1) - _rgb.min(-1) < .14)
# the drawing, not its sticker border (nor the thin dark line round the sticker's outer edge)
_solid = (_al > .5) & ~_white & (ndimage.distance_transform_edt(_al > .5) > 9)

STEM = (466, 530)        # x span of the valve stem (icon px)
CAP_BOTTOM = 232         # below the cap's bottom ink line (the white neck starts here) ...
STEM_TOP = 223           # ... and over the stem, where the stem's metal starts under the cap's ink
BORDER_TO = 214          # the cap owns its sticker border down to here; lower down the can's border carries on
TUCK = 4                 # px the can runs on under the cap's edge (no crack between them)

_cut = np.where((_xx >= STEM[0]) & (_xx <= STEM[1]), STEM_TOP, CAP_BOTTOM)
_cap = _solid & (_yy < _cut)
lab, n = ndimage.label(_cap)
CAP_CORE = lab == 1 + np.argmax(ndimage.sum(_cap, lab, range(1, n + 1)))       # the cap itself, one piece
CAP_CORE = ndimage.binary_fill_holes(CAP_CORE) & (_yy < _cut) & (_al > .02)     # (its pale highlights too)
CAN_CORE = _solid & ~CAP_CORE
_border = (_al > .01) & ~CAP_CORE & ~CAN_CORE
_d_cap = ndimage.distance_transform_edt(~CAP_CORE)
_d_can = ndimage.distance_transform_edt(~CAN_CORE)
CAP_BORDER = _border & (_d_cap < _d_can) & (_yy < BORDER_TO)
CAPR = CAP_CORE | CAP_BORDER
# the can: everything else, running TUCK px on under the cap's edge
_own = (_al > .01) & ~CAPR
CAN = _own | (CAPR & (ndimage.distance_transform_edt(~_own) <= TUCK))      # (not round the cap's outer edge)
_grow = lambda m, k: ndimage.binary_dilation(m, iterations=k)

DROP = ["jet", "cloud"]
FILLS = [   # each region grown 3 px: dump_parts feathers a fill's edge, so the part's own pixels come in at full strength
    {"part": "can", "region": _grow(CAN, 3).astype(np.float32), "plate": "upright"},
    {"part": "cap", "region": _grow(CAPR, 3).astype(np.float32), "plate": "upright"},
]
CLEAR = [   # and everything that is not theirs wiped (the recipe's old masks, its blur fill under the old cap)
    {"part": "can", "region": (~_grow(CAN, 1)).astype(np.float32)},
    {"part": "cap", "region": (~CAPR).astype(np.float32)},
]
