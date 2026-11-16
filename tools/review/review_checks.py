"""Engine review 2026-11-16 - headless checks for the fixes (needs the mock RGS on :8733).

  .venv312\\Scripts\\python.exe -I tools/review/review_checks.py [buys] [auto] [openbet] [replay] [social] [sizes]

  buys     every bonus bought with enough balance, real (USD) and GC/social (the mock sends gameModes[].maxBet 0
           for every mode on a GC wallet, as the live RGS does): rounds play, the balance is start - price + win,
           cards are disabled only when the price is over the balance, never "Lower the bet" at a 0 cap
  auto     the reviewer's autoplay scenario in both modes: a low balance, 25 rounds at 1.00 - autoplay ends by
           itself, the bar is fully back, a plain spin works at the lowest level; Auto and Spin stop a run;
           a run that cannot cover even its first round never starts
  openbet  a default level above the balance opens on the highest level the balance covers
  replay   the Bet Replay window for a loss, a small win, a big win, a bonus and an extreme bonus, real and social
  social   every screen in social mode (HUD, shop, autoplay, rules, notices, bonus intro, win sign, history,
           replay) free of the restricted words (RULES.SWEEPS) and "$"
  sizes    screenshots at 1920x1080, 390x844, 844x390 and 400x225 (Popout S)

Screenshots go to research/review_2026-11-16/ (git-ignored scratch). Exit code 1 on any failure.
"""
import json, random, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
from cdp import Browser, MOCK, enter_game

OUT = Path(__file__).resolve().parents[2] / "research" / "review_2026-11-16"
U = 1_000_000
FAIL = []


def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what)
    if not ok:
        FAIL.append(what)


def url(sid, social=False, currency=None, extra=""):
    u = f"{MOCK}/index.html?sessionID={sid}&rgs_url={MOCK}&lang=en&device=desktop"
    if social:
        u += "&social=true"
    if currency:
        u += "&currency=" + currency
    return u + extra


def session(tag, units, currency="USD"):
    return f"{tag}{random.randint(100000, 999999)}~{units}" + ("" if currency == "USD" else "@" + currency)


def open_game(b, units, social, currency, tag="rv"):
    b.open(url(session(tag, units, currency), social, currency if currency != "USD" else None))
    enter_game(b)
    b.js("setRapid(true)")


def set_bet(b, amount):
    i = b.js(f"state.bets.indexOf({amount})")
    assert i >= 0, amount
    b.js(f"state.betIdx = {i}; refreshBet()")


# Plays out whatever is on screen: skips the reels, clicks through the bonus intro and the win signs.
FINISH = """(() => {
  for (const el of document.querySelectorAll('.bonusintro, .totalwin')) el.click();
  if (state.playing && !state.noSkip) state.skip = true;
  return state.playing || !!document.querySelector('.bonusintro, .totalwin');
})()"""


def finish(b, timeout=300):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not b.js(FINISH):
            return True
        time.sleep(.35)
    return False


def hist_len(b):
    return b.js("JSON.parse(localStorage.getItem(histKey()) || '[]').length")


def hist0(b):
    return json.loads(b.js("JSON.stringify(JSON.parse(localStorage.getItem(histKey()) || '[]')[0] || null)"))


def server_balance(b):
    return b.js("RGS.balance().then(() => RGS.state.balance)")


CARDS = """JSON.stringify([...document.querySelectorAll('#bshopRow .bscard')].map(c => ({ mode: c.dataset.mode,
  title: c.querySelector('.bsttl').textContent, price: c.querySelector('.bsprice').textContent,
  button: c.querySelector('.bsget').textContent, disabled: c.querySelector('.bsget').disabled })))"""


def buys():
    print("\n== buys: every bonus with enough balance, real and GC/social ==")
    b = Browser(1280, 720)
    try:
        for social, cur in ((False, "USD"), (True, "XGC")):
            tag = "GC/social" if social else "real"
            open_game(b, 1000, social, cur)
            set_bet(b, U)
            b.js("openBonus()"); time.sleep(.9)
            cards = json.loads(b.js(CARDS))
            check(len(cards) == 3, f"{tag}: three cards {[(c['mode'], c['button']) for c in cards]}")
            check(not any("lower" in c["button"].lower() for c in cards), f"{tag}: no card asks to lower the bet at 1.00 (maxBet {b.js('JSON.stringify(RGS.state.config.gameModes.map(m => m.maxBet))')})")
            check(all(not c["disabled"] for c in cards), f"{tag}: every card enabled with 1,000 in the wallet")
            OUT.mkdir(parents=True, exist_ok=True)
            b.shot(OUT / f"bonus_cards_{'social_xgc' if social else 'real_usd'}.png")
            for mode, cost in (("bonus", 100), ("extremebonus", 400)):
                before, n0 = b.js("state.balance"), hist_len(b)
                if b.js("$('bonusWrap').hidden"):
                    b.js("openBonus()"); time.sleep(.8)
                b.js(f"document.querySelector('.bscard[data-mode={mode}] .bsget').click()"); time.sleep(.3)
                b.js(f"document.querySelector('.bscard[data-mode={mode}] .bsget').click()"); time.sleep(1.2)
                played = finish(b)
                h = hist0(b)
                ok = played and hist_len(b) == n0 + 1 and h and h["mode"] == mode
                check(ok, f"{tag}: {mode} bought and played out ({h and h['mode']}, win {h and h['payout']})")
                if ok:
                    want = before - cost * U + h["payout"]
                    shown, srv = b.js("state.balance"), server_balance(b)
                    check(shown == want == srv, f"{tag}: {mode} balance {shown} = start {before} - {cost * U} + win {h['payout']} = server {srv}")
            # a price over the balance disables a card, with "Low balance" - never "Lower the bet"
            set_bet(b, 20 * U)
            b.js("openBonus()"); time.sleep(.8)
            cards = {c["mode"]: c for c in json.loads(b.js(CARDS))}
            bal = b.js("state.balance")
            for m, cost in (("bonus", 100), ("extremebonus", 400)):
                over = cost * 20 * U > bal
                check(cards[m]["disabled"] == over and (("balance" in cards[m]["button"].lower()) == over),
                      f"{tag}: at 20.00 {m} {'disabled, Low balance' if over else 'enabled'} ({cards[m]['button']})")
            b.js("closeBonus()"); time.sleep(.5)
            # Bonus Boost: on, a spin costs 1.25x
            set_bet(b, U)
            b.js("openBonus()"); time.sleep(.8)
            b.js("document.querySelector('.bscard[data-mode=boost] .bsget').click()"); time.sleep(.3)
            b.js("closeBonus()"); time.sleep(.6)
            before, n0 = b.js("state.balance"), hist_len(b)
            b.js("$('spinBtn').click()"); time.sleep(.8)
            finish(b)
            h = hist0(b)
            check(hist_len(b) == n0 + 1 and h["mode"] == "boost" and b.js("state.balance") == before - 1_250_000 + h["payout"],
                  f"{tag}: Bonus Boost spin charged 1.25 and played as boost ({h['mode']})")
            b.js("state.boost = false; refreshBet()")
            check(not b.console(), f"{tag}: console clean {b.console()[:3]}")
    finally:
        b.close()


AUTO_STATE = """JSON.stringify({ auto: state.auto || 0, playing: !!state.playing, on: $('autoBtn').classList.contains('on'),
  label: $('autoBtn').getAttribute('aria-label'), count: $('autoN').hidden ? '' : $('autoN').textContent,
  spin: $('spinBtn').textContent, spinOff: $('spinBtn').disabled, autoOff: $('autoBtn').disabled,
  balance: state.balance, bet: bet(), notice: $('notice').textContent })"""


def start_auto(b, n):
    b.js("$('autoBtn').click()"); time.sleep(.6)
    b.js(f"document.querySelector('#autoOpts button[data-n=\"{n}\"]').click()"); time.sleep(.2)
    b.js("$('autoYes').click()"); time.sleep(.3)


def bar_back(b, tag, what):
    s = json.loads(b.js(AUTO_STATE))
    check(s["auto"] == 0 and not s["on"] and not s["count"] and s["label"] in ("Auto play",) and not s["autoOff"]
          and not s["spinOff"] and s["spin"] == "Spin", f"{tag}: {what}: autoplay fully off, bar back {s}")
    return s


def auto():
    print("\n== auto: the reviewer's scenario (low balance, 25 rounds), stop, spin-stop, no start ==")
    b = Browser(1280, 720)
    try:
        for social, cur in ((False, "USD"), (True, "XGC")):
            tag = "GC/social" if social else "real"
            # 1. the reviewer: a balance that cannot cover all 25 rounds at 1.00
            open_game(b, 3.3, social, cur)
            set_bet(b, U)
            n0 = hist_len(b)
            start_auto(b, 25)
            s = json.loads(b.js(AUTO_STATE))
            check(s["auto"] > 0 and s["on"], f"{tag}: 25 rounds start on 3.30 (only the first round has to be covered) {s['auto']}")
            t0 = time.time()
            while time.time() - t0 < 400 and b.js("state.auto > 0 || state.playing"):
                b.js(FINISH); time.sleep(.4)
            finish(b); time.sleep(.8)
            s = bar_back(b, tag, "25 rounds on 3.30 ended by itself")
            ran = hist_len(b) - n0
            check(ran == 25 or s["balance"] < U, f"{tag}: it ran {ran} rounds and stopped only when 1.00 was not covered (balance {s['balance']})")
            # plain spins at the lowest level and at any level the balance covers
            b.js("state.betIdx = 0; refreshBet()")
            for lvl in [0] + [i for i in range(1, 8)]:
                if b.js(f"state.bets[{lvl}] <= state.balance"):
                    b.js(f"state.betIdx = {lvl}; refreshBet()")
                    n1, bal = hist_len(b), b.js("state.balance")
                    b.js("$('spinBtn').click()"); time.sleep(.6)
                    finish(b); time.sleep(.4)
                    check(hist_len(b) == n1 + 1, f"{tag}: after autoplay a plain spin at level {lvl} ({b.js('fmt(bet())')}) plays (balance {bal} -> {b.js('state.balance')})")
            b.shot(OUT / f"auto_after_lowbalance_{'social' if social else 'real'}.png")
            # 2. Auto stops a run at once; nothing more starts; Spin works
            open_game(b, 1000, social, cur)
            set_bet(b, 10_000)
            start_auto(b, 100)
            t0 = time.time()
            while time.time() - t0 < 60 and hist_len(b) < 2:
                b.js(FINISH); time.sleep(.3)
            b.js("$('autoBtn').click()"); time.sleep(.2)
            check(b.js("state.auto") == 0, f"{tag}: the Auto press stops the run at once")
            finish(b); time.sleep(2)
            n1 = hist_len(b); time.sleep(2.5)
            check(hist_len(b) == n1, f"{tag}: no round starts after the stop")
            bar_back(b, tag, "after Auto stop")
            b.js("$('spinBtn').click()"); time.sleep(.6); finish(b)
            check(hist_len(b) == n1 + 1, f"{tag}: a plain spin plays after the stop")
            # 3. Spin between two autoplay rounds stops the run and starts nothing
            start_auto(b, 100)
            t0, stopped = time.time(), False
            while time.time() - t0 < 60:
                if b.js("state.auto > 0 && !state.playing && !document.querySelector('.bonusintro, .totalwin')"):
                    n2 = hist_len(b)
                    b.js("$('spinBtn').click()"); stopped = True; break
                b.js(FINISH); time.sleep(.05)
            time.sleep(.3)
            check(stopped and b.js("state.auto") == 0, f"{tag}: Spin between two autoplay rounds stops the run")
            finish(b); time.sleep(2)
            check(stopped and hist_len(b) == n2, f"{tag}: ... and starts no round of its own ({hist_len(b)} vs {n2 if stopped else '-'})")
            bar_back(b, tag, "after the Spin stop")
            # 4. a run that cannot cover its first round never starts
            open_game(b, 0.5, social, cur)
            set_bet(b, U)
            start_auto(b, 25)
            time.sleep(.6)
            s = json.loads(b.js(AUTO_STATE))
            check(s["auto"] == 0 and not s["on"] and "balance" in s["notice"].lower(), f"{tag}: 25 rounds on 0.50 at 1.00 never start and say why ({s['notice']})")
            check(not b.console(), f"{tag}: console clean {b.console()[:3]}")
    finally:
        b.close()


# The authenticate answer rewritten in the page (the mock always says 1.00): default level 5.00
OPENBET = """(() => { const real = window.fetch;
  window.fetch = async (u, o) => { const res = await real(u, o);
    if (!String(u).includes('/wallet/authenticate')) return res;
    const d = await res.clone().json(); d.config.defaultBetLevel = 5000000;
    return new Response(JSON.stringify(d), { status: 200, headers: { 'Content-Type': 'application/json' } }); }; })();"""


def openbet():
    print("\n== openbet: default above the balance -> the highest level covered ==")
    b = Browser(1280, 720)
    try:
        ident = b.preload(OPENBET)
        for social, cur in ((False, "USD"), (True, "XGC")):
            b.open(url(session("ob", 2.5, cur), social, cur if social else None)); enter_game(b)
            check(b.js("bet()") == 2_000_000, f"{'GC/social' if social else 'real'}: 2.50 in the wallet, default 5.00 -> opens at 2.00 ({b.js('fmt(bet())')})")
            b.open(url(session("ob", 1000, cur), social, cur if social else None)); enter_game(b)
            check(b.js("bet()") == 5_000_000, f"{'GC/social' if social else 'real'}: 1,000 in the wallet -> opens at the default 5.00 ({b.js('fmt(bet())')})")
        b.unpreload(ident)
    finally:
        b.close()


REPLAYS = [("base", 3, "loss"), ("base", 0, "small win"), ("base", 38, "big win"), ("bonus", 5, "bonus"), ("extremebonus", 3, "extreme bonus")]
RP = """JSON.stringify({ phase: $('replayPlay').dataset.phase, hidden: $('replayWrap').hidden,
  rows: [...document.querySelectorAll('#rpCard .rprow')].map(r => r.querySelector('.k').textContent + ': ' + r.querySelector('.v').textContent),
  title: $('rpTitle').textContent, go: $('rpGoTxt').textContent, status: $('rpStatus').hidden ? '' : $('rpStatus').textContent, note: $('rpNote').textContent })"""


def replay():
    print("\n== replay: the Bet Replay window ==")
    b = Browser(1280, 720)
    try:
        for social in (False, True):
            tag = "social" if social else "real"
            for mode, ev, what in REPLAYS:
                amt = 2_000_000
                b.open(f"{MOCK}/index.html?replay=true&game=test&version=1&mode={mode}&event={ev}&amount={amt}"
                       f"&rgs_url={MOCK}&lang=en&device=desktop" + ("&social=true&currency=XGC" if social else "&currency=USD"))
                ok = b.wait("$('replayPlay').dataset.phase === 'ready'", 60)
                d = json.loads(b.js(RP))
                book = json.loads(b.js(f"fetch('{MOCK}/bet/replay/test/1/{mode}/{ev}').then(r => r.json()).then(j => JSON.stringify({{m: j.payoutMultiplier, c: j.costMultiplier}}))"))
                want = b.js(f"fmt(Math.round({book['m']} * {amt}))")
                check(ok, f"{tag} {what}: ready with Start ({d['go']}) {d['rows']}")
                if ok and mode == "base" and ev == 38:
                    b.shot(OUT / f"replay_start_{tag}.png")
                b.js("$('replayPlay').click()"); time.sleep(1)
                t0 = time.time()
                while time.time() - t0 < 300 and b.js("$('replayPlay').dataset.phase") != "done":
                    b.js(FINISH); time.sleep(.4)
                d = json.loads(b.js(RP))
                rows = dict(r.split(": ", 1) for r in d["rows"])
                win = list(rows.values())[-1]
                check(d["phase"] == "done" and d["go"].lower() == "play again" and win == want,
                      f"{tag} {what}: played, then PLAY AGAIN; total win {win} = {book['m']}x the bet {want}")
                if mode == "base" and ev == 38:
                    b.shot(OUT / f"replay_end_{tag}.png")
                check(not b.js("document.querySelector('body.replay #spinBtn') && getComputedStyle($('spinBtn')).display !== 'none'"), f"{tag} {what}: no betting UI")
            b.open(f"{MOCK}/index.html?replay=true&game=test&version=1&mode=base&event=99999999&amount=1000000&rgs_url={MOCK}&lang=en" + ("&social=true" if social else ""))
            ok = b.wait("$('replayPlay').dataset.phase === 'error'", 30)
            check(ok, f"{tag}: a bad event shows the error state {json.loads(b.js(RP))['title']}")
            b.shot(OUT / f"replay_error_{tag}.png")
            errs = [e for e in b.console() if "500" not in e]   # the failed GET of the bad event is the one expected
            check(not errs, f"{tag}: console clean {errs[:3]}")
    finally:
        b.close()


SCAN = """(() => {
  const RX = new RegExp('\\\\b(' + RULES.SWEEPS.map(p => p[0].replace(/ /g, '\\\\s+')).join('|') + ')\\\\b', 'i');
  const hits = [];
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    if (/^(SCRIPT|STYLE)$/.test(n.parentElement.tagName)) continue;
    const t = n.nodeValue; if (RX.test(t) || t.includes('$')) hits.push(t.trim().slice(0, 140));
  }
  for (const el of document.querySelectorAll('[aria-label], [title], [alt]'))
    for (const a of ['aria-label', 'title', 'alt']) { const v = el.getAttribute(a); if (v && (RX.test(v) || v.includes('$'))) hits.push(a + ': ' + v.slice(0, 140)); }
  return JSON.stringify(hits);
})()"""


def social():
    print("\n== social: every screen free of restricted words ==")
    b = Browser(1280, 720)
    try:
        def scan(where):
            hits = json.loads(b.js(SCAN))
            check(not hits, f"social {where}: no restricted word {hits[:6]}")
        for how in ("url", "jurisdiction"):
            if how == "url":
                b.open(url(session("so", 1000, "XGC"), True, "XGC"))
            else:   # no social=true in the link: authenticate's jurisdiction.socialCasino alone
                ident = b.preload("""(() => { const real = window.fetch; window.fetch = async (u, o) => { const res = await real(u, o);
                  if (!String(u).includes('/wallet/authenticate')) return res; const d = await res.clone().json(); d.config.jurisdiction.socialCasino = true;
                  return new Response(JSON.stringify(d), { status: 200, headers: { 'Content-Type': 'application/json' } }); }; })();""")
                b.open(url(session("so", 1000, "XGC"), False, "XGC"))
            time.sleep(1.5); scan(f"[{how}] loading screen")
            enter_game(b); b.js("setRapid(true)")
            if how != "url":
                b.unpreload(ident)
                check(b.js("SOCIAL") is True, "social from the jurisdiction alone")
            scan(f"[{how}] HUD")
            set_bet(b, U)
            b.js("openBonus()"); time.sleep(.9); scan(f"[{how}] bonus panel")
            b.js("document.querySelector('.bscard[data-mode=bonus] .bsget').click()"); time.sleep(.3); scan(f"[{how}] bonus panel armed")
            b.js("closeBonus(); bshopArmed = null"); time.sleep(.5)
            b.js("$('autoBtn').click()"); time.sleep(.6); scan(f"[{how}] autoplay picker")
            b.js("autoDismiss && autoDismiss()"); time.sleep(.4)
            for code in ("ERR_IPB", "ERR_VAL", "ERR_GLE"):
                b.js(f"notice(`<b>${{rgsMessage({{ code: '{code}' }})}}</b>`, true)"); scan(f"[{how}] notice {code}")
            b.js("notice(T('<b>Not enough balance</b> — lower the {bet|play amount}.'), true)"); scan(f"[{how}] notice low balance")
            b.js("state.betIdx = state.bets.length - 1; refreshBet(); $('spinBtn').click()"); time.sleep(.5); scan(f"[{how}] notice from a spin over the balance")
            set_bet(b, U)
            # a bought bonus: intro, spins, total win
            b.js("openBonus()"); time.sleep(.8)
            b.js("document.querySelector('.bscard[data-mode=bonus] .bsget').click()"); time.sleep(.2)
            b.js("document.querySelector('.bscard[data-mode=bonus] .bsget').click()")
            seen = set()
            t0 = time.time()
            while time.time() - t0 < 300:
                if b.js("!!document.querySelector('.bonusintro')") and "intro" not in seen:
                    time.sleep(1.2); scan(f"[{how}] bonus intro"); seen.add("intro")
                if b.js("!!document.querySelector('.totalwin')") and "total" not in seen:
                    time.sleep(1.2); scan(f"[{how}] win sign"); seen.add("total")
                if not b.js(FINISH):
                    break
                time.sleep(.3)
            scan(f"[{how}] after the bonus")
            b.js("$('menuBtn').click()"); time.sleep(1.2); scan(f"[{how}] rules, paytable and recent rounds")
            if how == "url":
                b.shot(OUT / "social_rules.png")
            b.js("document.querySelector('#infoClose') && $('infoClose').click()"); time.sleep(.5)
            # a big spin win's sign, drawn directly
            b.js("void totalWinScreen(123456789, { total: false })"); time.sleep(1.5); scan(f"[{how}] spin win sign")
            finish(b)
            for x in ("false", "true"):   # the bonus intros, drawn directly (a skipped bonus may pass them by)
                b.js(f"void bonusIntro(12, {x})"); time.sleep(2.5); scan(f"[{how}] bonus intro (extreme {x})")
                finish(b)
            b.js("void totalWinScreen(55555555, { total: true })"); time.sleep(2)
            b.js("document.querySelector('.totalwin').click()"); time.sleep(1.5); scan(f"[{how}] bonus total win sign")
            finish(b)
            check(not b.console(), f"social [{how}]: console clean {b.console()[:3]}")
        b.open(f"{MOCK}/index.html?replay=true&game=test&version=1&mode=bonus&event=5&amount=1000000&rgs_url={MOCK}&lang=en&social=true")
        b.wait("$('replayPlay').dataset.phase === 'ready'", 60); scan("replay window, no currency in the link")
        check("$" not in b.js("$('rpCard').textContent"), "social replay with no currency: bare figures, no $")
        b.js("$('replayPlay').click()")
        t0 = time.time()
        while time.time() - t0 < 300 and b.js("$('replayPlay').dataset.phase") != "done":
            b.js(FINISH); time.sleep(.4)
        scan("replay window at the end")
        b.shot(OUT / "replay_end_social_nocurrency.png")
    finally:
        b.close()


SIZES = [(1920, 1080, "desktop"), (390, 844, "phone_portrait"), (844, 390, "phone_landscape"), (400, 225, "popout_s")]


def sizes():
    print("\n== sizes: screenshots ==")
    for w, h, name in SIZES:
        b = Browser(w, h)
        try:
            b.open(url(session("sz", 1000, "XGC"), True, "XGC"), settle=0)
            for t in (1.6, 3.2):   # the SMUKIEZ ident mid-drop and landed
                time.sleep(t - (1.6 if t > 1.6 else 0))
                b.shot(OUT / f"intro_{name}_{t:.1f}s.png")
            enter_game(b); b.js("setRapid(true)")
            b.shot(OUT / f"game_{name}.png")
            b.js("openBonus()"); time.sleep(1); b.shot(OUT / f"bonus_{name}.png")
            b.js("closeBonus()"); time.sleep(.6)
            b.js("void bonusIntro(15, true)"); time.sleep(2.2); b.shot(OUT / f"bonusintro_{name}.png")
            fit = json.loads(b.js("""JSON.stringify((() => { const r = document.querySelector('.bonusintro .bstack').getBoundingClientRect();
              return { l: r.left, t: r.top, r: r.right, b: r.bottom, W: innerWidth, H: innerHeight }; })())"""))
            check(fit["l"] >= -1 and fit["t"] >= -1 and fit["r"] <= fit["W"] + 1 and fit["b"] <= fit["H"] + 1, f"{name}: bonus intro inside the window {fit}")
            finish(b); time.sleep(.6)
            b.js("void totalWinScreen(987654321, { total: true })"); time.sleep(3)
            b.js("document.querySelector('.totalwin').click()"); time.sleep(1.2)
            b.shot(OUT / f"winsign_{name}.png")
            box = json.loads(b.js("""JSON.stringify((() => { const els = [...document.querySelectorAll('.totalwin .twhead .twlogo.on, .totalwin .twamount')];
              const rs = els.map(e => e.getBoundingClientRect()).filter(r => r.width);
              return { l: Math.min(...rs.map(r => r.left)), t: Math.min(...rs.map(r => r.top)), r: Math.max(...rs.map(r => r.right)), b: Math.max(...rs.map(r => r.bottom)), W: innerWidth, H: innerHeight }; })())"""))
            check(box["l"] >= -1 and box["t"] >= -1 and box["r"] <= box["W"] + 1 and box["b"] <= box["H"] + 1, f"{name}: win sign whole inside the window {box}")
            finish(b)
            b.open(f"{MOCK}/index.html?replay=true&game=test&version=1&mode=base&event=38&amount=1000000&rgs_url={MOCK}&lang=en&currency=USD")
            b.wait("$('replayPlay').dataset.phase === 'ready'", 60); time.sleep(.6)
            b.shot(OUT / f"replay_{name}.png")
            r = json.loads(b.js("JSON.stringify((() => { const r = $('rpCard').getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom, W: innerWidth, H: innerHeight }; })())"))
            check(r["l"] >= -1 and r["t"] >= -1 and r["r"] <= r["W"] + 1 and r["b"] <= r["H"] + 1, f"{name}: replay window inside the window {r}")
            check(not b.console(), f"{name}: console clean {b.console()[:3]}")
        finally:
            b.close()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    want = sys.argv[1:] or ["buys", "auto", "openbet", "replay", "social", "sizes"]
    for name in want:
        globals()[name]()
    print("\nFAIL:\n" + "\n".join(FAIL) if FAIL else "\nPASS: " + ", ".join(want))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
