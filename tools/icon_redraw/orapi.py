# OpenRouter helpers for the icon redraw. The key is read from the user's key file and never printed.
import json, os, urllib.request, urllib.error

KEY_FILE = os.path.join(os.environ.get('USERPROFILE', os.path.expanduser('~')), '.smukiez', 'openrouter-key.txt')
BASE = 'https://openrouter.ai/api/v1'


def _key():
    return open(KEY_FILE, encoding='utf-8').read().strip()


def call(path, body=None, timeout=600):
    """GET (body None) or POST JSON to the OpenRouter API; returns the parsed JSON or raises
    RuntimeError with the HTTP status and the server's error text."""
    req = urllib.request.Request(
        BASE + path,
        data=None if body is None else json.dumps(body).encode('utf-8'),
        headers={'Authorization': 'Bearer ' + _key(), 'Content-Type': 'application/json',
                 'User-Agent': 'smukiez-icons/1.0', 'X-Title': 'Smukiez icon redraw'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'HTTP {e.code}: {e.read().decode("utf-8", "replace")[:600]}')
