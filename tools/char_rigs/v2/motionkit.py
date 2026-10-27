"""Clip authoring: channels sampled at 120 fps, shaped with eased keys, bumps and springs (overlap,
follow-through, settle), then written as a few eased bezier keys per channel (animkit.write)."""
import math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r'C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\char_rigs')
import animkit as ak            # noqa: E402

FPS = 120


class Clip:
    def __init__(self, dur, loop=False):
        self.dur = dur; self.loop = loop
        self.n = int(round(dur * FPS)) + 1
        self.t = np.linspace(0, dur, self.n)
        self.ch = {}
        self.slots = {}; self.events = []; self.draw = []

    def get(self, bone, comp):
        return self.ch.get(bone, {}).get(comp, np.full(self.n, ak.DEFAULT[comp]))

    def set(self, bone, comp, v):
        self.ch.setdefault(bone, {})[comp] = np.asarray(v, float) * np.ones(self.n)

    def add(self, bone, comp, v):
        base = self.get(bone, comp)
        if comp in ('sx', 'sy'):
            self.set(bone, comp, base * v)
        else:
            self.set(bone, comp, base + v)

    def face(self, slot, keys):
        """[(time, attachment)]"""
        self.slots.setdefault(slot, {})['attachment'] = [({'name': a} if not t else {'time': round(t, 4), 'name': a})
                                                         for t, a in keys]

    def color(self, slot, keys):
        """[(time, 'rrggbbaa')], linear"""
        self.slots.setdefault(slot, {})['rgba'] = [({'color': c} if not t else {'time': round(t, 4), 'color': c})
                                                   for t, c in keys]

    def event(self, t, name, **kw):
        e = {'time': round(t, 4), 'name': name}; e.update(kw); self.events.append(e)

    def json(self):
        a = {'bones': {}}
        ak.write(a, self.t, self.ch, self.loop)
        # every one-shot keeps its exact length even if its last key is earlier
        if self.slots: a['slots'] = self.slots
        if self.events: a['events'] = sorted(self.events, key=lambda e: e['time'])
        if self.draw: a['drawOrder'] = self.draw
        d = ak.duration(a)
        if d < self.dur - 1e-4:
            a['bones'].setdefault('root', {})['rotate'] = [{'value': 0}, {'time': round(self.dur, 4), 'value': 0}]
        return a


# ---------------------------------------------------------------- curve shapes

def ease(x):
    x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)


def ease_out(x):
    x = np.clip(x, 0, 1); return 1 - (1 - x) ** 3


def ease_in(x):
    x = np.clip(x, 0, 1); return x ** 3


def keys(t, kv, shape='smooth'):
    """value through keys [(time, value)], eased between keys (zero slope at each key: holds and
    turns read as weight), or 'flow' (Catmull-Rom through the keys: no stops)"""
    T = np.array([k[0] for k in kv], float); V = np.array([k[1] for k in kv], float)
    out = np.empty_like(t)
    if shape == 'flow' and len(T) > 2:
        from scipy.interpolate import PchipInterpolator
        return PchipInterpolator(T, V, extrapolate=True)(np.clip(t, T[0], T[-1]))
    for i, tt in enumerate(t):
        j = np.searchsorted(T, tt, side='right') - 1
        if j < 0: out[i] = V[0]; continue
        if j >= len(T) - 1: out[i] = V[-1]; continue
        u = (tt - T[j]) / (T[j + 1] - T[j])
        out[i] = V[j] + (V[j + 1] - V[j]) * ease(u)
    return out


def bump(t, t0, tp, t1, amp=1.0):
    """0 before t0, eases up to amp at tp, eases back to 0 at t1"""
    up = ease((t - t0) / max(tp - t0, 1e-6)); dn = ease((t - tp) / max(t1 - tp, 1e-6))
    return amp * np.where(t < tp, up, 1 - dn) * ((t >= t0) & (t <= t1))


def osc(t, period, amp, phase=0.0):
    return amp * np.sin(2 * math.pi * (t / period + phase))


def hop(t, t0, t1, height):
    """a ballistic hop between take-off t0 and landing t1 (parabola)"""
    u = np.clip((t - t0) / (t1 - t0), 0, 1)
    return height * 4 * u * (1 - u) * ((t >= t0) & (t <= t1))


# ---------------------------------------------------------------- springs

def spring(target, t, freq=3.0, zeta=.55, loop=False):
    if loop:
        return ak.spring_loop(target, t, freq, zeta)
    return ak.spring(target, t, freq, zeta)


def lag(clip, child, parent_world, local, d=.05, freq=2.6, zeta=.5, settle=True):
    """the child's world angle trails what it is asked for (parent world + local): delayed, sprung"""
    t = clip.t
    want = parent_world + local
    if clip.loop:
        sh = np.interp((t - d) % clip.dur, t, want)
        got = ak.spring_loop(sh, t, freq, zeta)
    else:
        got = ak.spring(ak.delay(want, t, d), t, freq, zeta)
    out = got - parent_world
    if settle and not clip.loop:
        # the trailing dies away over the last half second (smootherstep on the deviation), so the
        # clip still ends on its exact pose without yanking a link back
        D = t[-1]; w = np.clip((t - (D - .5)) / .5, 0, 1); w = w * w * w * (w * (w * 6 - 15) + 10)
        out = local + (out - local) * (1 - w)
    return out


def settle(clip, v, rest, window=.25):
    return ak.settle(v, clip.t, rest, window)


def smooth(v, t, sigma=.03):
    return ak.smooth(v, t, sigma)
