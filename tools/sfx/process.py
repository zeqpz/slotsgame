"""raw/<name>_<t>.pcm (24 kHz stereo s16) -> clean/<name>_<t>.wav (44.1 kHz stereo s16)
+ sheets/<name>.png (raw vs clean spectrograms) + stats.json.

Chain per take:
  DC + high-pass (per kind) -> spectral gate (noise profile from the take's own quiet frames,
  one gain mask from the mid applied to both channels) -> pick the main event, tight onset,
  natural tail -> downward expander for what is left between/after -> tiny exciter for the
  air the 24 kHz source lacks (above 12 kHz, instantaneous so no smearing) -> 44.1 kHz ->
  gentle compressor (slow attack: transients pass) -> loudness to the kind's target ->
  true-ish peak limiter at -1.5 dBFS -> fades (de-click) -> stats.
Usage: python process.py [name ...]"""
import os, sys, glob, json
import numpy as np
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec
from audiolib import write_wav, lufs, analyze, noise_floor

HERE = os.path.dirname(os.path.abspath(__file__))
RAW, OUT, SHEETS = (os.path.join(HERE, d) for d in ("raw", "clean", "sheets"))
SR0, SR = 24000, 44100
CEIL = 10 ** (-1.5 / 20)

# kind: hp Hz, gate (pct, k, gmin), expander thr dB, group thr dB, merge gap s, max len s,
#       tail floor dB, fade-in ms, fade-out ms, target momentary-max LUFS, transient onset?
K = {
    "click":  dict(hp=150, gate=(20, 2.5, .02), exp=-44, grp=-26, gap=.04, mx=.22, tail=-48, fin=.6, fout=12, tgt=-24, tr=True),
    "drop":   dict(hp=120, gate=(20, 2.5, .02), exp=-46, grp=-26, gap=.06, mx=.45, tail=-50, fin=.6, fout=25, tgt=-25, tr=True),
    "hit":    dict(hp=60,  gate=(15, 2.2, .03), exp=-50, grp=-28, gap=.12, mx=1.1, tail=-52, fin=.8, fout=60, tgt=-21, tr=True),
    "impact": dict(hp=35,  gate=(12, 2.0, .04), exp=-54, grp=-28, gap=.20, mx=1.5, tail=-56, fin=.5, fout=120, tgt=-17, tr=True),
    "spray":  dict(hp=300, gate=(10, 1.6, .05), exp=-50, grp=-30, gap=.15, mx=2.2, tail=-50, fin=3, fout=60, tgt=-21, tr=False),
    "tone":   dict(hp=200, gate=(12, 2.0, .04), exp=-54, grp=-34, gap=.25, mx=1.6, tail=-56, fin=2, fout=150, tgt=-22, tr=False),
    "whoosh": dict(hp=80,  gate=(12, 2.0, .04), exp=-52, grp=-34, gap=.25, mx=1.8, tail=-54, fin=5, fout=150, tgt=-23, tr=False),
    "foley":  dict(hp=90,  gate=(18, 2.3, .03), exp=-48, grp=-30, gap=.15, mx=1.4, tail=-50, fin=2, fout=60, tgt=-23, tr=False),
}
MAXLEN = {"spray_short": .75, "spray_long": 2.0, "count_tick": .09, "ui_hover": .08, "slider_tick": .07,
          "ui_click": .14, "fs_tick": .2, "cap_pop": .2, "paint_drip": .3, "count_end": 1.4,
          "mult_slam": 1.3, "land_soft": .4, "land_brick": .6, "reel_stop": .5, "cash_flick": .35,
          "sneaker_scuff": .5, "cash_riffle": 1.0, "cigar_puff": 2.4, "lighter": 1.6, "count_whoosh": 1.4,
          "float_away": 1.8, "cascade": 1.1, "can_shake": .9, "swish_in": .6, "swish_out": .6,
          "sparkle": 1.3, "shine": 1.0, "glow_pulse": 1.4}
# whole-take kinds keep everything from the first rise to the last fall (one gesture)
WHOLE = {"spray", "whoosh", "tone"}
WHOLE_NAMES = {"cash_riffle", "cigar_puff", "lighter", "can_shake", "cascade", "land_dice", "land_chain", "count_end", "buy_confirm"}
N_FFT, HOP = 1024, 256


def stft(x):
    f, t, Z = signal.stft(x, SR0, nperseg=N_FFT, noverlap=N_FFT - HOP, boundary="even", padded=True)
    return Z


def istft(Z, n):
    _, y = signal.istft(Z, SR0, nperseg=N_FFT, noverlap=N_FFT - HOP, boundary=True)
    y = y[:n]
    return np.pad(y, (0, max(0, n - len(y))))


def smooth2(a, fb, ft):
    from scipy.ndimage import uniform_filter
    return uniform_filter(a, size=(2 * fb + 1, 2 * ft + 1), mode="nearest")


def gate(st, pct, k, gmin):
    """Spectral gate on a stereo take with a mask from the mid."""
    mid = st.mean(1)
    Z = stft(mid)
    P = np.abs(Z) ** 2
    Ps = smooth2(P, 2, 1)
    N = np.percentile(Ps, pct, axis=1) / 0.75
    N = 10 ** smooth2(np.log10(N + 1e-16)[:, None], 4, 0)[:, 0]
    G = np.sqrt(np.clip(1 - k * N[:, None] / np.maximum(Ps, 1e-16), gmin * gmin, 1))
    for t in range(1, G.shape[1]):                     # hold: decays stay natural
        G[:, t] = np.maximum(G[:, t], G[:, t - 1] * 0.72)
    G = smooth2(G, 1, 0)
    out = np.zeros_like(st)
    for c in range(st.shape[1]):
        out[:, c] = istft(stft(st[:, c]) * G, len(st))
    noise_db = 10 * np.log10(N.sum() / (N_FFT / 2) + 1e-20)
    return out, noise_db


def env(x, win, sr):
    n = max(1, int(win * sr))
    return np.sqrt(np.convolve(x * x, np.ones(n) / n, mode="same"))


def pick_event(m, kd, whole):
    e = env(m, .008, SR0)
    pk = e.max()
    thr = pk * 10 ** (kd["grp"] / 20)
    on = e > thr
    gs = []
    i = 0
    while i < len(on):
        if not on[i]:
            i += 1; continue
        j = i
        while j < len(on) and on[j]: j += 1
        if gs and (i - gs[-1][1]) / SR0 < kd["gap"]:
            gs[-1][1] = j
        else:
            gs.append([i, j])
        i = j
    if not whole and kd["tr"]:
        return pick_hit(m, kd)
    if whole:
        # every group loud enough to matter, merged into one gesture
        big = [g for g in gs if e[g[0]:g[1]].max() > pk * 0.12]
        g0 = [big[0][0], big[-1][1]]
    else:
        g0 = max(gs, key=lambda g: e[g[0]:g[1]].max())
    seg = np.abs(m[g0[0]:g0[1]])
    if kd["tr"]:
        e2 = env(m, .0015, SR0)
        at = g0[0] + int(np.argmax(seg))
        # the attack: first sample within the event region that rises out of the floor before the peak
        lo = max(0, g0[0] - int(.03 * SR0))
        rise = np.nonzero(e2[lo:at + 1] > e2[at] * 0.06)[0]
        start = lo + (rise[0] if len(rise) else 0) - int(.0012 * SR0)
    else:
        lead = max(0, g0[0] - int(.04 * SR0))
        hits = np.nonzero(np.abs(m[lead:g0[1]]) > seg.max() * 0.03)[0]
        start = lead + (hits[0] if len(hits) else 0) - int(.004 * SR0)
    start = max(0, start)
    stop = min(len(m), g0[1] + int(1.5 * SR0))
    if not whole:
        nxt = [g for g in gs if g[0] > g0[1] and e[g[0]:g[1]].max() > pk * 0.3]
        if nxt:
            stop = min(stop, nxt[0][0] - int(.008 * SR0))
    floor = pk * 10 ** (kd["tail"] / 20)
    tail = np.nonzero(e[g0[1]:stop] > floor)[0]
    stop = g0[1] + (tail[-1] if len(tail) else 0) + int(.02 * SR0)
    return start, min(stop, len(m))


def onsets(m, sr):
    """(sample, peak) for every sharp rise: >10 dB within 12 ms, above -32 dB re the take's max."""
    hop = int(.002 * sr)
    e = env(m, .003, sr)[::hop]
    d = 20 * np.log10(e / e.max() + 1e-9)
    w = 6
    out = []
    for t in range(w, len(d)):
        if d[t] > -32 and d[t] - d[t - w:t].min() > 10:
            if out and t - out[-1] < 20:       # 40 ms: the same hit
                continue
            out.append(t)
    res = []
    for t in out:
        # walk back to where the rise starts
        s = t
        while s > 0 and d[s - 1] < d[s] and d[t] - d[s - 1] < 30:
            s -= 1
        pkv = d[t:t + 30].max()
        before = d[max(0, s - 25):s].max() if s > 0 else -99
        # a new hit stands clear of what was already sounding (a ringing tail's wobble does not)
        if res and pkv < before + 5:
            continue
        res.append((s * hop, pkv))
    return res


def pick_hit(m, kd):
    """The main hit: the first onset within 3 dB of the loudest one; it ends where the next real
    hit begins (a second slam, a bounce under -18 dB is part of this one) or the tail floor."""
    on = onsets(m, SR0)
    e = env(m, .008, SR0)
    if not on:
        a = int(np.argmax(e)); on = [(max(0, a - int(.01 * SR0)), 0.0)]
    top = max(p for _, p in on)
    i0 = next(i for i, (_, p) in enumerate(on) if p >= top - 3)
    start = max(0, on[i0][0] - int(.001 * SR0))
    stop = len(m)
    for s, p in on[i0 + 1:]:
        if p > on[i0][1] - 18:
            stop = s - int(.004 * SR0); break
    pk = e[start:stop].max()
    floor = pk * 10 ** (kd["tail"] / 20)
    tail = np.nonzero(e[start:stop] > floor)[0]
    stop = start + (tail[-1] if len(tail) else 0) + int(.015 * SR0)
    return start, min(stop, len(m))


def expand(st, thr_db, sr, ratio=3.0, rel_db=2.0, frame=.005):
    m = np.abs(st).max(1)
    n = max(1, int(frame * sr)); k = -(-len(m) // n)
    pad = np.pad(m, (0, k * n - len(m)))
    r = np.sqrt((pad.reshape(k, n) ** 2).mean(1)) + 1e-12
    lvl = 20 * np.log10(r / r.max())
    g = np.clip((lvl - thr_db) * (ratio - 1), -70, 0)
    g = np.maximum(g, np.concatenate([g[1:], g[-1:]]))
    g = np.maximum(g, np.concatenate([g[2:], g[-1:], g[-1:]]))   # open 2 frames early: attacks intact
    for t in range(1, k):
        g[t] = max(g[t], g[t - 1] - rel_db)
    gain = np.interp(np.arange(len(m)), np.arange(k) * n + n / 2, 10 ** (g / 20))
    return st * gain[:, None]


def excite(st, sr, amt):
    """Add air above the 24 kHz source's 12 kHz edge: soft-saturate the 5-11 kHz band and keep
    only the new harmonics above 11.5 kHz. Instantaneous, so transients stay where they are."""
    if amt <= 0:
        return st
    sos_b = signal.butter(4, [5000, 11000], "bandpass", fs=sr, output="sos")
    sos_h = signal.butter(6, 11500, "highpass", fs=sr, output="sos")
    b = signal.sosfiltfilt(sos_b, st, axis=0)
    s = b.std() + 1e-9
    h = np.tanh(b / s * 1.5) * s
    h = signal.sosfiltfilt(sos_h, h, axis=0)
    return st + amt * h


def compress(st, sr, thr_rel_db=-10, ratio=2.0, att=.006, rel=.09):
    m = np.abs(st).max(1)
    pk = m.max() + 1e-12
    a, r = np.exp(-1 / (att * sr)), np.exp(-1 / (rel * sr))
    env_ = np.zeros_like(m); v = 0.0
    for i, x in enumerate(m):
        v = a * v + (1 - a) * x if x > v else r * v + (1 - r) * x
        env_[i] = v
    lvl = 20 * np.log10(env_ / pk + 1e-12)
    over = np.maximum(0, lvl - thr_rel_db)
    gdb = -over * (1 - 1 / ratio)
    return st * (10 ** (gdb / 20))[:, None]


def limit(st, sr, ceil=CEIL, look=.0015, rel=.06):
    m = np.abs(st).max(1)
    need = np.minimum(1, ceil / np.maximum(m, 1e-12))
    n = max(1, int(look * sr))
    from scipy.ndimage import minimum_filter1d
    g = minimum_filter1d(need, 2 * n + 1, mode="nearest")
    r = np.exp(-1 / (rel * sr))
    out = np.empty_like(g); v = 1.0
    for i, x in enumerate(g):
        v = x if x < v else r * v + (1 - r) * x
        out[i] = v
    # smooth the attack ramp (the min-filter already looks ahead n samples)
    out = np.convolve(np.pad(out, (n, n), mode="edge"), np.ones(n) / n, mode="same")[n:-n]
    y = st * out[:, None]
    return np.clip(y, -ceil, ceil)   # anything left (a sample or two) is clipped by < 0.1 dB


EXCITE = {"click": .25, "drop": .2, "hit": .2, "impact": .12, "spray": .35, "tone": .3, "whoosh": .15, "foley": .2}


def process(name, kind, st):
    kd = dict(K[kind])
    st = st - st.mean(0)
    nf_raw_rel = noise_floor(st, SR0) - 20 * np.log10(np.abs(st).max() + 1e-12)
    sos = signal.butter(4, kd["hp"], "highpass", fs=SR0, output="sos")
    st = signal.sosfiltfilt(sos, st, axis=0)
    raw_floor = None
    g, noise_db = gate(st, *kd["gate"])
    m = g.mean(1)
    whole = kind in WHOLE or name in WHOLE_NAMES
    a, b = pick_event(m, kd, whole)
    mx = MAXLEN.get(name, kd["mx"])
    b = min(b, a + int(mx * SR0))
    y = g[a:b].copy()
    if len(y) < int(.015 * SR0):
        return None, {"err": "too short"}
    y = expand(y, kd["exp"], SR0)
    y = signal.resample_poly(y, 147, 80, axis=0)       # 24k -> 44.1k
    y = excite(y, SR, EXCITE[kind])
    y = compress(y, SR)
    # loudness to target (momentary max over 400 ms, the measure that suits one-shots)
    _, M = lufs(y, SR)
    y *= 10 ** ((kd["tgt"] - M) / 20)
    y = limit(y, SR)
    # tail: drop what trails under the floor, then fades
    e = env(np.abs(y).max(1), .006, SR)
    live = np.nonzero(e > e.max() * 10 ** (kd["tail"] / 20))[0]
    y = y[:min(len(y), live[-1] + int(.02 * SR))]
    nin = max(1, int(kd["fin"] / 1000 * SR)); nout = min(len(y) // 2, int(kd["fout"] / 1000 * SR))
    y[:nin] *= (np.linspace(0, 1, nin) ** 1.5)[:, None]
    y[-nout:] *= (np.linspace(1, 0, nout) ** 2)[:, None]
    y[0] = 0; y[-1] = 0
    st_ = analyze(y, SR)
    st_["gen_noise_db"] = noise_db
    st_["nf_raw_rel"] = nf_raw_rel
    st_["nf_out"] = noise_floor(y, SR)
    st_["nf_out_rel"] = st_["nf_out"] - st_["peak_db"]
    _, st_["mmax"] = lufs(y, SR)
    return y, st_


def spectro(ax, x, sr, title):
    f, t, S = signal.spectrogram(x, sr, nperseg=512, noverlap=384)
    ax.pcolormesh(t, f / 1000, 10 * np.log10(S + 1e-14), vmin=-120, vmax=-30, cmap="magma", shading="auto")
    ax.set_title(title, fontsize=7); ax.tick_params(labelsize=5)


def main():
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(OUT, exist_ok=True); os.makedirs(SHEETS, exist_ok=True)
    filt = sys.argv[1:]
    stats = json.load(open(os.path.join(HERE, "stats.json"))) if os.path.exists(os.path.join(HERE, "stats.json")) else {}
    for name, prompt, takes, kind in spec.jobs():
        if filt and name not in filt:
            continue
        raws = sorted(glob.glob(os.path.join(RAW, f"{name}_*.pcm")), key=lambda p: int(p.rsplit("_", 1)[1][:-4]))
        if not raws:
            continue
        fig, axes = plt.subplots(len(raws), 2, figsize=(9, 1.25 * len(raws)), squeeze=False)
        for i, p in enumerate(raws):
            tag = os.path.basename(p)[:-4]
            st = np.frombuffer(open(p, "rb").read(), "<i2").reshape(-1, 2).astype(np.float64) / 32768
            spectro(axes[i][0], st.mean(1), SR0, f"{tag} RAW {len(st)/SR0:.2f}s")
            try:
                y, s = process(name, kind, st)
            except Exception as e:
                y, s = None, {"err": repr(e)}
            stats[tag] = s
            if y is None:
                axes[i][1].set_title(f"{tag} {s}", fontsize=7); continue
            write_wav(os.path.join(OUT, tag + ".wav"), y, SR)
            spectro(axes[i][1], y.mean(1), SR,
                    f"{tag} {s['dur']:.2f}s pk {s['peak_db']:.1f} M {s['mmax']:.1f} nf raw {s['nf_raw_rel']:.0f}dBr -> out {s['nf_out']:.0f}dBFS")
            print(f"{tag:18s} {s['dur']:5.2f}s pk {s['peak_db']:5.1f} M {s['mmax']:6.1f} I {s['lufs']:6.1f} nf raw {s['nf_raw_rel']:6.1f}dBr out {s['nf_out']:6.1f}dBFS ({s['nf_out_rel']:6.1f}dBr) cen {s['centroid']:5.0f}")
        fig.tight_layout(); fig.savefig(os.path.join(SHEETS, name + ".png"), dpi=80); plt.close(fig)
    json.dump(stats, open(os.path.join(HERE, "stats.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
