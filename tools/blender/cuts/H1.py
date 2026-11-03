# H1 - Bag of cash: what Blender's cut changes from the rig recipe (tools/icon_rigs/recipes/H1.py).
# The two loose rope ends are cut apart, each its own bendy piece with its own ink edge and sticker border, so
# they can swing separately. What they and the $ cover is painted from the clean plate (tools/blender/plate.py):
# the sack's neck, its left side, the gathered top's flap and the sticker border round them, plain cloth under
# the $. The recipe's blur fill and the ghost of the ropes' border left on the sack are gone.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "icon_rigs", "recipes"))
from H1 import TAILS, DOLLAR     # noqa: E402

PLATE_PROMPT = (
    "1. Remove the two loose rope ends that stick out to the left of the tie. The brown rope still wraps tightly round the "
    "neck of the sack, the same coils, but nothing hangs out of it. Where the loose ends were, paint what was behind them: "
    "the gathered cloth of the sack's top above the tie, the sack's pinched neck and its left side below the tie, in the "
    "same style and shading, with the plain white sticker border following the sack's own outline there.\n"
    "2. Remove the green dollar sign printed on the front of the sack. Paint plain sack cloth there instead, with the same "
    "burlap weave, the same folds and the same shading carrying on naturally across where it was.")

DROP = ["knot_patch"]            # the recipe's blur patch: the plate paints that spot now

# the rope ends' pixels split along the gap / the ink between them (icon px, left to right); the upper rope lies
# over the lower one where they meet, so the lower one gets a new ink edge along its top there. Each piece's
# sticker border is its own "rim" part, drawn behind both ropes: at rest the two rims make the art's border, and
# when the ropes part each keeps a whole border of its own.
DIVIDER = [(90, 420), (254, 396), (266, 391), (278, 386), (290, 381), (302, 383), (320, 385), (345, 386), (380, 384)]
SPLIT = {"tails": [
    {"name": "rope_lo", "side": "below", "line": DIVIDER, "rim": True, "tuck": 5,
     "chain": [(348, 391), (290, 413), (234, 466), (138, 490)],
     "ink": [(299, 378), (306, 379), (322, 381), (352, 382)]},       # just under the upper rope: hidden at rest
    {"name": "rope_up", "side": "above", "line": DIVIDER, "rim": True,
     "chain": [(364, 362), (290, 354), (218, 353), (132, 372)]},
]}

# where a part takes the plate's pixels: the rope ends' area, split at the tie's top edge - the flap above goes to
# the top, the neck, knot and side below to the body (just past the area: outside it the art's own outline stays);
# under the $ the plate's cloth is matched to the sack's own light round it
TIE_TOP = 345
FILLS = [
    {"part": "top", "region": ("grow", TAILS, 2), "above": TIE_TOP, "left": 372},
    {"part": "body", "region": ("grow", TAILS, 5), "below": TIE_TOP, "left": 372},   # past the recipe's blur hole
    # the $ grown past its outline, and the ink at the tips of its counters (thin enough to slip the grow)
    {"part": "body", "region": ("or", ("grow", DOLLAR, 8), ("grow", ("and", ("fill", ("grow", DOLLAR, 8)), ("art", ("ink",))), 4)),
     "blend": "matched"},
]
CLEAR = [   # the recipe's blur fill left on the sack above the tie, where the top owns the spot
    {"part": "body", "region": ("grow", TAILS, 2), "above": TIE_TOP, "left": 372},
    # the tie is a copy laid over everything: cut it back to its own coil ends (their ink kept), so it carries
    # no frozen copy of the ropes' roots - the ropes run in under the coils and stay whole when they swing
    {"part": "band", "region": ("poly", [(300, 290), (382, 290), (376, 334), (368, 340), (362, 346), (359, 355), (359, 366),
                                         (361, 373), (363, 378), (355, 381), (347, 385), (341, 390), (338, 397), (338, 405),
                                         (341, 411), (348, 414), (352, 416), (349, 421), (348, 427), (350, 433), (356, 438),
                                         (362, 442), (362, 470), (300, 470)])},
    # the ropes' border the recipe's cut left on the sack and the top, out in the air: wherever the plate is
    # empty at least 4 px from its sack (so the sack's own outline is never touched)
    {"part": "body", "region": ("grow", TAILS, 20), "plate_clear": 4},
    {"part": "top", "region": ("grow", TAILS, 20), "plate_clear": 4},
]
# the gathered top flops above the tie but its foot stays held in it: its mesh is weighted to the band below y 350,
# to its own bone above y 285, blended between
ANCHOR = {"top": {"bone": "band", "y0": 350, "y1": 285}}
