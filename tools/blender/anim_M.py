# M - the Multi booster (a chunk of brick wall; the game paints the multiplier value over it) - animated in Blender:
# four Actions on its rig (idle, land, hit, multi) laid one after another on the rig's NLA track, and its effects
# drawn frame by frame in Grease Pencil on the same timeline. The special symbols wear no tier glow: everything here
# comes from what it is - a loose chunk of wall.
#   the wall     a root bone ("chunk", added here at the foot of the wall) squashes and shudders the whole chunk; the
#                two halves either side of the stepped crack down the mortar turn about the crack's foot, so the crack
#                creaks open and slams shut; the three loose corner bricks tip up, jump out of their beds, clatter back
#   idle         alive (the game loops it on every Multi): the top-left brick tips up and clatters back, the bottom
#                brick works out and knocks in, the chunk hops and lands squashed (crack jolts, bricks bounce, dust
#                out of the bottom corners), a pulse of energy runs up the crack and flashes at the top, the
#                top-right brick tips; crumbs trickle from the mortar
#   land         it thuds down: squash and rebound, the crack jolts, the loose bricks hop and clatter, mortar dust
#                rolls out from both bottom corners, crumbs bounce
#   hit          crouch, then it CRACKS: the halves spring apart with a flash of gold out of the crack, impact lines
#                all round, the corner bricks jump out of their beds, brick chips and dust burst out of the crack; it
#                shakes there, then SLAMS shut - dust puffed out of the crack's two ends, the bricks drop back in -
#                gold glints
#   multi        its own multiplier going off: it charges - trembling harder and harder, light seeping out through
#                every mortar joint, the crack creaking open on a glowing inside, sparks crawling up it, arcs
#                crackling off its edges, its light welling up round it - then lets go: it punches out, flings the
#                halves open, the joints flash white, and it shoots spikes of light, dust and chips at the four cells
#                it hits (up, down, left, right), then slams back together
# The wall's dark inside (the "cavity") sits behind the parts: whatever a brick tipping up or the crack opening
# uncovers is the depth of the wall, never the board (the crack's inside rides the chunk, each brick's socket the half
# it sits in; it glows green with the multi's charge). Runs INSIDE Blender, after build_symbol_scene.py
# (tools/blender/run.py runs both in a background Blender).
import bpy, importlib, json, math, os, random, sys
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
import fxkit
importlib.reload(fxkit)
from fxkit import (key, rest, px, smooth, gp_object, gp_mat, gp_layer, ride, stroke, star, ring, Board,
                   LIME, WHITE, GOLD)

SID = "M"
sc, arm, spec = fxkit.setup(SID)
FPS = sc.render.fps


def srgb(r, g, b, a=1.0):
    """A colour picked off the art (0-255, sRGB) as Blender's linear colour."""
    f = lambda c: (c / 255) / 12.92 if c / 255 <= .04045 else ((c / 255 + .055) / 1.055) ** 2.4
    return (f(r), f(g), f(b), a)


# ------------------------------------------------------------------ the root bone: the whole chunk
ROOT_AT = (509, 922)                        # the foot of the wall, mid-way: it squashes and shudders from here
if "chunk" not in arm.data.bones:
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    b = eb.new("chunk")
    b.head = fxkit.vec(*ROOT_AT)
    b.tail = b.head + Vector((0, 0, .6))
    b.roll = 0
    for n in ("left", "right"):
        eb[n].use_connect = False
        eb[n].parent = b
    bpy.ops.object.mode_set(mode="OBJECT")
arm.pose.bones["chunk"].rotation_mode = "XYZ"

ART, FXB, FX = fxkit.layers(sc, SID)
fxkit.glow_compositor(sc, SID, back=dict(strength=1.0, size=.55, gain=1.6), front=dict(strength=.85, size=.4, gain=1.5))
if arm.animation_data:
    arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)

BONES = ["chunk", "left", "right", "brick_tl", "brick_tr", "brick_bl"]
CLIPS = {"idle": (1, 90), "land": (101, 130), "hit": (201, 250), "multi": (301, 356)}
arm["clips"] = {k: list(v) for k, v in CLIPS.items()}

# measured off the art (icon px): the mortar joints, by the part they lie on (bed joints followed column by column
# along the middle of the mortar, head joints row by row), and the wall's inside behind the crack and the loose
# bricks (the inside of the black outline, round the crack's stepped line and the bricks' sockets)
JOINTS = {
    "brick_tl": [
        [(267, 137), (273, 155), (274, 167), (274, 239)],
        [(308, 137), (308, 167)],
    ],
    "left": [
        [(174, 245), (192, 253), (210, 256), (222, 254), (234, 255), (246, 249), (258, 248)],
        [(264, 246), (294, 250), (324, 245), (336, 252), (342, 253), (354, 253), (372, 248), (384, 253), (390, 252), (402, 255),
         (450, 252), (462, 254), (468, 252), (480, 252), (492, 248), (504, 249)],
        [(168, 357), (186, 364), (276, 367), (306, 366), (318, 368), (330, 366), (378, 367), (408, 362), (474, 367), (588, 368), (606, 366)],
        [(174, 467), (216, 476), (258, 478), (300, 476), (312, 479), (324, 478), (342, 481), (378, 480), (396, 475), (426, 479),
         (456, 478), (486, 474), (504, 477)],
        [(582, 477), (606, 475), (618, 476)],
        [(186, 593), (204, 585), (228, 580), (240, 580), (258, 584), (294, 578), (312, 582), (342, 580), (402, 582), (426, 578),
         (444, 581), (504, 580)],
        [(510, 580), (534, 583), (558, 581)],
        [(564, 580), (600, 582)],
        [(174, 691), (198, 683), (240, 687), (252, 686), (282, 690), (306, 683), (330, 686), (354, 686), (372, 684), (390, 685),
         (408, 682), (444, 685), (468, 680), (498, 684), (540, 679), (564, 680), (570, 682), (600, 680)],
        [(174, 802), (186, 796), (198, 793), (264, 793), (282, 797), (330, 797), (354, 794), (396, 794), (414, 796), (492, 791)],
        [(308, 167), (309, 239)], [(281, 259), (281, 355)], [(403, 259), (403, 355)], [(402, 372), (403, 474)],
        [(294, 481), (294, 571)], [(499, 481), (499, 505), (497, 511), (498, 571)], [(306, 586), (308, 604), (306, 628), (306, 676)],
        [(398, 586), (398, 676)], [(604, 586), (604, 676)], [(292, 690), (295, 702), (295, 714), (291, 732), (292, 786)],
        [(302, 690), (302, 786)], [(291, 797), (291, 899)], [(405, 797), (405, 899)],
    ],
    "right": [
        [(504, 249), (516, 248), (540, 250)], [(552, 253), (576, 249), (582, 250)], [(594, 252), (606, 255), (624, 255), (684, 245)],
        [(708, 248), (720, 251), (726, 250)], [(750, 249), (762, 252), (786, 254), (798, 254), (822, 250), (828, 251)],
        [(624, 366), (642, 367), (660, 364), (726, 363), (750, 366), (786, 367), (810, 364), (846, 364)],
        [(504, 477), (516, 479), (582, 477)],
        [(618, 476), (624, 478), (654, 476), (666, 479), (690, 478), (738, 481), (774, 472), (804, 470), (828, 464)],
        [(600, 582), (636, 585), (690, 585), (720, 581), (786, 578), (834, 583), (852, 581)],
        [(600, 680), (612, 680), (624, 686), (636, 689), (654, 689), (678, 685), (708, 687), (732, 682), (744, 682), (792, 686),
         (810, 684), (828, 686), (840, 690), (858, 676)],
        [(492, 791), (576, 794), (600, 797), (642, 797), (720, 793), (744, 797), (816, 798), (828, 796), (846, 787)],
        [(506, 155), (507, 239)], [(688, 161), (687, 239)], [(599, 259), (599, 355)], [(729, 259), (730, 355)], [(631, 372), (631, 474)],
        [(514, 481), (514, 571)], [(725, 481), (725, 571)], [(768, 586), (768, 628), (773, 658), (770, 676)], [(499, 690), (499, 786)],
        [(708, 690), (708, 786)], [(589, 797), (589, 899)], [(710, 797), (709, 893)],
    ],
    "brick_tr": [[(684, 245), (708, 248)], [(828, 251), (852, 238)], [(693, 143), (688, 161)]],
    "brick_bl": [[(278, 797), (278, 821), (276, 827), (277, 899)]],
}
CAVITY = [
    [(173, 128), (183, 128), (194, 132), (207, 134), (256, 134), (268, 143), (287, 142), (308, 159), (308, 244), (306, 246), (289, 246),
     (172, 246), (158, 234), (156, 227), (156, 193), (161, 175), (160, 154), (164, 136), (168, 130)],
    [(806, 131), (831, 132), (844, 143), (849, 145), (854, 152), (855, 164), (850, 199), (856, 212), (857, 227), (853, 237), (844, 249),
     (734, 249), (690, 249), (688, 247), (688, 155), (701, 141), (707, 139), (728, 137), (742, 141), (756, 141), (776, 135)],
    [(466, 141), (496, 142), (507, 149), (513, 144), (532, 145), (549, 143), (551, 145), (551, 208), (608, 210), (618, 214), (630, 224),
     (638, 238), (641, 252), (641, 324), (658, 333), (668, 345), (672, 355), (674, 366), (674, 477), (672, 488), (666, 501), (651, 515),
     (636, 520), (552, 521), (553, 538), (611, 538), (619, 540), (629, 545), (638, 553), (647, 570), (649, 581), (649, 688), (647, 699),
     (641, 712), (626, 726), (611, 731), (538, 732), (539, 755), (599, 756), (616, 765), (626, 777), (632, 798), (632, 900), (630, 902),
     (628, 901), (601, 898), (593, 895), (586, 902), (579, 904), (547, 904), (545, 902), (545, 843), (494, 842), (480, 839), (470, 834),
     (461, 826), (452, 809), (451, 682), (456, 667), (466, 655), (483, 646), (494, 644), (562, 643), (561, 625), (508, 625), (497, 623),
     (480, 614), (470, 602), (465, 587), (465, 471), (467, 463), (472, 453), (480, 444), (497, 435), (508, 433), (587, 432), (587, 409),
     (569, 399), (559, 387), (555, 377), (554, 297), (507, 296), (496, 294), (479, 285), (468, 271), (464, 258), (464, 143)],
    [(173, 800), (287, 800), (289, 802), (289, 893), (289, 896), (285, 900), (271, 906), (233, 907), (219, 904), (208, 904), (201, 906),
     (190, 904), (186, 899), (186, 884), (184, 876), (177, 861), (173, 844), (165, 828), (162, 817), (165, 806)],
]
# the crack, top to bottom, inside the wall (the recipe's stepped line, its ends trimmed to the black outline)
CRACK = [(507, 146), (507, 252), (597, 252), (597, 366), (630, 366), (630, 477), (508, 477), (508, 581), (605, 581),
         (605, 688), (494, 688), (494, 798), (588, 798), (588, 900)]


def hard(act, bone, f):
    """Every channel of a bone keyed at f is hit, not eased into (a landing, a slam)."""
    for fc in fxkit.fcurves(act):
        if fc.data_path.startswith(f'pose.bones["{bone}"]'):
            for kp in fc.keyframe_points:
                if abs(kp.co.x - f) < .5:
                    kp.handle_left_type = kp.handle_right_type = "VECTOR"
            fc.update()


def crack(f, r):
    """The crack's two halves turned apart by r degrees each (negative: pressed past shut)."""
    key(arm, "left", f, r=r)
    key(arm, "right", f, r=-r)


def corner_bricks(keys, d=1, hits=()):
    """The two loose top bricks, mirrored: (frame, out, up, tilt) - out in units away from the middle, tilt in degrees
    lifting the outer end; the top-right one a beat (d frames) behind the top-left."""
    for bone, dd, sgn in (("brick_tl", 0, -1), ("brick_tr", d, 1)):
        for f, out, up, tilt in keys:
            key(arm, bone, f + dd, x=sgn * out, y=up, r=sgn * tilt)
        for f in hits:
            hard(act, bone, f + dd)


# ================================================================== idle: alive - it plays on every Multi on the board
# 90 frames, a seamless loop from and back to rest: the top-left brick tips up and clatters back, the bottom brick
# works out and knocks in, then the whole chunk gives a little hop and lands squashed (the crack jolts, the corner
# bricks bounce, dust kicks out of the bottom corners), a pulse of energy runs up the crack (it creaks open with it)
# and flashes at the top, and the top-right brick tips. The middle, where the game paints the value, only squashes.
f0, f1 = CLIPS["idle"]
act = fxkit.begin_action(arm, SID + "_idle")
rest(arm, BONES, f0)
rest(arm, BONES, f1 + 1)                    # the loop: frame 91 is frame 1 again
for f, r, y in ((6, 0, 0), (11, -11, .03), (15, 0, 0), (18, -3, .01), (21, 0, 0), (23, -.7, 0), (25, 0, 0)):
    key(arm, "brick_tl", f, r=r, y=y)            # tips up on its inner corner, drops back, bounces twice smaller
for f in (15, 21, 25):
    hard(act, "brick_tl", f)
for f, x in ((26, 0), (30, -.16), (33, -.13), (36, 0), (38, -.03), (40, 0)):
    key(arm, "brick_bl", f, x=x)            # works out of its bed and knocks back in
for f in (36, 40):
    hard(act, "brick_bl", f)
IDLE_LAND = 50
for f, sx, sy, y, r in ((40, 1, 1, 0, 0), (43, 1.05, .93, 0, 0), (46, .97, 1.05, .2, 1.6), (48, .985, 1.025, .23, 1.2),
                        (IDLE_LAND, 1.07, .9, 0, -.6), (53, .98, 1.025, 0, .3), (56, 1.008, .993, 0, 0), (59, 1, 1, 0, 0)):
    key(arm, "chunk", f, sx=sx, sy=sy, y=y, r=r)  # a little hop, leaning, landing squashed
hard(act, "chunk", IDLE_LAND)
corner_bricks(((45, 0, 0, 0), (49, 0, -.01, 0), (IDLE_LAND + 1, 0, .11, 5.5), (IDLE_LAND + 4, 0, 0, 0), (IDLE_LAND + 6, 0, .025, 1.2),
               (IDLE_LAND + 8, 0, 0, 0)), d=1, hits=(IDLE_LAND + 4, IDLE_LAND + 8))
for f, r in ((47, 0), (IDLE_LAND, .3), (IDLE_LAND + 3, -.06), (IDLE_LAND + 5, 0),       # jolted by the landing ...
             (62, 0), (67, .24), (71, .18), (75, 0), (77, -.03), (79, 0)):             # ... and creaking with the pulse
    crack(f, r)
hard(act, "left", IDLE_LAND); hard(act, "right", IDLE_LAND); hard(act, "left", 75); hard(act, "right", 75)
for f, r in ((70, 0), (75, 10), (79, 0), (82, 2.6), (85, 0), (87, .6), (89, 0)):
    key(arm, "brick_tr", f, r=r)
for f in (79, 85, 89):
    hard(act, "brick_tr", f)
fxkit.make_cyclic(act)
fxkit.end_action(arm, act, f0)

# ================================================================== land: a heavy thud
f0, f1 = CLIPS["land"]
act = fxkit.begin_action(arm, SID + "_land")
rest(arm, BONES, f0)
rest(arm, BONES, f1)
for f, sx, sy in ((103, 1.075, .9), (106, .97, 1.05), (109, 1.018, .985), (113, .996, 1.005), (118, 1, 1)):
    key(arm, "chunk", f, sx=sx, sy=sy)
hard(act, "chunk", 103)
for f, r in ((103, .55), (106, -.12), (109, .05), (112, 0)):
    crack(f, r)
hard(act, "left", 103); hard(act, "right", 103)
corner_bricks(((103, 0, 0, 0), (106, .01, .11, 3), (109, 0, 0, 0), (111, 0, .028, .8), (113, 0, 0, 0), (118, 0, 0, 0)), hits=(109, 113))
for f, x, y in ((103, 0, 0), (106, -.05, .035), (109, 0, 0), (112, -.01, 0), (114, 0, 0)):
    key(arm, "brick_bl", f, x=x, y=y)
hard(act, "brick_bl", 109)
fxkit.end_action(arm, act, f0)

# ================================================================== hit: crouch, CRACK, shake, SLAM, settle
f0, f1 = CLIPS["hit"]
act = fxkit.begin_action(arm, SID + "_hit")
rest(arm, BONES, f0)
rest(arm, BONES, f1)
for f, sx, sy, y in ((205, 1.045, .925, 0), (208, .965, 1.07, .07), (212, 1.01, .995, .03), (218, 1.0, 1.01, 0), (224, 1.02, .985, 0),
                     (227, 1.065, .905, 0), (230, .975, 1.035, 0), (234, 1.01, .992, 0), (239, 1, 1, 0)):
    key(arm, "chunk", f, sx=sx, sy=sy, y=y)
for f, x in ((202, .012), (203, -.018), (204, .02), (205, -.012), (206, 0)):
    key(arm, "chunk", f, x=x)               # it strains
hard(act, "chunk", 227)
for f, r in ((205, -.15), (208, 2.3), (211, 1.9), (213, 2.3), (215, 2.0), (217, 2.35), (219, 2.05), (221, 2.3), (224, 2.6),
             (227, -.45), (230, .18), (233, -.05), (236, 0)):
    crack(f, r)
hard(act, "left", 227); hard(act, "right", 227)
# the loose corner bricks jump out of their beds and rattle there, then drop back in with the slam
corner_bricks(((207, 0, 0, 0), (210, .05, .17, 9), (213, .04, .12, 5.5), (216, .055, .17, 8.5), (219, .04, .12, 5), (222, .05, .16, 8),
               (225, .03, .08, 4), (228, 0, 0, 0), (231, 0, .03, 2), (234, 0, 0, 0), (236, 0, .006, .5), (238, 0, 0, 0)),
              hits=(228, 234, 238))
for f, x, y, r in ((207, 0, 0, 0), (210, -.13, .05, 5), (214, -.1, .03, 3), (218, -.13, .05, 5), (222, -.11, .04, 4), (228, 0, 0, 0),
                   (231, -.025, .01, 1), (234, 0, 0, 0)):
    key(arm, "brick_bl", f, x=x, y=y, r=r)
hard(act, "brick_bl", 228); hard(act, "brick_bl", 234)
fxkit.end_action(arm, act, f0)

# ================================================================== multi: charge - harder and harder - and let go
f0, f1 = CLIPS["multi"]
act = fxkit.begin_action(arm, SID + "_multi")
rest(arm, BONES, f0)
rest(arm, BONES, f1)
for f, sx, sy in ((303, 1, 1), (318, 1.025, .965), (326, 1.045, .935), (328, 1.12, 1.12), (331, 1.05, .92), (334, .985, 1.02),
                  (338, 1.006, .995), (343, 1, 1)):
    key(arm, "chunk", f, sx=sx, sy=sy)
hard(act, "chunk", 331)
for i, f in enumerate(range(304, 327, 2)):  # the tremble builds
    a = .004 + .03 * smooth(303, 326, f)
    key(arm, "chunk", f, x=a if i % 2 else -a, r=(.08 + .55 * smooth(303, 326, f)) * (-1 if i % 2 else 1))
key(arm, "chunk", 327, x=0, r=0)
for f, r in ((303, 0), (309, .3), (313, .24), (318, .62), (321, .52), (326, 1.1), (328, 2.8), (331, -.5), (334, .15), (337, -.03), (340, 0)):
    crack(f, r)
hard(act, "left", 331); hard(act, "right", 331)
corner_bricks(((305, 0, 0, 0), (307, 0, .025, 1.5), (309, 0, 0, 0), (312, 0, .035, 2), (314, 0, 0, 0), (318, 0, .045, 2.6),
               (320, 0, 0, 0), (323, 0, .05, 3), (325, 0, 0, 0), (327, 0, 0, 0), (329, .05, .17, 8), (332, 0, 0, 0), (334, 0, .03, 1.5),
               (336, 0, 0, 0)), d=2, hits=(309, 314, 320, 325, 332, 336))
for f, x in ((306, 0), (308, -.02), (310, 0), (315, -.03), (317, 0), (322, -.035), (324, 0), (327, 0), (329, -.13), (332, 0), (334, -.02),
             (336, 0)):
    key(arm, "brick_bl", f, x=x)
for f in (310, 317, 324, 332, 336):
    hard(act, "brick_bl", f)
fxkit.end_action(arm, act, f0)

# ================================================================== the wall's dark inside, behind the parts
# the inside of the crack rides the whole chunk (it lies between the two halves); each loose brick's socket rides the
# half the brick sits on, so it stays put under the brick however far the halves swing
mat = bpy.data.materials.get(SID + "_cavity") or bpy.data.materials.new(SID + "_cavity")
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()
em = nt.nodes.new("ShaderNodeEmission")
out = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(em.outputs[0], out.inputs["Surface"])
TL_SOCKET, TR_SOCKET, CRACK_INSIDE, BL_SOCKET = CAVITY
for name, polys, bone in (("cavity", [CRACK_INSIDE], "chunk"), ("cavity_left", [TL_SOCKET, BL_SOCKET], "left"),
                          ("cavity_right", [TR_SOCKET], "right")):
    me = bpy.data.meshes.get(f"{SID}_{name}") or bpy.data.meshes.new(f"{SID}_{name}")
    me.clear_geometry()
    verts, faces = [], []
    for poly in polys:
        i0 = len(verts)
        verts += [(px(x, y)[0], 0.0, px(x, y)[1]) for x, y in poly]
        faces.append(tuple(range(i0, len(verts)))[::-1])
    me.from_pydata(verts, [], faces)
    old = bpy.data.objects.get(f"{SID}_{name}")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    cav = bpy.data.objects.new(f"{SID}_{name}", me)
    ART.objects.link(cav)
    cav.location.y = .1                     # behind every part (they step 0.1 toward the camera from -0.1)
    me.materials.clear()
    me.materials.append(mat)
    ride(cav, arm, bone)
DARK = srgb(26, 16, 14)                     # the depth of the wall: near black, warm
col = em.inputs["Color"]
if nt.animation_data:
    nt.animation_data_clear()
for f, c in ((1, DARK), (304, DARK), (311, (.03, .1, .015, 1)), (318, (.12, .42, .04, 1)), (324, (.42, .95, .22, 1)), (327, (1, 1, .9, 1)),
             (330, (.3, .75, .12, 1)), (335, DARK)):
    col.default_value = c
    col.keyframe_insert("default_value", frame=f)

# ================================================================== effects
INK = srgb(14, 12, 14)
DUST = dict(fill=srgb(244, 239, 228), shade=srgb(219, 210, 193), hi=srgb(255, 254, 250), ink=srgb(162, 150, 134))
BRICK = [srgb(235, 128, 66), srgb(200, 84, 56), srgb(232, 186, 132)]     # orange, red, tan (off the art)
GRIT = [srgb(124, 110, 98), srgb(184, 96, 62), srgb(78, 66, 60)]
OUTLINE = [px(x, y) for x, y in json.load(open(os.path.join(fxkit.ROOT, "art", "blender", "parts", SID, "outline.json")))["points"]]
EDGE = fxkit.resample(OUTLINE, 220)          # 9 px outside the sticker
CX, CZ = px(509, 515)                        # the wall's middle

dust_ob = gp_object(ART, SID + "_dust", depth=-1.0)        # on the art, in front of every part
m_fill = gp_mat(dust_ob, "m_dust_fill", DUST["fill"], fill=DUST["fill"])
m_shade = gp_mat(dust_ob, "m_dust_shade", DUST["shade"], fill=DUST["shade"])
m_hi = gp_mat(dust_ob, "m_dust_hi", DUST["hi"], fill=DUST["hi"])
m_ink = gp_mat(dust_ob, "m_dust_ink", DUST["ink"])
m_chip = [gp_mat(dust_ob, f"m_chip{i}", INK, fill=c) for i, c in enumerate(BRICK)]
m_grit = [gp_mat(dust_ob, f"m_grit{i}", c, fill=c) for i, c in enumerate(GRIT)]
m_tick = gp_mat(dust_ob, "m_tick", srgb(246, 242, 232))
db = Board()


def cloud(board, f0, life, x, z, scale, drift=(0.0, .45), seed=0, lobes=6):
    """A cartoon cloud of mortar dust, shaded like the art (lit up-left, shade down-right, a light ink line): it
    billows out and shrinks away to nothing as it rolls - never fades to grey."""
    for k in range(life):
        t = k / max(1, life - 1)
        size = math.sin(math.pi * min(1.0, t * 1.05)) ** .6
        rr = scale * (.3 + .75 * size) * size
        if rr < .03:
            continue
        cx, cz = x + drift[0] * t, z + drift[1] * t

        def fn(dr, cx=cx, cz=cz, rr=rr):
            base = fxkit.puff(cx, cz, rr, lobes=lobes, seed=seed, bump=.09)
            stroke(dr, base, .004, mat=m_fill, cyclic=True, fill=True, line=False)
            stroke(dr, fxkit.puff(cx + rr * .14, cz - rr * .17, rr * .6, lobes=lobes - 1, seed=seed + 1, bump=.08), .004, mat=m_shade,
                   cyclic=True, fill=True, line=False)
            stroke(dr, fxkit.puff(cx - rr * .24, cz + rr * .16, rr * .36, lobes=4, seed=seed + 2, bump=.08), .004, mat=m_hi,
                   cyclic=True, fill=True, line=False)
            stroke(dr, base, .009, mat=m_ink, cyclic=True)
        board.add(f0 + k, fn)


def chip_shape(cx, cz, r, rot, seed):
    rnd = random.Random(seed)
    n = rnd.randint(4, 6)
    pts = []
    for i in range(n):
        a = rot + 2 * math.pi * i / n + rnd.uniform(-.4, .4)
        rr = r * rnd.uniform(.62, 1.0)
        pts.append((cx + math.cos(a) * rr, cz + math.sin(a) * rr * .82))
    return pts


def flying(board, f0, life, x0, z0, vx, vz, draw, g=30.0, shrink=.4):
    """Something thrown: a ballistic arc from (x0, z0) at (vx, vz) units/s; it shrinks away over the last part of
    its life (never fades - a fade reads as dirt). draw(dr, x, z, scale, t)."""
    for k in range(life):
        t = k / FPS
        u = k / max(1, life - 1)
        s = 1.0 if u < 1 - shrink else max(0.0, (1 - u) / shrink) ** .8
        if s < .08:
            continue
        x, z = x0 + vx * t, z0 + vz * t - .5 * g * t * t
        board.add(f0 + k, lambda dr, x=x, z=z, s=s, t=t: draw(dr, x, z, s, t))


def chip(board, f0, life, at, v, r, seed, g=30.0):
    """A brick chip, inked, tumbling as it flies."""
    rnd = random.Random(seed)
    spin = rnd.uniform(-14, 14)
    mat = m_chip[seed % 3]
    flying(board, f0, life, at[0], at[1], v[0], v[1],
           lambda dr, x, z, s, t: stroke(dr, chip_shape(x, z, r * s, spin * t, seed), .016, mat=mat, cyclic=True, fill=True), g=g)


def grit(board, f0, life, at, v, r, seed, g=26.0):
    """A crumb of mortar or brick: a tiny solid speck falling."""
    mat = m_grit[seed % 3]
    flying(board, f0, life, at[0], at[1], v[0], v[1],
           lambda dr, x, z, s, t: stroke(dr, ring(x, z, r * s, n=8), .004, mat=mat, cyclic=True, fill=True, line=False), g=g, shrink=.3)


def trickle(board, f0, x0, x1, y_px, n, seed, life=(9, 14), r=(.026, .042)):
    """A few crumbs dropping out of a joint between x0 and x1 (icon px) at y_px."""
    rnd = random.Random(seed)
    for i in range(n):
        x, z = px(rnd.uniform(x0, x1), y_px)
        grit(board, f0 + rnd.randint(0, 4), rnd.randint(*life), (x, z), (rnd.uniform(-.5, .5), rnd.uniform(-.3, .6)),
             rnd.uniform(*r), seed * 31 + i)


def dust(board, f0, life, at_px, scale, drift, seed):
    x, z = px(*at_px)
    cloud(board, f0, life, x, z, scale, drift=drift, seed=seed)


def ticks(board, f0, xs_px, y_px, spread, n=5):
    """Impact ticks: short lines kicked out sideways along the ground under the wall."""
    for k in range(n):
        t = k / (n - 1)
        for xp, side in xs_px:
            x, z = px(xp, y_px)
            board.add(f0 + k, lambda dr, x=x, z=z, s=side, t=t: stroke(
                dr, [(x + s * spread * (.15 + t), z - .05 + .1 * t), (x + s * spread * (.45 + 1.1 * t), z + .02 + .14 * t)],
                .03 * (1 - t) + .006, mat=m_tick))


# --- idle: a puff of mortar where a brick lands, crumbs trickling; the hop kicks dust out of the bottom corners
dust(db, 15, 9, (176, 252), .24, (-.4, .2), 3); trickle(db, 15, 175, 250, 254, 5, 1)
dust(db, 36, 8, (292, 846), .2, (.1, .3), 5); trickle(db, 36, 286, 298, 860, 3, 2)
for side, xp, sd in ((-1, 185, 7), (1, 835, 8)):
    dust(db, IDLE_LAND, 12, (xp, 925), .5, (side * 1.4, .4), sd)
ticks(db, IDLE_LAND, ((205, -1), (815, 1)), 935, .8, n=4)
trickle(db, IDLE_LAND + 1, 180, 300, 254, 3, 9); trickle(db, IDLE_LAND + 2, 700, 840, 256, 3, 10)
trickle(db, 68, 497, 517, 160, 3, 3, life=(10, 15))
dust(db, 79, 9, (842, 254), .24, (.4, .2), 6); trickle(db, 79, 760, 840, 256, 5, 4)
# --- land: dust rolls out from both bottom corners, chips bounce, ticks
for side, xp, s1, s2 in ((-1, 180, 11, 15), (1, 840, 13, 17)):
    dust(db, 102, 13, (xp, 925), .55, (side * 1.6, .45), s1)
    dust(db, 103, 11, (xp + side * 40, 915), .38, (side * 2.1, .25), s2)
    for i in range(3):
        rnd = random.Random(s1 * 7 + i)
        x, z = px(xp - side * rnd.uniform(10, 60), 900)
        chip(db, 103 + i, rnd.randint(11, 15), (x, z), (side * rnd.uniform(1.6, 3.0), rnd.uniform(3.2, 4.6)), rnd.uniform(.09, .13), s1 * 13 + i)
ticks(db, 102, ((200, -1), (820, 1)), 935, 1.0)
trickle(db, 109, 180, 300, 254, 3, 21); trickle(db, 110, 700, 840, 256, 3, 22)
# --- hit: the crack bursts - chips and dust out of it, crumbs from the jumping bricks; the slam squeezes dust out
CRACK_PX = fxkit.resample(CRACK, 80, closed=False)
for i in range(14):
    rnd = random.Random(100 + i)
    x, z = px(*CRACK_PX[int(rnd.uniform(0, .6) * 79)])
    side = -1 if i % 2 else 1
    chip(db, 208 + rnd.randint(0, 2), rnd.randint(16, 22), (x + side * .1, z), (side * rnd.uniform(1.6, 3.8), rnd.uniform(3.4, 6.0)),
         rnd.uniform(.1, .17), 200 + i)
for i, (xp, yp) in enumerate(((507, 150), (597, 262), (630, 375))):
    dust(db, 208 + i, 11 - i, (xp, yp), .5 - .08 * i, ((-1) ** i * .6, 1.3 - .3 * i), 30 + i)
trickle(db, 211, 180, 300, 250, 5, 31, life=(12, 18)); trickle(db, 212, 700, 840, 252, 5, 32, life=(12, 18))
trickle(db, 212, 470, 650, 300, 5, 33, life=(12, 18))
CRACK_ENDS = ((507, 126, -.55, 1.15), (507, 126, .65, .95), (588, 924, -1.0, -.05), (588, 924, 1.0, -.05))
for i, (xp, yp, dx, dz) in enumerate(CRACK_ENDS):     # squeezed out of the crack's two ends as it slams shut
    dust(db, 227 + i % 2, 10, (xp, yp), .4, (dx, dz), 40 + i)
for side, xp in ((-1, 180), (1, 840)):
    dust(db, 227, 13, (xp, 925), .6, (side * 1.8, .5), 50 + side)
    dust(db, 228, 11, (xp + side * 50, 915), .4, (side * 2.3, .3), 52 + side)
ticks(db, 227, ((210, -1), (810, 1)), 935, 1.15, n=6)
for i in range(6):
    rnd = random.Random(300 + i)
    side = -1 if i % 2 else 1
    x, z = px(509 + side * rnd.uniform(200, 330), 905)
    chip(db, 228 + rnd.randint(0, 2), rnd.randint(11, 15), (x, z), (side * rnd.uniform(1.0, 2.6), rnd.uniform(2.8, 4.2)), rnd.uniform(.08, .12), 400 + i)
# --- multi: crumbs shaken loose while it charges; the release blasts dust and chips at the four cells it hits
for f in range(306, 326, 4):
    trickle(db, f, 170, 850, random.Random(f).choice((254, 368, 479, 582, 686)), 2, f)
BLASTS = {"up": ((509, 104), (0, 1), 2.15), "down": ((509, 932), (0, -1), 1.9), "left": ((128, 520), (-1, 0), 2.15),
          "right": ((890, 520), (1, 0), 2.15)}
for j, (name, (at, d, reach)) in enumerate(BLASTS.items()):
    for i in range(2):
        dust(db, 327 + i, 12, (at[0] + d[0] * 25 * i, at[1] - d[1] * 25 * i), .42 - .1 * i,
             (d[0] * (1.3 + .5 * i), d[1] * (1.1 + .4 * i) + .15), 60 + 4 * j + i)
    for i in range(3):
        rnd = random.Random(500 + 10 * j + i)
        x, z = px(*at)
        sp = rnd.uniform(3.6, 5.0)
        a = math.atan2(d[1], d[0]) + rnd.uniform(-.4, .4)
        chip(db, 327 + rnd.randint(0, 1), rnd.randint(10, 13), (x + d[0] * .1, z + d[1] * .1), (math.cos(a) * sp, math.sin(a) * sp + .8),
             rnd.uniform(.09, .14), 600 + 10 * j + i, g=16.0)
for i, (xp, yp, dx, dz) in enumerate(CRACK_ENDS):
    dust(db, 331 + i % 2, 9, (xp, yp), .36, (dx * .9, dz * .9), 80 + i)
for side, xp in ((-1, 180), (1, 840)):
    dust(db, 331, 12, (xp, 925), .5, (side * 1.6, .45), 90 + side)
ticks(db, 331, ((210, -1), (810, 1)), 935, 1.05)
db.draw(gp_layer(dust_ob, "dust"))

# --- glow behind the wall (bloomed): the hit's flash as it cracks; the multi's charge welling up round the wall and
# its burst as it lets go
back = gp_object(FXB, SID + "_back", depth=.35)
ride(back, arm, "chunk")
b_gold = gp_mat(back, "glow_gold_fill", GOLD, fill=GOLD)
b_white = gp_mat(back, "glow_white_fill", WHITE, fill=WHITE)
b_lime = gp_mat(back, "glow_lime_fill", LIME, fill=LIME)
b_lime_line = gp_mat(back, "glow_lime", LIME)
bb = Board()
fxkit.starburst(bb, 208, 11, CX, CZ, 3.2, 6.0, b_gold, b_white, points=14)
fxkit.starburst(bb, 327, 12, CX, CZ, 3.4, 6.2, b_lime, b_white, points=16)
INNER = fxkit.offset(EDGE, -.1)
for f in range(304, 336):
    lv = .25 + 1.1 * smooth(304, 326, f) if f <= 326 else 1.6 * (1 - smooth(327, 335, f))
    lv *= 1 + .12 * math.sin(f * 2.1)
    if lv < .05:
        continue
    bb.add(f, lambda dr, lv=lv: [stroke(dr, INNER, r * (.85 + .2 * min(lv, 1.5)), opacity=min(1, a * lv), mat=b_lime_line, cyclic=True)
                                 for r, a in ((.42, .07), (.32, .085), (.23, .1), (.15, .12))])
bb.draw(gp_layer(back, "burst"))

# --- over the art (bloomed)
fxw = gp_object(FX, SID + "_fx", depth=-.8)                # stays where the frame is
w_white = gp_mat(fxw, "fx_white_line", WHITE); w_lime = gp_mat(fxw, "fx_lime_line", LIME)
w_spark = gp_mat(fxw, "fx_white_fill", WHITE, fill=WHITE); w_gold = gp_mat(fxw, "fx_gold_fill", GOLD, fill=GOLD)
w_limef = gp_mat(fxw, "fx_lime_fill", LIME, fill=LIME)
world = Board()


def burst_lines(board, f0, life, mats, n=18, r0=.12, r1=.75, seed=0, width=.03):
    """Comic impact lines kicked out all round the wall's edge as it cracks or slams."""
    rnd = random.Random(seed)
    for i in range(n):
        x, z = EDGE[int((i + rnd.uniform(-.3, .3)) / n * len(EDGE)) % len(EDGE)]
        nx, nz = x - CX, z - CZ
        L = math.hypot(nx, nz) or 1
        nx, nz = nx / L, nz / L
        ln = rnd.uniform(.7, 1.0)
        for k in range(life):
            t = k / max(1, life - 1)
            a, b = r0 + (r1 - r0) * t * ln, r0 + (r1 - r0) * min(1, t * 1.8 + .25) * ln
            board.add(f0 + k, lambda dr, x=x, z=z, nx=nx, nz=nz, a=a, b=b, t=t, i=i: stroke(
                dr, [(x + nx * a, z + nz * a), (x + nx * b, z + nz * b)], width * (1 - t) + .006, mat=mats[i % len(mats)]))


def arcs(board, f0, f1, mats, step=2, per=3, seed=0, reach=(.7, 1.25)):
    """Arcs of the charge crackling off the wall's sticker edge, forked, redrawn every `step` frames."""
    for f in range(f0, f1 + 1, step):
        rr = random.Random(f * 17 + seed)
        for j in range(per):
            x, z = EDGE[rr.randrange(len(EDGE))]
            nx, nz = x - CX, z - CZ
            L = math.hypot(nx, nz) or 1
            nx, nz = nx / L, nz / L
            x, z = x - nx * .2, z - nz * .2                  # from on the white border itself
            ln = rr.uniform(*reach)
            pts = fxkit.zigzag(x, z, x + nx * ln, z + nz * ln, n=6, amp=.15, seed=f * 7 + j)
            mx, mz = pts[3]
            a = math.atan2(nz, nx) + rr.choice((-1, 1)) * rr.uniform(.5, .9)
            fork = fxkit.zigzag(mx, mz, mx + math.cos(a) * ln * .45, mz + math.sin(a) * ln * .45, n=3, amp=.08, seed=f * 11 + j)
            board.add(f, lambda dr, pts=pts, fork=fork, j=j: (stroke(dr, pts, .032, mat=mats[j % len(mats)]),
                                                              stroke(dr, fork, .022, mat=mats[(j + 1) % len(mats)])), hold=step)


def beam(board, f0, life, at_px, d, length, mats, half=.55):
    """A spike of light shot out of the wall's edge toward a neighbouring cell: out in a few frames, then it thins
    to nothing."""
    x0, z0 = px(*at_px)
    ux, uz = d
    vx, vz = -uz, ux
    for k in range(life):
        t = k / max(1, life - 1)
        L = length * (1 - (1 - min(1.0, t * 2.4)) ** 2)
        w = half * (1 - t) ** 1.25
        if w < .012 or L < .05:
            continue

        def fn(dr, L=L, w=w):
            for mat, ww, ll in ((mats[0], w, L), (mats[1], w * .42, L * .86)):
                stroke(dr, [(x0 + vx * ww, z0 + vz * ww), (x0 + ux * ll * .5 + vx * ww * .5, z0 + uz * ll * .5 + vz * ww * .5),
                            (x0 + ux * ll, z0 + uz * ll), (x0 + ux * ll * .5 - vx * ww * .5, z0 + uz * ll * .5 - vz * ww * .5),
                            (x0 - vx * ww, z0 - vz * ww)], .004, mat=mat, cyclic=True, fill=True, line=False)
        board.add(f0 + k, fn)


fxkit.sparkle(world, 76, 9, *px(507, 128), .38, w_limef)       # idle: the pulse flashes out of the top of the crack
fxkit.sparkle(world, 77, 7, *px(540, 110), .2, w_spark, rot0=.5)
# hit: impact lines as it cracks and as it slams; gold glints for the win
burst_lines(world, 208, 5, (w_white,), seed=1)
burst_lines(world, 227, 5, (w_white,), n=14, seed=2, r1=.6)
rnd = random.Random(7)
for i in range(8):
    fxkit.sparkle(world, 229 + rnd.randint(0, 11), rnd.randint(7, 10), rnd.uniform(-4.6, 4.6), rnd.uniform(-3.6, 4.6),
                  rnd.uniform(.25, .45), w_gold if i % 2 == 0 else w_spark, rot0=rnd.uniform(0, 1))
# multi: arcs crackle off the charged wall, faster as it builds; the release shoots light at the four cells it hits
arcs(world, 310, 318, (w_lime, w_white), step=3, per=2, seed=3)
arcs(world, 319, 326, (w_lime, w_white, w_lime), step=2, per=3, seed=4, reach=(.9, 1.5))
for name, (at, d, reach) in BLASTS.items():
    beam(world, 327, 11, at, d, reach, (w_limef, w_spark))
burst_lines(world, 331, 5, (w_white,), n=14, seed=5, r1=.6)
world.draw(gp_layer(fxw, "fx"))

# --- light out of the crack and through the joints (each riding the part it lies on)
crackfx = gp_object(FX, SID + "_crack", depth=-.8)
ride(crackfx, arm, "chunk")
c_lime = gp_mat(crackfx, "fx_lime_line", LIME); c_white = gp_mat(crackfx, "fx_white_line", WHITE)
c_gold = gp_mat(crackfx, "fx_gold_line", GOLD)
cb = Board()
CRACK_W = [px(x, y) for x, y in CRACK]
for f in range(208, 214):                    # the hit: light flashes out of the crack as it splits
    w = .07 * (1 - (f - 208) / 6) ** 1.3
    cb.add(f, lambda dr, w=w: (stroke(dr, CRACK_W, w, mat=c_gold), stroke(dr, CRACK_W, w * .4, mat=c_white)))
for f in range(304, 336):                    # the multi: the crack glows, brighter and brighter, then flashes out
    if f <= 326:
        w = .008 + .034 * smooth(304, 326, f) * (1 + .18 * math.sin(f * 2.3))
    else:
        w = .08 * (1 - smooth(327, 335, f))
    if w < .004:
        continue
    cb.add(f, lambda dr, w=w: (stroke(dr, CRACK_W, w, mat=c_lime), stroke(dr, CRACK_W, w * .4, mat=c_white)))
CRL = fxkit.resample(CRACK_W, 200, closed=False)
for f in range(61, 78):                      # idle: a pulse of energy runs up the crack, bottom to top
    u = (f - 61) / 16
    head = int((1 - u) * 199)
    seg = CRL[max(0, head - 4):min(200, head + 40)]
    w = .085 * math.sin(math.pi * min(1, u * 1.15)) + .018
    if len(seg) > 1:
        cb.add(f, lambda dr, seg=seg, w=w: (stroke(dr, seg, w, mat=c_lime), stroke(dr, seg, w * .4, mat=c_white)))
CR = fxkit.resample(CRACK_W, 160, closed=False)
for i in range(5):                           # sparks crawling up the crack while it charges
    for f in range(309 + 2 * i, 327):
        u = 1 - ((f - 309 - 2 * i) * .035 + i * .19) % 1
        x, z = CR[int(u * 159)]
        cb.add(f, lambda dr, x=x, z=z, f=f: stroke(dr, star(x, z, .14 + .05 * math.sin(f), f * .5), .004, mat=c_white,
                                                    cyclic=True, fill=True, line=False))
cb.draw(gp_layer(crackfx, "crack"))


def dist_to_crack(line):
    best = 1e9
    for (x, y) in line:
        for (ax, ay), (bx, by) in zip(CRACK, CRACK[1:]):
            dx, dy = bx - ax, by - ay
            t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / max(1e-6, dx * dx + dy * dy)))
            best = min(best, math.hypot(ax + dx * t - x, ay + dy * t - y))
    return best


for part, lines in JOINTS.items():           # the light spreads out from the crack along every joint
    ob = gp_object(FX, f"{SID}_joints_{part}", depth=-.8)
    ride(ob, arm, part)
    j_lime = gp_mat(ob, "fx_lime_line", LIME); j_white = gp_mat(ob, "fx_white_line", WHITE)
    jb = Board()
    for li, line in enumerate(lines):
        pts = [px(x, y) for x, y in line]
        t_on = 305 + 14 * min(1, dist_to_crack(line) / 330)
        for f in range(int(t_on), 336):
            if f <= 326:
                w = .042 * smooth(t_on, t_on + 6, f) * (.55 + .45 * smooth(t_on, 326, f)) * (1 + .18 * math.sin(f * 1.7 + li))
                mats = (j_lime, j_white)
            else:
                w = .066 * (1 - smooth(327, 335, f))                    # it flashes white, then thins to nothing
                mats = (j_white, j_white)
            if w < .004:
                continue
            jb.add(f, lambda dr, pts=pts, w=w, mats=mats: (stroke(dr, pts, w, mat=mats[0]), stroke(dr, pts, w * .38, mat=mats[1])))
    jb.draw(gp_layer(ob, "joints"))

sc.frame_start, sc.frame_end = 1, max(b for a, b in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], "| saved", fxkit.save(SID))
