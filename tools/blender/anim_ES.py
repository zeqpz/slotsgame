# ES - the extreme scatter ("XFS" in purple dripping graffiti, still wet) - animated in Blender: four Actions on its
# rig (idle, land, hit, multi) laid one after another on the rig's NLA track, and its effects drawn frame by frame in
# Grease Pencil on the same timeline. No tier glow: the scatter glows in its own purple, and the rest is wet paint
# with an electric edge - it is the extreme one.
#   the letters  X is a sticker of its own and moves freely; F and S are one (the F's middle bar runs into the S):
#                a bone "fs" (added here at their feet) carries the pair's big moves, and each letter adds only a
#                little of its own, so the paint between them (the "weld", weighted F-to-S across the join) stretches
#                like wet paint instead of tearing; a root bone "word" under it all
#   the drips    nine drips, each its own chain of bones and its own spring (fxkit.secondary): stiff at the root,
#                soft at the tip, free to stretch - they lag, whip and ooze with how their letter really moves
#   idle         wet paint at rest: the drips ooze longer in turn and snap back, a ripple runs along the word (X, then
#                F and S), a glint slides over the gloss, a spark now and then; the purple glow breathes
#   land         the word squashes left to right as it hits - X, then the FS - the drips whip down and spring back,
#                paint spatters out from under it, the glow flares
#   hit          a wave: X crouches, hops leaning out and slams down; then F and S hop as one, leaning the other way,
#                the paint between them stretching; every slam flings the drips and spatters paint, purple lightning
#                jumps between the letters, rings roll out, glints
#   multi        the charge: the letters quiver and swell, the drips are drawn up short, the paint bubbles and lifts
#                off, purple arcs crackle off the edges and the glow wells up - then it lets go: the word pops and
#                slams, the drips fling down, a ring of spatter and streaks bursts out, sparkles
# Runs INSIDE Blender, after build_symbol_scene.py (tools/blender/run.py runs both in a background Blender).
import bpy, importlib, json, math, os, random, sys
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
import fxkit
importlib.reload(fxkit)
from fxkit import (key, rest, px, smooth, gp_object, gp_mat, gp_layer, ride, stroke, star, ring, Board, WHITE)

SID = "ES"
sc, arm, spec = fxkit.setup(SID)
FPS = sc.render.fps
PARTS = os.path.join(fxkit.ROOT, "art", "blender", "parts", SID)
W, H = spec["size"]


def srgb(r, g, b, a=1.0):
    """A colour picked off the art (0-255, sRGB) as Blender's linear colour."""
    f = lambda c: (c / 255) / 12.92 if c / 255 <= .04045 else ((c / 255 + .055) / 1.055) ** 2.4
    return (f(r), f(g), f(b), a)


CH = {p["name"]: p["chain"] for p in spec["parts"] if p.get("chain")}
LETTER_OF = {"x": "letter_x", "f": "letter_f", "s": "letter_s"}
DRIPS_OF = {L: [n for n in CH if n.startswith(k + "_")] for k, L in LETTER_OF.items()}
DRIP_BONES = [b.name for b in arm.data.bones if b.name.split(".")[0] in CH]
NBONES = {n: len(CH[n]) - 1 for n in CH}

# ------------------------------------------------------------------ the rig, as the animation needs it
FOOT = {"word": (420, 566), "fs": (535, 482)}
if "word" not in arm.data.bones:
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    for name in ("word", "fs"):
        b = eb.new(name)
        b.head = fxkit.vec(*FOOT[name])
        b.tail = b.head + Vector((0, 0, .6))
        b.roll = 0
    eb["fs"].parent = eb["word"]
    for n, par in (("letter_x", "word"), ("letter_f", "fs"), ("letter_s", "fs")):
        eb[n].use_connect = False
        eb[n].parent = eb[par]
    bpy.ops.object.mode_set(mode="OBJECT")
for n in ("word", "fs"):
    arm.pose.bones[n].rotation_mode = "XYZ"
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
LETTERS_Y = min(bpy.data.objects[f"{SID}_letter_{k}"].matrix_world.translation.y for k in "xfs")
weld.location.y = LETTERS_Y - .1              # drawn over both letters (it covers where they meet)
FRONT = LETTERS_Y - .4                        # the art layer's effects, in front of everything

ART, FXB, FX = fxkit.layers(sc, SID)
fxkit.glow_compositor(sc, SID, back=dict(strength=1.0, size=.55, gain=1.6), front=dict(strength=.9, size=.42, gain=1.5))
if arm.animation_data:
    arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)

RIGID = ["word", "fs", "letter_x", "letter_f", "letter_s"]
CLIPS = {"idle": (1, 90), "land": (101, 130), "hit": (201, 256), "multi": (301, 356)}
arm["clips"] = {k: list(v) for k, v in CLIPS.items()}


# ------------------------------------------------------------------ the drips' springs
def drip_chain(name, seed):
    """Each drip its own spring: longer drips are softer and swing slower; the root anchored in the paint, soft at
    the tip."""
    ch = CH[name]
    L = sum(math.dist(ch[i], ch[i + 1]) for i in range(len(ch) - 1))
    rnd = random.Random(seed)
    base = (4.6 - L / 60) * rnd.uniform(.9, 1.1)
    nb = len(ch) - 1
    freq = [base * 2.1] + [base * (.95 - .15 * i) for i in range(1, nb)]
    return dict(chain=ch, freq=freq, zeta=rnd.uniform(.14, .2), gain=rnd.uniform(.75, .95), limit=16, stretch=True, stretch_limit=.3)


HANG = {L: {n: drip_chain(n, 7 * j + i) for i, n in enumerate(names)} for j, (L, names) in enumerate(DRIPS_OF.items())}


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


def hop(bone, f, h, lean=0.0, crouch=4, up=7, down=5, sq=1.0):
    """A hop from the foot: crouch, spring up stretched and leaning, slam down squashed (a hit key), settle."""
    t1, t2, t3 = f + crouch, f + crouch + up, f + crouch + up + down
    key(arm, bone, f, y=0, r=0, sx=1, sy=1)
    key(arm, bone, t1, y=0, r=-lean * .3, sx=1 + .05 * sq, sy=1 - .08 * sq)
    key(arm, bone, t2, y=h, r=lean, sx=1 - .04 * sq, sy=1 + .07 * sq)
    key(arm, bone, t3, y=0, r=-lean * .25, sx=1 + .08 * sq, sy=1 - .11 * sq)
    hard(act, bone, t3)
    key(arm, bone, t3 + 4, y=0, r=lean * .1, sx=1 - .02 * sq, sy=1 + .03 * sq)
    key(arm, bone, t3 + 8, y=0, r=0, sx=1 + .006 * sq, sy=1 - .008 * sq)
    key(arm, bone, t3 + 12, y=0, r=0, sx=1, sy=1)
    return t3                                   # the frame it lands


def wobble(bone, f, amp, frames=(0, 3, 7, 11, 15)):
    """A little squash ripple of a letter's own, on top of the pair's move (it keeps the paint between them tight)."""
    for k, (d, s) in enumerate(zip(frames, (0, 1, -.6, .25, 0))):
        key(arm, bone, f + d, sx=1 + amp * s * .6, sy=1 - amp * s)


# ================================================================== idle: wet paint, oozing; a ripple along the word
f0, f1 = CLIPS["idle"]
act = fxkit.begin_action(arm, SID + "_idle")
rest(arm, RIGID + DRIP_BONES, f0)
rest(arm, RIGID, f1 + 1)
for bone, f in (("letter_x", 30), ("fs", 36)):
    key(arm, bone, f, y=0, sx=1, sy=1)
    key(arm, bone, f + 4, y=0, sx=1.02, sy=.975)
    key(arm, bone, f + 9, y=.08, sx=.985, sy=1.03)
    key(arm, bone, f + 14, y=0, sx=1.03, sy=.96)
    hard(act, bone, f + 14)
    key(arm, bone, f + 19, y=0, sx=.995, sy=1.008)
    key(arm, bone, f + 24, y=0, sx=1, sy=1)
wobble("letter_f", 48, .012)
wobble("letter_s", 50, .012)
T_IDLE = (f1 - f0 + 1) / FPS
OOZE = {n: (i * .41 + .07) % 1 for i, n in enumerate(sorted(CH, key=lambda n: random.Random(n + "es").random()))}


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

# ================================================================== land: splat, left to right
f0, f1 = CLIPS["land"]
act = fxkit.begin_action(arm, SID + "_land")
rest(arm, RIGID + DRIP_BONES, f0)
rest(arm, RIGID, f1)
LAND_HIT = {"letter_x": 102, "fs": 104}
for bone, h in LAND_HIT.items():
    for f, sx, sy in ((h, 1.09, .87), (h + 4, .96, 1.06), (h + 8, 1.02, .98), (h + 12, .997, 1.004), (h + 17, 1, 1)):
        key(arm, bone, f, sx=sx, sy=sy)
    hard(act, bone, h)
wobble("letter_s", 105, .02)


def land_forces(name, i, t):
    f = CLIPS["land"][0] + t * FPS
    hit = LAND_HIT["letter_x"] if name.startswith("x_") else LAND_HIT["fs"]
    kick = math.exp(-((f - hit - 1.5) / 1.6) ** 2)
    return Vector((0, 0, -120 * kick * (i / NBONES[name])))       # the impact flings them down


follow(f0, f1, forces=land_forces, gain=.9)
fxkit.end_action(arm, act, f0)

# ================================================================== hit: the wave - X, then F and S
f0, f1 = CLIPS["hit"]
act = fxkit.begin_action(arm, SID + "_hit")
rest(arm, RIGID + DRIP_BONES, f0)
rest(arm, RIGID, f1)
LAND_X = hop("letter_x", 203, .4, lean=5)
LAND_FS = hop("fs", 211, .4, lean=-4)
wobble("letter_f", LAND_FS - 1, .02)          # F hits a hair before S: the paint between them pulls
wobble("letter_s", LAND_FS, .025)
for f, sx, sy in ((201, 1, 1), (236, 1, 1), (240, 1.03, .97), (244, .99, 1.01), (249, 1, 1)):
    key(arm, "word", f, sx=sx, sy=sy)           # the word's last little bounce together


def hit_forces(name, i, t):
    f = CLIPS["hit"][0] + t * FPS
    hit = LAND_X if name.startswith("x_") else LAND_FS
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
for bone, ph in (("letter_x", 0), ("fs", 1)):
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
INK = srgb(12, 6, 18)
PAINT, PAINT_SH, PAINT_HI = srgb(170, 59, 236), srgb(90, 15, 152), srgb(244, 163, 254)
PURPLE = srgb(186, 92, 255)                    # the glow and the light: the paint's own purple, lit
CENTRES = {"letter_x": px(225, 290), "letter_f": px(440, 290), "letter_s": px(650, 300)}
WORD_C = px(420, 300)


def tail_at(bone, f):
    """Where a bone's tail is (world x, z) at frame f, as the clips move it."""
    sc.frame_set(f)
    p = arm.matrix_world @ arm.pose.bones[bone].tail
    return p.x, p.z


def tips(names, f):
    return {n: tail_at(f"{n}.{NBONES[n] - 1}", f) for n in names}


# the glow behind each letter, in its own purple: round each sticker, 9 px out (halo.json, made by the cut), every
# stretch of it riding the letter it belongs to
HALO = json.load(open(os.path.join(PARTS, "halo.json")))["loops"]
runs = []
for lp in HALO:
    pts = [px(x, y) for x, y in lp["pts"]]
    own = [LETTER_OF[o] for o in lp["owner"]]
    k0 = next((k for k in range(len(own)) if own[k] != own[k - 1]), 0)       # start where the owner changes
    pts, own = pts[k0:] + pts[:k0], own[k0:] + own[:k0]
    cur, who = [], None
    for p, m in zip(pts + pts[:1], own + own[:1]):
        if who is not None and m != who:
            if len(cur) > 2: runs.append((who, cur))
            cur = [cur[-1]]
        cur.append(p); who = m
    if len(cur) > 2:
        runs.append((who, cur))
halo = {}
for bone in LETTER_OF.values():
    ob = gp_object(FXB, f"{SID}_halo_{bone}", depth=.3)
    ride(ob, arm, bone)
    halo[bone] = (ob, gp_mat(ob, "glow_purple", PURPLE), Board())


def glow_at(f, level, hold=2):
    for who, pts in runs:
        ob, mat, board = halo[who]
        board.add(f, lambda dr, pts=pts, lv=level: [stroke(dr, pts, r * (.8 + .2 * min(lv, 2)), opacity=min(1, a * lv), mat=mat)
                                                    for r, a in ((.28, .05), (.2, .065), (.13, .08), (.08, .1))], hold)


REST_GLOW = .45
for f in range(1, 91, 2):                      # idle: it breathes
    glow_at(f, REST_GLOW + .15 * math.sin(2 * math.pi * (f - 1) / 90))
for f in range(101, 131):                      # land: flares with the slam
    glow_at(f, REST_GLOW + .9 * math.exp(-max(0, f - 102) / 4) * (f >= 102), hold=1)
for f in range(201, 257):                      # hit: flaring with each slam
    lv = REST_GLOW + .25 * smooth(201, 208, f) - .25 * smooth(240, 256, f)
    lv += .85 * math.exp(-max(0, f - LAND_X) / 4) * (f >= LAND_X) + .85 * math.exp(-max(0, f - LAND_FS) / 4) * (f >= LAND_FS)
    glow_at(f, lv, hold=1)
for f in range(301, 357):                      # multi: wells up with the charge, flashes as it lets go
    lv = REST_GLOW + 1.0 * smooth(303, REL, f) * (1 + .12 * math.sin(f * 2.2)) if f <= REL else REST_GLOW + 1.6 * math.exp(-(f - REL) / 5)
    glow_at(f, lv, hold=1)
for ob, mat, board in halo.values():
    board.draw(gp_layer(ob, "glow"))

# paint: drops flung off the drips' tips and spattered round the letters, bubbles and lift-off while it charges
paint = gp_object(ART, SID + "_paint", depth=FRONT)
m_paint = gp_mat(paint, "es_paint", INK, fill=PAINT)
m_hi = gp_mat(paint, "es_paint_hi", PAINT_HI, fill=PAINT_HI)
m_sh = gp_mat(paint, "es_paint_sh", PAINT_SH, fill=PAINT_SH)
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
    """A drop of wet paint thrown off: inked, shaded, with its highlight; it stretches with its speed and shrinks
    away at the end (never fades)."""
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
            stroke(dr, drop_pts(x, z, rr, vx, vz, tail), .017, mat=m_paint, cyclic=True, fill=True)
            stroke(dr, ring(x + rr * .2, z - rr * .22, rr * .55, n=14), .004, mat=m_sh, cyclic=True, fill=True, line=False)
            stroke(dr, ring(x - rr * .3, z + rr * .3, rr * .3, n=10), .004, mat=m_hi, cyclic=True, fill=True, line=False)
        board.add(f0 + k, fn)


def fling(board, f, names, speed=(2.2, 3.6), r=(.075, .115), seed=0, spread=.9):
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


FEET = {"letter_x": px(225, 520), "fs": px(540, 540)}
X_DRIPS, F_DRIPS, S_DRIPS = DRIPS_OF["letter_x"], DRIPS_OF["letter_f"], DRIPS_OF["letter_s"]
# land: spatter out low from under the word, left to right; drops off the drips as they whip
for (bone, f), seed in zip(LAND_HIT.items(), (1, 2)):
    spatter(pb_, f, *FEET[bone], 6 if bone == "letter_x" else 8, (2.4, 3.6), (.07, .115), seed, up=.6, spread=1.2, rx=1.4)
fling(pb_, 105, X_DRIPS, seed=3); fling(pb_, 107, F_DRIPS + S_DRIPS, seed=4)
# hit: each slam spatters paint out both ways and flings drops off the drips
spatter(pb_, LAND_X, *FEET["letter_x"], 9, (3.0, 4.6), (.08, .13), 5, up=.8, spread=1.25, rx=1.6)
spatter(pb_, LAND_FS, *FEET["fs"], 12, (3.0, 4.8), (.08, .13), 6, up=.8, spread=1.25, rx=2.4)
fling(pb_, LAND_X + 2, X_DRIPS, speed=(3, 4.4), seed=7); fling(pb_, LAND_FS + 2, F_DRIPS + S_DRIPS, speed=(3, 4.4), seed=8)
# multi: the paint bubbles as it charges (rising, then popping), and drops lift off the letters' tops
bub = random.Random(9)
for i in range(18):
    who = ("letter_x", "letter_f", "letter_s")[i % 3]
    cx, cz = CENTRES[who]
    f = 305 + bub.randint(0, 18)
    x, z = cx + bub.uniform(-.8, .8), cz + bub.uniform(-.6, 1.4)
    life = bub.randint(6, 10)
    rr = bub.uniform(.08, .13)
    for k in range(life):
        t = k / (life - 1)
        pb_.add(f + k, lambda dr, x=x, z=z + .5 * t, r=rr * (.4 + .8 * t): (
            stroke(dr, ring(x, z, r, n=18), .012, mat=m_paint, cyclic=True, fill=True),
            stroke(dr, ring(x - r * .32, z + r * .32, r * .3, n=8), .004, mat=m_hi, cyclic=True, fill=True, line=False)))
    pb_.add(f + life, lambda dr, x=x, z=z + .5, r=rr * 1.3: [stroke(dr, star(x, z, r * 1.5, .3, points=5, inner=.35), .01, mat=m_hi, cyclic=True)])
lift = random.Random(15)
TOPS = [p for who, pts in runs for p in pts if p[1] > 1.0]
for i in range(14):
    x, z = TOPS[lift.randrange(len(TOPS))]
    f = 308 + lift.randint(0, 14)
    life = lift.randint(9, 13)
    rr = lift.uniform(.07, .11)
    drift = lift.uniform(-.25, .25)
    for k in range(life):
        t = k / (life - 1)
        s_ = min(1, t * 4) * max(0.0, 1 - max(0, (t - .7) / .3)) ** .8
        if s_ < .1:
            continue
        pb_.add(f + k, lambda dr, x=x + drift * t, z=z - .15 + 1.1 * t ** 1.3, r=rr * s_, t=t: (
            stroke(dr, drop_pts(x, z, r, 0, 2.0, .9 * (1 - t) + .2), .016, mat=m_paint, cyclic=True, fill=True),
            stroke(dr, ring(x - r * .3, z + r * .3, r * .3, n=10), .004, mat=m_hi, cyclic=True, fill=True, line=False)))
spatter(pb_, REL + 3, *WORD_C, 24, (4.2, 6.2), (.08, .13), 11, up=1.0, spread=math.pi, life=(10, 13), g=14.0, rx=3.0)
fling(pb_, 334, X_DRIPS + F_DRIPS + S_DRIPS, speed=(3, 4.2), seed=12)
pb_.draw(gp_layer(paint, "paint"))

# light over the art (bloomed): glints and sparks, speed lines under the hops, lightning between the letters, rings,
# arcs off the charged paint, the release's burst
fxw = gp_object(FX, SID + "_fx", depth=FRONT - .1)
w_white = gp_mat(fxw, "fx_white_line", WHITE); w_purple = gp_mat(fxw, "fx_purple_line", PURPLE)
w_spark = gp_mat(fxw, "fx_white_fill", WHITE, fill=WHITE); w_purplef = gp_mat(fxw, "fx_purple_fill", PURPLE, fill=PURPLE)
world = Board()
on = {}
for bone in LETTER_OF.values():
    ob = gp_object(FX, f"{SID}_fx_{bone}", depth=FRONT - .1)
    ride(ob, arm, bone)
    on[bone] = (ob, gp_mat(ob, "fx_white_fill", WHITE, fill=WHITE), gp_mat(ob, "fx_purple_line", PURPLE), Board())


def bolt(board, f, p0, p1, mats, seed, hold=1, width=.034, forks=2):
    """A bolt of purple lightning from p0 to p1, forked."""
    rnd = random.Random(seed)
    pts = fxkit.zigzag(*p0, *p1, n=7, amp=.22, seed=seed)
    board.add(f, lambda dr, pts=pts: (stroke(dr, pts, width, mat=mats[0]), stroke(dr, pts, width * .4, mat=mats[1])), hold)
    for k in range(forks):
        mx, mz = pts[rnd.randint(2, 5)]
        a = math.atan2(p1[1] - p0[1], p1[0] - p0[0]) + rnd.choice((-1, 1)) * rnd.uniform(.6, 1.1)
        ln = math.dist(p0, p1) * rnd.uniform(.2, .35)
        fk = fxkit.zigzag(mx, mz, mx + math.cos(a) * ln, mz + math.sin(a) * ln, n=3, amp=.1, seed=seed * 3 + k)
        board.add(f, lambda dr, fk=fk: stroke(dr, fk, width * .6, mat=mats[0]), hold)


# idle: a glint on each letter's gloss in turn; a lone spark crawls along the X's edge, then the S's
fxkit.sparkle(on["letter_x"][3], 22, 9, *px(150, 110), .32, on["letter_x"][1])
fxkit.sparkle(on["letter_f"][3], 52, 9, *px(410, 105), .28, on["letter_f"][1], rot0=.4)
fxkit.sparkle(on["letter_s"][3], 74, 9, *px(700, 150), .3, on["letter_s"][1], rot0=.8)
for who, f_start in (("letter_x", 8), ("letter_s", 60)):
    pts = next(p for w_, p in runs if w_ == who)
    for k in range(10):
        x, z = pts[min(len(pts) - 1, int(len(pts) * (.15 + .05 * k)))]
        world.add(f_start + k, lambda dr, x=x, z=z, k=k: stroke(dr, star(x, z, .1 + .05 * math.sin(k * 1.3), k * .6), .004, mat=w_spark,
                                                                cyclic=True, fill=True, line=False))
# land: quick glints
fxkit.sparkle(on["letter_x"][3], 105, 8, *px(130, 95), .28, on["letter_x"][1])
fxkit.sparkle(on["letter_s"][3], 109, 8, *px(720, 120), .26, on["letter_s"][1], rot0=.4)
# hit: speed lines under each hop; lightning jumps the gap between the letters at each slam; rings; glints
for x0, t0 in ((px(225, 0)[0], 208), (px(540, 0)[0], 216)):
    for k in range(5):
        for j, dx in enumerate((-1.0, -.35, .35, 1.0)):
            world.add(t0 + k, lambda dr, x=x0 + dx, k=k, j=j: stroke(dr, [(x + .05 * j, -3.3 + .25 * k), (x + .05 * j, -4.2 + .3 * k)], .026,
                                                                     mat=w_white))
for f, seed in ((LAND_X, 1), (LAND_X + 2, 2), (LAND_FS, 3), (LAND_FS + 2, 4), (LAND_FS + 4, 5)):
    rnd = random.Random(seed)
    a = px(250 + rnd.uniform(0, 60), 160 + rnd.uniform(0, 260))
    b = px(420 + rnd.uniform(0, 60), 160 + rnd.uniform(0, 260))
    bolt(world, f, a, b, (w_purple, w_white), seed * 17, hold=2)
for f, (cx, cz) in ((LAND_X, FEET["letter_x"]), (LAND_FS, FEET["fs"])):
    fxkit.shock_rings(world, f, cx, cz + .4, .6, 3.4, (w_purple, w_white), life=9, lag=2, width=.06)
rnd = random.Random(14)
for i in range(10):
    fxkit.sparkle(world, LAND_X + rnd.randint(1, 26), rnd.randint(7, 10), rnd.uniform(-4.6, 4.6), rnd.uniform(-3.2, 3.6),
                  rnd.uniform(.25, .45), w_spark if i % 3 else w_purplef, rot0=rnd.uniform(0, 1))
# multi: purple arcs crackling off the letters' edges as it charges, bolts across the gap; the release bursts
EDGE_RUNS = [(who, fxkit.resample(pts, max(8, len(pts) // 2), closed=False)) for who, pts in runs]
for f in range(309, REL + 1, 2):
    rr = random.Random(f * 3)
    for j in range(2 + (f > 318)):
        who, pts = EDGE_RUNS[rr.randrange(len(EDGE_RUNS))]
        x, z = pts[rr.randrange(len(pts))]
        cx, cz = CENTRES[who]
        nx, nz = x - cx, z - cz
        L = math.hypot(nx, nz) or 1
        nx, nz = nx / L, nz / L
        ln = rr.uniform(.55, 1.05)
        zz = fxkit.zigzag(x - nx * .15, z - nz * .15, x + nx * ln, z + nz * ln, n=6, amp=.14, seed=f + j)
        world.add(f, lambda dr, zz=zz, j=j: stroke(dr, zz, .03, mat=w_purple if j % 2 else w_white), hold=2)
for f in range(315, REL + 1, 3):
    bolt(world, f, px(300, 150 + 4 * (f - 315) % 230), px(400, 200 + 7 * (f - 315) % 200), (w_purple, w_white), f, hold=2, width=.028, forks=1)
fxkit.streaks(world, REL + 1, 9, *WORD_C, 4.6, 6.2, (w_white, w_purple), n=16, rot=.1)
fxkit.shock_rings(world, REL + 1, *WORD_C, 3.2, 6.0, (w_purple, w_white), life=11, lag=3, width=.1)
for i in range(10):
    a = 2 * math.pi * i / 10 + .3
    fxkit.sparkle(world, REL + 2 + i % 4, 9, WORD_C[0] + math.cos(a) * 4.8, WORD_C[1] + math.sin(a) * 3.6, .32,
                  w_spark if i % 2 else w_purplef, rot0=a)
world.draw(gp_layer(fxw, "fx"))
for ob, _, _, board in on.values():
    board.draw(gp_layer(ob, "fx"))

sc.frame_start, sc.frame_end = 1, max(b for a, b in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], "| saved", fxkit.save(SID))
