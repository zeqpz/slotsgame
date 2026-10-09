# M - the Multi booster: a chunk of brick wall with the multiplier painted over it by the page,
# so the bricks stay where they are. Idle: the chunk shudders, the loose top corner bricks tip up
# and drop back with a puff of mortar dust off each, the crack between its halves creaks open a
# hair, and the bottom corner brick works out and back. Land: it thuds down, the loose bricks hop
# and settle, dust puffs from both bottom corners.
# Win: it cracks - the chunk splits along its mortar joints into two halves that spring apart at
# the top, brick chips and dust fly out of the crack, the loose bricks rattle - then it slams
# back together and settles.
CRACK_FOOT = (588, 905)    # bottom of the crack: both halves turn about here (and squash from here)
# the crack's path down the mortar, top to bottom (vertical joints, joined along the bed joints)
CRACK = [(507, 60), (507, 252), (597, 252), (597, 366), (630, 366), (630, 477), (508, 477), (508, 581), (605, 581),
         (605, 688), (494, 688), (494, 798), (588, 798), (588, 960)]
LEFT = [(80, 60)] + CRACK + [(80, 960)]
MORTAR = (219, 215, 188)


def shake(t0, amp, n=5, step=.04):
    """a decaying side-to-side tremble starting at t0 (ends on 0)"""
    k = [(t0, 0, "linear")]
    for i in range(n):
        k.append((t0 + step * (i + 1), amp * (1 - i / n) * (1 if i % 2 == 0 else -1), "inout"))
    k.append((t0 + step * (n + 1), 0, "inout"))
    return k


def tip(t0, deg, settle=True):
    """a loose brick tips up on one corner, drops back, bounces twice smaller"""
    return [(t0, 0, "linear"), (t0 + .15, deg, "out"), (t0 + .30, 0, "in"), (t0 + .40, deg * .25, "out"), (t0 + .50, 0, "in"),
            (t0 + .57, deg * .06, "out"), (t0 + .64, 0, "in")]


def puff(t0, dur, at, to, s0=.4, s1=1.25, a=.95):
    """bones + alpha for a dust puff: jumps (while hidden) to `at` (units from its rest spot),
    billows up fast while it drifts on to `to`, then thins out and shrinks away (opaque most of
    the way: a half-faded puff only reads as a grey smudge); back to its rest spot after"""
    end, top = t0 + dur, t0 + dur * .35
    hold = lambda v, v1, e="out": [(0, 0), (t0, 0, "step"), (t0 + .001, v, "step"), (end, v1, e), (end + .01, 0, "step")]
    sc = [(0, 1), (t0, 1, "step"), (t0 + .001, s0, "step"), (top, s1, "out"), (end, s1 * .6, "in"), (end + .01, 1, "step")]
    return ({"x": hold(at[0], to[0]), "y": hold(at[1], to[1]), "sx": sc, "sy": list(sc)},
            [(0, 0), (t0, 0, "step"), (t0 + .04, a), (t0 + dur * .72, a, "linear"), (end, 0, "linear")])


def chip(t0, dur, dx, dy, lift, spin):
    """a brick chip: pops out of the crack, flies an arc (up `lift`, then down to dy), spins, fades"""
    end = t0 + dur
    return ({"x": [(0, 0), (t0, 0, "step"), (end, dx, "linear"), (end + .01, 0, "step")],
             "y": [(0, 0), (t0, 0, "step"), (t0 + dur * .35, lift, "out"), (end, dy, "in"), (end + .01, 0, "step")],
             "r": [(0, 0), (t0, 0, "step"), (end, spin, "linear"), (end + .01, 0, "step")]},
            [(0, 0), (t0, 0, "step"), (t0 + .04, 1), (t0 + dur * .6, 1, "linear"), (end, 0, "in")])


# ---------------------------------------------------------------- idle
I_PA, I_PA_A = puff(.55, .6, (0, 65), (-3, 67), s0=.35, s1=.9, a=.8)          # off brick A (top left)
I_PR, I_PR_A = puff(1.7, .6, (0, 65), (3, 67), s0=.35, s1=.9, a=.8)          # off brick D (top right)
# ---------------------------------------------------------------- land
L_PL, L_PL_A = puff(.05, .42, (0, 0), (-5, .5), s0=.45, s1=1.2)
L_PR, L_PR_A = puff(.07, .42, (0, 0), (5, .5), s0=.45, s1=1.15)
# ---------------------------------------------------------------- win
W_PC, W_PC_A = puff(.08, .55, (0, 0), (0, 8), s0=.4, s1=1.35)
W_PL, W_PL_A = puff(.62, .5, (0, 0), (-6, .5), s0=.45, s1=1.25)
W_PR, W_PR_A = puff(.64, .5, (0, 0), (6, .5), s0=.45, s1=1.2)
W_C1, W_C1_A = chip(.1, .7, -20, -12, 8, 280)
W_C2, W_C2_A = chip(.13, .66, 18, -14, 7, -320)
OPEN = 1.3                 # degrees each half turns away from the crack at the widest

RIG = {
    "id": "M",
    "parts": [
        # the loose bricks: the top corners and the bottom-left corner (their sticker border with them;
        # "cc" thresholds the rectangle so its edges are hard - no seam where it meets the wall). No
        # fill: a brick lifting off its bed opens a dark gap under it, which is just what it should show
        {"name": "brick_tl", "mask": ("cc", ("rect", 136, 104, 309, 247), 220, 180), "pivot": (306, 244), "parent": "left"},
        {"name": "brick_tr", "mask": ("cc", ("rect", 688, 104, 882, 250), 770, 180), "pivot": (692, 247), "parent": "right"},
        {"name": "brick_bl", "mask": ("cc", ("rect", 136, 800, 290, 935), 220, 860), "pivot": (213, 852), "parent": "left"},
        # the two halves either side of the crack (hard-edged: they meet in flat mortar)
        {"name": "left", "mask": ("cc", ("poly", LEFT), 300, 500), "pivot": CRACK_FOOT},
        {"name": "right", "mask": "rest", "pivot": CRACK_FOOT},
        {"name": "chip1", "copy": "brick_tl", "scale": .3, "at": (515, 175), "hidden": True},
        {"name": "chip2", "copy": "brick_tr", "scale": .26, "at": (560, 225), "hidden": True},
        {"name": "dust_c", "sprite": "puff", "size": 17, "at": (540, 150), "hidden": True, "args": {"color": MORTAR}},
        {"name": "dust_l", "sprite": "puff", "size": 16, "at": (200, 905), "hidden": True, "args": {"color": MORTAR}},
        {"name": "dust_r", "sprite": "puff", "size": 16, "at": (820, 905), "hidden": True, "args": {"color": MORTAR}},
    ],
    "draw": ["left", "right", "brick_tl", "brick_tr", "brick_bl", "dust_c", "chip1", "chip2", "dust_l", "dust_r"],
    "anims": {
        "idle": {"dur": 2.5, "bones": {
            # a shudder, then (between the two loose bricks) the crack creaks open a hair and shuts
            "left": {"x": [(0, 0)] + shake(.08, .35),
                     "r": [(0, 0), (.92, 0, "linear"), (1.0, .45, "out"), (1.08, .3, "inout"), (1.2, 0, "in"), (1.27, -.08, "out"), (1.34, 0, "soft")]},
            "right": {"x": [(0, 0)] + shake(.08, .35),
                      "r": [(0, 0), (.92, 0, "linear"), (1.0, -.45, "out"), (1.08, -.3, "inout"), (1.2, 0, "in"), (1.27, .08, "out"), (1.34, 0, "soft")]},
            "brick_tl": {"r": [(0, 0)] + tip(.25, -6.5)},
            "brick_tr": {"r": [(0, 0)] + tip(1.4, 6)},
            "brick_bl": {"x": [(0, 0), (1.95, 0, "linear"), (2.07, -.9, "out"), (2.2, .15, "inout"), (2.3, 0, "soft")]},
            "dust_l": I_PA, "dust_r": I_PR,
        }, "alpha": {"dust_l": I_PA_A, "dust_r": I_PR_A}},
        "land": {"dur": .55, "bones": {
            "left": {"sy": [(0, 1), (.07, .95, "in"), (.18, 1.02, "out"), (.3, .995, "inout"), (.4, 1, "soft")]},
            "right": {"sy": [(0, 1), (.07, .95, "in"), (.18, 1.02, "out"), (.3, .995, "inout"), (.4, 1, "soft")]},
            "brick_tl": {"y": [(0, 0), (.08, 0, "linear"), (.16, 1.3, "out"), (.26, 0, "in"), (.32, .25, "out"), (.38, 0, "in")],
                         "r": [(0, 0), (.08, 0, "linear"), (.16, -2.5, "out"), (.28, 0, "in"), (.36, -.5, "out"), (.42, 0, "in")]},
            "brick_tr": {"y": [(0, 0), (.09, 0, "linear"), (.17, 1.1, "out"), (.27, 0, "in"), (.33, .2, "out"), (.39, 0, "in")],
                         "r": [(0, 0), (.09, 0, "linear"), (.17, 2.2, "out"), (.29, 0, "in"), (.37, .4, "out"), (.43, 0, "in")]},
            "dust_l": L_PL, "dust_r": L_PR,
        }, "alpha": {"dust_l": L_PL_A, "dust_r": L_PR_A}},
        "win": {"dur": 1.4, "bones": {
            # crack open (.06 - .16), hold with a tremble, slam shut (.55 - .64), settle
            "left": {"r": [(0, 0), (.06, 0, "linear"), (.16, OPEN, "out"), (.24, OPEN * .8, "inout"), (.32, OPEN, "inout"), (.40, OPEN * .82, "inout"),
                           (.48, OPEN * .95, "inout"), (.62, 0, "in"), (.7, -.25, "out"), (.8, 0, "soft")],
                     "x": shake(0, .3, n=1, step=.03),
                     "y": [(0, 0), (.06, 0, "linear"), (.16, 1.0, "out"), (.5, .6, "inout"), (.62, 0, "in"), (.75, .35, "out"), (.88, 0, "in")],
                     "sy": [(0, 1), (.6, 1, "linear"), (.66, .96, "in"), (.76, 1.015, "out"), (.88, 1, "soft")]},
            "right": {"r": [(0, 0), (.06, 0, "linear"), (.16, -OPEN, "out"), (.24, -OPEN * .8, "inout"), (.32, -OPEN, "inout"), (.40, -OPEN * .82, "inout"),
                            (.48, -OPEN * .95, "inout"), (.62, 0, "in"), (.7, .25, "out"), (.8, 0, "soft")],
                      "x": shake(0, .3, n=1, step=.03),
                      "y": [(0, 0), (.06, 0, "linear"), (.16, 1.0, "out"), (.5, .6, "inout"), (.62, 0, "in"), (.75, .35, "out"), (.88, 0, "in")],
                      "sy": [(0, 1), (.6, 1, "linear"), (.66, .96, "in"), (.76, 1.015, "out"), (.88, 1, "soft")]},
            "brick_tl": {"r": [(0, 0), (.1, 0, "linear"), (.24, -6, "out"), (.36, -2, "inout"), (.46, -4, "inout"), (.62, 0, "in"),
                               (.72, -1.5, "out"), (.82, 0, "in"), (.88, -.3, "out"), (.94, 0, "in")]},
            "brick_tr": {"r": [(0, 0), (.12, 0, "linear"), (.26, 5.5, "out"), (.38, 2, "inout"), (.48, 3.6, "inout"), (.63, 0, "in"),
                               (.73, 1.3, "out"), (.83, 0, "in"), (.89, .25, "out"), (.95, 0, "in")]},
            "brick_bl": {"x": [(0, 0), (.12, 0, "linear"), (.26, -1.3, "out"), (.5, -1.0, "inout"), (.63, 0, "in"), (.72, -.25, "out"), (.82, 0, "soft")]},
            "dust_c": W_PC, "dust_l": W_PL, "dust_r": W_PR, "chip1": W_C1, "chip2": W_C2,
        }, "alpha": {"dust_c": W_PC_A, "dust_l": W_PL_A, "dust_r": W_PR_A, "chip1": W_C1_A, "chip2": W_C2_A}},
    },
}
