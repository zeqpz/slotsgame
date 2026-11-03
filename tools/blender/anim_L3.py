# L3 - the grey beanie - animated in Blender: four Actions on its rig (idle, land, hit, multi) laid one after
# another on the rig's NLA track, and its effects drawn frame by frame in Grease Pencil on the same timeline.
#   the hat     keyed by hand on the cuff (the hat's root, squashing on its brim): it breathes (idle), lands soft and
#               squashes flat (land), crouches, hops and lands with a squish (hit), swells with static in three pulses
#               and slumps when it lets go (multi)
#   the crown   soft knit held by the cuff at its seam (tools/blender/cuts/L3.py): it flops over, worked out in Blender
#               from how the keys move the cuff - a slow, heavy, well damped spring that stretches - and keyed onto its
#               bone sparsely; a breeze stirs it in the idle, static lifts it in the multi
#   the logo    the SMK tag pops off the cuff and wobbles (the cuff under it is plain knit from the clean plate)
#   effects     wool fluff puffs and stray fibres where the brim lands, speed lines, a spray-paint burst and glints off
#               the tag, static: fuzz standing up all round the knit, sparks crackling along it, a discharge
# Runs INSIDE Blender, after build_symbol_scene.py (tools/blender/run.py runs both in a background Blender).
import bpy, importlib, json, math, os, random, sys
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
import fxkit
importlib.reload(fxkit)
from fxkit import key, rest, px, vec, smooth, gp_object, gp_mat, gp_layer, ride, stroke, star, ring, Board, WHITE, GOLD

SID = "L3"
sc, arm, spec = fxkit.setup(SID)
FPS = sc.render.fps
SPARK = (0.62, 0.9, 1.0, 1)                 # static: a cold blue-white
CROWN_ROOT = (510, 330)                     # the crown bends from the middle of its seam

# ------------------------------------------------------------------ the rig: the crown pivots at its seam
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
b = arm.data.edit_bones["crown"]
b.head = vec(*CROWN_ROOT)
b.tail = b.head + Vector((0, 0, .6))
b.roll = 0
bpy.ops.object.mode_set(mode="OBJECT")
for pb in arm.pose.bones:
    pb.rotation_mode = "XYZ"

ART, FXB, FX = fxkit.layers(sc, SID)
fxkit.glow_compositor(sc, SID, back=dict(strength=.9, size=.5, gain=1.5), front=dict(strength=.8, size=.4, gain=1.5))
if arm.animation_data:
    arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)

BONES = ["cuff", "crown", "logo"]
HANGING = {"crown": dict(chain=[CROWN_ROOT, (510, 95)], freq=[1.6], zeta=.26, stretch=True, gain=1.0, limit=14, stretch_limit=.14)}
CLIPS = {"idle": (1, 80), "land": (101, 126), "hit": (201, 250), "multi": (301, 346)}
arm["clips"] = {k: list(v) for k, v in CLIPS.items()}


def follow(f0, f1, loop=False, forces=None, gain=1.0):
    """The crown, worked out from how this clip moves the cuff, keyed onto its bone."""
    res = fxkit.secondary(sc, arm, "cuff", f0, f1, HANGING, loop=loop, forces=forces, gain=gain)
    print(f"  {f0}-{f1}:", ", ".join(f"{b} {min(v):+.2f}..{max(v):+.2f}" for b, v in res.items()))
    for bone, vals in res.items():
        if bone.endswith(":sy"):
            bn = bone[:-3]                          # its stretch: sy along, sx keeping its volume, keyed together
            series = list(vals) + ([vals[0]] if loop else [])
            ks = sorted(set(fxkit.sparse(series, .004)))
            for i in ks:
                key(arm, bn, f0 + i, sx=1 / math.sqrt(max(.5, series[i])), sy=series[i])
        else:
            fxkit.key_series(arm, bone, f0, vals, channel="r", tol=.2, loop=loop)


def squash(bone, rows, hard_at=()):
    for row in rows:
        f, sx, sy = row[:3]
        key(arm, bone, f, sx=sx, sy=sy)
    for f in hard_at:
        for i in (0, 1):
            fxkit.hard(arm.animation_data.action, bone, "scale", i, f)


# ================================================================== idle: it breathes; the crown sways
f0, f1 = CLIPS["idle"]
act = fxkit.begin_action(arm, SID + "_idle")
rest(arm, BONES, f0)
squash("cuff", [(21, 1.015, .978), (41, .996, 1.012), (61, 1.004, .996), (81, 1, 1)])
for f, s in ((46, 1), (52, 1.045), (58, .99), (64, 1.01), (70, 1), (81, 1)):
    key(arm, "logo", f, s=s)
for f, r in ((46, 0), (51, -2), (56, 1.6), (61, -.7), (66, 0), (81, 0)):
    key(arm, "logo", f, r=r)


def breeze(name, i, t):
    T = 80 / FPS
    return Vector((15 * math.sin(2 * math.pi * t / T + .6) + 5 * math.sin(4 * math.pi * t / T), 0, 0))


follow(f0, f1, loop=True, forces=breeze)
fxkit.make_cyclic(act)
fxkit.end_action(arm, act, f0)

# ================================================================== land: a soft plop, squashed flat on its brim
f0, f1 = CLIPS["land"]
act = fxkit.begin_action(arm, SID + "_land")
rest(arm, BONES, f0)
squash("cuff", [(103, 1.13, .84), (106, .95, 1.07), (110, 1.025, .985), (114, .995, 1.005), (119, 1, 1), (f1, 1, 1)], hard_at=(103,))
for f, r in ((103, 0), (106, -2.6), (110, 1.6), (114, -.7), (119, .2), (f1, 0)):     # it lands a little askew and rocks
    key(arm, "cuff", f, r=r)
for f, s in ((104, .96), (108, 1.05), (113, .99), (118, 1), (f1, 1)):
    key(arm, "logo", f, s=s)
follow(f0, f1, gain=.9)
fxkit.end_action(arm, act, f0)

# ================================================================== hit: crouch, hop, the tag pops, a squishy landing
f0, f1 = CLIPS["hit"]
act = fxkit.begin_action(arm, SID + "_hit")
rest(arm, BONES, f0)
for f, sx, sy, y, r in ((205, 1.1, .86, 0, 0), (208, .9, 1.13, .25, -3), (213, .97, 1.05, .85, 2), (217, 1, 1, .98, 3.5),
                        (221, .97, 1.04, .7, -1.5), (224, 1.0, 1.0, 0, 0), (225, 1.15, .82, 0, 0), (229, .95, 1.06, 0, 1),
                        (233, 1.02, .99, 0, 0), (238, 1, 1, 0, 0), (f1, 1, 1, 0, 0)):
    key(arm, "cuff", f, sx=sx, sy=sy, y=y, r=r)
fxkit.hard(act, "cuff", "location", 1, 224)
for i in (0, 1):
    fxkit.hard(act, "cuff", "scale", i, 225)
for f, s in ((210, 1), (214, 1.3), (218, 1.17), (222, 1.22), (225, .95), (230, 1.06), (236, .99), (242, 1), (f1, 1)):
    key(arm, "logo", f, s=s)
for f, r in ((212, 0), (215, -7), (219, 6), (223, -3), (228, 1.5), (234, -.5), (240, 0), (f1, 0)):
    key(arm, "logo", f, r=r)
follow(f0, f1, gain=.8)
fxkit.end_action(arm, act, f0)

# ================================================================== multi: it swells with static, three pulses, then lets go
f0, f1 = CLIPS["multi"]
act = fxkit.begin_action(arm, SID + "_multi")
rest(arm, BONES, f0)
PULSES, LET_GO = (308, 315, 322), 327
for f, s in ((305, 1.04), (308, 1.06), (311, 1.03), (315, 1.09), (318, 1.05), (322, 1.12), (325, 1.11)):
    key(arm, "cuff", f, sx=s, sy=s)
squash("cuff", [(LET_GO, 1.06, 1.06), (LET_GO + 1, 1.16, .82), (LET_GO + 5, .94, 1.08), (LET_GO + 9, 1.03, .98),
                (LET_GO + 13, 1, 1), (f1, 1, 1)], hard_at=(LET_GO + 1,))
for i, f in enumerate(range(311, 326, 2)):           # the charge makes it tremble
    key(arm, "cuff", f, x=.022 if i % 2 else -.022, r=.7 if i % 2 else -.7)
key(arm, "cuff", LET_GO, x=0, r=0); key(arm, "cuff", f1, x=0, r=0)
for f, s in ((308, 1.03), (315, 1.05), (322, 1.08), (LET_GO, 1.08), (LET_GO + 2, .93), (LET_GO + 6, 1.04), (LET_GO + 11, 1), (f1, 1)):
    key(arm, "logo", f, s=s)


def static(name, i, t):
    f = f0 + t * FPS
    env = smooth(304, 312, f) * (1 - smooth(LET_GO - 1, LET_GO + 2, f))
    if env <= 0:
        return Vector((0, 0, 0))
    rnd = random.Random(int(f) * 17)
    return Vector(((rnd.random() - .5) * 50 * env, 0, 46 * env))           # lifted, crackling


follow(f0, f1, forces=static, gain=.8)
fxkit.end_action(arm, act, f0)


# ================================================================== effects
def track(bone, pts, f):
    pb = arm.pose.bones[bone]
    sc.frame_set(f)
    M = arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted()
    out = [((M @ vec(*p)).x, (M @ vec(*p)).z) for p in pts]
    sc.frame_set(1)
    return out


sc.frame_set(1)
fx = gp_object(FX, SID + "_fx", depth=-.8)
on_hat = gp_object(FX, SID + "_fx_hat", depth=-.8)
on_tag = gp_object(FX, SID + "_fx_tag", depth=-.8)
ride(on_hat, arm, "cuff")
ride(on_tag, arm, "logo")
back = gp_object(FXB, SID + "_fxb_glow", depth=.35)       # (never a part's name: gp_object replaces that object)
art_fx = gp_object(ART, SID + "_fx_dust", depth=-1.0)            # on the art, in front of every piece
m = dict(white=gp_mat(fx, "fx_white_line", WHITE), white_f=gp_mat(fx, "fx_white_fill", WHITE, fill=WHITE),
         spark=gp_mat(fx, "fx_spark_line", SPARK), spark_f=gp_mat(fx, "fx_spark_fill", SPARK, fill=SPARK),
         gold_f=gp_mat(fx, "fx_gold_fill", GOLD, fill=GOLD))
mh = dict(spark=gp_mat(on_hat, "fx_spark_line", SPARK), white=gp_mat(on_hat, "fx_white_line", WHITE))
mt = dict(white_f=gp_mat(on_tag, "fx_white_fill", WHITE, fill=WHITE), gold_f=gp_mat(on_tag, "fx_gold_fill", GOLD, fill=GOLD))
mb = dict(spark=gp_mat(back, "glow_spark", SPARK), white=gp_mat(back, "glow_white", WHITE))
m_fluff = gp_mat(art_fx, "fx_fluff", (.55, .55, .58, 1), fill=(.9, .9, .91, 1))
m_fibre = gp_mat(art_fx, "fx_fibre", (.42, .42, .45, 1))
world, behind, hat, tag, dust = Board(), Board(), Board(), Board(), Board()

FEET = (px(141, 856), px(848, 937))                            # the brim's corners it stands on
outline = json.load(open(os.path.join(fxkit.ROOT, "art", "blender", "parts", SID, "outline.json")))["points"]
EDGE = fxkit.offset(fxkit.resample([px(x, y) for x, y in outline], 150), -.2)     # the knit's edge, inside the border


def normal(i, pts):
    (ax, az), (bx, bz) = pts[i - 1], pts[(i + 1) % len(pts)]
    tx, tz = bx - ax, bz - az
    L = math.hypot(tx, tz) or 1
    area = sum(pts[k][0] * pts[(k + 1) % len(pts)][1] - pts[(k + 1) % len(pts)][0] * pts[k][1] for k in range(len(pts)))
    s = 1 if area > 0 else -1
    return s * tz / L, -s * tx / L


NORMALS = [normal(i, EDGE) for i in range(len(EDGE))]


def puffs(f0, x, z, scale=.5, life=11, seed=1, out=1.0):
    for side, sd in ((-1, seed), (1, seed + 4)):
        fxkit.dust(dust, f0, life, x + side * .3, z + .05, scale * (1 if side * out > 0 else .7), m_fluff,
                   drift=(side * 1.1, .3), seed=sd)


def fibres(f0, x, z, n=4, spread=(40, 140), speed=(2.5, 4.0), life=12, seed=0):
    """Stray wool fibres flung off: little curls that fly, tumble and shrink away."""
    rnd = random.Random(seed)
    for i in range(n):
        a = math.radians(rnd.uniform(*spread))
        sp = rnd.uniform(*speed)
        spin = rnd.uniform(-9, 9)
        L = rnd.uniform(.22, .36)
        for k in range(life):
            t = k / FPS
            u = k / (life - 1)
            cx, cz = x + math.cos(a) * sp * t, z + math.sin(a) * sp * t - 9 * t * t
            ang = spin * t + a
            s = L * (1 - u * u)
            if s < .03:
                continue
            pts = [(cx + math.cos(ang) * s * (j / 3 - .5) - math.sin(ang) * .05 * math.sin(j * 2.1) * s / L,
                    cz + math.sin(ang) * s * (j / 3 - .5) + math.cos(ang) * .05 * math.sin(j * 2.1) * s / L) for j in range(4)]
            dust.add(f0 + k, lambda dr, pts=pts: stroke(dr, pts, .012, mat=m_fibre))


def zap(x0, z0, x1, z1, seed, n=6, amp=.18):
    return fxkit.zigzag(x0, z0, x1, z1, n=n, amp=amp, seed=seed)


def rings_out(board, f0, cx, cz, r0, r1, mats, life=11, lag=3, width=.12):
    """Rings rolling outward at full strength, thinning to nothing (never fading to a dim, dirty line)."""
    for j, mat in enumerate(mats):
        for k in range(life):
            t = k / (life - 1)
            r = r0 + (r1 - r0) * (1 - (1 - t) ** 1.6)
            w = width * (1 - t) ** 1.3
            if w > .004:
                board.add(f0 + lag * j + k, lambda dr, r=r, w=w, mat=mat, f=f0 + k: stroke(
                    dr, ring(cx, cz, r, n=96, wobble=.02, seed=f), w, mat=mat, cyclic=True))


# ---- idle: the tag catches the light
fxkit.sparkle(tag, 28, 10, *px(355, 395), .3, mt["white_f"], rot0=.4)
fxkit.sparkle(tag, 60, 9, *px(690, 455), .24, mt["white_f"], rot0=1.1)

# ---- land: fluff puffs out from under the brim, a few fibres fly
for (x, z), sd in zip(FEET, (3, 7)):
    puffs(102, x, z, scale=.48, life=12, seed=sd)
    fibres(103, x, z + .2, n=3, seed=sd, spread=(60, 120) if x < 0 else (60, 120))

# ---- hit: speed lines under the hop, the tag bursts out in a spray of paint flecks and glints, a squishy landing
for k, f in enumerate(range(209, 215)):
    for j, x in enumerate((-2.6, -1.2, .4, 2.0)):
        world.add(f, lambda dr, x=x, k=k, j=j: stroke(dr, [(x + .07 * j, -4.6 + .45 * k), (x + .07 * j, -5.6 + .45 * k)],
                                                     .026 * (1 - k / 6) + .006, mat=m["white"]))
c = track("logo", [(515, 505)], 214)[0]
rnd = random.Random(5)
for i in range(44):                                            # paint flecks off the tag
    a = rnd.uniform(0, 2 * math.pi)
    sp = rnd.uniform(2.2, 4.6)
    r0 = rnd.uniform(.05, .12)
    for k in range(11):
        t = k / 10
        d = sp * (1 - (1 - t) ** 2.2)
        x, z = c[0] + math.cos(a) * d * 1.15, c[1] + math.sin(a) * d * .9 - .6 * t * t
        r = r0 * (1 - t ** 1.5) + .006
        world.add(213 + k, lambda dr, x=x, z=z, r=r, i=i: stroke(dr, ring(x, z, r, n=10), .004,
                                                               mat=m["white_f"] if i % 5 else m["spark_f"], cyclic=True,
                                                               fill=True, line=False))
for k, f in enumerate(range(213, 219)):                        # streaks of spray behind it
    t = k / 5
    for j in range(10):
        a = 2 * math.pi * j / 10 + .2
        ra, rb = 1.8 + 2.4 * t, 1.8 + 2.4 * t + .9 * (1 - t)
        behind.add(f, lambda dr, a=a, ra=ra, rb=rb, t=t: stroke(
            dr, [(c[0] + math.cos(a) * ra * 1.2, c[1] + math.sin(a) * ra * .85), (c[0] + math.cos(a) * rb * 1.2, c[1] + math.sin(a) * rb * .85)],
            .05 * (1 - t) + .006, mat=mb["white"]))
for i, (lx, ly) in enumerate(((330, 405), (520, 380), (690, 440), (445, 600), (735, 560))):
    fxkit.sparkle(tag, 215 + 4 * i, 9, *px(lx, ly), .32 - .03 * (i % 2), mt["white_f"] if i % 2 else mt["gold_f"], rot0=i * .7)
for (x, z), sd in zip(FEET, (11, 13)):
    puffs(225, x, z, scale=.58, life=13, seed=sd)
    fibres(226, x, z + .25, n=4, seed=sd + 2)

# ---- multi: static - fuzz stands up all round the knit, sparks crackle along its edge, the edge glows with each
#      pulse; then it lets go in a discharge. All of it is drawn on the hat's real edge, frame by frame: the outline
#      moved the way the pieces move it - the cuff's bone below the seam, blended into the crown's bone above it
#      the same way the crown's mesh is weighted (tools/blender/cuts/L3.py ANCHOR) - so it follows the swell, the
#      tremble and the crown's flop exactly.
AN_Y0, AN_Y1 = 330, 150
BASE = fxkit.resample([px(x, y) for x, y in outline], 150)      # 2 px outside the sticker's edge


def edge_at(f, pts):
    """World (x, z) of outline points (rest positions) on the hat as it is at frame f."""
    sc.frame_set(f)
    out = []
    mats = {}
    for b in ("cuff", "crown"):
        pb = arm.pose.bones[b]
        mats[b] = arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted()
    for x, z in pts:
        y_icon = 500 - z * 100
        t = max(0.0, min(1.0, (AN_Y0 - y_icon) / (AN_Y0 - AN_Y1)))
        t = t * t * (3 - 2 * t)
        v = Vector((x, 0, z))
        q = mats["cuff"] @ v * (1 - t) + mats["crown"] @ v * t
        out.append((q.x, q.z))
    return out


DEF = {f: edge_at(f, BASE) for f in range(303, LET_GO + 2)}
sc.frame_set(1)
for f in range(304, LET_GO + 1):
    e = smooth(304, 322, f)
    pulse = sum(math.exp(-((f - p) / 2.0) ** 2) for p in PULSES)
    L = (.12 + .3 * e) * (1 + .4 * pulse)
    rr = random.Random(f * 3)
    knit = fxkit.offset(DEF[f], -.2)                               # the knit's edge, inside the border
    for i in range(len(knit)):
        (x, z), (nx, nz) = knit[i], normal(i, knit)
        ln = L * rr.uniform(.6, 1.2)
        tw = rr.uniform(-.35, .35)
        world.add(f, lambda dr, x=x, z=z, nx=nx, nz=nz, ln=ln, tw=tw: stroke(
            dr, [(x, z), (x + (nx + tw * nz) * ln, z + (nz - tw * nx) * ln)], .013, mat=m["white"]))
for f in range(308, LET_GO, 2):                                # sparks crackle along the edge, just outside it
    rr = random.Random(f * 7 + 1)
    for j in range(3 + (f > 314) + (f > 320)):
        n_pts = rr.randint(5, 10)
        i0 = rr.randrange(len(BASE))
        lift = rr.uniform(.06, .16)
        for hold_f in (f, f + 1):                              # on twos, each frame on the hat as it is then
            ring_ = DEF[hold_f]
            pts = []
            for q in range(n_pts + 1):
                i = (i0 + q) % len(ring_)
                (x, z), (nx, nz) = ring_[i], normal(i, ring_)
                hump = math.sin(math.pi * q / n_pts)
                kink = (.07 if q % 2 else -.05) * hump + random.Random(f * 31 + j * 7 + q).uniform(-.03, .03)
                d = .05 + lift * hump + kink
                pts.append((x + nx * d, z + nz * d))
            world.add(hold_f, lambda dr, pts=pts: stroke(dr, pts, .036, mat=m["spark"]))
            world.add(hold_f, lambda dr, pts=pts: stroke(dr, pts, .013, mat=m["white"]))
for p in PULSES:                                           # each pulse of static lights the hat's edge from behind
    for k in range(7):
        t = k / 6
        w = .085 * (1 - t) ** 1.2 + .004
        glow_line = fxkit.offset(DEF[p - 1 + k], .2)
        behind.add(p - 1 + k, lambda dr, w=w, g=glow_line: stroke(dr, g, w, mat=mb["spark"], cyclic=True))
        behind.add(p - 1 + k, lambda dr, w=w, g=glow_line: stroke(dr, g, w * .4, mat=mb["white"], cyclic=True))
cx, cz = px(515, 520)
rnd = random.Random(9)
for j in range(10):                                            # the discharge: bolts thrown out all round
    a = 2 * math.pi * j / 10 + rnd.uniform(-.2, .2)
    for k in range(5):
        t = k / 4
        r0, r1 = 3.4 + 1.2 * t, 4.6 + 1.3 * t
        pts = zap(cx + math.cos(a) * r0, cz + math.sin(a) * r0 * .95, cx + math.cos(a) * r1, cz + math.sin(a) * r1 * .95,
                  seed=j * 13 + k, n=5, amp=.22)
        world.add(LET_GO + k, lambda dr, pts=pts, t=t: stroke(dr, pts, .04 * (1 - t) + .008, mat=m["spark"]))
        world.add(LET_GO + k, lambda dr, pts=pts, t=t: stroke(dr, pts, .015 * (1 - t) + .004, mat=m["white"]))
rings_out(behind, LET_GO, cx, cz, 2.0, 6.0, (mb["spark"], mb["white"]), life=11, lag=3, width=.12)
for (x, z), sd in zip(FEET, (17, 19)):
    puffs(LET_GO + 1, x, z, scale=.5, life=12, seed=sd)
    fibres(LET_GO + 1, x, z + .25, n=3, seed=sd + 1)
for i in range(6):
    fxkit.sparkle(world, LET_GO + 3 + rnd.randint(0, 10), rnd.randint(7, 9), rnd.uniform(-4.6, 4.6), rnd.uniform(-4, 5),
                  rnd.uniform(.2, .34), m["white_f"] if i % 2 else m["spark_f"], rot0=rnd.uniform(0, 1))

world.draw(gp_layer(fx, "fx"))
hat.draw(gp_layer(on_hat, "fx"))
tag.draw(gp_layer(on_tag, "fx"))
behind.draw(gp_layer(back, "burst"))
dust.draw(gp_layer(art_fx, "dust"))

sc.frame_start, sc.frame_end = 1, max(b for a, b in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], "| saved", fxkit.save(SID))
