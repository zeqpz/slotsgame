# M - the Multi booster (a chunk of brick wall; the game paints the multiplier value over it): what Blender's cut
# changes from the rig recipe (tools/icon_rigs/recipes/M.py). The recipe's parts stay as they are - the two halves
# either side of the stepped crack down the mortar, the three loose corner bricks - so the cut only makes them
# meet without hairlines and gives the crack a torn sticker edge:
#   - the half behind (left) runs on 5 px under the half in front (right) all down the crack, and both halves run
#     4 px under the loose bricks along the edges where the bricks sit on them. Those strips are the art's own
#     pixels (mortar and ink), so when the halves part or a brick tips up the edge is mortar / ink, never a gap.
#   - where the crack runs through the white sticker border at the top, it tears along a zigzag, not a ruler line.
# Nothing a part uncovers is painted: a brick tipping up or the crack opening shows the wall's dark inside, which
# anim_M.py puts behind the parts (the "cavity", made in Blender). So no clean plate: the strips come from
# art/blender/plates/M_art.png, which is the art itself (a copy of art/icons-src/M.png, made here when it is
# missing) - FILLS can only take pixels from a plate.
import os, shutil, sys
import numpy as np
from PIL import Image
from scipy import ndimage

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
sys.path.insert(0, os.path.join(_ROOT, "tools", "icon_rigs", "recipes"))
sys.path.insert(0, os.path.join(_ROOT, "tools", "icon_rigs"))
import rigkit                     # noqa: E402
from M import LEFT               # noqa: E402

_ART = os.path.join(_ROOT, "art", "icons-src", "M.png")
_COPY = os.path.join(_ROOT, "art", "blender", "plates", "M_art.png")
if not os.path.exists(_COPY):
    os.makedirs(os.path.dirname(_COPY), exist_ok=True)
    shutil.copyfile(_ART, _COPY)

_art = Image.open(_ART).convert("RGBA")
W, H = _art.size
_alpha = np.asarray(_art)[..., 3] > 0
yy, xx = np.mgrid[0:H, 0:W]

# the recipe's halves (its LEFT polygon, binary like its "cc" mask) and its loose bricks (plain rectangles)
L = rigkit.Canvas(_art).poly(LEFT) > .5
BRICKS = {"brick_tl": (136, 104, 309, 247, "left"), "brick_tr": (688, 104, 882, 250, "right"),
          "brick_bl": (136, 800, 290, 935, "left")}
rect = {k: (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1) for k, (x0, y0, x1, y1, _) in BRICKS.items()}
any_brick = np.zeros((H, W), bool)
for r in rect.values():
    any_brick |= r

# the torn top: the crack's first run (x 507) zigzags through the sticker border instead of running straight
ZIG = [(507, 92)] + [(507 + (5 if i % 2 else -5), 100 + 8 * i) for i in range(7)] + [(507, 156)]
_zx = np.interp(np.arange(H), [y for _, y in ZIG], [x for x, _ in ZIG])        # the tear's x per row
newL = L.copy()
_band = (yy >= ZIG[0][1]) & (yy <= ZIG[-1][1])
newL[_band] = (xx < _zx[:, None])[_band]
to_left = newL & ~L & ~any_brick & _alpha          # right -> left along the tear
to_right = L & ~newL & ~any_brick & _alpha         # left -> right

# the half behind runs 5 px on under the half in front, all down the crack
R = ~newL
tuck = R & (ndimage.distance_transform_edt(R) <= 5.5) & ~any_brick & _alpha
# (every region is carried 4 px out into the transparent air round it: fills and clears are feathered at their
# edges, and out there the fall-off touches nothing - no thinned edge, no ghost of a neighbour's edge)
_air = lambda r: r | (ndimage.binary_dilation(r, iterations=4) & ~_alpha)
FILLS = [
    {"part": "left", "region": _air(to_left | tuck), "plate": "art"},
    {"part": "right", "region": _air(to_right), "plate": "art"},
]
CLEAR = [
    {"part": "left", "region": _air(to_right & ~tuck)},
    {"part": "right", "region": _air(to_left)},
]
# each half runs 4 px on under the loose bricks that sit on it (the bricks' inner edges: where the rectangle borders
# the wall, not the air)
for _name, (_x0, _y0, _x1, _y1, _half) in BRICKS.items():
    _inner = rect[_name] & (ndimage.distance_transform_edt(rect[_name]) <= 4.5)
    _area = newL if _half == "left" else ~newL
    _near = ndimage.binary_dilation(_area & ~rect[_name] & _alpha, iterations=6)
    FILLS.append({"part": _half, "region": _air(_inner & _near & _alpha), "plate": "art"})
