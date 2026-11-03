# L9 - the freight car with a graffiti piece - animated in Blender: four Actions on its rig (idle, land, hit, multi)
# laid one after another on the rig's NLA track, and its effects drawn frame by frame in Grease Pencil.
#   the rig     the car is ONE image (tools/blender/cuts/L9.py) on a fine mesh skinned to four bones: the car body
#               (rigid steel: it rocks and bounces), the two bogies (each stays on the rail and kicks up when a wheel
#               hits a rail joint), and the root. The strip between body and bogies - the bolsters and springs just
#               under the underframe - is weighted half and half, so the springs are what squeeze and stretch
#   the motion  every rail joint is a wheel bump: the front wheel, then the rear one, then the other bogie a beat
#               later. The car body is never keyed by hand: it rides its springs - a damped spring in heave and one
#               in pitch, driven by where the bogies hold it and by how the car is shoved (worked out in Blender
#               frame by frame from the keys, then keyed sparsely)
#   idle        rolling along: two rail joints a loop, clack-clack, clack-clack, the body nodding on its springs
#   land        set down on the rails: right bogie first, the body sinks on its springs and bobs; sparks off the wheels
#   hit         a coupling jolt: it lurches forward so hard it hops off the rails, slams back down (a clack and
#               sparks off all four wheels), snaps back past its spot and rocks to rest - the wheels spinning, a shower
#               of sparks off the rear wheels then the front ones, speed lines, wet paint flung off the fresh piece,
#               the piece glinting
#   multi       a pull-back toy: wound back click by click (three notches, the wheels spinning backwards, sparks
#               spat forward, the rail crackling under it more each click, the car squatting and trembling on its
#               springs); let go, it shoots forward - a flat ring flung out round it, speed lines, a shower of sparks,
#               a cloud of dust - and the coupling snaps it back to its spot
#   effects     spinning glints on the wheel rims (the wheels turning, smeared when fast), clack ticks at the rail,
#               sparks, speed lines, the rail's crackle, dust and wheel smoke, paint drops, glints and the launch ring -
#               its own effects (a low symbol: no tier glow)
# Runs INSIDE Blender, after build_symbol_scene.py (tools/blender/run.py runs both in a background Blender).
import bpy, importlib, math, os, random, sys
from mathutils import Matrix, Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
import fxkit
importlib.reload(fxkit)
from fxkit import (key, rest, px, smooth, gp_object, gp_mat, gp_layer, ride, stroke, star, Board, WHITE, LIME, GOLD)

SID = "L9"
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
    """(name, head px, tail px or None, parent) - a bone with no tail points up (x/y keys move it right/up)."""
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    for name, head, tail, parent in defs:
        b = eb.get(name) or eb.new(name)
        b.head = wpt(*head)
        if tail is None:
            b.tail = b.head + Vector((0, 0, .6))
            b.roll = 0
        else:
            b.tail = wpt(*tail)
            b.align_roll(Vector((0, -1, 0)))
        b.parent = eb[parent] if parent else None
        b.use_connect = False
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


def spring(drive, n, freq, zeta, sub=8, v0=0.0, x0=0.0, loop=False, laps=4):
    """A damped spring (freq Hz, zeta) following drive(t) -> target (and drive accelerations), frame by frame:
    drive(t) returns (target, extra acceleration). n frames; a loop runs a few laps and returns the settled one."""
    w = 2 * math.pi * freq
    dt = 1.0 / (FPS * sub)
    x, v = x0, v0
    out = []
    for lap in range(laps if loop else 1):
        rec = []
        for k in range(n):
            rec.append(x)
            for s in range(sub):
                t = (k + s / sub) / FPS
                tgt, acc = drive(t)
                a = w * w * (tgt - x) - 2 * zeta * w * v + acc
                v += a * dt
                x += v * dt
        out = rec
    return out


def to_rest_start(vals):
    """A looping series moved to start exactly at rest: the offset at its first frame taken out smoothly over the
    lap (whole at the first frame, nothing halfway round - a raised cosine), so the loop still joins up."""
    n = len(vals)
    a = vals[0]
    return [v - a * (.5 + .5 * math.cos(2 * math.pi * k / n)) for k, v in enumerate(vals)]


def keys(bone, f0, vals, channel, tol, loop=False):
    fxkit.key_series(arm, bone, f0, vals, channel=channel, tol=tol, loop=loop)


# ================================================================== the rig
# icon px: the car body rocks about the middle of its springs; each bogie stands on the rail under its wheels
SPRINGS = (500, 590)
RAIL = 655
BOGIE_L, BOGIE_R = (205, RAIL), (796, RAIL)
WHEELS = {"bogie_l": [(153, 620), (257, 620)], "bogie_r": [(743, 620), (848, 620)]}
WHEEL_R = 33
add_bones([("root", (500, RAIL), None, None),
           ("body", SPRINGS, None, "root"),
           ("bogie_l", BOGIE_L, None, "root"),
           ("bogie_r", BOGIE_R, None, "root")])


def car_weights(x, y):
    """the car body above the underframe's foot; each bogie below it across its own span (soft at its ends, so the
    sticker border round the wheels stretches into the boxes' border instead of tearing); the springs between"""
    down = sstep(580, 616, y)                                   # 0 on the body, 1 on the wheels
    wl = down * sstep(96, 116, x) * (1 - sstep(296, 316, x))
    wr = down * sstep(686, 706, x) * (1 - sstep(886, 906, x))
    return {"body": 1 - wl - wr, "bogie_l": wl, "bogie_r": wr}


skin("body", car_weights)
BONES = ["root", "body", "bogie_l", "bogie_r"]

ART, FXB, FX = fxkit.layers(sc, SID)
fxkit.glow_compositor(sc, SID, back=dict(strength=.7, size=.5, gain=1.3), front=dict(strength=.75, size=.4, gain=1.4))
if arm.animation_data:
    arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)

CLIPS = {"idle": (1, 78), "land": (101, 124), "hit": (201, 254), "multi": (301, 348)}
arm["clips"] = {k: list(v) for k, v in CLIPS.items()}
SPAN = (BOGIE_R[0] - BOGIE_L[0]) / 100.0          # units between the bogie centres
WB = (WHEELS["bogie_l"][1][0] - WHEELS["bogie_l"][0][0]) / 100.0   # a bogie's wheelbase, units


def bump(f, at, amp, up=1.6, down=3.2):
    """a wheel dropping off a rail joint and kicked back up: quick rise, a slower fall with a little undershoot"""
    t = f - at
    if t < 0 or t > up + down + 3:
        return 0.0
    if t < up:
        return amp * math.sin(.5 * math.pi * t / up)
    t2 = (t - up) / down
    if t2 < 1:
        return amp * (math.cos(math.pi * t2) * .5 + .5) * (1 - .25 * t2) - amp * .18 * math.sin(math.pi * t2)
    return -amp * .12 * math.sin(math.pi * min(1, (t - up - down) / 3))


def bogie_motion(f, events):
    """(lift, tilt degrees) of a bogie from its wheel bumps: events [(frame, wheel 0 rear / 1 front, amp)]"""
    front = sum(bump(f, a, amp) for a, wheel, amp in events if wheel == 1)
    back = sum(bump(f, a, amp) for a, wheel, amp in events if wheel == 0)
    return (front + back) / 2, math.degrees(math.atan2(front - back, WB))


def ride_springs(f0, n, lift_l, lift_r, shove=None, freq=(2.3, 2.6), zeta=(.32, .3), loop=False, gain=(1, 1)):
    """the car body on its springs: heave follows the mean of the bogies' lifts, pitch their difference (and a shove:
    the car's acceleration rocks it back on its springs). Returns per-frame (heave units, pitch degrees, x lag)."""
    def heave(t):
        f = f0 + t * FPS
        return ((lift_l(f) + lift_r(f)) / 2, 0.0)

    def pitch(t):
        f = f0 + t * FPS
        tgt = math.degrees(math.atan2(lift_r(f) - lift_l(f), SPAN))
        return (tgt, (shove(f)[1] if shove else 0.0))

    def lag(t):
        f = f0 + t * FPS
        return (0.0, (shove(f)[0] if shove else 0.0))

    h = spring(heave, n, freq[0], zeta[0], loop=loop)
    p = spring(pitch, n, freq[1], zeta[1], loop=loop)
    x = spring(lag, n, 2.0, .35, loop=loop)
    if loop:
        h, p, x = to_rest_start(h), to_rest_start(p), to_rest_start(x)
    return [v * gain[0] for v in h], [v * gain[1] for v in p], x


# ================================================================== idle: rolling along, two rail joints a loop
f0, f1 = CLIPS["idle"]
N = f1 - f0 + 1
act = fxkit.begin_action(arm, SID + "_idle")
rest(arm, BONES, f0)
A = .03                                              # a wheel's kick, units (3 px)
EV_R = [(f0 + 7, 1, A), (f0 + 10, 0, A * .9), (f0 + 46, 1, A * .9), (f0 + 49, 0, A)]      # front bogie first ...
EV_L = [(f0 + 16, 1, A), (f0 + 19, 0, A * .85), (f0 + 55, 1, A * .95), (f0 + 58, 0, A * .9)]   # ... the rear one a beat later
idle_l = [bogie_motion(f, EV_L) for f in range(f0, f0 + N)]
idle_r = [bogie_motion(f, EV_R) for f in range(f0, f0 + N)]
keys("bogie_l", f0, [v[0] for v in idle_l], "y", .0015, loop=True)
keys("bogie_l", f0, [v[1] for v in idle_l], "r", .06, loop=True)
keys("bogie_r", f0, [v[0] for v in idle_r], "y", .0015, loop=True)
keys("bogie_r", f0, [v[1] for v in idle_r], "r", .06, loop=True)
LL = lambda f: bogie_motion(f0 + (f - f0) % N, EV_L)[0]
LR = lambda f: bogie_motion(f0 + (f - f0) % N, EV_R)[0]
h, p, _ = ride_springs(f0, N, LL, LR, loop=True, gain=(1.5, 1.6))
# and a slow float on top: the car breathing on its springs between the joints
h = [v + .006 * math.sin(2 * math.pi * k / N) * math.sin(2 * math.pi * k / N) for k, v in enumerate(h)]
keys("body", f0, h, "y", .0012, loop=True)
keys("body", f0, p, "r", .03, loop=True)
fxkit.make_cyclic(act)
fxkit.end_action(arm, act, f0)

# ================================================================== land: set down on the rails, right bogie first
f0, f1 = CLIPS["land"]
N = f1 - f0 + 1
act = fxkit.begin_action(arm, SID + "_land")
rest(arm, BONES, f0)
TOUCH_R, TOUCH_L = f0 + 1, f0 + 2


def squash(f, at, amp=.055, depth=.025):
    """a bogie taking the car's weight: it squashes on the rail and springs back"""
    t = f - at
    if t < 0:
        return 1.0, 0.0
    e = math.exp(-t / 3.0) * math.cos(t * .75)
    return 1 - amp * e, -depth * e


for bone, at in (("bogie_r", TOUCH_R), ("bogie_l", TOUCH_L)):
    sq = [squash(f, at) for f in range(f0, f1 + 1)]
    for i in range(len(sq) - 4, len(sq)):
        sq[i] = (1 + (sq[i][0] - 1) * (len(sq) - 1 - i) / 4, sq[i][1] * (len(sq) - 1 - i) / 4)
    keys(bone, f0, [s for s, _ in sq], "sy", .002)
    keys(bone, f0, [1 + (1 - s) * .6 for s, _ in sq], "sx", .002)
    keys(bone, f0, [y for _, y in sq], "y", .001)


def land_drive_l(f):
    return squash(f, TOUCH_L)[1] * 2.2


def land_drive_r(f):
    return squash(f, TOUCH_R)[1] * 2.2


# the body arrives falling: its springs catch it - an initial downward speed, then the spring does the rest
h = spring(lambda t: ((land_drive_l(f0 + t * FPS) + land_drive_r(f0 + t * FPS)) / 2, 0.0), N, 2.4, .33, v0=-1.25)
p = spring(lambda t: (math.degrees(math.atan2(land_drive_r(f0 + t * FPS) - land_drive_l(f0 + t * FPS), SPAN)) * 3, 0.0), N, 2.7, .3)
for arr in (h, p):                                    # the clip ends exactly at rest
    for i in range(N - 6, N):
        arr[i] *= (N - 1 - i) / 6
keys("body", f0, h, "y", .001)
keys("body", f0, p, "r", .03)
rest(arm, BONES, f1)
fxkit.end_action(arm, act, f0)


# ================================================================== hit: a coupling jolt - lurch, a hop off the rails, snap back
f0, f1 = CLIPS["hit"]
N = f1 - f0 + 1
act = fxkit.begin_action(arm, SID + "_hit")
rest(arm, BONES, f0)
HOP_DOWN = f0 + 14                                    # the wheels come back down on the rails
SNAP = f0 + 22                                        # the coupling catches it
for f, x, y in ((f0 + 4, -.09, 0), (f0 + 9, .5, .1), (f0 + 12, .66, .12), (HOP_DOWN, .71, 0), (SNAP, -.11, 0),
                (f0 + 29, .045, 0), (f0 + 36, 0, 0), (f1, 0, 0)):
    key(arm, "root", f, x=x, y=y)
fxkit.hard(act, "root", "location", 1, HOP_DOWN)
fxkit.hard(act, "root", "location", 0, SNAP)


def root_x(f):
    sc.frame_set(int(f))
    return arm.pose.bones["root"].location.x


RX = [root_x(f) for f in range(f0 - 1, f1 + 2)]
ACC = [(RX[i + 1] - 2 * RX[i] + RX[i - 1]) * FPS * FPS for i in range(1, len(RX) - 1)]   # units/s^2, per frame f0..f1
# the wheels slam back down on the rails (all four, front a hair first), then two more rail joints as it rocks
EV_R = [(HOP_DOWN - 1, 1, .06), (HOP_DOWN, 0, .055), (f0 + 26, 1, .03), (f0 + 28, 0, .028)]
EV_L = [(HOP_DOWN, 1, .055), (HOP_DOWN + 1, 0, .05), (f0 + 30, 1, .03), (f0 + 32, 0, .025)]
for bone, ev in (("bogie_l", EV_L), ("bogie_r", EV_R)):
    mv = [bogie_motion(f, ev) for f in range(f0, f1 + 1)]
    keys(bone, f0, [m[0] for m in mv], "y", .0015)
    keys(bone, f0, [m[1] for m in mv], "r", .06)


def shove(f):
    a = ACC[max(0, min(len(ACC) - 1, int(round(f - f0))))]
    return (-a * .45, a * 8.5)                       # lag back (units/s^2), pitch back (deg/s^2 per unit/s^2)


h, p, xl = ride_springs(f0, N, lambda f: bogie_motion(f, EV_L)[0], lambda f: bogie_motion(f, EV_R)[0], shove=shove,
                        freq=(2.4, 1.9), zeta=(.3, .26), gain=(1.6, 1.0))
p = [5.2 * math.tanh(v / 5.2) for v in p]
for arr in (h, p, xl):
    for i in range(N - 8, N):
        arr[i] *= ((N - 1 - i) / 8) ** 1.5
keys("body", f0, h, "y", .001)
keys("body", f0, p, "r", .04)
keys("body", f0, [v * .4 for v in xl], "x", .001)
rest(arm, BONES, f1)
fxkit.end_action(arm, act, f0)

# ================================================================== multi: a pull-back car - wound back click by click, let go
f0, f1 = CLIPS["multi"]
N = f1 - f0 + 1
act = fxkit.begin_action(arm, SID + "_multi")
rest(arm, BONES, f0)
PULSES = (f0 + 4, f0 + 12, f0 + 20)                  # each click it winds back a notch, the wheels spinning backwards
GO = f0 + 27                                          # let go: it shoots forward
WIND = [(f0, 0), (PULSES[0] + 2, -.065), (PULSES[1], -.065), (PULSES[1] + 2, -.13), (PULSES[2], -.13), (PULSES[2] + 2, -.2),
        (GO - 1, -.205), (GO + 4, .62), (GO + 7, .7), (GO + 14, -.08), (GO + 19, .025), (f1 - 3, 0), (f1, 0)]
for f, x in WIND:
    key(arm, "root", f, x=x)
for f in (PULSES[0] + 2, PULSES[1] + 2, PULSES[2] + 2, GO - 1, GO + 14):
    fxkit.hard(act, "root", "location", 0, f)
RX = [root_x(f) for f in range(f0 - 1, f1 + 2)]
ACC = [(RX[i + 1] - 2 * RX[i] + RX[i - 1]) * FPS * FPS for i in range(1, len(RX) - 1)]
EV_R = [(p, 0, .035) for p in PULSES] + [(p + 2, 1, .03) for p in PULSES] + [(GO + 3, 1, .05), (GO + 5, 0, .045)]
EV_L = [(p + 1, 0, .035) for p in PULSES] + [(p + 3, 1, .03) for p in PULSES] + [(GO + 6, 1, .05), (GO + 8, 0, .045)]
rnd = random.Random(9)
TREM = [0.0] * N                                       # wound up: a tremble that builds with each click
for i in range(N):
    f = f0 + i
    env = smooth(PULSES[0] - 1, PULSES[0] + 2, f) * (.5 + .25 * smooth(PULSES[1], PULSES[1] + 2, f) + .25 * smooth(PULSES[2], PULSES[2] + 2, f)) \
        * (1 - smooth(GO - 1, GO + 1, f))
    TREM[i] = env * .011 * (1 if i % 2 else -1) * (.7 + .3 * rnd.random())
for bone, ev, ph in (("bogie_l", EV_L, 0), ("bogie_r", EV_R, 1)):
    mv = [bogie_motion(f, ev) for f in range(f0, f1 + 1)]
    keys(bone, f0, [m[0] + TREM[i] * .5 * (1 if (i + ph) % 2 else -1) for i, m in enumerate(mv)], "y", .001)
    keys(bone, f0, [m[1] for m in mv], "r", .06)
SQUAT = lambda f: -.028 * (smooth(PULSES[0], PULSES[0] + 3, f) + smooth(PULSES[1], PULSES[1] + 3, f) + smooth(PULSES[2], PULSES[2] + 3, f)) \
    * (1 - smooth(GO - 1, GO + 2, f))
h, p, xl = ride_springs(f0, N, lambda f: bogie_motion(f, EV_L)[0] + SQUAT(f), lambda f: bogie_motion(f, EV_R)[0] + SQUAT(f),
                        shove=shove, freq=(2.6, 1.9), zeta=(.3, .25), gain=(1.3, 1.0))
p = [5.5 * math.tanh(v / 5.5) for v in p]
h = [v + TREM[i] for i, v in enumerate(h)]
for arr in (h, p, xl):
    for i in range(N - 8, N):
        arr[i] *= ((N - 1 - i) / 8) ** 1.5
keys("body", f0, h, "y", .0008)
keys("body", f0, p, "r", .04)
keys("body", f0, [v * .4 for v in xl], "x", .001)
rest(arm, BONES, f1)
fxkit.end_action(arm, act, f0)

# ================================================================== effects
# (sizes in units: the frame is 13 across, 512 px - a unit is ~39 px, so a line needs a radius of ~.025 to read)
sc.frame_set(1)
W_YEL, W_ORA, W_HOT = (1.0, .82, .32, 1), (1.0, .52, .12, 1), (1.0, .97, .84, 1)
PAINT = [(.55, .95, .2, 1), (1.0, .66, .1, 1), (1.0, .86, .16, 1)]          # the piece's lime, orange and yellow
DUST_LINE, DUST_FILL = (.5, .47, .43, 1), (.86, .83, .78, 1)
SMOKE_LINE, SMOKE_FILL = (.26, .25, .26, 1), (.52, .5, .5, 1)
LIM = 6.05                                               # everything stays inside the frame (6.5), its glow too


def wheel_world(bone, k):
    return px(*WHEELS[bone][k])


def contact(bone, k):                                    # where a wheel meets the rail
    x, _ = px(WHEELS[bone][k][0], RAIL)
    return x, px(0, RAIL)[1]


def root_dx(f):
    sc.frame_set(int(f))
    return arm.pose.bones["root"].location.x


# --- wheel rims: glints spinning round the visible part of each wheel (they ride the bogies)
rims = {}
for bone in ("bogie_l", "bogie_r"):
    ob = gp_object(ART, f"{SID}_rims_{bone}", depth=-1.0)
    ride(ob, arm, bone)
    rims[bone] = (ob, gp_mat(ob, "rim_glint", (.93, .98, 1.0, 1)), gp_mat(ob, "rim_blur", (.6, .8, .9, 1)), Board())


def rim_glints(f, angle, count=2, length=52, blur=0.0, level=1.0):
    """bright arcs on each wheel's rim at `angle` (degrees, turning clockwise as it rolls right; negative speed =
    backwards) - drawn only on the rim's lower part, which shows below the side frame; blur adds a smeared arc
    behind each (a fast spin)"""
    r = WHEEL_R / 100.0 * .9
    for bone, (ob, m_glint, m_blur, bd) in rims.items():
        for k in range(2):
            cx, cz = wheel_world(bone, k)
            for j in range(count):
                a0 = angle + 360.0 * j / count + 23 * k + (7 if bone == "bogie_r" else 0)
                a0 = (a0 + 180) % 360 - 180
                lo, hi = -170, -12                         # the visible arc (degrees, 0 = right, -90 = bottom)
                span = length + abs(blur)
                sgn = 1 if blur >= 0 else -1
                seg = [a for a in (a0 + sgn * s for s in [-span * u / 12 for u in range(13)]) if lo <= a <= hi]
                if len(seg) < 2:
                    continue
                pts = [(cx + math.cos(math.radians(a)) * r, cz + math.sin(math.radians(a)) * r) for a in seg]
                m = len(pts)
                if blur:
                    bd.add(f, lambda dr, pts=pts, m=m: stroke(dr, pts, 0, radii=[.05 * (1 - i / (m - 1)) ** .7 + .006 for i in range(m)],
                                                               mat=m_blur))
                head = pts[:max(2, int(m * length / span))]
                hm = len(head)
                bd.add(f, lambda dr, head=head, hm=hm: stroke(dr, head, 0, radii=[.046 * level * min(1.0, 1.8 * (1 - i / (hm - 1))) ** .6 + .006
                                                                                  for i in range(hm)], mat=m_glint))


f0, f1 = CLIPS["idle"]                                   # rolling slowly, two turns a loop (the arcs repeat exactly)
for f in range(f0, f1 + 1):
    rim_glints(f, -360.0 * 2 * (f - f0) / (f1 - f0 + 1), level=.8)
f0, f1 = CLIPS["land"]                                   # the wheels creep a little as it settles
for f in range(f0, f1 + 1):
    rim_glints(f, -40.0 * smooth(f0, f1, f) - 20, level=.8)
f0, f1 = CLIPS["hit"]                                    # spun hard by the lurch, backwards on the snap back, to rest
ang = 0.0
for f in range(f0, f1 + 1):
    spd = 48 * smooth(f0 + 3, f0 + 8, f) * (1 - smooth(f0 + 13, f0 + 19, f)) - 32 * smooth(f0 + 17, SNAP, f) * (1 - smooth(f0 + 26, f0 + 37, f))
    ang -= spd
    rim_glints(f, ang, count=3 if abs(spd) > 20 else 2, blur=max(-80, min(80, spd * 1.5)), level=1.0)
f0, f1 = CLIPS["multi"]                                  # spinning backwards as it is wound, forwards as it shoots off
ang = 0.0
for f in range(f0, f1 + 1):
    back = sum(14 * smooth(p_ - 1, p_ + 1, f) * (1 - smooth(p_ + 3, p_ + 6, f)) for p_ in PULSES)
    spd = -back * (1 + .3 * smooth(PULSES[1], PULSES[2], f)) + 56 * smooth(GO - 1, GO + 2, f) * (1 - smooth(GO + 8, GO + 16, f)) \
        - 26 * smooth(GO + 11, GO + 14, f) * (1 - smooth(GO + 17, f1 - 2, f))
    ang -= spd
    rim_glints(f, ang, count=3 if abs(spd) > 22 else 2, blur=max(-85, min(85, spd * 1.5)), level=1.0)
for bone, (ob, m1, m2, bd) in rims.items():
    bd.draw(gp_layer(ob, "rims"))

# --- over the art (bloomed): sparks, clack ticks, speed lines, the rail crackling, the launch burst
fxw = gp_object(FX, SID + "_fx", depth=-.8)
m_yel = gp_mat(fxw, "fx_spark_yellow", W_YEL)
m_ora = gp_mat(fxw, "fx_spark_orange", W_ORA)
m_hot = gp_mat(fxw, "fx_spark_hot", W_HOT)
m_white = gp_mat(fxw, "fx_white_line", WHITE)
m_lime = gp_mat(fxw, "fx_lime_line", LIME)
world = Board()
fxb = gp_object(FX, SID + "_fx_on", depth=-.8)          # rides the car body: glints on the piece
ride(fxb, arm, "body")
o_spark = gp_mat(fxb, "fx_white_fill", WHITE, fill=WHITE)
o_gold = gp_mat(fxb, "fx_gold_fill", GOLD, fill=GOLD)
o_white = gp_mat(fxb, "fx_white_line", WHITE)
onbody = Board()


def sparks(f0, life, x, z, ang, spread, n, speed, seed, g=-10.0, length=.42, width=.052):
    """a spray of sparks off a wheel on the rail: hot streaks (their length the speed's blur) flying out along `ang`
    (degrees) +- spread, falling, thinning to nothing - white-hot, then yellow, then orange as they cool"""
    rnd = random.Random(seed)
    for i in range(n):
        a = math.radians(ang + rnd.uniform(-spread, spread))
        sp = speed * rnd.uniform(.6, 1.15)
        lf = max(4, int(life * rnd.uniform(.6, 1.0)))
        d0 = rnd.randint(0, 1)
        for k in range(lf):
            t = (k + 1) / FPS
            vx, vz = math.cos(a) * sp, math.sin(a) * sp + g * t
            sx_, sz_ = x + math.cos(a) * sp * t, z + math.sin(a) * sp * t + .5 * g * t * t
            if (sz_ < z - .04 and vz < 0) or abs(sx_) > LIM or abs(sz_) > LIM:
                break
            spd_ = math.hypot(vx, vz) or 1
            u = k / max(1, lf - 1)
            ln = length * (.35 + .65 * min(1.0, spd_ / max(1e-3, speed))) * (1 - .6 * u)
            mat = m_hot if u < .3 else m_yel if u < .65 else m_ora
            ex, ez = sx_ - vx / spd_ * ln, sz_ - vz / spd_ * ln
            world.add(f0 + d0 + k, lambda dr, sx_=sx_, sz_=sz_, ex=ex, ez=ez, w=width * (1 - .8 * u) + .006, mat=mat: stroke(
                dr, [(sx_, sz_), ((sx_ + ex) / 2, (sz_ + ez) / 2), (ex, ez)], 0, radii=[w, w * .8, w * .25], mat=mat))


def tick(f, x, z, size=1.0, mat=None):
    """a clack: short strokes kicked up from the rail where a wheel lands on it, flying apart and thinning away"""
    for k in range(4):
        t = k / 3
        for a in (155, 25, 120, 60):
            aa = math.radians(a)
            r0, r1 = (.14 + .16 * t) * size, (.26 + .3 * t) * size
            world.add(f + k, lambda dr, aa=aa, r0=r0, r1=r1, t=t: stroke(
                dr, [(x + math.cos(aa) * r0, z + math.sin(aa) * r0 * .75), (x + math.cos(aa) * r1, z + math.sin(aa) * r1 * .75)],
                .03 * (1 - t) * size + .006, mat=mat if mat is not None else m_white))


def crackle(f, x0, x1, z, amp, seed, mats, width=.03):
    """electric arcs running along the rail between two points"""
    pts = fxkit.zigzag(x0, z, x1, z, n=max(4, int((x1 - x0) / .35)), amp=amp, seed=seed)
    world.add(f, lambda dr, pts=pts: stroke(dr, pts, width, mat=mats[0]), hold=2)
    world.add(f, lambda dr, pts=pts: stroke(dr, pts, width * .4, mat=mats[1]), hold=2)


def ellipse_rings(f0, cx, cz, r0, r1, aspect, mats, life=12, lag=3, width=.12):
    """rings flung out round the car - wide and flat like the car - thinning to threads as they go (never fading)"""
    for j, mat in enumerate(mats):
        for k in range(life):
            t = k / (life - 1)
            r = r0 + (r1 - r0) * (1 - (1 - t) ** 2)
            pts = [(max(-LIM, min(LIM, cx + math.cos(a) * r)), cz + math.sin(a) * r * aspect)
                   for a in (2 * math.pi * i / 120 for i in range(120))]
            world.add(f0 + lag * j + k, lambda dr, pts=pts, w=width * (1 - t) ** 1.3 + .008, mat=mat: stroke(dr, pts, w, mat=mat, cyclic=True))


def speed_lines(f0, life, rows, x_tail, seed, mats=None):
    """speed lines streaming off behind the car: each starts at its tail and stretches back, thick in the middle"""
    rnd = random.Random(seed)
    for j, zz in enumerate(rows):
        d = rnd.randint(0, 3)
        ln0 = rnd.uniform(1.4, 2.6)
        for k in range(life):
            t = k / max(1, life - 1)
            f = f0 + d + k
            xe = x_tail + root_dx(f) - .15 - 1.2 * t
            xs = max(-LIM, xe - ln0 * math.sin(math.pi * min(1, t * 1.6 + .15)))
            if xe - xs < .1 or xe < -LIM + .1:
                continue
            n = 8
            pts = [(xe + (xs - xe) * i / n, zz) for i in range(n + 1)]
            rr = [(.03 * (1 - t) + .008) * math.sin(math.pi * (.15 + .85 * i / n)) ** .5 for i in range(n + 1)]
            mat = (mats or [m_white])[j % len(mats or [m_white])]
            world.add(f, lambda dr, pts=pts, rr=rr, mat=mat: stroke(dr, pts, 0, radii=rr, mat=mat))


# idle: each wheel clacks onto the next rail: a tick and a couple of sparks
f0, f1 = CLIPS["idle"]
for (at, wheel), bone in [((f0 + 7, 1), "bogie_r"), ((f0 + 10, 0), "bogie_r"), ((f0 + 46, 1), "bogie_r"), ((f0 + 49, 0), "bogie_r"),
                          ((f0 + 16, 1), "bogie_l"), ((f0 + 19, 0), "bogie_l"), ((f0 + 55, 1), "bogie_l"), ((f0 + 58, 0), "bogie_l")]:
    x, z = contact(bone, wheel)
    tick(at + 1, x, z - .02, size=.6)
    sparks(at + 1, 7, x, z, 158, 14, 3, 3.0, at * 7 + wheel, length=.24, width=.036)

# land: sparks fanned out along the rail from each wheel as it meets it, a clack
f0, f1 = CLIPS["land"]
for bone, at, seed in (("bogie_r", TOUCH_R, 3), ("bogie_l", TOUCH_L, 7)):
    for k in range(2):
        x, z = contact(bone, k)
        for side, ang in ((-1, 172), (1, 8)):
            sparks(at, 11, x + side * .05, z, ang + (-16 if side < 0 else 16), 16, 5, 4.6, seed * 10 + k * 3 + side, length=.34, width=.045)
        tick(at, x, z - .02, size=.9)

# hit: a shower off the rear wheels as it lurches, a clack and sparks off all four as they slam down, sparks off
# the front ones on the snap back; speed lines streaming behind it
f0, f1 = CLIPS["hit"]
for i, (at, bone, k, ang, n) in enumerate([(f0 + 5, "bogie_l", 0, 150, 10), (f0 + 6, "bogie_l", 1, 148, 9), (f0 + 7, "bogie_r", 0, 152, 7),
                                            (f0 + 8, "bogie_r", 1, 150, 6)]):
    x, z = contact(bone, k)
    for dfr in range(0, 6, 2):
        f = at + dfr
        sparks(f, 14, x + root_dx(f), z, ang, 24, n - dfr // 2, 6.2 - .5 * dfr, 31 * i + dfr)
for bone in ("bogie_l", "bogie_r"):
    for k in range(2):
        x, z = contact(bone, k)
        x += root_dx(HOP_DOWN)
        tick(HOP_DOWN, x, z - .02, size=1.0)
        for side, ang in ((-1, 170), (1, 10)):
            sparks(HOP_DOWN, 11, x, z, ang + (-28 if side < 0 else 28), 20, 5, 4.6, 300 + k * 7 + side + (50 if bone == "bogie_r" else 0))
for i, (at, bone, k) in enumerate([(SNAP - 2, "bogie_r", 1), (SNAP - 1, "bogie_r", 0), (SNAP, "bogie_l", 1), (SNAP + 1, "bogie_l", 0)]):
    x, z = contact(bone, k)
    sparks(at, 13, x + root_dx(at), z, 32, 22, 8, 5.4, 500 + i)
speed_lines(f0 + 6, 13, [px(0, y)[1] for y in (352, 398, 452, 506, 560, 618)], px(28, 0)[0], 11)

# multi: every click, a clack under each wheel and sparks spat forward by the wheels spinning backwards; the rail
# crackling under it, more each click; let go: it shoots off - a flat ring round it, speed lines, sparks
f0, f1 = CLIPS["multi"]
RAILZ = px(0, RAIL)[1]
for p_ in PULSES:
    for bone in ("bogie_l", "bogie_r"):
        for k in range(2):
            x, z = contact(bone, k)
            tick(p_ + 2, x + root_dx(p_ + 2), z - .02, size=.85, mat=m_lime)
for f in range(PULSES[0], GO + 1):
    lvl = sum(smooth(p_ - 1, p_ + 2, f) for p_ in PULSES)
    if f % 2 == 0:
        for bone in ("bogie_l", "bogie_r"):
            for k in range(2):
                x, z = contact(bone, k)
                sparks(f, 10, x + root_dx(f) + .1, z, 24, 20, int(1 + 1.5 * lvl), 3.0 + .9 * lvl, f * 13 + k + (5 if bone == "bogie_r" else 0),
                       g=-8.0, length=.3, width=.042)
        dx = root_dx(f)
        for s in range(int(round(lvl))):                # the rail crackles under it
            a, b = (-4.3, -1.6, .9)[s] + dx, (-1.2, 1.4, 4.1)[s] + dx
            crackle(f, max(-LIM, a), min(LIM, b), RAILZ - .05, .06 + .03 * lvl, f * 3 + s, (m_lime, m_white), width=.026 + .006 * lvl)
CX, CZ = px(500, 470)
ellipse_rings(GO, CX + root_dx(GO + 2), CZ, 4.8, 5.75, .53, (m_lime, m_white), life=11, lag=3)
speed_lines(GO + 1, 13, [px(0, y)[1] for y in (330, 380, 430, 480, 530, 580, 630)], px(28, 0)[0], 17, mats=[m_white, m_lime])
for bone in ("bogie_l", "bogie_r"):
    for k in range(2):
        x, z = contact(bone, k)
        sparks(GO, 14, x + root_dx(GO), z, 150, 24, 10, 6.4, 77 + k + (9 if bone == "bogie_r" else 0))

# glints on the piece (they ride the car body): the hit's shine as it rocks back, the multi's as it shoots off
PIECE = [(215, 455), (340, 432), (468, 412), (585, 450), (700, 437), (790, 425), (420, 520), (640, 505)]
rnd = random.Random(4)
for base, cnt in ((CLIPS["hit"][0] + 16, 7), (GO + 3, 6)):
    for i in range(cnt):
        x, y = PIECE[(i * 3 + (1 if base > 300 else 0)) % len(PIECE)]
        fxkit.sparkle(onbody, base + rnd.randint(0, 16), rnd.randint(9, 12), *px(x + rnd.uniform(-20, 20), y + rnd.uniform(-15, 15)),
                      rnd.uniform(.36, .55), o_gold if i % 3 == 1 else o_spark, rot0=rnd.uniform(0, 1))
f0, f1 = CLIPS["idle"]
fxkit.sparkle(onbody, f0 + 30, 10, *px(812, 418), .36, o_spark, rot0=.3)       # idle: the piece catches the light once
world.draw(gp_layer(fxw, "fx"))
onbody.draw(gp_layer(fxb, "fx"))

# --- on the art: dust and smoke at the rail, wet paint flung off the fresh piece
dust = gp_object(ART, SID + "_dust", depth=-1.0)
m_dust = gp_mat(dust, "fx_dust", DUST_LINE, fill=DUST_FILL)
m_smoke = gp_mat(dust, "fx_smoke", SMOKE_LINE, fill=SMOKE_FILL)
m_paint = [gp_mat(dust, f"fx_paint{i}", tuple(c * .55 for c in col[:3]) + (1,), fill=col) for i, col in enumerate(PAINT)]
db = Board()
f0, f1 = CLIPS["land"]
for bone, at in (("bogie_r", TOUCH_R), ("bogie_l", TOUCH_L)):
    x, z = px(BOGIE_R[0] if bone == "bogie_r" else BOGIE_L[0], RAIL + 4)
    for s, seed in ((-1, 3), (1, 5)):
        fxkit.dust(db, at + 1, 11, x + s * .95, z, .36, m_dust, drift=(s * 1.3, .22), seed=seed + (0 if bone == "bogie_r" else 10))
f0, f1 = CLIPS["hit"]
x, z = px(70, RAIL)
for i, (d, seed) in enumerate(((0, 2), (2, 6), (4, 11), (7, 14))):
    fxkit.dust(db, f0 + 6 + d, 14, max(-LIM + .9, x + root_dx(f0 + 6 + d) - .25 * i), z + .12 * i, .72 - .1 * i, m_dust,
               drift=(-1.5, .6), seed=seed)
for bone in ("bogie_l", "bogie_r"):                     # the wheels slam down: a little dust
    x, z = px(BOGIE_R[0] if bone == "bogie_r" else BOGIE_L[0], RAIL + 4)
    for s in (-1, 1):
        fxkit.dust(db, HOP_DOWN + 1, 10, x + root_dx(HOP_DOWN) + s * .9, z, .34, m_dust, drift=(s * 1.1, .2), seed=60 + s)
f0, f1 = CLIPS["multi"]
for i, f in enumerate(range(PULSES[0] + 1, GO + 1, 3)):  # smoke boiling off the wheels spinning in place
    for bone in ("bogie_l", "bogie_r"):
        x, z = px(BOGIE_R[0] + 70 if bone == "bogie_r" else BOGIE_L[0] + 70, RAIL + 10)
        fxkit.dust(db, f, 12, x + root_dx(f), z - .03 * (i % 2), .2 + .03 * i, m_smoke, drift=(1.1, .25 + .03 * i),
                   seed=40 + i + (20 if bone == "bogie_r" else 0))
x, z = px(60, RAIL)
for i, d in enumerate((1, 3, 6)):                       # the launch kicks a cloud up behind it
    fxkit.dust(db, GO + d, 14, max(-LIM + .9, x + root_dx(GO + d) - .3 * i), z + .14 * i, .75 - .1 * i, m_dust, drift=(-1.6, .6), seed=90 + i)

G = -11.0


TOPS = [(190, 425), (300, 400), (400, 395), (520, 400), (610, 415), (700, 395), (790, 392)]   # the letters' upper edge


def paint_drops(f0, n, seed, vx_rng, vz_rng, life=18):
    """wet paint thrown off the piece: drops in its lime, orange and yellow leaving the letters' top edge, arcing over
    the roof and falling away behind, stretched along their flight, shrinking"""
    rnd = random.Random(seed)
    for i in range(n):
        x, y = TOPS[rnd.randrange(len(TOPS))]
        x0, z0 = px(x + rnd.uniform(-30, 30), y + rnd.uniform(-8, 8))
        vx, vz = rnd.uniform(*vx_rng), rnd.uniform(*vz_rng)
        r0 = rnd.uniform(.08, .14)
        mat = m_paint[i % 3]
        st = f0 + rnd.randint(0, 3)
        for k in range(life):
            t = k / FPS
            f = st + k
            xx = x0 + root_dx(st) + vx * t
            zz = z0 + vz * t + .5 * G * t * t
            r = r0 * (1 - (k / life) ** 2)
            if r < .015 or abs(xx) > LIM - .1 or abs(zz) > LIM - .1:
                break
            stretch = 1 + min(1.5, math.hypot(vx, vz + G * t) * .22)
            ang = math.atan2(vz + G * t, vx)
            pts = [(xx + math.cos(ang) * math.cos(u) * r * stretch - math.sin(ang) * math.sin(u) * r,
                    zz + math.sin(ang) * math.cos(u) * r * stretch + math.cos(ang) * math.sin(u) * r)
                   for u in (2 * math.pi * q / 16 for q in range(16))]
            db.add(f, lambda dr, pts=pts, mat=mat: stroke(dr, pts, .007, mat=mat, cyclic=True, fill=True))


paint_drops(CLIPS["hit"][0] + 6, 16, 21, (-4.6, -1.2), (2.6, 4.8))
paint_drops(SNAP - 1, 9, 25, (1.2, 3.4), (2.4, 4.2))
paint_drops(GO + 1, 14, 23, (-4.8, -1.6), (2.8, 5.0))
db.draw(gp_layer(dust, "dust"))

sc.frame_start, sc.frame_end = 1, max(b for a, b in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], "| saved", fxkit.save(SID))
