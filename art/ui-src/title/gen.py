# The game title logo (owner, 2026-11-08): SMUKIEZ & SKELLY in the style of the SMUKIEZ wall tag
# (frontend/assets/wall_tag.webp as the style reference), transparent, generated with OpenRouter's image model
# (the same call as intro_wordmark/gen.py). The key is read from the key file and never printed.
#   python gen.py <tag> <variant,...> [quality]
import base64, concurrent.futures as cf, io, json, os, re, sys, time, urllib.request, urllib.error
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
KEY_FILE = r'C:\Users\CooperHinkel\Documents\gamdevkey.txt'
TAG_ART = os.path.join(ROOT, 'frontend', 'assets', 'wall_tag.webp')


def key():
    return re.findall(r'sk-or-[A-Za-z0-9_-]+', open(KEY_FILE, encoding='utf-8').read())[0]


def call(path, body, timeout=900):
    req = urllib.request.Request('https://openrouter.ai/api/v1' + path, data=json.dumps(body).encode(),
                                 headers={'Authorization': 'Bearer ' + key(), 'Content-Type': 'application/json',
                                          'User-Agent': 'smukiez-title/1.0', 'X-Title': 'Smukiez title logo'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'HTTP {e.code}: {e.read().decode("utf-8", "replace")[:600]}')


def ref():
    im = Image.open(TAG_ART).convert('RGBA')
    im.thumbnail((1536, 1536))
    buf = io.BytesIO(); im.save(buf, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


BASE = (
    "Design the game title logo for a street-art slot game. It reads exactly SMUKIEZ & SKELLY - the word SMUKIEZ "
    "(7 letters: S M U K I E Z), an ampersand, then the word SKELLY (6 letters: S K E L L Y). Use the reference image "
    "as the STYLE reference: it is the brand's own SMUKIEZ wall tag - match it closely: chunky wildstyle graffiti "
    "letters with sharp arrow terminals, glossy gradient fills in lime green, violet purple and hot pink with white "
    "highlights, a thick black outline around every letter, a bright neon-green outer edge line, and a few glossy "
    "paint drips hanging off the bottoms. {extra} The spelling must be exactly SMUKIEZ & SKELLY and readable at a "
    "glance: every letter legible, no extra or missing letters, nothing overlapping that hides a letter. Premium "
    "game-logo finish, crisp edges. "
    "Background: fully transparent - no wall, no bricks, no texture, no shadow on a background, nothing else in the "
    "image (no frame, no extra text, no characters). The logo centred with generous empty margins all round."
)
VARIANTS = {
    'a': "Stack it in two lines: SMUKIEZ large on top, and below it a smaller ampersand followed by SKELLY, centred.",
    'b': "Stack it in two lines: SMUKIEZ on top, SKELLY below at the same size, with a big bold ampersand tucked "
         "between and overlapping the two lines at the left, like a sticker.",
    'c': "One single line: SMUKIEZ & SKELLY, the ampersand smaller and slightly raised between the two words.",
}


def gen(tag, v, quality):
    body = dict(model='openai/gpt-image-2.5-sunburst', prompt=BASE.format(extra=VARIANTS[v]), quality=quality,
                background='transparent', output_format='png', aspect_ratio=('16:9' if v == 'c' else '3:2'), n=1,
                input_references=[{'type': 'image_url', 'image_url': {'url': ref()}}])
    t0 = time.time()
    for attempt in range(3):
        try:
            r = call('/images', body)
            break
        except Exception as e:
            err = str(e)
            if 'aspect_ratio' in err and body.get('aspect_ratio') == '16:9':
                body['aspect_ratio'] = '3:2'; continue
            if attempt == 2 or not any(s in err for s in ('HTTP 502', 'HTTP 503', 'HTTP 429', 'timed out')):
                return dict(v=v, error=err[:400])
            time.sleep(8)
    out = os.path.join(HERE, tag, f'{v}.png')
    open(out, 'wb').write(base64.b64decode(r['data'][0]['b64_json']))
    im = Image.open(out)
    return dict(v=v, size=im.size, mode=im.mode, cost=(r.get('usage') or {}).get('cost'), secs=round(time.time() - t0, 1),
                ratio=body['aspect_ratio'])


if __name__ == '__main__':
    tag, vs = sys.argv[1], sys.argv[2].split(',')
    quality = sys.argv[3] if len(sys.argv) > 3 else 'high'
    os.makedirs(os.path.join(HERE, tag), exist_ok=True)
    total = 0
    with cf.ThreadPoolExecutor(4) as ex:
        for res in ex.map(lambda v: gen(tag, v, quality), vs):
            total += res.get('cost') or 0
            print(json.dumps(res), flush=True)
    print('batch cost $%.3f' % total)
