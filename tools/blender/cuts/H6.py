# H6 - Skateboard seen from underneath: what Blender's cut changes from the rig recipe (tools/icon_rigs/recipes/H6.py).
# The recipe's truck outlines were measured on the old drawing (they take slivers of the deck's paint along with
# the redrawn trucks), and its deck hangs off a helper sprite ("flip") that the Blender cut leaves out, so this cut
# re-cuts the art itself when tools/blender/dump_parts.py runs it (recut(), below):
#   deck      the board, with the clean plate (art/blender/plates/H6.png: the deck without its trucks - the blue
#             paint, the yellow lettering and the scuffs carried on underneath) laid in exactly where a truck lies
#             over it, so a truck can steer, give and spring off it and only real deck shows
#   truck_f   the front truck: baseplate, hanger, axle and both wheels, and the sticker border round the wheel that
#   truck_b   sticks out past the deck - each steers about its kingpin
# A truck's pixels: inside a hand outline round the hardware, wherever the art is not the deck's own paint (the
# plate shows the deck there) - so no graffiti rides along with a truck - plus the bulge its wheel puts in the
# sticker's outline (the art's pixels outside the plate's outline).
import os, sys
import numpy as np

PLATE_PROMPT = (
    "1. Remove both skateboard trucks completely - the two metal baseplates, hangers and axles - together with all four "
    "cream wheels.\n"
    "2. Paint the underside of the deck where they were, in the same style: the same bright blue paint with its "
    "darker blue spots, the yellow graffiti lettering carrying on naturally underneath, the same scuffs, scratches and "
    "worn black patches, and the wooden edge of the deck. The plain white sticker border follows the deck's own "
    "outline where the wheels used to stick out past it.")

CENTER = (484, 487)          # the middle of the deck (its centroid): it flips about its long axis through here
KING_F = (330, 432)          # where each hanger meets its baseplate: the truck steers about here
KING_B = (676, 806)
# generous hand outlines round each truck (icon px; straight edges): the cut keeps only the truck's own pixels
TRUCK_F = [(272, 352), (300, 330), (338, 338), (390, 368), (440, 404), (452, 440), (476, 462), (494, 500), (492, 536),
           (476, 566), (446, 584), (404, 582), (372, 562), (356, 520), (330, 508), (262, 494), (234, 494), (214, 518),
           (184, 534), (150, 532), (124, 512), (114, 478), (118, 440), (133, 404), (160, 385), (205, 379), (241, 385),
           (263, 404), (273, 422), (282, 396)]
TRUCK_B = [(622, 712), (650, 690), (690, 700), (735, 724), (760, 760), (766, 800), (780, 812), (806, 830), (818, 868),
           (810, 906), (786, 928), (746, 932), (712, 912), (700, 884), (660, 872), (606, 860), (590, 876), (556, 884),
           (520, 876), (494, 850), (488, 808), (498, 772), (524, 751), (565, 746), (597, 758), (614, 782), (616, 760)]
BULGE_F = (90, 330, 520, 620)
BULGE_B = (470, 700, 860, 960)


def shape(pts, W, H, ss=4):
    from PIL import Image, ImageDraw
    big = Image.new("L", (W * ss, H * ss), 0)
    ImageDraw.Draw(big).polygon([(x * ss, y * ss) for x, y in pts], fill=255)
    return np.asarray(big.resize((W, H), Image.BOX), np.float32) / 255 > .5


def recut(m):
    """Run inside tools/blender/dump_parts.py (m = its module): replace the recipe's parts with this cut."""
    from PIL import Image
    from scipy import ndimage
    W, H = m.W, m.H
    src = np.asarray(m.rig.src.convert("RGBA")).astype(np.float32) / 255
    art = m.premul(m.rig.src)
    plate = m.premul(Image.open(os.path.join(m.ROOT, "art", "blender", "plates", "H6.png")))
    yy, xx = np.mgrid[0:H, 0:W]
    rgb = src[..., :3]
    sat = rgb.max(-1) - rgb.min(-1)
    # the deck's own paint: the saturated blues and yellows, and the bare wood of its edge (the trucks are steel,
    # black and cream; their rust specks are too small to survive the opening)
    blue = (rgb[..., 2] > rgb[..., 0] + .18) & (sat > .28)
    yellow = (rgb[..., 0] > .6) & (rgb[..., 1] > .5) & (rgb[..., 2] < .5) & (sat > .3)
    wood = (rgb[..., 0] - rgb[..., 2] > .3) & (sat > .32) & (rgb[..., 0] > rgb[..., 1]) & (rgb[..., 1] > rgb[..., 2])   # (the cream
    #                                                                     wheels stay under .25 of colour)
    paint = ndimage.binary_opening(blue | yellow | wood, iterations=1)
    differs = ndimage.gaussian_filter(np.abs(art - plate).max(-1), 1.0) > .12

    def truck(poly, box, king):
        x0, y0, x1, y1 = box
        inside = shape(poly, W, H)
        own = inside & ~paint & (differs | (sat < .2))
        own = ndimage.binary_closing(own, iterations=3) & inside
        own = ndimage.binary_fill_holes(own) & inside & ~paint
        lab, n = ndimage.label(own)
        own = lab == lab[king[1], king[0]]
        out = (art[..., 3] > .01) & (plate[..., 3] < .5) & (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
        bulge = ndimage.binary_opening(out, iterations=3)
        both = own | bulge
        lab, n = ndimage.label(both)
        both = lab == lab[king[1], king[0]]
        both |= out & ndimage.binary_dilation(both, iterations=8)   # the thin ends of the wheel's border too,
        # and the fillets where the sticker border bridges from the wheel to the deck's edge (well outside the
        # plate's outline - not the px-thin slivers where the plate draws the deck's edge a hair inside the art's)
        far_out = out & (ndimage.distance_transform_edt(plate[..., 3] < .5) > 2.5)
        both |= far_out & ndimage.binary_dilation(both, iterations=22)
        both = ndimage.binary_fill_holes(both) & ~(paint & ~both)
        return ndimage.binary_dilation(both, iterations=1) & (art[..., 3] > .01) & ~(paint & ~both)
    tf, tb = truck(TRUCK_F, BULGE_F, KING_F), truck(TRUCK_B, BULGE_B, KING_B)
    trucks = tf | tb
    m.full.clear(); m.meta.clear()
    deck = np.where(trucks[..., None], plate, art)              # the plate exactly where a truck lies over it
    # where a wheel's sticker border joins the deck's, the two borders make one white corner; under the truck the
    # deck's border is grown 6 px (hidden at rest), so a wheel steering off the corner never pinches open a
    # hairline of background between the two borders
    pa = plate[..., 3] > .5
    web = ndimage.binary_dilation(pa, iterations=6) & ~pa & trucks & (art[..., 3] > .98)
    w = (m.feather(web.astype(np.float32), 1.0) * web)[..., None]
    white = np.array([.97, .97, .98, 1.0], np.float32)
    m.full["deck"] = deck + white * w * (1 - deck[..., 3:4])     # white laid behind the deck's own edge
    m.full["truck_f"] = art * tf[..., None]
    m.full["truck_b"] = art * tb[..., None]
    m.meta.update({
        "deck": {"pivot": CENTER, "parent": None, "hidden": False},
        "truck_f": {"pivot": KING_F, "parent": "deck", "hidden": False},
        "truck_b": {"pivot": KING_B, "parent": "deck", "hidden": False},
    })
    m.draw[:] = ["deck", "truck_f", "truck_b"]
    print(f"   H6 re-cut: deck (plate under the trucks) + truck_f ({int(tf.sum())} px) + truck_b ({int(tb.sum())} px)")


_m = sys.modules.get("__main__")
if _m is not None and hasattr(_m, "full") and hasattr(_m, "meta") and getattr(_m, "sid", None) == "H6":
    recut(_m)
