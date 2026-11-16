r"""OpenRouter image calls for the lobby tile art. The key is read from %USERPROFILE%\.smukiez\openrouter-key.txt
and never printed or logged. Every call is appended to tools/media/ledger.jsonl (prompt, refs, size, cost)."""
import base64, io, json, os, time, urllib.error, urllib.request

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
KEY_FILE = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), ".smukiez", "openrouter-key.txt")
BASE = "https://openrouter.ai/api/v1"
LEDGER = os.path.join(HERE, "ledger.jsonl")


def _key():
    with open(KEY_FILE, encoding="utf-8") as fh:
        return fh.read().strip()


def call(path, body=None, timeout=900):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + _key(), "Content-Type": "application/json",
                                          "User-Agent": "smukiez-media/1.0", "X-Title": "Smukiez lobby tile"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:800]}")


def credit():
    c = call("/credits")["data"]
    return c["total_credits"] - c["total_usage"]


def ref(path, max_side=1536):
    im = Image.open(path).convert("RGBA")
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=94)
    return {"type": "image_url", "image_url": {"url": "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()}}


def generate(out, prompt, refs=(), aspect="2:3", transparent=False, model="openai/gpt-image-2.6-sunburst",
             quality="high", extra=None, tag=""):
    body = {"model": model, "prompt": prompt, "aspect_ratio": aspect, "quality": quality, "n": 1}
    if transparent:
        body["background"] = "transparent"
    if refs:
        body["input_references"] = [ref(r) for r in refs]
    if extra:
        body.update(extra)
    t0 = time.time()
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "tag": tag, "out": os.path.relpath(out, ROOT), "model": model,
           "aspect": aspect, "transparent": transparent, "extra": extra,
           "refs": [os.path.relpath(r, ROOT) for r in refs], "prompt": prompt}
    try:
        j = call("/images", body)
        item = j["data"][0]
        raw = base64.b64decode(item["b64_json"]) if item.get("b64_json") else urllib.request.urlopen(item["url"], timeout=120).read()
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "wb") as fh:
            fh.write(raw)
        im = Image.open(out)
        rec.update(size=im.size, mode=im.mode, cost=(j.get("usage") or {}).get("cost"), secs=round(time.time() - t0, 1))
        return out, rec
    except Exception as e:
        rec.update(error=str(e)[:600], secs=round(time.time() - t0, 1))
        raise
    finally:
        with open(LEDGER, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
