"""A replayed round in a real WebKit engine (Playwright's WebKit build for Windows: WebContent + GPU process, like iOS)
with iPhone 12 emulation (390x844 @3 or landscape, Safari or Chrome-for-iOS user agent): the WebKit processes'
memory (private bytes, sampled every 100 ms, plus Windows' own peak counters, so a short spike is never missed),
crashes, reloads, console errors, live canvases. iOS crash review 2, 2026-11-16.

Not part of the project's venv: needs a throwaway venv with playwright + psutil and the WebKit build
(  uv venv X; uv pip install --python X playwright psutil; PLAYWRIGHT_BROWSERS_PATH=Y X -m playwright install webkit  ).
usage: wkprobe.py OUTJSON --base URL --mode base --event 33152 [--land] [--crios] [--ablate a,b] [--shot PNG] [--reps 1]
ablations (functions replaced after load, to find what a spike comes from): nodebris nopopfx nocork norigpop nosplash
"""
import json, sys, threading, time
import psutil
from playwright.sync_api import sync_playwright

a = sys.argv[1:]
out = a[0]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
base = opt("--base", "http://localhost:8733")
mode, event = opt("--mode", "corkstorm"), opt("--event", "43029")
land, crios = "--land" in a, "--crios" in a
abl = [x for x in opt("--ablate", "").split(",") if x]
reps = int(opt("--reps", 1))
shot = opt("--shot", "")
CRIOS = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
         "CriOS/141.0.7390.96 Mobile/15E148 Safari/604.1")
ABL = {
    "nodebris": "window.debrisBlow = () => false;",
    "nopopfx": "window.popFx = () => {};",
    "nocork": "window.corkShot = () => false;",
    "nosplash": "window.fxSplash = () => {};",
    "norigpop": "(() => { const rp = window.rigPlay; window.rigPlay = (c, clip, o) => clip === 'pop' ? null : rp(c, clip, o); })();",
}
CENSUS = """(() => { const cv = [...document.querySelectorAll('canvas')]; let px = 0; for (const c of cv) px += c.width * c.height;
  let cork = 0, pops = 0; try { cork = FXS.parts.filter(p => p.kind === 'cork').length; } catch (e) {} try { pops = bursts.length; } catch (e) {}
  return JSON.stringify({ n: cv.length, mb: +(px * 4 / 1e6).toFixed(1), cork, pops, lite: !!window.LITE, mob: !!window.MOBILE,
    zfit: document.documentElement.classList.contains('zfit'), gfxLow: !!(window.GFX && GFX.low),
    phase: (document.getElementById('replayPlay') || { dataset: {} }).dataset.phase || '' }); })()"""


def kind(p):
    try:
        n = p.name().lower()
    except Exception:
        return None
    return "web" if "webprocess" in n else "gpu" if "gpuprocess" in n else "net" if "network" in n else "ui" if "playwright" in n else None


res = {"mode": mode, "event": event, "land": land, "crios": crios, "ablate": abl, "runs": []}
with sync_playwright() as pw:
    for rep in range(reps):
        dev = dict(pw.devices["iPhone 12 landscape" if land else "iPhone 12"])
        if crios:
            dev["user_agent"] = CRIOS
        br = pw.webkit.launch()
        root = None
        for p in psutil.process_iter(["name", "create_time"]):
            if (p.info["name"] or "").lower() == "playwright.exe":
                if not root or p.info["create_time"] > root.info["create_time"]:
                    root = p
        ctx = br.new_context(**dev)
        if abl:
            ctx.add_init_script("addEventListener('load', () => { " + " ".join(ABL[x] for x in abl) + " });")
        pg = ctx.new_page()
        log, crashed, navs = [], [], []
        pg.on("console", lambda m: log.append(f"{m.type}: {m.text[:300]}") if m.type in ("error", "warning") else None)
        pg.on("pageerror", lambda e: log.append(f"pageerror: {str(e)[:300]}"))
        pg.on("crash", lambda *_: crashed.append(time.time()))
        pg.on("framenavigated", lambda f: navs.append(f.url) if f == pg.main_frame else None)
        samples, stop, t0 = [], [False], [time.time()]
        procs = {}

        def sampler():
            while not stop[0]:
                if root:
                    try:
                        for c in root.children(recursive=True):
                            k = kind(c)
                            if k in ("web", "gpu"):
                                procs[c.pid] = (k, c)
                    except Exception:
                        pass
                row = {"t": round(time.time() - t0[0], 2)}
                for pid, (k, pr) in list(procs.items()):
                    try:
                        row[k] = row.get(k, 0) + pr.memory_info().private / 1e6
                    except Exception:
                        pass
                samples.append(row)
                time.sleep(.1)
        th = threading.Thread(target=sampler, daemon=True); th.start()
        url = f"{base}/?replay=true&game=test&version=1&mode={mode}&event={event}&amount=1000000&rgs_url={base}"
        pg.goto(url)
        t1 = time.time()
        while time.time() - t1 < 120 and pg.evaluate("(document.getElementById('replayPlay')||{dataset:{}}).dataset.phase") != "ready":
            time.sleep(.3)
        time.sleep(3)
        idle = samples[-1] if samples else {}
        t0[0] = time.time(); samples.clear()
        # a bonus's intro and TOTAL WIN wait for a press: given one once they have been up ~3 s
        pg.evaluate("""() => { clearInterval(window.__clk); const seen = {};
          window.__clk = setInterval(() => { for (const s of ['.bonusintro', '.totalwin']) { const e = document.querySelector(s);
            if (e && e.getBoundingClientRect().width > 0) { seen[s] = (seen[s] || 0) + 1; if (seen[s] > 8) { e.click(); seen[s] = 0; } } } }, 400); }""")
        pg.click("#replayPlay")
        cpeak = {"n": 0, "mb": 0}; took = False; done = False; c = {}
        while time.time() - t0[0] < 700 and not crashed:
            try:
                c = json.loads(pg.evaluate(CENSUS))
            except Exception as e:
                log.append("evaluate: " + str(e)[:200]); break
            cpeak["n"] = max(cpeak["n"], c["n"]); cpeak["mb"] = max(cpeak["mb"], c["mb"])
            if shot and not took and c["pops"]:
                pg.screenshot(path=shot); took = True
            if samples:
                samples[-1]["cork"] = c["cork"]; samples[-1]["pops"] = c["pops"]; samples[-1]["cmb"] = c["mb"]
            if c["phase"] == "done":
                done = True; break
            time.sleep(.2)
        stop[0] = True; th.join()
        peaks = {}
        for pid, (k, pr) in procs.items():
            try:
                mi = pr.memory_info()
                peaks[k] = round(peaks.get(k, 0) + mi.peak_pagefile / 1e6, 1)
            except Exception:
                pass
        sp = {k: round(max((s.get(k, 0) for s in samples), default=0), 1) for k in ("web", "gpu")}
        tot = round(max((s.get("web", 0) + s.get("gpu", 0) for s in samples), default=0), 1)
        at = max(samples, key=lambda s: s.get("web", 0) + s.get("gpu", 0))["t"] if samples else 0
        run = {"rep": rep, "done": done, "secs": round(time.time() - t0[0], 1), "crashed": bool(crashed), "navigations": len(navs),
               "idle": {k: round(v, 1) for k, v in idle.items() if k != "t"}, "sampled_peak": sp, "sampled_peak_total": tot, "peak_at_s": at,
               "os_peak_private": peaks, "canvas_peak": cpeak, "console": log[:20], "series": [{k: (round(v, 1) if isinstance(v, float) else v) for k, v in x.items()} for x in samples[::3]], "lite": c.get("lite") if not crashed else None,
               "mob": c.get("mob"), "zfit": c.get("zfit"), "gfxLow": c.get("gfxLow")}
        res["runs"].append(run)
        print(json.dumps({k: v for k, v in run.items() if k not in ("console", "series")}), "console:", log[:4], flush=True)
        br.close()
json.dump(res, open(out, "w"), indent=1)
