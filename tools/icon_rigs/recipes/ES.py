# ES - Extreme scatter: "XFS" in purple dripping graffiti (it was XXFS until 2026-10-24: the first X
# is cut away in tools/letter_art/make.py). Like the bonus scatter, the paint is still wet: the
# drips under each letter ooze longer and snap back in turn, and a little ripple runs through the
# word. Land: the letters squash left to right and the drips whip down and spring back. Win: a
# wave - X, F, S hop and slam down one after another, flinging their drips, and the piece
# sparkles. (The page adds a glow and a landing punch on top, so it stays lively, not busy.)
# Written in 1x px of the 420x302 canvas; the source is the 2x render (840x604), see src_scale.
BLOB = ("grow", ("opaque",), 2)   # the whole piece (letters + drips, with its soft edge); the cartoon art (tools/letter_art) has no loose spatter
# (the loose spatter dots ride with the letter on their side)
H = 302

W = 420

# the three letters share one black outline: split along the dark seams between them
SEAM_XF = [(168.8, 0), (168.8, 150), (173.8, 170), (179.8, 185), (180.8, 240), (177.8, H)]              # down the gap
# F/S (measured on the XFS render): down the notch between the F's bar and the S's top, across
# the short stretch where their paint runs together, down the middle of the black line they share,
# then along the middle of the gap between the F's stem and the S's bowl
SEAM_FS = [(276, 0), (276, 30), (283, 42), (283, 72), (276, 88), (268, 96), (266.5, 102), (267, 114), (268, 120), (271, 128),
           (276, 138), (266.5, 144), (254, 150), (252, 162), (250.5, 174), (250, 186), (252, 198), (257, 210), (259, 222),
           (265, 234), (266, 252), (262, 270), (262, H)]
SIDES = {
    "x": ("poly", [(0, 0)] + SEAM_XF + [(0, H)]),
    "f": ("poly", SEAM_XF + SEAM_FS[::-1]),
    "s": ("poly", SEAM_FS + [(W, H), (W, 0)]),
}
CUT = 230                  # the drips hang below this line; each letter's run stretches from its middle
PIVOTS = {"x": (112.8, 226), "f": (217.8, 240), "s": (317.8, 236)}   # letter bottoms
RUN_X = {"x": 117.8, "f": 212.8, "s": 322.8}
LOWER = ("rect", -10, CUT, W + 18, H + 10)


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
    {"name": "glint_a", "sprite": "sparkle", "size": 15, "at": (72, 62), "hidden": True, "parent": "letter_x"},
    {"name": "glint_b", "sprite": "sparkle", "size": 12, "at": (217.8, 62), "hidden": True, "parent": "letter_f"},
    {"name": "glint_c", "sprite": "sparkle", "size": 13, "at": (357.8, 120), "hidden": True, "parent": "letter_s"},
]

RIG = {
    "id": "ES",
    "src_scale": 2,
    "parts": parts,
    "draw": ["drip_" + k for k in L] + ["letter_" + k for k in L] + ["glint_a", "glint_b", "glint_c"],
    "anims": {
        # wet paint: each letter's drips ooze and snap back in turn; one ripple runs along the word
        "idle": {"dur": 2.6, "bones": {
            "drip_x": ooze(.05), "drip_f": ooze(.55, 1.25), "drip_s": ooze(1.1, 1.24),
            **{"letter_" + k: bob(1.55 + .1 * i) for i, k in enumerate(L)},
        }},
        # dropped in: the letters squash left to right, every run of drips whips down and springs back
        "land": {"dur": .55, "bones": {
            **{"letter_" + k: {"sy": [(0, 1), (.025 * i, 1), (.025 * i + .06, .9, "in"), (.025 * i + .18, 1.04, "out"), (.025 * i + .32, .99), (.025 * i + .44, 1)],
                               "sx": [(0, 1), (.025 * i, 1), (.025 * i + .06, 1.06, "in"), (.025 * i + .18, .98, "out"), (.025 * i + .32, 1.005), (.025 * i + .44, 1)]}
               for i, k in enumerate(L)},
            **{"drip_" + k: whip(.04 + .02 * i, 1.22, .42) for i, k in enumerate(L)},
        }},
        # a wave: X, F, S hop one after another; each slam flings its drips; sparkles
        "win": {"dur": 1.45, "bones": {
            **{"letter_" + k: hop(.16 * i, 3.6) for i, k in enumerate(L)},
            **{"drip_" + k: whip(.16 * i + .35, 1.3) for i, k in enumerate(L)},
            "glint_a": GA, "glint_b": GB, "glint_c": GC,
        }, "alpha": {"glint_a": GA_ALPHA, "glint_b": GB_ALPHA, "glint_c": GC_ALPHA}},
    },
}
