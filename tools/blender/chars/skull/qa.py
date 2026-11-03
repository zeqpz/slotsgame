"""SMOKE SKULL - quality check of the rendered clips (run after run.py, with the venv python):
    python tools/blender/chars/skull/qa.py [clip,clip...]
reads  art/blender/chars/skull/renders/<clip>/####.png, <clip>_unlit/, meta.json
writes art/blender/chars/skull/qa/
  <clip>_sheet.jpg   every frame on the game's dark wall
  <clip>_legs.jpg    the legs (knees, cuffs, ankles, laces) at 2x on the frames where they move most
  <clip>_upper.jpg   neck, hood, jaw, elbows, cigar at 2x on the same frames
  <clip>.webp        the clip playing (idle: looped twice, so the seam shows)
  report.txt         per clip: holes / cracks inside the silhouette, hairline seams, start / end against rest, the
                     loop seam, the unlit mask's coverage, the shoe spans"""
import glob, json, os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
BASE = os.path.join(REPO, "art", "blender", "chars", "skull")
REN = os.path.join(BASE, "renders")
OUT = os.path.join(BASE, "qa")
os.makedirs(OUT, exist_ok=True)
WALL = (23, 20, 28, 255)
meta = json.load(open(os.path.join(REN, "meta.json")))
clips = sys.argv[1].split(",") if len(sys.argv) > 1 else list(meta["clips"])
LEGS = (130, 820, 600, 1200)
UPPER = (150, 360, 560, 760)


def load(p):
    return np.asarray(Image.open(p).convert("RGBA")).astype(np.float32) / 255


def on_wall(a):
    im = Image.fromarray((a * 255).astype(np.uint8), "RGBA")
    bg = Image.new("RGBA", im.size, WALL)
    bg.alpha_composite(im)
    return bg.convert("RGB")


def holes(alpha):
    a = alpha > .5
    h = ndimage.binary_fill_holes(a) & ~a
    lab, n = ndimage.label(h)
    cracks, open_ = 0, 0
    if n:
        dist = ndimage.distance_transform_edt(h)
        for i in range(1, n + 1):
            m = lab == i
            if dist[m].max() <= 2.5:
                cracks += int(m.sum())
            else:
                open_ += int(m.sum())
    return cracks, open_


def seams(alpha):
    """see-through hairlines inside the figure: a pixel clearly less opaque than solid pixels on both sides of it"""
    a = alpha
    solid = a > .985
    thin = (a < .9) & (a > .02)
    lr = np.zeros_like(solid); ud = np.zeros_like(solid)
    lr[:, 1:-1] = solid[:, :-2] & solid[:, 2:]
    ud[1:-1, :] = solid[:-2, :] & solid[2:, :]
    return int((thin & (lr | ud)).sum())


rep = []
idle0 = load(os.path.join(REN, "idle", "0001.png"))
for clip in clips:
    fs = sorted(glob.glob(os.path.join(REN, clip, "*.png")))
    us = sorted(glob.glob(os.path.join(REN, clip + "_unlit", "*.png")))
    if not fs:
        continue
    frames = [load(f) for f in fs]
    n = len(frames)
    rep.append(f"== {clip}: {n} frames ({n / 30:.2f} s), unlit {len(us)} frames")
    # sheet
    T = (144, 240)
    cols = 12
    rows = (n + cols - 1) // cols
    sheet = Image.new("RGB", (cols * T[0], rows * T[1]))
    for i, a in enumerate(frames):
        t = on_wall(a).resize(T, Image.LANCZOS)
        ImageDraw.Draw(t).text((3, 2), f"{i:03d}", fill=(255, 220, 0))
        sheet.paste(t, ((i % cols) * T[0], (i // cols) * T[1]))
    sheet.save(os.path.join(OUT, f"{clip}_sheet.jpg"), quality=86)
    # webp
    seq = [on_wall(a).resize((360, 600), Image.LANCZOS) for a in frames] * (2 if meta["clips"][clip].get("loop") else 1)
    seq[0].save(os.path.join(OUT, f"{clip}.webp"), save_all=True, append_images=seq[1:], duration=33, loop=0, quality=80)
    # where the legs move most: frame-to-frame change in the legs box
    lb = LEGS
    mv = [0.0] + [float(np.abs(frames[i][lb[1]:lb[3], lb[0]:lb[2]] - frames[i - 1][lb[1]:lb[3], lb[0]:lb[2]]).mean()) for i in range(1, n)]
    dev = [float(np.abs(frames[i][lb[1]:lb[3], lb[0]:lb[2]] - idle0[lb[1]:lb[3], lb[0]:lb[2]]).mean()) for i in range(n)]
    pick = sorted(set(sorted(range(n), key=lambda i: -dev[i])[:6] + sorted(range(n), key=lambda i: -mv[i])[:3]))
    for nm, box in (("legs", LEGS), ("upper", UPPER)):
        tiles = []
        for i in pick:
            t = on_wall(frames[i][box[1]:box[3], box[0]:box[2]])
            t = t.resize(((box[2] - box[0]) * 2, (box[3] - box[1]) * 2), Image.LANCZOS)
            ImageDraw.Draw(t).text((4, 4), f"{clip} {i:03d}", fill=(255, 220, 0))
            tiles.append(t)
        c3 = 3
        r3 = (len(tiles) + c3 - 1) // c3
        S = Image.new("RGB", (c3 * tiles[0].width, r3 * tiles[0].height))
        for j, t in enumerate(tiles):
            S.paste(t, ((j % c3) * t.width, (j // c3) * t.height))
        S.save(os.path.join(OUT, f"{clip}_{nm}.jpg"), quality=86)
    # holes, cracks, seams
    hs = [holes(a[..., 3]) for a in frames]
    sm = [seams(a[..., 3]) for a in frames]
    bad = [(i, c) for i, (c, o) in enumerate(hs) if c > 0]
    rep.append(f"   cracks (thin holes inside the silhouette): {len(bad)} frames {bad[:12]}")
    rep.append(f"   open holes (wide, e.g. between a lace and the shoe): max {max(o for c, o in hs)} px")
    rep.append(f"   hairline seam pixels: max {max(sm)} (frame {int(np.argmax(sm))}), mean {np.mean(sm):.1f}")
    # start / end against rest (idle frame 1), the loop seam
    d0 = float(np.abs(frames[0] - idle0).mean() * 255)
    d1 = float(np.abs(frames[-1] - idle0).mean() * 255)
    step = [float(np.abs(frames[i] - frames[i - 1]).mean() * 255) for i in range(1, n)]
    if meta["clips"][clip].get("loop"):
        seam = float(np.abs(frames[0] - frames[-1]).mean() * 255)
        rep.append(f"   loop seam (last -> first): {seam:.3f}/255 vs frame steps median {np.median(step):.3f}, max {max(step):.3f}")
        rep.append(f"   cues {meta['clips'][clip].get('cues')}")
    else:
        rep.append(f"   first frame vs rest: {d0:.3f}/255   last frame vs rest: {d1:.3f}/255   (frame steps median {np.median(step):.3f}, max {max(step):.3f} at {int(np.argmax(step)) + 1})")
    if clip == "exit":
        rep.append(f"   last frame max alpha: {frames[-1][..., 3].max():.3f}")
    if clip == "enter":
        rep.append(f"   first frame max alpha: {frames[0][..., 3].max():.3f}")
    if us:
        cov = [float((load(u)[..., 3] > .5).mean() * 100) for u in us[::max(1, len(us) // 6)]]
        rep.append(f"   unlit mask coverage % (sampled): {[round(c, 2) for c in cov]}")
    tr = meta["track"].get(clip)
    if tr:
        rep.append(f"   shoes frame 0: {tr[0]['shoes']}   min bottom over clip: {min(min(s[2] for s in r['shoes']) for r in tr):.1f}")
# the smoke loop (its own clock): the seam, nothing touching the frame's edges, a sheet; and the ember track: a dot on
# the ember in a few frames of every clip (the game puts the smoke's origin there)
sf = sorted(glob.glob(os.path.join(REN, "smoke", "*.png")))
if sf and (len(sys.argv) < 2 or "smoke" in sys.argv[1].split(",")):
    fr = [load(f) for f in sf]
    st = [float(np.abs(fr[i] - fr[i - 1]).mean() * 255) for i in range(1, len(fr))]
    seam = float(np.abs(fr[0] - fr[-1]).mean() * 255)
    edge = max(float(max(a[0, :, 3].max(), a[-1, :, 3].max(), a[:, 0, 3].max(), a[:, -1, 3].max())) for a in fr)
    rep.append(f"== smoke loop: {len(fr)} frames, origin {meta['smoke']['origin']}")
    rep.append(f"   loop seam (last -> first): {seam:.3f}/255 vs frame steps median {np.median(st):.3f}, max {max(st):.3f}")
    rep.append(f"   max alpha on the frame's edges: {edge:.3f}")
    ys_, xs_ = np.nonzero(np.max([a[..., 3] for a in fr], 0) > .02)
    rep.append(f"   plume extent over the loop (px): x {xs_.min()}..{xs_.max()}, y {ys_.min()}..{ys_.max()}")
    T = (144, 240)
    sheet = Image.new("RGB", (12 * T[0], ((len(fr) + 11) // 12) * T[1]))
    for i, a in enumerate(fr):
        t = on_wall(a).resize(T, Image.LANCZOS)
        ImageDraw.Draw(t).text((3, 2), f"{i:03d}", fill=(255, 220, 0))
        sheet.paste(t, ((i % 12) * T[0], (i // 12) * T[1]))
    sheet.save(os.path.join(OUT, "smoke_sheet.jpg"), quality=86)
    seq = [on_wall(a).resize((360, 600), Image.LANCZOS) for a in fr] * 2
    seq[0].save(os.path.join(OUT, "smoke.webp"), save_all=True, append_images=seq[1:], duration=33, loop=0, quality=80)
tiles = []
for clip in clips:
    tr = meta["track"].get(clip)
    if not tr or "ember" not in tr[0]:
        continue
    for i in (0, len(tr) // 3, 2 * len(tr) // 3):
        im = on_wall(load(os.path.join(REN, clip, f"{i + 1:04d}.png")))
        x, y = tr[i]["ember"]
        d = ImageDraw.Draw(im)
        d.ellipse([x - 6, y - 6, x + 6, y + 6], outline=(255, 0, 255), width=3)
        d.text((8, 8), f"{clip} {i}", fill=(255, 220, 0))
        x0, y0 = int(min(max(0, x - 120), 420)), int(min(max(0, y - 160), 900))
        t = im.crop((x0, y0, x0 + 300, y0 + 300))
        ImageDraw.Draw(t).text((4, 4), f"{clip} {i}", fill=(255, 220, 0))
        tiles.append(t)
if tiles:
    S = Image.new("RGB", (300 * 6, 300 * ((len(tiles) + 5) // 6)))
    for j, t in enumerate(tiles):
        S.paste(t, ((j % 6) * 300, (j // 6) * 300))
    S.save(os.path.join(OUT, "ember_track.jpg"), quality=86)
open(os.path.join(OUT, "report.txt"), "w").write("\n".join(rep) + "\n")
print("\n".join(rep))
