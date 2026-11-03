"""Synthesised sounds (44.1 kHz, noise-free by construction) for what the generator did badly:
paint drips (a bubble 'plip': a damped sine whose pitch rises, a tiny onset click, a wet
splat of filtered noise). Output: synth/<name>_<n>.wav"""
import os, sys
import numpy as np
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audiolib import write_wav

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "synth")
SR = 44100


def bp_noise(n, lo, hi, rng):
    sos = signal.butter(2, [lo, hi], "bandpass", fs=SR, output="sos")
    return signal.sosfilt(sos, rng.standard_normal(n))


def drip(f0, rise, tau, splat, seed, dur=.22):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f0 * (1 + rise * (1 - np.exp(-t / .011)))           # the bubble's pitch sweeps up
    ph = 2 * np.pi * np.cumsum(f) / SR
    amp = np.minimum(1, t / .0007) * np.exp(-t / tau)
    tone = np.sin(ph) * amp + .12 * np.sin(2 * ph + .7) * amp ** 1.6
    click = bp_noise(n, 2500, 7000, rng) * np.exp(-t / .0009)
    click /= np.abs(click).max() + 1e-9
    wet = bp_noise(n, 300, 2200, rng) * np.exp(-t / .006) * np.minimum(1, t / .0004)
    wet /= np.abs(wet).max() + 1e-9
    mono = tone + .22 * click + splat * wet
    # a little width: the splat decorrelated across the two sides, the tone centred
    wet2 = bp_noise(n, 300, 2200, np.random.default_rng(seed + 99)) * np.exp(-t / .006) * np.minimum(1, t / .0004)
    wet2 /= np.abs(wet2).max() + 1e-9
    L = tone + .22 * click + splat * wet
    R = tone + .22 * click + splat * (.6 * wet + .4 * wet2)
    st = np.stack([L, R], 1)
    # end where it has died away, with a short fade
    e = np.abs(st).max(1)
    live = np.nonzero(e > e.max() * 10 ** (-60 / 20))[0]
    st = st[:live[-1] + 1]
    nf = min(len(st) // 3, int(.012 * SR))
    st[-nf:] *= (np.linspace(1, 0, nf) ** 2)[:, None]
    st *= 10 ** (-3 / 20) / np.abs(st).max()
    return st


DRIPS = [  # f0 Hz, pitch rise, decay s, splat level
    (880, .95, .022, .30),
    (1080, .80, .019, .25),
    (720, 1.10, .026, .35),
    (1300, .70, .016, .22),
    (980, 1.00, .021, .45),   # a fatter, wetter one
    (620, .85, .030, .40),
]


def pan(x, p):
    """equal-power pan, p in -1..1"""
    a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], 1)


def ping(f, tau, n, amp=1.0, bright=1.0):
    """one glassy bell ping: a sine plus two inharmonic partials, 0.4 ms attack"""
    t = np.arange(n) / SR
    env = np.minimum(1, t / .0004) * np.exp(-t / tau)
    y = np.sin(2 * np.pi * f * t) * env
    for ratio, lvl, tk in ((2.76, .22 * bright, .55), (5.40, .09 * bright, .35), (2.0, .12, .8)):
        if f * ratio < 19000:
            y += lvl * np.sin(2 * np.pi * f * ratio * t + ratio) * np.exp(-t / (tau * tk)) * np.minimum(1, t / .0004)
    return amp * y


NOTES = [2093.0, 2349.3, 2637.0, 3136.0, 3520.0, 4186.0, 4698.6, 5274.0, 6271.9]   # C7 pentatonic-ish


def place(buf, x, at):
    i = int(at * SR)
    m = min(len(x), len(buf) - i)
    if m > 0:
        buf[i:i + m] += x[:m]


def tidy(st, peak_db=-4.0, tail_db=-62, fade=.03):
    e = np.abs(st).max(1)
    live = np.nonzero(e > e.max() * 10 ** (tail_db / 20))[0]
    st = st[:live[-1] + 1]
    nf = min(len(st) // 3, int(fade * SR))
    st[-nf:] *= (np.linspace(1, 0, nf) ** 2)[:, None]
    st[0] = 0
    return st * (10 ** (peak_db / 20) / np.abs(st).max())


def sparkle(seed, count=8, spread=.42, dur=1.0, rising=True):
    rng = np.random.default_rng(seed)
    buf = np.zeros((int(dur * SR), 2))
    times = np.sort(rng.random(count)) ** 1.3 * spread
    idx = np.sort(rng.choice(len(NOTES), count, replace=True)) if rising else rng.choice(len(NOTES), count)
    for k, (t0, ni) in enumerate(zip(times, idx)):
        f = NOTES[ni] * (1 + rng.normal(0, .003))
        x = ping(f, rng.uniform(.05, .13), int(.5 * SR), amp=(1 - .5 * k / count) * rng.uniform(.6, 1.0))
        place(buf, pan(x, rng.uniform(-.65, .65)), t0)
    # air: a faint high shimmer that follows the pings
    n = len(buf); t = np.arange(n) / SR
    air = bp_noise(n, 7000, 15000, rng)
    air /= np.abs(air).max()
    aenv = np.clip(1 - np.abs(t - spread / 2) / (spread / 2 + .15), 0, 1) ** 2
    buf += pan(air * aenv * .05, 0) * 1.0
    return tidy(buf)


def glint(f, seed):
    rng = np.random.default_rng(seed)
    n = int(1.1 * SR)
    x = ping(f, .13, n, bright=1.3)
    x += .35 * ping(f * 2.0, .07, n)
    tr = bp_noise(n, 6000, 14000, rng) * np.exp(-np.arange(n) / SR / .0015)
    x += .25 * tr / (np.abs(tr).max() + 1e-9)
    st = np.stack([x, np.roll(x, 9) * .97], 1)
    return tidy(st, tail_db=-56, fade=.06)


def shine(seed, dur=.55):
    rng = np.random.default_rng(seed)
    n = int(dur * SR); t = np.arange(n) / SR
    # a swipe: noise through a resonant band sweeping up 2.5 k -> 11 k
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    blk = 256
    for i in range(0, n, blk):
        p = min(1, (i / SR) / .26)
        fc = 2500 * (11000 / 2500) ** p
        sos = signal.butter(2, [fc * .8, min(fc * 1.25, 20000)], "bandpass", fs=SR, output="sos")
        seg = signal.sosfilt(sos, noise[max(0, i - 2048):i + blk])[-min(blk, n - i):]
        out[i:i + len(seg)] = seg
    out /= np.abs(out).max() + 1e-9
    env = np.sin(np.pi * np.clip(t / .30, 0, 1)) ** 2
    sw = out * env * .55
    st = np.stack([sw * np.linspace(1, .5, n), sw * np.linspace(.5, 1, n)], 1)   # left to right
    for k, (at, f) in enumerate(((.20, 4186.0 * rng.uniform(.99, 1.01)), (.27, 6271.9 * rng.uniform(.99, 1.01)))):
        place(st, pan(ping(f, .11, int(.4 * SR), amp=.8 - .25 * k), .3 + .3 * k), at)
    return tidy(st)


def glow(seed, dur=.95, base=1568.0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR); t = np.arange(n) / SR
    att, rel = .22, .55
    env = np.where(t < att, np.sin(np.pi / 2 * t / att) ** 2, np.exp(-(t - att) / (rel / 3)))
    tone = np.zeros(n)
    for ratio, lvl in ((.5, .35), (1.0, 1.0), (1.5, .28), (2.0, .4)):
        for det in (-.0025, .0025):
            tone += lvl * np.sin(2 * np.pi * base * ratio * (1 + det) * t + rng.uniform(0, 6))
    tone *= env / 4
    # breathing shimmer on top
    air = bp_noise(n, 5000, 13000, rng)
    air /= np.abs(air).max()
    trem = .6 + .4 * np.sin(2 * np.pi * 14 * t)
    air *= env * trem * .12
    L = tone + air
    R = np.roll(tone, 13) + bp_noise(n, 5000, 13000, np.random.default_rng(seed + 7)) / 4 * env * trem * .12
    return tidy(np.stack([L, R], 1), tail_db=-58, fade=.08)


def main():
    os.makedirs(OUT, exist_ok=True)
    jobs = {}
    for i, sd in enumerate((11, 23, 37), 1):
        jobs[f"sparkle_{i}"] = sparkle(sd)
    for i, f in enumerate((3136.0, 3520.0, 4186.0, 4698.6), 1):
        jobs[f"glint_{i}"] = glint(f, 50 + i)
    for i, sd in enumerate((5, 9), 1):
        jobs[f"shine_{i}"] = shine(sd)
    for i, (sd, b) in enumerate(((3, 1568.0), (4, 1760.0)), 1):
        jobs[f"glow_pulse_{i}"] = glow(sd, base=b)
    for k, y in jobs.items():
        write_wav(os.path.join(OUT, k + ".wav"), y, SR)
        print(f"{k}: {len(y) / SR:.3f}s")


def main_drips():
    os.makedirs(OUT, exist_ok=True)
    for i, (f0, rise, tau, splat) in enumerate(DRIPS, 1):
        y = drip(f0, rise, tau, splat, seed=i)
        write_wav(os.path.join(OUT, f"paint_drip_{i}.wav"), y, SR)
        print(f"paint_drip_{i}: {len(y) / SR:.3f}s")


if __name__ == "__main__":
    main_drips()
    main()
