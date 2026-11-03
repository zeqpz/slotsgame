"""Shared audio helpers: WAV io, BS.1770 loudness, analysis."""
import wave, numpy as np
from scipy import signal


def read_wav(p):
    with wave.open(p) as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if sw == 2:
        x = np.frombuffer(raw, "<i2").astype(np.float64) / 32768
    elif sw == 3:
        b = np.frombuffer(raw, np.uint8).reshape(-1, 3)
        v = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
        v = np.where(v >= 1 << 23, v - (1 << 24), v)
        x = v.astype(np.float64) / (1 << 23)
    elif sw == 4:
        x = np.frombuffer(raw, "<i4").astype(np.float64) / 2**31
    else:
        x = (np.frombuffer(raw, np.uint8).astype(np.float64) - 128) / 128
    return x.reshape(-1, ch), sr, sw


def write_wav(p, x, sr):
    x = np.asarray(x)
    if x.ndim == 1:
        x = x[:, None]
    pcm = (np.clip(x, -1, 1) * 32767).round().astype("<i2")
    with wave.open(p, "wb") as w:
        w.setnchannels(x.shape[1]); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())


def k_weight(x, sr):
    # BS.1770 pre-filter + RLB high-pass, designed via bilinear at any sr
    f0, G, Q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    K = np.tan(np.pi * f0 / sr); Vh = 10 ** (G / 20); Vb = Vh ** 0.4996667741545416
    a0 = 1 + K / Q + K * K
    b1 = [(Vh + Vb * K / Q + K * K) / a0, 2 * (K * K - Vh) / a0, (Vh - Vb * K / Q + K * K) / a0]
    a1 = [1, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0]
    f0, Q = 38.13547087602444, 0.5003270373238773
    K = np.tan(np.pi * f0 / sr)
    a2 = [1, 2 * (K * K - 1) / (1 + K / Q + K * K), (1 - K / Q + K * K) / (1 + K / Q + K * K)]
    b2 = [1, -2, 1]
    return signal.lfilter(b2, a2, signal.lfilter(b1, a1, x, axis=0), axis=0)


def lufs(x, sr):
    """Integrated loudness (gated), and a short-sound friendly 'momentary max'."""
    if x.ndim == 1:
        x = x[:, None]
    y = k_weight(x, sr)
    blk, hop = int(0.4 * sr), int(0.1 * sr)
    if len(y) < blk:
        y = np.vstack([y, np.zeros((blk - len(y), y.shape[1]))])
    ms = []
    for i in range(0, len(y) - blk + 1, hop):
        ms.append((y[i:i + blk] ** 2).mean(0).sum())
    ms = np.array(ms)
    L = -0.691 + 10 * np.log10(ms + 1e-15)
    g = ms[L > -70]
    if len(g) == 0:
        return -99.0, -99.0
    rel = -0.691 + 10 * np.log10(g.mean()) - 10
    g2 = ms[(L > -70) & (L > rel)]
    I = -0.691 + 10 * np.log10(g2.mean())
    return float(I), float(L.max())


def analyze(x, sr):
    m = x.mean(1) if x.ndim > 1 else x
    pk = np.abs(x).max()
    I, M = lufs(x, sr)
    f, P = signal.welch(m, sr, nperseg=min(2048, len(m)))
    cen = float((f * P).sum() / max(P.sum(), 1e-20))
    # noise floor: 10th percentile of 10 ms RMS frames relative to full scale, and re peak frame
    n = max(1, int(0.01 * sr)); k = len(m) // n
    r = np.sqrt((m[:k * n].reshape(k, n) ** 2).mean(1)) + 1e-12
    floor = 20 * np.log10(np.percentile(r, 10))
    # edge levels (first/last 2 ms abs max)
    e = max(1, int(0.002 * sr))
    return dict(dur=len(m) / sr, peak_db=20 * np.log10(pk + 1e-12), lufs=I, mmax=M, centroid=cen,
                floor_db=floor, start_db=20 * np.log10(np.abs(m[:e]).max() + 1e-12),
                end_db=20 * np.log10(np.abs(m[-e:]).max() + 1e-12))


def noise_floor(x, sr, pct=10):
    """Stationary noise floor (dBFS RMS): per-frequency low percentile of the power over time,
    summed over frequency, calibrated so white noise of RMS r reads 20log10(r)."""
    from scipy import signal as _s
    m = x.mean(1) if x.ndim > 1 else x
    if len(m) < 2048:
        m = np.pad(m, (0, 2048 - len(m)))
    f, t, Z = _s.stft(m, sr, nperseg=1024, noverlap=768)
    P = np.abs(Z) ** 2
    nb = np.percentile(P, pct, axis=1).sum()
    # calibration on white noise
    rng = np.random.default_rng(0); w = rng.standard_normal(sr) * 0.1
    _, _, Zw = _s.stft(w, sr, nperseg=1024, noverlap=768)
    cal = np.percentile(np.abs(Zw) ** 2, pct, axis=1).sum() / 0.01
    return 10 * np.log10(nb / cal + 1e-20)
