"""Screens of two builds side by side, held still, and how many pixels differ (iOS memory, 2026-11-16).

For each build (--a URL, --b URL; e.g. the commit before served on another port, and this one) and each profile
(phone 390x844 / 844x390 @3 with the iOS Safari UA, desktop 1600x900 @1), the same states: the features screen, the
board after entering, the bonus shop, the rules panel; and a replayed round at its end (PLAY AGAIN). Math.random is
seeded before the page runs, so both builds roll the same idles; before each shot every CSS animation is held at its
end (or at 1 s for a looping one) and every symbol is put back on its rest pose, so what is compared is the picture,
not the moment. Writes A|B|diff sheets and diff.json (share of pixels off by > 16/255, mean, where).
usage: abshots.py OUTDIR --a URL --b URL [--only phone_p,phone_l,desk]
"""
import json, os, sys, time
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import Browser, IPHONE_UA, game_url, enter_game, INTRO_GONE, FEATURES_UP

a = sys.argv[1:]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
out = Path(a[0]); out.mkdir(parents=True, exist_ok=True)
A, B = opt("--a", "http://localhost:8756"), opt("--b", "http://localhost:8733")
only = [x for x in opt("--only", "").split(",") if x]
PROFILES = [("phone_p", 390, 844, 3, IPHONE_UA, True), ("phone_l", 844, 390, 3, IPHONE_UA, True), ("desk", 1600, 900, 1, None, False),
            # Safari with its toolbar: a 390x664 window on a 390x844 screen
            ("phone_tb", 390, 664, 3, IPHONE_UA, True)]
SEED = """(() => { let s = 0x2F6E2B1; Math.random = () => { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; return ((s >>> 0) % 1e9) / 1e9; }; })();"""
HOLD = """(() => {
  for (const an of document.getAnimations()) { try { const t = an.effect.getComputedTiming(); an.pause(); an.currentTime = isFinite(t.endTime) ? t.endTime : 1000; } catch (e) {} }
  try { rigPlay = () => null; } catch (e) {}   // no new clip starts (an idle due in the next second)
  try { for (const el of [...symPlaying]) rigStop(el); } catch (e) {}
  try { document.querySelectorAll('.rig').forEach(el => { if (el._clip) rigStop(el); }); } catch (e) {}
  try { BoardGL.touch(); } catch (e) {}
  return 1; })()"""


def states(b, base, tag):
    shots = {}
    def hold_shot(name):
        b.js(HOLD); time.sleep(.6); b.js(HOLD); time.sleep(.4)
        shots[name] = b.shot(out / f"{tag}_{name}.png")
    b.open(game_url(base), .5)
    b.wait(f"({INTRO_GONE}) && {FEATURES_UP}", 150)
    time.sleep(2.5); hold_shot("features")
    b.js("document.getAnimations().forEach(x => x.play()); 1")
    enter_game(b); time.sleep(3); hold_shot("board")
    b.js("document.getElementById('bonusBtn').click(); 1"); time.sleep(2); hold_shot("shop")
    b.js("closeBonus(); 1"); time.sleep(1.2)
    b.js("document.getElementById('menuBtn').click(); 1"); time.sleep(2); hold_shot("rules")
    b.js("document.getElementById('infoClose').click(); 1"); time.sleep(1)
    b.open(f"{base}/?replay=true&game=test&version=1&mode=base&event=33152&amount=1000000&rgs_url={base}", .5)
    b.wait("(document.getElementById('replayPlay') || {dataset: {}}).dataset.phase === 'ready'", 150)
    time.sleep(2); hold_shot("replay_ready")
    b.js("document.getAnimations().forEach(x => x.play()); document.getElementById('replayPlay').click(); 1")
    t0 = time.time()
    while time.time() - t0 < 240 and b.js("document.getElementById('replayPlay').dataset.phase") != "done":
        time.sleep(.5)
    time.sleep(2); hold_shot("replay_done")
    return shots


res = {}
from PIL import Image
import numpy as np
for name, w, h, dpr, ua, mob in PROFILES:
    if only and name not in only:
        continue
    got = {}
    for which, base in (("a", A), ("b", B)):
        br = Browser(w, h, dpr, ua=ua, mobile=mob)
        try:
            br.ws.call("Page.addScriptToEvaluateOnNewDocument", source=SEED)
            if name == "phone_tb":
                br.ws.call("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=dpr, mobile=True, screenWidth=390, screenHeight=844)
            got[which] = states(br, base, f"{name}_{which}")
            got[which + "_console"] = br.console()
        finally:
            br.close()
    for st in got["a"]:
        IA = np.asarray(Image.open(got["a"][st]).convert("RGB")).astype(int)
        IB = np.asarray(Image.open(got["b"][st]).convert("RGB")).astype(int)
        if IA.shape != IB.shape:
            res[f"{name}/{st}"] = {"shape": [IA.shape, IB.shape]}
            continue
        d = np.abs(IA - IB).max(axis=2)
        ys, xs = np.nonzero(d > 16)
        res[f"{name}/{st}"] = {"over16_pct": round(float((d > 16).mean()) * 100, 3), "over4_pct": round(float((d > 4).mean()) * 100, 3),
                               "mean": round(float(np.abs(IA - IB).mean()), 3),
                               "bbox16": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(xs) else None}
        sheet = np.concatenate([IA, IB, np.minimum(255, d[..., None].repeat(3, 2) * 4)], axis=1).astype("uint8")
        im = Image.fromarray(sheet)
        if im.width > 3000:
            im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
        im.save(out / f"ab_{name}_{st}.png")
        print(name, st, json.dumps(res[f"{name}/{st}"]), flush=True)
    res[f"{name}/console"] = {"a": got["a_console"][:8], "b": got["b_console"][:8]}
json.dump(res, open(out / "diff.json", "w"), indent=1)
