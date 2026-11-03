# L2 - the graffiti marker and its orange scribble - animated in Blender: four Actions on its rig (idle, land, hit,
# multi) laid one after another on the rig's NLA track, its line written on in the slices' materials, and its
# effects drawn frame by frame in Grease Pencil on the same timeline.
#   the line    the marker's own stroke, cut in twelve slices in the order it was scribbled (tools/blender/cuts/L2.py).
#               Each slice's material reads, pixel by pixel, how far along that order it lies (a map made here from the
#               recipe's path) against one keyed "progress": the line is drawn on, or rewound, along the scribble
#   the marker  keyed on a bone turned to lie along the marker, so it squashes and pumps along itself; while the line
#               is drawn it follows the drawing point - leaning into each pass, swinging back at each turn
#   idle        it lifts, taps its nib (a spatter), scribbles quick strokes across (flecks fly), leans back to look at
#               its work; a wet sheen runs along the fresh paint and a drop gathers on the nib and falls
#   land        it lands on its nib - the sticker squashes, the marker bounces along itself, paint spatters
#   hit         it rewinds the line into the nib, then scribbles it back on, spraying at the drawing point, and pops
#   multi       charged, it rattles; it rewinds the line and writes it back on, fast, its drawing point burning
#               white-gold; then it pumps the nib and paint bursts out in a splash, rings of light
# Runs INSIDE Blender, after build_symbol_scene.py (tools/blender/run.py runs both in a background Blender).
import bpy, importlib, math, os, random, sys
import numpy as np
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "icon_rigs", "recipes"))
import fxkit
importlib.reload(fxkit)
from fxkit import key, rest, px, vec, smooth, gp_object, gp_mat, gp_layer, ride, stroke, star, ring, Board, WHITE, GOLD
from L2 import PATH, SLICES                          # the scribble's centre line, in drawing order (recipe)

SID = "L2"
sc, arm, spec = fxkit.setup(SID)
FPS = sc.render.fps
ORANGE = (1.0, 0.45, 0.06, 1)
PAINT_INK = (.32, .12, .02, 1)
PIVOT = (545, 515)                                   # the marker's middle (recipe)
NIB = (232, 930)                                     # the tip of its chisel nib
AXIS = Vector((0.648, 0.0, 0.762))                   # along the marker, nib -> cap (world, z up)
ACROSS = Vector((0.762, 0.0, -0.648))                # its local x: across it, toward its lower right
SOFT = .003                                          # how soft the drawing point is, as a share of the line

# ------------------------------------------------------------------ the rig: a root, and the marker's bone along it
keep = {o.name: o.matrix_world.copy() for o in sc.objects if o.parent_type == "BONE"}
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
root = eb.get("root") or eb.new("root")
root.head = vec(500, 965); root.tail = root.head + Vector((0, 0, .6)); root.roll = 0
mk = eb["marker"]
mk.tail = mk.head + AXIS * .8
mk.align_roll(Vector((0, -1, 0)))
for b in eb:
    if b.name != "root" and b.parent is None:
        b.parent = root
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

BONES = ["root", "marker"] + SLICES
CLIPS = {"idle": (1, 80), "land": (101, 126), "hit": (201, 252), "multi": (301, 348)}
arm["clips"] = {k: list(v) for k, v in CLIPS.items()}
arm["slow"] = {"idle": 2.5}
IDLE_CALM = .7                   # the idle's moves at 70% of how far they were keyed (fxkit.calm)     # owner, 2026-11-03: the idle plays 2.5x slower than keyed (Time Remapping, fxkit.render_clip)

# ------------------------------------------------------------------ the write-on, in the slices' materials
P = np.array(PATH, np.float64)
SEG = P[1:] - P[:-1]
SEGL = np.sqrt((SEG ** 2).sum(1))
CUM = np.concatenate([[0], np.cumsum(SEGL)])
LENGTH = CUM[-1]


def along(xy):
    """How far along the scribble (0..1) the nearest point of its centre line is, for each icon-px point."""
    best_d = np.full(len(xy), np.inf); best_t = np.zeros(len(xy))
    for i in range(len(SEG)):
        u = np.clip(((xy - P[i]) @ SEG[i]) / SEGL[i] ** 2, 0, 1)
        d = (((P[i] + u[:, None] * SEG[i]) - xy) ** 2).sum(1)
        better = d < best_d
        best_d[better] = d[better]
        best_t[better] = (CUM[i] + u[better] * SEGL[i]) / LENGTH
    return best_t


def path_at(t):
    """The point on the centre line t of the way along, and the direction it runs there (icon px)."""
    d = min(max(t, 0), 1) * LENGTH
    i = min(int(np.searchsorted(CUM, d, side="right")) - 1, len(SEG) - 1)
    u = (d - CUM[i]) / SEGL[i]
    return tuple(P[i] + SEG[i] * u), tuple(SEG[i] / SEGL[i])


grp = bpy.data.node_groups.get(SID + "_reveal") or bpy.data.node_groups.new(SID + "_reveal", "ShaderNodeTree")
grp.nodes.clear()
for s in list(grp.interface.items_tree):
    grp.interface.remove(s)
grp.interface.new_socket("t", in_out="INPUT", socket_type="NodeSocketFloat")
grp.interface.new_socket("alpha", in_out="INPUT", socket_type="NodeSocketFloat")
grp.interface.new_socket("alpha", in_out="OUTPUT", socket_type="NodeSocketFloat")
gi, go = grp.nodes.new("NodeGroupInput"), grp.nodes.new("NodeGroupOutput")
prog = grp.nodes.new("ShaderNodeValue"); prog.name = prog.label = "progress"
prog.outputs[0].default_value = 1 + SOFT


def mnode(op, a, b, clamp=False):
    n = grp.nodes.new("ShaderNodeMath"); n.operation = op; n.use_clamp = clamp
    for k, v in enumerate((a, b)):
        if isinstance(v, (int, float)):
            n.inputs[k].default_value = v
        else:
            grp.links.new(v, n.inputs[k])
    return n.outputs[0]


shown = mnode("ADD", mnode("DIVIDE", mnode("SUBTRACT", prog.outputs[0], gi.outputs["t"]), SOFT), .5, clamp=True)
grp.links.new(mnode("MULTIPLY", shown, gi.outputs["alpha"]), go.inputs["alpha"])

parts = {p["name"]: p for p in spec["parts"]}
for s in SLICES:
    x0, y0, x1, y1 = parts[s]["box"]
    w, h = x1 - x0, y1 - y0
    xs, ys = np.meshgrid(np.arange(w) + x0 + .5, (y1 - .5) - np.arange(h))      # image rows run bottom up
    t = along(np.stack([xs.ravel(), ys.ravel()], 1)).astype(np.float32)
    # written to an EXR beside the parts (a generated image is not kept in the .blend) and loaded back from it
    path = os.path.join(fxkit.ROOT, "art", "blender", "parts", SID, f"{s}_along.exr")
    for old in [i for i in bpy.data.images if i.name.startswith(f"{SID}_{s}_along")]:
        bpy.data.images.remove(old)
    tmp = bpy.data.images.new(f"{SID}_{s}_along_tmp", w, h, alpha=False, float_buffer=True)
    tmp.colorspace_settings.name = "Non-Color"           # before writing: else it is saved through a colour curve
    px4 = np.repeat(t, 4); px4[3::4] = 1
    tmp.pixels.foreach_set(px4)
    tmp.filepath_raw = path
    tmp.file_format = "OPEN_EXR"
    tmp.save()
    bpy.data.images.remove(tmp)
    img = bpy.data.images.load(path)
    img.name = f"{SID}_{s}_along"
    img.colorspace_settings.name = "Non-Color"
    chk = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(chk)
    assert abs(chk[0::4].max() - t.max()) < 1e-3, f"{s}: the along-map did not come back from {path}"
    nt = bpy.data.materials[f"{SID}_{s}"].node_tree
    tex = next(n for n in nt.nodes if n.type == "TEX_IMAGE")
    mix = next(n for n in nt.nodes if n.type == "MIX_SHADER")
    tm = nt.nodes.new("ShaderNodeTexImage"); tm.image = img; tm.interpolation = "Linear"; tm.extension = "EXTEND"
    gn = nt.nodes.new("ShaderNodeGroup"); gn.node_tree = grp
    nt.links.new(tm.outputs["Color"], gn.inputs["t"])
    nt.links.new(tex.outputs["Alpha"], gn.inputs["alpha"])
    nt.links.new(gn.outputs["alpha"], mix.inputs["Fac"])


def progress(f, v, interp="BEZIER"):
    prog.outputs[0].default_value = v
    prog.outputs[0].keyframe_insert("default_value", frame=f)
    for fc in fxkit.fcurves(grp.animation_data.action):
        for kp in fc.keyframe_points:
            if abs(kp.co.x - f) < .5:
                kp.interpolation = interp


FULL = 1 + SOFT
progress(1, FULL)


# ------------------------------------------------------------------ keying helpers
def mkey(f, dx=0.0, dz=0.0, r=None, sx=None, sy=None):
    """Key the marker: a shift in world units (x right, z up), turned into its own frame; r degrees; sx across,
    sy along it."""
    v = ACROSS * 0 + Vector((dx, 0, dz))
    key(arm, "marker", f, x=v.dot(ACROSS), y=v.dot(AXIS), r=r, sx=sx, sy=sy)


def write_follow(f0, f1, curve, lean=.25, tilt=6.0, pull=.28):
    """While the line is drawn (or rewound) the marker follows the drawing point: drawn toward it a little, leaning
    the way it runs, so each pass reads as the marker's own stroke."""
    xs, zs, rs = [], [], []
    cx, cy = 500, 500
    for f in range(f0, f1 + 1):
        t = curve.evaluate(f)
        (x, y), (dx, dy) = path_at(t)
        t2 = curve.evaluate(f + 1)
        sgn = 1 if t2 >= t else -1
        env = smooth(f0 - 1, f0 + 4, f) * (1 - smooth(f1 - 4, f1 + 1, f))     # eases in and out: never a jump
        xs.append(env * ((x - cx) / 100 * pull + dx * sgn * lean * .01 * 30))
        zs.append(env * (-(y - cy) / 100 * pull - dy * sgn * lean * .01 * 30))
        rs.append(env * (-dx * sgn * tilt))
    return xs, zs, rs


def key_marker_series(f0, xs, zs, rs, extra=None):
    keepf = sorted(set(fxkit.sparse(xs, .003)) | set(fxkit.sparse(zs, .003)) | set(fxkit.sparse(rs, .15)))
    for i in keepf:
        dx, dz, r = xs[i], zs[i], rs[i]
        if extra:
            ex, ez, er = extra(f0 + i)
            dx, dz, r = dx + ex, dz + ez, r + er
        mkey(f0 + i, dx, dz, r=r)


# ================================================================== idle: hovering, ready
f0, f1 = CLIPS["idle"]
act = fxkit.begin_action(arm, SID + "_idle")
rest(arm, BONES, f0)
TAP, WIGGLE = 11, (19, 49)
IDLE_KEYS = [   # (frame, along, across, turn, squash along) - it lifts well off the paper, taps its nib hard, scribbles
                # wide strokes across the line, then leans right back to look at its work and settles
    (3, .06, -.02, 2.5, 1.02), (7, .34, -.06, 8.5, 1.07), (TAP, -.13, .02, -3.0, .86), (14, .1, 0, 2.5, 1.04), (17, .02, .1, -2, .98)]
for k, f in enumerate(range(WIGGLE[0] + 2, WIGGLE[1] + 1, 5)):    # the scribble: wide strokes across, working down
    side = 1 if k % 2 == 0 else -1
    IDLE_KEYS.append((f, .05 - .035 * k, .3 * side, -7.5 * side, .95 if k % 2 else 1.03))
IDLE_KEYS += [(52, -.06, .06, 2.0, .96), (58, .22, -.12, 9.5, 1.06), (63, .27, -.15, 11.0, 1.07),     # the lean back
              (68, .05, -.02, 2.0, .97), (72, -.05, .03, -2.4, .985), (76, .02, 0, .8, 1.005), (81, 0, 0, 0, 1)]
for f, a, c, r, sy in IDLE_KEYS:
    v = AXIS * a + ACROSS * c
    mkey(f, v.x, v.z, r=r, sx=1 / math.sqrt(sy), sy=sy)
fxkit.hard(act, "marker", "location", 1, TAP)
fxkit.calm(act, IDLE_CALM)    # owner, 2026-11-03: the idle 30% less dramatic
fxkit.make_cyclic(act)
fxkit.end_action(arm, act, f0)

# ================================================================== land: it lands on its nib
f0, f1 = CLIPS["land"]
act = fxkit.begin_action(arm, SID + "_land")
rest(arm, BONES, f0)
for f, sx, sy in ((103, 1.07, .9), (106, .97, 1.04), (110, 1.01, .99), (115, 1, 1), (f1, 1, 1)):
    key(arm, "root", f, sx=sx, sy=sy)
for i in (0, 1):
    fxkit.hard(act, "root", "scale", i, 103)
for f, a, sx, sy, r in ((103, -.06, 1.05, .9, 0), (106, .09, .97, 1.06, -2.2), (110, -.02, 1.01, .985, 1.4), (114, .015, 1, 1.004, -.6),
                        (119, 0, 1, 1, .2), (f1, 0, 1, 1, 0)):
    v = AXIS * a
    mkey(f, v.x, v.z, r=r, sx=sx, sy=sy)
fxkit.end_action(arm, act, f0)

# ================================================================== hit: rewind the line into the nib, scribble it back on
f0, f1 = CLIPS["hit"]
act = fxkit.begin_action(arm, SID + "_hit")
rest(arm, BONES, f0)
REWIND, WRITE, DONE = (205, 211), (212, 238), 238
progress(f0, FULL); progress(REWIND[0], FULL)
progress(REWIND[1], -SOFT)
progress(WRITE[0], -SOFT)
TURNS = [CUM[i] / LENGTH for i in (4, 7, 12, 17)] + [FULL]          # where each pass ends and the next turns back
for k, t in enumerate(TURNS, 1):                     # five passes, quick on the runs, a beat at each turn
    progress(WRITE[0] + (WRITE[1] - WRITE[0]) * k / 5, t)
progress(f1, FULL)
pc = next(fc for fc in fxkit.fcurves(grp.animation_data.action))
xs, zs, rs = write_follow(REWIND[0], WRITE[1], pc)


def hit_extra(f):
    """Anticipation (it lifts off and leans back), and the flourish after the last pass."""
    lift = AXIS * (.12 * smooth(f0, 204, f) * (1 - smooth(204, 207, f)))
    return lift.x, lift.z, 3 * smooth(f0, 204, f) * (1 - smooth(204, 207, f))


key_marker_series(REWIND[0], xs, zs, rs, extra=hit_extra)
for f in (f0, 202, 204):
    e = hit_extra(f)
    mkey(f, e[0], e[1], r=e[2])
for k in range(1, 5):                                # it presses on the nib at each turn
    ft = round(WRITE[0] + (WRITE[1] - WRITE[0]) * k / 5)
    for f, sx, sy in ((ft - 2, 1, 1), (ft, 1.03, .95), (ft + 2, 1, 1)):
        key(arm, "marker", f, sx=sx, sy=sy)
for f, a, sx, sy, r in ((DONE + 2, -.08, 1.06, .9, -4), (DONE + 5, .14, .95, 1.1, 3), (DONE + 9, -.03, 1.015, .985, -1.2),
                        (DONE + 13, 0, 1, 1, .4), (f1, 0, 1, 1, 0)):
    v = AXIS * a
    mkey(f, v.x, v.z, r=r, sx=sx, sy=sy)
fxkit.end_action(arm, act, f0)

# ================================================================== multi: shaken, light runs along the line; it pumps and lets go
f0, f1 = CLIPS["multi"]
act = fxkit.begin_action(arm, SID + "_multi")
rest(arm, BONES, f0)
SHAKE, MREWIND, MWRITE, LET_GO = (302, 305), (306, 309), (310, 322), 327
for i, f in enumerate(range(SHAKE[0], SHAKE[1] + 1)):              # charged: it rattles
    a = (.06 + .03 * i) * (1 if i % 2 else -1)
    v = AXIS * a
    mkey(f, v.x, v.z, r=(1.5 + .6 * i) * (-1 if i % 2 else 1), sx=1, sy=1)
progress(f0, FULL); progress(MREWIND[0], FULL); progress(MREWIND[1], -SOFT); progress(MWRITE[0], -SOFT)
for k, t in enumerate(TURNS, 1):                    # and writes the line back on, fast, in its five passes
    progress(MWRITE[0] + (MWRITE[1] - MWRITE[0]) * k / 5, t)
progress(f1, FULL)
mxs, mzs, mrs = write_follow(MREWIND[0], MWRITE[1], pc)
key_marker_series(MREWIND[0], mxs, mzs, mrs)
for f, a, sx, sy, r in ((LET_GO - 3, .2, .96, 1.07, 2), (LET_GO, -.16, 1.08, .86, -1), (LET_GO + 3, .06, .97, 1.05, -3),
                        (LET_GO + 7, -.02, 1.01, .99, 1.5), (LET_GO + 11, 0, 1, 1, -.4), (LET_GO + 16, 0, 1, 1, 0), (f1, 0, 1, 1, 0)):
    v = AXIS * a
    mkey(f, v.x, v.z, r=r, sx=sx, sy=sy)
fxkit.hard(act, "marker", "location", 1, LET_GO)
for f, sx, sy in ((LET_GO, 1, 1), (LET_GO + 1, 1.04, .94), (LET_GO + 5, .99, 1.02), (LET_GO + 9, 1, 1), (f1, 1, 1)):
    key(arm, "root", f, sx=sx, sy=sy)
fxkit.end_action(arm, act, f0)


# ================================================================== effects
def where(bone, pts, f):
    pb = arm.pose.bones[bone]
    sc.frame_set(f)
    M = arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted()
    return [((M @ vec(*p)).x, (M @ vec(*p)).z) for p in pts]


sc.frame_set(1)
fx = gp_object(FX, SID + "_fx", depth=-.8)
back = gp_object(FXB, SID + "_fxb_glow", depth=.35)       # (never a part's name: gp_object replaces that object)
paint = gp_object(ART, SID + "_fx_paint", depth=-1.0)            # drops and spatter: on the art, in front of every piece
m = dict(white=gp_mat(fx, "fx_white_line", WHITE), white_f=gp_mat(fx, "fx_white_fill", WHITE, fill=WHITE),
         orange=gp_mat(fx, "fx_orange_line", ORANGE), orange_f=gp_mat(fx, "fx_orange_fill", ORANGE, fill=ORANGE),
         gold_f=gp_mat(fx, "fx_gold_fill", GOLD, fill=GOLD))
mb = dict(orange=gp_mat(back, "glow_orange", ORANGE), white=gp_mat(back, "glow_white", WHITE))
mp = dict(drop=gp_mat(paint, "paint_drop", PAINT_INK, fill=ORANGE), fleck=gp_mat(paint, "paint_fleck", ORANGE, fill=ORANGE))
world, behind, wet = Board(), Board(), Board()
LINE = [px(x, y) for x, y in PATH]
LINE_PTS = fxkit.resample(LINE, 400, closed=False)


_mk = spec_parts = {p["name"]: p for p in spec["parts"]}["marker"]
_mk_img = bpy.data.images.load(os.path.join(fxkit.ROOT, "art", "blender", "parts", SID, "marker.png"), check_existing=True)
_mw, _mh = _mk_img.size
_mpx = np.empty(_mw * _mh * 4, np.float32); _mk_img.pixels.foreach_get(_mpx)
_MA = _mpx[3::4].reshape(_mh, _mw)[::-1] > .3          # rows top-down, icon px inside the marker's box
_MA = np.pad(_MA, 6)
for _ in range(6):                                      # grown 6 px: the effect clears its edge
    _MA = _MA | np.roll(_MA, 1, 0) | np.roll(_MA, -1, 0) | np.roll(_MA, 1, 1) | np.roll(_MA, -1, 1)
_MINV = {}


def under_marker(f, x, z):
    """Is world point (x, z) behind the marker as it is at frame f? (effects along the line hide there)"""
    if f not in _MINV:
        pb = arm.pose.bones["marker"]
        sc.frame_set(f)
        _MINV[f] = (arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted()).inverted()
    q = _MINV[f] @ Vector((x, 0, z))
    ix, iy = int(round(q.x * 100 + 500)) - _mk["box"][0] + 6, int(round(500 - q.z * 100)) - _mk["box"][1] + 6
    return 0 <= iy < _MA.shape[0] and 0 <= ix < _MA.shape[1] and bool(_MA[iy, ix])


def visible_runs(f, pts):
    """A polyline cut where it passes behind the marker: the runs left in front of nothing."""
    out, cur = [], []
    for p in pts:
        if under_marker(f, *p):
            if len(cur) >= 3: out.append(cur)
            cur = []
        else:
            cur.append(p)
    if len(cur) >= 3: out.append(cur)
    return out


def run_along(t0, length):
    """The points of the centre line from t0 to t0 + length (shares of the line)."""
    n = len(LINE_PTS)
    a, b = max(0, int(t0 * n)), max(0, min(n - 1, int((t0 + length) * n)))      # (clamped: never a negative index)
    return LINE_PTS[a:b + 1]


def specks(board, f, x, z, n, r, mats, seed, size=(.012, .03), bias=(0, 0)):
    rnd = random.Random(seed)
    for i in range(n):
        a = rnd.uniform(0, 2 * math.pi); d = r * math.sqrt(rnd.random())
        sx, sz = x + math.cos(a) * d + bias[0], z + math.sin(a) * d + bias[1]
        rr = rnd.uniform(*size)
        board.add(f, lambda dr, sx=sx, sz=sz, rr=rr, i=i: stroke(dr, ring(sx, sz, rr, n=8), .003, mat=mats[i % len(mats)],
                                                               cyclic=True, fill=True, line=False))


def splash(board, f0, x, z, n, speed, mats, seed, life=12, grav=8.0, size=(.03, .07), spread=(0, 360)):
    """Paint flung out: drops that fly, fall and shrink away."""
    rnd = random.Random(seed)
    for i in range(n):
        a = math.radians(rnd.uniform(*spread)); sp = rnd.uniform(*speed); r0 = rnd.uniform(*size)
        for k in range(life):
            t = k / FPS; u = k / (life - 1)
            dx, dz = math.cos(a) * sp * t, math.sin(a) * sp * t - grav * t * t
            r = r0 * (1 - u ** 1.8)
            if r < .006:
                continue
            board.add(f0 + k, lambda dr, x=x + dx, z=z + dz, r=r, i=i: stroke(dr, ring(x, z, r, n=10), .005,
                                                                         mat=mats[i % len(mats)], cyclic=True, fill=True))


def rings_out(board, f0, cx, cz, r0, r1, mats, life=11, lag=3, width=.12):
    """Rings rolling outward at full strength, thinning to nothing (never fading to a dim, dirty line)."""
    for j, mat in enumerate(mats):
        for k in range(life):
            t = k / (life - 1)
            r = r0 + (r1 - r0) * (1 - (1 - t) ** 1.6)
            w = width * (1 - t) ** 1.3
            if w > .004:
                board.add(f0 + lag * j + k, lambda dr, r=r, w=w, mat=mat, f=f0 + k: stroke(
                    dr, ring(cx, cz, r, n=96, wobble=.02, seed=f), w, mat=mat, cyclic=True))


# ---- idle: a wet sheen glides along the fresh paint; a drop gathers on the nib and falls
for f in range(1, 81):
    t = (f - 1) / 80
    for pts in visible_runs(f, run_along(t * 1.1 - .05, .045)):
        nn = len(pts)
        world.add(f, lambda dr, pts=pts, nn=nn: stroke(dr, pts, 0, radii=fxkit.taper(nn, .03, ends=.45),
                                                       opacities=[.75] * nn, mat=m["white"]))
nx, nz = where("marker", [NIB], TAP)[0]
splash(wet, TAP, nx, nz, 7, (1.6, 2.8), (mp["drop"], mp["fleck"]), seed=2, spread=(30, 160), size=(.02, .045), life=10, grav=6)
for k, f in enumerate(range(WIGGLE[0] + 1, WIGGLE[1] + 1, 2)):    # paint flecks off the nib as it scribbles
    nx, nz = where("marker", [NIB], f)[0]
    specks(wet, f, nx, nz + .1, 4, .35, (mp["fleck"],), seed=900 + f, size=(.012, .028))
for k, f in enumerate(range(50, 78)):
    nx, nz = where("marker", [NIB], f)[0]
    if f < 66:                                              # it gathers on the nib...
        u = (f - 50) / 16
        r = .015 + .055 * u ** .8
        wet.add(f, lambda dr, x=nx, z=nz - r * .6, r=r: stroke(dr, [(x + math.cos(a) * r, z + math.sin(a) * r * (1.15 if math.sin(a) < 0 else .9))
                                                                     for a in (2 * math.pi * i / 16 for i in range(16))],
                                                                .01, mat=mp["drop"], cyclic=True, fill=True))
    else:                                                   # ...falls, stretching, and is gone
        t = (f - 66) / FPS
        z = nz - .06 - 7 * t * t
        r = .07 * (1 - smooth(72, 77, f))
        if r > .01:
            wet.add(f, lambda dr, x=nx, z=z, r=r, t=t: stroke(dr, [(x + math.cos(a) * r * .85, z + math.sin(a) * r * (1.3 + 2 * t))
                                                                     for a in (2 * math.pi * i / 16 for i in range(16))],
                                                              .01, mat=mp["drop"], cyclic=True, fill=True))

# ---- land: paint spatters from the nib
nx, nz = px(*NIB)
splash(wet, 103, nx, nz, 9, (2.0, 3.6), (mp["drop"], mp["fleck"]), seed=3, spread=(20, 170), size=(.025, .055))
for k in range(5):
    t = k / 4
    for j, a in enumerate((25, 60, 100, 140)):
        ar = math.radians(a)
        world.add(103 + k, lambda dr, ar=ar, t=t: stroke(dr, [(nx + math.cos(ar) * (.3 + .5 * t), nz + math.sin(ar) * (.3 + .5 * t)),
                                                             (nx + math.cos(ar) * (.55 + .5 * t), nz + math.sin(ar) * (.55 + .5 * t))],
                                                        .03 * (1 - t) + .006, mat=m["white"]))

# ---- hit: speed streaks as it rewinds; at the drawing point a spray of paint; sparkles down the line after
def head_fx(rew0, wr0, wr1, glow=False):
  for f in range(rew0, wr1 + 1):
      t = pc.evaluate(f)
      t_next = pc.evaluate(f + 1)
      (x, y), (dx, dy) = path_at(t)
      fx_, fz_ = px(x, y)
      if f < wr0:                                        # rewinding: white zips racing back along the line
          for pts in visible_runs(f, run_along(max(0, t - .02), .08)):
              nn = len(pts)
              world.add(f, lambda dr, pts=pts, nn=nn: stroke(dr, pts, 0, radii=fxkit.taper(nn, .05, ends=.4), mat=m["white"]))
          continue
      if t <= 0.002 or t >= .999:
          continue
      if under_marker(f, fx_, fz_):                           # the drawing point is behind the marker: no spray shows
          continue
      specks(world, f, fx_, fz_, 14, .42, (m["orange_f"], m["orange_f"], m["white_f"]), seed=f, bias=(dx * .002, -dy * .002))
      for trail in visible_runs(f, run_along(max(0, t - .03), .03)):
          nn = len(trail)
          world.add(f, lambda dr, pts=trail, nn=nn: stroke(dr, pts, 0, radii=fxkit.taper(nn, .06, ends=.5), opacities=[.9] * nn,
                                                           mat=m["orange"]))
      specks(wet, f, fx_, fz_, 6, .55, (mp["fleck"],), seed=f + 500, size=(.01, .022))
      if glow:                                            # charged: the drawing point burns white-gold
          fxkit.sparkle(world, f, 3, fx_, fz_, .34, m["gold_f"] if f % 2 else m["white_f"], rot0=f * .7)


head_fx(REWIND[0], WRITE[0], WRITE[1])
rnd = random.Random(7)
for i in range(8):
    t = (i + .5) / 8
    (x, y), _ = path_at(t)
    fxkit.sparkle(world, DONE + 1 + i, 6, *px(x, y), rnd.uniform(.26, .4), m["white_f"] if i % 3 else m["gold_f"], rot0=rnd.random())
mx, mz = px(*PIVOT)                                         # the pop: rings of light behind the marker
rings_out(behind, DONE + 2, mx, mz, 1.4, 5.6, (mb["orange"], mb["white"]), life=10, lag=3, width=.1)

# ---- multi: rattle marks as it is charged, the line rewound and written back on burning gold, a splash as it pumps
for k, f in enumerate(range(SHAKE[0], SHAKE[1] + 1)):
    cx, cz = where("marker", [(700, 330)], f)[0]
    side = 1 if k % 2 else -1
    for j in range(3):
        ox = (ACROSS.x * side) * (1.15 + .18 * j)
        oz = (ACROSS.z * side) * (1.15 + .18 * j)
        pts = [(cx + ox + AXIS.x * s * .35, cz + oz + AXIS.z * s * .35) for s in (-1, 0, 1)]
        pts[1] = (pts[1][0] + ACROSS.x * side * .08, pts[1][1] + ACROSS.z * side * .08)
        world.add(f, lambda dr, pts=pts: stroke(dr, pts, .024, mat=m["white"]), hold=2)
head_fx(MREWIND[0], MWRITE[0], MWRITE[1], glow=True)
nx, nz = where("marker", [NIB], LET_GO)[0]
splash(wet, LET_GO, nx, nz, 16, (2.6, 4.6), (mp["drop"], mp["fleck"]), seed=11, spread=(10, 170), size=(.03, .08), life=12, grav=5)
specks(world, LET_GO, nx, nz, 18, .6, (m["orange_f"], m["white_f"]), seed=19, size=(.015, .035))
rings_out(behind, LET_GO, mx, mz, 1.6, 5.6, (mb["orange"], mb["white"], mb["orange"]), life=11, lag=3, width=.13)   # round the whole marker
fxkit.streaks(world, LET_GO, 8, nx + .2, nz + .2, .8, 1.9, (m["white"], m["orange"]), n=12, rot=.3)      # (inside the frame)
rnd = random.Random(31)
for i in range(6):
    fxkit.sparkle(world, LET_GO + 3 + rnd.randint(0, 8), rnd.randint(7, 8), rnd.uniform(-4.6, 4.6), rnd.uniform(-4.2, 4.8),
                  rnd.uniform(.2, .36), m["white_f"] if i % 2 else m["gold_f"], rot0=rnd.uniform(0, 1))

world.draw(gp_layer(fx, "fx"))
behind.draw(gp_layer(back, "burst"))
wet.draw(gp_layer(paint, "paint"))

sc.frame_start, sc.frame_end = 1, max(b for a, b in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], "| saved", fxkit.save(SID))
