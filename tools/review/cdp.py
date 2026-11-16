"""Minimal headless-Chrome driver over the DevTools protocol, stdlib only (review tooling).

Ported from zeqpz/fallslotsga tools/review (2026-11-16); used by the review checks next to it. Starts its own Chrome on a random port
in 9400-9800 with a throwaway profile and kills only that process on close().
"""
import base64, json, os, random, shutil, socket, struct, subprocess, tempfile, time, urllib.request
from pathlib import Path

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
MOCK = "http://localhost:8733"


class WS:
    def __init__(self, url):
        host, rest = url[5:].split("/", 1)
        h, p = host.split(":")
        self.s = socket.create_connection((h, int(p)))
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET /{rest} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                        f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.s.recv(4096)
        self.buf = buf.split(b"\r\n\r\n", 1)[1]
        self.id = 0
        self.events = []

    def _recv(self, n):
        while len(self.buf) < n:
            c = self.s.recv(1 << 20)
            if not c:
                raise EOFError
            self.buf += c
        d, self.buf = self.buf[:n], self.buf[n:]
        return d

    def send(self, obj):
        data = json.dumps(obj).encode()
        hdr = bytearray([0x81])
        n = len(data)
        if n < 126:
            hdr.append(0x80 | n)
        elif n < 65536:
            hdr.append(0x80 | 126); hdr += struct.pack(">H", n)
        else:
            hdr.append(0x80 | 127); hdr += struct.pack(">Q", n)
        mask = os.urandom(4)
        self.s.sendall(bytes(hdr) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self):
        msg = b""
        while True:
            b0, b1 = self._recv(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._recv(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._recv(8))[0]
            msg += self._recv(n)
            if b0 & 0x80:
                return json.loads(msg)

    def call(self, method, **params):
        self.id += 1
        self.send({"id": self.id, "method": method, "params": params})
        while True:
            m = self.recv()
            if m.get("id") == self.id:
                if "error" in m:
                    raise RuntimeError(m["error"])
                return m.get("result", {})
            if "method" in m:
                self.events.append(m)


class Browser:
    def __init__(self, w=1200, h=675):
        self.port = random.randint(9400, 9800)
        self.prof = tempfile.mkdtemp(prefix="review_chrome_")
        self.proc = subprocess.Popen(
            [CHROME, "--headless=new", f"--remote-debugging-port={self.port}", f"--user-data-dir={self.prof}",
             f"--window-size={w},{h}", "--no-first-run", "--hide-scrollbars", "--mute-audio",
             "--autoplay-policy=no-user-gesture-required", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        tabs = None
        for _ in range(150):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json"))
                break
            except Exception:
                time.sleep(.2)
        page = next(t for t in tabs if t["type"] == "page")
        self.ws = WS(page["webSocketDebuggerUrl"])
        self.ws.call("Page.enable"); self.ws.call("Runtime.enable"); self.ws.call("Log.enable")
        self.size(w, h)

    def size(self, w, h):
        self.w, self.h = w, h
        self.ws.call("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=1, mobile=w < h)

    def open(self, url, settle=1.0):
        self.ws.events.clear()
        self.ws.call("Page.navigate", url=url)
        time.sleep(settle)

    def preload(self, source):
        """Run `source` in every page before its own scripts (returns an id for unpreload)."""
        return self.ws.call("Page.addScriptToEvaluateOnNewDocument", source=source)["identifier"]

    def unpreload(self, ident):
        self.ws.call("Page.removeScriptToEvaluateOnNewDocument", identifier=ident)

    def js(self, expr, await_=True):
        r = self.ws.call("Runtime.evaluate", expression=expr, awaitPromise=await_, returnByValue=True)
        if "exceptionDetails" in r:
            raise RuntimeError(json.dumps(r["exceptionDetails"])[:900])
        return r["result"].get("value")

    def wait(self, expr, timeout=90, step=.25):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                if self.js(expr):
                    return True
            except RuntimeError:
                pass
            time.sleep(step)
        return False

    def shot(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        d = self.ws.call("Page.captureScreenshot", format="png")
        path.write_bytes(base64.b64decode(d["data"]))
        return path

    def console(self):
        """Console errors / warnings / failed requests seen since the last open()."""
        out = []
        for m in self.ws.events:
            if m["method"] == "Runtime.consoleAPICalled" and m["params"]["type"] in ("error", "warning"):
                out.append(m["params"]["type"] + ": " + " ".join(str(a.get("value", a.get("description", ""))) for a in m["params"]["args"])[:300])
            elif m["method"] == "Runtime.exceptionThrown":
                out.append("exception: " + json.dumps(m["params"]["exceptionDetails"])[:400])
            elif m["method"] == "Log.entryAdded" and m["params"]["entry"]["level"] in ("error", "warning"):
                out.append("log: " + m["params"]["entry"]["text"][:300])
        return out

    def close(self):
        try:
            self.ws.call("Browser.close")
        except Exception:
            pass
        try:
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()
        shutil.rmtree(self.prof, ignore_errors=True)


def sid(tag="rv"):
    """A session of our own on the mock (wallets are per session id there)."""
    return f"{tag}{random.randint(100000, 999999)}"


def game_url(session=None, social=False, currency=None, extra=""):
    s = session or sid()
    if currency and currency != "USD":
        s += "@" + currency          # the mock pins the wallet's currency from the session suffix
    u = f"{MOCK}/?sessionID={s}&rgs_url={MOCK}"
    if social:
        u += "&social=true"
    if currency:
        u += "&currency=" + currency
    return u + extra


def replay_url(mode="base", event=844, amount=1000000, currency="USD", social=False, rgs=MOCK, extra=""):
    u = f"{MOCK}/?replay=true&game=test&version=1&mode={mode}&event={event}&rgs_url={rgs}"
    if amount is not None:
        u += f"&amount={amount}"
    if currency:
        u += "&currency=" + currency
    if social:
        u += "&social=true"
    return u + extra


INTRO_GONE = "!document.getElementById('intro') || document.getElementById('intro').classList.contains('gone')"
FEATURES_UP = "(() => { const f = document.querySelector('.fhit'); return !!(f && f.getBoundingClientRect().width > 0); })()"


def enter_game(b, timeout=120):
    """Wait out the loader, then close the feature intro ("Click to play")."""
    if not b.wait(f"({INTRO_GONE}) && {FEATURES_UP}", timeout):
        raise RuntimeError("feature intro never came up")
    time.sleep(.8)
    b.js("document.querySelector('.fhit').click()")
    b.wait("!document.body.classList.contains('features-up') && typeof RGS !== 'undefined' && RGS.state.authenticated", 30)
    time.sleep(1.5)


# What the live RGS answers for a social-casino GC wallet, as the reviewer saw it (2026-11-15): every
# gameModes[].maxBet is 0, the wallet holds 1,000 GC and the bet ladder runs far above it. The mock
# does not know this shape, so the page's own fetch is wrapped and the authenticate answer rewritten.
XGC_AUTH = """
(() => {
  const real = window.fetch, U = 1000000;
  window.fetch = async (url, opt) => {
    const res = await real(url, opt);
    if (!String(url).includes('/wallet/authenticate')) return res;
    const d = await res.clone().json();
    d.balance = { amount: 1000 * U, currency: 'XGC' };
    const c = d.config;
    c.betLevels = [100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000].map(v => v * U);
    c.minBet = c.betLevels[0]; c.maxBet = c.betLevels[c.betLevels.length - 1]; c.stepBet = c.minBet;
    c.defaultBetLevel = 10000 * U;
    for (const m of c.gameModes) m.maxBet = 0;
    __JURIS__
    return new Response(JSON.stringify(d), { status: 200, headers: { 'Content-Type': 'application/json' } });
  };
})();
"""


def xgc_auth(jurisdiction_social=False):
    return XGC_AUTH.replace("__JURIS__", "c.jurisdiction.socialCasino = true;" if jurisdiction_social else "")
