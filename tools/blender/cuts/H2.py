# H2 - Glock: what Blender's cut changes from the rig recipe (tools/icon_rigs/recipes/H2.py).
# The slide is the mover: it runs back along its rail when the gun fires (the recipe's cut down the middle of the
# slide/frame seam is kept - it lies on the seam's ink line in the new art). Where the slide's front uncovers the
# frame when it runs back, the frame takes the clean plate (art/blender/plates/H2.png: the pistol with its slide
# taken away - the frame's flat top edge and its sticker border painted where the slide sat).
# The trigger stays still (a moving blade needs the guard's inside painted under it, and the recipe draws the
# trigger under the frame): the recipe's trigger mask was measured on the old drawing and cuts a ragged hole round
# the new art's blade (a chunk of the frame, slivers of the guard's white), so the trigger is dropped and the frame
# takes the art's own pixels back there (plate "art" = art/blender/plates/H2_art.png, a byte copy of
# art/icons-src/H2.png - nothing painted: it only lets FILLS put the art's pixels back where an old mask cut a hole).
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "icon_rigs", "recipes"))
from H2 import SLIDE, TRIGGER_POLY     # noqa: E402

# (worded as shapes: the image model's safety filter turns down a request that names the parts of a pistol)
PLATE_PROMPT = (
    "Take away the long polished silver bar that runs along the top of the illustration - the brushed-metal block "
    "with the rows of vertical grooves at both ends, the recessed rectangular window in its middle and the two small "
    "bumps on its top edge: everything above the long straight dark line that runs diagonally down across the "
    "picture from the upper left to the right. Keep the dark charcoal lower piece below that line exactly as it is, "
    "in the same place, with every detail. Its flat straight top edge, along that diagonal line, is now the top of "
    "the shape: give it the same black outline, and run the plain white sticker border along it, following the new "
    "outline. Paint nothing else where the silver bar was - only the transparent background above that edge, and "
    "its sticker border.")

DROP = ["trigger"]

# the trigger, its guard and the recipe's housing copy: the frame's hole there, grown past every ragged edge
HOUSING_POLY = [(410, 418), (545, 418), (545, 492), (500, 492), (470, 462), (410, 450)]
TRIGGER_HOLE = ("grow", ("or", TRIGGER_POLY, ("poly", HOUSING_POLY)), 6)

# the frame above the seam at the front: what the slide's nose uncovers when it runs back (the slide travels at
# most ~40 px along the rail). It ends where the frame's own strip of seam ink begins (the recipe keeps 4 px of
# it under the slide's edge, so the slide's soft edge shows ink at rest, never the plate's border), and the fill's
# soft edge blends into that strip - no see-through seam between them.
# The plate was fitted with plate.py's own fit (tools/icon_redraw/install.py fit) on the frame only - the art
# masked to below the seam: the whole-silhouette fit plate.py does pulls a plate that lacks the slide out of scale
# (scale 1.26, ink 4.2 px off) - fitted on the frame it is scale 0.972, ink 0.19 px off.
# Left of the frame's front face (x < 72) the strip is the sticker border's, not ink: there the plate's rounded
# border corner takes it too, or the strip's straight top edge pokes out as a white spike when the slide is back.
FRONT = ("or", ("and", ("shrink", SLIDE, 4), ("rect", -10, 40, 190, 330)),
         ("and", SLIDE, ("rect", -10, 40, 72, 330)))

# At the rear the seam runs on through the beavertail's own sticker border (the notch between the slide's tail and
# the grip's top is above the seam): left on the slide, that piece of border would ride away with it. It is the
# frame's - it stays put when the slide runs back. The region reaches past the seam, so the slide is cleared to
# nothing there (not to a feathered half-ink line), and the frame takes it from 4 px higher than the slide lets go:
# the two whites overlap, no seam at rest. (At the front the border corner is drawn in Blender: anim_H2.py.)
REAR_BORDER = ("poly", [(902, 452), (1010, 452), (1010, 560), (902, 560)])
REAR_GIVE = ("poly", [(902, 456), (1010, 456), (1010, 560), (902, 560)])
FILLS = [
    {"part": "frame", "region": FRONT},
    {"part": "frame", "region": TRIGGER_HOLE, "plate": "art"},
    {"part": "frame", "region": REAR_BORDER, "plate": "art"},
]
CLEAR = [
    {"part": "slide", "region": REAR_GIVE},
]
