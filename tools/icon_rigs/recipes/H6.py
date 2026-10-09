# H6 - Skateboard, seen from underneath. Idle: it carves - the deck leans one way then the other
# while both trucks steer against the lean, then it pops a quick manual (the nose lifts on the
# back wheels and taps down). Land: the deck drops onto its wheels, the trucks give and spring
# back. Win: a kickflip - wind up, pop, the board flips once round its long axis at the top of
# the jump, then lands on its wheels with a dust puff and settles.
import math

CENTER = (530, 490)        # the middle of the deck: it leans and flips about here
AXLE_F = (292, 476)        # middle of the front axle: the truck rocks against the deck about here
AXLE_B = (652, 852)        # middle of the back axle
TAIL_WHEEL = (770, 935)    # the back wheel's contact patch: the manual pivots here
PPU = 10.0
AXIS = -45                 # the deck's long axis in skeleton degrees (nose top-left, tail bottom-right)


def about(point, a):
    """translation (units) that makes a rotation of a degrees about CENTER act about `point`"""
    px, py = (point[0] - CENTER[0]) / PPU, (CENTER[1] - point[1]) / PPU     # point relative to the pivot, y up
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return px - (c * px - s * py), py - (s * px + c * py)


def manual(keys):
    """deck r/x/y keys for a lean about the back wheel: keys = [(t, deg, ease)]"""
    r, x, y = [], [], []
    for t, a, *e in keys:
        dx, dy = about(TAIL_WHEEL, a)
        r.append((t, a, *e)); x.append((t, dx, *e)); y.append((t, dy, *e))
    return r, x, y


# the trucks: outlines that follow the gaps between each truck's sticker border and the deck's
# (through the middle of the see-through wedge between each far wheel's border and the deck's,
# so neither sticker border is split), minus the deck's own paint (blue, cyan, yellow), so no deck
# graphics ride along with a truck
TRUCK_F = [(88, 470), (92, 420), (120, 399), (130, 387), (140, 378), (150, 373), (160, 371), (170, 372), (180, 374), (190, 377),
           (200, 381), (210, 387), (220, 394), (230, 403), (240, 413), (250, 417), (262, 421), (288, 419), (296, 410), (279, 398),
           (276, 340), (290, 325), (320, 326), (365, 346), (405, 375), (432, 404), (436, 430), (452, 447), (474, 478), (482, 515),
           (470, 552), (440, 572), (395, 578), (355, 566), (332, 535), (300, 520), (250, 512), (205, 527), (140, 527), (92, 505)]
TRUCK_B = [(468, 840), (470, 795), (490, 768), (500, 752), (510, 743), (520, 738), (530, 736), (540, 736), (550, 737), (560, 737),
           (570, 744), (580, 752), (586, 757), (606, 762), (612, 745), (607, 705), (640, 690), (700, 692), (735, 712), (742, 790),
           (724, 812), (804, 814), (822, 850), (824, 905), (806, 944), (768, 956), (716, 950), (696, 925), (688, 895), (610, 905),
           (540, 906), (494, 895)]
DECK_COLOURS = ("or", ("color", "#3f86d0", 70), ("color", "#16d8e5", 80), ("color", "#ffd56d", 70))

# idle: carve (0 .. 1.6 s), then the manual (1.7 .. 2.5 s)
_mr, _mx, _my = manual([(1.70, 0), (1.92, -7.5, "out"), (2.12, -6.4, "inout"), (2.30, .8, "in"), (2.42, -.5, "out"), (2.55, 0, "soft")])
# the carve rolls the board a little along its length too (down-right = forward)
IDLE_DECK = {
    "r": [(0, 0), (.45, 4.0, "inout"), (1.05, -3.6, "inout"), (1.45, .8, "inout"), (1.65, 0, "soft")] + _mr[1:],
    "x": [(0, 0), (.45, -1.6, "inout"), (1.05, 1.5, "inout"), (1.45, -.3, "inout"), (1.65, 0, "soft")] + _mx[1:],
    "y": [(0, 0), (.45, 1.2, "inout"), (1.05, -.9, "inout"), (1.45, .2, "inout"), (1.65, 0, "soft")] + _my[1:],
}

# win: the pop lean, and the flip - one turn round the long axis. The helper bone "flip" carries
# the jump and the lean; during the flip it also turns onto the board's across-axis and scales
# along it (sy), while the deck turns back by the same angle: R(lean) R(a) S R(-a) - so nothing
# turns, the board just thins to an edge, shows its other side and comes back.
FLIP0, FLIP1 = .17, .47
q = (FLIP1 - FLIP0) / 4
FLIP_SY = [(0, 1), (FLIP0, 1, "linear"), (FLIP0 + q, 0, "in"), (FLIP0 + 2 * q, -1, "out"), (FLIP0 + 3 * q, 0, "in"), (FLIP1, 1, "out"), (1.4, 1)]
WIN_LEAN = [(0, 0), (.12, 3.0, "inout"), (.30, -7, "out"), (.47, -1.5, "inout"), (.60, 2.0, "in"), (.72, -1.2, "out"), (.86, .5, "inout"), (1.02, 0, "soft"), (1.4, 0)]


def lean_at(t):
    for (ta, va, *_), (tb, vb, *_) in zip(WIN_LEAN, WIN_LEAN[1:]):
        if ta <= t <= tb:
            return va + (vb - va) * (t - ta) / (tb - ta)
    return 0


def flip_r():
    """the lean, plus AXIS while the flip runs (stepped on at FLIP0, off at FLIP1, where sy is 1)"""
    eps = .002
    keys = [k for k in WIN_LEAN if k[0] < FLIP0 - eps]
    keys.append((FLIP0 - eps, lean_at(FLIP0 - eps), "linear"))
    keys.append((FLIP0, lean_at(FLIP0) + AXIS, "step"))
    keys += [(t, v + AXIS, *e) for t, v, *e in WIN_LEAN if FLIP0 < t < FLIP1 - eps]
    keys.append((FLIP1 - eps, lean_at(FLIP1 - eps) + AXIS, "linear"))
    keys.append((FLIP1, lean_at(FLIP1), "step"))
    keys += [k for k in WIN_LEAN if k[0] > FLIP1]
    return keys


DECK_COUNTER = [(0, 0), (FLIP0, -AXIS, "step"), (FLIP1, 0, "step"), (1.4, 0)]


RIG = {
    "id": "H6",
    "parts": [
        {"name": "truck_f", "mask": ("minus", ("poly", TRUCK_F), DECK_COLOURS), "pivot": AXLE_F, "parent": "deck", "fill": "deck"},
        {"name": "truck_b", "mask": ("minus", ("poly", TRUCK_B), DECK_COLOURS), "pivot": AXLE_B, "parent": "deck", "fill": "deck"},
        {"name": "deck", "mask": "rest", "pivot": CENTER, "parent": "flip"},
        # an invisible helper bone for the kickflip (never shown)
        {"name": "flip", "sprite": "sparkle", "size": 2, "at": CENTER, "hidden": True},
        {"name": "puff_a", "sprite": "puff", "size": 20, "at": (640, 930), "hidden": True},
        {"name": "puff_b", "sprite": "puff", "size": 17, "at": (880, 900), "hidden": True},
        {"name": "glint_a", "sprite": "sparkle", "size": 13, "at": (300, 160), "hidden": True, "parent": "deck"},
        {"name": "glint_b", "sprite": "sparkle", "size": 11, "at": (820, 720), "hidden": True, "parent": "deck"},
    ],
    "draw": ["flip", "puff_a", "puff_b", "deck", "truck_f", "truck_b", "glint_a", "glint_b"],
    "anims": {
        "idle": {"dur": 2.6, "bones": {
            "deck": IDLE_DECK,
            "truck_f": {"r": [(0, 0), (.5, -2.4, "inout"), (1.1, 2.2, "inout"), (1.5, -.5, "inout"), (1.7, 0, "soft"),
                              (1.95, 2.0, "out"), (2.3, -1.2, "inout"), (2.55, 0, "soft")]},
            "truck_b": {"r": [(0, 0), (.5, 2.2, "inout"), (1.1, -2.0, "inout"), (1.5, .4, "inout"), (1.7, 0, "soft"),
                              (2.28, 0), (2.36, -1.6, "in"), (2.5, 0, "out")]},
        }},
        "land": {"dur": .55, "bones": {
            "deck": {"y": [(0, 0), (.08, -1.8, "in"), (.22, .7, "out"), (.36, -.2), (.5, 0)],
                     "r": [(0, 0), (.08, .8, "in"), (.24, -.6, "out"), (.4, .1), (.52, 0)]},
            "truck_f": {"r": [(0, 0), (.1, 3.5, "in"), (.26, -2.0, "out"), (.42, .5), (.55, 0)]},
            "truck_b": {"r": [(0, 0), (.1, -3.0, "in"), (.26, 1.8, "out"), (.42, -.4), (.55, 0)]},
        }},
        "win": {"dur": 1.4, "bones": {
            "flip": {"r": flip_r(), "sy": FLIP_SY,
                     "y": [(0, 0), (.12, -1.4, "inout"), (.40, 8.5, "out"), (.62, 0, "in"), (.74, .9, "out"), (.88, 0, "in"), (1.4, 0)]},
            "deck": {"r": DECK_COUNTER},
            "truck_f": {"r": [(0, 0), (.12, 1.2, "inout"), (.3, -3.5, "out"), (.5, 2.4, "inout"), (.64, -2.2, "in"), (.8, 1.0, "out"), (1.0, 0, "soft")]},
            "truck_b": {"r": [(0, 0), (.12, -1.2, "inout"), (.3, 3.2, "out"), (.5, -2.4, "inout"), (.64, 2.0, "in"), (.8, -.9, "out"), (1.0, 0, "soft")]},
            # dust off the wheels on the landing: billows out fast, then thins and shrinks away
            "puff_a": {"sx": [(0, 1), (.6, 1, "step"), (.61, .5, "step"), (.8, 1.35, "out"), (1.06, 1.0, "in"), (1.08, 1, "step")],
                       "sy": [(0, 1), (.6, 1, "step"), (.61, .5, "step"), (.8, 1.2, "out"), (1.06, .9, "in"), (1.08, 1, "step")],
                       "x": [(0, 0), (.61, 0), (1.06, -6, "out"), (1.08, 0, "step")],
                       "y": [(0, 0), (.61, 0), (1.06, 1.5, "out"), (1.08, 0, "step")]},
            "puff_b": {"sx": [(0, 1), (.62, 1, "step"), (.63, .5, "step"), (.82, 1.3, "out"), (1.08, .95, "in"), (1.1, 1, "step")],
                       "sy": [(0, 1), (.62, 1, "step"), (.63, .5, "step"), (.82, 1.2, "out"), (1.08, .9, "in"), (1.1, 1, "step")],
                       "x": [(0, 0), (.63, 0), (1.08, 5, "out"), (1.1, 0, "step")],
                       "y": [(0, 0), (.63, 0), (1.08, 1.5, "out"), (1.1, 0, "step")]},
            "glint_a": {"sx": [(0, 1), (.46, 1, "step"), (.47, .3, "step"), (.6, 1.2, "out"), (.82, .2, "in"), (.84, 1, "step")],
                        "sy": [(0, 1), (.46, 1, "step"), (.47, .3, "step"), (.6, 1.2, "out"), (.82, .2, "in"), (.84, 1, "step")],
                        "r": [(0, 0), (.47, 0), (.82, 90, "linear"), (.84, 0, "step")]},
            "glint_b": {"sx": [(0, 1), (.52, 1, "step"), (.53, .3, "step"), (.66, 1.2, "out"), (.88, .2, "in"), (.9, 1, "step")],
                        "sy": [(0, 1), (.52, 1, "step"), (.53, .3, "step"), (.66, 1.2, "out"), (.88, .2, "in"), (.9, 1, "step")],
                        "r": [(0, 0), (.53, 0), (.88, -90, "linear"), (.9, 0, "step")]},
        }, "alpha": {
            "puff_a": [(0, 0), (.61, 0, "step"), (.65, .95), (.92, .9, "linear"), (1.06, 0, "linear")],
            "puff_b": [(0, 0), (.63, 0, "step"), (.67, .9), (.94, .85, "linear"), (1.08, 0, "linear")],
            "glint_a": [(0, 0), (.47, 0, "step"), (.56, 1), (.82, 0)],
            "glint_b": [(0, 0), (.53, 0, "step"), (.62, 1), (.88, 0)],
        }},
    },
}
