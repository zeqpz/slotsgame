"""Memory / frame measurement over CDP (headless Chrome, mobile emulation). Ported from zeqpz/fallslotsga and Voodoo on
Bourbon (Documents/orleans) for the Smukiez & Skelly phone tier, 2026-11-16 (research/ios_phone_2026-11-16.md):
  iosprobe3.py the WebKit memory model per scenario (runset/runsub in the report), table3.py the before/after table,
  soak3.py 150 live rounds, failsafe.py refused canvases + lost WebGL, wkprobe.py Playwright WebKit (scratch venv),
  lag.py / lagtable.py frame times at 4x throttle, picfit.py / picmax.py picture sizes (tools/phone_art.py),
  abshots.py desktop A/B, detail.py / jsprobe.py / phoneshots.py / clipshot.py quick looks.

Original notes:

iOS memory review, 2026-11-16 (research/ios_memory_2026-11-16.md). Scripts in this folder:
  (scen.py, leak.py, trace.py, table.py: in zeqpz/fallslotsga, not copied here)
  scen.py   peak memory per scenario (loading, boot, base spin with pops, big win, bonus) as an "iOS model":
            JS heap + 2D canvases + WebGL buffers/textures + ImageBitmaps + decoded audio + decoded pictures on
            screen + composited layers that paint, plus Windows' view of our Chrome (private bytes, GPU memory)
  leak.py   100+ fast-forwarded live spins and two bought bonuses: memory must plateau, balances must match
  lag.py    frame times per scenario with CPU throttling (+ --profile: top self-time functions)
  trace.py  one forced round traced: style/layout/paint/commit totals and which JS forced layout
  table.py  the budget table (markdown) from two scen.py results
All need the mock RGS (frontend/mock_rgs.py on :8733, or --base). Chrome runs headless on a random port 9400-9800
with a throwaway profile and only that process is closed. instr.js is injected before the page's scripts and
counts every canvas, WebGL texture upload, ImageBitmap and decoded AudioBuffer (WeakRefs: until a GC runs the
counts include garbage).
    .venv312/Scripts/python.exe -I tools/review/memprobe/iosprobe3.py out.json --boot [--w 390 --h 844 --dpr 3]
"""
import base64, json, os, random, shutil, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # tools/review: cdp.py
from cdp import WS, CHROME  # noqa

HERE = Path(__file__).resolve().parent
INSTR = (HERE / "instr.js").read_text(encoding="utf-8")


def _dims():   # every picture's size under frontend/assets (decoded bytes = w x h x 4)
    from PIL import Image
    root = HERE.parents[2] / "frontend"
    out = {}
    for f in (root / "assets").rglob("*"):
        if f.suffix.lower() in (".webp", ".png", ".jpg") and "/sym/d" not in f.as_posix():
            try:
                out[f.relative_to(root).as_posix()] = Image.open(f).size
            except Exception:
                pass
    return out


DIMS = _dims()
IPHONE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1")
CRIOS_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "CriOS/141.0.7390.96 Mobile/15E148 Safari/604.1")   # Chrome for iOS: WebKit underneath


class Browser:
    def __init__(self, w=390, h=844, dpr=3, ua=IPHONE_UA, mobile=True, extra_flags=()):
        self.port = random.randint(9400, 9800)
        self.prof = tempfile.mkdtemp(prefix="memprobe_")
        self.proc = subprocess.Popen(
            [CHROME, "--headless=new", f"--remote-debugging-port={self.port}", f"--user-data-dir={self.prof}",
             f"--window-size={w},{h}", "--no-first-run", "--hide-scrollbars", "--mute-audio",
             "--enable-precise-memory-info", "--js-flags=--expose-gc",
             "--autoplay-policy=no-user-gesture-required", *extra_flags, "about:blank"],
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
        for m in ("Page.enable", "Runtime.enable", "Log.enable"):
            self.ws.call(m)
        self.ws.call("Page.addScriptToEvaluateOnNewDocument", source=INSTR)
        if ua:
            self.ws.call("Emulation.setUserAgentOverride", userAgent=ua, platform="iPhone")
        self.size(w, h, dpr, mobile)

    def size(self, w, h, dpr=3, mobile=True):
        self.w, self.h, self.dpr = w, h, dpr
        self.ws.call("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=dpr, mobile=mobile)
        if mobile:
            self.ws.call("Emulation.setTouchEmulationEnabled", enabled=True, maxTouchPoints=5)

    def open(self, url, settle=1.0):
        self.ws.events.clear()
        self.ws.call("Page.navigate", url=url)
        time.sleep(settle)

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
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        d = self.ws.call("Page.captureScreenshot", format="png")
        path.write_bytes(base64.b64decode(d["data"]))
        return path

    def console(self):
        out = []
        for m in self.ws.events:
            if m["method"] == "Runtime.consoleAPICalled" and m["params"]["type"] in ("error", "warning"):
                out.append(m["params"]["type"] + ": " + " ".join(str(a.get("value", a.get("description", ""))) for a in m["params"]["args"])[:300])
            elif m["method"] == "Runtime.exceptionThrown":
                out.append("exception: " + json.dumps(m["params"]["exceptionDetails"])[:500])
            elif m["method"] == "Log.entryAdded" and m["params"]["entry"]["level"] in ("error",):
                out.append("log: " + m["params"]["entry"]["text"][:300])
        return out

    def wait_event(self, method, timeout=60):
        t0 = time.time()
        while time.time() - t0 < timeout:
            for i, m in enumerate(self.ws.events):
                if m.get("method") == method:
                    return self.ws.events.pop(i)
            m = self.ws.recv()
            if "method" in m:
                self.ws.events.append(m)
        raise TimeoutError(method)

    def gc(self):
        try:
            self.ws.call("HeapProfiler.collectGarbage")
        except Exception:
            pass

    # ---- Chrome's own accounting (memory-infra) ----
    def memdump(self):
        self.ws.call("Tracing.start", transferMode="ReturnAsStream", traceConfig={
            "recordMode": "recordUntilFull", "includedCategories": ["disabled-by-default-memory-infra"], "excludedCategories": ["*"],
            "memoryDumpConfig": {"triggers": []}})
        time.sleep(1.0)
        r = self.ws.call("Tracing.requestMemoryDump", levelOfDetail="detailed")
        self.ws.call("Tracing.end")
        ev = self.wait_event("Tracing.tracingComplete", 60)
        h = ev["params"]["stream"]
        buf = []
        while True:
            d = self.ws.call("IO.read", handle=h, size=1 << 22)
            buf.append(base64.b64decode(d["data"]) if d.get("base64Encoded") else d["data"].encode())
            if d.get("eof"):
                break
        self.ws.call("IO.close", handle=h)
        trace = json.loads(b"".join(buf))
        evs = trace["traceEvents"] if isinstance(trace, dict) else trace
        names = {}
        for e in evs:
            if e.get("ph") == "M" and e.get("name") == "process_name":
                names[e["pid"]] = e["args"]["name"]
        best = {}
        for e in evs:
            if e.get("ph") != "v":
                continue
            d = e.get("args", {}).get("dumps", {})
            score = (1 if d.get("allocators") else 0, e.get("ts", 0))
            if e["pid"] not in best or score >= best[e["pid"]][0]:
                best[e["pid"]] = (score, d)
        out = {}
        for pid, (_, d) in best.items():
            pt = d.get("process_totals", {})
            pmf = int(pt.get("private_footprint_bytes", "0"), 16)
            alloc = {}
            for k, v in d.get("allocators", {}).items():
                if k.count("/") > 1:
                    continue
                s_ = v.get("attrs", {}).get("size") or v.get("attrs", {}).get("effective_size")
                if s_:
                    alloc[k] = int(s_["value"], 16)
            out[names.get(pid, str(pid)) + ":" + str(pid)] = {"pmf": pmf, "alloc": alloc}
        return out

    def layers(self):
        """Composited layers that draw content, summed as backing-store bytes (physical px x 4)."""
        self.ws.call("LayerTree.enable")
        ev = None
        try:
            ev = self.wait_event("LayerTree.layerTreeDidChange", 10)
            time.sleep(.4)
            # take the newest
            for m in list(self.ws.events):
                if m.get("method") == "LayerTree.layerTreeDidChange":
                    ev = m
            self.ws.events = [m for m in self.ws.events if m.get("method") != "LayerTree.layerTreeDidChange"]
        finally:
            self.ws.call("LayerTree.disable")
        ls = (ev or {}).get("params", {}).get("layers") or []
        draws = [l for l in ls if l.get("drawsContent")]
        return {"n": len(ls), "ndraw": len(draws), "areas": sorted(((l["width"] * l["height"]), l["width"], l["height"]) for l in draws)[::-1][:12],
                "sum_px": sum(l["width"] * l["height"] for l in draws)}

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


def pics_bytes(pics):
    rows, tot, tot_vis = [], 0, 0
    for u, where in pics:
        wh = DIMS.get(u)
        b = wh[0] * wh[1] * 4 if wh else 0
        rows.append((b, u, where))
        tot += b
        if not where.startswith(("held", "css-hidden")):
            tot_vis += b
    rows.sort(reverse=True)
    return tot, tot_vis, rows


# force the next /wallet/play answers to given replay books (live session, measurement only)
FORCE = """
(() => {
  const real = window.fetch;
  window.__force = [];
  window.fetch = async (url, opt) => {
    const res = await real(url, opt);
    if (!String(url).includes('/wallet/play') || !window.__force.length) return res;
    const d = await res.clone().json();
    if (!d.round) return res;
    const [mode, ev] = window.__force.shift();
    const rp = await (await real(location.origin + '/bet/replay/test/1/' + mode + '/' + ev)).json();
    d.round.state = rp.state; d.round.payoutMultiplier = rp.payoutMultiplier;
    d.round.payout = Math.round(rp.payoutMultiplier * d.round.amount);
    return new Response(JSON.stringify(d), { status: 200, headers: { 'Content-Type': 'application/json' } });
  };
})();
"""

MOCK = "http://localhost:8733"


def game_url(base=MOCK, extra=""):
    s = f"mem{random.randint(100000, 999999)}"
    return f"{base}/?sessionID={s}&rgs_url={base}{extra}"


INTRO_GONE = "!document.getElementById('intro') || document.getElementById('intro').classList.contains('gone')"
FEATURES_UP = "(() => { const f = document.querySelector('.fhit'); return !!(f && f.getBoundingClientRect().width > 0); })()"


def enter_game(b, timeout=150):
    if not b.wait(f"({INTRO_GONE}) && {FEATURES_UP}", timeout):
        raise RuntimeError("feature intro never came up")
    time.sleep(.8)
    r = json.loads(b.js("JSON.stringify(document.querySelector('.fhit').getBoundingClientRect())"))
    x, y = r["left"] + r["width"] / 2, r["top"] + r["height"] / 2
    b.ws.call("Input.dispatchTouchEvent", type="touchStart", touchPoints=[{"x": x, "y": y}])
    b.ws.call("Input.dispatchTouchEvent", type="touchEnd", touchPoints=[])
    time.sleep(.6)
    if b.js("document.body.classList.contains('features-up')"):
        b.js("document.querySelector('.fhit').click()")
    b.wait("!document.body.classList.contains('features-up') && typeof RGS !== 'undefined' && RGS.state.authenticated", 30)
    time.sleep(1.5)


ROUND = """(async (mode, skip) => {
  const t0 = performance.now();
  const skipper = setInterval(() => { if (skip && !state.noSkip) state.skip = true;
    if (skip) for (const s of ['.bonusintro', '.totalwin']) { const e = document.querySelector(s); if (e) e.click(); } }, 400);
  let ok, err = null;
  try { ok = await playRound(mode); } catch (e) { ok = false; err = String(e && e.stack || e); }
  clearInterval(skipper);
  return JSON.stringify({ ok, err, ms: Math.round(performance.now() - t0) });
})(%s, %s)"""


PS_MEM = r"""
$ErrorActionPreference = 'SilentlyContinue'
$procs = Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" | Where-Object { $_.CommandLine -like '*__PROF__*' }
$gpu = @{}
try {
  $c = Get-Counter '\GPU Process Memory(*)\Shared Usage','\GPU Process Memory(*)\Dedicated Usage' -ErrorAction Stop
  foreach ($s in $c.CounterSamples) { if ($s.InstanceName -match 'pid_(\d+)_') { $k=[int]$matches[1]; $gpu[$k] = [double]$gpu[$k] + $s.CookedValue } }
} catch {}
$out = foreach ($p in $procs) {
  $t = 'browser'; if ($p.CommandLine -match '--type=([a-z-]+)') { $t = $matches[1] }
  [pscustomobject]@{ pid=$p.ProcessId; type=$t; priv=[double]$p.PrivatePageCount; ws=[double]$p.WorkingSetSize; gpu=[double]$gpu[[int]$p.ProcessId]; util=($p.CommandLine -match 'utility') }
}
$out | ConvertTo-Json -Compress
"""


def procmem(b):
    """Windows view of our own Chrome: private bytes per process + GPU (shared+dedicated) usage, MB."""
    import subprocess as sp
    prof = os.path.basename(b.prof)
    r = sp.run(["powershell", "-NoProfile", "-Command", PS_MEM.replace("__PROF__", prof)], capture_output=True, text=True, timeout=90)
    try:
        rows = json.loads(r.stdout or "[]")
    except Exception:
        return {"err": r.stdout[:200] + r.stderr[:200]}
    if isinstance(rows, dict):
        rows = [rows]
    rend = [x for x in rows if x["type"] == "renderer"]
    page = max(rend, key=lambda x: x["priv"]) if rend else {"priv": 0, "gpu": 0}
    gp = next((x for x in rows if x["type"] == "gpu-process"), {"priv": 0, "gpu": 0})
    return {"renderer_priv": round(page["priv"] / 1e6, 1), "gpu_priv": round(gp["priv"] / 1e6, 1),
            "gpu_mem": round((gp["gpu"] + page["gpu"]) / 1e6, 1),
            "total": round((page["priv"] + gp["priv"] + gp["gpu"] + page["gpu"]) / 1e6, 1)}


def layer_list(b):
    """Composited layers drawing content, with their node and an estimate of backing bytes on screen
    (layout size x accumulated transform scale^2 x dpr^2 x 4)."""
    b.ws.call("DOM.enable")
    b.ws.call("DOM.getDocument", depth=-1)
    b.ws.call("LayerTree.enable")
    ev = None
    try:
        ev = b.wait_event("LayerTree.layerTreeDidChange", 10)
        time.sleep(.5)
        for m in list(b.ws.events):
            if m.get("method") == "LayerTree.layerTreeDidChange":
                ev = m
        b.ws.events = [m for m in b.ws.events if m.get("method") != "LayerTree.layerTreeDidChange"]
    finally:
        b.ws.call("LayerTree.disable")
    ls = (ev or {}).get("params", {}).get("layers") or []
    byid = {l["layerId"]: l for l in ls}

    def scale(l):
        s = 1.0
        while l:
            t = l.get("transform")
            if t:
                import math
                s *= math.sqrt(abs(t[0] * t[5] - t[1] * t[4])) or 1
            l = byid.get(l.get("parentLayerId"))
        return s
    out = []
    for l in ls:
        if not l.get("drawsContent"):
            continue
        k = scale(l)
        mb = l["width"] * l["height"] * k * k * b.dpr ** 2 * 4 / 1e6
        name = ""
        if l.get("backendNodeId"):
            try:
                n = b.ws.call("DOM.describeNode", backendNodeId=l["backendNodeId"])["node"]
                at = dict(zip(n.get("attributes", [])[::2], n.get("attributes", [])[1::2]))
                name = n["nodeName"].lower() + ("#" + at["id"] if at.get("id") else "") + ("." + at["class"].replace(" ", ".") if at.get("class") else "")
            except Exception as e:
                name = "?"
        out.append({"mb": round(mb, 2), "w": l["width"], "h": l["height"], "k": round(k, 3), "name": name[:80], "paints": l.get("paintCount", 0)})
    out.sort(key=lambda x: -x["mb"])
    return out
