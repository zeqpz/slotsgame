# H4 - Fresh kicks. A pair of high-tops hung up by their laces: they sway from the knot at the
# top, the front shoe swinging a beat behind the back one and knocking back against it.
# Land: they drop onto the laces, bob and swing. Win: the front shoe kicks out, the pair
# swings high, the shoes clack together (a little puff) and the clean white toe caps glint.
KNOT = (520, 34)               # where the laces hang from
JOIN = (604, 306)              # where the front shoe's laces run into its collar: it swings about here

# the front shoe, from the top of its collar round its sole and toe and up the side of its laces
FRONT = ("poly", [(598, 300), (650, 298), (672, 280), (680, 266), (870, 266), (906, 330), (928, 420), (942, 480),
                  (956, 560), (966, 640), (965, 662), (915, 716), (870, 744), (790, 798), (710, 846), (620, 881),
                  (500, 903), (380, 906), (300, 897), (242, 864), (238, 800), (282, 750), (340, 700), (400, 662),
                  (446, 646), (462, 610), (470, 575), (490, 545), (520, 510), (545, 480), (575, 450), (592, 425),
                  (598, 380), (600, 330)])
# the back shoe's own colours (not its white sticker rim): only near these does lifting the front
# shoe need repairing - everywhere else the front shoe hangs over open air
BACK_ART = ("minus", ("opaque",), ("or", FRONT, ("color", "#ffffff", 40)))

REST = {"x": 0, "y": 0, "r": 0, "sx": 1, "sy": 1}


def shown(on, off, dur, **chans):
    out = {}
    for ch, keys in chans.items():
        rest = REST[ch]
        out[ch] = [(0, rest), (on, keys[0][1], "step")] + list(keys[1:]) + [(off, rest, "step"), (dur, rest)]
    return out


def twinkle(on, peak, off, dur, size=1.15, spin=90):
    return shown(on, off + .02, dur, sx=[(on, .3), (peak, size, "out"), (off, .2, "in")],
                 sy=[(on, .3), (peak, size, "out"), (off, .2, "in")], r=[(on, 0), (off, spin, "linear")])


def fade(on, full, hold, off, peak=1.0):
    return [(0, 0), (on, 0, "step"), (full, peak), (hold, peak), (off, 0, "in")]


RIG = {
    "id": "H4",
    "parts": [
        {"name": "front", "mask": FRONT, "pivot": JOIN, "parent": "back"},
        # never shown: repairs the back shoe only where it really lies under the front one
        # (not along the top of the front collar: a gap opening there between the two collars
        # should show daylight, not a smear)
        {"name": "front_patch", "mask": ("minus", ("and", FRONT, ("grow", BACK_ART, 34)), ("rect", 612, 240, 980, 322)),
         "exclusive": False, "hidden": True,
         "parent": "back", "fill": "back"},
        {"name": "back", "mask": "rest", "pivot": KNOT, "parent": "wire"},
        {"name": "wire", "sprite": "sparkle", "size": 4, "at": KNOT, "pivot": KNOT, "hidden": True},   # never shown: the swing
        {"name": "clack", "sprite": "puff", "size": 14, "at": (452, 612), "hidden": True, "parent": "back"},
        {"name": "glint_b", "sprite": "sparkle", "size": 14, "at": (215, 515), "hidden": True, "parent": "back"},
        {"name": "glint_f", "sprite": "sparkle", "size": 16, "at": (455, 705), "hidden": True, "parent": "front"},
    ],
    "draw": ["wire", "front_patch", "back", "front", "clack", "glint_b", "glint_f"],
    "anims": {
        # a breeze: the pair sways on its laces, the front shoe a beat behind - it swings out and
        # knocks back against the back shoe (never past it: that would uncover the back shoe's
        # hidden heel)
        "idle": {"dur": 2.8, "bones": {
            "wire": {"r": [(0, 0), (.5, 3.2), (1.12, -2.6), (1.7, 1.4), (2.2, -.5), (2.6, 0)]},
            "front": {"r": [(0, 0), (.42, -2.0), (.86, 0, "in"), (.96, -.5, "out"), (1.06, 0, "in"), (1.44, -1.4), (1.86, 0, "in"),
                            (1.95, -.3, "out"), (2.04, 0, "in")]},
            "glint_f": twinkle(1.9, 2.06, 2.36, 2.8),
        }, "alpha": {"glint_f": fade(1.9, 2.0, 2.06, 2.36)}},
        # dropped onto the laces: a bob on the stretch of the laces, then a little swing
        "land": {"dur": .55, "bones": {
            "wire": {"y": [(0, 0), (.08, -2.2, "in"), (.2, .9, "out"), (.34, -.3), (.46, 0)],
                     "sy": [(0, 1), (.08, 1.025, "in"), (.2, .99, "out"), (.34, 1)],
                     "r": [(0, 0), (.12, 1.4), (.3, -1.0), (.45, .3), (.55, 0)]},
            "front": {"r": [(0, 0), (.1, -2.2, "out"), (.24, 0, "in"), (.32, -.7, "out"), (.42, 0, "in")]},
        }},
        # a kick: the front shoe flicks out, the pair swings up and back, the shoes clack together
        "win": {"dur": 1.4, "bones": {
            "wire": {"r": [(0, 0), (.14, -1.5), (.42, 7, "out"), (.72, -4.5, "inout"), (.98, 2.2), (1.2, -.8), (1.4, 0)],
                     "y": [(0, 0), (.14, -1), (.42, 2.5, "out"), (.72, 0), (1.4, 0)]},
            "front": {"r": [(0, 0), (.36, -6.5, "out"), (.56, 0, "in"), (.66, -1.6, "out"), (.76, 0, "in"), (.84, -.4, "out"), (.92, 0, "in")]},
            "clack": shown(.55, 1.05, 1.4, x=[(.55, 0), (1.0, -3, "out")], y=[(.55, 0), (1.0, -2.5, "out")],
                           sx=[(.55, .4), (1.0, 1.2, "out")], sy=[(.55, .4), (1.0, 1.1, "out")]),
            "glint_b": twinkle(.4, .56, .86, 1.4, size=1.25),
            "glint_f": twinkle(.62, .78, 1.08, 1.4, size=1.3, spin=-90),
        }, "alpha": {
            "clack": fade(.55, .6, .66, 1.0, peak=.95),
            "glint_b": fade(.4, .5, .56, .86),
            "glint_f": fade(.62, .72, .78, 1.08),
        }},
    },
}
