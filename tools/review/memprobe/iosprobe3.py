"""What WebKit on an iPhone holds for the game, sampled through a boot or a replayed round (iOS crash review 3, 2026-11-16).

Headless Chrome with iPhone emulation (390x844 or 844x390 @3, Safari or Chrome-for-iOS UA), stdlib CDP, instr.js injected
before the page. Every ~0.5 s it sums the WebKit memory model:
  canvas2d  every live 2D canvas, in the page or not (WebKit/Cocoa: each one is an IOSurface): w x h x 4
  gl        WebGL drawing buffers (front + back, + depth/stencil where asked)
  tex       WebGL texture uploads (+1/3 when mipmapped)
  bmp       live ImageBitmaps
  pics      decoded pictures the page shows (<img>, CSS backgrounds/masks on a displayed element): file w x h x 4 (every
            4th sample). Pictures only held by the preloader (new Image(), never painted) are reported as picsHeld and not
            in the total: WebKit decodes on paint/draw, not on load.
  layers    the composited layers WebKit is certain to make - running transform/opacity/filter animations, 3D
            transforms, will-change, the log frame over the canvases - each at its LAYOUT box x DPR^2 x 4. WebKit never
            scales a layer's backing store down for a transform-scaled ancestor (GraphicsLayerCA), so under
            #app { transform: scale(fit) } a layer costs its unscaled layout box; under #app { zoom: fit } (the mobile
            tier since this review) the layout box itself is zoomed, so the size is offsetWidth x currentCSSZoom.
            Tiled (> 1280 px) layers capped at 156 MB like WebKit. Overlap layers are not modelled: a lower bound.
  swf       WebKit software filters (a drop-shadow that is not the last filter in the list)
  audio     decoded AudioBuffers (reported beside the total, and in totalAudio)
total = canvas2d + gl + tex + bmp + pics + layers + swf;  totalAudio = total + audio.

Scenarios:
  --boot          live game: load, studio intro, features screen, first touch (sounds/music), one natural spin
  --mode M --event N   replay mode: load, START REPLAY, the round to PLAY AGAIN (peak of the whole run, and at the
                  moments a cork is in the air or a tile is blowing: "corkpop")
usage: iosprobe3.py OUTJSON (--boot | --mode corkstorm --event 43029) [--base URL] [--w 390 --h 844 --dpr 3]
                    [--ua ios|crios] [--throttle 1] [--extra "&x=1"] [--shots DIR/prefix] [--screenh 844]
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import Browser, IPHONE_UA, CRIOS_UA, MOCK, pics_bytes, game_url, enter_game

a = sys.argv[1:]
out = a[0]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
base = opt("--base", MOCK)
boot = "--boot" in a
mode, event = opt("--mode", "corkstorm"), int(opt("--event", 43029))
w, h, dpr = int(opt("--w", 390)), int(opt("--h", 844)), float(opt("--dpr", 3))
ua = CRIOS_UA if opt("--ua", "ios") == "crios" else IPHONE_UA
thr = float(opt("--throttle", 1))
extra = opt("--extra", "")
shots = opt("--shots", "")
MB = 1e6

CENSUS = """JSON.stringify((() => {
  const q = __mem.quick();
  const z = el => (el && el.currentCSSZoom) || 1;
  let cork = 0, pops = 0;
  try { cork = FXS.parts.filter(p => p.kind === 'cork').length; } catch (e) {}
  try { cork += corkLive.size; } catch (e) {}   // the mobile tier's cork: one picture in the air
  pops += document.querySelectorAll('.cell.popping, .cell.explode').length;
  try { pops += bursts.length; } catch (e) {}   // (Voodoo on Bourbon: a tile is hexed away on the burst canvas)   // tiles blowing (their own clip, or the scale-and-fade)
  let swf = 0, swn = 0;
  for (const el of document.querySelectorAll('body *')) {
    const f = getComputedStyle(el).filter;
    if (!f || f === 'none') continue;
    const ds = (f.match(/drop-shadow/g) || []).length;
    if (!ds || (ds === 1 && /drop-shadow\\((?:[^()]|\\([^()]*\\))*\\)\\s*$/.test(f))) continue;
    if (!el.getClientRects().length) continue;
    const k = z(el), w = el.offsetWidth * k, h = el.offsetHeight * k;
    if (!w || !h) continue;
    swn++; swf += (w + 60) * (h + 60) * devicePixelRatio * devicePixelRatio * 4 * (1 + 2 * ds);
  }
  const lay = new Map();
  const want = el => { if (el && el.isConnected && el.tagName !== 'CANVAS' && !lay.has(el)) lay.set(el, 1); };
  for (const an of document.getAnimations()) {
    if (an.playState !== 'running') continue;
    const ef = an.effect, t = ef && ef.target;
    if (!t || !(t instanceof Element)) continue;
    let props = [];
    try { props = ef.getKeyframes().flatMap(k => Object.keys(k)); } catch (e) {}
    if (props.some(p => /^(transform|opacity|filter|translate|rotate|scale)$/.test(p))) want(t);
  }
  for (const el of document.querySelectorAll('body *')) {
    if (el.tagName === 'CANVAS') continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none') continue;
    if (/matrix3d|perspective/.test(cs.transform) || /transform|opacity/.test(cs.willChange) || cs.transformStyle === 'preserve-3d'
        || (cs.backdropFilter && cs.backdropFilter !== 'none')) want(el);
  }
  const pf = document.getElementById('paintframe'); if (pf && pf.getClientRects().length) want(pf);
  let wkl = 0, wkn = 0; const top = [];
  for (const el of lay.keys()) {
    if (getComputedStyle(el).display === 'none' || !el.getClientRects().length) continue;
    const k = z(el), w = el.offsetWidth * k, h = el.offsetHeight * k;
    if (!w || !h) continue;
    const b = Math.min(w * h * devicePixelRatio * devicePixelRatio * 4, 156 * 1048576);
    wkn++; wkl += b;
    top.push([+(b / 1e6).toFixed(1), (el.id ? '#' + el.id : el.tagName.toLowerCase() + '.' + String(el.className).split(' ')[0]).slice(0, 40)]);
  }
  top.sort((x, y) => y[0] - x[0]);
  const app = document.getElementById('app'), acs = app ? getComputedStyle(app) : null;
  return { n2d: q.n2d, c2d: q.c2d, ngl: q.ngl, nlost: q.nlost, cgl: q.cgl, tex: q.tex, bmp: q.bmp, aud: q.aud, heap: q.heap,
           domCanvases: document.querySelectorAll('canvas').length, swf, swn, wkl, wkn, top: top.slice(0, 8),
           cork, pops, phase: (document.getElementById('replayPlay') || { dataset: {} }).dataset.phase || '',
           anims: document.getAnimations().length, nodes: document.getElementsByTagName('*').length,
           appZoom: acs ? acs.zoom : '', appTransform: acs ? acs.transform : '',
           mob: !!window.MOBILE, lite: !!window.LITE, ios: !!window.IOS_WEBKIT };
})())"""

b = Browser(w, h, dpr, ua=ua, mobile=True)
screenh = int(opt("--screenh", 0))   # Safari's bars: a window shorter than the screen (e.g. --h 664 --screenh 844)
if screenh:
    b.ws.call("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=dpr, mobile=True, screenWidth=w, screenHeight=screenh)
res = {"profile": f"{w}x{h}@{dpr}{' screen ' + str(screenh) if screenh else ''} {opt('--ua', 'ios')} x{thr}", "base": base, "scenario": "boot" if boot else f"{mode}/{event}", "samples": []}
pics_last = [0.0, 0.0, []]
nsamp = [0]


def sample(tag=""):
    c = json.loads(b.js(CENSUS))
    if nsamp[0] % 4 == 0:
        tot, vis, rows = pics_bytes(json.loads(b.js("JSON.stringify(__mem.pics())")))
        pics_last[:] = [vis / MB, (tot - vis) / MB, rows[:10]]
    nsamp[0] += 1
    s = {"t": round(time.time() - t0, 1), "tag": tag, "canvas2d": round(c["c2d"] / MB, 1), "canvasN": c["n2d"], "domCanvases": c["domCanvases"],
         "gl": round(c["cgl"] / MB, 1), "glN": c["ngl"], "glLost": c["nlost"], "tex": round(c["tex"] / MB, 1), "bmp": round(c["bmp"] / MB, 1),
         "pics": round(pics_last[0], 1), "picsHeld": round(pics_last[1], 1), "layers": round(c["wkl"] / MB, 1), "layersN": c["wkn"], "swf": round(c["swf"] / MB, 1),
         "audio": round(c["aud"] / MB, 1), "heap": round(c["heap"] / MB, 1), "anims": c["anims"], "nodes": c["nodes"],
         "cork": c["cork"], "pops": c["pops"], "phase": c["phase"], "mob": c["mob"], "lite": c["lite"], "ios": c["ios"],
         "appZoom": c["appZoom"], "appTransform": c["appTransform"][:40], "topLayers": c["top"]}
    s["total"] = round(s["canvas2d"] + s["gl"] + s["tex"] + s["bmp"] + s["pics"] + s["layers"] + s["swf"], 1)
    s["totalAudio"] = round(s["total"] + s["audio"], 1)
    res["samples"].append(s)
    return s, c


KEYS = ("total", "totalAudio", "canvas2d", "canvasN", "gl", "glN", "tex", "bmp", "pics", "picsHeld", "layers", "layersN", "swf", "audio", "heap", "anims")
t0 = time.time()
try:
    if boot:
        b.open(game_url(base, extra), .3)
        t0 = time.time()
        deadline = time.time() + 150
        from memlib import INTRO_GONE, FEATURES_UP
        while time.time() < deadline:
            time.sleep(.5)
            try:
                s, c = sample("load")
            except RuntimeError:
                continue
            try:
                if b.js(f"({INTRO_GONE}) && {FEATURES_UP}"):
                    break
            except RuntimeError:
                pass
        for _ in range(4):
            time.sleep(.5); sample("features")
        if shots:
            b.shot(f"{shots}_features.png")
        enter_game(b)
        for _ in range(8):
            time.sleep(.5); sample("board")
        if shots:
            b.shot(f"{shots}_board.png")
        if thr > 1:
            b.ws.call("Emulation.setCPUThrottlingRate", rate=thr)
        b.js("window.__spinDone = false; playRound('base').then(() => window.__spinDone = true, () => window.__spinDone = true); 1")
        t1 = time.time()
        while time.time() - t1 < 120:
            time.sleep(.5)
            sample("spin")
            if b.js("window.__spinDone"):
                break
        for _ in range(4):
            time.sleep(.5); sample("after")
    else:
        url = f"{base}/?replay=true&game=test&version=1&mode={mode}&event={event}&amount=1000000&rgs_url={base}{extra}"
        b.open(url, .3)
        t0 = time.time()
        t1 = time.time()
        while time.time() - t1 < 120:
            time.sleep(.5)
            try:
                s, c = sample("load")
            except RuntimeError:
                continue
            if c["phase"] == "ready":
                break
        for _ in range(4):
            time.sleep(.5); sample("ready")
        if thr > 1:
            b.ws.call("Emulation.setCPUThrottlingRate", rate=thr)
        # a bonus's intro and its TOTAL WIN wait for a press: given one after they have been up ~3 s (lag.py's clicker)
        b.js("""(() => { clearInterval(window.__clk); const seen = {};
          window.__clk = setInterval(() => { for (const s of ['.bonusintro', '.totalwin']) { const e = document.querySelector(s);
            if (e && e.getBoundingClientRect().width > 0) { seen[s] = (seen[s] || 0) + 1; if (seen[s] > 8) { e.click(); seen[s] = 0; } } } }, 400); })()""")
        b.js("document.getElementById('replayPlay').click(); 1")
        took = set()
        t1 = time.time()
        while time.time() - t1 < 900:
            time.sleep(.5)
            s, c = sample("round")
            if shots:
                if c["cork"] and "cork" not in took:
                    took.add("cork"); b.shot(f"{shots}_cork.png")
                if c["pops"] and "pop" not in took:
                    took.add("pop"); b.shot(f"{shots}_pop.png")
            if c["phase"] == "done":
                break
        if shots:
            b.shot(f"{shots}_done.png")
    S = res["samples"]
    res["peak"] = {k: max(x[k] for x in S) for k in KEYS}
    worst = max(S, key=lambda x: x["total"])
    res["peak_at"] = {k: worst[k] for k in ("t", "tag", "topLayers") + KEYS}
    phases = {}
    for x in S:
        phases.setdefault(x["tag"], []).append(x)
    res["peak_by_phase"] = {p: {k: max(x[k] for x in xs) for k in KEYS} for p, xs in phases.items()}
    cp = [x for x in S if x["cork"] or x["pops"]]
    res["peak_corkpop"] = {k: max(x[k] for x in cp) for k in KEYS} if cp else {}
    res["pics_top"] = pics_last[2]
    res["console"] = b.console()
    res["secs"] = round(time.time() - t0, 1)
    print(res["scenario"], res["profile"], "peak", json.dumps(res["peak"]), flush=True)
    print("  by phase", json.dumps({p: v["total"] for p, v in res["peak_by_phase"].items()}), "corkpop", res["peak_corkpop"].get("total"))
    print("  worst at", worst["t"], worst["tag"], worst["topLayers"][:5])
    print("  console", res["console"][:5])
finally:
    try:
        b.ws.call("Emulation.setCPUThrottlingRate", rate=1)
    except Exception:
        pass
    b.close()
    json.dump(res, open(out, "w"), indent=1)
