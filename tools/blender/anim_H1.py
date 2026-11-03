# H1 - the bag of cash - animated in Blender: four Actions on its rig (idle, land, hit, multi) laid one after
# another on the rig's NLA track, and its effects drawn frame by frame in Grease Pencil on the same timeline.
#   the bag     keyed by hand: it breathes and sways (idle), thuds down (land), crouches, leaps and crashes back
#               (hit), swells with the multiplier's charge in three pulses and lets it go (multi)
#   the ropes   the two loose rope ends and the gathered top follow the bag: worked out in Blender from how the keys
#               move the tie (each rope its own weight and spring, so they swing separately - the upper one quick
#               and light, the lower one slow and heavy), then keyed onto their bones sparsely, like hand keys
#   the glow    tier 1 neon (fxkit.neon): violet light behind the sticker, lime comets running round its edge,
#               lime flooding in on a land, a hit and a multiplier
#   effects     glints, impact ticks, speed lines, sparks out of the mouth, a starburst, lightning, charge rings,
#               dust puffs and $ notes thrown out of the mouth
# Runs INSIDE Blender, after build_symbol_scene.py (tools/blender/run.py runs both in a background Blender).
import bpy, importlib, math, os, random, sys
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
import fxkit
importlib.reload(fxkit)
from fxkit import (key, rest, px, smooth, gp_object, gp_mat, gp_layer, ride, stroke, star, puff, Board,
                   LIME, VIOLET, WHITE, GOLD)

SID = "H1"
sc, arm, spec = fxkit.setup(SID)
FPS = sc.render.fps
ART, FXB, FX = fxkit.layers(sc, SID)
fxkit.glow_compositor(sc, SID, back=dict(strength=1.0, size=.55, gain=1.6), front=dict(strength=.85, size=.4, gain=1.5))
if arm.animation_data:
    arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)

RIGID = ["body", "band", "top", "dollar"]
ROPE_BONES = [f"{r}.{i}" for r in ("rope_up", "rope_lo") for i in range(3)]
# what hangs off the tie: the chains in icon px (root first), their stiffness (Hz, softer toward the tip) and
# damping. The upper rope is shorter and springier; the lower one heavier, slower and swings wider.
HANGING = {
    "rope_up": dict(chain=[(364, 362), (290, 354), (218, 353), (132, 372)], freq=[3.4, 2.8, 2.3], zeta=.22, gain=.6, limit=14),
    "rope_lo": dict(chain=[(348, 391), (290, 413), (234, 466), (138, 490)], freq=[2.9, 2.3, 1.9], zeta=.18, gain=.7, limit=16),
    "top": dict(chain=[(512, 330), (512, 110)], freq=[2.6], zeta=.28, stretch=True, gain=.5, limit=6, stretch_limit=.1),
}
CLIPS = {"idle": (1, 72), "land": (101, 124), "hit": (201, 246), "multi": (301, 342)}
arm["clips"] = {k: list(v) for k, v in CLIPS.items()}


def follow(f0, f1, loop=False, forces=None, gain=1.0):
    """The ropes and the top, worked out from how this clip moves the tie, keyed onto their bones."""
    res = fxkit.secondary(sc, arm, "band", f0, f1, HANGING, loop=loop, forces=forces, gain=gain)
    print(f"  {f0}-{f1}:", ", ".join(f"{b} {min(v):+.1f}..{max(v):+.1f}" for b, v in res.items()))
    for bone, vals in res.items():
        if bone.endswith(":sy"):
            b = bone[:-3]
            fxkit.key_series(arm, b, f0, vals, channel="sy", tol=.004, loop=loop)
            fxkit.key_series(arm, b, f0, [1 / math.sqrt(max(.5, v)) for v in vals], channel="sx", tol=.004, loop=loop)
        else:
            fxkit.key_series(arm, bone, f0, vals, channel="r", tol=.25, loop=loop)
    return res


# ================================================================== idle: breathes, sways; the ropes stir
f0, f1 = CLIPS["idle"]
act = fxkit.begin_action(arm, SID + "_idle")
rest(arm, RIGID + ROPE_BONES, f0)
key(arm, "body", 37, sx=.988, sy=1.024); key(arm, "body", 73, sx=1, sy=1)
key(arm, "body", 19, r=.45); key(arm, "body", 55, r=-.45); key(arm, "body", 73, r=0)
for f, s in ((41, 1), (46, 1.035), (53, 1), (73, 1)):
    key(arm, "dollar", f, s=s)


def breeze(name, i, t):
    T = 2.4                                         # the loop: every stir repeats exactly
    if name == "top":
        return Vector((5 * math.sin(2 * math.pi * t / T + 1.0), 0, 0))
    if name == "rope_up":
        a = 30 * math.sin(2 * math.pi * t / T)
    else:
        a = 34 * math.sin(2 * math.pi * t / T + 2.0) + 9 * math.sin(2 * math.pi * t / (T / 3) + 1.0)
    return Vector((0, 0, a * (i / 3) ** .8))


follow(f0, f1, loop=True, forces=breeze)
fxkit.make_cyclic(act)
fxkit.end_action(arm, act, f0)

# ================================================================== land: a heavy thud
f0, f1 = CLIPS["land"]
act = fxkit.begin_action(arm, SID + "_land")
rest(arm, RIGID + ROPE_BONES, f0)
for f, sx, sy, y in ((103, 1.12, .86, 0), (106, .95, 1.06, .05), (110, 1.025, .98, 0), (114, .995, 1.006, 0), (119, 1, 1, 0), (124, 1, 1, 0)):
    key(arm, "body", f, sx=sx, sy=sy, y=y)
for f, s in ((103, .95), (106, 1.06), (110, 1), (124, 1)):
    key(arm, "dollar", f, s=s)
follow(f0, f1, gain=.45)
fxkit.end_action(arm, act, f0)

# ================================================================== hit: crouch, leap, hang, crash, bounce
f0, f1 = CLIPS["hit"]
act = fxkit.begin_action(arm, SID + "_hit")
rest(arm, RIGID + ROPE_BONES, f0)
for f, sx, sy, y, r in ((205, 1.12, .86, 0, 0), (209, .90, 1.14, .45, -3), (214, .97, 1.05, 1.18, 2), (218, 1, 1, 1.3, 4),
                        (222, .96, 1.06, .75, 2), (226, 1.15, .82, 0, 0), (230, .95, 1.07, .06, -1), (235, 1.02, .985, 0, 0),
                        (240, 1, 1, 0, 0), (246, 1, 1, 0, 0)):
    key(arm, "body", f, sx=sx, sy=sy, y=y, r=r)
fxkit.hard(act, "body", "location", 1, 226)          # it hits the ground at full speed
for f, s, r in ((210, 1.18, -6), (218, 1.08, 4), (226, .94, 0), (232, 1.04, 0), (240, 1, 0), (246, 1, 0)):
    key(arm, "dollar", f, s=s, r=r)
follow(f0, f1, gain=.5)
fxkit.end_action(arm, act, f0)

# ================================================================== multi: the charge, in three pulses, then let go
f0, f1 = CLIPS["multi"]
act = fxkit.begin_action(arm, SID + "_multi")
rest(arm, RIGID + ROPE_BONES, f0)
for f, sx, sy in ((305, 1.06, .92), (310, 1.10, 1.10), (313, 1.06, 1.06), (317, 1.12, 1.12), (320, 1.07, 1.07),
                  (324, 1.14, 1.14), (328, .96, 1.04), (332, 1.02, .98), (336, 1, 1), (342, 1, 1)):
    key(arm, "body", f, sx=sx, sy=sy)
for i, f in enumerate(range(308, 327, 2)):          # the current makes it tremble
    key(arm, "body", f, r=.9 if i % 2 else -.9, x=.03 if i % 2 else -.03)
key(arm, "body", 328, r=0, x=0); key(arm, "body", 342, r=0, x=0)
for f, s in ((310, 1.12), (313, 1.05), (317, 1.15), (320, 1.06), (324, 1.2), (328, .96), (333, 1.02), (342, 1)):
    key(arm, "dollar", f, s=s)


def charge(name, i, t):
    f = f0 + t * FPS
    env = smooth(306, 312, f) * (1 - smooth(324, 329, f))
    if env <= 0:
        return Vector((0, 0, 0))
    rnd = random.Random(int(f) * 31 + i * 7 + (0 if name == "rope_up" else 101 if name == "rope_lo" else 211))
    jolt = Vector(((rnd.random() - .5) * 2, 0, (rnd.random() - .5) * 2)) * 60 * env
    if name == "top":
        return jolt * .5
    return Vector((0, 0, 140 * env * (i / 3) ** .6)) + jolt     # charged, the ends lift and stand out


follow(f0, f1, forces=charge, gain=.6)
fxkit.end_action(arm, act, f0)

# ================================================================== the tier glow, behind the sack
fxkit.neon(SID, arm, FXB, CLIPS, tier=1, land_at=103, hit_span=(205, 240), pulses=(310, 317, 324), charge_span=(306, 326))

# behind the sack: the hit's starburst at the top of the leap, the multi's charge rings as it lets go
back = gp_object(FXB, SID + "_back", depth=.35)
ride(back, arm, "body")
b_lime = gp_mat(back, "glow_lime_fill", LIME, fill=LIME)
b_white = gp_mat(back, "glow_white_fill", WHITE, fill=WHITE)
b_violet = gp_mat(back, "glow_violet", VIOLET)
b_lime_line = gp_mat(back, "glow_lime", LIME)
bb = Board()
CX, CZ = 0.1, 0.3                                    # the sack's middle
fxkit.starburst(bb, 211, 11, CX, CZ, 3.4, 7.0, b_lime, b_white)
fxkit.shock_rings(bb, 326, CX, CZ - .2, 4.6, 6.6, (b_violet, b_lime_line))
bb.draw(gp_layer(back, "burst"))

# ================================================================== effects over the art
fxw = gp_object(FX, SID + "_fx", depth=-.8)          # stays where the frame is
fxb = gp_object(FX, SID + "_fx_on", depth=-.8)       # rides the sack
ride(fxb, arm, "body")
w_white = gp_mat(fxw, "fx_white_line", WHITE); w_lime = gp_mat(fxw, "fx_lime_line", LIME)
w_spark = gp_mat(fxw, "fx_white_fill", WHITE, fill=WHITE); w_gold = gp_mat(fxw, "fx_gold_fill", GOLD, fill=GOLD)
o_spark = gp_mat(fxb, "fx_white_fill", WHITE, fill=WHITE); o_lime = gp_mat(fxb, "fx_lime_fill", LIME, fill=LIME)
o_white = gp_mat(fxb, "fx_white_line", WHITE); o_limel = gp_mat(fxb, "fx_lime_line", LIME)
world, onbag = Board(), Board()

# idle: the $ catches the light, and the top's tip
fxkit.sparkle(onbag, 44, 9, *px(585, 535), .42, o_spark)
fxkit.sparkle(onbag, 12, 7, *px(215, 80), .3, o_spark, rot0=.4)
# land: impact ticks at the base
for k, f in enumerate(range(102, 108)):
    t = k / 5
    for side in (-1, 1):
        world.add(f, lambda dr, s=side, t=t: stroke(dr, [(s * (2.3 + 1.7 * t), -4.3), (s * (3.1 + 2.5 * t), -4.12 + .12 * t)],
                                                   .035 * (1 - t) + .008, mat=w_lime))
# hit: speed lines under the leap, sparks spat from the mouth, sparkles all round
for k, f in enumerate(range(207, 214)):
    for j, x in enumerate((-1.7, -.6, .5, 1.6)):
        world.add(f, lambda dr, x=x, k=k, j=j: stroke(dr, [(x + .06 * j, -4.7 + .4 * k), (x + .06 * j, -5.8 + .4 * k)], .028,
                                                     opacity=.85 - .1 * k, mat=w_white))
MOUTH = px(512, 150)
rnd = random.Random(5)
for i in range(10):
    a = math.radians(rnd.uniform(25, 155))
    sp = rnd.uniform(3.5, 5.5)
    for k, f in enumerate(range(213, 221)):
        t = k / 7
        x0, z0 = MOUTH[0] + math.cos(a) * sp * t * .55, MOUTH[1] + math.sin(a) * sp * t * .55
        onbag.add(f, lambda dr, x0=x0, z0=z0, a=a, t=t, i=i: stroke(dr, [(x0, z0), (x0 - math.cos(a) * .5 * (1 - t), z0 - math.sin(a) * .5 * (1 - t))],
                                                                    .03 * (1 - t) + .006, mat=o_limel if i % 2 else o_white))
for i in range(9):
    fxkit.sparkle(world, 215 + rnd.randint(0, 18), rnd.randint(6, 9), rnd.uniform(-4.8, 4.8), rnd.uniform(-2, 5.6), rnd.uniform(.25, .5),
                  w_gold if i % 3 == 0 else w_spark, rot0=rnd.uniform(0, 1))
# multi: lightning crackles off the sack, sparks orbit it, and it lets go in a spray of streaks
fxkit.lightning(onbag, 309, 325, CX, CZ, (3.9, 4.4), (5.4, 5.8), (o_limel, o_white, o_white))
for i in range(5):
    for k, f in enumerate(range(312, 331)):
        a = i * 2 * math.pi / 5 + k * .24
        onbag.add(f, lambda dr, a=a, k=k: stroke(dr, star(CX + math.cos(a) * 4.6, CZ + math.sin(a) * 4.9, .24 + .1 * math.sin(k * .7), a), .004,
                                                 mat=o_lime, cyclic=True, fill=True, line=False))
fxkit.streaks(world, 326, 8, CX, CZ, 4.4, 6.6, (w_white, w_lime))
world.draw(gp_layer(fxw, "fx"))
onbag.draw(gp_layer(fxb, "fx"))

# ================================================================== on the art: dust, and the $ notes
dust = gp_object(ART, SID + "_dust", depth=-1.0)    # in front of every part (they step 0.1 toward the camera)
m_dust = gp_mat(dust, "fx_dust", (.66, .58, .48, 1), fill=(.97, .94, .87, 1))    # burlap dust, inked lightly
db = Board()
for base, life in ((102, 12), (227, 11)):            # cartoon puffs rolling out from under the sack
    for side, seed in ((-1, 3), (1, 5), (-1, 9), (1, 13)):
        far = 1 if seed in (3, 5) else .65
        fxkit.dust(db, base, life, side * 2.0, -4.3, far, m_dust, drift=(side * 2.4 * far, .45), seed=seed)
db.draw(gp_layer(dust, "dust"))

dp = next(p for p in spec["parts"] if p["name"] == "dollar")
hw, hh = (dp["box"][2] - dp["box"][0]) / 200, (dp["box"][3] - dp["box"][1]) / 200
me = bpy.data.meshes.get(SID + "_note") or bpy.data.meshes.new(SID + "_note")
me.clear_geometry()
me.from_pydata([(-hw, 0, -hh), (hw, 0, -hh), (hw, 0, hh), (-hw, 0, hh)], [], [(0, 1, 2, 3)])
uv = me.uv_layers.get("UVMap") or me.uv_layers.new()
for i, c in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
    uv.data[i].uv = c
if not me.materials:
    me.materials.append(bpy.data.materials[SID + "_dollar"])
G = 30.0
rnd = random.Random(21)
for i in range(5):
    name = f"{SID}_note{i}"
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    ob = bpy.data.objects.new(name, me)
    ART.objects.link(ob)
    vx = (-5.2, -2.4, .4, 2.8, 5.4)[i] + rnd.uniform(-.4, .4)
    vz = rnd.uniform(4.2, 6.0)
    spin = rnd.uniform(-540, 540)
    x0, z0 = MOUTH[0], MOUTH[1] + 1.25                # the mouth, near the top of the leap
    for f in range(213, 243):
        t = (f - 213) / FPS
        s = .32 * min(1, (f - 212) / 3) * (1 - smooth(236, 242, f) * .9)
        ob.location = (x0 + vx * t, -1.1 - .05 * i, z0 + vz * t - .5 * G * t * t)
        ob.rotation_euler = (0, math.radians(spin * t), 0)
        ob.scale = (s * max(.12, abs(math.cos(t * (7 + i)))), 1, s)      # it flutters edge-on and back
        for path in ("location", "rotation_euler", "scale"):
            ob.keyframe_insert(path, frame=f)
    for f, hidden in ((1, True), (213, False), (243, True)):
        ob.hide_render = ob.hide_viewport = hidden
        ob.keyframe_insert("hide_render", frame=f); ob.keyframe_insert("hide_viewport", frame=f)

sc.frame_start, sc.frame_end = 1, max(b for a, b in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], "| saved", fxkit.save(SID))
