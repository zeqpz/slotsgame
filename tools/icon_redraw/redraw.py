"""Redraw slot icons with GPT Image 2.5 Sunburst (OpenRouter), keeping each drawing where it is.

  python tools/icon_redraw/redraw.py <tag> <ID,ID..|all> [quality]   -> %TEMP%/icon_redraw/<tag>/<ID>.png
  python tools/icon_redraw/install.py <tag> <ID,ID..|all> [--dry]    -> art/icons-src/<ID>.png (old drawing kept in geom/)

then tools/icon_rigs/build.py, tools/make_flat_icons.py and tools/make_tier_glow.py. See README.md.
The prompt is art/STYLE.md in words: the same drawing with more detail, the shared lighting, a plain
white sticker edge (the tiers' glow is the game's), a transparent background. The key is read from
%USERPROFILE%/.smukiez/openrouter-key.txt by orapi.py and never printed.
"""
import base64, io, json, os, sys, time, tempfile
import concurrent.futures as cf
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from orapi import call
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, 'art', 'icons-src')
OUT = os.path.join(tempfile.gettempdir(), 'icon_redraw')   # raw model output: not shipped, not kept in the repo

SUBJECT = {
    'H1': 'a tied cloth money bag with a brown rope round its neck and a green dollar sign on the front',
    'H2': 'a black semi-automatic pistol seen from the side',
    'H3': 'a gold Cuban-link chain necklace with a small engraved clasp',
    'H4': 'a pair of black-and-white high-top sneakers hanging by their laces',
    'H5': 'a silver retro boombox with two big speakers and a cassette deck',
    'H6': 'a skateboard with a blue graffiti deck graphic, black trucks and white wheels',
    'H7': 'an open grey cardboard box with a graffiti tag on its side',
    'L1': 'a bright green spray-paint can spraying a puff of green paint from its nozzle',
    'L2': 'a black paint marker with an orange scribble stroke behind it',
    'L3': 'a grey knit beanie with a white graffiti tag on its cuff',
    'L4': 'two hanging clothing price tags with graffiti lettering, on a string loop',
    'L5': 'a pair of orange-red dice with white pips',
    'L6': 'a camouflage T-shirt with a white graffiti tag across the chest',
    'L7': 'a black hoodie with a grey graffiti tag across the chest',
    'L8': 'a clear zip-lock plastic bag holding green herb buds',
    'L9': 'a white subway train car with a big colourful graffiti piece on its side',
    'L10': 'a light-blue 1960s lowrider car bouncing up on its hydraulics, front end raised',
    'M': 'a section of a cracked red brick wall',
    'BS': 'the letters FS in dripping lime-green graffiti bubble letters',
    'ES': 'the letters XFS in dripping purple graffiti bubble letters',
}

ALL = ['H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'H7', 'L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8', 'L9', 'L10', 'M', 'BS', 'ES']
TOP, PREMIUM = {'H1', 'H2', 'H3'}, {'H4', 'H5', 'H6', 'H7'}

LIGHT = ('Lighting: one key light from the upper left, in front of the subject; soft front fill; a thin cool pale-cyan '
         'rim light along the right and lower-right edges; core shadows and ambient occlusion on the lower-right side '
         'and in creases; any cast shadow falls down and to the right.')


def edge(icon, foil=False):
    # the owner turned the foil edges down (off style): every icon is white, the game draws the tier glow
    if not foil:
        return 'The sticker border is plain matte white vinyl, thick and even.'
    if icon in TOP:
        return ('The sticker border is GOLD FOIL instead of white: a thick, even, metallic gold die-cut edge with a bright '
                'specular highlight on its upper left and two or three small star glints - it marks a top-paying symbol.')
    if icon in PREMIUM:
        return ('The sticker border is CHROME / SILVER FOIL instead of white: a thick, even, mirror-polished silver die-cut '
                'edge with a crisp highlight on its upper left - it marks a premium symbol.')
    return 'The sticker border is plain matte white vinyl, thick and even.'


def prompt(icon):
    return (
        f'Redraw this slot-machine symbol as a high-end, professionally illustrated version of the same drawing: {SUBJECT[icon]}.\n\n'
        'Keep it the same drawing: the same object, design and pose, the same proportions and composition, the same size and '
        'position in the frame, the same colours, and any lettering or graffiti tags kept as they are. It must line up with '
        'the original when laid on top of it.\n\n'
        'Keep the art style: a bold hand-inked cartoon sticker with a streetwear / graffiti feel, thick confident black '
        'outlines with varied line weight, and a thick, even die-cut sticker border around the whole outer silhouette. '
        + edge(icon) + '\n\n'
        'Make it much better: far more detail and richer lighting - soft form shading and clear core shadows, ambient '
        'occlusion where parts meet, crisp glossy highlights and reflections on shiny surfaces, fine material texture where '
        'it fits (fabric weave and stitching, leather grain, brushed or worn metal, paper fibres, spray-paint grain), cleaner '
        'linework, and small extra details that suit the object.\n\n' + LIGHT + '\n\n'
        'Background: fully transparent around the sticker. No cast shadow on the ground, no glow, nothing else in the image.')


def ref(icon):
    """The icon as the reference image, on a canvas of a ratio the model offers (the scatters are wide)."""
    geom = os.path.join(SRC, 'geom', icon + '.png')
    im = Image.open(geom if os.path.exists(geom) else os.path.join(SRC, icon + '.png')).convert('RGBA')
    W, H = im.size
    ratio = '1:1' if W == H else '4:3'
    if ratio == '4:3':
        cw = max(W, round(H * 4 / 3)); ch = round(cw * 3 / 4)
        if ch < H: ch = H; cw = round(ch * 4 / 3)
        can = Image.new('RGBA', (cw, ch), (0, 0, 0, 0)); can.paste(im, ((cw - W) // 2, (ch - H) // 2)); im = can
    buf = io.BytesIO(); im.save(buf, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode(), ratio


def gen(tag, icon, quality):
    url, ratio = ref(icon)
    body = dict(model='openai/gpt-image-2.5-sunburst', prompt=prompt(icon), quality=quality, background='transparent',
                output_format='png', aspect_ratio=ratio, n=1,
                input_references=[{'type': 'image_url', 'image_url': {'url': url}}])
    t0 = time.time()
    for attempt in range(3):
        try:
            r = call('/images', body, timeout=900)
            break
        except Exception as e:
            err = str(e)
            if attempt == 2 or not any(s in err for s in ('HTTP 502', 'HTTP 503', 'HTTP 429', 'timed out')):
                return dict(icon=icon, error=err[:400], secs=round(time.time() - t0, 1))
            time.sleep(8)
    d = r['data'][0]
    out = os.path.join(OUT, tag, f'{icon}.png')
    open(out, 'wb').write(base64.b64decode(d['b64_json']))
    im = Image.open(out)
    return dict(icon=icon, size=im.size, mode=im.mode, cost=(r.get('usage') or {}).get('cost'), secs=round(time.time() - t0, 1))


if __name__ == '__main__':
    tag = sys.argv[1]
    icons = ALL if sys.argv[2] == 'all' else sys.argv[2].split(',')
    quality = sys.argv[3] if len(sys.argv) > 3 else 'high'
    os.makedirs(os.path.join(OUT, tag), exist_ok=True)
    total = 0
    with cf.ThreadPoolExecutor(6) as ex, open(os.path.join(OUT, tag, 'log.jsonl'), 'a') as log:
        for res in ex.map(lambda i: gen(tag, i, quality), icons):
            total += res.get('cost') or 0
            print(json.dumps(res), flush=True); log.write(json.dumps(res) + '\n')
    print('batch cost $%.3f' % total)
