"""Cut the game's music out of the Lyria takes and encode it.

  python tools/music/build.py              # every cue with a take in art/music-src/
  python tools/music/build.py base menu    # only these
  python tools/music/build.py --wav base   # also a 48 kHz WAV (head + the loop twice) in %TEMP%/music_build/

Each cue in cues.py is cut from art/music-src/<cue>.mp3:

  - decoded and resampled to 48 kHz, the game's rate
  - its beat grid found: the tempo by folding the onset curve over candidate beat lengths, the
    downbeat as the beat of the bar where the harmony changes most
  - the loop: `bars` bars from a downbeat, chosen where the two bars after its end sound most like the
    two bars after its start, so going round sounds like carrying on; the end is then lined up with
    the start to the sample by cross-correlation, and the loop's first 1/16 note is crossfaded in from
    what the take plays after the loop's end
  - a head (cues.py) played once in front of it
  - levelled so the loop reads -14 LUFS, then encoded into frontend/assets/: Opus in Ogg (trimmed to
    the sample by every decoder) and AAC in ADTS for browsers without Opus, with 4800 frames in
    front (the loop's end, or silence before a head) for decoders that cut a little off the front

and the cue's MUSIC entry for frontend/index.html is printed.
"""
import json, os, sys, tempfile, wave
import numpy as np
import av
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from cues import CUES

SRC = os.path.join(ROOT, "art", "music-src")
OUT = os.path.join(ROOT, "frontend", "assets")
WAVS = os.path.join(tempfile.gettempdir(), "music_build")
SR = 48000
HOP = 240              # onset curve resolution: 5 ms
MASTER_LUFS = -14.0
PREROLL = 4800         # AAC frames in front of the cue
OPUS_RATE, AAC_RATE = 128000, 160000


# ------------------------------------------------------------------ audio in and out
def load(path):
    c = av.open(path)
    rate = c.streams.audio[0].rate
    x = np.concatenate([f.to_ndarray() for f in c.decode(audio=0)], axis=1).T.astype(np.float64)
    c.close()
    if rate != SR:
        g = np.gcd(SR, rate)
        x = signal.resample_poly(x, SR // g, rate // g, axis=0)
    return x


def encode(pcm, path, fmt, codec, bitrate, sample_fmt):
    out = av.open(path, "w", format=fmt)
    st = out.add_stream(codec, rate=SR, layout="stereo")
    st.bit_rate = bitrate
    pcm = pcm.astype(np.float32)
    for i in range(0, len(pcm), 1024):
        ch = pcm[i:i + 1024]
        arr = ch.T.copy() if sample_fmt.endswith("p") else ch.reshape(1, -1).copy()
        fr = av.AudioFrame.from_ndarray(arr, format=sample_fmt, layout="stereo")
        fr.sample_rate = SR; fr.pts = i
        for p in st.encode(fr):
            out.mux(p)
    for p in st.encode(None):
        out.mux(p)
    out.close()


def decoded(path):
    c = av.open(path)
    y = np.concatenate([f.to_ndarray() for f in c.decode(audio=0)], axis=1).T
    c.close()
    return y


def offset_of(y, seg, near, span=3000):
    """where seg (a second of drums: a sustained tone would match a period off too) sits in y, within
    +-span of `near`"""
    lo = max(0, near - span)
    win = y[lo:near + span + len(seg), 0]
    c = signal.correlate(win, seg[:, 0], mode="valid")
    norm = np.sqrt(signal.correlate(win ** 2, np.ones(len(seg)), mode="valid")) + 1e-9
    return lo + int(np.argmax(c / norm))


def lufs(x):
    """BS.1770 integrated loudness (K-weighted, gated), 48 kHz stereo"""
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1, -1.99004745483398, 0.99007225036621]
    y = signal.lfilter(b2, a2, signal.lfilter(b1, a1, x, axis=0), axis=0)
    blk, hop = int(.4 * SR), int(.1 * SR)
    ms = np.array([(y[i:i + blk] ** 2).mean(0).sum() for i in range(0, len(y) - blk, hop)])
    ld = -0.691 + 10 * np.log10(ms + 1e-12)
    gated = ms[ld > -70]
    rel = -0.691 + 10 * np.log10(gated.mean()) - 10
    return -0.691 + 10 * np.log10(ms[(ld > -70) & (ld > rel)].mean())


# ------------------------------------------------------------------ the beat grid
def stft_mag(mono, n, hop):
    _, _, Z = signal.stft(mono, SR, nperseg=n, noverlap=n - hop, boundary=None, padded=False)
    return np.abs(Z)                                   # frame k is centred on k * hop + n / 2


def beat_grid(x, bpm):
    """Beat times (samples, float) and the index of the first downbeat."""
    mono = x.mean(1)
    mag = np.log1p(100 * stft_mag(mono, 2048, HOP))
    onset = lambda m: np.maximum(np.diff(m, axis=1), 0).sum(0)
    flux = onset(mag)
    env = np.maximum(flux - signal.medfilt(flux, 41), 0)
    low = onset(mag[1:7])                              # under 150 Hz: the kick
    t_of = lambda k: (k + 1) * HOP + 1024              # a flux frame's time, in samples
    # tempo: the autocorrelation's strongest beat length within 12% of the asked tempo (or its double or half)
    e = env - env.mean()
    ac = signal.correlate(e, e, mode="full", method="fft")[len(e) - 1:]
    fps = SR / HOP
    cands = []
    for f in (1, 2, .5):
        for b in np.arange(bpm * f * .88, bpm * f * 1.12, .02):
            if 70 <= b <= 190:
                lag = 60 * fps / b
                cands.append((sum(np.interp(k * lag, np.arange(len(ac)), ac) for k in (1, 2, 4, 8)) - .3 * f, b))
    b0 = max(cands)[1]
    if abs(b0 * 2 - bpm) < abs(b0 - bpm): b0 *= 2  # count half-time grooves at the asked pace
    if abs(b0 / 2 - bpm) < abs(b0 - bpm): b0 /= 2
    # then fine: fold the onset curve over each candidate beat length; the true one stacks the hits
    k = np.arange(len(env))
    best = None
    for b in np.linspace(b0 * .995, b0 * 1.005, 801):
        P = 60 * fps / b
        ph = (k / P) % 1.0
        h = np.bincount((ph * 64).astype(int), weights=env, minlength=64)
        h = np.convolve(np.r_[h[-2:], h, h[:2]], [.25, .5, 1, .5, .25], "valid")
        j = int(np.argmax(h))
        if best is None or h[j] > best[0]:
            best = (h[j], b, j)
    _, b, j = best
    P = 60 * fps / b                                   # beat length in flux frames
    # the folded hits can be the off-beat hi-hats (house's open hats outweigh a soft kick): the beat
    # is where the kick lands, so move half a beat if the kick lines up there clearly better
    hl = np.bincount(((k / P) % 1.0 * 64).astype(int), weights=low, minlength=64)
    near = lambda c: hl[[(c + o) % 64 for o in (-2, -1, 0, 1, 2)]].sum()
    if near(j + 32) > 1.3 * near(j):
        j = (j + 32) % 64
    first = (j / 64) * P
    n_beats = int((len(env) - first) / P)
    beats = np.array([t_of(first + i * P) for i in range(n_beats)])
    beats = beats[beats < len(x) - 1]
    # downbeat: claps and snares land on 2 and 4, which leaves two candidates (when they stand out);
    # between those, the music changes on bar lines, so the phase whose 4-beat blocks differ most from
    # the block before starts the bars. (Not the chord changes alone: house piano pushes its chords a
    # beat early, which put the bar line a beat early.)
    bp = signal.sosfilt(signal.butter(4, [1500, 6000], "bp", fs=SR, output="sos"), mono)
    snare = np.log(np.array([np.sqrt((bp[int(t):int(t) + int(.06 * SR)] ** 2).mean()) for t in beats]) + 1e-9)
    by_parity = [snare[0::2].mean(), snare[1::2].mean()]
    parity = None if abs(by_parity[0] - by_parity[1]) < .1 else 1 - int(np.argmax(by_parity))
    F = beat_features(x, beats)
    def change(q):
        blocks = [F[i:i + 4].mean(0) for i in range(q, len(F) - 3, 4)]
        return np.mean([np.linalg.norm(a - b) for a, b in zip(blocks[1:], blocks[:-1])])
    d = max((q for q in range(4) if parity is None or q % 2 == parity), key=change)
    return beats, b, d


def chroma_per_beat(x, beats):
    mono = signal.decimate(x.mean(1), 4)
    sr, n, hop = SR / 4, 4096, 512
    _, _, Z = signal.stft(mono, sr, nperseg=n, noverlap=n - hop, boundary=None, padded=False)
    f = np.fft.rfftfreq(n, 1 / sr)
    sel = (f > 80) & (f < 2000)
    midi = 69 + 12 * np.log2(f[sel] / 440)
    w = np.clip(1 - np.abs(midi - np.round(midi)) / .3, 0, 1)
    pc = np.round(midi).astype(int) % 12
    M = np.zeros((12, sel.sum()))
    M[pc, np.arange(sel.sum())] = w
    C = M @ np.abs(Z[sel])                              # 12 x frames
    ft = (np.arange(C.shape[1]) * hop + n / 2) * 4      # frame centres, in 48 kHz samples
    out = np.zeros((len(beats), 12))
    for i, t0 in enumerate(beats):
        t1 = beats[i + 1] if i + 1 < len(beats) else t0 + (beats[1] - beats[0])
        m = (ft >= t0) & (ft < t1)
        v = C[:, m].mean(1) if m.any() else np.zeros(12)
        out[i] = v / (np.linalg.norm(v) + 1e-9)
    return out


def band_db(x, beats):
    """each beat's spectrum: 24 bands from 40 Hz to 16 kHz, in dB"""
    mono = x.mean(1)
    mag = stft_mag(mono, 2048, 480) ** 2
    f = np.fft.rfftfreq(2048, 1 / SR)
    edges = np.geomspace(40, 16000, 25)
    bands = np.stack([mag[(f >= lo) & (f < hi)].sum(0) for lo, hi in zip(edges[:-1], edges[1:])])
    ft = np.arange(mag.shape[1]) * 480 + 1024
    B = np.zeros((len(beats), 24))
    for i, t0 in enumerate(beats):
        t1 = beats[i + 1] if i + 1 < len(beats) else t0 + (beats[1] - beats[0])
        m = (ft >= t0) & (ft < t1)
        B[i] = 10 * np.log10(bands[:, m].mean(1) + 1e-12) if m.any() else -120
    return B


def beat_features(x, beats):
    """One vector a beat for telling bars apart: the band spectrum and the chroma, each standardised"""
    z = lambda A: (A - A.mean(0)) / (A.std(0) + 1e-9)
    F = np.hstack([z(band_db(x, beats)), z(chroma_per_beat(x, beats))])
    return F / (np.linalg.norm(F, axis=1, keepdims=True) + 1e-9)


# ------------------------------------------------------------------ the loop
def transients(mono):
    """the hits: the rectified top end, smoothed over 1 ms - lines up drums even where the chords differ"""
    hf = np.abs(signal.sosfilt(signal.butter(2, 1500, "hp", fs=SR, output="sos"), mono))
    return np.convolve(hf, np.ones(48) / 48, "same")


def best_lag(a, b, span):
    """how far to shift b (within +-span) to line it up with a"""
    c = signal.correlate(b, a, mode="valid")             # b is a longer by 2 * span
    norm = np.sqrt(signal.correlate(b ** 2, np.ones(len(a)), mode="valid")) + 1e-9
    return int(np.argmax(c / norm)) - span


def cut(cue, x, verbose=True):
    spec = CUES[cue]
    beats, bpm, d = beat_grid(x, spec["bpm"])
    B, C = band_db(x, beats), chroma_per_beat(x, beats)
    nb = spec["bars"] * 4
    rms = np.array([20 * np.log10(np.sqrt((x[int(beats[i]):int(beats[i + 1])] ** 2).mean()) + 1e-9) for i in range(len(beats) - 1)] + [-99])
    med = np.median(rms)
    w = 8                                               # beats compared after each junction
    head = spec["head"]
    lo = int(np.searchsorted(beats, spec["loop_from"] * SR))
    if head is not None:                                # the loop carries on the head's bar: same beat of it
        h = int(np.argmin(np.abs(beats - head * SR))); d = h % 4
    cands = [i for i in range(max(lo, 4), len(beats) - nb - w - 1) if i % 4 == d]
    # a junction is judged by what is heard on either side of it: the spectrum (dB apart, 60 Hz to
    # 11 kHz, over the 2 bars after and the bar before) and the harmony (chroma, 1 = the same chord)
    db = lambda i, j, n: np.abs(B[i:i + n].mean(0) - B[j:j + n].mean(0))[2:22].mean()
    chord = lambda i, j, n: (C[i:i + n] * C[j:j + n]).sum(1).mean()
    scored = []
    for i in cands:
        a, b = range(i, i + w), range(i + nb, i + nb + w)
        if min(rms[list(a) + list(b)]) < med - 6:       # a junction in a breakdown, the outro or silence
            continue
        scored.append((-db(i, i + nb, w) - .5 * db(i - 4, i + nb - 4, 4)
                       + 4 * (chord(i, i + nb, w) - 1) + 2 * (chord(i - 4, i + nb - 4, 4) - 1), i))
    if not scored:
        raise RuntimeError(f"{cue}: no {spec['bars']}-bar stretch fits")
    scored.sort(reverse=True)
    score, i = scored[0]
    S = int(round(beats[i]))
    L0 = int(round(beats[i + nb])) - S
    # to the sample: the hits of the 2 beats after the end against those after the start
    tr = transients(x.mean(1))
    span, A = int(.02 * SR), int(2 * 60 / bpm * SR)
    lag = best_lag(tr[S:S + A] - tr[S:S + A].mean(), tr[S + L0 - span:S + L0 + span + A] - tr[S:S + A].mean(), span)
    L = L0 + lag
    hp = signal.sosfilt(signal.butter(2, 150, "hp", fs=SR, output="sos"), x.mean(1))
    rho = np.corrcoef(hp[S:S + A], hp[S + L:S + L + A])[0, 1]
    F16 = int(min(60 / bpm / 4, .08) * SR)
    loop = x[S:S + L].copy()
    fade = .5 - .5 * np.cos(np.pi * np.arange(F16) / F16)
    loop[:F16] = x[S + L:S + L + F16] * (1 - fade)[:, None] + x[S:S + F16] * fade[:, None]
    # the head
    if head is None:
        pre, H, H_len = np.zeros((0, 2)), 0, 0
    else:
        H = int(round(beats[h]))                         # on the take's own beat
        tail = int(spec.get("tail", 2.0) * SR)
        pre = x[:H + tail].copy()
        ring = np.ones(H + tail); ring[H:] = .5 + .5 * np.cos(np.pi * np.arange(tail) / tail)
        pre *= ring[:, None]; H_len = H + tail
    if len(pre):
        pre[:96] *= np.linspace(0, 1, 96)[:, None]       # no click at the very start
    info = dict(bpm=bpm, downbeat=d, start_s=S / SR, frames=L, lag=lag, score=score, rho=rho,
                head=H, head_len=H_len, beats=len(beats))
    if verbose:
        print(f"  {cue}: {bpm:.3f} BPM, loop {spec['bars']} bars from {S / SR:.2f}s ({L} frames = {L / SR:.3f}s, "
              f"end shifted {lag:+d}), junction {db(i, i + nb, w):.2f} dB apart, chord match {chord(i, i + nb, w):.2f}, "
              f"seam correlation {rho:.2f}"
              + (f", head {H / SR:.2f}s" if H else ""))
        print("    next best starts:", ", ".join(f"{beats[j] / SR:.1f}s ({sc:.2f})" for sc, j in scored[1:5]))
    return pre, loop, info


# ------------------------------------------------------------------ build
def build(cue, wav=False):
    spec = CUES[cue]
    x = load(os.path.join(SRC, cue + ".mp3"))
    pre, loop, info = cut(cue, x)
    g = 10 ** ((MASTER_LUFS - lufs(np.vstack([loop, loop]))) / 20)
    pre, loop = pre * g, loop * g
    peak = max(np.abs(loop).max(), np.abs(pre).max() if len(pre) else 0)
    if peak > .98:                                       # never clip: take the whole cue down a little
        pre, loop = pre * .98 / peak, loop * .98 / peak
        g *= .98 / peak
    cue_pcm = np.vstack([pre, loop])
    ogg, aac = os.path.join(OUT, f"music_{cue}.ogg"), os.path.join(OUT, f"music_{cue}.aac")
    encode(cue_pcm, ogg, "ogg", "libopus", OPUS_RATE, "flt")
    lead = loop[-PREROLL:] if not info["head_len"] else np.zeros((PREROLL, 2))
    encode(np.vstack([lead, cue_pcm]), aac, "adts", "aac", AAC_RATE, "fltp")
    # check what a decoder hands back: Opus to the sample, AAC with its encoder delay in front
    hl = info["head_len"]
    drums = cue_pcm[hl + SR // 4:hl + SR // 4 + SR]      # a second of the loop
    y = decoded(ogg)
    assert len(y) == len(cue_pcm), (cue, len(y), len(cue_pcm))
    assert offset_of(y, drums, hl + SR // 4) == hl + SR // 4, cue
    ya = decoded(aac)
    aac_start = offset_of(ya, drums, PREROLL + 1024 + hl + SR // 4) - hl - SR // 4
    level = 10 ** ((spec["game_lufs"] - MASTER_LUFS) / 20) / (g / g)   # the master reads MASTER_LUFS
    entry = {"ogg": f"assets/music_{cue}.ogg", "aac": f"assets/music_{cue}.aac", "frames": info["frames"]}
    if info["head_len"]:
        entry.update(head=info["head"], headLen=info["head_len"])
    entry.update(aacStart=aac_start, aacFrames=len(ya), bpm=round(info["bpm"], 3), bars=spec["bars"], level=round(level, 3))
    print(f"  {cue}: {os.path.getsize(ogg) // 1024} KB ogg, {os.path.getsize(aac) // 1024} KB aac, "
          f"peak {peak * (g if peak <= .98 else 1):.2f}, {len(cue_pcm) / SR:.1f}s")
    if wav:
        os.makedirs(WAVS, exist_ok=True)
        demo = np.vstack([pre, loop, loop])
        with wave.open(os.path.join(WAVS, cue + ".wav"), "wb") as fh:
            fh.setnchannels(2); fh.setsampwidth(2); fh.setframerate(SR)
            fh.writeframes((np.clip(demo, -1, 1) * 32767).astype("<i2").tobytes())
    return entry


def main(argv):
    want = [a for a in argv if a in CUES] or [c for c in CUES if os.path.exists(os.path.join(SRC, c + ".mp3"))]
    entries = {}
    for cue in want:
        print(cue)
        entries[cue] = build(cue, wav="--wav" in argv)
    print("\nMUSIC entries for frontend/index.html:")
    for cue, e in entries.items():
        print(f"  {cue + ':':7}" + json.dumps(e, separators=(", ", ": ")).replace('"', "").replace("{", "{ ").replace("}", " },")
              .replace("ogg: ", 'ogg: "').replace(".ogg,", '.ogg",').replace("aac: assets", 'aac: "assets').replace(".aac,", '.aac",'))


if __name__ == "__main__":
    main(sys.argv[1:])
