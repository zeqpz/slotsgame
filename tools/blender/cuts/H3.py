# H3 - Gold chain: what Blender's cut changes from the rig recipe (tools/icon_rigs/recipes/H3.py).
# The recipe cut the loop into seven hard-edged slices and a clasp, measured on the old flat drawing: on the new art
# the slices miss the sticker border and the clasp polygon takes bits of two links. Blender bends the loop as ONE
# mesh instead (anim_H3.py weights it to a ring of bones round the loop), so nothing ever opens between pieces:
#   s1     every link and the sticker border round them (the art's own pixels), running 6 px in under the clasp's
#          two end caps; s2..s7 are dropped
#   clasp  the box clasp with its two end caps and the white border along its sides, re-cut to the new art's clasp
#          (a box along the chain at 39 degrees)
# Neither ever uncovers anything (the links bend under the clasp with it, the clasp only swells), so H3 needs no
# clean plate. The re-cut takes the art's own pixels through the plate "art" (art/blender/plates/H3_art.png, a byte
# copy of art/icons-src/H3.png - nothing painted).
# The recipe hangs every part from "hang", a helper bone made from a hidden sprite (not a part): run this file
# after dump_parts (python tools/blender/cuts/H3.py) to set those parents to none - anim_H3.py builds the real
# hang / toss bones itself.
import json, math, os


def box(cx, cy, deg, u0, u1, v0, v1):
    """A rectangle along a direction: u along deg (image px, y down), v across it."""
    a = math.radians(deg)
    ux, uy, vx, vy = math.cos(a), math.sin(a), -math.sin(a), math.cos(a)
    return [(cx + u * ux + v * vx, cy + u * uy + v * vy) for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))]


CLASP_C, CLASP_DEG = (308.5, 547.8), 39.0
CLASP_BOX = ("poly", box(*CLASP_C, CLASP_DEG, -84, 93, -80, 80))       # the end caps' outer ink, the side borders
LINKS_HOLE = ("poly", box(*CLASP_C, CLASP_DEG, -78, 87, -74, 74))      # the links run 6 px in under the clasp all round
EVERYTHING = ("rect", -10, -10, 1010, 1010)

DROP = ["s2", "s3", "s4", "s5", "s6", "s7"]
FILLS = [
    {"part": "s1", "region": ("minus", EVERYTHING, LINKS_HOLE), "plate": "art"},
    {"part": "clasp", "region": CLASP_BOX, "plate": "art"},
]
CLEAR = [
    {"part": "s1", "region": LINKS_HOLE},
    {"part": "clasp", "region": ("minus", EVERYTHING, CLASP_BOX)},
]


def fix_parents(path=None):
    path = path or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                                "art", "blender", "parts", "H3", "parts.json")
    spec = json.load(open(path))
    names = {p["name"] for p in spec["parts"]}
    for p in spec["parts"]:
        if p["parent"] and p["parent"] not in names:
            p["parent"] = None
    json.dump(spec, open(path, "w"), indent=1)
    return [(p["name"], p["parent"]) for p in spec["parts"]]


def inner_outline(grow=9):
    """The bracelet's hole as one closed path (icon px), `grow` px inside it: the line anim_H3.py draws the glow
    along where the light behind the sticker shows through the hole (tools/blender/outline.py traces only the outer
    edge). Writes art/blender/parts/H3/outline_inner.json."""
    import numpy as np
    from PIL import Image
    from scipy import ndimage
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    a = np.asarray(Image.open(os.path.join(root, "art", "icons-src", "H3.png")).convert("RGBA").getchannel("A")) > 128
    hole = ndimage.binary_fill_holes(a) & ~a
    lab, n = ndimage.label(hole)
    sizes = ndimage.sum(hole, lab, range(1, n + 1))
    hole = lab == 1 + int(np.argmax(sizes))
    m = ndimage.distance_transform_edt(hole) > grow
    m = ndimage.binary_opening(m, iterations=2)
    H, W = m.shape
    pad = np.zeros((H + 2, W + 2), bool)
    pad[1:-1, 1:-1] = m
    ys, xs = np.nonzero(pad)
    start = (ys.min(), xs[ys == ys.min()].min())
    nb = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
    path, cur, back = [start], start, 6
    for _ in range(400000):                            # Moore-neighbour tracing (as tools/blender/outline.py)
        for k in range(8):
            d = (back + 1 + k) % 8
            ny, nx = cur[0] + nb[d][0], cur[1] + nb[d][1]
            if pad[ny, nx]:
                back = (d + 4) % 8
                cur = (ny, nx)
                break
        if cur == start:
            break
        path.append(cur)
    pts = [(x - 1.0, y - 1.0) for y, x in path]

    def rdp(p, eps):
        if len(p) < 3:
            return p
        (x0, y0), (x1, y1) = p[0], p[-1]
        dx, dy = x1 - x0, y1 - y0
        nrm = math.hypot(dx, dy) or 1e-9
        dd = [abs(dy * (x - x0) - dx * (y - y0)) / nrm for x, y in p[1:-1]]
        i = int(np.argmax(dd)) + 1
        if dd[i - 1] > eps:
            return rdp(p[:i + 1], eps)[:-1] + rdp(p[i:], eps)
        return [p[0], p[-1]]
    half = len(pts) // 2
    simple = rdp(pts[:half + 1], 1.6)[:-1] + rdp(pts[half:] + [pts[0]], 1.6)[:-1]
    out = os.path.join(root, "art", "blender", "parts", "H3", "outline_inner.json")
    json.dump({"id": "H3", "grow": grow, "source": "art hole", "points": [[round(x, 1), round(y, 1)] for x, y in simple]},
              open(out, "w"))
    return len(simple), out


if __name__ == "__main__":
    print("H3 parents:", fix_parents())
    print("H3 inner outline:", inner_outline())
