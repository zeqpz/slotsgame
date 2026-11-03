# Runs INSIDE Blender (MCP for Blender execute_code, or Blender's Text Editor). Builds one symbol's 2D cutout
# scene: its parts (art/blender/parts/<ID>, tools/blender/dump_parts.py) as unlit image planes in their draw
# order, a 2D armature with a bone per part at the part's pivot, an orthographic camera on a transparent film.
# A rigid part rides its bone. A part that bends (a "chain" in parts.json) is a fine mesh with a chain of bones
# down its length, weighted smoothly along it (Armature modifier), so it curls like a rope; its "rim" (the
# sticker border drawn behind) uses the same bones. A part held at one end ("anchor") is weighted from the
# holding bone at its foot to its own bone above. The animation is then keyed in Blender on the bones.
# The symbol comes from the SMK_SID environment variable (tools/blender/run.py sets it; default H1). Works in
# the Blender window (MCP for Blender) and in a background Blender alike.
import bpy, json, os, math, sys
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
import fxkit                    # noqa: E402
SID = os.environ.get("SMK_SID", "H1")
PARTS_DIR = os.path.join(os.path.dirname(os.path.dirname(HERE)), "art", "blender", "parts", SID)
PX = 100.0                      # icon px per Blender unit: the 1000 px icon is 10 units across
CELL = 8.0                      # icon px per grid cell on a bending part
BLEND = 48.0                    # icon px over which neighbouring chain bones share a vertex (a rope curves, never creases)
DEPTH = 0.1                     # units toward the camera per step of draw order (Eevee sorts the see-through
                                # parts by distance: a wide step keeps the order however the parts move)

spec = json.load(open(os.path.join(PARTS_DIR, "parts.json")))
W, H = spec["size"]
def w(x, y):                    # icon px (y down) -> world (x right, z up), icon centred on the origin
    return Vector(((x - W / 2) / PX, 0.0, (H / 2 - y) / PX))
parts = {p["name"]: p for p in spec["parts"]}

# ---- the scene: its own, so whatever else is open stays as it was
sc = fxkit.use_scene(SID)
for o in list(sc.collection.all_objects):
    bpy.data.objects.remove(o, do_unlink=True)
for coll in list(sc.collection.children):
    sc.collection.children.unlink(coll)
sc.render.engine = "BLENDER_EEVEE"
sc.render.film_transparent = True
sc.render.fps = 30
sc.render.resolution_x = sc.render.resolution_y = 512
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
sc.view_settings.view_transform = "Standard"     # the art's own colours, untouched
sc.view_settings.look = "None"
sc.frame_start, sc.frame_end = 1, 72

cam_data = bpy.data.cameras.new(SID + "_cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = 13.0     # the 10-unit icon with room round it for motion and effects
cam = bpy.data.objects.new(SID + "_cam", cam_data)
sc.collection.objects.link(cam)
cam.location = (0, -30, 0)
cam.rotation_euler = (math.radians(90), 0, 0)
sc.camera = cam

# ---- the armature: a bone per rigid part at its pivot, a chain of bones down each bending part
arm_data = bpy.data.armatures.new(SID + "_rig")
arm = bpy.data.objects.new(SID + "_rig", arm_data)
sc.collection.objects.link(arm)
arm.show_in_front = True
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
eb = arm_data.edit_bones
toward_cam = Vector((0, -1, 0))
for p in spec["parts"]:
    if p.get("bones_of"):
        continue
    if p.get("chain"):
        ch = p["chain"]
        prev = None
        for i in range(len(ch) - 1):
            b = eb.new(f"{p['name']}.{i}")
            b.head, b.tail = w(*ch[i]), w(*ch[i + 1])
            b.align_roll(toward_cam)        # local Z at the camera: turning it is a turn in the picture
            if prev:
                b.parent, b.use_connect = prev, True
            prev = b
    else:
        b = eb.new(p["name"])
        b.head = w(*p["pivot"])
        b.tail = b.head + Vector((0, 0, 0.6))
        b.roll = 0
for p in spec["parts"]:
    if p["parent"] and not p.get("bones_of"):
        root = eb[f"{p['name']}.0"] if p.get("chain") else eb[p["name"]]
        root.parent = eb[p["parent"]]
bpy.ops.object.mode_set(mode="OBJECT")
for pb in arm.pose.bones:
    pb.rotation_mode = "XYZ"    # 2D: Z turns the part in the picture, X/Y scale it


def material(p):
    img = bpy.data.images.load(os.path.join(PARTS_DIR, p["name"] + ".png"), check_existing=True)
    img.reload()
    img.alpha_mode = "STRAIGHT"
    mat = bpy.data.materials.get(SID + "_" + p["name"]) or bpy.data.materials.new(SID + "_" + p["name"])
    mat.use_nodes = True
    mat.surface_render_method = "BLENDED"
    mat.use_backface_culling = False
    nt = mat.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; tex.interpolation = "Cubic"; tex.extension = "CLIP"
    emit = nt.nodes.new("ShaderNodeEmission")
    clear = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tex.outputs["Color"], emit.inputs["Color"])
    nt.links.new(tex.outputs["Alpha"], mix.inputs["Fac"])
    nt.links.new(clear.outputs[0], mix.inputs[1])
    nt.links.new(emit.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return mat


def chain_weights(ch, x, y):
    """Weights of the chain's bones for a point (icon px): where it falls along the chain, blended across each
    joint over BLEND px, so the part bends smoothly instead of kinking."""
    best, s_at, acc = None, 0.0, 0.0
    joints = [0.0]
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
    def step(v):
        v = max(0.0, min(1.0, v))
        return v * v * (3 - 2 * v)
    out = []
    for i in range(n):
        lo = 1.0 if i == 0 else step((s_at - (joints[i] - BLEND / 2)) / BLEND)
        hi = 1.0 if i == n - 1 else 1 - step((s_at - (joints[i + 1] - BLEND / 2)) / BLEND)
        out.append(lo * hi)
    tot = sum(out) or 1.0
    return [v / tot for v in out]


def grid_mesh(p):
    x0, y0, x1, y1 = p["box"]
    nx, ny = max(2, round((x1 - x0) / CELL)), max(2, round((y1 - y0) / CELL))
    verts, faces, uvs = [], [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x, y = x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny
            v = w(x, y)
            verts.append((v.x, 0.0, v.z))
            uvs.append((i / nx, 1 - j / ny))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a + nx + 1, a + nx + 2, a + 1, a))          # wound to face the camera, like the planes
    me = bpy.data.meshes.new(SID + "_" + p["name"])
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new()
    for poly in me.polygons:
        for li in poly.loop_indices:
            uv.data[li].uv = uvs[me.loops[li].vertex_index]
    return me


def plane(p):
    x0, y0, x1, y1 = p["box"]
    a, b = w(x0, y1), w(x1, y0)                 # bottom left, top right
    me = bpy.data.meshes.new(SID + "_" + p["name"])
    me.from_pydata([(a.x, 0, a.z), (b.x, 0, a.z), (b.x, 0, b.z), (a.x, 0, b.z)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    for i, c in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[i].uv = c
    return me


bpy.context.view_layer.update()
for p in spec["parts"]:
    bends = p.get("chain") or p.get("bones_of") or p.get("anchor")
    me = grid_mesh(p) if bends else plane(p)
    me.materials.append(material(p))
    ob = bpy.data.objects.new(SID + "_" + p["name"], me)
    sc.collection.objects.link(ob)
    ob.hide_render = ob.hide_viewport = p["hidden"]
    if bends:
        # deformed by the rig: weights per vertex, the Armature modifier bends the mesh with the bones
        ob.parent = arm
        ob.location.y = -DEPTH * (p["draw"] + 1)
        if p.get("anchor"):
            an = p["anchor"]
            groups = {p["name"]: ob.vertex_groups.new(name=p["name"]), an["bone"]: ob.vertex_groups.new(name=an["bone"])}
        else:
            src = parts[p["bones_of"]] if p.get("bones_of") else p
            ch = src["chain"]
            groups = {i: ob.vertex_groups.new(name=f"{src['name']}.{i}") for i in range(len(ch) - 1)}
        for v in me.vertices:
            x, y = v.co.x * PX + W / 2, H / 2 - v.co.z * PX
            if p.get("anchor"):
                t = max(0.0, min(1.0, (an["y0"] - y) / (an["y0"] - an["y1"])))
                t = t * t * (3 - 2 * t)
                groups[p["name"]].add([v.index], t, "REPLACE")
                groups[an["bone"]].add([v.index], 1 - t, "REPLACE")
            else:
                for i, wt in enumerate(chain_weights(ch, x, y)):
                    if wt > 1e-4:
                        groups[i].add([v.index], wt, "REPLACE")
        mod = ob.modifiers.new("rig", "ARMATURE")
        mod.object = arm
        mod.use_vertex_groups = True
    else:
        world = Matrix.Translation((0, -DEPTH * (p["draw"] + 1), 0))   # draw order: later parts nearer the camera
        ob.parent, ob.parent_type, ob.parent_bone = arm, "BONE", p["name"]
        bpy.context.view_layer.update()
        ob.matrix_world = world                     # stays exactly where it was cut, now riding its bone
bpy.context.view_layer.update()
print(SID, "scene:", len(spec["parts"]), "parts,", len(arm_data.bones), "bones:", [b.name for b in arm_data.bones])
