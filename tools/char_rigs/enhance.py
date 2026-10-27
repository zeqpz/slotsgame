"""SUPERSEDED (2026-10-27) by tools/char_rigs/v2/build_v2.py: the characters were redrawn and re-rigged
(v2). This v1 pass is kept for reference; it refuses to overwrite frontend/assets/spine unless --v1 is given.

Character rig pass: art/characters-src/<rig>.json (the rigs as delivered) -> frontend/assets/spine/.

  python tools/char_rigs/enhance.py [--out <dir>] [--only smukiez|smoke-skull]

Needs PIL, numpy, scipy and OpenCV (smukiez-slot/.venv has them). Runs in about two minutes.
Real-ESRGAN (.tools/realesrgan) is only needed the first time: its x4 faces are cached as
source art in art/characters-src/hires/.

The pass, in order (each module's docstring says why):
- rig_boy.py - SMUKIEZ joints: thighs hang from the torso, leg IK stretches, knee helper bones
  (half-angle transform constraints), both trouser legs rebuilt as contour meshes with smooth
  thigh->knee->shin weights; leg_right's inner edge redrawn; the front sneaker's see-through
  stitching filled; socks behind the shoes (the gap between cuff and tongue); the left arm one layer under its own sleeve slot (sleeve_left); the cash
  hands' wrists rebuilt onto the forearm.
- rig_skull.py - SMOKE SKULL re-cut: the body as hoodie / two trouser legs / two rigid shoes cut
  along the drawing's outlines, hidden parts painted underneath, an even sticker outline per
  part, a crotch backing and a hood backing that bridges jaw and hood; faces at 1.45x from
  Real-ESRGAN on their own page.
- boy_anims / skull_anims (below) - the re-authored idles and the reactions played bigger.
- motion.py - overlap, follow-through, squash and settle on every reaction; knees kept within
  60 degrees; the skull's shoes move as one; the faces relax to idle under a head take before
  each reaction ends; the skull's smoke trails the head (smoke_lag bone); every clip re-keyed
  as sparse eased beziers (lengths and names unchanged); the walk-on/off part fades removed
  (the game fades the whole canvas instead).
- atlaskit.write_pages - every page as WebP (quality 95, lossless alpha) plus the atlas.
"""
import json, os, sys, copy, argparse
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, "art", "characters-src")
DEFAULT_OUT = os.path.join(ROOT, "frontend", "assets", "spine")
import atlaskit as ak
import rig_boy
import rig_skull
import motion

REACT_GAIN = 1.7
SOFT = (.37, 0, .63, 1)


def tl(keys, ease=SOFT):
    out = []
    mid_seam = len(keys) >= 3 and (keys[0][1] - keys[-2][1]) * (keys[1][1] - keys[0][1]) > 0
    for i, (t, v) in enumerate(keys):
        k = {"time": round(t, 4), "value": round(v, 4)} if t else {"value": round(v, 4)}
        if i + 1 < len(keys):
            t1, v1 = keys[i + 1]
            e = ease
            if mid_seam and i == 0: e = (.3, .45, .58, 1)
            if mid_seam and i == len(keys) - 2: e = (.42, 0, .7, .55)
            x1, y1, x2, y2 = e
            k["curve"] = [round(t + x1 * (t1 - t), 4), round(v + y1 * (v1 - v), 4), round(t + x2 * (t1 - t), 4), round(v + y2 * (v1 - v), 4)]
        out.append(k)
    return out


def wave(dur, a, b, period, phase=0.0):
    import math
    n = int(round(dur / (period / 2)))
    pts = sorted(((i * period / 2 - phase) % dur, a if i % 2 == 0 else b) for i in range(n))
    v0 = (a + b) / 2 + (a - b) / 2 * math.cos(2 * math.pi * (phase / period))
    return [(0, v0)] + [p for p in pts if 1e-3 < p[0] < dur - 1e-3] + [(dur, v0)]


def amplify(anim, gain, skip=(), skip_kinds=None):
    for bone, tls in anim.get("bones", {}).items():
        if bone in skip:
            continue
        for kind, keys in tls.items():
            if skip_kinds and kind in skip_kinds.get(bone, ()):
                continue
            for k in keys:
                if kind.startswith("scale"):
                    for f in ("value", "x", "y"):
                        if f in k: k[f] = round(1 + (k[f] - 1) * gain, 5)
                else:
                    for f in ("value", "x", "y"):
                        if f in k: k[f] = round(k[f] * gain, 4)
                c = k.get("curve")
                if isinstance(c, list):
                    for i in range(1, len(c), 2):
                        c[i] = round(1 + (c[i] - 1) * gain, 5) if kind.startswith("scale") else round(c[i] * gain, 4)


def boy_anims(j):
    a = j["animations"]["idle"]; D = 3.2
    bones = a.setdefault("bones", {})
    bones["body"] = {"translatex": tl(wave(D, -6, 6, 3.2)), "translatey": tl(wave(D, 0, -9, 1.6))}
    bones["torso"] = {"rotate": tl(wave(D, 1.4, -1.4, 3.2, phase=.12)), "translatey": tl(wave(D, 0, 3, 1.6, phase=-.18))}
    bones["head"] = {"rotate": tl([(0, -2), (.9, 2.4), (1.7, -1.4), (2.5, 2), (3.2, -2)]), "translatey": tl(wave(D, 0, -3, 1.6, phase=-.3))}
    bones["grip"] = {"rotate": tl(wave(D, -1.4, 2.4, 3.2, phase=-.2)), "translatey": tl(wave(D, 0, 4, 1.6, phase=-.25))}
    for i in range(6):
        bones[f"bill_{i}"] = {"rotate": tl(wave(D, -1.6 - i * .25, 1.6 + i * .25, 1.6, phase=-.08 * i))}
    for name in ("anticipation", "win", "big_win", "lose", "cash_show"):
        amplify(j["animations"][name], REACT_GAIN, skip=("root",), skip_kinds={"torso": ("translate", "translatex", "translatey")})


NECK = {"w": 340, "h": 190, "centre": (30, 790), "rgb": (26, 26, 30)}


def neck_fill(j):
    """The hood behind the skull was never painted: under the jaw the wall showed through the
    figure (and a turn of the head opened it wider). A dark hood-interior backing sits behind
    every other part, hung on the torso, so the gap reads as the inside of the hood."""
    from PIL import ImageDraw, ImageFilter
    W, H = NECK["w"], NECK["h"]; ss = 4
    im = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([ss * 6, ss * 6, (W - 6) * ss, (H - 6) * ss], fill=NECK["rgb"] + (255,))
    im = im.filter(ImageFilter.GaussianBlur(ss * 2)).resize((W, H), Image.LANCZOS)
    B = {b["name"]: b for b in j["bones"]}
    def world(n):
        b = B[n]; x, y = b.get("x", 0), b.get("y", 0)
        if b.get("parent"):
            px, py = world(b["parent"]); x, y = x + px, y + py
        return x, y
    tx, ty = world("torso")
    cx, cy = NECK["centre"]
    j["slots"].insert(0, {"name": "neck_fill", "bone": "torso", "attachment": "neck_fill"})
    j["skins"][0]["attachments"]["neck_fill"] = {"neck_fill": {"x": cx - tx, "y": cy - ty, "width": W, "height": H}}
    return im


def skull_anims(j):
    a = j["animations"]["idle"]; D = 4.0
    bones = a.setdefault("bones", {})
    bones["torso"] = {"rotate": tl(wave(D, -2, 2, 4.0)), "translatey": tl(wave(D, 0, 7, 2.0)), "translatex": tl(wave(D, -3, 3, 4.0, phase=.2))}
    bones["head"] = {"rotate": tl([(0, 2.2), (1.1, -2.6), (2.2, 1.8), (3.2, -1.8), (4, 2.2)]), "translatey": tl(wave(D, 0, 2, 2.0, phase=-.25))}
    bones["beanie"] = {"rotate": tl([(0, 1.2), (1.35, -2), (2.45, 1.5), (3.45, -1.5), (4, 1.2)])}
    bones["jaw"] = {"rotate": tl([(0, 0), (.35, 2.6), (.75, 0), (2.2, 0), (2.55, 3.1), (2.95, 0), (4, 0)])}
    bones["arm_left"] = {"rotate": tl(wave(D, -2, 2, 4.0, phase=.3))}
    bones["arm_right"] = {"rotate": tl(wave(D, 2, -2, 4.0, phase=.1))}
    bones["pocket"] = {"translatey": tl(wave(D, 0, 3, 2.0, phase=-.15))}
    keep = ("smoke_base", "smoke_mid", "smoke_tip", "wisp_a", "wisp_b", "ember", "cigar", "ash_cap", "ash_1", "ash_2", "ash_3", "ash_4", "root", "jaw")
    for name in ("anticipation", "win", "big_win", "lose"):
        amplify(j["animations"][name], REACT_GAIN, skip=keep)


def load(name):
    j = json.load(open(os.path.join(SRC, name + ".json"), encoding="utf-8"))
    atlas = ak.Atlas(open(os.path.join(SRC, name + ".atlas"), encoding="utf-8").read())
    pages = {p["name"]: Image.open(os.path.join(SRC, p["name"])).convert("RGBA") for p in atlas.pages}
    return j, atlas, pages


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--only", default=None)
    ap.add_argument("--v1", action="store_true", help="really overwrite the game's rigs with the v1 pass")
    args = ap.parse_args()
    if os.path.abspath(args.out) == os.path.abspath(DEFAULT_OUT) and not args.v1:
        sys.exit("enhance.py is the v1 pass: the game's rigs are v2 now (tools/char_rigs/v2/build_v2.py). "
                 "Pass --out <dir> to build v1 elsewhere, or --v1 to overwrite frontend/assets/spine anyway.")
    for name in ("smukiez", "smoke-skull"):
        if args.only and name != args.only: continue
        out_dir = os.path.join(args.out, name)
        j, atlas, pages = load(name)
        if name == "smukiez":
            stats = rig_boy.fix(j, atlas, pages)
            boy_anims(j)
            lifts = {r: motion.boy_reaction(j, r) for r in ("anticipation", "win", "big_win", "lose", "cash_show", "cash_count")}
            for r in ("cash_toss", "cash_toss_alt_1", "cash_toss_alt_2", "cash_toss_alt_3"):
                motion.boy_compact(j, r)
            motion.boy_compact(j, "idle", loop=True)
            motion.strip_fades(j)
            for r in ("enter", "exit"):
                motion.boy_compact(j, r)
            print("boy socks follow their shoes in", rig_boy.finish_socks(j), "clip timelines")   # last: the clips are final
            print("boy legs (verts, tris):", stats, "hips lifted for the knees:", lifts)
        else:
            neck = neck_fill(j)
            pages, stats, _ = rig_skull.fix(j, atlas, pages, {"neck_fill": neck})
            skull_anims(j)
            motion.add_smoke_lag(j)
            for r in ("anticipation", "win", "big_win", "lose"):
                motion.skull_reaction(j, r)
            motion.skull_compact(j, "idle", loop=True, smoke=True, feet=True)
            for r in ("smoke_loop", "ember_loop"):
                motion.skull_compact(j, r, loop=True)
            motion.skull_compact(j, "ash_break", smoke=True, take=True)
            motion.strip_fades(j)
            for r in ("enter", "exit"):
                motion.skull_compact(j, r, smoke=True)
            print("skull parts (verts):", stats)
        ak.write_pages(out_dir, name, atlas, pages)
        with open(os.path.join(out_dir, name + ".json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(j, fh, separators=(",", ":"))
        print(f"{name}: -> {out_dir}")


if __name__ == "__main__":
    main()
