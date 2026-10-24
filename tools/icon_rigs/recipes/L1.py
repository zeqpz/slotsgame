# L1 - Spray can, spraying. The painted cloud is gone from the rig (it was one picture, chopped
# into copies that faded in and out): the can now sprays a live mist. A stream of paint-mist
# puffs is born where the jet fans out, each one growing, slowing and drifting off as it thins
# away, then born again - staggered, so the can is always spraying, and at rest the puffs where
# they sit make the cloud. The jet flickers and the cap dips as if the button is held.
# Land: the can rocks on its base. Win: a hard press - the jet shoots longer and the mist bursts
# out twice as fast and twice as far.
import math

NOZZLE = (668, 158)
SPAWN = (476, 182)          # icon px: where the jet fans out into mist
PPU = 10                    # icon px per skeleton unit (1000 px icon = 100 units)
GREEN = (0, 255, 61)

# each puff: (phase in its life at rest, direction in degrees (180 = straight left, toward the
# old cloud), how far it travels in units, its size in units, seed)
PUFFS = [(.14, 176, 24, 26, 1), (.22, 196, 26, 23, 2), (.3, 160, 22, 24, 3), (.38, 186, 28, 27, 4),
         (.46, 206, 23, 22, 5), (.52, 168, 27, 26, 6), (.58, 190, 25, 28, 7), (.26, 150, 18, 19, 8),
         (.42, 214, 19, 19, 9), (.34, 182, 16, 18, 10), (.18, 200, 14, 17, 11), (.5, 140, 20, 21, 12),
         (.08, 182, 9, 13, 13)]


def smooth(a, b, x):
    t = min(1, max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t)


def life(u, dist):
    """offset (units, y up), scale and alpha of a puff `u` of the way through its life"""
    k = 1 - (1 - u) ** 1.8                      # fast out of the jet, slowing as it spreads
    return k * dist, .35 + .95 * u ** .7, smooth(0, .08, u) * (1 - smooth(.6, 1, u))


def puff_track(phase, ang, dist, lives, dur, spread=1.0, grow=1.0):
    """keyframes for one puff over a clip of `dur` s in which it lives `lives` times, starting and
    ending where it rests (its life at `phase`)"""
    a = math.radians(ang); dx, dy = math.cos(a), -math.sin(a)   # icon y is down, skeleton y is up
    def at(u):
        d, s, al = life(u, dist * spread)
        return d * dx, d * dy + 2.5 * u, s * (1 + (grow - 1) * u), al
    x0, y0, s0, _ = at(phase)
    keys = {"x": [], "y": [], "sx": [], "sy": [], "r": []}; alpha = []
    def add(t, u, ease=None):
        x, y, s, al = at(u)
        e = (ease,) if ease else ()
        keys["x"].append((t, x - x0, *e)); keys["y"].append((t, y - y0, *e))
        keys["sx"].append((t, s / s0, *e)); keys["sy"].append((t, s / s0, *e))
        keys["r"].append((t, (u - phase) * 40, *e))
        alpha.append((t, al, *e))
    n = 30
    for i in range(n + 1):
        t = dur * i / n
        u = phase + lives * t / dur
        if i and math.floor(phase + lives * dur * (i - 1) / n / dur) < math.floor(u):   # a life ended in this step: reborn
            tc = dur * (math.floor(u) - phase) / lives
            add(round(tc, 4), 1.0)
            add(round(tc + .001, 4), 0.0, "step")
        add(round(t, 4), u % 1 if i < n else phase)
    return keys, alpha


def puffs(dur, lives, spread=1.0, grow=1.0):
    bones, alpha = {}, {}
    for i, (ph, ang, dist, size, seed) in enumerate(PUFFS):
        k, a = puff_track(ph, ang, dist, lives, dur, spread, grow)
        bones[f"mist{i}"] = k; alpha[f"mist{i}"] = a
    return bones, alpha


def rest_at(ph, ang, dist):
    a = math.radians(ang)
    d, _, _ = life(ph, dist)
    return (SPAWN[0] + d * math.cos(a) * PPU, SPAWN[1] - (d * -math.sin(a) + 2.5 * ph) * PPU)


SIZE_K, DIST_K = 1.7, 1.25   # the puffs fill the space the painted cloud used to (x 136-486, y 32-440)
PUFFS = [(ph, ang, dist * DIST_K, size * SIZE_K, seed) for ph, ang, dist, size, seed in PUFFS]
MIST = [{"name": f"mist{i}", "sprite": "mist", "size": size * life(ph, dist)[1], "args": {"color": GREEN, "seed": seed},
         "at": rest_at(ph, ang, dist), "parent": "can"} for i, (ph, ang, dist, size, seed) in enumerate(PUFFS)]

IDLE_B, IDLE_A = puffs(3.0, 2)
WIN_B, WIN_A = puffs(1.4, 2, spread=1.5, grow=1.25)

RIG = {
    "id": "L1",
    "parts": [
        # the jet stops where the old cloud began; the mist takes over from there
        # (its cut end fades out over ~20 px, under the newest puff)
        {"name": "jet", "mask": ("and", ("poly", [(462, 127), (674, 148), (674, 170), (462, 235)]),
                                 ("blur", ("poly", [(492, 0), (1000, 0), (1000, 1000), (492, 1000)]), 12)),
         "pivot": NOZZLE, "parent": "cap"},
        # the painted cloud is cut out and never drawn
        # (grown, so its white sticker edge goes with it)
        {"name": "cloud", "mask": ("minus", ("grow", ("poly", [(146, 92), (168, 48), (250, 32), (335, 48), (412, 88), (474, 196), (486, 300), (424, 344),
                                            (364, 354), (318, 372), (306, 428), (240, 440), (164, 424), (136, 330), (140, 250)]), 22),
                                   ("poly", [(480, 60), (1000, 60), (1000, 1000), (300, 1000), (300, 470), (480, 400)])),
         "pivot": (300, 238), "parent": "can"},
        {"name": "cap", "mask": ("poly", [(562, 96), (598, 60), (812, 68), (802, 142), (762, 302), (700, 308), (640, 304), (612, 276)]),
         "pivot": (690, 300), "parent": "can", "fill": "can"},
        {"name": "can", "mask": "rest", "pivot": (420, 935)},
        *MIST,
    ],
    "draw": ["can", "cap", "jet"] + [m["name"] for m in MIST],
    "anims": {
        "idle": {"dur": 3.0, "bones": {
            "cap": {"y": [(0, 0), (.14, -1.4, "in"), (.36, 0, "out"), (1.55, 0), (1.68, -1.0, "in"), (1.9, 0, "out")]},
            "jet": {"sx": [(0, 1), (.2, 1.09, "out"), (.5, .95), (.85, 1.06), (1.25, .97), (1.7, 1.08), (2.2, .96), (2.6, 1.03), (3.0, 1)],
                    "sy": [(0, 1), (.35, 1.06), (.9, .94), (1.5, 1.05), (2.3, .96), (3.0, 1)],
                    "r": [(0, 0), (.6, 1.5), (1.4, -1.2), (2.2, 1.0), (3.0, 0)]},
            **IDLE_B,
        }, "alpha": IDLE_A},
        "land": {"dur": .6, "bones": {
            "can": {"r": [(0, 0), (.1, 3.2, "out"), (.26, -2.2), (.42, .8), (.6, 0)],
                    "sy": [(0, 1), (.08, .95, "in"), (.2, 1.02, "out"), (.34, 1)]},
        }},
        "win": {"dur": 1.4, "bones": {
            "cap": {"y": [(0, 0), (.10, -3.2, "in"), (1.0, -3.0), (1.2, 0, "out")]},
            "jet": {"sx": [(0, 1), (.16, 1.28, "out"), (.3, 1.12), (.45, 1.26), (.6, 1.14), (.75, 1.24), (1.0, 1.1), (1.25, 1, "out")],
                    "sy": [(0, 1), (.16, 1.18, "out"), (1.0, 1.1), (1.25, 1)]},
            "can": {"r": [(0, 0), (.08, -1.6), (.16, 1.4), (.24, -1.0), (.32, .6), (.42, 0)]},
            **WIN_B,
        }, "alpha": WIN_A},
    },
}
