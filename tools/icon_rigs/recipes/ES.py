# ES - Extreme scatter: "XXFS" in purple dripping graffiti. Like the bonus scatter, the paint is
# still wet: the drips under each letter ooze longer and snap back in turn, and a little ripple
# runs through the word. Land: the letters squash left to right and the drips whip down and spring
# back. Win: a wave - X, X, F, S hop and slam down one after another, flinging their drips, and
# the piece sparkles. (The page adds a glow and a landing punch on top, so it stays lively, not busy.)
BLOB = ("grow", ("cc", ("opaque",), 100, 120), 2)   # the whole piece (letters + drips, with its soft edge) - not the loose spatter
# (the loose spatter dots ride with the letter on their side)
H = 302

# the four letters share one black outline: split along the dark seams between them
SEAM_XX = [(168, 0), (168, 56), (163, 62), (160, 67), (157, 71), (155, 77), (155, 95), (158, 140), (160, 166), (162, 176),
           (163, 182), (166, 186), (168, 190), (171, 194), (174, 198), (176, 202), (175, 210), (176, 216), (177, H)]   # the line between the X's arms, through the diamond
SEAM_XF = [(281, 0), (281, 150), (286, 170), (292, 185), (293, 240), (290, H)]                          # down the gap
SEAM_FS = [(395, 0), (395, 62), (393, 70), (391, 76), (389, 84), (381, 92), (380, 112), (380, 125), (385, 135), (386, 145),
           (380, 155), (377, 170), (377, 215), (383, 240), (383, H)]                                    # F's bar end, round the S's bowl
SIDES = {
    "x1": ("poly", [(0, 0)] + SEAM_XX + [(0, H)]),
    "x2": ("poly", SEAM_XX + SEAM_XF[::-1]),
    "f": ("poly", SEAM_XF + SEAM_FS[::-1]),
    "s": ("poly", SEAM_FS + [(512, H), (512, 0)]),
}
CUT = 230                  # the drips hang below this line; each letter's run stretches from its middle
PIVOTS = {"x1": (100, 228), "x2": (225, 226), "f": (330, 240), "s": (430, 236)}   # letter bottoms
RUN_X = {"x1": 95, "x2": 230, "f": 325, "s": 435}
LOWER = ("rect", -10, CUT, 530, H + 10)


def twinkle(t0, t1, t2, spin=90, peak=1.2):
    """a glint: pops in at t0, peaks at t1, gone by t2 - every channel back at rest by the end"""
    bones = {"sx": [(0, 1), (t0, .3, "step"), (t1, peak, "out"), (t2, .2, "in"), (t2 + .02, 1, "step")],
             "sy": [(0, 1), (t0, .3, "step"), (t1, peak, "out"), (t2, .2, "in"), (t2 + .02, 1, "step")],
             "r": [(0, 0), (t0, 0), (t2, spin, "linear"), (t2 + .02, 0, "step")]}
    return bones, [(0, 0), (t0, 0, "step"), (t0 + .1, 1), (t2, 0)]


def ooze(t0, long=1.22, d=.65):
    """a run of drips creeping longer, then snapping back up with a wobble"""
    return {"sy": [(0, 1), (t0, 1), (t0 + d, long, "in"), (t0 + d + .1, .94, "out"), (t0 + d + .22, 1.03), (t0 + d + .34, 1)]}


def whip(t0, long=1.25, d=.48):
    """drips flung down by a landing at t0 and springing back (over d seconds)"""
    k = d / .48
    return {"sy": [(0, 1), (t0, 1), (t0 + .1 * k, long, "out"), (t0 + .24 * k, .92, "inout"), (t0 + .36 * k, 1.04), (t0 + d, 1)]}


def hop(t0, h, up=.15, down=.13):
    """a letter's hop from its bottom: crouch, spring up stretched, slam down squashed, settle"""
    t1, t2, t3 = t0 + .07, t0 + .07 + up, t0 + .07 + up + down
    return {"y": [(0, 0), (t1, 0), (t2, h, "out"), (t3, 0, "in")],
            "sy": [(0, 1), (t0, 1), (t1, .93, "in"), (t2, 1.07, "out"), (t3, .9, "in"), (t3 + .12, 1.03, "out"), (t3 + .24, 1)],
            "sx": [(0, 1), (t0, 1), (t1, 1.05, "in"), (t2, .96, "out"), (t3, 1.07, "in"), (t3 + .12, .99, "out"), (t3 + .24, 1)]}


def bob(t0, h=1.0):
    """a small ripple bob"""
    return {"y": [(0, 0), (t0, 0), (t0 + .12, h, "out"), (t0 + .26, 0, "in")],
            "sy": [(0, 1), (t0, 1), (t0 + .12, 1.03, "out"), (t0 + .26, .97, "in"), (t0 + .38, 1.005, "out"), (t0 + .48, 1)],
            "sx": [(0, 1), (t0, 1), (t0 + .12, .985, "out"), (t0 + .26, 1.02, "in"), (t0 + .38, 1, "out")]}


GA, GA_ALPHA = twinkle(.62, .78, 1.04, 90, 1.25)
GB, GB_ALPHA = twinkle(.8, .96, 1.22, -90)
GC, GC_ALPHA = twinkle(.98, 1.12, 1.38, 90, 1.1)

L = list(SIDES)
parts = [{"name": "drip_" + k, "mask": ("and", SIDES[k], LOWER, BLOB), "pivot": (RUN_X[k], CUT), "parent": "letter_" + k} for k in L]
parts += [{"name": "letter_" + k, "mask": SIDES[k], "pivot": PIVOTS[k]} for k in L]
parts += [
    {"name": "glint_a", "sprite": "sparkle", "size": 15, "at": (60, 70), "hidden": True, "parent": "letter_x1"},
    {"name": "glint_b", "sprite": "sparkle", "size": 12, "at": (330, 62), "hidden": True, "parent": "letter_f"},
    {"name": "glint_c", "sprite": "sparkle", "size": 13, "at": (470, 120), "hidden": True, "parent": "letter_s"},
]

RIG = {
    "id": "ES",
    "parts": parts,
    "draw": ["drip_" + k for k in L] + ["letter_" + k for k in L] + ["glint_a", "glint_b", "glint_c"],
    "anims": {
        # wet paint: each letter's drips ooze and snap back in turn; one ripple runs along the word
        "idle": {"dur": 2.6, "bones": {
            "drip_x1": ooze(.05), "drip_f": ooze(.4, 1.25), "drip_x2": ooze(.8, 1.2, .6), "drip_s": ooze(1.2, 1.24),
            **{"letter_" + k: bob(1.55 + .1 * i) for i, k in enumerate(L)},
        }},
        # dropped in: the letters squash left to right, every run of drips whips down and springs back
        "land": {"dur": .55, "bones": {
            **{"letter_" + k: {"sy": [(0, 1), (.025 * i, 1), (.025 * i + .06, .9, "in"), (.025 * i + .18, 1.04, "out"), (.025 * i + .32, .99), (.025 * i + .44, 1)],
                               "sx": [(0, 1), (.025 * i, 1), (.025 * i + .06, 1.06, "in"), (.025 * i + .18, .98, "out"), (.025 * i + .32, 1.005), (.025 * i + .44, 1)]}
               for i, k in enumerate(L)},
            **{"drip_" + k: whip(.04 + .02 * i, 1.22, .42) for i, k in enumerate(L)},
        }},
        # a wave: X, X, F, S hop one after another; each slam flings its drips; sparkles
        "win": {"dur": 1.45, "bones": {
            **{"letter_" + k: hop(.13 * i, 3.6) for i, k in enumerate(L)},
            **{"drip_" + k: whip(.13 * i + .35, 1.3) for i, k in enumerate(L)},
            "glint_a": GA, "glint_b": GB, "glint_c": GC,
        }, "alpha": {"glint_a": GA_ALPHA, "glint_b": GB_ALPHA, "glint_c": GC_ALPHA}},
    },
}
