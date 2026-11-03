"""OpenRouter helpers for the framed3 sound/image pass. The key is read from
Documents/gamdevkey.txt and never printed."""
import json, os, sys, time, urllib.request, urllib.error, base64

KEY_PATH = os.path.join(os.path.expanduser("~"), "Documents", "gamdevkey.txt")
BASE = "https://openrouter.ai/api/v1"


def _key():
    with open(KEY_PATH, "r", encoding="utf-8") as f:
        return f.read().strip()


def _req(path, body=None, method=None, timeout=240):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, method=method or ("POST" if body else "GET"))
    req.add_header("Authorization", "Bearer " + _key())
    req.add_header("X-Title", "smukiez slot sfx")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    return urllib.request.urlopen(req, timeout=timeout)


def credits():
    with _req("/credits") as r:
        d = json.load(r)["data"]
    return d["total_credits"] - d["total_usage"]


def speech(text, fmt="pcm", model="bytedance-seed/seed-audio-1-0", retries=3, **extra):
    """Returns (bytes, content_type)."""
    body = {"model": model, "input": text, "response_format": fmt}
    body.update(extra)
    last = None
    for a in range(retries):
        try:
            with _req("/audio/speech", body) as r:
                return r.read(), r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read()[:400]!r}"
            if e.code in (400, 401, 402, 403):
                break
        except Exception as e:  # timeouts, resets
            last = repr(e)
        time.sleep(3 + 4 * a)
    raise RuntimeError(last)


def image(prompt, model="openai/gpt-image-2.5-sunburst", retries=3, **extra):
    """Returns (png_bytes, cost)."""
    body = {"model": model, "prompt": prompt}
    body.update(extra)
    last = None
    for a in range(retries):
        try:
            with _req("/images", body, timeout=300) as r:
                d = json.load(r)
            img = d["data"][0]
            raw = base64.b64decode(img["b64_json"]) if img.get("b64_json") else urllib.request.urlopen(img["url"]).read()
            return raw, (d.get("usage") or {}).get("cost")
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read()[:400]!r}"
            if e.code in (400, 401, 402, 403):
                break
        except Exception as e:
            last = repr(e)
        time.sleep(3 + 4 * a)
    raise RuntimeError(last)
