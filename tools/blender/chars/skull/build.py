# SMOKE SKULL - the cut-out scene, built INSIDE Blender (tools/blender/chars/skull/run.py runs it in a background Blender).
# The parts (art/blender/chars/skull/parts, made by parts.py) as unlit image planes in their draw order, on a 2D armature:
#   rigid pieces ride one bone each (legs: thigh / shin / cuff / shoe per side; arms: upper / fore; head, jaw, cigar ...);
#   the cloth and cords bend (a fine grid skinned to a chain of bones): the hoodie body (hem -> chest), the beanie
#   (brim -> crown -> tip), the two drawstrings and the four free lace ends.
# One orthographic camera for every clip: frame 720 x 1200 (w:h 0.6), the standing figure 1000 px tall (1/1.2 of the
# frame), soles 1.5 % above the bottom edge, centred across. Transparent film.
# Units: 100 master px = 1 Blender unit, the master (1024 x 1536) centred on the origin, x right, z up, the camera
# looking along +y. Bones: all rigid bones point up (roll 0): location x/y = right/up, rotation z = turn counter-
# clockwise in the picture, scale x/y. Draw order = depth, 0.1 unit toward the camera per step.
import bpy, json, math, os, sys
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
PARTS = os.path.join(REPO, "art", "blender", "chars", "skull", "parts")
SID = "SKULL"
spec = json.load(open(os.path.join(PARTS, "parts.json")))
W, H = spec["size"]
JN = spec["joints"]
PX = 100.0
DEPTH = 0.1
RES = (720, 1200)


def wpt(x, y):
    return Vector(((x - W / 2) / PX, 0.0, (H / 2 - y) / PX))


def sstep(e0, e1, v):
    t = max(0.0, min(1.0, (v - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------- scene
sc = bpy.context.scene
sc.name = SID
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
sc.render.engine = "BLENDER_EEVEE"
sc.render.film_transparent = True
sc.render.fps = 30
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
sc.render.image_settings.color_depth = "8"
sc.render.filter_size = 1.0                        # crisp ink (the default 1.5 px filter softens the lines)
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
try:
    sc.eevee.taa_render_samples = 16
except Exception:
    pass

# ---------------------------------------------------------------------------- camera
fx0, fy0, fx1, fy1 = spec["figure_box"]            # the standing figure (master px): beanie top .. soles
fig_h = fy1 - fy0
k = 1000.0 / fig_h                                 # out px per master px
frame_h_units = RES[1] / k / PX
cam_py = fy1 - (RES[1] * (1 - .015) - RES[1] / 2) / k
cam_px = (fx0 + fx1) / 2
cd = bpy.data.cameras.new(SID + "_cam")
cd.type = "ORTHO"
cd.ortho_scale = frame_h_units
cd.sensor_fit = "VERTICAL"
cam = bpy.data.objects.new(SID + "_cam", cd)
sc.collection.objects.link(cam)
c = wpt(cam_px, cam_py)
cam.location = (c.x, -30, c.z)
cam.rotation_euler = (math.radians(90), 0, 0)
sc.camera = cam
CAMINFO = dict(k=k, cam_px=cam_px, cam_py=cam_py, rest_height_px=round(fig_h * k), ground_y=round(RES[1] / 2 + (fy1 - cam_py) * k, 1))

# ---------------------------------------------------------------------------- armature
RIGID = [  # name, parent
    ("root", None), ("pelvis", "root"), ("torso", "pelvis"), ("chest", "torso"), ("neck", "chest"), ("head", "neck"),
    ("jaw", "head"), ("cigar", "head"), ("ember", "cigar"), ("pocket", "torso"), ("hood", "chest"),
    ("arm_l_upper", "chest"), ("arm_l_fore", "arm_l_upper"), ("arm_r_upper", "chest"), ("arm_r_fore", "arm_r_upper"),
    ("thigh_l", "pelvis"), ("shin_l", "thigh_l"), ("cuff_l", "shin_l"), ("shoe_l", "shin_l"),
    ("thigh_r", "pelvis"), ("shin_r", "thigh_r"), ("cuff_r", "shin_r"), ("shoe_r", "shin_r"),
]
CHAINS = {p["name"]: (p["chain"], p["parent"]) for p in spec["parts"] if p.get("chain")}
ad = bpy.data.armatures.new(SID + "_rig")
arm = bpy.data.objects.new(SID + "_rig", ad)
sc.collection.objects.link(arm)
arm.show_in_front = True
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
eb = ad.edit_bones
for name, parent in RIGID:
    b = eb.new(name)
    b.head = wpt(*JN[name])
    b.tail = b.head + Vector((0, 0, .6))
    b.roll = 0
    if parent:
        b.parent = eb[parent]
for name, (ch, parent) in CHAINS.items():
    prev = None
    for i in range(len(ch) - 1):
        b = eb.new(f"{name}.{i}")
        b.head, b.tail = wpt(*ch[i]), wpt(*ch[i + 1])
        b.align_roll(Vector((0, -1, 0)))
        b.parent = prev or eb[parent]
        b.use_connect = prev is not None
        prev = b
bpy.ops.object.mode_set(mode="OBJECT")
for pb in arm.pose.bones:
    pb.rotation_mode = "XYZ"


# ---------------------------------------------------------------------------- materials: the picture, or the unlit mask
def material(name, unlit):
    """unlit image: its colour (mode 0) or, for the mask pass (mode 1), white if this part is one the rim light skips,
    black if not (it still covers what is behind it). 'mode' is a Value node set by the renderer."""
    img = bpy.data.images.load(os.path.join(PARTS, name + ".png"), check_existing=True)
    img.alpha_mode = "STRAIGHT"
    mat = bpy.data.materials.new(SID + "_" + name)
    mat.use_nodes = True
    mat.surface_render_method = "BLENDED"
    mat.use_backface_culling = False
    nt = mat.node_tree
    nt.nodes.clear()
    N, Lk = nt.nodes, nt.links
    tex = N.new("ShaderNodeTexImage"); tex.image = img; tex.interpolation = "Linear"; tex.extension = "CLIP"
    mode = N.new("ShaderNodeValue"); mode.name = mode.label = "mode"; mode.outputs[0].default_value = 0.0
    mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"
    cin = [s for s in mix.inputs if s.type == "RGBA"]
    Lk.new(mode.outputs[0], mix.inputs[0])
    Lk.new(tex.outputs["Color"], cin[0])
    cin[1].default_value = (1, 1, 1, 1) if unlit else (0, 0, 0, 1)
    emit = N.new("ShaderNodeEmission")
    Lk.new(next(s for s in mix.outputs if s.type == "RGBA"), emit.inputs["Color"])
    clear = N.new("ShaderNodeBsdfTransparent")
    sh = N.new("ShaderNodeMixShader")
    Lk.new(tex.outputs["Alpha"], sh.inputs["Fac"])
    Lk.new(clear.outputs[0], sh.inputs[1])
    Lk.new(emit.outputs[0], sh.inputs[2])
    out = N.new("ShaderNodeOutputMaterial")
    Lk.new(sh.outputs[0], out.inputs["Surface"])
    return mat


def plane_mesh(p):
    x0, y0, x1, y1 = p["box"]
    a, b = wpt(x0, y1), wpt(x1, y0)
    me = bpy.data.meshes.new(SID + "_" + p["name"])
    me.from_pydata([(a.x, 0, a.z), (b.x, 0, a.z), (b.x, 0, b.z), (a.x, 0, b.z)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    for i, cc in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[i].uv = cc
    return me


def grid_mesh(p, cell=6):
    x0, y0, x1, y1 = p["box"]
    nx, ny = max(2, math.ceil((x1 - x0) / cell)), max(2, math.ceil((y1 - y0) / cell))
    verts, uvs, pts = [], [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x, y = x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny
            v = wpt(x, y)
            verts.append((v.x, 0.0, v.z)); uvs.append((i / nx, 1 - j / ny)); pts.append((x, y))
    faces = []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a + nx + 1, a + nx + 2, a + 1, a))
    me = bpy.data.meshes.new(SID + "_" + p["name"])
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new()
    for poly in me.polygons:
        for li in poly.loop_indices:
            uv.data[li].uv = uvs[me.loops[li].vertex_index]
    return me, pts


def chain_w(ch, x, y, blend):
    """weights of a chain's bones for a point: where it falls along the chain, blended over `blend` px at each joint"""
    best, s_at, acc, joints = None, 0.0, 0.0, [0.0]
    for i in range(len(ch) - 1):
        (ax, ay), (bx, by) = ch[i], ch[i + 1]
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy)
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (L * L)))
        d = math.hypot(ax + dx * t - x, ay + dy * t - y)
        if best is None or d < best:
            best, s_at = d, acc + t * L
        acc += L
        joints.append(acc)
    n = len(ch) - 1
    out = []
    for i in range(n):
        lo = 1.0 if i == 0 else sstep(joints[i] - blend / 2, joints[i] + blend / 2, s_at)
        hi = 1.0 if i == n - 1 else 1 - sstep(joints[i + 1] - blend / 2, joints[i + 1] + blend / 2, s_at)
        out.append(lo * hi)
    tot = sum(out) or 1.0
    return [v / tot for v in out], s_at


def weights_for(p):
    n = p["name"]
    if n == "torso":
        # the hoodie: the hem rides the torso bone, the chest and shoulders the chest bone, a soft blend between
        return lambda x, y: {"torso": sstep(830, 945, y), "chest": 1 - sstep(830, 945, y)}
    if n == "beanie":
        ch = p["chain"]
        def f(x, y):
            ws, s = chain_w(ch, x, y, 50)
            # the brim and the knit hanging down the side stay on the head; the crown and the tip flop
            hold = 1 - sstep(330, 250, y)
            out = {"head": hold}
            for i, wv in enumerate(ws):
                out[f"beanie.{i}"] = (1 - hold) * wv
            return out
        return f
    ch = p["chain"]
    blend = 26 if n.startswith("lace") else 22
    def f(x, y):
        ws, s = chain_w(ch, x, y, blend)
        root = 1 - sstep(2, 10, s)        # the very root sits on its holder (the lace's knot, the string's eyelet)
        out = {p["parent"]: root}
        for i, wv in enumerate(ws):
            out[f"{n}.{i}"] = (1 - root) * wv
        return out
    return f


PARTOBJ = {}
for p in spec["parts"]:
    name = p["name"]
    skinned = p.get("chain") or p.get("skin")
    if skinned:
        me, pts = grid_mesh(p, 5 if name.startswith(("lace", "string")) else 7)
    else:
        me = plane_mesh(p)
    me.materials.append(material(name, p.get("unlit", False)))
    ob = bpy.data.objects.new(SID + "_" + name, me)
    sc.collection.objects.link(ob)
    depth = -DEPTH * (p["draw"] + 1)
    if skinned:
        ob.parent = arm
        ob.matrix_world = Matrix.Translation((0, depth, 0))
        wf = weights_for(p)
        groups = {}
        for vi, (x, y) in enumerate(pts):
            for bone, wv in wf(x, y).items():
                if wv > 1e-4:
                    if bone not in groups:
                        groups[bone] = ob.vertex_groups.new(name=bone)
                    groups[bone].add([vi], wv, "REPLACE")
        mod = ob.modifiers.new("rig", "ARMATURE")
        mod.object = arm
        mod.use_vertex_groups = True
    else:
        ob.parent, ob.parent_type, ob.parent_bone = arm, "BONE", p["bone"]
        bpy.context.view_layer.update()
        ob.matrix_world = Matrix.Translation((0, depth, 0))
    PARTOBJ[name] = ob
bpy.context.view_layer.update()
arm["caminfo"] = CAMINFO
print(SID, "built:", len(spec["parts"]), "parts,", len(ad.bones), "bones | camera", CAMINFO, flush=True)
