"""Cartoon lettering in the symbol icons' style.

  python tools/letter_art/make.py              # BS, ES, BONUS (traced from the shipped art) + the BONUS plate
  python tools/letter_art/make.py xbonus       # XTREME BONUS (the Extreme Bonus intro's title)
  python tools/letter_art/make.py play start   # PLAY (the Bonus panel's) and START (the auto play picker's), white with black ink
  python tools/letter_art/make.py --ship       # copy the BONUS button pair, XTREME BONUS, PLAY and START into frontend/assets
  then: BS/ES -> art/icons-src at 512 px (see README), tools/make_flat_icons.py, tools/icon_rigs/build.py

The traced pieces keep the game's own lettering (same letters, same places, so the symbol rigs'
seams and drip cuts still fit) and repaint it: ink outline, flat paint with a shade and a highlight,
a 3D block, clean round drips, shine, the white sticker edge. build() sets a word in a font instead.

Writes <out>/<NAME>.png (the whole sticker) and <out>/<NAME>_parts/<letter>.png (each letter
with its drips, same canvas) plus <NAME>.json (each letter's box and drip spots, canvas px).
"""
import json, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cartoon as C

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONTS = {"comic": ("C:/Windows/Fonts/comicbd.ttf", False), "segoe": ("C:/Windows/Fonts/seguibl.ttf", False), "arial": ("C:/Windows/Fonts/ariblk.ttf", False), "jraot": (os.path.join(ROOT, "frontend/assets/jraot-hollow.ttf"), True)}

LIME = dict(fill=(.64, .91, .10), shade=(.39, .64, .05), block=(.22, .40, .03), hi=(.86, 1.0, .52))
# the scatters' griddy texture, in source px: coarse and bold enough to survive the board's
# downscale (a symbol is ~150 css px there; a 9 px grid of 1 px lines washed out to nothing)
GRID = dict(cell=13, line=1.6, dark=.5)
PURPLE = dict(fill=(.69, .31, .90), shade=(.47, .17, .68), block=(.28, .07, .43), hi=(.91, .72, 1.0))

PIECES = {
    # name: (text, output size, palette, letter jitter [(dx, dy, angle, scale)...], drips per letter)
    "FS": ("FS", (1024, 772), LIME, [(-14, 6, 4, 1.0), (14, -6, -5, 1.0)],
           [[(.22, .42), (.78, .26)], [(.16, .34), (.84, .22)]]),
    "XFS": ("XFS", (1100, 760), PURPLE, [(-14, 4, 5, 1.0), (2, -6, -4, 1.0), (14, 6, 4, .98)],
            [[(.14, .34), (.86, .40)], [(.22, .38)], [(.18, .26), (.84, .32)]]),
    "BONUS": ("BONUS", (1520, 1012), LIME, [(-20, 10, 5, 1.0), (-10, -6, -3, 1.0), (0, 4, 2, 1.0), (10, -8, -4, 1.0), (20, 6, 4, 1.0)],
              [[(.25, .36)], [(.5, .44)], [(.18, .28), (.84, .4)], [(.3, .3)], [(.2, .38)]]),
}


def build(name, font="comic", out_dir=None, seed=7, fatten=.02):
    text, (OW, OH), pal, jitter, drip_spec = PIECES[name]
    fpath, hollow = FONTS[font]
    rng = np.random.default_rng(seed)
    S = C.SS
    W, H = OW * S, OH * S
    # glyphs sized so the word (with overlaps) fills ~86% of the width and leaves room for drips
    px = int(H * .62)
    gl = [C.glyph(ch, fpath, px, hollow) for ch in text]
    widths = [g.shape[1] for g in gl]
    overlap = .03
    total = sum(widths) * (1 - overlap) + widths[-1] * overlap
    WIDE = 1.0                                     # letters a little wider than the font: chunkier
    k = min(W * .8 / (total * WIDE), H * .5 / max(g.shape[0] for g in gl))
    gl = [np.asarray(Image.fromarray(g.astype(np.uint8) * 255).resize((max(1, int(g.shape[1] * k * WIDE)), max(1, int(g.shape[0] * k))), Image.LANCZOS)) > 127 for g in gl]
    widths = [g.shape[1] for g in gl]
    total = sum(widths) * (1 - overlap) + widths[-1] * overlap
    x = (W - total) / 2
    top = H * .1
    letters, meta = [], []
    for i, (g, (dx, dy, ang, sc)) in enumerate(zip(gl, jitter)):
        cx = x + g.shape[1] / 2 + dx * S
        cy = top + g.shape[0] / 2 + dy * S
        m = C.place((H, W), g, cx, cy, ang, sc)
        # round the outer corners off (an open pass only: a close would fill the S's openings)
        if fatten:                                    # bubble-fat strokes, the icons' chunky look
            m = C.dil(m, g.shape[0] * fatten)
        m = C.cv2.morphologyEx(m.astype(np.uint8), C.cv2.MORPH_OPEN, C.disc(g.shape[0] * .035)).astype(bool)
        ys, xs = np.nonzero(m)
        x0, x1 = xs.min(), xs.max()
        dxs = [x0 + (x1 - x0) * f for f, _ in drip_spec[i]]
        dls = [L * (ys.max() - ys.min()) for _, L in drip_spec[i]]
        dr, spots = C.add_drips(m, dxs, dls, g.shape[0] * .15, rng)
        letters.append({"body": m, "drips": dr})
        meta.append({"char": text[i], "box": [int(x0 / S), int(ys.min() / S), int(x1 / S), int(ys.max() / S)],
                     "drips": [[round(a / S, 1), round(b / S, 1), round(c / S, 1)] for a, b, c in spots]})
        x += g.shape[1] * (1 - overlap)
    P = dict(pal, ink=H * .019, sticker=H * .010, depth=H * .022, shade_w=H * .034, hi_w=H * .014, hi_inset=H * .014,
             gloss_period=H * .05, light=255)
    full, layers = C.render(letters, P, (OW, OH))
    # trim to the piece (plus a small margin), the parts on the same box
    ys, xs = np.nonzero(full[..., 3] > 0)
    m = int(OH * .02)
    box = (max(0, xs.min() - m), max(0, ys.min() - m), min(OW, xs.max() + m + 1), min(OH, ys.max() + m + 1))
    full = full[box[1]:box[3], box[0]:box[2]]
    layers = [l[box[1]:box[3], box[0]:box[2]] for l in layers]
    for mt in meta:
        b = mt["box"]; mt["box"] = [b[0] - box[0], b[1] - box[1], b[2] - box[0], b[3] - box[1]]
        mt["drips"] = [[a - box[0], b2 - box[1], c - box[1]] for a, b2, c in mt["drips"]]
    OW, OH = full.shape[1], full.shape[0]
    out_dir = out_dir or os.path.join(ROOT, "art", "letters")
    os.makedirs(os.path.join(out_dir, name + "_parts"), exist_ok=True)
    Image.fromarray(full, "RGBA").save(os.path.join(out_dir, name + ".png"))
    for i, lay in enumerate(layers):
        Image.fromarray(lay, "RGBA").save(os.path.join(out_dir, name + "_parts", f"{i}_{text[i]}.png"))
    with open(os.path.join(out_dir, name + ".json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"size": [int(OW), int(OH)], "letters": meta}, fh, indent=1, default=float)
    return os.path.join(out_dir, name + ".png")


def plate(src=os.path.join(ROOT, "art/ui-src/bonus_btn_bg.png"), out_dir=None, out_scale=1.25):
    """The purple spray plate behind BONUS, repainted: its own silhouette (from the old art's
    alpha, smoothed), flat purple with a shade band and a highlight, a black ink line, the cyan
    second outline the old plate had, and the white sticker edge."""
    S = C.SS
    im = Image.open(src).convert("RGBA")
    OW, OH = im.size
    a = np.asarray(im.resize((OW * S, OH * S), Image.LANCZOS))[..., 3] > 128
    a = C.keep_big(a, (OW * S * .2) ** 2) if hasattr(C, "keep_big") else a
    sil = C.cv2.GaussianBlur(a.astype(np.float32), (0, 0), OH * S * .02) > .5
    H = OH * S
    ink, cyan, stick = H * .024, H * .03, H * .012
    body = C.ero(sil, ink + cyan + stick)                       # the old silhouette included its rims
    body = C.cv2.morphologyEx(body.astype(np.uint8), C.cv2.MORPH_OPEN, C.disc(H * .04)).astype(bool)
    rgba = np.zeros((H, OW * S, 4), np.float32)
    def put(m, col):
        rgba[m] = list(col) + [1.0]
    line = C.dil(body, ink)
    cy = C.dil(line, cyan)
    put(C.dil(cy, stick), (1, 1, 1))
    put(cy, (.19, .84, .94))
    put(line, (0, 0, 0))
    put(body, (.67, .17, .82))
    put(C.shade_band(body, 0, -H * .07), (.45, .08, .58))
    put(C.shade_band(C.ero(body, H * .03), 0, H * .03), (.84, .45, .95))
    # a few cartoon paint specks on the plate
    rng = np.random.default_rng(3)
    ys, xs = np.nonzero(C.ero(body, H * .1))
    for _ in range(14):
        i = rng.integers(len(xs)); r = H * rng.uniform(.008, .02)
        d = Image.new("L", (OW * S, H), 0); C.ImageDraw.Draw(d).ellipse([xs[i] - r, ys[i] - r, xs[i] + r, ys[i] + r], fill=255)
        put(np.asarray(d) > 127, (.52, .1, .66))
    x = (rgba * 255).clip(0, 255).astype(np.uint8)
    out = Image.fromarray(x, "RGBA").resize((round(OW * out_scale), round(OH * out_scale)), Image.LANCZOS)
    out_dir = out_dir or os.path.join(ROOT, "art", "letters")
    os.makedirs(out_dir, exist_ok=True)
    out.save(os.path.join(out_dir, "BONUS_plate.png"))
    return os.path.join(out_dir, "BONUS_plate.png")


# ---------------------------------------------------------------- traced from the shipped art
# The lettering is the game's own (the same letters in the same places, so the symbol rigs'
# seams and drip cuts still land on them); only the painting changes. Drips: (x, bottom y) in
# source px, chosen from the original's drips (fewer, cleaner).
TRACED = {
    "BS": dict(src="art/ui-src/BS_orig.png", t=13, pal=LIME, out=2, grow=1.0, smooth=3.0, crack=2.5, grid=True,
               drips=[(75, 340), (93, 368), (137, 305), (151, 352), (205, 258), (265, 330), (282, 362),
                      (390, 335), (401, 378), (440, 322), (466, 362)]),
    "ES": dict(src="art/ui-src/ES_orig.png", t=11, pal=PURPLE, out=2, grow=1.0, smooth=2.5, crack=2.5,
               # XFS, not XXFS (owner, 2026-10-24): everything left of the seam between the two X's
               # goes, and what is left is centred on a canvas XFS_W source px wide
               cut_left=[(168, 0), (168, 56), (163, 62), (160, 67), (157, 71), (155, 77), (155, 95), (158, 140), (160, 166),
                         (162, 176), (163, 182), (166, 186), (168, 190), (171, 194), (174, 198), (176, 202), (175, 210), (176, 216), (177, 302)],
               width=420, grid=True,
               drips=[(48, 258), (75, 290), (145, 276), (186, 263), (238, 268), (256, 258), (330, 262),
                      (346, 252), (410, 266), (425, 290), (442, 284)]),
    "BONUS": dict(src="art/ui-src/bonus_btn_text.png", t=8, pal=LIME, out=1.5, grow=6.0, smooth=7.0, crack=10.0,
                  drips=[(95, 455), (130, 495), (280, 440), (355, 360), (445, 405), (525, 352), (580, 438),
                         (660, 468), (710, 432)]),
}


def letters_with_drips(face, drips_src, k, SH, rng):
    """The faces split into letters, each drip (x, bottom y in source px) hung from the letter
    right above it."""
    import trace as T
    letters = [{"body": m, "drips": np.zeros_like(m)} for m in T.letters(face, (12 * k) ** 2)]
    for x, yb in drips_src:
        X = x * k
        col = int(round(X))
        best = None
        for L in letters:
            ys = np.nonzero(L["body"][:, max(0, col - 2):col + 3].any(1))[0]
            if len(ys) and (best is None or ys.max() > best[1]):
                best = (L, ys.max())
        if best is None:
            continue
        L, ybot = best
        dr, _ = C.add_drips(L["body"], [X], [yb * k - ybot], 9.5 * k * (SH / 386) ** .3, rng)
        L["drips"] |= dr
    return letters


def paint(pal, hh):
    """The paint geometry for a piece hh working px tall (ink, block, shade, highlights scale with it)."""
    return dict(pal, ink=hh * .017, sticker=hh * .009, depth=hh * .02, shade_w=hh * .03, hi_w=hh * .012,
                hi_inset=hh * .012, gloss_period=hh * .05, light=255)


def traced(name, out_dir=None, seed=11):
    import trace as T
    cfg = TRACED[name]
    src = os.path.join(ROOT, cfg["src"])
    S = C.SS
    k = cfg["out"] * S                              # working px per source px
    face, _, (SW, SH) = T.trace(src, k, cfg["t"], crack_src=cfg["crack"], grow_src=cfg["grow"], smooth_src=cfg["smooth"])
    drips_src = list(cfg["drips"])
    shift = 0.0
    if cfg.get("cut_left"):
        import cv2
        poly = np.array([(0, 0)] + [(x * k, y * k) for x, y in cfg["cut_left"]] + [(0, face.shape[0])], np.int32)
        kill = np.zeros(face.shape, np.uint8); cv2.fillPoly(kill, [poly], 1)
        face = face & ~kill.astype(bool)
        # the rest, centred on the new width
        xs = np.nonzero(face.any(0))[0]
        W2 = int(round(cfg["width"] * k))
        shift = (W2 - (xs.max() - xs.min() + 1)) / 2 - xs.min()
        M = np.float32([[1, 0, shift], [0, 1, 0]])
        face = cv2.warpAffine(face.astype(np.uint8), M, (W2, face.shape[0]), flags=cv2.INTER_NEAREST).astype(bool)
        seam_x = lambda y: np.interp(y, [p[1] for p in cfg["cut_left"]], [p[0] for p in cfg["cut_left"]])
        drips_src = [(x + shift / k, y) for x, y in drips_src if x > seam_x(y) + 4]
        SW = cfg["width"]
        print(f"{name}: cut at the seam, shifted {shift / k:+.1f} source px, canvas {SW}x{SH}")
    H, W = face.shape
    letters = letters_with_drips(face, drips_src, k, SH, np.random.default_rng(seed))
    P = paint(cfg["pal"], SH * k)
    if cfg.get("grid"):   # the griddy texture (cartoon.render), GRID in source px
        P["grid"] = dict(spacing=max(6, int(round(GRID["cell"] * k))), width=max(1, int(round(GRID["line"] * k))), dark=GRID["dark"],
                         inset=hh * .012, dots=True)
    OW, OH = round(SW * cfg["out"]), round(SH * cfg["out"])
    full, layers = C.render(letters, P, (OW, OH))
    out_dir = out_dir or os.path.join(ROOT, "art", "letters")
    os.makedirs(out_dir, exist_ok=True)
    Image.fromarray(full, "RGBA").save(os.path.join(out_dir, name + "_traced.png"))
    return os.path.join(out_dir, name + "_traced.png")


# ---------------------------------------------------------------- XTREME BONUS
# The Extreme Bonus intro's title (owner, 2026-10-24: "Xtreme Bonus in the same font as the bonus
# font, in purple"). BONUS is the logo's own lettering, traced exactly as traced("BONUS") does;
# the art has no X, T, R, E or M, so XTREME is set in BROMO - the bundled face closest to that
# lettering (chunky, upright, the same B O N U S shapes) - each letter knocked a little off its
# line the way the hand-drawn BONUS letters sit, softened and fattened to the traced letters'
# weight, and tucked behind BONUS's top. Everything is painted with the same ink, block, shine
# and drips, at the same scale, in the scatter purple.
BROMO = os.path.join(ROOT, "frontend/assets/bromo.otf")
XB = dict(top=150,          # source px added above BONUS for the XTREME line
          cap=124,          # XTREME's letter height, source px (BONUS's are ~270)
          sink=8,           # how far XTREME's bottom tucks behind BONUS's top, source px
          overlap=-.06, grow=0.0, smooth=3.0,   # a little air between the letters; BROMO is already the weight
          jitter=[(-4, 6, 6), (-2, -4, -3), (0, 4, 4), (1, -6, -4), (2, 3, 3), (4, -4, -5)],   # (dx, dy src px, degrees)
          drips=[(.18, 52), (.86, 40)])   # on the end letters only, (x across the letter, length src px)


def xtreme_bonus(out_dir=None, seed=11):
    import trace as T
    cfg = TRACED["BONUS"]
    k = cfg["out"] * C.SS
    face, _, (SW, SH) = T.trace(os.path.join(ROOT, cfg["src"]), k, cfg["t"], crack_src=cfg["crack"], grow_src=cfg["grow"], smooth_src=cfg["smooth"])
    top = XB["top"]
    face = np.pad(face, ((int(round(top * k)), 0), (0, 0)))
    H, W = face.shape
    rng = np.random.default_rng(seed)
    bonus = letters_with_drips(face, [(x, y + top) for x, y in cfg["drips"]], k, SH, rng)
    ys, xs = np.nonzero(face)
    cx_all, top_b = (xs.min() + xs.max()) / 2, ys.min()
    cap = XB["cap"] * k
    gl = []
    for ch in "XTREME":
        g = C.glyph(ch, BROMO, int(cap * 1.5))
        g = np.asarray(Image.fromarray(g.astype(np.uint8) * 255).resize((max(1, round(g.shape[1] * cap / g.shape[0])), round(cap)), Image.LANCZOS)) > 127
        gl.append(g)
    widths = [g.shape[1] for g in gl]
    total = sum(widths) - XB["overlap"] * sum(widths[:-1])
    x = cx_all - total / 2
    cy = top_b + XB["sink"] * k - cap / 2
    xtreme = []
    for g, (dx, dy, ang) in zip(gl, XB["jitter"]):
        m = C.place((H, W), g, x + g.shape[1] / 2 + dx * k, cy + dy * k, ang)
        m = C.rounded(C.dil(m, XB["grow"] * k) if XB["grow"] else m, XB["smooth"] * k)
        xtreme.append({"body": m, "drips": np.zeros_like(m)})
        x += g.shape[1] * (1 - XB["overlap"])
    for L, (fx, length) in zip([xtreme[0], xtreme[-1]], XB["drips"]):
        bx = np.nonzero(L["body"].any(0))[0]
        X = bx.min() + (bx.max() - bx.min()) * fx
        dr, _ = C.add_drips(L["body"], [X], [length * k], 9.5 * k * (SH / 386) ** .3 * .8, rng)
        L["drips"] |= dr
    # XTREME first, so BONUS (and its ink) paints over the tucked-in bottom
    full, _ = C.render(xtreme + bonus, paint(PURPLE, SH * k), (round(SW * cfg["out"]), round((SH + top) * cfg["out"])))
    im = Image.fromarray(full, "RGBA")
    im = im.crop(im.getbbox())
    out_dir = out_dir or os.path.join(ROOT, "art", "letters")
    os.makedirs(out_dir, exist_ok=True)
    im.save(os.path.join(out_dir, "XTREME_BONUS.png"))
    return os.path.join(out_dir, "XTREME_BONUS.png")


# ---------------------------------------------------------------- PLAY / START
# The lettered buttons (owner, 2026-10-25): the Bonus panel's Play stood out on its yellow plate and
# should be "a white fill with a black outline" in "the same font as the Bonus symbol"; the auto play
# picker's Start follows it. Set as XTREME is: BROMO letters at BONUS's letter height, painted with
# BONUS's ink, block, shine and drips - in white, with no white sticker edge, so the outermost line
# is the black ink. Then ("more rounded and bumpy", "the portions for the letters are uneven",
# "make the Y fit better", "the spacing is uneven"): every letter is swollen, rounded and lumped
# like a bubble letter; set to its own width with every stroke at one weight (BROMO's P and S are
# narrow beside a wide A, and its strokes run 58-74 px at a 300 px cap); its Y is drawn (BROMO's is
# a slanted lowercase-style y whose V swelled shut); and the letters are spaced optically.
# a near-white fill, so the white highlight band and the gloss read on it the way BONUS's do on lime
WHITE = dict(fill=(.93, .93, .96), shade=(.74, .75, .80), block=(.45, .45, .50), hi=(1.0, 1.0, 1.0))
LT = dict(cap=270,           # letter height, BONUS source px (BONUS's are ~270)
          out=.6,            # output px per BONUS source px: ~160 px letters, sharp at 2x in the buttons
          stroke=.235,       # x cap: every stroke's weight before the swelling
          grow=9.0,          # src px: swollen past BROMO's weight toward the traced BONUS letters' fat strokes
          bubble=.045,       # x cap: every corner and stroke end rounded off, bubble-letter soft
          bumps=[(.30, .045), (.11, .020)],   # (spacing, amplitude) x cap: big lumps, small bumps on them
          ink=1.5, drip_w=1.25,  # x BONUS's ink and drip width: a white letter needs the heavier line to hold on the grey
          # optical spacing, in widths of the black outline (each letter's line is drawn outside its
          # body, so two bodies 2 widths apart have outlines just touching): the gap to the letter
          # before, row by row, counted no deeper than `depth` (an open side - L's empty top - is not a
          # hole to fill), averages `air`; the bodies never come closer than `touch`, where the two
          # outlines run together as one line. `air` is the loosest pair's gap at `touch` (make.py
          # prints them: PLAY 4.1 4.3 3.2, START 4.0 3.4 3.9 4.5), so every pair opens up to the same
          # gap rather than each stopping where its nearest points meet
          depth=6.0, air=4.5, touch=1.0)
WORDS = {
    # aspect: each letter's width / height. notches: open shapes the swelling would fill, cut back at
    # their drawn size like the counters - rows (from, to) x the letter's height where its hull, less
    # the letter, stays open. jitter: (dy src px, degrees) per letter, hand-placed, not tipsy.
    # drips: (letter, x across it, length src px). ship: the file the game loads.
    "PLAY": dict(aspect={"P": .66, "L": .58, "A": .78, "Y": .74}, notches={"A": (.64, 1.0), "Y": (0.0, .56)},
                 jitter=[(2, 2.5), (-2, -2), (2, 1.5), (-2, -2.5)],
                 drips=[(0, .26, 72), (0, .76, 34), (1, .22, 118), (1, .80, 46), (2, .17, 56), (2, .85, 98), (3, .50, 86)],
                 ship="bonus_play_text.webp"),
    "START": dict(aspect={"S": .60, "T": .66, "A": .78, "R": .66}, notches={"A": (.64, 1.0)},
                  jitter=[(2, 2.5), (-2, -2), (2, 1.5), (-2, -2), (2, 2)],
                  drips=[(0, .30, 64), (1, .50, 104), (2, .17, 52), (2, .85, 90), (3, .22, 70), (4, .50, 96)],
                  ship="auto_start_text.webp"),
}


def stroke_of(m):
    """A mask's typical stroke width: twice the median depth along its ridge."""
    d = C.cv2.distanceTransform(m.astype(np.uint8), C.cv2.DIST_L2, 5)
    ridge = (d >= C.cv2.dilate(d, np.ones((3, 3), np.uint8)) - 1e-3) & (d > 2)
    return 2 * float(np.median(d[ridge]))


def y_glyph(cap, aspect, stroke, join=.52):
    """A Y as three round-ended strokes: arms from the top corners meeting a little above the
    middle, a straight stem from there down."""
    from PIL import ImageDraw
    w, h, r = int(round(cap * aspect)), int(round(cap)), stroke / 2
    im = Image.new("L", (w, h), 0); d = ImageDraw.Draw(im)
    jx, jy = w / 2, h * join
    for (x0, y0), (x1, y1) in (((r, r), (jx, jy)), ((w - r, r), (jx, jy)), ((jx, jy), (jx, h - r))):
        d.line([(x0, y0), (x1, y1)], fill=255, width=int(round(stroke)))
        for x, y in ((x0, y0), (x1, y1)):
            d.ellipse([x - r, y - r, x + r, y + r], fill=255)
    return np.asarray(im) > 127


def letter_glyph(ch, cap, spec):
    """One letter at the cap height, its own width (the word's aspect) and the one stroke weight."""
    want = LT["stroke"] * cap
    if ch == "Y":
        return y_glyph(cap, spec["aspect"][ch], want)
    g = C.glyph(ch, BROMO, int(cap * 1.5))
    size = (max(1, round(cap * spec["aspect"][ch])), round(cap))
    g = np.asarray(Image.fromarray(g.astype(np.uint8) * 255).resize(size, Image.LANCZOS)) > 127
    d = (want - stroke_of(g)) / 2                      # thicken or thin every stroke to the one weight
    g = np.pad(g, int(abs(d)) + 2)
    g = C.dil(g, d) if d > 0 else C.ero(g, -d)
    ys, xs = np.nonzero(g)
    g = g[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return np.asarray(Image.fromarray(g.astype(np.uint8) * 255).resize(size, Image.LANCZOS)) > 127


def space(letters, ink, W):
    """Optical spacing: each letter slides left until the gap to the letters before it, measured
    row by row and counted no deeper than LT depth, averages LT air - or until the bodies come
    within LT touch, whichever comes first (all in outline widths, `ink` px). Spacing by nearest
    points alone pressed P and L together and left a hole above L's foot beside the A."""
    depth, air, touch = (LT[n] * ink for n in ("depth", "air", "touch"))
    cols = np.arange(W)
    so_far = letters[0]["body"].copy()
    report = []
    for L in letters[1:]:
        right = np.where(so_far, cols, -1).max(1)
        left = np.where(L["body"], cols, W).min(1)
        both = (right >= 0) & (left < W)
        g = np.where(both, left - right, np.inf)[(right >= 0) | (left < W)].astype(float)
        mean_gap = lambda s: float(np.minimum(g - s, depth).mean())
        lo, hi = 0.0, float(g[np.isfinite(g)].min() - touch)
        at_touch = mean_gap(hi)
        if at_touch < air:
            for _ in range(40):                       # mean_gap falls as the letter slides in
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if mean_gap(mid) > air else (lo, mid)
        L["body"] = C.shift(L["body"], -int(round(hi)), 0)
        so_far |= L["body"]
        report.append(f"{at_touch / ink:.1f}{'' if at_touch < air else '*'}")
    return report   # each pair's mean gap (outline widths) with the bodies at `touch`; * = stopped there


def lettered(word, out_dir=None, seed=11):
    spec = WORDS[word]
    S = C.SS
    k = LT["out"] * S                               # working px per BONUS source px
    SH = Image.open(os.path.join(ROOT, TRACED["BONUS"]["src"])).size[1]
    cap = LT["cap"] * k
    gl = [letter_glyph(ch, cap, spec) for ch in word]
    pad = cap * .35
    W, H = int(sum(g.shape[1] for g in gl) + pad * (len(gl) + 1)), int(cap * 1.95)
    W, H = W - W % S, H - H % S
    rng = np.random.default_rng(seed)
    x, cy = pad, pad * .6 + cap / 2
    letters = []
    for ch, g, (dy, ang) in zip(word, gl, spec["jitter"]):
        at = (x + g.shape[1] / 2, cy + dy * k, ang)
        m = C.place((H, W), g, *at)
        open_ = C.fill_enclosed(g) & ~g                 # the counters: P's bowl, A's eye
        if ch in spec["notches"]:
            hull = np.zeros(g.shape, np.uint8)
            C.cv2.fillConvexPoly(hull, C.cv2.convexHull(np.argwhere(g)[:, ::-1].astype(np.int32)), 1)
            r0, r1 = (int(f * g.shape[0]) for f in spec["notches"][ch])
            rows = np.zeros(g.shape, bool); rows[r0:r1] = True
            open_ |= hull.astype(bool) & ~g & rows
        holes = C.place((H, W), open_, *at)
        m = C.bubble(C.dil(m, LT["grow"] * k), LT["bubble"] * cap)
        m = C.bubble(C.bumpy(m, [(s * cap, a * cap) for s, a in LT["bumps"]], rng), cap * .008)   # the bumps' own edges eased a hair
        # the swelling fills the counters in from inside: they are cut back at the font's own size,
        # rounded, so the strokes swell outward only and the letters stay readable
        m &= ~C.bubble(C.dil(holes, cap * .012), cap * .02)
        letters.append({"body": m, "drips": np.zeros((H, W), bool)})
        x += g.shape[1] + pad                       # set wide apart, then drawn together by space()
    P = paint(WHITE, SH * k)
    P.update(ink=P["ink"] * LT["ink"], sticker=0)
    print(word, "pairs' mean gap at touch:", " ".join(space(letters, P["ink"], W)))
    for i, fx, length in spec["drips"]:
        L = letters[i]
        bx = np.nonzero(L["body"].any(0))[0]
        dr, _ = C.add_drips(L["body"], [bx.min() + (bx.max() - bx.min()) * fx], [length * k], 9.5 * k * (SH / 386) ** .3 * LT["drip_w"], rng)
        L["drips"] |= dr
    full, _ = C.render(letters, P, (W // S, H // S))
    im = Image.fromarray(full, "RGBA")
    im = im.crop(im.getbbox())
    out_dir = out_dir or os.path.join(ROOT, "art", "letters")
    os.makedirs(out_dir, exist_ok=True)
    im.save(os.path.join(out_dir, word + ".png"))
    return os.path.join(out_dir, word + ".png")


if __name__ == "__main__":
    args = sys.argv[1:]
    font = "comic"
    out = None
    if "--font" in args:
        i = args.index("--font"); font = args[i + 1]; del args[i:i + 2]
    if "--out" in args:
        i = args.index("--out"); out = args[i + 1]; del args[i:i + 2]
    if "--ship" in args:      # the BONUS button pair straight into the game
        args.remove("--ship")
        Image.open(os.path.join(ROOT, "art/letters/BONUS_traced.png")).save(os.path.join(ROOT, "frontend/assets/bonus_btn_text.webp"), "WEBP", quality=92, alpha_quality=100, method=6)
        Image.open(os.path.join(ROOT, "art/letters/BONUS_plate.png")).save(os.path.join(ROOT, "frontend/assets/bonus_btn_bg.webp"), "WEBP", quality=92, alpha_quality=100, method=6)
        xb = os.path.join(ROOT, "art/letters/XTREME_BONUS.png")
        if os.path.exists(xb):
            Image.open(xb).save(os.path.join(ROOT, "frontend/assets/xbonus_text.webp"), "WEBP", quality=92, alpha_quality=100, method=6)
        for word, spec in WORDS.items():
            src = os.path.join(ROOT, f"art/letters/{word}.png")
            if os.path.exists(src):
                Image.open(src).save(os.path.join(ROOT, "frontend/assets", spec["ship"]), "WEBP", quality=92, alpha_quality=100, method=6)
        print("shipped bonus_btn_text.webp + bonus_btn_bg.webp + xbonus_text.webp + " + " + ".join(s["ship"] for s in WORDS.values()))
        if not args: sys.exit(0)
    for n in (args or list(TRACED) + ["plate"]):
        if n == "plate": print(plate(out_dir=out))
        elif n == "xbonus": print(xtreme_bonus(out))
        elif n.upper() in WORDS: print(lettered(n.upper(), out))
        elif n.endswith("_traced") or n in TRACED: print(traced(n.replace("_traced", ""), out))
        else: print(build(n, font, out))
