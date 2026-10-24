"""Inputs for the live spray rims (frontend/index.html, "spray rims"): the bonus-buy panel's grey
plate on its own, its outline as a distance field, and the grey plate texture the board shows
through its frame.

  python tools/sprayrim/make_masks.py

art/ui-src/bonus_panel.png (grey plate + sprayed blue rim) ->
  frontend/assets/bonus_plate.webp    the grey plate alone (the rim is drawn live over its edge)
  frontend/assets/bonus_plate_sdf.png the plate's edge as a distance field: 128 = the edge, +1 per
                                      SDF_PX source px outside, -1 per SDF_PX inside (R channel)
  frontend/assets/plate_grey.webp     the plate's texture, edge to edge, for the board's backing
"""
import os
import numpy as np
import cv2
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "art", "ui-src", "bonus_panel.png")
HI = os.path.join(ROOT, "frontend", "assets", "bonus_panel.webp")   # the 2.5x high-res pass of the same art
OUT = os.path.join(ROOT, "frontend", "assets")
SDF_PX = .75      # source px per SDF step: +-127 steps = +-95 source px around the edge
SDF_SCALE = .5    # the field is stored at half the source size (it is smooth; the GPU interpolates)


def plate_mask(a):
    rgb, al = a[..., :3], a[..., 3]
    sat = rgb.max(-1) - rgb.min(-1)
    lum = rgb @ np.array([.3, .59, .11], np.float32)
    grey = (al > .6) & (sat < .12) & (lum > .12)
    # the plate is the big grey area, its black scratches and specks included
    m = cv2.morphologyEx(grey.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    m = (lab == i).astype(np.uint8)
    h, w = m.shape
    ff = np.pad(m, 1); mask = np.zeros((h + 4, w + 4), np.uint8)
    cv2.floodFill(ff, mask, (0, 0), 2)
    m = (ff[1:-1, 1:-1] != 2)
    return cv2.GaussianBlur(m.astype(np.float32), (0, 0), 2.0) > .5


def main():
    a = np.asarray(Image.open(SRC).convert("RGBA")).astype(np.float32) / 255
    H, W = a.shape[:2]
    m = plate_mask(a)
    # signed distance (source px): + outside the plate, - inside
    dout = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
    din = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5)
    sd = np.where(m, -din, dout)
    v = np.clip(128 + sd / SDF_PX, 0, 255)
    small = cv2.resize(v, (round(W * SDF_SCALE), round(H * SDF_SCALE)), interpolation=cv2.INTER_AREA)
    Image.fromarray(small.round().astype(np.uint8), "L").convert("RGB").save(os.path.join(OUT, "bonus_plate_sdf.png"), optimize=True)
    # the grey plate alone, at the high-res pass's size, with a soft 2 px edge
    hi = Image.open(HI).convert("RGBA")
    k = hi.width / W
    mh = cv2.resize(m.astype(np.float32), hi.size, interpolation=cv2.INTER_LINEAR)
    mh = cv2.GaussianBlur(mh, (0, 0), 1.2 * k)
    mh = np.clip((mh - .5) * 3 + .5, 0, 1)
    px = np.asarray(hi).astype(np.float32)
    px[..., 3] = px[..., 3] * mh
    Image.fromarray(px.round().astype(np.uint8), "RGBA").save(os.path.join(OUT, "bonus_plate.webp"), "WEBP", quality=88, alpha_quality=100, method=6)
    # the plate texture edge to edge, for the board's backing: the plate's interior, cropped
    ys, xs = np.nonzero(cv2.erode(m.astype(np.uint8), np.ones((41, 41), np.uint8)))
    box = (int(xs.min() * k), int(ys.min() * k), int(xs.max() * k), int(ys.max() * k))
    tex = hi.crop(box).convert("RGB")
    tex.save(os.path.join(OUT, "plate_grey.webp"), "WEBP", quality=82, method=6)
    print("plate", W, H, "-> sdf", small.shape[::-1], "| plate.webp", hi.size, "| plate_grey", tex.size)


if __name__ == "__main__":
    main()
