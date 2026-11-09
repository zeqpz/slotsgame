"""The rig against Blender: parity.mjs's shots (art/blender/chars/<char>/qa/rig/<dd>/<clip>/####.png, the game's rig
player over the whole frame at density dd) vs the renders (art/blender/chars/<char>/renders/<clip>/####.png, scaled to
dd as the frames used to be packed: premultiplied Lanczos). Per clip: PSNR over a dark wall colour (mean, min, worst
frame); a sheet per clip: render | rig | |diff| x4 | 3x zooms where the clip moves most and where it differs most.
  python tools/blender/chars/rig/parity.py <char> <dd>
-> art/blender/chars/<char>/qa/rig/<char>_<dd>_<clip>.png and <char>_<dd>_report.json
The rig blends in linear light like Eevee and samples its atlas a little finer than the picture; at the boy's d35 it
measured ~33 dB against the renders on every clip (2026-11-09) - the shipped WebP frames themselves were ~34.5 dB."""
import glob, json, os, sys
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
char, dd = sys.argv[1:3]
QA = os.path.join(ROOT, "art", "blender", "chars", char, "qa", "rig")
REN = os.path.join(ROOT, "art", "blender", "chars", char, "renders")
man = json.load(open(os.path.join(ROOT, "frontend", "assets", "chars", char, "manifest.json")))
BG = np.array([38, 34, 44], np.float32)
comp = lambda p: p[..., :3] + BG * (1 - p[..., 3:4] / 255)          # premultiplied over the wall colour
psnr = lambda a, b: 10 * np.log10(255 ** 2 / max(((a - b) ** 2).mean(), 1e-9))


def window(score, s):
    H, W = score.shape; s = min(s, H, W)
    I = np.pad(score.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    t = I[s:, s:] - I[:-s, s:] - I[s:, :-s] + I[:-s, :-s]
    y, x = np.unravel_index(np.argmax(t), t.shape)
    return int(x), int(y), int(x) + s, int(y) + s


rep = {}
for clip in man["clips"]:
    shots = sorted(glob.glob(os.path.join(QA, dd, clip, "*.png")))
    if not shots:
        continue
    rows = []
    for fp in shots:
        i = int(os.path.basename(fp)[:4])
        r = np.asarray(Image.open(fp)).astype(np.float32)
        b = Image.open(os.path.join(REN, clip, f"{i + 1:04d}.png")).convert("RGBA")
        b = np.asarray(b.convert("RGBa").resize((r.shape[1], r.shape[0]), Image.LANCZOS)).astype(np.float32)
        # crop to what either shows (the empty frame around the figure would flatter the number)
        a = (r[..., 3] > 0) | (b[..., 3] > 0)
        ys, xs = np.nonzero(a) if a.any() else (np.array([0, r.shape[0] - 1]), np.array([0, r.shape[1] - 1]))
        y0, y1, x0, x1 = max(0, ys.min() - 4), ys.max() + 5, max(0, xs.min() - 4), xs.max() + 5
        rows.append((i, comp(b)[y0:y1, x0:x1], comp(r)[y0:y1, x0:x1], r[y0:y1, x0:x1, 3]))
    ps = np.array([psnr(a, b) for _, a, b, _ in rows])
    rep[clip] = {"frames": len(rows), "psnr_mean": round(float(ps.mean()), 2), "psnr_min": round(float(ps.min()), 2), "worst": rows[int(ps.argmin())][0]}
    print(clip, json.dumps(rep[clip]), flush=True)
    pick = sorted({rows[0][0], rows[len(rows) // 3][0], rows[2 * len(rows) // 3][0], rep[clip]["worst"]})
    trs = []
    for i, a, b, al in [r for r in rows if r[0] in pick]:
        dif = np.abs(a - b); zs = max(48, a.shape[1] // 4)
        nxt = [r for r in rows if r[0] > i][:1]
        mot = np.abs(nxt[0][3] - al) if nxt and nxt[0][3].shape == al.shape else dif.max(2)
        zm, zd = window(mot, zs), window(dif.max(2), zs)
        z = lambda t, bb: np.kron(t[bb[1]:bb[3], bb[0]:bb[2]], np.ones((3, 3, 1)))
        trs.append((i, [a, b, np.clip(dif * 4, 0, 255), z(a, zm), z(b, zm), z(a, zd), z(b, zd)]))
    labels = ["Blender render", "live rig", "|diff| x4", "render 3x (moving)", "rig 3x (moving)", "render 3x (max diff)", "rig 3x (max diff)"]
    W = max(sum(t.shape[1] + 6 for t in tl) for _, tl in trs); H = sum(max(t.shape[0] for t in tl) + 26 for _, tl in trs) + 20
    sh = Image.new("RGB", (W, H), (255, 255, 255)); dr = ImageDraw.Draw(sh)
    dr.text((4, 4), f"{char} {clip} {dd}: PSNR {rep[clip]['psnr_mean']} dB (min {rep[clip]['psnr_min']})", fill=(0, 0, 0))
    y = 20
    for i, tl in trs:
        x = 0
        for k, t in enumerate(tl):
            sh.paste(Image.fromarray(np.clip(t, 0, 255).astype(np.uint8)), (x, y + 20)); dr.text((x + 2, y + 4), f"{labels[k]} f{i}", fill=(0, 0, 0))
            x += t.shape[1] + 6
        y += max(t.shape[0] for t in tl) + 26
    sh.save(os.path.join(QA, f"{char}_{dd}_{clip}.png"))
json.dump(rep, open(os.path.join(QA, f"{char}_{dd}_report.json"), "w"), indent=1)
