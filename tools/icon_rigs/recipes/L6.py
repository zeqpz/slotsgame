# L6 - Camo t-shirt. Cloth in a breeze: the shirt sways a little as if on a hanger, the sleeves
# flutter on their armholes (lifted by the wind and dropping back, each in its own rhythm), the
# hem billows and the body breathes in and out. Land: it drops in and the cloth flops - sleeves
# flick up and settle, the hem billows. Win: a gust hits it - the shirt puffs out, the sleeves
# blow up and flap, the logo pops, two wind streaks whip past.
#
# Cut: each sleeve is cut along its armhole seam and reaches a band further in under the body
# (both hold those pixels), so the sleeve can swing without opening a gap. The hem is a copy of
# the shirt's bottom with a feathered top edge laid over the body: it only ever billows down from
# its rest size (never wider, barely tilted), so the body's own hem never shows past it. The logo
# likewise only grows.
L_SEAM = [(172, 145), (196, 176), (206, 220), (217, 266), (230, 305), (242, 341), (249, 391), (251, 430), (251, 468),
          (245, 497), (222, 530), (200, 600)]   # left armhole seam, shoulder to armpit, then out through the gap under the arm
R_SEAM = [(755, 140), (748, 172), (745, 220), (743, 270), (741, 320), (740, 360), (737, 400), (734, 436), (746, 462),
          (765, 500), (790, 600)]
BAND = 45                                   # how far a sleeve reaches in under the body

SLEEVE_L_CUT = ("poly", [(0, 100), (172, 100)] + L_SEAM + [(0, 600)])
SLEEVE_R_CUT = ("poly", [(755, 100), (1000, 100), (1000, 600)] + R_SEAM[::-1])
SLEEVE_L = ("or", SLEEVE_L_CUT, ("poly", L_SEAM[1:9] + [(x + BAND, y) for x, y in reversed(L_SEAM[1:9])]))
SLEEVE_R = ("or", SLEEVE_R_CUT, ("poly", R_SEAM[1:8] + [(x - BAND, y) for x, y in reversed(R_SEAM[1:8])]))
BODY = ("minus", ("opaque",), ("or", SLEEVE_L_CUT, SLEEVE_R_CUT))
# the logo: its white outline, every pocket inside it filled
RING = ("grow", ("cc", ("color", "#ffffff", 70), 268, 340), 3)
LOGO = ("minus", ("rect", 240, 220, 740, 720), ("cc", ("minus", ("rect", 236, 216, 744, 724), RING), 238, 218))
HEM = ("rect", 150, 792, 850, 1000)



def gust(t0, t1, dist):
    """a wind streak whipping left to right across the shirt between t0 and t1 (the sprite's head is
    on its left, so it flies mirrored); every channel is back at rest once it has faded"""
    k = lambda v: (t1 + .01, v, "step")
    return ({"x": [(0, 0), (t0, 0), (t1, dist, "out"), k(0)],
             "sx": [(0, 1), (t0, -1, "step"), (t1, -1), k(1)],
             "sy": [(0, 1), (t0, .6, "step"), (t0 + (t1 - t0) * .4, 1.0), (t1, .5), k(1)]},
            [(0, 0), (t0, 0, "step"), (t0 + .1, .85), (t1 - .16, .7), (t1, 0)])


COLLAR = (500, 80)          # the shirt hangs (and sways) from here
ARMHOLE_L, ARMHOLE_R = (230, 320), (741, 320)   # the sleeves swing about the middle of their armholes

RIG = {
    "id": "L6",
    "parts": [
        {"name": "logo", "mask": LOGO, "pivot": (490, 420), "parent": "body"},
        {"name": "sleeve_l", "mask": SLEEVE_L, "pivot": ARMHOLE_L, "parent": "body"},
        {"name": "sleeve_r", "mask": SLEEVE_R, "pivot": ARMHOLE_R, "parent": "body"},
        {"name": "body", "mask": BODY, "pivot": COLLAR, "exclusive": False},
        {"name": "hem", "mask": HEM, "pivot": (500, 792), "parent": "body", "exclusive": False, "feather": 12},
        {"name": "gust_a", "sprite": "streak", "size": 32, "args": {"h": 24}, "at": (170, 290), "hidden": True},
        {"name": "gust_b", "sprite": "streak", "size": 26, "args": {"h": 24}, "at": (200, 650), "hidden": True},
    ],
    "draw": ["sleeve_l", "sleeve_r", "body", "hem", "logo", "gust_a", "gust_b"],
    "anims": {
        # a breeze from the left: the shirt leans with it, the sleeves flutter a beat apart
        "idle": {"dur": 2.8, "bones": {
            "body": {"r": [(0, 0), (.6, 1.6), (1.3, -.8), (1.95, .4), (2.55, 0)],
                     "sx": [(0, 1), (.5, 1.022), (1.1, .996), (1.7, 1.012), (2.3, 1.0)]},
            "sleeve_l": {"r": [(0, 0), (.3, -3.6, "out"), (.62, -.8), (.94, -2.8), (1.26, -.5), (1.6, -1.6), (1.95, -.2), (2.35, 0)]},
            "sleeve_r": {"r": [(0, 0), (.42, 3.3, "out"), (.75, .6), (1.07, 2.5), (1.4, .4), (1.74, 1.3), (2.1, .1), (2.5, 0)]},
            "hem": {"sy": [(0, 1), (.45, 1.04), (.85, 1.012), (1.25, 1.034), (1.65, 1.01), (2.05, 1.024), (2.45, 1.0)],
                    "r": [(0, 0), (.45, .3), (.85, -.12), (1.25, .2), (1.65, -.06), (2.05, .08), (2.45, 0)]},
        }},
        # dropped in: the cloth flops - sleeves flick up and fall back, the hem flares
        "land": {"dur": .55, "bones": {
            "body": {"sy": [(0, 1), (.08, 1.03, "in"), (.2, .985, "out"), (.34, 1.004), (.46, 1.0)],
                     "sx": [(0, 1), (.08, .985, "in"), (.2, 1.015, "out"), (.34, 1.0)]},
            "sleeve_l": {"r": [(0, 0), (.1, -3.4, "out"), (.25, .5), (.39, -.8), (.52, 0)]},
            "sleeve_r": {"r": [(0, 0), (.12, 3.2, "out"), (.27, -.5), (.41, .7), (.55, 0)]},
            "hem": {"sy": [(0, 1), (.1, 1.05, "out"), (.26, 1.008), (.4, 1.02), (.55, 1.0)]},
        }},
        # a gust: the shirt puffs out and leans, the sleeves blow up and flap, the logo pops
        "win": {"dur": 1.4, "bones": {
            "body": {"sx": [(0, 1), (.1, .985), (.3, 1.07, "back"), (.7, 1.04), (1.2, 1.0, "inout")],
                     "sy": [(0, 1), (.1, 1.0), (.3, 1.03, "back"), (.7, 1.015), (1.2, 1.0, "inout")],
                     "r": [(0, 0), (.12, 0), (.34, 2.0, "out"), (.62, -.9), (.88, .7), (1.12, -.25), (1.36, 0)]},
            "sleeve_l": {"r": [(0, 0), (.12, .3), (.3, -4.6, "out"), (.44, -2.6), (.58, -4.0), (.72, -1.8), (.86, -2.7), (1.02, -.8), (1.18, -1.1), (1.36, 0)]},
            "sleeve_r": {"r": [(0, 0), (.14, -.3), (.33, 4.3, "out"), (.47, 2.3), (.61, 3.7), (.75, 1.5), (.89, 2.4), (1.05, .6), (1.21, .8), (1.38, 0)]},
            "hem": {"sy": [(0, 1), (.12, 1.0), (.32, 1.08, "out"), (.5, 1.035), (.68, 1.065), (.86, 1.025), (1.04, 1.04), (1.3, 1.0)],
                    "r": [(0, 0), (.12, 0), (.32, .35, "out"), (.5, -.12), (.68, .25), (.86, -.06), (1.04, .12), (1.3, 0)]},
            "logo": {"sx": [(0, 1), (.16, 1), (.38, 1.14, "back"), (.86, 1.08), (1.2, 1.0, "inout")],
                     "sy": [(0, 1), (.16, 1), (.38, 1.14, "back"), (.86, 1.08), (1.2, 1.0, "inout")]},
            "gust_a": gust(.08, .6, 64)[0],
            "gust_b": gust(.2, .74, 58)[0],
        }, "alpha": {
            "gust_a": gust(.08, .6, 64)[1],
            "gust_b": gust(.2, .74, 58)[1],
        }},
    },
}
