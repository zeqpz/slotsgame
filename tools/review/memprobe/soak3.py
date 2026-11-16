"""150+ live rounds on a phone profile, memory per round (iOS crash review 3, 2026-11-16): does anything GROW?

Same rounds as soak.py (two of every three a big book forced in - the biggest tumble chains and Cork Storms - the
third a natural spin; every 5th played out, the rest skipped), then after each round, once things have settled and
a GC has run: the WebKit memory model's parts (iosprobe3.py: 2D canvases, WebGL buffers + textures, ImageBitmaps,
the certain layers at their layout size, software filters), decoded audio, JS heap, DOM nodes, running animations,
listeners on window. Prints a line per round; at the end the first/last-20 means and a least-squares slope per
round for each, failed rounds, console errors and the shown balance against the RGS's.
usage: soak3.py OUTJSON [--base URL] [--rounds 150] [--ua ios|crios] [--throttle 1] [--w 390 --h 844] [--extra &x=1]
"""
import json, os, random, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import Browser, IPHONE_UA, CRIOS_UA, FORCE, game_url, enter_game, MOCK

a = sys.argv[1:]
out = a[0]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
base = opt("--base", MOCK)
N = int(opt("--rounds", 150))
thr = float(opt("--throttle", 1))
ua = CRIOS_UA if opt("--ua", "ios") == "crios" else IPHONE_UA
w, h = int(opt("--w", 390)), int(opt("--h", 844))
# Smukiez & Skelly's heaviest base books (2026-11-16): the longest tumble chains without a bonus (36873: 7 tumbles,
# 4 Multis; 2120, 37141, 29819: 6), the biggest base wins (33152: 9,120x; 76262: 6,424x; 56676: 6,360x) and one that
# lands the bonus (38: 10 free spins, 11 tumbles)
BIG = [("base", 36873), ("base", 33152), ("base", 2120), ("base", 76262), ("base", 38), ("base", 37141),
       ("base", 56676), ("base", 29819)]
ROUND = """(async (skip) => {
  const t0 = performance.now();
  const skipper = setInterval(() => { if (skip && !state.noSkip) state.skip = true;
    for (const s of ['.bonusintro', '.totalwin']) { const e = document.querySelector(s); if (e && e.getBoundingClientRect().width > 0) e.click(); } }, skip ? 300 : 2500);
  let ok, err = null;
  try { ok = await playRound('base'); } catch (e) { ok = false; err = String(e && e.stack || e); }
  clearInterval(skipper);
  return JSON.stringify({ ok, err, ms: Math.round(performance.now() - t0) });
})(%s)"""
MEM = """JSON.stringify((() => {
  const q = __mem.quick(), z = el => (el && el.currentCSSZoom) || 1;
  const lay = new Set();
  for (const an of document.getAnimations()) { const t = an.effect && an.effect.target; if (an.playState === 'running' && t instanceof Element && t.tagName !== 'CANVAS') lay.add(t); }
  for (const el of document.querySelectorAll('body *')) { if (el.tagName === 'CANVAS') continue; const cs = getComputedStyle(el);
    if (cs.display !== 'none' && (/matrix3d|perspective/.test(cs.transform) || /transform|opacity/.test(cs.willChange))) lay.add(el); }
  const pf = document.getElementById('paintframe'); if (pf) lay.add(pf);
  let wkl = 0; for (const el of lay) { if (!el.getClientRects().length) continue; const k = z(el); wkl += Math.min(el.offsetWidth * k * el.offsetHeight * k * devicePixelRatio * devicePixelRatio * 4, 156 * 1048576); }
  return { c2d: q.c2d, n2d: q.n2d, gl: q.cgl, ngl: q.ngl, tex: q.tex, bmp: q.bmp, aud: q.aud, naud: q.naud, heap: q.heap, wkl,
           nodes: document.getElementsByTagName('*').length, anims: document.getAnimations().length,
           canvasesInDom: document.querySelectorAll('canvas').length, imgs: document.images.length };
})())"""
rows, fails = [], 0
b = Browser(w, h, 3, ua=ua, mobile=True)
try:
    b.ws.call("Page.addScriptToEvaluateOnNewDocument", source=FORCE)
    b.open(game_url(base, opt("--extra", "")), 2)
    enter_game(b)
    time.sleep(3)
    if thr > 1:
        b.ws.call("Emulation.setCPUThrottlingRate", rate=thr)
    for i in range(1, N + 1):
        forced = None
        if i % 3 != 0:
            forced = BIG[(i // 3 * 2 + (i % 3) - 1) % len(BIG)]
            b.js(f"__force.push([{json.dumps(forced[0])}, {forced[1]}])")
        r = json.loads(b.js(ROUND % ("false" if i % 5 == 0 else "true")))
        time.sleep(1.2)   # the round's leftovers settle (idle-freed canvases, fading figures)
        b.gc()
        m = json.loads(b.js(MEM))
        r.update({"i": i, "forced": forced}, **{k: (round(v / 1e6, 2) if k in ("c2d", "gl", "tex", "bmp", "aud", "heap", "wkl") else v) for k, v in m.items()})
        r["model"] = round(r["c2d"] + r["gl"] + r["tex"] + r["bmp"] + r["wkl"], 2)
        if r["ok"] is not True:
            fails += 1
        rows.append(r)
        print(json.dumps({k: r[k] for k in ("i", "ok", "ms", "model", "c2d", "n2d", "wkl", "bmp", "aud", "heap", "nodes", "anims", "canvasesInDom")}), flush=True)
    b.ws.call("Emulation.setCPUThrottlingRate", rate=1)
    time.sleep(1)
    bal = json.loads(b.js("JSON.stringify({ shown: document.getElementById('balance').textContent, state: state.balance, rgs: RGS.state.balance })"))
    con = b.console()
    keys = ("model", "c2d", "n2d", "wkl", "bmp", "aud", "heap", "nodes", "anims", "canvasesInDom", "imgs")
    def mean(xs): return round(sum(xs) / len(xs), 3) if xs else 0
    def slope(k):
        xs = [r["i"] for r in rows]; ys = [r[k] for r in rows]; n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        return round(sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / max(1e-9, sum((x - mx) ** 2 for x in xs)), 5)
    summ = {k: {"first20": mean([r[k] for r in rows[:20]]), "last20": mean([r[k] for r in rows[-20:]]), "max": max(r[k] for r in rows),
                "slope_per_round": slope(k)} for k in keys}
    res = {"rounds": N, "ua": opt("--ua", "ios"), "fails": fails, "summary": summ, "balance": bal, "console": con[:30], "rows": rows}
    print("fails", fails, "balance", bal)
    for k, v in summ.items():
        print(f"  {k:14s} first20 {v['first20']:9.3f}  last20 {v['last20']:9.3f}  max {v['max']:9.3f}  slope/round {v['slope_per_round']}")
    print("console", con[:8])
finally:
    try:
        b.ws.call("Emulation.setCPUThrottlingRate", rate=1)
    except Exception:
        pass
    b.close()
    json.dump(locals().get("res", {"rows": rows}), open(out, "w"), indent=1)
