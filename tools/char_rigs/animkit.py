"""Animation building blocks for the character rig pass.

The delivered clips are baked: a linear key on every 30 fps frame of every channel, sums of
sine bumps with every bone peaking on the same frame. These helpers read any Spine 4.2 bone
timeline into evenly sampled channels, let the rig pass reshape them (overlap, follow-through,
settle, limits), and write them back as a few eased bezier keys per channel - turning points and
whatever else the curve needs to stay within a small tolerance of the motion.
"""
import math
import numpy as np

FPS = 120                      # sampling rate for all channel work
COMP = {"rotate": ("rotate",), "translate": ("x", "y"), "scale": ("sx", "sy"), "shear": ("shx", "shy"),
        "translatex": ("x",), "translatey": ("y",), "scalex": ("sx",), "scaley": ("sy",),
        "shearx": ("shx",), "sheary": ("shy",)}
OUT = {"rotate": "rotate", "x": "translatex", "y": "translatey", "sx": "scalex", "sy": "scaley",
       "shx": "shearx", "shy": "sheary"}
DEFAULT = {"rotate": 0.0, "x": 0.0, "y": 0.0, "sx": 1.0, "sy": 1.0, "shx": 0.0, "shy": 0.0}
TOL = {"rotate": .06, "x": .12, "y": .12, "sx": .0012, "sy": .0012, "shx": .06, "shy": .06}


def _bez(p0, p1, p2, p3, s):
    u = 1 - s
    return u * u * u * p0 + 3 * u * u * s * p1 + 3 * u * s * s * p2 + s * s * s * p3


def eval_keys(keys, kind, comp_index, t):
    """Value of one component of a Spine timeline at times t (array)."""
    fields = ("value",) if len(COMP[kind]) == 1 else ("x", "y")
    f = fields[comp_index]
    d = DEFAULT[COMP[kind][comp_index]]
    T = np.array([k.get("time", 0.0) for k in keys], float)
    V = np.array([k.get(f, d) for k in keys], float)
    t = np.asarray(t, float)
    out = np.empty_like(t)
    for i, tt in enumerate(t):
        j = np.searchsorted(T, tt, side="right") - 1
        if j < 0: out[i] = V[0]; continue
        if j >= len(T) - 1: out[i] = V[-1]; continue
        k = keys[j]; c = k.get("curve")
        t0, t1, v0, v1 = T[j], T[j + 1], V[j], V[j + 1]
        if c == "stepped":
            out[i] = v0
        elif isinstance(c, list):
            cx1, cy1, cx2, cy2 = c[4 * comp_index: 4 * comp_index + 4]
            lo, hi = 0.0, 1.0
            for _ in range(40):                         # solve x(s) = tt
                s = (lo + hi) / 2
                if _bez(t0, cx1, cx2, t1, s) < tt: lo = s
                else: hi = s
            out[i] = _bez(v0, cy1, cy2, v1, (lo + hi) / 2)
        else:
            a = 0 if t1 == t0 else (tt - t0) / (t1 - t0)
            out[i] = v0 + (v1 - v0) * a
    return out


def duration(anim):
    d = 0.0
    def walk(o):
        nonlocal d
        if isinstance(o, dict):
            if isinstance(o.get("time"), (int, float)): d = max(d, o["time"])
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(anim)
    return d


def sample(anim, dur, fps=FPS):
    """{bone: {comp: samples}} for every bone timeline of an animation, on t = 0, 1/fps .. dur."""
    n = int(round(dur * fps)) + 1
    t = np.linspace(0, dur, n)
    ch = {}
    for bone, tls in anim.get("bones", {}).items():
        for kind, keys in tls.items():
            if kind not in COMP or not keys: continue
            for ci, comp in enumerate(COMP[kind]):
                ch.setdefault(bone, {})[comp] = eval_keys(keys, kind, ci, t)
    return t, ch


def fit(t, v, tol, loop=False):
    """Sparse eased keys reproducing samples v(t) within tol: [(time, value, slope)]. A loop's
    first and last keys share one slope, so it runs through its seam without a hitch."""
    n = len(v)
    if n < 2 or v.max() - v.min() <= tol:
        return [(0.0, float(v.mean() if n else 0), 0.0)]
    dv = np.gradient(v, t)
    if loop:
        dv[0] = dv[-1] = (v[1] - v[-2]) / ((t[1] - t[0]) + (t[-1] - t[-2]))
    idx = {0, n - 1}
    # turning points
    s = np.sign(np.diff(v))
    for i in range(1, n - 1):
        if s[i - 1] != 0 and s[i] != 0 and s[i - 1] != s[i]: idx.add(i)
        elif s[i - 1] != 0 and s[i] == 0: idx.add(i)
    def slope(i):
        if 0 < i < n - 1 and np.sign(v[i] - v[i - 1]) != np.sign(v[i + 1] - v[i]): return 0.0
        if not loop and i in (0, n - 1) and abs(dv[i]) < 1e-9: return 0.0
        return float(dv[i])
    for _ in range(400):
        ks = sorted(idx)
        worst, wi = 0, None
        for a, b in zip(ks[:-1], ks[1:]):
            if b - a < 2: continue
            t0, t1 = t[a], t[b]; m0, m1 = slope(a), slope(b); dt = t1 - t0
            u = (t[a:b + 1] - t0) / dt
            h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u; h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
            pred = h00 * v[a] + h10 * dt * m0 + h01 * v[b] + h11 * dt * m1
            e = np.abs(pred - v[a:b + 1])
            j = int(np.argmax(e))
            if e[j] > worst: worst, wi = e[j], a + j
        if worst <= tol or wi is None: break
        idx.add(wi)
    ks = sorted(idx)
    return [(float(t[i]), float(v[i]), slope(i)) for i in ks]


def keys_json(fitted, nd=4):
    out = []
    for i, (t, v, m) in enumerate(fitted):
        k = {"value": round(v, nd)}
        if t: k = {"time": round(t, 4), "value": round(v, nd)}
        if i + 1 < len(fitted):
            t1, v1, m1 = fitted[i + 1]; dt = t1 - t
            k["curve"] = [round(t + dt / 3, 4), round(v + m * dt / 3, nd), round(t1 - dt / 3, 4), round(v1 - m1 * dt / 3, nd)]
        out.append(k)
    return out


def write(anim, t, ch, loop=False):
    """Replace the animation's bone timelines with fitted single-value timelines; the clip keeps
    its exact length."""
    dur = duration(anim)
    bones = {}
    for bone, comps in ch.items():
        tls = {}
        for comp, v in comps.items():
            if np.abs(v - DEFAULT[comp]).max() < TOL[comp] * .5:
                continue
            tls[OUT[comp]] = keys_json(fit(t, v, TOL[comp], loop), 5 if comp in ("sx", "sy") else 4)
        if tls: bones[bone] = tls
    anim["bones"] = bones
    if duration(anim) < dur - 1e-4:
        bones.setdefault("root", {})["rotate"] = [{"value": 0}, {"time": round(dur, 4), "value": 0}]


def channels_like(ch, bone, comps=("rotate",), n=None):
    d = ch.setdefault(bone, {})
    for c in comps:
        if c not in d: d[c] = np.full(n, DEFAULT[c])
    return d


# ---------------------------------------------------------------- shaping

def delay(v, t, d):
    """v shifted later by d seconds (holding the first value)."""
    return np.interp(t - d, t, v, left=v[0], right=v[-1])


def spring(target, t, freq=3.0, zeta=.55, v0=None):
    """A damped spring chasing `target` (sampled on t): lag, overshoot, settle."""
    dt = t[1] - t[0]; sub = 4; h = dt / sub
    w = 2 * math.pi * freq
    x = target[0] if v0 is None else v0; vel = 0.0
    out = np.empty_like(target)
    for i in range(len(t)):
        g = target[i]
        for _ in range(sub):
            a = w * w * (g - x) - 2 * zeta * w * vel
            vel += a * h; x += vel * h
        out[i] = x
    return out


def spring_loop(target, t, freq=3.0, zeta=.55, laps=4):
    """Steady-state spring response to a looping target: the last of several laps, so the clip
    still loops seamlessly."""
    big = np.concatenate([target[:-1]] * laps + [target[-1:]])
    tt = np.arange(len(big)) * (t[1] - t[0])
    r = spring(big, tt, freq, zeta)
    return r[-len(target):]


def settle(v, t, rest, window=.2):
    """Ease v onto `rest` over the last `window` seconds (a one-shot must end where it started)."""
    D = t[-1]
    w = np.clip((t - (D - window)) / window, 0, 1); w = w * w * (3 - 2 * w)
    return v * (1 - w) + rest * w


def ease_in(v, t, rest, window=.12):
    """Ease v up from `rest` over the first `window` seconds."""
    w = np.clip(t / window, 0, 1); w = w * w * (3 - 2 * w)
    return rest + (v - rest) * w


def accel(v, t):
    return np.gradient(np.gradient(v, t), t)


def smooth(v, t, sigma=.03):
    from scipy.ndimage import gaussian_filter1d
    return gaussian_filter1d(v, sigma / (t[1] - t[0]), mode="nearest")
