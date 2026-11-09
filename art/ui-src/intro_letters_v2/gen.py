# The loading ident's letters, v2 (owner, 2026-11-08): instead of cutting the intro wordmark apart,
# every letter of SMUKIEZ is generated on its own - plus the swoosh under the word and a TM in the
# same brush hand - with OpenRouter's image model, the current wordmark (frontend/assets/
# intro_wordmark.webp, on black) as the style reference. build.py lays them out as one word.
# The key is read from the key file and never printed.
#   python gen.py <round> <piece,...> [quality]     pieces: S M U K i E Z swoosh tm
import base64, concurrent.futures as cf, io, json, os, re, sys, time, urllib.request, urllib.error
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
KEY_FILE = r'C:\Users\CooperHinkel\Documents\gamdevkey.txt'
REF_ART = os.path.join(ROOT, 'frontend', 'assets', 'intro_wordmark.webp')


def key():
    return re.findall(r'sk-or-[A-Za-z0-9_-]+', open(KEY_FILE, encoding='utf-8').read())[0]


def call(path, body, timeout=900):
    req = urllib.request.Request('https://openrouter.ai/api/v1' + path, data=json.dumps(body).encode(),
                                 headers={'Authorization': 'Bearer ' + key(), 'Content-Type': 'application/json',
                                          'User-Agent': 'smukiez-intro-letters/1.0', 'X-Title': 'Smukiez intro letters'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'HTTP {e.code}: {e.read().decode("utf-8", "replace")[:600]}')


def ref():
    im = Image.open(REF_ART).convert('RGBA')
    bg = Image.new('RGBA', im.size, (0, 0, 0, 255)); bg.alpha_composite(im)
    bg = bg.convert('RGB'); bg.thumbnail((1536, 1536))
    buf = io.BytesIO(); bg.save(buf, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


STYLE = (
    "Use the reference image only as the STYLE reference: it is the brand's own SMUKIEZ wordmark - white brush "
    "graffiti with a slight East-Asian brush-calligraphy feel: one loaded brush, thick confident strokes with "
    "tapered entries and exits, dry-brush split edges on some strokes, sharp flicked terminals, a few small round "
    "paint drips hanging off the bottom of strokes, a slight forward slant. Match that hand exactly - the same "
    "stroke weight, texture and slant - so this piece can stand beside the others as one word.\n\n"
    "Colour: pure solid white strokes only - no grey fills, no colour, no outline, no shadow, no glow, no 3D. "
    "Background: fully transparent. Nothing else in the image: no other letters, no frame, no texture, no text. "
)
PIECES = {
    'S': "Draw ONE single letter: a capital S, as in the reference - a big flowing S whose top stroke sweeps up to the "
         "right and whose bottom stroke ends in a long tapered tail sweeping down to the lower left, a drip under the "
         "top stroke. The letter fills about 80% of the image height, centred.",
    'M': "Draw ONE single letter: a capital M, as in the reference - two tall upright strokes joined by a sharp V in the "
         "middle, rough brush edges, a drip or two hanging off the bottoms of the uprights. The letter fills about 80% "
         "of the image height, centred.",
    'U': "Draw ONE single letter: a capital U, as in the reference - a rounded U with tall sides, the right side ending "
         "in a little flick at the bottom, a drip hanging off the bottom. The letter fills about 80% of the image height, "
         "centred.",
    'K': "Draw ONE single letter: a capital K, as in the reference - a tall upright stroke with a drip at its foot, a long "
         "arm flicking up to the upper right and a leg kicking down to the lower right. The letter fills about 80% of "
         "the image height, centred.",
    'i': "Draw ONE single letter: a lowercase i, as in the reference - a short upright brush stroke, a bit shorter than a "
         "capital, with its dot drawn as a short slanted slash above it. The whole letter (stroke and dot) fills about "
         "70% of the image height, centred.",
    'E': "Draw ONE single letter: a capital E, as in the reference - an upright stroke with three arms reaching to the "
         "right, the arms drawn as fast tapered brush strokes, a drip under one arm. The letter fills about 80% of the "
         "image height, centred.",
    'Z': "Draw ONE single letter: a capital Z, as in the reference - its top stroke runs to the right and ends in a sharp "
         "ARROWHEAD pointing up and to the right, a strong diagonal down to the lower left, and the bottom stroke sweeping "
         "out to the right, a drip hanging under the arrow. The letter fills about 80% of the image height, centred.",
    'swoosh': "Draw ONLY the swoosh line that runs under the word in the reference: one long, fast brush stroke that starts "
              "thin at the left, swells in the middle and tapers to a fine flicked point at the right, with a gentle "
              "upward curve and a little dry-brush splitting. No letters at all. It spans about 90% of the image width, "
              "centred vertically.",
    'tm': "Draw ONLY a small trademark sign: the two capital letters T and M side by side, hand-brushed in the same "
          "graffiti hand (quick confident strokes, a slight slant, rough brush edges), compact like a real TM mark. "
          "Nothing else. It fills about 60% of the image, centred.",
}
RATIO = {'swoosh': '16:9', 'tm': '3:2'}


def gen(rnd, v, quality):
    body = dict(model='openai/gpt-image-2.5-sunburst', prompt=PIECES[v] + "\n\n" + STYLE, quality=quality,
                background='transparent', output_format='png', aspect_ratio=RATIO.get(v, '1:1'), n=1,
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
    out = os.path.join(HERE, rnd, f'{v}.png')
    open(out, 'wb').write(base64.b64decode(r['data'][0]['b64_json']))
    im = Image.open(out)
    return dict(v=v, size=im.size, mode=im.mode, cost=(r.get('usage') or {}).get('cost'), secs=round(time.time() - t0, 1))


if __name__ == '__main__':
    rnd, vs = sys.argv[1], sys.argv[2].split(',')
    quality = sys.argv[3] if len(sys.argv) > 3 else 'high'
    os.makedirs(os.path.join(HERE, rnd), exist_ok=True)
    total = 0
    with cf.ThreadPoolExecutor(5) as ex:
        for res in ex.map(lambda v: gen(rnd, v, quality), vs):
            total += res.get('cost') or 0
            print(json.dumps(res), flush=True)
    print('batch cost $%.3f' % total)
