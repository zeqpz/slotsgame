# L5 - A pair of dice, caught mid-tumble: each stands on a corner, so they rock on those corners.
# Idle: the top die rattles on its corner and the bottom one rocks back against it; then the
# bottom die gives a little hop, lands tilted on its corner and rocks back to rest, nudging the
# top one. Land: both clack down - a small squash and a rock each. Win: they roll a hop: a crouch,
# both jump and tumble a full turn (opposite ways, a beat apart), land tilted and rock to rest,
# with two twinkles at the top of the jump.
#
# The rocking is a rotation about the corner a die stands on; each bone pivots on its die's
# centre (so the tumble spins in place), and the keys below add the shift that keeps the corner
# planted while it rocks (see `track`).
import math

A_C, A_FOOT = (304, 340), (300, 604)       # top die: centre, the corner it stands on
B_C, B_FOOT = (700, 640), (722, 893)       # bottom die
PPU = 10.0                                 # icon px per skeleton unit (1000 px icon = 100 units)

# the dice only touch through their shared white border; the cut runs down its middle
DIE_A = ("poly", [(0, 0), (600, 0), (595, 380), (574, 405), (566, 420), (557, 435), (543, 450), (524, 465), (504, 480),
                  (483, 495), (464, 510), (446, 525), (429, 540), (410, 560), (395, 600), (395, 1000), (0, 1000)])


def track(c, foot, keys):
    """keys: (t, deg, sx, sy, hop_x, hop_y, planted, ease). A planted key turns/squashes the die about
    its foot (the corner stays put); otherwise about its centre, lifted by the hop (in units)."""
    dx, dy = (foot[0] - c[0]) / PPU, (c[1] - foot[1]) / PPU      # foot - centre, skeleton units (y up)
    ch = {"r": [], "sx": [], "sy": [], "x": [], "y": []}
    for t, deg, sx, sy, hx, hy, planted, ease in keys:
        tx, ty = hx, hy
        if planted:
            a = math.radians(deg); co, si = math.cos(a), math.sin(a)
            px, py = dx * sx, dy * sy                               # scale, then rotate (Spine's order)
            tx += dx - (px * co - py * si); ty += dy - (px * si + py * co)
        for k, v in (("r", deg), ("sx", sx), ("sy", sy), ("x", tx), ("y", ty)):
            e = ease.get(k, ease.get("*", "inout")) if isinstance(ease, dict) else ease
            ch[k].append((t, round(v, 4)) if t == 0 else (t, round(v, 4), e))
    return {k: v for k, v in ch.items() if any(abs(x[1] - (1 if k in ("sx", "sy") else 0)) > 1e-6 for x in v)}


def twinkle(t0, t1, peak=1.2, spin=90):
    """a sparkle that flares and fades between t0 and t1 - (bone channels, alpha keys); hidden
    either side, and every channel is back at rest once it has faded"""
    tm = t0 + (t1 - t0) * .45
    s = [(0, 1), (t0, .3, "step"), (tm, peak, "out"), (t1, .2, "in"), (t1 + .01, 1, "step")]
    return ({"sx": s, "sy": list(s), "r": [(0, 0), (t0, 0), (t1, spin, "linear"), (t1 + .01, 0, "step")]},
            [(0, 0), (t0, 0, "step"), (t0 + (t1 - t0) * .3, 1), (t1, 0)])


P = True
AIR_UP = {"r": "linear", "*": "out"}       # in the air the tumble turns at an even rate, the hop eases
AIR_DOWN = {"r": "linear", "*": "in"}
RIG = {
    "id": "L5",
    "parts": [
        {"name": "die_a", "mask": DIE_A, "pivot": A_C},
        {"name": "die_b", "mask": "rest", "pivot": B_C},
        {"name": "tw_a", "sprite": "sparkle", "size": 14, "at": (110, 120), "hidden": True},      # beside the dice at the top of the jump
        {"name": "tw_b", "sprite": "sparkle", "size": 12, "at": (905, 470), "hidden": True},
        {"name": "dust", "sprite": "puff", "size": 24, "at": (722, 900), "hidden": True},          # kicked out from under the bottom die as it lands
    ],
    "draw": ["die_a", "dust", "die_b", "tw_a", "tw_b"],          # the lower die is the nearer one: it passes in front
    "anims": {
        "idle": {"dur": 2.6, "bones": {
            # rattles on its corner ... then is nudged when the other die lands
            "die_a": track(A_C, A_FOOT,
                           [(0, 0, 1, 1, 0, 0, P, "inout"), (.2, 5.4, 1, 1, 0, 0, P, "out"), (.39, -2.6, 1, 1, 0, 0, P, "inout"),
                            (.53, 1.2, 1, 1, 0, 0, P, "inout"), (.65, -.45, 1, 1, 0, 0, P, "inout"), (.77, 0, 1, 1, 0, 0, P, "inout"),
                            (1.62, 0, 1, 1, 0, 0, P, "inout"), (1.72, 1.3, 1, 1, 0, 0, P, "out"), (1.84, -.6, 1, 1, 0, 0, P, "inout"),
                            (1.96, .2, 1, 1, 0, 0, P, "inout"), (2.06, 0, 1, 1, 0, 0, P, "inout")]),
            # rocks back against it; then hops, turns a little in the air, lands tilted and rocks to rest
            "die_b": track(B_C, B_FOOT,
                           [(0, 0, 1, 1, 0, 0, P, "inout"), (.12, 0, 1, 1, 0, 0, P, "inout"), (.28, -3.0, 1, 1, 0, 0, P, "out"),
                            (.43, 1.3, 1, 1, 0, 0, P, "inout"), (.56, -.45, 1, 1, 0, 0, P, "inout"), (.68, 0, 1, 1, 0, 0, P, "inout"),
                            (1.18, 0, 1, 1, 0, 0, P, "inout"), (1.26, 0, 1.03, .95, 0, 0, P, "inout"),           # crouch
                            (1.44, 4.0, 1, 1.02, 0, 3.6, False, "out"),                                          # up
                            (1.60, 9.0, 1, 1, 0, 0, P, "in"),                                                    # lands on its corner, tilted
                            (1.66, 9.0, 1.03, .95, 0, 0, P, "out"),
                            (1.78, -3.0, 1, 1, 0, 0, P, "inout"), (1.90, 1.2, 1, 1, 0, 0, P, "inout"),
                            (2.01, -.4, 1, 1, 0, 0, P, "inout"), (2.12, 0, 1, 1, 0, 0, P, "inout")]),
        }},
        "land": {"dur": .5, "bones": {
            "die_a": track(A_C, A_FOOT, [(0, 0, 1, 1, 0, 0, P, "inout"), (.06, 0, 1.03, .95, 0, 0, P, "in"), (.16, -2.6, 1, 1, 0, 0, P, "out"),
                                         (.28, 1.2, 1, 1, 0, 0, P, "inout"), (.38, -.4, 1, 1, 0, 0, P, "inout"), (.46, 0, 1, 1, 0, 0, P, "inout")]),
            "die_b": track(B_C, B_FOOT, [(0, 0, 1, 1, 0, 0, P, "inout"), (.09, 0, 1.03, .95, 0, 0, P, "in"), (.19, 2.4, 1, 1, 0, 0, P, "out"),
                                         (.31, -1.1, 1, 1, 0, 0, P, "inout"), (.41, .35, 1, 1, 0, 0, P, "inout"), (.5, 0, 1, 1, 0, 0, P, "inout")]),
        }},
        "win": {"dur": 1.4, "bones": {
            # crouch, jump up-left while tumbling a full turn clockwise, land tilted, rock to rest
            "die_a": track(A_C, A_FOOT, [(0, 0, 1, 1, 0, 0, P, "inout"), (.12, 0, 1.04, .93, 0, 0, P, "inout"),
                                         (.42, -180, 1, 1.03, -3.0, 8.0, False, AIR_UP),
                                         (.70, -354, 1, 1, 0, 0, P, AIR_DOWN),
                                         (.7001, 6, 1, 1, 0, 0, P, "step"),
                                         (.76, 6, 1.04, .94, 0, 0, P, "out"),
                                         (.88, -2.6, 1, 1, 0, 0, P, "inout"), (1.0, 1.1, 1, 1, 0, 0, P, "inout"),
                                         (1.11, -.4, 1, 1, 0, 0, P, "inout"), (1.22, 0, 1, 1, 0, 0, P, "inout")]),
            "die_b": track(B_C, B_FOOT, [(0, 0, 1, 1, 0, 0, P, "inout"), (.18, 0, 1.04, .93, 0, 0, P, "inout"),
                                         (.48, 180, 1, 1.03, 3.0, 6.5, False, AIR_UP),
                                         (.76, 355, 1, 1, 0, 0, P, AIR_DOWN),
                                         (.7601, -5, 1, 1, 0, 0, P, "step"),
                                         (.82, -5, 1.04, .94, 0, 0, P, "out"),
                                         (.94, 2.2, 1, 1, 0, 0, P, "inout"), (1.06, -.9, 1, 1, 0, 0, P, "inout"),
                                         (1.17, .3, 1, 1, 0, 0, P, "inout"), (1.28, 0, 1, 1, 0, 0, P, "inout")]),
            "dust": {"sx": [(0, 1), (.76, .5, "step"), (1.22, 1.7, "out"), (1.23, 1, "step")],
                     "sy": [(0, 1), (.76, .4, "step"), (1.22, .95, "out"), (1.23, 1, "step")],
                     "y": [(0, 0), (.76, 0), (1.22, -.6, "out"), (1.23, 0, "step")]},
            "tw_a": twinkle(.30, .66, spin=-90)[0],
            "tw_b": twinkle(.38, .74)[0],
        }, "alpha": {
            "tw_a": twinkle(.30, .66, spin=-90)[1],
            "tw_b": twinkle(.38, .74)[1],
            "dust": [(0, 0), (.76, 0, "step"), (.80, 1), (1.22, 0, "in")],
        }},
    },
}
