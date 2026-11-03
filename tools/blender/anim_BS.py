# BS - the bonus scatter ("FS" in green dripping graffiti, still wet) - animated in Blender: four Actions on its rig
# (idle, land, hit, multi) laid one after another on the rig's NLA track, and its effects drawn frame by frame in
# Grease Pencil on the same timeline. No tier glow: the scatter glows in its own green, and the rest is wet paint.
#   the letters  F and S are glued at the top by the goo, so the big squash, stretch and slam is the word's (a root
#                bone "word", added here under both); each letter adds a smaller hop and squash of its own, a beat
#                apart. The goo between them (the "weld": the Y of slime, the black and white round it - the whole
#                join) is weighted F-to-S by a smooth field (cuts/BS.py), so as the letters move in turn it bends
#                like wet paint and never tears
#   the drips    nine drips, each its own chain of bones and its own spring (fxkit.secondary): stiff at the root,
#                soft at the tip, free to stretch - they lag, whip and ooze with how their letter really moves,
#                each at its own pace, so they never move as one
#   idle         wet paint at rest: each drip in turn oozes longer and snaps back up, they sway a little apart; F
#                gives a small bounce, then S; a glint runs over the gloss; the green glow breathes
#   land         the word squashes as it hits, F's paint a beat before S's; the drips are flung down long and spring
#                back, paint spatters out from under it, the glow flares
#   hit          the word crouches, F leaps and S follows a beat behind (the goo between them bending), F slams down
#                and then S, each flinging its drips and spattering paint; the word squashes and rebounds; glints,
#                glow, speed lines
#   multi        the charge: the letters quiver and swell, the drips are drawn up short, the paint bubbles and green
#                arcs crackle off it, the glow wells up - then it lets go: both letters pop, the drips fling down,
#                a ring of paint spatter bursts out, sparkles
# Runs INSIDE Blender, after build_symbol_scene.py (tools/blender/run.py runs both in a background Blender).
import bpy, importlib, json, math, os, random, sys
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
import fxkit
importlib.reload(fxkit)
from fxkit import (key, rest, px, smooth, gp_object, gp_mat, gp_layer, ride, stroke, star, ring, Board,
                   LIME, WHITE, GOLD)

SID = "BS"
sc, arm, spec = fxkit.setup(SID)
FPS = sc.render.fps
PARTS = os.path.join(fxkit.ROOT, "art", "blender", "parts", SID)
W, H = spec["size"]


def srgb(r, g, b, a=1.0):
    """A colour picked off the art (0-255, sRGB) as Blender's linear colour."""
    f = lambda c: (c / 255) / 12.92 if c / 255 <= .04045 else ((c / 255 + .055) / 1.055) ** 2.4
    return (f(r), f(g), f(b), a)


CH = {p["name"]: p["chain"] for p in spec["parts"] if p.get("chain")}
F_DRIPS = [n for n in CH if n.startswith("f_")]
S_DRIPS = [n for n in CH if n.startswith("s_")]
DRIP_BONES = [b.name for b in arm.data.bones if b.name.split(".")[0] in CH]

# ------------------------------------------------------------------ the rig, as the animation needs it
ROOT_AT = (512, 700)                          # under the middle of the word
if "word" not in arm.data.bones:
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    b = eb.new("word")
    b.head = fxkit.vec(*ROOT_AT)
    b.tail = b.head + Vector((0, 0, .6))
    b.roll = 0
    for n in ("letter_f", "letter_s"):
        eb[n].use_connect = False
        eb[n].parent = b
    bpy.ops.object.mode_set(mode="OBJECT")
arm.pose.bones["word"].rotation_mode = "XYZ"
for n in DRIP_BONES:                          # a drip keeps its own size when its letter squashes: it stretches
    arm.data.bones[n].inherit_scale = "NONE"  # and thins on its own spring, never twice over
# the weld: each point of its mesh goes with F as much as the cut measured (weld_weights.json), the rest with S
WW = json.load(open(os.path.join(PARTS, "weld_weights.json")))
weld = bpy.data.objects[SID + "_weld"]
gF, gS = weld.vertex_groups["letter_f"], weld.vertex_groups["weld"]
bx0, by0, bx1, by1 = WW["box"]
grid, step = WW["f"], WW["step"]


def weld_f(xp, yp):
    gx = min(max((xp - bx0) / step, 0), len(grid[0]) - 1.001)
    gy = min(max((yp - by0) / step, 0), len(grid) - 1.001)
    i, j = int(gy), int(gx)
    u, v = gy - i, gx - j
    return (grid[i][j] * (1 - u) * (1 - v) + grid[i][j + 1] * (1 - u) * v + grid[i + 1][j] * u * (1 - v) + grid[i + 1][j + 1] * u * v)


for v in weld.data.vertices:
    xp, yp = v.co.x * 100 + W / 2, H / 2 - v.co.z * 100
    wf = weld_f(xp, yp)
    gF.add([v.index], wf, "REPLACE")
    gS.add([v.index], 1 - wf, "REPLACE")
# drawn over both letters (it covers where they meet); the art layer's effects in front of everything
letters_y = min(bpy.data.objects[SID + "_letter_f"].matrix_world.translation.y, bpy.data.objects[SID + "_letter_s"].matrix_world.translation.y)
weld.location.y = letters_y - .1
FRONT = letters_y - .4

ART, FXB, FX = fxkit.layers(sc, SID)
fxkit.glow_compositor(sc, SID, back=dict(strength=1.0, size=.55, gain=1.6), front=dict(strength=.85, size=.4, gain=1.5))
if arm.animation_data:
    arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)

RIGID = ["word", "letter_f", "letter_s"]
CLIPS = {"idle": (1, 90), "land": (101, 130), "hit": (201, 256), "multi": (301, 356)}
arm["clips"] = {k: list(v) for k, v in CLIPS.items()}


# ------------------------------------------------------------------ the drips' springs
def drip_chain(name, seed):
    """Each drip its own spring: longer drips are softer and swing slower; stiff at the root, soft at the tip."""
    ch = CH[name]
    L = sum(math.dist(ch[i], ch[i + 1]) for i in range(len(ch) - 1))
    rnd = random.Random(seed)
    base = (4.4 - L / 75) * rnd.uniform(.9, 1.1)
    nb = len(ch) - 1
    freq = [base * 2.1] + [base * (.95 - .15 * i) for i in range(1, nb)]      # the root anchored in the paint
    return dict(chain=ch, freq=freq, zeta=rnd.uniform(.14, .2), gain=rnd.uniform(.75, .95), limit=16, stretch=True, stretch_limit=.3)


HANG = {"letter_f": {n: drip_chain(n, i) for i, n in enumerate(F_DRIPS)},
        "letter_s": {n: drip_chain(n, 10 + i) for i, n in enumerate(S_DRIPS)}}
NBONES = {n: len(CH[n]) - 1 for n in CH}


def follow(f0, f1, loop=False, forces=None, gain=1.0):
    """The drips, worked out from how this clip moves their letters, keyed onto their bones."""
    for holder, chains in HANG.items():
        res = fxkit.secondary(sc, arm, holder, f0, f1, chains, loop=loop, forces=forces, gain=gain)
        print(f"  {f0}-{f1} {holder}:", ", ".join(f"{b} {min(v):+.2f}..{max(v):+.2f}" for b, v in res.items()))
        for bone, vals in res.items():
            if bone.endswith(":sy"):
                b = bone[:-3]
                fxkit.key_series(arm, b, f0, vals, channel="sy", tol=.004, loop=loop)
                fxkit.key_series(arm, b, f0, [1 / math.sqrt(max(.5, v)) for v in vals], channel="sx", tol=.004, loop=loop)
            else:
                fxkit.key_series(arm, bone, f0, vals, channel="r", tol=.25, loop=loop)


def hard(act, bone, f):
    for fc in fxkit.fcurves(act):
        if fc.data_path.startswith(f'pose.bones["{bone}"]'):
            for kp in fc.keyframe_points:
                if abs(kp.co.x - f) < .5:
                    kp.handle_left_type = kp.handle_right_type = "VECTOR"
            fc.update()


# ================================================================== idle: wet paint, oozing
f0, f1 = CLIPS["idle"]
act = fxkit.begin_action(arm, SID + "_idle")
rest(arm, RIGID + DRIP_BONES, f0)
rest(arm, RIGID, f1 + 1)
for bone, f, h in (("letter_f", 14, .06), ("letter_s", 56, .06)):
    t = f
    key(arm, bone, t, y=0, sx=1, sy=1)
    key(arm, bone, t + 4, y=0, sx=1.01, sy=.988)
    key(arm, bone, t + 9, y=h, sx=.993, sy=1.014)
    key(arm, bone, t + 14, y=0, sx=1.016, sy=.98)
    hard(act, bone, t + 14)
    key(arm, bone, t + 19, y=0, sx=.997, sy=1.004)
    key(arm, bone, t + 24, y=0, sx=1, sy=1)
T_IDLE = (f1 - f0 + 1) / FPS
OOZE = {n: (i * .37 + .05) % 1 for i, n in enumerate(sorted(CH, key=lambda n: random.Random(n).random()))}


def idle_forces(name, i, t):
    """Each drip in turn is drawn slowly longer by the wet paint's weight, then snaps back up; and they all sway a
    little, each at its own phase. The loop repeats exactly every T_IDLE."""
    u = (t / T_IDLE) % 1
    s = ((u - OOZE[name]) % 1) * T_IDLE
    pull = smooth(0, .75, s) if s < .78 else 0.0
    n = NBONES[name]
    k = (i / n) ** 1.4
    sway = .9 * math.sin(2 * math.pi * (u + OOZE[name] * 2.3)) * i / n
    return Vector((sway, 0, -46 * pull * k))


follow(f0, f1, loop=True, forces=idle_forces)
fxkit.make_cyclic(act)
fxkit.end_action(arm, act, f0)

# ================================================================== land: splat
f0, f1 = CLIPS["land"]
act = fxkit.begin_action(arm, SID + "_land")
rest(arm, RIGID + DRIP_BONES, f0)
rest(arm, RIGID, f1)
for f, sx, sy in ((102, 1.06, .9), (106, .97, 1.04), (110, 1.016, .986), (114, .997, 1.004), (119, 1, 1)):
    key(arm, "word", f, sx=sx, sy=sy)
hard(act, "word", 102)
for bone, d in (("letter_f", 0), ("letter_s", 2)):
    for f, sx, sy in ((101, 1, 1), (103, 1.015, .978), (107, .993, 1.01), (111, 1, 1)):
        key(arm, bone, f + d, sx=sx, sy=sy)


def land_forces(name, i, t):
    f = CLIPS["land"][0] + t * FPS
    hit = 102 if name.startswith("f_") else 104
    kick = math.exp(-((f - hit - 1.5) / 1.6) ** 2)
    return Vector((0, 0, -120 * kick * (i / NBONES[name])))       # the impact flings them down


follow(f0, f1, forces=land_forces, gain=.9)
fxkit.end_action(arm, act, f0)

# ================================================================== hit: hop, hop, splash
f0, f1 = CLIPS["hit"]
act = fxkit.begin_action(arm, SID + "_hit")
rest(arm, RIGID + DRIP_BONES, f0)
rest(arm, RIGID, f1)
for f, sx, sy in ((201, 1, 1), (205, 1.05, .92), (209, .96, 1.06), (213, .985, 1.02), (217, 1.08, .89), (221, .97, 1.04),
                  (225, 1.012, .99), (230, 1, 1)):
    key(arm, "word", f, sx=sx, sy=sy)           # the word crouches, stretches up, slams and rebounds as one
hard(act, "word", 217)


def leap(bone, t0, h):
    """A letter's own leap on top of the word's: off the ground at t0, the top of it 5 frames on, down hard 5 more."""
    key(arm, bone, t0, y=0, sx=1, sy=1)
    key(arm, bone, t0 + 5, y=h, sx=.988, sy=1.016)
    key(arm, bone, t0 + 10, y=0, sx=1.018, sy=.978)
    hard(act, bone, t0 + 10)
    key(arm, bone, t0 + 14, y=.012, sx=.996, sy=1.005)
    key(arm, bone, t0 + 18, y=0, sx=1, sy=1)
    return t0 + 10                              # the frame it lands


LAND_F = leap("letter_f", 206, .32)             # F leads ...
LAND_S = leap("letter_s", 208, .32)             # ... S a beat behind


def hit_forces(name, i, t):
    f = CLIPS["hit"][0] + t * FPS
    hit = LAND_F if name.startswith("f_") else LAND_S
    kick = math.exp(-((f - hit - 1.2) / 1.5) ** 2)
    return Vector((0, 0, -150 * kick * (i / NBONES[name])))


follow(f0, f1, forces=hit_forces, gain=.8)
fxkit.end_action(arm, act, f0)

# ================================================================== multi: charge, and let go
f0, f1 = CLIPS["multi"]
act = fxkit.begin_action(arm, SID + "_multi")
rest(arm, RIGID + DRIP_BONES, f0)
rest(arm, RIGID, f1)
REL = 326                                       # it lets go
for f, sx, sy in ((303, 1, 1), (312, 1.02, 1.02), (319, 1.035, 1.035), (324, 1.075, .955), (REL, 1.08, .95), (329, 1.13, 1.17),
                  (332, 1.08, .9), (335, .98, 1.04), (339, 1.01, .99), (344, 1, 1)):
    key(arm, "word", f, sx=sx, sy=sy)          # it swells with the charge, crouches, pops, slams down
hard(act, "word", 332)
for bone, ph in (("letter_f", 0), ("letter_s", 1)):
    for i, f in enumerate(range(305, REL, 2)):  # it quivers, harder and harder
        a = .005 + .012 * smooth(304, REL, f)
        key(arm, bone, f, x=a if (i + ph) % 2 else -a, r=(.15 + .55 * smooth(304, REL, f)) * (1 if (i + ph) % 2 else -1))
    key(arm, bone, REL + 1, x=0, r=0)
    key(arm, bone, f1, x=0, r=0)


def multi_forces(name, i, t):
    f = CLIPS["multi"][0] + t * FPS
    n = NBONES[name]
    k = i / n
    up = smooth(304, 318, f) * (1 - smooth(REL - 1, REL + 1, f))        # the charge draws them up short
    kick = math.exp(-((f - 332.5) / 1.6) ** 2)                          # the slam flings them down
    jit = math.sin(f * 2.7 + len(name) * 1.3) * smooth(304, REL, f) * (1 - smooth(REL - 1, REL + 1, f))
    return Vector((14 * jit * k, 0, (32 * up - 150 * kick) * k))


follow(f0, f1, forces=multi_forces, gain=.85)
fxkit.end_action(arm, act, f0)

# ================================================================== effects
INK = srgb(10, 16, 6)
PAINT, PAINT_SH, PAINT_HI = srgb(158, 228, 36), srgb(70, 128, 16), srgb(232, 252, 150)
GREEN = LIME
CENTRES = {"letter_f": px(275, 330), "letter_s": px(735, 330)}


def tail_at(bone, f):
    """Where a bone's tail is (world x, z) at frame f, as the clips move it."""
    sc.frame_set(f)
    p = arm.matrix_world @ arm.pose.bones[bone].tail
    return p.x, p.z


def tips(names, f):
    return {n: tail_at(f"{n}.{NBONES[n] - 1}", f) for n in names}


# the glow behind each letter, in its own green: round each letter's edge (the word's outline, 9 px out, split
# between the two letters), riding it
OUT = [(x, y) for x, y in json.load(open(os.path.join(PARTS, "outline.json")))["points"]]
OUTW = fxkit.resample([px(x, y) for x, y in OUT], 260)
halo = {}
for bone in ("letter_f", "letter_s"):
    ob = gp_object(FXB, f"{SID}_halo_{bone}", depth=.3)
    ride(ob, arm, bone)
    halo[bone] = (ob, gp_mat(ob, "glow_green", GREEN), Board())
MID_X = px(512, 0)[0]
mine = ["letter_f" if x < MID_X else "letter_s" for x, z in OUTW]
runs = []                                      # the outline split into runs, each its letter's
cur, who = [], None
for p, m in zip(OUTW + OUTW[:1], mine + mine[:1]):
    if who is not None and m != who:
        if len(cur) > 2: runs.append((who, cur))
        cur = [cur[-1]]
    cur.append(p); who = m
if len(cur) > 2:
    runs.append((who, cur))


def glow_at(f, level, hold=2, bones=("letter_f", "letter_s")):
    for who, pts in runs:
        if who not in bones:
            continue
        ob, mat, board = halo[who]
        board.add(f, lambda dr, pts=pts, lv=level: [stroke(dr, pts, r * (.8 + .2 * min(lv, 2)), opacity=min(1, a * lv), mat=mat)
                                                    for r, a in ((.28, .05), (.2, .065), (.13, .08), (.08, .1))], hold)


REST_GLOW = .45
for f in range(1, 91, 2):                      # idle: it breathes
    glow_at(f, REST_GLOW + .15 * math.sin(2 * math.pi * (f - 1) / 90))
for f in range(101, 131):                      # land: flares with each letter's slam
    glow_at(f, REST_GLOW + .9 * math.exp(-max(0, f - 102) / 4) * (f >= 102), hold=1)
for f in range(201, 257):                      # hit: flaring with each slam
    lv = REST_GLOW + .25 * smooth(201, 208, f) - .25 * smooth(240, 256, f)
    lv += .85 * math.exp(-max(0, f - LAND_F) / 4) * (f >= LAND_F) + .85 * math.exp(-max(0, f - LAND_S) / 4) * (f >= LAND_S)
    glow_at(f, lv, hold=1)
for f in range(301, 357):                      # multi: wells up with the charge, flashes as it lets go
    lv = REST_GLOW + 1.0 * smooth(303, REL, f) * (1 + .12 * math.sin(f * 2.2)) if f <= REL else REST_GLOW + 1.6 * math.exp(-(f - REL) / 5)
    glow_at(f, lv, hold=1)
for ob, mat, board in halo.values():
    board.draw(gp_layer(ob, "glow"))

# paint: drops flung off the drips' tips and spattered round the letters, bubbles while it charges
paint = gp_object(ART, SID + "_paint", depth=FRONT)
m_paint = gp_mat(paint, "bs_paint", INK, fill=PAINT)
m_hi = gp_mat(paint, "bs_paint_hi", PAINT_HI, fill=PAINT_HI)
m_sh = gp_mat(paint, "bs_paint_sh", PAINT_SH, fill=PAINT_SH)
pb_ = Board()


def drop_pts(x, z, r, vx, vz, tail):
    """A paint drop: round at the front, drawn out into a tail behind it as it flies."""
    sp = math.hypot(vx, vz)
    ux, uz = (vx / sp, vz / sp) if sp > 1e-3 else (0.0, -1.0)
    out = []
    for k in range(28):
        a = 2 * math.pi * k / 28
        cx, cz = math.cos(a), math.sin(a)
        back = max(0.0, -(cx * ux + cz * uz))
        pull = tail * back ** 2.2
        out.append((x + cx * r - ux * pull * r, z + cz * r - uz * pull * r))
    return out


def drop(board, f0, life, at, v, r, seed, g=24.0, shrink=.4):
    """A drop of wet paint thrown off: inked, with its highlight; it stretches with its speed and shrinks away at the
    end (never fades)."""
    x0, z0 = at
    for k in range(life):
        t = k / FPS
        u = k / max(1, life - 1)
        s = 1.0 if u < 1 - shrink else max(0.0, (1 - u) / shrink) ** .8
        if s < .1:
            continue
        vx, vz = v[0], v[1] - g * t
        x, z = x0 + v[0] * t, z0 + v[1] * t - .5 * g * t * t
        tail = min(2.2, math.hypot(vx, vz) / 2.4)
        rr = r * s

        def fn(dr, x=x, z=z, rr=rr, vx=vx, vz=vz, tail=tail):
            pts = drop_pts(x, z, rr, vx, vz, tail)
            stroke(dr, pts, .017, mat=m_paint, cyclic=True, fill=True)
            stroke(dr, ring(x + rr * .2, z - rr * .22, rr * .55, n=14), .004, mat=m_sh, cyclic=True, fill=True, line=False)
            stroke(dr, ring(x - rr * .3, z + rr * .3, rr * .3, n=10), .004, mat=m_hi, cyclic=True, fill=True, line=False)
        board.add(f0 + k, fn)


def fling(board, f, names, speed=(2.2, 3.6), r=(.085, .13), seed=0, spread=.9):
    """Drops thrown off the drips' tips as they whip (at frame f)."""
    rnd = random.Random(seed)
    for n, (x, z) in tips(names, f).items():
        for j in range(rnd.choice((1, 1, 2))):
            a = -math.pi / 2 + rnd.uniform(-spread, spread)
            sp = rnd.uniform(*speed)
            drop(board, f + rnd.randint(0, 1), rnd.randint(9, 13), (x, z - .05), (math.cos(a) * sp * 1.3, math.sin(a) * sp * .4 + 1.6),
                 rnd.uniform(*r), seed * 13 + j)


def spatter(board, f, cx, cz, n, speed, r, seed, up=1.0, spread=math.pi, base=math.pi / 2, life=(11, 16), g=24.0, rx=1.0):
    """Paint spattered out from a point: drops in a fan (spread round base angle)."""
    rnd = random.Random(seed)
    for i in range(n):
        a = base + spread * ((i + rnd.uniform(.1, .9)) / n * 2 - 1)
        sp = rnd.uniform(*speed)
        drop(board, f + rnd.randint(0, 2), rnd.randint(*life), (cx + rnd.uniform(-.3, .3) * rx, cz + rnd.uniform(-.1, .1)),
             (math.cos(a) * sp, math.sin(a) * sp * up), rnd.uniform(*r), seed * 31 + i, g=g)


# land: spatter out low from under each letter, drops off the drips as they whip
for bone, f, seed in (("letter_f", 102, 1), ("letter_s", 104, 2)):
    x, z = px(275 if bone == "letter_f" else 735, 690)
    spatter(pb_, f, x, z, 7, (2.4, 3.6), (.08, .13), seed, up=.6, spread=1.2, base=math.pi / 2, rx=1.6)
fling(pb_, 105, F_DRIPS, seed=3); fling(pb_, 107, S_DRIPS, seed=4)
# hit: each slam spatters paint out both ways and flings drops off the drips
for bone, f, seed in (("letter_f", LAND_F, 5), ("letter_s", LAND_S, 6)):
    x, z = px(275 if bone == "letter_f" else 735, 700)
    spatter(pb_, f, x, z, 11, (3.0, 4.6), (.09, .15), seed, up=.8, spread=1.25, base=math.pi / 2, rx=2.0)
fling(pb_, LAND_F + 2, F_DRIPS, speed=(3, 4.4), seed=7); fling(pb_, LAND_S + 2, S_DRIPS, speed=(3, 4.4), seed=8)
# multi: the paint bubbles as it charges (rising, then popping); the release throws a ring of spatter
bub = random.Random(9)
for i in range(16):
    bone = "letter_f" if i % 2 == 0 else "letter_s"
    f = 305 + bub.randint(0, 18)
    x = bub.uniform(-4.4, -.6) if bone == "letter_f" else bub.uniform(.4, 4.6)
    z = bub.uniform(.6, 3.2)
    life = bub.randint(6, 10)
    rr = bub.uniform(.09, .15)
    for k in range(life):
        t = k / (life - 1)
        pb_.add(f + k, lambda dr, x=x, z=z + .5 * t, r=rr * (.4 + .8 * t): (
            stroke(dr, ring(x, z, r, n=18), .012, mat=m_paint, cyclic=True, fill=True),
            stroke(dr, ring(x - r * .32, z + r * .32, r * .3, n=8), .004, mat=m_hi, cyclic=True, fill=True, line=False)))
    pb_.add(f + life, lambda dr, x=x, z=z + .5, r=rr * 1.3: [stroke(dr, star(x, z, r * 1.5, .3, points=5, inner=.35), .01, mat=m_hi, cyclic=True)])
lift = random.Random(15)                     # paint lifting off the letters' tops as the charge takes hold
TOPS = [p for who, pts in runs for p in pts if p[1] > 1.2]
for i in range(14):
    x, z = TOPS[lift.randrange(len(TOPS))]
    f = 308 + lift.randint(0, 14)
    life = lift.randint(9, 13)
    rr = lift.uniform(.08, .13)
    drift = lift.uniform(-.25, .25)
    for k in range(life):
        t = k / (life - 1)
        s_ = min(1, t * 4) * max(0.0, 1 - max(0, (t - .7) / .3)) ** .8
        if s_ < .1:
            continue
        pb_.add(f + k, lambda dr, x=x + drift * t, z=z - .15 + 1.1 * t ** 1.3, r=rr * s_, t=t: (
            stroke(dr, drop_pts(x, z, r, 0, 2.0, .9 * (1 - t) + .2), .016, mat=m_paint, cyclic=True, fill=True),
            stroke(dr, ring(x - r * .3, z + r * .3, r * .3, n=10), .004, mat=m_hi, cyclic=True, fill=True, line=False)))
CX, CZ = px(512, 360)
spatter(pb_, REL + 3, CX, CZ, 24, (4.2, 6.2), (.09, .15), 11, up=1.0, spread=math.pi, base=math.pi / 2, life=(10, 13), g=14.0, rx=3.5)
fling(pb_, 334, F_DRIPS + S_DRIPS, speed=(3, 4.2), seed=12)
pb_.draw(gp_layer(paint, "paint"))

# light over the art (bloomed): glints on the gloss, speed lines under the hops, arcs off the charged paint, the
# release's sparkle burst
fxw = gp_object(FX, SID + "_fx", depth=FRONT - .1)
w_white = gp_mat(fxw, "fx_white_line", WHITE); w_green = gp_mat(fxw, "fx_green_line", GREEN)
w_spark = gp_mat(fxw, "fx_white_fill", WHITE, fill=WHITE); w_greenf = gp_mat(fxw, "fx_green_fill", GREEN, fill=GREEN)
world = Board()
on = {}
for bone in ("letter_f", "letter_s"):
    ob = gp_object(FX, f"{SID}_fx_{bone}", depth=FRONT - .1)
    ride(ob, arm, bone)
    on[bone] = (ob, gp_mat(ob, "fx_white_fill", WHITE, fill=WHITE), gp_mat(ob, "fx_green_line", GREEN), Board())
# idle: a glint on each letter's gloss, in turn
fxkit.sparkle(on["letter_f"][3], 40, 9, *px(205, 120), .34, on["letter_f"][1])
fxkit.sparkle(on["letter_s"][3], 78, 9, *px(870, 160), .3, on["letter_s"][1], rot0=.5)
# land: two quick glints
fxkit.sparkle(on["letter_f"][3], 106, 8, *px(160, 90), .3, on["letter_f"][1])
fxkit.sparkle(on["letter_s"][3], 109, 8, *px(820, 130), .28, on["letter_s"][1], rot0=.4)
# hit: speed lines under each hop, glints all round after the slams
for bone, t0 in (("letter_f", 207), ("letter_s", 209)):
    x0 = px(275 if bone == "letter_f" else 735, 0)[0]
    for k in range(5):
        for j, dx in enumerate((-1.3, -.45, .45, 1.3)):
            world.add(t0 + k, lambda dr, x=x0 + dx, k=k, j=j: stroke(dr, [(x + .05 * j, -4.0 + .25 * k), (x + .05 * j, -4.9 + .3 * k)], .026,
                                                                     mat=w_white))
rnd = random.Random(14)
for i in range(9):
    fxkit.sparkle(world, LAND_F + rnd.randint(1, 22), rnd.randint(7, 10), rnd.uniform(-5.0, 5.0), rnd.uniform(-3.3, 4.2),
                  rnd.uniform(.25, .45), w_spark if i % 3 else w_greenf, rot0=rnd.uniform(0, 1))
# multi: green arcs crackling off the letters' edges as it charges; the release bursts sparkles and streaks
EDGE_RUNS = [(who, fxkit.resample(pts, max(8, len(pts) // 2), closed=False)) for who, pts in runs]
for f in range(309, REL + 1, 2):
    rr = random.Random(f * 3)
    for j in range(2 + (f > 318)):
        who, pts = EDGE_RUNS[rr.randrange(len(EDGE_RUNS))]
        x, z = pts[rr.randrange(len(pts))]
        cx, cz = CENTRES[who]
        nx, nz = x - cx, z - cz
        L = math.hypot(nx, nz) or 1
        ln = rr.uniform(.55, 1.05)
        zz = fxkit.zigzag(x, z, x + nx / L * ln, z + nz / L * ln, n=6, amp=.14, seed=f + j)
        world.add(f, lambda dr, zz=zz, j=j: stroke(dr, zz, .03, mat=w_green if j % 2 else w_white), hold=2)
fxkit.streaks(world, REL + 1, 9, CX, CZ, 4.6, 6.2, (w_white, w_green), n=16, rot=.1)
for i in range(10):
    a = 2 * math.pi * i / 10 + .3
    fxkit.sparkle(world, REL + 2 + i % 4, 9, CX + math.cos(a) * 5.0, CZ + math.sin(a) * 3.9, .32, w_spark if i % 2 else w_greenf, rot0=a)
world.draw(gp_layer(fxw, "fx"))
for ob, _, _, board in on.values():
    board.draw(gp_layer(ob, "fx"))

sc.frame_start, sc.frame_end = 1, max(b for a, b in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], "| saved", fxkit.save(SID))
