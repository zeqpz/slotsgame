"""QA of the boy's renders (art/blender/chars/boy/renders) -> art/blender/chars/boy/qa/:
  <clip>_sheet.jpg   every frame (on twos for long clips), small, on a mid-grey wall
  <clip>_zoom.jpg    each joint (knees, ankles, hips, elbow, wrist, shoulder, neck, waist, beanie) at 3x on the
                     frames where it bends most, beside the same joint at rest
  report.txt         per clip: frame count, cracks / holes inside the silhouette vs the rest pose, frame-to-frame
                     pops, the loop seam (idle last -> first), one-shots' first / last frame vs the idle's first
                     (the rest pose), the unlit pass's coverage
Run with the project venv python: python tools/blender/chars/boy/qa_boy.py [clip ...]"""
import glob, json, os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
BOY = os.path.join(ROOT, "art", "blender", "chars", "boy")
REN = os.environ.get("BOY_RENDERS") or os.path.join(BOY, "renders")
QA = os.path.join(BOY, "qa")
WALL = (58, 52, 74)


def load(path):
    return np.asarray(Image.open(path).convert("RGBA")).astype(np.float32) / 255.


def on_wall(a):
    rgb = a[..., :3] * a[..., 3:4] + np.array(WALL, np.float32) / 255. * (1 - a[..., 3:4])
    return Image.fromarray((rgb * 255 + .5).clip(0, 255).astype(np.uint8))


def half(a):
    """the crack check runs on the frame at the 720 x 1200 scale (it measures px-wide gaps; at the 2x master the
    full-size pass is four times the work for the same answer)"""
    k = max(1, a.shape[1] // 720)
    return a if k == 1 else a.reshape(a.shape[0] // k, k, a.shape[1] // k, k, 4).mean((1, 3))


def cracks(a, rest_mask=None):
    a = half(a)
    """hairline cracks and holes inside the figure: see-through pixels with solid paint on both sides within 2 px
    (across the gap, any of four directions), and see-through pockets enclosed by the figure"""
    al = a[..., 3]
    solid = al > .95
    gap = al < .85
    sand = np.zeros_like(gap)
    pad = np.pad(solid, 3)
    H, W = al.shape
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        for d1 in (1, 2):
            for d2 in (1, 2):
                fw = pad[3 + dy * d1:3 + dy * d1 + H, 3 + dx * d1:3 + dx * d1 + W]
                bw = pad[3 - dy * d2:3 - dy * d2 + H, 3 - dx * d2:3 - dx * d2 + W]
                sand |= fw & bw
    thin = gap & sand
    sil = ndimage.binary_fill_holes(al > .5)
    holes = sil & (al < .5)
    bad = thin | holes
    if rest_mask is not None:
        bad &= ~rest_mask
    return bad


def main(only):
    os.makedirs(QA, exist_ok=True)
    rep = json.load(open(os.path.join(QA, "pose_report.json")))
    meta = json.load(open(os.path.join(REN, "meta.json")))
    rest = load(os.path.join(REN, "idle", "0001.png"))
    rest_bad = ndimage.binary_dilation(cracks(rest), iterations=2)
    lines = [f"rest: {int(cracks(rest).sum())} px of cracks/holes inside the silhouette (the drawing's own)"]
    for clip, info in meta["clips"].items():
        if only and clip not in only:
            continue
        files = sorted(glob.glob(os.path.join(REN, clip, "*.png")))
        if not files:
            continue
        fr = [load(f) for f in files]
        n = len(fr)
        lines.append(f"\n== {clip}: {n} frames ({n / 30:.2f} s){' loop' if info['loop'] else ''}"
                     + (f" cues {info.get('cues')}" if info["loop"] else ""))
        # cracks / holes
        worst = []
        for i, a in enumerate(fr):
            b = cracks(a, rest_bad)
            lab, k = ndimage.label(b)
            if k:
                sizes = ndimage.sum(b, lab, range(1, k + 1))
                big = [(int(s), ndimage.center_of_mass(b, lab, j + 1)) for j, s in enumerate(sizes) if 6 <= s < 1500]
                if big:
                    worst.append((i, sum(s for s, _ in big), [(s, (int(c[1]), int(c[0]))) for s, c in big[:4]]))
        lines.append(f"  cracks/holes (>=6 px, not in the rest pose): {len(worst)} frames"
                     + "".join(f"\n    f{i}: {t} px at {spots}" for i, t, spots in sorted(worst, key=lambda w: -w[1])[:8]))
        # nothing may touch the frame's edges (the game shows the frame on open wall: a cut would read as a
        # straight slice): alpha in the outermost 4 px
        edge = []
        for i, a in enumerate(fr):
            al = a[..., 3]
            m = max(al[:4].max(), al[-4:].max(), al[:, :4].max(), al[:, -4:].max())
            if m > 0:
                edge.append((i, round(float(m) * 255)))
        lines.append(f"  edge alpha (outer 4 px): {len(edge)} frames {edge[:12]}")
        # pops: frame-to-frame change
        d = [float(np.abs(fr[i + 1] - fr[i]).mean() * 255) for i in range(n - 1)]
        if info["loop"]:
            seam = float(np.abs(fr[0] - fr[-1]).mean() * 255)
            lines.append(f"  loop seam (last -> first) {seam:.2f} vs frame steps median {np.median(d):.2f} max {max(d):.2f}")
        med = float(np.median(d)) if d else 0
        pops = [(i + 1, round(v, 2)) for i, v in enumerate(d) if v > 3 * med + 1.5]
        lines.append(f"  frame steps: median {med:.2f}, max {max(d) if d else 0:.2f}; pops {pops[:10]}")
        if not info["loop"]:
            f0 = float(np.abs(fr[0] - rest).max() * 255)
            fl = float(np.abs(fr[-1] - rest).max() * 255)
            lines.append(f"  vs rest (max abs, 0-255): first {f0:.1f}, last {fl:.1f}  (pose: first "
                         f"{rep[clip]['first_vs_rest_px']} px, last {rep[clip]['last_vs_rest_px']} px)")
        # unlit coverage
        uf = sorted(glob.glob(os.path.join(REN, clip + "_unlit", "*.png")))
        if uf:
            u = [load(uf[i]) for i in range(0, len(uf), max(1, len(uf) // 6))]
            lines.append(f"  unlit: {len(uf)} frames; shoe px (sampled) {[int((x[..., 3] > .5).sum()) for x in u]}")
        # contact sheet
        step = 1 if n <= 100 else 2
        idx = list(range(0, n, step))
        tw, th = 144, 240
        cols = 12
        rows = (len(idx) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw, rows * (th + 14)), (20, 20, 24))
        dr = ImageDraw.Draw(sheet)
        for j, i in enumerate(idx):
            im = on_wall(fr[i]).resize((tw, th), Image.LANCZOS)
            x, y = (j % cols) * tw, (j // cols) * (th + 14)
            sheet.paste(im, (x, y + 14))
            dr.text((x + 3, y + 1), str(i), fill=(230, 230, 230))
        sheet.save(os.path.join(QA, f"{clip}_sheet.jpg"), quality=88)
        # joint zooms: the frames each joint bends most (or moves most from rest)
        J = rep[clip]["joints"]
        names = list(J[0].keys())
        rj = rep["idle"]["joints"][0]
        tiles = []
        for jn in names:
            score = [abs(J[i][jn][2] - rj[jn][2]) for i in range(n)]
            best = sorted(range(n), key=lambda i: -score[i])
            pick = []
            for i in best:
                if all(abs(i - q) > 4 for q in pick):
                    pick.append(i)
                if len(pick) == 3:
                    break
            row = []
            for i in [0] + pick:
                x, y = J[i][jn][0], J[i][jn][1]
                box = (int(x - 60), int(y - 60), int(x + 60), int(y + 60))
                im = on_wall(fr[i]).crop(box).resize((300, 300), Image.LANCZOS)
                ImageDraw.Draw(im).text((4, 4), f"{jn} f{i} {score[i]:.1f}", fill=(255, 255, 120))
                row.append(im)
            tiles.append(row)
        zoom = Image.new("RGB", (4 * 300, len(tiles) * 300), (0, 0, 0))
        for r, row in enumerate(tiles):
            for c, im in enumerate(row):
                zoom.paste(im, (c * 300, r * 300))
        zoom.save(os.path.join(QA, f"{clip}_zoom.jpg"), quality=88)
    open(os.path.join(QA, "report.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1:])
