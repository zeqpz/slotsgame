# L8 - the zip bag of buds - animated in Blender: four Actions on its rig (idle, land, hit, multi) laid one after
# another on the rig's NLA track, and its effects drawn frame by frame in Grease Pencil.
#   the rig     the bag is ONE image (tools/blender/cuts/L8.py) on a fine mesh skinned to its bones: the root (it
#               squashes on its bottom), the bag (it sways and shakes about its middle), the belly (it breathes:
#               weighted most in the middle of the plastic, least at the corners, so the bag bulges like a pillow),
#               the pile of buds (it slumps, lags and bounces inside the bag, the plastic round it giving), a bone
#               for each loose bud round the pile's edge (a soft local weight: the bud hops, its neighbours shift a
#               little with it, the plastic's creases over it crinkle) and the seal - a chain of bones each way from
#               its middle, so the zip flexes and its corners flick
#   idle        a stuffed bag, breathing and rocking: it fills slowly while it rocks on its bottom, lets the breath out
#               and flumps down (a squash, the pile slumping, the buds settling one after another); its top trails
#               the rock, the pile sloshes behind it, the zip swings loose and lifts its corners; a glint slides over
#               the plastic at the top of the breath, the out-breath lets a curl of aroma and a little leaf out of
#               the seal (previous idle: anim_L8.orig.py.txt)
#   land        set down: it squashes on its bottom, the pile slumps after it and the buds jiggle, the seal flicks,
#               the squeeze pushes a puff out of the seal
#   hit         it crouches and hops, the buds float up inside it and crash back when it lands, then it gets a
#               shake: the pile sloshes, the seal flaps and a cloud of aroma bursts out; the plastic glints
#   multi       pumped up in three pulses: it balloons (the whole bag puffing out, its belly most), the seal strains
#               and leaks a curl each pulse, the pile floats up and the buds spread apart, motes gathering and racing
#               round it; then the seal pops - a flash and quick rays at the zip, a fountain of aroma, a smoke ring
#               blown out round the top, leaf flecks everywhere - and the bag flops back with a wobble
#   effects     aroma puffs, curls and a smoke ring out of the seal, leaf flecks, glints and shines on the plastic,
#               the multi's motes and pop - its own effects (a low symbol: no tier glow)
# Runs INSIDE Blender, after build_symbol_scene.py (tools/blender/run.py runs both in a background Blender).
import bpy, importlib, math, os, random, sys
from mathutils import Matrix, Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
import fxkit
importlib.reload(fxkit)
from fxkit import (key, rest, px, smooth, gp_object, gp_mat, gp_layer, ride, stroke, star, puff, Board, WHITE, LIME, GOLD)

SID = "L8"
sc, arm, spec = fxkit.setup(SID)
FPS = sc.render.fps
W, H = spec["size"]
PARTS = {p["name"]: p for p in spec["parts"]}


# ================================================================== the skin (this symbol's rig helpers)
def wpt(x, y):
    """icon px -> rig space (the icon centred on the origin, z up)"""
    return Vector(((x - W / 2) / 100.0, 0.0, (H / 2 - y) / 100.0))


def sstep(e0, e1, v):
    t = max(0.0, min(1.0, (v - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def add_bones(defs):
    """(name, head px, tail px or None, parent[, connect]) - a bone with no tail points up (x/y keys move it
    right/up); a bone with a tail lies along it (a chain), its turn in the picture its rotation."""
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    for name, head, tail, parent, *conn in defs:
        b = eb.get(name) or eb.new(name)
        b.head = wpt(*head)
        if tail is None:
            b.tail = b.head + Vector((0, 0, .6))
            b.roll = 0
        else:
            b.tail = wpt(*tail)
            b.align_roll(Vector((0, -1, 0)))
        b.parent = eb[parent] if parent else None
        b.use_connect = bool(conn and conn[0])
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"


def skin(name, weights, cell=6):
    """The part's plane becomes a fine grid on the icon's own lattice (cells at multiples of `cell` px), skinned to
    the rig: weights(x, y) -> {bone: weight} (icon px; they sum to 1)."""
    p = PARTS[name]
    ob = bpy.data.objects[SID + "_" + name]
    x0, y0, x1, y1 = p["box"]
    gx0, gy0 = math.floor(x0 / cell) * cell, math.floor(y0 / cell) * cell
    nx, ny = math.ceil((x1 - gx0) / cell), math.ceil((y1 - gy0) / cell)
    verts, uvs, pts = [], [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x, y = gx0 + i * cell, gy0 + j * cell
            v = wpt(x, y)
            verts.append((v.x, 0.0, v.z))
            uvs.append(((x - x0) / (x1 - x0), 1 - (y - y0) / (y1 - y0)))
            pts.append((x, y))
    faces = []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a + nx + 1, a + nx + 2, a + 1, a))
    me = bpy.data.meshes.new(SID + "_" + name + "_skin")
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new()
    for poly in me.polygons:
        for li in poly.loop_indices:
            uv.data[li].uv = uvs[me.loops[li].vertex_index]
    me.materials.append(ob.data.materials[0])
    old = ob.data
    ob.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    depth = -0.1 * (p["draw"] + 1)
    ob.parent = arm
    ob.parent_type = "OBJECT"
    ob.matrix_parent_inverse = Matrix.Identity(4)
    ob.matrix_world = Matrix.Translation((0, depth, 0))
    ob.vertex_groups.clear()
    groups = {}
    for vi, (x, y) in enumerate(pts):
        for bone, wt in weights(x, y).items():
            if wt > 1e-4:
                if bone not in groups:
                    groups[bone] = ob.vertex_groups.new(name=bone)
                groups[bone].add([vi], wt, "REPLACE")
    for m in list(ob.modifiers):
        ob.modifiers.remove(m)
    mod = ob.modifiers.new("rig", "ARMATURE")
    mod.object = arm
    mod.use_vertex_groups = True
    return ob


def chain_w(ch, x, y, blend):
    """weights of a chain's bones for a point (icon px): where it falls along the chain, blended over `blend` px
    across each joint (the same rule build_symbol_scene.py uses for a bending part)"""
    best, s_at, acc, joints = None, 0.0, 0.0, [0.0]
    for i in range(len(ch) - 1):
        (ax, ay), (bx, by) = ch[i], ch[i + 1]
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy)
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (L * L)))
        d = math.hypot(ax + dx * t - x, ay + dy * t - y)
        if best is None or d < best:
            best, s_at = d, acc + t * L
        acc += L
        joints.append(acc)
    n = len(ch) - 1
    out = []
    for i in range(n):
        lo = 1.0 if i == 0 else sstep(joints[i] - blend / 2, joints[i] + blend / 2, s_at)
        hi = 1.0 if i == n - 1 else 1 - sstep(joints[i + 1] - blend / 2, joints[i + 1] + blend / 2, s_at)
        out.append(lo * hi)
    tot = sum(out) or 1.0
    return [v / tot for v in out]


def inside(poly, x, y):
    c = False
    for i in range(len(poly)):
        (ax, ay), (bx, by) = poly[i - 1], poly[i]
        if (ay > y) != (by > y) and x < ax + (bx - ax) * (y - ay) / (by - ay):
            c = not c
    return c


def sdist(poly, x, y):
    """signed distance to a closed polygon, px: negative inside"""
    d = min(math.hypot(ax + (bx - ax) * t - x, ay + (by - ay) * t - y)
            for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1])
            for t in [max(0.0, min(1.0, ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / max(1e-9, (bx - ax) ** 2 + (by - ay) ** 2)))])
    return -d if inside(poly, x, y) else d


def keys(bone, f0, vals, channel, tol, loop=False):
    fxkit.key_series(arm, bone, f0, vals, channel=channel, tol=tol, loop=loop)


def hop(f, at, dur=11, amp=1.0):
    """a jostle: up quick, down past rest, a little bounce, still - 0 outside [at, at + dur]"""
    t = (f - at) / dur
    if t <= 0 or t >= 1:
        return 0.0
    return amp * math.sin(math.pi * min(1, t / .38)) if t < .38 else amp * (-.32 * math.sin(math.pi * (t - .38) / .34) if t < .72
                                                                            else .1 * math.sin(math.pi * (t - .72) / .28))


# ================================================================== the rig
BOTTOM = (505, 893)
MID = (505, 560)
PILE_C = (505, 555)
SEAL_C = (520, 207)
ZIP_L = [SEAL_C, (350, 192), (172, 158)]          # the zip line, from its middle out to each corner
ZIP_R = [SEAL_C, (680, 182), (826, 118)]
BUDS = {"bud_top": ((585, 355), 44), "bud_ur": ((668, 418), 38), "bud_r": ((736, 535), 46), "bud_br": ((692, 660), 46),
        "bud_b": ((572, 712), 44), "bud_bl": ((350, 718), 46), "bud_l": ((268, 532), 46), "bud_ul": ((405, 395), 40)}
# the pile's outline (icon px), loosely: the plastic round it gives as the pile moves
PILE = [(205, 600), (230, 520), (262, 478), (300, 440), (330, 415), (360, 380), (400, 362), (450, 345), (500, 330), (545, 312),
        (585, 302), (622, 330), (650, 380), (690, 372), (708, 420), (722, 462), (766, 480), (792, 530), (792, 592), (762, 612),
        (752, 652), (742, 702), (700, 732), (650, 732), (620, 762), (600, 797), (568, 797), (530, 762), (480, 737), (440, 762),
        (400, 782), (330, 792), (288, 770), (270, 700), (285, 652), (250, 632), (210, 612)]
RED = [(160, 157), (300, 185), (400, 200), (500, 207), (575, 205), (650, 190), (750, 155), (840, 112)]   # the red zip line


def red_y(x):
    for (ax, ay), (bx, by) in zip(RED, RED[1:]):
        if x <= bx:
            return ay + (by - ay) * max(0.0, (x - ax) / (bx - ax))
    return RED[-1][1]


defs = [("root", BOTTOM, None, None), ("bag", MID, None, "root"), ("belly", MID, None, "bag"), ("pile", PILE_C, None, "bag")]
defs += [(n, c, None, "pile") for n, (c, _) in BUDS.items()]
for side, ch in (("zip_l", ZIP_L), ("zip_r", ZIP_R)):
    for i in range(len(ch) - 1):
        defs.append((f"{side}.{i}", ch[i], ch[i + 1], "bag" if i == 0 else f"{side}.{i - 1}", i > 0))
add_bones(defs)


def bag_weights(x, y):
    w = {}
    s = 1 - sstep(red_y(x) + 32, red_y(x) + 92, y)                 # the seal band (and the plastic above it)
    if s > 0:
        side = sstep(SEAL_C[0] - 34, SEAL_C[0] + 34, x)             # left / right of the zip's middle
        for name, ch, k in (("zip_l", ZIP_L, 1 - side), ("zip_r", ZIP_R, side)):
            if k * s > 0:
                for i, cw in enumerate(chain_w(ch, x, y, 70)):
                    w[f"{name}.{i}"] = w.get(f"{name}.{i}", 0) + s * k * cw
    rest_ = 1 - s
    q = 1 - sstep(-6, 40, sdist(PILE, x, y)) if rest_ > 0 else 0.0  # in the pile, fading out into the plastic
    if rest_ * q > 0:
        beta = {n: math.exp(-((x - c[0]) ** 2 + (y - c[1]) ** 2) / (2 * sg * sg)) for n, (c, sg) in BUDS.items()}
        B = sum(beta.values())
        if B > .9:
            beta = {n: b * .9 / B for n, b in beta.items()}
        for n, b in beta.items():
            if b > 1e-3:
                w[n] = rest_ * q * b
        w["pile"] = rest_ * q * (1 - sum(b for b in beta.values() if b > 1e-3))
    if rest_ * (1 - q) > 0:
        r = math.hypot((x - MID[0]) / 430, (y - MID[1]) / 390)
        b = max(0.0, 1 - r * r) ** 1.3                                # the belly: most in the middle, none at the corners
        w["belly"] = rest_ * (1 - q) * b
        w["bag"] = rest_ * (1 - q) * (1 - b)
    tot = sum(w.values())
    return {k: v / tot for k, v in w.items()}


skin("bag", bag_weights)
ZIP_BONES = [f"{s}.{i}" for s in ("zip_l", "zip_r") for i in range(2)]
BONES = ["root", "bag", "belly", "pile"] + list(BUDS) + ZIP_BONES

ART, FXB, FX = fxkit.layers(sc, SID)
fxkit.glow_compositor(sc, SID, back=dict(strength=.7, size=.5, gain=1.3), front=dict(strength=.8, size=.42, gain=1.4))
if arm.animation_data:
    arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)

CLIPS = {"idle": (1, 84), "land": (101, 124), "hit": (201, 254), "multi": (301, 348)}
arm["clips"] = {k: list(v) for k, v in CLIPS.items()}
# the seal's flex: stiff springs (it is the bag's firm edge), the corners a little softer
SEAL = {"zip_l": dict(chain=ZIP_L, freq=[4.2, 3.4], zeta=.3, gain=.55, limit=5),
        "zip_r": dict(chain=ZIP_R, freq=[4.0, 3.2], zeta=.28, gain=.55, limit=5)}


def seal(f0, f1, loop=False, forces=None, gain=1.0):
    res = fxkit.secondary(sc, arm, "bag", f0, f1, SEAL, loop=loop, forces=forces, gain=gain)
    print(f"  seal {f0}-{f1}:", ", ".join(f"{b} {min(v):+.1f}..{max(v):+.1f}" for b, v in res.items()))
    for bone, vals in res.items():
        keys(bone, f0, vals, "r", .15, loop=loop)


def bud_keys(f0, n, plan, loop=False):
    """plan: {bud: [(frame, dx px, dy px, deg, dur)]} - each bud's hops, keyed per frame (a loop ends on its start)"""
    for b in BUDS:
        xs, ys, rs = [], [], []
        for k in range(n):
            f = f0 + k
            x = y = r = 0.0
            for at, dx, dy, deg, dur in plan.get(b, []):
                for lap in ((-n, 0, n) if loop else (0,)):
                    h = hop(f + lap, at, dur)
                    x += h * dx / 100; y += h * dy / 100; r += h * deg
            xs.append(x); ys.append(y); rs.append(r)
        if any(abs(v) > 1e-6 for v in xs + ys + rs):
            keys(b, f0, xs, "x", .0012, loop)
            keys(b, f0, ys, "y", .0012, loop)
            keys(b, f0, rs, "r", .1, loop)


# ================================================================== idle: a stuffed bag, breathing and rocking
# One slow breath and one lazy rock a loop (84 frames). It fills (slow in, a held beat at the top) while it rocks
# right and back, then lets the breath out quicker as it rocks left, and flumps down onto its bottom: a little
# squash, the pile slumping after it, the buds settling one after another round it. Everything soft follows a few
# frames behind what drives it: the top of the bag lags the rock (it pivots on its bottom, its middle bends), the
# pile sloshes behind the lean and stays more upright than the plastic, the buds drift against each other, the zip
# hangs on looser springs than in the jolts of the other clips and its corners lift as the bag fills.
# Every channel is a function of the loop's own frames (so it joins itself exactly) and starts on the rest pose
# (what a lagging channel still holds at frame 0 is eased out over the lap - unpin).
# Effects: a glint slides over the plastic at the top of the breath and twinkles out at the corner; the out-breath
# lets a curl of aroma out of the seal with a little leaf riding up on it.
f0, f1 = CLIPS["idle"]
N = f1 - f0 + 1
T = N / FPS
act = fxkit.begin_action(arm, SID + "_idle")
rest(arm, BONES, f0)
SWAY = 3.0                                             # degrees, the rock at its widest


def circ_smooth(vals, sigma):
    """a periodic series smoothed with a circular gaussian (sigma in frames)"""
    n = len(vals)
    ker = [math.exp(-.5 * (d / sigma) ** 2) for d in range(-3 * int(sigma + 1), 3 * int(sigma + 1) + 1)]
    h = len(ker) // 2
    tot = sum(ker)
    return [sum(ker[j] * vals[(i + j - h) % n] for j in range(len(ker))) / tot for i in range(n)]


def _breath_raw(t):
    if t < .5:                                         # in: slow, easing into the top
        return .5 - .5 * math.cos(math.pi * t / .5)
    if t < .58:                                        # held a beat
        return 1.0
    if t < .8:                                         # out: quicker
        return .5 + .5 * math.cos(math.pi * (t - .58) / .22)
    return 0.0


BR = circ_smooth([_breath_raw(k / N) for k in range(N)], 2.2)
FL = circ_smooth([math.exp(-.5 * (min(abs(k - .84 * N), N - abs(k - .84 * N)) / 2.6) ** 2) for k in range(N)], 1.0)  # the flump


def per(arr, k):
    """a periodic table read at any (fractional) frame"""
    k = k % N
    i = int(math.floor(k))
    u = k - i
    return arr[i % N] * (1 - u) + arr[(i + 1) % N] * u


def br(k):
    return per(BR, k)


def fl(k):
    return per(FL, k)


def sway(k):
    """the rock, -1..1 (right = +): right first, back through upright at the top of the breath, left on the out-breath.
    Its clock eases through the loop's start (upright, the breath out: the rest pose), so the bag hangs there a
    moment before it pushes off again - and the one-shots, which end at rest, hand over to it without a jolt"""
    ph = 2 * math.pi * k / N
    c = ph - .72 * math.sin(ph)
    return math.sin(c) + .14 * math.sin(2 * c)


def unpin(vals, base=0.0):
    """a periodic series made to start exactly at `base`: the offset at frame 0 eased out over the lap"""
    v0 = vals[0] - base
    return [v - v0 * (.5 + .5 * math.cos(2 * math.pi * k / N)) for k, v in enumerate(vals)]


ch = {}


def put(bone, c, v):
    ch.setdefault((bone, c), []).append(v)


BUD_LAG = {"bud_top": 5, "bud_ur": 7, "bud_r": 9, "bud_br": 8, "bud_b": 10, "bud_bl": 9, "bud_l": 7, "bud_ul": 6}
for k in range(N):
    b, q, s = br(k), fl(k), sway(k)
    # the whole bag: it fills taller and a touch wider, flumps onto its bottom, rocks on it (rolling with the rock)
    put("root", "sx", 1 + .012 * b + .03 * q)
    put("root", "sy", 1 + .028 * b - .042 * q)
    put("root", "r", -SWAY * s)
    put("root", "x", .03 * s)
    # its middle bends behind the rock: the top of the bag trails it
    put("bag", "r", -.55 * SWAY * (sway(k - 5) - s))
    # the belly puffs out like a pillow, a frame behind the breath
    put("belly", "sx", 1 + .062 * br(k - 1) + .012 * fl(k - 1))
    put("belly", "sy", 1 + .04 * br(k - 1) - .01 * fl(k - 1))
    # the pile: lifts a little on the breath, sloshes behind the lean (and stays more upright than the plastic),
    # slumps after the flump
    put("pile", "x", .05 * sway(k - 6))
    put("pile", "y", .018 * br(k - 4) - .045 * fl(k - 2))
    put("pile", "r", .4 * SWAY * sway(k - 4))
    put("pile", "sx", 1 + .02 * fl(k - 2))
    put("pile", "sy", 1 - .03 * fl(k - 2) + .008 * br(k - 4))
    # the buds drift against each other behind the slosh (each a little later the further down the pile it sits)
    for bn, d in BUD_LAG.items():
        cx, cy = BUDS[bn][0]
        ox = (cx - PILE_C[0]) / 260
        put(bn, "x", .022 * (sway(k - d) - sway(k - 5)))
        put(bn, "y", .012 * (br(k - d) - br(k - 4)) * (1 if cy < PILE_C[1] else .5))
        put(bn, "r", 3.0 * (sway(k - d) - sway(k - 4)) * (1 if ox >= 0 else -1))

# the flump settles the buds: one after another round the pile, top first, each dropping and bouncing back
SETTLE = {"bud_top": (0, -1, -6, -7), "bud_ul": (1, -2, -5, 6), "bud_ur": (2, 2, -5, -6), "bud_l": (3, 2, -6, 7),
          "bud_r": (4, -2, -6, -6), "bud_bl": (5, 2, -5, 6), "bud_br": (6, -2, -5, -5), "bud_b": (7, 0, -4, 5)}
AT = round(.84 * N) - 1
for bn, (d, dx, dy, deg) in SETTLE.items():
    for key_ in ("x", "y", "r"):
        vals = ch[(bn, key_)]
        for k in range(N):
            h = sum(hop(k + lap, AT + round(d * .85), 11) for lap in (-N, 0, N))
            vals[k] += h * {"x": dx / 100, "y": dy / 100, "r": deg}[key_]

for (bone, c), vals in ch.items():
    ch[(bone, c)] = unpin(vals, 1.0 if c in ("sx", "sy") else 0.0)
for bone in sorted({b_ for b_, _ in ch}):              # keyed together per bone, every frame round the loop
    for k in range(N + 1):
        kw = {c: ch[(bone, c)][k % N] for b_, c in ch if b_ == bone}
        for a, z in (("x", "y"), ("y", "x"), ("sx", "sy"), ("sy", "sx")):
            if a in kw and z not in kw:
                kw[z] = 1.0 if z[0] == "s" else 0.0
        key(arm, bone, f0 + k, **kw)
print("  idle peaks:", ", ".join(f"{b_}.{c} {min(v):+.3f}..{max(v):+.3f}" for (b_, c), v in ch.items() if not b_.startswith("bud")))

# the zip on looser springs than in the jolts (it hangs off the bag's real motion), its corners lifting as the bag
# fills and dropping on the flump; kept in step with the rock that drives it and started at rest
LOOSE = {"zip_l": dict(SEAL["zip_l"], freq=[2.9, 2.4], zeta=.24, gain=.8, limit=4),
         "zip_r": dict(SEAL["zip_r"], freq=[2.7, 2.25], zeta=.23, gain=.8, limit=4)}
BR_MEAN = sum(BR) / N


def breath(name, i, t):
    k = t * FPS
    a = 26 * (br(k) - BR_MEAN) - 14 * fl(k - 1)
    return Vector((0, 0, a * (1 if i == 2 else .4)))


res = fxkit.secondary(sc, arm, "bag", f0, f1, LOOSE, loop=True, forces=breath, rest_start=False)
for bone, vals in res.items():
    vals = unpin(vals)
    print(f"  idle {bone} {min(vals):+.1f}..{max(vals):+.1f}")
    keys(bone, f0, vals, "r", .08, loop=True)
fxkit.make_cyclic(act)
fxkit.end_action(arm, act, f0)

# ================================================================== land: squashes on its bottom, the pile slumps after it
f0, f1 = CLIPS["land"]
act = fxkit.begin_action(arm, SID + "_land")
rest(arm, BONES, f0)
for f, sx, sy in ((f0 + 2, 1.075, .9), (f0 + 6, .965, 1.045), (f0 + 10, 1.02, .985), (f0 + 14, .995, 1.004), (f0 + 19, 1, 1), (f1, 1, 1)):
    key(arm, "root", f, sx=sx, sy=sy)
fxkit.hard(act, "root", "scale", 1, f0 + 2)
for f, y, sy in ((f0 + 2, .03, 1.0), (f0 + 5, -.075, .955), (f0 + 9, .03, 1.02), (f0 + 13, -.012, .995), (f0 + 18, 0, 1), (f1, 0, 1)):
    key(arm, "pile", f, y=y, sy=sy)
for f, s in ((f0 + 3, .985), (f0 + 7, 1.02), (f0 + 12, 1.0), (f1, 1)):
    key(arm, "belly", f, s=s)
bud_keys(f0, f1 - f0 + 1, {"bud_top": [(f0 + 5, 2, 6, -7, 10)], "bud_ur": [(f0 + 6, 4, 4, -6, 9)], "bud_r": [(f0 + 5, 5, 3, -5, 10)],
                           "bud_br": [(f0 + 7, 3, 3, -4, 9)], "bud_b": [(f0 + 6, -2, 4, 5, 9)], "bud_bl": [(f0 + 7, -3, 4, 5, 10)],
                           "bud_l": [(f0 + 6, -5, 3, 6, 10)], "bud_ul": [(f0 + 5, -3, 5, 6, 9)]})
seal(f0, f1, gain=.5)
rest(arm, ["root", "bag", "belly", "pile"], f1)
fxkit.end_action(arm, act, f0)

# ================================================================== hit: crouch, hop, the buds float and crash, a shake
f0, f1 = CLIPS["hit"]
act = fxkit.begin_action(arm, SID + "_hit")
rest(arm, BONES, f0)
UP, LAND = f0 + 12, f0 + 20
for f, sx, sy, y in ((f0 + 4, 1.1, .875, 0), (f0 + 8, .91, 1.11, .62), (UP, .985, 1.02, 1.25), (f0 + 16, 1.0, 1.0, .95),
                     (LAND, 1.12, .87, 0), (f0 + 24, .96, 1.05, .06), (f0 + 28, 1.02, .985, 0), (f0 + 33, 1, 1, 0), (f1, 1, 1, 0)):
    key(arm, "root", f, sx=sx, sy=sy, y=y)
fxkit.hard(act, "root", "location", 1, LAND)
for f, r in ((f0 + 22, 0), (f0 + 25, 5.2), (f0 + 29, -4.6), (f0 + 33, 3.4), (f0 + 37, -2.0), (f0 + 41, .8), (f0 + 45, 0), (f1, 0)):
    key(arm, "bag", f, r=r)
# the pile: sinks in the crouch, lags as it leaps, floats at the top, slams down on the landing, sloshes in the shake
for f, x, y, sy in ((f0 + 4, 0, -.03, .97), (f0 + 8, 0, -.085, .95), (UP, 0, .025, 1.03), (f0 + 17, 0, .05, 1.02),
                    (LAND + 1, 0, -.1, .93), (f0 + 24, 0, .035, 1.03), (f0 + 26, -.04, -.01, 1), (f0 + 30, .045, 0, 1),
                    (f0 + 34, -.035, 0, 1), (f0 + 38, .02, 0, 1), (f0 + 43, 0, 0, 1), (f1, 0, 0, 1)):
    key(arm, "pile", f, x=x, y=y, sy=sy)
for f, s in ((f0 + 4, .975), (f0 + 9, 1.03), (LAND + 1, .97), (f0 + 26, 1.035), (f0 + 34, 1.0), (f1, 1)):
    key(arm, "belly", f, s=s)
plan = {}
rnd = random.Random(2)
for i, b in enumerate(BUDS):
    cx, cy = BUDS[b][0]
    ox, oy = (cx - PILE_C[0]) / 260, (cy - PILE_C[1]) / 220     # out from the pile's middle
    plan[b] = [(f0 + 9 + i % 3, ox * 7, 6 + abs(oy) * 4, rnd.uniform(-9, 9), 12),                 # floating up
               (LAND + 1 + i % 2, ox * 6, 7, rnd.uniform(-8, 8), 11),                          # bouncing off the bottom
               (f0 + 26 + (i * 3) % 7, -ox * 5 + rnd.uniform(-3, 3), rnd.uniform(1, 5), rnd.uniform(-8, 8), 11)]  # the shake
bud_keys(f0, f1 - f0 + 1, plan)
seal(f0, f1, gain=.5)
rest(arm, ["root", "bag", "belly", "pile"], f1)
fxkit.end_action(arm, act, f0)

# ================================================================== multi: pumped up in three pulses, then the seal lets go
f0, f1 = CLIPS["multi"]
act = fxkit.begin_action(arm, SID + "_multi")
rest(arm, BONES, f0)
PULSES = (f0 + 5, f0 + 13, f0 + 21)
GO = f0 + 27
for f, s in ((PULSES[0] - 2, .985), (PULSES[0] + 1, 1.08), (PULSES[0] + 4, 1.06), (PULSES[1] + 1, 1.15), (PULSES[1] + 4, 1.13),
             (PULSES[2] + 1, 1.23), (GO - 1, 1.245), (GO + 2, .92), (GO + 6, 1.04), (GO + 10, .985), (GO + 15, 1.0), (f1, 1)):
    key(arm, "belly", f, sx=s, sy=1 + (s - 1) * .8)
fxkit.hard(act, "belly", "scale", 0, GO + 2)
for f, y in ((PULSES[0] + 2, .03), (PULSES[1] + 2, .06), (PULSES[2] + 2, .09), (GO - 1, .095), (GO + 3, -.07), (GO + 8, .025),
             (GO + 13, -.008), (GO + 17, 0), (f1, 0)):
    key(arm, "pile", f, y=y)
for i, f in enumerate(range(PULSES[1], GO, 2)):          # straining: it trembles
    key(arm, "bag", f, r=(.8 if i % 2 else -.8) * (.6 + .4 * (f >= PULSES[2])), x=(.012 if i % 2 else -.012))
key(arm, "bag", GO, r=0, x=0); key(arm, "bag", f1, r=0, x=0)
for f, sx, sy in ((PULSES[0] + 1, 1.015, 1.01), (PULSES[1] + 1, 1.03, 1.02), (PULSES[2] + 1, 1.05, 1.035), (GO - 1, 1.055, 1.04),
                  (GO + 1, .94, 1.07), (GO + 5, 1.045, .96), (GO + 10, .99, 1.01), (GO + 15, 1, 1), (f1, 1, 1)):
    key(arm, "root", f, sx=sx, sy=sy)                     # the whole bag puffs up, then flops
plan = {}
for i, b in enumerate(BUDS):
    cx, cy = BUDS[b][0]
    ox, oy = (cx - PILE_C[0]) / 260, (cy - PILE_C[1]) / 220
    plan[b] = [(p + i % 2, ox * 4, -oy * 4 + 2, 4 * (1 if i % 2 else -1), 9) for p in PULSES] + \
              [(GO + 2 + i % 3, ox * 7, 8, 9 * (1 if i % 2 else -1), 12)]
bud_keys(f0, f1 - f0 + 1, plan)


def strain(name, i, t):
    f = f0 + t * FPS
    env = (smooth(PULSES[0], PULSES[0] + 3, f) * .4 + smooth(PULSES[1], PULSES[1] + 3, f) * .3 + smooth(PULSES[2], PULSES[2] + 3, f) * .3) \
        * (1 - smooth(GO - 1, GO + 1, f))
    return Vector((0, 0, 90 * env * (1 if i == 2 else .5)))   # the corners pulled up as it balloons


seal(f0, f1, forces=strain, gain=.75)
rest(arm, ["root", "bag", "belly", "pile"], f1)
fxkit.end_action(arm, act, f0)

# ================================================================== effects
# (sizes in units: the frame is 13 across, 512 px - a unit is ~39 px, so a line needs a radius of ~.025 to read)
sc.frame_set(1)
AROMA_INK, AROMA_FILL = (.34, .55, .24, 1), (.84, .96, .7, 1)
LEAF = [(.42, .62, .2, 1), (.6, .76, .3, 1), (.86, .56, .25, 1)]
LIM = 6.25


def bone_pt(bone, x, y, f):
    """where icon point (x, y) on a bone's part sits at frame f (world x, z)"""
    sc.frame_set(int(f))
    pb = arm.pose.bones[bone]
    m = arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted()
    v = m @ wpt(x, y)
    return v.x, v.z


# --- on the art: aroma puffs, curls and a smoke ring out of the seal, leaf flecks
art_fx = gp_object(ART, SID + "_aroma", depth=-1.0)
m_aroma = gp_mat(art_fx, "fx_aroma", AROMA_INK, fill=AROMA_FILL)
m_wisp = gp_mat(art_fx, "fx_wisp", (.66, .86, .52, 1))
m_wisp_hi = gp_mat(art_fx, "fx_wisp_hi", (.9, 1.0, .82, 1))
m_leaf = [gp_mat(art_fx, f"fx_leaf{i}", tuple(c * .6 for c in col[:3]) + (1,), fill=col) for i, col in enumerate(LEAF)]
ab = Board()


def aroma(f0, life, x, z, scale, drift, seed, lobes=6):
    """a cartoon puff of aroma: solid, it swells out and shrinks away (fxkit.dust's rule: never a fade)"""
    fxkit.dust(ab, f0, life, x, z, scale, m_aroma, drift=drift, seed=seed, lobes=lobes)


def wisp(f0, life, x, z, height, seed, width=.05, sway=.3):
    """a curl of aroma rising and unrolling from a point: it grows up from its root, its root then lifts away after
    it, thinning to nothing as it goes - a pale core line along it"""
    rnd = random.Random(seed)
    ph = rnd.uniform(0, 6.28)
    for k in range(life):
        t = k / max(1, life - 1)
        n = 16
        top = height * min(1, .2 + t * 1.15)
        bot = height * max(0, t - .3) * 1.25
        pts, rr = [], []
        for i in range(n + 1):
            u = i / n
            zz = z + bot + (top - bot) * u
            xx = x + sway * math.sin(ph + 5.0 * u + 2.6 * t) * (.3 + u)
            pts.append((xx, min(LIM, zz)))
            rr.append(width * math.sin(math.pi * u) ** .7 * (1 - t ** 1.6) + .003)
        ab.add(f0 + k, lambda dr, pts=pts, rr=rr: stroke(dr, pts, 0, radii=rr, mat=m_wisp))
        ab.add(f0 + k, lambda dr, pts=pts, rr=rr: stroke(dr, pts, 0, radii=[r * .35 for r in rr], mat=m_wisp_hi))


def flecks(f0, n, x, z, seed, speed=(2.0, 4.2), life=18, spread=(45, 135)):
    """little leaf bits thrown out: spinning flakes that fall and shrink"""
    rnd = random.Random(seed)
    for i in range(n):
        a = math.radians(rnd.uniform(*spread))
        sp = rnd.uniform(*speed)
        r0 = rnd.uniform(.065, .1)
        spin = rnd.uniform(-.6, .6)
        st = f0 + rnd.randint(0, 3)
        for k in range(life):
            t = k / FPS
            xx = x + math.cos(a) * sp * t
            zz = z + math.sin(a) * sp * t - 5.5 * t * t
            r = r0 * (1 - (k / life) ** 2)
            if abs(xx) > LIM - .1 or abs(zz) > LIM - .1:
                break
            ang = spin * k
            pts = [(xx + math.cos(ang + u) * r * (1.0 if q % 2 == 0 else .5), zz + math.sin(ang + u) * r * (1.0 if q % 2 == 0 else .5))
                   for q, u in enumerate(2 * math.pi * j / 8 for j in range(8))]
            ab.add(st + k, lambda dr, pts=pts, m=m_leaf[i % 3]: stroke(dr, pts, .005, mat=m, cyclic=True, fill=True))


def smoke_ring(f0, life, cx, cz, rx0, rx1, aspect, n, seed, scale):
    """a ring of aroma blown out of the seal: puffs round an ellipse that widens as it rises, each swelling then
    shrinking away"""
    rnd = random.Random(seed)
    for i in range(n):
        a = 2 * math.pi * i / n + rnd.uniform(-.12, .12)
        x0, z0 = cx + math.cos(a) * rx0, cz + math.sin(a) * rx0 * aspect
        x1, z1 = cx + math.cos(a) * rx1, cz + math.sin(a) * rx1 * aspect + .8
        sc_ = scale * (1.1 if math.sin(a) < 0 else .85)        # the near side of the ring a little fuller
        aroma(f0 + rnd.randint(0, 1), life, x0, z0, sc_, (x1 - x0, z1 - z0), seed * 31 + i, lobes=5)


SX, SZ = px(*SEAL_C)                                   # the middle of the seal
TOPX, TOPZ = px(520, 160)                              # just above it, where the aroma comes out
# idle: the out-breath lets a curl of aroma out of the seal, a little leaf riding up on it, turning as it goes
f0, f1 = CLIPS["idle"]
m_leafy = gp_mat(art_fx, "fx_leafy", (.15, .3, .08, 1), fill=(.5, .8, .25, 1))


def fan_leaf(cx, cz, r, rot):
    """a little five-bladed leaf (world units): each blade a pointed lancet out from the middle, a short stem"""
    out = []
    for a, ln in ((0, 1.0), (.6, .78), (-.6, .78), (1.18, .5), (-1.18, .5)):
        ang = math.pi / 2 + a + rot
        L = r * ln
        ax, az = math.cos(ang), math.sin(ang)
        nx, nz = -az, ax
        n = 7
        side = [(u, .2 * L * math.sin(math.pi * u) ** .85) for u in (i / n for i in range(n + 1))]
        pts = [(cx + ax * L * u + nx * w, cz + az * L * u + nz * w) for u, w in side]
        pts += [(cx + ax * L * u - nx * w, cz + az * L * u - nz * w) for u, w in reversed(side[1:-1])]
        out.append(pts)
    sa = rot - math.pi / 2
    stem = [(cx, cz), (cx + math.cos(sa + .25) * r * .42, cz + math.sin(sa + .25) * r * .42)]
    return out, stem


AT_OUT = f0 + 50                                       # the out-breath
sx_, sz_ = bone_pt("bag", 515, 165, AT_OUT)
wisp(AT_OUT, 28, sx_ - .3, sz_ - .05, 2.0, 3, width=.085, sway=.32)
LF0, LFL = AT_OUT + 6, 23
for k in range(LFL):
    t = k / (LFL - 1)
    up = 1 - (1 - t) ** 1.6
    x = sx_ + .3 + .26 * math.sin(2 * math.pi * 1.05 * t)
    z = sz_ + .15 + 1.75 * up
    pop = 1.12 * math.sin(math.pi / 2 * min(1, k / 4)) if k < 5 else 1 + .12 * max(0, 1 - (k - 4) / 3)
    s = pop * (1 - smooth(LFL - 8, LFL - 1, k))
    if s < .08:
        continue
    blades, stem = fan_leaf(x, z, .4 * s, .38 * math.sin(2 * math.pi * 1.05 * t + 1.1))
    ab.add(LF0 + k, lambda dr, stem=stem: stroke(dr, stem, .014, mat=m_leafy))
    for bl in blades:
        ab.add(LF0 + k, lambda dr, bl=bl: stroke(dr, bl, .009, mat=m_leafy, cyclic=True, fill=True))
# land: the squeeze pushes a puff out of the seal, and a curl after it
f0, f1 = CLIPS["land"]
for k, (dx, d, sd, sz) in enumerate(((-.35, 0, 2, .52), (.4, 1, 5, .46), (0, 2, 8, .4))):
    x, z = bone_pt("zip_l.0" if dx < 0 else "zip_r.0", 520 + dx * 100, 165, f0 + 3 + d)
    aroma(f0 + 3 + d, 13, x, z + .1, sz, (dx * 1.6, 1.2), sd)
wisp(f0 + 6, 17, TOPX + .2, TOPZ, 1.4, 6, width=.04)
# hit: a cloud bursts out of the seal in the shake, curls after it, flecks fly
f0, f1 = CLIPS["hit"]
for k in range(7):
    st = f0 + 24 + 2 * k
    x, z = bone_pt("bag", 440 + 25 * k, 165, st)
    aroma(st, 16, x + (-.35 if k % 2 else .35), z + .1, .56 + .06 * (k % 3), ((-1 if k % 2 else 1) * (.7 + .2 * k), 1.05 + .1 * k), 20 + k)
x, z = bone_pt("bag", 520, 170, f0 + 25)
flecks(f0 + 25, 10, x, z, 5)
wisp(f0 + 30, 24, x - .7, z + .3, 1.7, 9)
wisp(f0 + 33, 21, x + .8, z + .2, 1.5, 11)
# multi: curls leaking out of the seal as it strains; the release - the seal pops: a fountain of aroma, a smoke ring
# blown out round the top of the bag, flecks everywhere
f0, f1 = CLIPS["multi"]
for i, p_ in enumerate(PULSES):
    wisp(p_ + 2, 15, SX + (-.9, .8, -.2)[i], TOPZ - .1, 1.0 + .25 * i, 30 + i, width=.035 + .008 * i)
for k in range(6):
    st = GO + k
    a = (-1) ** k * (.2 + .1 * k)
    aroma(st, 16, TOPX + a * .5, TOPZ + .1, .56 + .06 * (k % 3), (a * 1.5, 1.55 - .08 * k), 50 + k)
smoke_ring(GO + 2, 16, TOPX, TOPZ + .25, .9, 3.3, .32, 13, 7, .46)
flecks(GO + 1, 14, TOPX, TOPZ + .1, 13, speed=(2.5, 5.2), spread=(20, 160))
ab.draw(gp_layer(art_fx, "aroma"))

# --- over the art (bloomed): glints on the plastic, the multi's motes and the pop
fxw = gp_object(FX, SID + "_fx", depth=-.8)
w_spark = gp_mat(fxw, "fx_white_fill", WHITE, fill=WHITE)
w_lime = gp_mat(fxw, "fx_lime_fill", LIME, fill=LIME)
w_limel = gp_mat(fxw, "fx_lime_line", LIME)
w_white = gp_mat(fxw, "fx_white_line", WHITE)
world = Board()
fxb = gp_object(FX, SID + "_fx_on", depth=-.8)         # rides the bag: the plastic's glints
ride(fxb, arm, "bag")
o_spark = gp_mat(fxb, "fx_white_fill", WHITE, fill=WHITE)
o_gold = gp_mat(fxb, "fx_gold_fill", GOLD, fill=GOLD)
o_white = gp_mat(fxb, "fx_white_line", WHITE)
onbag = Board()
GLARE = [(232, 330), (782, 318), (214, 770), (790, 790), (312, 128), (712, 132), (470, 840)]   # bright spots on the plastic


def shine(board, f0, life, x, z, length, mat, ang=.9):
    """a glint running along the plastic: a short bright streak that grows and shrinks to a point"""
    for k in range(life):
        t = k / max(1, life - 1)
        ln = length * math.sin(math.pi * t)
        if ln < .05:
            continue
        dx, dz = math.cos(ang) * ln / 2, math.sin(ang) * ln / 2
        n = 6
        pts = [(x - dx + 2 * dx * i / n, z - dz + 2 * dz * i / n) for i in range(n + 1)]
        board.add(f0 + k, lambda dr, pts=pts: stroke(dr, pts, 0, radii=[.03 * math.sin(math.pi * i / n) ** .6 + .004 for i in range(n + 1)],
                                                     mat=mat))


# idle: at the top of the breath (the plastic taut) a glint slides over it, top-left to bottom-right - a broad
# streak with a thin one running beside it, growing as they cross the middle and shrinking away - and twinkles out
f0, f1 = CLIPS["idle"]
G0, GL = f0 + 40, 15
GA, GB = (262, 318), (700, 738)                        # icon px: where the glint starts and ends
gax, gaz = px(*GA)
gbx, gbz = px(*GB)
tl = math.hypot(gbx - gax, gbz - gaz)
tx_, tz_ = (gbx - gax) / tl, (gbz - gaz) / tl          # the way it travels
sx_, sz_ = tz_ * -1, tx_                               # the way the streaks lie (across it)
if sz_ < 0:
    sx_, sz_ = -sx_, -sz_
for k in range(GL):
    t = k / (GL - 1)
    e = math.sin(math.pi * t) ** .8
    u = t * t * (3 - 2 * t)
    cx_, cz_ = gax + (gbx - gax) * u, gaz + (gbz - gaz) * u
    for off, ln, rad, op in ((0.0, 2.6, .13, .78), (.42, 1.5, .06, .92)):
        L = ln * e
        if L < .1:
            continue
        n = 8
        pts = [(cx_ + tx_ * off + sx_ * L * (i / n - .5), cz_ + tz_ * off + sz_ * L * (i / n - .5)) for i in range(n + 1)]
        rr = [rad * math.sin(math.pi * i / n) ** .6 + .004 for i in range(n + 1)]
        onbag.add(G0 + k, lambda dr, pts=pts, rr=rr, op=op: stroke(dr, pts, 0, opacity=op, radii=rr, mat=o_white))
fxkit.sparkle(onbag, G0 + GL - 4, 11, *px(722, 760), .44, o_spark, rot0=.3)
f0, f1 = CLIPS["land"]
fxkit.sparkle(onbag, f0 + 5, 9, *px(*GLARE[0]), .4, o_spark, rot0=.5)
rnd = random.Random(7)
f0, f1 = CLIPS["hit"]
for i in range(7):
    fxkit.sparkle(onbag, LAND + 2 + rnd.randint(0, 18), rnd.randint(9, 12), *px(*GLARE[i]), rnd.uniform(.38, .56),
                  o_gold if i % 3 == 2 else o_spark, rot0=rnd.uniform(0, 1))
for i, (x, y) in enumerate(((225, 520), (790, 560), (480, 815))):
    shine(onbag, LAND + 4 + 5 * i, 9, *px(x, y), 1.0, o_white, ang=1.25 if i != 2 else .2)
# multi: motes gather round the bag with every pulse and race round it, closing in; the seal pops
f0, f1 = CLIPS["multi"]
for i in range(10):
    for k, f in enumerate(range(PULSES[0] + (i % 3) * 8, GO + 1)):
        a = 2 * math.pi * i / 10 + k * .21
        rad = 5.1 - 1.2 * smooth(PULSES[0], GO, f)
        cz = px(0, 520)[1]
        s = (.24 + .08 * math.sin(k * .9 + i)) * min(1, k / 3)
        world.add(f, lambda dr, a=a, rad=rad, cz=cz, s=s, i=i: stroke(dr, star(math.cos(a) * rad * .9, cz + math.sin(a) * rad * .98, s, a), .004,
                                                                       mat=w_lime if i % 2 else w_spark, cyclic=True, fill=True, line=False))
for k in range(5):                                     # the pop: a flash at the seal, flung out in quick rays
    t = k / 4
    world.add(GO + k, lambda dr, t=t: stroke(dr, star(TOPX, TOPZ - .25, .45 + .9 * t, .3 + .4 * t, points=6, inner=.24 * (1 - .8 * t)), .004,
                                             mat=w_spark if t < .5 else w_lime, cyclic=True, fill=True, line=False))
for i in range(12):
    a = math.radians(15 + 150 * i / 11)
    for k in range(8):
        t = k / 7
        r0, r1 = .45 + 1.9 * t, .45 + 1.9 * t + .85 * (1 - t)
        world.add(GO + 1 + k, lambda dr, a=a, r0=r0, r1=r1, t=t, i=i: stroke(
            dr, [(TOPX + math.cos(a) * r0, TOPZ - .25 + math.sin(a) * r0), (TOPX + math.cos(a) * r1, TOPZ - .25 + math.sin(a) * r1)],
            .04 * (1 - t) + .006, mat=w_limel if i % 2 else w_white))
for i in range(6):
    fxkit.sparkle(onbag, GO + 3 + rnd.randint(0, 9), rnd.randint(9, 11), *px(*GLARE[i]), rnd.uniform(.36, .5), o_spark, rot0=rnd.uniform(0, 1))
world.draw(gp_layer(fxw, "fx"))
onbag.draw(gp_layer(fxb, "fx"))

sc.frame_start, sc.frame_end = 1, max(b for a, b in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], "| saved", fxkit.save(SID))
