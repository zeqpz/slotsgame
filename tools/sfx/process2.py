"""Second pass: every take is cleaned whole, then cut into its individual events (each tick,
drop, clack, hiss...), each event finished and scored. select.py then keeps the best, most
alike few per sound.

raw/<name>_<t>.pcm (24 kHz stereo s16) -> cand/<name>/<t>_<e>.wav (44.1 kHz stereo s16) + cand.json
Usage: python process2.py [name ...]"""
import os, sys, glob, json, shutil
import numpy as np
from scipy import signal
from scipy.ndimage import uniform_filter, minimum_filter1d
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec
from audiolib import write_wav, lufs, analyze, noise_floor

HERE = os.path.dirname(os.path.abspath(__file__))
RAW, CAND = os.path.join(HERE, "raw"), os.path.join(HERE, "cand")
SR0, SR = 24000, 44100
CEIL = 10 ** (-1.5 / 20)

# mode: "hit" = each onset is an event; "gesture" = loudest group of activity merged over `gap`;
#       "sustain" = the longest steady stretch (a hiss, a whoosh)
K = {
    "click":  dict(lim=1.0, mode="hit", hp=150, gate=(10, 2.5, .02), exp=-44, tail=-46, fin=.4, fout=8, tgt=-24, ex=.25),
    "drop":   dict(lim=1.0, mode="hit", hp=110, gate=(10, 2.5, .02), exp=-46, tail=-48, fin=.5, fout=20, tgt=-25, ex=.2),
    "hit":    dict(mode="hit", hp=60,  gate=(8, 2.2, .03), exp=-50, tail=-50, fin=.6, fout=45, tgt=-21, ex=.2),
    "impact": dict(mode="hit", hp=48,  gate=(8, 2.0, .04), exp=-54, tail=-54, fin=.4, fout=110, tgt=-17, ex=.12),
    "spray":  dict(mode="sustain", hp=300, gate=(6, 1.6, .05), exp=-50, tail=-50, fin=4, fout=70, tgt=-21, ex=.35),
    "tone":   dict(mode="gesture", gap=.25, hp=200, gate=(6, 2.0, .04), exp=-54, tail=-56, fin=2, fout=150, tgt=-22, ex=.3),
    "whoosh": dict(mode="gesture", gap=.25, hp=80,  gate=(6, 2.0, .04), exp=-52, tail=-54, fin=5, fout=150, tgt=-23, ex=.15),
    "foley":  dict(mode="gesture", gap=.15, hp=90,  gate=(6, 2.3, .03), exp=-48, tail=-50, fin=2, fout=60, tgt=-23, ex=.2),
}
# per sound: (min s, max s, keep, mode override)
T = {
    "spray_short": (.35, .55, 3, None), "spray_long": (.9, 1.5, 2, None),
    "paint_drip": (.06, .3, 4, None), "glow_pulse": (.4, 1.3, 2, None), "shine": (.25, .9, 2, None),
    "sparkle": (.3, 1.2, 3, None), "count_tick": (.015, .06, 3, None), "count_end": (.35, 1.8, 2, "gesture"),
    "mult_slam": (.3, 1.2, 3, None), "count_whoosh": (.6, 1.4, 2, None), "float_away": (.6, 1.8, 2, None),
    "paint_burst": (.12, .7, 3, None),
    "land_soft": (.05, .35, 3, None), "land_bag": (.08, .5, 3, None), "land_can": (.06, .5, 3, None),
    "land_chain": (.12, .7, 3, "gesture"), "land_coin": (.1, .7, 2, "gesture"), "land_dice": (.15, .8, 3, "gesture"),
    "land_baggie": (.08, .5, 3, None), "land_fabric": (.06, .4, 3, None), "land_hoodie": (.08, .5, 2, None),
    "land_marker": (.05, .4, 3, None), "land_brick": (.06, .5, 3, None), "land_board": (.08, .6, 2, None),
    "land_box": (.06, .4, 2, None), "land_shoe": (.06, .4, 2, None), "land_boombox": (.06, .5, 2, None),
    "land_metal": (.06, .5, 3, None), "land_card": (.03, .3, 2, None), "land_toy": (.04, .35, 2, None),
    "cascade": (.3, 1.0, 2, "gesture"), "reel_stop": (.06, .45, 3, None), "can_shake": (.15, .8, 2, "gesture"),
    "ui_click": (.015, .1, 3, None), "ui_hover": (.01, .035, 3, None), "slider_tick": (.01, .06, 2, None),
    "swish_in": (.15, .55, 2, None), "swish_out": (.15, .55, 2, None), "cap_pop": (.03, .2, 2, None),
    "buy_confirm": (.4, 1.4, 1, "gesture"), "fs_tick": (.03, .2, 2, None),
    "sneaker_scuff": (.08, .32, 2, "gesture"), "cigar_puff": (.6, 1.1, 2, None), "lighter": (.4, 1.6, 1, None),
    "cash_riffle": (.3, 1.0, 2, None), "cash_flick": (.04, .35, 2, None),
}
N_FFT, HOP = 1024, 256
EVMIN = {"paint_drip": -32, "count_tick": -22, "ui_click": -20, "ui_hover": -24, "slider_tick": -22, "fs_tick": -20}
SINGLE = {"land_soft", "land_brick", "land_card", "land_toy", "land_fabric", "land_shoe", "land_box", "cash_flick", "reel_stop"}
# impacts: the sub boom is cut short (a slam should punch, not drone): under TIGHT_HZ the
# sound decays with this time constant after the first 70 ms
TIGHT = {"impact": (160, .11), "hit": (140, .16)}


def stft(x):
    return signal.stft(x, SR0, nperseg=N_FFT, noverlap=N_FFT - HOP, boundary="even", padded=True)[2]


def istft(Z, n):
    y = signal.istft(Z, SR0, nperseg=N_FFT, noverlap=N_FFT - HOP, boundary=True)[1][:n]
    return np.pad(y, (0, max(0, n - len(y))))


def gate(st, pct, k, gmin):
    mid = st.mean(1)
    P = np.abs(stft(mid)) ** 2
    Ps = uniform_filter(P, size=(5, 3), mode="nearest")
    N = np.percentile(Ps, pct, axis=1) / 0.75
    N = 10 ** uniform_filter(np.log10(N + 1e-16), size=9, mode="nearest")
    G = np.sqrt(np.clip(1 - k * N[:, None] / np.maximum(Ps, 1e-16), gmin * gmin, 1))
    for t in range(1, G.shape[1]):
        G[:, t] = np.maximum(G[:, t], G[:, t - 1] * 0.72)
    G = uniform_filter(G, size=(3, 1), mode="nearest")
    out = np.zeros_like(st)
    for c in range(st.shape[1]):
        out[:, c] = istft(stft(st[:, c]) * G, len(st))
    return out, N, G


def env(x, win, sr):
    n = max(1, int(win * sr))
    return np.sqrt(np.convolve(x * x, np.ones(n) / n, mode="same"))


def onsets(m, sr, floor_db=-34):
    hop = int(.002 * sr)
    e = env(m, .003, sr)[::hop]
    d = 20 * np.log10(e / (e.max() + 1e-12) + 1e-9)
    w = 6
    raw = []
    for t in range(w, len(d)):
        if d[t] > floor_db and d[t] - d[t - w:t].min() > 10:
            if raw and t - raw[-1] < 12:      # 24 ms: the same hit
                continue
            raw.append(t)
    res = []
    for t in raw:
        s = t
        while s > 0 and d[s - 1] < d[s] and d[t] - d[s - 1] < 30:
            s -= 1
        pkv = d[t:t + 20].max()
        before = d[max(0, s - 15):s].max() if s > 0 else -99
        if res and pkv < before + 5:          # a wobble in a ringing tail, not a new hit
            continue
        res.append((s * hop, pkv))
    return res


def retrigger(m, a, b, rise_db=9):
    """First point after the peak where the sound comes back up (a second click inside one
    event): the event should end just before it. The envelope is 5 ms wide, so a thud's own
    low-frequency ripple never reads as a new hit, and a rise must hold for 3 ms."""
    e = env(m[a:b], .005, SR0)
    if len(e) < 10:
        return b
    d = 20 * np.log10(e / (e.max() + 1e-12) + 1e-9)
    top = int(np.argmax(d))
    lo = d[top]
    hold = int(.003 * SR0)
    for i in range(top + int(.006 * SR0), len(d) - hold):
        lo = min(lo, d[i])
        if d[i] > -30 and d[i] - lo > rise_db and (d[i:i + hold] - lo > rise_db - 2).all():
            j = i
            while j > top and d[j - 1] < d[j]:
                j -= 1
            return a + j - int(.002 * SR0)
    return b


def ev_hits(m, mn, mx, tail_db, single=False):
    on = onsets(m, SR0)
    out = []
    e = env(m, .004, SR0)
    for i, (s, p) in enumerate(on):
        start = max(0, s - int(.0008 * SR0))
        nxt = on[i + 1][0] - int(.002 * SR0) if i + 1 < len(on) else len(m)
        stop = min(nxt, start + int(mx * SR0 * 1.6))
        if single:
            r = retrigger(m, start, stop)
            if r < stop:
                stop, nxt = r, r
        seg = e[start:stop]
        if len(seg) < 8:
            continue
        pk = seg.max()
        live = np.nonzero(seg > pk * 10 ** (tail_db / 20))[0]
        stop = start + live[-1] + int(.006 * SR0)
        cut = stop >= nxt - 2      # it runs into the next hit
        out.append(dict(a=start, b=min(stop, len(m)), pk=p, cut=bool(cut)))
    return out


def ev_gesture(m, gap, tail_db, mx):
    e = env(m, .008, SR0)
    pk = e.max()
    on = e > pk * 10 ** (-30 / 20)
    gs = []
    i = 0
    while i < len(on):
        if not on[i]:
            i += 1; continue
        j = i
        while j < len(on) and on[j]: j += 1
        if gs and (i - gs[-1][1]) / SR0 < gap:
            gs[-1][1] = j
        else:
            gs.append([i, j])
        i = j
    out = []
    for g in gs:
        gp = e[g[0]:g[1]].max()
        if gp < pk * 10 ** (-12 / 20):
            continue
        lead = max(0, g[0] - int(.04 * SR0))
        hits = np.nonzero(np.abs(m[lead:g[1]]) > np.abs(m[g[0]:g[1]]).max() * 0.03)[0]
        a = max(0, lead + (hits[0] if len(hits) else 0) - int(.003 * SR0))
        stop = min(len(m), g[1] + int(1.2 * SR0))
        nx = [h for h in gs if h[0] > g[1]]
        if nx:
            stop = min(stop, nx[0][0] - int(.01 * SR0))
        live = np.nonzero(e[g[1]:stop] > gp * 10 ** (tail_db / 20))[0]
        b = g[1] + (live[-1] if len(live) else 0) + int(.015 * SR0)
        out.append(dict(a=a, b=min(b, len(m)), pk=20 * np.log10(gp / pk), cut=False))
    return out


def ev_sustain(m, mx):
    """The longest steady stretch (spray hiss): above -14 dB re the take's loudest 20 ms."""
    e = env(m, .02, SR0)
    on = e > e.max() * 10 ** (-14 / 20)
    best, i = None, 0
    while i < len(on):
        if not on[i]:
            i += 1; continue
        j = i
        while j < len(on) and on[j]: j += 1
        if best is None or j - i > best[1] - best[0]:
            best = [i, j]
        i = j
    a, b = best
    # back up to the true start of the hiss (where it rises out of the floor)
    e2 = env(m, .003, SR0)
    lo = max(0, a - int(.08 * SR0))
    r = np.nonzero(e2[lo:a + 1] > e2[a] * 0.1)[0]
    a = lo + (r[0] if len(r) else 0)
    ev = [dict(a=a, b=min(len(m), b + int(.03 * SR0)), pk=0.0, cut=False)]
    return ev


def expand(st, thr_db, sr, ratio=3.0, rel_db=2.0, frame=.004):
    m = np.abs(st).max(1)
    n = max(1, int(frame * sr)); k = -(-len(m) // n)
    pad = np.pad(m, (0, k * n - len(m)))
    r = np.sqrt((pad.reshape(k, n) ** 2).mean(1)) + 1e-12
    lvl = 20 * np.log10(r / r.max())
    g = np.clip((lvl - thr_db) * (ratio - 1), -70, 0)
    g = np.maximum(g, np.concatenate([g[1:], g[-1:]]))
    g = np.maximum(g, np.concatenate([g[2:], g[-1:], g[-1:]]))
    for t in range(1, k):
        g[t] = max(g[t], g[t - 1] - rel_db)
    gain = np.interp(np.arange(len(m)), np.arange(k) * n + n / 2, 10 ** (g / 20))
    return st * gain[:, None]


def excite(st, sr, amt):
    """Air above the source's 12 kHz edge: soft-saturate 5-11 kHz at 4x oversampling (no
    aliasing), keep only the new 11.5-17 kHz harmonics. Instantaneous: transients stay put."""
    if amt <= 0 or len(st) < 64:
        return st
    b = signal.sosfiltfilt(signal.butter(4, [5000, 11000], "bandpass", fs=sr, output="sos"), st, axis=0)
    s = b.std() + 1e-9
    up = signal.resample_poly(b, 4, 1, axis=0)
    h = np.tanh(up / s * 1.5) * s
    h = signal.sosfiltfilt(signal.butter(8, 17000, "lowpass", fs=sr * 4, output="sos"), h, axis=0)
    h = signal.resample_poly(h, 1, 4, axis=0)[:len(st)]
    h = signal.sosfiltfilt(signal.butter(8, 11500, "highpass", fs=sr, output="sos"), h, axis=0)
    return st + amt * h


def follow(x, att, rel, sr, blk=32):
    """Peak follower with attack/release, run on 32-sample block maxima (fast), held per block."""
    nb = -(-len(x) // blk)
    b = np.pad(x, (0, nb * blk - len(x))).reshape(nb, blk).max(1)
    a, r = np.exp(-blk / (att * sr)), np.exp(-blk / (rel * sr))
    out = np.empty(nb); v = 0.0
    for i in range(nb):
        v = a * v + (1 - a) * b[i] if b[i] > v else r * v + (1 - r) * b[i]
        out[i] = v
    return np.repeat(out, blk)[:len(x)]


def compress(st, sr, thr_rel_db=-10, ratio=2.0, att=.006, rel=.09):
    m = np.abs(st).max(1)
    pk = m.max() + 1e-12
    e = follow(m, att, rel, sr)
    gdb = -np.maximum(0, 20 * np.log10(e / pk + 1e-12) - thr_rel_db) * (1 - 1 / ratio)
    g = 10 ** (gdb / 20)
    g = np.convolve(np.pad(g, (64, 64), mode="edge"), np.ones(64) / 64, mode="same")[64:-64]
    return st * g[:, None]


def limit(st, sr, ceil=CEIL, look=.0015, rel=.06, blk=32):
    m = np.abs(st).max(1)
    need = np.minimum(1, ceil / np.maximum(m, 1e-12))
    n = max(1, int(look * sr))
    g = minimum_filter1d(need, 2 * n + 1, mode="nearest")
    nb = -(-len(g) // blk)
    bmin = np.pad(g, (0, nb * blk - len(g)), constant_values=1).reshape(nb, blk).min(1)
    r = np.exp(-blk / (rel * sr))
    out = np.empty(nb); v = 1.0
    for i in range(nb):
        v = bmin[i] if bmin[i] < v else r * v + (1 - r) * bmin[i]
        out[i] = v
    out = np.minimum(np.repeat(out, blk)[:len(g)], g)
    out = np.convolve(np.pad(out, (n, n), mode="edge"), np.ones(n) / n, mode="same")[n:-n]
    return np.clip(st * out[:, None], -ceil, ceil)


def tighten(y, hz, tau, sr, hold=.07):
    lo = signal.sosfiltfilt(signal.butter(2, hz, "lowpass", fs=sr, output="sos"), y, axis=0)
    t = np.arange(len(y)) / sr
    g = np.where(t < hold, 1.0, np.exp(-(t - hold) / tau))
    return y - lo + lo * g[:, None]


FOUT = {"count_end": 380, "cigar_puff": 250, "sneaker_scuff": 90, "spray_long": 120}


def tame(y, sr, hold=.014, tau=.014):
    """clicks: after the first 14 ms everything decays fast - crisp, and no room / hiss tail"""
    t = np.arange(len(y)) / sr
    return y * np.where(t < hold, 1.0, np.exp(-(t - hold) / tau))[:, None]


def finish(seg, kd, mx, kind=None, name=None):
    if name in FOUT:
        kd = dict(kd, fout=FOUT[name])
    y = seg[:int(mx * SR0)].copy()
    if kind == "click":
        y = tame(y, SR0)
    if kind in TIGHT:
        y = tighten(y, *TIGHT[kind], SR0)
    y = expand(y, kd["exp"], SR0)
    y = signal.resample_poly(y, 147, 80, axis=0)
    y = excite(y, SR, kd["ex"])
    y = compress(y, SR)
    _, M = lufs(y, SR)
    pk_db = 20 * np.log10(np.abs(y).max() + 1e-12)
    # to the loudness target, but never more than LIMIT_DB into the limiter: a short click
    # measured over 400 ms reads quiet, and chasing that would flatten its transient
    gain = min(kd["tgt"] - M, -1.5 - pk_db + kd.get("lim", 2.0))
    y *= 10 ** (gain / 20)
    y = limit(y, SR)
    e = env(np.abs(y).max(1), .004, SR)
    live = np.nonzero(e > e.max() * 10 ** (kd["tail"] / 20))[0]
    y = y[:min(len(y), live[-1] + int(.012 * SR))]
    nin = max(2, int(kd["fin"] / 1000 * SR)); nout = max(2, min(len(y) // 2, int(kd["fout"] / 1000 * SR)))
    y[:nin] *= (np.linspace(0, 1, nin) ** 1.5)[:, None]
    y[-nout:] *= (np.linspace(1, 0, nout) ** 2)[:, None]
    return y


BANDS = [(60, 250), (250, 600), (600, 1200), (1200, 2400), (2400, 4800), (4800, 8000), (8000, 12000), (12000, 18000)]


def bands(y):
    f, P = signal.welch(y.mean(1), SR, nperseg=min(1024, len(y)))
    v = np.array([P[(f >= a) & (f < b)].sum() for a, b in BANDS]) + 1e-14
    return list(10 * np.log10(v / v.sum()))


def main():
    filt = sys.argv[1:]
    db = json.load(open(os.path.join(HERE, "cand.json"))) if os.path.exists(os.path.join(HERE, "cand.json")) else {}
    for name, prompt, takes, kind in spec.jobs():
        if filt and name not in filt:
            continue
        kd = dict(K[kind])
        mn, mx, keep, mode = T[name]
        mode = mode or kd["mode"]
        d = os.path.join(CAND, name)
        shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        db[name] = []
        raws = sorted(glob.glob(os.path.join(RAW, f"{name}_*.pcm")), key=lambda p: int(p.rsplit("_", 1)[1][:-4]))
        for p in raws:
            t = int(p.rsplit("_", 1)[1][:-4])
            st = np.frombuffer(open(p, "rb").read(), "<i2").reshape(-1, 2).astype(np.float64) / 32768
            if len(st) < 2048 or np.abs(st).max() < 1e-3:
                continue
            st = st - st.mean(0)
            nf_raw = noise_floor(st, SR0) - 20 * np.log10(np.abs(st).max())
            st = signal.sosfiltfilt(signal.butter(4, kd["hp"], "highpass", fs=SR0, output="sos"), st, axis=0)
            g, Nn, Gg = gate(st, *kd["gate"])
            Zw = stft(np.random.default_rng(0).standard_normal(SR0))
            cal = (np.abs(Zw) ** 2).mean(1).sum()       # white noise of variance 1
            m = g.mean(1)
            if mode == "hit":
                evs = ev_hits(m, mn, mx, kd["tail"], single=kind in ("click", "drop") or name in SINGLE)
            elif mode == "gesture":
                evs = ev_gesture(m, kd.get("gap", .15), kd["tail"], mx)
            else:
                evs = ev_sustain(m, mx)
            evs = [e for e in evs if e["pk"] > EVMIN.get(name, -14)][:24]
            for i, ev in enumerate(evs):
                seg = g[ev["a"]:ev["b"]]
                raw_len = len(seg) / SR0
                if raw_len < mn * .8:
                    continue
                y = finish(seg, kd, mx, kind, name)
                if len(y) < int(mn * .8 * SR):
                    continue
                a = analyze(y, SR)
                # tail state before our fade: is the event still sounding where we cut it?
                nf = noise_floor(y, SR)
                f0, f1 = ev["a"] // HOP, max(ev["a"] // HOP + 1, min(Gg.shape[1], ev["b"] // HOP))
                pk_in = np.abs(seg.mean(1)).max() + 1e-12
                hiss_raw = 10 * np.log10(Nn.sum() / cal + 1e-20) - 20 * np.log10(pk_in)
                hiss = 10 * np.log10((Nn[:, None] * Gg[:, f0:f1] ** 2).sum(0).mean() / cal + 1e-20) - 20 * np.log10(pk_in)
                fn = f"{t}_{i}.wav"
                write_wav(os.path.join(d, fn), y, SR)
                db[name].append(dict(file=fn, take=t, ev=i, dur=a["dur"], peak=a["peak_db"], mmax=lufs(y, SR)[1],
                                     I=a["lufs"], cen=a["centroid"], nf_raw=nf_raw, nf_out=nf, ev_pk=ev["pk"],
                                     cut=ev["cut"] or raw_len > mx, raw_len=raw_len, hiss_raw=hiss_raw, hiss=hiss, bands=bands(y)))
        print(f"{name:14s} {len(raws)} takes -> {len(db[name])} candidates", flush=True)
    json.dump(db, open(os.path.join(HERE, "cand.json"), "w"), indent=0)


if __name__ == "__main__":
    main()
