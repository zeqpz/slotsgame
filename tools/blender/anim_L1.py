# L1 - the spray can - animated in Blender: four Actions on its rig (idle, land, hit, multi) laid one after another
# on the rig's NLA track, and its spray drawn frame by frame in Grease Pencil on the same timeline.
# (Redone 2026-11-03 for the new upright art; the old spraying-can version is anim_L1.orig.py.txt.)
#   the rig     tip (the root, low on the base's right side: the can tilts over about it), the can on it (its base:
#               sways, squashes, rattles) and the cap on the can (pressed straight down onto the stem)
#               (tools/blender/cuts/L1.py)
#   the spray   drawn frame by frame, only when the cap is pressed: a cone of paint shooting from the nozzle (it
#               rides the nozzle while the can rumbles, sags a little under its own weight, and once the cap is let
#               go its tail leaves the nozzle and flies into the cloud), a cloud of cartoon paint puffs billowing
#               where it ends (solid, inked, glossy - they swell, boil on twos, then drift and shrink away), specks
#               round the jet, droplets flung off the cloud
#   idle        calm, not spraying: it sways on its base, a glint slides down the glossy body, the ball inside
#               rattles once (a little hop and shiver, the cap a beat behind, rattle marks)
#   land        it thuds onto its base (dust), tips over a little and lets out a quick puff, drops back upright
#   hit         it crouches, tips over, the cap is slammed down: a strong burst - long jet, a big boiling cloud,
#               droplets, sparkles - the can rumbling with the thrust; then it rights itself and rocks to rest
#   multi       shaken hard (the ball rattles, pulses of light), then it tips over and lets go one big burst with
#               rings of light and streaks; it rights itself by the end
# Every one-shot ends exactly on the rest pose (upright, cap up, no paint left in the air): the idle follows.
# Runs INSIDE Blender, after build_symbol_scene.py (tools/blender/run.py runs both in a background Blender).
import bpy, importlib, math, os, random, sys
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
import fxkit
importlib.reload(fxkit)
from fxkit import key, rest, px, vec, gp_object, gp_mat, gp_layer, stroke, ring, puff, Board, WHITE, GOLD

SID = "L1"
sc, arm, spec = fxkit.setup(SID)
FPS = sc.render.fps
GREEN = (0.02, 0.80, 0.01, 1)               # the paint (the can's green; linear)
DARK = (0.004, 0.26, 0.004, 1)              # its shade
PAINT_INK = (0.003, 0.02, 0.004, 1)           # its cartoon outline
LIGHT = (0.74, 1.0, 0.58, 1)                # wet highlights, the glow
SHINE = (0.93, 1.0, 0.88, 1)                # gloss on the paint
STICKER = (1.0, 1.0, 1.0, 1)               # the white sticker border round the spray
FLECK = (0.002, 0.10, 0.002, 1)             # spray-paint grain
NOZZLE = (441, 126)                          # the nozzle hole, on the cap's left face
CAP_FOOT = (498, 231)                        # the cap's bottom, on the stem: it squashes about this
BASE = (499, 958)                            # the middle of the can's base
TIP = (600, 958)                             # right of the middle of the base: the can tilts over about this

# ------------------------------------------------------------------ the rig: tip (new root), can on it, cap on the can
keep = {o.name: o.matrix_world.copy() for o in sc.objects if o.parent_type == "BONE"}
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
if "tip" not in eb:
    eb.new("tip")
for name, at, parent in (("tip", TIP, None), ("can", BASE, "tip"), ("cap", CAP_FOOT, "can")):
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

BONES = ["tip", "can", "cap"]
CLIPS = {"idle": (1, 80), "land": (101, 126), "hit": (201, 252), "multi": (301, 348)}
arm["clips"] = {k: list(v) for k, v in CLIPS.items()}


def can_keys(rows):
    """(frame, x, y, r, sx, sy) on the can's base (it sways, rattles and squashes about the middle of its base)."""
    for f, x, y, r, sx, sy in rows:
        key(arm, "can", f, x=x, y=y, r=r, sx=sx, sy=sy)


def tilt(rows):
    """(frame, degrees) on the tip: negative tips the can over to the right, the nozzle turning up to the left."""
    for f, r in rows:
        key(arm, "tip", f, r=r)


def press(rows):
    """The cap: (frame, squash) - pushed down onto the stem (y) and squashed (sy), a little wider (sx)."""
    for f, sy in rows:
        down = max(0.0, 1 - sy)
        key(arm, "cap", f, y=-down * .6 if sy < 1 else 0, sx=1 + (1 - sy) * .35, sy=sy)


# ================================================================== idle: calm - it sways, a glint, the ball rattles once
f0, f1 = CLIPS["idle"]
act = fxkit.begin_action(arm, SID + "_idle")
rest(arm, BONES, f0)
rest(arm, BONES, f1 + 1)
RATTLE, ROCK = 36, 58
# it sways on its base, the ball knocks inside (a hop and a shiver, the cap a beat behind), and later it rocks up
# onto the edge of its base and drops back with a little settle
can_keys([(14, 0, 0, 2.8, .994, 1.01), (28, 0, 0, -1.2, 1.0, 1.0), (RATTLE, 0, 0, 0, 1, 1),
          (RATTLE + 2, 0, .07, 2.2, .985, 1.025), (RATTLE + 4, 0, 0, -1.9, 1.025, .975), (RATTLE + 6, 0, .05, 1.5, .99, 1.015),
          (RATTLE + 8, 0, 0, -.9, 1.012, .988), (RATTLE + 10, 0, .015, .4, 1, 1), (RATTLE + 13, 0, 0, 0, 1, 1),
          (ROCK, 0, 0, 0, 1, 1), (ROCK + 9, 0, 0, 0, 1, 1), (ROCK + 10, 0, 0, 0, 1.03, .965), (ROCK + 13, 0, 0, .9, .995, 1.008),
          (ROCK + 17, 0, 0, -.4, 1, 1)])
fxkit.hard(act, "can", "scale", 0, ROCK + 10); fxkit.hard(act, "can", "scale", 1, ROCK + 10)
tilt([(ROCK, 0), (ROCK + 6, -4.2), (ROCK + 9, 0)])
fxkit.hard(act, "tip", "rotation_euler", 2, ROCK + 9)
key(arm, "cap", RATTLE + 3, y=0, sx=1, sy=1)
key(arm, "cap", RATTLE + 5, y=-.03, sx=1.02, sy=.95)              # the cap a beat behind: it chatters on its stem
key(arm, "cap", RATTLE + 7, y=0, sx=.99, sy=1.0)
key(arm, "cap", RATTLE + 9, y=-.015, sx=1.008, sy=.975)
key(arm, "cap", RATTLE + 12, y=0, sx=1, sy=1)
key(arm, "cap", ROCK + 10, y=0, sx=1, sy=1)
key(arm, "cap", ROCK + 12, y=-.02, sx=1.012, sy=.965)
key(arm, "cap", ROCK + 15, y=0, sx=1, sy=1)
fxkit.make_cyclic(act)
fxkit.end_action(arm, act, f0)

# ================================================================== land: thud, a little tip and a puff, back upright
f0, f1 = CLIPS["land"]
act = fxkit.begin_action(arm, SID + "_land")
rest(arm, BONES, f0)
LAND_ON, LAND_OFF, LAND_BACK = 110, 115, 119
can_keys([(103, 0, 0, 0, 1.08, .9), (106, 0, 0, 0, .97, 1.04), (109, 0, 0, 0, 1, 1),
          (LAND_BACK, 0, 0, 0, 1, 1), (LAND_BACK + 1, 0, 0, 0, 1.04, .955), (LAND_BACK + 3, 0, 0, 1.4, .99, 1.015),
          (LAND_BACK + 5, 0, 0, -.5, 1, 1), (f1, 0, 0, 0, 1, 1)])
fxkit.hard(act, "can", "scale", 0, 103); fxkit.hard(act, "can", "scale", 1, 103)
tilt([(106, 0), (LAND_ON, -11.0), (LAND_OFF, -12.0), (LAND_BACK, 0), (f1, 0)])
fxkit.hard(act, "tip", "rotation_euler", 2, LAND_BACK)
press([(LAND_ON - 1, 1), (LAND_ON, .88), (LAND_OFF - 1, .9), (LAND_OFF + 1, 1.03), (LAND_OFF + 4, 1), (f1, 1)])
fxkit.hard(act, "cap", "scale", 1, LAND_ON)
fxkit.end_action(arm, act, f0)

# ================================================================== hit: crouch, tip over, slam the cap - a strong burst
f0, f1 = CLIPS["hit"]
act = fxkit.begin_action(arm, SID + "_hit")
rest(arm, BONES, f0)
HIT_ON, HIT_OFF, HIT_BACK = 210, 233, 240
rows = [(205, 0, 0, 3.0, 1.03, .955), (HIT_ON, 0, 0, 0, 1.0, 1.0)]
for k, f in enumerate(range(HIT_ON + 2, HIT_OFF, 2)):              # the thrust rumbles it
    e = 1 - .5 * (f - HIT_ON) / (HIT_OFF - HIT_ON)
    rows.append((f, .025 * e * (1 if k % 2 else -1), 0, .7 * e * (-1 if k % 2 else 1), 1, 1))
rows += [(HIT_OFF, 0, 0, 0, 1, 1), (HIT_BACK, 0, 0, 0, 1, 1), (HIT_BACK + 1, 0, 0, 0, 1.05, .93), (HIT_BACK + 3, 0, 0, 3.0, .98, 1.03),
         (HIT_BACK + 6, 0, 0, -1.4, 1, 1), (HIT_BACK + 9, 0, 0, .5, 1, 1), (f1, 0, 0, 0, 1, 1)]
can_keys(rows)
tilt([(205, 0), (HIT_ON, -19.5), (HIT_ON + 3, -14.5), (HIT_ON + 6, -16.4), (HIT_OFF, -15.8), (HIT_BACK, 0), (f1, 0)])
fxkit.hard(act, "tip", "rotation_euler", 2, HIT_BACK)
press([(HIT_ON - 2, 1), (HIT_ON, .84), (HIT_OFF - 1, .86), (HIT_OFF + 1, 1.06), (HIT_OFF + 4, .98), (HIT_BACK + 1, 1), (f1, 1)])
fxkit.hard(act, "cap", "scale", 1, HIT_ON)
fxkit.end_action(arm, act, f0)

# ================================================================== multi: shaken (the ball rattles), then one big burst
f0, f1 = CLIPS["multi"]
act = fxkit.begin_action(arm, SID + "_multi")
rest(arm, BONES, f0)
SHAKE, MUL_ON, MUL_OFF, MUL_BACK = (303, 315), 321, 335, 341
rows, k, f = [], 0, SHAKE[0]
while f <= SHAKE[1]:
    e = (f - SHAKE[0]) / (SHAKE[1] - SHAKE[0])
    up = k % 2 == 0
    rows.append((f, 0, (.07 + .1 * e) * (1 if up else -.35), (1 + 1.6 * e) * (1 if up else -1),
                 .98 if up else 1.03, 1.03 if up else .96))
    f += 2; k += 1
can_keys(rows + [(SHAKE[1] + 2, 0, 0, 0, 1, 1), (MUL_ON, 0, 0, 0, 1, 1), (MUL_ON + 2, -.03, 0, -.8, 1, 1), (MUL_ON + 4, .03, 0, .8, 1, 1),
                 (MUL_ON + 7, -.02, 0, -.5, 1, 1), (MUL_ON + 10, .02, 0, .4, 1, 1), (MUL_OFF, 0, 0, 0, 1, 1),
                 (MUL_BACK, 0, 0, 0, 1, 1), (MUL_BACK + 1, 0, 0, 0, 1.05, .93), (MUL_BACK + 3, 0, 0, 2.8, .985, 1.025),
                 (MUL_BACK + 5, 0, 0, -1.0, 1, 1), (f1, 0, 0, 0, 1, 1)])
tilt([(SHAKE[1] + 2, 0), (MUL_ON, -20.0), (MUL_ON + 3, -15.0), (MUL_ON + 6, -16.8), (MUL_OFF, -16.2), (MUL_BACK, 0), (f1, 0)])
fxkit.hard(act, "tip", "rotation_euler", 2, MUL_BACK)
press([(SHAKE[0] + 4, 1), (SHAKE[0] + 6, .97), (SHAKE[0] + 8, 1), (MUL_ON - 2, 1), (MUL_ON, .83), (MUL_OFF - 1, .85),
       (MUL_OFF + 1, 1.06), (MUL_OFF + 4, .985), (MUL_BACK + 1, 1), (f1, 1)])
fxkit.hard(act, "cap", "scale", 1, MUL_ON)
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
mp = dict(puff=gp_mat(paint, "paint_puff", PAINT_INK, fill=DARK), body=gp_mat(paint, "paint_body", PAINT_INK, fill=GREEN),
          ink=gp_mat(paint, "paint_ink", PAINT_INK), shine=gp_mat(paint, "paint_shine", SHINE, fill=SHINE),
          speck=gp_mat(paint, "paint_speck", GREEN, fill=GREEN), drop=gp_mat(paint, "paint_drop", PAINT_INK, fill=GREEN),
          dust=gp_mat(paint, "fx_dust", (.6, .58, .62, 1), fill=(.96, .95, .97, 1)),
          border=gp_mat(paint, "paint_border", STICKER, fill=STICKER), inkf=gp_mat(paint, "paint_inkfill", PAINT_INK, fill=PAINT_INK),
          dark=gp_mat(paint, "paint_dark", DARK, fill=DARK), fleck=gp_mat(paint, "paint_fleck", FLECK, fill=FLECK))
world, behind, air = Board(), Board(), Board()
ALL = sorted({f for a, b in CLIPS.values() for f in range(a - 1, b + 3)})


def mats(f, bones):
    sc.frame_set(f)
    out = {}
    for b in bones:
        pb = arm.pose.bones[b]
        out[b] = arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted()
    return out


M = {f: mats(f, ("can", "cap")) for f in ALL}
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


def nozzle(f):
    """Where the nozzle is at frame f and which way it points (the cap's own left, unit vector), world (x, z)."""
    Mc = M[f]["cap"]
    p = Mc @ vec(*NOZZLE)
    d = (Mc.to_3x3() @ Vector((-1, 0, 0))).normalized()
    return (p.x, p.z), (d.x, d.z)


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 2.2


def clamp_in(x, z, r, lim=6.15):
    """Keep a round shape of radius r inside the 13-unit frame (a sprite is clipped at its edge)."""
    return max(-lim + r, min(lim - r, x)), max(-lim + r, min(lim - r, z))


def dot(board, f, x, z, r, mat):
    if r > .006:
        board.add(f, lambda dr, x=x, z=z, r=r: stroke(dr, ring(x, z, r, n=12), .004, mat=mat, cyclic=True, fill=True, line=False))


BW, IW = .2, .1                            # the spray's white sticker border and its ink line (units), as the art's
# the cloud, drawn like the original art's: lumps (u along the jet, v across it, r - in units of the cloud's radius R)
# whose union is one scalloped silhouette, inked and bordered all round, curls of ink inside, a wet gloss up on the left
CLOUD = [(0.0, 0.0, .56), (-.18, .34, .42), (.1, -.38, .45), (.32, .14, .44)]          # its heart
for _k in range(12):                                                                  # and its scalloped rim
    _a = math.radians(_k * 30)
    _d, _r = (.5, .3) if _k == 6 else (.73, .35 + .06 * ((_k * 7) % 3) / 2)           # (k 6 faces the jet: it enters there)
    CLOUD.append((math.cos(_a) * _d, math.sin(_a) * _d * 1.12, _r))
CURLS = [0, 2, 3, 9, 13]                                                              # lumps with an ink curl round their lower left


def spray(on_f, off_f, L=2.2, W=.55, R=1.9, seed=0, grow=3, tail=4, linger=10):
    """One spray, drawn like the original art's: a cone of paint from the nozzle, thin at the nozzle and widening into a
    big round cloud of paint lumps - one inked silhouette with the white sticker border round jet and cloud, curls of
    ink inside, a wet gloss, spray-paint specks. The cap is held from on_f to off_f: the jet shoots out over `grow`
    frames, the cloud billows out from where it ends (its lumps pop out from the jet's end outward) and boils; the jet
    rides the nozzle while the can rumbles and always ends in the cloud. Let go at off_f: the jet's tail leaves the
    nozzle and runs into the cloud over `tail` frames; the cloud drifts off and its lumps shrink away (staggered,
    the last gone `linger` frames after the tail). Returns the cloud's middle and the jet's direction (world)."""
    rnd = random.Random(seed)
    (nx0, nz0), (dx0, dz0) = nozzle(on_f + 5)                          # the settled tilt: the jet's end is fixed in the air
    A = (nx0 + dx0 * L, nz0 + dz0 * L)
    e1 = (dx0, dz0); e2 = (-dz0, dx0) if dx0 >= 0 else (dz0, -dx0)       # e2: across the jet, pointing up
    C = [A[0] + e1[0] * R * .68, A[1] + e1[1] * R * .68]
    # fit the full-grown cloud inside the frame (nothing clips at the sprite's edge): move its middle in if need be
    lim = 6.2
    for _ in range(3):
        for u, v, r in CLOUD:
            x = C[0] + (e1[0] * u + e2[0] * v) * R; z = C[1] + (e1[1] * u + e2[1] * v) * R
            rr = r * R * 1.1 + IW + BW
            C[0] += min(0.0, lim - (x + rr)) + max(0.0, -lim - (x - rr))
            C[1] += min(0.0, lim - (z + rr)) + max(0.0, -lim - (z - rr))
    lumps = []
    for i, (u, v, r) in enumerate(CLOUD):
        d = math.hypot(u + .5, v) / 1.6                                  # how far from where the jet comes in
        lumps.append(dict(u=u, v=v, r=r, i=i, born=on_f + grow - 1 + int(round(d * 7)) + rnd.randint(0, 1),
                          die=off_f + tail + int(linger * (.8 + .2 * rnd.random())), ph=rnd.uniform(0, 6.3),
                          fl=[(rnd.uniform(0, 6.3), rnd.uniform(.1, .7), rnd.uniform(.014, .028)) for _ in range(4)]))
    last = max(p["die"] for p in lumps)
    grown = on_f + grow - 1

    for f in range(on_f, last + 1):
        border, ink, dark, green, top = [], [], [], [], []              # drawn in that order: one silhouette
        # ---- the cloud
        g_all = ease((f - grown) / 10) if f >= grown else 0.0
        off = max(0, f - off_f)
        cx = C[0] + e1[0] * R * .3 * ease(off / 14)
        cz = C[1] + e1[1] * R * .3 * ease(off / 14) + .35 * ease(off / 14)
        Rf = R * (.55 + .45 * g_all)
        if f > off_f:                                                   # let go: the whole cloud shrinks away as one
            Rf *= 1 - min(1.0, (f - off_f) / max(1, last - off_f)) ** 1.3
        for p in lumps:
            if f < p["born"]:
                continue
            a = (f - p["born"]) / 5
            s = 1.08 * math.sin(min(1.0, a) * math.pi / 2) if a < 1 else 1.08 - .08 * min(1.0, (a - 1) * 1.5)
            s *= 1 + .04 * math.sin((f // 2) * 1.9 + p["ph"])          # it boils, on twos
            r = p["r"] * Rf * s
            if r < .04:
                continue
            x = cx + (e1[0] * p["u"] + e2[0] * p["v"]) * Rf
            z = cz + (e1[1] * p["u"] + e2[1] * p["v"]) * Rf
            x, z = clamp_in(x, z, r + IW + BW, 6.25)
            k = max(.35, min(1.0, r / .5))                              # small lumps: thinner lines
            border.append(ring(x, z, r + (IW + BW) * k, n=40))
            ink.append(ring(x, z, r + IW * k, n=40))
            dark.append(ring(x, z, r, n=40))
            green.append(ring(x - .13 * r, z + .12 * r, r * .86, n=40))
            if p["i"] in CURLS and r > .2:                              # a curl of ink round its lower left
                arc = [(x + math.cos(t) * r * .97, z + math.sin(t) * r * .97) for t in
                       (math.radians(180 + 95 * j / 9) for j in range(10))]
                top.append(("curl", arc, .05 * k))
            if p["i"] in (1, 5, 6, 7) and r > .2:                     # a wet gloss on the top lumps (the light is up left)
                gl = [(x + math.cos(t) * r * .62, z + math.sin(t) * r * .58) for t in (math.radians(112 + 38 * j / 5) for j in range(6))]
                top.append(("streak", gl, .07 * k))
                top.append(("blob", (x - .05 * r, z + .66 * r, .06 * r)))
            for t, rr, sz in p["fl"]:                                   # spray-paint grain
                top.append(("fleck", (x + math.cos(t) * rr * r, z + math.sin(t) * rr * r, sz * k)))
        # ---- the jet: a cone from the nozzle to the cloud
        if f <= off_f:
            (px0, pz0), _ = nozzle(f)
            s0f = 0.0
        else:
            (px0, pz0), _ = nozzle(off_f)
            s0f = ease((f - off_f) / tail)
        jl = math.hypot(A[0] - px0, A[1] - pz0)
        ux, uz = (A[0] - px0) / jl, (A[1] - pz0) / jl
        head = jl * (ease((f - on_f + 1) / grow) if f <= off_f else 1.0)
        s0 = jl * s0f
        if head - s0 > .05 and s0f < .97:
            n = 16
            ss = [s0 + (head - s0) * j / (n - 1) for j in range(n)]
            flick = 1 + .05 * math.sin(f * 2.1)

            def side(extra, sgn):
                out = []
                for s in ss:
                    t = s / jl
                    hw = (.035 + (W - .035) * t) * flick
                    if s0 > 0:
                        hw *= min(1.0, (s - s0) / .5) ** .55                # a let-go tail: rounded off to a point
                    e = extra(t) if s - s0 > .06 or s0 == 0 else 0.0
                    out.append((px0 + ux * s - uz * (hw + e) * sgn, pz0 + uz * s + ux * (hw + e) * sgn))
                return out
            poly = lambda extra: side(extra, 1) + side(extra, -1)[::-1]
            border.insert(0, poly(lambda t: (.02 + .055 * t) + BW * fxkit.smooth(.25, .6, t)))
            ink.insert(0, poly(lambda t: .02 + .055 * t))
            green.insert(0, poly(lambda t: 0.0))
            hi = side(lambda t: 0.0, 1)[2:n // 2 + 1]                       # a streak of gloss along its upper edge
            hi = [(x - (x - (px0 + ux * s)) * .45, z - (z - (pz0 + uz * s)) * .45) for (x, z), s in zip(hi, ss[2:n // 2 + 1])]
            top.append(("streak", hi, .03))
            if f < on_f + grow + 9 and f <= off_f:                       # the paint's front as it shoots out: round, inked
                hx, hz = px0 + ux * head, pz0 + uz * head
                hr = (.035 + (W - .035) * head / jl) * 1.1
                border.append(ring(hx, hz, hr + .075 + BW * min(1.0, head / jl * 2), n=28))
                ink.append(ring(hx, hz, hr + .075, n=28))
                green.append(ring(hx - .08 * hr, hz + .08 * hr, hr, n=28))
            r2 = random.Random(seed * 997 + f // 2)                       # specks of paint misting off it, in its border
            for j in range(10 if f <= off_f else 4):
                s = r2.uniform(max(s0, .35 * jl), head)
                t = s / jl
                hw = .035 + (W - .035) * t
                sg = r2.choice((-1, 1))
                o = hw + .08 + r2.uniform(.02, .2) * (.4 + t)
                top.append(("speck", (px0 + ux * s - uz * o * sg, pz0 + uz * s + ux * o * sg, r2.uniform(.016, .032))))
            for j in range(5):                                            # grain inside it
                s = r2.uniform(max(s0, .3 * jl), head); t = s / jl
                o = (.035 + (W - .035) * t) * r2.uniform(-.7, .7)
                top.append(("fleck", (px0 + ux * s - uz * o, pz0 + uz * s + ux * o, r2.uniform(.012, .022))))
        for pts in border:
            air.add(f, lambda dr, pts=pts: stroke(dr, pts, .004, mat=mp["border"], cyclic=True, fill=True, line=False))
        for pts in ink:
            air.add(f, lambda dr, pts=pts: stroke(dr, pts, .004, mat=mp["inkf"], cyclic=True, fill=True, line=False))
        for pts in dark:
            air.add(f, lambda dr, pts=pts: stroke(dr, pts, .004, mat=mp["dark"], cyclic=True, fill=True, line=False))
        for pts in green:
            air.add(f, lambda dr, pts=pts: stroke(dr, pts, .004, mat=mp["body"], cyclic=True, fill=True, line=False))
        for kind, a, *rest in top:
            if kind == "curl":
                air.add(f, lambda dr, a=a, w=rest[0]: stroke(dr, a, w, mat=mp["ink"], radii=fxkit.taper(len(a), w, .4)))
            elif kind == "streak" and len(a) > 1:
                air.add(f, lambda dr, a=a, w=rest[0]: stroke(dr, a, w, mat=mp["shine"], radii=fxkit.taper(len(a), w, .4)))
            elif kind == "blob":
                air.add(f, lambda dr, a=a: stroke(dr, ring(a[0], a[1], a[2], n=14), .004, mat=mp["shine"], cyclic=True, fill=True, line=False))
            elif kind == "fleck":
                air.add(f, lambda dr, a=a: stroke(dr, ring(a[0], a[1], a[2], n=8), .004, mat=mp["fleck"], cyclic=True, fill=True, line=False))
            elif kind == "speck":
                air.add(f, lambda dr, a=a: stroke(dr, ring(a[0], a[1], a[2], n=8), .004, mat=mp["speck"], cyclic=True, fill=True, line=False))
    return (C[0], C[1]), e1


def fling(f0, n, seed, x, z, spread=(0, 360), speed=(3, 6), size=(.04, .09), life=12, grav=6.0):
    """Paint droplets flung out: they fly, fall and shrink away."""
    rnd = random.Random(seed)
    for i in range(n):
        a = math.radians(rnd.uniform(*spread)); sp = rnd.uniform(*speed); r0 = rnd.uniform(*size)
        for k in range(life):
            t = k / FPS; u = k / (life - 1)
            r = r0 * (1 - u ** 1.6)
            xx, zz = clamp_in(x + math.cos(a) * sp * t, z + math.sin(a) * sp * t - grav * t * t, r)
            if r > .006:
                air.add(f0 + k, lambda dr, xx=xx, zz=zz, r=r: stroke(dr, ring(xx, zz, r, n=14), .022, mat=mp["drop"], cyclic=True, fill=True))


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


def rattle_marks(f, side, scale=1.0, idle=False):
    """Two little curved marks beside the body as the ball knocks inside (on the side it is thrown to)."""
    cx, cz = on("can", f, (499, 600))
    for j in range(2):
        ox = side * (2.5 + .3 * j) * scale ** .3
        pts = [(cx + ox - side * .14 * (1 - s * s), cz + .12 * j + s * .42 * scale * (1 - .2 * j)) for s in (-1, -.5, 0, .5, 1)]
        world.add(wrap(f) if idle else f, lambda dr, pts=pts: stroke(dr, pts, .045, mat=m["white"],
                                                                     radii=fxkit.taper(len(pts), .05, .35)), hold=2)


def press_flash(f):
    """A pop of light at the nozzle as the cap goes down."""
    (x, z), (dx, dz) = nozzle(f)
    fxkit.sparkle(world, f, 6, x + dx * .15, z + dz * .15, .42, m["white_f"], rot0=.4)


# ---- idle: a glint slides down the glossy body, the cap's rim twinkles, the ball rattles (no paint)
for k in range(12):                                                     # the glint, riding the can as it sways
    f = 8 + k
    t = k / 11
    x, z = on("can", f, (352, 430 + 360 * t))
    rr = .34 * math.sin(math.pi * t) ** .8
    if rr > .02:
        world.add(f, lambda dr, x=x, z=z, rr=rr, t=t: stroke(dr, fxkit.star(x, z, rr, .3 + .6 * t), .004, mat=m["white_f"],
                                                              cyclic=True, fill=True, line=False))
fxkit.sparkle(world, 24, 10, *on("can", 24, (338, 318)), .3, m["white_f"], rot0=.6)         # the collar catches the light
fxkit.sparkle(world, 72, 9, *on("cap", 72, (402, 76)), .3, m["white_f"], rot0=1.0)         # and the cap's rim
for k, f in enumerate(range(RATTLE + 2, RATTLE + 9, 2)):
    rattle_marks(f, 1 if k % 2 == 0 else -1, scale=.8, idle=True)

# ---- land: dust from the base, a short tip and a quick puff, dust again as it drops back
bx, bz = px(*BASE)
ticks(world, 103, bx, bz - .1, (m["white"], m["light"], m["white"]), seed=3)
for side, sd in ((-1, 3), (1, 7)):
    fxkit.dust(air, 103, 11, bx + side * 1.9, bz - .1, .42, mp["dust"], drift=(side * 1.0, .25), seed=sd)
press_flash(LAND_ON)
spray(LAND_ON, LAND_OFF, L=1.5, W=.32, R=1.0, seed=11, grow=2, tail=3, linger=5)
lx, lz = px(300, 960)
fxkit.dust(air, LAND_BACK, 6, lx - .2, lz - .05, .3, mp["dust"], drift=(-.7, .15), seed=17)

# ---- hit: the burst - a long jet, a big boiling cloud, droplets, sparkles, the can rumbling
press_flash(HIT_ON)
(cx, cz), (tx, tz) = spray(HIT_ON, HIT_OFF, L=2.1, W=.55, R=1.95, seed=21, grow=3, tail=4, linger=10)
fling(HIT_ON + 6, 10, seed=5, x=cx, z=cz, spread=(70, 250), speed=(3.5, 6.5), size=(.045, .09), life=13, grav=6)
fling(HIT_ON + 14, 8, seed=6, x=cx, z=cz, spread=(80, 240), speed=(3, 5.5), size=(.04, .08), life=12, grav=6)
for k, f in enumerate(range(HIT_ON + 1, HIT_ON + 7)):                    # thrust lines off the can's right side
    t = k / 5
    for j in range(3):
        x0, z0 = on("can", f, (725, 470 + 110 * j))
        world.add(f, lambda dr, x0=x0, z0=z0, t=t: stroke(dr, [(x0 + .15 + .4 * t, z0 - .05 * t), (x0 + .75 + .8 * t, z0 - .2 - .1 * t)],
                                                         .03 * (1 - t) + .006, mat=m["white"]))
rnd = random.Random(8)
for i in range(7):
    fxkit.sparkle(world, HIT_ON + 8 + rnd.randint(0, 16), rnd.randint(7, 10), cx + rnd.uniform(-2.2, 1.6), cz + rnd.uniform(-1.6, 1.2),
                  rnd.uniform(.2, .36), m["white_f"] if i % 3 else m["gold_f"], rot0=rnd.uniform(0, 1))
lx, lz = px(300, 960)
fxkit.dust(air, HIT_BACK, 10, lx - .2, lz - .05, .38, mp["dust"], drift=(-.9, .2), seed=23)
ticks(world, HIT_BACK, *px(330, 965), (m["white"], m["light"], m["white"]), a0=100, a1=175, n=3, seed=9)

# ---- multi: shaken - rattle marks, pulses of light; then the big burst with rings of light and streaks
for k, f in enumerate(range(SHAKE[0] + 1, SHAKE[1] + 1, 2)):
    rattle_marks(f, 1 if k % 2 else -1, scale=1.0 + .25 * k / 6)
for p in (SHAKE[0] + 2, SHAKE[0] + 7, SHAKE[1]):                          # it glows with each knock
    ox, oz = on("can", p, (499, 520))
    rings_out(behind, p, ox, oz, 2.4, 3.4, (mb["green"], mb["light"]), life=7, lag=2, width=.09)
press_flash(MUL_ON)
(cx, cz), (tx, tz) = spray(MUL_ON, MUL_OFF, L=2.2, W=.6, R=2.15, seed=31, grow=3, tail=4, linger=7)
cx, cz = clamp_in(cx, cz, 1.2)
rings_out(behind, MUL_ON + 2, cx, cz, 1.0, 2.4, (mb["green"], mb["white"], mb["light"]), life=10, lag=3, width=.12)
rings_out(behind, MUL_ON + 4, *on("can", MUL_ON + 4, (499, 520)), 2.4, 4.5, (mb["light"], mb["white"]), life=10, lag=3, width=.1)
fxkit.streaks(world, MUL_ON + 2, 8, cx, cz, 1.3, 2.7, (m["white"], m["light"]), n=14, rot=.2)
fling(MUL_ON + 5, 14, seed=12, x=cx, z=cz, spread=(0, 360), speed=(4, 7), size=(.045, .09), life=11, grav=5)
rnd = random.Random(31)
for i in range(7):
    fxkit.sparkle(world, MUL_ON + 4 + rnd.randint(0, 9), rnd.randint(7, 8), rnd.uniform(-4.6, 4.6), rnd.uniform(-3.8, 4.8),
                  rnd.uniform(.2, .36), m["white_f"] if i % 2 else m["gold_f"], rot0=rnd.uniform(0, 1))
fxkit.dust(air, MUL_BACK, 6, *(lambda p: (p[0] - .2, p[1] - .05))(px(300, 960)), .34, mp["dust"], drift=(-.8, .2), seed=33)

world.draw(gp_layer(fx, "fx"))
behind.draw(gp_layer(glow, "burst"))
air.draw(gp_layer(paint, "paint"))

# nothing a one-shot draws may still be on screen on its last frame (the idle follows straight on)
for name, (a, b) in CLIPS.items():
    if name == "idle":
        continue
    left = [f for brd in (world, behind, air) for f in brd.frames if b - 1 <= f <= b]
    if left:
        print(f"  WARNING {name}: effects still drawn on frames {sorted(set(left))}")

sc.frame_start, sc.frame_end = 1, max(b for a, b in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], "| saved", fxkit.save(SID))
