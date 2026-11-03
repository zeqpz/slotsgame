# H5 - the boombox - animated in Blender: four Actions on its rig (idle, land, hit, multi) on the rig's NLA track,
# its effects drawn frame by frame in Grease Pencil on the same timeline. It plays.
#   the box      bobs, squashes and hops on its base to the beat, rocks on the hit, swells with the multiplier
#   the cones    each speaker is a mesh bent by two bones: the grille in the middle (a "cone" bone, added here)
#                pumps out on every kick and sucks back, while the chrome ring holds and only thumps a little -
#                the ring's inner edge squeezes as the cone pushes, like a woofer
#   the handle   a mesh bent by bones: the carry handle bar rocks on its two posts (worked out with
#                fxkit.secondary from how the box moves: it lags a bob, jumps on a landing); every key - nine piano
#                keys and the three round keys - has its own bone and presses down in its slot (the slot above
#                stretches, the key's foot slides in behind the lid); the slot and the posts' feet stay on the box
#   the glow     tier 2 neon (fxkit.neon): violet, quieter, pink when charged
#   effects      sound waves fanning out of both sides, bass rings rolling off the speakers, music notes floating
#                up, the power light pulsing to the beat, the tape reels turning, lightning and charge rings for the
#                multiplier, a starburst, streaks, sparkles, landing dust
# Runs INSIDE Blender, after build_symbol_scene.py (tools/blender/run.py runs both in a background Blender).
import bpy, importlib, math, os, random, sys
from mathutils import Matrix, Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
import fxkit
importlib.reload(fxkit)
from fxkit import (key, rest, px, vec, smooth, gp_object, gp_mat, gp_layer, ride, stroke, star, ring, Board,
                   LIME, VIOLET, WHITE, GOLD, PINK)

SID = "H5"
sc, arm, spec = fxkit.setup(SID)
FPS = sc.render.fps
PARTS = {p["name"]: p for p in spec["parts"]}
if arm.animation_data:
    arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)

# ------------------------------------------------------------------ measured on the art (icon px)
BASE = (470, 790)                                   # the body bone (recipe): the box squashes and hops from here
HINGE = (952, 262)                                  # the handle bone (recipe): the handle rocks about its right post
SPK = {"l": (165.7, 565.4, 120.1, 152.6, -3.5), "r": (712.2, 624.8, 159.5, 174.5, -6.8)}   # the rings' outer ink
PIANO = [(186, 231), (242, 278), (283, 320), (329, 367), (376, 417), (426, 465), (478, 515), (520, 552), (553, 588)]
ROUND = [(636, 678), (711, 753), (786, 831)]
KEYS = [(a, b, 243) for a, b in PIANO] + [(a, b, 234) for a, b in ROUND]     # x range, top
LID_Y = 259                                          # the keys stand on the lid's top ink
LED = (829, 444, 29, 19)                             # the power light window: centre, half size
REELS = [(402.5, 500, 12.5), (482, 508, 16)]         # the tape hubs in the cassette window

# ------------------------------------------------------------------ the rig: cone bones, key bones, bent meshes
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
for side in "lr":
    cx, cy = SPK[side][:2]
    b = eb["spk_" + side]                                # the ring bone moves to the ring's own centre
    b.head = vec(cx, cy); b.tail = b.head + Vector((0, 0, .6)); b.roll = 0
    c = eb.get("cone_" + side) or eb.new("cone_" + side)
    c.head = vec(cx, cy); c.tail = c.head + Vector((0, 0, .5)); c.roll = 0
    c.parent = b
for i, (x0, x1, top) in enumerate(KEYS):
    k = eb.get(f"k{i}") or eb.new(f"k{i}")
    k.head = vec((x0 + x1) / 2, LID_Y); k.tail = k.head + Vector((0, 0, .3)); k.roll = 0
    k.parent = eb["body"]
bpy.ops.object.mode_set(mode="OBJECT")
for pb in arm.pose.bones:
    pb.rotation_mode = "XYZ"
bpy.context.view_layer.update()


def sstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


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


def handle_weights(x, y):
    wh = sstep((235 - y) / 60)                       # the bar and the rail above the slot: the handle bone
    out = {"handle": wh}
    rem = 1 - wh
    for i, (x0, x1, top) in enumerate(KEYS):
        wx = sstep((x - (x0 - 5)) / 5) * sstep(((x1 + 5) - x) / 5)
        wy = sstep((y - (top - (6 if i >= 9 else 10))) / (5 if i >= 9 else 8))
        w = wx * wy * rem
        if w > 1e-4:
            out[f"k{i}"] = w
    out["body"] = max(0.0, 1 - sum(out.values()))   # the slot, the posts' feet: on the box
    return out


def speaker_weights(side):
    cx, cy, rx, ry, deg = SPK[side]
    a = math.radians(deg)

    def fn(x, y):
        dx, dy = x - cx, y - cy
        u, v = dx * math.cos(a) + dy * math.sin(a), -dx * math.sin(a) + dy * math.cos(a)
        r = math.hypot(u / rx, v / ry)
        wc = 1 - sstep((r - .6) / .24)              # the grille: the cone; the chrome ring holds
        return {"cone_" + side: wc, "spk_" + side: 1 - wc}
    return fn


regrid("handle", handle_weights, 4)
regrid("spk_l", speaker_weights("l"), 6)
regrid("spk_r", speaker_weights("r"), 6)

ART, FXB, FX = fxkit.layers(sc, SID)
fxkit.glow_compositor(sc, SID, back=dict(strength=.95, size=.55, gain=1.5), front=dict(strength=.9, size=.42, gain=1.5))

KEYB = [f"k{i}" for i in range(len(KEYS))]
BONES = ["body", "handle", "spk_l", "spk_r", "cone_l", "cone_r"] + KEYB
CLIPS = {"idle": (1, 72), "land": (101, 124), "hit": (201, 254), "multi": (301, 346)}
arm["clips"] = {k: list(v) for k, v in CLIPS.items()}
HANG = {"handle": dict(chain=[HINGE, (130, 140)], freq=[3.0], zeta=.22, gain=.85, limit=1.7)}


def body(f, sx=None, sy=None, y=None, r=None, x=None):
    key(arm, "body", f, sx=sx, sy=sy)
    if y is not None or x is not None:
        key(arm, "body", f, y=y if y is not None else 0, x=x if x is not None else 0)
    if r is not None:
        key(arm, "body", f, r=r)


def cones(f, s, lag=1, ring=None, s_r=None):
    """Both cones at scale s (the right one a frame later and a touch smaller), the rings at `ring`."""
    key(arm, "cone_l", f, s=s)
    key(arm, "cone_r", f + lag, s=1 + (s - 1) * .92 if s_r is None else s_r)
    if ring is not None:
        key(arm, "spk_l", f, s=ring)
        key(arm, "spk_r", f + lag, s=1 + (ring - 1) * .9)


def press(i, f, depth=6.5, hold=0, up=4):
    """Key i pressed: down in two frames, held, back up."""
    b = f"k{i}"
    key(arm, b, f, y=0)
    key(arm, b, f + 2, y=-depth / 100)
    if hold:
        key(arm, b, f + 2 + hold, y=-depth / 100)
    key(arm, b, f + 2 + hold + up, y=0)


def follow(f0, f1, loop=False, gain=1.0, forces=None):
    res = fxkit.secondary(sc, arm, "body", f0, f1, HANG, loop=loop, gain=gain, forces=forces)
    print(f"  {f0}-{f1}:", ", ".join(f"{b} {min(v):+.2f}..{max(v):+.2f}" for b, v in res.items()))
    for bone, vals in res.items():
        fxkit.key_series(arm, bone, f0, vals, channel="r", tol=.06, loop=loop)


# ================================================================== idle: it plays - a calm groove
f0, f1 = CLIPS["idle"]
act = fxkit.begin_action(arm, SID + "_idle")
rest(arm, BONES, f0)
IDLE_BEATS = [(1, 1.0), (19, .55), (37, .9), (55, .5)]
for fb, s in IDLE_BEATS:                                 # calm: the cones carry the beat, the box only nods to it
    body(fb, sx=1, sy=1, y=0)
    body(fb + 2, sx=1 + .007 * s, sy=1 - .014 * s, y=0)
    body(fb + 5, sx=1 - .0025 * s, sy=1 + .005 * s, y=.02 * s)
    body(fb + 10, sx=1, sy=1, y=0)
    cones(fb, 1, ring=1)
    cones(fb + 2, 1 + .085 * s, ring=1 + .012 * s)
    cones(fb + 6, 1 - .022 * s, ring=1)
    cones(fb + 11, 1)
for i, f in ((3, 9), (5, 27), (10, 45), (1, 63)):      # a little riff on the keys, off the beat
    press(i, f, depth=5.5)
rest(arm, BONES, f1 + 1)                                # every curve closes the loop on the rest pose
follow(f0, f1, loop=True, gain=.9)
fxkit.make_cyclic(act)
fxkit.end_action(arm, act, f0)

# ================================================================== land: a thud on its base
f0, f1 = CLIPS["land"]
act = fxkit.begin_action(arm, SID + "_land")
rest(arm, BONES, f0)
for f, sx, sy, y in ((103, 1.085, .87, 0), (106, .96, 1.05, .05), (110, 1.02, .985, 0), (114, .995, 1.005, 0), (119, 1, 1, 0),
                     (124, 1, 1, 0)):
    body(f, sx=sx, sy=sy, y=y)
fxkit.hard(act, "body", "scale", 1, 103)
for f, s, rg in ((101, 1, 1), (103, 1.15, 1.03), (106, .93, 1.0), (109, 1.05, 1.0), (113, .985, 1), (118, 1, 1), (124, 1, 1)):
    cones(f, s, ring=rg, lag=0)
for i in range(len(KEYS)):                              # the knock rattles every key in its slot
    press(i, 102 + (i % 4) // 2, depth=4.5 + 2 * (i % 2), up=5)
follow(f0, f1, gain=1.0)
fxkit.end_action(arm, act, f0)

# ================================================================== hit: double-time - it hops, rocks and pumps
f0, f1 = CLIPS["hit"]
act = fxkit.begin_action(arm, SID + "_hit")
rest(arm, BONES, f0)
HIT_BEATS = [(203, 1.0), (212, .8), (221, 1.15), (230, .85), (239, 1.3)]
body(201, sx=1, sy=1, y=0, r=0)
for n, (fb, s) in enumerate(HIT_BEATS):
    rock = (2.6 if n % 2 == 0 else -2.6) * s
    last = n == len(HIT_BEATS) - 1
    body(fb, sx=1.0, sy=1.0, y=0, r=0 if n == 0 else -rock * .3)
    body(fb + 1, sx=1 + .06 * s, sy=1 - .1 * s, y=0)
    body(fb + 4, sx=1 - .03 * s, sy=1 + .05 * s, y=(.42 if last else .2) * s, r=rock)
    if not last:
        body(fb + 7, sx=1 + .025 * s, sy=1 - .04 * s, y=0, r=rock * .5)
    fxkit.hard(act, "body", "scale", 1, fb + 1)
    cones(fb, 1, ring=1)
    cones(fb + 1, 1 + .17 * s, ring=1 + .035 * s)
    cones(fb + 4, 1 - .045 * s, ring=1)
    if not last:
        cones(fb + 7, 1 + .03 * s)
for f, sx, sy, y, r in ((246, 1.07, .9, 0, 0), (249, .97, 1.035, .04, 0), (252, 1.0, 1.0, 0, 0), (254, 1, 1, 0, 0)):
    body(f, sx=sx, sy=sy, y=y, r=r)
fxkit.hard(act, "body", "location", 1, 246)
for f, s, rg in ((246, 1.14, 1.03), (249, .96, 1), (252, 1.0, 1), (254, 1, 1)):
    cones(f, s, ring=rg, lag=0)
for i in range(9):                                       # a run up the piano keys, then the round keys on the beat
    press(i, 204 + 2 * i, depth=6.5, up=4)
for i, f in ((9, 221), (10, 230), (11, 239), (9, 239), (10, 241)):
    press(i, f, depth=6.5, up=4)
follow(f0, f1, gain=1.0)
fxkit.end_action(arm, act, f0)

# ================================================================== multi: cranked up in three pulses, then BOOM
f0, f1 = CLIPS["multi"]
act = fxkit.begin_action(arm, SID + "_multi")
rest(arm, BONES, f0)
PULSES = (312, 320, 328)
for f, s, y in ((301, 1, 0), (306, 1.0, 0), (312, 1.045, 0), (315, 1.025, 0), (320, 1.07, 0), (323, 1.045, 0), (328, 1.095, 0),
                (330, 1.08, 0), (331, .94, 0), (332, 1.1, .05), (334, 1.03, .34), (337, .99, .02), (338, .95, 0), (341, 1.015, .03),
                (344, .998, 0), (346, 1, 0)):
    body(f, sx=1 + (s - 1) * (.6 if f in (331, 338) else 1), sy=s if f not in (331, 338) else 1 - (1 - s) * 1.3, y=y)
fxkit.hard(act, "body", "location", 1, 338)
rnd = random.Random(5)
cone_keys = [(301, 1.0), (306, 1.0)]
for f in range(307, 331):                                # the cones hum with the charge, pushing out with each pulse
    level = 1 + .06 * sstep((f - 306) / 6) + .06 * sstep((f - 315) / 5) + .06 * sstep((f - 323) / 5)
    pulse = sum(.045 * math.exp(-((f - p) / 1.6) ** 2) for p in PULSES)
    cone_keys.append((f, level + pulse + rnd.uniform(-.014, .014) * (f - 306) / 12))
cone_keys += [(331, .88), (332, 1.3), (335, .94), (339, 1.05), (343, .99), (346, 1.0)]
for f, s in cone_keys:
    cones(f, s, lag=0, ring=1 + max(0, s - 1) * .25)
fxkit.hard(act, "cone_l", "scale", 0, 332); fxkit.hard(act, "cone_l", "scale", 1, 332)
for i in range(len(KEYS)):                               # every key goes down and stays down, then they all pop up
    f = 305 + 2 * i
    b = f"k{i}"
    key(arm, b, f, y=0)
    key(arm, b, f + 2, y=-.065)
    key(arm, b, 331, y=-.065)
    key(arm, b, 333, y=.02)
    key(arm, b, 336, y=0)
    key(arm, b, 346, y=0)
follow(f0, f1, gain=1.0)
fxkit.end_action(arm, act, f0)

sc.frame_set(1)
bpy.context.view_layer.update()


def at(bone, f, p):
    sc.frame_set(f)
    pb = arm.pose.bones[bone]
    v = arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted() @ vec(*p)
    return v.x, v.z


# ================================================================== the tier glow
fxkit.neon(SID, arm, FXB, CLIPS, tier=2, bone="body", outline="outline", land_at=103, hit_span=(203, 246),
           pulses=PULSES, charge_span=(307, 331))

# ================================================================== effects
sc.frame_set(1)
back = gp_object(FXB, SID + "_back", depth=.35)
ride(back, arm, "body")
b_pink = gp_mat(back, "glow_pink_fill", PINK, fill=PINK)
b_white = gp_mat(back, "glow_white_fill", WHITE, fill=WHITE)
b_violet = gp_mat(back, "glow_violet", VIOLET)
b_pink_l = gp_mat(back, "glow_pink", PINK)
bb = Board()
CX, CZ = px(490, 500)
fxkit.starburst(bb, 240, 12, CX, CZ, 3.8, 6.4, b_pink, b_white, points=16)
fxkit.shock_rings(bb, 332, CX, CZ, 4.6, 6.4, (b_violet, b_pink_l, b_violet), life=10, lag=2)   # gone by 345
bb.draw(gp_layer(back, "burst"))

on_box = gp_object(FX, SID + "_fx_box", depth=-.8)       # rides the box
ride(on_box, arm, "body")
world = gp_object(FX, SID + "_fx", depth=-.8)            # stays where the frame is
o_white = gp_mat(on_box, "fx_white_line", WHITE)
o_pink = gp_mat(on_box, "fx_pink_line", PINK)
o_violet = gp_mat(on_box, "fx_violet_line", VIOLET)
o_lime = gp_mat(on_box, "fx_lime_line", LIME)
o_whitef = gp_mat(on_box, "fx_white_fill", WHITE, fill=WHITE)
o_pinkf = gp_mat(on_box, "fx_pink_fill", PINK, fill=PINK)
o_limef = gp_mat(on_box, "fx_lime_fill", LIME, fill=LIME)
w_white = gp_mat(world, "fx_white_line", WHITE)
w_pink = gp_mat(world, "fx_pink_line", PINK)
w_violet = gp_mat(world, "fx_violet_line", VIOLET)
w_whitef = gp_mat(world, "fx_white_fill", WHITE, fill=WHITE)
w_pinkf = gp_mat(world, "fx_pink_fill", PINK, fill=PINK)
w_violetf = gp_mat(world, "fx_violet_fill", VIOLET, fill=VIOLET)
w_goldf = gp_mat(world, "fx_gold_fill", GOLD, fill=GOLD)
box_b, world_b = Board(), Board()


def ell(cx, cz, rx, rz, deg, a0=0.0, a1=2 * math.pi, n=64):
    a = math.radians(-deg)                       # icon px tilt (y down) -> world tilt (z up)
    ca, sa = math.cos(a), math.sin(a)
    return [(cx + rx * math.cos(t) * ca - rz * math.sin(t) * sa, cz + rx * math.cos(t) * sa + rz * math.sin(t) * ca)
            for t in (a0 + (a1 - a0) * i / (n - 1) for i in range(n))]


def bass_rings(board, f0, side, power=1.0, life=9, mats=None):
    """Rings rolling off a speaker's chrome ring on a kick: the speaker's own ellipse, growing, thinning away."""
    cx, cy, rx, ry, deg = SPK[side]
    X, Z = px(cx, cy)
    for j, mat in enumerate(mats or (o_white, o_violet)):
        for k in range(life):
            t = k / (life - 1)
            g = min(1.9, 1.04 + (.42 + .1 * j) * power * t ** .8)
            board.add(f0 + 2 * j + k, lambda dr, g=g, t=t, mat=mat: stroke(
                dr, ell(X, Z, rx / 100 * g, ry / 100 * g, deg, n=72), .05 * (1 - t) ** 1.3 + .006, mat=mat, cyclic=True))


def sound_waves(board, f0, side, power=1.0, n=3, life=11, mats=None):
    """Arcs fanning out of a side of the box - ))) - one after another, thinning as they go."""
    if side == "l":
        ox, oz, ang = *px(20, 575), math.pi
    else:
        ox, oz, ang = *px(985, 600), 0.0
    for j in range(n):
        mat = (mats or (o_white, o_pink, o_violet))[j % 3]
        for k in range(life):
            t = k / (life - 1)
            r = .25 + min(1.1 * power, .85) * t + .05 * j
            span = math.radians(42 - 8 * t)
            pts = [(ox + math.cos(ang + a) * r - math.cos(ang) * .25, oz + math.sin(ang + a) * r * 1.15)
                   for a in (-span + 2 * span * i / 16 for i in range(17))]
            board.add(f0 + 3 * j + k, lambda dr, pts=pts, t=t, mat=mat: stroke(
                dr, pts, 0, radii=fxkit.taper(len(pts), (.095 * (1 - t) ** 1.1 + .012) * (1 - t ** 6), ends=.3), mat=mat))


def note_shape(dr, x, z, s, kind, tilt, mat_fill, mat_line):
    """A music note in Grease Pencil: kind 0 an eighth note, 1 two beamed eighths."""
    ca, sa = math.cos(tilt), math.sin(tilt)

    def P(u, v):
        return (x + (u * ca - v * sa) * s, z + (u * sa + v * ca) * s)
    heads = [(0, 0)] if kind == 0 else [(-.32, -.06), (.32, .06)]
    for hx, hz in heads:
        stroke(dr, [P(hx + .17 * math.cos(t) * math.cos(.45) - .12 * math.sin(t) * math.sin(.45),
                      hz + .17 * math.cos(t) * math.sin(.45) + .12 * math.sin(t) * math.cos(.45)) for t in
                    (2 * math.pi * i / 20 for i in range(20))], .004, mat=mat_fill, cyclic=True, fill=True, line=False)
        stroke(dr, [P(hx + .15, hz + .03), P(hx + .15, hz + .78)], .035 * s, mat=mat_line)
    if kind == 0:
        stroke(dr, [P(.15, .78), P(.3, .62), P(.42, .45), P(.36, .3)], .035 * s, mat=mat_line)
    else:
        stroke(dr, [P(-.17, .72), P(.47, .84), P(.47, .74), P(-.17, .62)], .004, mat=mat_fill, cyclic=True, fill=True, line=False)


def note(board, f0, life, x0, z0, vx, vz, s, kind, seed, mat_fill, mat_line):
    """A note floating up: pops in, sways as it rises, shrinks away to nothing."""
    rnd = random.Random(seed)
    ph = rnd.uniform(0, 6.28)
    for k in range(life):
        t = k / (life - 1)
        size = s * min(1.0, k / 3) * (1 - sstep((t - .7) / .3))
        if size < .02:
            continue
        x = x0 + vx * t + .18 * math.sin(ph + t * 6)
        z = z0 + vz * t
        tilt = .25 * math.sin(ph + t * 5)
        board.add(f0 + k, lambda dr, x=x, z=z, size=size, tilt=tilt: note_shape(dr, x, z, size, kind, tilt, mat_fill, mat_line))


def led(board, f0, life, power=1.0, mat=None):
    """The power light flares with a beat."""
    cx, cy, hx, hy = LED
    X, Z = px(cx, cy)
    for k in range(life):
        t = k / max(1, life - 1)
        e = power * (1 - t) ** 1.5
        if e < .05:
            continue
        g = .85 + .25 * e
        pts = []
        for i in range(32):
            a = 2 * math.pi * i / 32
            c, s_ = math.cos(a), math.sin(a)
            pts.append((X + (hx / 100) * g * math.copysign(abs(c) ** .5, c), Z + (hy / 100) * g * math.copysign(abs(s_) ** .5, s_)))
        board.add(f0 + k, lambda dr, pts=pts, e=e: stroke(dr, pts, .004, opacity=min(1, .35 + .6 * e), mat=mat or o_pinkf,
                                                          cyclic=True, fill=True, line=False))


# idle: the light on every beat, small rings on the strong beats, a note now and then
for fb, s in IDLE_BEATS:
    led(box_b, fb + 1, 7, power=s)
    if s > .8:
        for side in "lr":
            bass_rings(box_b, fb + 1, side, power=.45, life=7, mats=(o_violet,))
note(world_b, 8, 26, *px(190, 300), -.6, 1.5, .95, 0, 1, w_pinkf, w_pink)
note(world_b, 42, 26, *px(820, 330), .5, 1.4, .9, 1, 2, w_whitef, w_white)

# land: the knock booms out of both speakers and both sides
for side in "lr":
    bass_rings(box_b, 102, side, power=.8, life=8)
    sound_waves(box_b, 103, side, power=.7, n=2, life=9)
led(box_b, 102, 8, power=1.0)

# hit: every beat booms, notes fly, sparkles
for n, (fb, s) in enumerate(HIT_BEATS):
    led(box_b, fb + 1, 7, power=s, mat=o_pinkf if n % 2 else o_limef)
    for side in "lr":
        bass_rings(box_b, fb + 1, side, power=.9 * s, life=8)
        sound_waves(box_b, fb + 1, side, power=.95 * s, n=3 if n < len(HIT_BEATS) - 1 else 2, life=10 if n < len(HIT_BEATS) - 1 else 9)
rnd = random.Random(8)
for i in range(7):
    side = i % 2
    x0, z0 = px(170, 360) if side == 0 else px(790, 360)
    note(world_b, 205 + 5 * i, min(24, 253 - (205 + 5 * i)), x0 + rnd.uniform(-.4, .4), z0 + rnd.uniform(0, .4), (-1 if side == 0 else 1) * rnd.uniform(.6, 1.4),
         rnd.uniform(1.6, 2.3), rnd.uniform(.9, 1.2), i % 2, 30 + i, (w_pinkf, w_whitef, w_violetf)[i % 3], (w_pink, w_white, w_violet)[i % 3])
for i in range(9):
    fxkit.sparkle(world_b, 222 + rnd.randint(0, 22), rnd.randint(6, 9), rnd.uniform(-5.6, 5.6), rnd.uniform(-3.6, 4.6),
                  rnd.uniform(.22, .42), w_goldf if i % 3 == 0 else w_whitef, rot0=rnd.uniform(0, 1))

# multi: charge rings pour into the speakers, the light climbs, lightning crackles; then it all blows out
for p in PULSES:
    for side in "lr":
        cx, cy, rx, ry, deg = SPK[side]
        X, Z = px(cx, cy)
        for k in range(7):
            t = k / 6
            g = 1.75 - .7 * t
            box_b.add(p - 6 + k, lambda dr, g=g, t=t, X=X, Z=Z, rx=rx, ry=ry, deg=deg: stroke(
                dr, ell(X, Z, rx / 100 * g, ry / 100 * g, deg, n=72), .015 + .04 * t, mat=o_pink, cyclic=True))
    led(box_b, p, 8, power=1.0 + .3 * PULSES.index(p), mat=o_pinkf)
fxkit.lightning(box_b, 309, 330, CX, CZ, (4.5, 3.3), (5.7, 4.2), (o_pink, o_white, o_violet), per=3, step=2, seed=3)
for side in "lr":
    bass_rings(box_b, 332, side, power=1.6, life=10, mats=(o_white, o_pink, o_violet))
    sound_waves(box_b, 332, side, power=1.1, n=3, life=9)
led(box_b, 332, 10, power=1.6, mat=o_limef)
mx, mz = px(490, 500)
fxkit.streaks(world_b, 333, 8, mx, mz, 4.0, 6.2, (w_white, w_pink, w_violet), n=16, rot=.1, width=.04)
for i in range(5):
    a = math.radians(40 + 25 * i)
    note(world_b, 333 + i // 2, 345 - (333 + i // 2), *px(490, 160), math.cos(a) * 2.6, 1.0 + math.sin(a) * .8, 1.0, i % 2, 60 + i,
         (w_pinkf, w_whitef)[i % 2], (w_pink, w_white)[i % 2])

box_b.draw(gp_layer(on_box, "fx"))
world_b.draw(gp_layer(world, "fx"))

# ================================================================== on the art: the tape reels, landing dust
sc.frame_set(1)
art_fx = gp_object(ART, SID + "_artfx", depth=-1.0)
ride(art_fx, arm, "body")
m_spoke = gp_mat(art_fx, "fx_reel", (.85, .85, .88, 1))
m_dust = gp_mat(art_fx, "fx_dust", (.40, .40, .44, 1), fill=(.80, .80, .84, 1))
ab = Board()
SPEED = {"idle": 9.0, "land": 9.0, "hit": 16.0, "multi": 9.0}     # degrees a frame: the tape runs
for clip, (a, b) in CLIPS.items():
    # the reels turn a whole number of thirds of a turn over each clip (three spokes: every third looks the same),
    # so the last frame of land / hit / multi shows them exactly as the rest pose does, and the idle loops seamlessly
    span = (b - a + 1) if clip == "idle" else (b - a)
    raw = [0.0]
    for f in range(a + 1, b + 2):
        raw.append(raw[-1] + SPEED[clip] * (2.2 if clip == "multi" and f >= 307 else 1.0))
    total = raw[span]
    k = 120 * max(1, round(total / 120)) / total
    for f in range(a, b + 1):
        ang = math.radians(raw[f - a] * k)
        for rx_, ry_, rr in REELS:
            X, Z = px(rx_, ry_)
            for j in range(3):
                aa = ang + 2 * math.pi * j / 3
                ab.add(f, lambda dr, X=X, Z=Z, rr=rr, aa=aa: stroke(
                    dr, [(X + math.cos(aa) * rr / 100 * .3, Z + math.sin(aa) * rr / 100 * .3),
                         (X + math.cos(aa) * rr / 100 * .78, Z + math.sin(aa) * rr / 100 * .78)], rr / 100 * .1, mat=m_spoke))
ab.draw(gp_layer(art_fx, "reels"))

dust_ob = gp_object(ART, SID + "_dust", depth=-1.0)     # dust stays on the ground, not on the box
m_dust2 = gp_mat(dust_ob, "fx_dust", (.40, .40, .44, 1), fill=(.80, .80, .84, 1))
w_lime_d = gp_mat(dust_ob, "fx_lime_line", LIME)
db = Board()
for x0, side, seed in ((150, -1, 3), (860, 1, 5), (300, -1, 9), (650, 1, 13)):
    far = 1 if seed in (3, 5) else .6
    X, Z = px(x0, 840 if x0 > 500 else 760)
    fxkit.dust(db, 102, 12, X, Z - .1, .85 * far, m_dust2, drift=(side * 1.6 * far, .4), seed=seed)
for k, f in enumerate(range(102, 108)):
    t = k / 5
    for (x0, y0), s in (((120, 752), -1), ((900, 860), 1)):
        X, Z = px(x0, y0)
        db.add(f, lambda dr, X=X, Z=Z, s=s, t=t: stroke(dr, [(X + s * (.2 + .9 * t), Z - .05), (X + s * (.6 + 1.2 * t), Z + .1 * t)],
                                                       .035 * (1 - t) + .008, mat=w_lime_d))
db.draw(gp_layer(dust_ob, "dust"))

sc.frame_start, sc.frame_end = 1, max(b for a, b in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], "| saved", fxkit.save(SID))
