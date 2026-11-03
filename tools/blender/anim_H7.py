# H7 - the limited drop box - animated in Blender: four Actions on its rig (idle, land, hit, multi) laid one after
# another on the rig's NLA track, and its effects drawn frame by frame in Grease Pencil.
#   the box     keyed by hand, squashing and hopping from its bottom front corner: something alive knocks twice from
#               inside (idle), it thuds down (land), it crouches, jumps and the drop bursts out of it (hit), it
#               rattles as the charge builds and blows open (multi)
#   the flaps   each folds about its own hinge: Blender keys an exact fold for every frame (the hinge stays put, the
#               free edge travels along the flap, the way a flap seen from above folds), on a helper bone per flap -
#               the fold matrix split into turn x scale x turn (R S R) over the helper and the flap's bone. How far
#               each folds is worked out in Blender: a damped spring per flap (its own stiffness, so the four move
#               separately), driven by how the keys throw the box about, plus the kicks from inside
#   the glow    tier 2 neon (fxkit.neon's light), drawn each frame along the silhouette the posed parts make - so the
#               flaps carry their glow as they fold
#   effects     knock marks, dust, the drop: a burst of light out of the box, confetti and stars flung out and
#               tumbling down, a poof; charge crackle, light leaking out of the opening, shock rings
# Runs INSIDE Blender, after build_symbol_scene.py (tools/blender/run.py runs both in a background Blender).
import bpy, importlib, math, os, random, sys
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
import fxkit
importlib.reload(fxkit)
from fxkit import (rest, px, smooth, gp_object, gp_mat, gp_layer, ride, stroke, star, Board, LIME, VIOLET, WHITE, GOLD, PINK)

SID = "H7"
sc, arm, spec = fxkit.setup(SID)
FPS = sc.render.fps
ART, FXB, FX = fxkit.layers(sc, SID)
fxkit.glow_compositor(sc, SID, back=dict(strength=1.0, size=.55, gain=1.6), front=dict(strength=.9, size=.42, gain=1.5))
if arm.animation_data:
    arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)

PARTS = [p["name"] for p in spec["parts"]]
FLAPS = ["flap_fl", "flap_r", "flap_bl", "flap_br"]
CLIPS = {"idle": (1, 72), "land": (101, 124), "hit": (201, 252), "multi": (301, 348)}
arm["clips"] = {k: list(v) for k, v in CLIPS.items()}
OPENING = (560, 330)         # the middle of the box's open top (icon px)
FEET = [(150, 790), (580, 870), (830, 790)]                      # the box's bottom corners
sys.path.insert(0, os.path.join(HERE, "cuts"))
import importlib.util as _iu
_spec = _iu.spec_from_file_location("cut_H7", os.path.join(HERE, "cuts", "H7.py"))
CUT = _iu.module_from_spec(_spec); _spec.loader.exec_module(CUT)
HINGES = {"flap_fl": (CUT.FL_HINGE, CUT.FL_TIP), "flap_r": (CUT.R_HINGE, CUT.R_TIP),
          "flap_bl": (CUT.BL_HINGE, CUT.BL_TIP), "flap_br": (CUT.BR_HINGE, CUT.BR_TIP)}


# ------------------------------------------------------------------ the rig: a helper bone over each flap
def helpers():
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    for f in FLAPS:
        hinge, tip = HINGES[f]
        head = fxkit.vec(*CUT.mid(hinge))
        b = eb.get(f + "_h") or eb.new(f + "_h")
        b.head, b.tail, b.roll = head, head + Vector((0, 0, .6)), 0
        b.parent = eb["body"]
        eb[f + ".0"].parent = b
    bpy.ops.object.mode_set(mode="OBJECT")
    for f in FLAPS:
        arm.pose.bones[f + "_h"].rotation_mode = "XYZ"


helpers()
BONES = ["body"] + [f + "_h" for f in FLAPS] + [f + ".0" for f in FLAPS]
CH = {"x": ("location", 0), "y": ("location", 1), "r": ("rotation_euler", 2), "sx": ("scale", 0), "sy": ("scale", 1)}


def k1(bone, f, **chans):
    """Key single channels of a bone (x / y units, r degrees, sx / sy; s = both): only those F-curves get a key."""
    if "s" in chans:
        s = chans.pop("s"); chans["sx"] = chans["sy"] = s
    pb = arm.pose.bones[bone]
    for ch, v in chans.items():
        path, i = CH[ch]
        getattr(pb, path)[i] = math.radians(v) if ch == "r" else v
        pb.keyframe_insert(path, index=i, frame=f, group=bone)


def keys(bone, ch, pairs):
    for f, v in pairs:
        k1(bone, f, **{ch: v})


def hard(act, bone, ch, f):
    path, i = CH[ch]
    fxkit.hard(act, bone, path, i, f)


def box(rows):
    """Key the box: (frame, y, sx, sy, r)."""
    for f, y, sx, sy, r in rows:
        k1("body", f, y=y, sx=sx, sy=sy, r=r)


# ------------------------------------------------------------------ the fold
def fold_matrix(flap, s, rho=0.0):
    """The fold of a flap as a 2x2 matrix in the picture (x right, z up) about its hinge's middle: the hinge line
    stays, the free edge moves along the flap (middle of hinge -> middle of free edge) to s of its length; then a
    turn of rho degrees about the hinge's middle."""
    hinge, tip = HINGES[flap]
    a, b = fxkit.vec(*hinge[0]), fxkit.vec(*hinge[1])
    h = Vector((b.x - a.x, b.z - a.z)).normalized()
    n = Vector((-h.y, h.x))
    m0, t0 = fxkit.vec(*CUT.mid(hinge)), fxkit.vec(*CUT.mid(tip))
    v = Vector((t0.x - m0.x, t0.z - m0.z))
    k = (s - 1) / n.dot(v)
    A = [[1 + k * v.x * n.x, k * v.x * n.y], [k * v.y * n.x, 1 + k * v.y * n.y]]
    c, si = math.cos(math.radians(rho)), math.sin(math.radians(rho))
    return [[c * A[0][0] - si * A[1][0], c * A[0][1] - si * A[1][1]], [si * A[0][0] + c * A[1][0], si * A[0][1] + c * A[1][1]]]


def rsr(A):
    """A 2x2 matrix (det > 0) as turn(t1) x scale(s1, s2) x turn(t2) - the helper bone turns and scales, the flap's
    bone turns. Degrees."""
    a, b, c, d = A[0][0], A[0][1], A[1][0], A[1][1]
    if abs(b) < 1e-9 and abs(c) < 1e-9 and abs(a - 1) < 1e-9 and abs(d - 1) < 1e-9:
        return 0.0, 1.0, 1.0, 0.0
    # SVD of a 2x2 (closed form)
    E, F = (a + d) / 2, (a - d) / 2
    G, Hh = (c + b) / 2, (c - b) / 2
    Q, R = math.hypot(E, Hh), math.hypot(F, G)
    s1, s2 = Q + R, Q - R
    a1, a2 = math.atan2(G, F), math.atan2(Hh, E)
    t2 = (a2 - a1) / 2
    t1 = (a2 + a1) / 2
    return math.degrees(t1), s1, s2, math.degrees(t2)


def key_fold(flap, f, s, rho=0.0):
    t1, s1, s2, t2 = rsr(fold_matrix(flap, s, rho))
    k1(flap + "_h", f, r=t1, sx=s1, sy=s2)
    k1(flap + ".0", f, r=t2)


SPRING = {   # per flap: stiffness (Hz), damping, how hard the box's moves throw it, its fold range
    "flap_fl": dict(hz=2.5, zeta=.16, k=.0105, lo=.5, hi=1.36, rho=1.6),
    "flap_r": dict(hz=3.0, zeta=.19, k=.0095, lo=.5, hi=1.34, rho=-1.4),
    "flap_bl": dict(hz=3.5, zeta=.24, k=.0042, lo=.86, hi=1.12, rho=-.8),
    "flap_br": dict(hz=3.2, zeta=.21, k=.0048, lo=.86, hi=1.12, rho=.9),
}


def flaps(f0, f1, loop=False, kicks=(), shake=None, settle=8):
    """How far each flap folds, worked out from how this clip moves the box: each fold is a damped spring (s = 1 at
    rest) the box's vertical acceleration at its hinge throws about (a box shooting up leaves its flaps behind:
    they fold down; stopping dead flings them up), plus kicks from inside [(frame, push per flap {flap: units/s2},
    frames)] and shake(flap, f) (a rattle). Keyed as an exact fold on every frame."""
    pb = arm.pose.bones["body"]
    rest_inv = pb.bone.matrix_local.inverted()
    n = f1 - f0 + 1
    out = {}
    for flap, cfg in SPRING.items():
        m0 = fxkit.vec(*CUT.mid(HINGES[flap][0]))
        zs = []
        for f in range(f0, f1 + 1):
            sc.frame_set(f)
            zs.append(((arm.matrix_world @ pb.matrix @ rest_inv) @ m0).z)
        om = 2 * math.pi * cfg["hz"]
        z, sub = cfg["zeta"], 8
        dt = 1 / (FPS * sub)
        phi, vel = 0.0, 0.0
        rec = []
        for lap in range(3 if loop else 1):
            rec = []
            for kf in range(n):
                rec.append(phi)
                k2 = (kf + 1) % n if loop else min(kf + 1, n - 1)
                km = (kf - 1) % n if loop else max(kf - 1, 0)
                acc = (zs[k2] - 2 * zs[kf] + zs[km]) * FPS * FPS
                push = sum(p.get(flap, 0) for fk, p, d in kicks if fk <= f0 + kf < fk + d)
                if shake:
                    push += shake(flap, f0 + kf)
                for s_ in range(sub):
                    a = -om * om * phi - 2 * z * om * vel - cfg["k"] * acc * om + push
                    vel += a * dt
                    phi += vel * dt
                    lo, hi = cfg["lo"] - 1, cfg["hi"] - 1
                    if phi < lo:
                        phi, vel = lo, abs(vel) * .3
                    if phi > hi:
                        phi, vel = hi, -abs(vel) * .3
            out[flap] = rec
        if not loop and settle:
            for j in range(settle):
                t = (j + 1) / settle
                rec[n - settle + j] *= 1 - t * t * (3 - 2 * t)
        else:                                           # a loop starts exactly at rest: the rest of it eased out
            r0 = rec[0]
            rec = [p - r0 * (.5 + .5 * math.cos(2 * math.pi * kf / n)) for kf, p in enumerate(rec)]
        out[flap] = rec
        for kf, p in enumerate(rec + ([rec[0]] if loop else [])):
            key_fold(flap, f0 + kf, 1 + p, cfg["rho"] * p / max(1e-6, cfg["hi"] - 1))
        print(f"  {f0}-{f1} {flap}: fold {1 + min(rec):.2f}..{1 + max(rec):.2f}")
    return out



# ================================================================== idle: something alive knocks twice from inside
f0, f1 = CLIPS["idle"]
act = fxkit.begin_action(arm, SID + "_idle")
rest(arm, BONES, f0)
box([(10, 0, 1, 1, 0), (12, -.006, 1.014, .976, 0), (17, .05, .99, 1.022, -.4), (21, 0, 1.009, .986, .15), (24, 0, .997, 1.006, 0), (29, 0, 1, 1, 0),
     (40, 0, 1, 1, 0), (42, -.004, 1.009, .985, 0), (47, .03, .994, 1.014, .3), (51, 0, 1.005, .992, -.08), (55, 0, 1, 1.002, 0), (73, 0, 1, 1, 0)])
hard(act, "body", "y", 21); hard(act, "body", "y", 51)
KN = [(11, {"flap_fl": 60, "flap_r": 52, "flap_bl": 70, "flap_br": 64}, 2), (41, {"flap_fl": 36, "flap_r": 40, "flap_bl": 44, "flap_br": 40}, 2)]
flaps(f0, f1, loop=True, kicks=KN)
fxkit.make_cyclic(act)
fxkit.end_action(arm, act, f0)

# ================================================================== land: it thuds down, the flaps flop
f0, f1 = CLIPS["land"]
act = fxkit.begin_action(arm, SID + "_land")
rest(arm, BONES, f0)
box([(103, -.02, 1.05, .9, 0), (107, .06, .98, 1.04, .3), (111, 0, 1.012, .984, -.15), (115, 0, .997, 1.006, 0), (124, 0, 1, 1, 0)])
for ch in ("y", "sx", "sy"):
    hard(act, "body", ch, 103)
hard(act, "body", "y", 111)
flaps(f0, f1)
fxkit.end_action(arm, act, f0)

# ================================================================== hit: the drop - crouch, jump, it bursts open
f0, f1 = CLIPS["hit"]
BURST = 209
act = fxkit.begin_action(arm, SID + "_hit")
rest(arm, BONES, f0)
box([(205, -.025, 1.05, .9, -1.0), (207, -.03, 1.06, .88, -1.2), (210, .58, .95, 1.09, 2.0), (214, .86, 1.0, 1.02, -.8), (217, .78, 1, 1, -.4),
     (221, 0, 1.06, .89, 0), (225, .12, .985, 1.035, .5), (228, 0, 1.012, .978, -.2), (233, 0, .997, 1.006, 0), (240, 0, 1, 1, 0), (252, 0, 1, 1, 0)])
for ch in ("y", "sx", "sy", "r"):
    hard(act, "body", ch, 221)
hard(act, "body", "y", 228)
flaps(f0, f1, kicks=[(BURST, {"flap_fl": 230, "flap_r": 215, "flap_bl": 150, "flap_br": 165}, 3)])
fxkit.end_action(arm, act, f0)

# ================================================================== multi: it rattles as the charge builds, then blows open
f0, f1 = CLIPS["multi"]
PUL = (307, 313, 319)
REL = 327
act = fxkit.begin_action(arm, SID + "_multi")
rest(arm, BONES, f0)
box([(305, 0, 1, 1, 0), (307, .02, 1.035, 1.035, 0), (310, 0, 1, 1, 0), (313, .025, 1.045, 1.045, 0), (316, 0, 1, 1, 0), (319, .03, 1.055, 1.055, 0),
     (322, 0, 1.01, .99, 0), (325, -.03, 1.05, .91, 0), (327, -.035, 1.06, .9, 0), (330, .32, .95, 1.1, 0), (334, .38, 1.0, 1.02, 0),
     (338, 0, 1.05, .91, 0), (341, .05, .985, 1.03, 0), (344, 0, 1.005, .995, 0), (348, 0, 1, 1, 0)])
for i, f in enumerate(range(303, 327)):              # it rattles harder and harder
    a = (.006 + .014 * (f - 303) / 24) * (1 if i % 2 else -1)
    k1("body", f, x=a, r=a * 30)
k1("body", 327, x=0, r=0); k1("body", 348, x=0, r=0)
for ch in ("y", "sx", "sy"):
    hard(act, "body", ch, 338)


PHASE = {"flap_fl": 0, "flap_r": 1, "flap_bl": 1, "flap_br": 0}


def rattle(flap, f):
    if 304 <= f < 327:
        return (40 + 120 * (f - 304) / 23) * (1 if (f + PHASE[flap]) % 2 else -1)
    return 0.0


flaps(f0, f1, kicks=[(REL, {"flap_fl": 260, "flap_r": 250, "flap_bl": 170, "flap_br": 180}, 3)] +
      [(p, {"flap_fl": 70, "flap_r": 64, "flap_bl": 52, "flap_br": 56}, 2) for p in PUL], shake=rattle)
fxkit.end_action(arm, act, f0)


# ------------------------------------------------------------------ the tier glow, following the posed silhouette
# fxkit.neon rides one bone; here several parts move against each other, so the glow is drawn each frame along the
# silhouette the posed parts actually make (the same light as fxkit.neon: the halo colour in stacked bands just
# behind the sticker's edge, comets running round it, the charge colour flooding in) - no glow is left in the air
# where a part has moved away, and none is missing where it has moved to.
def silhouettes(names, frames, cell=3.0, grow=9.0):
    """{frame: closed loop of world (x, z) points}, `grow` icon px outside the union of the named parts as they are
    posed at that frame. Each part's opaque pixels (every `cell` px of its image) ride its evaluated mesh (a bone's
    plane, or a chain's bent grid), are splatted onto a grid of `cell` px, grown, and the outer edge is traced."""
    import numpy as np
    dg = bpy.context.evaluated_depsgraph_get()
    samples = []
    for name in names:
        ob = bpy.data.objects[SID + "_" + name]
        img = ob.data.materials[0].node_tree.nodes["Image Texture"].image if "Image Texture" in ob.data.materials[0].node_tree.nodes else None
        if img is None:
            img = next(n.image for n in ob.data.materials[0].node_tree.nodes if n.type == "TEX_IMAGE")
        w, h = img.size
        px_ = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(px_)
        al = px_.reshape(h, w, 4)[::-1, :, 3]                 # top row first
        step = max(1, int(round(cell)))
        ys, xs = np.nonzero(al[::step, ::step] > .5)
        u = (xs * step + .5) / w
        v = (ys * step + .5) / h                              # down from the top
        me = ob.data
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        z0 = co[0, 2]
        nx = int(np.sum(np.abs(co[:, 2] - z0) < 1e-6)) - 1   # the grid's columns (a plane: 1)
        ny = len(co) // (nx + 1) - 1
        if len(co) == 4:                                      # a plane: corners bottom-left, bottom-right, top-right, top-left
            kind = "plane"
            ij = None
        else:
            kind = "grid"
            fi, fj = u * nx, v * ny
            i0 = np.clip(np.floor(fi).astype(int), 0, nx - 1); j0 = np.clip(np.floor(fj).astype(int), 0, ny - 1)
            ij = (i0, j0, fi - i0, fj - j0, nx)
        samples.append((ob, kind, u, v, ij))
    N = int(1300 / cell) + 8
    off = 6.5 + 4 * cell / 100
    r_close = 1
    r_grow = int(round(grow / cell))
    disk = [(dy, dx) for dy in range(-r_grow - r_close, r_grow + r_close + 1) for dx in range(-r_grow - r_close, r_grow + r_close + 1)
            if dx * dx + dy * dy <= (r_grow + r_close + .3) ** 2]
    out = {}
    for f in frames:
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        pts = []
        for ob, kind, u, v, ij in samples:
            oe = ob.evaluated_get(dg)
            me = oe.to_mesh()
            co = np.empty(len(me.vertices) * 3, np.float32)
            me.vertices.foreach_get("co", co)
            oe.to_mesh_clear()
            co = co.reshape(-1, 3)
            M = np.array(ob.matrix_world, np.float32)
            wco = co @ M[:3, :3].T + M[:3, 3]
            if kind == "plane":
                bl, br, tl = wco[0], wco[1], wco[3]
                p = bl[None] + u[:, None] * (br - bl)[None] + (1 - v)[:, None] * (tl - bl)[None]
            else:
                i0, j0, a, b, nx = ij
                g = wco.reshape(-1, nx + 1, 3)
                p = (g[j0, i0] * ((1 - a) * (1 - b))[:, None] + g[j0, i0 + 1] * (a * (1 - b))[:, None]
                     + g[j0 + 1, i0] * ((1 - a) * b)[:, None] + g[j0 + 1, i0 + 1] * (a * b)[:, None])
            pts.append(p[:, [0, 2]])
        P = np.concatenate(pts)
        gx = np.clip(((P[:, 0] + off) * 100 / cell).astype(int), 0, N - 1)
        gz = np.clip(((off - P[:, 1]) * 100 / cell).astype(int), 0, N - 1)
        m = np.zeros((N, N), bool)
        m[gz, gx] = True
        grown = np.zeros_like(m)
        for dy, dx in disk:                                  # closed and grown in one pass (a disk of the grow radius)
            grown[max(0, dy):N + min(0, dy), max(0, dx):N + min(0, dx)] |= m[max(0, -dy):N - max(0, dy), max(0, -dx):N - max(0, dx)]
        out[f] = trace(grown, cell, off)
    return out


def trace(m, cell, off):
    """The outer edge of a grid mask as a smooth closed loop of world points (CCW), starting straight under its
    middle (so the comets' positions round it stay put as the shape moves)."""
    import numpy as np
    H, W = m.shape
    pad = np.zeros((H + 2, W + 2), bool); pad[1:-1, 1:-1] = m
    ys, xs = np.nonzero(pad)
    start = (ys.min(), xs[ys == ys.min()].min())
    nb = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
    path, cur, back = [start], start, 6
    for _ in range(200000):
        for k in range(8):
            d = (back + 1 + k) % 8
            ny_, nx_ = cur[0] + nb[d][0], cur[1] + nb[d][1]
            if pad[ny_, nx_]:
                back = (d + 4) % 8
                cur = (ny_, nx_)
                break
        if cur == start:
            break
        path.append(cur)
    pts = [((x - 1 + .5) * cell / 100 - off, off - (y - 1 + .5) * cell / 100) for y, x in path]
    # smooth the stair-steps: a circular moving average, then even spacing
    n = len(pts)
    k = 3
    sm = [(sum(pts[(i + j) % n][0] for j in range(-k, k + 1)) / (2 * k + 1),
           sum(pts[(i + j) % n][1] for j in range(-k, k + 1)) / (2 * k + 1)) for i in range(n)]
    area = sum(sm[i][0] * sm[(i + 1) % n][1] - sm[(i + 1) % n][0] * sm[i][1] for i in range(n))
    if area < 0:
        sm = sm[::-1]
    loop = fxkit.resample(sm, 180)
    cx = sum(p[0] for p in loop) / len(loop); cz = sum(p[1] for p in loop) / len(loop)
    below = [i for i, p in enumerate(loop) if p[1] < cz]
    i0 = min(below, key=lambda i: abs(loop[i][0] - cx)) if below else 0
    return loop[i0:] + loop[:i0]


def neon_live(names, clips, tier=2, land_at=None, hit_span=None, pulses=None, charge_span=None, extra=None):
    """The tier glow (art/STYLE.md), as fxkit.neon draws it, along the posed silhouette of `names` each frame.
    extra(f) -> (level, charge, crackle) adds to the clip's own (an effect that should light the glow)."""
    g = fxkit.TIER_GLOW[tier]
    frames = sorted({f for a, b in clips.values() for f in range(a, b + 1)})
    loops = silhouettes(names, frames)
    rim = gp_object(FXB, SID + "_rim", depth=.3)
    m_halo = gp_mat(rim, f"glow_halo_{tier}", g["halo"])
    m_charge = gp_mat(rim, f"glow_charge_{tier}", g["charge"])
    m_comet = gp_mat(rim, f"glow_comet_{tier}", g["comet"])
    m_hot = gp_mat(rim, "glow_white", WHITE)
    aura, runs = Board(), Board()
    L0 = g["level"]

    def aura_at(f, level, charge=0.0, crackle=0.0):
        loop = loops[f]
        e0 = fxkit.offset(loop, -.08)
        e = fxkit.jitter(e0, crackle * .5, f) if crackle else e0
        grow_ = .85 + .15 * min(level, 2)
        lv = level * L0

        def fn(dr):
            for r, a in ((.38, .08), (.29, .09), (.21, .10), (.14, .12)):
                stroke(dr, e, r * grow_, opacity=min(1, a * lv * (1 - .6 * charge)), mat=m_halo, cyclic=True)
            if charge > .02:
                for r, a in ((.2, .10), (.13, .14), (.085, .18)):
                    stroke(dr, e, r * grow_, opacity=min(1, a * charge * lv), mat=m_charge, cyclic=True)
            if crackle:
                stroke(dr, fxkit.jitter(loop, crackle * 1.6, f + 5), .014, opacity=min(1, .8 * lv), mat=m_hot, cyclic=True)
        aura.add(f, fn)

    def comet(f, head, length, level=1.0, backward=False):
        loop = loops[f]
        p = fxkit.arc(loop, head if backward else head - length, length)
        if backward:
            p = p[::-1]
        m = len(p)
        tail = [min(1.0, (j / max(1, m - 1)) ** 1.6 * 1.3) for j in range(m)]
        lv = level * (.85 + .15 * L0)

        def fn(dr):
            stroke(dr, p, 0, radii=fxkit.taper(m, .075 * lv, ends=.18), opacities=[.35 * t for t in tail], mat=m_comet)
            stroke(dr, p, 0, radii=fxkit.taper(m, .045 * lv, ends=.18), opacities=[.8 * t for t in tail], mat=m_comet)
            stroke(dr, p, 0, radii=fxkit.taper(m, .018 * lv, ends=.18), opacities=tail, mat=m_hot)
        runs.add(f, fn)

    def plus(f, lv, ch, cr):
        if extra:
            a, b, c = extra(f)
            return lv + a, min(1.0, ch + b), cr + c
        return lv, ch, cr
    if "idle" in clips:                              # it breathes; two comets chase round once a loop
        f0, f1 = clips["idle"]
        n = f1 - f0 + 1
        for f in range(f0, f1 + 1):
            t = (f - f0) / n
            aura_at(f, *plus(f, .9 + .2 * math.sin(2 * math.pi * t), 0.0, 0.0))
            comet(f, t, .14)
            comet(f, t + .5, .1, level=.75)
    if "land" in clips:                              # it flares with the landing, light runs up both sides
        f0, f1 = clips["land"]
        la = land_at or f0 + 2
        for f in range(f0, f1 + 1):
            hit = math.exp(-max(0, f - la) / 3.5) if f >= la else (f - f0) / max(1, la - f0)
            aura_at(f, *plus(f, 1 + 1.4 * hit, .7 * hit, 0.0))
            if la <= f <= la + 11:
                u = (f - la) / 11
                comet(f, .5 * u, .12 * (1 - u) + .04, level=1.3 - .5 * u)
                comet(f, -.5 * u, .12 * (1 - u) + .04, level=1.3 - .5 * u, backward=True)
    if "hit" in clips:                               # it burns bright, three comets race round
        f0, f1 = clips["hit"]
        a, b = hit_span or (f0 + 4, f1 - 6)
        for f in range(f0, f1 + 1):
            lv = 1 + .6 * smooth(f0, a + 4, f) - .6 * smooth(b - 8, f1, f)
            aura_at(f, *plus(f, lv, .5 * (lv - 1) / .6, 0.0))
            if a <= f <= b:
                for j in range(3):
                    comet(f, (f - a) / 14 + j / 3, .1, level=1.2)
    if "multi" in clips:                             # it pulses with each swell, crackling between
        f0, f1 = clips["multi"]
        ps = pulses or [f0 + (f1 - f0) * k // 5 for k in (1, 2, 3)]
        c0, c1 = charge_span or (ps[0] - 4, ps[-1] + 2)
        for f in range(f0, f1 + 1):
            pulse = sum(math.exp(-((f - p) / 2.2) ** 2) for p in ps)
            charged = smooth(c0, c0 + 4, f) * (1 - smooth(c1 - 1, c1 + 4, f))
            aura_at(f, *plus(f, 1 + 1.2 * pulse + .3 * charged, min(1, pulse + .3 * charged), .03 * charged))
            if charged > .1:
                for j in range(4):
                    comet(f, (f - c0) / 10 + j / 4, .07, level=1.1, backward=j % 2 == 1)
    aura.draw(gp_layer(rim, "aura"))
    runs.draw(gp_layer(rim, "comets"))
    return rim


# ================================================================== the tier glow, along the box and its flaps as they fold
neon_live(PARTS, CLIPS, tier=2, land_at=103, hit_span=(209, 242), pulses=PUL, charge_span=(304, 327))


# ================================================================== effects
def at(f, x, y, bone="body"):
    """Where icon point (x, y) on a part is at frame f (world x, z)."""
    sc.frame_set(f)
    pb = arm.pose.bones[bone]
    p = arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted() @ fxkit.vec(x, y)
    return p.x, p.z


fxw = gp_object(FX, SID + "_fx", depth=-.8)            # stays where the frame is
fxb_ = gp_object(FX, SID + "_fx_box", depth=-.8)       # rides the box
ride(fxb_, arm, "body")
back = gp_object(FXB, SID + "_back", depth=.35)        # behind the box, bloomed
inside = gp_object(ART, SID + "_out", depth=-.55)      # what comes out of the box: in front of the back flaps and
ride(inside, arm, "body")                              # the inside, behind the front flaps
w_white = gp_mat(fxw, "fx_white_line", WHITE); w_pink = gp_mat(fxw, "fx_pink_line", PINK); w_lime = gp_mat(fxw, "fx_lime_line", LIME)
w_spark = gp_mat(fxw, "fx_white_fill", WHITE, fill=WHITE); w_gold = gp_mat(fxw, "fx_gold_fill", GOLD, fill=GOLD)
x_white = gp_mat(fxb_, "fx_white_line", WHITE); x_spark = gp_mat(fxb_, "fx_white_fill", WHITE, fill=WHITE)
x_pinkf = gp_mat(fxb_, "fx_pink_fill", PINK, fill=PINK)
b_violet = gp_mat(back, "glow_violet", VIOLET); b_pink = gp_mat(back, "glow_pink", PINK); b_white = gp_mat(back, "glow_white", WHITE)
b_goldf = gp_mat(back, "glow_gold_fill", GOLD, fill=GOLD); b_whitef = gp_mat(back, "glow_white_fill", WHITE, fill=WHITE)
b_pinkf = gp_mat(back, "glow_pink_fill", PINK, fill=PINK)
CONF = [gp_mat(inside, "conf_" + n, c, fill=c) for n, c in (("lime", LIME), ("violet", VIOLET), ("pink", PINK), ("gold", GOLD), ("white", WHITE))]
i_ray = gp_mat(inside, "ray_gold", GOLD, fill=(1.0, .9, .45, 1)); i_rayw = gp_mat(inside, "ray_white", WHITE, fill=WHITE)
i_puff = gp_mat(inside, "poof", (.55, .53, .58, 1), fill=(.96, .95, .97, 1))
world, onbox, behind, out = Board(), Board(), Board(), Board()
ox, oz = px(*OPENING)


def knock(board, f0, pts, mat):
    """Cartoon knock marks: little bows popping out from the box where it is hit from inside."""
    for k in range(6):
        t = k / 5
        for (x, y), ang in pts:
            cx, cz = px(x, y)
            a = math.radians(ang)
            r = .18 + .3 * t
            arcp = [(cx + math.cos(a + d) * r, cz + math.sin(a + d) * r) for d in (-.5, -.25, 0, .25, .5)]
            board.add(f0 + k, lambda dr, arcp=arcp, t=t: stroke(dr, arcp, 0, radii=fxkit.taper(5, .03 * (1 - t) + .006, ends=.4), mat=mat))


def ticks(board, f0, x, z, mat, spread=1.0):
    for k in range(6):
        t = k / 5
        for side in (-1, 1):
            for j in range(2):
                ang = math.radians(170 - 30 * j) if side < 0 else math.radians(10 + 30 * j)
                r0, r1 = (.35 + .55 * t) * spread, (.62 + .9 * t) * spread
                board.add(f0 + k, lambda dr, ang=ang, r0=r0, r1=r1, t=t: stroke(
                    dr, [(x + math.cos(ang) * r0, z + math.sin(ang) * r0 * .55), (x + math.cos(ang) * r1, z + math.sin(ang) * r1 * .55)],
                    .028 * (1 - t) + .007, mat=mat))


def rays(board, f0, life, n, seed, spread=(25, 155), length=(1.6, 5.2), mats=(i_ray, i_rayw)):
    """Light shooting up out of the opening: thin wedges fanning out, growing, then thinning to needles."""
    rnd = random.Random(seed)
    for i in range(n):
        a = math.radians(spread[0] + (spread[1] - spread[0]) * (i + rnd.uniform(-.3, .3)) / (n - 1))
        L1 = rnd.uniform(*length)
        mat = mats[i % len(mats)]
        for k in range(life):
            t = k / (life - 1)
            L = L1 * (1 - (1 - t) ** 2.2)
            w = .16 * math.sin(math.pi * min(1, t * 1.15)) ** .8 + .002
            dx, dz = math.cos(a), math.sin(a)
            p0 = (ox + dx * .3, oz + dz * .3)
            pts = [p0, (ox + dx * L - dz * w, oz + dz * L + dx * w), (ox + dx * (L + .2), oz + dz * (L + .2)), (ox + dx * L + dz * w, oz + dz * L - dx * w)]
            board.add(f0 + k, lambda dr, pts=pts, mat=mat: stroke(dr, pts, .003, mat=mat, cyclic=True, fill=True, line=False))


def confetti(board, f0, n, seed, speed=(5.5, 9.5), spread=(55, 125), life=(26, 36), g=17.0):
    """Confetti flung out of the box: little paper rectangles tumbling (they turn and flip edge-on as they fall),
    shrinking away at the end of their fall."""
    rnd = random.Random(seed)
    for i in range(n):
        a = math.radians(rnd.uniform(*spread))
        sp = rnd.uniform(*speed)
        vx, vz = math.cos(a) * sp, math.sin(a) * sp
        lf = rnd.randint(*life)
        th0, om = rnd.uniform(0, 6.28), rnd.uniform(-14, 14)
        fl0, flo = rnd.uniform(0, 6.28), rnd.uniform(9, 18)
        w, h = rnd.uniform(.07, .1), rnd.uniform(.035, .05)
        mat = CONF[i % len(CONF)]
        st = f0 + rnd.randint(0, 3)
        for k in range(lf):
            t = k / FPS
            drag = math.exp(-1.4 * t)
            x = ox + vx * (1 - drag) / 1.4 + rnd.uniform(-.004, .004)
            z = oz + .1 + vz * (1 - drag) / 1.4 - .5 * g * t * t * .55
            sc_ = min(1, (k + 1) / 3) * (1 - smooth(lf - 6, lf - 1, k))
            if sc_ < .05:
                continue
            th = th0 + om * t
            fw = w * max(.12, abs(math.cos(fl0 + flo * t))) * sc_
            fh = h * sc_
            c, s_ = math.cos(th), math.sin(th)
            pts = [(x + c * dx_ - s_ * dz_, z + s_ * dx_ + c * dz_) for dx_, dz_ in ((-fw, -fh), (fw, -fh), (fw, fh), (-fw, fh))]
            board.add(st + k, lambda dr, pts=pts, mat=mat: stroke(dr, pts, .003, mat=mat, cyclic=True, fill=True, line=False))


def stars(board, f0, n, seed, mat, speed=(4.5, 7.5)):
    rnd = random.Random(seed)
    for i in range(n):
        a = math.radians(rnd.uniform(40, 140))
        sp = rnd.uniform(*speed)
        vx, vz = math.cos(a) * sp, math.sin(a) * sp
        lf = rnd.randint(16, 22)
        spin = rnd.uniform(-9, 9)
        r = rnd.uniform(.16, .24)
        for k in range(lf):
            t = k / FPS
            drag = math.exp(-2.2 * t)
            x, z = ox + vx * (1 - drag) / 2.2, oz + .2 + vz * (1 - drag) / 2.2
            rr = r * math.sin(math.pi * min(1, (k + 1) / lf * 1.05)) ** .5
            board.add(f0 + 1 + k, lambda dr, x=x, z=z, rr=rr, t=t: stroke(dr, star(x, z, rr, spin * t, points=5, inner=.45), .003,
                                                                       mat=mat, cyclic=True, fill=True, line=False))


def poof(board, f0, life, scale, seed):
    for j, (dx, dz, s) in enumerate(((-.5, .1, .8), (.45, .15, .75), (0, .35, 1.0), (-.2, -.05, .6), (.3, -.1, .65))):
        fxkit.dust(board, f0 + j % 2, life - j % 3, ox + dx * scale, oz + dz * scale, s * scale * .55, i_puff,
                   drift=(dx * .8, .6 * scale), seed=seed + j, lobes=6)


# idle: knock marks where it is hit from inside, a glint on the tag
knock(onbox, 11, [((330, 470), 160), ((720, 470), 20), ((560, 260), 90)], x_white)
knock(onbox, 41, [((300, 620), 170), ((820, 560), 10)], x_white)
fxkit.sparkle(onbox, 58, 9, *px(250, 560), .34, x_spark)

# land: ticks and dust at its feet
for x, y in FEET:
    ticks(world, 102, *px(x, y + 10), w_white, spread=.8)

# hit: the drop bursts out - light, a poof, confetti and stars - and the box lands
rays(out, BURST, 14, 9, 3)
poof(out, BURST, 12, 1.0, 11)
confetti(out, BURST, 30, 5)
stars(out, BURST, 6, 9, i_ray)
fxkit.starburst(behind, BURST + 1, 11, ox, oz + .6, 3.2, 6.4, b_goldf, b_whitef, points=12)
rnd = random.Random(14)
for i in range(7):
    fxkit.sparkle(world, BURST + 4 + rnd.randint(0, 14), rnd.randint(6, 9), rnd.uniform(-4.8, 4.8), rnd.uniform(-1, 5.8), rnd.uniform(.24, .44),
                  w_gold if i % 3 == 0 else w_spark, rot0=rnd.uniform(0, 1))
for x, y in FEET:
    ticks(world, 221, *px(x, y + 10), w_white)

# multi: crackling with the charge, light leaking out of the top with each jolt, then it blows open
fxkit.lightning(world, 305, 326, ox, oz - 1.2, (3.6, 3.0), (5.4, 4.6), (w_pink, w_white, w_white), per=3, step=2, seed=5)
HOLE = [px(x, y) for x, y in ((400, 298), (490, 333), (534, 420), (576, 505), (638, 424), (694, 340), (600, 322), (500, 308))]
for f in range(303, REL + 1):
    lv = .25 * smooth(303, 326, f) + sum(math.exp(-((f - p) / 1.8) ** 2) for p in PUL) * .7
    if lv < .05:
        continue
    onbox.add(f, lambda dr, lv=lv: stroke(dr, fxkit.offset(HOLE, -.04), .004, opacity=min(.9, lv), mat=x_pinkf, cyclic=True, fill=True, line=False))
for i, p in enumerate(PUL):
    fxkit.sparkle(onbox, p, 7, *px(560 + 60 * (i - 1), 300), .3 + .06 * i, x_spark, rot0=.3 * i)
rays(out, REL, 14, 11, 7, mats=(i_rayw, i_ray))
poof(out, REL, 12, 1.1, 21)
confetti(out, REL, 34, 17)
stars(out, REL, 7, 19, i_rayw)
fxkit.shock_rings(behind, REL + 1, ox, oz - .6, 4.2, 6.3, (b_pink, b_white, b_violet), life=12, lag=3)
fxkit.streaks(world, REL, 7, ox, oz - .6, 4.4, 6.3, (w_white, w_pink), n=14, rot=.2)
for x, y in FEET:
    ticks(world, 338, *px(x, y + 10), w_white, spread=.9)
world.draw(gp_layer(fxw, "fx"))
onbox.draw(gp_layer(fxb_, "fx"))
behind.draw(gp_layer(back, "burst"))
out.draw(gp_layer(inside, "out"))

# ================================================================== on the art: dust at its feet
dust = gp_object(ART, SID + "_dust", depth=-1.0)       # in front of every part
m_dust = gp_mat(dust, "fx_dust", (.42, .4, .41, 1), fill=(.82, .79, .75, 1))
db = Board()
for f, big in ((102, .6), (221, .85), (338, .75)):
    for i, (x, y) in enumerate(FEET):
        side = (-1, 0, 1)[i]
        cx, cz = px(x, y)
        if side == 0:
            for s2 in (-1, 1):
                fxkit.dust(db, f, 10, cx + s2 * .3, cz + .05, big * .5, m_dust, drift=(s2 * 1.4 * big, .15), seed=f + s2 + 7)
        else:
            fxkit.dust(db, f, 10, cx + side * .25, cz + .1, big * .55, m_dust, drift=(side * 1.5 * big, .2), seed=f + i)
db.draw(gp_layer(dust, "dust"))

sc.frame_start, sc.frame_end = 1, max(b for a, b in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], "| saved", fxkit.save(SID))
