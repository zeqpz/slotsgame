"""Character rig pass: art/characters-src/<rig>.json (the rigs as delivered) -> frontend/assets/spine/.

  python tools/char_rigs/enhance.py

What it changes, and why:
- SMUKIEZ (the boy): his legs are two-bone IK chains with only 1-2 units of slack between hip
  and planted foot, so whenever a clip lifts his hips (win, big win) the IK could not reach and
  his shoe came off his trouser leg. The leg IK now stretches ("stretch": true): the legs
  lengthen a touch instead of letting go of the feet.
- Both idles barely moved (the boy swayed 2 units on a 1,622-unit figure, the skull leaned
  0.7 degrees) and read as frozen. They are re-authored as layered, eased loops: weight shift,
  breathing that travels up the body a beat late, head and hat follow-through, the bills
  fluttering in the boy's hand, the skull drawing on his cigar. Slot timelines (faces, hands)
  and the skull's leg/foot work are kept as delivered.
- The reactions (anticipation, win, big win, lose, cash show) keep their timing and are played
  bigger (REACT_GAIN) - on screen a big-win hop was about 2% of the figure's height.
- Written compact (no indentation): the boy's skeleton drops from 4.9 MB of whitespace-padded
  JSON to a fraction of that, which the game downloads before the first spin.
"""
import json, os, copy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, "art", "characters-src")
OUT = {"smukiez": os.path.join(ROOT, "frontend", "assets", "spine", "smukiez", "smukiez.json"),
       "smoke-skull": os.path.join(ROOT, "frontend", "assets", "spine", "smoke-skull", "smoke-skull.json")}
REACT_GAIN = 1.7
SOFT = (.37, 0, .63, 1)            # ease in and out: every key here is a turning point


def tl(keys, ease=SOFT):
    """[(t, v), ...] -> a Spine 4.2 single-value timeline with a bezier on every segment.
    Turning points ease in and out; a loop whose seam falls mid-motion leaves the seam at
    speed (ease-out into the first turn, ease-in out of the last) so it never hitches there."""
    out = []
    mid_seam = len(keys) >= 3 and (keys[0][1] - keys[-2][1]) * (keys[1][1] - keys[0][1]) > 0
    for i, (t, v) in enumerate(keys):
        k = {"time": round(t, 4), "value": round(v, 4)} if t else {"value": round(v, 4)}
        if i + 1 < len(keys):
            t1, v1 = keys[i + 1]
            e = ease
            if mid_seam and i == 0: e = (.3, .45, .58, 1)          # leaving the seam at speed
            if mid_seam and i == len(keys) - 2: e = (.42, 0, .7, .55)   # arriving at the seam at speed
            x1, y1, x2, y2 = e
            k["curve"] = [round(t + x1 * (t1 - t), 4), round(v + y1 * (v1 - v), 4), round(t + x2 * (t1 - t), 4), round(v + y2 * (v1 - v), 4)]
        out.append(k)
    return out


def wave(dur, a, b, period, phase=0.0):
    """A loop between a and b with the given period (dur must be a whole number of periods),
    starting `phase` seconds into the cycle - turning points only, so it eases like a sine."""
    n = int(round(dur / (period / 2)))
    keys = []
    # turning points at phase-shifted half periods, wrapped into [0, dur]
    pts = sorted(((i * period / 2 - phase) % dur, a if i % 2 == 0 else b) for i in range(n))
    # the value at t=0 / t=dur: interpolate on the cycle (cosine) so the loop closes exactly
    import math
    v0 = (a + b) / 2 + (a - b) / 2 * math.cos(2 * math.pi * (phase / period))
    keys = [(0, v0)] + [p for p in pts if 1e-3 < p[0] < dur - 1e-3] + [(dur, v0)]
    return keys


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
                if isinstance(c, list):   # bezier handles carry absolute values: scale those too
                    for i in range(1, len(c), 2):
                        c[i] = round(1 + (c[i] - 1) * gain, 5) if kind.startswith("scale") else round(c[i] * gain, 4)


def boy(j):
    for ik in j.get("ik", []):
        if ik["name"] in ("leg_left", "leg_right"):
            ik["stretch"] = True
    # The trouser legs hung from the hips (body) while the shirt rides the torso, so every lean
    # or lift of the torso pulled the hem off the waistband - a gap at the waist. The thighs
    # now hang from the torso itself: the waist travels with the shirt, and the leg IK (which
    # now stretches) keeps the shoes planted.
    B = {b["name"]: b for b in j["bones"]}
    t = B["torso"]
    for leg in ("thigh_left", "thigh_right"):
        b = B[leg]
        if b.get("parent") == "body":
            b["parent"] = "torso"
            b["x"] = round(b.get("x", 0) - t.get("x", 0), 3)
            b["y"] = round(b.get("y", 0) - t.get("y", 0), 3)
    a = j["animations"]["idle"]; D = 3.2
    bones = a.setdefault("bones", {})
    bones["body"] = {"translatex": tl(wave(D, -6, 6, 3.2)), "translatey": tl(wave(D, 0, -9, 1.6))}
    bones["torso"] = {"rotate": tl(wave(D, 1.4, -1.4, 3.2, phase=.12)), "translatey": tl(wave(D, 0, 3, 1.6, phase=-.18))}
    bones["head"] = {"rotate": tl([(0, -2), (.9, 2.4), (1.7, -1.4), (2.5, 2), (3.2, -2)]), "translatey": tl(wave(D, 0, -3, 1.6, phase=-.3))}
    bones["grip"] = {"rotate": tl(wave(D, -1.4, 2.4, 3.2, phase=-.2)), "translatey": tl(wave(D, 0, 4, 1.6, phase=-.25))}
    for i in range(6):   # the fan of bills ruffles, each a beat behind the next
        bones[f"bill_{i}"] = {"rotate": tl(wave(D, -1.6 - i * .25, 1.6 + i * .25, 1.6, phase=-.08 * i))}
    for name in ("anticipation", "win", "big_win", "lose", "cash_show"):
        # the torso's own lift stays as delivered: amplified, it would stretch the legs too far
        amplify(j["animations"][name], REACT_GAIN, skip=("root",), skip_kinds={"torso": ("translate", "translatex", "translatey")})


NECK = {"w": 340, "h": 190, "at": (8, 1560), "centre": (30, 790), "rgb": (26, 26, 30)}


def neck_fill(j):
    """The hood behind the skull was never painted: under the jaw the wall showed through the
    figure (and a turn of the head opened it wider). A dark hood-interior backing now sits behind
    every other part, hung on the torso, so the gap reads as the inside of the hood."""
    from PIL import Image, ImageDraw, ImageFilter
    W, H = NECK["w"], NECK["h"]; ss = 4
    im = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([ss * 6, ss * 6, (W - 6) * ss, (H - 6) * ss], fill=NECK["rgb"] + (255,))
    im = im.filter(ImageFilter.GaussianBlur(ss * 2)).resize((W, H), Image.LANCZOS)
    page = Image.open(os.path.join(SRC, "smoke-skull.png")).convert("RGBA")
    page.paste(im, NECK["at"], im)
    atlas = open(os.path.join(SRC, "smoke-skull.atlas"), encoding="utf-8").read().replace("\r\n", "\n").rstrip("\n")
    atlas += (f"\nneck_fill\n  rotate: false\n  xy: {NECK['at'][0]}, {NECK['at'][1]}\n  size: {W}, {H}\n"
              f"  orig: {W}, {H}\n  offset: 0, 0\n  index: -1\n")
    write_pages("smoke-skull", atlas, {"smoke-skull.png": page})
    # bone-local placement: the torso bone's setup world position, from the bone chain
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


def write_pages(name, atlas, images=None):
    """Write a rig's atlas pages as WebP (quality 95, lossless alpha: under one level of average
    colour error, about a fifth of the PNG's bytes) and point the atlas at them. Pages not
    passed in come from the source PNGs."""
    from PIL import Image
    out_dir = os.path.dirname(OUT[name])
    lines = atlas.replace("\r\n", "\n").split("\n")
    for i, line in enumerate(lines):
        if line.strip().lower().endswith(".png") and ":" not in line:
            src = line.strip()
            img = (images or {}).get(src) or Image.open(os.path.join(SRC, src)).convert("RGBA")
            dst = src[:-4] + ".webp"
            img.save(os.path.join(out_dir, dst), "WEBP", quality=95, method=6, alpha_quality=100)
            stale = os.path.join(out_dir, src)
            if os.path.exists(stale):
                os.remove(stale)          # the page now ships as WebP only
            lines[i] = dst
    with open(os.path.join(out_dir, name + ".atlas"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines).rstrip("\n") + "\n")


def skull(j):
    neck_fill(j)
    a = j["animations"]["idle"]; D = 4.0
    bones = a.setdefault("bones", {})
    bones["torso"] = {"rotate": tl(wave(D, -2, 2, 4.0)), "translatey": tl(wave(D, 0, 7, 2.0)), "translatex": tl(wave(D, -3, 3, 4.0, phase=.2))}
    bones["head"] = {"rotate": tl([(0, 2.2), (1.1, -2.6), (2.2, 1.8), (3.2, -1.8), (4, 2.2)]), "translatey": tl(wave(D, 0, 2, 2.0, phase=-.25))}
    bones["beanie"] = {"rotate": tl([(0, 1.2), (1.35, -2), (2.45, 1.5), (3.45, -1.5), (4, 1.2)])}   # lags the head
    bones["jaw"] = {"rotate": tl([(0, 0), (.35, 2.6), (.75, 0), (2.2, 0), (2.55, 3.1), (2.95, 0), (4, 0)])}   # two draws on the cigar
    bones["arm_left"] = {"rotate": tl(wave(D, -2, 2, 4.0, phase=.3))}
    bones["arm_right"] = {"rotate": tl(wave(D, 2, -2, 4.0, phase=.1))}
    bones["pocket"] = {"translatey": tl(wave(D, 0, 3, 2.0, phase=-.15))}
    keep = ("smoke_base", "smoke_mid", "smoke_tip", "wisp_a", "wisp_b", "ember", "cigar", "ash_cap", "ash_1", "ash_2", "ash_3", "ash_4", "root",
            "jaw")   # the jaw already opens as wide as the face art allows
    for name in ("anticipation", "win", "big_win", "lose"):
        amplify(j["animations"][name], REACT_GAIN, skip=keep)


def main():
    for name, fix in (("smukiez", boy), ("smoke-skull", skull)):
        j = json.load(open(os.path.join(SRC, name + ".json"), encoding="utf-8"))
        fix(j)
        if name == "smukiez":
            write_pages(name, open(os.path.join(SRC, "smukiez.atlas"), encoding="utf-8").read())
        with open(OUT[name], "w", encoding="utf-8", newline="\n") as fh:
            json.dump(j, fh, separators=(",", ":"))
        print(f"{name}: {os.path.getsize(os.path.join(SRC, name + '.json')) // 1024} KB -> {os.path.getsize(OUT[name]) // 1024} KB")


if __name__ == "__main__":
    main()
