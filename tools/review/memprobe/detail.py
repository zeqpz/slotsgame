"""Where the WebKit model's canvases / WebGL / textures / bitmaps come from: boot the live game at a phone profile
(enter it, wait), then dump __mem.detail() grouped by owner. Smukiez & Skelly phone pass, 2026-11-16.
usage: detail.py OUTJSON [--base URL] [--w 390 --h 844 --dpr 3] [--ua ios|crios] [--extra "&x=1"] [--spin]
"""
import json, os, sys, time
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import Browser, IPHONE_UA, CRIOS_UA, MOCK, game_url, enter_game

a = sys.argv[1:]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
base = opt("--base", MOCK)
w, h, dpr = int(opt("--w", 390)), int(opt("--h", 844)), float(opt("--dpr", 3))
b = Browser(w, h, dpr, ua=CRIOS_UA if opt("--ua", "ios") == "crios" else IPHONE_UA, mobile=dpr > 1)
try:
    b.open(game_url(base, opt("--extra", "")), .3)
    enter_game(b)
    time.sleep(3)
    if "--spin" in a:
        b.js("playRound('base')")
        time.sleep(2)
    b.gc(); time.sleep(.5)
    d = b.js("JSON.stringify(__mem.detail())")
    d = json.loads(d)
    out = {"console": b.console(), "detail": d}
    cv = defaultdict(lambda: [0, 0.0])
    for c in d["cv"]:
        k = (c["type"], c["id"][:30], c["st"].split("|")[0][:90])
        cv[k][0] += 1; cv[k][1] += c["mb"]
    print("canvases (type, id, first frame) n MB:")
    for k, v in sorted(cv.items(), key=lambda kv: -kv[1][1])[:30]:
        print(f"  {v[1]:7.1f} MB  x{v[0]:<4} {k}")
    tx = defaultdict(lambda: [0, 0.0])
    for t in d["tex"]:
        tx[t["gl"][:60]][0] += 1; tx[t["gl"][:60]][1] += t["mb"]
    print("textures by context:")
    for k, v in sorted(tx.items(), key=lambda kv: -kv[1][1]):
        print(f"  {v[1]:7.1f} MB  x{v[0]:<4} {k}")
    print("bitmaps:", len(d["bmp"]), sorted({x["st"][:80] for x in d["bmp"]})[:6])
    print("audio MB:", round(sum(x["mb"] for x in d["aud"]), 1), "n", len(d["aud"]))
    json.dump(out, open(a[0], "w"), indent=1)
finally:
    b.close()
