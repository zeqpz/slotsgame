# Builds the intro ident's wordmark assets from the chosen generation (r1/b_seal.png, see gen.py):
#   frontend/assets/intro_wordmark.webp       white strokes on transparent, ~2400 px wide
#   frontend/assets/intro_wordmark_glow.webp  its soft white bloom, on the same canvas
# Steps: strokes forced pure white (alpha kept), cropped to the strokes, Real-ESRGAN x4 (the hires
# tool's own pass) and Lanczos down to the output width with premultiplied alpha, alpha tidied; the
# glow is the alpha blurred at two radii. Run with the art venv (Pillow, numpy).
import os, sys
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'hires'))
import upscale as hx

SRC = os.path.join(HERE, 'r1', 'b_seal.png')
OUT = os.path.join(ROOT, 'frontend', 'assets')
WIDTH = 2400      # the strokes' width in the output
PAD = 0.07        # room round the strokes for the glow, as a fraction of the width

im = Image.open(SRC).convert('RGBA')
a = np.asarray(im).astype(np.float32)
al = a[..., 3] * (a[..., :3].mean(-1) / 255.0) ** 0.5   # any grey edge the model left counts as thinner paint
al[al < 6] = 0
white = np.dstack([np.full(al.shape + (3,), 255, np.float32), al]).astype(np.uint8)
im = Image.fromarray(white, 'RGBA')
im = im.crop(im.getbbox())
big = hx.esrgan(hx.bleed(im), hx.A)
h = round(WIDTH * im.height / im.width)
strokes = hx.tidy_alpha(hx.resize_premul(big, (WIDTH, h)))
# pure white everywhere (the model's x4 can tint an edge), alpha as resampled
s = np.asarray(strokes).copy(); s[..., :3] = 255; strokes = Image.fromarray(s, 'RGBA')
p = round(WIDTH * PAD)
canvas = Image.new('RGBA', (WIDTH + 2 * p, h + 2 * p), (255, 255, 255, 0))
canvas.alpha_composite(strokes, (p, p))
canvas.save(os.path.join(OUT, 'intro_wordmark.webp'), 'WEBP', lossless=True, quality=100, method=6)
# the glow: a tight halo and a wide bloom from the strokes' alpha, white
A = Image.fromarray(np.asarray(canvas)[..., 3])
near = np.asarray(A.filter(ImageFilter.GaussianBlur(10)), np.float32)
far = np.asarray(A.filter(ImageFilter.GaussianBlur(42)), np.float32)
g = np.clip(near * .9 + far * 1.6, 0, 255)
glow = np.dstack([np.full(g.shape + (3,), 255, np.uint8), g.astype(np.uint8)])
Image.fromarray(glow, 'RGBA').resize((canvas.width // 2, canvas.height // 2), Image.LANCZOS).save(   # a blur: half the pixels is plenty
    os.path.join(OUT, 'intro_wordmark_glow.webp'), 'WEBP', quality=80, alpha_quality=80, method=6)
for n in ('intro_wordmark.webp', 'intro_wordmark_glow.webp'):
    f = os.path.join(OUT, n)
    print(n, Image.open(f).size, os.path.getsize(f) // 1024, 'KB')
