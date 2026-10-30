"""Generate takes of a music cue with Google's Lyria 3 through OpenRouter.

  python tools/music/lyria.py base                  # one take, Lyria 3 Pro (a full song, ~$0.08)
  python tools/music/lyria.py intro total --takes 2 # two takes of each, all at once
  python tools/music/lyria.py menu --clip           # Lyria 3 Clip instead (30 s, ~$0.04)

The prompts are in cues.py. Takes land in %TEMP%/music_gen/<cue>/<stamp>_<n>.mp3 - what OpenRouter
sends back: MP3, 44.1 kHz stereo, 192 kbps - each with a .json beside it (model, prompt, cost). Copy
the keeper to art/music-src/<cue>.mp3 and run tools/music/build.py to cut it into the game's loop.

The key is read from %USERPROFILE%/.smukiez/openrouter-key.txt (never printed, never committed),
as tools/icon_redraw does.
"""
import base64, json, os, sys, tempfile, threading, time, urllib.error, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cues import CUES

KEY_FILE = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), ".smukiez", "openrouter-key.txt")
URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS = {"pro": "google/lyria-3-pro-preview", "clip": "google/lyria-3-clip-preview"}
OUT = os.path.join(tempfile.gettempdir(), "music_gen")


def generate(prompt, model):
    """One generation. Audio only comes back streamed: base64 pieces in each chunk's delta.audio.
    Returns (audio bytes, the model's text, usage)."""
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "modalities": ["text", "audio"], "stream": True}
    key = open(KEY_FILE, encoding="utf-8").read().strip()
    req = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"), headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json",
        "User-Agent": "smukiez-music/1.0", "X-Title": "Smukiez music"})
    audio, text, usage = [], [], None
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            for raw in r:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                ev = json.loads(data)
                if ev.get("error"):
                    raise RuntimeError(json.dumps(ev["error"])[:600])
                usage = ev.get("usage") or usage
                for ch in ev.get("choices", []):
                    d = ch.get("delta") or {}
                    if isinstance(d.get("content"), str):
                        text.append(d["content"])
                    if (d.get("audio") or {}).get("data"):
                        audio.append(d["audio"]["data"])
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:600]}")
    if not audio:
        raise RuntimeError(f"no audio came back (text: {''.join(text)[:200]!r})")
    return base64.b64decode("".join(audio)), "".join(text), usage


def take(cue, n, model, stamp, log):
    t0 = time.time()
    try:
        blob, text, usage = generate(CUES[cue]["prompt"], model)
    except Exception as e:
        log.append(f"{cue} take {n}: FAILED {e}")
        return
    d = os.path.join(OUT, cue); os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{stamp}_{n}.mp3")
    with open(path, "wb") as fh:
        fh.write(blob)
    with open(path[:-4] + ".json", "w", encoding="utf-8") as fh:
        json.dump({"cue": cue, "model": model, "prompt": CUES[cue]["prompt"], "text": text, "usage": usage}, fh, indent=1)
    log.append(f"{cue} take {n}: {path} ({len(blob) // 1024} KB, {time.time() - t0:.0f} s, ${(usage or {}).get('cost', '?')})")


def main(argv):
    model = MODELS["clip" if "--clip" in argv else "pro"]
    takes = int(argv[argv.index("--takes") + 1]) if "--takes" in argv else 1
    cues = [a for a in argv if a in CUES]
    if not cues:
        sys.exit(f"which cue? {', '.join(CUES)}")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    log = []
    jobs = [threading.Thread(target=take, args=(c, n + 1, model, stamp, log)) for c in cues for n in range(takes)]
    for j in jobs:
        j.start()
    for j in jobs:
        j.join()
    print("\n".join(sorted(log)))


if __name__ == "__main__":
    main(sys.argv[1:])
