"""The safety net under failure (iOS crash review 2, 2026-11-16): a replayed round where, once it is playing, every
new 2D context is refused (getContext -> null, as WebKit does out of canvas memory) and every WebGL context is lost
(WEBGL_lose_context). The round must play to its end with no exception, no reload, GFX.low set.
usage: failsafe.py [--base URL] [--mode base --event 33152] [--restore] [--desk]
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import Browser, IPHONE_UA, MOCK

a = sys.argv[1:]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
base, mode, event = opt("--base", MOCK), opt("--mode", "base"), opt("--event", "33152")
restore = "--restore" in a   # give the WebGL contexts back 3 s later (the board rebuilds its atlases: boardgl.js rebuild())
desk = "--desk" in a
b = Browser(1600, 900, 1, ua=None, mobile=False) if desk else Browser(390, 844, 3, ua=IPHONE_UA, mobile=True)
try:
    b.open(f"{base}/?replay=true&game=test&version=1&mode={mode}&event={event}&amount=1000000&rgs_url={base}", 2)
    b.wait("(document.getElementById('replayPlay') || {dataset: {}}).dataset.phase === 'ready'", 120)
    time.sleep(2)
    # the replay viewer swallows an exception from the round (it shows it in the ticker): surface it here
    b.js("""(() => { const real = window.presentRound; window.presentRound = async (...x) => {
      try { return await real(...x); } catch (e) { console.error('presentRound threw: ' + (e && e.stack || e)); throw e; } }; })()""")
    # a bonus's intro and its TOTAL WIN wait for a press: given one after they have been up ~3 s
    b.js("""(() => { const seen = {}; setInterval(() => { for (const s of ['.bonusintro', '.totalwin']) { const e = document.querySelector(s);
      if (e && e.getBoundingClientRect().width > 0) { seen[s] = (seen[s] || 0) + 1; if (seen[s] > 8) { e.click(); seen[s] = 0; } } } }, 400); })()""")
    b.js("window.__t0 = performance.timeOrigin; window.__c0 = performance.now(); document.getElementById('replayPlay').click(); 1")
    time.sleep(2.5)
    lost = b.js("""(() => { let n = 0;
      for (const c of document.querySelectorAll('canvas')) { const g = c.__mt && /webgl/.test(c.__mt.type) ? c.getContext(c.__mt.type) : null;
        const x = g && g.getExtension('WEBGL_lose_context'); if (x) { x.loseContext(); n++; (window.__lost = window.__lost || []).push(x); } }
      const real = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function (t, o) { return /2d/.test(t) && !this.__mt ? null : real.call(this, t, o); };
      // the effect canvases made from now on get nothing; the ones already made keep theirs - and the next pops'
      // symbols (new canvases) get none
      return n; })()""")
    if restore:
        time.sleep(3)
        b.js("(window.__lost || []).forEach(x => { try { x.restoreContext(); } catch (e) {} }); 1")
    t0 = time.time()
    while time.time() - t0 < 600 and b.js("document.getElementById('replayPlay').dataset.phase") != "done":
        time.sleep(.5)
    res = {"webgl_lost": lost, "done": b.js("document.getElementById('replayPlay').dataset.phase"), "secs": round(time.time() - t0, 1),
           "gfx": json.loads(b.js("JSON.stringify(GFX)")),
           "tex_mb_after": b.js("+(__mem.quick().tex / 1e6).toFixed(1)"), "same_document": b.js("performance.timeOrigin === window.__t0"),
           "error_panel": b.js("!!(document.getElementById('errorRetry') && document.getElementById('errorRetry').offsetParent)"),
           "console": b.console()[:12]}
    print(json.dumps(res, indent=1))
finally:
    b.close()
