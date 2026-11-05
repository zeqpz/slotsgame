# Runs INSIDE Blender (tools/blender/chars/boy/run.py). Builds SMUKIEZ (the boy) as a 2D cutout rig:
#   parts     art/blender/chars/boy/parts (prep_parts.py) as unlit image planes in their draw order, each one rigid
#             on its bone at the joints (thigh / shin / shoe, upper arm / forearm / hand, neck, head) - separate
#             pieces overlapping at every joint, never stretched across it. Only the cloth that bends as cloth is
#             skinned: the T-shirt (the chest over the waist, each sleeve with its arm), the beanie (its crown over
#             the cuff, two bones to the slouching tip) and every bill (base / tip, so they flap)
#   armature  master px (y down) -> world: 100 px a unit, x right, z up, the 1024 x 1536 master centred on the
#             origin (fxkit.px / fxkit.vec measure the same way). Bones that are only turned run along their limb;
#             the ones that are moved (root, hips, grip, feet, hands) point up, so their x / y keys are screen
#             right / up. Legs and arms reach their ends (the shin its foot, the forearm its hand on the money):
#             solved per frame in anim_boy.py (two-bone, in the picture plane) and keyed as plain turns
#   faces     seven head objects, one per expression, their visibility keyed per clip
#   camera    ONE fixed orthographic camera for every clip: 720 x 1200, the standing figure 1000 px tall (1/1.2 of
#             the frame), soles 1.5 % above the bottom edge, centred
#   mask      every part's material mixes to a flat mask colour (shoes white, the rest black) when the shared
#             "BOY_mask" node group's value is 1: the shoe pass for the game's unlit layer
import bpy, json, math, os, sys
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, os.path.join(ROOT, "tools", "blender"))
import fxkit                    # noqa: E402  (read-only: px / vec / secondary / Board)

SID = "BOY"
PARTS = os.path.join(ROOT, "art", "blender", "chars", "boy", "parts")
PARTS4 = os.path.join(ROOT, "art", "blender", "chars", "boy", "parts_4x")
spec = json.load(open(os.path.join(PARTS, "parts.json")))
W, H = spec["size"]
fxkit.ICON[0], fxkit.ICON[1] = W, H
PX = 100.0
DEPTH = 0.1
RES = (1440, 2400)                                   # the 2x master (packed down for each screen)
REST_PX = RES[1] / 1.2                              # the standing figure's height on screen
FAN = spec["fan"]
NB = len(FAN["angles"])


def w(x, y):
    return Vector(((x - W / 2) / PX, 0.0, (H / 2 - y) / PX))


def rot_screen(p, c, deg):
    """rotate p about c by deg, counter-clockwise on screen (y down)"""
    a = math.radians(deg); x, y = p[0] - c[0], p[1] - c[1]
    return (c[0] + x * math.cos(a) + y * math.sin(a), c[1] - x * math.sin(a) + y * math.cos(a))


PIV = tuple(FAN["pivot"]); C0 = FAN["front_centre"]; BW, BH = FAN["size"]; ANG = FAN["front_angle"]; PAD = FAN["pad"]


def bill_xy(k, u, v):
    """bill k (0 back .. 5 front): px (u, v) of the upright bill image -> master px"""
    th = FAN["angles"][NB - 1 - k]
    x = C0[0] - (BW / 2 + PAD) + u; y = C0[1] - (BH / 2 + PAD) + v
    q = rot_screen((x, y), C0, -ANG)
    return rot_screen(q, PIV, th)


def bill_points(k):
    return bill_xy(k, PAD + BW / 2, PAD), bill_xy(k, PAD + BW / 2, PAD + BH * .5)


# ---------------------------------------------------------------- joints (master px)
J = dict(ground=(507.5, spec["rest_box"][3]), hips=(482, 1040), waist=(480, 1012), chest=(468, 880),
         collar=(455, 785), neck_top=(462, 712), head_top=(470, 330),
         cuff=(478, 372), cap_mid=(425, 205), cap_top=(338, 80),
         shoulder_l=(318, 800), elbow_l=(300, 932), wrist_l=(456, 928),
         shoulder_r=(622, 800), elbow_r=(626, 880), wrist_r=(668, 925),
         hip_l=(395, 1042), knee_l=(356, 1158), ankle_l=(338, 1278),
         hip_r=(548, 1048), knee_r=(580, 1168), ankle_r=(585, 1300))

UP = None
BONES = [  # name, head, tail (None: points up), parent, connected
    ("root", J["ground"], UP, None, False),
    ("hips", J["hips"], UP, "root", False),               # the acting
    ("body", J["hips"], UP, "hips", False),               # keyed by the leg guard only: drops the hips where a
                                                          # leg would have to reach past its drawn length
    ("torso", J["waist"], J["chest"], "body", False),
    ("chest", J["chest"], (458, 772), "torso", False),
    ("neck", J["collar"], J["neck_top"], "chest", False),
    ("head", J["neck_top"], UP, "neck", False),           # the acting (turns about the chin / neck top)
    ("head_fx", J["neck_top"], J["head_top"], "head", False),   # its follow-through (springs, fxkit.secondary)
    ("beanie", J["cuff"], UP, "head_fx", False),
    ("cap.0", J["cuff"], J["cap_mid"], "beanie", False),
    ("cap.1", J["cap_mid"], J["cap_top"], "cap.0", True),
    ("arm_l_upper", J["shoulder_l"], J["elbow_l"], "chest", False),
    ("arm_l_fore", J["elbow_l"], J["wrist_l"], "arm_l_upper", True),
    ("arm_r_upper", J["shoulder_r"], J["elbow_r"], "chest", False),
    ("arm_r_fore", J["elbow_r"], J["wrist_r"], "arm_r_upper", True),
    ("grip", PIV, UP, "chest", False),
    ("hand_l", J["wrist_l"], UP, "grip", False),
    ("hand_r", J["wrist_r"], UP, "grip", False),
    ("thigh_l", J["hip_l"], J["knee_l"], "body", False),
    ("shin_l", J["knee_l"], J["ankle_l"], "thigh_l", True),
    ("thigh_r", J["hip_r"], J["knee_r"], "body", False),
    ("shin_r", J["knee_r"], J["ankle_r"], "thigh_r", True),
    ("foot_l", J["ankle_l"], UP, "root", False),
    ("foot_r", J["ankle_r"], UP, "root", False),
]
for k in range(NB):
    top, mid = bill_points(k)
    BONES.append((f"bill_{k}", PIV, UP, "grip", False))                 # the acting (the fan opens / closes)
    BONES.append((f"billfx_{k}.0", PIV, mid, f"bill_{k}", False))         # its flap (springs)
    BONES.append((f"billfx_{k}.1", mid, top, f"billfx_{k}.0", True))
THROWN = 5                                          # loose bills (big_win makes it rain)
for k in range(THROWN):
    BONES.append((f"toss_{k}", C0, UP, None, False))     # free of the rig: flung, they fly on their own

RIGID = {"neck": "neck", "arm_r_upper": "arm_r_upper", "arm_r_fore": "arm_r_fore", "pelvis": "body",
         "shoe_l": "foot_l", "shoe_r": "foot_r", "shin_l": "shin_l", "shin_r": "shin_r", "thigh_l": "thigh_l",
         "thigh_r": "thigh_r", "arm_l_upper": "arm_l_upper", "arm_l_fore": "arm_l_fore", "head": "head_fx",
         "hand_l": "hand_l", "hand_r": "hand_r"}


def sstep(e0, e1, v):
    t = max(0.0, min(1.0, (v - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def torso_weights(x, y):
    """the shirt: the waist bone below the chest, the chest above (blended over 140 px); each sleeve goes with
    its upper arm from the shoulder seam to the hem, so sleeve and arm never part"""
    c = sstep(J["chest"][1] + 70, J["chest"][1] - 70, y)
    out = {"torso": 1 - c, "chest": c}
    sl = sstep(J["shoulder_l"][0] + 40, J["shoulder_l"][0] + 5, x) * sstep(J["shoulder_l"][1] - 10, J["shoulder_l"][1] + 50, y)
    sr = sstep(J["shoulder_r"][0] - 40, J["shoulder_r"][0] - 5, x) * sstep(J["shoulder_r"][1] - 10, J["shoulder_r"][1] + 40, y)
    sl, sr = .85 * sl, .85 * sr
    k = 1 - sl - sr
    out = {b: v * k for b, v in out.items()}
    out["arm_l_upper"] = sl
    out["arm_r_upper"] = sr
    return out


def beanie_weights(x, y):
    """the cuff rides the head; the crown above the cuff's top edge bends over two bones to the slouching tip"""
    line = 410 - 70 * (x - 170) / 590               # the cuff's top edge (y at x)
    h = line - y                                    # px above it
    a = sstep(-10, 45, h)
    b = sstep(120, 220, h)
    return {"beanie": 1 - a, "cap.0": a * (1 - b), "cap.1": a * b}


def bill_weights(k):
    top, mid = bill_points(k)
    ax = (top[0] - PIV[0], top[1] - PIV[1]); L = math.hypot(*ax)
    ax = (ax[0] / L, ax[1] / L)

    def f(x, y):
        z = ((x - PIV[0]) * ax[0] + (y - PIV[1]) * ax[1]) / L      # 0 at the pivot .. 1 at the top
        t = sstep(.42, .9, z)
        return {f"billfx_{k}.0": 1 - t, f"billfx_{k}.1": t}
    return f


# ---------------------------------------------------------------- scene
sc = fxkit.use_scene(SID)
for o in list(sc.collection.all_objects):
    bpy.data.objects.remove(o, do_unlink=True)
for coll in list(sc.collection.children):
    sc.collection.children.unlink(coll)
sc.render.engine = "BLENDER_EEVEE"
try:
    sc.eevee.taa_render_samples = 32
except Exception:
    pass
sc.render.film_transparent = True
sc.render.fps = 30
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
sc.render.image_settings.color_depth = "8"
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
sc.render.use_compositing = False

# the camera: fixed for every clip
rb = spec["rest_box"]
rest_h = rb[3] - rb[1]                              # master px, beanie top to soles
s = REST_PX / rest_h                                # screen px per master px
cam_data = bpy.data.cameras.new(SID + "_cam")
cam_data.type = "ORTHO"
cam_data.sensor_fit = "VERTICAL"
cam_data.ortho_scale = RES[1] / s / PX
cam = bpy.data.objects.new(SID + "_cam", cam_data)
sc.collection.objects.link(cam)
ground_y = RES[1] * (1 - .015)                      # the soles on screen (px, y down)
cx = (rb[0] + rb[2]) / 2
cam.location = (w(cx, 0).x, -40, w(0, rb[3]).z + (ground_y - RES[1] / 2) / s / PX)
cam.rotation_euler = (math.radians(90), 0, 0)
cam_data.clip_start, cam_data.clip_end = .1, 100
sc.camera = cam

# ---------------------------------------------------------------- armature
arm_data = bpy.data.armatures.new(SID + "_rig")
arm = bpy.data.objects.new(SID + "_rig", arm_data)
sc.collection.objects.link(arm)
arm.show_in_front = True
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
eb = arm_data.edit_bones
toward_cam = Vector((0, -1, 0))
for name, head, tail, parent, conn in BONES:
    b = eb.new(name)
    b.head = w(*head)
    if tail is None:
        b.tail = b.head + Vector((0, 0, .6))
        b.roll = 0
    else:
        b.tail = w(*tail)
        b.align_roll(toward_cam)
    if parent:
        b.parent = eb[parent]
        b.use_connect = conn
bpy.ops.object.mode_set(mode="OBJECT")
for pb in arm.pose.bones:
    pb.rotation_mode = "XYZ"
arm_data.bones["arm_r_fore"].inherit_scale = "NONE"   # the hidden arm stretches bone by bone (no shear)

# ---------------------------------------------------------------- materials
mask_ng = bpy.data.node_groups.get(SID + "_mask") or bpy.data.node_groups.new(SID + "_mask", "ShaderNodeTree")
mask_ng.nodes.clear()
if not any(getattr(i, "in_out", "") == "OUTPUT" for i in mask_ng.interface.items_tree):
    mask_ng.interface.new_socket("Value", in_out="OUTPUT", socket_type="NodeSocketFloat")
mv = mask_ng.nodes.new("ShaderNodeValue"); mv.name = "mask"; mv.outputs[0].default_value = 0.0
go = mask_ng.nodes.new("NodeGroupOutput")
mask_ng.links.new(mv.outputs[0], go.inputs[0])


def material(name, file, mask_white=False):
    hi = os.path.join(PARTS4, file)                 # the 4x textures (hires_parts.py), same geometry
    img = bpy.data.images.load(hi if os.path.exists(hi) else os.path.join(PARTS, file), check_existing=True)
    img.reload()
    img.alpha_mode = "STRAIGHT"
    mat = bpy.data.materials.get(SID + "_" + name) or bpy.data.materials.new(SID + "_" + name)
    mat.use_nodes = True
    mat.surface_render_method = "BLENDED"
    mat.use_backface_culling = False
    nt = mat.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; tex.interpolation = "Cubic"; tex.extension = "CLIP"
    grp = nt.nodes.new("ShaderNodeGroup"); grp.node_tree = mask_ng
    mix_c = nt.nodes.new("ShaderNodeMix"); mix_c.data_type = "RGBA"
    nt.links.new(grp.outputs[0], mix_c.inputs["Factor"])
    sock = lambda socks, ident: next(x for x in socks if x.identifier == ident)
    nt.links.new(tex.outputs["Color"], sock(mix_c.inputs, "A_Color"))
    sock(mix_c.inputs, "B_Color").default_value = (1, 1, 1, 1) if mask_white else (0, 0, 0, 1)
    emit = nt.nodes.new("ShaderNodeEmission")
    clear = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(sock(mix_c.outputs, "Result_Color"), emit.inputs["Color"])
    nt.links.new(tex.outputs["Alpha"], mix.inputs["Fac"])
    nt.links.new(clear.outputs[0], mix.inputs[1])
    nt.links.new(emit.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return mat, img


def grid(name, box, cell, uvmap, xy):
    """a fine grid over box (in its own px), uv from uvmap(px), placed by xy(px) -> master px"""
    x0, y0, x1, y1 = box
    nx, ny = max(2, round((x1 - x0) / cell)), max(2, round((y1 - y0) / cell))
    verts, uvs, pts = [], [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            u, v = x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny
            X, Y = xy(u, v)
            p = w(X, Y)
            verts.append((p.x, 0.0, p.z)); uvs.append(uvmap(u, v)); pts.append((X, Y))
    faces = []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a + nx + 1, a + nx + 2, a + 1, a))
    me = bpy.data.meshes.new(SID + "_" + name)
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new()
    for poly in me.polygons:
        for li in poly.loop_indices:
            uv.data[li].uv = uvs[me.loops[li].vertex_index]
    return me, pts


def place_rigid(ob, bone, depth):
    ob.parent, ob.parent_type, ob.parent_bone = arm, "BONE", bone
    bpy.context.view_layer.update()
    ob.matrix_world = Matrix.Translation((0, depth, 0))


def place_skinned(ob, pts, weights, depth):
    ob.parent = arm
    ob.matrix_world = Matrix.Translation((0, depth, 0))
    groups = {}
    for vi, (x, y) in enumerate(pts):
        for bone, wt in weights(x, y).items():
            if wt > 1e-4:
                if bone not in groups:
                    groups[bone] = ob.vertex_groups.new(name=bone)
                groups[bone].add([vi], wt, "REPLACE")
    mod = ob.modifiers.new("rig", "ARMATURE")
    mod.object = arm
    mod.use_vertex_groups = True


def box_grid(name, box, cell):
    x0, y0, x1, y1 = box
    return grid(name, box, cell, lambda u, v: ((u - x0) / (x1 - x0), 1 - (v - y0) / (y1 - y0)), lambda u, v: (u, v))


bpy.context.view_layer.update()
SKIN = {"torso": torso_weights, "beanie": beanie_weights}
objs = {}
for p in spec["parts"]:
    name, d = p["name"], p["draw"]
    depth = -DEPTH * (d + 1)
    if name == "bills":
        bw, bh = spec["bill_size"]
        for k in range(NB):
            mat, _ = material(f"bill_{k}", "bill.png")
            me, pts = grid(f"bill_{k}", (0, 0, bw, bh), 12, lambda u, v: (u / bw, 1 - v / bh), lambda u, v, k=k: bill_xy(k, u, v))
            me.materials.append(mat)
            ob = bpy.data.objects.new(SID + f"_bill_{k}", me)
            sc.collection.objects.link(ob)
            place_skinned(ob, pts, bill_weights(k), -DEPTH * (d + 1 + .15 * k))
            objs[f"bill_{k}"] = ob
        continue
    if name == "head":
        for f in spec["faces"]:
            box = spec["head_boxes"][f]
            mat, _ = material("head_" + f, "head_" + f + ".png")
            me, _ = box_grid("head_" + f, box, 1e9)
            me.materials.append(mat)
            ob = bpy.data.objects.new(SID + "_head_" + f, me)
            sc.collection.objects.link(ob)
            place_rigid(ob, "head_fx", depth)
            ob.hide_render = ob.hide_viewport = f != "idle"
            objs["head_" + f] = ob
        continue
    mat, _ = material(name, name + ".png", mask_white=name.startswith("shoe"))
    if name in SKIN:
        me, pts = box_grid(name, p["box"], 8)
        me.materials.append(mat)
        ob = bpy.data.objects.new(SID + "_" + name, me)
        sc.collection.objects.link(ob)
        place_skinned(ob, pts, SKIN[name], depth)
    else:
        me, _ = box_grid(name, p["box"], 1e9)
        me.materials.append(mat)
        ob = bpy.data.objects.new(SID + "_" + name, me)
        sc.collection.objects.link(ob)
        place_rigid(ob, RIGID[name], depth)
    objs[name] = ob

# loose bills (hidden until a clip throws them)
bw, bh = spec["bill_size"]
for k in range(THROWN):
    mat, _ = material(f"toss_{k}", "bill.png")
    me, _ = grid(f"toss_{k}", (0, 0, bw, bh), 1e9, lambda u, v: (u / bw, 1 - v / bh),
                 lambda u, v: (C0[0] - bw / 2 + u, C0[1] - bh / 2 + v))
    me.materials.append(mat)
    ob = bpy.data.objects.new(SID + f"_toss_{k}", me)
    sc.collection.objects.link(ob)
    place_rigid(ob, f"toss_{k}", -DEPTH * (len(spec["parts"]) + 2 + .08 * k))   # thrown: in front of him
    ob.hide_render = ob.hide_viewport = True
    objs[f"toss_{k}"] = ob

bpy.context.view_layer.update()
arm["px_per_unit"] = PX
arm["screen_scale"] = s
arm["ground_y"] = ground_y
arm["rest_px"] = REST_PX
print(SID, "scene:", len(objs), "objects,", len(arm_data.bones), "bones; ortho", round(cam_data.ortho_scale, 3),
      "cam", tuple(round(v, 3) for v in cam.location))
