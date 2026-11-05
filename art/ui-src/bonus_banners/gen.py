# The bonus shop's card banners (owner, 2026-11-05, after the Tipsy Harvest shop): a night street scene
# in the game's own graffiti style (art/STYLE.md: charcoal brick, neon lime + violet), generated with no
# text and no icon, then the board's own scatter art (assets/flat/BS.webp, ES.webp) composited big in the
# middle on a pool of light - so the icon is the real symbol and no lettering can come out garbled.
#   python gen.py bg [fs,xfs]     backgrounds -> art/ui-src/bonus_banners/bg_<name>.png  (OpenRouter)
#   python gen.py comp [fs,xfs]   composite   -> frontend/assets/bonus/banner_<name>.webp (720x405)
# The key is read from the key file and never printed.
import base64, io, json, os, re, sys, urllib.request, urllib.error
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
KEY_FILE = r'C:\Users\CooperHinkel\Documents\gamdevkey.txt'
OUT = os.path.join(ROOT, 'frontend', 'assets', 'bonus')
W, H = 720, 405
ICON_H, ICON_W = .70, .80
ICONS = {'fs': os.path.join(ROOT, 'frontend', 'assets', 'flat', 'BS.webp'), 'xfs': os.path.join(ROOT, 'frontend', 'assets', 'flat', 'ES.webp')}
GLOW = {'fs': (108, 252, 84), 'xfs': (180, 84, 228)}

STYLE = ("Street-art slot game look: a night city scene painted like a premium graffiti mural illustration - charcoal "
         "brick and concrete (#18171c, #24222a, #34313b), neon-lime (#9CE424, glow #6CFC54) and violet (#B454E4, deep "
         "#6C24B4) spray paint and neon light, bold black outlines, wet paint drips, a thin cool cyan-white rim light. ")
COMMON = ("A wide 16:9 background scene for a mobile game shop card banner. {scene} Keep the MIDDLE of the picture open "
          "and simple (a soft glow of light there, nothing important) because a big game icon will be placed over the "
          "centre later; put the interesting details toward the left and right sides and the bottom. Absolutely NO "
          "text, no letters, no numbers, no logos, no signs with writing, no readable graffiti words, no frame, no "
          "border, no UI, no people. " + STYLE + "Full bleed, edge to edge.")
BG = {
    'fs': ("A back alley at night: a charcoal brick wall covered in abstract neon-LIME graffiti swirls and arrows "
           "(shapes only, no words), a dented trash can and a stack of spray-paint cans on the left, a fire escape "
           "and a dripping lime paint splash on the right, wet pavement reflecting lime light, a soft lime glow "
           "behind the middle."),
    'xfs': ("A rooftop at midnight over a dark city skyline: a purple-black stormy sky, a big pale moon low behind the "
            "middle with a violet glow, a water tower and a satellite dish on the left, a chain-link fence with violet "
            "spray-paint drips and a few floating violet smoke wisps on the right, neon violet light on the edges."),
}


def key():
    return re.findall(r'sk-or-[A-Za-z0-9_-]+', open(KEY_FILE, encoding='utf-8').read())[0]


def call(body):
    req = urllib.request.Request('https://openrouter.ai/api/v1/images', data=json.dumps(body).encode(),
                                 headers={'Authorization': 'Bearer ' + key(), 'Content-Type': 'application/json',
                                          'User-Agent': 'smukiez-banners/1.0', 'X-Title': 'Smukiez bonus banners'})
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'HTTP {e.code}: {e.read().decode("utf-8", "replace")[:500]}')


def gen_bg(name):
    body = dict(model='openai/gpt-image-2.5-sunburst', prompt=COMMON.format(scene=BG[name]), quality='high',
                output_format='png', aspect_ratio='16:9', n=1)
    r = call(body)
    open(os.path.join(HERE, f'bg_{name}.png'), 'wb').write(base64.b64decode(r['data'][0]['b64_json']))
    return (r.get('usage') or {}).get('cost')


def cover(im, w, h):
    k = max(w / im.size[0], h / im.size[1])
    im = im.resize((max(w, round(im.size[0] * k)), max(h, round(im.size[1] * k))), Image.LANCZOS)
    x, y = (im.size[0] - w) // 2, (im.size[1] - h) // 2
    return im.crop((x, y, x + w, y + h))


def comp(name):
    S = 2
    bg = cover(Image.open(os.path.join(HERE, f'bg_{name}.png')).convert('RGB'), W * S, H * S).convert('RGBA')
    icon = Image.open(ICONS[name]).convert('RGBA')
    icon = icon.crop(icon.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox())
    k = min(H * S * ICON_H / icon.size[1], W * S * ICON_W / icon.size[0])
    icon = icon.convert('RGBa').resize((round(icon.size[0] * k), round(icon.size[1] * k)), Image.LANCZOS).convert('RGBA')
    x, y = (W * S - icon.size[0]) // 2, (H * S - icon.size[1]) // 2
    yy, xx = np.mgrid[0:H * S, 0:W * S].astype(np.float32)
    d = np.hypot((xx - W * S / 2) / (W * S * .34), (yy - H * S / 2) / (H * S * .46))
    glow = Image.new('RGBA', bg.size, GLOW[name] + (0,))
    glow.putalpha(Image.fromarray((np.clip(1 - d, 0, 1) ** 1.6 * 150).astype(np.uint8), 'L'))
    bg.alpha_composite(glow)
    sh = Image.new('L', bg.size, 0)
    sh.paste(icon.getchannel('A').point(lambda v: int(v * .62)), (x + 7 * S, y + 11 * S))
    sh = sh.filter(ImageFilter.GaussianBlur(9 * S))
    bg.alpha_composite(Image.merge('RGBA', (Image.new('L', bg.size, 8),) * 3 + (sh,)))
    bg.alpha_composite(icon, (x, y))
    out = bg.convert('RGB').resize((W, H), Image.LANCZOS)
    os.makedirs(OUT, exist_ok=True)
    out.save(os.path.join(HERE, f'banner_{name}.png'))
    out.save(os.path.join(OUT, f'banner_{name}.webp'), 'WEBP', quality=88, method=6)
    return os.path.join(OUT, f'banner_{name}.webp')


if __name__ == '__main__':
    step = sys.argv[1]
    names = sys.argv[2].split(',') if len(sys.argv) > 2 else list(BG)
    for n in names:
        print(n, gen_bg(n) if step == 'bg' else comp(n), flush=True)
