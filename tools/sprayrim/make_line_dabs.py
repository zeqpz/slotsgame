"""Spray-paint dabs for the win line (frontend/index.html, drawWinLine).

  python tools/sprayrim/make_line_dabs.py

frontend/assets/fx/line_dab_{0..3}.webp: one puff of aerosol paint each - a dense, slightly
lighter core fading out through a fringe of fine overspray droplets, with a faint glow - laid
along the cluster dozens of times, overlapping, so the line reads as one sprayed stroke.
frontend/assets/fx/line_drip.webp: a run of paint, top to bottom, ending in a drop, hung off
the stroke here and there.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "frontend", "assets", "fx")
ORANGE = np.array([255, 138, 42], np.float32)
LIGHT = np.array([255, 196, 110], np.float32)
DEEP = np.array([226, 92, 12], np.float32)
SS = 4


def dab(seed, size=96):
    rng = np.random.default_rng(seed)
    S = size * SS
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    c = S / 2 + rng.normal(0, S * .015, 2)
    # an uneven core: a few overlapping gaussians, never a perfect disc
    core = np.zeros((S, S), np.float32)
    for _ in range(4):
        o = rng.normal(0, S * .05, 2); sg = S * rng.uniform(.15, .19)
        core = np.maximum(core, np.exp(-(((xx - c[0] - o[0]) ** 2 + (yy - c[1] - o[1]) ** 2) / (2 * sg * sg))))
    a = np.clip(core * 1.5, 0, 1) ** 1.1
    glow = np.exp(-(((xx - c[0]) ** 2 + (yy - c[1]) ** 2) / (2 * (S * .26) ** 2))) * .22
    # overspray: fine droplets, densest near the core
    im = Image.new("L", (S, S), 0); d = ImageDraw.Draw(im)
    for _ in range(420):
        r = abs(rng.normal(0, S * .19)); th = rng.uniform(0, 2 * np.pi)
        x, y = c[0] + r * np.cos(th), c[1] + r * np.sin(th)
        if r > S * .47: continue
        rr = S * rng.uniform(.004, .013) * (1.3 - r / (S * .5))
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=int(255 * rng.uniform(.55, 1)))
    dots = np.asarray(im, np.float32) / 255
    alpha = np.clip(np.maximum(np.maximum(a, dots), glow), 0, 1)
    # colour: light in the heart of the core, orange, deeper at the fringe
    t = np.clip(core * 1.25, 0, 1)
    rgb = DEEP[None, None] * (1 - t[..., None]) + ORANGE[None, None] * t[..., None]
    rgb = rgb * (1 - np.clip((core - .75) * 3, 0, 1)[..., None]) + LIGHT[None, None] * np.clip((core - .75) * 3, 0, 1)[..., None]
    out = Image.fromarray(np.dstack([rgb, alpha * 255]).clip(0, 255).astype(np.uint8), "RGBA")
    return out.resize((size, size), Image.LANCZOS)


def drip(w=24, h=120):
    S = (w * SS, h * SS)
    im = Image.new("RGBA", S, (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    W, H = S
    steps = 80
    for k in range(steps + 1):
        t = k / steps
        y = t * (H - W * .9)
        ww = W * (.95 - .5 * t ** .7)
        d.ellipse([W / 2 - ww / 2, y - ww / 2, W / 2 + ww / 2, y + ww / 2], fill=tuple(int(v) for v in ORANGE) + (255,))
    r = W * .36
    d.ellipse([W / 2 - r, H - W * .9 - r * .8, W / 2 + r, H - W * .9 + r * 1.2], fill=tuple(int(v) for v in ORANGE) + (255,))
    # a highlight streak down the left of the run
    hl = Image.new("RGBA", S, (0, 0, 0, 0)); hd = ImageDraw.Draw(hl)
    hd.line([(W * .38, W * .3), (W * .4, H - W * 1.3)], fill=tuple(int(v) for v in LIGHT) + (200,), width=int(W * .12))
    hd.ellipse([W * .3, H - W * 1.15, W * .45, H - W]
               , fill=(255, 235, 200, 220))
    im = Image.alpha_composite(im, hl.filter(ImageFilter.GaussianBlur(SS * .6)))
    return im.resize((w, h), Image.LANCZOS)


def main():
    os.makedirs(OUT, exist_ok=True)
    for i in range(4):
        dab(11 + i).save(os.path.join(OUT, f"line_dab_{i}.webp"), "WEBP", quality=90, alpha_quality=100, method=6)
    drip().save(os.path.join(OUT, "line_drip.webp"), "WEBP", quality=90, alpha_quality=100, method=6)
    print("wrote 4 dabs + a drip in", OUT)


if __name__ == "__main__":
    main()
