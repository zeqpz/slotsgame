"""The spray can's effect art: the can that paints a Multi's value on, and the cartoon puff it
blows out while it sprays.

  python tools/make_spray_fx.py

art/fx-src/spray_can.png (1000 px source, drawn facing away from us - see art/fx-src/README.md)
  -> the can trimmed, 480 px tall, the icons' white sticker edge added if the source has none;
     prints the size and the nozzle point in the shipped image's pixels (SPRAY in index.html)
a drawn puff in L1's cloud style (flat L1 green, black ink, inner curls, white sticker edge)
  -> art/fx-src/spray_puff.png (1024 px), the puff 256 px wide

Both are painted in L1's exact green (0, 255, 61), and both ship once per Multi value's heat
colour: frontend/assets/fx/spray_can_<hue>.webp and spray_puff_<hue>.webp, the green turned to that
hue with its saturation and brightness kept. The values (SPRAY.values) and the heat scale
(HEAT_ANCHORS) are read out of frontend/index.html, and the hue is rounded the way the game rounds
it, so the file names always match what the game asks for. Tinting here rather than in the
browser keeps it off the loading screen: a canvas PNG encode took seconds per picture on a slow
laptop.
"""
import glob, json, math, os, random, re
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "art", "fx-src")
OUT = os.path.join(ROOT, "frontend", "assets", "fx")
GREEN = (0, 255, 61)
INK = (0, 0, 0)


def sticker_edge(im, px):
    """The icons' white edge: a band px wide round the art's silhouette, under it."""
    a = im.getchannel("A")
    grown = a.filter(ImageFilter.MaxFilter(2 * (px // 2) + 1))
    grown = grown.filter(ImageFilter.GaussianBlur(px * .12)).point(lambda v: 255 if v > 110 else int(v * 255 / 110))
    base = Image.new("RGBA", im.size, (255, 255, 255, 0)); base.putalpha(grown)
    return Image.alpha_composite(base, im)


def has_sticker_edge(im):
    """True when the outermost few pixels of the art are mostly white, like every icon's."""
    a = im.getchannel("A").point(lambda v: 255 if v > 128 else 0)
    inner = a.filter(ImageFilter.MinFilter(9))
    ring = ImageChops.subtract(a, inner)
    px = [im.getpixel((x, y)) for x in range(0, im.width, 2) for y in range(0, im.height, 2) if ring.getpixel((x, y))]
    if not px: return False
    return sum(1 for p in px if min(p[:3]) > 235) / len(px) > .6


def puff(size=1024, seed=7):
    """Overlapping round lobes inked as one silhouette, with the little curl strokes L1's cloud
    carries inside it."""
    rnd = random.Random(seed)
    S = size * 2   # drawn at 2x and brought down, on top of the 1024 px source's own detail
    lobes = [(.50, .56, .25), (.30, .60, .17), (.70, .58, .18), (.40, .37, .17), (.61, .38, .16), (.21, .45, .11), (.79, .44, .11)]
    ink_w = S * .028
    sil = Image.new("L", (S, S), 0); d = ImageDraw.Draw(sil)
    for x, y, r in lobes:
        d.ellipse([(x - r) * S - ink_w, (y - r) * S - ink_w, (x + r) * S + ink_w, (y + r) * S + ink_w], fill=255)
    fill = Image.new("L", (S, S), 0); d = ImageDraw.Draw(fill)
    for x, y, r in lobes:
        d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=255)
    im = Image.new("RGBA", (S, S), INK + (0,))
    im.putalpha(sil)
    green = Image.new("RGBA", (S, S), GREEN + (255,)); green.putalpha(fill)
    im = Image.alpha_composite(im, green)
    # inner curls: thin crescents hugging the lower-left of a few lobes (the cut between two
    # bulges of cloud, as L1 draws it) - a dark disc minus the same disc nudged up-right
    d = ImageDraw.Draw(im)
    for (x, y, r), (a0, k) in zip([lobes[0], lobes[3], lobes[4], lobes[2]], [(200, .55), (210, .5), (190, .45), (215, .5)]):
        cr = r * k * S
        cx = x * S + math.cos(math.radians(a0)) * r * S * .45
        cy = y * S - math.sin(math.radians(a0)) * r * S * .45
        m = Image.new("L", (S, S), 0); md = ImageDraw.Draw(m)
        md.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=255)
        off = cr * .22
        md.ellipse([cx - cr + off, cy - cr - off * .9, cx + cr + off, cy + cr - off * .9], fill=0)
        # keep only the lower-left arc of the crescent
        md.polygon([(cx - cr * 1.2, cy - cr * 1.3), (cx + cr * 1.3, cy - cr * 1.3), (cx + cr * 1.3, cy + cr * .2)], fill=0)
        m = ImageChops.multiply(m, fill)
        ink = Image.new("RGBA", (S, S), INK + (255,)); ink.putalpha(m)
        im = Image.alpha_composite(im, ink)
    im = im.resize((size, size), Image.LANCZOS)
    im = sticker_edge(im, int(size * .022))
    return im.crop(im.getbbox())


def game_hues():
    """The heat hue of every Multi value, exactly as the game works it out (heatHue + Math.round)."""
    html = open(os.path.join(ROOT, "frontend", "index.html"), encoding="utf-8").read()
    anchors = json.loads(re.search(r"const HEAT_ANCHORS = (\[\[.*?\]\]);", html).group(1))
    values = json.loads(re.search(r"values: (\[[0-9., ]+\]),", html).group(1))
    def hue(v):
        x = max(1.25, min(1000, v))
        for (v0, h0), (v1, h1) in zip(anchors, anchors[1:]):
            if x <= v1:
                return h0 + (h1 - h0) * math.log(x / v0) / math.log(v1 / v0)
        return 0
    return sorted({math.floor(hue(v) + .5) for v in values})   # Math.round, not Python's round


def tint(im, hue):
    """L1's green turned to `hue`, as the game's colour rule has it: green-led pixels only (spread
    48 or more, hue 93-177 degrees), saturation and brightness kept (HSV); greys, ink, white and
    cream stay as they are."""
    a = np.asarray(im.convert("RGBA")).astype(np.float64)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = np.maximum(np.maximum(r, g), b); dl = mx - np.minimum(np.minimum(r, g), b)
    with np.errstate(divide="ignore", invalid="ignore"):
        h = (b - r) / dl + 2
        sel = (a[..., 3] > 0) & (dl >= 48) & (mx == g) & (h >= 1.55) & (h <= 2.95)
        s = np.where(mx > 0, dl / mx, 0)
    h6 = (hue % 360) / 60; k = int(h6) % 6; f = h6 - int(h6)
    v = mx; P = v * (1 - s); Q = v * (1 - s * f); U = v * (1 - s * (1 - f))
    out = [(v, U, P), (Q, v, P), (P, v, U), (P, Q, v), (U, P, v), (v, P, Q)][k]
    for c in range(3):
        a[..., c] = np.where(sel, out[c], a[..., c])
    return Image.fromarray(np.clip(np.floor(a + .5), 0, 255).astype(np.uint8), "RGBA")


def ship(im, name, hues):
    """One WebP per heat hue; any older tints of this picture are cleared out first."""
    for old in glob.glob(os.path.join(OUT, name + "*.webp")):
        os.remove(old)
    total = 0
    for h in hues:
        path = os.path.join(OUT, f"{name}_{h}.webp")
        tint(im, h).save(path, "WEBP", quality=92, alpha_quality=100, method=6)
        total += os.path.getsize(path)
    return total


def main():
    os.makedirs(SRC, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    hues = game_hues()
    print("heat hues", hues)
    p = puff()
    p.save(os.path.join(SRC, "spray_puff.png"))
    small = p.resize((256, round(256 * p.height / p.width)), Image.LANCZOS)
    kb = ship(small, "spray_puff", hues) // 1024
    print("puff", small.size, f"x{len(hues)} tints, {kb} KB")
    can_src = os.path.join(SRC, "spray_can.png")
    if os.path.exists(can_src):
        meta_path = os.path.join(SRC, "spray_can.json")
        meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
        im = Image.open(can_src).convert("RGBA")
        if not has_sticker_edge(im):
            im = sticker_edge(im, 14)   # the icons' edge is ~14 px on a 1000 px source
            print("can: sticker edge added")
        box = im.getbbox(); pad = 8
        box = (max(0, box[0] - pad), max(0, box[1] - pad), min(im.width, box[2] + pad), min(im.height, box[3] + pad))
        im = im.crop(box)
        k = 480 / im.height
        out = im.resize((round(im.width * k), 480), Image.LANCZOS)
        kb = ship(out, "spray_can", hues) // 1024
        print(f"can x{len(hues)} tints, {kb} KB")
        nz = meta.get("nozzle")
        if nz:
            print("can", out.size, "nozzle", [round((nz[0] - box[0]) * k, 1), round((nz[1] - box[1]) * k, 1)])
        else:
            print("can", out.size, "(no nozzle in spray_can.json)")


if __name__ == "__main__":
    main()
