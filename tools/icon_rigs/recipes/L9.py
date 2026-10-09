# L9 - Freight car with a graffiti piece. It rolls: the car body rocks on its springs over two
# bogies that stay on the rails, and each bogie kicks up as it clacks over a rail joint (front,
# then back) with the body answering. Land: dropped onto the rails, the body sinks on its springs
# and bounces. Win: it lurches forward and back - the body leans against the jolt, dust kicks
# up from the rear wheels, speed lines streak off behind and the fresh piece glints.
SPRINGS = (495, 590)        # the middle of the underframe: the body rocks about here
RAIL_L, RAIL_R = (195, 668), (790, 668)   # where each bogie's wheels meet the rail

# a bogie with its sticker border, cut along the underframe bar's bottom edge down past its wheels.
# It sits behind the body, and carries a copy of the strip of black bar above it (its "frame"),
# so when the body rises off it on its springs the gap shows black frame, never a hole.
BOGIE_L = ("poly", [(113, 600), (312, 600), (312, 642), (292, 650), (292, 692), (98, 692), (98, 630), (113, 616)])
BOGIE_R = ("poly", [(706, 600), (878, 600), (888, 625), (888, 692), (700, 692), (700, 642), (706, 632)])
FRAME_L = ("rect", 116, 570, 305, 604)
FRAME_R = ("rect", 713, 570, 871, 604)


def twinkle(t0, t1, t2, spin=90, peak=1.2):
    """a glint: pops in at t0, peaks at t1, gone by t2 - every channel back at rest by the end"""
    bones = {"sx": [(0, 1), (t0, .3, "step"), (t1, peak, "out"), (t2, .2, "in"), (t2 + .02, 1, "step")],
             "sy": [(0, 1), (t0, .3, "step"), (t1, peak, "out"), (t2, .2, "in"), (t2 + .02, 1, "step")],
             "r": [(0, 0), (t0, 0), (t2, spin, "linear"), (t2 + .02, 0, "step")]}
    return bones, [(0, 0), (t0, 0, "step"), (t0 + .1, 1), (t2, 0)]


def clack(*times, h=.4):
    """a bogie riding over rail joints: a quick kick up at each time, dropped straight back"""
    y = [(0, 0)]
    for t in times:
        y += [(t, 0), (t + .06, h, "out"), (t + .17, 0, "in")]
    return y


def drift(t0, t1, dx, dy, s0=.5, s1=1.3, spin=0):
    """a puff or streak that appears at t0 and drifts (dx, dy) while growing, gone at t1"""
    return {"x": [(0, 0), (t0, 0), (t1, dx, "out"), (t1 + .02, 0, "step")],
            "y": [(0, 0), (t0, 0), (t1, dy, "out"), (t1 + .02, 0, "step")],
            "sx": [(0, 1), (t0, s0, "step"), (t1, s1, "out"), (t1 + .02, 1, "step")],
            "sy": [(0, 1), (t0, s0, "step"), (t1, s1, "out"), (t1 + .02, 1, "step")],
            **({"r": [(0, 0), (t0, 0), (t1, spin), (t1 + .02, 0, "step")]} if spin else {})}


LURCH = [(0, 0), (.1, -.6, "inout"), (.32, 3.0, "out"), (.56, -.9, "inout"), (.8, .7), (1.02, -.25), (1.24, 0)]
GA, GA_ALPHA = twinkle(.56, .72, .98, 90)
GB, GB_ALPHA = twinkle(.72, .88, 1.14, -90, 1.1)

RIG = {
    "id": "L9",
    "parts": [
        {"name": "bogie_l", "mask": BOGIE_L, "pivot": RAIL_L},
        {"name": "bogie_r", "mask": BOGIE_R, "pivot": RAIL_R},
        {"name": "body", "mask": "rest", "pivot": SPRINGS},
        # the frames copy the bar's black: cut after the body, so the body keeps its bar
        {"name": "frame_l", "mask": FRAME_L, "exclusive": False, "parent": "bogie_l"},
        {"name": "frame_r", "mask": FRAME_R, "exclusive": False, "parent": "bogie_r"},
        {"name": "dust_a", "sprite": "puff", "args": {"color": (226, 220, 204)}, "size": 15, "at": (150, 650), "hidden": True},
        {"name": "dust_b", "sprite": "puff", "args": {"color": (226, 220, 204)}, "size": 12, "at": (255, 660), "hidden": True},
        {"name": "speed_a", "sprite": "streak", "size": 15, "at": (10, 430), "hidden": True},
        {"name": "speed_b", "sprite": "streak", "size": 11, "at": (-5, 500), "hidden": True},
        {"name": "glint_a", "sprite": "sparkle", "size": 13, "at": (330, 420), "hidden": True, "parent": "body"},
        {"name": "glint_b", "sprite": "sparkle", "size": 11, "at": (740, 410), "hidden": True, "parent": "body"},
    ],
    # the bogies (and their frames) sit behind the body, tucked up under its bar
    "draw": ["speed_a", "speed_b", "frame_l", "frame_r", "bogie_l", "bogie_r", "body", "dust_a", "dust_b", "glint_a", "glint_b"],
    "anims": {
        # rolling along: the bogies clack over two rail joints each (front, then back) and the body
        # pitches with every kick - nose up, tail up - and sways on its springs in between
        "idle": {"dur": 2.6, "bones": {
            "body": {"r": [(0, 0), (.4, 0), (.5, .8, "out"), (.66, .1, "inout"), (.76, -.75, "out"), (.95, .2, "inout"), (1.25, -.25, "soft"), (1.7, 0, "soft"),
                           (1.8, .7, "out"), (1.96, .1, "inout"), (2.06, -.65, "out"), (2.25, .15, "inout"), (2.6, 0, "soft")],
                     "y": [(0, 0), (.4, 0), (.5, .45, "out"), (.66, -.12, "in"), (.76, .4, "out"), (.92, -.1, "in"), (1.05, 0),
                           (1.7, 0), (1.8, .4, "out"), (1.96, -.1, "in"), (2.06, .35, "out"), (2.22, -.08, "in"), (2.36, 0)],
                     "x": [(0, 0), (.9, .35, "soft"), (1.9, -.3, "soft"), (2.6, 0, "soft")]},
            "bogie_r": {"y": clack(.4, 1.7, h=.5), "x": [(0, 0), (.9, .35, "soft"), (1.9, -.3, "soft"), (2.6, 0, "soft")]},   # the front bogie meets each joint first ...
            "bogie_l": {"y": clack(.66, 1.96, h=.5), "x": [(0, 0), (.9, .35, "soft"), (1.9, -.3, "soft"), (2.6, 0, "soft")]},  # ... the back one a moment later
        }},
        # set down on the rails: the body sinks on its springs and bounces, the bogies take the weight
        "land": {"dur": .55, "bones": {
            "body": {"y": [(0, 0), (.08, -1.3, "in"), (.22, .55, "out"), (.36, -.18), (.55, 0)],
                     "r": [(0, 0), (.1, .6, "out"), (.26, -.45), (.42, .15), (.55, 0)]},
            "bogie_l": {"sy": [(0, 1), (.08, .93, "in"), (.2, 1.03, "out"), (.34, 1)]},
            "bogie_r": {"sy": [(0, 1), (.09, .93, "in"), (.21, 1.03, "out"), (.35, 1)]},
        }},
        # a lurch forward and back: the body leans against the jolt, dust kicks up behind the rear
        # wheels, speed lines streak off, the piece glints
        "win": {"dur": 1.4, "bones": {
            "body": {"x": LURCH,
                     "r": [(0, 0), (.1, -.7), (.3, 1.7, "out"), (.52, -1.5), (.74, .8), (.96, -.35), (1.2, 0)],
                     "y": [(0, 0), (.1, -.4), (.3, .7, "out"), (.46, -.3), (.62, .2), (.8, 0)]},
            "bogie_l": {"x": LURCH, "y": clack(.2, .62, h=.5)},
            "bogie_r": {"x": LURCH, "y": clack(.14, .56, h=.5)},
            "dust_a": drift(.14, .95, -7, 2.5, .45, 1.35, -20),
            "dust_b": drift(.2, 1.0, -5, 4, .4, 1.2, 25),
            "speed_a": drift(.16, .56, -7, 0, 1, .8),
            "speed_b": drift(.22, .62, -6, 0, 1, .7),
            "glint_a": GA, "glint_b": GB,
        }, "alpha": {
            "dust_a": [(0, 0), (.14, 0, "step"), (.22, .95), (.95, 0, "in")],
            "dust_b": [(0, 0), (.2, 0, "step"), (.28, .9), (1.0, 0, "in")],
            "speed_a": [(0, 0), (.16, 0, "step"), (.22, .85), (.56, 0, "in")],
            "speed_b": [(0, 0), (.22, 0, "step"), (.28, .75), (.62, 0, "in")],
            "glint_a": GA_ALPHA, "glint_b": GB_ALPHA,
        }},
    },
}
