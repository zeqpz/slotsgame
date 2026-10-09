# L8 - Zip bag of buds. The bag is alive with what is inside it: it breathes (bulges and eases),
# the zip seal at the top flexes, and the loose buds round the edge of the pile jostle and
# settle one after another as if the bag had just been set down. Land: the bag squashes on its
# bottom and the buds lag, drop and bounce. Win: the bag hops and gets a shake - the buds fly
# about inside it, a puff of aroma escapes the seal and the plastic glints.
import numpy as np

BOTTOM = (505, 905)                                     # the bag's bottom edge: it squashes and bulges from here
LIGHT = ("or", ("color", "#98b058", 60), ("color", "#908838", 50))   # a bud's light flesh (one blob per bud)
NOTCYAN = ("minus", ("opaque",), ("color", "#d0f0f8", 70))           # anything but the bag's clear plastic
BLACK = ("color", "#000000", 40)                                     # the bag's own ink (outline, creases)


def bud(x, y, extra=None):
    """one bud: its light blob (the connected piece at x, y) grown over its dark outline - but not
    into a neighbour's flesh or the plastic round it"""
    cc = ("cc", LIGHT, x, y)
    m = ("and", ("minus", ("grow", cc, 10), ("minus", LIGHT, cc)), NOTCYAN)
    return ("minus", m, extra) if extra else m


ZIP = ("rect", 90, 0, 910, 300)                         # the seal band, cut on a straight line through clear plastic
BUDS = {   # name: (seed inside its flesh, pivot at its root in the pile)
    "bud_top": ((586, 332), (585, 440)),
    "bud_ur": ((670, 393), (662, 478)),
    "bud_r": ((735, 520), (690, 560)),
    "bud_br": ((690, 650), (650, 600)),
    "bud_b": ((586, 667), (560, 672)),
    "bud_l": ((280, 520), (340, 545)),
    "bud_ul": ((400, 390), (425, 425)),
}
# bud_l touches the bag's outline: leave the outline on the bag
MASKS = {n: bud(*s, extra=BLACK if n == "bud_l" else None) for n, (s, _) in BUDS.items()}


def twinkle(t0, t1, t2, spin=90, peak=1.2):
    """a glint: pops in at t0, peaks at t1, gone by t2 - every channel back at rest by the end"""
    bones = {"sx": [(0, 1), (t0, .3, "step"), (t1, peak, "out"), (t2, .2, "in"), (t2 + .02, 1, "step")],
             "sy": [(0, 1), (t0, .3, "step"), (t1, peak, "out"), (t2, .2, "in"), (t2 + .02, 1, "step")],
             "r": [(0, 0), (t0, 0), (t2, spin, "linear"), (t2 + .02, 0, "step")]}
    return bones, [(0, 0), (t0, 0, "step"), (t0 + .1, 1), (t2, 0)]


def jostle(t0, dx, dy, r, d=.42):
    """a bud nudged at t0: it hops (dx, dy units, tilting r degrees), drops back past rest and settles"""
    return {"x": [(0, 0), (t0, 0), (t0 + d * .35, dx, "out"), (t0 + d * .7, -dx * .25, "in"), (t0 + d, 0, "out")],
            "y": [(0, 0), (t0, 0), (t0 + d * .35, dy, "out"), (t0 + d * .7, -dy * .3, "in"), (t0 + d, 0, "out")],
            "r": [(0, 0), (t0, 0), (t0 + d * .35, r, "out"), (t0 + d * .7, -r * .35, "in"), (t0 + d, 0, "out")]}


def sgn(i):
    return 1 if i % 2 else -1


GA, GA_ALPHA = twinkle(.62, .78, 1.04, 90)
GB, GB_ALPHA = twinkle(.78, .94, 1.2, -90, 1.1)

parts = [{"name": "zip", "mask": ZIP, "pivot": (495, 300), "parent": "bag"}]
parts += [{"name": n, "mask": MASKS[n], "pivot": piv, "parent": "bag"} for n, (_, piv) in BUDS.items()]
parts += [
    {"name": "bag", "mask": "rest", "pivot": BOTTOM},
    # not drawn: repairs the plastic under all the buds in ONE pass (a fill sees holes cut by other
    # parts as transparent, so repairing them bud by bud left the bag see-through). Faint: it only
    # marks the holes. (The seal only ever stretches over its own hole, so that one needs no repair.)
    {"name": "under", "mask": ("and", ("or", *MASKS.values()), np.full((1000, 1000), .05, np.float32)),
     "exclusive": False, "parent": "bag", "fill": "bag"},
    {"name": "aroma", "sprite": "puff", "args": {"color": (214, 240, 178)}, "size": 20, "at": (505, 120), "hidden": True, "parent": "bag"},
    {"name": "glint_a", "sprite": "sparkle", "size": 14, "at": (215, 330), "hidden": True, "parent": "bag"},
    {"name": "glint_b", "sprite": "sparkle", "size": 11, "at": (775, 760), "hidden": True, "parent": "bag"},
]

RIG = {
    "id": "L8",
    "parts": parts,
    "draw": ["bag", "zip"] + list(BUDS) + ["aroma", "glint_a", "glint_b"],
    "anims": {
        # the bag breathes while the loose buds settle one after another round the pile
        "idle": {"dur": 2.7, "bones": {
            "bag": {"sx": [(0, 1), (1.0, 1.014, "soft"), (1.5, 1.014), (2.5, 1, "soft")],
                    "sy": [(0, 1), (1.0, .99, "soft"), (1.5, .99), (2.5, 1, "soft")]},
            "zip": {"sy": [(0, 1), (.9, 1.035, "soft"), (1.6, 1.035), (2.5, 1, "soft")]},
            "bud_top": jostle(.15, .2, 1.0, -6),
            "bud_r": jostle(.5, .8, .4, -5),
            "bud_b": jostle(.85, .3, -.8, 6),
            "bud_l": jostle(1.15, -.8, .3, 5),
            "bud_ul": jostle(1.45, -.4, .7, 7, .38),
            "bud_br": jostle(1.75, .55, -.55, -4),
            "bud_ur": jostle(2.05, .4, .7, -7, .38),
        }},
        # set down hard: the bag squashes on its bottom, the buds lag, drop and bounce
        "land": {"dur": .55, "bones": {
            "bag": {"sy": [(0, 1), (.08, .94, "in"), (.22, 1.03, "out"), (.38, .99), (.55, 1)],
                    "sx": [(0, 1), (.08, 1.035, "in"), (.22, .985, "out"), (.38, 1.004), (.55, 1)]},
            "zip": {"sy": [(0, 1), (.08, 1, "in"), (.22, 1.05, "out"), (.4, 1)]},
            **{n: {"y": [(0, 0), (.1, -1.0 - .25 * (i % 3), "in"), (.25, .8 + .2 * (i % 2), "out"), (.4, -.15), (.55, 0)],
                   "r": [(0, 0), (.12, 3 * sgn(i), "out"), (.3, -2 * sgn(i)), (.55, 0)]}
               for i, n in enumerate(BUDS)},
        }},
        # a hop and a shake: the buds fly about inside, a puff of aroma escapes the seal, the plastic glints
        "win": {"dur": 1.45, "bones": {
            "bag": {"y": [(0, 0), (.1, 0), (.26, 3.2, "out"), (.4, 0, "in"), (.52, .6, "out"), (.62, 0, "in")],
                    "sy": [(0, 1), (.1, .94, "in"), (.24, 1.05, "out"), (.4, .95, "in"), (.54, 1.02, "out"), (.68, 1)],
                    "sx": [(0, 1), (.1, 1.035, "in"), (.24, .975, "out"), (.4, 1.03, "in"), (.54, .99, "out"), (.68, 1)],
                    "r": [(0, 0), (.62, 0), (.74, 3.0, "out"), (.86, -3.0), (.98, 2.2), (1.1, -1.2), (1.24, .4), (1.38, 0)]},
            "zip": {"sy": [(0, 1), (.24, 1.06, "out"), (.42, 1.0, "in"), (.62, 1.0), (.7, 1.07, "out"), (1.1, 1.02), (1.35, 1)]},
            **{n: {"y": [(0, 0), (.12, 0), (.26, -.6 - .15 * (i % 3), "out"), (.42, 1.0 + .2 * (i % 2), "out"), (.56, -.35, "in"), (.66, 0, "out"),
                         (.8, .4 * sgn(i)), (.95, -.3 * sgn(i)), (1.1, .2 * sgn(i)), (1.3, 0)],
                   "x": [(0, 0), (.66, 0), (.78, -.75 * sgn(i)), (.9, .75 * sgn(i)), (1.04, -.45 * sgn(i)), (1.2, .15 * sgn(i)), (1.36, 0)],
                   "r": [(0, 0), (.26, -4 * sgn(i)), (.46, 5 * sgn(i)), (.66, 0), (.8, -6 * sgn(i)), (.95, 5 * sgn(i)), (1.12, -2.2 * sgn(i)), (1.32, 0)]}
               for i, n in enumerate(BUDS)},
            "aroma": {"y": [(0, 0), (.66, 0), (1.36, 8, "out"), (1.38, 0, "step")],
                      "x": [(0, 0), (.66, 0), (1.0, -1.5), (1.36, 1.2), (1.38, 0, "step")],
                      "sx": [(0, 1), (.66, .45, "step"), (1.36, 1.25, "out"), (1.38, 1, "step")],
                      "sy": [(0, 1), (.66, .45, "step"), (1.36, 1.15, "out"), (1.38, 1, "step")]},
            "glint_a": GA, "glint_b": GB,
        }, "alpha": {
            "aroma": [(0, 0), (.66, 0, "step"), (.74, .9), (1.36, 0, "in")],
            "glint_a": GA_ALPHA, "glint_b": GB_ALPHA,
        }},
    },
}
