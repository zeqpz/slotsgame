# H4 - fresh kicks - animated in Blender: four Actions on its rig (idle, land, hit, multi) laid one after another on
# the rig's NLA track, and its effects drawn frame by frame in Grease Pencil.
#   the pair    hangs from a knot over a wire: a helper bone there carries the swing of the whole pair and its bob
#               (keyed by hand): it sways (idle), drops onto the reel and bounces on its laces (land), is yanked
#               back and flung (hit), shivers with the charge and is flung by the release (multi)
#   the shoes   each hangs from its own lace and turns about where the lace goes into its collar. The front shoe
#               swings out and comes back to clack against the back one, the back one is knocked away and comes back
#               (keyed as arcs that meet at the clacks - the shoes never pass through each other); both lag the
#               pair's swing (worked out in Blender from the swing: a critically damped follow)
#   the laces   bend: each lace's chord follows its shoe a little late, so the lace bows and whips between the knot
#               and the shoe (its two bones keyed so the lower one runs into the collar along the shoe)
#   loose ends  the two loose lace ends with their aglets hang from the knot on their own springs (fxkit.secondary,
#               driven by how the laces move, a breeze, the clacks, the charge) - each its own weight
#   the glow    tier 2 neon (fxkit.neon's light), drawn each frame along the silhouette the posed parts make
#   effects     clack flashes and ticks, glints on the white leather and the aglets, speed arcs off the flung toe, a
#               starburst, sparkles, pink lightning crackling between the shoes, shock rings
# Runs INSIDE Blender, after build_symbol_scene.py (tools/blender/run.py runs both in a background Blender).
import bpy, importlib, math, os, random, sys
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
import fxkit
importlib.reload(fxkit)
from fxkit import (rest, px, smooth, gp_object, gp_mat, gp_layer, ride, stroke, star, Board, LIME, VIOLET, WHITE, GOLD, PINK)

SID = "H4"
sc, arm, spec = fxkit.setup(SID)
FPS = sc.render.fps
ART, FXB, FX = fxkit.layers(sc, SID)
fxkit.glow_compositor(sc, SID, back=dict(strength=1.0, size=.55, gain=1.6), front=dict(strength=.9, size=.42, gain=1.5))
if arm.animation_data:
    arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)

import importlib.util as _iu
_spec = _iu.spec_from_file_location("cut_H4", os.path.join(HERE, "cuts", "H4.py"))
CUT = _iu.module_from_spec(_spec); _spec.loader.exec_module(CUT)
PARTS = [p["name"] for p in spec["parts"]]
CLIPS = {"idle": (1, 72), "land": (101, 124), "hit": (201, 250), "multi": (301, 346)}
arm["clips"] = {k: list(v) for k, v in CLIPS.items()}
LACES = {"back": CUT.BACK_LACE, "front": CUT.FRONT_LACE}


# ------------------------------------------------------------------ the rig: the knot over the laces
def helpers():
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    head = fxkit.vec(*CUT.KNOT)
    sw = eb.get("swing") or eb.new("swing")
    sw.head, sw.tail, sw.roll = head, head + Vector((0, 0, .6)), 0
    eb["back_lace.0"].parent = sw
    eb["front_lace.0"].parent = sw
    eb["back_end.0"].parent = eb["back_lace.0"]          # the loose ends hang beside their laces
    eb["front_end.0"].parent = eb["front_lace.0"]
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.pose.bones["swing"].rotation_mode = "XYZ"


helpers()
BONES = [b.name for b in arm.pose.bones]
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


def series(bone, f0, vals, ch, tol, loop=False):
    s = list(vals) + ([vals[0]] if loop else [])
    for i in fxkit.sparse(s, tol):
        k1(bone, f0 + i, **{ch: s[i]})


def follow(vals, hz, loop=False, laps=3):
    """A critically damped follow of a per-frame series (it lags, never overshoots): how a hanging thing trails what
    it hangs from. On a loop, run round until it repeats."""
    om, dt, sub = 2 * math.pi * hz, 1 / FPS, 8
    n = len(vals)
    x, v = vals[0], 0.0
    out = []
    for lap in range(laps if loop else 1):
        out = []
        for k in range(n):
            out.append(x)
            k2 = (k + 1) % n if loop else min(k + 1, n - 1)
            for s in range(sub):
                g = vals[k] + (vals[k2] - vals[k]) * (s + 1) / sub
                a = om * om * (g - x) - 2 * om * v
                v += a * dt / sub
                x += v * dt / sub
    return out


def swing_angles(f0, f1):
    """The swing bone's turn on each frame of a clip, as its keys make it (degrees)."""
    out = []
    pb = arm.pose.bones["swing"]
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        out.append(math.degrees(pb.rotation_euler.z))
    return out


def arcs(f0, f1, spans, sign):
    """A shoe's swing out from the other and back, per frame: half-sine arcs [(start, end, degrees)] that meet the
    rest line with speed at their ends - the clacks. sign -1: the front shoe (it swings clockwise, over the back);
    +1: the back shoe (counter-clockwise, in under the front)."""
    out = []
    for f in range(f0, f1 + 1):
        v = 0.0
        for a, b, amp in spans:
            if a <= f <= b:
                v = sign * amp * math.sin(math.pi * (f - a) / (b - a))
        out.append(v)
    return out


def hang(f0, f1, front_spans, back_spans, loop=False, lag_hz=1.7, lace_hz=2.6):
    """Key both laces and shoes for a clip: each shoe's turn relative to the swing = its lag behind the pair's swing
    plus its arcs; each lace's chord follows its shoe a little late, and its two bones are keyed so the lace runs
    from the knot along that chord and into the collar along the shoe (the shoe itself is never keyed: it rides the
    lace's lower bone). Returns the shoes' turns per frame."""
    phi = swing_angles(f0, f1)
    lag = [a - b for a, b in zip(follow(phi, lag_hz, loop), phi)]
    res = {}
    for name, spans, sign in (("front", front_spans, -1), ("back", back_spans, 1)):
        b = [l + a for l, a in zip(lag, arcs(f0, f1, spans, sign))]
        c = follow(b, lace_hz, loop)
        ch = LACES[name]
        L0 = math.dist(ch[0], ch[1]); L1 = math.dist(ch[1], ch[2])
        a0 = [((L0 + L1) * ci - L1 * bi) / L0 for ci, bi in zip(c, b)]
        if loop:                                       # a loop starts exactly at rest: what the follow left at its first
            n = len(b)                                 # frame is taken out over the lap (raised cosine)
            b0, a00 = b[0], a0[0]
            b = [bi - b0 * (.5 + .5 * math.cos(2 * math.pi * k / n)) for k, bi in enumerate(b)]
            a0 = [ai - a00 * (.5 + .5 * math.cos(2 * math.pi * k / n)) for k, ai in enumerate(a0)]
        if not loop:                                   # the clip ends exactly at rest
            for k in range(1, 7):
                t = k / 6
                w = t * t * (3 - 2 * t)
                i = len(b) - 7 + k
                b[i] *= 1 - w; a0[i] *= 1 - w
        series(name + "_lace.0", f0, a0, "r", .03, loop)
        series(name + "_lace.1", f0, [bi - ai for bi, ai in zip(b, a0)], "r", .03, loop)
        res[name] = b
        print(f"  {f0}-{f1} {name}: shoe {min(b):+.2f}..{max(b):+.2f}, lace bend {min(bi - ai for bi, ai in zip(b, a0)):+.2f}.."
              f"{max(bi - ai for bi, ai in zip(b, a0)):+.2f}")
    return res


HANG_ENDS = {   # the loose ends: stiffness per joint (Hz, softer to the aglet), damping, how much of the lag shows
    "back_end": dict(chain=CUT.BACK_END, freq=[3.0, 2.5, 2.1], zeta=.2, gain=.8, limit=16),
    "front_end": dict(chain=CUT.FRONT_END, freq=[2.7, 2.2, 1.8], zeta=.17, gain=.8, limit=18),
}


def ends(f0, f1, loop=False, forces=None, gain=1.0):
    """The loose ends, worked out from how their laces move in this clip (each hangs beside its own lace)."""
    for name, holder in (("back_end", "back_lace.0"), ("front_end", "front_lace.0")):
        res = fxkit.secondary(sc, arm, holder, f0, f1, {name: HANG_ENDS[name]}, loop=loop, forces=forces, gain=gain)
        print(f"  {f0}-{f1}:", ", ".join(f"{b} {min(v):+.1f}..{max(v):+.1f}" for b, v in res.items()))
        for bone, vals in res.items():
            fxkit.key_series(arm, bone, f0, vals, channel="r", tol=.25, loop=loop)


def jolts(f0, clacks, amp, lift=0.0, lift_span=None):
    """Forces on the loose ends: a jolt out from the shoes at each clack (the aglets flick), and while a charge
    holds (lift_span: (from, to) frames), a pull up and out - they stand out like charged hair."""
    def fn(name, i, t):
        f = f0 + t * FPS
        side = -1 if name == "back_end" else 1
        w = (i / 3) ** .7
        acc = Vector((0, 0, 0))
        for c, a in clacks:
            if 0 <= f - c < 3:
                acc += Vector((side * a, 0, a * .35)) * w * amp
        if lift and lift_span:
            env = smooth(lift_span[0], lift_span[0] + 6, f) * (1 - smooth(lift_span[1] - 1, lift_span[1] + 3, f))
            if env > 0:
                rnd = random.Random(int(f) * 17 + i * 5 + (0 if side < 0 else 50))
                acc += (Vector((side * .35, 0, 1.0)) * lift + Vector(((rnd.random() - .5), 0, (rnd.random() - .5))) * lift * .5) * env * w
        return acc
    return fn



# ================================================================== idle: the pair sways; the front shoe drifts out and clacks back
f0, f1 = CLIPS["idle"]
act = fxkit.begin_action(arm, SID + "_idle")
rest(arm, BONES, f0)
keys("swing", "r", [(1, 0), (19, 1.0), (37, 0), (55, -1.0), (73, 0)])
IDLE_CLACK = [(1, 1.0), (73, 1.0)]
hang(f0, f1, front_spans=[(1, 73, 1.5)], back_spans=[(1, 15, .45)], loop=True)


def breeze(name, i, t):
    T = 72 / FPS
    a = (26 if name == "back_end" else 30) * math.sin(2 * math.pi * t / T + (0.0 if name == "back_end" else 1.9))
    a += 8 * math.sin(2 * math.pi * t / (T / 3) + 1.0)
    return Vector((a * (i / 3) ** .8, 0, 0))


ends(f0, f1, loop=True, forces=breeze)
fxkit.make_cyclic(act)
fxkit.end_action(arm, act, f0)

# ================================================================== land: it drops onto the reel and bounces on its laces
f0, f1 = CLIPS["land"]
act = fxkit.begin_action(arm, SID + "_land")
rest(arm, BONES, f0)
keys("swing", "y", [(103, -.15), (106, .055), (109, -.022), (113, .007), (117, 0), (124, 0)])
keys("swing", "r", [(103, -.5), (108, .45), (113, -.18), (118, 0), (124, 0)])
hard(act, "swing", "y", 103)
LAND_CLACKS = [(111, 1.0), (116, .45), (119, .2)]
hang(f0, f1, front_spans=[(103, 111, 3.0), (111, 116, 1.0), (116, 119, .3)], back_spans=[(111, 118, 1.0), (116, 121, .3)])
ends(f0, f1, forces=jolts(f0, LAND_CLACKS, 260), gain=.8)
fxkit.end_action(arm, act, f0)

# ================================================================== hit: yanked back, flung, the shoes clack together three times
f0, f1 = CLIPS["hit"]
act = fxkit.begin_action(arm, SID + "_hit")
rest(arm, BONES, f0)
keys("swing", "r", [(205, 2.4), (211, -5.2), (219, 3.0), (228, -1.5), (236, .6), (244, 0), (250, 0)])
keys("swing", "y", [(205, .045), (210, .09), (217, -.035), (222, .01), (226, 0), (250, 0)])
HIT_CLACKS = [(217, 1.0), (224, .55), (229, .25)]
hang(f0, f1, front_spans=[(204, 217, 8.5), (217, 224, 3.4), (224, 229, 1.2), (229, 232, .35)],
     back_spans=[(217, 226, 3.0), (224, 231, 1.2), (229, 233, .4)])
ends(f0, f1, forces=jolts(f0, HIT_CLACKS, 420), gain=.85)
fxkit.end_action(arm, act, f0)

# ================================================================== multi: it shivers with the charge, rattling, and is flung by the release
f0, f1 = CLIPS["multi"]
PUL = (307, 313, 319)
REL = 327
act = fxkit.begin_action(arm, SID + "_multi")
rest(arm, BONES, f0)
keys("swing", "s", [(303, 1), (307, 1.03), (310, 1), (313, 1.04), (316, 1), (319, 1.05), (322, 1.0), (325, .97), (327, .965),
                    (330, 1.04), (334, 1), (346, 1)])
jit = [(303, 0)]
for i, f in enumerate(range(304, 327)):
    jit.append((f, (.25 + .5 * (f - 304) / 22) * (1 if i % 2 else -1)))
jit += [(327, 0), (332, 6.2), (338, -2.8), (342, 1.1), (346, 0)]
keys("swing", "r", jit)
keys("swing", "y", [(326, -.03), (329, .1), (334, 0), (346, 0)])
MULTI_CLACKS = [(310, .5), (316, .6), (322, .7), (336, 1.0), (341, .45)]
hang(f0, f1, front_spans=[(305, 310, 1.1), (311, 316, 1.4), (317, 322, 1.7), (327, 336, 6.0), (336, 341, 2.0), (341, 344, .5)],
     back_spans=[(310, 314, .5), (316, 320, .6), (322, 326, .7), (336, 343, 2.4), (341, 345, .6)])
ends(f0, f1, forces=jolts(f0, MULTI_CLACKS, 380, lift=170, lift_span=(305, 327)), gain=.85)
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


# ================================================================== the tier glow, along the pair as it swings
neon_live(PARTS, CLIPS, tier=2, land_at=103, hit_span=(207, 240), pulses=PUL, charge_span=(304, 327))


# ================================================================== effects
def at(f, x, y, bone):
    """Where icon point (x, y) on a bone's part is at frame f (world x, z; f may be fractional)."""
    sc.frame_set(int(math.floor(f)), subframe=f - math.floor(f))
    pb = arm.pose.bones[bone]
    p = arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted() @ fxkit.vec(x, y)
    return p.x, p.z


fxw = gp_object(FX, SID + "_fx", depth=-.8)            # stays where the frame is
fxf = gp_object(FX, SID + "_fx_front", depth=-.8)      # rides the front shoe
ride(fxf, arm, "front")
fxk = gp_object(FX, SID + "_fx_back", depth=-.8)       # rides the back shoe
ride(fxk, arm, "back")
fxa = gp_object(FX, SID + "_fx_aglet_f", depth=-.8)    # rides the front loose end's tip
ride(fxa, arm, "front_end.2")
fxb2 = gp_object(FX, SID + "_fx_aglet_b", depth=-.8)   # rides the back loose end's tip
ride(fxb2, arm, "back_end.2")
back = gp_object(FXB, SID + "_burst", depth=.35)       # behind the pair, bloomed (not "_back": that is the back shoe)
w_white = gp_mat(fxw, "fx_white_line", WHITE); w_pink = gp_mat(fxw, "fx_pink_line", PINK); w_violet = gp_mat(fxw, "fx_violet_line", VIOLET)
w_spark = gp_mat(fxw, "fx_white_fill", WHITE, fill=WHITE); w_gold = gp_mat(fxw, "fx_gold_fill", GOLD, fill=GOLD)
w_pinkf = gp_mat(fxw, "fx_pink_fill", PINK, fill=PINK)
f_spark = gp_mat(fxf, "fx_white_fill", WHITE, fill=WHITE); f_white = gp_mat(fxf, "fx_white_line", WHITE)
k_spark = gp_mat(fxk, "fx_white_fill", WHITE, fill=WHITE); k_white = gp_mat(fxk, "fx_white_line", WHITE)
a_spark = gp_mat(fxa, "fx_white_fill", WHITE, fill=WHITE); a_pink = gp_mat(fxa, "fx_pink_fill", PINK, fill=PINK)
b2_spark = gp_mat(fxb2, "fx_white_fill", WHITE, fill=WHITE); b2_pink = gp_mat(fxb2, "fx_pink_fill", PINK, fill=PINK)
b_pink = gp_mat(back, "glow_pink", PINK); b_white = gp_mat(back, "glow_white", WHITE); b_violet = gp_mat(back, "glow_violet", VIOLET)
b_pinkf = gp_mat(back, "glow_pink_fill", PINK, fill=PINK); b_whitef = gp_mat(back, "glow_white_fill", WHITE, fill=WHITE)
world, onfront, onback, ag_f, ag_b, bb = Board(), Board(), Board(), Board(), Board(), Board()
CONTACT = (505, 548)         # where the shoes meet: the front's lace loops against the back's midsole (icon px)
TOE_F, TOE_B = (262, 812), (92, 586)
AGLET_F, AGLET_B = (682, 388), (482, 244)


def clack(board, f, x, z, strength=1.0, mats=None):
    """The shoes knocking together: a hot little star at the contact, and short ticks flicking out round it - drawn
    for a few frames and gone (it thins away, it does not fade)."""
    mats = mats or (w_spark, w_white)
    life = 5 if strength > .5 else 4
    for k in range(life):
        t = k / (life - 1)
        r = (.28 + .3 * strength) * math.sin(math.pi * min(1, .25 + t * .9))
        board.add(f + k, lambda dr, r=r, t=t: stroke(dr, star(x, z, r + .02, .4 + .6 * t, points=4, inner=.22), .004,
                                                     mat=mats[0], cyclic=True, fill=True, line=False))
        n = 6 if strength > .5 else 4
        for j in range(n):
            a = 2 * math.pi * j / n + .35
            r0, r1 = (.32 + .55 * t) * (.7 + .5 * strength), (.55 + .8 * t) * (.7 + .5 * strength)
            board.add(f + k, lambda dr, a=a, r0=r0, r1=r1, t=t: stroke(
                dr, [(x + math.cos(a) * r0, z + math.sin(a) * r0), (x + math.cos(a) * r1, z + math.sin(a) * r1)],
                .03 * (1 - t) * (.6 + .5 * strength) + .006, mat=mats[1]))


def shine(board, f0, life, pts, mat, width=.05):
    """A glint sweeping across shiny leather: a short bright slash travelling along a path (points in the part's own
    icon px), swelling then thinning to a needle."""
    for k in range(life):
        t = k / (life - 1)
        i = t * (len(pts) - 1)
        j = min(int(i), len(pts) - 2)
        u = i - j
        x = pts[j][0] + (pts[j + 1][0] - pts[j][0]) * u
        y = pts[j][1] + (pts[j + 1][1] - pts[j][1]) * u
        cx, cz = px(x, y)
        w = width * math.sin(math.pi * t) + .004
        board.add(f0 + k, lambda dr, cx=cx, cz=cz, w=w: stroke(dr, [(cx - .28, cz - .22), (cx, cz), (cx + .28, cz + .22)], 0, mat=mat,
                                                              radii=[.004, w, .004]))


def arc_trail(board, f0, f1, x, y, bone, mat, back_frames=4.0, width=.045):
    """Speed arcs behind a part flung through the air: the path a point on it took over the last few frames, a
    tapering line, thick at the point."""
    for f in range(f0, f1 + 1):
        pts = [at(f - back_frames + back_frames * i / 16, x, y, bone) for i in range(17)]
        span = math.dist(pts[0], pts[-1])
        if span < .25:
            continue
        m = len(pts)
        board.add(f, lambda dr, pts=pts, m=m: stroke(dr, pts, 0, radii=[.004 + width * (i / (m - 1)) ** 1.7 for i in range(m)],
                                                     opacities=[.2 + .8 * i / (m - 1) for i in range(m)], mat=mat))


# idle: the clack at the loop's turn (soft), the aglets catch the light, a glint runs across the front toe
for f, s in IDLE_CLACK[:1]:
    clack(world, f + 1, *at(f + 1, *CONTACT, "front"), strength=.25)
fxkit.sparkle(ag_f, 24, 8, *px(*AGLET_F), .2, a_spark)
fxkit.sparkle(ag_b, 50, 8, *px(*AGLET_B), .18, b2_spark, rot0=.6)
shine(onfront, 40, 9, [(300, 760), (360, 715), (420, 690)], f_white)

# land: the drop's motion lines over the knot, the clacks, the aglets flick
kx, kz = px(*CUT.KNOT)
for k in range(5):
    t = k / 4
    for j, dx in enumerate((-.9, -.3, .3, .9)):
        world.add(101 + k, lambda dr, dx=dx, t=t, j=j: stroke(dr, [(kx + dx, kz + .55 + .25 * t + .1 * (j % 2)), (kx + dx, kz + 1.3 - .2 * t)],
                                                             .026 * (1 - t) + .006, mat=w_white))
for f, s in LAND_CLACKS:
    clack(world, f, *at(f, *CONTACT, "front"), strength=s)
fxkit.sparkle(onback, 112, 8, *px(150, 520), .3, k_spark)

# hit: the toe's speed arcs as it is flung, three clacks (the first with a starburst behind), the leather glints,
# sparkles all round
arc_trail(world, 207, 216, *TOE_F, "front", w_white)
arc_trail(world, 219, 223, *TOE_F, "front", w_white, back_frames=3, width=.03)
arc_trail(world, 207, 214, *TOE_B, "back", w_white, back_frames=3, width=.03)
for f, s in HIT_CLACKS:
    clack(world, f, *at(f, *CONTACT, "front"), strength=s)
cx_, cz_ = at(217, *CONTACT, "front")
fxkit.starburst(bb, 217, 10, cx_, cz_, 2.6, 6.0, b_pinkf, b_whitef, points=12)
shine(onfront, 220, 9, [(290, 770), (360, 720), (430, 690)], f_white, width=.07)
shine(onback, 224, 9, [(110, 560), (180, 520), (240, 500)], k_white, width=.06)
fxkit.sparkle(ag_f, 218, 9, *px(*AGLET_F), .3, a_spark)
fxkit.sparkle(ag_b, 220, 9, *px(*AGLET_B), .26, b2_spark, rot0=.5)
rnd = random.Random(8)
for i in range(9):
    fxkit.sparkle(world, 216 + rnd.randint(0, 16), rnd.randint(6, 9), rnd.uniform(-4.8, 4.8), rnd.uniform(-4.2, 5.4), rnd.uniform(.24, .46),
                  w_gold if i % 3 == 0 else w_spark, rot0=rnd.uniform(0, 1))

# multi: pink crackle between the two shoes, the aglets glow with the charge, each rattle clacks, the release rings
# out and flings them
for f in range(305, 327, 2):
    rr = random.Random(f)
    for j in range(2 if f < 316 else 3):
        p0 = at(f, rr.uniform(380, 560), rr.uniform(300, 520), "back")
        p1 = at(f, rr.uniform(600, 820), rr.uniform(340, 600), "front")
        world.add(f, lambda dr, p0=p0, p1=p1, f=f, j=j: stroke(dr, fxkit.zigzag(*p0, *p1, n=7, amp=.2, seed=f * 3 + j), .026,
                                                               mat=(w_pink, w_white, w_violet)[j % 3]), hold=2)
for f in range(305, 328):
    env = smooth(305, 312, f) * (1 - smooth(325, 329, f))
    r = .1 + .12 * env + .06 * sum(math.exp(-((f - p) / 1.6) ** 2) for p in PUL)
    if env > .05:
        ag_f.add(f, lambda dr, r=r: stroke(dr, fxkit.ring(*px(*AGLET_F), r, n=24), .004, mat=a_pink, cyclic=True, fill=True, line=False))
        ag_b.add(f, lambda dr, r=r: stroke(dr, fxkit.ring(*px(*AGLET_B), r, n=24), .004, mat=b2_pink, cyclic=True, fill=True, line=False))
for f, s in MULTI_CLACKS:
    clack(world, f, *at(f, *CONTACT, "front"), strength=s, mats=(w_spark, w_pink) if f < REL else None)
cx_, cz_ = px(500, 520)
fxkit.shock_rings(bb, REL, cx_, cz_, 4.4, 6.4, (b_pink, b_white, b_violet), life=12, lag=3)
fxkit.streaks(world, REL, 7, cx_, cz_, 4.6, 6.4, (w_white, w_pink), n=14, rot=.15)
arc_trail(world, 329, 335, *TOE_F, "front", w_white)
world.draw(gp_layer(fxw, "fx"))
onfront.draw(gp_layer(fxf, "fx"))
onback.draw(gp_layer(fxk, "fx"))
ag_f.draw(gp_layer(fxa, "fx"))
ag_b.draw(gp_layer(fxb2, "fx"))
bb.draw(gp_layer(back, "burst"))

sc.frame_start, sc.frame_end = 1, max(b for a, b in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], "| saved", fxkit.save(SID))
