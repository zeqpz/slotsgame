"""The cover: the game's own background (bg_<shape>.png, shot from the game) with the two figures standing on
its pavement, each with a soft contact shadow (cast down and to the right, as the art's light does).
usage: python compose.py   -> final_16x9.png (3840x2160), final_3x4.png (2160x2880), review_final.jpg"""
import os
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))


def figure(name):
    im = Image.open(os.path.join(HERE, f"char_{name}.png")).convert("RGBA")
    a = im.getchannel("A").point(lambda v: 255 if v > 24 else 0)
    return im.crop(a.getbbox())


def place(bg, fig, cx, feet_y, height):
    k = height / fig.height
    f = fig.resize((round(fig.width * k), round(height)), Image.LANCZOS)
    x, y = round(cx - f.width / 2), round(feet_y - f.height)
    # contact shadow: a soft dark pool under the feet, pushed down and to the right
    sh = Image.new("L", bg.size, 0)
    w = f.width * .62
    ImageDraw.Draw(sh).ellipse([cx - w / 2 + f.width * .05, feet_y - height * .022, cx + w / 2 + f.width * .09, feet_y + height * .03], fill=170)
    sh = sh.filter(ImageFilter.GaussianBlur(height * .018))
    bg.paste(Image.new("RGBA", bg.size, (6, 5, 10, 255)), (0, 0), sh)
    bg.alpha_composite(f, (x, y))


boy, skull = figure("boy"), figure("skull")
out = {}
for shape, spec in {
    "16x9": dict(boy=(.165, .965, .78), skull=(.84, .965, .78)),
    "3x4": dict(boy=(.29, .965, .5), skull=(.71, .965, .5)),
}.items():
    bg = Image.open(os.path.join(HERE, f"bg_{shape}.png")).convert("RGBA")
    W, H = bg.size
    for name, fig in (("boy", boy), ("skull", skull)):
        cx, fy, hh = spec[name]
        place(bg, fig, cx * W, fy * H, hh * H)
    p = os.path.join(HERE, f"final_{shape}.png")
    bg.convert("RGB").save(p, optimize=True)
    out[shape] = bg.convert("RGB")
    print(shape, bg.size)
# a review sheet
a, b = out["16x9"], out["3x4"]
H = 700
a, b = a.resize((round(a.width * H / a.height), H)), b.resize((round(b.width * H / b.height), H))
s = Image.new("RGB", (a.width + b.width + 10, H)); s.paste(a, (0, 0)); s.paste(b, (a.width + 10, 0))
s.save(os.path.join(HERE, "review_final.jpg"), quality=82)
