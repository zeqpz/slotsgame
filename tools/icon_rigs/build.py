"""Build the animated symbol rigs.

  python tools/icon_rigs/build.py              # every recipe in tools/icon_rigs/recipes/
  python tools/icon_rigs/build.py L10 L1       # only these (the atlas still holds every rig built before)
  python tools/icon_rigs/build.py --preview-only L10   # just the preview sheet, nothing written to the game

Writes:
  frontend/assets/icons/icons.png (+ icons_2.png ...), icons.atlas   one shared Spine atlas
  frontend/assets/icons/icons.json                                    {ID: Spine 4.2 skeleton}  (what the game loads)
  art/icons-spine/<ID>.json                                           the same skeletons one per file (Spine editor import)
  tools/icon_rigs/_preview/<ID>_<clip>.png                            Pillow preview sheets (not shipped)
"""
import importlib.util, json, os, sys, glob, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rigkit
from PIL import Image, ImageDraw

HERE = rigkit.HERE
RECIPES = os.path.join(HERE, "recipes")
PREVIEW = os.path.join(HERE, "_preview")
ART = os.path.join(rigkit.ROOT, "art", "icons-spine")


def load_recipe(path):
    spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.RIG


def preview(rig, frames=10):
    os.makedirs(PREVIEW, exist_ok=True)
    out = []
    for clip, spec in rig.r["anims"].items():
        dur = spec.get("dur", 1.0)
        poses = [rig.pose(clip, dur * i / (frames - 1)) for i in range(frames)]
        w, h = poses[0].size
        sheet = Image.new("RGB", (w * frames, h + 16), (34, 32, 40))
        d = ImageDraw.Draw(sheet)
        for i, p in enumerate(poses):
            sheet.paste(p, (i * w, 16), p)
            d.text((i * w + 3, 2), f"{dur * i / (frames - 1):.2f}s", fill=(200, 200, 200))
        d.text((w * frames - 70, 2), f"{rig.id} {clip}", fill=(255, 220, 90))
        path = os.path.join(PREVIEW, f"{rig.id}_{clip}.png"); sheet.save(path); out.append(path)
    # the cut itself: every part on its own, plus the rest pose re-assembled
    parts = list(rig.parts.items())
    th = 140
    tiles = []
    for name, p in parts:
        im = p["img"].copy(); im.thumbnail((th, th))
        t = Image.new("RGB", (th, th + 14), (60, 58, 70)); t.paste(im, ((th - im.width) // 2, 14 + (th - im.height) // 2), im)
        ImageDraw.Draw(t).text((3, 1), name, fill=(255, 255, 255)); tiles.append(t)
    rest = rig.pose(list(rig.r["anims"])[0], 0); rest.thumbnail((th, th))
    t = Image.new("RGB", (th, th + 14), (20, 20, 24)); t.paste(rest, ((th - rest.width) // 2, 14), rest)
    ImageDraw.Draw(t).text((3, 1), "rest pose", fill=(255, 220, 90)); tiles.append(t)
    sheet = Image.new("RGB", (th * len(tiles), th + 14)); [sheet.paste(t, (i * th, 0)) for i, t in enumerate(tiles)]
    path = os.path.join(PREVIEW, f"{rig.id}_parts.png"); sheet.save(path); out.append(path)
    return out


def main(argv):
    preview_only = "--preview-only" in argv
    want = [a for a in argv if not a.startswith("--")]
    paths = sorted(glob.glob(os.path.join(RECIPES, "*.py")))
    recipes = {os.path.basename(p)[:-3]: p for p in paths if not os.path.basename(p).startswith("_")}
    todo = want or list(recipes)
    rigs = {}
    for rid in recipes:                          # every rig is cut (the atlas holds them all) ...
        if preview_only and rid not in todo:
            continue
        t0 = time.time()
        rig = rigkit.Rig(load_recipe(recipes[rid])); rig.cut(); rigs[rid] = rig
        if rid in todo:                          # ... but only the asked-for ones get previews
            for p in preview(rig):
                print("  preview", os.path.relpath(p, rigkit.ROOT))
        print(f"cut {rid}: {len(rig.parts)} parts in {time.time() - t0:.1f}s")
    if preview_only:
        return
    # one atlas for every rig: parts scaled to the output density
    images, names = {}, {}
    for rid, rig in rigs.items():
        names[rid] = {}
        for pname, p in rig.parts.items():
            k = rigkit.OUT_PX_PER_UNIT / rig.ppu
            im = p["img"].resize((max(1, round(p["img"].width * k)), max(1, round(p["img"].height * k))), Image.LANCZOS)
            reg = f"{rid}/{pname}"
            images[reg] = im; names[rid][pname] = reg
    placed, pages = rigkit.pack(images)
    pages = rigkit.trim_pages(pages)
    os.makedirs(rigkit.OUT_DIR, exist_ok=True)
    for f in glob.glob(os.path.join(rigkit.OUT_DIR, "icons*.png")):
        os.remove(f)
    page_names = ["icons.png"] + [f"icons_{i + 1}.png" for i in range(1, len(pages))]
    lines = []
    for pi, (pg, pn) in enumerate(zip(pages, page_names)):
        pg.save(os.path.join(rigkit.OUT_DIR, pn), optimize=True)
        if pi: lines.append("")
        lines += [pn, f"size: {pg.width},{pg.height}", "format: RGBA8888", "filter: Linear,Linear", "repeat: none", "pma: false"]
        for reg, (p, x, y, w, h) in sorted(placed.items()):
            if p != pi: continue
            lines += [reg, "  rotate: false", f"  xy: {x}, {y}", f"  size: {w}, {h}", f"  orig: {w}, {h}", "  offset: 0, 0", "  index: -1"]
    with open(os.path.join(rigkit.OUT_DIR, "icons.atlas"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    bundle = {}
    os.makedirs(ART, exist_ok=True)
    for rid, rig in rigs.items():
        sk = rig.skeleton(names[rid])
        bundle[rid] = sk
        with open(os.path.join(ART, f"{rid}.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(sk, fh, indent=1)
    with open(os.path.join(rigkit.OUT_DIR, "icons.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(bundle, fh, separators=(",", ":"))
    total = sum(os.path.getsize(os.path.join(rigkit.OUT_DIR, f)) for f in os.listdir(rigkit.OUT_DIR))
    print(f"wrote {len(rigs)} rigs, {len(placed)} regions on {len(pages)} page(s) "
          f"({', '.join(f'{p.width}x{p.height}' for p in pages)}), {total // 1024} KB in frontend/assets/icons")


if __name__ == "__main__":
    main(sys.argv[1:])
