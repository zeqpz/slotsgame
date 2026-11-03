# H6 - the skateboard (seen from underneath) - animated in Blender: four Actions on its rig (idle, land, hit, multi)
# laid one after another on the rig's NLA track, and its effects drawn frame by frame in Grease Pencil.
#   the board   keyed by hand on two helper bones added here: "air" carries the jumps, leans and spins, "flip" rolls
#               the board about its own long axis (it turns onto the board's axis, squashes across it and the deck
#               turns back by the same angle: R(a) S R(-a) - so the board thins to its edge and comes back mirrored,
#               the way a board rolls over seen from below). Idle: it carves, rolling from rail to rail. Land: it
#               slaps down on its wheels and bucks. Hit: a kickflip - crouch, pop, the board flips over once (its grip
#               tape shows for the half turn it is upside down, the trucks drop behind it), catches and lands. Multi:
#               the charge winds it up like a spring in three jolts, and it lets go in a 360 shove-it
#   the trucks  steer against the board's lean (a real carve) and give on their bushings when it lands
#   the glow    tier 2 neon (fxkit.neon's light), drawn each frame along the silhouette the posed parts make - the
#               board spins and flips, so the glow follows it rather than riding one bone
#   effects     pop dust, speed lines, the flip's swoosh, the spin's smear, sparkles, charge crackle, shock rings,
#               landing dust and impact ticks
# Runs INSIDE Blender, after build_symbol_scene.py (tools/blender/run.py runs both in a background Blender).
import bpy, importlib, math, os, random, sys
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
import fxkit
importlib.reload(fxkit)
from fxkit import (rest, px, smooth, gp_object, gp_mat, gp_layer, ride, stroke, star, Board, LIME, VIOLET, WHITE, GOLD, PINK)

SID = "H6"
sc, arm, spec = fxkit.setup(SID)
FPS = sc.render.fps
ART, FXB, FX = fxkit.layers(sc, SID)
fxkit.glow_compositor(sc, SID, back=dict(strength=1.0, size=.55, gain=1.6), front=dict(strength=.85, size=.4, gain=1.5))
if arm.animation_data:
    arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)

PARTS = ["deck", "truck_f", "truck_b"]
CENTER = tuple(next(p for p in spec["parts"] if p["name"] == "deck")["pivot"])   # the deck's middle (its centroid)
AX = -48.2                   # the board's long axis, degrees in the picture (nose top left, tail bottom right)
CLIPS = {"idle": (1, 72), "land": (101, 124), "hit": (201, 250), "multi": (301, 346)}
arm["clips"] = {k: list(v) for k, v in CLIPS.items()}
WHEELS = [(176, 528), (428, 574), (548, 874), (752, 924)]          # each wheel's lowest point (icon px)
NOSE, TAIL = (175, 120), (880, 890)


# ------------------------------------------------------------------ the rig: two helper bones over the deck
def helpers():
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    head = fxkit.vec(*CENTER)
    made = {}
    for name in ("air", "flip"):
        b = eb.get(name) or eb.new(name)
        b.head, b.tail, b.roll = head, head + Vector((0, 0, .6)), 0
        made[name] = b
    made["flip"].parent = made["air"]
    eb["deck"].parent = made["flip"]
    bpy.ops.object.mode_set(mode="OBJECT")
    for n in ("air", "flip"):
        arm.pose.bones[n].rotation_mode = "XYZ"


helpers()
BONES = ["air", "flip"] + PARTS
CH = {"x": ("location", 0), "y": ("location", 1), "r": ("rotation_euler", 2), "sx": ("scale", 0), "sy": ("scale", 1)}


def k1(bone, f, **chans):
    """Key single channels of a bone (x / y units, r degrees, sx / sy; s = both): only those F-curves get a key."""
    if "s" in chans:
        s = chans.pop("s"); chans["sx"] = chans["sy"] = s
    pb = arm.pose.bones[bone]
    for ch, v in chans.items():
        path, i = CH[ch]
        getattr(pb, path)[i] = math.radians(v) if ch == "r" else v
        pb.keyframe_insert(path, index=i, frame=f, group=bone)


def keys(bone, ch, pairs):
    for f, v in pairs:
        k1(bone, f, **{ch: v})


def hard(act, bone, ch, f):
    path, i = CH[ch]
    fxkit.hard(act, bone, path, i, f)


def axis_on(f0, f1):
    """The flip bone turned onto the board's axis and the deck turned back, for the whole clip: R(a) R(-a) = no
    change until the flip bone squashes."""
    for f in (f0, f1):
        k1("flip", f, r=AX); k1("deck", f, r=-AX)


# ------------------------------------------------------------------ the grip side: dark grip tape when it is upside down
def grip_material():
    """The deck's material shows grip tape (dark, gritty; the white sticker border stays white) where its "grip"
    value is 1 - keyed on for the frames the board is upside down (Blender draws a mirrored mesh as front-facing,
    so it is keyed, not read off the face)."""
    mat = bpy.data.materials[SID + "_deck"]
    nt = mat.node_tree
    N, L = nt.nodes, nt.links
    tex = next(n for n in N if n.type == "TEX_IMAGE")
    emit = next(n for n in N if n.type == "EMISSION")
    val = N.new("ShaderNodeValue"); val.name = val.label = "grip"; val.outputs[0].default_value = 0.0
    sep = N.new("ShaderNodeSeparateColor"); L.new(tex.outputs["Color"], sep.inputs[0])

    def mathn(op, a, b, clamp=False):
        n = N.new("ShaderNodeMath"); n.operation = op; n.use_clamp = clamp
        if isinstance(a, (int, float)):
            n.inputs[0].default_value = a
        else:
            L.new(a, n.inputs[0])
        if isinstance(b, (int, float)):
            n.inputs[1].default_value = b
        else:
            L.new(b, n.inputs[1])
        return n.outputs[0]
    lo = mathn("MINIMUM", mathn("MINIMUM", sep.outputs[0], sep.outputs[1]), sep.outputs[2])
    white = mathn("MULTIPLY", mathn("SUBTRACT", lo, .72), 1 / .16, clamp=True)        # the sticker border
    fac = mathn("MULTIPLY", val.outputs[0], mathn("SUBTRACT", 1.0, white), clamp=True)
    uv = N.new("ShaderNodeTexCoord")
    noise = N.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 260.0; noise.inputs["Detail"].default_value = 2.0
    L.new(uv.outputs["UV"], noise.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = .35, (.045, .045, .052, 1)
    ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = .72, (.15, .15, .165, 1)
    L.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"
    L.new(fac, mix.inputs["Factor"])
    ca, cb = [s for s in mix.inputs if s.type == "RGBA"][:2]
    L.new(tex.outputs["Color"], ca); L.new(ramp.outputs["Color"], cb)
    L.new([s for s in mix.outputs if s.type == "RGBA"][0], emit.inputs["Color"])
    return val


GRIP = grip_material()


def flipped(frames):
    """The frames the board is upside down: grip tape on, the trucks drawn behind the deck."""
    obs = [bpy.data.objects[SID + "_" + n] for n in ("truck_f", "truck_b")]
    base = {o.name: o.location.copy() for o in obs}
    # which way is "behind": nudge each truck along each of its local axes and keep the one that moves it away
    # from the camera (+y in the world)
    ax = {}
    for o in obs:
        best = None
        for i in range(3):
            bpy.context.view_layer.update()
            y0 = o.matrix_world.translation.y
            o.location[i] += .1
            bpy.context.view_layer.update()
            dy = o.matrix_world.translation.y - y0
            o.location = base[o.name]
            if best is None or abs(dy) > abs(best[1]):
                best = (i, dy)
        ax[o.name] = (best[0], 1 if best[1] > 0 else -1)
    bpy.context.view_layer.update()
    allf = sorted(frames)
    for f in allf:
        for f_ in (f - 1, f + 1):
            if f_ not in frames:
                GRIP.outputs[0].default_value = 0.0
                GRIP.outputs[0].keyframe_insert("default_value", frame=f_)
                for o in obs:
                    o.location = base[o.name]
                    o.keyframe_insert("location", index=ax[o.name][0], frame=f_)
        GRIP.outputs[0].default_value = 1.0
        GRIP.outputs[0].keyframe_insert("default_value", frame=f)
        for o in obs:
            i, sg = ax[o.name]
            o.location = base[o.name]
            o.location[i] += sg * .35
            o.keyframe_insert("location", index=i, frame=f)
    for owner in [bpy.data.materials[SID + "_deck"].node_tree] + obs:
        ad = owner.animation_data
        if ad and ad.action:
            for fc in fxkit.fcurves(ad.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"
    for o in obs:
        o.location = base[o.name]



# ================================================================== idle: it carves, rail to rail
f0, f1 = CLIPS["idle"]
act = fxkit.begin_action(arm, SID + "_idle")
rest(arm, BONES, f0)
axis_on(f0, f1 + 1)
keys("air", "r", [(19, 1.6), (37, 0), (55, -1.6), (73, 0)])
keys("air", "y", [(19, .03), (37, 0), (55, .03), (73, 0)])
keys("flip", "sy", [(19, .962), (37, 1), (55, .962), (73, 1)])           # it rolls onto one rail, then the other
keys("truck_f", "r", [(20, 3.2), (38, 0), (56, -3.2), (73, 0)])           # the trucks steer against the lean
keys("truck_b", "r", [(22, -2.8), (40, 0), (58, 2.8), (73, 0)])
fxkit.make_cyclic(act)
fxkit.end_action(arm, act, f0)

# ================================================================== land: it slaps down on its wheels and bucks
f0, f1 = CLIPS["land"]
act = fxkit.begin_action(arm, SID + "_land")
rest(arm, BONES, f0)
axis_on(f0, f1)
keys("air", "y", [(103, -.07), (107, .09), (111, 0), (116, .012), (124, 0)])
keys("air", "sx", [(103, 1.05), (107, .975), (111, 1.012), (116, .997), (124, 1)])
keys("air", "sy", [(103, .91), (107, 1.045), (111, .982), (116, 1.006), (124, 1)])
keys("air", "r", [(103, -.6), (107, .8), (111, -.3), (116, 0), (124, 0)])
for ch in ("y", "sy", "sx"):
    hard(act, "air", ch, 103)
hard(act, "air", "y", 111)
keys("truck_f", "r", [(103, 4.6), (107, -2.8), (111, 1.3), (116, -.45), (121, .1), (124, 0)])
keys("truck_b", "r", [(103, -4.2), (107, 2.5), (111, -1.1), (116, .35), (121, -.08), (124, 0)])
fxkit.end_action(arm, act, f0)

# ================================================================== hit: a kickflip
f0, f1 = CLIPS["hit"]
FL0, FL1 = 209, 219                                   # one turn over, about its long axis
act = fxkit.begin_action(arm, SID + "_hit")
rest(arm, BONES, f0)
axis_on(f0, f1)
keys("air", "y", [(204, -.07), (206, -.09), (213, 1.22), (216, 1.3), (222, 0), (225, .17), (228, 0), (233, .02), (240, 0), (250, 0)])
keys("air", "r", [(204, 3.0), (206, 3.6), (213, -7.0), (218, -4.2), (222, 1.6), (226, -1.1), (230, .4), (236, 0), (250, 0)])
keys("air", "sx", [(204, 1.04), (206, 1.05), (210, .965), (214, 1), (222, 1.07), (225, .97), (228, 1.02), (232, .996), (237, 1), (250, 1)])
keys("air", "sy", [(204, .93), (206, .92), (210, 1.06), (214, 1), (222, .88), (225, 1.05), (228, .965), (232, 1.012), (237, 1), (250, 1)])
for ch in ("y", "sy", "sx", "r"):
    hard(act, "air", ch, 222)
hard(act, "air", "y", 228)
upside = set()
k1("flip", FL0 - 1, sy=1)
for f in range(FL0, FL1 + 1):                          # dense keys: the turn is a cosine across the board
    c = math.cos(2 * math.pi * (f - FL0) / (FL1 - FL0))
    k1("flip", f, sy=c)
    if c < 0:
        upside.add(f)
k1("flip", FL1 + 1, sy=1)
keys("truck_f", "r", [(204, 2.0), (206, 2.6), (209, -3.0), (213, 1.6), (218, -1.0), (222, 5.2), (225, -3.0), (228, 2.0), (232, -.8),
                      (237, .25), (242, 0), (250, 0)])
keys("truck_b", "r", [(204, -2.0), (206, -2.6), (209, 3.0), (213, -1.6), (218, 1.0), (222, -5.0), (225, 2.8), (228, -1.9), (232, .75),
                      (237, -.22), (242, 0), (250, 0)])
hard(act, "truck_f", "r", 222); hard(act, "truck_b", "r", 222)
fxkit.end_action(arm, act, f0)
flipped(upside)

# ================================================================== multi: wound up by the charge, then a 360 shove-it
f0, f1 = CLIPS["multi"]
PUL = (305, 311, 317)
act = fxkit.begin_action(arm, SID + "_multi")
rest(arm, BONES, f0)
axis_on(f0, f1)
keys("air", "r", [(303, 0), (305, 3.0), (308, 1.8), (311, 7.0), (314, 5.4), (317, 11.0), (320, 9.4), (323, 14.5), (326, 15.5),
                  (331, -250), (337, -352), (341, -361.6), (344, -359.6), (346, -360)])
keys("air", "s", [(303, 1), (305, 1.045), (308, 1), (311, 1.055), (314, 1), (317, 1.065), (320, 1.0), (323, .965), (326, .95), (330, .9),
                  (334, .9)])
keys("air", "sx", [(337, 1.05), (340, .985), (343, 1.004), (346, 1)])
keys("air", "sy", [(337, .89), (340, 1.03), (343, .995), (346, 1)])
keys("air", "y", [(323, -.03), (326, -.05), (331, .26), (337, 0), (340, .05), (343, 0), (346, 0)])
for ch in ("y", "sx", "sy"):
    hard(act, "air", ch, 337)
for i, f in enumerate(range(318, 327)):                # charged to bursting, it shivers
    k1("air", f, x=.012 if i % 2 else -.012)
k1("air", 317, x=0); k1("air", 327, x=0)
tf = [(303, 0)]
tb = [(303, 0)]
for p in PUL:                                          # each jolt rattles the trucks
    tf += [(p, 3.4), (p + 1, -2.6), (p + 2, 1.4), (p + 4, 0)]
    tb += [(p, -3.0), (p + 1, 2.4), (p + 2, -1.2), (p + 4, 0)]
tf += [(326, 0), (331, -4.0), (336, -2.0), (337, 4.6), (340, -2.4), (343, .8), (346, 0)]
tb += [(326, 0), (331, 3.6), (336, 1.8), (337, -4.2), (340, 2.2), (343, -.7), (346, 0)]
keys("truck_f", "r", tf); keys("truck_b", "r", tb)
fxkit.end_action(arm, act, f0)


# ------------------------------------------------------------------ the tier glow, following the posed silhouette
# fxkit.neon rides one bone; here several parts move against each other, so the glow is drawn each frame along the
# silhouette the posed parts actually make (the same light as fxkit.neon: the halo colour in stacked bands just
# behind the sticker's edge, comets running round it, the charge colour flooding in) - no glow is left in the air
# where a part has moved away, and none is missing where it has moved to.
def silhouettes(names, frames, cell=3.0, grow=9.0):
    """{frame: closed loop of world (x, z) points}, `grow` icon px outside the union of the named parts as they are
    posed at that frame. Each part's opaque pixels (every `cell` px of its image) ride its evaluated mesh (a bone's
    plane, or a chain's bent grid), are splatted onto a grid of `cell` px, grown, and the outer edge is traced."""
    import numpy as np
    dg = bpy.context.evaluated_depsgraph_get()
    samples = []
    for name in names:
        ob = bpy.data.objects[SID + "_" + name]
        img = ob.data.materials[0].node_tree.nodes["Image Texture"].image if "Image Texture" in ob.data.materials[0].node_tree.nodes else None
        if img is None:
            img = next(n.image for n in ob.data.materials[0].node_tree.nodes if n.type == "TEX_IMAGE")
        w, h = img.size
        px_ = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(px_)
        al = px_.reshape(h, w, 4)[::-1, :, 3]                 # top row first
        step = max(1, int(round(cell)))
        ys, xs = np.nonzero(al[::step, ::step] > .5)
        u = (xs * step + .5) / w
        v = (ys * step + .5) / h                              # down from the top
        me = ob.data
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        z0 = co[0, 2]
        nx = int(np.sum(np.abs(co[:, 2] - z0) < 1e-6)) - 1   # the grid's columns (a plane: 1)
        ny = len(co) // (nx + 1) - 1
        if len(co) == 4:                                      # a plane: corners bottom-left, bottom-right, top-right, top-left
            kind = "plane"
            ij = None
        else:
            kind = "grid"
            fi, fj = u * nx, v * ny
            i0 = np.clip(np.floor(fi).astype(int), 0, nx - 1); j0 = np.clip(np.floor(fj).astype(int), 0, ny - 1)
            ij = (i0, j0, fi - i0, fj - j0, nx)
        samples.append((ob, kind, u, v, ij))
    N = int(1300 / cell) + 8
    off = 6.5 + 4 * cell / 100
    r_close = 1
    r_grow = int(round(grow / cell))
    disk = [(dy, dx) for dy in range(-r_grow - r_close, r_grow + r_close + 1) for dx in range(-r_grow - r_close, r_grow + r_close + 1)
            if dx * dx + dy * dy <= (r_grow + r_close + .3) ** 2]
    out = {}
    for f in frames:
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        pts = []
        for ob, kind, u, v, ij in samples:
            oe = ob.evaluated_get(dg)
            me = oe.to_mesh()
            co = np.empty(len(me.vertices) * 3, np.float32)
            me.vertices.foreach_get("co", co)
            oe.to_mesh_clear()
            co = co.reshape(-1, 3)
            M = np.array(ob.matrix_world, np.float32)
            wco = co @ M[:3, :3].T + M[:3, 3]
            if kind == "plane":
                bl, br, tl = wco[0], wco[1], wco[3]
                p = bl[None] + u[:, None] * (br - bl)[None] + (1 - v)[:, None] * (tl - bl)[None]
            else:
                i0, j0, a, b, nx = ij
                g = wco.reshape(-1, nx + 1, 3)
                p = (g[j0, i0] * ((1 - a) * (1 - b))[:, None] + g[j0, i0 + 1] * (a * (1 - b))[:, None]
                     + g[j0 + 1, i0] * ((1 - a) * b)[:, None] + g[j0 + 1, i0 + 1] * (a * b)[:, None])
            pts.append(p[:, [0, 2]])
        P = np.concatenate(pts)
        gx = np.clip(((P[:, 0] + off) * 100 / cell).astype(int), 0, N - 1)
        gz = np.clip(((off - P[:, 1]) * 100 / cell).astype(int), 0, N - 1)
        m = np.zeros((N, N), bool)
        m[gz, gx] = True
        grown = np.zeros_like(m)
        for dy, dx in disk:                                  # closed and grown in one pass (a disk of the grow radius)
            grown[max(0, dy):N + min(0, dy), max(0, dx):N + min(0, dx)] |= m[max(0, -dy):N - max(0, dy), max(0, -dx):N - max(0, dx)]
        out[f] = trace(grown, cell, off)
    return out


def trace(m, cell, off):
    """The outer edge of a grid mask as a smooth closed loop of world points (CCW), starting straight under its
    middle (so the comets' positions round it stay put as the shape moves)."""
    import numpy as np
    H, W = m.shape
    pad = np.zeros((H + 2, W + 2), bool); pad[1:-1, 1:-1] = m
    ys, xs = np.nonzero(pad)
    start = (ys.min(), xs[ys == ys.min()].min())
    nb = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
    path, cur, back = [start], start, 6
    for _ in range(200000):
        for k in range(8):
            d = (back + 1 + k) % 8
            ny_, nx_ = cur[0] + nb[d][0], cur[1] + nb[d][1]
            if pad[ny_, nx_]:
                back = (d + 4) % 8
                cur = (ny_, nx_)
                break
        if cur == start:
            break
        path.append(cur)
    pts = [((x - 1 + .5) * cell / 100 - off, off - (y - 1 + .5) * cell / 100) for y, x in path]
    # smooth the stair-steps: a circular moving average, then even spacing
    n = len(pts)
    k = 3
    sm = [(sum(pts[(i + j) % n][0] for j in range(-k, k + 1)) / (2 * k + 1),
           sum(pts[(i + j) % n][1] for j in range(-k, k + 1)) / (2 * k + 1)) for i in range(n)]
    area = sum(sm[i][0] * sm[(i + 1) % n][1] - sm[(i + 1) % n][0] * sm[i][1] for i in range(n))
    if area < 0:
        sm = sm[::-1]
    loop = fxkit.resample(sm, 180)
    cx = sum(p[0] for p in loop) / len(loop); cz = sum(p[1] for p in loop) / len(loop)
    below = [i for i, p in enumerate(loop) if p[1] < cz]
    i0 = min(below, key=lambda i: abs(loop[i][0] - cx)) if below else 0
    return loop[i0:] + loop[:i0]


def neon_live(names, clips, tier=2, land_at=None, hit_span=None, pulses=None, charge_span=None, extra=None):
    """The tier glow (art/STYLE.md), as fxkit.neon draws it, along the posed silhouette of `names` each frame.
    extra(f) -> (level, charge, crackle) adds to the clip's own (an effect that should light the glow)."""
    g = fxkit.TIER_GLOW[tier]
    frames = sorted({f for a, b in clips.values() for f in range(a, b + 1)})
    loops = silhouettes(names, frames)
    rim = gp_object(FXB, SID + "_rim", depth=.3)
    m_halo = gp_mat(rim, f"glow_halo_{tier}", g["halo"])
    m_charge = gp_mat(rim, f"glow_charge_{tier}", g["charge"])
    m_comet = gp_mat(rim, f"glow_comet_{tier}", g["comet"])
    m_hot = gp_mat(rim, "glow_white", WHITE)
    aura, runs = Board(), Board()
    L0 = g["level"]

    def aura_at(f, level, charge=0.0, crackle=0.0):
        loop = loops[f]
        e0 = fxkit.offset(loop, -.08)
        e = fxkit.jitter(e0, crackle * .5, f) if crackle else e0
        grow_ = .85 + .15 * min(level, 2)
        lv = level * L0

        def fn(dr):
            for r, a in ((.38, .08), (.29, .09), (.21, .10), (.14, .12)):
                stroke(dr, e, r * grow_, opacity=min(1, a * lv * (1 - .6 * charge)), mat=m_halo, cyclic=True)
            if charge > .02:
                for r, a in ((.2, .10), (.13, .14), (.085, .18)):
                    stroke(dr, e, r * grow_, opacity=min(1, a * charge * lv), mat=m_charge, cyclic=True)
            if crackle:
                stroke(dr, fxkit.jitter(loop, crackle * 1.6, f + 5), .014, opacity=min(1, .8 * lv), mat=m_hot, cyclic=True)
        aura.add(f, fn)

    def comet(f, head, length, level=1.0, backward=False):
        loop = loops[f]
        p = fxkit.arc(loop, head if backward else head - length, length)
        if backward:
            p = p[::-1]
        m = len(p)
        tail = [min(1.0, (j / max(1, m - 1)) ** 1.6 * 1.3) for j in range(m)]
        lv = level * (.85 + .15 * L0)

        def fn(dr):
            stroke(dr, p, 0, radii=fxkit.taper(m, .075 * lv, ends=.18), opacities=[.35 * t for t in tail], mat=m_comet)
            stroke(dr, p, 0, radii=fxkit.taper(m, .045 * lv, ends=.18), opacities=[.8 * t for t in tail], mat=m_comet)
            stroke(dr, p, 0, radii=fxkit.taper(m, .018 * lv, ends=.18), opacities=tail, mat=m_hot)
        runs.add(f, fn)

    def plus(f, lv, ch, cr):
        if extra:
            a, b, c = extra(f)
            return lv + a, min(1.0, ch + b), cr + c
        return lv, ch, cr
    if "idle" in clips:                              # it breathes; two comets chase round once a loop
        f0, f1 = clips["idle"]
        n = f1 - f0 + 1
        for f in range(f0, f1 + 1):
            t = (f - f0) / n
            aura_at(f, *plus(f, .9 + .2 * math.sin(2 * math.pi * t), 0.0, 0.0))
            comet(f, t, .14)
            comet(f, t + .5, .1, level=.75)
    if "land" in clips:                              # it flares with the landing, light runs up both sides
        f0, f1 = clips["land"]
        la = land_at or f0 + 2
        for f in range(f0, f1 + 1):
            hit = math.exp(-max(0, f - la) / 3.5) if f >= la else (f - f0) / max(1, la - f0)
            aura_at(f, *plus(f, 1 + 1.4 * hit, .7 * hit, 0.0))
            if la <= f <= la + 11:
                u = (f - la) / 11
                comet(f, .5 * u, .12 * (1 - u) + .04, level=1.3 - .5 * u)
                comet(f, -.5 * u, .12 * (1 - u) + .04, level=1.3 - .5 * u, backward=True)
    if "hit" in clips:                               # it burns bright, three comets race round
        f0, f1 = clips["hit"]
        a, b = hit_span or (f0 + 4, f1 - 6)
        for f in range(f0, f1 + 1):
            lv = 1 + .6 * smooth(f0, a + 4, f) - .6 * smooth(b - 8, f1, f)
            aura_at(f, *plus(f, lv, .5 * (lv - 1) / .6, 0.0))
            if a <= f <= b:
                for j in range(3):
                    comet(f, (f - a) / 14 + j / 3, .1, level=1.2)
    if "multi" in clips:                             # it pulses with each swell, crackling between
        f0, f1 = clips["multi"]
        ps = pulses or [f0 + (f1 - f0) * k // 5 for k in (1, 2, 3)]
        c0, c1 = charge_span or (ps[0] - 4, ps[-1] + 2)
        for f in range(f0, f1 + 1):
            pulse = sum(math.exp(-((f - p) / 2.2) ** 2) for p in ps)
            charged = smooth(c0, c0 + 4, f) * (1 - smooth(c1 - 1, c1 + 4, f))
            aura_at(f, *plus(f, 1 + 1.2 * pulse + .3 * charged, min(1, pulse + .3 * charged), .03 * charged))
            if charged > .1:
                for j in range(4):
                    comet(f, (f - c0) / 10 + j / 4, .07, level=1.1, backward=j % 2 == 1)
    aura.draw(gp_layer(rim, "aura"))
    runs.draw(gp_layer(rim, "comets"))
    return rim


# ================================================================== the tier glow, along the board as it moves
neon_live(PARTS, CLIPS, tier=2, land_at=103, hit_span=(207, 240), pulses=PUL, charge_span=(303, 326))


# ================================================================== effects
def at(f, x, y, bone="deck"):
    """Where icon point (x, y) on a part is at frame f (world x, z; f may be fractional)."""
    sc.frame_set(int(math.floor(f)), subframe=f - math.floor(f))
    pb = arm.pose.bones[bone]
    p = arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted() @ fxkit.vec(x, y)
    return p.x, p.z


def frame_of(f, bone="air"):
    sc.frame_set(f)
    pb = arm.pose.bones[bone]
    return (arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted()).copy()


fxw = gp_object(FX, SID + "_fx", depth=-.8)            # stays where the frame is
fxd = gp_object(FX, SID + "_fx_deck", depth=-.8)       # rides the deck
ride(fxd, arm, "deck")
fxt = gp_object(FX, SID + "_fx_truck", depth=-.8)      # rides the front truck
ride(fxt, arm, "truck_f")
back = gp_object(FXB, SID + "_back", depth=.35)        # behind the board, bloomed
w_white = gp_mat(fxw, "fx_white_line", WHITE); w_lime = gp_mat(fxw, "fx_lime_line", LIME); w_pink = gp_mat(fxw, "fx_pink_line", PINK)
w_spark = gp_mat(fxw, "fx_white_fill", WHITE, fill=WHITE); w_gold = gp_mat(fxw, "fx_gold_fill", GOLD, fill=GOLD)
w_pinkf = gp_mat(fxw, "fx_pink_fill", PINK, fill=PINK)
d_spark = gp_mat(fxd, "fx_white_fill", WHITE, fill=WHITE)
t_spark = gp_mat(fxt, "fx_white_fill", WHITE, fill=WHITE)
b_violet = gp_mat(back, "glow_violet", VIOLET); b_pink = gp_mat(back, "glow_pink", PINK); b_white = gp_mat(back, "glow_white", WHITE)
b_pinkf = gp_mat(back, "glow_pink_fill", PINK, fill=PINK); b_whitef = gp_mat(back, "glow_white_fill", WHITE, fill=WHITE)
world, ondeck, ontruck, bb = Board(), Board(), Board(), Board()


def ticks(board, f0, x, z, mat, spread=1.0, n=3):
    """Impact ticks: short strokes flicking out sideways from where something hits."""
    for k in range(6):
        t = k / 5
        for side in (-1, 1):
            for j in range(n):
                ang = math.radians(170 - 30 * j) if side < 0 else math.radians(10 + 30 * j)
                r0, r1 = (.35 + .55 * t) * spread, (.62 + .9 * t) * spread
                board.add(f0 + k, lambda dr, ang=ang, r0=r0, r1=r1, t=t: stroke(
                    dr, [(x + math.cos(ang) * r0, z + math.sin(ang) * r0 * .55), (x + math.cos(ang) * r1, z + math.sin(ang) * r1 * .55)],
                    .028 * (1 - t) + .007, mat=mat))


def trails(board, f0, f1, pts, mat):
    """Speed lines while it shoots up: from where each point is now, back to where it was three frames ago."""
    for f in range(f0, f1 + 1):
        for x, y in pts:
            ax_, az = at(f, x, y)
            bx, bz = at(max(f - 3, f0 - 1), x, y)
            if math.hypot(ax_ - bx, az - bz) < .15:
                continue
            board.add(f, lambda dr, ax_=ax_, az=az, bx=bx, bz=bz: stroke(
                dr, [(ax_, az - .2), (ax_ + (bx - ax_) * 1.5, az - .2 + (bz - az) * 1.5)], 0, mat=mat,
                radii=[.026, .004], opacities=[.95, .25]))


# idle: the paint catches the light, a bearing twinkles
fxkit.sparkle(ondeck, 14, 9, *px(250, 205), .34, d_spark)
fxkit.sparkle(ontruck, 42, 8, *px(444, 519), .28, t_spark, rot0=.5)

# land: ticks where the wheels hit
for x, y in WHEELS:
    ticks(world, 102, *px(x, y + 8), w_white, spread=.75, n=2)

# hit: the pop off the tail, speed lines, the flip's swoosh, sparkles at the top, the landing
ticks(world, 206, *at(206, *TAIL), w_white, spread=.9)
trails(world, 207, 213, [(150, 330), (330, 560), (520, 700), (700, 860), (860, 880)], w_white)
hw = 1.62                                              # the board's half width, across its axis (units)
cA, sA = math.cos(math.radians(AX)), math.sin(math.radians(AX))
for f in range(FL0, FL1 + 1):
    u = (f - FL0) / (FL1 - FL0)
    if not .1 < u < .9:
        continue
    M = frame_of(f)
    for j, st in enumerate((-2.6, 2.6)):               # near the nose and near the tail
        for side in (-1, 1):                            # whoosh marks beside the board, bowing round its edge
            pts = []
            for i in range(9):
                v = i / 8
                along = st + (v - .5) * 1.5
                across = side * (hw * 1.12 + .28 * math.sin(math.pi * v))
                lx, lz = along * cA - across * sA, along * sA + across * cA
                p = M @ (fxkit.vec(*CENTER) + Vector((lx, 0, lz)))
                pts.append((p.x, p.z))
            w = .034 * math.sin(math.pi * u) + .004
            world.add(f, lambda dr, pts=pts, w=w, j=j: stroke(dr, pts, 0, radii=fxkit.taper(len(pts), w, ends=.4),
                                                             mat=(w_white, w_lime)[j]))
rnd = random.Random(6)
for i in range(8):
    x, y = rnd.uniform(-4.8, 4.8), rnd.uniform(-3.5, 5.6)
    fxkit.sparkle(world, 213 + rnd.randint(0, 7), rnd.randint(6, 9), x, y, rnd.uniform(.25, .45), w_gold if i % 3 == 0 else w_spark,
                  rot0=rnd.uniform(0, 1))
for x, y in WHEELS:
    ticks(world, 222, *at(222, x, y + 8), w_white, spread=.9, n=3)
fxkit.starburst(bb, 222, 9, *at(222, *CENTER), 3.6, 6.6, b_pinkf, b_whitef, points=10)

# multi: crackling with the charge, rings as it lets go, the spin's smear, the landing
cx, cz = px(*CENTER)
fxkit.lightning(world, 306, 325, cx, cz, (3.4, 3.4), (5.2, 5.2), (w_pink, w_white, w_white), per=3, step=2, seed=3)
for p in PUL:
    for i, (x, y) in enumerate(((176, 470), (428, 520), (548, 820), (752, 870))):
        fxkit.sparkle(world, p + i % 2, 6, *at(p, x, y), .22 + .04 * (p - PUL[0]) / 6, w_spark, rot0=.3 * i)
fxkit.shock_rings(bb, 327, cx, cz, 4.4, 6.4, (b_pink, b_white, b_violet), life=12, lag=3)
fxkit.streaks(world, 327, 7, cx, cz, 4.6, 6.4, (w_white, w_pink), n=14, rot=.25)
for f in range(328, 338):                             # the spin's smear: the nose and tail sweep their arcs
    for tip in (NOSE, TAIL):
        pts = [at(f - 3.5 + 3.5 * i / 20, *tip) for i in range(21)]
        m = len(pts)
        world.add(f, lambda dr, pts=pts, m=m: stroke(dr, pts, 0, radii=[.004 + .045 * (i / (m - 1)) ** 1.6 for i in range(m)],
                                                     opacities=[.15 + .85 * (i / (m - 1)) for i in range(m)], mat=w_white))
for x, y in WHEELS:
    ticks(world, 337, *at(337, x, y + 8), w_white, spread=.85, n=2)
world.draw(gp_layer(fxw, "fx"))
ondeck.draw(gp_layer(fxd, "fx"))
ontruck.draw(gp_layer(fxt, "fx"))
bb.draw(gp_layer(back, "burst"))

# ================================================================== on the art: dust kicked up by the wheels
dust = gp_object(ART, SID + "_dust", depth=-1.0)       # in front of every part
m_dust = gp_mat(dust, "fx_dust", (.42, .4, .41, 1), fill=(.82, .79, .75, 1))
db = Board()
for f, big in ((102, .55), (222, .8), (337, .7)):
    for i, (x, y) in enumerate(WHEELS):
        wx, wz = at(f, x, y)
        side = -1 if i % 2 == 0 else 1
        fxkit.dust(db, f + (i % 2), 10, wx + side * .25, wz - .05, big * .55, m_dust, drift=(side * 1.3 * big, .2 * big), seed=7 * i + f)
tx, tz = at(206, *TAIL)
fxkit.dust(db, 206, 9, tx + .2, tz - .1, .5, m_dust, drift=(.9, .1), seed=4)
db.draw(gp_layer(dust, "dust"))

sc.frame_start, sc.frame_end = 1, max(b for a, b in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], "| saved", fxkit.save(SID))
