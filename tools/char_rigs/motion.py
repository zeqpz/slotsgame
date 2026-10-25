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
from animkit import sample, write, duration, delay, spring, spring_loop, settle, accel, smooth, DEFAULT

KNEE_MAX = 60.0          # deg: deepest knee bend the boy's trousers are asked to make
FOOT_KEEP = .3           # share of the skull's foot/leg motion kept (what both feet do together)
FOOT_APART = .12         # ... and of what they do against each other (the shoes overlap)
HOP_SINK = .012          # units of the skull's hip sink per unit/s^2 of the hop's vertical acceleration (win: ~5)
HOP_SINK_MAX = 8.0       # ... and no deeper than this


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


def face_take(t, amp=1.0, at=0.0):
    """head (scaleX, scaleY) for a quick squash-stretch-settle as a new face comes in at `at`
    (the squash bottoms out on the swap)"""
    keys_t = np.array([0, .06, .15, .27, .4]) + at - (.06 if at > 0 else 0)
    sy = np.interp(t, keys_t, [1, 1 - .07 * amp, 1 + .035 * amp, 1 - .008 * amp, 1])
    sx = np.interp(t, keys_t, [1, 1 + .05 * amp, 1 - .02 * amp, 1 + .004 * amp, 1])
    return smooth(sx, t, .02), smooth(sy, t, .02)


RELAX = .36       # s before a reaction ends: its face relaxes back to the idle face


def face_swaps(anim, slot, D, idle_face="face_idle"):
    """Every face change inside the clip gets a take; a reaction's own face relaxes back to the
    idle face just before the end, under a take, so the hand-over to idle never swaps the face
    with nothing moving. Returns the swap times after t=0."""
    keys = anim.get("slots", {}).get(slot, {}).get("attachment")
    if not keys: return []
    if keys[-1].get("name") != idle_face and D > 1.0:
        keys.append({"time": round(D - RELAX, 4), "name": idle_face})
    return [k["time"] for k in keys if k.get("time", 0) > 0]


def takes(t, swaps, amp):
    sx = np.ones_like(t); sy = np.ones_like(t)
    for at in [0.0] + list(swaps):
        a, b = face_take(t, amp, at)
        sx *= a; sy *= b
    return sx, sy


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
        hx, hyy = takes(t, face_swaps(a, "head", D), 1.0)
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

def plant_feet(ch, n):
    # planted feet: the shoes overlap, so they move together - what the two feet do in common is
    # kept at FOOT_KEEP, what they do against each other at FOOT_APART
    for kind in ("leg", "foot"):
        L, R = f"{kind}_left", f"{kind}_right"
        for c in ("x", "y", "rotate"):
            l = ch_get(ch, n, L, c); r = ch_get(ch, n, R, c)
            if not (np.ptp(l) or np.ptp(r)): continue
            d0 = DEFAULT[c]
            com = ((l - d0) + (r - d0)) / 2; dif = ((l - d0) - (r - d0)) / 2
            keep, apart = FOOT_KEEP, FOOT_APART
            if kind == "foot":
                # the front shoe overlaps the back one: any difference between them - even the
                # same tilt about two different heels - slides one over the other and shows the
                # join. The shoes move as one, by translation only.
                apart = 0.0
                if c == "rotate": keep = 0.0
            ch_set(ch, L, c, d0 + com * keep + dif * apart)
            ch_set(ch, R, c, d0 + com * keep - dif * apart)


def skull_reaction(j, name, take=True):
    a = j["animations"][name]
    D = duration(a)
    t, ch = sample(a, D)
    n = len(t)
    plant_feet(ch, n)
    if name in ("win", "big_win"):
        skull_hop_feet(j, t, ch)
    elif name == "anticipation":
        skull_tiptoe(j, t, ch)
    elif name == "lose":
        skull_slump(j, t, ch)
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
    # the knees take the push-off and the landing: the hips sink as the hop's vertical acceleration
    # peaks (the legs are jointed and on the pelvis now, rig_skull.joint_legs) - only ever a sink,
    # since past the drawn stance the trousers would buckle inward
    sink = settle(spring(np.clip(-ay * HOP_SINK, -HOP_SINK_MAX, 0), t, 2.8, .55), t, 0)   # ay > 0: push-off, landing
    ch_set(ch, "pelvis", "y", ch_get(ch, n, "pelvis", "y") + np.minimum(sink, 0))
    head_w = torso_w + head_new
    bl = ch_get(ch, n, "beanie", "rotate")
    ch_set(ch, "beanie", "rotate", lag_chain(t, head_w, bl, .07, 2.0, .33))
    for arm in ("arm_left", "arm_right"):
        ch_set(ch, arm, "rotate", lag_chain(t, torso_w, ch_get(ch, n, arm, "rotate"), .04, 2.8, .6))
    # the jaw flaps a little on a landing
    jaw = ch_get(ch, n, "jaw", "rotate") + settle(spring(np.clip(ay * .0009, 0, 3), t, 3.0, .5), t, 0)
    ch_set(ch, "jaw", "rotate", np.maximum(jaw, 0))
    if take:
        hx, hyy = takes(t, face_swaps(a, "face", D), .8)
        ch_set(ch, "head", "sx", ch_get(ch, n, "head", "sx") * hx)
        ch_set(ch, "head", "sy", ch_get(ch, n, "head", "sy") * hyy)
    smoke_follow(j, t, ch)
    write(a, t, ch)


def skull_compact(j, name, loop=False, smoke=False, take=False, feet=False, steps=False):
    a = j["animations"][name]
    D = duration(a)
    t, ch = sample(a, D)
    n = len(t)
    if feet:
        plant_feet(ch, n)
    if steps:
        skull_idle_feet(j, t, ch)
    if take:
        swaps = face_swaps(a, "face", D)
        if swaps:
            hx, hyy = 1, 1
            for at in swaps:
                x_, y_ = face_take(t, .8, at); hx = hx * x_; hyy = hyy * y_
            ch_set(ch, "head", "sx", ch_get(ch, n, "head", "sx") * hx)
            ch_set(ch, "head", "sy", ch_get(ch, n, "head", "sy") * hyy)
    if smoke:
        smoke_follow(j, t, ch, loop)
    write(a, t, ch, loop)


# ---------------------------------------------------------------- the skull's feet
# With jointed legs on an IK (rig_skull.joint_legs) the feet can move without tearing the
# trousers, so they take part in every move (owner, 2026-10-25: the feet standing still under a
# moving body "made the movement feel weird"). Sizes are in units; the skull is drawn at ~0.37
# CSS px per unit, so a 10-unit lift reads as a small, clear step.

BACK_TOE = (-330.0, 145.0)   # world: the ball of the side-on back shoe (foot_left), where its heel lift pivots


def window(t, t0, t1):
    """0 -> 1 -> 0 over [t0, t1] (sine squared), 0 outside."""
    u = np.clip((t - t0) / (t1 - t0), 0, 1)
    return np.sin(np.pi * u) ** 2


def heel(j, deg, pivot=BACK_TOE, foot="foot_left"):
    """A heel lift on the back shoe: the foot bone's (x, y, rotate) offsets that turn it by `deg`
    (array) about its toe, so the toe stays on the ground and the heel comes up."""
    W = fk(j, {}, 1, [foot])[foot]
    ox, oy = float(np.ravel(W[4])[0]) - pivot[0], float(np.ravel(W[5])[0]) - pivot[1]
    r = np.radians(deg)
    return ox * np.cos(r) - oy * np.sin(r) - ox, ox * np.sin(r) + oy * np.cos(r) - oy, deg


def add(ch, n, bone, comp, v):
    ch_set(ch, bone, comp, ch_get(ch, n, bone, comp) + v)


def skull_idle_feet(j, t, ch):
    """The weight shifts with the hips (enhance.skull_anims sways them +-HIP_SWAY, furthest right
    at 1.8 s and left at 3.8 s): with the weight on the front foot the back heel comes up, and
    with it back on the back foot the front foot taps once."""
    n = len(t)
    lift = window(t, 1.1, 2.5)
    dx, dy, r = heel(j, 3.2 * lift)
    add(ch, n, "foot_left", "x", dx); add(ch, n, "foot_left", "y", dy); add(ch, n, "foot_left", "rotate", r)
    tap = window(t, 3.3, 3.78)
    add(ch, n, "foot_right", "y", 9.0 * tap); add(ch, n, "foot_right", "rotate", -2.0 * tap)


def skull_hop_feet(j, t, ch):
    """In the air the feet tuck up and part a little, both scaled by the hop's height, and they
    are down again for the landing (which the hips' sink takes, skull_reaction)."""
    n = len(t)
    my = ch_get(ch, n, "motion", "y")
    h = np.clip(my / max(float(my.max()), 1.0), 0, 1) if my.max() > 1 else np.zeros(n)
    tuck = smooth(np.clip(my, 0, None) * .3, t, .04)
    add(ch, n, "foot_left", "y", tuck); add(ch, n, "foot_right", "y", tuck)
    add(ch, n, "foot_left", "x", -6.0 * h); add(ch, n, "foot_right", "x", 6.0 * h)
    add(ch, n, "foot_left", "rotate", 4.0 * h); add(ch, n, "foot_right", "rotate", -3.0 * h)


def skull_tiptoe(j, t, ch):
    """Leaning in, he comes up onto his toes: the heels and the hips rise together (the legs keep
    their length - past their drawn stance the trousers would buckle), the upper body keeps the
    height the clip gave it."""
    n = len(t)
    ty = ch_get(ch, n, "torso", "y")
    tip = np.clip(.6 * ty, 0, 9.0)
    W = fk(j, {}, 1, ["foot_left"])["foot_left"]
    reach = float(np.ravel(W[4])[0]) - BACK_TOE[0]
    dx, dy, r = heel(j, np.degrees(tip / reach))
    add(ch, n, "foot_left", "x", dx); add(ch, n, "foot_left", "y", dy); add(ch, n, "foot_left", "rotate", r)
    add(ch, n, "foot_right", "y", tip)
    add(ch, n, "pelvis", "y", tip); add(ch, n, "torso", "y", -tip)


def skull_slump(j, t, ch):
    """Losing, he sinks into his knees as he slumps, and the front foot scuffs the ground."""
    n = len(t)
    D = t[-1]
    add(ch, n, "pelvis", "y", -5.0 * window(t, .1, D - .05))
    scuff = window(t, .55, 1.35)
    add(ch, n, "foot_right", "x", 7.0 * scuff); add(ch, n, "foot_right", "y", 4.0 * window(t, .55, .95))
    add(ch, n, "foot_right", "rotate", -3.0 * scuff)


SMOKE_BONE = "smoke_lag"


def add_smoke_lag(j):
    """A bone between the cigar and the smoke plume, at the ember: the body clips swing it so
    the smoke trails the head and settles (smoke_loop keeps animating the plume's own bones on
    its own track, untouched). Inserted before smoke_base, so weighted meshes are re-indexed."""
    names = [b["name"] for b in j["bones"]]
    if SMOKE_BONE in names: return
    i = names.index("smoke_base")
    sb = j["bones"][i]
    j["bones"].insert(i, {"name": SMOKE_BONE, "parent": sb["parent"], "x": sb.get("x", 0), "y": sb.get("y", 0), "length": 30})
    sb["parent"] = SMOKE_BONE; sb["x"] = 0; sb["y"] = 0
    for sk in j["skins"]:
        for atts in sk["attachments"].values():
            for att in atts.values():
                if att.get("type") != "mesh" or len(att["vertices"]) == len(att["uvs"]): continue
                v = att["vertices"]; k = 0; nv = len(att["uvs"]) // 2; c = 0
                while c < nv:
                    m = int(v[k]); k += 1
                    for _ in range(m):
                        if v[k] >= i: v[k] = int(v[k]) + 1
                        k += 4
                    c += 1


def smoke_follow(j, t, ch, loop=False):
    """Keys smoke_lag: the plume keeps its own heading while the head turns and catches up
    (a loose spring), leans away from sideways motion, and squashes/stretches a little with
    vertical motion of the body."""
    n = len(t)
    names = [b["name"] for b in j["bones"]]
    if SMOKE_BONE not in names: return
    W = fk(j, ch, n, ["cigar"])
    cw = world_rot(W["cigar"])
    cx = smooth(W["cigar"][4], t, .03); cy = smooth(W["cigar"][5], t, .03)
    vx = np.gradient(cx, t); vy = np.gradient(cy, t)
    sp = (lambda v: spring_loop(v, t, 1.4, .45)) if loop else (lambda v: settle(spring(v, t, 1.4, .45), t, v[-1], .3))
    lag = sp(cw) - cw
    lag = lag + sp(np.clip(-vx * .045, -6, 6))
    sy = 1 + sp(np.clip(-vy * .00035, -.07, .07))
    if not loop:
        lag = settle(lag, t, 0, .3); sy = settle(sy, t, 1, .3)
    ch_set(ch, SMOKE_BONE, "rotate", lag)
    ch_set(ch, SMOKE_BONE, "sy", sy)


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
