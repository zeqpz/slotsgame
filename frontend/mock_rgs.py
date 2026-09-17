"""Local stand-in for the Stake Engine RGS, for testing frontend/ before upload.

Implements the documented wallet protocol (authenticate / balance / play / end-round and
bet/event) over the game's real optimized books, and serves the frontend from the same
origin so no CORS is involved.

    .venv/Scripts/python.exe frontend/mock_rgs.py
    ->  http://localhost:8733/index.html?sessionID=test&rgs_url=http://localhost:8733&lang=en&device=desktop

Money follows the spec: integers with six decimal places, 1_000_000 == 1.00.
This is a test harness, not a wallet — balances live in memory and reset on restart.
"""

import bisect
import json
import os
import random
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import zstandard

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GAME = os.path.join(ROOT, "math-sdk", "games", "smukiez_tag_run")
PUBLISH = os.path.join(GAME, "library", "publish_files")
CACHE = os.path.join(GAME, "library", "beta_cache")

PORT = 8733
UNIT = 1_000_000
ID_RE = re.compile(rb'"id":\s*(\d+)')

MIME = {
    ".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".png": "image/png", ".mp4": "video/mp4",
    ".wav": "audio/wav", ".ttf": "font/ttf", ".otf": "font/otf", ".json": "application/json",
}

with open(os.path.join(PUBLISH, "index.json"), encoding="utf-8") as fh:
    MODES = {m["name"]: float(m["cost"]) for m in json.load(fh)["modes"]}

# Mirrors the ladder the live RGS actually serves, so the client is exercised against the
# real range rather than a convenient one.
BET_LEVELS = [
    10_000, 20_000, 50_000, 100_000, 200_000, 400_000, 600_000, 800_000, 1_000_000,
    1_200_000, 1_400_000, 1_600_000, 1_800_000, 2_000_000, 3_000_000, 4_000_000, 5_000_000,
    6_000_000, 7_000_000, 8_000_000, 9_000_000, 10_000_000, 12_000_000, 14_000_000,
    16_000_000, 18_000_000, 20_000_000, 30_000_000, 40_000_000, 50_000_000, 75_000_000,
    100_000_000, 150_000_000, 200_000_000, 250_000_000, 300_000_000, 350_000_000,
    400_000_000, 450_000_000, 500_000_000, 750_000_000, 1_000_000_000,
]

# sessionID -> wallet. A real RGS would own this; here it is just enough to exercise the client.
SESSIONS = {}


class Mode:
    """Draws a book from a mode's optimized lookup table, exactly as the RGS would."""

    def __init__(self, name):
        self.name = name
        self.jsonl = os.path.join(CACHE, f"books_{name}.jsonl")
        self.ids, self.cum, self.total, self.offsets = [], [], 0, {}

    def load(self):
        idx = self.jsonl + ".idx"
        if not (os.path.exists(self.jsonl) and os.path.exists(idx)):
            src = os.path.join(PUBLISH, f"books_{self.name}.jsonl.zst")
            print(f"[{self.name}] decompressing books (first run)...", flush=True)
            os.makedirs(CACHE, exist_ok=True)
            offsets, pos, buf = {}, 0, b""
            with open(src, "rb") as fh, open(self.jsonl, "wb") as out:
                reader = zstandard.ZstdDecompressor().stream_reader(fh)
                while True:
                    chunk = reader.read(1 << 20)
                    if not chunk:
                        break
                    buf += chunk
                    while True:
                        nl = buf.find(b"\n")
                        if nl < 0:
                            break
                        line, buf = buf[: nl + 1], buf[nl + 1 :]
                        m = ID_RE.search(line[:64])
                        if m:
                            offsets[int(m.group(1))] = pos
                        out.write(line)
                        pos += len(line)
                if buf.strip():
                    m = ID_RE.search(buf[:64])
                    if m:
                        offsets[int(m.group(1))] = pos
                    out.write(buf)
            with open(idx, "w", encoding="utf-8") as fh:
                json.dump(offsets, fh)
            self.offsets = offsets
        else:
            with open(idx, encoding="utf-8") as fh:
                self.offsets = {int(k): v for k, v in json.load(fh).items()}

        running = 0
        with open(os.path.join(PUBLISH, f"lookUpTable_{self.name}_0.csv"), encoding="utf-8") as fh:
            for line in fh:
                book_id, weight, _ = line.strip().split(",")
                weight = int(weight)
                if weight <= 0:
                    continue
                running += weight
                self.ids.append(int(book_id))
                self.cum.append(running)
        self.total = running
        print(f"[{self.name}] {len(self.offsets)} books, weight {running}", flush=True)

    def draw(self):
        roll = random.randrange(self.total)
        book_id = self.ids[bisect.bisect_right(self.cum, roll)]
        with open(self.jsonl, "rb") as fh:
            fh.seek(self.offsets[book_id])
            return json.loads(fh.readline())


LOADED = {}


START_BALANCE = 1_000_000 * UNIT   # test float; the real wallet governs on Stake


def wallet(session_id):
    """Currency can be pinned for testing by suffixing the session: 'test@XSC', 'test@XGC'."""
    currency = "USD"
    if "@" in session_id:
        currency = session_id.rsplit("@", 1)[1].upper() or "USD"
    return SESSIONS.setdefault(
        session_id,
        {"balance": START_BALANCE, "currency": currency, "round": None, "bet": 0, "mode": "base"},
    )


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype, cache="no-store"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json")

    def _err(self, code, status=400, message=None):
        self._json({"error": code, "message": message or code}, status)

    def do_OPTIONS(self):
        self._send(204, b"", "text/plain")

    def do_GET(self):
        path = urlparse(self.path).path
        # Bet Replay, exactly as the live RGS shapes it: unauthenticated, event = book id.
        if path.startswith("/bet/replay/"):
            parts = path.split("/")[3:]          # game, version, mode, event
            if len(parts) != 4 or parts[2] not in LOADED:
                return self._err("ERR_VAL", 400, "unknown mode")
            mode = LOADED[parts[2]]
            try:
                book_id = int(parts[3])
            except ValueError:
                return self._err("ERR_VAL", 400, "event must be an integer")
            if book_id not in mode.offsets:
                return self._json({"error": "ERR_GEN", "message": "no such event"}, 500)
            with open(mode.jsonl, "rb") as fh:
                fh.seek(mode.offsets[book_id])
                book = json.loads(fh.readline())
            return self._json({
                "state": book.get("events", []),
                "payoutMultiplier": book["payoutMultiplier"] / 100,
                "costMultiplier": MODES[parts[2]],
            })
        if path in ("/", "/index.html"):
            path = "/index.html"
        local = os.path.normpath(os.path.join(HERE, path.lstrip("/")))
        if not local.startswith(HERE) or not os.path.isfile(local):
            self._json({"error": "not found"}, 404)
            return
        ctype = MIME.get(os.path.splitext(local)[1].lower(), "application/octet-stream")
        with open(local, "rb") as fh:
            self._send(200, fh.read(), ctype)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return self._err("ERR_VAL")

        session_id = body.get("sessionID")
        if not session_id:
            return self._err("ERR_IS")
        w = wallet(session_id)
        bal = {"amount": w["balance"], "currency": w["currency"]}

        if path == "/wallet/authenticate":
            # The live RGS omits `round` entirely unless one is still open.
            out = {
                "balance": bal,
                "config": {
                    "minBet": BET_LEVELS[0],
                    "maxBet": BET_LEVELS[-1],
                    "stepBet": BET_LEVELS[0],
                    "defaultBetLevel": 1 * UNIT,
                    "betLevels": BET_LEVELS,
                    "gameModes": [
                        {"mode": name, "costMultiplier": cost, "maxBet": BET_LEVELS[-1]}
                        for name, cost in MODES.items()
                    ],
                    "jurisdiction": {"socialCasino": False, "disabledFullscreen": False, "disabledTurbo": False},
                },
            }
            if w["round"] is not None:
                out["round"] = w["round"]
            return self._json(out)

        if path == "/wallet/balance":
            return self._json({"balance": bal})

        if path == "/wallet/play":
            if w["round"] is not None:
                return self._err("ERR_VAL")           # a round is already open
            amount, mode = body.get("amount"), body.get("mode")
            if mode not in MODES or not isinstance(amount, int) or amount not in BET_LEVELS:
                return self._err("ERR_VAL")
            price = int(amount * MODES[mode])
            if price > w["balance"]:
                return self._err("ERR_IPB")
            w["balance"] -= price
            w["bet"], w["mode"] = amount, mode
            book = LOADED[mode].draw()
            # Shape it the way the live RGS does: the event stream is called `state`, the
            # round total is a plain multiple of the bet (the books store hundredths), and a
            # round that pays nothing is settled here and comes back inactive.
            mult = book["payoutMultiplier"] / 100
            payout = round(mult * amount)
            w["counter"] = w.get("counter", 52_600_000) + 1
            rnd = {
                "betID": w["counter"],
                "amount": amount,
                "payout": payout,
                "payoutMultiplier": mult,
                "active": payout > 0,
                "mode": mode,
                "state": book.get("events", []),
            }
            w["round"] = rnd if payout > 0 else None
            return self._json({"round": rnd, "balance": {"amount": w["balance"], "currency": w["currency"]}})

        if path == "/wallet/end-round":
            rnd = w["round"]
            if rnd is None:
                return self._err("ERR_VAL", message="player does not have active round")
            w["balance"] += rnd["payout"]
            w["round"] = None
            # end-round answers with the bare wallet, not a { balance: ... } envelope.
            return self._json({"amount": w["balance"], "currency": w["currency"]})

        if path == "/bet/event":
            return self._json({"event": body.get("event")})

        return self._json({"error": "not found"}, 404)


def main():
    for name in MODES:
        m = Mode(name)
        m.load()
        LOADED[name] = m
    url = (f"http://localhost:{PORT}/index.html?sessionID=test"
           f"&rgs_url=http://localhost:{PORT}&lang=en&device=desktop")
    print(f"\nMock RGS + game on {url}\n", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    sys.exit(main())
