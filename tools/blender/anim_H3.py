# H3 - the gold chain - animated in Blender: four Actions on its rig (idle, land, hit, multi) on the rig's NLA track,
# its effects drawn frame by frame in Grease Pencil on the same timeline.
#   the rig      a ring of 28 bones round the loop (added here), each one link's length, children of a "hang" bone at
#                the top of the loop, under a "toss" bone at its middle. The links are ONE mesh weighted smoothly
#                round the ring, so the loop bends anywhere and nothing ever opens between pieces; the clasp rides
#                the ring where it sits (its stretch of the ring is held rigid)
#   the swing    keyed by hand: the loop sways from its top (idle), drops and squashes (land), is flung up and
#                spun round once like a chain twirled on a finger (hit), tightens in three pulses and bursts (multi)
#   the links    worked out in Blender: the ring is a closed chain of point masses on springs to where they would
#                sit if the loop were rigid, stiff near the top and loose far from it, held to their lengths, driven
#                by how the keys really move the top - the far end lags a swing, the loop wobbles after a landing,
#                links rattle when it hits (impulses) and tremble with the charge; keyed onto the ring bones
#   the ripple   a swell runs round the links (each bone fattens in turn), glints riding it
#   the glow     tier 1 neon (fxkit.neon) round the outside, and the same light through the hole in the middle
#   effects      the clasp's bling, clinks, gold glitter, speed arcs and flung sparkles in the spin, a burst of rays,
#                lightning arcing across the hole, shock rings, streaks
# Runs INSIDE Blender, after build_symbol_scene.py (tools/blender/run.py runs both in a background Blender).
import bpy, importlib, json, math, os, random, sys
from mathutils import Matrix, Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
import fxkit
importlib.reload(fxkit)
from fxkit import (key, rest, px, vec, smooth, gp_object, gp_mat, gp_layer, ride, stroke, star, ring, Board,
                   LIME, VIOLET, WHITE, GOLD)

SID = "H3"
sc, arm, spec = fxkit.setup(SID)
FPS = sc.render.fps
PARTS = {p["name"]: p for p in spec["parts"]}
if arm.animation_data:
    arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)

# ------------------------------------------------------------------ measured on the art (icon px)
HANG = (300, 196)            # the top of the loop: it sways from here
MID = (488, 482)             # the middle of the loop: it spins and squashes about here
BOTTOM_Y = 792               # the loop's lowest link: a landing squashes onto it
CLASP_C = (308.5, 547.8)     # the clasp box's middle (tools/blender/cuts/H3.py)
# the loop's centre line (the recipe's, which the new art was fitted to), clockwise from the clasp
PATH = [(300, 545), (235, 487), (180, 440), (140, 380), (122, 320), (140, 262), (185, 218), (255, 200),
        (335, 208), (415, 238), (490, 290), (560, 345), (625, 405), (695, 455), (765, 510), (825, 570),
        (848, 640), (825, 705), (765, 740), (690, 752), (610, 740), (530, 715), (455, 690), (395, 645),
        (345, 595)]
N = 28
Q = fxkit.resample(PATH, N, closed=True)                # the ring's joints, evenly round the loop
SEG = [math.dist(Q[i], Q[(i + 1) % N]) for i in range(N)]
LOOP = sum(SEG)
S = [sum(SEG[:i]) for i in range(N)]                   # each joint's distance round the loop
CENTRE = (sum(q[0] for q in Q) / N, sum(q[1] for q in Q) / N)


def ring_dist(a, b):
    d = abs(a - b) % LOOP
    return min(d, LOOP - d)


I_HANG = min(range(N), key=lambda i: math.dist(Q[i], HANG))
I_CLASP = min(range(N), key=lambda i: math.dist(Q[i], CLASP_C))
CLASP_IDX = [i for i in range(N) if ring_dist(S[i], S[I_CLASP]) <= 180]      # the clasp's stretch and a link past
# each end cap: held rigid, so the links under its ends move with it (a rigid box in a bending chain)
I_BOTTOM = max(range(N), key=lambda i: Q[i][1])

# ------------------------------------------------------------------ the rig
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
toss = eb.get("toss") or eb.new("toss")
toss.head = vec(*MID); toss.tail = toss.head + Vector((0, 0, .6)); toss.roll = 0
hang = eb.get("hang") or eb.new("hang")
hang.head = vec(*HANG); hang.tail = hang.head + Vector((0, 0, .6)); hang.roll = 0
hang.parent = toss
toward_cam = Vector((0, -1, 0))
for i in range(N):
    b = eb.get(f"r{i}") or eb.new(f"r{i}")
    b.head, b.tail = vec(*Q[i]), vec(*Q[(i + 1) % N])
    b.align_roll(toward_cam)
    b.parent = hang
    b.use_connect = False
eb["clasp"].parent = hang
eb["s1"].parent = hang
bpy.ops.object.mode_set(mode="OBJECT")
for pb in arm.pose.bones:
    pb.rotation_mode = "XYZ"
bpy.context.view_layer.update()
RINGB = [f"r{i}" for i in range(N)]
REST3 = {b: arm.data.bones[b].matrix_local.to_3x3() for b in RINGB}


def nearest_s(x, y):
    """Distance round the loop of the ring's nearest point to (x, y) (icon px)."""
    best, s_at = None, 0.0
    for i in range(N):
        (ax, ay), (bx, by) = Q[i], Q[(i + 1) % N]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / L2))
        d = math.hypot(ax + dx * t - x, ay + dy * t - y)
        if best is None or d < best:
            best, s_at = d, S[i] + t * SEG[i]
    return s_at


def ring_weights(x, y):
    """Each ring bone's weight at a point: hats on the bones' middles, so a point between two bones takes both."""
    s = nearest_s(x, y)
    out = {}
    for i in range(N):
        c = S[i] + SEG[i] / 2
        w = 1 - ring_dist(s, c) / SEG[i]
        if w > 0:
            out[f"r{i}"] = w
    tot = sum(out.values()) or 1
    return {k: v / tot for k, v in out.items()}


def regrid(name, weights, cell):
    """Give a part a fine grid mesh bent by the rig: weights(x, y) -> {bone: weight} in icon px."""
    p = PARTS[name]
    ob = bpy.data.objects[SID + "_" + name]
    depth = ob.matrix_world.translation.y
    x0, y0, x1, y1 = p["box"]
    nx, ny = max(2, round((x1 - x0) / cell)), max(2, round((y1 - y0) / cell))
    verts, uvs, faces = [], [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x, y = x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny
            verts.append((px(x, y)[0], 0.0, px(x, y)[1]))
            uvs.append((i / nx, 1 - j / ny))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a + nx + 1, a + nx + 2, a + 1, a))
    me = bpy.data.meshes.new(SID + "_" + name + "_bent")
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new()
    for poly in me.polygons:
        for li in poly.loop_indices:
            uv.data[li].uv = uvs[me.loops[li].vertex_index]
    me.materials.append(ob.data.materials[0])
    ob.data = me
    ob.parent, ob.parent_type, ob.parent_bone = arm, "OBJECT", ""
    bpy.context.view_layer.update()
    ob.matrix_world = Matrix.Translation((0, depth, 0))
    groups = {}
    for v in me.vertices:
        x, y = (v.co.x * 100 + 500), (500 - v.co.z * 100)
        for bone, w in weights(x, y).items():
            if w > 1e-4:
                if bone not in groups:
                    groups[bone] = ob.vertex_groups.new(name=bone)
                groups[bone].add([v.index], w, "REPLACE")
    mod = ob.modifiers.new("rig", "ARMATURE")
    mod.object = arm
    mod.use_vertex_groups = True
    return ob


regrid("s1", ring_weights, 8)

ART, FXB, FX = fxkit.layers(sc, SID)
fxkit.glow_compositor(sc, SID, back=dict(strength=1.0, size=.55, gain=1.6), front=dict(strength=.95, size=.42, gain=1.55))

CLIPS = {"idle": (1, 84), "land": (101, 124), "hit": (201, 254), "multi": (301, 346)}
arm["clips"] = {k: list(v) for k, v in CLIPS.items()}
HAND = ["toss", "hang", "clasp"]
ZB = (500 - BOTTOM_Y) / 100 - (500 - MID[1]) / 100      # the bottom, below the toss bone (units)


def tossk(f, sx=None, sy=None, y=0.0, x=0.0, r=None, plant=True, s=None):
    if s is not None:
        sx = sy = s
    if sx is not None or sy is not None:
        key(arm, "toss", f, sx=sx, sy=sy)
        sy_ = 1 if sy is None else sy
        key(arm, "toss", f, x=x, y=y + (ZB * (1 - sy_) if plant else 0))
    else:
        key(arm, "toss", f, x=x, y=y)
    if r is not None:
        key(arm, "toss", f, r=r)


# ------------------------------------------------------------------ the links: a closed chain on springs
QW = [Vector((px(*q)[0], 0, px(*q)[1])) for q in Q]
FREQ = [2.6 + (9.0 - 2.6) * math.exp(-(ring_dist(S[i], S[I_HANG]) / 260) ** 2) for i in range(N)]
NORMAL = []
for i in range(N):
    a, b = QW[i - 1], QW[(i + 1) % N]
    t = (b - a).normalized()
    nrm = Vector((t.z, 0, -t.x))
    c = Vector((px(*CENTRE)[0], 0, px(*CENTRE)[1]))
    if nrm.dot(QW[i] - c) < 0:
        nrm = -nrm
    NORMAL.append(nrm)                                  # outward, away from the hole


def rigid_fit(P, G, idx):
    """Move P[idx] onto G[idx]'s shape, turned and shifted to sit where P[idx] are (the clasp's stretch is rigid)."""
    cp = sum((P[i] for i in idx), Vector()) / len(idx)
    cg = sum((G[i] for i in idx), Vector()) / len(idx)
    num = sum((G[i] - cg).x * (P[i] - cp).z - (G[i] - cg).z * (P[i] - cp).x for i in idx)
    den = sum((G[i] - cg).x * (P[i] - cp).x + (G[i] - cg).z * (P[i] - cp).z for i in idx)
    th = math.atan2(num, den)
    c, s = math.cos(th), math.sin(th)
    for i in idx:
        g = G[i] - cg
        P[i] = cp + Vector((g.x * c - g.z * s, 0, g.x * s + g.z * c))


def simulate(f0, f1, loop=False, gain=1.0, stiff=1.0, zeta=.2, forces=None, warm=3, sub=8, settle=8):
    """The ring's joints frame by frame, in the hang bone's rest frame (world units): springs to where a rigid loop
    would put them, driven by how the keys move the hang bone, held to their lengths, the clasp's stretch rigid."""
    pb = arm.pose.bones["hang"]
    rest_inv = pb.bone.matrix_local.inverted()
    Hm = []
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        Hm.append((arm.matrix_world @ pb.matrix @ rest_inv).copy())
    nf = len(Hm)
    Hinv = [m.inverted() for m in Hm]
    G = [[m @ q for q in QW] for m in Hm]
    om = [2 * math.pi * fr * stiff for fr in FREQ]
    P = [g.copy() for g in G[0]]
    V = [Vector((0, 0, 0)) for _ in range(N)]
    steps = nf * (warm + 1) if loop else nf
    rec = []
    dt = 1.0 / (FPS * sub)
    for step in range(steps):
        k = step % nf
        k2 = (k + 1) % nf if loop else min(k + 1, nf - 1)
        if step >= steps - nf:
            rec.append([Hinv[k] @ p for p in P])
        for s_ in range(sub):
            u0, u1 = s_ / sub, (s_ + 1) / sub
            G0 = [G[k][i].lerp(G[k2][i], u0) for i in range(N)]
            G1 = [G[k][i].lerp(G[k2][i], u1) for i in range(N)]
            fr = f0 + k + u0
            for i in range(N):
                vg = (G1[i] - G0[i]) / dt
                acc = (G0[i] - P[i]) * om[i] ** 2 - (V[i] - vg) * (2 * zeta * om[i])
                if forces:
                    acc = acc + forces(i, fr)
                V[i] = V[i] + acc * dt
            old = [p.copy() for p in P]
            for i in range(N):
                P[i] = P[i] + V[i] * dt
            for _ in range(2):                          # held to its lengths (the keys' squash included)
                for i in range(N):
                    j = (i + 1) % N
                    target = (G1[j] - G1[i]).length
                    d = P[j] - P[i]
                    L = d.length
                    if L > 1e-9:
                        c = (L - target) / L * .5
                        P[i] = P[i] + d * c
                        P[j] = P[j] - d * c
            rigid_fit(P, G1, CLASP_IDX)
            for i in range(N):
                V[i] = (P[i] - old[i]) / dt
    D = [[(rec[k][i] - QW[i]) * gain for i in range(N)] for k in range(nf)]
    # smoothed along the ring (the clasp's stretch held as it is): no link may kink against its neighbours - a kink
    # pinches the sticker border on the outside of the bend into a notch
    free = [i for i in range(N) if i not in CLASP_IDX]
    for k in range(nf):
        for _ in range(3):
            d = D[k]
            D[k] = [d[i] if i not in free else (d[i - 1] + d[i] * 2 + d[(i + 1) % N]) / 4 for i in range(N)]
    if loop:                                            # starts exactly at rest, still joins up (raised cosine)
        D0 = D[0]
        D = [[D[k][i] - D0[i] * (.5 + .5 * math.cos(2 * math.pi * k / nf)) for i in range(N)] for k in range(nf)]
    elif settle:
        for j in range(settle):
            k = nf - settle + j
            t = (j + 1) / settle
            fade = 1 - t * t * (3 - 2 * t)
            D[k] = [d * fade for d in D[k]]
    print(f"  links {f0}-{f1}: max off the rigid loop {max(d.length for dk in D for d in dk) * 100:.1f} px")
    return [[QW[i] + D[k][i] for i in range(N)] for k in range(nf)]


def fit2(A, B, idx):
    """Turn and shift taking points A[idx] onto B[idx] (2D, x/z)."""
    ca = sum((A[i] for i in idx), Vector()) / len(idx)
    cb = sum((B[i] for i in idx), Vector()) / len(idx)
    num = sum((A[i] - ca).x * (B[i] - cb).z - (A[i] - ca).z * (B[i] - cb).x for i in idx)
    den = sum((A[i] - ca).x * (B[i] - cb).x + (A[i] - ca).z * (B[i] - cb).z for i in idx)
    return math.atan2(num, den), ca, cb


CP = vec(*PARTS["clasp"]["pivot"])


def key_ring(f0, rec, swell=None, clasp_pop=None, loop=False):
    """Key the ring bones (and the clasp riding its stretch) from the simulated joints, every frame."""
    nf = len(rec)
    frames = list(range(nf)) + ([0] if loop else [])
    for n, k in enumerate(frames):
        f = f0 + n
        R = rec[k]
        for i in range(N):
            j = (i + 1) % N
            h, t = R[i], R[j]
            h0, t0 = QW[i], QW[j]
            ang = math.atan2(t.z - h.z, t.x - h.x) - math.atan2(t0.z - h0.z, t0.x - h0.x)
            ang = (ang + math.pi) % (2 * math.pi) - math.pi
            ratio = (t - h).length / (t0 - h0).length
            d = REST3[f"r{i}"].transposed() @ (h - h0)
            pb = arm.pose.bones[f"r{i}"]
            pb.location = (d.x, d.y, 0)
            pb.rotation_euler = (0, 0, ang)
            pb.scale = (swell(i, f0 + k) if swell else 1.0, ratio, 1)
            for path in ("location", "rotation_euler", "scale"):
                pb.keyframe_insert(path, frame=f, group=f"r{i}")
        th, ca, cb = fit2(QW, R, CLASP_IDX)
        c, s = math.cos(th), math.sin(th)
        v = CP - ca
        newp = cb + Vector((v.x * c - v.z * s, 0, v.x * s + v.z * c))
        pb = arm.pose.bones["clasp"]
        pb.location = (newp.x - CP.x, newp.z - CP.z, 0)
        pb.rotation_euler = (0, 0, th)
        sc_ = clasp_pop(f0 + k) if clasp_pop else 1.0
        pb.scale = (sc_, sc_, 1)
        for path in ("location", "rotation_euler", "scale"):
            pb.keyframe_insert(path, frame=f, group="clasp")


def bump(u, width=6):
    """A smooth periodic bump peaking at u = 0 (mod 1)."""
    return ((1 + math.cos(2 * math.pi * u)) / 2) ** width


def pulse(f, c, w):
    """A bell round frame c, exactly nothing two widths away (clips start and end on the rest pose)."""
    u = (f - c) / w
    return math.exp(-u * u) * (1 - smooth(1.3, 2.0, abs(u)))


def env(f, peaks, width=2.0):
    return sum(a * math.exp(-((f - p) / width) ** 2) for p, a in peaks)


def rattle(at, strength, seed, spread=.06, waves=4):
    """An impulse through the links when the loop hits something: a ripple of kicks out and in round the loop
    (`waves` of them - never link against link: alternate kicks fold the links and pinch the sticker border), the
    kick arriving later the further round the loop from the bottom."""
    rnd = random.Random(seed)
    ph = rnd.uniform(0, 2 * math.pi)
    sign = [math.sin(2 * math.pi * waves * S[i] / LOOP + ph) for i in range(N)]

    def fn(i, f):
        delay = ring_dist(S[i], S[I_BOTTOM]) * spread / 30
        u = f - at - delay
        if 0 <= u < 1.5:
            return NORMAL[i] * (strength * sign[i])
        return Vector((0, 0, 0))
    return fn


def combine(*fns):
    def fn(i, f):
        v = Vector((0, 0, 0))
        for g in fns:
            v = v + g(i, f)
        return v
    return fn


# ================================================================== idle: it sways from its top; a swell runs round
f0, f1 = CLIPS["idle"]
n_idle = f1 - f0 + 1
act = fxkit.begin_action(arm, SID + "_idle")
rest(arm, HAND + RINGB, f0)
for f, r, y in ((1, 0, 0), (22, 2.4, .025), (43, 0, 0), (64, -2.4, .025), (85, 0, 0)):
    key(arm, "hang", f, r=r)
    key(arm, "toss", f, y=y)
SWELL_ON = (8, 76)                                       # the swell's lap: it rises, runs once round, sinks


def idle_env(f):
    return smooth(SWELL_ON[0], SWELL_ON[0] + 8, f) * (1 - smooth(SWELL_ON[1] - 8, SWELL_ON[1], f))


rec = simulate(f0, f1, loop=True, gain=.85)
key_ring(f0, rec, swell=lambda i, f: 1 + .075 * idle_env(f) * bump(S[i] / LOOP - (f - SWELL_ON[0]) / (SWELL_ON[1] - SWELL_ON[0])),
         clasp_pop=lambda f: 1 + .02 * pulse(f, 60, 3.0), loop=True)
fxkit.make_cyclic(act)
fxkit.end_action(arm, act, f0)

# ================================================================== land: it drops, squashes, the links rattle
f0, f1 = CLIPS["land"]
act = fxkit.begin_action(arm, SID + "_land")
rest(arm, HAND + RINGB, f0)
for f, sx, sy, y in ((103, 1.08, .86, 0), (106, .96, 1.05, .05), (110, 1.02, .985, 0), (114, .995, 1.004, 0), (119, 1, 1, 0),
                     (124, 1, 1, 0)):
    tossk(f, sx=sx, sy=sy, y=y)
fxkit.hard(act, "toss", "scale", 1, 103)
for f, r in ((101, 0), (103, -2.2), (108, 1.6), (113, -.7), (118, .2), (123, 0), (124, 0)):
    key(arm, "hang", f, r=r)
rec = simulate(f0, f1, gain=.3, stiff=1.4, zeta=.28, forces=rattle(102, 80, 1))
key_ring(f0, rec, swell=lambda i, f: 1 + .09 * math.exp(-((ring_dist(S[i], S[I_BOTTOM]) - (f - 102) * 90) / 120) ** 2)
         * smooth(101.2, 102.5, f) * (1 - smooth(110, 118, f)),
         clasp_pop=lambda f: 1 + .02 * pulse(f, 105, 2.0))
fxkit.end_action(arm, act, f0)

# ================================================================== hit: flung up and spun round once, a crash, bling
f0, f1 = CLIPS["hit"]
act = fxkit.begin_action(arm, SID + "_hit")
rest(arm, HAND + RINGB, f0)
for f, sx, sy, y, r in ((204, 1.07, .9, 0, 3), (206, 1.05, .92, 0, 5), (209, .94, 1.08, .75, -55), (213, 1.0, 1.0, 1.05, -200),
                        (218, 1.0, 1.02, .5, -330), (221, .99, 1.01, .04, -360), (222, 1.1, .86, 0, -360),
                        (225, .96, 1.05, .05, -360), (229, 1.02, .985, 0, -360), (233, .995, 1.004, 0, -360),
                        (238, 1, 1, 0, -360), (254, 1, 1, 0, -360)):
    tossk(f, sx=sx, sy=sy, y=y, r=r, plant=f >= 221 or f <= 206)
fxkit.hard(act, "toss", "scale", 1, 222)
fxkit.hard(act, "toss", "location", 1, 222)
for f, r in ((201, 0), (204, 4), (206, 6), (210, -2), (216, 1), (222, -3.5), (228, 2.4), (234, -1.2), (241, .4), (248, 0), (254, 0)):
    key(arm, "hang", f, r=r)
rec = simulate(f0, f1, gain=.28, stiff=2.4, zeta=.3, forces=rattle(221.5, 230, 2))
key_ring(f0, rec, swell=lambda i, f: 1 + .1 * math.exp(-((ring_dist(S[i], S[I_BOTTOM]) - (f - 222) * 110) / 130) ** 2)
         * (1 - smooth(232, 240, f)) + .05 * env(f, [(212, 1)], 3) * (.5 + .5 * math.sin(S[i] / LOOP * 12.57)),
         clasp_pop=lambda f: 1 + .04 * pulse(f, 226, 2.2) - .01 * pulse(f, 230, 2.0))
fxkit.end_action(arm, act, f0)

# ================================================================== multi: it tightens in three pulses, then bursts
f0, f1 = CLIPS["multi"]
act = fxkit.begin_action(arm, SID + "_multi")
rest(arm, HAND + RINGB, f0)
PULSES = (314, 321, 328)
for f, s_ in ((301, 1), (306, .97), (311, 1.0), (314, 1.05), (317, 1.02), (321, 1.08), (324, 1.05), (328, 1.11), (330, 1.1),
              (332, .96), (335, 1.12), (339, .985), (343, 1.005), (346, 1)):
    tossk(f, s=s_, plant=False)
fxkit.hard(act, "toss", "scale", 0, 332); fxkit.hard(act, "toss", "scale", 1, 332)    # the snap into the burst
rnd = random.Random(4)
hk = [(301, 0), (308, 0)]
for f in range(310, 331, 2):
    hk.append((f, rnd.uniform(-1, 1) * (.3 + 1.1 * (f - 310) / 20)))
hk += [(331, 0), (334, -2.5), (339, 1.5), (343, -.5), (346, 0)]
for f, r in hk:
    key(arm, "hang", f, r=r)


BUZZ = 11.0                                              # Hz: the links shiver, alternate ones in and out


def tremble(i, f):
    e = smooth(307, 312, f) * (1 - smooth(329, 332, f)) * (.35 + .65 * smooth(312, 328, f))
    if e <= 0:
        return Vector((0, 0, 0))
    w = 2 * math.pi * BUZZ
    lobe = math.sin(2 * math.pi * 6 * S[i] / LOOP)          # six lobes round the loop, buzzing in and out
    return NORMAL[i] * (.03 * w * w * e * lobe * math.sin(w * (f / FPS)))


def burst(i, f):
    if 332.5 <= f < 334:
        return NORMAL[i] * 110
    return Vector((0, 0, 0))


rec = simulate(f0, f1, gain=.33, stiff=1.5, forces=combine(tremble, burst, rattle(333.5, 60, 3)))
key_ring(f0, rec, swell=lambda i, f: 1 + sum(.08 * bump(S[i] / LOOP - (f - p + 6) / 12, 8) * (smooth(p - 6, p - 3, f) * (1 - smooth(p + 3, p + 6, f)))
                                                for p in PULSES) + .08 * math.exp(-((f - 334) / 2.0) ** 2),
         clasp_pop=lambda f: 1 + .015 * pulse(f, 314, 1.6) + .02 * pulse(f, 321, 1.6) + .025 * pulse(f, 328, 1.6) + .04 * pulse(f, 334, 2.2))
fxkit.end_action(arm, act, f0)

sc.frame_set(1)
bpy.context.view_layer.update()


def at(bone, f, p):
    sc.frame_set(f)
    pb = arm.pose.bones[bone]
    v = arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted() @ vec(*p)
    return v.x, v.z


def path_point(s):
    """The ring's point at distance s round the loop (icon px)."""
    s %= LOOP
    for i in range(N):
        if s <= S[i] + SEG[i] or i == N - 1:
            t = (s - S[i]) / SEG[i]
            (ax, ay), (bx, by) = Q[i], Q[(i + 1) % N]
            return ax + (bx - ax) * t, ay + (by - ay) * t


def path_normal(s):
    s %= LOOP
    i = min(N - 1, max(0, int(s / LOOP * N)))
    return NORMAL[i].x, NORMAL[i].z


# ================================================================== the tier glow: round the outside, and the hole
sc.frame_set(1)
fxkit.neon(SID, arm, FXB, CLIPS, tier=1, bone="hang", outline="outline", land_at=103, hit_span=(206, 246),
           pulses=PULSES, charge_span=(307, 331))
inner = json.load(open(os.path.join(fxkit.ROOT, "art", "blender", "parts", SID, "outline_inner.json")))["points"]
HOLE = fxkit.offset(fxkit.resample([px(x, y) for x, y in inner], 120), .08)    # the sticker's inner edge
hole_ob = gp_object(FXB, SID + "_hole", depth=.3)
ride(hole_ob, arm, "hang")
h_violet = gp_mat(hole_ob, "glow_halo_1", VIOLET)
h_lime = gp_mat(hole_ob, "glow_charge_1", LIME)
h_white = gp_mat(hole_ob, "glow_white", WHITE)
hb = Board()


def hole_level(f):
    """How bright the hole's light burns: following fxkit.neon's tier-1 rim (idle breathing, the landing flare, the
    hit's burn, the multiplier's pulses)."""
    for clip, (a, b) in CLIPS.items():
        if a <= f <= b:
            if clip == "idle":
                return .9 + .2 * math.sin(2 * math.pi * (f - a) / (b - a + 1)), 0.0
            if clip == "land":
                hit = math.exp(-max(0, f - 103) / 3.5) if f >= 103 else (f - a) / 2
                return 1 + 1.4 * hit, .7 * hit
            if clip == "hit":
                lv = 1 + .6 * smooth(a, 210, f) - .6 * smooth(240, b, f)
                return lv, .5 * (lv - 1) / .6
            pulse = sum(math.exp(-((f - p) / 2.2) ** 2) for p in PULSES)
            charged = smooth(307, 311, f) * (1 - smooth(330, 335, f))
            return 1 + 1.2 * pulse + .3 * charged, min(1, pulse + .3 * charged)
    return 1.0, 0.0


for clip, (a, b) in CLIPS.items():
    for f in range(a, b + 1, 1 if clip in ("land", "multi") else 2):
        lv, ch = hole_level(f)

        def fn(dr, lv=lv, ch=ch):
            grow = .85 + .15 * min(lv, 2)
            for r, op in ((.3, .08), (.22, .09), (.15, .11), (.1, .13)):
                stroke(dr, HOLE, r * grow, opacity=min(1, op * lv * (1 - .6 * ch)), mat=h_violet, cyclic=True)
            if ch > .02:
                for r, op in ((.16, .1), (.1, .14), (.065, .18)):
                    stroke(dr, HOLE, r * grow, opacity=min(1, op * ch * lv), mat=h_lime, cyclic=True)
        hb.add(f, fn, 1 if clip in ("land", "multi") else 2)
hb.draw(gp_layer(hole_ob, "aura"))

# ================================================================== effects
sc.frame_set(1)
back = gp_object(FXB, SID + "_back", depth=.35)
ride(back, arm, "toss")
b_lime = gp_mat(back, "glow_lime_fill", LIME, fill=LIME)
b_white = gp_mat(back, "glow_white_fill", WHITE, fill=WHITE)
b_gold = gp_mat(back, "glow_gold_fill", GOLD, fill=GOLD)
b_violet = gp_mat(back, "glow_violet", VIOLET)
b_lime_l = gp_mat(back, "glow_lime", LIME)
bb = Board()
CX, CZ = px(*CENTRE)


def rays(board, f0, life, cx, cz, r0, r1, mats, n=14, rot=.15, seed=0, width=.16):
    """A burst of light rays opening out round (cx, cz): filled wedges that lengthen and thin to needles as they burn
    out (no disc in the middle: it would glow through the hole)."""
    rnd = random.Random(seed)
    lens = [rnd.uniform(.7, 1.0) for _ in range(n)]
    for k in range(life):
        t = k / max(1, life - 1)
        for i in range(n):
            a = rot + 2 * math.pi * i / n + .25 * t
            rt = r0 + (r1 - r0) * lens[i] * t ** .55
            rb = r0 * .85 + (rt - r0 * .85) * .35 * t
            hw = width * (1 - t) ** 1.3 + .012
            mat = mats[i % len(mats)]
            pts = [(cx + math.cos(a) * rb - math.sin(a) * hw, cz + math.sin(a) * rb + math.cos(a) * hw),
                   (cx + math.cos(a) * rt, cz + math.sin(a) * rt),
                   (cx + math.cos(a) * rb + math.sin(a) * hw, cz + math.sin(a) * rb - math.cos(a) * hw)]
            board.add(f0 + k, lambda dr, pts=pts, mat=mat: stroke(dr, pts, .004, mat=mat, cyclic=True, fill=True, line=False))


rays(bb, 222, 12, CX, CZ, 3.4, 6.2, (b_gold, b_white, b_lime), n=16, seed=2)
rays(bb, 333, 12, CX, CZ, 3.4, 6.2, (b_lime, b_white, b_gold), n=18, rot=.3, seed=6, width=.2)
fxkit.shock_rings(bb, 333, CX, CZ, 4.4, 6.3, (b_violet, b_lime_l, b_violet), life=10, lag=2)   # gone by 346
bb.draw(gp_layer(back, "burst"))

on_loop = gp_object(FX, SID + "_fx_loop", depth=-.8)     # rides the loop's top: glints, clinks, lightning
ride(on_loop, arm, "hang")
on_clasp = gp_object(FX, SID + "_fx_clasp", depth=-.85)  # rides the clasp: its bling
ride(on_clasp, arm, "clasp")
world = gp_object(FX, SID + "_fx", depth=-.8)            # stays where the frame is
l_white = gp_mat(on_loop, "fx_white_fill", WHITE, fill=WHITE)
l_gold = gp_mat(on_loop, "fx_gold_fill", GOLD, fill=GOLD)
l_white_l = gp_mat(on_loop, "fx_white_line", WHITE)
l_gold_l = gp_mat(on_loop, "fx_gold_line", GOLD)
l_lime_l = gp_mat(on_loop, "fx_lime_line", LIME)
c_white = gp_mat(on_clasp, "fx_white_fill", WHITE, fill=WHITE)
c_gold = gp_mat(on_clasp, "fx_gold_fill", GOLD, fill=GOLD)
w_white = gp_mat(world, "fx_white_line", WHITE)
w_gold = gp_mat(world, "fx_gold_line", GOLD)
w_lime = gp_mat(world, "fx_lime_line", LIME)
w_whitef = gp_mat(world, "fx_white_fill", WHITE, fill=WHITE)
w_goldf = gp_mat(world, "fx_gold_fill", GOLD, fill=GOLD)
w_limef = gp_mat(world, "fx_lime_fill", LIME, fill=LIME)
loop_b, clasp_b, world_b = Board(), Board(), Board()
CLX, CLZ = px(*CLASP_C)


def bling(board, f0, life, size, seed=0, mats=(c_white, c_gold)):
    """The clasp catches the light: a long four-point flare over a smaller turned star, opening and shrinking away."""
    for k in range(life):
        t = k / max(1, life - 1)
        r = size * math.sin(math.pi * min(1.0, t * 1.08)) ** .8
        if r < .02:
            continue
        a = .3 + .5 * t + seed
        board.add(f0 + k, lambda dr, r=r, a=a: (
            stroke(dr, star(CLX, CLZ, r, a, points=4, inner=.09), .004, mat=mats[0], cyclic=True, fill=True, line=False),
            stroke(dr, star(CLX, CLZ, r * .48, a + math.pi / 4, points=4, inner=.2), .004, mat=mats[1], cyclic=True, fill=True, line=False)))


def clinks(board, f0, n, seed, life=4, size=.32):
    """Links knocking together: little ticks of light flashing out of the loop here and there."""
    rnd = random.Random(seed)
    for j in range(n):
        s = rnd.uniform(0, LOOP)
        x, y = path_point(s)
        nx, nz = path_normal(s)
        X, Z = px(x, y)
        X, Z = X + nx * .42, Z + nz * .42
        fs = f0 + rnd.randint(0, 3)
        mat = l_white_l if j % 2 else l_gold_l
        for k in range(life):
            t = k / max(1, life - 1)
            for a in (-.55, 0, .55):
                aa = math.atan2(nz, nx) + a
                r0, r1 = size * (.25 + .5 * t), size * (.55 + .6 * t)
                board.add(fs + k, lambda dr, X=X, Z=Z, aa=aa, r0=r0, r1=r1, t=t, mat=mat: stroke(
                    dr, [(X + math.cos(aa) * r0, Z + math.sin(aa) * r0), (X + math.cos(aa) * r1, Z + math.sin(aa) * r1)],
                    .03 * (1 - t) + .008, mat=mat))


# idle: glints ride the swell round the links; the clasp's gleam
for f in range(CLIPS["idle"][0], CLIPS["idle"][1] + 1):
    u = (f - CLIPS["idle"][0]) / n_idle
    s = u * LOOP
    x, y = path_point(s)
    nx, nz = path_normal(s)
    X, Z = px(x, y)
    e = idle_env(f)
    u = (f - SWELL_ON[0]) / (SWELL_ON[1] - SWELL_ON[0])
    x, y = path_point(u * LOOP)
    nx, nz = path_normal(u * LOOP)
    X, Z = px(x, y)
    r = (.2 + .1 * math.sin(f * .9)) * e
    if f % 3 == 0 or r < .03:
        continue
    loop_b.add(f, lambda dr, X=X, Z=Z, nx=nx, nz=nz, r=r, f=f: stroke(dr, star(X + nx * .3, Z + nz * .3, r, f * .2), .004,
                                                                       mat=l_white, cyclic=True, fill=True, line=False))
bling(clasp_b, 57, 11, .75)
fxkit.sparkle(loop_b, 20, 8, *px(176, 196), .34, l_white, rot0=.2)          # the art's own stars twinkle
fxkit.sparkle(loop_b, 40, 8, *px(782, 508), .3, l_gold, rot0=.5)

# land: clinks, gold glitter kicked up at the bottom, lime ticks
clinks(loop_b, 102, 9, 1)
BX, BZ = px(690, BOTTOM_Y + 12)
rnd = random.Random(11)
for i in range(10):
    a = math.radians(rnd.uniform(20, 160))
    sp = rnd.uniform(2.2, 4.2)
    life = rnd.randint(9, 13)
    for k in range(life):
        t = k / FPS
        x, z = BX + math.cos(a) * sp * t * (1.4 if i % 2 else .9) + (i - 5) * .22, BZ + math.sin(a) * sp * t - 9 * t * t
        rr = .17 * math.sin(math.pi * min(1, k / (life - 1)))
        if rr > .02:
            world_b.add(102 + k, lambda dr, x=x, z=z, rr=rr, k=k, i=i: stroke(dr, star(x, z, rr, k * .4 + i), .004,
                                                                             mat=w_goldf if i % 3 else w_whitef, cyclic=True, fill=True, line=False))
for k, f in enumerate(range(102, 108)):
    t = k / 5
    for s_, x0 in ((-1, px(380, 0)[0]), (1, px(860, 0)[0])):
        world_b.add(f, lambda dr, s_=s_, x0=x0, t=t: stroke(dr, [(x0 + s_ * (.3 + 1.2 * t), BZ - .02), (x0 + s_ * (.8 + 1.8 * t), BZ + .14 * t)],
                                                           .035 * (1 - t) + .008, mat=w_lime))

# hit: speed arcs trail the spin, sparks fly off it, the crash clinks, the clasp blings, sparkles everywhere
def at_sub(bone, fr, p):
    """at(), between frames."""
    sc.frame_set(int(math.floor(fr)), subframe=fr - math.floor(fr))
    pb = arm.pose.bones[bone]
    v = arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted() @ vec(*p)
    return v.x, v.z


for f in range(209, 221):
    for j, (ex, ey) in enumerate(((122, 320), (848, 640), (560, 345), (530, 715))):
        pts = []
        for m in range(13):                              # where this end of the loop was over the last frames
            fb = max(201.0, f - m * .3)
            pts.append(at_sub("hang", fb, (ex, ey)))
        world_b.add(f, lambda dr, pts=pts, j=j: stroke(dr, pts, 0, radii=fxkit.taper(len(pts), .06, ends=.45),
                                                       mat=(w_white, w_gold)[j % 2]))
rnd = random.Random(5)
for i in range(14):
    f = 210 + int(i * 10 / 14)
    s = rnd.uniform(0, LOOP)
    x, z = at("hang", f, path_point(s))
    x1, z1 = at("hang", f + 1, path_point(s))
    vx, vz = (x1 - x) * FPS * 1.2, (z1 - z) * FPS * 1.2
    for k in range(9):
        t = k / FPS
        X, Z = x + vx * t, z + vz * t - 6 * t * t
        if abs(X) > 6.1 or abs(Z) > 6.1:
            break
        rr = .2 * (1 - k / 9) + .03
        world_b.add(f + k, lambda dr, X=X, Z=Z, rr=rr, k=k, i=i: stroke(dr, star(X, Z, rr, k * .5 + i), .004,
                                                                       mat=w_goldf if i % 2 else w_whitef, cyclic=True, fill=True, line=False))
clinks(loop_b, 222, 12, 2)
bling(clasp_b, 224, 14, 1.25)
for i in range(11):
    fxkit.sparkle(world_b, 226 + rnd.randint(0, 18), rnd.randint(6, 9), rnd.uniform(-5.4, 5.4), rnd.uniform(-4.4, 4.8),
                  rnd.uniform(.24, .46), w_goldf if i % 3 else w_whitef, rot0=rnd.uniform(0, 1))

# multi: lightning arcs across the hole and crackles off the links, the burst clinks and blings
inner_pts = [px(x, y) for x, y in inner]
for f in range(309, 331, 2):
    rr = random.Random(f * 5)
    for j in range(2):
        a = rr.randrange(len(inner_pts))
        b = (a + len(inner_pts) // 2 + rr.randint(-6, 6)) % len(inner_pts)
        p0, p1 = inner_pts[a], inner_pts[b]
        loop_b.add(f, lambda dr, p0=p0, p1=p1, f=f, j=j: stroke(dr, fxkit.zigzag(*p0, *p1, n=9, amp=.3, seed=f * 7 + j), 0,
                                                                radii=fxkit.taper(10, .045, ends=.2),
                                                                mat=l_lime_l if j == 0 else l_white_l), hold=2)
    for j in range(2):
        s = rr.uniform(0, LOOP)
        x, y = path_point(s)
        nx, nz = path_normal(s)
        X, Z = px(x, y)
        loop_b.add(f, lambda dr, X=X, Z=Z, nx=nx, nz=nz, f=f, j=j: stroke(
            dr, fxkit.zigzag(X + nx * .45, Z + nz * .45, X + nx * 1.25, Z + nz * 1.25, n=5, amp=.16, seed=f * 11 + j), 0,
            radii=fxkit.taper(6, .04, ends=.25), mat=l_white_l if j else l_lime_l), hold=2)
for p in PULSES:
    bling(clasp_b, p - 2, 6, .5 + .15 * PULSES.index(p))
clinks(loop_b, 333, 12, 3)
bling(clasp_b, 333, 13, 1.35, mats=(c_white, c_gold))
fxkit.streaks(world_b, 334, 8, CX, CZ, 4.0, 6.1, (w_white, w_lime, w_gold), n=16, rot=.15, width=.045)
for i in range(7):                                       # every one done by 345: nothing pops when the clip ends
    fxkit.sparkle(world_b, 337 + rnd.randint(0, 2), rnd.randint(6, 7), rnd.uniform(-5, 5), rnd.uniform(-4, 4.6), rnd.uniform(.28, .45),
                  w_limef if i % 2 else w_whitef, rot0=rnd.uniform(0, 1))

loop_b.draw(gp_layer(on_loop, "fx"))
clasp_b.draw(gp_layer(on_clasp, "fx"))
world_b.draw(gp_layer(world, "fx"))

sc.frame_start, sc.frame_end = 1, max(b for a, b in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], "| saved", fxkit.save(SID))
