"""Hand-inked vector helpers: every ink line is a FILLED shape of varying width (never a
uniform stroke). Closed outlines become rings that swell on the shadow side; open lines
become tapered ribbons; hatch marks are lens-shaped slivers."""
import math
import numpy as np

LIGHT = np.array([-0.55, -0.83])          # light comes from the upper left
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def arr(P):
    return np.asarray(P, dtype=float)


def dedupe(P, closed):
    P = arr(P)
    keep = [0]
    for i in range(1, len(P)):
        if np.hypot(*(P[i] - P[keep[-1]])) > 1e-6:
            keep.append(i)
    P = P[keep]
    if closed and len(P) > 1 and np.hypot(*(P[0] - P[-1])) < 1e-6:
        P = P[:-1]
    return P


def resample(P, closed, step=1.5):
    P = dedupe(P, closed)
    Q = np.vstack([P, P[:1]]) if closed else P
    seg = np.linalg.norm(np.diff(Q, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    L = s[-1]
    n = max(int(round(L / step)), 6)
    t = np.linspace(0, L, n, endpoint=not closed)
    return np.stack([np.interp(t, s, Q[:, 0]), np.interp(t, s, Q[:, 1])], 1)


def chaikin(P, closed, it=3):
    P = arr(P)
    for _ in range(it):
        if closed:
            Q = np.roll(P, -1, 0)
            A, B = .75 * P + .25 * Q, .25 * P + .75 * Q
            N = np.empty((2 * len(P), 2)); N[0::2] = A; N[1::2] = B
            P = N
        else:
            P0, Q = P[:-1], P[1:]
            A, B = .75 * P0 + .25 * Q, .25 * P0 + .75 * Q
            N = np.empty((2 * len(P0), 2)); N[0::2] = A; N[1::2] = B
            P = np.vstack([P[:1], N, P[-1:]])
    return P


def arclen(P, closed):
    Q = np.vstack([P, P[:1]]) if closed else P
    seg = np.linalg.norm(np.diff(Q, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    return (s[:-1], s[-1]) if closed else (s, s[-1])


def tangents(P, closed):
    if closed:
        T = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    else:
        T = np.gradient(P, axis=0)
    return T / (np.linalg.norm(T, axis=1, keepdims=True) + 1e-12)


def left_normals(T):
    return np.stack([T[:, 1], -T[:, 0]], 1)


def signed_area(P):
    x, y = P[:, 0], P[:, 1]
    return .5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)


def noise(s, rng, amp, wls=(37, 83, 171)):
    v = np.zeros_like(s)
    for wl in wls:
        v += np.sin(2 * np.pi * s / wl + rng.uniform(0, 2 * np.pi)) * rng.uniform(.5, 1)
    return amp * v / len(wls)


def outline_ring(P, base, seed, bias=.55, amp=.16, step=1.2, smooth_it=0, inner_frac=.5, wmul=None,
                 wls=(37, 83, 171), floor=None, wob=0.0, wob_wls=(150, 270, 430)):
    """A closed hand-inked outline around polygon P: returns (outer, inner) loops whose
    band is the ink. The band is wider where the edge faces away from the light.
    wls: wavelengths (px of outline length) of the width's swell; floor: the narrowest the
    line may get; wob: how far (px) the line's centre wanders off P, so long straight edges
    are not ruled."""
    rng = np.random.default_rng(seed)
    P = arr(P)
    if smooth_it:
        P = chaikin(P, True, smooth_it)
    P = resample(P, True, step)
    T = tangents(P, True)
    n = left_normals(T)
    # make n point outward
    c = P.mean(0)
    if np.mean(np.sum(n * (P - c), 1)) < 0:
        n = -n
    s, L = arclen(P, True)
    sh = np.clip(-(n @ LIGHT), 0, 1)                  # 1 where the edge faces the shadow
    sh = smooth_closed(sh, 9)
    w = base * (1 - bias * .5 + bias * sh) * (1 + noise(s, rng, amp, wls))
    if wmul is not None:
        w = w * smooth_closed(wmul(P), 15)
    w = np.maximum(w, base * .3 if floor is None else floor)
    if wob:
        P = P + n * noise(s, rng, wob, wob_wls)[:, None]
    outer = P + n * (w * (1 - inner_frac))[:, None]
    inner = P - n * (w * inner_frac)[:, None]
    return outer, inner


def smooth_closed(v, k):
    if k <= 1:
        return v
    ker = np.ones(k) / k
    pad = np.concatenate([v[-k:], v, v[:k]])
    return np.convolve(pad, ker, mode='same')[k:-k]


def ribbon(P, wmax, seed=0, t0=.18, t1=.18, power=.75, bias=.35, amp=.14, step=1.0,
           smooth_it=0, wmin_frac=0.0, side_bias=0.0):
    """An open hand-inked line: a filled ribbon that tapers to a point at each end
    (t0/t1 = fraction of the length the taper takes; 0 = blunt end)."""
    rng = np.random.default_rng(seed)
    P = arr(P)
    if smooth_it:
        P = chaikin(P, False, smooth_it)
    P = resample(P, False, step)
    T = tangents(P, False)
    n = left_normals(T)
    s, L = arclen(P, False)
    u = s / max(L, 1e-9)
    tap = np.ones_like(u)
    if t0 > 0:
        tap = np.minimum(tap, u / t0)
    if t1 > 0:
        tap = np.minimum(tap, (1 - u) / t1)
    tap = np.clip(tap, 0, 1) ** power
    tap = np.maximum(tap, wmin_frac)
    sh = np.abs(n @ LIGHT)
    w = wmax * tap * (1 - bias * .5 + bias * sh) * (1 + noise(s, rng, amp))
    w = np.maximum(w, 0)
    a = .5 + side_bias * .5          # share of the width on the left side
    Lp = P + n * (w * a)[:, None]
    Rp = P - n * (w * (1 - a))[:, None]
    return np.vstack([Lp, Rp[::-1]])


def sliver(p0, p1, w, bow=0.0, seed=0, kind='stroke'):
    """A hatch mark from p0 to p1, optionally bowed. 'stroke' is a brush flick: a rounded
    start and a long tapered tail; 'lens' is pointed at both ends (for shines)."""
    p0, p1 = arr(p0), arr(p1)
    d = p1 - p0
    L = np.hypot(*d)
    nrm = np.array([d[1], -d[0]]) / (L + 1e-9)
    t = np.linspace(0, 1, 24)
    pts = p0[None] + d[None] * t[:, None] + nrm[None] * (bow * L * 4 * t * (1 - t))[:, None]
    if kind == 'lens':
        return ribbon(pts, w, seed=seed, t0=.5, t1=.5, power=.7, amp=.05, step=.7)
    return ribbon(pts, w, seed=seed, t0=.16, t1=.7, power=.85, amp=.05, step=.7)


def ellipse_pts(cx, cy, rx, ry, a0, a1, n=None):
    """Points on an ellipse, angles in degrees, y down: 90 = the near (bottom) side."""
    if n is None:
        n = max(int(abs(a1 - a0) / 360 * 2 * math.pi * max(rx, ry) / 1.0), 12)
    t = np.radians(np.linspace(a0, a1, n))
    return np.stack([cx + rx * np.cos(t), cy + ry * np.sin(t)], 1)


def d_of(*loops):
    out = []
    for L in loops:
        L = arr(L)
        out.append('M' + ' L'.join(f'{x:.2f},{y:.2f}' for x, y in L) + 'Z')
    return ' '.join(out)


def d_ring(outer, inner):
    return d_of(outer, inner[::-1])
