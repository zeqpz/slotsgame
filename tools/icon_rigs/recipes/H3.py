# H3 - Gold chain. A Cuban-link loop with a box clasp. It hangs from its top and sways like a
# pendulum; a ripple runs round the links (each run of links swells in turn, as if the chain
# were being rolled through the fingers) with glints chasing it, and the clasp flashes.
# Land: the loop drops, squashes flat and the links rattle. Win: it is tossed like a coin -
# a crouch, up it goes flipping over once, and it lands with a rattle, a swing, the clasp
# popping and sparkles all round.
import math

HANG = (300, 196)                  # the top of the loop: it swings from here
MID = (488, 482)                   # the middle of the loop: it flips about here
# the loop's centre line, clockwise from the clasp
PATH = [(300, 545), (235, 487), (180, 440), (140, 380), (122, 320), (140, 262), (185, 218), (255, 200),
        (335, 208), (415, 238), (490, 290), (560, 345), (625, 405), (695, 455), (765, 510), (825, 570),
        (848, 640), (825, 705), (765, 740), (690, 752), (610, 740), (530, 715), (455, 690), (395, 645),
        (345, 595), (300, 545)]
CLASP = ("poly", [(205, 478), (258, 446), (302, 464), (362, 526), (416, 578), (420, 612), (384, 646),
                  (334, 658), (278, 626), (218, 568), (186, 520)])     # takes the clasp's white rim on the outside too
N = 7
SLICES = [f"s{i + 1}" for i in range(N)]
# the links run on 4 px under the clasp (drawn over them), so its edges never show a seam
CHAIN = ("minus", ("grow", ("opaque",), 2), ("shrink", CLASP, 4))

REST = {"x": 0, "y": 0, "r": 0, "sx": 1, "sy": 1}


def shown(on, off, dur, **chans):
    out = {}
    for ch, keys in chans.items():
        rest = REST[ch]
        out[ch] = [(0, rest), (on, keys[0][1], "step")] + list(keys[1:]) + [(off, rest, "step"), (dur, rest)]
    return out


def twinkle(on, peak, off, dur, size=1.1, spin=90):
    return shown(on, off + .02, dur, sx=[(on, .3), (peak, size, "out"), (off, .2, "in")],
                 sy=[(on, .3), (peak, size, "out"), (off, .2, "in")], r=[(on, 0), (off, spin, "linear")])


def fade(on, full, hold, off, peak=1.0):
    return [(0, 0), (on, 0, "step"), (full, peak), (hold, peak), (off, 0, "in")]


def ripple(start, span, amp=1.08, each=.22):
    """every slice swells and settles, one after another round the loop"""
    out = {}
    for i, s in enumerate(SLICES):
        t = start + span * i / N
        k = [(0, 1), (t, 1), (t + each * .45, amp, "out"), (t + each, 1, "inout")]
        out[s] = {"sx": k, "sy": k}
    return out


def merge(*dicts):
    out = {}
    for d in dicts:
        for k, v in d.items():
            out.setdefault(k, {}).update(v)
    return out


parts = [{"name": "clasp", "mask": CLASP, "pivot": (312, 548), "parent": "hang"}]
parts += [{"name": s, "mask": ("along", CHAIN, PATH, i / N, (i + 1) / N), "exclusive": False, "parent": "hang"}
          for i, s in enumerate(SLICES)]
parts += [
    # never shown: two bare bones - the toss (about the middle) carries the swing (from the top)
    {"name": "toss", "sprite": "sparkle", "size": 4, "at": MID, "pivot": MID, "hidden": True},
    {"name": "hang", "sprite": "sparkle", "size": 4, "at": HANG, "pivot": HANG, "hidden": True, "parent": "toss"},
    {"name": "g1", "sprite": "sparkle", "size": 14, "at": (150, 300), "hidden": True, "parent": "hang"},
    {"name": "g2", "sprite": "sparkle", "size": 13, "at": (520, 300), "hidden": True, "parent": "hang"},
    {"name": "g3", "sprite": "sparkle", "size": 14, "at": (830, 620), "hidden": True, "parent": "hang"},
    {"name": "g4", "sprite": "sparkle", "size": 16, "at": (300, 520), "hidden": True, "parent": "hang"},
]

RIG = {
    "id": "H3",
    "parts": parts,
    "draw": ["toss", "hang"] + SLICES + ["clasp", "g1", "g2", "g3", "g4"],
    "anims": {
        "idle": {"dur": 2.8, "bones": merge(
            {"hang": {"r": [(0, 0), (.48, 3.6), (1.04, -2.8), (1.56, 1.6), (2.02, -.6), (2.45, 0)]},
             "clasp": {"sx": [(0, 1), (1.9, 1), (2.04, 1.07, "out"), (2.3, 1)], "sy": [(0, 1), (1.9, 1), (2.04, 1.07, "out"), (2.3, 1)]},
             "g1": twinkle(.3, .45, .7, 2.8), "g2": twinkle(.75, .9, 1.15, 2.8, size=1.0, spin=-90),
             "g3": twinkle(1.2, 1.35, 1.6, 2.8), "g4": twinkle(1.92, 2.08, 2.4, 2.8, size=1.25)},
            ripple(.2, 1.7)),
            "alpha": {"g1": fade(.3, .4, .45, .7), "g2": fade(.75, .85, .9, 1.15), "g3": fade(1.2, 1.3, 1.35, 1.6),
                      "g4": fade(1.92, 2.02, 2.08, 2.4)}},
        "land": {"dur": .55, "bones": merge(ripple(.06, .22, amp=1.06, each=.14), {
            # squash about the middle, with y keeping the bottom of the loop planted (31 units below)
            "toss": {"y": [(0, 0), (.08, -2.5, "in"), (.2, 1.25, "out"), (.34, -.3), (.45, 0)],
                     "sy": [(0, 1), (.08, .92, "in"), (.2, 1.04, "out"), (.34, .99), (.45, 1)],
                     "sx": [(0, 1), (.08, 1.05, "in"), (.2, .98, "out"), (.34, 1)]},
            "hang": {"r": [(0, 0), (.1, -1.6), (.26, 1.1), (.42, -.3), (.55, 0)]},
        })},
        "win": {"dur": 1.4, "bones": merge(
            {"toss": {"y": [(0, 0), (.12, -3.1, "inout"), (.42, 8, "out"), (.70, 0, "in"), (.78, -3.1, "out"), (.9, .9), (1.02, 0)],
                      # one flip over the horizontal axis: sy follows cos() through 0 and -1
                      "sy": [(0, 1), (.12, .9, "inout"), (.27, .08, "in"), (.42, -1, "out"), (.56, -.08, "in"), (.70, 1, "out"),
                             (.78, .9, "out"), (.9, 1.03), (1.02, 1)],
                      "sx": [(0, 1), (.12, 1.05, "inout"), (.42, .96), (.70, 1), (.78, 1.05, "out"), (.9, .985), (1.02, 1)],
                      "r": [(0, 0), (.12, 0), (.42, -8, "inout"), (.70, 0, "inout")]},
             "hang": {"r": [(0, 0), (.70, 0), (.86, 3.2, "out"), (1.04, -1.8), (1.22, .6), (1.4, 0)]},
             "clasp": {"sx": [(0, 1), (.68, 1), (.80, 1.16, "back"), (1.1, 1)], "sy": [(0, 1), (.68, 1), (.80, 1.16, "back"), (1.1, 1)]},
             "g4": twinkle(.70, .84, 1.12, 1.4, size=1.4), "g1": twinkle(.74, .88, 1.14, 1.4, spin=-90),
             "g2": twinkle(.80, .94, 1.2, 1.4, size=1.2), "g3": twinkle(.86, 1.0, 1.28, 1.4, spin=-90)},
            ripple(.70, .36, amp=1.08, each=.16)),
            "alpha": {"g4": fade(.70, .78, .84, 1.12), "g1": fade(.74, .82, .88, 1.14), "g2": fade(.80, .88, .94, 1.2),
                      "g3": fade(.86, .94, 1.0, 1.28)}},
    },
}
