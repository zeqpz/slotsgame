# The game title, v2 (owner, 2026-11-08: the generated stacked logo read as generic AI). Built from
# our own art instead: his real SMUKIEZ wall tag (frontend/assets/wall_tag.webp) as the hero word,
# untouched, and "& SKELLY" as a contrasting piece designed here in code, with nothing generated:
#   a - a slap-tag sticker: a bone-white sticker slapped across the tag's foot at an angle, "& skelly"
#       in black marker (the game's aaaiight-fat face), the skeleton's head (his Blender render)
#       peeking over its edge
#   b - bone letters: SKELLY built stroke by stroke from cartoon bones (vector: capsules with knuckled
#       ends), bone-white in a black ink line, a lime "&" sticker-dot before it
#   c - a stencil on tape: a strip of masking tape across the foot, "& SKELLY" sprayed through a
#       stencil (bridged Impact capitals) in black with its overspray
#   python build.py [a b c]  -> v2/preview_<v>.png (on the wall) + v2/title_<v>.png (transparent)
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
A = os.path.join(ROOT, 'frontend', 'assets')
FONT_MARKER = os.path.join(A, 'aaaiight-fat.ttf')
FONT_BLOCK = r'C:\Windows\Fonts\impact.ttf'
SKULL = os.path.join(ROOT, 'art', 'blender', 'chars', 'skull', 'renders', 'idle', '0001.png')
BONE, INK, LIME, VIOLET = (241, 234, 216), (12, 10, 14), (184, 242, 58), (110, 36, 180)
W, H = 3500, 2350
rng = np.random.default_rng(7)


def trim(im):
    return im.crop(im.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox())


def tag_layer():
    tag = trim(Image.open(os.path.join(A, 'wall_tag.webp')).convert('RGBA'))
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    layer.alpha_composite(tag, ((W - tag.width) // 2, 30))
    return layer, ((W - tag.width) // 2, 30, tag.width, tag.height)


def outline(alpha, px):
    """alpha grown by px (a round brush): the ink line behind a shape"""
    return alpha.filter(ImageFilter.MaxFilter(px * 2 + 1)) if px < 12 else \
        alpha.filter(ImageFilter.GaussianBlur(px * .55)).point(lambda v: 255 if v > 22 else 0)


def solid(alpha, rgb):
    out = Image.new('RGBA', alpha.size, rgb + (0,)); out.putalpha(alpha); return out


def grain(size, amt):
    n = (rng.random((size[1], size[0])) * 2 - 1) * amt
    return Image.fromarray(np.clip(128 + n, 0, 255).astype(np.uint8), 'L')


def shade(rgba, amt=22):
    """paper / paint grain over a flat fill (kept to its alpha)"""
    a = rgba.getchannel('A')
    g = grain(rgba.size, amt).filter(ImageFilter.GaussianBlur(.7))
    rgb = np.asarray(rgba.convert('RGB')).astype(np.int16) + (np.asarray(g).astype(np.int16) - 128)[..., None]
    out = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), 'RGB').convert('RGBA'); out.putalpha(a)
    return out


def drop_shadow(alpha, dx, dy, blur, rgb=(0, 0, 0), k=.55):
    sh = Image.new('L', alpha.size, 0); sh.paste(alpha, (dx, dy))
    return solid(sh.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * k)), rgb)


def skull_head(height):
    im = trim(Image.open(SKULL).convert('RGBA'))
    head = im.crop((0, 0, im.width, int(im.height * .40)))   # the beanie and the skull, down to the jaw
    head = trim(head)
    k = height / head.height
    return head.resize((round(head.width * k), round(head.height * k)), Image.LANCZOS)


# ---------------------------------------------------------------- a: slap-tag sticker
def variant_a():
    layer, (tx, ty, tw, th) = tag_layer()
    sw, sh_ = 1720, 540
    st = Image.new('L', (sw + 200, sh_ + 200), 0)
    ImageDraw.Draw(st).rounded_rectangle((100, 100, 100 + sw, 100 + sh_), radius=70, fill=255)
    # a peeled corner: cut the top-right corner off on a diagonal
    ImageDraw.Draw(st).polygon([(100 + sw - 150, 100), (100 + sw + 10, 100), (100 + sw + 10, 100 + 150)], fill=0)
    face = shade(solid(st, BONE), 14)
    # the marker lettering
    txt = Image.new('L', st.size, 0)
    f = ImageFont.truetype(FONT_MARKER, 400)
    d = ImageDraw.Draw(txt)
    l, t, r, b = d.textbbox((0, 0), '& skelly', font=f)
    k = min((sw - 170) / (r - l), (sh_ - 120) / (b - t))
    f = ImageFont.truetype(FONT_MARKER, int(400 * k)); l, t, r, b = d.textbbox((0, 0), '& skelly', font=f)
    d.text((100 + (sw - (r - l)) / 2 - l, 100 + (sh_ - (b - t)) / 2 - t - 10), '& skelly', font=f, fill=255)
    face.alpha_composite(solid(ImageChops.multiply(txt, st), INK))
    # the curl of the peeled corner (its back, a shade darker, with a fold line)
    curl = Image.new('RGBA', st.size, (0, 0, 0, 0)); cd = ImageDraw.Draw(curl)
    cd.polygon([(100 + sw - 150, 100), (100 + sw + 10, 100 + 150), (100 + sw - 100, 100 + 120)], fill=(214, 205, 184, 255), outline=INK, width=8)
    face.alpha_composite(curl)
    ink = outline(st, 12)
    sticker = solid(ink, INK); sticker.alpha_composite(face)
    sticker = sticker.rotate(6, resample=Image.BICUBIC, expand=True)
    sx, sy = tx + tw - sticker.width + 40, ty + th - 330
    # the head peeks over the sticker's top edge, behind it, near its right end
    head = skull_head(640)
    hx, hy = sx + sticker.width - head.width - 240, sy - head.height + 250
    hl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); hl.alpha_composite(head, (hx, hy))
    layer.alpha_composite(drop_shadow(hl.getchannel('A'), 10, 16, 14))
    layer.alpha_composite(hl)
    sl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); sl.alpha_composite(sticker, (sx, sy))
    layer.alpha_composite(drop_shadow(sl.getchannel('A'), 14, 22, 18, k=.7))
    layer.alpha_composite(sl)
    return layer


# ---------------------------------------------------------------- b: bone letters
GLYPHS = {   # strokes on a 1 x 1.4 cell, y down
    'S': [((1, 0), (0, 0)), ((0, 0), (0, .7)), ((0, .7), (1, .7)), ((1, .7), (1, 1.4)), ((1, 1.4), (0, 1.4))],
    'K': [((0, 0), (0, 1.4)), ((.05, .78), (1, 0)), ((.32, .55), (1, 1.4))],
    'E': [((0, 0), (0, 1.4)), ((0, 0), (.95, 0)), ((0, .7), (.72, .7)), ((0, 1.4), (.95, 1.4))],
    'L': [((0, 0), (0, 1.4)), ((0, 1.4), (.9, 1.4))],
    'Y': [((0, 0), (.5, .72)), ((1, 0), (.5, .72)), ((.5, .72), (.5, 1.4))],
}
WIDTH = {'S': 1, 'K': 1, 'E': .95, 'L': .9, 'Y': 1}


def bone(draw, p0, p1, t, fill):
    """a cartoon bone from p0 to p1, shaft t thick, a pair of knuckles at each end"""
    (x0, y0), (x1, y1) = p0, p1
    L = math.hypot(x1 - x0, y1 - y0) or 1
    ux, uy = (x1 - x0) / L, (y1 - y0) / L; nx, ny = -uy, ux
    draw.line([(x0, y0), (x1, y1)], fill=fill, width=int(t))
    for (cx, cy) in ((x0, y0), (x1, y1)):
        for s in (-1, 1):
            r = t * .58
            px, py = cx + nx * s * t * .48, cy + ny * s * t * .48
            draw.ellipse((px - r, py - r, px + r, py + r), fill=fill)


def bone_word(word, cell, t, gap):
    pad = int(t * 2)
    widths = [WIDTH[c] * cell for c in word]
    ww = int(sum(widths) + gap * (len(word) - 1) + 2 * pad); hh = int(cell * 1.4 + 2 * pad)
    alpha = Image.new('L', (ww, hh), 0); d = ImageDraw.Draw(alpha)
    x = pad
    for c, w in zip(word, widths):
        for (a, b) in GLYPHS[c]:
            # strokes pulled in a little from the corners, so the knuckles sit on the joints
            p0 = (x + a[0] * cell, pad + a[1] * cell); p1 = (x + b[0] * cell, pad + b[1] * cell)
            bone(d, p0, p1, t, 255)
        x += w + gap
    return alpha


def variant_b():
    layer, (tx, ty, tw, th) = tag_layer()
    cell, t = 250, 62
    alpha = bone_word('SKELLY', cell, t, 78)
    ink = outline(alpha, 16)
    word = solid(ink, INK)
    fill = shade(solid(alpha, BONE), 12)
    # a touch of shading down each bone: the lower edge darker (the alpha eroded upward)
    low = ImageChops.subtract(alpha, ImageChops.offset(alpha, 0, -14))
    fill.alpha_composite(solid(ImageChops.multiply(low, alpha).point(lambda v: int(v * .45)), (150, 140, 120)))
    word.alpha_composite(fill)
    word = word.rotate(-4, resample=Image.BICUBIC, expand=True)
    # the "&": a lime sticker-dot in a black line, the marker ampersand in black on it
    dot = 400
    dl = Image.new('L', (dot + 60, dot + 60), 0); ImageDraw.Draw(dl).ellipse((30, 30, 30 + dot, 30 + dot), fill=255)
    amp = solid(outline(dl, 12), INK); amp.alpha_composite(shade(solid(dl, LIME), 10))
    al = Image.new('L', dl.size, 0); fa = ImageFont.truetype(FONT_MARKER, 300); da = ImageDraw.Draw(al)
    l, tt, r, b = da.textbbox((0, 0), '&', font=fa)
    da.text(((dl.width - (r - l)) / 2 - l, (dl.height - (b - tt)) / 2 - tt), '&', font=fa, fill=255)
    amp.alpha_composite(solid(al, INK))
    amp = amp.rotate(10, resample=Image.BICUBIC, expand=True)
    total = amp.width - 60 + word.width
    x0 = (W - total) // 2 + 120
    y0 = ty + th - 300
    wl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    wl.alpha_composite(word, (x0 + amp.width - 60, y0))
    wl.alpha_composite(amp, (x0 + 40, y0 + 40))
    layer.alpha_composite(drop_shadow(wl.getchannel('A'), 0, 26, 3, VIOLET, k=1))   # a hard violet drop, like a tag's 3D
    layer.alpha_composite(drop_shadow(wl.getchannel('A'), 12, 40, 22, k=.6))
    layer.alpha_composite(wl)
    return layer


# ---------------------------------------------------------------- c: stencil on tape
def variant_c():
    layer, (tx, ty, tw, th) = tag_layer()
    tw2, thh = 2300, 470
    tape = Image.new('L', (tw2 + 100, thh + 100), 0); d = ImageDraw.Draw(tape)
    # torn ends: a zigzag down each end
    pts = [(50 + 20, 50)]
    for i in range(1, 11):
        pts.append((50 + (0 if i % 2 else 26) + rng.integers(-6, 7), 50 + thh * i / 10))
    pts += [(50 + tw2 - 20, 50 + thh)]
    for i in range(9, -1, -1):
        pts.append((50 + tw2 - (0 if i % 2 else 26) + rng.integers(-6, 7), 50 + thh * i / 10))
    d.polygon(pts, fill=255)
    face = shade(solid(tape, (222, 206, 160)), 16)
    # the stencil: Impact capitals with bridges cut across them
    txt = Image.new('L', tape.size, 0); dt = ImageDraw.Draw(txt)
    f = ImageFont.truetype(FONT_BLOCK, 330)
    l, t, r, b = dt.textbbox((0, 0), '& SKELLY', font=f)
    ox, oy = 50 + (tw2 - (r - l)) / 2 - l, 50 + (thh - (b - t)) / 2 - t
    dt.text((ox, oy), '& SKELLY', font=f, fill=255)
    bridges = Image.new('L', tape.size, 255); db = ImageDraw.Draw(bridges)
    yb = 50 + thh / 2
    db.rectangle((0, yb - 9, tape.width, yb + 9), fill=0)
    stencil = ImageChops.multiply(txt, bridges)
    spray = stencil.filter(ImageFilter.GaussianBlur(9)).point(lambda v: int(v * .55))
    speck = Image.fromarray((rng.random((tape.height, tape.width)) > .985).astype(np.uint8) * 255, 'L')
    speck = ImageChops.multiply(speck, stencil.filter(ImageFilter.GaussianBlur(26)).point(lambda v: 255 if v > 10 else 0))
    face.alpha_composite(solid(ImageChops.multiply(ImageChops.lighter(spray, speck), tape), INK))
    face.alpha_composite(solid(ImageChops.multiply(stencil, tape), INK))
    face = face.rotate(-4, resample=Image.BICUBIC, expand=True)
    x0, y0 = (W - face.width) // 2 + 60, ty + th - 290
    fl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); fl.alpha_composite(face, (x0, y0))
    layer.alpha_composite(drop_shadow(fl.getchannel('A'), 8, 14, 12, k=.5))
    layer.alpha_composite(fl)
    return layer


def save(name, layer):
    out = trim(layer)
    out.save(os.path.join(HERE, f'title_{name}.png'))
    wall = Image.open(os.path.join(A, 'bonus_wall.webp')).convert('RGBA')
    k = max(out.width * 1.15 / wall.width, out.height * 1.3 / wall.height)
    wall = wall.resize((round(wall.width * k), round(wall.height * k)))
    wall = wall.point(lambda v: int(v * .7))
    wall.alpha_composite(out, ((wall.width - out.width) // 2, (wall.height - out.height) // 2))
    wall.convert('RGB').resize((wall.width // 3, wall.height // 3), Image.LANCZOS).save(os.path.join(HERE, f'preview_{name}.png'))


if __name__ == '__main__':
    which = sys.argv[1:] or ['a', 'b', 'c']
    for v in which:
        save(v, {'a': variant_a, 'b': variant_b, 'c': variant_c}[v]())
        print('built', v)
