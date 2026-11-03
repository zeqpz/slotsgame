# L1 - the spray can - animated in Blender: four Actions on its rig (idle, land, hit, multi) laid one after another
# on the rig's NLA track, and its spray drawn frame by frame in Grease Pencil on the same timeline.
#   the rig     the can (root, on its base), the cap on top of it, the jet (the cone of paint from the nozzle to the
#               cloud) and the painted cloud (tools/blender/cuts/L1.py). Re-pivoted here: the jet turns about its far
#               end in the cloud, so its tip stays in the nozzle - every frame it is keyed to where the pressed cap
#               has taken the nozzle; the cloud swells and swings about where the jet feeds it.
#   the cap     pressed by hand: it squashes down on its stem and springs back
#   the cloud   billows as paint is pushed into it, and follows the can's moves on a soft spring (worked out in
#               Blender from how the keys move the can, keyed onto its bone)
#   the spray   drawn frame by frame: paint droplets streaming down the jet from the nozzle (always - the can is
#               spraying), cartoon mist puffs boiling off the cloud and shrinking away, droplets flung off it
#   idle        two gentle presses a loop; each sends a pulse of paint down the jet and the cloud breathes out
#   land        the can thuds onto its base, rocks; the jolt squirts a burst of paint; dust
#   hit         it leans back, the cap is slammed down, a big burst: the cloud swells and boils over in mist, the can
#               recoils from the thrust, paint droplets fly, sparkles
#   multi       it is shaken (the ball rattles), the cloud swells with each shake in three pulses, glowing; then the
#               cap is slammed and the cloud blows out in a ring of mist, rings of light
# Runs INSIDE Blender, after build_symbol_scene.py (tools/blender/run.py runs both in a background Blender).
import bpy, importlib, math, os, random, sys
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
import fxkit
importlib.reload(fxkit)
from fxkit import key, rest, px, vec, smooth, gp_object, gp_mat, gp_layer, stroke, ring, puff, Board, WHITE, GOLD

SID = "L1"
sc, arm, spec = fxkit.setup(SID)
FPS = sc.render.fps
GREEN = (0.08, 0.86, 0.10, 1)               # the paint (the art's spray green)
PAINT_INK = (0.01, 0.16, 0.03, 1)           # its cartoon outline
LIGHT = (0.72, 1.0, 0.55, 1)                # wet highlights, the glow
NOZZLE = (652, 159)                          # where the jet leaves the cap
FAR = (470, 189)                             # the jet's far end, in the cloud: it turns about this
FEED = (472, 285)                            # between where the jet feeds the cloud and where it meets the can: it swells and sways about this
BASE = (468, 962)                            # the can's base, where it stands
CLOUD_C = (300, 230)                         # the cloud's middle
AXIS = Vector((0.43, 0.0, 0.90)).normalized()     # along the can, base -> top (world, z up)

# ------------------------------------------------------------------ the rig: new pivots for the jet, the cloud, the can
keep = {o.name: o.matrix_world.copy() for o in sc.objects if o.parent_type == "BONE"}
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
for name, at, parent in (("can", BASE, None), ("jet", FAR, "can"), ("cloud", FEED, "can")):
    b = eb[name]
    b.head = vec(*at)
    b.tail = b.head + Vector((0, 0, .6))
    b.roll = 0
    b.parent = eb[parent] if parent else None
bpy.ops.object.mode_set(mode="OBJECT")
for pb in arm.pose.bones:
    pb.rotation_mode = "XYZ"
bpy.context.view_layer.update()
for name, mw in keep.items():                        # the parts stay exactly where they were cut
    bpy.data.objects[name].matrix_world = mw
bpy.context.view_layer.update()

ART, FXB, FX = fxkit.layers(sc, SID)
fxkit.glow_compositor(sc, SID, back=dict(strength=.9, size=.5, gain=1.5), front=dict(strength=.8, size=.4, gain=1.5))
if arm.animation_data:
    arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)

BONES = ["can", "cap", "jet", "cloud"]
CLOUD_SPRING = {"cloud": dict(chain=[FEED, (170, 235)], freq=[1.7], zeta=.35, gain=.5, limit=2.2)}
CLIPS = {"idle": (1, 80), "land": (101, 126), "hit": (201, 252), "multi": (301, 348)}
arm["clips"] = {k: list(v) for k, v in CLIPS.items()}


# ------------------------------------------------------------------ helpers
def mats(f, bones):
    sc.frame_set(f)
    out = {}
    for b in bones:
        pb = arm.pose.bones[b]
        out[b] = arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted()
    return out


def jet_follow(f0, f1):
    """Key the jet so its tip stays in the nozzle: each frame, where the cap has taken the nozzle (in the can's own
    frame) sets the jet's turn about its far end and its length."""
    F, N0 = vec(*FAR), vec(*NOZZLE)
    a0 = math.atan2((N0 - F).z, (N0 - F).x)
    L0 = (N0 - F).length
    rs, ss = [], []
    for f in range(f0, f1 + 1):
        M = mats(f, ("can", "cap"))
        q = M["can"].inverted() @ (M["cap"] @ N0)
        d = q - F
        rs.append(math.degrees(math.atan2(d.z, d.x) - a0))
        ss.append(d.length / L0)
    for i in sorted(set(fxkit.sparse(rs, .03)) | set(fxkit.sparse(ss, .0015))):
        key(arm, "jet", f0 + i, r=rs[i], sx=ss[i])


def cloud_follow(f0, f1, gain=1.0):
    """The cloud's soft follow-through: a spring on how the keys move the can, keyed onto its turn."""
    res = fxkit.secondary(sc, arm, "can", f0, f1, CLOUD_SPRING, gain=gain)
    print(f"  {f0}-{f1}:", ", ".join(f"{b} {min(v):+.2f}..{max(v):+.2f}" for b, v in res.items()))
    fxkit.key_series(arm, "cloud", f0, res["cloud"], channel="r", tol=.1)


def press(rows):
    """The cap: (frame, squash) - sy down on its stem, sx out a little to keep its volume."""
    for f, sy in rows:
        key(arm, "cap", f, sx=1 + (1 - sy) * .45, sy=sy)


def billow(rows):
    for f, s in rows:
        key(arm, "cloud", f, s=s)


def can_keys(rows):
    """(frame, x, y, r, sx, sy) on the can's base."""
    for f, x, y, r, sx, sy in rows:
        key(arm, "can", f, x=x, y=y, r=r, sx=sx, sy=sy)


# ================================================================== idle: two gentle presses; the cloud breathes
f0, f1 = CLIPS["idle"]
act = fxkit.begin_action(arm, SID + "_idle")
rest(arm, BONES, f0)
PRESSES = (10, 50)
for p in PRESSES:
    press([(p - 1, 1), (p + 2, .94), (p + 7, .95), (p + 10, 1.01), (p + 13, 1)])
    billow([(p + 3, 1), (p + 10, 1.02), (p + 17, .997), (p + 24, 1)])
press([(f1 + 1, 1)]); billow([(f1 + 1, 1)])
can_keys([(21, 0, 0, .4, 1, 1), (41, 0, 0, 0, 1, 1), (61, 0, 0, -.4, 1, 1), (81, 0, 0, 0, 1, 1)])
jet_follow(f0, f1 + 1)
fxkit.make_cyclic(act)
fxkit.end_action(arm, act, f0)

# ================================================================== land: it thuds onto its base and rocks
f0, f1 = CLIPS["land"]
act = fxkit.begin_action(arm, SID + "_land")
rest(arm, BONES, f0)
can_keys([(103, 0, 0, 0, 1.08, .9), (106, 0, 0, 2.4, .97, 1.04), (110, 0, 0, -1.6, 1.01, .99), (114, 0, 0, .7, 1, 1),
          (119, 0, 0, -.2, 1, 1), (f1, 0, 0, 0, 1, 1)])
for i in (0, 1):
    fxkit.hard(act, "can", "scale", i, 103)
press([(103, 1), (105, .9), (109, 1.02), (113, 1), (f1, 1)])               # the jolt squirts it
billow([(105, 1), (110, 1.03), (116, .995), (121, 1), (f1, 1)])
cloud_follow(f0, f1, gain=.8)
jet_follow(f0, f1)
fxkit.end_action(arm, act, f0)

# ================================================================== hit: lean back, slam the cap, a big burst
f0, f1 = CLIPS["hit"]
act = fxkit.begin_action(arm, SID + "_hit")
rest(arm, BONES, f0)
SLAM = 208
can_keys([(204, -.04, 0, 3.0, .98, 1.02), (SLAM, 0, 0, 0, 1.05, .94), (212, .14, 0, -2.6, 1, 1.01), (217, .1, 0, -1.8, 1, 1),
          (224, .03, 0, .9, 1, 1), (231, 0, 0, -.4, 1, 1), (238, 0, 0, .1, 1, 1), (f1, 0, 0, 0, 1, 1)])
press([(204, 1.05), (SLAM - 1, 1.04), (SLAM + 1, .84), (226, .86), (230, 1.04), (234, .98), (239, 1), (f1, 1)])
fxkit.hard(act, "cap", "scale", 1, SLAM + 1)
billow([(SLAM + 1, 1), (SLAM + 5, 1.06), (SLAM + 9, 1.045), (SLAM + 13, 1.065), (SLAM + 18, 1.045), (229, 1.05), (234, .985),
        (239, 1.01), (244, 1), (f1, 1)])
cloud_follow(f0, f1, gain=1.0)
jet_follow(f0, f1)
fxkit.end_action(arm, act, f0)

# ================================================================== multi: shaken (the ball rattles), three swells, let go
f0, f1 = CLIPS["multi"]
act = fxkit.begin_action(arm, SID + "_multi")
rest(arm, BONES, f0)
SHAKE, PULSES, LET_GO = (304, 322), (310, 316, 322), 326
rows, k, f = [], 0, SHAKE[0]
while f <= SHAKE[1]:
    e = (f - SHAKE[0]) / (SHAKE[1] - SHAKE[0])
    a = (.07 + .12 * e) * (1 if k % 2 == 0 else -1)            # up and down along the can, harder and harder
    v = AXIS * a
    rows.append((f, v.x, v.z, (1 + 1.5 * e) * (-1 if k % 2 else 1), 1, 1))
    f += 2; k += 1
can_keys(rows + [(LET_GO - 1, 0, 0, 1.5, 1, 1), (LET_GO + 1, .12, 0, -2.4, 1.04, .95), (LET_GO + 6, .05, 0, 1.4, 1, 1),
                 (LET_GO + 11, 0, 0, -.6, 1, 1), (LET_GO + 16, 0, 0, .2, 1, 1), (f1, 0, 0, 0, 1, 1)])
billow([(306, 1)] + [(p, s) for p, s in zip(PULSES, (1.03, 1.045, 1.06))] + [(p + 3, s - .015) for p, s in zip(PULSES, (1.03, 1.045, 1.06))]
       + [(LET_GO, 1.05), (LET_GO + 4, 1.08), (LET_GO + 9, 1.065), (LET_GO + 13, .98), (LET_GO + 17, 1.01), (LET_GO + 21, 1), (f1, 1)])
press([(LET_GO - 2, 1.04), (LET_GO, .84), (LET_GO + 9, .86), (LET_GO + 12, 1.04), (LET_GO + 16, .99), (LET_GO + 20, 1), (f1, 1)])
fxkit.hard(act, "cap", "scale", 1, LET_GO)
cloud_follow(f0, f1, gain=.8)
jet_follow(f0, f1)
fxkit.end_action(arm, act, f0)

# ================================================================== the spray and the effects
sc.frame_set(1)
fx = gp_object(FX, SID + "_fx", depth=-.8)                     # light: glints, streaks, rings in front (bloomed)
glow = gp_object(FXB, SID + "_fxb_glow", depth=.35)            # light behind the art (bloomed)
paint = gp_object(ART, SID + "_fx_paint", depth=-1.0)          # paint in the air: on the art, in front of every piece
m = dict(white=gp_mat(fx, "fx_white_line", WHITE), white_f=gp_mat(fx, "fx_white_fill", WHITE, fill=WHITE),
         light=gp_mat(fx, "fx_light_line", LIGHT), light_f=gp_mat(fx, "fx_light_fill", LIGHT, fill=LIGHT),
         gold_f=gp_mat(fx, "fx_gold_fill", GOLD, fill=GOLD))
mb = dict(light=gp_mat(glow, "glow_light", LIGHT), white=gp_mat(glow, "glow_white", WHITE), green=gp_mat(glow, "glow_green", GREEN))
mp = dict(puff=gp_mat(paint, "paint_puff", PAINT_INK, fill=GREEN), drop=gp_mat(paint, "paint_drop", PAINT_INK, fill=GREEN),
          speck=gp_mat(paint, "paint_speck", LIGHT, fill=LIGHT), dust=gp_mat(paint, "fx_dust", (.6, .58, .62, 1), fill=(.96, .95, .97, 1)))
world, behind, air = Board(), Board(), Board()
ALL = sorted({f for a, b in CLIPS.values() for f in range(a, b + 2)})
M = {f: mats(f, ("can", "jet", "cloud", "cap")) for f in ALL}
sc.frame_set(1)
IDLE_N = CLIPS["idle"][1] - CLIPS["idle"][0] + 1


def wrap(f):
    """Idle frames past the loop's end come round to its start (the loop plays seamlessly)."""
    a, b = CLIPS["idle"]
    return a + (f - a) % IDLE_N if a <= f <= b + 40 else f


def on(bone, f, p):
    """World (x, z) of an icon-px point riding a bone at frame f."""
    q = M[f][bone] @ vec(*p)
    return q.x, q.z


def dot(board, f, x, z, r, mat, idle=False):
    if r > .006:
        board.add(wrap(f) if idle else f, lambda dr, x=x, z=z, r=r: stroke(dr, ring(x, z, r, n=12), .004, mat=mat, cyclic=True,
                                                                         fill=True, line=False))


def stream(f0, f1, rate, seed, size=(.018, .034), idle=False, speed=5):
    """Paint droplets running down the jet, nozzle to cloud, riding it as it moves: `rate` new ones a frame."""
    rnd = random.Random(seed)
    acc = 0.0
    for fb in range(f0, f1 + 1):
        acc += rate
        while acc >= 1:
            acc -= 1
            side, r0, tone = rnd.uniform(-.75, .75), rnd.uniform(*size), rnd.random()
            for k in range(speed + 1):
                u = k / speed
                f = wrap(fb + k) if idle else fb + k
                if f not in M:
                    continue
                ax = (NOZZLE[0] + (FAR[0] - NOZZLE[0]) * u, NOZZLE[1] + (FAR[1] - NOZZLE[1]) * u)
                half = 44 * u                                   # the cone opens out toward the cloud
                p = (ax[0] + .16 * side * half, ax[1] + side * half * .97)
                x, z = on("jet", f, p)
                dot(world, f, x, z, r0 * (.6 + .6 * u), m["white_f"] if tone < .3 else m["light_f"])


def mist(f0, n, seed, spread=(100, 260), dist=(1.2, 2.4), size=(.35, .6), life=(12, 18), idle=False, around=None):
    """Mist boiling off the cloud: cartoon puffs of paint that billow out from its edge, swell and shrink away."""
    rnd = random.Random(seed)
    cx, cz = on("cloud", f0, CLOUD_C) if around is None else around
    for i in range(n):
        a = math.radians(rnd.uniform(*spread))
        d0 = rnd.uniform(1.0, 1.5)
        fb = f0 + rnd.randint(0, 6)
        lf = rnd.randint(*life)
        x, z = cx + math.cos(a) * d0, cz + math.sin(a) * d0 * .9
        dd = rnd.uniform(*dist)
        top = size[1] * 1.05 + .35                         # it may not drift out of the frame (6.5 units each way)
        for _ in range(40):
            ex, ez = x + math.cos(a) * dd, z + math.sin(a) * dd * .9 + .25
            if abs(ex) + top <= 6.2 and abs(ez) + top <= 6.2:
                break
            dd *= .92
        for k in range(lf):
            t = k / (lf - 1)
            size_t = math.sin(math.pi * min(1.0, t * 1.05)) ** .6
            rr = rnd.uniform(*size) if k == 0 else rr
            r = rr * (.3 + .75 * size_t) * size_t
            px_, pz_ = x + math.cos(a) * dd * (1 - (1 - t) ** 2), z + math.sin(a) * dd * .9 * (1 - (1 - t) ** 2) + .25 * t
            if r > .03:
                air.add(wrap(fb + k) if idle else fb + k, lambda dr, px_=px_, pz_=pz_, r=r, s=seed * 31 + i: stroke(
                    dr, puff(px_, pz_, r, lobes=6, seed=s, bump=.12), .009, mat=mp["puff"], cyclic=True, fill=True))


def fling(f0, n, seed, x, z, spread=(0, 360), speed=(3, 6), size=(.04, .09), life=12, grav=6.0, idle=False):
    """Paint droplets flung out: they fly, fall and shrink away."""
    rnd = random.Random(seed)
    for i in range(n):
        a = math.radians(rnd.uniform(*spread)); sp = rnd.uniform(*speed); r0 = rnd.uniform(*size)
        for k in range(life):
            t = k / FPS; u = k / (life - 1)
            r = r0 * (1 - u ** 1.6)
            dot(air, f0 + k, x + math.cos(a) * sp * t, z + math.sin(a) * sp * t - grav * t * t, r,
                mp["drop"] if i % 3 else mp["speck"], idle=idle)


def rings_out(board, f0, cx, cz, r0, r1, mats_, life=11, lag=3, width=.12):
    """Rings rolling outward at full strength, thinning to nothing (never fading to a dim, dirty line)."""
    for j, mat in enumerate(mats_):
        for k in range(life):
            t = k / (life - 1)
            r = r0 + (r1 - r0) * (1 - (1 - t) ** 1.6)
            w = width * (1 - t) ** 1.3
            if w > .004:
                board.add(f0 + lag * j + k, lambda dr, r=r, w=w, mat=mat, f=f0 + k: stroke(
                    dr, ring(cx, cz, r, n=96, wobble=.02, seed=f), w, mat=mat, cyclic=True))


def ticks(board, f0, x, z, mats_, a0=20, a1=160, n=5, r0=.25, r1=.85, life=6, w=.035, seed=0):
    rnd = random.Random(seed)
    angs = [math.radians(a0 + (a1 - a0) * (i + .5) / n + rnd.uniform(-7, 7)) for i in range(n)]
    for k in range(life):
        t = k / max(1, life - 1)
        for i, a in enumerate(angs):
            ra = r0 + (r1 - r0) * t ** .7
            rb = ra + .3 * (1 - t) + .04
            board.add(f0 + k, lambda dr, a=a, ra=ra, rb=rb, t=t, i=i: stroke(
                dr, [(x + math.cos(a) * ra, z + math.sin(a) * ra), (x + math.cos(a) * rb, z + math.sin(a) * rb)],
                w * (1 - t) ** .8 + .006, mat=mats_[i % len(mats_)]))


# ---- idle: a trickle down the jet all the time, a pulse with each press, mist breathing off the cloud
stream(1, 80, .34, seed=1, idle=True)
for p in PRESSES:
    stream(p + 1, p + 7, 1.3, seed=p, idle=True, size=(.022, .04))
    mist(p + 5, 3, seed=p, spread=(110, 230), dist=(.6, 1.1), size=(.3, .45), life=(14, 18), idle=True)
    fling(p + 6, 4, seed=p + 3, x=on("cloud", p + 6, (180, 200))[0], z=on("cloud", p + 6, (180, 200))[1],
          spread=(120, 220), speed=(1.4, 2.4), size=(.03, .05), life=12, grav=3, idle=True)
fxkit.sparkle(world, 30, 9, *px(705, 105), .28, m["white_f"], rot0=.3)          # the cap's rim catches the light
fxkit.sparkle(world, 68, 9, *px(250, 120), .24, m["white_f"], rot0=1.0)         # a wet glint on the cloud

# ---- land: dust from the base, a squirt of paint, the cloud puffs
bx, bz = px(*BASE)
ticks(world, 103, bx, bz - .1, (m["white"], m["light"], m["white"]), seed=3)
for side, sd in ((-1, 3), (1, 7)):
    fxkit.dust(air, 103, 11, bx + side * .9, bz - .1, .45, mp["dust"], drift=(side * 1.1, .25), seed=sd)
stream(104, 110, 1.6, seed=104, size=(.022, .04))
mist(109, 4, seed=109, dist=(.7, 1.3), size=(.3, .45), life=(12, 15))

# ---- hit: the burst - a gush down the jet, the cloud boils over, droplets fly, the can recoils; sparkles
stream(201, 212, .5, seed=201)
stream(SLAM, 228, 2.2, seed=SLAM, size=(.026, .05), speed=4)
mist(SLAM + 3, 12, seed=SLAM, spread=(70, 290), dist=(1.4, 2.6), size=(.42, .72), life=(14, 20))
cx, cz = on("cloud", SLAM + 6, CLOUD_C)
fling(SLAM + 4, 20, seed=5, x=cx, z=cz, spread=(60, 300), speed=(4.5, 8), size=(.05, .1), life=14, grav=7)
rings_out(behind, SLAM + 2, cx, cz, 1.4, 3.4, (mb["light"], mb["white"]), life=10, lag=3, width=.1)    # inside the frame
for k, f in enumerate(range(SLAM + 1, SLAM + 6)):                       # thrust lines off the can's back
    t = k / 4
    for j in range(3):
        x0, z0 = on("can", f, (760 + 18 * j, 470 + 80 * j))
        world.add(f, lambda dr, x0=x0, z0=z0, t=t: stroke(dr, [(x0 + .2 + .5 * t, z0), (x0 + .9 + .9 * t, z0 - .1)],
                                                         .03 * (1 - t) + .006, mat=m["white"]))
rnd = random.Random(8)
for i in range(8):
    fxkit.sparkle(world, 222 + rnd.randint(0, 16), rnd.randint(7, 10), rnd.uniform(-4.6, 4.6), rnd.uniform(-4.2, 4.8),
                  rnd.uniform(.22, .4), m["white_f"] if i % 3 else m["gold_f"], rot0=rnd.uniform(0, 1))

# ---- multi: rattle marks as it is shaken, the cloud glows with each swell, then it blows out in a ring of mist
for k, f in enumerate(range(SHAKE[0] + 2, SHAKE[1] + 1, 2)):
    side = 1 if k % 2 else -1
    cx_, cz_ = on("can", f, (560, 620))
    for j in range(3):
        ox = (-AXIS.z * side) * (2.4 + .2 * j) * (1 if side > 0 else .9)
        oz = (AXIS.x * side) * (2.4 + .2 * j)
        pts = [(cx_ + ox + AXIS.x * s * .32, cz_ + oz + AXIS.z * s * .32) for s in (-1, 0, 1)]
        pts[1] = (pts[1][0] - AXIS.z * side * .08, pts[1][1] + AXIS.x * side * .08)
        world.add(f, lambda dr, pts=pts: stroke(dr, pts, .024, mat=m["white"]), hold=2)
for p in PULSES:
    for k in range(7):                                                   # the cloud glows with each swell
        t = k / 6
        f = p - 1 + k
        cx_, cz_ = on("cloud", f, CLOUD_C)
        s = M[f]["cloud"].to_scale().x
        w = .1 * (1 - t) ** 1.2 + .004
        loop_pts = [(cx_ + math.cos(a) * 2.25 * s, cz_ + math.sin(a) * 2.15 * s) for a in (2 * math.pi * i / 64 for i in range(64))]
        behind.add(f, lambda dr, w=w, pts=loop_pts: stroke(dr, pts, w, mat=mb["green"], cyclic=True))
        behind.add(f, lambda dr, w=w, pts=loop_pts: stroke(dr, pts, w * .45, mat=mb["light"], cyclic=True))
    stream(p - 2, p + 3, 1.0, seed=p)
stream(LET_GO, LET_GO + 12, 2.4, seed=LET_GO, size=(.026, .05), speed=4)
cx, cz = on("cloud", LET_GO + 4, CLOUD_C)
mist(LET_GO + 2, 16, seed=LET_GO, spread=(0, 360), dist=(1.4, 2.3), size=(.4, .66), life=(9, 12), around=(cx, cz))   # gone before the clip ends
fling(LET_GO + 3, 22, seed=11, x=cx, z=cz, spread=(0, 360), speed=(5, 8.5), size=(.05, .1), life=13, grav=5)
rings_out(behind, LET_GO + 1, 0, .3, 2.2, 5.6, (mb["green"], mb["white"], mb["light"]), life=11, lag=3, width=.13)   # round the whole can
fxkit.streaks(world, LET_GO + 1, 8, cx, cz, 2.6, 5.6, (m["white"], m["light"]), n=14, rot=.2)
rnd = random.Random(31)
for i in range(6):
    fxkit.sparkle(world, LET_GO + 5 + rnd.randint(0, 8), rnd.randint(7, 8), rnd.uniform(-4.6, 4.6), rnd.uniform(-4.2, 4.8),
                  rnd.uniform(.2, .36), m["white_f"] if i % 2 else m["gold_f"], rot0=rnd.uniform(0, 1))

world.draw(gp_layer(fx, "fx"))
behind.draw(gp_layer(glow, "burst"))
air.draw(gp_layer(paint, "paint"))

sc.frame_start, sc.frame_end = 1, max(b for a, b in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], "| saved", fxkit.save(SID))
