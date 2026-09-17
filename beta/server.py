"""Smukiez Tag Run — playable beta server.

Mimics the Stake Engine RGS locally: draws a book id from each mode's *optimized*
lookup table (so live odds are the real 96.5% RTP math) and returns that book's full
event list for the client to animate. Play-money only.

First run decompresses the published books into library/beta_cache/ and builds a
byte-offset index per mode (~30s); later runs start instantly.

Run:  python beta/server.py   ->  http://localhost:8722
"""

import bisect
import json
import os
import random
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import zstandard

BETA_DIR = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.join(os.path.dirname(BETA_DIR), "math-sdk", "games", "smukiez_tag_run")
PUBLISH_DIR = os.path.join(GAME_DIR, "library", "publish_files")
CACHE_DIR = os.path.join(GAME_DIR, "library", "beta_cache")

MODES = {"base": 1.0, "bonus": 100.0, "extremebonus": 400.0}
PORT = 8722
ID_RE = re.compile(rb'"id":\s*(\d+)')


class ModeData:
    def __init__(self, name: str, cost: float):
        self.name = name
        self.cost = cost
        self.jsonl_path = os.path.join(CACHE_DIR, f"books_{name}.jsonl")
        self.ids = []
        self.cum_weights = []
        self.total_weight = 0
        self.offsets = {}

    def build_cache(self):
        src = os.path.join(PUBLISH_DIR, f"books_{self.name}.jsonl.zst")
        idx_path = self.jsonl_path + ".idx"
        if not (os.path.exists(self.jsonl_path) and os.path.exists(idx_path)):
            print(f"[{self.name}] decompressing books + building index...", flush=True)
            os.makedirs(CACHE_DIR, exist_ok=True)
            offsets = {}
            pos = 0
            with open(src, "rb") as fh, open(self.jsonl_path, "wb") as out:
                reader = zstandard.ZstdDecompressor().stream_reader(fh)
                buf = b""
                while True:
                    chunk = reader.read(1 << 20)
                    if not chunk:
                        break
                    buf += chunk
                    while True:
                        nl = buf.find(b"\n")
                        if nl < 0:
                            break
                        line = buf[: nl + 1]
                        buf = buf[nl + 1 :]
                        match = ID_RE.search(line[:64])
                        if match:
                            offsets[int(match.group(1))] = pos
                        out.write(line)
                        pos += len(line)
                if buf.strip():
                    match = ID_RE.search(buf[:64])
                    if match:
                        offsets[int(match.group(1))] = pos
                    out.write(buf)
            with open(idx_path, "w", encoding="utf-8") as f:
                json.dump(offsets, f)
            self.offsets = offsets
        else:
            with open(idx_path, encoding="utf-8") as f:
                self.offsets = {int(k): v for k, v in json.load(f).items()}
        print(f"[{self.name}] {len(self.offsets)} books indexed", flush=True)

    def load_lut(self):
        lut = os.path.join(PUBLISH_DIR, f"lookUpTable_{self.name}_0.csv")
        running = 0
        with open(lut, encoding="utf-8") as f:
            for line in f:
                book_id, weight, _ = line.strip().split(",")
                weight = int(weight)
                if weight <= 0:
                    continue
                running += weight
                self.ids.append(int(book_id))
                self.cum_weights.append(running)
        self.total_weight = running
        print(f"[{self.name}] lut loaded, total weight {running}", flush=True)

    def draw(self) -> dict:
        roll = random.randrange(self.total_weight)
        book_id = self.ids[bisect.bisect_right(self.cum_weights, roll)]
        with open(self.jsonl_path, "rb") as f:
            f.seek(self.offsets[book_id])
            line = f.readline()
        return json.loads(line)


MODE_DATA = {}
STRIPS = {}


def load_strips():
    """Real reel strips, served so the client's spin-through shows authentic symbols."""
    reels_dir = os.path.join(GAME_DIR, "reels")
    for key, fname in (("basegame", "BR0.csv"), ("freegame", "FR0.csv")):
        cols = [[] for _ in range(5)]
        with open(os.path.join(reels_dir, fname), encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) == 5:
                    for i, sym in enumerate(parts):
                        cols[i].append(sym)
        STRIPS[key] = cols


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code: int, body: bytes, ctype: str, cache: str = "no-store"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json")

    def do_OPTIONS(self):
        # CORS + Private Network Access preflight for the devsave helper
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Max-Age", "600")
        self.end_headers()

    def do_POST(self):
        # dev helper: lets a browser page save pulled live-game files locally
        url = urlparse(self.path)
        if url.path == "/api/devsave":
            name = os.path.basename(parse_qs(url.query).get("name", [""])[0])
            if not name:
                self._json({"error": "name required"}, 400)
                return
            length = min(int(self.headers.get("Content-Length", 0)), 30 * 1024 * 1024)
            body = self.rfile.read(length)
            out_dir = os.path.join(os.path.dirname(BETA_DIR), "live-pull", "v10")
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, name), "wb") as f:
                f.write(body)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            body_out = json.dumps({"saved": name, "bytes": length}).encode()
            self.send_header("Content-Length", str(len(body_out)))
            self.end_headers()
            self.wfile.write(body_out)
        else:
            self._json({"error": "not found"}, 404)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            with open(os.path.join(BETA_DIR, "index.html"), "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        elif url.path.startswith("/assets/"):
            name = os.path.basename(url.path)  # basename strips any traversal
            path = os.path.join(BETA_DIR, "assets", name)
            if name.lower().endswith(".png") and os.path.exists(path):
                with open(path, "rb") as f:
                    self._send(200, f.read(), "image/png", cache="public, max-age=3600")
            else:
                self._json({"error": "asset not found"}, 404)
        elif url.path == "/api/strips":
            self._json(STRIPS)
        elif url.path == "/api/config":
            self._json(
                {
                    "modes": [{"name": n, "cost": c} for n, c in MODES.items()],
                    "wincap": 5000,
                    "books": {n: len(d.offsets) for n, d in MODE_DATA.items()},
                }
            )
        elif url.path == "/api/play":
            params = parse_qs(url.query)
            mode = params.get("mode", ["base"])[0]
            if mode not in MODE_DATA:
                self._json({"error": f"unknown mode {mode}"}, 400)
                return
            data = MODE_DATA[mode]
            forced = params.get("id", [None])[0]
            if forced is not None:  # debug replay of a specific book
                book_id = int(forced)
                if book_id not in data.offsets:
                    self._json({"error": f"book {book_id} not in mode {mode}"}, 400)
                    return
                with open(data.jsonl_path, "rb") as f:
                    f.seek(data.offsets[book_id])
                    book = json.loads(f.readline())
            else:
                book = data.draw()
            self._json({"mode": mode, "cost": data.cost, "book": book})
        else:
            self._json({"error": "not found"}, 404)


def main():
    load_strips()
    for name, cost in MODES.items():
        data = ModeData(name, cost)
        data.build_cache()
        data.load_lut()
        MODE_DATA[name] = data
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Smukiez beta running on http://localhost:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    sys.exit(main())
