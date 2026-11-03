# H7 - Limited drop box: what Blender's cut changes from the rig recipe (tools/icon_rigs/recipes/H7.py).
# The recipe's flap outlines were measured on the old drawing (the redrawn flaps are bigger and higher) and its flaps
# hang off helper sprites the Blender cut leaves out, so this cut re-cuts the art itself when
# tools/blender/dump_parts.py runs it (recut(), below). Five parts:
#   body      the box: its walls with the LIMITED tag, the inside seen through the opening, the sticker border round
#             the walls
#   flap_fl   the big front flaps, folded open over the front walls: each folds about its hinge (the wall's top edge)
#   flap_r    - a chain of one bone from the hinge's middle to the free edge's (Blender keys the fold)
#   flap_bl   the two flaps standing at the back, each with the sticker border above it, folding about their own
#   flap_br   hinges (the back rims)
# What the front flaps hide comes from the plate art/blender/plates/H7_back.png (the box with its front flaps gone:
# the back flaps whole, the inside, the rims - tools/blender/plate.py H7 back): under a front flap, the part of a
# back flap the plate shows there goes into that back flap (so it is whole when the front flap folds away), the
# rest into the body. Every switch between the art and the plate is exact (binary): the parts laid together are the
# art. (The main plate art/blender/plates/H7.png - no flaps at all - came back with taller walls, so it is not used.)
import os, sys
import numpy as np

PLATE_PROMPT = (
    "1. Remove all four flaps of the cardboard box: the two big flaps folded open at the front (front-left and "
    "front-right) and the two flaps standing up at the back.\n"
    "2. Show the box open at the top with no flaps at all: the cut top edges of its four walls form the rim, with the "
    "corrugated cardboard showing along the edges, and through the opening we see the inside of the box - the inner "
    "faces of the back walls in soft shadow and the dark floor - in the same grey cardboard texture, style and "
    "lighting. The LIMITED graffiti and the front walls stay exactly as they are.\n"
    "3. The sticker border (white, with its thin silver chrome inner edge) follows the box's new outline round the "
    "top rim.")
PLATES = {"back": (
    "1. Remove only the two FRONT flaps of the cardboard box - the big flap folded open over the front-left wall and "
    "the big flap folded open over the front-right wall.\n"
    "2. Keep the two flaps standing up at the back of the box exactly as they are, and paint the parts of them the "
    "front flaps were hiding, so both back flaps are whole: their full shape, their corrugated top edges and the "
    "same grey cardboard texture. Through the opening show the inside of the box - the inner walls in soft shadow "
    "and the dark floor - and the cut top edges of the front walls forming the rim.\n"
    "3. The sticker border (white, with its thin silver chrome inner edge) follows the new outline.")}

BASE = (580, 836)            # the bottom front corner: the box squashes and hops from here
# the front flaps (icon px, clockwise): the free edge (the top of its corrugated strip, a few px out), the edge
# down the V of the opening, the hinge (the wall's top edge), and the end at the sticker's outline
FL = [(50, 231), (100, 242), (150, 253), (200, 264), (250, 275), (300, 287), (350, 300), (400, 312), (450, 324), (490, 331),
      (536, 420), (578, 507), (450, 474), (310, 435), (220, 409), (137, 385), (123, 388)]
R = [(940, 260), (880, 279), (820, 298), (760, 317), (695, 338), (640, 420), (576, 507), (700, 466), (839, 420), (890, 345)]
# their hinges and free edges (the fold keeps the hinge put and moves the free edge along the flap)
FL_HINGE, FL_TIP = ((137, 386), (572, 511)), ((55, 236), (489, 332))
R_HINGE, R_TIP = ((579, 506), (838, 421)), ((697, 339), (937, 262))
# the back flaps: the hinge lines where they stand on the box (as the plate draws them whole), the split between
# them up through the V of the sticker, and their free edges
BL_HINGE, BL_TIP = ((132, 362), (400, 296)), ((64, 209), (390, 183))
BR_HINGE, BR_TIP = ((395, 296), (826, 415)), ((430, 180), (886, 235))
V_X = 396                    # the V between the back flaps


def mid(seg):
    return ((seg[0][0] + seg[1][0]) / 2, (seg[0][1] + seg[1][1]) / 2)


def chain(hinge, tip):
    return [mid(hinge), mid(tip)]


def shape(pts, W, H, ss=4):
    from PIL import Image, ImageDraw
    big = Image.new("L", (W * ss, H * ss), 0)
    ImageDraw.Draw(big).polygon([(x * ss, y * ss) for x, y in pts], fill=255)
    return np.asarray(big.resize((W, H), Image.BOX), np.float32) / 255 > .5


def above(line, W, H):
    """Pixels above the straight line through two points (y less than the line's y at that x), across the image."""
    (x0, y0), (x1, y1) = line
    xx = np.arange(W)
    yl = y0 + (y1 - y0) * (xx - x0) / (x1 - x0)
    return np.arange(H)[:, None] < yl[None, :]


def recut(m):
    """Run inside tools/blender/dump_parts.py (m = its module): replace the recipe's parts with this cut."""
    from PIL import Image
    from scipy import ndimage
    W, H = m.W, m.H
    art = m.premul(m.rig.src)
    plate = m.premul(Image.open(os.path.join(m.ROOT, "art", "blender", "plates", "H7_back.png")))
    yy, xx = np.mgrid[0:H, 0:W]
    opaque = art[..., 3] > .01
    fl, r = shape(FL, W, H), shape(R, W, H)
    # each front flap's end bulges the sticker's outline: the art's pixels outside the plate's outline next to it
    out = opaque & (plate[..., 3] < .5)
    out = ndimage.binary_opening(out, iterations=2)
    for mask, box in ((fl, (0, 200, 160, 420)), (r, (840, 230, 1000, 440))):
        x0, y0, x1, y1 = box
        bulge = out & (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
        lab, n = ndimage.label(bulge | mask)
        cy, cx = np.argwhere(mask)[len(np.argwhere(mask)) // 2]
        mask |= (lab == lab[cy, cx]) & bulge
    fl &= opaque; r &= opaque
    # the back flaps: what is above the front flaps' free edges and above the back rims, split at the V; with the
    # sticker border above them
    bl = opaque & ~fl & ~r & above(BL_HINGE, W, H) & (xx < V_X)
    br = opaque & ~fl & ~r & above(BR_HINGE, W, H) & (xx >= V_X)
    # under the front flaps: the plate - a back flap's own hidden part goes to that back flap
    bl_ext = (fl | r) & above(BL_HINGE, W, H) & (xx < V_X) & (plate[..., 3] > .01)
    br_ext = (fl | r) & above(BR_HINGE, W, H) & (xx >= V_X) & (plate[..., 3] > .01)
    body_plate = (fl | r) & ~bl_ext & ~br_ext
    m.full.clear(); m.meta.clear()
    body = art * (~(fl | r | bl | br))[..., None]
    body = np.where(body_plate[..., None], plate, body)
    m.full["body"] = body
    # each back flap runs on 3 px past its hinge into the box's rim, and the right one 3 px past the split into the
    # left one (the box and the left flap keep those pixels too): a flap folding about its hinge never opens a
    # hairline of daylight along the hinge or down the V between them (texture filtering softens both cut edges)
    def down3(seg):
        return tuple((x, y + 3) for x, y in seg)
    tuck_bl = opaque & ~fl & ~r & above(down3(BL_HINGE), W, H) & (xx < V_X) & ~bl & ~bl_ext
    tuck_br = opaque & ~fl & ~r & above(down3(BR_HINGE), W, H) & (xx >= V_X - 3) & ~br & ~br_ext
    m.full["flap_bl"] = np.where(bl_ext[..., None], plate, art * (bl | tuck_bl)[..., None])
    m.full["flap_br"] = np.where(br_ext[..., None], plate, np.where(tuck_br[..., None] & ~(fl | r)[..., None],
                                                                     np.maximum(art, body), art * br[..., None]))
    m.full["flap_fl"] = art * fl[..., None]
    m.full["flap_r"] = art * r[..., None]
    # a front flap lifted past the sticker's outline wears the sticker's border: a rim round each, built from the
    # border the art draws round the box's walls (its profile by distance from the edge), riding the flap's bone and
    # drawn behind everything - so it shows only where the flap sticks out (at rest the art's border covers it)
    src = np.asarray(m.rig.src.convert("RGBA")).astype(np.float32) / 255
    al = src[..., 3]
    outside = ndimage.distance_transform_edt(al > .5)
    walls = (yy > 520) & (al > .5) & (outside > 30)
    steps, prof = m.border_profile(src, ndimage.binary_fill_holes(walls), al, np.zeros_like(walls))
    for name, core in (("flap_fl", shape(FL, W, H)), ("flap_r", shape(R, W, H))):
        m.full[name + "_rim"] = m.ring(core, steps, prof) * art[..., 3:4]   # (never past the art's own outline)
    m.meta.update({
        "body": {"pivot": BASE, "parent": None, "hidden": False},
        "flap_bl": {"pivot": mid(BL_HINGE), "parent": "body", "hidden": False, "chain": chain(BL_HINGE, BL_TIP)},
        "flap_br": {"pivot": mid(BR_HINGE), "parent": "body", "hidden": False, "chain": chain(BR_HINGE, BR_TIP)},
        "flap_fl": {"pivot": mid(FL_HINGE), "parent": "body", "hidden": False, "chain": chain(FL_HINGE, FL_TIP)},
        "flap_r": {"pivot": mid(R_HINGE), "parent": "body", "hidden": False, "chain": chain(R_HINGE, R_TIP)},
        "flap_fl_rim": {"pivot": mid(FL_HINGE), "parent": "body", "hidden": False, "bones_of": "flap_fl"},
        "flap_r_rim": {"pivot": mid(R_HINGE), "parent": "body", "hidden": False, "bones_of": "flap_r"},
    })
    m.draw[:] = ["flap_fl_rim", "flap_r_rim", "body", "flap_bl", "flap_br", "flap_fl", "flap_r"]
    print(f"   H7 re-cut: body + flap_bl ({int((bl | bl_ext).sum())} px) flap_br ({int((br | br_ext).sum())}) "
          f"flap_fl ({int(fl.sum())}) flap_r ({int(r.sum())})")


_m = sys.modules.get("__main__")
if _m is not None and hasattr(_m, "full") and hasattr(_m, "meta") and getattr(_m, "sid", None) == "H7":
    recut(_m)
