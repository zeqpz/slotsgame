"""Pack a symbol's Blender renders (art/blender/renders/<ID>/<clip>/####.png: 512 px frames of the 13-unit camera,
RGBA, glow and effects composited in) into the sheets the game plays: one WebP per clip per density, frames in a
grid, every frame of a clip cropped to the same box (the union of everything any of its frames shows - an idle
stays near the icon, a hit's rings reach the edge), and frontend/assets/sym/manifest.json saying where each clip's
box sits on the icon and how the clip runs.
Densities are atlas px per rig unit, as the old rigs' (an icon is 100 units across its longer side): 1.6 for a
1080p screen or a phone, 2.4 between, 3.2 for a 2x screen - the game loads the one that suits the screen.
usage: python tools/blender/pack_frames.py <ID,ID..|all> [densities, default 1.6,2.4,3.2]
       python tools/blender/pack_frames.py fit   (re-apply FIT_TO_ART to the manifest only)"""
import glob, json, math, os, sys
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REN = os.path.join(ROOT, "art", "blender", "renders")
OUT = os.path.join(ROOT, "frontend", "assets", "sym")
CLIPS = ("idle", "land", "hit", "multi")
FRAME_UNITS = 13.0                      # the camera's view, in Blender units (10 = a 1000 px icon)
FPS = 30


HAZE = (4, 14)                          # alpha (of 255) under which the bloom's outer haze is let go, eased between
# Symbols whose art sits small in its square canvas (a wide, low car leaves half the square empty): their box on
# the board is their rest pose's own visible extent, centred on it, plus FIT_PAD units round it - so the board's
# fit (88% of the cell, see measureRigBox) sizes them by what is drawn, not by the canvas (owner, 2026-11-02:
# the lowrider sat small and oddly on the board; the freight car is the same shape).
FIT_TO_ART = {"L10", "L9"}
FIT_PAD = 0.15


def art_fit(sid):
    """The rest pose's visible extent (the landing's first frame, alpha over half), in Blender units from the
    frame's centre: (centre x, centre y, width, height)."""
    f = sorted(glob.glob(os.path.join(REN, sid, "land", "*.png")))[0]
    im = dehaze(Image.open(f).convert("RGBA"))
    S = im.size[0]
    u = S / FRAME_UNITS
    ys, xs = np.nonzero(np.asarray(im.getchannel("A")) > 128)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    return ((x0 + x1) / 2 - S / 2) / u, ((y0 + y1) / 2 - S / 2) / u, (x1 - x0) / u, (y1 - y0) / u


def apply_fit(sid, entry):
    """Re-centre an entry's clip boxes on its art and size its icon box to it (idempotent: undoes an earlier fit)."""
    ox, oy = entry.pop("fit", [0, 0])
    for c in entry["clips"].values():
        c["box"][0] = round(c["box"][0] + ox, 4); c["box"][1] = round(c["box"][1] + oy, 4)
    spec = json.load(open(os.path.join(ROOT, "art", "blender", "parts", sid, "parts.json")))
    entry["icon"] = [spec["size"][0] / 100, spec["size"][1] / 100]
    if sid not in FIT_TO_ART:
        return entry
    cx, cy, w, h = art_fit(sid)
    for c in entry["clips"].values():
        c["box"][0] = round(c["box"][0] - cx, 4); c["box"][1] = round(c["box"][1] - cy, 4)
    entry["icon"] = [round(w + 2 * FIT_PAD, 4), round(h + 2 * FIT_PAD, 4)]
    entry["fit"] = [round(cx, 4), round(cy, 4)]
    return entry


def dehaze(im):
    """The compositor's bloom leaves a haze under 5% opacity across much of the frame: invisible over the dark
    board, but it stretches every crop to the frame's edge and lossy compression turns it into blotches.
    Fade it out smoothly to nothing."""
    a = np.asarray(im).astype(np.float32)
    al = a[..., 3]
    t = np.clip((al - HAZE[0]) / (HAZE[1] - HAZE[0]), 0, 1)
    a[..., 3] = al * t * t * (3 - 2 * t)
    a[a[..., 3] < .5, :3] = 0          # no colour left under nothing (the compositor's Replace Alpha keeps the bloom's)
    return Image.fromarray(a.round().astype(np.uint8), "RGBA")


def resize(im, size):
    """Shrink with the colour premultiplied (Pillow's RGBa mode), so see-through edges never pick up dark fringes."""
    return im.convert("RGBa").resize(size, Image.LANCZOS).convert("RGBA")


def pack(sid, densities):
    clips = {c: sorted(glob.glob(os.path.join(REN, sid, c, "*.png"))) for c in CLIPS}
    clips = {c: f for c, f in clips.items() if f}
    if set(clips) != set(CLIPS):
        return sid, None, f"{sid}: clips missing ({', '.join(c for c in CLIPS if c not in clips)})"
    spec = json.load(open(os.path.join(ROOT, "art", "blender", "parts", sid, "parts.json")))
    W, H = spec["size"]
    entry = {"icon": [W / 100, H / 100], "clips": {}, "sheets": {}}   # the icon's own size, Blender units
    totals = {f"d{round(d * 10)}": 0 for d in densities}
    for c, files in clips.items():
        fs = [dehaze(Image.open(f).convert("RGBA")) for f in files]
        S = fs[0].size[0]
        u = S / FRAME_UNITS                                    # master px per Blender unit
        alpha = np.zeros((S, S), bool)
        for im in fs:
            alpha |= np.asarray(im.getchannel("A")) > 0
        ys, xs = np.nonzero(alpha)
        x0, x1, y0, y1 = max(0, xs.min() - 4), min(S, xs.max() + 5), max(0, ys.min() - 4), min(S, ys.max() + 5)
        crops = [im.crop((x0, y0, x1, y1)) for im in fs]
        # where the clip's box sits: its top-left from the icon's centre, and its size, in Blender units (y down)
        entry["clips"][c] = {"frames": len(fs), "fps": FPS, "loop": c == "idle",
                             "box": [round((x0 - S / 2) / u, 4), round((y0 - S / 2) / u, 4), round((x1 - x0) / u, 4), round((y1 - y0) / u, 4)]}
        for d in densities:
            px_per_unit = d * 10                               # rig units: an icon's 10 Blender units = 100
            cw, ch = max(2, round((x1 - x0) / u * px_per_unit)), max(2, round((y1 - y0) / u * px_per_unit))
            dd = f"d{round(d * 10)}"
            os.makedirs(os.path.join(OUT, dd), exist_ok=True)
            n = len(fs)
            cols = max(1, min(n, math.ceil(math.sqrt(n * ch / cw))))
            while cols * cw > 4096:
                cols -= 1
            rows = math.ceil(n / cols)
            sheet = Image.new("RGBA", (cols * cw, rows * ch), (0, 0, 0, 0))
            for i, im in enumerate(crops):
                sheet.paste(resize(im, (cw, ch)), ((i % cols) * cw, (i // cols) * ch))
            path = os.path.join(OUT, dd, f"{sid}_{c}.webp")
            sheet.save(path, "WEBP", quality=82, method=6)
            totals[dd] += os.path.getsize(path)
            entry["sheets"].setdefault(dd, {})[c] = {"w": cw, "h": ch, "cols": cols, "bytes": os.path.getsize(path)}
    return sid, apply_fit(sid, entry), f"{sid}: " + " | ".join(f"{dd} {t / 1e6:.2f} MB" for dd, t in totals.items())


if __name__ == "__main__":
    if sys.argv[1] == "fit":   # re-apply FIT_TO_ART to the manifest as it stands, without re-encoding any sheet
        man_path = os.path.join(OUT, "manifest.json")
        manifest = json.load(open(man_path))
        for sid, entry in manifest["symbols"].items():
            apply_fit(sid, entry)
            print(sid, entry["icon"], entry.get("fit", ""))
        json.dump(manifest, open(man_path, "w"), indent=1)
        sys.exit()
    ids = sys.argv[1].split(",") if sys.argv[1] != "all" else sorted(os.listdir(REN))
    densities = [float(v) for v in (sys.argv[2].split(",") if len(sys.argv) > 2 else ("1.6", "2.4", "3.2"))]
    man_path = os.path.join(OUT, "manifest.json")
    packed = {}
    with ProcessPoolExecutor(max_workers=min(6, len(ids))) as ex:
        for sid, entry, note in ex.map(pack, ids, [densities] * len(ids)):
            print(note, flush=True)
            if entry:
                packed[sid] = entry
    # read the manifest only now, so two packs of different symbols running at once each keep the other's entries
    manifest = json.load(open(man_path)) if os.path.exists(man_path) else {"densities": [], "symbols": {}}
    manifest["densities"] = sorted(set(manifest.get("densities", [])) | set(densities))
    manifest["symbols"].update(packed)
    json.dump(manifest, open(man_path, "w"), indent=1)
    print("->", man_path, "|", len(manifest["symbols"]), "symbols")
