"""Bake a character's Blender cutout rig into a live 2D rig: what the game draws instead of rendered frames.
Run in a background Blender on the character's .blend (it is only read, never saved):
  "C:/Users/CooperHinkel/Blender/blender-5.2.3-windows-x64/blender.exe" -b --factory-startup \\
      art/blender/chars/<char>/<char>.blend --python tools/blender/chars/rig/export_rig.py -- <out.json>
Nothing here invents or changes motion: every number is read off Blender's own evaluation at the clip's rendered times
(the same times the renders show, Time Remapping included):
  - each image plane that rides one bone (a "rigid" part): its world matrix, as the 2D map from its own (x, z) to
    master frame px (y down), per frame
  - each skinned part (cloth, cords, bills: a grid deformed by the Armature modifier): its rest vertices in armature
    space and weights (static), and the deform matrix of every bone that moves it, per frame - linear blend skinning,
    exactly what the modifier does (checked here against the evaluated meshes)
  - per frame, which parts show (keyed hide_render: face swaps, the tossed bills) and their depth along the camera
    (Eevee sorts the blended planes by origin depth: the draw order)
  - static: each part's triangles, UVs, image (path, size), and whether it is left out of the wall's neon light
    (its material's mask colour is white: shoes, the skull's cigar and laces)
The Grease Pencil effects (dust, glints, ember, ash) are not parts: render_fx.py renders them as small frame tracks."""
import bpy, json, math, os, sys
import numpy as np
from mathutils import Matrix

argv = sys.argv[sys.argv.index("--") + 1:]
OUT = argv[0]
sc = bpy.data.scenes.get("BOY") or bpy.data.scenes.get("SKULL") or bpy.context.scene
arm = next(o for o in sc.objects if o.type == "ARMATURE")
cam = sc.camera
pct = sc.render.resolution_percentage / 100
RES = (int(sc.render.resolution_x * pct), int(sc.render.resolution_y * pct))
cd = cam.data
assert cd.type == "ORTHO", cd.type
fit = cd.sensor_fit if cd.sensor_fit != "AUTO" else ("HORIZONTAL" if RES[0] >= RES[1] else "VERTICAL")
PPU = (RES[0] if fit == "HORIZONTAL" else RES[1]) / cd.ortho_scale     # master px per Blender unit
SHIFT = (cd.shift_x * cd.ortho_scale, cd.shift_y * cd.ortho_scale)
V = cam.matrix_world.inverted()                                        # world -> camera (x right, y up, -z ahead)


def aff(M):
    """world 4x4 -> [a, b, c, d, e, f, tx, ty]: a point (x, y, z) of M's input space lands at master px
    X = a x + c z + e y + tx, Y = b x + d z + f y + ty (y down). Depth: (V @ M).translation.z."""
    C = V @ M
    a = C[0][0] * PPU; c = C[0][2] * PPU; e = C[0][1] * PPU; tx = RES[0] / 2 + (C[0][3] - SHIFT[0]) * PPU
    b = -C[1][0] * PPU; d = -C[1][2] * PPU; f = -C[1][1] * PPU; ty = RES[1] / 2 - (C[1][3] - SHIFT[1]) * PPU
    return [a, b, c, d, e, f, tx, ty]


def depth(M):
    return -(V @ M).translation.z          # distance ahead of the camera: drawn farthest first


# ---- clips: the rendered times (tools/blender/chars/<char>/run.py: boy rendered_times, skull frame f0 + i)
clips = {k: (int(v[0]), int(v[1])) for k, v in arm["clips"].items()}
REMAP = {k: (int(v[0]), int(v[1])) for k, v in arm["remap"].items()} if "remap" in arm.keys() else None
loops = set(arm.get("loops", ["idle"]))


def rendered_times(name):
    a, b = clips[name]
    if REMAP is None:
        return [float(a + j) for j in range(b - a + 1)]
    old, new = REMAP[name]
    n_out = new if name in loops else new + 1
    return [a + j * old / new for j in range(n_out)]


def at(t):
    f = int(math.floor(t + 1e-9))
    sc.frame_set(f, subframe=t - f)


# ---- static: the parts
parts = [o for o in sc.objects if o.type == "MESH" and (o.parent is arm or any(m.type == "ARMATURE" for m in o.modifiers))]
deform = {b.name for b in arm.data.bones if b.use_deform}
static = {}
for o in parts:
    me = o.data
    uvl = me.uv_layers.active.data
    uv = [None] * len(me.vertices)
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            u = tuple(uvl[li].uv)
            if uv[vi] is not None and max(abs(u[0] - uv[vi][0]), abs(u[1] - uv[vi][1])) > 1e-6:
                raise SystemExit(f"{o.name}: vertex {vi} has two UVs (a seam): the rig needs one UV per vertex")
            uv[vi] = u
    tris = []
    for poly in me.polygons:
        vs = list(poly.vertices)
        for k in range(1, len(vs) - 1):
            tris += [vs[0], vs[k], vs[k + 1]]
    img, unlit, interp = None, False, None
    for ms in o.material_slots:
        m = ms.material
        if not (m and m.node_tree):
            continue
        for n in m.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image:
                img = {"name": n.image.name, "path": os.path.normpath(bpy.path.abspath(n.image.filepath)),
                       "size": list(n.image.size), "alpha": n.image.alpha_mode, "colorspace": n.image.colorspace_settings.name}
                interp = n.interpolation
            if n.type == "MIX" and getattr(n, "data_type", "") == "RGBA":
                # the mask colour (Mix B, chosen in mask mode): white = the light leaves this part alone
                for s in n.inputs:
                    if s.name == "B" and s.type == "RGBA" and not s.is_linked:
                        unlit = tuple(s.default_value)[:3] == (1.0, 1.0, 1.0)
    skinned = any(m.type == "ARMATURE" for m in o.modifiers)
    ent = {"skinned": skinned, "uv": [round(c, 7) for p in uv for c in p], "tris": tris, "img": img, "unlit": unlit,
           "interp": interp, "nv": len(me.vertices)}
    if skinned:
        md = next(m for m in o.modifiers if m.type == "ARMATURE")
        assert md.object is arm and not md.use_deform_preserve_volume and md.use_vertex_groups and not md.use_bone_envelopes, o.name
        to_arm = arm.matrix_world.inverted() @ o.matrix_world
        vg = {g.index: g.name for g in o.vertex_groups}
        ent["rest"], ent["w"] = [], []
        for v in me.vertices:
            p = to_arm @ v.co
            ent["rest"] += [p.x, p.y, p.z]
            ws = sorted([(vg[g.group], g.weight) for g in v.groups if g.weight > 0 and vg[g.group] in deform],
                        key=lambda t: -t[1])
            ent["w"].append([[n, w] for n, w in ws])
    else:
        ent["local"] = [c for v in me.vertices for c in (v.co.x, v.co.y, v.co.z)]
    static[o.name] = ent

bones_used = sorted({n for s in static.values() if s["skinned"] for ws in s["w"] for n, _ in ws})
arm_w = arm.matrix_world.copy()


def bone_D(pb):
    return arm_w @ (pb.matrix @ pb.bone.matrix_local.inverted())


def lbs(name, B):
    """skinned part -> master px, from the bones' maps B (as Blender's Armature modifier: weights normalised,
    a vertex with none stays at rest)"""
    s = static[name]
    rest = np.array(s["rest"]).reshape(-1, 3)
    I = aff(arm_w)
    out = np.zeros((len(rest), 2))
    for i, ws in enumerate(s["w"]):
        x, y, z = rest[i]
        tot = sum(w for _, w in ws)
        if tot <= 0:
            a, b, c, d, e, f, tx, ty = I
            out[i] = (a * x + c * z + e * y + tx, b * x + d * z + f * y + ty)
            continue
        X = Y = 0.0
        for n, w in ws:
            a, b, c, d, e, f, tx, ty = B[n]
            X += w * (a * x + c * z + e * y + tx); Y += w * (b * x + d * z + f * y + ty)
        out[i] = (X / tot, Y / tot)
    return out


# ---- per frame
res = {"res": RES, "fps": sc.render.fps, "ppu": PPU, "bones": bones_used, "static": static, "clips": {},
       "arm_identity": aff(arm_w)}
worst = {}
for clip in clips:
    times = rendered_times(clip)
    frames = []
    checks = sorted({0, len(times) // 3, (2 * len(times)) // 3, len(times) - 1})
    for fi, t in enumerate(times):
        at(t)
        dg = bpy.context.evaluated_depsgraph_get()
        fr = {"bones": {}, "parts": {}}
        for bn in bones_used:
            fr["bones"][bn] = aff(bone_D(arm.pose.bones[bn]))
        for o in parts:
            if o.hide_render:
                continue
            ev = o.evaluated_get(dg)
            M = ev.matrix_world
            p = {"z": depth(M)}
            if not static[o.name]["skinned"]:
                p["A"] = aff(M)
            fr["parts"][o.name] = p
        if fi in checks:            # the skinning maths against Blender's own deformed meshes, and rigid parts
            for o in parts:
                if o.hide_render:
                    continue
                ev = o.evaluated_get(dg)
                m = ev.to_mesh()
                C = V @ ev.matrix_world
                got = np.array([[RES[0] / 2 + ((C @ v.co).x - SHIFT[0]) * PPU, RES[1] / 2 - ((C @ v.co).y - SHIFT[1]) * PPU] for v in m.vertices])
                ev.to_mesh_clear()
                if static[o.name]["skinned"]:
                    mine = lbs(o.name, fr["bones"])
                else:
                    a, b, c, d, e, f, tx, ty = fr["parts"][o.name]["A"]
                    L = np.array(static[o.name]["local"]).reshape(-1, 3)
                    mine = np.stack([a * L[:, 0] + c * L[:, 2] + e * L[:, 1] + tx, b * L[:, 0] + d * L[:, 2] + f * L[:, 1] + ty], 1)
                err = float(np.abs(got - mine).max())
                worst[o.name] = max(worst.get(o.name, 0), err)
        frames.append(fr)
    res["clips"][clip] = {"times": times, "frames": frames, "loop": clip in loops}
    print(f"{clip}: {len(frames)} frames", flush=True)
res["check_max_px"] = worst
print("max |Blender - rig| master px per part:", json.dumps({k: round(v, 5) for k, v in worst.items()}), flush=True)
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
json.dump(res, open(OUT, "w"))
print("->", OUT, len(parts), "parts,", len(bones_used), "bones", flush=True)
