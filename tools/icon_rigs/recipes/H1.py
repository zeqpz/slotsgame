# H1 - Bag of cash. A heavy sack tied at the neck: it slumps and puffs back up as it settles,
# the gathered top flops over the tie, the loose ends of the tie sway, and the $ glints.
# Land: a heavy thud - the sack squashes flat and the top whips. Win: it crouches and jumps,
# and little $ bills burst out of the mouth at the top of the hop.
BOTTOM = (530, 936)        # where the sack sits: squash and stretch happen about here
NECK = (512, 366)          # the tie

TAILS = ("poly", [(104, 314), (250, 300), (332, 310), (364, 336), (368, 374), (352, 404), (330, 426),
                  (310, 452), (268, 486), (206, 522), (150, 548), (110, 548), (104, 480)])
BAND = ("poly", [(338, 345), (370, 320), (450, 304), (560, 304), (650, 312), (678, 320), (696, 345), (696, 404),
                 (678, 426), (620, 422), (540, 412), (450, 414), (396, 434), (352, 432), (334, 402)])
TOP = ("minus", ("or", ("poly", [(140, 20), (740, 20), (740, 346), (345, 346), (300, 318), (140, 318)]),   # its lower edge hides under the band
                 ("and", BAND, ("rect", 330, 290, 700, 372))),          # a strip of the tie under the band hides the seam
       TAILS)
GREEN = "#6fca85"
DOLLAR_BOX = ("rect", 350, 465, 660, 825)     # keeps the colour match off grey antialiasing elsewhere
DOLLAR = ("and", DOLLAR_BOX, ("grow", ("and", DOLLAR_BOX, ("color", GREEN, 50)), 14), ("or", ("color", GREEN, 60), ("ink",)))

REST = {"x": 0, "y": 0, "r": 0, "sx": 1, "sy": 1}


def shown(on, off, dur, **chans):
    """Keys for a part that is hidden at rest: it sits on its rest values until `on`, plays the
    given keys (absolute times, the first one at `on`), and snaps back to rest at `off`, once it
    has faded out - so every clip starts and ends on the rest pose."""
    out = {}
    for ch, keys in chans.items():
        rest = REST[ch]
        out[ch] = [(0, rest), (on, keys[0][1], "step")] + list(keys[1:]) + [(off, rest, "step"), (dur, rest)]
    return out


def twinkle(on, peak, off, dur, size=1.2, spin=90):
    """A sparkle that blooms and shrinks away while it turns."""
    return shown(on, off + .02, dur, sx=[(on, .3), (peak, size, "out"), (off, .2, "in")],
                 sy=[(on, .3), (peak, size, "out"), (off, .2, "in")], r=[(on, 0), (off, spin, "linear")])


def burst(on, dur, dx, dy, spin, top=.36, fall=.95):
    """A little bill shot out of the mouth: up and out, then it tumbles down and fades."""
    return shown(on, on + fall + .04, dur,
                 x=[(on, 0), (on + top, dx * .7, "out"), (on + fall, dx, "linear")],
                 y=[(on, 0), (on + top, dy, "out"), (on + fall, dy - 12, "in")],
                 r=[(on, 0), (on + fall, spin, "linear")],
                 sx=[(on, .6), (on + .3, 1, "out")], sy=[(on, .6), (on + .3, 1, "out")])


def fade(on, full, hold, off, peak=1.0):
    return [(0, 0), (on, 0, "step"), (full, peak), (hold, peak), (off, 0, "in")]


RIG = {
    "id": "H1",
    "parts": [
        {"name": "tails", "mask": TAILS, "pivot": (356, 372), "parent": "band"},
        # never shown: it only repairs the sack's edge under the knot. (Filling under the whole
        # tails would leave a ghost of the sticker border out in the air when they swing.)
        {"name": "knot_patch", "mask": ("and", TAILS, ("rect", 318, 330, 380, 460)), "exclusive": False,
         "hidden": True, "parent": "band", "fill": "body"},
        {"name": "top", "mask": TOP, "exclusive": False, "pivot": (512, 330), "parent": "band"},
        {"name": "dollar", "mask": DOLLAR, "pivot": (500, 645), "parent": "body", "fill": "body"},
        {"name": "body", "mask": "rest", "pivot": BOTTOM},
        # the tie never moves on the sack, so it is a copy laid over everything (cut after the
        # rest): the sack, the top and the tails all carry on unbroken underneath it - no seams
        {"name": "band", "mask": BAND, "exclusive": False, "pivot": NECK, "parent": "body"},
        # little bills that burst out of the mouth on a win (they start hidden behind the top flaps)
        {"name": "cash1", "copy": "dollar", "scale": .3, "at": (430, 190), "hidden": True},
        {"name": "cash2", "copy": "dollar", "scale": .34, "at": (505, 175), "hidden": True},
        {"name": "cash3", "copy": "dollar", "scale": .3, "at": (585, 190), "hidden": True},
        {"name": "glint", "sprite": "sparkle", "size": 14, "at": (585, 535), "hidden": True, "parent": "dollar"},
        {"name": "glint2", "sprite": "sparkle", "size": 11, "at": (395, 610), "hidden": True, "parent": "dollar"},
    ],
    "draw": ["knot_patch", "body", "cash1", "cash2", "cash3", "top", "dollar", "tails", "band", "glint", "glint2"],
    "anims": {
        "idle": {"dur": 2.6, "bones": {
            "body": {"sy": [(0, 1), (.42, 1.05, "inout"), (.62, 1.05), (.86, .93, "in"), (1.02, 1.02, "out"), (1.18, .99), (1.36, 1)],
                     "sx": [(0, 1), (.42, .97, "inout"), (.62, .97), (.86, 1.045, "in"), (1.02, .99, "out"), (1.18, 1.005), (1.36, 1)]},
            "top": {"r": [(0, 0), (.45, -1.5), (.90, 3.2, "in"), (1.10, -2.4, "out"), (1.34, 1.2), (1.6, -.4), (1.85, 0)],
                    "sy": [(0, 1), (.45, 1.03), (.88, .93, "in"), (1.06, 1.06, "out"), (1.26, .985), (1.5, 1)]},
            "tails": {"r": [(0, 0), (.45, 2), (.90, -6, "in"), (1.14, 5, "out"), (1.42, -2.5), (1.72, 1), (2.0, 0)]},
            "dollar": {"sx": [(0, 1), (1.62, 1), (1.82, 1.05, "out"), (2.15, 1)],
                       "sy": [(0, 1), (1.62, 1), (1.82, 1.05, "out"), (2.15, 1)]},
            "glint": twinkle(1.66, 1.84, 2.15, 2.6, size=1.15),
        }, "alpha": {
            "glint": fade(1.66, 1.78, 1.78, 2.15),
        }},
        "land": {"dur": .55, "bones": {
            "body": {"sy": [(0, 1), (.09, .88, "in"), (.22, 1.05, "out"), (.36, .985), (.5, 1)],
                     "sx": [(0, 1), (.09, 1.08, "in"), (.22, .97, "out"), (.36, 1.01), (.5, 1)]},
            "top": {"y": [(0, 0), (.1, -1.4, "in"), (.25, 1.2, "out"), (.4, 0)],
                    "r": [(0, 0), (.12, -2.2), (.28, 2.4), (.42, -.8), (.55, 0)]},
            "tails": {"r": [(0, 0), (.1, 8, "in"), (.26, -5), (.42, 2), (.55, 0)]},
        }},
        "win": {"dur": 1.4, "bones": {
            "body": {"y": [(0, 0), (.14, 0), (.40, 8, "out"), (.62, 0, "in"), (1.4, 0)],
                     "sy": [(0, 1), (.14, .88, "inout"), (.30, 1.07, "out"), (.50, 1.0), (.62, 1.02, "in"), (.70, .9, "out"), (.84, 1.03), (1.0, .995), (1.12, 1)],
                     "sx": [(0, 1), (.14, 1.08, "inout"), (.30, .95, "out"), (.50, 1.0), (.62, .99, "in"), (.70, 1.07, "out"), (.84, .98), (1.0, 1.003), (1.12, 1)]},
            "top": {"sy": [(0, 1), (.14, .93), (.40, .96), (.58, 1.09), (.72, .92), (.88, 1.03), (1.08, 1)],
                    "r": [(0, 0), (.20, -2), (.48, 3), (.74, -2.5), (.96, 1), (1.18, 0)]},
            "tails": {"r": [(0, 0), (.14, 5), (.42, -7), (.68, 7), (.92, -3), (1.18, 0)]},
            "dollar": {"sx": [(0, 1), (.30, 1), (.46, 1.09, "back"), (.82, 1)],
                       "sy": [(0, 1), (.30, 1), (.46, 1.09, "back"), (.82, 1)]},
            "cash1": burst(.30, 1.4, -15, 20, 50),
            "cash2": burst(.34, 1.4, 3, 25, -30),
            "cash3": burst(.32, 1.4, 15, 19, -50),
            "glint": twinkle(.40, .56, .82, 1.4, size=1.25),
            "glint2": twinkle(.70, .86, 1.1, 1.4, size=1.2, spin=-90),
        }, "alpha": {
            "cash1": fade(.30, .31, 1.0, 1.25),
            "cash2": fade(.34, .35, 1.05, 1.29),
            "cash3": fade(.32, .33, 1.0, 1.27),
            "glint": fade(.40, .50, .50, .82),
            "glint2": fade(.70, .80, .80, 1.1),
        }},
    },
}
