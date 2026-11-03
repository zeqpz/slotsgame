# L2 - Graffiti marker: what Blender's cut changes from the rig recipe (tools/icon_rigs/recipes/L2.py).
# The orange line is the marker's own stroke: it is cut into twelve slices in the order it was drawn (recipe), and
# anim_L2.py writes it back on in Blender, pixel by pixel along that order. The marker scribbles over the line, so
# the line runs on unbroken under it: each slice takes the clean plate's line (the line with the marker taken
# away and its passes joined up) wherever the marker covers its stretch of the path.
# Seams: the recipe's slices reach 8 px back along the path under the one before, but where the scribble folds back
# on itself two slices also meet side by side, edge to edge - and Blender's texture filtering softens both cut
# edges into a see-through hairline there (seen at rest). So every slice reaches 3 px under its neighbours all
# round: the art's own pixels (the "art" plate: the icon itself through tools/blender/plate.py --fit-only, a copy of
# art/icons-src/L2.png as art/blender/plates/L2_art_raw.png, the fit the identity) where the line shows, the clean
# plate's line under the marker. The slices never move apart (they only appear), so the overlap never shows.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "icon_rigs", "recipes"))
from L2 import PEN, STROKE, PATH, N, SLICES, BACK      # noqa: E402

PLATE_PROMPT = (
    "1. Remove the black graffiti marker completely: its black body with the white tag lettering, its cap, its orange "
    "tip and the marker's own white sticker border. Nothing of the marker is left.\n"
    "2. The orange scribbled line that was behind the marker carries on unbroken where the marker covered it: the same "
    "zigzag passes joined up naturally, the same thickness, the same bright orange spray-paint texture with its speckled "
    "edges, and the same plain white sticker border running along the line's own edges. Where there was only marker and "
    "no line behind it, leave it fully transparent.")

UNDER = ("and", PEN, ("hard", ("opaque",), .98))     # exactly what the marker covers, opaque (on the new art)
SOLID = ("hard", ("opaque",), .98)                    # inside the line: its soft outer edge is never doubled up


def _span(i):
    return max(0, i / N - BACK), (i + 1) / N


FILLS = []
for _i, _s in enumerate(SLICES):
    _t0, _t1 = _span(_i)
    FILLS += [
        # the line under the marker, from the clean plate - reaching 3 px under the neighbouring slices
        {"part": _s, "region": ("art", ("and", ("grow", ("along", UNDER, PATH, _t0, _t1), 3), UNDER))},
        # the line where it shows, its own pixels - reaching 3 px under the neighbouring slices
        {"part": _s, "region": ("art", ("and", ("grow", ("along", STROKE, PATH, _t0, _t1), 3), STROKE, SOLID)), "plate": "art"},
    ]
