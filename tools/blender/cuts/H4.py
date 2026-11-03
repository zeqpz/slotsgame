# H4 - Fresh kicks: what Blender's cut changes from the rig recipe (tools/icon_rigs/recipes/H4.py).
# The recipe's front-shoe outline was measured on the old drawing (it cuts through the redrawn lace loops) and the
# laces were part of the shoes, so this cut re-cuts the art itself when tools/blender/dump_parts.py runs it
# (recut(), below). Six moving pieces, each the art's own pixels inside its outline, and behind them all a "rim"
# per piece - the sticker border round that piece (the art's border pixels where they show at rest, the border's
# measured profile where another piece hides it), so pieces that swing apart each keep a whole border:
#   back        the back shoe (and the lace below its collar top); it hangs from back_lace
#   back_lace   the back shoe's lace from the knot down to its collar: a chain of two bones (it bends)
#   back_end    the loose lace end with its aglet hanging in front of the back collar: a chain (it flops)
#   front       the front shoe (and the lace below its collar top); it hangs from front_lace
#   front_lace  the front shoe's lace from the knot down to its collar, over the back shoe's heel: a chain
#   front_end   the loose lace end with its aglet crossing the front collar: a chain
# What a moving piece uncovers comes from the clean plates: under the front shoe, the back shoe whole
# (art/blender/plates/H4.png - the front shoe and its laces removed); under the laces, the collars and the back heel
# without them (art/blender/plates/H4_ends.png - the hanging laces removed; it is drawn on the art's own geometry).
# Every switch between the art and a plate is exact (binary): the pieces laid together are the art.
import os, sys
import numpy as np

PLATE_PROMPT = (
    "1. Remove the FRONT sneaker completely - the lower, right-hand shoe that is nearer to us - together with all of "
    "its laces: the laces that run up from it to the top of the picture and its loose lace end with the silver metal "
    "tip hanging down across it.\n"
    "2. Also remove the other loose lace end with a silver metal tip, the one that hangs down in front of the back "
    "shoe's padded collar.\n"
    "3. Paint the BACK sneaker (the upper, left-hand shoe) whole where the front shoe and those laces hid it: its "
    "heel, the back of its black padded collar, its grey and white leather panels, its cream midsole and dark rubber "
    "outsole running round to the heel - in exactly the same style, colours, shading and stitching, as one complete "
    "shoe. The black lace that runs up from the back shoe to the top of the picture stays.\n"
    "4. The plain white sticker border follows the back shoe's own outline where the front shoe used to be.")
PLATES = {"ends": (
    "1. Remove the two loose lace ends that hang down with silver metal tips (aglets): the one hanging straight down "
    "in front of the left shoe's padded collar, and the one running diagonally down in front of the right shoe's "
    "collar to its silver tip.\n"
    "2. Paint what was behind them in the same style: the shoes' padded collars, leather, stitching and the other "
    "laces carrying on naturally, and the plain white sticker border where a lace end stuck out past the outline.")}

KNOT = (512, 42)             # where the laces hang from (over a wire, off the top of the sticker)
# the chains (icon px, root first): each lace from its top down to where it goes into its shoe; the loose ends
# from their tops to their aglets
BACK_LACE = [(440, 40), (438, 104), (436, 172)]
BACK_END = [(486, 56), (484, 118), (483, 184), (482, 252)]
FRONT_LACE = [(580, 40), (588, 166), (596, 296)]
FRONT_END = [(606, 58), (613, 150), (634, 262), (684, 396)]
# outlines (icon px) round each lace, a few px out (the white between them is the sticker border, not lace)
G1 = [(408, 62), (413, 50), (422, 50), (430, 38), (438, 28), (448, 30), (453, 44), (459, 50), (467, 54), (467, 68), (457, 92),
      (453, 110), (452, 176), (424, 176), (427, 110), (423, 96), (410, 78)]
G2 = [(466, 64), (472, 50), (480, 50), (486, 44), (494, 46), (498, 56), (504, 60), (507, 72), (499, 95), (495, 110), (495, 180),
      (497, 258), (470, 258), (471, 180), (472, 110), (469, 95)]
SA = [(550, 52), (556, 42), (565, 42), (574, 54), (578, 38), (584, 31), (593, 34), (596, 50), (598, 90), (601, 140), (604, 200),
      (607, 250), (610, 300), (582, 300), (580, 250), (578, 200), (575, 150), (570, 110), (560, 82), (551, 66)]
SB = [(597, 62), (601, 50), (610, 50), (614, 62), (615, 100), (621, 150), (631, 200), (642, 250), (654, 292), (670, 330),
      (686, 364), (698, 392), (690, 406), (675, 404), (664, 374), (649, 336), (632, 292), (621, 250), (610, 200), (602, 150),
      (597, 100)]
# the front shoe: generous where it borders the sticker, exact (the outer edge of its lace loops' ink, a few px out)
# where it lies over the back shoe
FRONT = [(596, 294), (630, 291), (664, 287), (676, 280), (690, 240), (900, 240), (1000, 300), (1000, 1000), (200, 1000),
         (200, 800), (300, 735), (380, 690), (424, 662),
         (440, 648), (436, 631), (444, 611), (466, 606), (459, 594), (467, 577), (491, 573), (483, 562), (502, 542), (528, 537),
         (521, 526), (532, 509), (553, 506), (548, 497), (557, 478), (570, 473), (565, 463), (572, 442), (586, 437), (586, 400),
         (588, 330), (592, 300)]


def shape(pts, W, H, ss=4):
    from PIL import Image, ImageDraw
    big = Image.new("L", (W * ss, H * ss), 0)
    ImageDraw.Draw(big).polygon([(x * ss, y * ss) for x, y in pts], fill=255)
    return np.asarray(big.resize((W, H), Image.BOX), np.float32) / 255 > .5


def front_mask(src, W, H):
    """The front shoe's outline: the hand outline, with its edge over the back shoe snapped onto the outer edge of
    the lace loops' ink and then pulled 2 px inside it - the front shoe only ever swings over the back shoe (never
    off it), so the back keeps that hair of the loops' ink under the front, and the front carries none of the back's
    paint away with it. (Over the back's outsole the snap would take its dark blocks: there the outline is used.)"""
    from scipy import ndimage
    lum = (src[..., :3] * [.3, .59, .11]).sum(-1)
    poly = shape(FRONT, W, H)
    yy, xx = np.mgrid[0:H, 0:W]
    zone = (xx < 610) & (yy > 300) & (yy < 668)
    d_in = ndimage.distance_transform_edt(poly)
    d_out = ndimage.distance_transform_edt(~poly)
    grab = (lum < .2) & zone & (d_out <= 7) & ~poly & (yy < 596)
    seed = poly & zone & (d_in <= 2)
    lab, n = ndimage.label(grab | seed)
    ids = np.unique(lab[seed])
    grab &= np.isin(lab, ids[ids > 0])
    snapped = ndimage.binary_erosion(ndimage.binary_closing(poly | grab, iterations=1), iterations=2)
    return np.where(zone & (yy < 596), snapped, np.where(zone, ndimage.binary_erosion(poly, iterations=1), poly))


def recut(m):
    """Run inside tools/blender/dump_parts.py (m = its module): replace the recipe's parts with this cut."""
    from PIL import Image
    from scipy import ndimage
    W, H = m.W, m.H
    src = np.asarray(m.rig.src.convert("RGBA")).astype(np.float32) / 255
    art = m.premul(m.rig.src)
    P = os.path.join(m.ROOT, "art", "blender", "plates")
    p_back = m.premul(Image.open(os.path.join(P, "H4.png")))
    p_ends = m.premul(Image.open(os.path.join(P, "H4_ends.png")))
    yy, xx = np.mgrid[0:H, 0:W]
    al = src[..., 3]
    rgb = src[..., :3]
    white = (rgb.min(-1) > .8) & (rgb.max(-1) - rgb.min(-1) < .1)
    outside = ndimage.distance_transform_edt(al > .5)
    # everything but the sticker border: the drawing inside its outer ink line (white leather panels are enclosed by
    # ink, so they fill in)
    core = (al > .5) & ~white & (outside > 3)
    core = ndimage.binary_fill_holes(ndimage.binary_closing(core, iterations=2)) & (al > .5)
    sb = shape(SB, W, H) & core
    sa = shape(SA, W, H) & core & ~sb & (yy < 300)
    g2 = shape(G2, W, H) & core
    g1 = shape(G1, W, H) & core & ~g2 & (yy < 176)
    fpoly = front_mask(src, W, H)
    front = fpoly & core & ~sb & ~sa
    back = core & ~(front | sb | sa | g1 | g2)
    cores = {"back": back, "back_lace": g1, "back_end": g2, "front": front, "front_lace": sa, "front_end": sb}
    # the sticker border's profile, measured round the whole drawing where it is clean
    steps, prof = m.border_profile(src, core, al, np.zeros_like(core))
    full, meta = {}, {}
    # the pieces: their own pixels; under what moves over them, a plate
    b = art * back[..., None]
    for strand in (sa, sb, g2):                     # the laces over the back shoe: the collars without them
        over_back = strand & ~fpoly & (p_ends[..., 3] > .01)
        b = np.where(over_back[..., None], p_ends, b)
    # under the front shoe (and the laces lying on it): the back shoe carried on from its own art. The plate draws
    # the back's sole 30 px off where it runs in under the front, so near the seam the back's pixels are carried on
    # along the sole's own direction, a whole number of outsole blocks at a time (the white panel, the midsole's
    # lines and the outsole's blocks run on unbroken); under the front collar's top edge the heel's last rows carry
    # straight down; deeper in, the plate. Only the first tens of px ever show, as the shoes swing against each other.
    hidden = fpoly & core & ~back
    src_ok = (b[..., 3] > .98) & back                           # the back's own drawing (not its sticker border)
    src_ok &= ndimage.distance_transform_edt(~hidden) > 7      # not the hair of loop ink the back keeps at the seam
    b = np.where((hidden & (p_back[..., 3] > .01))[..., None], p_back, b)
    done = ~hidden.copy()
    ext = b.copy()
    u = np.array([1.0, -.42]); u /= np.linalg.norm(u)           # along the sole, toward the heel
    period = 23.9                                               # the outsole blocks' spacing along it
    sole = hidden & (xx < 600) & (yy > 360)
    for k in range(1, 7):
        sx = np.clip(np.round(xx - u[0] * period * k).astype(int), 0, W - 1)
        sy = np.clip(np.round(yy - u[1] * period * k).astype(int), 0, H - 1)
        ok = sole & ~done & src_ok[sy, sx]
        ext[ok] = b[sy[ok], sx[ok]]
        done |= ok
    dist, (iy, ix) = ndimage.distance_transform_edt(~src_ok, return_indices=True)
    top = hidden & ~done & (dist <= 16) & (yy < 360)
    ext[top] = b[iy[top], ix[top]]
    full["back"] = ext
    f = art * front[..., None]
    over_front = sb & fpoly & (p_ends[..., 3] > .01)
    full["front"] = np.where(over_front[..., None], p_ends, f)
    for name, c in (("back_lace", g1), ("back_end", g2), ("front_lace", sa), ("front_end", sb)):
        full[name] = art * c[..., None]
    # the rims: the art's border round each piece where it shows, the measured border where another piece hides it,
    # out as far as the border goes and 2 px in under the piece's own edge (no crack)
    border_px = art * ((al > .01) & ~core)[..., None]
    for name, c in cores.items():
        d = ndimage.distance_transform_edt(~c)
        inner = ndimage.distance_transform_edt(c)
        reach = np.clip(steps[-1] - 6.5 - d, 0, 1) * ((d > 0) | (inner <= 2))
        others = np.zeros_like(c)
        for o, oc in cores.items():
            if o != name:
                others |= oc
        others &= ~c
        rim = np.where(others[..., None], m.ring(c, steps, prof), border_px) * reach[..., None]
        full[name + "_rim"] = rim
        # the rim's solid inside (3 px in from its outer edge), drawn over every rim: where two rims overlap out of
        # line, the faint outer edge of one would show as a grey line across the other's white - the fills cover it.
        # At rest every pixel is the art's own, so the fills change nothing there.
        solid = ndimage.binary_erosion(rim[..., 3] > .97, iterations=3)
        print("     ", name, "rim fill", int(solid.sum()), "px")
        full[name + "_rimfill"] = rim * solid[..., None]
    m.full.clear(); m.meta.clear()
    m.full.update(full)
    m.meta.update({
        "back": {"pivot": BACK_LACE[-1], "parent": "back_lace.1", "hidden": False},
        "front": {"pivot": FRONT_LACE[-1], "parent": "front_lace.1", "hidden": False},
        "back_lace": {"pivot": BACK_LACE[0], "parent": None, "hidden": False, "chain": [list(map(float, p)) for p in BACK_LACE]},
        "back_end": {"pivot": BACK_END[0], "parent": None, "hidden": False, "chain": [list(map(float, p)) for p in BACK_END]},
        "front_lace": {"pivot": FRONT_LACE[0], "parent": None, "hidden": False, "chain": [list(map(float, p)) for p in FRONT_LACE]},
        "front_end": {"pivot": FRONT_END[0], "parent": None, "hidden": False, "chain": [list(map(float, p)) for p in FRONT_END]},
        "back_rim": {"pivot": BACK_LACE[-1], "parent": "back", "hidden": False},
        "front_rim": {"pivot": FRONT_LACE[-1], "parent": "front", "hidden": False},
    })
    m.meta["back_rimfill"] = {"pivot": BACK_LACE[-1], "parent": "back", "hidden": False}
    m.meta["front_rimfill"] = {"pivot": FRONT_LACE[-1], "parent": "front", "hidden": False}
    for n in ("back_lace", "back_end", "front_lace", "front_end"):
        m.meta[n + "_rim"] = {"pivot": m.meta[n]["pivot"], "parent": None, "hidden": False, "bones_of": n}
        m.meta[n + "_rimfill"] = {"pivot": m.meta[n]["pivot"], "parent": None, "hidden": False, "bones_of": n}
    rims = ["back_rim", "front_rim", "back_lace_rim", "back_end_rim", "front_lace_rim", "front_end_rim"]
    m.draw[:] = rims + [r + "fill" for r in rims] + ["back", "back_lace", "back_end", "front", "front_lace", "front_end"]
    print("   H4 re-cut:", ", ".join(f"{n} {int(c.sum())} px" for n, c in cores.items()))


_m = sys.modules.get("__main__")
if _m is not None and hasattr(_m, "full") and hasattr(_m, "meta") and getattr(_m, "sid", None) == "H4":
    recut(_m)
