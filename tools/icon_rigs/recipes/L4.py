# L4 - Hangtag: two tags on a string loop. It hangs, so it swings like a pendulum: the loop
# rocks about its top, the front tag swings on the string a beat behind it and the back tag a
# beat behind that, twisting on the string as it goes (it narrows as it turns edge-on). Land:
# the tags drop onto the string - it stretches and springs back - and swing. Win: a hard flick,
# a big swing with the back tag fanning out, the logo sticker popping with a twinkle.
#
# Cut: the back tag is only ever seen to the right of the front one, so the front tag inpaints
# the rest of it ("fill") - that is what shows if the two drift apart. Their relative swing stays
# small (about a degree); the twist only folds the back tag further in behind the front one.
import math

HOLE = (497, 298)          # the grommet: both tags hang on the string here
TOP = (450, 44)            # the top of the loop: the whole thing rocks about this
EDGE = [(665, 250), (658, 290), (630, 440), (602, 590), (580, 715), (560, 865), (555, 900), (546, 1000)]   # front tag's right edge (ink centre)


def edge(d):               # that edge, shifted d px right
    return [(x + d, y) for x, y in EDGE]


# the string loop above the front tag (the white border between the strands and the tag's top
# edge stays with the tag); it reaches a little way under the tag so no seam shows along its edge
STRING_AREA = ("poly", [(240, 0), (600, 0), (600, 200), (580, 222), (556, 236), (548, 251), (530, 250), (500, 247),
                        (440, 241), (420, 238), (380, 232), (300, 224), (240, 224)])
# the left strand runs on behind the tag: a stub of it hides under the tag's top edge, so a gap
# never opens there when the tag swings on the string
STUB = ("poly", [(404, 226), (440, 234), (442, 262), (404, 256)])
BACK = ("poly", [(548, 251), (556, 236), (580, 222), (600, 200), (1000, 200), (1000, 1000)] + edge(5)[:0:-1]
                + [(660, 279), (600, 268), (548, 259)])
FRONT = ("minus", ("opaque",), ("or", BACK, STRING_AREA))
# the grommet and the bit of string on the tag (just the ink and the glint in the hole): it stays
# on top of the logo sticker when that pops
KNOT = ("or", ("and", ("or", ("disc", 497, 298, 16), ("poly", [(493, 268), (508, 268), (506, 288), (491, 288)])), ("grow", ("ink",), 1)),
        ("and", ("disc", 497, 299, 9), ("color", "#ffffff", 80)))
# the logo sticker: its white border ring, every pocket inside it filled
RING = ("grow", ("cc", ("color", "#ffffff", 60), 327, 690), 3)
LOGO = ("minus", ("rect", 290, 270, 580, 880), ("cc", ("minus", ("rect", 286, 266, 584, 884), RING), 288, 268))


def swing(amp, period, decay, delay, end, hold=None):
    """a damped pendulum: keys on its extremes (ease in-out between them reads as a sine)"""
    keys = [(0, 0)] + ([(delay, 0)] if delay else [])
    t0 = t = delay + period / 4
    sign, first = 1, True
    while t <= (hold or end) - period / 4 + 1e-6:
        keys.append((round(t, 3), round(sign * amp * math.exp(-(t - t0) / decay), 3), "out" if first else "inout"))
        t, sign, first = t + period / 2, -sign, False
    keys.append((end, 0, "inout"))
    return keys


def twinkle(t0, t1, peak=1.2, spin=90):
    """a sparkle that flares and fades between t0 and t1 - (bone channels, alpha keys); hidden
    either side, and every channel is back at rest once it has faded"""
    tm = t0 + (t1 - t0) * .45
    s = [(0, 1), (t0, .3, "step"), (tm, peak, "out"), (t1, .2, "in"), (t1 + .01, 1, "step")]
    return ({"sx": s, "sy": list(s), "r": [(0, 0), (t0, 0), (t1, spin, "linear"), (t1 + .01, 0, "step")]},
            [(0, 0), (t0, 0, "step"), (t0 + (t1 - t0) * .3, 1), (t1, 0)])


RIG = {
    "id": "L4",
    "parts": [
        {"name": "logo", "mask": LOGO, "pivot": (432, 575), "parent": "front"},
        {"name": "knot", "mask": KNOT, "pivot": HOLE, "parent": "front", "fill": "front"},
        {"name": "back", "mask": BACK, "pivot": HOLE, "parent": "string"},
        {"name": "front", "mask": FRONT, "pivot": HOLE, "parent": "string", "exclusive": False, "fill": "back"},
        {"name": "string", "mask": ("or", ("grow", STRING_AREA, 4), STUB), "pivot": TOP, "exclusive": False},
        {"name": "tw", "sprite": "sparkle", "size": 15, "at": (522, 395), "hidden": True, "parent": "logo"},
    ],
    "draw": ["back", "string", "front", "logo", "knot", "tw"],
    "anims": {
        # a breeze: the loop rocks, the tags follow it a beat late and die down
        "idle": {"dur": 2.8, "bones": {
            "string": {"r": swing(1.8, 1.2, 1.7, 0, 2.6)},
            "front": {"r": swing(1.7, 1.2, 1.7, .12, 2.75)},
            "back": {"r": swing(1.95, 1.2, 1.8, .24, 2.8),
                     "sx": [(0, 1), (.55, .93), (1.15, 1.0), (1.75, .95), (2.35, 1.0)]},
        }},
        # dropped in: the string takes the weight (stretches, springs back) and the tags swing
        "land": {"dur": .55, "bones": {
            "string": {"sy": [(0, 1), (.09, 1.035, "in"), (.22, .985, "out"), (.36, 1.004), (.48, 1.0)],
                       "r": [(0, 0), (.14, -.7), (.32, .5), (.5, 0)]},
            "front": {"r": [(0, 0), (.12, 1.3), (.3, -1.0), (.45, .35), (.55, 0)]},
            "back": {"r": [(0, 0), (.15, 1.9), (.33, -1.4), (.48, .45), (.55, 0)]},
        }},
        # flicked: a big swing that dies down, the back tag twisting, the logo popping at the top of it
        "win": {"dur": 1.4, "bones": {
            "string": {"r": swing(3.4, .74, .9, 0, 1.4, hold=1.3)},
            "front": {"r": swing(3.0, .74, .9, .07, 1.4, hold=1.36)},
            "back": {"r": swing(3.6, .74, .95, .16, 1.4, hold=1.4),
                     "sx": [(0, 1), (.3, .9), (.62, 1.0), (.94, .91), (1.26, 1.0)]},
            "logo": {"sx": [(0, 1), (.16, 1), (.38, 1.12, "back"), (.86, 1.07), (1.18, 1.0, "inout")],
                     "sy": [(0, 1), (.16, 1), (.38, 1.12, "back"), (.86, 1.07), (1.18, 1.0, "inout")]},
            "tw": twinkle(.34, .8)[0],
        }, "alpha": {
            "tw": twinkle(.34, .8)[1],
        }},
    },
}
