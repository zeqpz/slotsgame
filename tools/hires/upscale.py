"""Re-make the game's flat raster art at high resolution.

  python tools/hires/upscale.py                 # every asset in TABLE
  python tools/hires/upscale.py hud_bar win_box # only these
  python tools/hires/upscale.py --list          # the table, with source and output sizes

Sources: art/ui-src/ - the art as it shipped before this pass, never written to. Most of the HUD and
panel plates came to us as 256-colour palette PNGs with error-diffusion dither, which reads as grit
and blotches at any size. Every asset goes:

  source -> (palette art: de-dither, a premultiplied Gaussian of `dd` px that melts the dither dots
  without moving an edge) -> colour bleed under the transparent pixels (so no dark fringe is dragged
  in) -> Real-ESRGAN x4 on the GPU (anime model: clean edges, flat fills stay flat) -> Lanczos to the
  output size with premultiplied alpha -> alpha clean-up -> WebP into frontend/assets/.

Output sizes come from measuring the game: `scale` is the source size multiplied up so the art is
drawn at or under its own pixels on a 4K-class screen (1920x1080 @2x, 2560x1440) at the largest it
is ever shown (win pops included). Art already big enough still goes through the x4 pass and comes
back at `scale` 1-1.5: the same size, without the dither.

Needs realesrgan-ncnn-vulkan (https://github.com/xinntao/Real-ESRGAN, release v0.2.5.0). Set
REALESRGAN to the .exe, or keep it at ../.tools/realesrgan/ next to the repo. Results of the x4 pass
are cached by content hash in %LOCALAPPDATA%/smukiez-hires (or ~/.cache/smukiez-hires).
"""
import hashlib, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, "art", "ui-src")
OUT = os.path.join(ROOT, "frontend", "assets")
ESRGAN = os.environ.get("REALESRGAN") or os.path.join(os.path.dirname(ROOT), ".tools", "realesrgan", "realesrgan-ncnn-vulkan.exe")
CACHE = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.cache"), "smukiez-hires")

# name: source file in art/ui-src, output file in frontend/assets, scale vs the source, de-dither px
# (0 = the source is full colour), model, WebP quality (None = lossless).
A = "realesrgan-x4plus-anime"
TABLE = {}


def add(name, src, out, scale, dd=0.0, model=A, q=90, kit=None, accent=False, note=""):
    TABLE[name] = dict(src=src, out=out, scale=scale, dd=dd, model=model, q=q, kit=kit, accent=accent)


def load():
    import json
    with open(os.path.join(HERE, "assets.json"), encoding="utf-8") as fh:
        for row in json.load(fh):
            add(**row)


# ---------- image helpers ----------
def premul(a):
    a = a.astype(np.float32)
    al = a[..., 3:4] / 255.0
    return np.concatenate([a[..., :3] * al, a[..., 3:4]], -1)


def unpremul(p):
    al = p[..., 3:4]
    rgb = np.where(al > 0.5, p[..., :3] * 255.0 / np.maximum(al, 1e-3), 0)
    return np.concatenate([rgb, al], -1).clip(0, 255)


def chan_op(p, fn):
    return np.stack([np.asarray(fn(Image.fromarray(p[..., i].astype(np.float32), "F")), np.float32) for i in range(p.shape[-1])], -1)


def blur1d(x, k, axis):
    r = len(k) // 2
    pad = [(0, 0)] * x.ndim; pad[axis] = (r, r)
    xp = np.pad(x, pad, mode="edge")
    out = np.zeros_like(x)
    for i, w in enumerate(k):
        out += w * np.take(xp, range(i, i + x.shape[axis]), axis=axis)
    return out


def gauss(x, sigma):
    r = max(1, int(np.ceil(sigma * 3)))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2); k /= k.sum()
    return blur1d(blur1d(x, k, 0), k, 1)


def box(x, r):
    k = np.ones(2 * r + 1) / (2 * r + 1)
    return blur1d(blur1d(x, k, 0), k, 1)


def dedither(im, sigma):
    p = gauss(premul(np.asarray(im.convert("RGBA"))), sigma)
    return Image.fromarray(unpremul(p).round().astype(np.uint8), "RGBA")


def bleed(im, passes=24):
    """Fill the colour under fully transparent pixels with the nearest visible colour, so a model
    that looks at RGB without alpha (or a resampler) never drags black into the edges."""
    a = np.asarray(im.convert("RGBA")).astype(np.float32)
    rgb, al = a[..., :3], a[..., 3]
    known = al > 8
    if known.all() or not known.any():
        return im
    acc = rgb * known[..., None]; w = known.astype(np.float32)
    k = lambda x: box(x, 2)
    fill = rgb.copy(); have = known.copy()
    for _ in range(passes):
        s = k(acc); ws = k(w)
        new = (~have) & (ws > 1e-4)
        fill[new] = s[new] / ws[new][:, None]
        have |= new
        acc = fill * have[..., None]; w = have.astype(np.float32)
        if have.all():
            break
    out = np.where(known[..., None], rgb, fill)
    return Image.fromarray(np.dstack([out, al]).clip(0, 255).round().astype(np.uint8), "RGBA")


def resize_premul(im, size):
    p = premul(np.asarray(im.convert("RGBA")))
    p = chan_op(p, lambda c: c.resize(size, Image.LANCZOS))
    p[..., 3] = p[..., 3].clip(0, 255)
    return Image.fromarray(unpremul(p).round().astype(np.uint8), "RGBA")


def tidy_alpha(im):
    a = np.asarray(im).copy()
    al = a[..., 3]
    al[al >= 250] = 255
    al[al <= 3] = 0
    a[al == 0, :3] = 0
    return Image.fromarray(a, "RGBA")


def esrgan(im, model):
    os.makedirs(CACHE, exist_ok=True)
    buf = np.asarray(im.convert("RGBA")).tobytes()
    key = hashlib.sha1(buf + repr((im.size, model)).encode()).hexdigest()
    hit = os.path.join(CACHE, key + ".png")
    if not os.path.exists(hit):
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "in.png"); im.save(src)
            r = subprocess.run([ESRGAN, "-i", src, "-o", hit, "-n", model, "-s", "4", "-f", "png"],
                               cwd=os.path.dirname(ESRGAN), capture_output=True, text=True)
            if r.returncode or not os.path.exists(hit):
                raise RuntimeError(f"Real-ESRGAN failed: {r.stderr[-400:]}")
    return Image.open(hit).convert("RGBA")


# ---------- the pass ----------
def make(name):
    t = TABLE[name]
    src = Image.open(os.path.join(SRC, t["src"]))
    flat = src.mode not in ("RGBA", "LA", "P") and "transparency" not in src.info
    im = src.convert("RGBA")
    w, h = im.size
    pre = dedither(im, t["dd"]) if t["dd"] else im
    pre = bleed(pre)
    up = esrgan(pre, t["model"])
    size = (max(1, round(w * t["scale"])), max(1, round(h * t["scale"])))
    out = resize_premul(up, size) if size != up.size else up
    if t["kit"] == "plate":   # the grey-plate / blue-rim family is painted again, layer by layer
        import platekit
        out = Image.fromarray(platekit.render(np.asarray(out), t["scale"], accent=t["accent"]), "RGBA")
    out = tidy_alpha(out)
    dst = os.path.join(OUT, t["out"])
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if flat:
        out = out.convert("RGB")
    if t["out"].endswith(".jpg"):
        out.convert("RGB").save(dst, "JPEG", quality=t["q"] or 92, optimize=True, progressive=True, subsampling=0)
    elif t["q"] is None:
        out.save(dst, "WEBP", lossless=True, method=6, exact=False)
    else:
        out.save(dst, "WEBP", quality=t["q"], method=6, alpha_quality=100)
    return src.size, out.size, os.path.getsize(dst)


def main(argv):
    load()
    if "--list" in argv:
        for n, t in TABLE.items():
            s = Image.open(os.path.join(SRC, t["src"])).size
            print(f"{n:22s} {t['src']:24s} {s[0]:5d}x{s[1]:<5d} x{t['scale']:<5} -> {t['out']}")
        return
    names = [a for a in argv if not a.startswith("--")] or list(TABLE)
    total = 0
    for n in names:
        (sw, sh), (ow, oh), b = make(n)
        total += b
        print(f"{n:22s} {sw}x{sh} -> {ow}x{oh}  {b // 1024} KB")
    print(f"{len(names)} assets, {total // 1024} KB")


if __name__ == "__main__":
    main(sys.argv[1:])
