# H5 - Boombox: what Blender's cut changes from the rig recipe (tools/icon_rigs/recipes/H5.py).
# The recipe was measured on the old flat drawing: its key rectangles, handle polygon and speaker discs miss the new
# art (bits of the handle in the keys, the speakers' chrome rings left on the box, a blur under the cones). Blender
# moves the boombox by bending meshes, so nothing it does ever uncovers anything and H5 needs no clean plate:
#   handle  everything above the lid's top ink line - the carry handle and its two posts, the inner rail, the dark
#           slot with the piano keys and the three round keys, the sticker border over them - running 8 px on under
#           the lid (the box is drawn over it). anim_H5.py weights it to bones: the handle bar bounces on its posts,
#           every key presses down on its own (the slot above it stretches, its foot slides in behind the lid), the
#           slot and the posts' feet stay on the box
#   body    the box below that line, the speakers' own pixels kept under them (a speaker only ever swells over them)
#   spk_l, spk_r  each speaker whole - chrome ring, its outer ink, the grille - fitted ellipses 3 px past the ring's
#           outer ink; anim_H5.py bends the cone in the middle (it pumps) while the ring holds
#   key1..3 dropped: the keys live in the handle's mesh now
# The re-cut takes the art's own pixels through the plate "art" (art/blender/plates/H5_art.png, a byte copy of
# art/icons-src/H5.png - nothing painted).

# the lid's top ink line, left to right (icon px): the middle of the black line the keys stand on
LID = [(-10, 252), (60, 252), (95, 257), (120, 260), (200, 260), (300, 257.5), (400, 256.5), (500, 256), (600, 259.5),
       (700, 260.5), (820, 262), (880, 265), (1010, 266)]
TUCK = 8
ABOVE = ("poly", [(-10, -10), (1010, -10)] + [(x, y + TUCK) for x, y in reversed(LID)])
BELOW = ("poly", LID + [(1010, 1010), (-10, 1010)])
LID_UP = ("poly", [(-10, -10), (1010, -10)] + list(reversed(LID)))
UNDER_TUCK = ("poly", [(x, y + TUCK) for x, y in LID] + [(1010, 1010), (-10, 1010)])

# the speakers: ellipses fitted to the chrome rings' outer ink (cv2.fitEllipse), 3 px out
SPK_L = (165.7, 565.4, 120.1, 152.6, -3.5)
SPK_R = (712.2, 624.8, 159.5, 174.5, -6.8)


def ring(e, grow):
    cx, cy, rx, ry, deg = e
    return ("ellipse", cx, cy, rx + grow, ry + grow, deg)


EVERYTHING = ("rect", -10, -10, 1010, 1010)
DROP = ["key1", "key2", "key3"]
FILLS = [
    {"part": "handle", "region": ABOVE, "plate": "art"},
    {"part": "body", "region": BELOW, "plate": "art"},
    {"part": "spk_l", "region": ring(SPK_L, 3), "plate": "art"},
    {"part": "spk_r", "region": ring(SPK_R, 3), "plate": "art"},
]
CLEAR = [
    {"part": "handle", "region": UNDER_TUCK},
    {"part": "body", "region": LID_UP},
    {"part": "spk_l", "region": ("minus", EVERYTHING, ring(SPK_L, 3))},
    {"part": "spk_r", "region": ("minus", EVERYTHING, ring(SPK_R, 3))},
]
