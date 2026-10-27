"""Image generation for the character redo (openai/gpt-image-2.5-sunburst via OpenRouter).

Every call is logged to ledger.jsonl with its usage.cost; the running total is checked before each
call and nothing is sent once BUDGET would be passed. The key is read by orapi (never printed)."""
import base64, io, json, os, sys, time, threading
import concurrent.futures as cf
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from orapi import call
from PIL import Image

MODEL = 'openai/gpt-image-2.5-sunburst'
BUDGET = 15.0          # USD for this job
STOP_AT = 14.4         # leave headroom for one more image's cost
import paths
LEDGER = os.path.join(paths.SRC, 'ledger.jsonl')
OUT = os.path.join(paths.WORK, 'gen')
_lock = threading.Lock()

LIGHTING = ('Lighting: one key light from the upper left, in front of the subject; soft front fill; a thin '
            'cool pale-cyan rim light along the right and lower-right edges; core shadows and ambient '
            'occlusion on the lower-right side and in creases; any cast shadow falls down and to the right.')

STYLE = ('Art style: a hand-inked cartoon in a streetwear / graffiti sticker style, drawn by a professional '
         'illustrator: bold, confident black outlines with varied line weight (heavier on the outside edge and on '
         'the shadow side), rich form shading, fine material texture where it fits (knit ribs, cotton weave and '
         'stitching, denim or fleece texture, rubber and canvas on the sneakers), clean crisp colour fills and '
         'small extra details. No white sticker border: the black outline is the outer edge of the drawing. '
         'No other light sources and no coloured scene lighting.')


def spent():
    tot = 0.0
    if os.path.exists(LEDGER):
        for line in open(LEDGER, encoding='utf-8'):
            try:
                tot += float(json.loads(line).get('cost') or 0)
            except Exception:
                pass
    return tot


def data_url(path_or_img, max_side=None, bg=None):
    im = path_or_img if isinstance(path_or_img, Image.Image) else Image.open(path_or_img)
    im = im.convert('RGBA')
    if max_side and max(im.size) > max_side:
        s = max_side / max(im.size)
        im = im.resize((round(im.size[0] * s), round(im.size[1] * s)), Image.LANCZOS)
    if bg is not None:
        b = Image.new('RGBA', im.size, bg + (255,)); b.alpha_composite(im); im = b.convert('RGB')
    buf = io.BytesIO(); im.save(buf, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def generate(tag, name, prompt, refs=(), aspect='2:3', quality='high', background='transparent', n=1, ref_bg=None):
    """One request (n images). refs: list of image paths or PIL images. Returns list of saved paths."""
    with _lock:
        s = spent()
        if s >= STOP_AT:
            raise RuntimeError(f'budget stop: spent ${s:.3f} of ${BUDGET}')
    body = dict(model=MODEL, prompt=prompt, n=n, quality=quality, background=background, aspect_ratio=aspect)
    if refs:
        body['input_references'] = [{'type': 'image_url', 'image_url': {'url': data_url(r, 2048, ref_bg)}} for r in refs]
    t0 = time.time()
    err = None
    try:
        r = call('/images', body, timeout=900)
    except Exception as e:
        r = None; err = str(e)[:500]
    rec = dict(tag=tag, name=name, quality=quality, aspect=aspect, n=n, secs=round(time.time() - t0, 1))
    paths = []
    if r and r.get('data'):
        os.makedirs(os.path.join(OUT, tag), exist_ok=True)
        for i, d in enumerate(r['data']):
            raw = base64.b64decode(d['b64_json'])
            p = os.path.join(OUT, tag, f'{name}{"_" + str(i) if n > 1 else ""}.png')
            k = 1
            while os.path.exists(p):
                p = os.path.join(OUT, tag, f'{name}{"_" + str(i) if n > 1 else ""}_v{k}.png'); k += 1
            open(p, 'wb').write(raw)
            im = Image.open(p)
            paths.append(p)
            rec.setdefault('files', []).append([os.path.basename(p), im.size, im.mode])
        rec['cost'] = (r.get('usage') or {}).get('cost')
        rec['usage'] = {k: v for k, v in (r.get('usage') or {}).items() if k != 'cost'}
    else:
        rec['error'] = err or ('no data: ' + json.dumps(r)[:300])
        rec['cost'] = (r or {}).get('usage', {}).get('cost') if isinstance(r, dict) else None
    with _lock:
        open(LEDGER, 'a', encoding='utf-8').write(json.dumps(rec) + '\n')
        rec['total'] = round(spent(), 4)
    print(json.dumps(rec), flush=True)
    return paths


def run_many(jobs, workers=6):
    """jobs: list of dicts of generate() kwargs. Runs in parallel; returns {name: paths}."""
    out = {}
    with cf.ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(generate, **j): j['name'] for j in jobs}
        for f in cf.as_completed(futs):
            try:
                out[futs[f]] = f.result()
            except Exception as e:
                print('FAILED', futs[f], e, flush=True); out[futs[f]] = []
    print(f'ledger total ${spent():.3f}', flush=True)
    return out


if __name__ == '__main__':
    print(f'spent ${spent():.3f} of ${BUDGET}')
