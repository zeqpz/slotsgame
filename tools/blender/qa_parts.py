"""Quality check of a symbol's cut (art/blender/parts/<ID>): the parts laid back together must match the art, and
everything a moving part can uncover must be clean. Writes art/blender/qa/<ID>_parts.png:
  row 1  rest composite | original | difference x4 (should be near black) - the knot area
  row 2  without the front movers (what they uncover) | each mover alone | the body alone
  row 3  the same for the whole icon at half size
usage: python tools/blender/qa_parts.py <ID> [mover,mover..]   (default: every part with a chain, and the dollar)"""
import json, os, sys
import numpy as np
from PIL import Image, ImageChops, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sid = sys.argv[1]
P = os.path.join(ROOT, "art", "blender", "parts", sid)
spec = json.load(open(os.path.join(P, "parts.json")))
parts = [p for p in sorted(spec["parts"], key=lambda q: q["draw"]) if not p["hidden"]]
movers = sys.argv[2].split(",") if len(sys.argv) > 2 else [p["name"] for p in parts if p.get("chain")] + [p["name"] for p in parts if p["name"] == "dollar"]
src = Image.open(os.path.join(ROOT, "art", "icons-src", sid + ".png")).convert("RGBA")
BG = (40, 40, 44, 255)

def comp(names=None, skip=()):
    c = Image.new("RGBA", src.size, BG)
    for p in parts:
        if (names is None or p["name"] in names) and p["name"] not in skip:
            c.alpha_composite(Image.open(os.path.join(P, p["name"] + ".png")).convert("RGBA"), (p["box"][0], p["box"][1]))
    return c

orig = Image.new("RGBA", src.size, BG); orig.alpha_composite(src)
rest = comp()
diff = ImageChops.difference(rest.convert("RGB"), orig.convert("RGB")).point(lambda v: min(255, v * 4))
d = np.asarray(ImageChops.difference(rest.convert("RGB"), orig.convert("RGB"))).max(-1)
print(f"rest vs art: mean {d.mean():.2f}/255, px off by >24: {(d > 24).sum()}, by >64: {(d > 64).sum()}")
under = comp(skip=movers)
box = (60, 200, 560, 620)
tiles = [rest.crop(box), orig.crop(box), diff.convert("RGBA").crop(box), under.crop(box),
         comp(names=movers).crop(box), comp(names=["body"]).crop(box)]
tw, th = box[2] - box[0], box[3] - box[1]
sheet = Image.new("RGB", (tw * 3, th * 2 + 500), (0, 0, 0))
for i, t in enumerate(tiles):
    sheet.paste(t.convert("RGB"), ((i % 3) * tw, (i // 3) * th))
for i, im in enumerate((rest, under, diff.convert("RGBA"))):
    sheet.paste(im.resize((500, 500), Image.LANCZOS).convert("RGB"), (i * 500, th * 2))
dr = ImageDraw.Draw(sheet)
for i, t in enumerate(["rest", "art", "diff x4", "without " + "+".join(movers), "movers", "body"]):
    dr.text(((i % 3) * tw + 6, (i // 3) * th + 4), t, fill=(255, 255, 0))
out = os.path.join(ROOT, "art", "blender", "qa", sid + "_parts.png")
sheet.save(out)
print("saved", out)
