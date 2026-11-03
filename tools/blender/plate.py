"""A symbol's clean plate: the same drawing with its moving front parts taken away (what is behind them painted in,
in the art's own style), fitted onto the art pixel for pixel. A part's hidden area is filled from it, so whatever
an animation uncovers is real art, not a blur. Generated with OpenRouter (openai/gpt-image-2.5-sunburst; the key
is read from %USERPROFILE%\\.smukiez\\openrouter-key.txt and never printed).
usage: python tools/blender/plate.py <ID> [name] [--fit-only]
  -> art/blender/plates/<ID>.png (fitted onto art/icons-src/<ID>.png), <ID>_raw.png, <ID>_align.png
The prompt is PLATE_PROMPT in tools/blender/cuts/<ID>.py; a symbol whose moving parts lie on top of each other
can have more plates, PLATES = {"name": prompt} -> art/blender/plates/<ID>_<name>.png (a fill picks one by
"plate": name)."""
import base64, importlib.util, io, json, os, sys, time
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools", "icon_redraw"))
from orapi import call                              # noqa: E402
from install import arr, fit, ink, warp             # noqa: E402
from scipy import ndimage                           # noqa: E402

SRC = os.path.join(ROOT, "art", "icons-src")
OUT = os.path.join(ROOT, "art", "blender", "plates")


def cut_spec(sid):
    spec = importlib.util.spec_from_file_location("cut_" + sid, os.path.join(HERE, "cuts", sid + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def generate(sid, remove, name=""):
    im = Image.open(os.path.join(SRC, sid + ".png")).convert("RGBA")
    buf = io.BytesIO(); im.save(buf, "PNG")
    prompt = ("Edit this slot-machine symbol. Return the SAME picture - the same drawing, size and position in the frame, the "
              "same colours, lighting, linework, texture and the same thick plain white sticker border - with only these "
              "changes:\n\n" + remove + "\n\nEverything else stays exactly as it is. Background: fully transparent around "
              "the sticker. No shadow, no glow, nothing else in the image.")
    body = dict(model="openai/gpt-image-2.5-sunburst", prompt=prompt, quality="high", background="transparent",
                output_format="png", aspect_ratio="1:1", n=1,
                input_references=[{"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}}])
    for attempt in range(3):
        try:
            r = call("/images", body, timeout=900)
            break
        except Exception as e:
            if attempt == 2 or not any(s in str(e) for s in ("HTTP 502", "HTTP 503", "HTTP 429", "timed out")):
                raise
            time.sleep(8)
    tag = sid + ("_" + name if name else "")
    json.dump(r, open(os.path.join(OUT, tag + "_response.json"), "w"))     # kept first: a paid picture is never lost
    d = r["data"][0]
    b = d.get("b64_json") or ""
    if b.startswith("data:"):
        b = b.split(",", 1)[1]
    if b:
        data = base64.b64decode(b + "=" * (-len(b) % 4))
    else:
        import urllib.request
        data = urllib.request.urlopen(d["url"], timeout=120).read()
    raw = os.path.join(OUT, tag + "_raw.png")
    open(raw, "wb").write(data)
    return raw, (r.get("usage") or {}).get("cost")


def fit_plate(sid, name=""):
    tag = sid + ("_" + name if name else "")
    old = arr(Image.open(os.path.join(SRC, sid + ".png")))
    new = arr(Image.open(os.path.join(OUT, tag + "_raw.png")))
    p, score = fit(old, new)
    H, W = old.shape[:2]
    pm = new.copy(); pm[..., :3] *= pm[..., 3:4]                 # premultiplied, cubic: no dark fringes
    w = np.clip(warp(pm, p, (H, W), order=3), 0, 1)
    a = w[..., 3:4]
    rgb = np.where(a > 1e-3, w[..., :3] / np.maximum(a, 1e-3), 0)
    body = ndimage.binary_dilation(a[..., 0] > .12, iterations=3)  # drop the model's faint alpha haze
    a = np.where(body[..., None] & (a > .03), a, 0)
    out = np.concatenate([np.clip(rgb, 0, 1), a], -1)
    Image.fromarray((out * 255).round().astype(np.uint8), "RGBA").save(os.path.join(OUT, tag + ".png"))
    oi, wi = ink(old) > .5, ink(out) > .5
    d_new = ndimage.distance_transform_edt(~wi)
    ov = np.full((H, W, 3), 40, np.uint8)
    ov[oi] = (230, 40, 40); ov[wi] = (40, 220, 230); ov[oi & wi] = (255, 255, 255)
    Image.fromarray(ov).save(os.path.join(OUT, tag + "_align.png"))
    return dict(scale=round(p[0], 4), turn_deg=round(float(np.degrees(p[1])), 2), shift=(round(p[2], 1), round(p[3], 1)),
                score=round(score, 3), ink_old_to_new=(round(float(d_new[oi].mean()), 2), round(float(np.percentile(d_new[oi], 90)), 1)))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sid, name = args[0], (args[1] if len(args) > 1 else "")
    os.makedirs(OUT, exist_ok=True)
    if "--fit-only" not in sys.argv:
        cut = cut_spec(sid)
        prompt = cut.PLATES[name] if name else cut.PLATE_PROMPT
        raw, cost = generate(sid, prompt, name)
        print(sid, name or "(main)", "plate generated", raw, "cost", cost)
    print(sid, name or "(main)", "fit:", json.dumps(fit_plate(sid, name)))
