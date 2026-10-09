# H2 - Glock. The slide is its own piece and runs along its rail: idle is a press check (the
# slide eased back and let slam home) with a shine running down the top; land is the gun
# settling in the hand. Win is a double tap: the trigger squeezes, the muzzle flashes, the
# gun kicks muzzle-up about the grip while the slide cycles, twice, and smoke drifts off.
import math

GRIP = (700, 640)                      # the hand: the gun kicks about here
MUZZLE = (40, 190)                     # the front of the slide, on the bore line
AXIS = math.atan(.2886)                # the slide's rail runs down-right at ~16 degrees
BACK = (math.cos(AXIS), -math.sin(AXIS))   # rearward along the rail, skeleton units (y up)

# the slide/frame seam is the long ink line under the slide: cut down its middle
SLIDE = ("poly", [(0, 40), (995, 40), (995, 499), (0, 212)])
TRIGGER_POLY = ("poly", [(405, 444), (478, 440), (504, 462), (522, 484), (514, 500), (470, 514), (430, 532),
                         (404, 550), (380, 556), (370, 548), (378, 520), (390, 488), (400, 462)])
TRIGGER = ("minus", TRIGGER_POLY, ("color", "#ffffff", 80))     # the blade and its ink, not the guard's white rim
HOUSING = ("and", ("ink",), ("poly", [(410, 418), (545, 418), (545, 492), (500, 492), (470, 462), (410, 450)]))

REST = {"x": 0, "y": 0, "r": 0, "sx": 1, "sy": 1}


def shown(on, off, dur, **chans):
    """Keys for a part hidden at rest: on its rest values until `on`, then the given keys
    (absolute times, the first at `on`), snapped back to rest at `off` once it has faded out."""
    out = {}
    for ch, keys in chans.items():
        rest = REST[ch]
        out[ch] = [(0, rest), (on, keys[0][1], "step")] + list(keys[1:]) + [(off, rest, "step"), (dur, rest)]
    return out


def fade(on, full, hold, off, peak=1.0):
    return [(0, 0), (on, 0, "step"), (full, peak), (hold, peak), (off, 0, "in")]


def rack(keys):
    """slide keys as distances back along the rail -> x/y channels"""
    return {"x": [(t, d * BACK[0], *e) for t, d, *e in keys], "y": [(t, d * BACK[1], *e) for t, d, *e in keys]}


def shot(t, kick=12):
    """one round at time t: (frame r keys, slide travel keys, trigger r keys)"""
    return ([(t, 0), (t + .07, -kick, "snap"), (t + .2, 1.2, "inout"), (t + .3, 0)],
            [(t, 0), (t + .045, 4.6, "snap"), (t + .13, 0, "in")],
            [(t - .14, 0), (t - .01, 9, "in"), (t + .08, 0, "out")])


S1, S2 = .20, .62
f1, s1, t1 = shot(S1, 12)
f2, s2, t2 = shot(S2, 10)

RIG = {
    "id": "H2",
    "parts": [
        {"name": "slide", "mask": SLIDE, "pivot": (500, 300), "parent": "frame"},
        # the trigger hangs from the frame and is drawn UNDER it: its root carries on up into the
        # housing (a copy - the frame keeps those pixels), so pulling it never opens a gap there,
        # and the open guard round the blade simply stays see-through as it swings
        {"name": "trigger", "mask": ("or", TRIGGER, HOUSING), "exclusive": False, "pivot": (452, 448), "parent": "frame"},
        # the frame also keeps a 4 px strip under the slide's lower edge (inside the seam's ink
        # line), so the antialiased cut never shows through at rest
        {"name": "frame", "mask": ("minus", ("rect", -10, -10, 1010, 1010), ("or", ("shrink", SLIDE, 4), TRIGGER)), "exclusive": False,
         "pivot": GRIP},
        {"name": "flash", "sprite": "sparkle", "size": 30, "args": {"color": (255, 190, 50)}, "at": (-14, 174),
         "hidden": True, "parent": "frame"},
        {"name": "flash_core", "sprite": "sparkle", "size": 15, "at": (2, 178), "hidden": True, "parent": "frame"},
        {"name": "smoke", "sprite": "puff", "size": 18, "args": {"color": (206, 206, 212)}, "at": (20, 170),
         "hidden": True, "parent": "frame"},
        {"name": "shine", "sprite": "sparkle", "size": 11, "at": (760, 300), "hidden": True, "parent": "slide"},
    ],
    "draw": ["trigger", "frame", "slide", "smoke", "flash", "flash_core", "shine"],
    "anims": {
        # press check: ease the slide back, peek, let it slam home; then a shine runs along the slide
        "idle": {"dur": 2.6, "bones": {
            "frame": {"r": [(0, 0), (.4, -1.6), (.95, -1.2), (1.02, .8, "snap"), (1.2, -.3), (1.45, 0)],
                      "x": [(0, 0), (.4, .4), (.95, .5), (1.02, -.3, "snap"), (1.3, 0)]},
            "slide": rack([(0, 0), (.42, 0), (.72, 3.4, "inout"), (.95, 3.4), (1.0, 0, "in")]),
            "shine": shown(1.4, 2.12, 2.6, x=[(1.4, 0), (2.1, -46, "inout")], y=[(1.4, 0), (2.1, 46 * math.tan(AXIS) - 1, "inout")],
                           sx=[(1.4, .3), (1.6, 1.1, "out"), (1.9, 1.0), (2.1, .2, "in")],
                           sy=[(1.4, .3), (1.6, 1.1, "out"), (1.9, 1.0), (2.1, .2, "in")],
                           r=[(1.4, 0), (2.1, -120, "linear")]),
        }, "alpha": {
            "shine": fade(1.4, 1.52, 1.95, 2.1),
        }},
        "land": {"dur": .55, "bones": {
            "frame": {"r": [(0, 0), (.09, 3.4, "out"), (.25, -1.8), (.4, .6), (.55, 0)],
                      "y": [(0, 0), (.08, -1.6, "in"), (.2, .6, "out"), (.36, 0)]},
            "slide": rack([(0, 0), (.07, 1.4, "out"), (.18, -.3, "in"), (.28, 0)]),
        }},
        "win": {"dur": 1.4, "bones": {
            "frame": {"r": [(0, 0), (S1, 0)] + f1[1:] + [(S2, 0)] + f2[1:] + [(1.4, 0)],
                      "x": [(0, 0), (S1, 0), (S1 + .06, 1.8, "snap"), (S1 + .26, 0), (S2, 0), (S2 + .06, 1.5, "snap"), (S2 + .26, 0)]},
            "slide": rack([(0, 0), (S1, 0)] + s1[1:] + [(S2, 0)] + s2[1:] + [(1.4, 0)]),
            "trigger": {"r": [(0, 0)] + t1 + t2 + [(1.4, 0)]},
            "flash": shown(S1, S2 + .16, 1.4, sx=[(S1, .5), (S1 + .05, 1.25, "out"), (S1 + .12, .3, "in"), (S2, .5, "step"), (S2 + .05, 1.15, "out"), (S2 + .12, .3, "in")],
                           sy=[(S1, .5), (S1 + .05, 1.25, "out"), (S1 + .12, .3, "in"), (S2, .5, "step"), (S2 + .05, 1.15, "out"), (S2 + .12, .3, "in")],
                           r=[(S1, -16), (S1 + .12, 4), (S2, -16, "step"), (S2 + .12, 4)]),
            "flash_core": shown(S1, S2 + .14, 1.4, sx=[(S1, .6), (S1 + .04, 1.2, "out"), (S1 + .1, .3, "in"), (S2, .6, "step"), (S2 + .04, 1.1, "out"), (S2 + .1, .3, "in")],
                                sy=[(S1, .6), (S1 + .04, 1.2, "out"), (S1 + .1, .3, "in"), (S2, .6, "step"), (S2 + .04, 1.1, "out"), (S2 + .1, .3, "in")]),
            "smoke": shown(S2 + .06, 1.36, 1.4, x=[(S2 + .06, 0), (1.32, -6, "out")], y=[(S2 + .06, 0), (1.32, 7, "out")],
                           sx=[(S2 + .06, .45), (1.32, 1.25, "out")], sy=[(S2 + .06, .45), (1.32, 1.25, "out")],
                           r=[(S2 + .06, 0), (1.32, 25)]),
        }, "alpha": {
            "flash": [(0, 0), (S1, 0, "step"), (S1 + .02, 1), (S1 + .12, 0, "in"), (S2, 0), (S2 + .02, 1), (S2 + .12, 0, "in")],
            "flash_core": [(0, 0), (S1, 0, "step"), (S1 + .02, 1), (S1 + .1, 0, "in"), (S2, 0), (S2 + .02, 1), (S2 + .1, 0, "in")],
            "smoke": fade(S2 + .06, S2 + .14, S2 + .3, 1.32, peak=.9),
        }},
    },
}
