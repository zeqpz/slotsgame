"""Cut a symbol's art into its parts (the masks in tools/icon_rigs/recipes/<ID>.py) and write them out for
Blender: one full-resolution PNG per part plus parts.json (each part's box, pivot, parent and draw order, in
icon px; a part that bends also gets its bone chain). Only the cutting comes from the recipe; the recipe's clips
and code-drawn sprites are left out - the animation and the effects are made in Blender.
tools/blender/cuts/<ID>.py, when there is one, changes the cut for Blender:
  DROP   recipe parts left out
  SPLIT  a recipe part cut into pieces along a line, each with its own ink edge and sticker border (the border
         rebuilt from the art's own border profile, optionally as a "<piece>_rim" part drawn behind all the
         pieces), and a bone chain when the piece bends
  FILLS  where a part takes the clean plate's pixels (art/blender/plates/<ID>.png, tools/blender/plate.py)
         instead of the recipe's blur fill, so whatever a moving part uncovers is real art
  CLEAR  where a part's recipe fill is wiped (another part owns the spot)
  ISLANDS parts whose small cut-off bits are dropped (a neighbour's border left behind on them)
  ANCHOR a part whose mesh is held by another bone at one end (weights blended between the two by height)
usage: python tools/blender/dump_parts.py <ID> [out dir]   (default art/blender/parts/<ID>)"""
import importlib.util, json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools", "icon_rigs"))
import rigkit                     # noqa: E402
from build import load_recipe     # noqa: E402


def premul(img):
    a = np.asarray(img.convert("RGBA")).astype(np.float32) / 255
    a[..., :3] *= a[..., 3:4]
    return a


def to_img(arr):
    a = np.clip(arr[..., 3:4], 0, 1)
    rgb = np.where(a > 1e-4, arr[..., :3] / np.maximum(a, 1e-4), 0)
    return Image.fromarray((np.concatenate([np.clip(rgb, 0, 1), a], -1) * 255).round().astype(np.uint8), "RGBA")


def side_of(line, W, H, side):
    """bool HxW: the pixels above (y < line(x)) or below a polyline given left to right."""
    xs, ys = zip(*line)
    yl = np.interp(np.arange(W), xs, ys)
    yy = np.arange(H)[:, None]
    return yy < yl[None, :] if side == "above" else yy >= yl[None, :]


def stroke_mask(pts, width, W, H, ss=4):
    big = Image.new("L", (W * ss, H * ss), 0)
    d = ImageDraw.Draw(big)
    d.line([(x * ss, y * ss) for x, y in pts], fill=255, width=int(width * ss), joint="curve")
    for x, y in (pts[0], pts[-1]):
        r = width * ss / 2
        d.ellipse([x * ss - r, y * ss - r, x * ss + r, y * ss + r], fill=255)
    return np.asarray(big.resize((W, H), Image.LANCZOS), np.float32) / 255


def border_profile(src, core, part_alpha, other):
    """The art's own sticker border round `core`, measured where it is clean (well away from the rest of the
    icon): premultiplied colour and alpha by distance from the core's edge, in 0.5 px steps."""
    d = ndimage.distance_transform_edt(~core)
    clean = (part_alpha > .02) & (ndimage.distance_transform_edt(~other) > 28) & (d > 0) & (d < 24)
    pm = src.copy(); pm[..., :3] *= pm[..., 3:4]
    steps = np.arange(0.5, 24, 0.5)
    prof = np.zeros((len(steps), 4), np.float32)
    for i, k in enumerate(steps):
        m = clean & (np.abs(d - k) <= .5)
        if m.sum() >= 12:
            prof[i] = pm[m].mean(0)
        elif i:
            prof[i] = prof[i - 1] * .5
    return steps, prof


def ring(core, steps, prof):
    """The border round a piece: the measured profile laid out by distance from the piece's edge."""
    d = ndimage.distance_transform_edt(~core)
    out = np.zeros(core.shape + (4,), np.float32)
    m = (d > 0) & (d <= steps[-1])
    for c in range(4):
        out[..., c][m] = np.interp(d[m], steps, prof[:, c])
    return out


def feather(region, px=1.5):
    return np.asarray(Image.fromarray((region * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(px)), np.float32) / 255


def matched(arr, plate, region, ring_px=10):
    """Lay the plate into the part over `region` (opaque cloth) with its colour matched to the part round the
    patch: the difference along a ring just outside is spread smoothly inside (push-pull), so the patch carries
    the part's own light and tone up to its edge, and keeps the plate's weave and folds."""
    ring = ndimage.binary_dilation(region, iterations=ring_px) & ~region & (arr[..., 3] > .98) & (plate[..., 3] > .98)
    a_rgb = arr[..., :3] / np.maximum(arr[..., 3:4], 1e-4)
    p_rgb = plate[..., :3] / np.maximum(plate[..., 3:4], 1e-4)
    diff = np.zeros(arr.shape, np.float32)
    diff[..., :3] = (a_rgb - p_rgb) * ring[..., None]
    diff[..., 3] = ring
    field = rigkit.inpaint(diff, ~ring)[..., :3]
    w = feather(region)[..., None]
    rgb = a_rgb * (1 - w) + np.clip(p_rgb + field, 0, 1) * w
    a = np.maximum(arr[..., 3:4], plate[..., 3:4] * w)
    return np.concatenate([rgb * a, a], -1)


def load_cut(sid):
    path = os.path.join(HERE, "cuts", sid + ".py")
    if not os.path.exists(path):
        return None
    spec = importlib.util.spec_from_file_location("cut_" + sid, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sid = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "art", "blender", "parts", sid)
os.makedirs(out, exist_ok=True)
for f in os.listdir(out):
    if f.endswith(".png"):
        os.remove(os.path.join(out, f))
recipe = load_recipe(os.path.join(ROOT, "tools", "icon_rigs", "recipes", sid + ".py"))
rig = rigkit.Rig(recipe)
rig.cut()
W, H = rig.cv.W, rig.cv.H
spec = {p["name"]: p for p in rig.r["parts"]}
draw = list(rig.r.get("draw") or [p["name"] for p in rig.r["parts"]])
full, meta = {}, {}
for name, part in rig.parts.items():
    p = spec.get(name, {})
    if part.get("sprite") or p.get("copy"):
        continue                  # code-drawn sprites and copies: Blender makes its own effects
    arr = np.zeros((H, W, 4), np.float32)
    x0, y0, x1, y1 = part["box"]
    arr[y0:y1, x0:x1] = premul(part["img"])
    full[name] = arr
    meta[name] = {"pivot": p.get("pivot"), "parent": p.get("parent"), "hidden": bool(p.get("hidden"))}

cut = load_cut(sid)
notes = []
if cut:
    src = np.asarray(rig.src).astype(np.float32) / 255           # straight RGBA
    yy, xx = np.mgrid[0:H, 0:W]
    plate_path = os.path.join(ROOT, "art", "blender", "plates", sid + ".png")
    plate = premul(Image.open(plate_path)) if os.path.exists(plate_path) else None
    for name in getattr(cut, "DROP", []):
        full.pop(name, None); meta.pop(name, None)
        draw = [n for n in draw if n != name]
    for base, pieces in getattr(cut, "SPLIT", {}).items():
        part_alpha = full[base][..., 3]
        rgb, al = src[..., :3], src[..., 3]
        white = (rgb.min(-1) > .80) & (rgb.max(-1) - rgb.min(-1) < .10)
        outside = ndimage.distance_transform_edt(al > .5)          # px to the transparent outside
        core = (part_alpha > .5) & (al > .5) & ~white & (outside > 7)  # the part without its sticker border
        core = ndimage.binary_closing(core, iterations=2)
        lab, n = ndimage.label(core)
        if n > 1:
            sizes = ndimage.sum(np.ones_like(al), lab, range(1, n + 1))
            core = np.isin(lab, 1 + np.nonzero(sizes >= sizes.max() * .02)[0])
        core = ndimage.binary_fill_holes(core)
        other = (al > .5) & (part_alpha < .02)
        steps, prof = border_profile(src, core, part_alpha, other)
        pm = src.copy(); pm[..., :3] *= pm[..., 3:4]
        ink_rgb = np.median(src[core & (rgb.max(-1) < .2)][:, :3], 0)
        names, rims, shapes, bodies = [], [], {}, {}
        for pc in pieces:
            line = pc["line"]
            if pc.get("tuck"):      # the piece behind runs on under the one in front, so no crack shows between
                line = [(x, y - pc["tuck"] if pc["side"] == "below" else y + pc["tuck"]) for x, y in line]
            mine = core & side_of(line, W, H, pc["side"])
            body = pm * mine[..., None]
            shape = mine.astype(np.float32)
            if pc.get("ink"):                                       # a new ink edge where it was cut from the other piece
                ink = stroke_mask(pc["ink"], pc.get("ink_width", 6), W, H)
                body = np.concatenate([ink[..., None] * ink_rgb, ink[..., None]], -1) + body * (1 - ink[..., None])
                shape = np.maximum(shape, ink)
            shapes[pc["name"]], bodies[pc["name"]] = shape > .5, body
        tails_px = pm * np.clip(part_alpha, 0, 1)[..., None]           # the art's own pixels in the part's area
        for pc in pieces:
            shape, body = shapes[pc["name"]], bodies[pc["name"]]
            chain = [list(map(float, q)) for q in pc.get("chain", [])] or None
            m = {"pivot": pc["chain"][0] if pc.get("chain") else meta[base]["pivot"], "parent": meta[base]["parent"],
                 "hidden": False, "chain": chain}
            d = ndimage.distance_transform_edt(~shape)
            inner = ndimage.distance_transform_edt(shape)
            # as far out as the border goes, and 2 px in under the piece's own edge (no crack between them)
            reach = np.clip(steps[-1] - 6.5 - d, 0, 1) * ((d > 0) | (inner <= 2))
            under = np.zeros_like(shape)
            for other, s in shapes.items():
                if other != pc["name"]:
                    under |= s
            under &= ~shape
            # the border: the art's own pixels wherever they show at rest (so the pieces lie back exactly), and
            # the measured border profile where another piece hides it - it shows only once the pieces part
            border = np.where(under[..., None], ring(shape, steps, prof), tails_px) * reach[..., None]
            if pc.get("rim"):                                       # the border as its own part, behind every piece
                full[pc["name"] + "_rim"] = border
                meta[pc["name"] + "_rim"] = dict(m, chain=None, bones_of=pc["name"])
                rims.append(pc["name"] + "_rim")
                arr = body
            else:
                arr = body + border * (1 - body[..., 3:4])
            full[pc["name"]] = arr
            meta[pc["name"]] = m
            names.append(pc["name"])
        full.pop(base); meta.pop(base)
        i = draw.index(base)
        draw = draw[:i] + rims + names + draw[i + 1:]
        notes.append(f"{base} -> {'+'.join(names)} (border {prof[np.argmax(prof[:, 3] < .05) - 1, 3]:.2f}a out to {steps[np.argmax(prof[:, 3] < .05)]} px)")
    fills = getattr(cut, "FILLS", [])
    plates = {"": plate}
    if fills:
        for f in fills:
            pname = f.get("plate", "")
            if pname not in plates:
                plates[pname] = premul(Image.open(os.path.join(ROOT, "art", "blender", "plates", f"{sid}_{pname}.png")))
            pl = plates[pname]
            region = rig.cv.eval(f["region"]) > .5
            if "above" in f: region &= yy < f["above"]
            if "below" in f: region &= yy >= f["below"]
            if "left" in f: region &= xx < f["left"]
            arr = full[f["part"]]
            if f.get("blend") == "matched":
                full[f["part"]] = matched(arr, pl, region)
            else:
                w = feather(region)
                full[f["part"]] = arr * (1 - w[..., None]) + pl * w[..., None]
            notes.append(f"{f['part']} <- plate ({int(region.sum())} px, {f.get('blend', 'alpha')})")
    for c in getattr(cut, "CLEAR", []):
        region = rig.cv.eval(c["region"]) > .5
        if "above" in c: region &= yy < c["above"]
        if "below" in c: region &= yy >= c["below"]
        if "left" in c: region &= xx < c["left"]
        if "plate_clear" in c:      # only out in the air: where the plate is empty, that far from anything on it
            region &= ndimage.distance_transform_edt(plate[..., 3] < .05) > c["plate_clear"]
        full[c["part"]] = full[c["part"]] * (1 - feather(region)[..., None])
        notes.append(f"{c['part']} cleared ({int(region.sum())} px)")
    for name in getattr(cut, "ISLANDS", []):
        a = full[name][..., 3]
        lab, n = ndimage.label(ndimage.binary_dilation(a > .02, iterations=2))
        if n > 1:
            sizes = ndimage.sum(a, lab, range(1, n + 1))
            keep = np.isin(lab, 1 + np.nonzero(sizes >= sizes.max() * .05)[0])
            full[name] = full[name] * keep[..., None]
            notes.append(f"{name}: {n - int(np.unique(lab[keep]).size)} island(s) dropped ({int(sizes.sum() - sizes[sizes >= sizes.max() * .05].sum())} px)")
    for name, an in getattr(cut, "ANCHOR", {}).items():
        meta[name]["anchor"] = an

parts = []
for name, arr in full.items():
    img = to_img(arr)
    bb = img.getbbox()
    img.crop(bb).save(os.path.join(out, name + ".png"))
    x0, y0, x1, y1 = bb
    m = meta[name]
    q = {"name": name, "box": [x0, y0, x1, y1], "pivot": list(m["pivot"] or ((x0 + x1) / 2, (y0 + y1) / 2)),
         "parent": m["parent"], "hidden": m["hidden"], "draw": draw.index(name) if name in draw else -1}
    for k in ("chain", "bones_of", "anchor"):
        if m.get(k):
            q[k] = m[k]
    parts.append(q)
json.dump({"id": sid, "size": [W, H], "parts": sorted(parts, key=lambda q: q["draw"])},
          open(os.path.join(out, "parts.json"), "w"), indent=1)
print(sid, W, "x", H, "->", out, ":", ", ".join(f"{q['name']}({q['box'][2] - q['box'][0]}x{q['box'][3] - q['box'][1]})" for q in parts))
for n in notes:
    print("  ", n)
