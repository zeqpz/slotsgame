# L6 - Camo t-shirt: what Blender's cut changes from the rig recipe (tools/icon_rigs/recipes/L6.py).
# The shirt is ONE image: its sleeves flutter, its hem billows and its body sways and puffs by skinning in Blender
# (anim_L6.py lays bone chains down the sleeves and a row of flaps along the hem, and weights the one mesh to them,
# blended across the armholes), so cloth never cracks at a seam and nothing moving uncovers anything. The recipe's
# body was measured on the old drawing and lost half the white sticker border along the shoulders, so the body
# takes the art's own pixels everywhere (plate "art" = art/blender/plates/L6_art.png, a byte copy of
# art/icons-src/L6.png - nothing painted: it only lets FILLS put the art's pixels into a part), and the separate
# sleeve and hem copies are dropped.
# The logo is the one piece that moves on the cloth (it pops, squashes and wobbles), cut exactly round its white
# outline on the new art; under it the shirt takes the clean plate (art/blender/plates/L6.png: the shirt with the
# tag taken off and the camo painted on), colour-matched to the camo round it.
PLATE_PROMPT = (
    "Remove the graffiti logo from the front of the t-shirt: the dark brown 'Smukiez' tag lettering with its thick white "
    "outline, and the long white-outlined drip that hangs down from it to the middle of the shirt. Paint the shirt's "
    "camouflage there instead: the same paint-splatter camo (khaki, olive green, brown and dark brown splats with small "
    "specks), the same fabric shading and soft folds, carrying on naturally across where the logo was. Keep the collar, "
    "the sleeves, the hem and the white sticker border round the shirt exactly as they are.")

DROP = ["sleeve_l", "sleeve_r", "hem"]          # the sleeves and the hem are the body's own pixels, bent by skinning

ALL = ("rect", -8, -8, 1008, 1008)
# the tag: its white outline on the new art (the piece of white round the drip's foot) with all it encloses
LOGO_SHAPE = ("fill", ("cc", ("art", ("color", "#ffffff", 80)), 444, 640))
FILLS = [
    {"part": "body", "region": ALL, "plate": "art"},                                   # the whole shirt, as drawn
    {"part": "body", "region": ("near", LOGO_SHAPE, 3), "blend": "matched"},           # under the tag: clean camo
    {"part": "logo", "region": ("near", LOGO_SHAPE, 3), "plate": "art"},              # the tag, as drawn
]
CLEAR = [   # the tag cut back to its own outline (and the outline's soft outer pixel): no camo rides along with it
    {"part": "logo", "region": ("minus", ALL, ("near", LOGO_SHAPE, 1))},
]
