"""Lobby tile art for Engine's tile editor (Studio > Media > Create tile), from the raw model art in media/src/
(made by tools/media/gen.py). Engine's rules (game-tile-requirements, read 2026-11-16): ONE feature character as a
transparent PNG enlarged to fill the key focus box; a bright environmental background with no dark edges; a
gradient band behind the title in a colour already on the tile; no wording, promo text or multipliers in the art.

  .venv312/Scripts/python.exe -I tools/media/make_tile.py
-> media/tile_character.png        Foreground layer: Smukiez waist up, the cut faded out at the bottom (use this one)
   media/tile_character_full.png   Foreground layer, whole figure
   media/tile_character_3x4.png    the bust already placed in the 3:4 key focus box, on a transparent 1632x2184 canvas
   media/tile_background.jpg       Background layer, 3:4 (2400x3200)
   media/tile_background_16x9.jpg  Background layer, 16:9 (3840x2160)
   media/preview_tile_3x4.png      mock of the editor's 408x546 tile: background + foreground + gradient + title
   media/preview_cover_16x9.png    mock of the 640x360 cover
   media/smukiez_tile_3x4.jpg / smukiez_cover_16x9.jpg   full-size composites with no title (backups)
   media/qa_*.png                  checks: the key focus box drawn over the tile, edge brightness numbers printed

Key focus box and title area, measured off Engine's guide images (imagery.jpg, text.jpg), as fractions of the 3:4
tile: focus box x .155-.843, y .037-.551 (a square); title band x .05-.95, y .588-.826; studio line y .870-.905."""
import os, sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, "media", "src")
OUT = os.path.join(ROOT, "media")

CHAR_RAW = os.path.join(SRC, "char_full_a.png")
BG34_RAW = os.path.join(SRC, "bg_3x4_a.webp")
BG169_RAW = os.path.join(SRC, "bg_16x9_a.webp")

FOCUS = (.155, .037, .843, .551)          # key focus box (x0, y0, x1, y1), fractions of the 3:4 tile
TITLE = (.05, .588, .95, .826)            # title safe band
BUST_CUT = .72                            # the bust ends this far down the whole figure (mid-thigh; the fade starts under the hands)
HERO = .88                                # beanie top to the bottom of the hands / cash, share of the bust's height
BUST_FADE = .10                           # bottom share of the bust that fades out (the gradient band covers it)
GRAD_RGB = (150, 52, 214)                 # gradient band: the mural's electric purple (on the tile, reads under white)
FONT = r"C:\Windows\Fonts\impact.ttf"     # stand-in for the editor's League Gothic / Proxima Nova Black
TITLE_TXT = ("SMUKIEZ", "& SKELLY")


# ---------------------------------------------------------------- character
def clean_alpha(im):
    """Keep alpha only on and just round the solid silhouette (drops the model's faint haze and specks) and give the
    soft edge ring the colour of the nearest solid pixel, so no dark or light fringe shows on any background."""
    a = np.asarray(im).astype(np.float32)
    al = a[..., 3]
    solid = ndimage.binary_fill_holes(al >= 128)
    lab, n = ndimage.label(solid)
    if n > 1:
        sizes = ndimage.sum(solid, lab, range(1, n + 1))
        solid = np.isin(lab, 1 + np.nonzero(sizes >= max(400, sizes.max() * .002))[0])
    near = ndimage.binary_dilation(solid, iterations=2)
    al2 = np.where(near, al, 0)
    core = ndimage.binary_erosion(solid, iterations=1)
    al2 = np.where(core, 255, al2)
    rgb = a[..., :3]
    inner = ndimage.binary_erosion(solid, iterations=2)
    idx = ndimage.distance_transform_edt(~inner, return_distances=False, return_indices=True)
    ring = near & ~inner
    rgb[ring] = rgb[idx[0][ring], idx[1][ring]]
    out = Image.fromarray(np.dstack([rgb, al2]).clip(0, 255).astype(np.uint8), "RGBA")
    return out.crop(out.getbbox())


def bust(full):
    h = round(full.height * BUST_CUT)
    b = full.crop((0, 0, full.width, h))
    b = b.crop(b.getbbox())
    a = np.asarray(b.getchannel("A")).astype(np.float32)
    f = round(b.height * BUST_FADE)
    ramp = np.ones(b.height, np.float32)
    t = np.linspace(0, 1, f)
    ramp[-f:] = 1 - t * t * (3 - 2 * t)                    # smoothstep to zero at the cut
    b.putalpha(Image.fromarray((a * ramp[:, None]).astype(np.uint8)))
    return b.crop(b.getbbox())


def place_in_focus(b, W, H):
    """Scale and position the bust so the hero part - beanie to the bottom of the hands and cash fan, HERO of the
    bust's height - spans the key focus box from its top down to the top of the title band, centred on the box; the
    tee below runs on under the title and the gradient. Returns (scaled bust, x, y)."""
    x0, y0, x1 = FOCUS[0] * W, FOCUS[1] * H, FOCUS[2] * W
    s = (TITLE[1] - FOCUS[1]) * H / (HERO * b.height)
    im = b.resize((round(b.width * s), round(b.height * s)), Image.LANCZOS)
    return im, round((x0 + x1) / 2 - im.width / 2), round(y0)


# ---------------------------------------------------------------- background
def cover_crop(im, w, h, fx=.5, fy=.5):
    s = max(w / im.width, h / im.height)
    big = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x = min(max(0, round(big.width * fx - w / 2)), big.width - w)
    y = min(max(0, round(big.height * fy - h / 2)), big.height - h)
    return big.crop((x, y, x + w, y + h))


def edge_report(name, im, band=.06):
    """Luma of the outer band: the reviewers' 'no dark edges' check. Prints the darkest 1 % and the share of pixels
    darker than 70/255 (mostly the ink outlines) and the darkest spot once the lines are blurred away."""
    g = np.asarray(im.convert("RGB")).astype(np.float32)
    L = g @ np.array([.2126, .7152, .0722], np.float32)
    h, w = L.shape
    b = max(2, round(min(w, h) * band))
    m = np.zeros_like(L, bool)
    m[:b], m[-b:], m[:, :b], m[:, -b:] = True, True, True, True
    e = L[m]
    # the ink outlines are thin dark lines; a dark AREA (shadow, black, navy) survives a blur the width of a brick
    blur = ndimage.gaussian_filter(L, min(w, h) / 160)[m]
    print(f"{name:28s} edge mean {e.mean():5.1f}  p5 {np.percentile(e, 5):5.1f}  dark<70 {100 * (e < 70).mean():4.1f}% "
          f"(ink lines)  darkest blurred area {blur.min():5.1f}  | whole mean {L.mean():5.1f}")


# ---------------------------------------------------------------- gradient + title (as the editor draws them)
def gradient(W, H, top=.50, solid=.86, rgb=GRAD_RGB):
    y = np.arange(H, dtype=np.float32) / H
    t = np.clip((y - top) / (solid - top), 0, 1)
    a = (t * t * (3 - 2 * t) * 255).astype(np.uint8)
    g = Image.new("RGBA", (W, H), rgb + (0,))
    g.putalpha(Image.fromarray(np.repeat(a[:, None], W, 1)))
    return g


def title(base, box, lines=TITLE_TXT):
    """White title lines, one size, as large as fits the box (fill the width, keep inside the height), with a soft
    shadow so it reads on the gradient."""
    W, H = base.size
    bx0, by0, bx1, by1 = box
    bw, bh = bx1 - bx0, by1 - by0
    gap = .04
    size = 10
    while True:
        f = ImageFont.truetype(FONT, size + 1)
        ws = [f.getbbox(t)[2] - f.getbbox(t)[0] for t in lines]
        hs = [f.getbbox(t)[3] - f.getbbox(t)[1] for t in lines]
        if max(ws) > bw or sum(hs) + gap * size * (len(lines) - 1) > bh:
            break
        size += 1
    f = ImageFont.truetype(FONT, size)
    hs = [f.getbbox(t)[3] - f.getbbox(t)[1] for t in lines]
    total = sum(hs) + gap * size * (len(lines) - 1)
    txt = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(txt)
    y = by0 + (bh - total) / 2
    for t, hh in zip(lines, hs):
        bb = f.getbbox(t)
        d.text((bx0 + (bw - (bb[2] - bb[0])) / 2 - bb[0], y - bb[1]), t, font=f, fill=(255, 255, 255, 255))
        y += hh + gap * size
    sh = Image.new("RGBA", base.size, (40, 0, 60, 0))
    sh.putalpha(txt.getchannel("A").filter(ImageFilter.GaussianBlur(max(1, size * .06))).point(lambda v: int(v * .7)))
    base.alpha_composite(sh, (0, max(1, round(size * .03))))
    base.alpha_composite(txt)


def soft_shadow(im, blur, alpha=.35, rgb=(40, 10, 70)):
    pad = blur * 3
    a = im.getchannel("A").point(lambda v: int(v * alpha))
    c = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), rgb + (0,))
    sh = Image.new("RGBA", im.size, rgb + (0,))
    sh.putalpha(a)
    c.alpha_composite(sh, (pad, pad))
    return c.filter(ImageFilter.GaussianBlur(blur)), pad


def save_rgb(img, name):
    """JPEG only: the PNG copies of these come out over Engine's 10 MB upload cap."""
    rgb = img.convert("RGB")
    p = os.path.join(OUT, name)
    rgb.save(p + ".jpg", quality=92, optimize=True, progressive=True)
    print(name, rgb.size)


def main():
    full = clean_alpha(Image.open(CHAR_RAW).convert("RGBA"))
    full.save(os.path.join(OUT, "tile_character_full.png"), optimize=True)
    b = bust(full)
    b.save(os.path.join(OUT, "tile_character.png"), optimize=True)
    print("tile_character_full.png", full.size, "| tile_character.png", b.size)

    # foreground already laid out in the 3:4 focus box (4x the 408x546 tile)
    W, H = 1632, 2184
    fb, x, y = place_in_focus(b, W, H)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay.alpha_composite(fb, (x, y)) if x >= 0 else lay.paste(fb, (x, y), fb)
    lay.save(os.path.join(OUT, "tile_character_3x4.png"), optimize=True)

    bg34 = cover_crop(Image.open(BG34_RAW).convert("RGB"), 2400, 3200)
    bg34.save(os.path.join(OUT, "tile_background.jpg"), quality=93, optimize=True, progressive=True)
    bg169 = cover_crop(Image.open(BG169_RAW).convert("RGB"), 3840, 2160)
    bg169.save(os.path.join(OUT, "tile_background_16x9.jpg"), quality=93, optimize=True, progressive=True)
    edge_report("tile_background.jpg", bg34)
    edge_report("tile_background_16x9.jpg", bg169)

    # ---- 3:4 tile mock, 408x546, layered as the editor does (rendered at 4x, then scaled down)
    k = 4
    W, H = 408 * k, 546 * k
    t = bg34.resize((W, H), Image.LANCZOS).convert("RGBA")
    fb, x, y = place_in_focus(b, W, H)
    t.alpha_composite(fb, (max(0, x), y)) if x >= 0 else t.paste(fb, (x, y), fb)
    t.alpha_composite(gradient(W, H))
    title(t, (TITLE[0] * W, TITLE[1] * H, TITLE[2] * W, TITLE[3] * H))
    t.resize((408, 546), Image.LANCZOS).convert("RGB").save(os.path.join(OUT, "preview_tile_3x4.png"), optimize=True)
    edge_report("preview_tile_3x4.png", t)

    # QA: the focus box and title band over the mock
    q = t.copy()
    d = ImageDraw.Draw(q)
    d.rectangle([FOCUS[0] * W, FOCUS[1] * H, FOCUS[2] * W, FOCUS[3] * H], outline=(255, 0, 0, 255), width=3 * k)
    d.rectangle([TITLE[0] * W, TITLE[1] * H, TITLE[2] * W, TITLE[3] * H], outline=(0, 255, 255, 255), width=2 * k)
    q.resize((816, 1092), Image.LANCZOS).convert("RGB").save(os.path.join(OUT, "qa_tile_focus_box.png"), optimize=True)

    # ---- 16:9 cover mock, 640x360: Smukiez right of centre filling the height, title on the left over a purple wash
    k = 4
    W, H = 640 * k, 360 * k
    c = bg169.resize((W, H), Image.LANCZOS).convert("RGBA")
    s = H * .96 / b.height
    cb = b.resize((round(b.width * s), round(b.height * s)), Image.LANCZOS)
    cx = round(W * .70 - cb.width / 2)
    c.alpha_composite(cb, (cx, round(H * .04)))
    xs = np.arange(W, dtype=np.float32) / W
    tt = np.clip((.62 - xs) / (.62 - .08), 0, 1)
    wash = Image.new("RGBA", (W, H), GRAD_RGB + (0,))
    wash.putalpha(Image.fromarray(np.repeat((tt * tt * (3 - 2 * tt) * 200).astype(np.uint8)[None, :], H, 0)))
    c.alpha_composite(wash)
    title(c, (W * .04, H * .25, W * .46, H * .75))
    c.resize((640, 360), Image.LANCZOS).convert("RGB").save(os.path.join(OUT, "preview_cover_16x9.png"), optimize=True)
    edge_report("preview_cover_16x9.png", c)

    # ---- full-size composites with no title (backups, Tipsy Harvest style)
    W, H = 2400, 3200
    t = bg34.copy().convert("RGBA")
    s = W * .86 / full.width
    fh = round(full.height * s)
    if fh > H * .96:
        s = H * .96 / full.height
    ff = full.resize((round(full.width * s), round(full.height * s)), Image.LANCZOS)
    sh, pad = soft_shadow(ff, 26)
    fx, fy = round(W / 2 - ff.width / 2), round(H - ff.height - H * .02)
    t.alpha_composite(sh, (fx - pad + 14, fy - pad + 22))
    t.alpha_composite(ff, (fx, fy))
    save_rgb(t, "smukiez_tile_3x4")
    W, H = 3840, 2160
    c = bg169.copy().convert("RGBA")
    s = H * .96 / full.height
    ff = full.resize((round(full.width * s), round(full.height * s)), Image.LANCZOS)
    sh, pad = soft_shadow(ff, 26)
    fx, fy = round(W / 2 - ff.width / 2), round(H - ff.height - H * .02)
    c.alpha_composite(sh, (fx - pad + 14, fy - pad + 22))
    c.alpha_composite(ff, (fx, fy))
    save_rgb(c, "smukiez_cover_16x9")


if __name__ == "__main__":
    main()
