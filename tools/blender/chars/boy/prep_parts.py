"""SMUKIEZ (the boy): the cutout parts Blender builds the rig from.

Source: art/blender/chars/boy/src/ - the cut of the v2 character pipeline (tools/char_rigs/v2: boy_parts.py,
boy_bills.py), every part complete on the master's 1024 x 1536 frame, hidden areas filled; the master label map;
the aligned edits (the figure with pieces taken away). This script cleans each part for rigid cutout joints and
writes art/blender/chars/boy/parts/<part>.png (cropped) + parts.json (box in master px, draw order, the bill fan).

Run with the project venv python (numpy, scipy, PIL, cv2):
  ../smukiez-slot/.venv/Scripts/python.exe tools/blender/chars/boy/prep_parts.py
"""
import json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
BOY = os.path.join(ROOT, "art", "blender", "chars", "boy")
SRC = os.path.join(BOY, "src")
OUT = os.path.join(BOY, "parts")
W, H = 1024, 1536

# back -> front (the shipped rig's slot order); the head is one slot with a face per expression
ORDER = ["neck", "arm_r_upper", "arm_r_fore", "pelvis", "shoe_l", "shoe_r", "shin_l", "shin_r", "thigh_l",
         "thigh_r", "torso", "arm_l_upper", "head", "beanie", "arm_l_fore", "bills", "hand_l", "hand_r"]
FACES = ["idle", "anticipation", "win", "big_win", "lose", "cash_show", "cash_count"]
NB = 6


def load(name):
    return np.asarray(Image.open(os.path.join(SRC, "parts", name + ".png")).convert("RGBA")).astype(np.float32) / 255.


def aligned(name):
    return np.asarray(Image.open(os.path.join(SRC, "aligned", name + ".png")).convert("RGBA")).astype(np.float32) / 255.


def master():
    return np.asarray(Image.open(os.path.join(ROOT, "art", "characters-src", "v2", "boy", "master.webp")).convert("RGBA")).astype(np.float32) / 255.


def labels():
    lab = np.load(os.path.join(SRC, "seg", "boy_labels.npy"))
    names = json.load(open(os.path.join(SRC, "seg", "boy_names.json")))
    return lab, names


def save(img, name, pad=4):
    a = img[..., 3]
    ys, xs = np.nonzero(a > 1 / 255.)
    x0, y0 = max(0, xs.min() - pad), max(0, ys.min() - pad)
    x1, y1 = min(img.shape[1], xs.max() + 1 + pad), min(img.shape[0], ys.max() + 1 + pad)
    crop = img[y0:y1, x0:x1]
    out = (crop * 255 + .5).clip(0, 255).astype(np.uint8)
    out[out[..., 3] == 0, :3] = 0
    Image.fromarray(out, "RGBA").save(os.path.join(OUT, name + ".png"))
    return [int(x0), int(y0), int(x1), int(y1)]


def main():
    os.makedirs(OUT, exist_ok=True)
    import fixes                                  # the per-joint clean-up (tools/blender/chars/boy/fixes.py)
    P = {}
    for n in ORDER:
        if n in ("bills", "head"):
            continue
        P[n] = load(n)
    heads = {f: load("head_" + f) for f in FACES}
    fixes.apply(P, heads, master(), labels(), aligned)
    spec = {"size": [W, H], "parts": [], "faces": FACES}
    for d, n in enumerate(ORDER):
        if n == "bills":
            spec["parts"].append({"name": n, "draw": d})
            continue
        if n == "head":
            for f in FACES:
                spec.setdefault("head_boxes", {})[f] = save(heads[f], "head_" + f)
            spec["parts"].append({"name": n, "draw": d, "box": spec["head_boxes"]["idle"]})
            continue
        spec["parts"].append({"name": n, "draw": d, "box": save(P[n], n)})
    # the cash: one bill, fanned
    bill = np.asarray(Image.open(os.path.join(SRC, "parts", "bill.png")).convert("RGBA"))
    Image.fromarray(bill, "RGBA").save(os.path.join(OUT, "bill.png"))
    spec["fan"] = json.load(open(os.path.join(SRC, "parts", "fan.json")))
    spec["bill_size"] = [bill.shape[1], bill.shape[0]]
    # the standing figure at rest (every part, the idle face, the fan's bills): its box
    comp = np.zeros((H, W), np.float32)
    for n, img in list(P.items()) + [("head", heads["idle"])]:
        comp = np.maximum(comp, img[..., 3])
    ys, xs = np.nonzero(comp > .5)
    spec["rest_box"] = [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]
    json.dump(spec, open(os.path.join(OUT, "parts.json"), "w"), indent=1)
    print("parts ->", OUT, "rest box", spec["rest_box"])


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    main()
