# Lays the separately generated letters (gen.py -> r1/) out as one word for the loading ident: each
# letter trimmed and scaled to one cap height (measured on its body, not its drips), the i shorter,
# set on a common baseline with a slight bob and tight, overlapping spacing, the swoosh under them
# and the brushed TM by the Z's arrow; the seal from the old wordmark (intro_letters/seal) after it.
# Writes the pieces to frontend/assets/intro_letters/ (<piece>.webp, pieces.json, glow.webp) and an
# assembled preview here.
#   python build.py [round]
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT = os.path.join(ROOT, 'frontend', 'assets', 'intro_letters')
RND = sys.argv[1] if len(sys.argv) > 1 else 'r1'
W, H = 2736, 1160
CAP = 470                 # cap height (letter bodies), px on the canvas
BASE = 780
GBLUR, GPAD = 26, 110   # the glow's blur, and its padding (> 3x the blur's reach... 4x)                # the baseline
# per letter: height factor, kerning before it (fraction of CAP, negative overlaps), baseline bob (px)
SPEC = {'S': (1.08, 0, 30), 'M': (1.0, -.10, -6), 'U': (.92, -.08, 6), 'K': (1.04, -.07, -10),
        'i': (.74, -.10, 4), 'E': (.98, -.06, -4), 'Z': (1.12, -.08, 14)}


def trim(im):
    return im.crop(im.getchannel('A').point(lambda v: 255 if v > 10 else 0).getbbox())


def body_rows(im):
    """top and bottom of the letter's body: rows with a real share of ink (drips are thin)"""
    a = np.asarray(im.getchannel('A')) > 60
    cnt = a.sum(1); thr = max(3, cnt.max() * .12)
    rows = np.nonzero(cnt >= thr)[0]
    return rows.min(), rows.max()


def main():
    os.makedirs(OUT, exist_ok=True)
    canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    meta = {}
    placed = []
    x = 0
    for k, (hk, kern, bob) in SPEC.items():
        im = trim(Image.open(os.path.join(HERE, RND, f'{k}.png')).convert('RGBA'))
        t, b = body_rows(im)
        s = CAP * hk / (b - t + 1)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        bb = round(b * s)                                   # the body's bottom inside the scaled letter
        x += kern * CAP
        placed.append((k, im, x, BASE + bob - bb))
        x += im.width
    word_w = x + CAP * .32   # (room for the TM after the Z)
    x0 = (W - word_w) / 2 - placed[0][2]
    for k, im, px, py in placed:
        X, Y = round(x0 + px), round(py)
        canvas.alpha_composite(im, (X, Y))
        meta[k] = [X, Y, im.width, im.height]
    # the swoosh: under the word from the M to past the Z, rising a touch to the right
    sw = trim(Image.open(os.path.join(HERE, RND, 'swoosh.png')).convert('RGBA'))
    sx0 = meta['M'][0] + 40; sx1 = meta['Z'][0] + meta['Z'][2] + 30
    s = (sx1 - sx0) / sw.width
    sw = sw.resize((round(sw.width * s), round(sw.height * s)), Image.LANCZOS).rotate(2, resample=Image.BICUBIC, expand=True)
    SX, SY = sx0, BASE + 105 - sw.height // 2
    canvas.alpha_composite(sw, (SX, SY)); meta['swash'] = [SX, SY, sw.width, sw.height]
    # the TM by the Z's arrowhead
    tm = trim(Image.open(os.path.join(HERE, RND, 'tm.png')).convert('RGBA'))
    s = CAP * .2 / tm.height
    tm = tm.resize((round(tm.width * s), round(tm.height * s)), Image.LANCZOS)
    zx, zy, zw, zh = meta['Z']
    TX, TY = zx + zw + 18, zy + 10
    canvas.alpha_composite(tm, (TX, TY)); meta['tm'] = [TX, TY, tm.width, tm.height]
    # the seal from the old wordmark, under the Z's end
    seal = Image.open(os.path.join(OUT, 'seal.webp')).convert('RGBA') if os.path.exists(os.path.join(OUT, 'seal.webp')) else None
    if seal is not None:
        SX2, SY2 = zx + zw - seal.width + 60, BASE + 170
        canvas.alpha_composite(seal, (SX2, SY2)); meta['seal'] = [SX2, SY2, seal.width, seal.height]
    # every piece out on its own, and the glow (the whole word blurred, white)
    for k, im, px, py in placed:
        im.save(os.path.join(OUT, f'{k}.webp'), 'WEBP', quality=92, method=6)
    sw.save(os.path.join(OUT, 'swash.webp'), 'WEBP', quality=92, method=6)
    tm.save(os.path.join(OUT, 'tm.webp'), 'WEBP', quality=92, method=6)
    # the glow that comes up once the word is in: built from these pieces (the whole word blurred, white)
    # (on a canvas padded by GPAD all round - well over 3x the blur - so it fades out to nothing
    # before any edge: the word reaches the wordmark's own edges; the page sets it GPAD out, pieces.json)
    big = Image.new('L', (W + 2 * GPAD, H + 2 * GPAD), 0); big.paste(canvas.getchannel('A'), (GPAD, GPAD))
    glow = Image.new('RGBA', big.size, (255, 255, 255, 0))
    glow.putalpha(big.filter(ImageFilter.GaussianBlur(GBLUR)).point(lambda v: min(255, int(v * 1.3))))
    glow.save(os.path.join(OUT, 'glow.webp'), 'WEBP', quality=85, method=6)
    meta['glow'] = [-GPAD, -GPAD, W + 2 * GPAD, H + 2 * GPAD]
    json.dump(dict(size=[W, H], pieces=meta), open(os.path.join(OUT, 'pieces.json'), 'w'), indent=1)
    prev = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    g2 = glow.crop((GPAD, GPAD, GPAD + W, GPAD + H)); g2.putalpha(g2.getchannel('A').point(lambda v: int(v * .55))); prev.alpha_composite(g2)
    prev.alpha_composite(canvas)
    prev.convert('RGB').resize((W // 2, H // 2), Image.LANCZOS).save(os.path.join(HERE, 'preview_word.png'))
    print(json.dumps(meta))


main()
