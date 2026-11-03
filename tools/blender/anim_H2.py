# H2 - the Glock - animated in Blender: four Actions on its rig (idle, land, hit, multi) on the rig's NLA track,
# its effects drawn frame by frame in Grease Pencil on the same timeline.
#   the gun     a root bone "gun" (added here, at the gun's middle) carries a hop, a squash and the multiplier's
#               swell; the frame bone (the grip) kicks muzzle-up about the hand on every shot
#   the slide   runs back along its rail on every shot (the barrel's kick cycling it) and snaps home; the idle is a
#               press check, the land jolts it, the multi racks it back and locks it while the charge builds, then
#               slams it home and fires. It never runs forward of home (nothing is painted behind its tail).
#   borders     when the slide is back the frame's front corner and the slide's tail stand out of the sticker's old
#               outline: two plain white sticker-border patches (meshes, drawn behind the slide / behind the
#               frame) fill in the border there on exactly the frames the slide is back
#   the glow    tier 1 neon (fxkit.neon) round the art's outline, riding the frame so it kicks with the gun
#   effects     muzzle flashes (white-hot ball, gold flame, lime tongues, sparks; bloomed, and fitted to the room
#               the frame leaves round the muzzle), shock rings and streaks at the muzzle, recoil lines off the
#               tail, brass casings flipping out of the ejection port (they shrink away before they would reach the
#               frame's edge or the clip's end), smoke puffs and a curling smoke wisp, bursts of rays behind, the
#               multiplier's charge (a ball of light swelling at the muzzle, energy streaming along the gun into
#               it, lightning round the gun), the press check's glint and click, sparkles, landing dust
# Every effect is gone by its clip's last frame (the game chains the clips from the rest pose).
# Runs INSIDE Blender, after build_symbol_scene.py (tools/blender/run.py runs both in a background Blender).
import bpy, importlib, math, os, random, sys
from mathutils import Matrix, Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
import fxkit
importlib.reload(fxkit)
from fxkit import (key, rest, px, vec, smooth, gp_object, gp_mat, gp_layer, ride, stroke, star, ring, puff, Board,
                   LIME, VIOLET, WHITE, GOLD)

SID = "H2"
sc, arm, spec = fxkit.setup(SID)
FPS = sc.render.fps
if arm.animation_data:
    arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)

# ------------------------------------------------------------------ the rig: a root bone at the gun's middle
GUN_C = (495, 490)          # the middle of the gun (its box 41..948 x 97..888): it swells and hops about here
GRIP = (700, 640)           # the frame bone's pivot (the recipe's): the gun kicks about the hand
BOTTOM_Y = 872              # the magazine's base: a landing squashes onto it
MUZZLE = (50, 197)          # just in front of the slide's nose, on the bore
PORT = (452, 228)           # the ejection port's top edge: casings leave here
AX = math.atan(.2886)       # the rail runs down to the right at 16 degrees
FWD = math.atan2(math.sin(AX), -math.cos(AX))          # forward along the bore, world angle (left and up)
REAR = Vector((math.cos(AX), 0, -math.sin(AX)))        # rearward along the rail, world (x, z) per unit

bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
g = eb.get("gun") or eb.new("gun")
g.head = vec(*GUN_C)
g.tail = g.head + Vector((0, 0, .6))
g.roll = 0
eb["frame"].parent = g
bpy.ops.object.mode_set(mode="OBJECT")
for pb in arm.pose.bones:
    pb.rotation_mode = "XYZ"
bpy.context.view_layer.update()

ART, FXB, FX = fxkit.layers(sc, SID)
fxkit.glow_compositor(sc, SID, back=dict(strength=1.0, size=.55, gain=1.6), front=dict(strength=.95, size=.42, gain=1.55))

BONES = ["gun", "frame", "slide"]
CLIPS = {"idle": (1, 80), "land": (101, 124), "hit": (201, 256), "multi": (301, 348)}
arm["clips"] = {k: list(v) for k, v in CLIPS.items()}
ZB = (500 - BOTTOM_Y) / 100 - (500 - GUN_C[1]) / 100      # the base, below the gun bone (units, negative)


def gun(f, s=None, sx=None, sy=None, y=0.0, x=None, r=None, plant=True):
    """Key the root: scale about the gun's middle, the base kept planted (a squash sits on its magazine)."""
    if s is not None:
        sx = sy = s
    if sx is not None or sy is not None:
        sy_ = 1 if sy is None else sy
        key(arm, "gun", f, sx=sx, sy=sy)
        key(arm, "gun", f, y=y + (ZB * (1 - sy_) if plant else 0), x=x if x is not None else 0)
    elif y or x is not None:
        key(arm, "gun", f, y=y, x=x if x is not None else 0)
    if r is not None:
        key(arm, "gun", f, r=r)


def slide(f, d):
    """The slide d px back along its rail (never forward of home)."""
    d = max(0.0, d) / 100
    key(arm, "slide", f, x=d * math.cos(AX), y=-d * math.sin(AX))


def kick(f, r=None, x=None, y=None):
    key(arm, "frame", f, r=r, x=x, y=y)


def hard_slide(act, f):
    for i in (0, 1):
        fxkit.hard(act, "slide", "location", i, f)


# ================================================================== idle: it floats, a press check, a glint
f0, f1 = CLIPS["idle"]
act = fxkit.begin_action(arm, SID + "_idle")
rest(arm, BONES, f0)
for f, y in ((1, 0), (21, .045), (41, 0), (61, -.035), (81, 0)):
    key(arm, "gun", f, y=y)
for f, r in ((1, 0), (24, -.9), (46, .25), (64, .6), (81, 0)):
    kick(f, r=r)
# the press check: the slide eased back, a peek, let go - it slams home, the gun jolts
for f, d in ((1, 0), (28, 0), (38, 11), (44, 11.5), (46, 0), (81, 0)):
    slide(f, d)
hard_slide(act, 46)
for f, r, x in ((44, .25, 0), (47, .9, -.012), (50, -.25, .004), (54, .2, 0)):
    kick(f, r=r, x=x)
kick(81, x=0)
fxkit.make_cyclic(act)
fxkit.end_action(arm, act, f0)

# ================================================================== land: it drops onto the reel, grip first
f0, f1 = CLIPS["land"]
act = fxkit.begin_action(arm, SID + "_land")
rest(arm, BONES, f0)
for f, sx, sy, y in ((103, 1.09, .87, 0), (106, .96, 1.06, .06), (110, 1.025, .982, 0), (114, .994, 1.006, 0),
                     (119, 1, 1, 0), (124, 1, 1, 0)):
    gun(f, sx=sx, sy=sy, y=y)
fxkit.hard(act, "gun", "scale", 1, 103)
for f, r in ((103, 2.6), (107, -1.4), (111, .6), (116, -.15), (121, 0), (124, 0)):
    kick(f, r=r)
for f, d in ((102, 0), (103, 7), (105, 1), (107, 3.5), (110, 0), (124, 0)):     # the slide rattles on its rail
    slide(f, d)
fxkit.end_action(arm, act, f0)

# ================================================================== hit: a double tap, the smoke, the glow
f0, f1 = CLIPS["hit"]
act = fxkit.begin_action(arm, SID + "_hit")
rest(arm, BONES, f0)
SHOTS = [(207, 13.0, .15, 26), (218, 14.5, .18, 29)]      # frame, kick degrees, push back (units), slide travel px
# braced: it settles low and aims a touch down; between the shots it fights back to the aim
for f, sx, sy, y in ((201, 1, 1, 0), (205, 1.03, .965, 0), (207, 1.03, .965, 0), (208, .97, 1.035, 0), (212, 1.0, 1.0, 0),
                     (218, 1.0, 1.0, 0), (219, .96, 1.045, .02), (224, 1.01, .99, 0), (234, 1, 1, 0), (238, 1.07, 1.07, .05),
                     (243, .985, 1.015, 0), (248, 1, 1, 0), (256, 1, 1, 0)):
    gun(f, sx=sx, sy=sy, y=y, plant=f < 236)
for f, r, x in ((201, 0, 0), (205, 2.4, -.04), (207, 2.4, -.04),
                (209, -13, .15), (211, -11, .1), (214, 2.2, -.02), (217, .6, 0), (218, .6, 0),
                (220, -14.5, .18), (222, -12.5, .13), (226, 3.0, -.03), (230, -1.1, .01), (234, .3, 0), (239, -.8, 0),
                (245, .25, 0), (250, 0, 0), (256, 0, 0)):
    kick(f, r=r, x=x)
for f in (209, 220):                                      # the kick is a blow, not an ease
    fxkit.hard(act, "frame", "rotation_euler", 2, f)
for sf, deg, push, travel in SHOTS:
    slide(sf - 1 if sf > 207 else 206, 0)
    slide(sf, 0)
    slide(sf + 1, travel)
    slide(sf + 2, travel * .7)
    slide(sf + 4, 0)
    hard_slide(act, sf + 1)
    hard_slide(act, sf + 4)
slide(256, 0)
fxkit.end_action(arm, act, f0)

# ================================================================== multi: racked, charged in three pulses, fired
f0, f1 = CLIPS["multi"]
act = fxkit.begin_action(arm, SID + "_multi")
rest(arm, BONES, f0)
PULSES = (314, 321, 328)
for f, d in ((301, 0), (303, 0), (308, 22), (311, 29), (330, 29), (331, 0), (333, 0), (334, 30), (335, 22), (337, 0), (348, 0)):
    slide(f, d)
hard_slide(act, 311); hard_slide(act, 331); hard_slide(act, 334); hard_slide(act, 337)
# the swell: three pulses, each bigger; it gathers itself (a squash) as the slide slams home, then fires
for f, s in ((301, 1), (306, 1.015), (312, 1.0), (314, 1.05), (317, 1.025), (321, 1.08), (324, 1.05), (328, 1.11),
             (330, 1.1), (332, .955), (334, 1.06), (338, .985), (342, 1.006), (348, 1)):
    gun(f, s=s, plant=False)
fxkit.hard(act, "gun", "scale", 0, 332); fxkit.hard(act, "gun", "scale", 1, 332)
# racked: it leans back as the slide comes back; trembling with the charge, harder each pulse; the shot kicks
rnd = random.Random(7)
mk = [(301, 0, 0), (305, -2.0, .02), (311, -3.0, .03)]
for f in range(312, 330, 2):
    amp = .5 + 1.4 * (f - 312) / 18
    mk.append((f, -3.0 + rnd.uniform(-amp, amp), .03 + rnd.uniform(-.025, .025) * amp))
mk += [(331, -1.2, .0), (333, .8, -.03), (335, -15, .22), (337, -12.5, .15), (341, 3.4, -.04), (345, -1.0, .01), (348, 0, 0)]
for f, r, x in mk:
    kick(f, r=r, x=x)
fxkit.hard(act, "frame", "rotation_euler", 2, 335)
fxkit.end_action(arm, act, f0)

sc.frame_set(1)
bpy.context.view_layer.update()


# ------------------------------------------------------------------ where things are, frame by frame
def at(bone, f, p):
    """World (x, z) of icon point p carried by bone at frame f."""
    sc.frame_set(f)
    pb = arm.pose.bones[bone]
    v = arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted() @ vec(*p)
    return v.x, v.z


def slide_px(f):
    sc.frame_set(f)
    return arm.pose.bones["slide"].location.length * 100


def frame_turn(f):
    """The frame's world turn at frame f (radians, counter-clockwise)."""
    sc.frame_set(f)
    pb = arm.pose.bones["frame"]
    m = (arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted()).to_3x3()
    return math.atan2(m[2][0], m[0][0])


ALL = [f for a, b in CLIPS.values() for f in range(a, b + 1)]
TRAVEL = {f: slide_px(f) for f in ALL}

# ------------------------------------------------------------------ sticker-border patches for the slide's travel
BORDER = (.9387, .9387, .9387, 1)        # the sticker's white (sRGB 248), scene-linear


def patch(name, pts, bone, depth):
    """A plain white sticker-border patch (an n-gon in icon px), riding bone, at depth (units toward camera)."""
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    me = bpy.data.meshes.get(name) or bpy.data.meshes.new(name)
    me.clear_geometry()
    me.from_pydata([(px(x, y)[0], 0.0, px(x, y)[1]) for x, y in pts], [], [list(range(len(pts)))])
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.surface_render_method = "BLENDED"
    mat.use_backface_culling = False
    nt = mat.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = BORDER
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    if not me.materials:
        me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ART.objects.link(ob)
    sc.frame_set(1)
    bpy.context.view_layer.update()
    ob.parent, ob.parent_type, ob.parent_bone = arm, "BONE", bone
    bpy.context.view_layer.update()
    ob.matrix_world = Matrix.Translation((0, depth, 0))
    hidden = None
    for f in ALL:                     # shown only while the slide is back
        h = TRAVEL[f] < .35
        if h != hidden or f in (CLIPS["idle"][0],):
            ob.hide_render = ob.hide_viewport = h
            ob.keyframe_insert("hide_render", frame=f); ob.keyframe_insert("hide_viewport", frame=f)
            hidden = h
    return ob


def arc_pts(cx, cy, r, a0, a1, n=8):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]


# the frame's front corner, in front of the frame and behind the slide: up the frame border's own outer edge, rounding
# over onto the frame's top with the border's own radius (17 px), back along the frame's seam ink
FRONT_PATCH = [(52.5, 252), (54.5, 242), (57, 234), (57, 230)] + arc_pts(74, 230, 17, 180, 270, 8) + \
              [(116, 226.5), (116, 241.5), (75, 229.6), (70, 252)]
# the slide's tail, behind the frame: a rounded corner under the cut bottom end of its border (the beavertail's own
# border stays on the frame - tools/blender/cuts/H2.py), showing only where the slide overhangs the grip
REAR_PATCH = [(896, 452), (916, 452)] + arc_pts(906, 452, 12, 0, 120, 6)
Y_FRAME = bpy.data.objects[SID + "_frame"].matrix_world.translation.y      # the parts' depths (draw order)
Y_SLIDE = bpy.data.objects[SID + "_slide"].matrix_world.translation.y
patch(SID + "_border_front", FRONT_PATCH, "frame", (Y_FRAME + Y_SLIDE) / 2)
patch(SID + "_border_rear", REAR_PATCH, "slide", Y_FRAME + .05)

# ================================================================== the tier glow, behind the sticker
sc.frame_set(1)
fxkit.neon(SID, arm, FXB, CLIPS, tier=1, bone="frame", outline="outline", land_at=103, hit_span=(206, 246),
           pulses=PULSES, charge_span=(307, 331))

# ================================================================== effects
CX, CZ = px(*GUN_C)
MX, MZ = px(*MUZZLE)


def rays(board, f0, life, cx, cz, r0, r1, mats, n=14, rot=.15, seed=0, width=.16):
    """A burst of light rays opening out round (cx, cz): filled wedges that lengthen and thin to needles as they
    burn out (no disc in the middle - it would glow through the trigger guard's holes)."""
    rnd = random.Random(seed)
    lens = [rnd.uniform(.7, 1.0) for _ in range(n)]
    for k in range(life):
        t = k / max(1, life - 1)
        for i in range(n):
            a = rot + 2 * math.pi * i / n + .25 * t
            rt = r0 + (r1 - r0) * lens[i] * t ** .55
            rb = r0 * .55 + (rt - r0 * .55) * .35 * t
            hw = width * (1 - t) ** 1.3 + .012
            mat = mats[i % len(mats)]
            pts = [(cx + math.cos(a) * rb - math.sin(a) * hw, cz + math.sin(a) * rb + math.cos(a) * hw),
                   (cx + math.cos(a) * rt, cz + math.sin(a) * rt),
                   (cx + math.cos(a) * rb + math.sin(a) * hw, cz + math.sin(a) * rb - math.cos(a) * hw)]
            board.add(f0 + k, lambda dr, pts=pts, mat=mat: stroke(dr, pts, .004, mat=mat, cyclic=True, fill=True, line=False))


sc.frame_set(1)
back = gp_object(FXB, SID + "_back", depth=.35)
ride(back, arm, "gun")
b_lime = gp_mat(back, "glow_lime_fill", LIME, fill=LIME)
b_white = gp_mat(back, "glow_white_fill", WHITE, fill=WHITE)
b_gold = gp_mat(back, "glow_gold_fill", GOLD, fill=GOLD)
b_violet = gp_mat(back, "glow_violet", VIOLET)
b_lime_line = gp_mat(back, "glow_lime", LIME)
bb = Board()
rays(bb, 219, 12, CX, CZ, 3.2, 6.2, (b_lime, b_white, b_lime), n=16, seed=2)
rays(bb, 334, 13, CX, CZ, 3.2, 6.2, (b_gold, b_white, b_lime), n=18, rot=.3, seed=6, width=.2)
fxkit.shock_rings(bb, 334, CX, CZ, 4.4, 6.3, (b_violet, b_lime_line, b_violet), life=10, lag=2)   # gone by 347
bb.draw(gp_layer(back, "burst"))

on_gun = gp_object(FX, SID + "_fx_gun", depth=-.8)       # rides the frame: the flash stays on the muzzle as it kicks
ride(on_gun, arm, "frame")
on_slide = gp_object(FX, SID + "_fx_slide", depth=-.8)   # rides the slide: its glint
ride(on_slide, arm, "slide")
world = gp_object(FX, SID + "_fx", depth=-.8)           # stays where the frame is
g_white = gp_mat(on_gun, "fx_white_fill", WHITE, fill=WHITE)
g_gold = gp_mat(on_gun, "fx_gold_fill", GOLD, fill=GOLD)
g_lime = gp_mat(on_gun, "fx_lime_fill", LIME, fill=LIME)
g_lime_l = gp_mat(on_gun, "fx_lime_line", LIME)
g_white_l = gp_mat(on_gun, "fx_white_line", WHITE)
s_white = gp_mat(on_slide, "fx_white_fill", WHITE, fill=WHITE)
w_white = gp_mat(world, "fx_white_line", WHITE)
w_lime = gp_mat(world, "fx_lime_line", LIME)
w_gold = gp_mat(world, "fx_gold_line", GOLD)
w_spark = gp_mat(world, "fx_white_fill", WHITE, fill=WHITE)
w_goldf = gp_mat(world, "fx_gold_fill", GOLD, fill=GOLD)
w_limef = gp_mat(world, "fx_lime_fill", LIME, fill=LIME)
gun_b, slide_b, world_b = Board(), Board(), Board()


def flame(cx, cz, ang, size, n, inner, seed, back=.12, jag=.25):
    """A jagged flame star round (cx, cz): petals long along ang, short to the sides, stubs behind."""
    rnd = random.Random(seed)
    pts = []
    for i in range(n * 2):
        a = ang + math.pi * i / n + rnd.uniform(-.1, .1)
        if i % 2 == 0:
            fwd = max(0.0, math.cos(a - ang))
            L = size * (back + (1 - back) * fwd ** 1.5) * (1 + jag * (rnd.random() - .5))
        else:
            L = size * inner * (.55 + .45 * max(0.0, math.cos(a - ang)))
        pts.append((cx + math.cos(a) * L, cz + math.sin(a) * L))
    return pts


def oval(cx, cz, rx, rz, ang, n=28):
    ca, sa = math.cos(ang), math.sin(ang)
    return [(cx + rx * math.cos(t) * ca - rz * math.sin(t) * sa, cz + rx * math.cos(t) * sa + rz * math.sin(t) * ca)
            for t in (2 * math.pi * i / n for i in range(n))]


SPREAD = .5                                              # the sparks' cone either side of the bore (radians)


def muzzle_flash(board, f, power=1.0, seed=0):
    """Five frames of muzzle flash on the frame's bone: the bang (a fat white-hot ball in gold flame with lime
    tongues), its biggest frame, then it tears into needles and tatters thrown forward, and sparks (all bloomed).
    Sized to stay inside the frame: the muzzle is 2 units from its left edge."""
    ang = FWD
    P = power
    REACH = (1.67, 2.18, 2.26, 2.46, 2.83)               # how far each frame's drawing reaches from the muzzle, x power
    for k in range(5):
        # it never leaves the frame: the room ahead of the muzzle, where it really is and points this frame
        mx_, mz_ = at("frame", f + k, MUZZLE)
        d_ = FWD + frame_turn(f + k)

        def room_at(a_):
            cx_, cz_ = math.cos(a_), math.sin(a_)
            return min((-6.2 - mx_) / cx_ if cx_ < -1e-6 else (6.2 - mx_) / cx_ if cx_ > 1e-6 else 99,
                       (6.2 - mz_) / cz_ if cz_ > 1e-6 else (-6.2 - mz_) / cz_ if cz_ < -1e-6 else 99)
        cone = min(room_at(d_ + SPREAD * u) for u in (-1, -.5, 0, .5, 1))         # sparks fly anywhere in it
        around = min(room_at(d_ + math.pi * u / 8) for u in range(16))            # the flame's stubs, all round
        fit = min(1.0, (cone - .05) / (REACH[k] * P), (around - .05) / (.55 * P))

        def fn(dr, k=k, fit=fit):
            Pk = power * fit
            fw = (0, .12, .26, .4, .5)[k] * Pk
            cx, cz = MX + math.cos(ang) * fw, MZ + math.sin(ang) * fw
            P_ = Pk

            def ahead(d):
                return cx + math.cos(ang) * d * P_, cz + math.sin(ang) * d * P_
            P = Pk
            if k == 0:
                stroke(dr, flame(cx, cz, ang, 1.45 * P, 7, .5, seed, back=.24, jag=.3), .004, mat=g_lime, cyclic=True, fill=True, line=False)
                stroke(dr, flame(cx, cz, ang, 1.08 * P, 7, .5, seed + 1, back=.26), .004, mat=g_gold, cyclic=True, fill=True, line=False)
                stroke(dr, oval(*ahead(.22), .5 * P, .4 * P, ang), .004, mat=g_white, cyclic=True, fill=True, line=False)
            elif k == 1:
                stroke(dr, flame(cx, cz, ang, 1.75 * P, 8, .42, seed + 2, back=.2, jag=.35), .004, mat=g_lime, cyclic=True, fill=True, line=False)
                stroke(dr, flame(cx, cz, ang, 1.3 * P, 8, .42, seed + 3, back=.22), .004, mat=g_gold, cyclic=True, fill=True, line=False)
                stroke(dr, oval(*ahead(.32), .56 * P, .38 * P, ang), .004, mat=g_white, cyclic=True, fill=True, line=False)
            elif k == 2:
                stroke(dr, flame(cx, cz, ang, 1.6 * P, 9, .14, seed + 4, back=.05, jag=.5), .004, mat=g_lime, cyclic=True, fill=True, line=False)
                stroke(dr, flame(cx, cz, ang, .95 * P, 7, .3, seed + 5, back=.1), .004, mat=g_gold, cyclic=True, fill=True, line=False)
                stroke(dr, oval(*ahead(.3), .3 * P, .2 * P, ang), .004, mat=g_white, cyclic=True, fill=True, line=False)
            elif k == 3:
                rnd = random.Random(seed + 9)
                for j in range(3):                        # tatters of flame flung on
                    a = ang + rnd.uniform(-.45, .45)
                    d = rnd.uniform(.7, 1.15) * P
                    stroke(dr, flame(cx + math.cos(a) * d, cz + math.sin(a) * d, ang, .32 * P, 5, .35, seed + 20 + j, back=.3),
                           .004, mat=g_gold if j % 2 else g_lime, cyclic=True, fill=True, line=False)
            rnd = random.Random(seed * 31 + k)
            for j in range(6 + 2 * k):                    # sparks thrown forward
                a = ang + rnd.uniform(-SPREAD, SPREAD)
                d0 = (.5 + .32 * k + rnd.uniform(0, .45)) * P
                ln = (.3 - .05 * k) * P
                stroke(dr, [(cx + math.cos(a) * d0, cz + math.sin(a) * d0), (cx + math.cos(a) * (d0 + ln), cz + math.sin(a) * (d0 + ln))],
                       .03 * (1 - .18 * k) * P, mat=g_white_l if j % 2 else g_lime_l)
        board.add(f + k, fn)


def kick_lines(board, f0, power=1.0):
    """The recoil, drawn: three short lines thrown back off the gun's tail as it kicks."""
    for k in range(4):
        t = k / 3
        for j, (x, y) in enumerate(((958, 372), (975, 430), (962, 488))):
            X, Z = px(x, y)
            a = math.radians(-18 + 10 * j)
            L0 = (.12 + .5 * t) * power
            L1 = L0 + .45 * (1 - t) * power
            board.add(f0 + k, lambda dr, X=X, Z=Z, a=a, L0=L0, L1=L1, t=t: stroke(
                dr, [(X + math.cos(a) * L0, Z + math.sin(a) * L0), (X + math.cos(a) * L1, Z + math.sin(a) * L1)],
                .035 * (1 - t) + .008, mat=w_white))


# idle: a glint runs down the slide's top edge after the press check; the slide's click; the slide stop's twinkle
TOP = [(858, 314), (700, 268), (520, 220), (330, 170), (175, 128)]
for k, f in enumerate(range(57, 72)):
    t = k / 14
    i = min(len(TOP) - 2, int(t * (len(TOP) - 1)))
    u = t * (len(TOP) - 1) - i
    x = TOP[i][0] + (TOP[i + 1][0] - TOP[i][0]) * u
    y = TOP[i][1] + (TOP[i + 1][1] - TOP[i][1]) * u
    r = .5 * math.sin(math.pi * min(1, t * 1.05)) ** .7 + .04
    slide_b.add(f, lambda dr, x=x, y=y, r=r, t=t: stroke(dr, star(*px(x, y), r, .3 + 1.2 * t), .004, mat=s_white, cyclic=True,
                                                         fill=True, line=False))
for k, f in enumerate(range(46, 51)):                     # the click as the slide slams home: a tick at the port
    t = k / 4
    for a in (55, 90, 125):
        aa = math.radians(a)
        X, Z = px(*PORT)
        gun_b.add(f, lambda dr, aa=aa, t=t, X=X, Z=Z: stroke(
            dr, [(X + math.cos(aa) * (.2 + .3 * t), Z + math.sin(aa) * (.2 + .3 * t)),
                 (X + math.cos(aa) * (.42 + .38 * t), Z + math.sin(aa) * (.42 + .38 * t))], .03 * (1 - t) + .008, mat=g_white_l))
fxkit.sparkle(gun_b, 12, 9, *px(560, 418), .34, g_white, rot0=.3)          # the slide stop catches the light

# land: impact ticks either side of the base
BASE_X0, BASE_X1 = px(560, BOTTOM_Y)[0], px(790, BOTTOM_Y)[0]
for k, f in enumerate(range(102, 108)):
    t = k / 5
    for side, x0 in ((-1, BASE_X0), (1, BASE_X1)):
        world_b.add(f, lambda dr, s=side, x0=x0, t=t: stroke(dr, [(x0 + s * (.3 + 1.2 * t), -3.78), (x0 + s * (.8 + 1.8 * t), -3.62 + .1 * t)],
                                                            .035 * (1 - t) + .008, mat=w_lime))

# hit: two flashes, rings and streaks at the muzzle, the kick drawn, sparkles after
for n, (sf, deg, push, travel) in enumerate(SHOTS):
    muzzle_flash(gun_b, sf, power=1.0 + .15 * n, seed=11 + 7 * n)
    mx, mz = at("frame", sf, MUZZLE)
    fxkit.shock_rings(world_b, sf, mx, mz, .3, 1.15, (w_white, w_lime), life=8, lag=2, width=.08)
    fxkit.streaks(world_b, sf + 1, 6, mx, mz, .5, 1.45, (w_white, w_gold), n=10, rot=.4 + n, width=.035)
    kick_lines(world_b, sf + 1, power=1 + .2 * n)
rnd = random.Random(3)
for i in range(10):
    fxkit.sparkle(world_b, 226 + rnd.randint(0, 20), rnd.randint(6, 9), rnd.uniform(-5.4, 5.4), rnd.uniform(-3.5, 5.2),
                  rnd.uniform(.25, .5), w_goldf if i % 3 == 0 else w_spark, rot0=rnd.uniform(0, 1))

# multi: the charge gathers at the muzzle - a ball of light swelling with each pulse, energy streaming along the gun
# into it, lightning crackling round the gun - then the ball goes off as the shot
ORB_SPAN = (306, 332)


def orb_level(f):
    lv = .16 * smooth(306, 311, f) + .1 * smooth(311, 314, f) + .1 * smooth(318, 321, f) + .1 * smooth(325, 328, f)
    lv += sum(.07 * math.exp(-((f - p) / 1.4) ** 2) for p in PULSES)
    return lv * (1 - smooth(331, 333, f))


for f in range(ORB_SPAN[0], ORB_SPAN[1] + 1):
    lv = orb_level(f)
    if lv < .02:
        continue
    r = lv * (1 + .07 * math.sin(f * 1.9))
    ox, oz = MX + math.cos(FWD) * (r * .6), MZ + math.sin(FWD) * (r * .6)
    rr = random.Random(f * 7)

    def fn(dr, r=r, ox=ox, oz=oz, rr=rr, f=f):
        stroke(dr, ring(ox, oz, r * 1.35, n=32), .004, opacity=.55, mat=g_lime, cyclic=True, fill=True, line=False)
        stroke(dr, ring(ox, oz, r, n=32), .004, mat=g_lime, cyclic=True, fill=True, line=False)
        stroke(dr, ring(ox, oz, r * .6, n=28), .004, mat=g_white, cyclic=True, fill=True, line=False)
        for j in range(3):                                # it crackles
            a = rr.uniform(0, 2 * math.pi)
            stroke(dr, fxkit.zigzag(ox + math.cos(a) * r * .9, oz + math.sin(a) * r * .9, ox + math.cos(a) * r * 1.65,
                                     oz + math.sin(a) * r * 1.65, n=4, amp=.07, seed=f * 3 + j), .022, mat=g_white_l if j else g_lime_l)
    gun_b.add(f, fn)
rnd = random.Random(17)
SOURCES = [(330, 170), (520, 215), (700, 265), (860, 318), (420, 300), (620, 350), (790, 400), (300, 290), (640, 560),
           (700, 700), (560, 455), (820, 520)]
for i in range(34):
    f0_ = 306 + int(i * 23 / 34)
    sx_, sy_ = SOURCES[rnd.randrange(len(SOURCES))]
    sx_, sy_ = sx_ + rnd.uniform(-30, 30), sy_ + rnd.uniform(-20, 20)
    S0, E0 = px(sx_, sy_), (MX + math.cos(FWD) * .2, MZ + math.sin(FWD) * .2)
    bend = rnd.uniform(-.5, .5)
    life = 7
    mat = g_lime_l if i % 3 else g_white_l
    for k in range(life):
        def P(t, S0=S0, E0=E0, bend=bend):
            u = t * t
            x = S0[0] + (E0[0] - S0[0]) * u
            z = S0[1] + (E0[1] - S0[1]) * u + bend * math.sin(math.pi * u)
            return x, z
        t1, t0 = (k + 1) / life, max(0, (k - 1.2) / life)
        pts = [P(t0 + (t1 - t0) * j / 5) for j in range(6)]
        gun_b.add(f0_ + k, lambda dr, pts=pts, k=k, mat=mat: stroke(dr, pts, 0, radii=fxkit.taper(6, .045 * (1 - .4 * k / life), ends=.4),
                                                                    mat=mat))


def crackle(board, f0, f1, cx, cz, r_in, r_out, mats, per=3, step=2, seed=0, width=.04):
    """Lightning arcs off the charged gun (fxkit.lightning, drawn bolder)."""
    for f in range(f0, f1 + 1, step):
        rr = random.Random(f * 13 + seed)
        for j in range(per):
            a = rr.uniform(0, 2 * math.pi)
            p0 = (cx + math.cos(a) * r_in[0], cz + math.sin(a) * r_in[1])
            p1 = (cx + math.cos(a) * r_out[0], cz + math.sin(a) * r_out[1])
            board.add(f, lambda dr, p0=p0, p1=p1, f=f, j=j: stroke(dr, fxkit.zigzag(*p0, *p1, n=6, amp=.28, seed=f * 7 + j), 0,
                                                                   radii=fxkit.taper(7, width, ends=.25), mat=mats[j % len(mats)]),
                      hold=step)


crackle(gun_b, 310, 330, CX, CZ, (3.6, 2.6), (5.0, 3.6), (g_lime_l, g_white_l, g_lime_l), per=3, step=2, seed=5)
muzzle_flash(gun_b, 333, power=1.25, seed=41)
mx, mz = at("frame", 333, MUZZLE)
fxkit.shock_rings(world_b, 333, mx, mz, .35, 1.2, (w_white, w_lime, w_gold), life=9, lag=2, width=.1)
fxkit.streaks(world_b, 334, 8, mx, mz, .6, 1.45, (w_white, w_lime, w_gold), n=12, rot=.2, width=.045)
kick_lines(world_b, 334, power=1.35)
for i in range(7):                                       # every one done by 347: nothing pops when the clip ends
    fxkit.sparkle(world_b, 338 + rnd.randint(0, 3), rnd.randint(6, 7), rnd.uniform(-5, 5), rnd.uniform(-3, 5), rnd.uniform(.28, .45),
                  w_limef if i % 2 else w_spark, rot0=rnd.uniform(0, 1))

gun_b.draw(gp_layer(on_gun, "fx"))
slide_b.draw(gp_layer(on_slide, "fx"))
world_b.draw(gp_layer(world, "fx"))

# ================================================================== on the art: casings, smoke, landing dust
sc.frame_set(1)
art_fx = gp_object(ART, SID + "_artfx", depth=-1.0)     # in front of every part
m_brass = gp_mat(art_fx, "fx_brass", (.06, .035, .01, 1), fill=(.86, .55, .12, 1))
m_brass_d = gp_mat(art_fx, "fx_brass_rim", (.06, .035, .01, 1), fill=(.42, .22, .04, 1))
m_brass_hi = gp_mat(art_fx, "fx_brass_hi", (1, .93, .62, 1))
m_mouth = gp_mat(art_fx, "fx_casing_mouth", (.06, .035, .01, 1), fill=(.05, .03, .01, 1))
m_smoke = gp_mat(art_fx, "fx_smoke", (.42, .42, .47, 1), fill=(.80, .80, .84, 1))
m_wisp = gp_mat(art_fx, "fx_wisp", (.78, .78, .82, 1))
m_dust = gp_mat(art_fx, "fx_dust", (.40, .40, .44, 1), fill=(.74, .74, .78, 1))
ab = Board()


def casing(board, f0, seed, vx=3.1, vz=7.4, spin=-1250.0, frames=30, end=None):
    """A brass casing flipped out of the ejection port, tumbling end over end in the picture as it arcs away; over
    its last frames (before it would reach the frame's edge, or `end`) it shrinks away to nothing, flying off."""
    x0, z0 = at("slide", f0, PORT)
    rnd = random.Random(seed)
    vx += rnd.uniform(-.3, .3); vz += rnd.uniform(-.4, .4)
    a0 = rnd.uniform(0, 360)
    L, W = .62, .27
    n = frames
    for k in range(frames):
        t = k / FPS
        if z0 + vz * t - 15.0 * t * t < -5.7 or x0 + vx * t > 5.6 or (end is not None and f0 + k > end):
            n = k
            break
    for k in range(n):
        t = k / FPS
        x, z = x0 + vx * t, z0 + vz * t - .5 * 30.0 * t * t
        a = math.radians(a0 + spin * t)
        ca, sa = math.cos(a), math.sin(a)
        grow = min(1.0, .45 + k * .3) * min(1.0, (n - 1 - k) / 5) ** .7
        if grow < .05:
            continue

        def P(u, v, x=x, z=z, ca=ca, sa=sa, g=grow):
            return (x + (u * ca - v * sa) * g, z + (u * sa + v * ca) * g)

        def fn(dr, P=P):
            body = [P(-L / 2 + .02, -W / 2), P(L / 2, -W / 2 + .02), P(L / 2, W / 2 - .02), P(-L / 2 + .02, W / 2)]
            stroke(dr, body, .016, mat=m_brass, cyclic=True, fill=True)
            stroke(dr, [P(-L / 2 - .02, -W / 2 - .03), P(-L / 2 + .09, -W / 2 - .03), P(-L / 2 + .09, W / 2 + .03), P(-L / 2 - .02, W / 2 + .03)],
                   .014, mat=m_brass_d, cyclic=True, fill=True)
            stroke(dr, [P(L / 2 - .015, -W / 2 + .05), P(L / 2 + .015, 0), P(L / 2 - .015, W / 2 - .05)], .032, mat=m_mouth)
            stroke(dr, [P(-L / 2 + .14, W / 2 - .075), P(L / 2 - .07, W / 2 - .075)], .02, mat=m_brass_hi)
        board.add(f0 + k, fn)


def smoke(board, f0, life, seed, n=3, power=1.0):
    """Puffs hanging at the muzzle once it is back on aim: they roll forward a little, rise, swell and shrink away
    (solid, never fading)."""
    mx, mz = at("frame", f0, MUZZLE)
    ang = FWD + frame_turn(f0)
    rnd = random.Random(seed)
    for i in range(n):
        d = (.22 + .2 * i) * power
        cx, cz = mx + math.cos(ang) * d, mz + math.sin(ang) * d + .1 * i
        fxkit.dust(board, f0 + 2 * i, life - 2 * i, cx, cz, (.46 - .05 * i) * power, m_smoke,
                   drift=(.25 + .12 * i + rnd.uniform(-.08, .08), .95 + .2 * i), seed=seed + i, lobes=6)


def wisp(board, f0, f1, seed):
    """A curl of smoke rising off the muzzle: it grows up out of it, sways, lets go and drifts up thinning away."""
    rnd = random.Random(seed)
    ph = rnd.uniform(0, 6.28)
    n = 18
    for f in range(f0, f1 + 1):
        t = (f - f0) / (f1 - f0)
        mx, mz = at("frame", f, MUZZLE)
        grow = min(1.0, t / .45)
        lift = max(0.0, t - .5) * 1.0                      # it lets go of the muzzle and rises off it
        pts, radii = [], []
        for j in range(n):
            u = j / (n - 1)
            h = u * 1.55 * grow
            sway = .22 * math.sin(u * 5.2 - t * 7 + ph) * u + .1 * math.sin(u * 2.3 + t * 3) * u
            pts.append((mx - .12 * u + sway, mz + .08 + h + lift))
            w = .075 * (1 - u) ** .8 + .015
            radii.append(w * (1 - max(0.0, t - .55) / .45) ** .7)
        if max(radii) > .006:
            board.add(f, lambda dr, pts=pts, radii=radii: stroke(dr, pts, 0, radii=radii, mat=m_wisp))


for n, (sf, deg, push, travel) in enumerate(SHOTS):
    casing(ab, sf + 1, seed=3 + n, vx=2.8 + .6 * n, vz=7.2 + .5 * n)
smoke(ab, 212, 16, seed=20, n=3, power=.95)
smoke(ab, 226, 20, seed=30, n=4, power=1.1)
wisp(ab, 236, 254, seed=4)
casing(ab, 334, seed=9, vx=3.4, vz=8.0, spin=-1500, end=346)
smoke(ab, 340, 8, seed=50, n=2, power=1.05)
for side, seed in ((-1, 3), (1, 5), (-1, 9), (1, 13)):     # landing dust rolling out from under the base
    far = 1 if seed in (3, 5) else .6
    x0 = BASE_X0 if side < 0 else BASE_X1
    fxkit.dust(ab, 102, 11, x0 + side * .2, -3.72, .6 * far, m_dust, drift=(side * 1.8 * far, .35), seed=seed)
ab.draw(gp_layer(art_fx, "fx"))

sc.frame_start, sc.frame_end = 1, max(b for a, b in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], "| saved", fxkit.save(SID))
