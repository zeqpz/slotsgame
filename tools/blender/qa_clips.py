"""Quality check of a symbol's rendered clips - run after every animation, before calling it done.
  art/blender/renders/<ID>/<clip>/####.png   the composited frames (what the game plays)
  art/blender/qa/art/<ID>/<clip>/####.png     the art layer alone, 1024 px (tools/blender/run.py, step qa)
Writes to art/blender/qa/<ID>/:
  <clip>_sheet.jpg    every frame of the clip, in order, on the game's dark wall colour
  <clip>_zoom.jpg     the moving joints (ropes and knot, the $) at 2x on the frames where they move most
  <clip>.webp         the clip playing, looped, for a look at the motion
  report.txt          per frame: holes inside the silhouette (gaps between parts), and alpha seams
usage: python tools/blender/qa_clips.py <ID> [x0,y0,x1,y1 icon px of the joint area to zoom]"""
import glob, os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sid = sys.argv[1]
zoom_box = tuple(int(v) for v in sys.argv[2].split(",")) if len(sys.argv) > 2 else (90, 260, 470, 600)
REN = os.path.join(ROOT, "art", "blender", "renders", sid)
ART = os.path.join(ROOT, "art", "blender", "qa", "art", sid)
OUT = os.path.join(ROOT, "art", "blender", "qa", sid)
os.makedirs(OUT, exist_ok=True)
WALL = (23, 20, 28, 255)
ORTHO = 13.0                      # the camera's view, in units (100 icon px each)


def on_wall(im):
    bg = Image.new("RGBA", im.size, WALL)
    bg.alpha_composite(im.convert("RGBA"))
    return bg.convert("RGB")


def icon_to_px(x, y, size):       # icon px -> render px (icon centred, ORTHO units across the frame)
    s = size / (ORTHO * 100)
    return size / 2 + (x - 500) * s, size / 2 + (y - 500) * s


report, firsts, lasts = [], {}, {}
for clip in [c for c in ("idle", "land", "hit", "multi") if os.path.isdir(os.path.join(REN, c))]:
    frames = sorted(glob.glob(os.path.join(REN, clip, "*.png")))
    arts = sorted(glob.glob(os.path.join(ART, clip, "*.png")))
    if not frames:
        continue
    # ---- contact sheet
    T, cols = 170, 12
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * T, rows * T), (0, 0, 0))
    for i, f in enumerate(frames):
        t = on_wall(Image.open(f)).resize((T, T), Image.LANCZOS)
        ImageDraw.Draw(t).text((4, 2), os.path.basename(f)[:4], fill=(255, 220, 0))
        sheet.paste(t, ((i % cols) * T, (i // cols) * T))
    sheet.save(os.path.join(OUT, f"{clip}_sheet.jpg"), quality=88)
    # ---- holes in the art layer: transparent pixels the silhouette closes round. A CRACK (thin: no point
    # more than 2.5 px from its edge, at 1024 px) is a gap between parts - a defect. A wide one is open space
    # the parts happen to close round (a swinging rope meeting the sack, a thrown note over the top): noted only.
    moves = []
    prev = None
    for f in arts:
        a = np.asarray(Image.open(f).getchannel("A")) > 127
        holes = ndimage.binary_fill_holes(a) & ~a
        lab, n = ndimage.label(holes)
        cracks, seams, spaces = [], [], 0
        if n:
            depth = ndimage.distance_transform_edt(holes)
            rgbf = np.asarray(Image.open(f).convert("RGB")).astype(np.float32) / 255
            for i, s in enumerate(ndimage.sum(holes, lab, range(1, n + 1)), 1):
                if s < 6:
                    continue
                if ndimage.maximum(depth, lab, i) <= 2.5:
                    # what it runs between: art on both sides is a crack; two white sticker borders almost
                    # touching (two separate pieces swinging together) only a hairline of open space
                    near = ndimage.binary_dilation(lab == i, iterations=3) & a
                    whiteness = rgbf[near].min(-1).mean() if near.any() else 0
                    (seams if whiteness > .8 else cracks).append(int(s))
                else:
                    spaces += 1
        tag = os.path.basename(f)[:4]
        if cracks:
            report.append(f"CRACK {clip} {tag}: {len(cracks)} thin gap(s) between parts, largest {max(cracks)} px")
        if seams:
            report.append(f"      {clip} {tag}: {len(seams)} hairline(s) between two sticker borders (pieces passing close - look)")
        if spaces and not cracks:
            report.append(f"      {clip} {tag}: {spaces} enclosed open space(s) (not a crack - check the sheet)")
        rgb = np.asarray(Image.open(f).convert("RGBA")).astype(np.int16)
        moves.append(0 if prev is None else int(np.abs(rgb - prev).mean() * 1000))
        prev = rgb
    if arts:
        firsts[clip] = np.asarray(Image.open(arts[0]).convert("RGBA")).astype(np.int16)
        lasts[clip] = np.asarray(Image.open(arts[-1]).convert("RGBA")).astype(np.int16)
        steps = [m / 1000 for m in moves[1:]]
        if clip == "idle" and steps:            # the loop's seam: the jump from the last frame to the first
            seam = np.abs(lasts[clip] - firsts[clip]).mean()
            report.append(f"idle loop seam {seam:.3f} vs typical frame step {np.median(steps):.3f} (max {max(steps):.3f})"
                          + ("  <-- POPS" if seam > 2 * max(steps) + .05 else ""))
    # ---- zoom: the joints on the frames that change most (and the first), 2x
    if arts:
        pick = sorted(np.argsort(moves)[-5:].tolist() + [0])
        size = Image.open(arts[0]).size[0]
        x0, y0 = icon_to_px(zoom_box[0], zoom_box[1], size)
        x1, y1 = icon_to_px(zoom_box[2], zoom_box[3], size)
        pad = 60 if clip == "hit" else 20      # the leap carries the bag up: a taller window
        box = (int(x0) - pad, int(y0) - (180 if clip == "hit" else pad), int(x1) + pad, int(y1) + pad)
        tiles = []
        for i in pick:
            im = on_wall(Image.open(arts[i])).crop(box)
            im = im.resize((im.width * 3 // 2, im.height * 3 // 2), Image.LANCZOS)
            ImageDraw.Draw(im).text((4, 2), os.path.basename(arts[i])[:4], fill=(255, 220, 0))
            tiles.append(im)
        zw, zh = tiles[0].size
        z = Image.new("RGB", (zw * 3, zh * 2), (0, 0, 0))
        for i, t in enumerate(tiles[:6]):
            z.paste(t, ((i % 3) * zw, (i // 3) * zh))
        z.save(os.path.join(OUT, f"{clip}_zoom.jpg"), quality=90)
    # ---- the clip playing (land / hit / multi with a beat of rest after, so the loop reads)
    ims = [on_wall(Image.open(f)) for f in frames]
    if clip != "idle":
        ims += [ims[-1]] * 12
    else:
        ims = ims * 2
    ims[0].save(os.path.join(OUT, f"{clip}.webp"), save_all=True, append_images=ims[1:], duration=33, loop=0, quality=90, method=4)
    report.append(f"{clip}: {len(frames)} frames, {len(arts)} art frames checked")
# every clip but the loop starts and ends on the rest pose (the idle's first frame), so the clips can follow each
# other in the game without a jump
if "idle" in firsts:
    for clip in ("land", "hit", "multi"):
        if clip in firsts:
            d0 = np.abs(firsts[clip] - firsts["idle"]).mean()
            d1 = np.abs(lasts[clip] - firsts["idle"]).mean()
            report.append(f"{clip} vs rest: first frame {d0:.3f}, last frame {d1:.3f}" + ("  <-- NOT AT REST" if max(d0, d1) > .5 else ""))
open(os.path.join(OUT, "report.txt"), "w").write("\n".join(report) + "\n")
print("\n".join(report))
print("->", OUT)
