# L3 - Beanie: what Blender's cut changes from the rig recipe (tools/icon_rigs/recipes/L3.py).
# The SMK logo pops off the cuff, wobbles and squashes, so the cuff under it is the clean plate's plain ribbed knit
# (the recipe kept a frozen copy of the logo there, under the moving one). The recipe's logo mask was read off the
# old drawing; on the new art the logo's black outline pokes past it in places (it would stay on the cuff as a
# ghost when the logo lifts), so the logo is found again on the new art here - its white letters and the black
# outline round them - and takes the art's own pixels from the "art" plate (the icon itself through
# tools/blender/plate.py --fit-only: a copy of art/icons-src/L3.png as art/blender/plates/L3_art_raw.png, no
# generation, the fit is the identity). The crown is soft knit that flops: its mesh is held by the cuff at its
# foot (below y 330 - the seam and everything under the cuff's edge) and by its own bone higher up (above y 150),
# blended between, so it bends over like a soft hat while its seam never opens.
import os, sys
import numpy as np
from PIL import Image
from scipy import ndimage
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, "tools", "icon_rigs"))
sys.path.insert(0, os.path.join(ROOT, "tools", "icon_rigs", "recipes"))
from L3 import LOGO, CROWN      # noqa: E402

PLATE_PROMPT = (
    "1. Remove the white graffiti 'SMK' logo and its thick black outline from the folded cuff of the grey beanie. "
    "Paint plain grey knitted cuff there instead: the same vertical knit ribs running straight down through where the "
    "logo was, the same fine knit texture and the same soft shading carrying on naturally, so the cuff looks as if it "
    "never had a logo.")


def _logo():
    """The logo on the new art: its white letters (pieces of 150 px and more) and the black outline within 15 px
    of them, every pocket inside filled, off the cuff's top seam (the recipe's crown band), grown 2 px for its
    soft edge."""
    import rigkit
    from build import load_recipe
    cv = rigkit.Rig(load_recipe(os.path.join(ROOT, "tools", "icon_rigs", "recipes", "L3.py"))).cv
    src = np.asarray(Image.open(os.path.join(ROOT, "art", "icons-src", "L3.png")).convert("RGBA")).astype(np.float32) / 255
    rgb, al = src[..., :3], src[..., 3]
    box = np.zeros(al.shape, bool); box[345:690, 262:780] = True
    white = box & (rgb.min(-1) > .80) & (rgb.max(-1) - rgb.min(-1) < .12) & (al > .5)
    dark = (rgb.max(-1) < .30) & (al > .5)
    lab, n = ndimage.label(white)
    keep = []
    for i in range(1, n + 1):                 # a letter is ringed in black ink; the knit's bright fold is not
        piece = lab == i
        if piece.sum() < 150:
            continue
        ringpx = ndimage.binary_dilation(piece, iterations=3) & ~piece
        if dark[ringpx].mean() > .55:
            keep.append(i)
    white = np.isin(lab, keep)
    ink = box & (rgb.max(-1) < .30) & (al > .5) & (ndimage.distance_transform_edt(~white) <= 15)
    crown = cv.eval(CROWN) > .5
    m = ndimage.binary_opening(ndimage.binary_fill_holes(white | ink), iterations=1) & ~crown
    lab, n = ndimage.label(m)
    m = np.isin(lab, np.unique(lab[white & m]))                 # only what holds letters
    return ndimage.binary_dilation(m, iterations=2) & ~crown, cv.eval(LOGO) > .5


NEW_LOGO, OLD_LOGO = _logo()
FILLS = [
    {"part": "logo", "region": NEW_LOGO.astype(np.float32), "plate": "art"},
    # the cuff under the logo: plain knit from the plate, colour-matched to the cuff round it - exactly the logo's own
    # area, so at rest the logo hides every patched pixel (past it, the cuff's dark rib seams run up to the logo)
    {"part": "cuff", "region": NEW_LOGO.astype(np.float32), "blend": "matched"},
]
CLEAR = [   # the old mask's fringe of knit past the logo's edge: the cuff owns that
    {"part": "logo", "region": (~ndimage.binary_dilation(NEW_LOGO, iterations=1)).astype(np.float32)},
]
ANCHOR = {"crown": {"bone": "cuff", "y0": 330, "y1": 150}}
