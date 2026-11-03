"""Strict noise pass on every GENERATED take (owner: "still some background noise ... chop it out").

Per take, from the raw Seed Audio PCM:
  1. DC + high-pass (rumble / hum) per kind.
  2. noisereduce, stationary, prop_decrease 1.0, noise profile = the take's own quietest 50 ms
     windows (outside the event); then a non-stationary pass (transient / foley kinds only -
     on a hiss-like sound such as the spray it would eat the sound itself).
  3. The event cut out as before, mastered as before (tighten / tame, expander, 44.1 k, a
     lighter exciter, compressor, loudness target, -1.5 dBFS limiter).
  4. Hard gate: 3 ms RMS envelope against max(residual noise + 12 dB, peak - 58 dB); 2 ms
     look-ahead, 1 ms attack, 12 ms hold, 20 ms raised-cosine release; closed = exact 0.
     Pre-roll cut to the first opening, the file ends where the last release ends.
  5. Guard: in the frames where the raw sound stands 20 dB over its noise, the cleaned take
     must keep its level (>= -1.5 dB), brightness (centroid within 15 %), flatness (within
     35 %) and transient (first 15 ms peak >= -2 dB); a take that fails is retried gentler,
     then replaced by the set's next-best candidate.
Writes build3/ (same file names as build/) + report3.json. Usage: python clean3.py [key ...]"""
import os, sys, json, warnings
import numpy as np
from scipy import signal
import noisereduce as nr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import process2 as P
from assemble import FINAL
from audiolib import read_wav, write_wav, lufs

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
BUILD3 = os.path.join(HERE, "build3")
SR0, SR = 24000, 44100
cand = json.load(open(os.path.join(HERE, "cand.json")))
picks = json.load(open(os.path.join(HERE, "picks.json")))
import spec
KIND = {n: k for n, (_, _, k) in spec.S.items()}
HP = {"click": 150, "drop": 110, "hit": 70, "impact": 50, "spray": 300, "tone": 200, "whoosh": 90, "foley": 100}
BED_MAX = -72.0     # the bed left under the sound, output dBFS (outside the sound: exact zero)
NONSTAT = {"click", "drop", "hit", "impact", "foley"}
LIM1 = ("count_tick", "ui_click", "ui_hover", "slider_tick", "fs_tick", "cap_pop")


def rms_db(x):
    return 10 * np.log10(np.mean(np.square(x)) + 1e-30)


def win_rms(x, sr, w):
    """RMS dBFS of every w-second window (hop w/10), both channels together."""
    m = np.square(x).mean(1) if x.ndim > 1 else np.square(x)
    n = max(1, int(w * sr)); h = max(1, n // 10)
    c = np.concatenate([[0], np.cumsum(m)])
    idx = np.arange(0, max(1, len(m) - n + 1), h)
    return 10 * np.log10((c[np.minimum(idx + n, len(m))] - c[idx]) / n + 1e-30), idx, n


def noise_clip(st, a, b):
    """The take's background bed: its quietest 50 ms windows away from the event, skipping the
    generator's digital-silence padding (under -92 dBFS), which is not the bed we hear."""
    d, idx, n = win_rms(st, SR0, .05)
    pad = int(.06 * SR0)
    ok = [(v, i) for v, i in zip(d, idx) if (i + n < a - pad or i > b + pad) and v > -92]
    if len(ok) < 3:
        ok = [(v, i) for v, i in zip(d, idx) if v > -92]
    if not ok:
        ok = [(v, i) for v, i in zip(d, idx)]
    vals = np.array([v for v, _ in ok])
    # the bed's level: a low percentile of what is left (the fade into the padding and the
    # quietest scraps are not it), and the windows that sit around that level
    bed = np.percentile(vals, 20) if len(vals) >= 5 else vals.min()
    ok = sorted(ok, key=lambda t: abs(t[0] - bed))
    lo = bed
    chosen, used = [], []
    for v, i in ok:
        if abs(v - bed) > 4 or len(chosen) >= 12:
            break
        if any(abs(i - j) < n for j in used):
            continue
        used.append(i); chosen.append(st[i:i + n])
    if not chosen:
        v, i = ok[0]; chosen = [st[i:i + n]]
    return np.concatenate(chosen), lo, used, n


def denoise(st, noise, kind, prop=1.0, nonstat=True):
    out = np.zeros_like(st)
    for c in range(st.shape[1]):
        y = nr.reduce_noise(y=st[:, c], sr=SR0, y_noise=noise[:, c], stationary=True, prop_decrease=prop,
                            n_std_thresh_stationary=1.5, n_fft=512, time_mask_smooth_ms=8, freq_mask_smooth_hz=200)
        if nonstat and kind in NONSTAT:
            y = nr.reduce_noise(y=y, sr=SR0, stationary=False, prop_decrease=prop * .8, time_constant_s=1.0,
                                n_fft=512, time_mask_smooth_ms=8, freq_mask_smooth_hz=200, thresh_n_mult_nonstationary=2)
        out[:, c] = y[:len(st)]
    return out


def feats(x, sr, mask_frames=None):
    m = x.mean(1)
    f, t, S = signal.stft(m, sr, nperseg=512, noverlap=384)
    P_ = np.abs(S) ** 2
    band = (f > 200) & (f < 11000)
    Pb = P_[band]
    e = Pb.sum(0)
    loud = mask_frames if mask_frames is not None else e > e.max() * 1e-2
    loud = np.pad(loud[:Pb.shape[1]], (0, max(0, Pb.shape[1] - len(loud))))
    if loud.sum() < 1:
        loud = e >= e.max()
    cen = (f[band][:, None] * Pb).sum(0) / (e + 1e-20)
    flat = np.exp(np.mean(np.log(Pb + 1e-20), 0)) / (np.mean(Pb, 0) + 1e-20)
    return dict(lvl=10 * np.log10(e[loud].mean() + 1e-30), cen=float(np.median(cen[loud])), flat=float(np.median(flat[loud])), loud=loud)


TONAL = {"count_end", "buy_confirm", "land_chain", "land_coin", "land_metal", "land_can"}   # ringing: cleaning a tone makes it purer


def guard(raw_seg, den_seg, noise_lvl, flat_tol=.35):
    """Is the sound itself intact where it stands well over the noise?"""
    m = raw_seg.mean(1)
    nfr = len(m) // 128 + 1
    mp = np.pad(np.square(raw_seg).mean(1), (256, 256 + 512))
    c = np.concatenate([[0], np.cumsum(mp)])
    lvl = 10 * np.log10((c[np.arange(nfr) * 128 + 512] - c[np.arange(nfr) * 128]) / 512 + 1e-30)
    loud = lvl > max(noise_lvl + 20, lvl.max() - 30)
    if loud.sum() < 2:
        loud = lvl > lvl.max() - 10
    a = feats(raw_seg, SR0, loud); b = feats(den_seg, SR0, loud)
    n15 = int(.015 * SR0)
    tr = 20 * np.log10((np.abs(den_seg[:n15]).max() + 1e-9) / (np.abs(raw_seg[:n15]).max() + 1e-9))
    r = dict(dlvl=b["lvl"] - a["lvl"], dcen=b["cen"] / a["cen"] - 1, dflat=b["flat"] / (a["flat"] + 1e-12) - 1, dtr=tr)
    r["ok"] = r["dlvl"] > -1.5 and abs(r["dcen"]) < .15 and abs(r["dflat"]) < flat_tol and r["dtr"] > -2
    return r


def dilate(m, back, fwd):
    """True wherever m is true within `back` samples later or `fwd` samples earlier."""
    c = np.concatenate([[0], np.cumsum(m.astype(np.int64))])
    i = np.arange(len(m))
    lo, hi = np.maximum(0, i - fwd), np.minimum(len(m), i + back + 1)
    return (c[hi] - c[lo]) > 0


def gate(y, thr_db, sr):
    env = np.sqrt(np.convolve(np.square(y).mean(1), np.ones(int(.003 * sr)) / int(.003 * sr), mode="same"))
    d = 20 * np.log10(env + 1e-12)
    op = d > thr_db
    if not op.any():
        return y[:0], 0, 0
    look, hold, att, rel = int(.002 * sr), int(.012 * sr), int(.001 * sr), int(.020 * sr)
    # hold: stay open 12 ms past every crossing; look-ahead: open 2 ms before it
    k = dilate(op, look, hold)
    g = k.astype(float)
    edges = np.diff(np.concatenate([[0], k.astype(int), [0]]))
    ons, offs = np.nonzero(edges == 1)[0], np.nonzero(edges == -1)[0]
    for s in ons:            # 1 ms attack ramp, ending where the gate opens
        a0 = max(0, s - att)
        g[a0:s] = np.maximum(g[a0:s], np.linspace(0, 1, s - a0 + 1)[:-1])
    for s in offs:           # 20 ms raised-cosine release after it closes
        e0 = min(len(g), s + rel)
        g[s:e0] = np.maximum(g[s:e0], .5 + .5 * np.cos(np.linspace(0, np.pi, e0 - s)))
    y = y * g[:, None]
    nz = np.nonzero(g > 0)[0]
    a, b = nz[0], nz[-1] + 1
    y = y[a:b].copy()
    y[0] = 0; y[-1] = 0
    return y, a, len(g) - b


def master(seg, kind, name, tgt, kd):
    y = seg.copy()
    if kind in P.TIGHT:
        y = P.tighten(y, *P.TIGHT[kind], SR0)
    if kind == "click":
        y = P.tame(y, SR0)
    y = P.expand(y, kd["exp"], SR0)
    y = signal.resample_poly(y, 147, 80, axis=0)
    y = P.excite(y, SR, kd["ex"] * .6)
    y = P.compress(y, SR)
    _, M = lufs(y, SR)
    pk = 20 * np.log10(np.abs(y).max() + 1e-12)
    lim = 1.0 if name in LIM1 else 2.0
    gain = min(tgt - M, -1.5 - pk + lim)
    y *= 10 ** (gain / 20)
    y = P.limit(y, SR)
    return y, gain


def build_one(name, c, tgt, prop=1.0, nonstat=True):
    kind = KIND[name]
    kd = dict(P.K[kind])
    mn, mx, keep, _ = P.T[name]
    st = np.frombuffer(open(os.path.join(P.RAW, f"{name}_{c['take']}.pcm"), "rb").read(), "<i2").reshape(-1, 2).astype(np.float64) / 32768
    st = st - st.mean(0)
    st = signal.sosfiltfilt(signal.butter(4, HP[kind], "highpass", fs=SR0, output="sos"), st, axis=0)
    a, b = c["a"], c["b"]
    noise, n_lvl, wins, wn = noise_clip(st, a, b)
    pk_raw = 20 * np.log10(np.abs(st[a:b]).max() + 1e-12)
    if n_lvl > pk_raw - 35:
        # no clean bed in this take (it is all sound): reduce nothing, the gate does the work
        den = st.copy(); n_lvl = min(n_lvl, -90.0)
    else:
        den = denoise(st, noise, kind, prop, nonstat)
    # residual noise after the denoise, in the same quiet windows
    n_after = rms_db(np.concatenate([den[i:i + wn] for i in wins])) if wins else -120.0
    seg_raw, seg = st[a:b][:int(mx * SR0)], den[a:b][:int(mx * SR0)]
    g = guard(seg_raw, seg, n_lvl, .65 if name in TONAL else .35)
    y, gain = master(seg, kind, name, tgt, kd)
    pk = 20 * np.log10(np.abs(y).max() + 1e-12)
    thr = max(n_after + gain + 12, pk - 60)
    y, pre, post = gate(y, thr, SR)
    # the end: a sound still going where its cap cuts it must fade, never stop dead - the kind's
    # (or the sound's own) fade, at least 10 ms, always down to an exact zero
    if len(y) > 8:
        nout = min(len(y) // 2, max(int(.010 * SR), int(P.FOUT.get(name, kd["fout"]) / 1000 * SR)))
        y[-nout:] *= (.5 + .5 * np.cos(np.linspace(0, np.pi, nout)))[:, None]
        nin = max(2, int(.0003 * SR))
        y[:nin] *= np.linspace(0, 1, nin)[:, None]
        y[0] = 0; y[-1] = 0
    return y, dict(guard=g, n_raw=n_lvl, n_after=n_after, thr=thr, gain=gain, pre_ms=pre / SR * 1000)


def measure(x, sr):
    """noise floor = RMS of the quietest 50 ms window (shorter files: a third of their length);
    tail = from the last moment the 10 ms envelope is within 40 dB of its peak to the end."""
    w = min(.05, len(x) / sr / 3)
    d, _, _ = win_rms(x, sr, w)
    e, idx, n = win_rms(x, sr, .01)
    top = e.max()
    last = idx[np.nonzero(e > top - 40)[0][-1]] + n
    tail = x[last:]
    hb = signal.sosfiltfilt(signal.butter(4, [8000, 16000], "bandpass", fs=sr, output="sos"), x, axis=0) if len(x) > 64 else x
    dh, _, _ = win_rms(hb, sr, w)
    return dict(floor=max(-140, d.min()), tail_ms=len(tail) / sr * 1000, tail_rms=max(-140, rms_db(tail)) if len(tail) > 10 else -140,
                hiss8_16=max(-140, dh.min()), dur=len(x) / sr, first=float(np.abs(x[0]).max()), last=float(np.abs(x[-1]).max()))


def main():
    os.makedirs(BUILD3, exist_ok=True)
    final = json.load(open(os.path.join(HERE, "final.json")))
    filt = sys.argv[1:]
    rep = json.load(open(os.path.join(HERE, "report3.json"))) if os.path.exists(os.path.join(HERE, "report3.json")) else {}
    for key, (src, stem, tgt, vol, what) in FINAL.items():
        if not src.startswith("gen:") or (filt and key not in filt):
            continue
        name = src[4:]
        ranked = sorted(cand[name], key=lambda c: c.get("pen", 99))
        want = [next(c for c in cand[name] if c["file"] == f) for f in picks[name]]
        spare = [c for c in ranked if c not in want]
        out = []
        for c in want + spare:
            if len(out) == len(want):
                break
            y = None
            for j, (prop, ns) in enumerate(((1.0, True), (1.0, False), (.85, False))):
                yy, info = build_one(name, c, tgt, prop=prop, nonstat=ns)
                info["pass"] = j
                bed_out = info["n_after"] + info["gain"]
                if info["guard"]["ok"] and bed_out <= BED_MAX and len(yy) >= int(.012 * SR):
                    y = yy; break
            if y is None:
                print(f"  {name} {c['file']}: REJECTED bed {bed_out:.1f} guard {dict((k, round(float(v), 2)) for k, v in info['guard'].items())}")
                continue
            out.append((c["file"], y, info))
        for i, (cf, y, info) in enumerate(out, 1):
            fn = f"sfx_{stem}_{i}.wav"
            before = measure(read_wav(os.path.join(HERE, "build", fn))[0], SR) if os.path.exists(os.path.join(HERE, "build", fn)) else None
            write_wav(os.path.join(BUILD3, fn), y, SR)
            after = measure(y, SR)
            rep[fn] = dict(key=key, src=cf, before=before, after=after, **{k: v for k, v in info.items() if k != "guard"}, guard=info["guard"])
            g = info["guard"]
            print(f"{fn:26s} {cf:8s} floor {before['floor'] if before else 0:7.1f} -> {after['floor']:7.1f}  tail {before['tail_ms'] if before else 0:5.0f} -> {after['tail_ms']:4.0f} ms"
                  f"  hiss8-16 {before['hiss8_16'] if before else 0:6.1f} -> {after['hiss8_16']:6.1f}  dur {after['dur']:.2f}"
                  f"  bed {info['n_raw']:.0f}>{info['n_after'] + info['gain']:.0f}out  pass {info['pass']}  guard lvl {g['dlvl']:+.1f} cen {g['dcen']*100:+.0f}% flat {g['dflat']*100:+.0f}% tr {g['dtr']:+.1f}", flush=True)
        if len(out) != len(want):
            print(f"  !! {key}: {len(out)} of {len(want)} takes")
        rep[key + "#n"] = len(out)
    json.dump(rep, open(os.path.join(HERE, "report3.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
