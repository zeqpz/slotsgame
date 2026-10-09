# H7 - Limited drop box: an open cardboard box with the LIMITED tag on its side. Something is
# alive in it. Idle: two bumps from inside - the box hops, all four flaps flap and settle - then a
# glint twinkles in the opening. Land: the box thuds down and the flaps flop and spring back.
# Win: the drop - the box crouches, jumps, the flaps burst wide open, a poof and sparkles shoot
# out of the opening, a glint flashes on the tag, and everything settles back.
#
# Flaps fold about their hinge (the rim edge they hang off): a flap "opens" by stretching away
# from its hinge. The front flaps' hinges are tilted, so each hangs off an invisible helper bone
# that turns onto the hinge, scales across it (sy) and is turned back by the flap - R(a) S R(-a):
# nothing turns, the flap only stretches square to its hinge, which stays put. Front flaps only
# ever stretch (>= 1): what is behind them is not in the art. The back flaps stand against the
# sky, so they fold both ways; their lower edges run on under the front flaps (non-exclusive,
# sharing the front flaps' outline) so a back flap lifting never opens a crack.
import math

BASE = (580, 836)          # the bottom front corner: the box squashes and hops from here
HINGE_FL = (356, 445)      # middle of the front-left rim (centre line (125, 387) -> (588, 504))
HINGE_R = (717, 467)       # middle of the front-right rim (centre line (590, 508) -> (845, 425))
A_FL = math.degrees(math.atan2(-117, 463))     # -14.2: the front-left rim in skeleton degrees
A_R = math.degrees(math.atan2(83, 255))        # +18.0: the front-right rim
OPENING = (592, 405)       # the dark inside of the box, between the front flaps
EPS = .001

# the outline between the front-left flap and the back flaps (upper edge of the black line)
FL_TOP = [(0, 222), (40, 226), (100, 238), (200, 254), (300, 274), (380, 291), (398, 295), (420, 299), (480, 316), (503, 320)]
# the outline between the right flap and the back-right flap, out to the right flap's tip
R_TOP = [(690, 331), (700, 333), (750, 315), (800, 302), (850, 289), (880, 280), (900, 270), (910, 268), (920, 256), (930, 243),
         (950, 235), (1000, 235)]


def down(pts, d):
    return [(x, y + d) for x, y in pts]


FLAP_FL = FL_TOP + [(528, 377), (592, 505), (588, 504), (125, 387), (92, 379), (0, 250)]
FLAP_R = [(590, 490), (640, 417), (683, 352)] + R_TOP + [(1000, 330), (880, 414), (845, 425), (590, 508)]
FLAP_BL = [(0, 140), (398, 140)] + down(list(reversed(FL_TOP[:7])), 10) + [(0, 232)]
# the back-right flap stands on the box's inner back wall along (503, 318) - (700, 332); its
# "core" stops there, and the flap itself runs 12 px further down over the wall (the wall stays in
# the body too) so a lifting flap pulls more wall into view instead of opening a crack
BR_SIDES = [(398, 140), (1000, 140)] + down(list(reversed(R_TOP[1:])), 10)
FLAP_BR_CORE = BR_SIDES + [(700, 332), (503, 318)] + down(list(reversed(FL_TOP[6:])), 10)
FLAP_BR = BR_SIDES + [(700, 344), (503, 330)] + down(list(reversed(FL_TOP[6:])), 10)


def hard(pts, seed):
    """a hard-edged (binary) polygon mask: the flaps meet the body and each other in flat paint,
    where two soft edges laid over each other would show a see-through seam"""
    return ("cc", ("poly", pts), *seed)


def hinge(alpha, k, dur):
    """bones for a front flap: (helper, flap) - k is the flap's stretch keys (1 at both ends)"""
    turn = [(0, 0), (EPS, alpha, "step"), (dur - EPS, alpha, "linear"), (dur, 0, "step")]
    back = [(0, 0), (EPS, -alpha, "step"), (dur - EPS, -alpha, "linear"), (dur, 0, "step")]
    return {"r": turn, "sy": k}, {"r": back}


def bump(t, s=1.0):
    """box keys for one knock from inside starting at t: squash, hop, land, settle"""
    return {"sy": [(t, 1, "linear"), (t + .06, 1 - .045 * s, "out"), (t + .18, 1 + .03 * s, "out"), (t + .32, 1 - .025 * s, "in"), (t + .44, 1, "soft")],
            "sx": [(t, 1, "linear"), (t + .06, 1 + .025 * s, "out"), (t + .18, 1 - .015 * s, "out"), (t + .32, 1 + .015 * s, "in"), (t + .44, 1, "soft")],
            "y": [(t, 0, "linear"), (t + .06, 0, "linear"), (t + .18, 1.6 * s, "out"), (t + .30, 0, "in")]}


def joined(*segs, start=None):
    """concatenate per-channel key lists of consecutive segments, with a rest key at 0"""
    out = {}
    for seg in segs:
        for ch, keys in seg.items():
            out.setdefault(ch, [(0, start[ch] if start else (1 if ch in ("sx", "sy") else 0))]).extend(keys)
    return out


def flap(t, amp, lag=0.0, back=False):
    """stretch keys for one flap of a flap after a knock at t (front flaps never go below 1)"""
    t += lag
    if back:   # folds in, springs out, small settle
        return [(t, 1, "linear"), (t + .1, 1 - .6 * amp, "out"), (t + .24, 1 + amp, "inout"), (t + .38, 1 - .25 * amp, "inout"), (t + .52, 1, "soft")]
    return [(t, 1, "linear"), (t + .14, 1 + amp, "out"), (t + .3, 1 + .1 * amp, "inout"), (t + .42, 1 + .35 * amp, "inout"), (t + .56, 1, "soft")]


def sparkle_keys(t0, dur, dx, dy, peak=1.15, spin=90):
    """a sparkle: pops out of the opening, travels (dx, dy) units, flares and fades"""
    end = t0 + dur
    sc = [(0, 1), (t0, 1, "step"), (t0 + .01, .3, "step"), (t0 + dur * .35, peak, "out"), (end, .25, "in"), (end + .01, 1, "step")]
    return {"x": [(0, 0), (t0, 0, "step"), (end, dx, "out"), (end + .01, 0, "step")],
            "y": [(0, 0), (t0, 0, "step"), (end, dy, "out"), (end + .01, 0, "step")],
            "sx": sc, "sy": list(sc), "r": [(0, 0), (t0, 0, "step"), (end, spin, "linear"), (end + .01, 0, "step")]}


def sparkle_alpha(t0, dur):
    return [(0, 0), (t0, 0, "step"), (t0 + .06, 1), (t0 + dur * .55, 1, "linear"), (t0 + dur, 0, "in")]


# ---------------------------------------------------------------- clips
IDLE_DUR, LAND_DUR, WIN_DUR = 2.6, .55, 1.45
K1, K2 = .2, 1.0           # the two knocks from inside

idle_fl_h, idle_fl = hinge(A_FL, [(0, 1)] + flap(K1, .09, .03) + flap(K2, .06, .03), IDLE_DUR)
idle_r_h, idle_r = hinge(A_R, [(0, 1)] + flap(K1, .08, .06) + flap(K2, .055, .06), IDLE_DUR)
land_fl_h, land_fl = hinge(A_FL, [(0, 1), (.05, 1, "linear"), (.17, 1.09, "out"), (.3, 1.01, "inout"), (.4, 1.03, "inout"), (.5, 1, "soft")], LAND_DUR)
land_r_h, land_r = hinge(A_R, [(0, 1), (.07, 1, "linear"), (.19, 1.08, "out"), (.32, 1.01, "inout"), (.42, 1.025, "inout"), (.52, 1, "soft")], LAND_DUR)
WIN_FL_K = [(0, 1), (.12, 1, "linear"), (.27, 1.2, "back"), (.45, 1.06, "inout"), (.56, 1.12, "inout"), (.72, 1.0, "inout"), (.84, 1.04, "inout"), (1.0, 1, "soft")]
WIN_R_K = [(0, 1), (.14, 1, "linear"), (.29, 1.18, "back"), (.47, 1.05, "inout"), (.58, 1.11, "inout"), (.74, 1.0, "inout"), (.86, 1.035, "inout"), (1.02, 1, "soft")]
win_fl_h, win_fl = hinge(A_FL, WIN_FL_K, WIN_DUR)
win_r_h, win_r = hinge(A_R, WIN_R_K, WIN_DUR)

M_FL, M_R = hard(FLAP_FL, (300, 330)), hard(FLAP_R, (800, 360))
M_BL, M_BR, M_BR_CORE = hard(FLAP_BL, (200, 210)), hard(FLAP_BR, (650, 250)), hard(FLAP_BR_CORE, (650, 250))

RIG = {
    "id": "H7",
    "parts": [
        # the front flaps claim first (they own the outlines they share with the back flaps)
        {"name": "flap_fl", "mask": M_FL, "pivot": HINGE_FL, "parent": "hinge_fl"},
        {"name": "flap_r", "mask": M_R, "pivot": HINGE_R, "parent": "hinge_r"},
        {"name": "flap_bl", "mask": M_BL, "pivot": (200, 256), "parent": "body", "exclusive": False},
        {"name": "flap_br", "mask": M_BR, "pivot": (600, 325), "parent": "body", "exclusive": False},
        # the box: everything but the flaps (an explicit mask, so it keeps the wall under the back-right
        # flap's overlap; "grow" so the silhouette's soft edge is taken whole)
        {"name": "body", "mask": ("minus", ("grow", ("opaque",), 2), ("or", M_FL, M_R, M_BL, M_BR_CORE)), "pivot": BASE, "exclusive": False},
        {"name": "hinge_fl", "sprite": "sparkle", "size": 2, "at": HINGE_FL, "hidden": True, "parent": "body"},
        {"name": "hinge_r", "sprite": "sparkle", "size": 2, "at": HINGE_R, "hidden": True, "parent": "body"},
        {"name": "poof", "sprite": "puff", "size": 30, "at": (590, 380), "hidden": True, "parent": "body"},
        {"name": "spark1", "sprite": "sparkle", "size": 15, "at": OPENING, "hidden": True},
        {"name": "spark2", "sprite": "sparkle", "size": 12, "at": OPENING, "hidden": True},
        {"name": "spark3", "sprite": "sparkle", "size": 10, "at": OPENING, "hidden": True},
        {"name": "glint", "sprite": "sparkle", "size": 14, "at": (262, 470), "hidden": True, "parent": "body"},
    ],
    "draw": ["flap_bl", "flap_br", "body", "poof", "hinge_fl", "hinge_r", "flap_fl", "flap_r", "glint", "spark1", "spark2", "spark3"],
    "anims": {
        "idle": {"dur": IDLE_DUR, "bones": {
            "body": joined(bump(K1), bump(K2, .65)),
            "hinge_fl": idle_fl_h, "flap_fl": idle_fl, "hinge_r": idle_r_h, "flap_r": idle_r,
            "flap_bl": {"sy": [(0, 1)] + flap(K1, .1, .02, back=True) + flap(K2, .07, .02, back=True)},
            "flap_br": {"sy": [(0, 1)] + flap(K1, .09, .07, back=True) + flap(K2, .06, .07, back=True)},
            "spark1": sparkle_keys(1.7, .6, 1.5, 3.5, peak=1.0, spin=80),
        }, "alpha": {"spark1": sparkle_alpha(1.7, .6)}},
        "land": {"dur": LAND_DUR, "bones": {
            "body": {"sy": [(0, 1), (.07, .93, "in"), (.2, 1.025, "out"), (.34, .995), (.48, 1)],
                     "sx": [(0, 1), (.07, 1.04, "in"), (.2, .99, "out"), (.34, 1.002), (.48, 1)]},
            "hinge_fl": land_fl_h, "flap_fl": land_fl, "hinge_r": land_r_h, "flap_r": land_r,
            "flap_bl": {"sy": [(0, 1), (.08, .91, "in"), (.22, 1.06, "out"), (.36, .98, "inout"), (.5, 1, "soft")]},
            "flap_br": {"sy": [(0, 1), (.09, .92, "in"), (.24, 1.05, "out"), (.38, .985, "inout"), (.52, 1, "soft")]},
        }},
        "win": {"dur": WIN_DUR, "bones": {
            "body": {"sy": [(0, 1), (.1, .93, "inout"), (.22, 1.06, "out"), (.38, 1.0, "inout"), (.46, .95, "in"), (.58, 1.02, "out"), (.72, 1, "soft")],
                     "sx": [(0, 1), (.1, 1.04, "inout"), (.22, .97, "out"), (.38, 1.0, "inout"), (.46, 1.03, "in"), (.58, .99, "out"), (.72, 1, "soft")],
                     "y": [(0, 0), (.1, 0, "linear"), (.27, 3.6, "out"), (.44, 0, "in"), (.58, .6, "out"), (.7, 0, "in")],
                     "r": [(0, 0), (.1, -1, "inout"), (.27, 2.2, "out"), (.44, -.8, "in"), (.6, .5, "out"), (.8, 0, "soft")]},
            "hinge_fl": win_fl_h, "flap_fl": win_fl, "hinge_r": win_r_h, "flap_r": win_r,
            "flap_bl": {"sy": [(0, 1), (.1, .9, "inout"), (.25, 1.15, "back"), (.42, .96, "inout"), (.56, 1.07, "inout"), (.72, .98, "inout"), (.88, 1, "soft")]},
            "flap_br": {"sy": [(0, 1), (.12, .9, "inout"), (.27, 1.13, "back"), (.44, .96, "inout"), (.58, 1.06, "inout"), (.74, .985, "inout"), (.9, 1, "soft")]},
            "glint": sparkle_keys(.5, .45, 0, 0, peak=1.2, spin=90),
            "poof": {"sx": [(0, 1), (.16, 1, "step"), (.17, .45, "step"), (.58, 1.45, "out"), (.6, 1, "step")],
                     "sy": [(0, 1), (.16, 1, "step"), (.17, .45, "step"), (.58, 1.3, "out"), (.6, 1, "step")],
                     "y": [(0, 0), (.17, 0), (.58, 18, "out"), (.6, 0, "step")]},
            "spark1": sparkle_keys(.2, .7, -21, 29, spin=110),
            "spark2": sparkle_keys(.27, .66, 21, 18, spin=-100),
            "spark3": sparkle_keys(.36, .62, 2, 38, peak=1.3, spin=90),
        }, "alpha": {
            "poof": [(0, 0), (.17, 0, "step"), (.23, .95), (.42, .85, "linear"), (.58, 0, "in")],
            "glint": sparkle_alpha(.5, .45),
            "spark1": sparkle_alpha(.2, .7), "spark2": sparkle_alpha(.27, .66), "spark3": sparkle_alpha(.36, .62),
        }},
    },
}
