# L10 - Lowrider: what Blender's cut changes from the rig recipe (tools/icon_rigs/recipes/L10.py).
# The recipe's masks were measured on the old drawing (its wheel ellipse sits on the far wheel and misses the
# redrawn tyres), so this cut re-cuts the art itself when tools/blender/dump_parts.py runs it (recut(), below):
#   body        the car; it pivots on the rear tyre's contact patch (the hydraulics lift the nose about it). The far
#               front wheel stays on it: its top is hidden behind the bumper, so it cannot drop without showing a
#               cut edge
#   wheel_near  the big front wheel under the fender (its whole tyre is drawn): it drops out of the wheel arch on its
#               springs when the nose kicks up, and carries the sticker border under the tyre with it
# Under the wheel the body takes the clean plate (art/blender/plates/L10.png: the car without its front tyres -
# the coil-over, the inner fender and the undercarriage painted in, the sticker border following the car without
# the tyre), switched exactly at the wheel's own outline: nothing of the tyre is left behind as a ghost, and the
# parts laid together are the art itself.
import os, sys
import numpy as np

PLATE_PROMPT = (
    "1. Remove the TYRES AND RIMS of the two front wheels of the car: the big front wheel in the middle of the picture, "
    "under the front fender, and the far front wheel at the bottom left, under the front bumper. Keep the chrome "
    "suspension parts that are in front of the far front wheel (its chrome shock absorber and the chrome arms crossing "
    "in front of it) exactly where they are.\n"
    "2. Where the tyres and rims were, paint what was behind them, in the same style and shading: the dark inside of "
    "the front wheel arch and the inner fender above the big wheel, the chrome undercarriage, suspension arms, coil "
    "springs and hydraulic cylinders under the car carrying on naturally, and empty transparent background below the "
    "car where the wheels stuck out under it. The plain white sticker border follows the car's new outline there.")

REAR = (866, 692)          # the rear tyre's contact patch
HUB_NEAR = (546, 566)      # the big front wheel's hub
# the tyre's outer edge a couple of px out (icon px, a smooth closed curve through the points)
NEAR = [(540, 476), (566, 480), (586, 494), (598, 516), (604, 542), (607, 570), (607, 600), (611, 620), (628, 629),
        (650, 633), (668, 636), (677, 648), (670, 662), (648, 670), (620, 674), (600, 674), (574, 670), (550, 670), (520, 667), (498, 656),
        (484, 642), (475, 622), (470, 596), (469, 562), (472, 532), (482, 506), (500, 488), (518, 479)]
# (its lower right takes the dark round of the tyre's far side and the bump it puts in the border, to x 677)
# the bulge the tyre puts in the sticker's outline: the art's pixels outside the plate's outline round the tyre's
# bottom (its sticker border), so the wheel carries its own border down with it; where the bulge ends, the art's
# border and the plate's run into each other
BULGE = (474, 630, 690, 720)


def catmull(pts, n=10):
    P = [np.array(p, float) for p in pts]
    m, out = len(P), []
    for i in range(m):
        p0, p1, p2, p3 = P[i - 1], P[i], P[(i + 1) % m], P[(i + 2) % m]
        for k in range(n):
            t = k / n
            out.append(.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
    return [tuple(p) for p in out]


def shape(pts, W, H, smooth=True, ss=4):
    """A hard-edged (binary) mask inside a closed outline: parts that meet along it tile the art exactly (two soft
    edges laid over each other leave a see-through seam)."""
    from PIL import Image, ImageDraw
    big = Image.new("L", (W * ss, H * ss), 0)
    ImageDraw.Draw(big).polygon([(x * ss, y * ss) for x, y in (catmull(pts) if smooth else pts)], fill=255)
    return np.asarray(big.resize((W, H), Image.BOX), np.float32) / 255 > .5


def recut(m):
    """Run inside tools/blender/dump_parts.py (m = its module): replace the recipe's parts with this cut."""
    from PIL import Image
    from scipy import ndimage
    W, H = m.W, m.H
    art = m.premul(m.rig.src)
    plate = m.premul(Image.open(os.path.join(m.ROOT, "art", "blender", "plates", "L10.png")))
    yy, xx = np.mgrid[0:H, 0:W]
    tyre = shape(NEAR, W, H)
    x0, y0, x1, y1 = BULGE
    bulge = (art[..., 3] > .01) & (plate[..., 3] < .5) & (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
    bulge = ndimage.binary_opening(bulge, iterations=3)          # not the thin slivers where the outlines differ
    lab, n = ndimage.label(bulge | tyre)
    near = (lab == lab[HUB_NEAR[1], HUB_NEAR[0]]) & (bulge | tyre)  # only the bulge that hangs off the tyre
    near |= ndimage.binary_closing(near, iterations=2) & (art[..., 3] > .01)
    m.full.clear(); m.meta.clear()
    m.full["body"] = np.where(near[..., None], plate, art)       # the plate exactly where the wheel lies over it
    m.full["wheel_near"] = art * near[..., None]
    m.meta.update({
        "body": {"pivot": REAR, "parent": None, "hidden": False},
        "wheel_near": {"pivot": HUB_NEAR, "parent": "body", "hidden": False},
    })
    m.draw[:] = ["body", "wheel_near"]
    print("   L10 re-cut: body (the plate under the big front wheel) + wheel_near")


_m = sys.modules.get("__main__")
if _m is not None and hasattr(_m, "full") and hasattr(_m, "meta") and getattr(_m, "sid", None) == "L10":
    recut(_m)
