# The intro ident's wordmark (owner, 2026-11-03): SMUKIEZ in his graffiti style with a slight Asian
# brush-calligraphy feel, white strokes on transparent, generated with OpenRouter's image model
# (the same call as tools/icon_redraw). The key is read from the key file and never printed.
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
                                          'User-Agent': 'smukiez-intro/1.0', 'X-Title': 'Smukiez intro wordmark'})
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
    "Design a single-line wordmark logo that reads exactly SMUKIEZ (7 letters: S M U K I E Z), for the cinematic "
    "studio intro of a street-art slot game. Use the reference image only as the STYLE reference: it is the brand's "
    "own graffiti tag of the same word - keep its attitude: sharp arrow terminals, flowing connected strokes, a "
    "confident hand-style, a few small paint drips. Blend in a slight East-Asian brush-calligraphy feel: strokes "
    "laid with a loaded ink brush - tapered entries and exits, dry-brush split edges on a few strokes, energetic "
    "sumi-ink movement. {extra} The word must stay clearly readable as SMUKIEZ at a glance - letterforms legible, "
    "evenly spaced, nothing overlapping that hides a letter. Premium, elegant, unique, cinematic.\n\n"
    "Colour: MONOCHROME ONLY - every stroke pure solid white, no colours, no grey fills, no gradients, no outlines in "
    "another colour, no 3D extrusion, no shadow, no glow. Background: fully transparent. Wide composition, the word "
    "centred with generous empty margins all round; nothing else in the image (no frame, no texture, no extra text)."
)
VARIANTS = {
    'a': "Add one small square seal-stamp accent (a hanko-style chop with a simple abstract mark, no readable "
         "characters) tucked after the last letter.",
    'b': "Keep it lean and fast: long tapered brush tails on the S and the Z, a subtle underline flick, no seal.",
    'c': "Make the letters bold and flowing like a tag, with one long brush swash running under the whole word and "
         "a tiny square seal stamp (no readable characters) at its end.",
    'd': "Letters connected in one continuous brush movement, crisp and premium, with very sparse dry-brush texture, "
         "no seal.",
}


def gen(tag, v, quality):
    body = dict(model='openai/gpt-image-2.5-sunburst', prompt=BASE.format(extra=VARIANTS[v]), quality=quality,
                background='transparent', output_format='png', aspect_ratio='16:9', n=1,
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
