"""Inputs for the live spray rims (frontend/sprayrim.js): for every piece of art with the sprayed
blue outline, the art without its outline, and the outline's shape as a distance field.

  python tools/sprayrim/make_rims.py [name ...]

For each name in RIMS:
  art/ui-src/<name>.png (the art at its own size: the mask and the field come from it) and
  frontend/assets/<name>.webp (the high-res pass of the same art) ->
    frontend/assets/rim/<name>.webp      the art with its blue outline cut away: the grey plate
                                         and whatever is painted on it (the live rim is drawn
                                         round the plate's edge instead)
    frontend/assets/rim/<name>_sdf.png   the plate's edge as a signed distance field, over the
                                         art padded by PAD on every side, at half size: grey 128
                                         is the edge, +1 per STEP source px outside, -1 inside
    frontend/assets/rim/rims.json        {name: {w, h, pad, step, scale, band}}: band is the old
                                         outline's width in source px, which the live rim keeps
  and frontend/assets/plate_grey.webp, the bonus panel's grey plate edge to edge (the see-through
  backing behind the board's reels)

The plate is the art's big grey area with everything it encloses (glyphs, specks, a hollow
middle like the volume tube's); the field is taken from that filled shape, the cut image keeps
the art's own transparency, so a hollow stays hollow.
"""
import json, os, sys
import numpy as np
import cv2
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "art", "ui-src")
ASSETS = os.path.join(ROOT, "frontend", "assets")
OUT = os.path.join(ASSETS, "rim")
STEP = 2.0        # source px per field step: +-127 steps = +-254 source px
SCALE = .5        # the field is stored at half the source size (it is smooth; the GPU interpolates)

RIMS = ["bonus_panel", "feature_box", "info_panel", "auto_box", "win_box", "vol_frame", "hud_bar", "hud_menu",
        "hud_audio", "hud_rapid", "hud_rapid_on", "hud_auto", "hud_minus", "hud_plus", "hud_hex"]


def plate_mask(a):
    rgb, al = a[..., :3], a[..., 3]
    sat = rgb.max(-1) - rgb.min(-1)
    lum = rgb @ np.array([.3, .59, .11], np.float32)
    grey = (al > .6) & (sat < .14) & (lum > .12)
    H, W = grey.shape
    k = max(3, int(round(min(W, H) * .02)) | 1)
    m = cv2.morphologyEx(grey.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    m = (lab == i).astype(np.uint8)
    ff = np.pad(m, 1); mask = np.zeros((H + 4, W + 4), np.uint8)
    cv2.floodFill(ff, mask, (0, 0), 2)
    filled = ff[1:-1, 1:-1] != 2
    # a smooth edge: the grey's grain and the dither leave it ragged
    return cv2.GaussianBlur(filled.astype(np.float32), (0, 0), max(1.0, min(W, H) * .004)) > .5


def make(name):
    a = np.asarray(Image.open(os.path.join(SRC, name + ".png")).convert("RGBA")).astype(np.float32) / 255
    H, W = a.shape[:2]
    m = plate_mask(a)
    # the old outline's width: how far its paint reaches out from the plate
    vis = a[..., 3] > .5
    dist_out = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
    rim = vis & ~m & (dist_out < .12 * min(W, H))
    band = float(np.percentile(dist_out[rim], 85)) if rim.any() else .03 * min(W, H)
    # the field, over the art padded on every side
    pad = int(min(250 * STEP / 2, max(48, .28 * max(W, H))))
    mp = np.pad(m, pad)
    dout = cv2.distanceTransform((~mp).astype(np.uint8), cv2.DIST_L2, 5)
    din = cv2.distanceTransform(mp.astype(np.uint8), cv2.DIST_L2, 5)
    sd = np.where(mp, -(din - .5), dout - .5)
    v = np.clip(128 + sd / STEP, 0, 255)
    small = cv2.resize(v, (round(mp.shape[1] * SCALE), round(mp.shape[0] * SCALE)), interpolation=cv2.INTER_AREA)
    os.makedirs(OUT, exist_ok=True)
    Image.fromarray(small.round().astype(np.uint8), "L").save(os.path.join(OUT, name + "_sdf.png"), optimize=True)
    # the art without its outline, at the high-res pass's size, with a soft edge
    hi = Image.open(os.path.join(ASSETS, name + ".webp")).convert("RGBA")
    k = hi.width / W
    mh = cv2.resize(m.astype(np.float32), hi.size, interpolation=cv2.INTER_LINEAR)
    mh = np.clip((cv2.GaussianBlur(mh, (0, 0), .9 * k) - .5) * 2.5 + .5, 0, 1)
    px = np.asarray(hi).astype(np.float32)
    px[..., 3] *= mh
    px[px[..., 3] < 1, :3] = 0
    Image.fromarray(px.round().astype(np.uint8), "RGBA").save(os.path.join(OUT, name + ".webp"), "WEBP", quality=88, alpha_quality=100, method=6)
    return {"w": W, "h": H, "pad": pad, "step": STEP, "scale": SCALE, "band": round(band, 2)}


def plate_texture():
    a = np.asarray(Image.open(os.path.join(SRC, "bonus_panel.png")).convert("RGBA")).astype(np.float32) / 255
    m = plate_mask(a)
    hi = Image.open(os.path.join(ASSETS, "bonus_panel.webp")).convert("RGBA")
    k = hi.width / a.shape[1]
    ys, xs = np.nonzero(cv2.erode(m.astype(np.uint8), np.ones((41, 41), np.uint8)))
    box = (int(xs.min() * k), int(ys.min() * k), int(xs.max() * k), int(ys.max() * k))
    hi.crop(box).convert("RGB").save(os.path.join(ASSETS, "plate_grey.webp"), "WEBP", quality=82, method=6)


def main(argv):
    names = argv or RIMS
    if not argv:
        plate_texture()
    meta_path = os.path.join(OUT, "rims.json")
    meta = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else {}
    for n in names:
        meta[n] = make(n)
        print(f"{n:14s} {meta[n]}")
    with open(meta_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(meta, fh, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
