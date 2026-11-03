# Helpers for making a symbol's animation INSIDE Blender (imported by tools/blender/anim_<ID>.py, which runs in
# Blender through MCP for Blender's execute_code or Blender's Text Editor). Nothing here makes a picture by
# itself: it sets Blender up - three view layers (the art; the glow behind it; the effects over it), the
# compositor that blooms the two effect layers into neon light, Actions on the rig placed on its NLA track, the
# secondary motion of the hanging parts (worked out in Blender from how the rig moves, keyed onto their bones),
# Grease Pencil layers drawn frame by frame - and the animation is the keys and drawings the symbol's own script
# lays down with these. Everything stays editable in Blender: keys in the Graph Editor, strips in the NLA, the
# drawings in Grease Pencil, the glow in the Compositor.
import bpy, glob, json, math, os, random
from mathutils import Vector

PX = 100.0                                    # icon px per unit (tools/blender/build_symbol_scene.py)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIME, VIOLET, WHITE, GOLD = (0.424, 0.988, 0.329, 1), (0.706, 0.329, 0.894, 1), (0.96, 1.0, 0.94, 1), (0.96, 0.77, 0.094, 1)
PINK, SMOKE = (0.93, 0.47, 1.0, 1), (0.86, 0.84, 0.9, 1)
ICON = [1000, 1000]                           # the icon's size in px (setup() reads it from parts.json)


def px(x, y):                                 # icon px -> (x, z) world, the icon centred on the origin
    return ((x - ICON[0] / 2) / PX, (ICON[1] / 2 - y) / PX)


def vec(x, y):
    a, b = px(x, y)
    return Vector((a, 0.0, b))


def use_scene(sid):
    """The symbol's scene, made current. In the Blender window it is switched to; in a background Blender
    (no window, tools/blender/run.py) the startup scene is renamed to it, so bpy.context works on it."""
    sc = bpy.data.scenes.get(sid)
    win = bpy.context.window
    if win is not None:
        if sc is None:
            sc = bpy.data.scenes.new(sid)
        win.scene = sc
        return sc
    if sc is None:
        sc = bpy.context.scene
        sc.name = sid
    return sc


def setup(sid):
    """For a symbol's animation script: its scene (current), its rig, and its cut (parts.json: sizes, parts,
    chains) - and the icon size px()/vec() measure in."""
    spec = json.load(open(os.path.join(ROOT, "art", "blender", "parts", sid, "parts.json")))
    ICON[0], ICON[1] = spec["size"]
    sc = use_scene(sid)
    return sc, bpy.data.objects[sid + "_rig"], spec


# ------------------------------------------------------------------ collections, view layers, compositor
def layers(sc, sid):
    """The art (rig, parts, camera) in one collection, the glow behind it in a second, the effects over it in a
    third; view layer "art" renders the first, "fxb" the second, "fx" the third, and the compositor stacks
    them: bloomed back glow, the art, bloomed effects."""
    cols = {}
    for key in ("ART", "FXB", "FX"):
        c = bpy.data.collections.get(f"{sid}_{key}") or bpy.data.collections.new(f"{sid}_{key}")
        if c.name not in sc.collection.children:
            sc.collection.children.link(c)
        cols[key] = c
    for o in list(sc.collection.objects):     # whatever the scene builder left at the top goes in the art
        cols["ART"].objects.link(o); sc.collection.objects.unlink(o)
    vls = {"art": sc.view_layers[0]}
    vls["art"].name = "art"
    for name in ("fxb", "fx"):
        vls[name] = sc.view_layers.get(name) or sc.view_layers.new(name)
    for vl in sc.view_layers:
        if vl.name not in vls:
            sc.view_layers.remove(vl)
    own = {"art": "ART", "fxb": "FXB", "fx": "FX"}
    for name, vl in vls.items():
        vl.use = True
        for key, c in cols.items():
            vl.layer_collection.children[c.name].exclude = key != own[name]
    cam = sc.camera
    for key in ("FXB", "FX"):
        if cam and cam.name not in cols[key].objects:
            cols[key].objects.link(cam)       # every layer looks through the same camera
    return cols["ART"], cols["FXB"], cols["FX"]


def glow_compositor(sc, sid, back=None, front=None):
    """Each effects layer bloomed (Glare: Bloom, from every lit pixel) with its light turned into alpha, so the
    glow shows on the transparent film; the back glow under the art, the effects over it."""
    back = dict(dict(strength=1.0, size=.6, gain=1.5), **(back or {}))
    front = dict(dict(strength=.9, size=.45, gain=1.5), **(front or {}))
    ng = bpy.data.node_groups.get(sid + "_comp") or bpy.data.node_groups.new(sid + "_comp", "CompositorNodeTree")
    ng.nodes.clear()
    if not any(getattr(s, "in_out", "") == "OUTPUT" for s in ng.interface.items_tree):
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    N, L = ng.nodes, ng.links

    def mathn(op, a, b=None, clamp=False, loc=(0, 0)):
        n = N.new("ShaderNodeMath"); n.operation = op; n.use_clamp = clamp; n.location = loc
        L.new(a, n.inputs[0])
        if isinstance(b, (int, float)):
            n.inputs[1].default_value = b
        elif b is not None:
            L.new(b, n.inputs[1])
        return n.outputs[0]

    def glow(layer, cfg, y):
        rl = N.new("CompositorNodeRLayers"); rl.scene = sc; rl.layer = layer; rl.location = (-900, y)
        g = N.new("CompositorNodeGlare"); g.location = (-650, y)
        g.inputs["Type"].default_value = "Bloom"
        g.inputs["Quality"].default_value = "High"
        for name, val in (("Threshold", 0.0), ("Strength", cfg["strength"]), ("Size", cfg["size"]), ("Saturation", 1.2)):
            try:
                g.inputs[name].default_value = val
            except Exception:
                pass
        L.new(rl.outputs["Image"], g.inputs["Image"])
        sep = N.new("CompositorNodeSeparateColor"); sep.location = (-420, y - 150)
        L.new(g.outputs["Image"], sep.inputs[0])
        lum = mathn("MAXIMUM", mathn("MAXIMUM", sep.outputs[0], sep.outputs[1], loc=(-250, y - 120)), sep.outputs[2], loc=(-100, y - 120))
        a = mathn("MAXIMUM", mathn("MULTIPLY", lum, cfg["gain"], loc=(50, y - 120)), rl.outputs["Alpha"], clamp=True, loc=(200, y - 120))
        sa = N.new("CompositorNodeSetAlpha"); sa.location = (350, y)
        sa.inputs["Type"].default_value = "Replace Alpha"
        L.new(g.outputs["Image"], sa.inputs["Image"]); L.new(a, sa.inputs["Alpha"])
        return sa.outputs["Image"]

    gb = glow("fxb", back, 400)
    gf = glow("fx", front, -400)
    art = N.new("CompositorNodeRLayers"); art.scene = sc; art.layer = "art"; art.location = (-900, 0)
    o1 = N.new("CompositorNodeAlphaOver"); o1.location = (600, 100)
    L.new(gb, o1.inputs["Background"]); L.new(art.outputs["Image"], o1.inputs["Foreground"])
    o2 = N.new("CompositorNodeAlphaOver"); o2.location = (800, 0)
    L.new(o1.outputs["Image"], o2.inputs["Background"]); L.new(gf, o2.inputs["Foreground"])
    out = N.new("NodeGroupOutput"); out.location = (1000, 0)
    L.new(o2.outputs["Image"], out.inputs[0])
    sc.compositing_node_group = ng
    sc.render.use_compositing = True
    return ng


# ------------------------------------------------------------------ actions on the rig, on its NLA track
def begin_action(arm, name):
    """A fresh Action for one clip, assigned to the rig so the keys go into it."""
    old = bpy.data.actions.get(name)
    if old:
        bpy.data.actions.remove(old)
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    return act


def end_action(arm, act, start):
    """Put the clip on the rig's NLA track at its own frames, so every clip lives in its own Action and the
    timeline plays them one after another (idle, land, hit, multi)."""
    ad = arm.animation_data
    slot = ad.action_slot
    ad.action = None
    tr = ad.nla_tracks.get("clips") or ad.nla_tracks.new()
    tr.name = "clips"
    for s in list(tr.strips):
        if s.name == act.name:
            tr.strips.remove(s)
    st = tr.strips.new(act.name, int(start), act)
    try:
        st.action_slot = slot
    except Exception:
        pass
    st.extrapolation = "NOTHING"
    st.blend_type = "REPLACE"
    return st


def fcurves(act):
    """Every F-curve of a (slotted) Action."""
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                out.extend(bag.fcurves)
    return out


def calm(act, k):
    """Tone a clip's motion down: every bone transform key (and its handles) drawn toward the rest pose, to k of
    how far it went (k = .7: 30% less movement). Materials, visibility and the rest are left as keyed."""
    rest = {"location": (0, 0, 0), "rotation_euler": (0, 0, 0), "rotation_quaternion": (1, 0, 0, 0), "scale": (1, 1, 1)}
    for fc in fcurves(act):
        if not fc.data_path.startswith("pose.bones["):
            continue
        r = rest.get(fc.data_path.rsplit(".", 1)[-1])
        if r is None:
            continue
        r = r[fc.array_index]
        for kp in fc.keyframe_points:
            for p in (kp.co, kp.handle_left, kp.handle_right):
                p.y = r + k * (p.y - r)
        fc.update()


def make_cyclic(act):
    """A looping clip: each curve repeats (Cycles modifier), so its first and last keys share smooth handles."""
    for fc in fcurves(act):
        if not any(m.type == "CYCLES" for m in fc.modifiers):
            fc.modifiers.new("CYCLES")
        fc.update()


def key(arm, bone, f, x=None, y=None, r=None, sx=None, sy=None, s=None):
    """Key one bone at frame f: x/y in units (screen right / up), r in degrees (counter-clockwise), sx/sy
    scale (s = both). Only the channels given are keyed."""
    pb = arm.pose.bones[bone]
    if x is not None or y is not None:
        if x is not None: pb.location.x = x
        if y is not None: pb.location.y = y
        pb.keyframe_insert("location", frame=f, group=bone)
    if r is not None:
        pb.rotation_euler.z = math.radians(r)
        pb.keyframe_insert("rotation_euler", frame=f, group=bone)
    if s is not None:
        sx = sy = s
    if sx is not None or sy is not None:
        if sx is not None: pb.scale.x = sx
        if sy is not None: pb.scale.y = sy
        pb.keyframe_insert("scale", frame=f, group=bone)


def rest(arm, bones, f):
    for b in bones:
        key(arm, b, f, x=0, y=0, r=0, sx=1, sy=1)


def hard(act, bone, path, index, f):
    """A key that is hit, not eased into (a landing): its handles point straight at its neighbours."""
    for fc in fcurves(act):
        if fc.data_path == f'pose.bones["{bone}"].{path}' and fc.array_index == index:
            for kp in fc.keyframe_points:
                if abs(kp.co.x - f) < .5:
                    kp.handle_left_type = kp.handle_right_type = "VECTOR"
            fc.update()


def sparse(vals, tol):
    """The frames worth a key in a sampled curve: its ends, its turning points, and whatever else the curve
    needs to stay within tol of the samples (Ramer-Douglas-Peucker) - so the keys read like an animator's."""
    n = len(vals)
    keep = {0, n - 1}
    for i in range(1, n - 1):
        if (vals[i] - vals[i - 1]) * (vals[i + 1] - vals[i]) < 0 and abs(vals[i]) > tol * .5:
            keep.add(i)

    def rdp(a, b):
        if b - a < 2:
            return
        worst, at = 0.0, None
        for i in range(a + 1, b):
            lin = vals[a] + (vals[b] - vals[a]) * (i - a) / (b - a)
            d = abs(vals[i] - lin)
            if d > worst:
                worst, at = d, i
        if worst > tol:
            keep.add(at); rdp(a, at); rdp(at, b)
    ks = sorted(keep)
    for a, b in zip(ks, ks[1:]):
        rdp(a, b)
    return sorted(keep)


def key_series(arm, bone, f0, vals, channel="r", tol=.25, loop=False):
    """Key a per-frame series (degrees for r, factors for sx/sy) from frame f0, sparsely."""
    series = list(vals) + ([vals[0]] if loop else [])
    for i in sparse(series, tol):
        key(arm, bone, f0 + i, **{channel: series[i]})


# ------------------------------------------------------------------ secondary motion
def secondary(sc, arm, holder, f0, f1, chains, loop=False, warm=3, sub=10, settle=8, forces=None, gain=1.0,
              rest_start=True):
    """How parts hanging off `holder` (a bone) follow it. Each chain is a row of point masses - its joints and
    its tip, in icon px, the first one fixed to the holder - each on a damped spring to where it would sit if the
    part were rigid (stiffness as a frequency in Hz, softer toward the tip, so the motion runs down it), held to
    its lengths. The holder's real movement in the clip (evaluated frame by frame from the keys already laid
    down) drives them: they lag as it sets off, float as it falls, whip when it stops. forces(name, i, t) adds
    an acceleration (a breeze, a charge); gain scales how much of the lag shows in this clip. Returns
    {bone: [degrees per frame]} - each bone's turn relative to its parent - and, for a chain marked "stretch",
    its scale too ({bone + ":sy": [...]}, softly held within stretch_limit of 1)."""
    clip_gain = gain
    fps = sc.render.fps
    pb = arm.pose.bones[holder]
    rest_inv = pb.bone.matrix_local.inverted()
    B = []
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        B.append((arm.matrix_world @ pb.matrix @ rest_inv).copy())
    nf = len(B)
    Binv = [m.inverted() for m in B]
    recs = {}
    for name, ch in chains.items():
        Q = [vec(*p) for p in ch["chain"]]
        n = len(Q)
        om = [2 * math.pi * hz for hz in ch["freq"]]
        zeta = ch.get("zeta", .15)
        stretch = ch.get("stretch", False)
        gain = ch.get("gain", 1.0) * clip_gain      # how much of the lag shows (the cartoon's moves are violent)
        limit = ch.get("limit", 0)                  # a soft cap on each joint's bend, degrees
        slim = ch.get("stretch_limit", 0)
        P = [B[0] @ q for q in Q]
        V = [Vector((0, 0, 0)) for _ in Q]
        a0 = [math.atan2(Q[i + 1].z - Q[i].z, Q[i + 1].x - Q[i].x) for i in range(n - 1)]
        l0 = [(Q[i + 1] - Q[i]).length for i in range(n - 1)]
        steps = nf * (warm + 1) if loop else nf
        rec = []
        dt = 1.0 / (fps * sub)
        for step in range(steps):
            k = step % nf
            k2 = (k + 1) % nf if loop else min(k + 1, nf - 1)
            if step >= steps - nf:                  # record the frame (on a loop, only the last, settled lap)
                R = [Binv[k] @ p for p in P]
                R = [Q[i] + (R[i] - Q[i]) * gain for i in range(n)]
                ang = [math.atan2(R[i + 1].z - R[i].z, R[i + 1].x - R[i].x) - a0[i] for i in range(n - 1)]
                ang = [math.degrees((d + math.pi) % (2 * math.pi) - math.pi) for d in ang]
                rel = [ang[0]] + [ang[i] - ang[i - 1] for i in range(1, n - 1)]
                if limit:
                    rel = [limit * math.tanh(r / limit) for r in rel]
                st = [(R[i + 1] - R[i]).length / l0[i] for i in range(n - 1)]
                if slim:
                    st = [1 + slim * math.tanh((q - 1) / slim) for q in st]
                rec.append((rel, st))
            for s in range(sub):
                u0, u1 = s / sub, (s + 1) / sub
                G0 = [(B[k] @ q).lerp(B[k2] @ q, u0) for q in Q]
                G1 = [(B[k] @ q).lerp(B[k2] @ q, u1) for q in Q]
                t = (step + u0) / fps
                for i in range(1, n):
                    vg = (G1[i] - G0[i]) / dt          # the goal's own velocity: damping acts on the lag only
                    acc = (G0[i] - P[i]) * om[i - 1] ** 2 - (V[i] - vg) * (2 * zeta * om[i - 1])
                    if forces:
                        acc = acc + forces(name, i, t)
                    V[i] = V[i] + acc * dt
                old = [p.copy() for p in P]
                P[0] = G1[0]
                for i in range(1, n):
                    P[i] = P[i] + V[i] * dt
                if not stretch:                     # held to its lengths (the holder's scale included)
                    for i in range(1, n):
                        L = (G1[i] - G1[i - 1]).length
                        d = P[i] - P[i - 1]
                        P[i] = P[i - 1] + d.normalized() * L
                for i in range(1, n):
                    V[i] = (P[i] - old[i]) / dt
        if not loop and settle:                     # ease the last frames onto the rest pose
            for j in range(settle):
                idx = nf - settle + j
                t = (j + 1) / settle
                fade = 1 - t * t * (3 - 2 * t)
                rel, sc_ = rec[idx]
                rec[idx] = ([r * fade for r in rel], [1 + (q - 1) * fade for q in sc_])
        recs[name] = (rec, n, stretch)
    if loop and rest_start:
        # a loop has no start of its own: begin it where everything hanging is nearest its rest pose, so the
        # other clips (which end at rest) hand over to it without a jump
        cost = [sum(sum(abs(r) for r in recs[nm][0][k][0]) + 30 * sum(abs(q - 1) for q in recs[nm][0][k][1]) for nm in recs)
                for k in range(nf)]
        k0 = min(range(nf), key=cost.__getitem__)
        recs = {nm: (rec[k0:] + rec[:k0], n, st) for nm, (rec, n, st) in recs.items()}
        # what is left of the offset there is taken out smoothly over the lap (a raised-cosine window: whole at
        # the first frame, nothing halfway round), so the loop starts exactly at rest and still joins up
        for nm, (rec, n, st) in recs.items():
            r0, s0 = rec[0]
            fixed = []
            for k, (rel, sc_) in enumerate(rec):
                w = .5 + .5 * math.cos(2 * math.pi * k / nf)
                fixed.append(([r - a * w for r, a in zip(rel, r0)], [q - (b - 1) * w for q, b in zip(sc_, s0)]))
            recs[nm] = (fixed, n, st)
    out = {}
    for name, (rec, n, stretch) in recs.items():
        for i in range(n - 1):
            out[f"{name}.{i}" if n > 2 else name] = [r[0][i] for r in rec]
            if stretch:
                out[(f"{name}.{i}" if n > 2 else name) + ":sy"] = [r[1][i] for r in rec]
    return out


# ------------------------------------------------------------------ grease pencil, drawn frame by frame
def gp_object(coll, name, depth=-0.6):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    oldd = bpy.data.grease_pencils.get(name)
    if oldd and oldd.users == 0:
        bpy.data.grease_pencils.remove(oldd)
    gpd = bpy.data.grease_pencils.new(name)
    ob = bpy.data.objects.new(name, gpd)
    coll.objects.link(ob)
    ob.location.y = depth                      # in front of the art
    ob.use_grease_pencil_lights = False        # drawn in its own colours: the scene has no lights to shade it
    return ob


def ride(ob, arm, bone):
    """Parent an object to a bone, keeping it where it is: it moves, scales and squashes with that bone."""
    world = ob.matrix_world.copy()
    ob.parent, ob.parent_type, ob.parent_bone = arm, "BONE", bone
    bpy.context.view_layer.update()
    ob.matrix_world = world


def gp_mat(gp_ob, name, color, fill=None, stroke=True):
    """A Grease Pencil material: its line colour, and its fill colour for strokes drawn with fill=True."""
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name)
        bpy.data.materials.create_gpencil_data(mat)
    g = mat.grease_pencil
    g.color = color
    if fill is not None:
        g.fill_color = fill
    if mat.name not in [m.name for m in gp_ob.data.materials if m]:
        gp_ob.data.materials.append(mat)
    return [m.name for m in gp_ob.data.materials].index(mat.name)


def gp_layer(gp_ob, name):
    L = gp_ob.data.layers.get(name) or gp_ob.data.layers.new(name)
    L.use_lights = False
    return L


def drawing(layer, f):
    for fr in layer.frames:
        if fr.frame_number == f:
            return fr.drawing
    return layer.frames.new(f).drawing


def stroke(dr, pts, radius, opacity=1.0, mat=0, cyclic=False, radii=None, opacities=None, fill=False, line=True):
    """One stroke through world (x, z) points; radius in units (or per point in radii). fill=True fills it with
    its material's fill colour (Grease Pencil 3 / Blender 5: filling is the stroke's own, by its fill id, and so
    is hiding its line - line=False - not the material's)."""
    dr.add_strokes([len(pts)])
    s = dr.strokes[-1]
    for i, (x, z) in enumerate(pts):
        p = s.points[i]
        p.position = (x, 0.0, z)
        p.radius = radii[i] if radii else radius
        p.opacity = opacities[i] if opacities else opacity
    s.cyclic = cyclic
    s.material_index = mat
    if fill:
        s.fill_id = len(dr.strokes)                 # its own fill (shared ids would merge shapes, holes and all)
        s.fill_opacity = opacity
    if not line:
        s.hide_stroke = True
    return s


def blank(layer, f):
    """An empty drawing from frame f on: what was drawn before stops showing."""
    drawing(layer, f)


class Board:
    """Collects what each frame of a Grease Pencil layer shows, then draws it: every frame with something on
    it gets its own drawing, held for its beat (2 = on twos), and the frame after the last beat of a run gets a
    blank, so nothing lingers."""
    def __init__(self):
        self.frames, self.hold = {}, {}

    def add(self, f, fn, hold=1):
        f = int(f)
        self.frames.setdefault(f, []).append(fn)
        self.hold[f] = max(self.hold.get(f, 1), hold)

    def draw(self, layer):
        for f in sorted(self.frames):
            dr = drawing(layer, f)
            for fn in self.frames[f]:
                fn(dr)
            dr.tag_positions_changed()              # the fills are triangulated from the new points
            end = f + self.hold[f]
            if not any(g in self.frames for g in range(f + 1, end + 1)):
                blank(layer, end)


# shapes (world units)
def star(cx, cz, r, rot=0.0, points=4, inner=0.28):
    out = []
    for i in range(points * 2):
        a = rot + i * math.pi / points
        rr = r if i % 2 == 0 else r * inner
        out.append((cx + math.cos(a) * rr, cz + math.sin(a) * rr))
    return out


def ring(cx, cz, r, n=48, wobble=0.0, seed=0):
    rnd = random.Random(seed)
    return [(cx + math.cos(2 * math.pi * i / n) * r * (1 + wobble * (rnd.random() - .5)),
             cz + math.sin(2 * math.pi * i / n) * r * (1 + wobble * (rnd.random() - .5))) for i in range(n)]


def puff(cx, cz, r, lobes=7, seed=0, n=56, bump=.16):
    rnd = random.Random(seed)
    ph = [rnd.random() * 6.28 for _ in range(3)]
    return [(cx + math.cos(t) * r * (1 + bump * math.sin(lobes * t + ph[0]) + .07 * math.sin(3 * t + ph[1])),
             cz + math.sin(t) * r * .78 * (1 + bump * math.sin(lobes * t + ph[0]) + .07 * math.sin(5 * t + ph[2])))
            for t in (2 * math.pi * i / n for i in range(n))]


def zigzag(x0, z0, x1, z1, n=7, amp=0.18, seed=0):
    rnd = random.Random(seed)
    dx, dz = x1 - x0, z1 - z0
    L = math.hypot(dx, dz) or 1
    nx, nz = -dz / L, dx / L
    pts = []
    for i in range(n + 1):
        t = i / n
        off = 0 if i in (0, n) else (rnd.random() - .5) * 2 * amp
        pts.append((x0 + dx * t + nx * off, z0 + dz * t + nz * off))
    return pts


def jitter(pts, amp, seed):
    rnd = random.Random(seed)
    return [(x + (rnd.random() - .5) * 2 * amp, z + (rnd.random() - .5) * 2 * amp) for x, z in pts]


def resample(pts, n, closed=True):
    """n points evenly spaced along a polyline (closed: back to its start)."""
    P = list(pts) + ([pts[0]] if closed else [])
    seg = [math.dist(P[i], P[i + 1]) for i in range(len(P) - 1)]
    total = sum(seg)
    out, i, acc = [], 0, 0.0
    for k in range(n):
        d = total * k / n
        while i < len(seg) - 1 and acc + seg[i] < d:
            acc += seg[i]; i += 1
        t = (d - acc) / (seg[i] or 1)
        out.append((P[i][0] + (P[i + 1][0] - P[i][0]) * t, P[i][1] + (P[i + 1][1] - P[i][1]) * t))
    return out


def offset(loop_pts, d):
    """A closed loop moved d units outward (negative: inward), each point along its own normal."""
    n = len(loop_pts)
    area = sum(loop_pts[i][0] * loop_pts[(i + 1) % n][1] - loop_pts[(i + 1) % n][0] * loop_pts[i][1] for i in range(n))
    sgn = 1 if area > 0 else -1                     # counter-clockwise: the outside is on the right of the travel
    out = []
    for i in range(n):
        (ax, az), (bx, bz) = loop_pts[i - 1], loop_pts[(i + 1) % n]
        tx, tz = bx - ax, bz - az
        L = math.hypot(tx, tz) or 1
        out.append((loop_pts[i][0] + sgn * tz / L * d, loop_pts[i][1] - sgn * tx / L * d))
    return out


def arc(loop_pts, start, length):
    """A run of a closed loop of points: from fraction `start` of the way round, `length` of it."""
    n = len(loop_pts)
    a = int(start % 1 * n)
    m = max(2, int(length * n))
    return [loop_pts[(a + j) % n] for j in range(m)]


def taper(m, r, ends=.3):
    """Radii for a stroke of m points: full in the middle, tapering to points at both ends."""
    out = []
    for j in range(m):
        t = j / max(1, m - 1)
        e = min(t, 1 - t) / ends
        out.append(r * min(1.0, e) ** .7)
    return out


def smooth(a, b, f):
    """0 before frame a, 1 after b, eased between."""
    t = max(0.0, min(1.0, (f - a) / (b - a)))
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ ready-made effects (drawn on a Board)
def sparkle(board, f0, life, x, z, r, mat, rot0=0.0, spin=.6, hold=1):
    """A four-point twinkle that blooms and shrinks away as it turns (filled with its material's fill colour)."""
    for k in range(life):
        t = k / max(1, life - 1)
        rr = r * math.sin(math.pi * min(1, t * 1.1))
        if rr > .015:
            board.add(f0 + k, lambda dr, x=x, z=z, rr=rr, a=rot0 + spin * t: stroke(dr, star(x, z, rr, a), .004, mat=mat,
                                                                                    cyclic=True, fill=True, line=False), hold)


def dust(board, f0, life, x, z, scale, mat, drift=(0.0, .45), seed=0, lobes=5):
    """A cartoon dust puff (fill + light ink): solid, it swells out and shrinks away to nothing - a fade
    would leave grey smudges. drift = how far it rolls over its life (units)."""
    for k in range(life):
        t = k / max(1, life - 1)
        size = math.sin(math.pi * min(1.0, t * 1.05)) ** .6
        rr = scale * (.3 + .75 * size) * size
        if rr > .03:
            board.add(f0 + k, lambda dr, cx=x + drift[0] * t, cz=z + drift[1] * t, rr=rr: stroke(
                dr, puff(cx, cz, rr, lobes=lobes, seed=seed, bump=.09), .008, opacity=.95, mat=mat, cyclic=True, fill=True))


def starburst(board, f0, life, cx, cz, r0, r1, mat_rays, mat_core, points=12):
    """Thin rays opening out behind a symbol round a hot heart; they burn out by thinning to needles (dimmed
    rays read dirty). Both materials draw filled."""
    for k in range(life):
        t = k / max(1, life - 1)
        r = r0 + (r1 - r0) * t
        board.add(f0 + k, lambda dr, t=t, r=r: stroke(dr, star(cx, cz, r, .15 + .45 * t, points=points, inner=.22 * (1 - .8 * t)), .004,
                                                     opacity=.75 * (1 - t ** 3), mat=mat_rays, cyclic=True, fill=True, line=False))
        board.add(f0 + k, lambda dr, t=t, r=r: stroke(dr, star(cx, cz, r * .72, .41 + .6 * t, points=points, inner=.16 * (1 - .8 * t)), .004,
                                                     opacity=.7 * (1 - t ** 2.5), mat=mat_core, cyclic=True, fill=True, line=False))
        board.add(f0 + k, lambda dr, t=t, r=r: stroke(dr, ring(cx, cz, r * .45, n=40), .004, opacity=.55 * (1 - t) ** 1.5,
                                                     mat=mat_core, cyclic=True, fill=True, line=False))


def shock_rings(board, f0, cx, cz, r0, r1, mats, life=13, lag=4, width=.12):
    """Rings of light rolling outward one after another (a release, a slam), thinning as they go."""
    for j, mat in enumerate(mats):
        for k in range(life):
            f = f0 + lag * j + k
            t = k / (life - 1)
            board.add(f, lambda dr, t=t, mat=mat, f=f: stroke(dr, ring(cx, cz, r0 + (r1 - r0) * t, n=96, wobble=.03, seed=f),
                                                               width * (1 - t) + .015, opacity=(1 - t) ** 1.2, mat=mat, cyclic=True))


def streaks(board, f0, life, cx, cz, r0, r1, mats, n=14, rot=.2, width=.035):
    """A spray of short streaks of light flying out from a point."""
    for i in range(n):
        a = 2 * math.pi * i / n + rot
        for k in range(life):
            t = k / max(1, life - 1)
            r = r0 + (r1 - r0) * t
            ln = (r1 - r0) * .4 * (1 - t)
            board.add(f0 + k, lambda dr, a=a, t=t, r=r, ln=ln, i=i: stroke(
                dr, [(cx + math.cos(a) * r, cz + math.sin(a) * r), (cx + math.cos(a) * (r + ln), cz + math.sin(a) * (r + ln))],
                width * (1 - t) + .006, mat=mats[i % len(mats)]))


def lightning(board, f0, f1, cx, cz, r_in, r_out, mats, per=3, step=2, seed=0):
    """Crackling arcs off a charged symbol: a few zigzags at random angles round it, redrawn every `step`
    frames. r_in / r_out: (rx, rz) of where they start and end."""
    for f in range(f0, f1 + 1, step):
        rr = random.Random(f * 13 + seed)
        for j in range(per):
            a = rr.uniform(0, 2 * math.pi)
            p0 = (cx + math.cos(a) * r_in[0], cz + math.sin(a) * r_in[1])
            p1 = (cx + math.cos(a) * r_out[0], cz + math.sin(a) * r_out[1])
            board.add(f, lambda dr, p0=p0, p1=p1, f=f, j=j: stroke(dr, zigzag(*p0, *p1, n=6, amp=.3, seed=f * 7 + j), .03,
                                                                   mat=mats[j % len(mats)]), hold=step)


# ------------------------------------------------------------------ the paying tiers' neon (art/STYLE.md)
TIER_GLOW = {
    1: dict(halo=VIOLET, charge=LIME, comet=LIME, level=1.0),    # the top three: violet backlight, lime light
    2: dict(halo=VIOLET, charge=PINK, comet=PINK, level=.8),     # the premium four: all violet, quieter
}


def neon(sid, arm, coll, clips, tier=1, bone="body", outline="outline_plate", land_at=None, hit_span=None,
         pulses=None, charge_span=None):
    """The tier glow, made in Blender: not a line round the sticker but light behind it - the halo colour in
    stacked bands falling off wide (the compositor's bloom smooths them into one glow) - with comets of light
    running round just outside the sticker's edge; the charge colour floods in when the symbol is struck. It
    rides `bone`. The path is art/blender/parts/<sid>/<outline>.json (tools/blender/outline.py, 9 px out).
    clips {"idle": (f0, f1), "land": .., "hit": .., "multi": ..}; land_at the frame it lands (default f0 + 2);
    hit_span (from, to) the hit burns bright and comets race (default f0 + 4 .. f1 - 6); pulses the multi's
    swells; charge_span (from, to) it crackles. Returns the Grease Pencil object."""
    g = TIER_GLOW[tier]
    pts = json.load(open(os.path.join(ROOT, "art", "blender", "parts", sid, outline + ".json")))["points"]
    loop_pts = resample([px(x, y) for x, y in pts], 180)       # 9 px outside the sticker: the comets' track
    edge = offset(loop_pts, -.08)                               # the sticker's own edge: the light sits half behind it
    bottom = min(range(len(loop_pts)), key=lambda i: loop_pts[i][1]) / len(loop_pts)
    rim = gp_object(coll, sid + "_rim", depth=.3)
    ride(rim, arm, bone)
    m_halo = gp_mat(rim, f"glow_halo_{tier}", g["halo"])
    m_charge = gp_mat(rim, f"glow_charge_{tier}", g["charge"])
    m_comet = gp_mat(rim, f"glow_comet_{tier}", g["comet"])
    m_hot = gp_mat(rim, "glow_white", WHITE)
    aura, runs = Board(), Board()
    L0 = g["level"]

    def aura_at(f, level, charge=0.0, crackle=0.0, hold=2):
        e = jitter(edge, crackle * .5, f) if crackle else edge
        grow = .85 + .15 * min(level, 2)
        lv = level * L0

        def fn(dr):
            for r, a in ((.38, .08), (.29, .09), (.21, .10), (.14, .12)):
                stroke(dr, e, r * grow, opacity=min(1, a * lv * (1 - .6 * charge)), mat=m_halo, cyclic=True)
            if charge > .02:
                for r, a in ((.2, .10), (.13, .14), (.085, .18)):
                    stroke(dr, e, r * grow, opacity=min(1, a * charge * lv), mat=m_charge, cyclic=True)
            if crackle:
                stroke(dr, jitter(loop_pts, crackle * 1.6, f + 5), .014, opacity=min(1, .8 * lv), mat=m_hot, cyclic=True)
        aura.add(f, fn, hold)

    def comet(f, head, length, level=1.0, hold=2, backward=False):
        p = arc(loop_pts, head if backward else head - length, length)
        if backward:
            p = p[::-1]
        m = len(p)
        tail = [min(1.0, (j / max(1, m - 1)) ** 1.6 * 1.3) for j in range(m)]      # faint tail, bright head
        lv = level * (.85 + .15 * L0)

        def fn(dr):
            stroke(dr, p, 0, radii=taper(m, .075 * lv, ends=.18), opacities=[.35 * t for t in tail], mat=m_comet)
            stroke(dr, p, 0, radii=taper(m, .045 * lv, ends=.18), opacities=[.8 * t for t in tail], mat=m_comet)
            stroke(dr, p, 0, radii=taper(m, .018 * lv, ends=.18), opacities=tail, mat=m_hot)
        runs.add(f, fn, hold)

    if "idle" in clips:                              # it breathes, two comets chase round once a loop
        f0, f1 = clips["idle"]
        n = f1 - f0 + 1
        for f in range(f0, f1 + 1, 2):
            t = (f - f0) / n
            aura_at(f, .9 + .2 * math.sin(2 * math.pi * t))
            comet(f, t, .14)
            comet(f, t + .5, .1, level=.75)
    if "land" in clips:                              # it flares with the landing, light runs up both sides
        f0, f1 = clips["land"]
        la = land_at or f0 + 2
        for f in range(f0, f1 + 1):
            hit = math.exp(-max(0, f - la) / 3.5) if f >= la else (f - f0) / max(1, la - f0)
            aura_at(f, 1 + 1.4 * hit, charge=.7 * hit, hold=1)
            if la <= f <= la + 11:
                u = (f - la) / 11
                comet(f, bottom + .5 * u, .12 * (1 - u) + .04, level=1.3 - .5 * u, hold=1)
                comet(f, bottom - .5 * u, .12 * (1 - u) + .04, level=1.3 - .5 * u, hold=1, backward=True)
    if "hit" in clips:                               # it burns bright, three comets race round
        f0, f1 = clips["hit"]
        a, b = hit_span or (f0 + 4, f1 - 6)
        for f in range(f0, f1 + 1, 2):
            lv = 1 + .6 * smooth(f0, a + 4, f) - .6 * smooth(b - 8, f1, f)
            aura_at(f, lv, charge=.5 * (lv - 1) / .6)
            if a <= f <= b:
                for j in range(3):
                    comet(f, (f - a) / 14 + j / 3, .1, level=1.2)
    if "multi" in clips:                             # it pulses with each swell, crackling between
        f0, f1 = clips["multi"]
        ps = pulses or [f0 + (f1 - f0) * k // 5 for k in (1, 2, 3)]
        c0, c1 = charge_span or (ps[0] - 4, ps[-1] + 2)
        for f in range(f0, f1 + 1, 2):
            pulse = sum(math.exp(-((f - p) / 2.2) ** 2) for p in ps)
            charged = smooth(c0, c0 + 4, f) * (1 - smooth(c1 - 1, c1 + 4, f))
            aura_at(f, 1 + 1.2 * pulse + .3 * charged, charge=min(1, pulse + .3 * charged), crackle=.03 * charged)
            if charged > .1:
                for j in range(4):
                    comet(f, (f - c0) / 10 + j / 4, .07, level=1.1, backward=j % 2 == 1)
    aura.draw(gp_layer(rim, "aura"))
    runs.draw(gp_layer(rim, "comets"))
    return rim


def save(sid):
    """Save the symbol's Blender file: art/blender/symbols/<sid>.blend (the rig, its four clips on the NLA
    track, the Grease Pencil effects, the compositor)."""
    out = os.path.join(ROOT, "art", "blender", "symbols")
    os.makedirs(out, exist_ok=True)
    for a in [a for a in bpy.data.actions if a.users == 0 and not a.use_fake_user]:
        bpy.data.actions.remove(a)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, sid + ".blend"))
    return bpy.data.filepath


# ------------------------------------------------------------------ rendering
def clip_ranges(sid):
    """The clips' frames, {"idle": (first, last), ...}: as the animation script recorded them on the rig
    (arm["clips"]), else read off its NLA strips (a loop's last key is its first frame again)."""
    arm = bpy.data.objects[sid + "_rig"]
    if "clips" in arm.keys():
        return {k: (int(v[0]), int(v[1])) for k, v in arm["clips"].items()}
    out = {}
    for st in arm.animation_data.nla_tracks["clips"].strips:
        name = st.name[len(sid) + 1:]
        out[name] = (int(round(st.frame_start)), int(round(st.frame_end)) - (1 if name == "idle" else 0))
    return out


def clip_slow(sid, name):
    """How many times slower than keyed a clip plays (arm["slow"], set by the animation script; 1 = as keyed)."""
    return float(bpy.data.objects[sid + "_rig"].get("slow", {}).get(name, 1))


def render_clip(sc, name, start, end, out_dir, slow=1.0):
    """Render frames start..end to out_dir/<name>/####.png (RGBA, through the compositor).
    slow > 1 plays the clip that many times slower with Blender's Time Remapping: every curve is evaluated between
    its keys, so the motion stays smooth (effects drawn frame by frame hold their drawing). A loop (end + 1 is
    start again) is sampled evenly round its whole cycle, so it still joins up."""
    for f in glob.glob(f"{out_dir}/{name}/*.png"):     # a clip's frame count can change: no stale frames left over
        os.remove(f)
    if slow == 1:
        sc.frame_start, sc.frame_end = start, end
    else:
        # Blender evaluates frame f at f * old / new
        sc.render.frame_map_old, sc.render.frame_map_new = 100, round(100 * slow)
        k = sc.render.frame_map_new / sc.render.frame_map_old
        sc.frame_start = math.ceil(start * k)
        sc.frame_end = sc.frame_start + round((end - start + 1) * k) - 1
    sc.render.filepath = f"{out_dir}/{name}/"
    try:
        bpy.ops.render.render(animation=True, scene=sc.name)
    finally:
        sc.render.frame_map_old = sc.render.frame_map_new = 100
