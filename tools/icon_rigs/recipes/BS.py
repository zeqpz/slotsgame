# BS - Bonus scatter: "FS" in green dripping graffiti. The paint is still wet: each run of drips
# oozes longer and snaps back up, one after another, and the two letters take turns giving a
# little bounce. Land: both letters squash and the drips whip down and spring back. Win: F then S
# hop and slam down, the drips stretch on every landing, and the piece sparkles. (The page adds a
# glow and a landing punch on top of this, so it stays lively but not busy.)
BLOB = ("grow", ("cc", ("opaque",), 125, 150), 2)   # the whole piece (letters + drips, with its soft edge) - not the loose spatter
# (the loose spatter dots ride with the letter on their side)

# F and S share their black outline: split along the middle of it - between the F's green rim
# and the S's (they touch at y 75-115), through the notch, down past the S's lower rim
SEAM = [(300, 0), (286, 30), (274, 40), (271, 48), (266, 56), (264, 64), (261, 72), (259, 80), (258, 110), (252, 122),
        (250, 140), (248, 160), (243, 185), (239, 205), (234, 230), (233, 260), (230, 300), (230, 386)]
F_SIDE = ("poly", [(0, 0)] + SEAM + [(0, 386)])
S_SIDE = ("poly", SEAM + [(512, 386), (512, 0)])
# ... but below the top each letter keeps the WHOLE shared black band, so when one hops away
# from the other both outlines stay closed (the band is drawn twice at rest - black on black).
# (Not at the top: there the band is the silhouette, and a shared copy stuck out as a spike.)
DARK = ("color", "#000000", 60)
BAND = ("and", DARK, ("or", ("poly", [(238, 117), (255, 117), (255, 142), (238, 142)]),
                     ("poly", [(231, 180), (250, 180), (246, 200), (240, 225), (238, 262), (229, 262), (231, 225)])))

# runs of drips, each cut on a line through the black just under its letter's bottom stroke;
# a run hangs from (and stretches about) the middle of that line, tucked behind its letter
DRIPS = {   # name: (polygon, pivot, letter)
    "drip_f1": ([(58, 302), (120.5, 302), (120.5, 386), (58, 386)], (89, 302), "f"),
    "drip_f2": ([(120.5, 304), (178, 290), (178, 386), (120.5, 386)], (150, 297), "f"),
    "drip_f3": ([(184, 201), (224, 201), (224, 266), (184, 266)], (204, 201), "f"),
    "drip_s1": ([(238, 272), (300, 290), (300, 372), (238, 372)], (269, 281), "s"),
    "drip_s2": ([(372, 303), (425, 303), (425, 386), (372, 386)], (398, 303), "s"),
    "drip_s3": ([(425, 300), (482, 276), (482, 386), (425, 386)], (454, 288), "s"),
}


def twinkle(t0, t1, t2, spin=90, peak=1.2):
    """a glint: pops in at t0, peaks at t1, gone by t2 - every channel back at rest by the end"""
    bones = {"sx": [(0, 1), (t0, .3, "step"), (t1, peak, "out"), (t2, .2, "in"), (t2 + .02, 1, "step")],
             "sy": [(0, 1), (t0, .3, "step"), (t1, peak, "out"), (t2, .2, "in"), (t2 + .02, 1, "step")],
             "r": [(0, 0), (t0, 0), (t2, spin, "linear"), (t2 + .02, 0, "step")]}
    return bones, [(0, 0), (t0, 0, "step"), (t0 + .1, 1), (t2, 0)]


def ooze(t0, long=1.2, d=.7):
    """a run of drips creeping longer, then snapping back up with a wobble"""
    return {"sy": [(0, 1), (t0, 1), (t0 + d, long, "in"), (t0 + d + .1, .94, "out"), (t0 + d + .22, 1.03), (t0 + d + .34, 1)]}


def whip(t0, long=1.25, d=.48):
    """drips flung down by a landing at t0 and springing back (over d seconds)"""
    k = d / .48
    return {"sy": [(0, 1), (t0, 1), (t0 + .1 * k, long, "out"), (t0 + .24 * k, .92, "inout"), (t0 + .36 * k, 1.04), (t0 + d, 1)]}


def hop(t0, h, up=.16, down=.14):
    """a letter's hop from its bottom: crouch, spring up stretched, slam down squashed, settle"""
    t1, t2, t3 = t0 + .08, t0 + .08 + up, t0 + .08 + up + down
    return {"y": [(0, 0), (t1, 0), (t2, h, "out"), (t3, 0, "in")],
            "sy": [(0, 1), (t0, 1), (t1, .93, "in"), (t2, 1.07, "out"), (t3, .9, "in"), (t3 + .12, 1.03, "out"), (t3 + .24, 1)],
            "sx": [(0, 1), (t0, 1), (t1, 1.05, "in"), (t2, .96, "out"), (t3, 1.07, "in"), (t3 + .12, .99, "out"), (t3 + .24, 1)]}


GA, GA_ALPHA = twinkle(.5, .66, .92, 90, 1.25)
GB, GB_ALPHA = twinkle(.7, .86, 1.12, -90)
GC, GC_ALPHA = twinkle(.88, 1.02, 1.28, 90, 1.1)

parts = [{"name": n, "mask": ("and", ("poly", poly), BLOB), "pivot": piv, "parent": "letter_" + l} for n, (poly, piv, l) in DRIPS.items()]
RUNS = ("or", *[("and", ("poly", poly), BLOB) for poly, _, _ in DRIPS.values()])
parts += [
    {"name": "letter_f", "mask": ("or", F_SIDE, BAND), "pivot": (130, 300)},
    # (not exclusive, to share the band: so it leaves the drip runs out by hand)
    {"name": "letter_s", "mask": ("minus", ("or", S_SIDE, BAND), RUNS), "exclusive": False, "pivot": (370, 302)},
    {"name": "glint_a", "sprite": "sparkle", "size": 16, "at": (70, 60), "hidden": True, "parent": "letter_f"},
    {"name": "glint_b", "sprite": "sparkle", "size": 13, "at": (450, 90), "hidden": True, "parent": "letter_s"},
    {"name": "glint_c", "sprite": "sparkle", "size": 11, "at": (300, 230), "hidden": True, "parent": "letter_s"},
]

RIG = {
    "id": "BS",
    "parts": parts,
    "draw": list(DRIPS) + ["letter_f", "letter_s", "glint_a", "glint_b", "glint_c"],
    "anims": {
        # wet paint: the drip runs ooze and snap back in turn; each letter gives one small bounce
        "idle": {"dur": 2.5, "bones": {
            "drip_f1": ooze(.05), "drip_s2": ooze(.4, 1.24), "drip_f3": ooze(.75, 1.16, .6),
            "drip_s1": ooze(1.05), "drip_f2": ooze(1.35, 1.18), "drip_s3": ooze(1.6, 1.2, .55),
            "letter_f": {"y": [(0, 0), (.3, 0), (.42, 1.2, "out"), (.56, 0, "in")],
                         "sy": [(0, 1), (.3, 1), (.42, 1.035, "out"), (.56, .96, "in"), (.68, 1.01, "out"), (.8, 1)],
                         "sx": [(0, 1), (.3, 1), (.42, .98, "out"), (.56, 1.03, "in"), (.68, .995, "out"), (.8, 1)]},
            "letter_s": {"y": [(0, 0), (1.15, 0), (1.27, 1.2, "out"), (1.41, 0, "in")],
                         "sy": [(0, 1), (1.15, 1), (1.27, 1.035, "out"), (1.41, .96, "in"), (1.53, 1.01, "out"), (1.65, 1)],
                         "sx": [(0, 1), (1.15, 1), (1.27, .98, "out"), (1.41, 1.03, "in"), (1.53, .995, "out"), (1.65, 1)]},
        }},
        # dropped in: both letters squash (S a beat after F), every run of drips whips down and springs back
        "land": {"dur": .55, "bones": {
            "letter_f": {"sy": [(0, 1), (.06, .9, "in"), (.18, 1.04, "out"), (.32, .99), (.45, 1)],
                         "sx": [(0, 1), (.06, 1.06, "in"), (.18, .98, "out"), (.32, 1.005), (.45, 1)]},
            "letter_s": {"sy": [(0, 1), (.03, 1), (.09, .9, "in"), (.21, 1.04, "out"), (.35, .99), (.48, 1)],
                         "sx": [(0, 1), (.03, 1), (.09, 1.06, "in"), (.21, .98, "out"), (.35, 1.005), (.48, 1)]},
            **{n: whip(.03 + .015 * i, 1.22, .42) for i, n in enumerate(DRIPS)},
        }},
        # F hops, then S; each slam flings its drips; sparkles
        "win": {"dur": 1.4, "bones": {
            "letter_f": hop(0, 4.5),
            "letter_s": hop(.24, 4.5),
            **{n: whip(.38 + .03 * i if l == "f" else .62 + .03 * i, 1.3) for i, (n, (_, _, l)) in enumerate(DRIPS.items())},
            "glint_a": GA, "glint_b": GB, "glint_c": GC,
        }, "alpha": {"glint_a": GA_ALPHA, "glint_b": GB_ALPHA, "glint_c": GC_ALPHA}},
    },
}
