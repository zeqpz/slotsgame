# L6 - the camo t-shirt - animated in Blender: four Actions on its rig (idle, land, hit, multi) laid one after another
# on the rig's NLA track, and its effects drawn frame by frame in Grease Pencil.
#   the rig     the shirt is ONE image (tools/blender/cuts/L6.py) on a fine mesh skinned to its bones, so cloth bends
#               and never cracks: the torso hangs from the collar (it sways and puffs out); each sleeve is a chain of
#               two bones from its armhole out to its cuff, the skin blended across the armhole seam so the sleeve
#               bends out of the body; along the hem a row of five flaps, each blended into its neighbours, so the
#               hem ripples and billows; the root at the hem squashes it. The tag is the one piece on top (cut round
#               its white outline; clean camo under it): it pops, squashes and wobbles on its own bone
#   the cloth   the sleeves and the hem flaps are never keyed by hand: they are worked out in Blender from how the
#               torso really moves (fxkit.secondary: each its own spring, the left sleeve on the windward side light
#               and quick, the right one heavier, the flaps softer toward the hem's ends) plus a breeze or a gust as a
#               force, then keyed sparsely
#   idle        a breeze from the left: the shirt sways from its collar and breathes, the sleeves flutter a beat
#               apart, a ripple runs along the hem; a wisp of wind slips past
#   land        dropped onto the reel: it squashes on its hem, the hem flares, the sleeves keep falling and flick
#               back up, the tag bobs; puffs of air squeezed out from under the hem
#   hit         a gust: it draws in, then the wind catches it - it balloons and lifts, the sleeves blow up and flap,
#               the hem billows and ripples, the tag pops; gust lines sweep across it, camo paint splats fly off its
#               edges, the tag sparkles; then the wind drops it back
#   multi       a whirlwind builds round it in three pulses - it inflates more each time, the sleeves rise, the hem
#               lifts and flutters, the tag pulses, the shirt trembles - then the whirlwind bursts: a ring and a
#               spray of streaks and paint, and the shirt snaps back and flaps itself still
#   effects     wind wisps and gust lines, a whirlwind of arcs, camo paint splats, air puffs, sparkles - its own
#               effects (a low symbol: no tier glow)
# Runs INSIDE Blender, after build_symbol_scene.py (tools/blender/run.py runs both in a background Blender).
import bpy, importlib, math, os, random, sys
from mathutils import Matrix, Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
import fxkit
importlib.reload(fxkit)
from fxkit import (key, rest, px, smooth, gp_object, gp_mat, gp_layer, ride, stroke, star, puff, Board, WHITE, LIME, GOLD)

SID = "L6"
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
        if head is not None:
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


def side_dist(line, x, y):
    """signed distance to an open polyline, px: positive on its left (as it runs from its first point)"""
    best = None
    for (ax, ay), (bx, by) in zip(line, line[1:]):
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / L2))
        d = math.hypot(ax + dx * t - x, ay + dy * t - y)
        if best is None or d < best[0]:
            cross = dx * (y - ay) - dy * (x - ax)          # image y is down: cross > 0 = on the polyline's right
            best = (d, -1 if cross > 0 else 1)
    return best[0] * best[1]


def keys(bone, f0, vals, channel, tol, loop=False):
    fxkit.key_series(arm, bone, f0, vals, channel=channel, tol=tol, loop=loop)


# ================================================================== the rig
COLLAR = (500, 80)                  # the torso hangs (and sways, and puffs out) from here (the recipe's pivot)
HEM_Y = 935
SL_L = [(232, 318), (176, 376), (122, 432)]         # each sleeve: armhole -> the sleeve's middle -> the cuff
SL_R = [(768, 312), (822, 368), (873, 422)]
# the armhole seams, each run so its sleeve lies on its left: the left one from under the arm up over the shoulder,
# the right one from over the shoulder down and out under the arm
SEAM_L = [(150, 560), (226, 528), (250, 495), (246, 430), (240, 360), (228, 290), (212, 220), (198, 150), (150, 60)]
SEAM_R = [(850, 60), (800, 150), (786, 220), (775, 290), (768, 360), (762, 430), (758, 490), (782, 520), (850, 550)]
FLAPS = [255, 378, 500, 622, 745]                    # the hem's flaps, x px (each from y 735 down to the hem)
add_bones([("root", (500, HEM_Y), None, None),
           ("body", None, None, "root")]
          + [(f"sleeve_l.{i}", SL_L[i], SL_L[i + 1], "body" if i == 0 else f"sleeve_l.{i - 1}", i > 0) for i in range(2)]
          + [(f"sleeve_r.{i}", SL_R[i], SL_R[i + 1], "body" if i == 0 else f"sleeve_r.{i - 1}", i > 0) for i in range(2)]
          + [(f"hem{k}", (x, 735), (x, HEM_Y), "body") for k, x in enumerate(FLAPS)])


def shirt_weights(x, y):
    w = {}
    sl = sstep(-14, 46, side_dist(SEAM_L, x, y))          # out in the left sleeve (soft across the seam)
    sr = sstep(-14, 46, side_dist(SEAM_R, x, y))
    if x > 500:
        sl = 0.0
    else:
        sr = 0.0
    for name, ch, s in (("sleeve_l", SL_L, sl), ("sleeve_r", SL_R, sr)):
        if s > 0:
            for i, cw in enumerate(chain_w(ch, x, y, 60)):
                w[f"{name}.{i}"] = s * cw
    torso = 1 - sl - sr
    h = sstep(700, 865, y) * torso                          # the hem band
    if h > 0:
        k = (x - FLAPS[0]) / (FLAPS[1] - FLAPS[0])           # where it falls along the row of flaps
        k = max(0.0, min(len(FLAPS) - 1.0, k))
        i0 = min(len(FLAPS) - 2, int(k))
        u = k - i0
        u = u * u * (3 - 2 * u)
        w[f"hem{i0}"] = w.get(f"hem{i0}", 0) + h * (1 - u)
        w[f"hem{i0 + 1}"] = w.get(f"hem{i0 + 1}", 0) + h * u
    w["body"] = torso - h
    return w


skin("body", shirt_weights)
SLEEVES = [f"sleeve_{s}.{i}" for s in "lr" for i in range(2)]
HEMS = [f"hem{k}" for k in range(len(FLAPS))]
BONES = ["root", "body", "logo"] + SLEEVES + HEMS

ART, FXB, FX = fxkit.layers(sc, SID)
fxkit.glow_compositor(sc, SID, back=dict(strength=.7, size=.5, gain=1.3), front=dict(strength=.75, size=.42, gain=1.4))
if arm.animation_data:
    arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)

CLIPS = {"idle": (1, 84), "land": (101, 124), "hit": (201, 254), "multi": (301, 348)}
arm["clips"] = {k: list(v) for k, v in CLIPS.items()}
# the cloth: the windward sleeve light and quick, the other heavier; the hem's flaps soft, softest at its ends
CLOTH = {"sleeve_l": dict(chain=SL_L, freq=[2.7, 2.2], zeta=.2, gain=.8, limit=16),
         "sleeve_r": dict(chain=SL_R, freq=[2.3, 1.9], zeta=.17, gain=.8, limit=16)}
for k, x in enumerate(FLAPS):
    soft = abs(k - 2) / 2
    CLOTH[f"hem{k}"] = dict(chain=[(x, 735), (x, HEM_Y)], freq=[2.6 - .5 * soft], zeta=.22, gain=.7, limit=7,
                            stretch=True, stretch_limit=.07)


def cloth(f0, f1, loop=False, forces=None, gain=1.0, root_gain=.6):
    """the sleeves and the hem worked out from how this clip moves the torso, keyed onto their bones"""
    res = fxkit.secondary(sc, arm, "body", f0, f1, CLOTH, loop=loop, forces=forces, gain=gain)
    print(f"  cloth {f0}-{f1}:", ", ".join(f"{b} {min(v):+.1f}..{max(v):+.2f}" for b, v in res.items()))
    for bone, vals in res.items():
        if bone.endswith(":sy"):
            b = bone[:-3]
            keys(b, f0, vals, "sy", .003, loop)
            keys(b, f0, [1 / math.sqrt(max(.5, v)) for v in vals], "sx", .003, loop)
        else:
            if bone.endswith(".0"):                    # the sleeve turns less at its armhole than along it
                vals = [v * root_gain for v in vals]
            keys(bone, f0, vals, "r", .2, loop)


def wind(t, T, phase=0.0):
    return math.sin(2 * math.pi * t / T + phase)


# ================================================================== idle: a breeze from the left
f0, f1 = CLIPS["idle"]
N = f1 - f0 + 1
T = N / FPS
act = fxkit.begin_action(arm, SID + "_idle")
rest(arm, BONES, f0)
for k in range(0, N + 1, 6):
    ph = 2 * math.pi * k / N
    key(arm, "body", f0 + k, r=.55 * math.sin(ph) - .15 * math.sin(2 * ph), sx=1 + .01 * (.5 - .5 * math.cos(ph)),
        sy=1 + .005 * (.5 - .5 * math.cos(ph)))


def breeze(name, i, t):
    if name == "sleeve_l":                             # windward: lifted and dropped, with a flutter
        a = 46 * (.5 + .5 * wind(t, T, -1.2)) + 17 * wind(t, T / 3, .4)
        return Vector((-10 * wind(t, T / 2), 0, a * (i / 2) ** .8))
    if name == "sleeve_r":                             # leeward: pushed out, a beat later
        a = 36 * (.5 + .5 * wind(t, T, -2.4)) + 14 * wind(t, T / 3, 2.0)
        return Vector((20 * (.5 + .5 * wind(t, T, -2.0)), 0, a * .6 * (i / 2) ** .8))
    k = int(name[3:])                                  # a ripple running along the hem, left to right
    ph = 2 * math.pi * 2 * t / T - .95 * k
    return Vector((18 * math.sin(ph), 0, 12 * math.cos(ph)))


cloth(f0, f1, loop=True, forces=breeze, gain=1.0)
fxkit.make_cyclic(act)
fxkit.end_action(arm, act, f0)

# ================================================================== land: squashes on its hem, the cloth keeps falling
f0, f1 = CLIPS["land"]
act = fxkit.begin_action(arm, SID + "_land")
rest(arm, BONES, f0)
for f, sx, sy in ((f0 + 2, 1.075, .9), (f0 + 6, .965, 1.045), (f0 + 10, 1.015, .99), (f0 + 14, .997, 1.003), (f0 + 18, 1, 1), (f1, 1, 1)):
    key(arm, "root", f, sx=sx, sy=sy)
fxkit.hard(act, "root", "scale", 1, f0 + 2)
for f, s in ((f0 + 3, .96), (f0 + 7, 1.05), (f0 + 11, .99), (f0 + 15, 1), (f1, 1)):
    key(arm, "logo", f, s=s)
for f, r in ((f0 + 4, .8), (f0 + 9, -.5), (f0 + 14, .2), (f0 + 19, 0), (f1, 0)):
    key(arm, "body", f, r=r)


def drop(name, i, t):
    f = f0 + t * FPS
    fall = smooth(f0, f0 + 2, f) * (1 - smooth(f0 + 3, f0 + 6, f))
    if name.startswith("sleeve"):
        return Vector((0, 0, -170 * fall * (i / 2)))   # the sleeves keep falling as the shirt stops
    k = int(name[3:])
    return Vector(((k - 2) * 45 * fall, 0, -60 * fall))   # the hem flares out


cloth(f0, f1, forces=drop, gain=1.0)
rest(arm, ["root", "body", "logo"], f1)
fxkit.end_action(arm, act, f0)

# ================================================================== hit: a gust catches it
f0, f1 = CLIPS["hit"]
act = fxkit.begin_action(arm, SID + "_hit")
rest(arm, BONES, f0)
GUST, DROP_ = f0 + 7, f0 + 33
for f, sx, sy, y, r in ((f0 + 5, .94, 1.035, -.03, 0), (GUST + 3, 1.12, 1.04, .35, -2.5), (GUST + 8, 1.09, 1.03, .55, -3.2),
                        (GUST + 14, 1.1, 1.035, .6, -1.5), (GUST + 20, 1.08, 1.03, .52, -2.4), (DROP_, 1.03, 1.0, .2, -.6),
                        (DROP_ + 4, 1.06, .93, 0, .3), (DROP_ + 8, .98, 1.02, .02, 0), (DROP_ + 13, 1, 1, 0, 0), (f1, 1, 1, 0, 0)):
    key(arm, "root", f, sx=sx, sy=sy, y=y, r=r)
fxkit.hard(act, "root", "location", 1, DROP_ + 4)
for f, r in ((GUST + 4, -1.2), (GUST + 10, 1.4), (GUST + 16, -1.0), (GUST + 22, .8), (DROP_ + 2, -.4), (DROP_ + 9, 0), (f1, 0)):
    key(arm, "body", f, r=r)
for f, s, r in ((f0 + 5, .95, 0), (GUST + 3, 1.24, -7), (GUST + 7, 1.12, 3), (GUST + 11, 1.17, -2), (GUST + 17, 1.1, 1),
                (DROP_ + 4, .96, 0), (DROP_ + 9, 1.02, 0), (DROP_ + 14, 1, 0), (f1, 1, 0)):
    key(arm, "logo", f, s=s, r=r)


def gust(name, i, t):
    f = f0 + t * FPS
    pre = smooth(f0 + 1, f0 + 5, f) * (1 - smooth(f0 + 5, GUST, f))
    blow = smooth(GUST - 1, GUST + 3, f) * (1 - smooth(DROP_ - 6, DROP_ + 1, f))
    flap = math.sin(2 * math.pi * 3.1 * t) * blow
    if name == "sleeve_l":
        return Vector((-60 * blow, 0, (-90 * pre + 420 * blow + 130 * flap) * (i / 2) ** .7))
    if name == "sleeve_r":
        return Vector((60 * blow, 0, (-90 * pre + 380 * blow + 120 * math.sin(2 * math.pi * 2.7 * t + 1.3) * blow) * (i / 2) ** .7))
    k = int(name[3:])
    ph = 2 * math.pi * 3.4 * t - 1.1 * k
    return Vector(((k - 2) * 60 * blow + 70 * blow * math.sin(ph), 0, 140 * blow + 60 * blow * math.cos(ph) - 40 * pre))


cloth(f0, f1, forces=gust, gain=.9)
rest(arm, ["root", "body", "logo"], f1)
fxkit.end_action(arm, act, f0)

# ================================================================== multi: a whirlwind builds in three pulses, then bursts
f0, f1 = CLIPS["multi"]
act = fxkit.begin_action(arm, SID + "_multi")
rest(arm, BONES, f0)
PULSES = (f0 + 5, f0 + 13, f0 + 21)
GO = f0 + 27
for f, s in ((PULSES[0] - 2, .985), (PULSES[0] + 1, 1.05), (PULSES[0] + 4, 1.035), (PULSES[1] + 1, 1.085), (PULSES[1] + 4, 1.07),
             (PULSES[2] + 1, 1.125), (GO - 1, 1.13), (GO + 2, .94), (GO + 6, 1.035), (GO + 10, .99), (GO + 15, 1), (f1, 1)):
    key(arm, "body", f, sx=s, sy=1 + (s - 1) * .45)
fxkit.hard(act, "body", "scale", 0, GO + 2)
for i, f in enumerate(range(PULSES[1], GO - 1, 2)):    # straining in the wind: it trembles
    key(arm, "root", f, r=(.7 if i % 2 else -.7) * (1 + .5 * (f >= PULSES[2])), x=(.015 if i % 2 else -.015))
for f, sx, sy, r, x in ((GO - 1, 1, 1, 0, 0), (GO + 2, 1.05, .93, 0, 0), (GO + 6, .98, 1.025, 0, 0), (GO + 11, 1, 1, 0, 0), (f1, 1, 1, 0, 0)):
    key(arm, "root", f, sx=sx, sy=sy, r=r, x=x)
for f, s in ((PULSES[0] + 1, 1.045), (PULSES[0] + 4, 1.01), (PULSES[1] + 1, 1.07), (PULSES[1] + 4, 1.025), (PULSES[2] + 1, 1.09),
             (GO - 1, 1.095), (GO + 2, .93), (GO + 6, 1.05), (GO + 10, .99), (GO + 14, 1), (f1, 1)):   # (on a torso already swelling)
    key(arm, "logo", f, s=s)


def whirl(name, i, t):
    f = f0 + t * FPS
    env = (smooth(PULSES[0] - 1, PULSES[0] + 2, f) * .45 + smooth(PULSES[1] - 1, PULSES[1] + 2, f) * .3
           + smooth(PULSES[2] - 1, PULSES[2] + 2, f) * .25) * (1 - smooth(GO - 1, GO + 1, f))
    snap = smooth(GO, GO + 1, f) * (1 - smooth(GO + 2, GO + 5, f))
    jit = math.sin(2 * math.pi * 7 * t + i) * env
    if name.startswith("sleeve"):
        s = -1 if name == "sleeve_l" else 1
        return Vector((s * 80 * env, 0, (330 * env + 70 * jit - 380 * snap) * (i / 2) ** .7))
    k = int(name[3:])
    ph = 2 * math.pi * 4.2 * t - 1.3 * k
    return Vector(((k - 2) * 55 * env + 55 * env * math.sin(ph), 0, 120 * env + 50 * env * math.cos(ph) - 160 * snap))


cloth(f0, f1, forces=whirl, gain=.9)
rest(arm, ["root", "body", "logo"], f1)
fxkit.end_action(arm, act, f0)

# ================================================================== effects
sc.frame_set(1)
CAMO = [(.86, .79, .55, 1), (.42, .52, .22, 1), (.58, .34, .15, 1), (.25, .19, .13, 1)]   # khaki, olive, brown, dark


def bone_pt(bone, x, y, f):
    """where icon point (x, y) on a bone's part sits at frame f (world x, z)"""
    sc.frame_set(int(f))
    pb = arm.pose.bones[bone]
    m = arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted()
    v = m @ wpt(x, y)
    return v.x, v.z


def clip_pts(pts, lim=6.25):
    return [(max(-lim, min(lim, x)), max(-lim, min(lim, z))) for x, z in pts]


# --- over the art (bloomed): wind lines, the whirlwind, sparkles round the tag, the burst
fxw = gp_object(FX, SID + "_fx", depth=-.8)
w_wind = gp_mat(fxw, "fx_wind", (.96, .98, .92, 1))
w_white = gp_mat(fxw, "fx_white_line", WHITE)
w_lime = gp_mat(fxw, "fx_lime_line", LIME)
w_spark = gp_mat(fxw, "fx_white_fill", WHITE, fill=WHITE)
w_limef = gp_mat(fxw, "fx_lime_fill", LIME, fill=LIME)
world = Board()


def gust_line(f0, life, path, length=.45, width=.03, mat=None, curl=True):
    """a line of wind: its head runs along `path` (u 0..1 -> x, z), its tail following, curling at the end;
    tapered at both ends, it thins to nothing instead of fading"""
    for k in range(life):
        t = k / max(1, life - 1)
        head = min(1.0, t * 1.25)
        tail = max(0.0, head - length)
        if head - tail < .02:
            continue
        n = 18
        pts = clip_pts([path(tail + (head - tail) * j / n) for j in range(n + 1)])
        wd = width * (1 - max(0, t - .65) / .35) + .003
        rr = [wd * math.sin(math.pi * j / n) ** .8 + .002 for j in range(n + 1)]
        world.add(f0 + k, lambda dr, pts=pts, rr=rr, mat=mat: stroke(dr, pts, 0, radii=rr, mat=mat if mat is not None else w_wind))


def swoosh(x0, z0, x1, z1, bend, wob=.0, curl_r=.0, seed=0):
    """a gust's path (u 0..1 -> x, z) from (x0, z0) to (x1, z1), bowed by `bend`, wobbling, and - with curl_r - rolling
    off its line into a shrinking curl at its end (a cartoon gust)"""
    rnd = random.Random(seed)
    ph = rnd.uniform(0, 6.28)
    dx, dz = x1 - x0, z1 - z0
    L = math.hypot(dx, dz)
    tx, tz = dx / L, dz / L
    nx_, nz_ = -tz, tx                                     # the side the curl turns to
    U = .76 if curl_r else 1.0

    def base(u):
        b = bend * math.sin(math.pi * u) + wob * math.sin(ph + 9 * u)
        return x0 + dx * u + nx_ * b, z0 + dz * u + nz_ * b

    def path(u):
        if u <= U:
            return base(u)
        v = (u - U) / (1 - U)
        bx, bz = base(U)
        cx, cz = bx + nx_ * curl_r, bz + nz_ * curl_r     # the curl's middle, beside the line where it leaves it
        a = v * 1.6 * math.pi
        r = curl_r * (1 - .45 * v)
        return cx + r * (-nx_ * math.cos(a) + tx * math.sin(a)), cz + r * (-nz_ * math.cos(a) + tz * math.sin(a))
    return path


# idle: one wisp of the breeze slips past the left sleeve
f0, f1 = CLIPS["idle"]
gust_line(f0 + 14, 26, swoosh(-6.1, -.4, -2.5, 1.5, .35, wob=.08, curl_r=.26, seed=1), length=.5, width=.03)
# hit: gust lines sweep across it from the lower left, curling off at the top right
f0, f1 = CLIPS["hit"]
for j, (x0, z0, x1, z1, bend, d) in enumerate([(-6.2, -3.2, 4.8, 3.8, .9, 0), (-6.2, -1.2, 5.6, 2.4, .6, 2), (-6.0, -4.6, 3.4, 1.0, -.5, 3),
                                               (-6.2, .6, 4.2, 5.2, .7, 5), (-5.6, -5.4, 5.6, -.8, .8, 7)]):
    gust_line(GUST - 2 + d, 16, swoosh(x0, z0, x1, z1, bend, wob=.12, curl_r=.32 if j % 2 == 0 else .0, seed=j + 3),
              length=.42, width=.055 if j < 2 else .042, mat=w_wind if j != 2 else w_lime)
for j, d in enumerate((14, 19)):                     # the wind gusting again while it flaps
    gust_line(GUST + d, 14, swoosh(-6.1, -2.2 + 1.6 * j, 5.2, 2.0 + 1.4 * j, .5, wob=.1, curl_r=.3, seed=20 + j), length=.4, width=.038)
# multi: the whirlwind - arcs of wind circling the shirt, more with every pulse, faster; then the burst
f0, f1 = CLIPS["multi"]
CXW, CZW = px(500, 520)
for f in range(f0 + 2, GO + 1):
    lvl = smooth(PULSES[0] - 2, PULSES[0] + 1, f) + smooth(PULSES[1] - 1, PULSES[1] + 1, f) + smooth(PULSES[2] - 1, PULSES[2] + 1, f)
    if lvl <= .05:
        continue
    narcs = 2 + int(round(lvl * 1.4))
    spin = .16 + .06 * lvl
    for a_i in range(narcs):
        base = (f - f0) * spin + 2 * math.pi * a_i / narcs
        rx, rz = 5.2 - .25 * lvl + .15 * (a_i % 2), 5.0 - .2 * lvl
        ln = .9 + .25 * lvl
        n = 16
        # each arc spirals in along its length (wind curling round it, not a ring), wavering a little
        pts = clip_pts([(CXW + math.cos(base + ln * j / n) * rx * (1 - .16 * j / n) * (1 + .025 * math.sin(f * .9 + j + a_i)),
                         CZW + math.sin(base + ln * j / n) * rz * (1 - .16 * j / n) * (1 + .025 * math.sin(f * .9 + j + a_i))) for j in range(n + 1)])
        rr = [(.024 + .012 * lvl) * math.sin(math.pi * j / n) ** .8 + .003 for j in range(n + 1)]
        world.add(f, lambda dr, pts=pts, rr=rr, a_i=a_i: stroke(dr, pts, 0, radii=rr, mat=w_lime if a_i % 3 == 2 else w_wind))
    if lvl > 1.2 and f % 2 == 0:                       # sparks caught in it
        for s in range(int(lvl * 2)):
            a = (f - f0) * spin * 1.3 + s * 2.1
            world.add(f, lambda dr, a=a, s=s: stroke(dr, star(CXW + math.cos(a) * 4.7, CZW + math.sin(a) * 4.5, .22 + .07 * (s % 2), a), .004,
                                                     mat=w_limef if s % 2 else w_spark, cyclic=True, fill=True, line=False))
# the burst: the whirlwind's arcs fly apart - each flung outward along its own spin, stretching thin, each ending in a
# curl of wind
for a_i in range(8):
    base0 = (GO - f0) * .34 + 2 * math.pi * a_i / 8
    for k in range(11):
        t = k / 10
        base = base0 + .5 * t
        rx, rz = 4.6 + 1.5 * (1 - (1 - t) ** 2), 4.4 + 1.5 * (1 - (1 - t) ** 2)
        ln = 1.1 * (1 - .65 * t)
        n = 16
        pts = clip_pts([(CXW + math.cos(base + ln * j / n) * rx, CZW + math.sin(base + ln * j / n) * rz) for j in range(n + 1)])
        rr = [(.06 * (1 - t) + .008) * math.sin(math.pi * j / n) ** .8 + .003 for j in range(n + 1)]
        world.add(GO + k, lambda dr, pts=pts, rr=rr, a_i=a_i: stroke(dr, pts, 0, radii=rr, mat=w_lime if a_i % 2 else w_wind))
    tipa = base0 + 1.15                                  # a curl of wind spun off the arc's leading end
    cx_, cz_ = CXW + math.cos(tipa) * 5.2, CZW + math.sin(tipa) * 5.0
    for k in range(9):
        t = k / 8
        n = 14
        pts = clip_pts([(cx_ + math.cos(tipa + 2.4 * math.pi * j / n * (.4 + .6 * t)) * .32 * (1 - .5 * j / n),
                         cz_ + math.sin(tipa + 2.4 * math.pi * j / n * (.4 + .6 * t)) * .32 * (1 - .5 * j / n)) for j in range(n + 1)])
        world.add(GO + 2 + k, lambda dr, pts=pts, t=t, n=n: stroke(dr, pts, 0, radii=[(.035 * (1 - t) + .005) * (1 - j / (n + 1)) for j in range(n + 1)],
                                                             mat=w_wind))
world.draw(gp_layer(fxw, "fx"))

# sparkles on the tag (they ride it)
fxt = gp_object(FX, SID + "_fx_tag", depth=-.85)
ride(fxt, arm, "logo")
t_spark = gp_mat(fxt, "fx_white_fill", WHITE, fill=WHITE)
t_gold = gp_mat(fxt, "fx_gold_fill", GOLD, fill=GOLD)
onlogo = Board()
TAG = [(300, 330), (420, 268), (560, 300), (690, 332), (470, 470), (455, 640), (360, 420), (640, 410)]
rnd = random.Random(3)
for i in range(7):
    x, y = TAG[i]
    fxkit.sparkle(onlogo, CLIPS["hit"][0] + 9 + rnd.randint(0, 12), rnd.randint(9, 12), *px(x, y), rnd.uniform(.38, .56),
                  t_gold if i % 3 == 1 else t_spark, rot0=rnd.uniform(0, 1))
for i in range(5):
    x, y = TAG[(i * 3) % len(TAG)]
    fxkit.sparkle(onlogo, GO + 1 + rnd.randint(0, 8), rnd.randint(9, 11), *px(x, y), rnd.uniform(.36, .5), t_spark, rot0=rnd.uniform(0, 1))
fxkit.sparkle(onlogo, CLIPS["idle"][0] + 56, 10, *px(*TAG[2]), .36, t_spark, rot0=.3)      # idle: the tag catches the light
onlogo.draw(gp_layer(fxt, "fx"))

# --- on the art: camo paint splats flung off the cloth, puffs of air from under the hem
art_fx = gp_object(ART, SID + "_splats", depth=-1.0)
m_camo = [gp_mat(art_fx, f"fx_camo{i}", tuple(c * .55 for c in col[:3]) + (1,), fill=col) for i, col in enumerate(CAMO)]
m_air = gp_mat(art_fx, "fx_air", (.62, .6, .5, 1), fill=(.95, .93, .86, 1))
ab = Board()
G = -9.0


def splats(f0, src, n, seed, vel, life=17, size=(.085, .14)):
    """camo paint thrown off the cloth: blobs with a droplet or two, flying, falling, spinning, shrinking away"""
    rnd = random.Random(seed)
    for i in range(n):
        bone, x, y = src[rnd.randrange(len(src))]
        st = f0 + rnd.randint(0, 4)
        x0, z0 = bone_pt(bone, x, y, st)
        vx, vz = vel(rnd)
        r0 = rnd.uniform(*size)
        mat = m_camo[i % 4]
        sd = rnd.randint(0, 999)
        drops = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(.25, .4)) for _ in range(rnd.randint(1, 3))]
        for k in range(life):
            t = k / FPS
            xx, zz = x0 + vx * t, z0 + vz * t + .5 * G * t * t
            r = r0 * (1 - (k / life) ** 1.6)
            if r < .012 or abs(xx) > 6.1 or abs(zz) > 6.1:
                break
            body = puff(xx, zz, r, lobes=5, seed=sd, n=22, bump=.28)
            ab.add(st + k, lambda dr, body=body, mat=mat: stroke(dr, body, .005, mat=mat, cyclic=True, fill=True))
            for dx, dz, rs in drops:
                cx, cz = xx + dx * r * 1.9, zz + dz * r * 1.9
                ab.add(st + k, lambda dr, cx=cx, cz=cz, rr=r * rs, mat=mat: stroke(dr, puff(cx, cz, rr, lobes=3, seed=1, n=10, bump=.1), .004,
                                                                                    mat=mat, cyclic=True, fill=True))


EDGES = [("sleeve_l.1", 70, 380), ("sleeve_l.1", 150, 470), ("sleeve_r.1", 930, 360), ("sleeve_r.1", 850, 470),
         ("hem0", 250, 920), ("hem2", 500, 935), ("hem4", 750, 920), ("body", 240, 600), ("body", 765, 640)]
f0, f1 = CLIPS["hit"]
splats(GUST + 1, EDGES, 16, 5, lambda r: (r.uniform(-1.0, 3.8), r.uniform(1.0, 4.5)))
f0, f1 = CLIPS["multi"]
rnd_ = random.Random(8)
splats(GO, EDGES, 18, 9, lambda r: (r.choice((-1, 1)) * r.uniform(1.5, 4.2), r.uniform(.5, 4.2)))
f0, f1 = CLIPS["land"]
for side, seed in ((-1, 3), (1, 5), (-1, 9), (1, 13)):
    far = 1 if seed in (3, 5) else .65
    x, z = px(500 + side * 230, HEM_Y + 8)
    fxkit.dust(ab, f0 + 2, 11, x, z, .42 * far + .1, m_air, drift=(side * 1.7 * far, .3), seed=seed)
ab.draw(gp_layer(art_fx, "splats"))

sc.frame_start, sc.frame_end = 1, max(b for a, b in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], "| saved", fxkit.save(SID))
