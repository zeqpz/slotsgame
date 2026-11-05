"""The boy's parts at 4x: every cut part (art/blender/chars/boy/parts/*.png, master resolution) upscaled 4x with
the drawing kept exactly - no redraw, nothing moved:
  lines    Real-ESRGAN x4 line-art model (realesrgan-ncnn-vulkan, realesrgan-x4plus-anime) after a colour bleed
           under the transparent pixels: the ink and every edge come back sharp at 4x
  grain    that model paints cloth, knit and skin flat, so the fabric's own fine texture is put back: the detail
           of a plain Lanczos upscale (its high band, sigma 2.2 px at 4x) added over the model's picture away
           from the lines (where the model's edge is the one to keep)
  alpha    the model's alpha, never narrower than a sharpened Lanczos of the drawing's own, tidied
-> art/blender/chars/boy/parts_4x/<part>.png. parts.json (boxes in master px) stays the geometry: build_boy.py
maps the 4x textures onto the same planes. Uses tools/hires/upscale.py's helpers (read-only).
Run with the project venv python:  python tools/blender/chars/boy/hires_parts.py"""
import glob, os, sys
import numpy as np
import cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, os.path.join(ROOT, "tools", "hires"))
import upscale as U                                   # noqa: E402  (bleed, esrgan, tidy_alpha)

PARTS = os.path.join(ROOT, "art", "blender", "chars", "boy", "parts")
OUT = os.path.join(ROOT, "art", "blender", "chars", "boy", "parts_4x")
MODEL = "realesrgan-x4plus-anime"
GRAIN_SIGMA, GRAIN_GAIN = 2.2, 1.0


PAD = 8


def up4(im):
    """one RGBA part -> 4x (PIL RGBA). It is padded by 8 transparent px for the model and cropped back: at some
    sizes (thigh_l's 202 x 182) realesrgan-ncnn-vulkan returns an all-black picture"""
    W0, H0 = im.size
    padded = Image.new("RGBA", (W0 + 2 * PAD, H0 + 2 * PAD), (0, 0, 0, 0))
    padded.paste(im, (PAD, PAD))
    out = _up4(padded)
    return out.crop((4 * PAD, 4 * PAD, 4 * (PAD + W0), 4 * (PAD + H0)))


def _up4(im):
    b = U.bleed(im)
    lz = np.asarray(b.resize((im.width * 4, im.height * 4), Image.LANCZOS)).astype(np.float32) / 255
    for attempt in range(3):
        ai = np.asarray(U.esrgan(b, MODEL).resize((im.width * 4, im.height * 4), Image.LANCZOS)).astype(np.float32) / 255
        # the GPU model now and then hands back a near-black picture (it did for thigh_l): check it against the
        # plain upscale and run it again (fresh, not from the cache) if it went wrong
        m = lz[..., 3] > .8
        err = float(np.abs(ai[..., :3][m] - lz[..., :3][m]).mean()) if m.any() else 0.0
        if err < .08:
            break
        print("  Real-ESRGAN gave a bad picture (mean error %.3f), running it again" % err, flush=True)
        import hashlib
        key = hashlib.sha1(np.asarray(b.convert("RGBA")).tobytes() + repr((b.size, MODEL)).encode()).hexdigest()
        hit = os.path.join(U.CACHE, key + ".png")
        if os.path.exists(hit):
            os.remove(hit)
        if attempt == 1:                            # it fails the same way each time on some RGBA inputs: the colour
            rgb_up = np.asarray(U.esrgan(b.convert("RGB").convert("RGBA"), MODEL).resize(      # alone, alpha from
                (im.width * 4, im.height * 4), Image.LANCZOS)).astype(np.float32) / 255     # the Lanczos upscale
            ai = np.dstack([rgb_up[..., :3], np.clip((lz[..., 3] - .5) * 3 + .5, 0, 1)])
            err = float(np.abs(ai[..., :3][m] - lz[..., :3][m]).mean())
            print("  colour-only pass: mean error %.3f" % err, flush=True)
            if err < .08:
                break
    else:
        raise RuntimeError("Real-ESRGAN keeps failing on this part")
    grain = lz[..., :3] - cv2.GaussianBlur(lz[..., :3], (0, 0), GRAIN_SIGMA)
    lum = ai[..., :3].mean(-1)
    g = np.hypot(cv2.Sobel(lum, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(lum, cv2.CV_32F, 0, 1, ksize=3))
    edge = cv2.GaussianBlur((g > .35).astype(np.float32), (0, 0), 3.0)
    flat = np.clip(1 - 2.5 * edge, 0, 1)[..., None]
    rgb = np.clip(ai[..., :3] + grain * flat * GRAIN_GAIN, 0, 1)
    # the alpha: the model's, but never narrower than the drawing's own (a sharpened Lanczos of it) - the model
    # can pull an edge in by a px, which opened the head's hidden hairline under the beanie's brim
    al = np.maximum(ai[..., 3], np.clip((lz[..., 3] - .5) * 3 + .5, 0, 1))
    out = np.dstack([rgb, al])
    return U.tidy_alpha(Image.fromarray((out * 255 + .5).astype(np.uint8), "RGBA"))


def main():
    os.makedirs(OUT, exist_ok=True)
    only = sys.argv[1:]
    for f in sorted(glob.glob(os.path.join(PARTS, "*.png"))):
        n = os.path.splitext(os.path.basename(f))[0]
        if only and n not in only:
            continue
        im = Image.open(f).convert("RGBA")
        up4(im).save(os.path.join(OUT, n + ".png"))
        print(n, im.size, "-> x4", flush=True)


if __name__ == "__main__":
    main()
