# H5 - Boombox. It plays: both speaker cones thump outward on every kick, the box bobs on its
# base to the beat, the carry handle rattles a beat behind and the three keys on top click down
# in turn. Land: it thuds onto its base and the cones jump from the knock. Win: double-time
# bass - the box hops and rocks, the cones pump hard and sound lines fan out of both sides.
import math

BASE = (470, 790)          # the middle of the bottom edge: the box squashes and hops from here
SPK_L = (162, 568)         # left speaker centre (outer black ring 62..262 x 447..690)
SPK_R = (716, 630)         # right speaker centre (outer ring 577..855 x 475..785)
HINGE = (952, 262)         # where the handle's right post meets the side panel: it rattles about here
PPU = 10.0                 # icon px per skeleton unit (1000 px icon = 100 units)


def env(hits, shape, rest):
    """keys for a per-hit envelope: shape is [(dt, amp, ease)] and a hit of strength s reads
    rest + amp * s at t + dt; a hit's tail is cut off where the next hit begins"""
    k = [(0, rest)]
    starts = [t for t, _ in hits][1:] + [1e9]
    for (t, s), nxt in zip(hits, starts):
        k.append((t, rest, "linear"))
        k += [(t + dt, rest + amp * s, e) for dt, amp, e in shape if t + dt < nxt - .005]
    return k


def pump(hits, amp, attack=.045, decay=.17, settle=.3, under=.015):
    """scale keys for a speaker cone: a fast push out on every hit, a soft fall back"""
    return env(hits, [(attack, amp, "out"), (decay, -under, "inout"), (settle, 0, "soft")], 1)


def bob(hits, sq=.03, hop=.6):
    """the box on the beat: squash on the hit, a small spring up, back to rest"""
    return {"sy": env(hits, [(.05, -sq, "out"), (.17, sq * .4, "inout"), (.32, 0, "soft")], 1),
            "sx": env(hits, [(.05, sq * .5, "out"), (.17, -sq * .2, "inout"), (.32, 0, "soft")], 1),
            "y": env(hits, [(.05, 0, "linear"), (.17, hop, "out"), (.32, 0, "in")], 0)}


def rattle(hits, amp=.5):
    """the handle lags the box: it dips as the box squashes, kicks up as it springs, settles"""
    return {"r": env(hits, [(.02, 0, "linear"), (.09, -amp, "out"), (.2, amp * .6, "inout"), (.32, 0, "soft")], 0)}


def press(times, depth=1.1):
    k = [(0, 0)]
    for t in times:
        k += [(t, 0, "linear"), (t + .04, -depth, "in"), (t + .2, 0, "out")]
    return k


IDLE_HITS = [(.15, 1), (.55, .55), (.95, 1), (1.25, .7), (1.65, .6)]
WIN_HITS = [(.05, 1.2), (.30, .8), (.55, 1.2), (.80, .8), (1.05, 1.0)]

# sound lines: three per side, fanned out from the box's flanks at speaker height
FAN = [-24, 0, 24]
ORIGIN = {"l": (40, 585), "r": (965, 640)}
LINE_LEN = 10              # units


def line_part(side, i, a):
    ox, oy = ORIGIN[side]
    sgn = -1 if side == "l" else 1
    ang = math.radians(a)                      # + = up, on either side
    dx, dy = sgn * math.cos(ang), -math.sin(ang)   # image px direction (y down)
    off = 2 + LINE_LEN * PPU / 2
    return {"name": f"line_{side}{i}", "sprite": "streak", "size": LINE_LEN, "args": {"w": 120, "h": 26},
            "at": (ox + dx * off, oy + dy * off), "hidden": True, "parent": "body"}


def line_keys(side, a, t0, travel=7, dur=.34):
    """flip to face outward while hidden, shoot off along the fan direction and fade"""
    sgn = -1 if side == "l" else 1
    ang = math.radians(a)
    ux, uy = sgn * math.cos(ang), math.sin(ang)    # skeleton units direction (y up)
    rot = a if side == "r" else -a                 # the sprite's point faces left; mirrored on the right
    end = t0 + dur + .01
    return {"x": [(0, 0), (t0, 0, "step"), (t0 + dur, ux * travel, "out"), (end, 0, "step")],
            "y": [(0, 0), (t0, 0, "step"), (t0 + dur, uy * travel, "out"), (end, 0, "step")],
            "r": [(0, 0), (t0, rot, "step"), (end, 0, "step")],
            "sx": [(0, 1), (t0, -sgn * .6, "step"), (t0 + dur, -sgn * 1.1, "out"), (end, 1, "step")]}


def line_alpha(t0, dur=.34):
    return [(0, 0), (t0, 0, "step"), (t0 + .04, 1), (t0 + dur, 0, "in")]


LINES = [(s, i, a) for s in "lr" for i, a in enumerate(FAN)]


def lines(kicks, snares=(), travel=7, dur=.34):
    """bones + alpha for the sound lines: every kick fires the outer pair of each fan, every
    snare the middle line; the right side fires a frame after the left"""
    bones, alpha = {}, {}
    for s, i, a in LINES:
        lag = .01 + (.02 if s == "r" else 0)
        times = [t + lag for t in (snares if i == 1 else kicks)]
        if not times:
            continue
        ks = [line_keys(s, a, t0, travel, dur) for t0 in times]
        al = [line_alpha(t0, dur) for t0 in times]
        bones[f"line_{s}{i}"] = {ch: ks[0][ch] + [k for kk in ks[1:] for k in kk[ch][1:]] for ch in ks[0]}
        alpha[f"line_{s}{i}"] = al[0] + [k for aa in al[1:] for k in aa[1:]]
    return bones, alpha


IDLE_LINES = lines([.95], travel=4, dur=.3)
WIN_LINES = lines([.05, .55], [.30, .80], travel=5)


RIG = {
    "id": "H5",
    "parts": [
        {"name": "spk_l", "mask": ("cc", ("ellipse", 162, 568, 101, 123), 162, 568), "pivot": SPK_L, "parent": "body", "fill": "body"},
        {"name": "spk_r", "mask": ("cc", ("ellipse", 716, 630, 140, 156), 716, 630), "pivot": SPK_R, "parent": "body", "fill": "body"},
        # the keys sit on the lid's top edge; they sink behind it (no fill: the gap above a pressed key is
        # open sky; "cc" makes the rectangles hard-edged, so no seam where they meet the lid)
        {"name": "key1", "mask": ("cc", ("rect", 630, 222, 690, 254), 660, 240), "pivot": (660, 254), "parent": "body"},
        {"name": "key2", "mask": ("cc", ("rect", 706, 222, 767, 254), 736, 240), "pivot": (736, 254), "parent": "body"},
        {"name": "key3", "mask": ("cc", ("rect", 781, 222, 846, 254), 813, 240), "pivot": (813, 254), "parent": "body"},
        # the carry handle: the loop above the lid, down to where its posts meet the body (hard-edged
        # - "cc" thresholds the polygon - so where it meets the lid in flat paint there is no seam)
        {"name": "handle", "mask": ("cc", ("poly", [(90, 246), (101, 200), (128, 128), (600, 96), (1000, 98), (1000, 262),
                                                    (930, 262), (926, 236), (600, 236), (176, 224), (152, 246)]), 500, 150),
         "pivot": HINGE, "parent": "body"},
        {"name": "body", "mask": "rest", "pivot": BASE},
    ] + [line_part(s, i, a) for s, i, a in LINES],
    "draw": ["handle", "key1", "key2", "key3", "body", "spk_l", "spk_r"] + [f"line_{s}{i}" for s, i, a in LINES],
    "anims": {
        "idle": {"dur": 2.4, "bones": {
            "body": bob(IDLE_HITS),
            "handle": rattle(IDLE_HITS, .35),
            "spk_l": {"sx": pump(IDLE_HITS, .085), "sy": pump(IDLE_HITS, .085)},
            "spk_r": {"sx": pump([(t + .02, s) for t, s in IDLE_HITS], .075), "sy": pump([(t + .02, s) for t, s in IDLE_HITS], .075)},
            "key1": {"y": press([.35])},
            "key2": {"y": press([.75, 1.45])},
            "key3": {"y": press([1.10])},
            **IDLE_LINES[0],
        }, "alpha": IDLE_LINES[1]},
        "land": {"dur": .55, "bones": {
            "body": {"sy": [(0, 1), (.07, .93, "in"), (.2, 1.025, "out"), (.34, .995), (.48, 1)],
                     "sx": [(0, 1), (.07, 1.035, "in"), (.2, .99, "out"), (.34, 1.002), (.48, 1)],
                     "y": [(0, 0), (.07, 0), (.2, .9, "out"), (.34, 0, "in")]},
            "handle": {"r": [(0, 0), (.08, -.7, "in"), (.22, .45, "out"), (.36, -.12), (.5, 0)]},
            "spk_l": {"sx": pump([(.06, 1)], .1), "sy": pump([(.06, 1)], .1)},
            "spk_r": {"sx": pump([(.08, 1)], .09), "sy": pump([(.08, 1)], .09)},
            "key1": {"y": press([.07], .8)}, "key2": {"y": press([.09], .8)}, "key3": {"y": press([.11], .8)},
        }},
        "win": {"dur": 1.4, "bones": dict({
            "body": dict(bob(WIN_HITS, sq=.045, hop=2.4),
                         r=[(0, 0), (.17, 2.2, "out"), (.42, -2.2, "inout"), (.67, 2.0, "inout"), (.92, -1.6, "inout"), (1.17, .5, "inout"), (1.38, 0, "soft")]),
            "handle": rattle(WIN_HITS, .6),
            "spk_l": {"sx": pump(WIN_HITS, .13, settle=.24), "sy": pump(WIN_HITS, .13, settle=.24)},
            "spk_r": {"sx": pump([(t + .02, s) for t, s in WIN_HITS], .115, settle=.24), "sy": pump([(t + .02, s) for t, s in WIN_HITS], .115, settle=.24)},
            "key1": {"y": press([.17, .67])}, "key2": {"y": press([.42, .92])}, "key3": {"y": press([.30, .80, 1.15])},
        }, **WIN_LINES[0]), "alpha": WIN_LINES[1]},
    },
}
