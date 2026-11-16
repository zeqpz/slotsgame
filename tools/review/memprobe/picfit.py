"""Which decoded pictures the mobile tier shows, at what size, against their file size (2026-11-16).
For every <img> and CSS background/border-image on an element that has a layout box: the file's w x h, the largest box it is
painted into (device px = CSS px on screen x DPR), and the oversize factor. Run at boot (features screen, board) and
optionally after opening the bonus shop / rules.
usage: picfit.py OUT.json [--base URL] [--w 390 --h 844 --dpr 3] [--ua ios|crios] [--extra &x=1]"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import Browser, IPHONE_UA, CRIOS_UA, MOCK, DIMS, game_url, enter_game, INTRO_GONE, FEATURES_UP

a = sys.argv[1:]
out = a[0]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
base = opt("--base", MOCK)
w, h, dpr = int(opt("--w", 390)), int(opt("--h", 844)), float(opt("--dpr", 3))
ua = CRIOS_UA if opt("--ua", "ios") == "crios" else IPHONE_UA
JS = r"""JSON.stringify((() => {
  const out = {};
  const add = (u, el, r) => { try { u = new URL(u, location.href).pathname.replace(/^\//, ''); } catch (e) { return; }
    const o = out[u] || (out[u] = { w: 0, h: 0, where: [] });
    o.w = Math.max(o.w, r.width * devicePixelRatio); o.h = Math.max(o.h, r.height * devicePixelRatio);
    if (o.where.length < 3) o.where.push((el.id ? '#' + el.id : el.tagName.toLowerCase() + '.' + String(el.className).split(' ')[0]).slice(0, 40)); };
  for (const el of document.querySelectorAll('body *')) {
    const rs = el.getClientRects(); if (!rs.length) continue;
    const r = el.getBoundingClientRect(); if (!r.width || !r.height) continue;
    if (el.tagName === 'IMG' && el.currentSrc && !el.currentSrc.startsWith('data:') && getComputedStyle(el).visibility !== 'hidden') add(el.currentSrc, el, r);
    for (const ps of [null, '::before', '::after']) {
      const cs = getComputedStyle(el, ps);
      if (ps && cs.content === 'none') continue;
      for (const p of ['backgroundImage', 'maskImage', 'webkitMaskImage', 'borderImageSource']) {
        const v = cs[p]; if (!v || v.indexOf('url(') < 0) continue;
        for (const m of v.matchAll(/url\("?([^")]+)"?\)/g)) if (!m[1].startsWith('data:')) add(m[1], el, r);
      }
    }
  }
  return out;
})())"""
res = {}
b = Browser(w, h, dpr, ua=ua, mobile=True)
FINISH = """(() => { for (const el of document.querySelectorAll('.bonusintro, .totalwin')) el.click(); if (state.playing && !state.noSkip) state.skip = true; return 1; })()"""


def grab(tag):
    d = json.loads(b.js(JS))
    for u, o in d.items():
        wh = DIMS.get(u)
        if not wh:
            continue
        r = res.setdefault(u, {"file": wh, "mb": round(wh[0] * wh[1] * 4 / 1e6, 2), "shown": [0, 0], "at": []})
        r["shown"] = [max(r["shown"][0], round(o["w"])), max(r["shown"][1], round(o["h"]))]
        r["at"].append(tag + ":" + ",".join(o["where"]))


try:
    b.open(game_url(base, opt("--extra", "")), .5)
    b.wait(f"({INTRO_GONE}) && {FEATURES_UP}", 150)
    time.sleep(1.5); grab("features")
    enter_game(b); time.sleep(2); grab("board")
    for sel, tag, close in (("#bonusBtn", "shop", "closeBonus()"), ("#menuBtn", "info", "document.getElementById('infoClose').click()"),
                            # (Smukiez & Skelly: the bonus intro and the win screens, opened straight from script as review_checks does)
                            ("@void bonusIntro(15, true)", "bonusintro", "finishScreens()"),
                            ("@void totalWinScreen(987654321, { total: true })", "totalwin", "finishScreens()")):
        try:
            if sel.startswith("@"):
                b.js(sel[1:] + "; 1"); time.sleep(3.2)
                if tag == "totalwin":
                    b.js("document.querySelector('.totalwin') && document.querySelector('.totalwin').click(); 1"); time.sleep(1.4)
            else:
                b.js(f"(() => {{ const e = document.querySelector({json.dumps(sel)}); if (e) e.click(); return !!e; }})()")
                time.sleep(1.8)
            grab(tag)
            b.js((FINISH if close == "finishScreens()" else close) + "; 1"); time.sleep(2.5); b.js(FINISH); time.sleep(1.2)
        except Exception as e:
            print(tag, e)
finally:
    b.close()
rows = sorted(res.items(), key=lambda kv: -kv[1]["mb"])
for u, r in rows:
    over = max(r["file"][0] / max(1, r["shown"][0]), r["file"][1] / max(1, r["shown"][1])) if r["shown"][0] else 0
    r["over"] = round(over, 2)
    print(f'{r["mb"]:6.2f} MB file {r["file"][0]}x{r["file"][1]} shown {r["shown"][0]}x{r["shown"][1]} over {over:4.2f}  {u}  {r["at"][:3]}')
json.dump(res, open(out, "w"), indent=1)
