# L7 - Hoodie. A worn hoodie, so it breathes: the chest rises and falls (the body stretches up
# from the hem) and it sways a touch, while the two drawstrings swing from their eyelets, each a
# two-piece cord whose lower half trails its upper half. Land: dropped on the reel, it squashes
# on its hem and the cords bounce. Win: hype - it crouches, hops and lands, rocks side to side,
# the cords whip about, and the chest tag glints. (The hood stays part of the body: lifted on its
# own it opened seams along the shoulder folds.)
import numpy as np

HEM = (510, 945)            # the waistband's bottom: the body breathes and sways from here

# drawstrings: a tight strip round each cord (its two ink lines + the grey cord between), cut in
# two where the cord reaches the tag - the upper half lies on plain cloth, the lower on the tag
STR_L1 = ("poly", [(383, 162), (388, 200), (393, 250), (396, 290), (416, 290), (412, 250), (406, 200), (400, 162)])
STR_L2 = ("poly", [(396, 290), (397, 300), (404, 350), (409, 380), (411, 393), (417, 400), (424, 393), (425, 380),
                   (421, 350), (417, 300), (416, 290)])
STR_R1 = ("poly", [(442, 160), (442, 200), (443, 245), (464, 245), (464, 200), (466, 160)])
STR_R2 = ("poly", [(443, 245), (443, 250), (449, 300), (454, 350), (456, 380), (457, 392), (462, 399), (468, 392),
                   (470, 380), (472, 350), (468, 300), (464, 250), (464, 245)])
LOGO_C = ("color", "#8b8b8b", 50)                       # the light grey tag on the chest
CHEST = ("poly", [(225, 290), (330, 240), (520, 165), (725, 240), (725, 565), (370, 565), (225, 440)])
CORDS = ("or", *[("minus", m, LOGO_C) for m in (STR_L1, STR_L2, STR_R1, STR_R2)])    # the cords' own ink
LOGO = ("and", ("minus", ("grow", LOGO_C, 2), CORDS), CHEST)


def twinkle(t0, t1, t2, spin=90, peak=1.2):
    """a glint: pops in at t0, peaks at t1, gone by t2 - every channel back at rest by the end"""
    bones = {"sx": [(0, 1), (t0, .3, "step"), (t1, peak, "out"), (t2, .2, "in"), (t2 + .02, 1, "step")],
             "sy": [(0, 1), (t0, .3, "step"), (t1, peak, "out"), (t2, .2, "in"), (t2 + .02, 1, "step")],
             "r": [(0, 0), (t0, 0), (t2, spin, "linear"), (t2 + .02, 0, "step")]}
    alpha = [(0, 0), (t0, 0, "step"), (t0 + .1, 1), (t2, 0)]
    return bones, alpha


GA, GA_ALPHA = twinkle(.30, .46, .72, 90)
GB, GB_ALPHA = twinkle(.44, .60, .86, -90, 1.25)
GC, GC_ALPHA = twinkle(.60, .74, 1.0, 90)

RIG = {
    "id": "L7",
    "parts": [
        {"name": "logo", "mask": LOGO, "pivot": (472, 372), "parent": "body"},
        {"name": "string_l", "mask": ("minus", STR_L1, LOGO_C), "pivot": (391, 163), "parent": "body"},
        {"name": "string_r", "mask": ("minus", STR_R1, LOGO_C), "pivot": (454, 161), "parent": "body"},
        {"name": "string_l2", "mask": ("minus", STR_L2, LOGO_C), "pivot": (406, 290), "parent": "string_l", "fill": "logo"},
        {"name": "string_r2", "mask": ("minus", STR_R2, LOGO_C), "pivot": (453, 245), "parent": "string_r", "fill": "logo"},
        {"name": "body", "mask": "rest", "pivot": HEM},
        # not drawn: repairs the body under the tag and the cords in ONE pass. (A fill sees
        # holes cut by other parts as transparent; repaired one part at a time, the body went
        # see-through round the cords.) Cut after the body, so it takes nothing from it.
        {"name": "under", "mask": ("and", ("or", LOGO, CORDS), np.full((1000, 1000), .05, np.float32)),   # faint: it only marks the holes
         "exclusive": False, "parent": "body", "fill": "body"},
        {"name": "glint_a", "sprite": "sparkle", "size": 15, "at": (300, 330), "hidden": True, "parent": "body"},
        {"name": "glint_b", "sprite": "sparkle", "size": 12, "at": (655, 292), "hidden": True, "parent": "body"},
        {"name": "glint_c", "sprite": "sparkle", "size": 10, "at": (470, 520), "hidden": True, "parent": "body"},
    ],
    "draw": ["body", "logo", "string_l", "string_l2", "string_r", "string_r2", "glint_a", "glint_b", "glint_c"],
    "anims": {
        # one slow breath with a lazy sway; the cords swing a beat behind the body, their tips later still
        "idle": {"dur": 2.8, "bones": {
            "body": {"y": [(0, 0), (1.1, .45, "soft"), (1.4, .45), (2.5, 0, "soft")],
                     "sy": [(0, 1), (1.1, 1.024, "soft"), (1.4, 1.024), (2.5, 1, "soft")],
                     "sx": [(0, 1), (1.1, .995, "soft"), (1.4, .995), (2.5, 1, "soft")],
                     "r": [(0, 0), (.9, 1.1, "soft"), (1.9, -.9, "soft"), (2.8, 0, "soft")]},
            "string_l": {"r": [(0, 0), (.55, -2.4, "soft"), (1.35, 2.0, "soft"), (2.1, -.9, "soft"), (2.8, 0, "soft")]},
            "string_l2": {"r": [(0, 0), (.75, -1.6, "soft"), (1.55, 1.6, "soft"), (2.3, -.6, "soft"), (2.8, 0, "soft")]},
            "string_r": {"r": [(0, 0), (.7, -2.0, "soft"), (1.5, 2.3, "soft"), (2.25, -.8, "soft"), (2.8, 0, "soft")]},
            "string_r2": {"r": [(0, 0), (.9, -1.4, "soft"), (1.7, 1.7, "soft"), (2.45, -.5, "soft"), (2.8, 0, "soft")]},
        }},
        # dropped onto the reel: squash on the hem, rebound; the cords keep falling, then bounce
        "land": {"dur": .55, "bones": {
            "body": {"sy": [(0, 1), (.08, .95, "in"), (.22, 1.025, "out"), (.38, .995), (.55, 1)],
                     "sx": [(0, 1), (.08, 1.025, "in"), (.22, .99, "out"), (.38, 1.002), (.55, 1)]},
            "string_l": {"r": [(0, 0), (.12, 2.2, "out"), (.3, -1.6), (.45, .5), (.55, 0)]},
            "string_l2": {"r": [(0, 0), (.16, 1.6, "out"), (.34, -1.2), (.5, .3), (.55, 0)]},
            "string_r": {"r": [(0, 0), (.13, -2.0, "out"), (.31, 1.5), (.46, -.4), (.55, 0)]},
            "string_r2": {"r": [(0, 0), (.17, -1.5, "out"), (.35, 1.1), (.5, -.3), (.55, 0)]},
        }},
        # hype: crouch, hop, land, then rock left-right-left; the cords trail the hop and whip on the rock
        "win": {"dur": 1.4, "bones": {
            "body": {"y": [(0, 0), (.1, 0), (.24, 3.2, "out"), (.38, 0, "in"), (.5, .5, "out"), (.6, 0, "in")],
                     "sy": [(0, 1), (.1, .95, "in"), (.22, 1.05, "out"), (.38, .955, "in"), (.52, 1.02, "out"), (.66, 1), (1.4, 1)],
                     "sx": [(0, 1), (.1, 1.03, "in"), (.22, .975, "out"), (.38, 1.025, "in"), (.52, .992, "out"), (.66, 1), (1.4, 1)],
                     "r": [(0, 0), (.4, 0), (.58, 2.8, "soft"), (.82, -2.8, "soft"), (1.04, 1.6, "soft"), (1.24, -.4, "soft"), (1.4, 0, "soft")]},
            "string_l": {"sy": [(0, 1), (.12, 1), (.24, .96, "out"), (.4, 1.04, "in"), (.52, .99), (.62, 1)],
                         "r": [(0, 0), (.4, 0), (.6, -3.6, "out"), (.84, 3.8), (1.06, -2.2), (1.26, .7), (1.4, 0)]},
            "string_l2": {"r": [(0, 0), (.24, 1.5, "out"), (.42, -1.5), (.66, -2.6), (.9, 2.8), (1.12, -1.4), (1.32, .4), (1.4, 0)]},
            "string_r": {"sy": [(0, 1), (.12, 1), (.25, .96, "out"), (.41, 1.04, "in"), (.53, .99), (.63, 1)],
                         "r": [(0, 0), (.4, 0), (.62, -3.2, "out"), (.86, 3.6), (1.08, -2.0), (1.28, .6), (1.4, 0)]},
            "string_r2": {"r": [(0, 0), (.25, -1.4, "out"), (.43, 1.4), (.68, -2.4), (.92, 2.6), (1.14, -1.2), (1.34, .3), (1.4, 0)]},
            "glint_a": GA, "glint_b": GB, "glint_c": GC,
        }, "alpha": {"glint_a": GA_ALPHA, "glint_b": GB_ALPHA, "glint_c": GC_ALPHA}},
    },
}
