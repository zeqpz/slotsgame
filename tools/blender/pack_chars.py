"""Pack a character's Blender renders (art/blender/chars/<char>/renders: <clip>/####.png beauty frames,
<clip>_unlit/####.png the parts the wall's neon leaves alone, meta.json - see tools/blender/chars/<char>/) into what
the game plays: frontend/assets/chars/<char>/.
A figure is far bigger on screen than a symbol, so its frames are not laid out in sheets - every decoded frame of
both figures at once would be over a gigabyte. Each clip is one file of its frames back to back, each frame its own
small WebP cropped to the clip's box; the game keeps the files as they are and decodes only the frames about to show.
  <dd>/<clip>.bin         the beauty frames at density dd (d5 = half the master's size, d7, d10 = full)
  unlit/<clip>.bin        the unlit mask's frames, at half density (a soft rim light needs no more)
  <dd>/smoke.bin          a figure's own looping smoke (meta "smoke": the skull's cigar), packed apart from the clips
                          so it never restarts when a clip changes: the game lays its emitter (origin) on the
                          ember each frame (track[clip][i].ember)
  manifest.json           sizes, rest height, ground, each clip's frames / loop / cues / box, each file's frame
                          offsets, and the per-frame shoe spans the foot shadows follow
usage: python tools/blender/pack_chars.py <char,char..|all> [densities, default .5,.7,1]"""
import glob, io, json, os, sys
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "art", "blender", "chars")
OUT = os.path.join(ROOT, "frontend", "assets", "chars")
UNLIT_DENSITY = .5
QUALITY = 84


def dname(d):
    """A density's folder name: tenths (d5, d7, d10) when exact, else hundredths (d25, d35)."""
    return f"d{round(d * 10)}" if abs(d * 10 - round(d * 10)) < 1e-6 else f"d{round(d * 100)}"


def box_of(files, pad=4):
    """The union of everything a clip's frames show, in master px (x0, y0, x1, y1)."""
    seen = None
    for f in files:
        a = np.asarray(Image.open(f).getchannel("A")) > 2
        seen = a if seen is None else seen | a
    if seen is None or not seen.any():
        return None
    ys, xs = np.nonzero(seen)
    H, W = seen.shape
    return max(0, xs.min() - pad), max(0, ys.min() - pad), min(W, xs.max() + pad + 1), min(H, ys.max() + pad + 1)


def resize(im, size):
    """Shrink with the colour premultiplied, so see-through edges never pick up dark fringes."""
    return im.convert("RGBa").resize(size, Image.LANCZOS).convert("RGBA")


def encode(files, box, d, path, mask=False):
    """The frames, cropped to box and scaled by d, one WebP each, back to back in one file -> their offsets."""
    x0, y0, x1, y1 = box
    size = (max(2, round((x1 - x0) * d)), max(2, round((y1 - y0) * d)))
    offsets, blob = [0], bytearray()
    for f in files:
        im = Image.open(f).convert("RGBA").crop(box)
        if mask:                                         # white, its alpha the mask: compresses to almost nothing
            a = im.getchannel("A")
            im = Image.merge("RGBA", (a.point(lambda v: 255),) * 3 + (a,))
        im = resize(im, size)
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=QUALITY if not mask else 70, method=4, alpha_quality=100 if not mask else 80)
        blob += buf.getvalue()
        offsets.append(len(blob))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(blob)
    return {"w": size[0], "h": size[1], "bytes": len(blob), "offsets": offsets}


def rest_mask(char):
    """The rest pose's silhouette (the idle's first frame), a quarter size: what every frame is compared with."""
    f = sorted(glob.glob(os.path.join(SRC, char, "renders", "idle", "*.png")))[0]
    im = Image.open(f).getchannel("A")
    return np.asarray(im.resize((im.width // 4, im.height // 4))).astype(np.float32) / 255


def away_from_rest(char, files):
    """For each frame, how far its silhouette is from the rest pose's (mean |alpha difference|): a frame near 0 is
    the rest pose, where a clip can be cut into another without a jump."""
    rest = rest_mask(char)
    out = []
    for f in files:
        im = Image.open(f).getchannel("A")
        a = np.asarray(im.resize((im.width // 4, im.height // 4))).astype(np.float32) / 255
        out.append(float(np.abs(a - rest).mean()))
    return out


def pack_clip(args):
    char, clip, densities = args
    ren = os.path.join(SRC, char, "renders")
    files = sorted(glob.glob(os.path.join(ren, clip, "*.png")))
    unlit = [] if clip == "smoke" else sorted(glob.glob(os.path.join(ren, clip + "_unlit", "*.png")))
    box = box_of(files)
    out = {"box": [int(v) for v in box], "files": {}, "away": [] if clip == "smoke" else away_from_rest(char, files)}
    for d in densities:
        dd = dname(d)
        out["files"][dd] = encode(files, box, d, os.path.join(OUT, char, dd, clip + ".bin"))
    if unlit:
        if len(unlit) != len(files):
            raise SystemExit(f"{char} {clip}: {len(unlit)} unlit frames for {len(files)} frames")
        ubox = box_of(unlit) or box
        out["unlit"] = dict(encode(unlit, ubox, UNLIT_DENSITY, os.path.join(OUT, char, "unlit", clip + ".bin"), mask=True),
                            box=[int(v) for v in ubox], density=UNLIT_DENSITY)
    return char, clip, out


if __name__ == "__main__":
    chars = sorted(os.listdir(SRC)) if sys.argv[1] == "all" else sys.argv[1].split(",")
    densities = [float(v) for v in (sys.argv[2].split(",") if len(sys.argv) > 2 else (".5", ".7", "1"))]
    metas = {c: json.load(open(os.path.join(SRC, c, "renders", "meta.json"))) for c in chars}
    jobs = [(c, clip, densities) for c in chars for clip in list(metas[c]["clips"]) + (["smoke"] if "smoke" in metas[c] else [])]
    packed = {}
    with ProcessPoolExecutor(max_workers=min(8, len(jobs))) as ex:
        for char, clip, out in ex.map(pack_clip, jobs):
            packed.setdefault(char, {})[clip] = out
            sizes = " | ".join(f"{dd} {v['bytes'] / 1e6:.1f} MB" for dd, v in out["files"].items())
            print(f"{char} {clip}: {len(out['files'][next(iter(out['files']))]['offsets']) - 1} frames | {sizes}", flush=True)
    for char in chars:
        m = metas[char]
        clips = {}
        # every clip's cues: the frames back at the rest pose, as near to it as the idle's own (Blender-measured) cues
        # are - so the player can leave a long clip (an idle break) for a reaction without a jump
        idle_away = packed[char]["idle"]["away"]
        near = max([idle_away[i] for i in m["clips"]["idle"].get("cues", []) if i < len(idle_away)] or [0.002]) * 1.15
        for clip, info in m["clips"].items():
            p = packed[char][clip]
            cues = info.get("cues") or [i for i, v in enumerate(p["away"]) if v <= near]
            clips[clip] = {"frames": info["frames"], "loop": bool(info.get("loop")), "cues": cues,
                           "box": p["box"], "files": p["files"], **({"unlit": p["unlit"]} if "unlit" in p else {})}
        man = {"fps": m["fps"], "size": m["size"], "rest_height": m["rest_height_px"], "ground_y": m["ground_y"],
               "densities": [dname(d) for d in densities], "density_of": {dname(d): d for d in densities}, "clips": clips, "track": m.get("track", {})}
        if "smoke" in m:
            p = packed[char]["smoke"]
            man["smoke"] = {"frames": m["smoke"]["frames"], "origin": m["smoke"]["origin"], "box": p["box"], "files": p["files"]}
        path = os.path.join(OUT, char, "manifest.json")
        json.dump(man, open(path, "w"), separators=(",", ":"))
        total = sum(v["bytes"] for c in list(clips.values()) + ([man["smoke"]] if "smoke" in man else []) for v in c["files"].values())
        print("->", path, f"| {len(clips)} clips | {total / 1e6:.1f} MB all densities")
