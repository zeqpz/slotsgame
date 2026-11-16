"""Boot the live game at a phone profile, enter it, and print the value of each JS expression given (QA helper).
usage: jsprobe.py [--base URL] [--w 390 --h 844 --dpr 3] [--extra "&x=1"] [--desk] EXPR [EXPR ...]"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import Browser, IPHONE_UA, MOCK, game_url, enter_game

a = sys.argv[1:]
def opt(k, d):
    if k in a:
        i = a.index(k); v = a[i + 1]; del a[i:i + 2]; return v
    return d
base, w, h, dpr, extra = opt("--base", MOCK), int(opt("--w", 390)), int(opt("--h", 844)), float(opt("--dpr", 3)), opt("--extra", "")
desk = "--desk" in a
if desk: a.remove("--desk")
b = Browser(w, h, dpr, ua=None if desk else IPHONE_UA, mobile=not desk)
try:
    b.open(game_url(base, extra), .3)
    enter_game(b)
    time.sleep(2)
    for e in a:
        try:
            print(e, "=>", json.dumps(b.js(e))[:2000])
        except Exception as ex:
            print(e, "=> ERR", str(ex)[:300])
    print("console", b.console()[:6])
finally:
    b.close()
