"""Quick look at the phone tier: boot the live game at phone profiles, enter, shoot the board (and the features
screen); optional replay to its end. Smukiez & Skelly phone pass, 2026-11-16.
usage: phoneshots.py OUTPREFIX [--base URL] [--extra "&mobile=1"] [--profiles p,l,tb,ltb,desk] [--replay mode/event]
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import Browser, IPHONE_UA, MOCK, game_url, enter_game, INTRO_GONE, FEATURES_UP

a = sys.argv[1:]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
pre, base, extra = a[0], opt("--base", MOCK), opt("--extra", "")
P = {"p": (390, 844, 3, 0), "l": (844, 390, 3, 0), "tb": (390, 664, 3, 844), "ltb": (750, 340, 3, 390), "desk": (1600, 900, 1, 0)}
for name in opt("--profiles", "p,l").split(","):
    w, h, dpr, sh = P[name]
    b = Browser(w, h, dpr, ua=None if name == "desk" else IPHONE_UA, mobile=name != "desk")
    try:
        if sh:
            sw, shh = (390, 844) if name == "tb" else (844, 390)
            b.ws.call("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=dpr, mobile=True, screenWidth=sw, screenHeight=shh)
        rp = opt("--replay", "")
        if rp:
            m, e = rp.split("/")
            b.open(f"{base}/?replay=true&game=test&version=1&mode={m}&event={e}&amount=1000000&rgs_url={base}{extra}", .5)
            b.wait("(document.getElementById('replayPlay') || {dataset: {}}).dataset.phase === 'ready'", 150)
            time.sleep(1.5); b.shot(f"{pre}_{name}_rpready.png")
            b.js("document.getElementById('replayPlay').click(); 1")
            t0 = time.time(); k = 0
            while time.time() - t0 < 600 and b.js("document.getElementById('replayPlay').dataset.phase") != "done":
                time.sleep(1); k += 1
                if k % 6 == 0: b.shot(f"{pre}_{name}_rp{k:03d}.png")
                b.js("for (const s of ['.bonusintro', '.totalwin']) { const e = document.querySelector(s); if (e && e.getBoundingClientRect().width > 0 && (e._seen = (e._seen || 0) + 1) > 4) e.click(); } 1")
            time.sleep(1.5); b.shot(f"{pre}_{name}_rpdone.png")
        else:
            b.open(game_url(base, extra), .5)
            b.wait(f"({INTRO_GONE}) && {FEATURES_UP}", 150)
            time.sleep(2); b.shot(f"{pre}_{name}_features.png")
            enter_game(b); time.sleep(3); b.shot(f"{pre}_{name}_board.png")
        print(name, "console", b.console()[:5])
    finally:
        b.close()
