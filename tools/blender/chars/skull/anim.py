# SMOKE SKULL - the clips, keyed INSIDE Blender on the rig build.py made (run after it, in the same Blender; run.py).
# Every clip is an Action on the rig, laid on its NLA track "clips" at its own frames:
#   (output frames, 1.35x slower than designed) idle 1-150 (loop, 5 s)   anticipation 201-265   win 301-397   lose 401-481
#   ash_break 501-597   enter 601-649   exit 701-728
# How the motion is made (all of it ends up as F-curve keys on the bones; nothing is drawn in the game):
#   * the body's poses are laid down as keyed curves per channel (pelvis, torso, chest, neck, head, jaw, cigar, arms)
#   * the legs are worked out per frame from where the hips are and where each shoe is meant to be (planted, tapping,
#     hopping): the thigh turns about the hip, the shin about the knee (the knee bends out - a flex keyed per clip,
#     more if the hips sink further), the shoe turns about the ankle to keep its own angle, and the last few px the
#     leg needs are taken up by the shoe sliding in or out of the pant cuff (its ankle runs on 40 px under the cuff)
#   * overlap and follow-through: the chest, neck and head each trail the turn below them (a damped spring); the
#     beanie's crown and tip, the drawstrings, the four free lace ends, the cuffs and the hood swing after their
#     holders (point masses on springs, driven by how the holder really moves - the rig's own pose, frame by frame)
#   * the one-shots start and end on the rest pose (= idle frame 1); the idle is a groove at 90 bpm that comes back
#     through the rest pose on every beat (the "cues": the frames the game can cut at)
import bpy, json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, os.path.join(REPO, "tools", "blender"))
import fxkit                    # noqa: E402  (read-only: Actions, NLA, sparse keys)

SID = "SKULL"
sc = bpy.data.scenes[SID] if SID in bpy.data.scenes else bpy.context.scene
arm = bpy.data.objects[SID + "_rig"]
spec = json.load(open(os.path.join(REPO, "art", "blender", "chars", "skull", "parts", "parts.json")))
JN = spec["joints"]
FPS = 30
# Every clip plays 1.35x slower than it is designed (owner, 2026-11-03: the clips ran too quickly): the curves below are
# written in design frames (c.t) and laid down on every OUTPUT frame at t = frame / SLOW - the same as Blender's Time
# Remapping (render.frame_map_old 100 / new 135) but keyed, so the Grease Pencil drawn per frame (the ember, the ash)
# runs smooth with it. The springs run in real time (1/30 s per output frame). Lengths here are output frames.
SLOW = 1.35
CLIPS = {"idle": (1, 150, True), "anticipation": (201, 65, False), "win": (301, 97, False), "lose": (401, 81, False),
         "ash_break": (501, 97, False), "enter": (601, 49, False), "exit": (701, 28, False)}
FACE_OF = {}                     # clip -> [(frame, face)]


def U(x, y):                     # master px -> world (x, z) units
    return np.array([(x - 512) / 100.0, (768 - y) / 100.0])


# ============================================================================ the rig in 2D (forward kinematics)
BONES = [b.name for b in arm.data.bones]
PARENT = {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones}
HEAD = {b.name: np.array([b.head_local.x, b.head_local.z]) for b in arm.data.bones}


def Tm(v):
    return np.array([[1, 0, v[0]], [0, 1, v[1]], [0, 0, 1.0]])


def Rm(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def Sm(sx, sy):
    return np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1.0]])


def app(M, p):
    return M[:2, :2] @ p + M[:2, 2]


def ang(M):
    return math.degrees(math.atan2(M[1, 0], M[0, 0]))


class Clip:
    """per-frame channels of one clip: ch[(bone, 'x'|'y'|'r'|'sx'|'sy')] = array over the clip's frames. Also the
    virtual channels that are not bones: ('foot_l'|'foot_r', 'x'|'y'|'r') where each shoe should be (world units,
    degrees, from its rest place, relative to the root), ('flex_l'|'flex_r', 'v') the knee bend (degrees)."""
    def __init__(self, name):
        self.name = name
        self.f0, self.n, self.loop = CLIPS[name]
        self.t = np.arange(self.n, dtype=float) / SLOW   # design frames from the clip's start (curves are written in these)
        self.i = np.arange(self.n, dtype=float)          # output frames
        self.nk = self.n / SLOW                          # the clip's length in design frames
        self.ch = {}

    def get(self, b, c):
        return self.ch.get((b, c), np.full(self.n, 1.0 if c in ("sx", "sy") else 0.0))

    def set(self, b, c, v):
        self.ch[(b, c)] = np.broadcast_to(np.asarray(v, float), (self.n,)).copy()

    def add(self, b, c, v):
        self.set(b, c, self.get(b, c) + v)

    def mul(self, b, c, v):
        self.set(b, c, self.get(b, c) * v)

    def fk(self, f):
        D = {}
        for b in BONES:
            Hh = HEAD[b]
            g = lambda c: float(self.get(b, c)[f]) if (b, c) in self.ch else (1.0 if c in ("sx", "sy") else 0.0)
            B = Tm(Hh) @ Tm((g("x"), g("y"))) @ Rm(g("r")) @ Sm(g("sx"), g("sy")) @ Tm(-Hh)
            D[b] = D[PARENT[b]] @ B if PARENT[b] else B
        return D


# ============================================================================ curve helpers (frames)
def keys(t, pts, ease=False):
    """a smooth curve through (frame, value) keys: Catmull-Rom (flowing through the keys), or ease=True: every key
    a hold (eased in and out of it). Before the first / after the last key it holds."""
    ks = sorted(pts)
    fx = np.array([k[0] for k in ks], float)
    fv = np.array([k[1] for k in ks], float)
    out = np.empty_like(t, dtype=float)
    m = np.zeros(len(ks))
    if not ease and len(ks) > 2:
        for i in range(1, len(ks) - 1):
            m[i] = (fv[i + 1] - fv[i - 1]) / (fx[i + 1] - fx[i - 1])
            # no overshoot past a turning point
            if (fv[i] - fv[i - 1]) * (fv[i + 1] - fv[i]) <= 0:
                m[i] = 0
    for j, tt in enumerate(t):
        if tt <= fx[0]:
            out[j] = fv[0]; continue
        if tt >= fx[-1]:
            out[j] = fv[-1]; continue
        i = np.searchsorted(fx, tt) - 1
        h = fx[i + 1] - fx[i]
        u = (tt - fx[i]) / h
        h00, h10, h01, h11 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u, -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
        out[j] = h00 * fv[i] + h10 * h * m[i] + h01 * fv[i + 1] + h11 * h * m[i + 1]
    return out


def sm(a, b, t):
    u = np.clip((np.asarray(t, float) - a) / (b - a), 0, 1)
    return u * u * (3 - 2 * u)


def bump(t, a, b, c, amp=1.0):
    """0 before a, eased up to amp at b, eased back to 0 at c"""
    return amp * (sm(a, b, t) - sm(b, c, t))


def spring(x, freq, zeta, loop=False, laps=3):
    """the response of a damped spring (freq Hz) dragged by x (per frame): what trails behind a move"""
    w = 2 * math.pi * freq
    n = len(x)
    dt = 1.0 / FPS / 8
    y, v = (x[0], 0.0)
    out = np.empty(n)
    seq = list(range(n)) * (laps if loop else 1)
    for idx, k in enumerate(seq):
        k2 = (k + 1) % n if loop else min(k + 1, n - 1)
        for s in range(8):
            xx = x[k] + (x[k2] - x[k]) * s / 8
            a = w * w * (xx - y) - 2 * zeta * w * v
            v += a * dt
            y += v * dt
        if idx >= len(seq) - n:
            out[k2 if loop else k] = y
    if not loop:
        out = np.concatenate([[x[0]], out[:-1]])
    return out


def settle_end(c, v, frames=10, target=0.0):
    """ease a series onto `target` over the clip's last frames (a one-shot ends exactly at rest)"""
    if c.loop:
        return v
    w = sm(c.n - 1 - frames, c.n - 1, c.i)
    return v * (1 - w) + target * w


def unpin(v, base=0.0):
    """a loop's series made to start exactly at base: the offset at frame 0 eased out over the lap (raised cosine)"""
    n = len(v)
    k = np.arange(n)
    return v - (v[0] - base) * (.5 + .5 * np.cos(2 * np.pi * k / n))


# ============================================================================ overlap: each link trails the turn below it
CHAIN_UP = [("chest", 2.6, .5, .55), ("neck", 2.4, .5, .45), ("head", 2.1, .45, .5)]


def follow(c, gain=1.0):
    world = c.get("pelvis", "r") + c.get("torso", "r")
    for b, hz, z, g in CHAIN_UP:
        lag = spring(world, hz, z, loop=c.loop) - world        # where it would be had it kept its old heading
        local = c.get(b, "r") + g * gain * lag
        local = unpin(local) if c.loop else settle_end(c, local, 8, 0.0)
        c.set(b, "r", local)
        world = world + local
    # the head bobs after the hips' ups and downs (a soft neck), the jaw drops a touch on a hard stop
    y = c.get("pelvis", "y") + c.get("root", "y") * .0
    acc = np.gradient(np.gradient(y)) * FPS * FPS
    hy = spring(np.clip(-acc * .00045 * gain, -.05, .05), 2.8, .45, loop=c.loop)
    jw = np.maximum(0, spring(np.clip(acc * .012 * gain, 0, 5), 3.2, .45, loop=c.loop))
    c.add("head", "y", unpin(hy) if c.loop else settle_end(c, hy, 8))
    c.add("jaw", "r", unpin(jw) if c.loop else settle_end(c, jw, 8))


# ============================================================================ the legs: hips to planted shoes
SIDE = {"l": -1, "r": +1}          # the knee bends out: to the left on the left leg, to the right on the right
TMIN, TMAX = -.12, .05           # how far the shoe may slide up into / down out of the cuff (units)
TOE = {"l": U(168, 1342), "r": U(712, 1452)}     # the toe / heel points the shoes rock on
HEEL = {"l": U(505, 1350), "r": U(548, 1452)}


def foot_about(c, s, pivot, deg):
    """rock shoe s by deg (series) about a world pivot (its toe, its heel): sets foot x / y / r"""
    A = HEAD[f"shoe_{s}"]
    d = A - pivot
    rad = np.radians(deg)
    x = pivot[0] + np.cos(rad) * d[0] - np.sin(rad) * d[1] - A[0]
    y = pivot[1] + np.sin(rad) * d[0] + np.cos(rad) * d[1] - A[1]
    c.add(f"foot_{s}", "x", x)
    c.add(f"foot_{s}", "y", y)
    c.add(f"foot_{s}", "r", deg)


def smin(a, b, k=.015):
    return -k * math.log(math.exp(-a / k) + math.exp(-b / k))


def solve_legs(c):
    for s in "lr":
        th, sh, cf, so = f"thigh_{s}", f"shin_{s}", f"cuff_{s}", f"shoe_{s}"
        for b in (th, sh, so):
            for ch_ in ("r", "x", "y"):
                c.set(b, ch_, 0)
    Hh = {s: HEAD[f"thigh_{s}"] for s in "lr"}
    for f in range(c.n):
        D = c.fk(f)
        rho = ang(D["pelvis"])
        for s in "lr":
            th, sh, so = f"thigh_{s}", f"shin_{s}", f"shoe_{s}"
            v1 = HEAD[sh] - HEAD[th]
            v2 = HEAD[so] - HEAD[sh]
            u2 = v2 / np.linalg.norm(v2)
            h = app(D["pelvis"], HEAD[th])
            tgt = app(D["root"], HEAD[so] + np.array([c.get(f"foot_{s}", "x")[f], c.get(f"foot_{s}", "y")[f]]))
            phi = ang(D["root"]) + c.get(f"foot_{s}", "r")[f]
            d = float(np.linalg.norm(tgt - h))
            side = SIDE[s]

            def tel_of(b):
                Rb = Rm(-side * b)[:2, :2]
                cc = v1 + Rb @ v2
                q = Rb @ u2
                cq = float(cc @ q)
                disc = cq * cq - float(cc @ cc) + d * d
                return (-cq + math.sqrt(max(disc, 0.0))), cc, q
            b = max(0.0, float(c.get(f"flex_{s}", "v")[f]))
            tel, cc, q = tel_of(b)
            if tel < TMIN:                      # the hips sink further than the cuff can take: bend the knee more
                lo, hi = b, 75.0
                for _ in range(40):
                    mid = (lo + hi) / 2
                    if tel_of(mid)[0] < TMIN:
                        lo = mid
                    else:
                        hi = mid
                b = hi
                tel, cc, q = tel_of(b)
            tel = smin(tel, TMAX)               # too far to reach: the shoe comes up with the leg
            w = cc + tel * q
            alpha = math.degrees(math.atan2(*(tgt - h)[::-1]) - math.atan2(*w[::-1]))
            alpha = (alpha + 180) % 360 - 180
            c.ch[(th, "r")][f] = alpha - rho
            c.ch[(sh, "r")][f] = -side * b
            c.ch[(so, "x")][f] = tel * u2[0]
            c.ch[(so, "y")][f] = tel * u2[1]
            c.ch[(so, "r")][f] = phi - (alpha - side * b)


# ============================================================================ secondary: hanging, trailing parts
def holder_mats(c, holder):
    return [c.fk(f)[holder] for f in range(c.n)]


def secondary(c, holder, chains, warm=3, sub=10, settle=10, forces=None, gain=1.0, mats=None):
    """fxkit.secondary in the rig's own 2D: point masses on springs (freq Hz per point, softer to the tip) pulled to
    where each point of the chain would sit were it rigid on the holder, held to their lengths; returns
    {bone: [degrees per frame]} (each bone's turn against its parent). A loop is run several laps, then started where
    it is nearest rest and unpinned to start exactly at rest; a one-shot settles onto rest over its last frames."""
    B = mats or holder_mats(c, holder)
    n = len(B)
    loop = c.loop
    dt = 1.0 / (FPS * sub)
    res = {}
    for name, chd in chains.items():
        Q = [U(*p) for p in chd["chain"]]
        m = len(Q)
        om = [2 * math.pi * hz for hz in chd["freq"]]
        zeta = chd.get("zeta", .2)
        g = chd.get("gain", 1.0) * gain
        limit = chd.get("limit", 0)
        a0 = [math.atan2(Q[i + 1][1] - Q[i][1], Q[i + 1][0] - Q[i][0]) for i in range(m - 1)]
        P = [app(B[0], q) for q in Q]
        V = [np.zeros(2) for _ in Q]
        steps = n * (warm + 1) if loop else n
        rec = []
        for step in range(steps):
            k = step % n
            k2 = (k + 1) % n if loop else min(k + 1, n - 1)
            if step >= steps - n:
                Binv = np.linalg.inv(B[k])
                R = [app(Binv, p) for p in P]
                R = [Q[i] + (R[i] - Q[i]) * g for i in range(m)]
                an = [math.atan2(R[i + 1][1] - R[i][1], R[i + 1][0] - R[i][0]) - a0[i] for i in range(m - 1)]
                an = [math.degrees((d_ + math.pi) % (2 * math.pi) - math.pi) for d_ in an]
                rel = [an[0]] + [an[i] - an[i - 1] for i in range(1, m - 1)]
                if limit:
                    rel = [limit * math.tanh(r / limit) for r in rel]
                rec.append(rel)
            for s_ in range(sub):
                u0, u1 = s_ / sub, (s_ + 1) / sub
                G0 = [app(B[k], q) * (1 - u0) + app(B[k2], q) * u0 for q in Q]
                G1 = [app(B[k], q) * (1 - u1) + app(B[k2], q) * u1 for q in Q]
                t = (step + u0) / FPS
                old = [p.copy() for p in P]
                for i in range(1, m):
                    vg = (G1[i] - G0[i]) / dt
                    acc = (G0[i] - P[i]) * om[i - 1] ** 2 - (V[i] - vg) * (2 * zeta * om[i - 1])
                    if forces:
                        acc = acc + forces(name, i, t, k)
                    V[i] = V[i] + acc * dt
                P[0] = G1[0]
                for i in range(1, m):
                    P[i] = P[i] + V[i] * dt
                for i in range(1, m):
                    L = float(np.linalg.norm(G1[i] - G1[i - 1]))
                    dv = P[i] - P[i - 1]
                    P[i] = P[i - 1] + dv / (np.linalg.norm(dv) + 1e-9) * L
                for i in range(1, m):
                    V[i] = (P[i] - old[i]) / dt
        rec = np.array(rec)                     # n x (m-1)
        if loop:
            rec = np.stack([unpin(rec[:, j]) for j in range(m - 1)], 1)
        elif settle:
            w = sm(n - 1 - settle, n - 1, np.arange(n))[:, None]
            rec = rec * (1 - w)
        for i in range(m - 1):
            res[f"{name}.{i}" if m > 2 else name] = rec[:, i]
    return res


CH = {p["name"]: p["chain"] for p in spec["parts"] if p.get("chain")}
HANG = {
    "beanie": ("head", {"beanie": dict(chain=CH["beanie"], freq=[3.2, 2.7, 2.3], zeta=.28, gain=.9, limit=9)}),
    "strings": ("chest", {"string_l": dict(chain=CH["string_l"], freq=[2.4, 2.1], zeta=.18, gain=1.0, limit=22),
                          "string_r": dict(chain=CH["string_r"], freq=[2.9, 2.5], zeta=.2, gain=1.0, limit=22)}),
    "laces_l": ("shoe_l", {"lace_l_up": dict(chain=CH["lace_l_up"], freq=[3.4, 3.0, 2.7, 2.4], zeta=.25, gain=.55, limit=7),
                           "lace_l_down": dict(chain=CH["lace_l_down"], freq=[2.6, 2.3, 2.1, 1.9, 1.8, 1.7], zeta=.2, gain=.7, limit=9)}),
    "laces_r": ("shoe_r", {"lace_r_left": dict(chain=CH["lace_r_left"], freq=[3.0, 2.6, 2.3, 2.1], zeta=.25, gain=.5, limit=6),
                           "lace_r_right": dict(chain=CH["lace_r_right"], freq=[3.2, 2.8, 2.5, 2.2], zeta=.25, gain=.55, limit=7)}),
    "cuff_l": ("shin_l", {"cuff_l": dict(chain=[JN["cuff_l"], (418, 1250)], freq=[4.5], zeta=.3, gain=.35, limit=4)}),
    "cuff_r": ("shin_r", {"cuff_r": dict(chain=[JN["cuff_r"], (600, 1268)], freq=[4.5], zeta=.3, gain=.35, limit=4)}),
    "hood": ("chest", {"hood": dict(chain=[JN["hood"], (640, 600)], freq=[3.0], zeta=.3, gain=.5, limit=4)}),
}


def gravity(name, i, t, k):
    """lace ends and strings are pulled down a little (they hang), the stiff upturned lace not at all"""
    if name in ("lace_l_down", "string_l", "string_r"):
        return np.array([0.0, -0.0])
    return np.zeros(2)


def hang_all(c, gain=1.0, forces=None):
    allm = [c.fk(f) for f in range(c.n)]
    for key, (holder, chains) in HANG.items():
        res = secondary(c, holder, chains, gain=gain, forces=forces or gravity, mats=[m[holder] for m in allm])
        for bone, vals in res.items():
            c.set(bone, "r", c.get(bone, "r") + vals)


# ============================================================================ the clips
def take(c, at, amp=1.0):
    """a face swap's 'take': the skull squashes a hair and springs back (the new face lands)"""
    k = min(1.0, (c.nk - 3 - at) / 14.0)              # over before the clip ends (it must end exactly at rest)
    sy = 1 - .035 * amp * bump(c.t, at, at + 2 * k, at + 7 * k) + .015 * amp * bump(c.t, at + 5 * k, at + 9 * k, at + 14 * k)
    c.mul("head", "sy", sy)
    c.mul("head", "sx", 2 - sy)


def idle():
    """move, then chill (owner, 2026-11-03: the loop was busy back to back with no time in between). First a short
    groove - four beats (16 design frames each, 0.72 s played): on each he nods into it and comes back up through the
    rest pose, the hips sway across two beats, the right toe taps on beats 1 and 3, a chew on beat 2, a drag on the
    cigar on beat 4 (the ember flares, the cigar tips up) - then ~2 s at the rest pose where he only breathes, slow,
    while the laces and the beanie settle. Never a bob up or down. Loops seamlessly on rest."""
    c = Clip("idle")
    t = c.t
    beat = 16
    ACTIVE = 4 * beat                                                   # design frames of groove, then the chill
    k = np.minimum((t // beat).astype(int), 4)
    u = (t % beat) / beat
    nod_amp = np.array([1.0, .6, .9, .45, 0.0])[k]
    nod = np.sin(np.pi * u ** .75) ** 2 * nod_amp                       # quick down after the beat, slower up
    sway = np.sin(np.pi * t / beat) * sm(0, 6, t) * (1 - sm(36, ACTIVE, t))   # lean one way, then the other; fades out
    breath = np.where(t < ACTIVE, np.sin(np.pi * u) ** 2 * (.6 + .4 * nod_amp) * .7,
                      .45 * np.sin(np.pi * np.clip((t - ACTIVE) / (c.nk - ACTIVE), 0, 1)) ** 2)   # one slow, small breath in the chill
    c.set("pelvis", "x", .05 * sway)
    c.set("pelvis", "r", -.5 * sway)
    c.set("flex_l", "v", 2.0 * np.clip(sway, 0, None))
    c.set("flex_r", "v", 2.0 * np.clip(-sway, 0, None))
    c.set("torso", "r", .9 * sway)
    c.set("chest", "r", .4 * sway)
    c.set("chest", "sy", 1 + .012 * breath)
    c.set("chest", "sx", 1 + .006 * breath)
    c.set("neck", "r", .8 * nod)
    c.set("head", "r", 2.4 * nod + .6 * sway)
    c.set("hood", "r", 0)
    # the drag (beat 4): the cigar tips up between his teeth, the jaw clamps; beat 2: a chew
    drag = bump(t, 49, 54, 63)
    c.set("cigar", "r", -5.5 * drag + 1.5 * bump(t, 18, 22, 29))
    c.set("jaw", "r", 2.2 * bump(t, 18, 21, 25) + 1.6 * bump(t, 23, 26, 31) - .8 * drag)
    for s, sg in (("l", 1), ("r", -1)):
        c.set(f"arm_{s}_upper", "r", sg * .8 * nod)
        c.set(f"arm_{s}_fore", "r", -sg * .6 * nod)
    # toe taps (the shoe rocks on its heel), beats 1 and 3
    tap_r = bump(t, 2, 5, 11, 7.0) + bump(t, 34, 37, 43, 6.0)
    foot_about(c, "r", HEEL["r"], tap_r)
    c.ember = .55 + .45 * drag                     # how hot the ember burns (fx.py)
    c.ember_drag = drag
    follow(c, .35)
    solve_legs(c)
    hang_all(c, .6)
    FACE_OF["idle"] = [(0, "idle")]
    return c


def anticipation():
    """the reels are spinning: he leans in to watch, cool about it - the head tips forward and down a touch, a slow
    chew on the cigar, the cigar bobbing once; feet planted, no rising; then he eases back to rest.
    Face: anticipation, idle at 1.24 s."""
    c = Clip("anticipation")
    t = c.t
    lean = keys(t, [(0, 0), (10, .7), (20, 1.0), (30, .95), (40, .3), (47, 0)])
    c.set("pelvis", "x", -.035 * lean)

    c.set("torso", "r", 1.6 * lean)
    c.set("chest", "r", .8 * lean)
    c.set("neck", "r", 1.4 * lean)
    c.set("head", "r", 3.0 * lean + bump(t, 16, 21, 27, .8))
    c.set("head", "x", -.04 * lean)
    c.set("cigar", "r", keys(t, [(0, 0), (12, -2.5), (22, 1.5), (32, -1), (42, 0), (47, 0)]))
    c.set("jaw", "r", bump(t, 14, 18, 23, 2.2) + bump(t, 22, 25, 30, 1.5))
    for s, sg in (("l", 1), ("r", -1)):
        c.set(f"arm_{s}_upper", "r", sg * .8 * lean)
        c.set(f"arm_{s}_fore", "r", -sg * .6 * lean)
    take(c, 0, .7)
    take(c, 37, .5)
    c.ember = .6 + .1 * lean
    c.ember_drag = 0 * t
    follow(c)
    solve_legs(c)
    hang_all(c)
    FACE_OF["anticipation"] = [(0, "anticipation"), (37, "idle")]
    return c


def win():
    """a win (the game plays it for big wins too): no jumping - he stays planted and cool. The win face lands with a
    take (the grin, the eyes lit), the jaw works round the cigar in a chuckle, he takes a pleased drag (the ember
    flares, a fat puff of smoke rolls up) and nods along to it - three small head bobs, the beanie's tip flopping after
    each - the body all but still; then back to rest. Face: win, idle at 2.04 s."""
    c = Clip("win")
    t = c.t
    beats = (12, 28, 44)
    nod = sum(bump(t, b - 3, b + 1, b + 9, a) for b, a in zip(beats, (1.0, .8, .6)))
    c.set("head", "r", 2.6 * nod + keys(t, [(0, 0), (6, -1.2), (14, 0), (60, 0)]))
    c.set("neck", "r", .8 * nod)
    c.set("chest", "r", .4 * nod)
    c.set("chest", "sy", 1 + .015 * bump(t, 10, 18, 30))              # the drag fills his chest
    c.set("chest", "sx", 1 + .007 * bump(t, 10, 18, 30))

    # the jaw: a chuckle (quick small chatter), then clamps on the drag
    c.set("jaw", "r", 2.4 * bump(t, 3, 5, 8) + 1.8 * bump(t, 7, 9, 12) + 1.4 * bump(t, 30, 32, 35) + 1.0 * bump(t, 34, 36, 40)
          - .6 * bump(t, 12, 16, 24))
    # the cigar tips up proudly with the drag, then settles
    c.set("cigar", "r", keys(t, [(0, 0), (8, -1), (16, -5), (26, -3.5), (40, -1.5), (54, 0), (71, 0)]))
    for s, sg in (("l", 1), ("r", -1)):
        c.set(f"arm_{s}_upper", "r", sg * .5 * nod)
        c.set(f"arm_{s}_fore", "r", -sg * .4 * nod)
    take(c, 0, 1.0)
    take(c, 61, .5)
    drag = bump(t, 10, 16, 26)
    c.ember = .6 + .4 * drag
    c.ember_drag = drag
    follow(c)
    solve_legs(c)
    hang_all(c, 1.0)
    FACE_OF["win"] = [(0, "win"), (61, "idle")]
    return c


def lose():
    """a loss: a long sigh - the chest swells then sags, the head drops and tilts away, the shoulders sink, the cigar
    droops in his teeth, the right shoe scuffs the ground; then he shrugs it off back to rest. Face: lose, idle at 1.64 s."""
    c = Clip("lose")
    t = c.t
    sag = keys(t, [(0, 0), (6, -.25), (14, .2), (30, 1.0), (40, .95), (48, .4), (56, 0), (59, 0)])
    c.set("chest", "sy", 1 + keys(t, [(0, 0), (8, .035), (16, .01), (30, -.03), (44, -.02), (54, 0), (59, 0)]))
    c.set("chest", "sx", 1 + keys(t, [(0, 0), (8, .015), (30, -.01), (54, 0), (59, 0)]))
    # the slump: the knees give a little and the hips sink only as far as that bend takes them (2 px)
    c.set("pelvis", "y", -.02 * np.clip(sag, 0, None))
    c.set("flex_l", "v", 5 * np.clip(sag, 0, None))
    c.set("flex_r", "v", 5 * np.clip(sag, 0, None))
    c.set("torso", "r", -2.5 * sag)
    c.set("chest", "r", -1.0 * sag)
    c.set("neck", "r", 3 * sag)
    c.set("head", "r", 8 * sag + keys(t, [(0, 0), (34, 0), (38, -1.2), (42, .8), (46, 0)]))
    c.set("head", "x", -.03 * sag)
    c.set("cigar", "r", 9 * np.clip(sag, 0, None) + 2 * bump(t, 30, 34, 40))
    c.set("jaw", "r", 3.5 * bump(t, 4, 9, 18) + 2.5 * np.clip(sag, 0, None))
    for s, sg in (("l", 1), ("r", -1)):
        c.set(f"arm_{s}_upper", "r", sg * keys(t, [(0, 0), (8, -1.5), (30, 2.5), (46, 1.5), (56, 0), (59, 0)]))
        c.set(f"arm_{s}_fore", "r", -sg * keys(t, [(0, 0), (30, 2), (46, 1), (56, 0), (59, 0)]))
    # the scuff: the right shoe slides out and back, toe dragging
    sc_ = bump(t, 20, 27, 36)
    c.set("foot_r", "x", .1 * sc_)
    c.set("foot_r", "y", .05 * bump(t, 19, 22, 27) + .03 * bump(t, 28, 31, 36))
    foot_about(c, "r", HEEL["r"], 5 * bump(t, 19, 23, 30))
    take(c, 0, .7)
    take(c, 49, .4)
    c.ember = .5 - .2 * np.clip(sag, 0, 1)
    c.ember_drag = 0 * t
    follow(c, 1.1)
    solve_legs(c)
    hang_all(c)
    FACE_OF["lose"] = [(0, "lose"), (49, "idle")]
    return c


ASH_BREAK = 26          # the frame (from the clip's start) the ash comes off


def ash_break():
    """an idle break: the ash has grown long on the cigar; he eyes it, gives the cigar a sharp flick with his jaw and
    head - the ash breaks off and drops to the ground (fx.py draws it) - watches it fall, then looks back up, pleased.
    Faces: anticipation (eyeing it), win (pleased) from 1.3 s, idle at 2.04 s."""
    c = Clip("ash_break")
    t = c.t
    F = ASH_BREAK
    c.set("head", "r", keys(t, [(0, 0), (12, 2.5), (F - 4, 3.5), (F - 1, -1.5), (F + 2, 2), (F + 9, 6), (F + 16, 5), (F + 24, -1),
                                (F + 30, .8), (F + 38, 0), (71, 0)]))
    c.set("head", "x", keys(t, [(0, 0), (12, -.03), (F + 9, -.05), (F + 24, 0), (71, 0)]))
    c.set("neck", "r", keys(t, [(0, 0), (12, 1), (F + 9, 3), (F + 24, 0), (71, 0)]))
    c.set("torso", "r", keys(t, [(0, 0), (12, .8), (F + 9, 2), (F + 24, -.5), (F + 34, 0), (71, 0)]))
    c.set("cigar", "r", keys(t, [(0, 0), (12, -2), (F - 3, -3), (F - 1, 7), (F + 1, -3), (F + 4, 2), (F + 8, -.8), (F + 12, 0), (71, 0)]))
    c.set("jaw", "r", keys(t, [(0, 0), (F - 4, 0), (F - 2, 3), (F, -.5), (F + 3, 0), (71, 0)]) + 2.5 * bump(t, F + 22, F + 26, F + 31))

    for s, sg in (("l", 1), ("r", -1)):
        c.set(f"arm_{s}_upper", "r", sg * keys(t, [(0, 0), (F + 22, 0), (F + 26, 1.5), (F + 32, 0), (71, 0)]))
    take(c, 0, .5)
    take(c, 39, .7)
    take(c, 61, .4)
    c.ember = .6 + .2 * bump(t, F - 2, F, F + 8)
    c.ember_drag = 0 * t
    follow(c)
    solve_legs(c)
    hang_all(c)
    FACE_OF["ash_break"] = [(0, "anticipation"), (39, "win"), (61, "idle")]
    return c


ENTER_DEPTH = -14.8      # units: how far below his place he starts (the whole figure under the frame's bottom edge)


def enter():
    """the walk-on: he rises up into place from below the frame, stepping as he comes (the feet lift in turn), and slows
    smoothly into place (no overshoot, no bounce); the beanie and laces trail and catch up."""
    c = Clip("enter")
    t = c.t
    u = np.clip(t / 30, 0, 1)                         # one smooth rise, slowing into place: no overshoot, no bounce
    c.set("root", "y", ENTER_DEPTH * (1 - u) ** 3)
    for s, ph in (("l", 0), ("r", 5)):
        c.set(f"foot_{s}", "y", bump(t, 6 + ph, 9 + ph, 13 + ph, .12) + bump(t, 16 + ph, 19 + ph, 23 + ph, .08))
        c.set(f"flex_{s}", "v", bump(t, 6 + ph, 9 + ph, 13 + ph, 12) + bump(t, 16 + ph, 19 + ph, 23 + ph, 9))

    c.set("torso", "r", keys(t, [(0, 0), (8, -1.5), (14, 1.5), (20, -1), (26, .5), (35, 0)]))
    c.set("head", "r", keys(t, [(0, 0), (9, 3), (18, -2), (25, 1.5), (30, -.5), (35, 0)]))
    c.ember = .55 + 0 * t
    c.ember_drag = 0 * t
    follow(c, .6)
    solve_legs(c)
    hang_all(c, .8)
    FACE_OF["enter"] = [(0, "idle")]
    return c


def exit_():
    """the walk-off: he sinks away out of the bottom of the frame, quicker and quicker, the
    beanie lifting off his head a touch as he drops; it ends with him wholly below the frame."""
    c = Clip("exit")
    t = c.t
    u = np.clip(t / 20, 0, 1)                         # one smooth sink, quicker and quicker: no bob first
    c.set("root", "y", (ENTER_DEPTH - .4) * u ** 2.2)
    for s, ph in (("l", 0), ("r", 3)):
        c.set(f"foot_{s}", "y", bump(t, 5 + ph, 8 + ph, 12 + ph, .08))
        c.set(f"flex_{s}", "v", bump(t, 5 + ph, 8 + ph, 12 + ph, 9))
    c.set("torso", "r", keys(t, [(0, 0), (4, -1), (9, 1.5), (14, 1), (20, 0)]))
    c.set("head", "r", keys(t, [(0, 0), (4, -1.5), (10, 2), (20, 3)]))
    c.ember = .55 + 0 * t
    c.ember_drag = 0 * t
    follow(c, .5)
    solve_legs(c)
    hang_all(c, .8)
    FACE_OF["exit"] = [(0, "idle")]
    return c


MAKERS = {"idle": idle, "anticipation": anticipation, "win": win, "lose": lose, "ash_break": ash_break,
          "enter": enter, "exit": exit_}

# ============================================================================ key it all into Blender
if arm.animation_data:
    arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)
RESULT = {}
for name, make in MAKERS.items():
    c = make()
    f0 = c.f0
    act = fxkit.begin_action(arm, f"{SID}_{name}")
    bones_keyed = sorted({b for (b, ch_) in c.ch if b in HEAD})
    # every bone, every channel, keyed on every frame of the clip (the motion is worked out per frame - the legs'
    # solve, the springs - so the keys hold it exactly); a loop's last key repeats its first; the channels a clip does
    # not move are keyed at rest on its first frame (nothing from another clip leaks in)
    for b in HEAD:
        for ch_ in ("x", "y", "r", "sx", "sy"):
            if (b, ch_) not in c.ch:
                fxkit.key(arm, b, f0, **{ch_: 1.0 if ch_ in ("sx", "sy") else 0.0})
    for b in bones_keyed:
        for ch_ in ("x", "y", "r", "sx", "sy"):
            if (b, ch_) not in c.ch:
                continue
            v = c.ch[(b, ch_)]
            series = list(v) + ([v[0]] if c.loop else [])
            for i, val in enumerate(series):
                fxkit.key(arm, b, f0 + i, **{ch_: float(val)})
    for fc in fxkit.fcurves(act):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
        fc.update()
    if c.loop:
        fxkit.make_cyclic(act)
    fxkit.end_action(arm, act, f0)
    # per frame: what fx.py and the packer need - where the ember, the cigar and the shoes are
    mats = [c.fk(f) for f in range(c.n)]
    RESULT[name] = dict(f0=f0, n=c.n, loop=c.loop, mats=mats, ember=np.asarray(c.ember) * np.ones(c.n),
                        drag=np.asarray(c.ember_drag) * np.ones(c.n), clip=c)
    print(f"  {name}: {c.n} frames from {f0}, {len(bones_keyed)} bones keyed", flush=True)

# the faces: one cranium + jaw per face, shown in turn (constant keys on hide_render / hide_viewport)
FACES = sorted({p["face"] for p in spec["parts"] if p.get("face")})
for p in spec["parts"]:
    if not p.get("face"):
        continue
    ob = bpy.data.objects[SID + "_" + p["name"]]
    if ob.animation_data:
        ob.animation_data_clear()
    ob.hide_render = p["face"] != "idle"
    ob.keyframe_insert("hide_render", frame=0)
    for name, (f0, n, loop) in CLIPS.items():
        for fr, face in FACE_OF[name]:                 # (design frames -> output frames)
            ob.hide_render = face != p["face"]
            ob.keyframe_insert("hide_render", frame=f0 + int(round(fr * SLOW)))
        ob.hide_render = p["face"] != "idle"
        ob.keyframe_insert("hide_render", frame=f0 + n)
    for fc in fxkit.fcurves(ob.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"

arm["clips"] = {k: [v[0], v[0] + v[1] - 1] for k, v in CLIPS.items()}
sc.frame_start, sc.frame_end = 1, max(v[0] + v[1] - 1 for v in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], flush=True)
