"""The live wall: the SMUKIEZ tag's glowing outline, its light spilling onto the bricks, and the
paint oozing and dripping out of the cracked holes.

  python tools/sprayrim/make_wall_fx.py

frontend/assets/wallfx/
  tag_glow.webp     the tag's green outline as a neon glow (same box as wall_tag.webp, half size)
  tag_spill.webp    the outline's light thrown on the wall round it (the box padded by SPILL_PAD)
  bonus_glow.webp   the BONUS button's cyan outline as neon (the plate's box padded by BTN_PAD)
  blob_<i>.webp     each paint blob in bonus_wall.webp cut out with its outline (oozes in place)
  drip_<c>.webp     a run of paint per colour, top to bottom, ending in its drop
  drop_<c>.webp     a falling drop per colour
  wallfx.json       {blobs: [{x, y, w, h (fractions of the wall art), colour, tips: [[x, y, w], ...]}]}
"""
import json, os
import numpy as np
import cv2
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
A = os.path.join(ROOT, "frontend", "assets")
OUT = os.path.join(A, "wallfx")
SPILL_PAD = .22
GLOW_PAD = .06
BTN_PAD = .14
INK = (52, 14, 60)                     # the blobs' dark purple outline


def tag():
    im = np.asarray(Image.open(os.path.join(A, "wall_tag.webp")).convert("RGBA")).astype(np.float32) / 255
    H, W = im.shape[:2]
    rgb, al = im[..., :3], im[..., 3]
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    green = (al > .5) & (g > .62) & (r < .72 * g) & (b < .55 * g)
    k = .5
    m = cv2.resize(green.astype(np.float32), (int(W * k), int(H * k)), interpolation=cv2.INTER_AREA)
    # padded, so the halo fades out before the picture ends (cut at the tag's own box, it left a
    # straight edge of light on the wall)
    m = np.pad(m, ((int(m.shape[0] * GLOW_PAD), int(m.shape[0] * GLOW_PAD)), (int(m.shape[1] * GLOW_PAD), int(m.shape[1] * GLOW_PAD))))
    h, w = m.shape
    # the glow: a tight bright halo and a wide soft one, plus the line itself lit up
    g1 = cv2.GaussianBlur(m, (0, 0), 3); g2 = cv2.GaussianBlur(m, (0, 0), 11); g3 = cv2.GaussianBlur(m, (0, 0), 26)
    a = np.clip(m * .9 + g1 * 1.1 + g2 * .9 + g3 * .7, 0, 1)
    col = np.zeros((h, w, 3), np.float32)
    lime, hot = np.array([110, 255, 70], np.float32), np.array([225, 255, 200], np.float32)
    t = np.clip(m * 1.2 + g1 * .5, 0, 1)[..., None]
    col[:] = lime
    col = col * (1 - t) + hot * t
    os.makedirs(OUT, exist_ok=True)
    Image.fromarray(np.dstack([col, a * 255]).clip(0, 255).astype(np.uint8), "RGBA").save(os.path.join(OUT, "tag_glow.webp"), "WEBP", quality=88, alpha_quality=100, method=6)
    # the spill: the outline's light thrown wide over the wall
    k2 = .2
    ms = cv2.resize(green.astype(np.float32), (int(W * k2), int(H * k2)), interpolation=cv2.INTER_AREA)
    ph, pw = int(ms.shape[0] * SPILL_PAD), int(ms.shape[1] * SPILL_PAD)
    mp = np.pad(ms, ((ph, ph), (pw, pw)))
    s = cv2.GaussianBlur(mp, (0, 0), 14) * 2.2 + cv2.GaussianBlur(mp, (0, 0), 40) * 3.2
    s = np.clip(s, 0, 1) ** .8
    # no floor and nothing at the image's edge: the light must fade out before the box ends
    hh, ww = s.shape
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    edge = np.minimum(np.minimum(xx, ww - 1 - xx) / (pw * .9), np.minimum(yy, hh - 1 - yy) / (ph * .9))
    s = np.clip((s - .04) / .96, 0, 1) * np.clip(edge, 0, 1) ** 1.5
    sc = np.zeros(mp.shape + (3,), np.float32); sc[:] = (120, 255, 90)
    Image.fromarray(np.dstack([sc, s * 255]).clip(0, 255).astype(np.uint8), "RGBA").save(os.path.join(OUT, "tag_spill.webp"), "WEBP", quality=85, alpha_quality=100, method=6)


def drip_sprite(fill, light, w=40, h=200):
    SS = 4
    W, H = w * SS, h * SS
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    ow = W * .13
    def run(col, grow):
        for k in range(101):
            t = k / 100
            y = t * (H - W * .62)
            ww = W * (.62 - .2 * t ** .8) + grow
            d.ellipse([W / 2 - ww / 2, y - ww / 2, W / 2 + ww / 2, y + ww / 2], fill=col)
        r = W * .3 + grow / 2
        d.ellipse([W / 2 - r, H - W * .62 - r * .9, W / 2 + r, H - W * .62 + r * 1.15], fill=col)
    run(INK + (255,), 2 * ow)
    run(fill + (255,), 0)
    # a highlight down the left of the run and a glint on the drop
    d.line([(W * .4, W * .25), (W * .42, H - W * .95)], fill=light + (255,), width=int(W * .09))
    d.ellipse([W * .36, H - W * .78, W * .46, H - W * .66], fill=(255, 255, 255, 230))
    return im.resize((w, h), Image.LANCZOS)


def drop_sprite(fill, light, s=28):
    SS = 4
    S = s * SS
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    o = S * .1
    d.polygon([(S / 2, S * .02), (S * .78, S * .55), (S * .22, S * .55)], fill=INK + (255,))
    d.ellipse([S * .14, S * .3, S * .86, S * .98], fill=INK + (255,))
    d.polygon([(S / 2, S * .02 + o * 1.4), (S * .78 - o, S * .55), (S * .22 + o, S * .55)], fill=fill + (255,))
    d.ellipse([S * .14 + o, S * .3 + o, S * .86 - o, S * .98 - o], fill=fill + (255,))
    d.ellipse([S * .32, S * .5, S * .44, S * .64], fill=(255, 255, 255, 230))
    return im.resize((s, s), Image.LANCZOS)


def blobs():
    im = Image.open(os.path.join(A, "bonus_wall.webp")).convert("RGB")
    a = np.asarray(im).astype(np.int16)
    H, W = a.shape[:2]
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    pink = (r > 170) & (b > 130) & (g < r - 40)
    green = (g > 170) & (r < g - 40) & (b < g - 60)
    out = []
    for name, m in (("pink", pink), ("green", green)):
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
        for i in range(1, n):
            x, y, w, h, area = st[i]
            if area < 1500:
                continue
            comp = lab == i
            # the blob with its dark outline
            full = cv2.dilate(comp.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))).astype(bool)
            ys, xs = np.nonzero(full)
            x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
            crop = a[y0:y1, x0:x1].astype(np.uint8)
            mk = full[y0:y1, x0:x1]
            # alpha: the paint and its outline (dark purple), not the bricks round it
            sub = a[y0:y1, x0:x1]
            lum = sub @ np.array([.3, .59, .11])
            sat = sub.max(-1) - sub.min(-1)
            # the paint with its highlights (holes in the colour mask) filled, grown by the
            # outline's width so the dark purple edge comes with it
            c0 = cv2.morphologyEx(comp[y0:y1, x0:x1].astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
            ff = np.pad(c0, 1); fm = np.zeros((ff.shape[0] + 2, ff.shape[1] + 2), np.uint8)
            cv2.floodFill(ff, fm, (0, 0), 2)
            filled = (ff[1:-1, 1:-1] != 2).astype(np.uint8)
            keep = cv2.dilate(filled, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))).astype(np.float32)
            alpha = cv2.GaussianBlur(keep, (0, 0), 1.2)
            sprite = np.dstack([crop, (alpha * 255).astype(np.uint8)])
            idx = len(out)
            Image.fromarray(sprite, "RGBA").save(os.path.join(OUT, f"blob_{idx}.webp"), "WEBP", quality=88, alpha_quality=95, method=6)
            # tips: the lowest points of the paint, column by column, that stand below their
            # neighbours (a drip's end)
            col_low = np.array([np.nonzero(comp[:, c])[0].max() if comp[:, c].any() else -1 for c in range(x, x + w)])
            tips = []
            span = max(6, w // 8)
            for c in range(len(col_low)):
                v = col_low[c]
                if v < 0:
                    continue
                lo, hi = max(0, c - span), min(len(col_low), c + span + 1)
                if v == col_low[lo:hi].max() and v > y + h * .45 and (not tips or c - tips[-1][0] > span):
                    # the run's width there: how much paint the column above the tip holds
                    tw = int(((col_low[lo:hi] > v - h * .12)).sum())
                    tips.append((c, v, tw))
            tips = sorted(tips, key=lambda t: -t[1])[:3]
            out.append({"x": x0 / W, "y": y0 / H, "w": (x1 - x0) / W, "h": (y1 - y0) / H, "colour": name,
                        "tips": [[round((x + c) / W, 5), round(v / H, 5), round(max(8, min(tw, 60)) / W, 5)] for c, v, tw in tips]})
    return out


def bonus_glow():
    """bonus_glow.webp: the BONUS button's cyan outline as a neon tube - the line itself lit near
    white, a tight cyan halo and a wide soft one - padded by GLOW_PAD on every side."""
    im = np.asarray(Image.open(os.path.join(A, "bonus_btn_bg.webp")).convert("RGBA")).astype(np.float32) / 255
    H, W = im.shape[:2]
    r, g, b, al = im[..., 0], im[..., 1], im[..., 2], im[..., 3]
    cyan = (al > .5) & (b > .7) & (g > .6) & (r < .5)
    py, px = int(H * BTN_PAD), int(W * BTN_PAD)
    m = np.pad(cyan.astype(np.float32), ((py, py), (px, px)))
    g1 = cv2.GaussianBlur(m, (0, 0), 4); g2 = cv2.GaussianBlur(m, (0, 0), 14); g3 = cv2.GaussianBlur(m, (0, 0), 34)
    a = np.clip(m + g1 * 1.8 + g2 * 1.9 + g3 * 1.6, 0, 1)
    t = np.clip(m * 1.2 + g1 * .9, 0, 1)[..., None]
    col = np.array([60, 220, 255], np.float32) * (1 - t) + np.array([225, 250, 255], np.float32) * t
    Image.fromarray(np.dstack([col, a * 255]).clip(0, 255).astype(np.uint8), "RGBA").save(os.path.join(OUT, "bonus_glow.webp"), "WEBP", quality=88, alpha_quality=100, method=6)


def main():
    os.makedirs(OUT, exist_ok=True)
    tag()
    bonus_glow()
    pal = {"pink": ((236, 112, 196), (255, 196, 236)), "green": ((132, 240, 70), (220, 255, 190))}
    for c, (f, l) in pal.items():
        drip_sprite(f, l).save(os.path.join(OUT, f"drip_{c}.webp"), "WEBP", quality=90, alpha_quality=100, method=6)
        drop_sprite(f, l).save(os.path.join(OUT, f"drop_{c}.webp"), "WEBP", quality=90, alpha_quality=100, method=6)
    bl = blobs()
    with open(os.path.join(OUT, "wallfx.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"blobs": bl, "spillPad": SPILL_PAD, "glowPad": GLOW_PAD}, fh, indent=1)
    for b in bl:
        print(b["colour"], round(b["x"], 3), round(b["y"], 3), "tips", len(b["tips"]))


if __name__ == "__main__":
    main()
