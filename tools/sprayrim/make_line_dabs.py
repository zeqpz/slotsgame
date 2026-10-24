"""Spray-paint dabs for the win line (frontend/index.html, drawWinLine).

  python tools/sprayrim/make_line_dabs.py

frontend/assets/fx/line_dab_{0..3}.webp: one burst of aerosol paint each, the way a can lays it
on a wall: a solid core with a ragged edge that breaks up into a speckle of fine droplets,
thinning out far past the core, with a few heavier drops thrown further. Laid along the cluster,
overlapping, the cores join into one solid stroke and the speckle becomes its overspray.
frontend/assets/fx/line_drip.webp: a run of paint, top to bottom, ending in a drop.
frontend/assets/fx/mult_glow.webp: a white spray blob (alpha only matters) - the shape of the
glow a Multi's value leaves on its cell: a soft round core breaking up into speckle, no edge.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "frontend", "assets", "fx")
ORANGE = (255, 138, 42)
SIZE = 128          # sprite px; drawn about 46 css px wide, so ~2.8 sprite px per css px
SS = 2              # supersampling for the droplet discs


def dab(seed, size=SIZE):
    rng = np.random.default_rng(seed)
    S = size * SS
    c = np.array([S / 2, S / 2]) + rng.normal(0, S * .01, 2)
    R = S * .17                                     # the core's radius
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    ang = np.arctan2(yy - c[1], xx - c[0])
    # the core's edge wobbles a little round the circle
    wob = sum(rng.uniform(.02, .06) * np.cos(k * ang + rng.uniform(0, 6.3)) for k in (2, 3, 5, 7))
    r = np.hypot(xx - c[0], yy - c[1]) / (R * (1 + wob))
    # speckle density: solid inside the core, then a long falling tail (a fine spray reaches far)
    dens = np.where(r < 1, 1.0, np.exp(-(r - 1) * 2.1) * .85 + np.exp(-(r - 1) * .55) * .07)
    # grain: each droplet a pixel or two, laid where a random field falls under the density
    grain = rng.random((S, S)).astype(np.float32)
    # clump the grain a little (spray is not perfectly uniform): a soft noise multiplies the density
    clump = np.asarray(Image.fromarray((rng.random((S // 6, S // 6)) * 255).astype(np.uint8)).resize((S, S), Image.BICUBIC), np.float32) / 255
    a = (grain < dens * (.75 + .5 * clump)).astype(np.float32)
    a[r < .92] = 1.0
    im = Image.fromarray((a * 255).astype(np.uint8), "L")
    # heavier drops thrown out past the speckle, and a couple sitting in it
    d = ImageDraw.Draw(im)
    for _ in range(rng.integers(5, 10)):
        rr = R * rng.uniform(1.2, 2.6); th = rng.uniform(0, 2 * np.pi)
        x, y = c[0] + rr * np.cos(th), c[1] + rr * np.sin(th)
        q = S * rng.uniform(.006, .016)
        d.ellipse([x - q, y - q, x + q, y + q], fill=255)
    alpha = np.asarray(im.resize((size, size), Image.LANCZOS), np.float32)
    rgb = np.empty((size, size, 3), np.float32); rgb[:] = ORANGE
    return Image.fromarray(np.dstack([rgb, alpha]).astype(np.uint8), "RGBA")


def drip(w=24, h=120):
    S = (w * 4, h * 4)
    im = Image.new("RGBA", S, (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    W, H = S
    for k in range(81):
        t = k / 80
        y = t * (H - W * .9)
        ww = W * (.95 - .5 * t ** .7)
        d.ellipse([W / 2 - ww / 2, y - ww / 2, W / 2 + ww / 2, y + ww / 2], fill=ORANGE + (255,))
    r = W * .36
    d.ellipse([W / 2 - r, H - W * .9 - r * .8, W / 2 + r, H - W * .9 + r * 1.2], fill=ORANGE + (255,))
    return im.resize((w, h), Image.LANCZOS)


def mult_glow(seed=5, size=192):
    rng = np.random.default_rng(seed)
    S = size
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    c = S / 2
    ang = np.arctan2(yy - c, xx - c)
    wob = sum(rng.uniform(.02, .05) * np.cos(k * ang + rng.uniform(0, 6.3)) for k in (2, 3, 5))
    r = np.hypot(xx - c, yy - c) / (S * .3 * (1 + wob))
    soft = np.clip(1.15 - r * .55, 0, 1) ** 1.4                 # the body: dense in the middle, thinning
    dens = np.where(r < 1, soft, soft * np.exp(-(r - 1) * 2.6))
    grain = rng.random((S, S)).astype(np.float32)
    a = np.where(r < .55, soft, (grain < dens * 1.1).astype(np.float32) * .95)
    a = np.clip(a, 0, 1)
    a[np.hypot(xx - c, yy - c) > S * .49] = 0
    out = np.dstack([np.full((S, S, 3), 255, np.float32), a * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def main():
    os.makedirs(OUT, exist_ok=True)
    for i in range(4):
        dab(11 + i).save(os.path.join(OUT, f"line_dab_{i}.webp"), "WEBP", quality=92, alpha_quality=100, method=6)
    drip().save(os.path.join(OUT, "line_drip.webp"), "WEBP", quality=90, alpha_quality=100, method=6)
    mult_glow().save(os.path.join(OUT, "mult_glow.webp"), "WEBP", quality=90, alpha_quality=100, method=6)
    print("wrote 4 dabs + a drip in", OUT)


if __name__ == "__main__":
    main()
