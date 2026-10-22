"""Motion pass: overlap, follow-through, squash and settle on the delivered clips.

The reactions as delivered were baked sine bumps: every bone of a clip rose and fell on the same
frames, so the whole figure moved like one stiff board, and every channel carried a linear key on
every 30 fps frame (most of the boy's 1.5 MB skeleton). Each clip keeps its choreography, its
length and its name; on top of it:
- overlapping action: each link down a chain (torso -> head -> beanie, torso -> hands -> bills)
  trails the one above it and overshoots a touch before it settles - a damped spring chasing the
  world-space angle the delivered clip asked for;
- weight: the big head dips on a hard landing and lifts on a push-off (from the body's
  vertical acceleration), and the torso squashes and stretches with it;
- a "take" on the face: the head pops (squash, stretch, settle) as a reaction's face comes in, so
  the swap reads as an expression change rather than a cut;
- every one-shot eases back onto its exact rest pose at the end, so the blend into idle is clean;
- the boy's knees never fold past KNEE_MAX: where a clip crouched him deeper (or tucked his feet
  up while his hips dropped), his hips ride higher instead;
- the skull's feet stay planted under him: his shoes are rigid now, and the delivered clips
  shuffled each foot on its own while the body hopped (FOOT_KEEP of that is kept);
- the result is written back as a few eased bezier keys per channel.
"""
import math
import numpy as np
import animkit as ak2
from animkit import sample, write, duration, delay, spring, settle, accel, smooth, DEFAULT

KNEE_MAX = 60.0          # deg: deepest knee bend the boy's trousers are asked to make
FOOT_KEEP = .3           # share of the skull's independent foot/leg shuffling that is kept


def ch_get(ch, n, bone, comp):
    return ch.get(bone, {}).get(comp, np.full(n, DEFAULT[comp]))


def ch_set(ch, bone, comp, v):
    ch.setdefault(bone, {})[comp] = v


def fk(j, ch, n, wanted):
    """World matrices per frame (arrays) for `wanted` bones and their ancestors (no constraints)."""
    B = {b["name"]: b for b in j["bones"]}
    out = {}
    def go(name):
        if name in out: return out[name]
        b = B[name]
        x = b.get("x", 0) + ch_get(ch, n, name, "x"); y = b.get("y", 0) + ch_get(ch, n, name, "y")
        r = np.radians(b.get("rotation", 0) + ch_get(ch, n, name, "rotate"))
        sx = b.get("scaleX", 1) * ch_get(ch, n, name, "sx"); sy = b.get("scaleY", 1) * ch_get(ch, n, name, "sy")
        la, lb = np.cos(r) * sx, np.cos(r + math.pi / 2) * sy
        lc, ld = np.sin(r) * sx, np.sin(r + math.pi / 2) * sy
        p = b.get("parent")
        if not p:
            m = (la, lb, lc, ld, x, y)
        else:
            pa, pb, pc, pd, px, py = go(p)
            m = (pa * la + pb * lc, pa * lb + pb * ld, pc * la + pd * lc, pc * lb + pd * ld, pa * x + pb * y + px, pc * x + pd * y + py)
        out[name] = m
        return m
    for w in wanted: go(w)
    return out


def world_rot(m):
    return np.degrees(np.arctan2(m[2], m[0]))


def lag_chain(t, parent_world, local, d, freq, zeta, rest=0.0):
    """The child's world angle trails what the clip asked for: delayed, then sprung."""
    want = parent_world + local
    got = spring(delay(want, t, d), t, freq, zeta)
    out = got - parent_world
    return settle(out, t, rest, .22)


def face_take(t, amp=1.0):
    """head (scaleX, scaleY) for a quick squash-stretch-settle as a new face comes in"""
    keys_t = np.array([0, .06, .15, .27, .4])
    sy = np.interp(t, keys_t, [1, 1 - .07 * amp, 1 + .035 * amp, 1 - .008 * amp, 1])
    sx = np.interp(t, keys_t, [1, 1 + .05 * amp, 1 - .02 * amp, 1 + .004 * amp, 1])
    return smooth(sx, t, .02), smooth(sy, t, .02)


# ---------------------------------------------------------------- the boy

def knee_lift(j, ch, n):
    """Per frame, how far the hips must rise for no knee to bend past KNEE_MAX."""
    B = {b["name"]: b for b in j["bones"]}
    W = fk(j, ch, n, ["thigh_left", "thigh_right", "foot_left", "foot_right"])
    need = np.zeros(n)
    for side in ("left", "right"):
        L1 = B[f"thigh_{side}"]["length"]; L2 = B[f"shin_{side}"]["length"]
        hx, hy = W[f"thigh_{side}"][4], W[f"thigh_{side}"][5]
        fx, fy = W[f"foot_{side}"][4], W[f"foot_{side}"][5]
        dmin = math.sqrt(L1 * L1 + L2 * L2 - 2 * L1 * L2 * math.cos(math.radians(180 - KNEE_MAX)))
        dx = hx - fx; dy = hy - fy
        lift = np.where(np.hypot(dx, dy) < dmin, np.sqrt(np.maximum(dmin * dmin - dx * dx, 0)) - dy, 0)
        need = np.maximum(need, lift)
    return need


def boy_knees(j, t, ch):
    """Keep the knees within KNEE_MAX: first the clip's crouches are made shallower as a whole
    (the dips keep their shape, just less deep), then anything left - a foot tucked up while
    the hips drop - lifts the hips in a broad, eased rise rather than a clipped hold."""
    n = len(t)
    by0 = ch_get(ch, n, "body", "y").copy()
    if knee_lift(j, ch, n).max() <= .5: return 0.0
    # frames where both feet are down: there only the depth of the crouch bends the knees
    planted = (ch_get(ch, n, "foot_left", "y") < 2) & (ch_get(ch, n, "foot_right", "y") < 2)
    best = 1.0
    for s in np.linspace(1, .25, 16):
        ch_set(ch, "body", "y", np.where(by0 < 0, by0 * s, by0))
        best = s
        if (knee_lift(j, ch, n) * planted).max() <= .5: break
    need = knee_lift(j, ch, n)
    if need.max() > .5:
        from scipy.ndimage import maximum_filter1d
        k = int(.14 / (t[1] - t[0]))
        need = smooth(maximum_filter1d(need, 2 * k + 1), t, .1)
        ch_set(ch, "body", "y", ch_get(ch, n, "body", "y") + need)
    return round(float(1 - best), 2), float(need.max())


def boy_reaction(j, name, take=True, knees=True):
    a = j["animations"][name]
    D = duration(a)
    t, ch = sample(a, D)
    n = len(t)
    lifted = boy_knees(j, t, ch) if knees else 0.0
    # torso trails the hips a hair
    tr = ch_get(ch, n, "torso", "rotate")
    tr = settle(spring(delay(tr, t, .03), t, 3.2, .7), t, 0)
    ch_set(ch, "torso", "rotate", tr)
    W = fk(j, ch, n, ["torso", "body"])
    torso_w = world_rot(W["torso"])
    # weight: vertical acceleration of the hips drives a squash and a head dip
    by = smooth(W["body"][5], t, .04)
    ay = smooth(accel(by, t), t, .03)
    sq = np.clip(-ay * 3.2e-5, -.05, .05)                       # push-off/landing squash
    sy = settle(1 + spring(sq, t, 3.6, .45), t, 1)
    sx = settle(1 - .55 * (sy - 1), t, 1)
    ch_set(ch, "torso", "sy", ch_get(ch, n, "torso", "sy") * sy)
    ch_set(ch, "torso", "sx", ch_get(ch, n, "torso", "sx") * sx)
    hy = ch_get(ch, n, "head", "y") + settle(spring(np.clip(-ay * .0022, -6, 6), t, 2.8, .5), t, 0)
    ch_set(ch, "head", "y", hy)
    # the head and the hands trail the torso
    head_local = ch_get(ch, n, "head", "rotate")
    ch_set(ch, "head", "rotate", lag_chain(t, torso_w, head_local, .05, 2.4, .5))
    grip_local = ch_get(ch, n, "grip", "rotate")
    grip_new = lag_chain(t, torso_w, grip_local, .04, 2.8, .55)
    ch_set(ch, "grip", "rotate", grip_new)
    gy = ch_get(ch, n, "grip", "y") + settle(spring(np.clip(-ay * .0016, -5, 5), t, 3.0, .5), t, 0)
    ch_set(ch, "grip", "y", gy)
    grip_w = torso_w + grip_new
    for i in range(6):   # the fanned bills flick after the hands, each a beat behind the last
        b = f"bill_{i}"
        loc = ch_get(ch, n, b, "rotate")
        ch_set(ch, b, "rotate", lag_chain(t, grip_w, loc, .03 + .012 * i, 3.4 - .2 * i, .38))
    if take:
        hx, hyy = face_take(t)
        ch_set(ch, "head", "sx", ch_get(ch, n, "head", "sx") * hx)
        ch_set(ch, "head", "sy", ch_get(ch, n, "head", "sy") * hyy)
    write(a, t, ch)
    return lifted


def boy_compact(j, name, loop=False):
    """Only re-key (no reshaping): eased sparse keys instead of a key per frame."""
    a = j["animations"][name]
    t, ch = sample(a, duration(a))
    write(a, t, ch, loop)


# ---------------------------------------------------------------- the skull

def skull_reaction(j, name, take=True):
    a = j["animations"][name]
    D = duration(a)
    t, ch = sample(a, D)
    n = len(t)
    # planted feet: keep only a little of each foot's and leg's own shuffling
    for b in ("leg_left", "leg_right", "foot_left", "foot_right"):
        for c in ("x", "y", "rotate"):
            if b in ch and c in ch[b]:
                ch[b][c] = ch[b][c] * FOOT_KEEP
    W = fk(j, ch, n, ["motion", "torso"])
    my = smooth(W["motion"][5], t, .04)
    ay = smooth(accel(my, t), t, .03)
    # torso trails the hop, squashes on push-off and landing
    tr = ch_get(ch, n, "torso", "rotate")
    ch_set(ch, "torso", "rotate", settle(spring(delay(tr, t, .03), t, 3.0, .65), t, 0))
    sq = np.clip(-ay * 2.6e-5, -.06, .06)
    sy = settle(1 + spring(sq, t, 3.4, .42), t, 1)
    old_sy = ch_get(ch, n, "torso", "sy")
    ch_set(ch, "torso", "sy", settle(1 + (old_sy - 1) * .6 + (sy - 1), t, 1))
    ch_set(ch, "torso", "sx", settle(ch_get(ch, n, "torso", "sx") * (1 - .5 * (sy - 1)), t, 1))
    W = fk(j, ch, n, ["torso"])
    torso_w = world_rot(W["torso"])
    head_local = ch_get(ch, n, "head", "rotate")
    head_new = lag_chain(t, torso_w, head_local, .05, 2.3, .5)
    ch_set(ch, "head", "rotate", head_new)
    hy = ch_get(ch, n, "head", "y") + settle(spring(np.clip(-ay * .0018, -6, 6), t, 2.6, .5), t, 0)
    ch_set(ch, "head", "y", hy)
    head_w = torso_w + head_new
    bl = ch_get(ch, n, "beanie", "rotate")
    ch_set(ch, "beanie", "rotate", lag_chain(t, head_w, bl, .07, 2.0, .33))
    for arm in ("arm_left", "arm_right"):
        ch_set(ch, arm, "rotate", lag_chain(t, torso_w, ch_get(ch, n, arm, "rotate"), .04, 2.8, .6))
    # the jaw flaps a little on a landing
    jaw = ch_get(ch, n, "jaw", "rotate") + settle(spring(np.clip(ay * .0009, 0, 3), t, 3.0, .5), t, 0)
    ch_set(ch, "jaw", "rotate", np.maximum(jaw, 0))
    if take:
        hx, hyy = face_take(t, .8)
        ch_set(ch, "head", "sx", ch_get(ch, n, "head", "sx") * hx)
        ch_set(ch, "head", "sy", ch_get(ch, n, "head", "sy") * hyy)
    write(a, t, ch)


def skull_compact(j, name, loop=False):
    a = j["animations"][name]
    t, ch = sample(a, duration(a))
    write(a, t, ch, loop)


# ---------------------------------------------------------------- enter / exit

def strip_fades(j, names=("enter", "exit")):
    """The walk-on / walk-off fades are the canvas's job now (CSS opacity on the whole figure):
    fading every slot on its own let each part show through the next - the arm through the
    torso, the hood backing through the face."""
    for n in names:
        a = j["animations"].get(n)
        if not a: continue
        for s, tls in a.get("slots", {}).items():
            for k in ("alpha", "rgba", "rgb"):
                tls.pop(k, None)
        a["slots"] = {s: v for s, v in a.get("slots", {}).items() if v}
