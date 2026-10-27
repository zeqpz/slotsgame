"""Spray-paint dabs for the win line (frontend/index.html, drawWinLine), in the theme's colours
(art/STYLE.md): neon lime paint with a hot pale centre, its overspray violet, a faint violet glow.

  python tools/sprayrim/make_line_dabs.py

frontend/assets/fx/line_dab_{0..3}.webp: one burst of aerosol paint each, the way a can lays it
on a wall: a solid core with a ragged edge that breaks up into a speckle of fine droplets,
thinning out far past the core, with a few heavier drops thrown further. Laid along the cluster,
overlapping, the cores join into one solid lime stroke, the speckle becomes its violet overspray and
the faint halos add up to a glow round the line (baked in, so the line costs no filter).
frontend/assets/fx/line_drip.webp: a run of lime paint, top to bottom, ending in a drop, lit from
the upper left like all the art (a highlight down its left side, the right side in shade).
frontend/assets/fx/mult_glow.webp: a white spray blob (alpha only matters) - the shape of the
glow a Multi's value leaves on its cell: a soft round core breaking up into speckle, no edge.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "frontend", "assets", "fx")
LIME = np.array([156, 228, 36], np.float32)        # #9CE424, the paint
LIME_HOT = np.array([232, 254, 150], np.float32)   # the hot middle of the stroke
LIME_SHADE = np.array([88, 150, 18], np.float32)   # a run's shaded side
VIOLET = np.array([180, 84, 228], np.float32)      # #B454E4, the overspray
VIOLET_DEEP = np.array([108, 36, 180], np.float32) # #6C24B4, the glow
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
    alpha = np.asarray(im.resize((size, size), Image.LANCZOS), np.float32) / 255
    rs = np.asarray(Image.fromarray(r.astype(np.float32), "F").resize((size, size), Image.BILINEAR), np.float32)
    # Two sprites from the one burst, laid in two layers by the game so a puff's overspray never
    # covers the core of the puff before it: the CORE (line_dab_N) - the lime paint and the speckle
    # just round it, hot in the middle - and under every core the MIST (line_mist_N) - the violet
    # overspray further out and the faint violet glow
    hot = (np.clip(1 - rs / .7, 0, 1) ** 1.3 * .36)[..., None]
    core_a = alpha * np.clip((1.45 - rs) / .35, 0, 1)
    core_rgb = LIME * (1 - hot) + LIME_HOT * hot
    core = Image.fromarray(np.dstack([np.broadcast_to(core_rgb, (size, size, 3)), core_a * 255]).clip(0, 255).round().astype(np.uint8), "RGBA")
    mist_a = alpha * np.clip((rs - .7) / .4, 0, 1)
    glow = np.clip(.3 * np.exp(-np.maximum(rs - .6, 0) * 1.25), 0, 1) * (rs < 2.9)
    a = mist_a + glow * (1 - mist_a)
    rgb = (VIOLET * mist_a[..., None] + VIOLET_DEEP * (glow * (1 - mist_a))[..., None]) / np.maximum(a, 1e-4)[..., None]
    mist = Image.fromarray(np.dstack([rgb, a * 255]).clip(0, 255).round().astype(np.uint8), "RGBA")
    return core, mist


def drip(w=24, h=120):
    S = (w * 4, h * 4)
    im = Image.new("L", S, 0); d = ImageDraw.Draw(im)
    W, H = S
    for k in range(81):
        t = k / 80
        y = t * (H - W * .9)
        ww = W * (.95 - .5 * t ** .7)
        d.ellipse([W / 2 - ww / 2, y - ww / 2, W / 2 + ww / 2, y + ww / 2], fill=255)
    r = W * .36
    bead = (H - W * .9 - r * .8, H - W * .9 + r * 1.2)
    d.ellipse([W / 2 - r, bead[0], W / 2 + r, bead[1]], fill=255)
    a = np.asarray(im, np.float32) / 255
    # lit from the upper left: across each row, the left of the run catches the light, the right is in
    # shade; a thin hot streak runs down the lit side, and the drop at the end has its own glint
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    half = np.maximum(ndrow(a) / 2, 1)
    u = (xx - W / 2) / half[:, None]                       # -1 left edge .. +1 right edge, per row
    shade = np.clip(u * .7 + .15, 0, 1)[..., None]
    col = LIME * (1 - shade) + LIME_SHADE * shade
    streak = np.exp(-((u + .45) / .14) ** 2)[..., None] * .45
    col = col * (1 - streak) + LIME_HOT * streak
    by, bx = (bead[0] + bead[1]) / 2 - r * .35, W / 2 - r * .35
    glint = np.exp(-(((xx - bx) / (r * .22)) ** 2 + ((yy - by) / (r * .18)) ** 2))[..., None]
    col = col * (1 - glint) + np.array([255, 255, 240], np.float32) * glint
    out = Image.fromarray(np.dstack([col, a * 255]).clip(0, 255).round().astype(np.uint8), "RGBA")
    return out.resize((w, h), Image.LANCZOS)


def ndrow(a):
    """The width of the paint in each row (px)."""
    return (a > .5).sum(1).astype(np.float32)


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
        core, mist = dab(11 + i)
        core.save(os.path.join(OUT, f"line_dab_{i}.webp"), "WEBP", quality=92, alpha_quality=100, method=6)
        mist.save(os.path.join(OUT, f"line_mist_{i}.webp"), "WEBP", quality=90, alpha_quality=100, method=6)
    drip().save(os.path.join(OUT, "line_drip.webp"), "WEBP", quality=90, alpha_quality=100, method=6)
    mult_glow().save(os.path.join(OUT, "mult_glow.webp"), "WEBP", quality=90, alpha_quality=100, method=6)
    print("wrote 4 dabs (core + mist) + a drip in", OUT)


if __name__ == "__main__":
    main()
