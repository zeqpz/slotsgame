# The bonus shop's card banners, v2 (owner, 2026-11-05): built from the game's OWN art, nothing generated -
# the brick wall (frontend/assets/bonus_wall.webp), the SMUKIEZ neon tag on it (wall_tag.webp), and the
# character in a real rendered frame (art/blender/chars): the boy for FREE SPINS, the skeleton for the
# extreme ones, the mode's scatter sticker (assets/flat/BS|ES.webp) beside him, a pool of the mode's light.
#   python build.py   -> frontend/assets/bonus/banner_fs.webp, banner_xfs.webp (720x405) + previews here
import os
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
A = os.path.join(ROOT, 'frontend', 'assets')
OUT = os.path.join(A, 'bonus')
W, H, S = 720, 405, 2
MODES = {
    'fs':  dict(char='art/blender/chars/boy/renders/cash_show/0052.png', icon='flat/BS.webp', glow=(108, 252, 84)),
    'xfs': dict(char='art/blender/chars/skull/renders/win/0030.png', icon='flat/ES.webp', glow=(180, 84, 228)),
}


def cover(im, w, h, cx=.5, cy=.5):
    k = max(w / im.size[0], h / im.size[1])
    im = im.resize((round(im.size[0] * k), round(im.size[1] * k)), Image.LANCZOS)
    x = round((im.size[0] - w) * cx); y = round((im.size[1] - h) * cy)
    return im.crop((x, y, x + w, y + h))


def pool(size, cx, cy, rx, ry, rgb, alpha):
    yy, xx = np.mgrid[0:size[1], 0:size[0]].astype(np.float32)
    d = np.hypot((xx - cx) / rx, (yy - cy) / ry)
    g = Image.new('RGBA', size, rgb + (0,))
    g.putalpha(Image.fromarray((np.clip(1 - d, 0, 1) ** 1.6 * alpha).astype(np.uint8), 'L'))
    return g


def trim(im):
    return im.crop(im.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox())


def build(name, m):
    w, h = W * S, H * S
    bg = cover(Image.open(os.path.join(A, 'bonus_wall.webp')).convert('RGB'), w, h, .5, .42)
    bg = ImageEnhance.Brightness(bg).enhance(.62).convert('RGBA')   # the wall darkened, as the game shows it
    tag = trim(Image.open(os.path.join(A, 'wall_tag.webp')).convert('RGBA'))
    k = w * .92 / tag.size[0]
    tag = tag.resize((round(tag.size[0] * k), round(tag.size[1] * k)), Image.LANCZOS)
    tag.putalpha(tag.getchannel('A').point(lambda v: int(v * .78)))
    bg.alpha_composite(tag, ((w - tag.size[0]) // 2, round(h * .06)))
    # the character: head to knees on the right, his own light pooled behind him
    ch = trim(Image.open(os.path.join(ROOT, m['char'])).convert('RGBA'))
    k = h * 1.22 / ch.size[1]
    ch = ch.resize((round(ch.size[0] * k), round(ch.size[1] * k)), Image.LANCZOS)
    cx = round(w * .71 - ch.size[0] / 2)
    bg.alpha_composite(pool(bg.size, w * .71, h * .55, w * .28, h * .62, m['glow'], 120))
    sh = Image.new('L', bg.size, 0); sh.paste(ch.getchannel('A').point(lambda v: int(v * .55)), (cx + 10 * S, round(h * .06) + 12 * S))
    bg.alpha_composite(Image.merge('RGBA', (Image.new('L', bg.size, 8),) * 3 + (sh.filter(ImageFilter.GaussianBlur(10 * S)),)))
    bg.alpha_composite(ch, (cx, round(h * .06)))
    # the mode's sticker on the left
    ic = trim(Image.open(os.path.join(A, m['icon'])).convert('RGBA'))
    k = min(h * .52 / ic.size[1], w * .38 / ic.size[0])
    ic = ic.resize((round(ic.size[0] * k), round(ic.size[1] * k)), Image.LANCZOS)
    ix, iy = round(w * .26 - ic.size[0] / 2), round(h * .5 - ic.size[1] / 2)
    sh = Image.new('L', bg.size, 0); sh.paste(ic.getchannel('A').point(lambda v: int(v * .6)), (ix + 6 * S, iy + 9 * S))
    bg.alpha_composite(Image.merge('RGBA', (Image.new('L', bg.size, 8),) * 3 + (sh.filter(ImageFilter.GaussianBlur(8 * S)),)))
    bg.alpha_composite(ic, (ix, iy))
    out = bg.convert('RGB').resize((W, H), Image.LANCZOS)
    os.makedirs(OUT, exist_ok=True)
    out.save(os.path.join(OUT, f'banner_{name}.webp'), 'WEBP', quality=88, method=6)
    out.save(os.path.join(HERE, f'preview_{name}.png'))


if __name__ == '__main__':
    for n, m in MODES.items():
        build(n, m)
        print('banner', n)
