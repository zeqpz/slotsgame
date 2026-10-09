# L3 - Beanie. Soft knit, so it squashes and stretches: the whole hat breathes on its rim, the
# ribbed crown above the folded cuff lags behind and flops like jelly, and the graffiti logo on
# the cuff pops. The crown and the cuff share the seam's ink line (both masks hold it), so the
# crown can sway a little under the cuff's edge without opening a gap. The cuff keeps its own copy
# of the logo underneath (a hole that big would inpaint half-transparent): the logo only ever
# grows from its rest size, so the copy never shows. Land: a soft squash on the
# rim with the crown wobbling after. Win: squash, a stretchy hop, the crown flopping side to side
# and the logo popping out with two twinkles.
SEAM = [(166, 430), (180, 420), (200, 404), (220, 398), (240, 390), (260, 382), (280, 374), (300, 366),
        (320, 358), (340, 354), (360, 348), (380, 342), (400, 338), (420, 334), (440, 334), (460, 334),
        (480, 332), (500, 334), (520, 334), (540, 338), (560, 342), (580, 346), (600, 350), (620, 354),
        (640, 362), (660, 370), (680, 378), (700, 388), (720, 400), (740, 412), (760, 424), (780, 440),
        (800, 456), (820, 474), (840, 494), (860, 515), (880, 534), (893, 550)]   # centre of the cuff's top ink line


def band(lo, hi):                           # the strip between two offsets of the seam line (not its
    pts = SEAM[1:]                          # left end, where it runs into the hat's outline)
    return ("poly", [(x, y + lo) for x, y in pts] + [(x, y + hi) for x, y in reversed(pts)])


INK1 = ("grow", ("ink",), 1)                # the linework with its soft edge
# both masks hold the seam's whole ink line (and a few px either side of its centre), so the
# crown can sway a little under the cuff's edge and only ever shows its own copy of that line
CROWN = ("or", ("poly", [(30, 0), (970, 0), (970, 563), (920, 563)] + [(x, y + 3) for x, y in reversed(SEAM)] + [(130, 423), (30, 415)]),
         ("and", band(-16, 11), INK1))
CUFF = ("or", ("poly", [(30, 409), (130, 417)] + [(x, y - 3) for x, y in SEAM] + [(920, 557), (970, 557), (970, 1000), (30, 1000)]),
        ("and", band(-8, 16), ("ink",)))   # hard-edged: the crown's copy of the line meets it flush
BOX = ("rect", 262, 345, 780, 690)
WHITE = ("and", BOX, ("color", "#ffffff", 45))
OUTLINE = ("and", ("grow", WHITE, 14), ("ink",))          # the ink round the letters (14 px: the outline, not the rib lines)
SOLID = ("minus", ("rect", 266, 349, 776, 686), ("cc", ("minus", BOX, ("or", WHITE, OUTLINE)), 266, 682))   # every pocket inside filled
LOGO = ("minus", ("grow", SOLID, 2), CROWN)

def twinkle(t0, t1, peak=1.2, spin=90):
    """a sparkle that flares and fades between t0 and t1 - (bone channels, alpha keys); hidden
    either side, and every channel is back at rest once it has faded"""
    tm = t0 + (t1 - t0) * .45
    s = [(0, 1), (t0, .3, "step"), (tm, peak, "out"), (t1, .2, "in"), (t1 + .01, 1, "step")]
    return ({"sx": s, "sy": list(s), "r": [(0, 0), (t0, 0), (t1, spin, "linear"), (t1 + .01, 0, "step")]},
            [(0, 0), (t0, 0, "step"), (t0 + (t1 - t0) * .3, 1), (t1, 0)])


RIM = (490, 880)        # bottom of the hat: it squashes onto this
NECK = (510, 450)       # the crown flexes about a point just under the seam's middle
LOGO_C = (515, 505)

RIG = {
    "id": "L3",
    "parts": [
        {"name": "logo", "mask": LOGO, "pivot": LOGO_C, "parent": "cuff"},
        {"name": "cuff", "mask": CUFF, "pivot": RIM, "exclusive": False},
        {"name": "crown", "mask": CROWN, "pivot": NECK, "parent": "cuff", "exclusive": False},
        {"name": "tw_a", "sprite": "sparkle", "size": 15, "at": (300, 395), "hidden": True, "parent": "logo"},
        {"name": "tw_b", "sprite": "sparkle", "size": 12, "at": (752, 455), "hidden": True, "parent": "logo"},
    ],
    "draw": ["crown", "cuff", "logo", "tw_a", "tw_b"],
    "anims": {
        # a breath and a shimmy: squash on the rim, stretch up, the crown flops after it; then the logo pops
        "idle": {"dur": 2.6, "bones": {
            "cuff": {"sy": [(0, 1), (.24, .955), (.48, 1.03, "out"), (.70, .99), (.92, 1.0)],
                     "sx": [(0, 1), (.24, 1.03), (.48, .98, "out"), (.70, 1.005), (.92, 1.0)]},
            "crown": {"sy": [(0, 1), (.30, .95), (.56, 1.05, "out"), (.80, .985), (1.04, 1.01), (1.26, 1.0)],
                      "r": [(0, 0), (.34, 0), (.58, 1.6), (.84, -1.3), (1.08, .7), (1.32, -.3), (1.56, 0)]},
            "logo": {"sx": [(0, 1), (1.56, 1), (1.74, 1.14, "out"), (1.94, 1.05), (2.08, 1.07), (2.34, 1.0)],
                     "sy": [(0, 1), (1.56, 1), (1.74, 1.14, "out"), (1.94, 1.05), (2.08, 1.07), (2.34, 1.0)],
                     "r": [(0, 0), (1.62, 0), (1.76, -3.0), (1.92, 1.8), (2.06, -.6), (2.2, 0)]},
        }},
        # dropped in: the knit squashes on its rim and springs back, the crown wobbling a beat late
        "land": {"dur": .55, "bones": {
            "cuff": {"sy": [(0, 1), (.08, .89, "in"), (.22, 1.05, "out"), (.36, .985), (.5, 1.0)],
                     "sx": [(0, 1), (.08, 1.07, "in"), (.22, .97, "out"), (.36, 1.01), (.5, 1.0)]},
            "crown": {"sy": [(0, 1), (.12, .91, "in"), (.28, 1.06, "out"), (.42, .98), (.55, 1.0)],
                      "r": [(0, 0), (.14, 1.2), (.30, -1.0), (.44, .35), (.55, 0)]},
            "logo": {"sx": [(0, 1), (.10, 1.0), (.22, 1.06, "out"), (.38, 1.0)],
                     "sy": [(0, 1), (.10, 1.0), (.22, 1.06, "out"), (.38, 1.0)]},
        }},
        "win": {"dur": 1.4, "bones": {
            "cuff": {"sy": [(0, 1), (.14, .91, "in"), (.34, 1.07, "out"), (.54, 1.0), (.62, .92, "in"), (.78, 1.03, "out"), (.96, .99), (1.16, 1.0)],
                     "sx": [(0, 1), (.14, 1.06, "in"), (.34, .96, "out"), (.54, 1.0), (.62, 1.05, "in"), (.78, .98, "out"), (.96, 1.005), (1.16, 1.0)],
                     "y": [(0, 0), (.14, 0), (.36, 5.0, "out"), (.60, 0, "in"), (1.4, 0)]},
            "crown": {"sy": [(0, 1), (.18, .93), (.40, 1.08, "out"), (.66, .93), (.84, 1.04), (1.02, .99), (1.22, 1.0)],
                      "r": [(0, 0), (.20, -1.2), (.44, 1.5), (.68, -1.5), (.90, 1.0), (1.10, -.4), (1.30, 0)]},
            "logo": {"sx": [(0, 1), (.20, 1), (.44, 1.22, "back"), (.92, 1.13), (1.22, 1.0, "inout")],
                     "sy": [(0, 1), (.20, 1), (.44, 1.22, "back"), (.92, 1.13), (1.22, 1.0, "inout")],
                     "r": [(0, 0), (.30, 0), (.48, -3.5), (.70, 3.0), (.92, -1.4), (1.14, 0)]},
            "tw_a": twinkle(.40, .82)[0],
            "tw_b": twinkle(.52, .96, spin=-90)[0],
        }, "alpha": {
            "tw_a": twinkle(.40, .82)[1],
            "tw_b": twinkle(.52, .96, spin=-90)[1],
        }},
    },
}
