# L7 - Black hoodie: what Blender's cut changes from the rig recipe (tools/icon_rigs/recipes/L7.py).
# The hoodie is ONE image - the tag is printed on it, so it breathes, shrugs and squashes with the cloth (skinned in
# Blender: anim_L7.py weights the one mesh to a chest, shoulder and hood bone) - and the two drawstrings are the
# pieces that move on it: each one cord, from its eyelet to the tip of its aglet, bending on a chain of bones like
# H1's ropes and swinging on its own spring. The recipe's cord strips were measured on the old drawing and slice the
# redrawn cords lengthwise (the right one loses its right edge, the left its top), so each cord is cut here round
# its own outline on the new art - the braided tube, its black edge and the shadow it casts to its right (the light
# comes from the left) - from the art's own pixels (plate "art" = art/blender/plates/L7_art.png, a byte copy of
# art/icons-src/L7.png: nothing painted, it only lets FILLS put the art's pixels into a part). Under the cords the
# hoodie takes the clean plate (art/blender/plates/L7.png: the cords and their shadows taken off, the eyelets left
# as empty rings, the fabric and the grey tag painted on underneath).
PLATE_PROMPT = (
    "Remove the two drawstrings that hang down from the hood: the two braided dark cords with silver metal tips, and the "
    "dark shadows they cast on the hoodie beside them. Keep the two round silver metal eyelets on the hood where the cords "
    "came out (now empty holes). Where the cords and their shadows were, paint the hoodie's black fabric and the light grey "
    "spray-painted graffiti letters carrying on naturally underneath, with the same folds, texture and shading.")

DROP = ["string_l2", "string_r2", "logo", "under"]   # the cords' lower halves (each cord is one piece now), the tag
                                                     # (the body carries it as drawn), the recipe's repair helper

ALL = ("rect", -8, -8, 1008, 1008)
# each cord's outline, icon px, traced on the new art row by row (from the pixels' brightness: the braid, its black
# edge and its shadow end where the fabric or the light grey tag begins): down its left edge, round the aglet's tip
# (hugged tight - a light pixel kept there would ride along as a pale fringe over dark cloth), back up its right one
CORD_L = ("poly", [(385.5, 154), (385.5, 160), (386, 170), (386.5, 180), (387.5, 188), (389, 200), (392.7, 224),
                   (394.7, 248), (396.7, 272), (399.7, 296), (402, 320), (403, 332), (404, 340), (406, 360), (408, 385),
                   (408.5, 390), (410.5, 392.3), (412.5, 394.4), (414.5, 395.6), (417.5, 395.8), (420, 394.6), (422, 392.6),
                   (423, 389), (423, 385), (422, 360),
                   (423.3, 340), (422.3, 320), (421.3, 296), (418.3, 272), (416.3, 248), (414.3, 224), (412.3, 200),
                   (411.3, 188), (403.3, 180), (400.3, 170), (397.5, 160), (395, 154)])
CORD_R = ("poly", [(459, 149), (456, 153), (454, 160), (452.5, 170), (451, 180), (449.7, 190), (449.7, 206), (450.7, 224),
                   (451.7, 248), (452.7, 260), (453.7, 272), (454.7, 296), (455.7, 308), (456.7, 330), (458, 344),
                   (461, 360), (463, 385), (464, 387.5), (466.5, 389.6), (468.3, 391.2), (470.5, 392.6), (474.5, 392.6),
                   (475.8, 390.8), (476.8, 388), (477, 385), (475.5, 360),
                   (473.5, 344), (474, 330), (475.3, 308), (475.3, 290), (475.3, 272), (474.3, 248), (473.3, 224),
                   (473.3, 206), (473, 195), (468, 185), (465, 175), (464, 165), (465, 155), (463, 149)])
# the bones down each cord, root (the eyelet) first; the last bone is the aglet, which stays straight
CHAIN_L = [(390, 158), (396, 224), (402, 290), (408, 352), (414, 397)]
CHAIN_R = [(458, 155), (457, 224), (460, 290), (464, 350), (469, 393)]

# each recipe cord strip becomes a whole cord: the strip is the piece (SPLIT gives it its chain of bones), then
# it takes the art's pixels over its own outline and loses whatever the old strip had outside it
FAR = [(0, -60), (1000, -60)]                         # a cut line above the icon: the piece is the whole strip
SPLIT = {
    "string_l": [{"name": "cord_l", "side": "below", "line": FAR, "chain": CHAIN_L}],
    "string_r": [{"name": "cord_r", "side": "below", "line": FAR, "chain": CHAIN_R}],
}
FILLS = [
    {"part": "body", "region": ALL, "plate": "art"},                                        # the hoodie and its tag
    {"part": "body", "region": ("near", ("or", CORD_L, CORD_R), 3)},                         # under the cords: clean
    {"part": "cord_l", "region": ("near", CORD_L, 2), "plate": "art"},
    {"part": "cord_r", "region": ("near", CORD_R, 2), "plate": "art"},
]
CLEAR = [   # cut back to just inside each outline, so the cut's soft edge falls on the cord's own black edge (cut on
            # the line itself, it carried a pale rim of the shadow and tag round it that showed over dark cloth)
    {"part": "cord_l", "region": ("minus", ALL, ("shrink", CORD_L, 1))},
    {"part": "cord_r", "region": ("minus", ALL, ("shrink", CORD_R, 1))},
]
