# L7 - the black hoodie - animated in Blender: four Actions on its rig (idle, land, hit, multi) laid one after another
# on the rig's NLA track, and its effects drawn frame by frame in Grease Pencil.
#   the rig     the hoodie is ONE image, its tag printed on it (tools/blender/cuts/L7.py), on a fine mesh skinned to
#               its bones: the root at the hem (it squashes and hops), the body (it sways from the hem), the chest (it
#               breathes: weighted over the whole upper body, so the eyelets ride it and the cords stay hung on them),
#               a shoulder bone each side (it shrugs; the arms below follow less and less, the hands stay in the
#               pocket), the hood's crown (it bobs), each sleeve's outer bend, the belly band and the waistband
#               (keyed only in the idle; children of the body, so the other clips move them as before). The two
#               drawstrings are the pieces on top: each a chain of four bones from its eyelet down, the last one its
#               metal aglet, which stays straight while the cord bends
#   the cords   never keyed by hand: worked out in Blender from how the chest really moves (fxkit.secondary), each on
#               its own springs - the left one longer and slower, the right one quicker - so they swing apart and
#               bend like H1's ropes; a breeze, a jolt or a charge adds a force
#   idle        worn by someone who isn't there, grooving: a rock-step lean right / left / right / left at 90 bpm with a
#               dip onto each lean; the hood flops over late, the shoulders roll, the sleeves swing out behind the lean
#               and bow on the dips, the belly band and waistband trail further behind (the cloth ripples down it),
#               the chest breathes; the cords hang looser and swing wide; on the second beat the tag lights up like
#               a neon sign, a lime band wiping across the letters white-hot at its front, two glints after it
#   land        dropped on the reel: it squashes on its hem, the shoulders dip and bounce, the hood nods, the cords
#               keep falling and bounce; puffs under the hem
#   hit         hype: it crouches, jumps with a shrug, the cords trailing then flying up; lands, then grooves - a
#               rocking bounce to a beat, a shoulder up on each rock, the cords whipping about; the tag gets a fresh
#               coat - spray-paint mist bursting off it - bounce marks beside the shoulders, sparkles on the aglets
#   multi       static: it draws a deep breath in three pulls, the charge building - the cords lift and splay apart
#               (they repel), the hood rises, sparks crackle off the aglets; then it discharges: a zap between the
#               aglets, bolts flying out from the chest, the cords drop and swing, it lets the breath go
#   effects     spray mist, bounce marks, static crackles and bolts, sparkles, puffs - its own effects (a low symbol:
#               no tier glow)
# Runs INSIDE Blender, after build_symbol_scene.py (tools/blender/run.py runs both in a background Blender).
import bpy, importlib, math, os, random, sys
from mathutils import Matrix, Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
import fxkit
importlib.reload(fxkit)
from fxkit import (key, rest, px, smooth, gp_object, gp_mat, gp_layer, ride, stroke, star, Board, WHITE, LIME, GOLD)

SID = "L7"
sc, arm, spec = fxkit.setup(SID)
FPS = sc.render.fps
W, H = spec["size"]
PARTS = {p["name"]: p for p in spec["parts"]}


# ================================================================== the skin (this symbol's rig helpers)
def wpt(x, y):
    """icon px -> rig space (the icon centred on the origin, z up)"""
    return Vector(((x - W / 2) / 100.0, 0.0, (H / 2 - y) / 100.0))


def sstep(e0, e1, v):
    t = max(0.0, min(1.0, (v - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def add_bones(defs):
    """(name, head px or None (keep it where it is), tail px or None, parent) - a bone with no tail points up (x/y
    keys move it right/up)."""
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    for name, head, tail, parent in defs:
        b = eb.get(name) or eb.new(name)
        if head is not None:
            b.head = wpt(*head)
            if tail is None:
                b.tail = b.head + Vector((0, 0, .6))
                b.roll = 0
            else:
                b.tail = wpt(*tail)
                b.align_roll(Vector((0, -1, 0)))
        b.parent = eb[parent] if parent else None
        b.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"


def skin(name, weights, cell=6):
    """The part's plane (or grid) becomes a fine grid on the icon's own lattice (cells at multiples of `cell` px),
    skinned to the rig: weights(x, y) -> {bone: weight} (icon px; they sum to 1)."""
    p = PARTS[name]
    ob = bpy.data.objects[SID + "_" + name]
    x0, y0, x1, y1 = p["box"]
    gx0, gy0 = math.floor(x0 / cell) * cell, math.floor(y0 / cell) * cell
    nx, ny = math.ceil((x1 - gx0) / cell), math.ceil((y1 - gy0) / cell)
    verts, uvs, pts = [], [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x, y = gx0 + i * cell, gy0 + j * cell
            v = wpt(x, y)
            verts.append((v.x, 0.0, v.z))
            uvs.append(((x - x0) / (x1 - x0), 1 - (y - y0) / (y1 - y0)))
            pts.append((x, y))
    faces = []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a + nx + 1, a + nx + 2, a + 1, a))
    me = bpy.data.meshes.new(SID + "_" + name + "_skin")
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new()
    for poly in me.polygons:
        for li in poly.loop_indices:
            uv.data[li].uv = uvs[me.loops[li].vertex_index]
    me.materials.append(ob.data.materials[0])
    old = ob.data
    ob.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    depth = -0.1 * (p["draw"] + 1)
    ob.parent = arm
    ob.parent_type = "OBJECT"
    ob.matrix_parent_inverse = Matrix.Identity(4)
    ob.matrix_world = Matrix.Translation((0, depth, 0))
    ob.vertex_groups.clear()
    groups = {}
    for vi, (x, y) in enumerate(pts):
        for bone, wt in weights(x, y).items():
            if wt > 1e-4:
                if bone not in groups:
                    groups[bone] = ob.vertex_groups.new(name=bone)
                groups[bone].add([vi], wt, "REPLACE")
    for m in list(ob.modifiers):
        ob.modifiers.remove(m)
    mod = ob.modifiers.new("rig", "ARMATURE")
    mod.object = arm
    mod.use_vertex_groups = True
    return ob


def chain_w(ch, x, y, blends):
    """weights of a chain's bones for a point (icon px): where it falls along the chain, blended across each joint
    over its own width in px (blends[i] for the joint after bone i) - wide where a cord bends, narrow at the aglet"""
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
        lo = 1.0 if i == 0 else sstep(joints[i] - blends[i - 1] / 2, joints[i] + blends[i - 1] / 2, s_at)
        hi = 1.0 if i == n - 1 else 1 - sstep(joints[i + 1] - blends[i] / 2, joints[i + 1] + blends[i] / 2, s_at)
        out.append(lo * hi)
    tot = sum(out) or 1.0
    return [v / tot for v in out]


def keys(bone, f0, vals, channel, tol, loop=False):
    fxkit.key_series(arm, bone, f0, vals, channel=channel, tol=tol, loop=loop)


# ================================================================== the rig
HEM = (510, 945)                          # the recipe's pivot: the hoodie sways from its hem
CHEST = (500, 360)
SH_L, SH_R = (240, 270), (760, 270)
HOOD = (495, 120)
CORDS = {n: [tuple(q) for q in PARTS[n]["chain"]] for n in ("cord_l", "cord_r")}   # eyelet first, the aglet last
ELB_L, ELB_R = (150, 545), (885, 545)    # the outer bend of each sleeve (the hands stay in the pocket)
MID, HEMB = (500, 625), (510, 885)       # the belly band (pocket, cuffs) and the ribbed waistband
add_bones([("root", (510, 950), None, None),
           ("body", None, None, "root"),
           ("chest", CHEST, None, "body"),
           ("sh_l", SH_L, None, "body"),
           ("sh_r", SH_R, None, "body"),
           ("hood", HOOD, None, "chest"),
           # the cloth below the chest and the sleeves' bends: children of the body, so in land / hit / multi
           # (which never key them) they ride it exactly as the body-weighted cloth did before
           ("elb_l", ELB_L, None, "body"),
           ("elb_r", ELB_R, None, "body"),
           ("mid", MID, None, "body"),
           ("hem", HEMB, None, "body"),
           ("cord_l.0", None, None, "chest"),
           ("cord_r.0", None, None, "chest")])


def hoodie_weights(x, y):
    """the hood's crown above its opening; each shoulder round its point (only out past the chest, so the eyelets
    stay on the chest); each sleeve's outer bend (not the cuffs in the pocket); the chest over the whole upper
    body; below it the belly band, and the waistband at the bottom"""
    hw = sstep(150, 92, y) * sstep(250, 300, x) * (1 - sstep(705, 755, x))
    r1 = 1 - hw
    wsl = math.exp(-((x - SH_L[0]) ** 2 + (y - SH_L[1]) ** 2) / (2 * 95 ** 2)) * (1 - sstep(300, 360, x))
    wsr = math.exp(-((x - SH_R[0]) ** 2 + (y - SH_R[1]) ** 2) / (2 * 95 ** 2)) * sstep(640, 700, x)
    wel = math.exp(-(x - ELB_L[0]) ** 2 / (2 * 85 ** 2) - (y - ELB_L[1]) ** 2 / (2 * 125 ** 2)) * (1 - sstep(245, 315, x))
    wer = math.exp(-(x - ELB_R[0]) ** 2 / (2 * 85 ** 2) - (y - ELB_R[1]) ** 2 / (2 * 125 ** 2)) * sstep(705, 775, x)
    tot = wsl + wsr + wel + wer
    if tot > 1:                          # where a shoulder and a bend overlap they share it
        wsl, wsr, wel, wer = (v / tot for v in (wsl, wsr, wel, wer))
        tot = 1.0
    r2 = r1 * (1 - tot)
    r = math.hypot((x - CHEST[0]) / 300, (y - CHEST[1]) / 300)
    wc = 1 - sstep(.75, 1.15, r)
    low = r2 * (1 - wc)
    wh = sstep(745, 865, y)
    return {"hood": hw, "sh_l": r1 * wsl, "sh_r": r1 * wsr, "elb_l": r1 * wel, "elb_r": r1 * wer, "chest": r2 * wc,
            "mid": low * (1 - wh), "hem": low * wh}


skin("body", hoodie_weights)
for n, ch in CORDS.items():                           # the cords bend along their length; the aglet stays straight
    skin(n, lambda x, y, n=n, ch=ch: {f"{n}.{i}": w for i, w in enumerate(chain_w(ch, x, y, (44, 40, 12)))}, cell=4)
CORD_BONES = [f"{n}.{i}" for n in CORDS for i in range(4)]
CLOTH = ["elb_l", "elb_r", "mid", "hem"]
BONES = ["root", "body", "chest", "sh_l", "sh_r", "hood"] + CLOTH + CORD_BONES

ART, FXB, FX = fxkit.layers(sc, SID)
fxkit.glow_compositor(sc, SID, back=dict(strength=.7, size=.5, gain=1.3), front=dict(strength=.8, size=.42, gain=1.4))
if arm.animation_data:
    arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)

CLIPS = {"idle": (1, 80), "land": (101, 124), "hit": (201, 254), "multi": (301, 348)}
arm["clips"] = {k: list(v) for k, v in CLIPS.items()}
arm["slow"] = {"idle": 2.5}
IDLE_CALM = .7                   # the idle's moves at 70% of how far they were keyed (fxkit.calm)     # owner, 2026-11-03: the idle plays 2.5x slower than keyed (Time Remapping, fxkit.render_clip)
# the cords: the left one a touch longer and slower, the right one quicker - so they never swing as one
# (each point's spring pulls it to where it hangs at rest, softer toward the tip so it trails the cord above it;
# the aglet is metal, so its bend against the braid is kept to half of what the springs give - see follow())
HANG = {"cord_l": dict(chain=CORDS["cord_l"], freq=[2.9, 2.5, 2.2, 2.0], zeta=.17, gain=.75, limit=15),
        "cord_r": dict(chain=CORDS["cord_r"], freq=[3.4, 2.9, 2.5, 2.3], zeta=.2, gain=.7, limit=14)}


def follow(f0, f1, loop=False, forces=None, gain=1.0):
    """the cords worked out from how this clip moves the chest, keyed onto their bones"""
    res = fxkit.secondary(sc, arm, "chest", f0, f1, HANG, loop=loop, forces=forces, gain=gain)
    print(f"  cords {f0}-{f1}:", ", ".join(f"{b} {min(v):+.1f}..{max(v):+.1f}" for b, v in res.items()))
    for bone, vals in res.items():
        if bone.endswith(".3"):                        # the aglet: stiff where it grips the braid
            vals = [v * .5 for v in vals]
        keys(bone, f0, vals, "r", .2, loop)


# ================================================================== idle: worn by someone who isn't there, grooving
# A laid-back rock-step at 90 bpm (a beat every 20 frames, four beats a loop): the invisible wearer leans from the
# hips right, left, right, left - the first pair a touch bigger than the second, so the two halves of the loop
# differ - and dips onto each lean (a squash on the beat). Everything loose follows a few frames behind the lean
# that drives it (overlap and follow-through, worked out from the lean itself, so it is always physically in
# step): the hood flops a beat late, the shoulders roll, the sleeves' bends swing out and bow on each dip, the belly
# band and the waistband trail further and further behind (the cloth ripples down the hoodie), the chest takes a
# slow breath over the loop. The cords hang off the chest on their springs and swing with it all.
# Every channel is a sum of the loop's own harmonics (so it joins itself exactly) and starts on the rest pose: what
# a lagging channel still holds at frame 0 is taken out smoothly over the lap (a raised cosine, whole at the ends).
f0, f1 = CLIPS["idle"]
N = f1 - f0 + 1
T = N / FPS
act = fxkit.begin_action(arm, SID + "_idle")
rest(arm, BONES, f0)
LEAN = 5.6                                             # degrees, at the peak of the bigger leans


def beat(k):
    """the groove's clock (radians, 4 pi a loop): it eases through the loop's start - the rest pose, upright - so
    the loop's seam is one of its gentlest steps, and makes the time up on the far side"""
    ph = 2 * math.pi * k / N
    return 2 * ph - .9 * math.sin(ph)


def sway(k):
    """the lean, -1..1 (right = +): two rocks a loop, the first pair a touch wider"""
    return math.sin(beat(k)) * (1 + .16 * math.cos(2 * math.pi * k / N))


def dip(k):
    """the bounce, 0..1: down onto each lean (the beat), up through the middle"""
    return abs(math.sin(2 * beat(k))) ** 2.5


def lean_x(k, h):
    """how far right (units) the lean carries a point h units above the hem"""
    return h * math.sin(math.radians(LEAN * sway(k)))


def trail(k, h, d):
    """follow-through: where the lean was d frames ago, against where it is now (units, at height h)"""
    return lean_x(k - d, h) - lean_x(k, h)


def unpin(vals, base=0.0):
    """a periodic series made to start exactly at `base`: the offset at frame 0 eased out over the lap"""
    v0 = vals[0] - base
    return [v - v0 * (.5 + .5 * math.cos(2 * math.pi * k / N)) for k, v in enumerate(vals)]


ch = {}                                                # (bone, channel) -> per frame values over the loop
for k in range(N):
    ph = 2 * math.pi * k / N
    s, b = sway(k), dip(k)
    breath = (.5 - .5 * math.cos(ph)) ** 1.3
    ch[("root", "sx")] = ch.get(("root", "sx"), []) + [1 + .018 * b]
    ch[("root", "sy")] = ch.get(("root", "sy"), []) + [1 - .036 * b]
    ch[("body", "r")] = ch.get(("body", "r"), []) + [-LEAN * s]
    ch[("body", "x")] = ch.get(("body", "x"), []) + [-.07 * sway(k - 3)]          # the hips shift against the lean
    ch[("chest", "r")] = ch.get(("chest", "r"), []) + [-.6 * LEAN * (sway(k - 4) - s)]
    ch[("chest", "sx")] = ch.get(("chest", "sx"), []) + [1 + .012 * breath]
    ch[("chest", "sy")] = ch.get(("chest", "sy"), []) + [1 + .024 * breath]
    ch[("chest", "y")] = ch.get(("chest", "y"), []) + [.02 * breath]
    # the hood: flops over late, and nods down after each beat
    ch[("hood", "r")] = ch.get(("hood", "r"), []) + [-1.15 * LEAN * (sway(k - 8) - sway(k - 4))]
    ch[("hood", "y")] = ch.get(("hood", "y"), []) + [-.03 * dip(k - 3) + .012 * breath]
    for bone, side in (("sh_l", 1), ("sh_r", -1)):  # the shoulder on the far side of the lean rises, then rolls back
        ch[(bone, "y")] = ch.get((bone, "y"), []) + [.04 * side * sway(k - 3) - .02 * dip(k - 2) + .016 * breath]
        ch[(bone, "r")] = ch.get((bone, "r"), []) + [-.5 * LEAN * (sway(k - 5) - s) - .7 * side * dip(k - 2)]
    for bone, side in (("elb_l", -1), ("elb_r", 1)):  # the sleeves swing behind the lean, and bow out on each dip
        ch[(bone, "x")] = ch.get((bone, "x"), []) + [.55 * trail(k, 4.0, 6) + side * .075 * dip(k - 2)]
        ch[(bone, "y")] = ch.get((bone, "y"), []) + [-.03 * dip(k - 3)]
        ch[(bone, "r")] = ch.get((bone, "r"), []) + [-.6 * LEAN * (sway(k - 7) - s)]
    # the cloth below trails down the hoodie, the waistband last and most, flaring on the dip
    ch[("mid", "x")] = ch.get(("mid", "x"), []) + [.5 * trail(k, 4.5, 5)]
    ch[("mid", "r")] = ch.get(("mid", "r"), []) + [-.5 * LEAN * (sway(k - 5) - s)]
    ch[("hem", "x")] = ch.get(("hem", "x"), []) + [.75 * trail(k, 5.0, 9) - .03 * sway(k - 6)]
    ch[("hem", "r")] = ch.get(("hem", "r"), []) + [-.7 * LEAN * (sway(k - 9) - s)]
    ch[("hem", "sx")] = ch.get(("hem", "sx"), []) + [1 + .022 * dip(k - 4)]
    ch[("hem", "sy")] = ch.get(("hem", "sy"), []) + [1 - .03 * dip(k - 4)]
for (bone, c), vals in ch.items():
    ch[(bone, c)] = unpin(vals, 1.0 if c in ("sx", "sy") else 0.0)
for bone in sorted({b for b, _ in ch}):                # keyed together per bone, every other frame, round the loop
    for k in range(0, N + 1, 2):
        kw = {c: ch[(bone, c)][k % N] for b, c in ch if b == bone}
        for a, z in (("x", "y"), ("y", "x"), ("sx", "sy"), ("sy", "sx")):
            if a in kw and z not in kw:
                kw[z] = 1.0 if z[0] == "s" else 0.0
        key(arm, bone, f0 + k, **kw)
print("  idle peaks:", ", ".join(f"{b}.{c} {min(v):+.3f}..{max(v):+.3f}" for (b, c), v in ch.items()))


def breeze(name, i, t):
    s = 1 if name == "cord_l" else -1
    ph = 0 if name == "cord_l" else 2.1
    a = 14 * math.sin(2 * math.pi * t / T + ph) + 8 * math.sin(2 * math.pi * t / (T / 3) + 1.3 * ph)
    return Vector((a * (i / 4) ** .9 * s, 0, 0))


# in the idle the cords hang looser than in the jolts of the other clips (softer springs, less damping): they swing
# wide and late behind the lean, the left one slower than the right
LOOSE = {"cord_l": dict(HANG["cord_l"], freq=[1.5, 1.35, 1.2, 1.1], zeta=.16, gain=1.0, limit=16),
         "cord_r": dict(HANG["cord_r"], freq=[1.8, 1.6, 1.45, 1.35], zeta=.18, gain=1.0, limit=15)}
res = fxkit.secondary(sc, arm, "chest", f0, f1, LOOSE, loop=True, forces=breeze, gain=1.0, rest_start=False)
for bone, vals in res.items():                         # kept in step with the lean that drives them, started at rest
    vals = unpin(vals)
    if bone.endswith(".3"):
        vals = [v * .5 for v in vals]
    print(f"  idle {bone} {min(vals):+.1f}..{max(vals):+.1f}")
    keys(bone, f0, vals, "r", .15, True)
fxkit.calm(act, IDLE_CALM)    # owner, 2026-11-03: the idle 30% less dramatic
fxkit.make_cyclic(act)
fxkit.end_action(arm, act, f0)

# ================================================================== land: squashes on its hem, the cords keep falling
f0, f1 = CLIPS["land"]
act = fxkit.begin_action(arm, SID + "_land")
rest(arm, BONES, f0)
for f, sx, sy in ((f0 + 2, 1.07, .91), (f0 + 6, .97, 1.04), (f0 + 10, 1.012, .99), (f0 + 14, .998, 1.002), (f0 + 18, 1, 1), (f1, 1, 1)):
    key(arm, "root", f, sx=sx, sy=sy)
fxkit.hard(act, "root", "scale", 1, f0 + 2)
for bone, s in (("sh_l", 1), ("sh_r", -1)):
    for f, y, r in ((f0 + 3, -.035, 1.5 * s), (f0 + 7, .025, -1 * s), (f0 + 11, -.008, .3 * s), (f0 + 16, 0, 0), (f1, 0, 0)):
        key(arm, bone, f, y=y, r=r)
for f, y, r in ((f0 + 4, -.03, -2), (f0 + 8, .02, 1.5), (f0 + 12, -.006, -.4), (f0 + 17, 0, 0), (f1, 0, 0)):
    key(arm, "hood", f, y=y, r=r)


def drop(name, i, t):
    f = f0 + t * FPS
    fall = smooth(f0, f0 + 2, f) * (1 - smooth(f0 + 3, f0 + 6, f))
    s = -1 if name == "cord_l" else 1                  # the jolt slackens them: they buckle out apart, then swing back
    return Vector((s * 150 * fall * (i / 4) ** .7, 0, -120 * fall * (i / 4)))


follow(f0, f1, forces=drop, gain=.8)
rest(arm, ["root", "body", "chest", "sh_l", "sh_r", "hood"], f1)
fxkit.end_action(arm, act, f0)

# ================================================================== hit: hype - a jump with a shrug, then a groove
f0, f1 = CLIPS["hit"]
act = fxkit.begin_action(arm, SID + "_hit")
rest(arm, BONES, f0)
UP, LAND = f0 + 11, f0 + 18
BEATS = (f0 + 22, f0 + 27, f0 + 32, f0 + 37)
for f, sx, sy, y in ((f0 + 4, 1.08, .9, 0), (f0 + 8, .93, 1.08, .5), (UP, .98, 1.02, .85), (f0 + 14, 1, 1, .7), (LAND, 1.1, .88, 0),
                     (f0 + 20, .97, 1.03, .02), (BEATS[0], 1.04, .95, 0), (BEATS[0] + 2, .985, 1.02, .07), (BEATS[1], 1.04, .95, 0),
                     (BEATS[1] + 2, .985, 1.02, .06), (BEATS[2], 1.035, .96, 0), (BEATS[2] + 2, .99, 1.015, .045), (BEATS[3], 1.025, .975, 0),
                     (BEATS[3] + 3, 1, 1, .015), (f0 + 44, 1, 1, 0), (f1, 1, 1, 0)):
    key(arm, "root", f, sx=sx, sy=sy, y=y)
for f in (LAND,) + BEATS:
    fxkit.hard(act, "root", "location", 1, f)
for f, r in ((f0 + 20, 0), (BEATS[0] + 1, 3.6), (BEATS[1] + 1, -3.6), (BEATS[2] + 1, 2.6), (BEATS[3] + 1, -1.6), (f0 + 44, .4), (f0 + 48, 0), (f1, 0)):
    key(arm, "body", f, r=r)
# the shoulders: dropped in the crouch, shrugged high in the jump, then one up on each rock
for bone, s in (("sh_l", 1), ("sh_r", -1)):
    seq = [(f0 + 4, -.045, 2 * s), (f0 + 8, .09, -3 * s), (UP, .1, -3.5 * s), (LAND, -.04, 2 * s), (f0 + 20, .01, 0)]
    for k, bt in enumerate(BEATS):
        up = (k % 2 == 0) == (s > 0)                  # leaning right lifts the left shoulder, and back
        seq.append((bt + 1, (.065 if up else -.02) * (1 - .2 * k), (-2.5 if up else 1) * s * (1 - .2 * k)))
    seq += [(f0 + 44, 0, 0), (f1, 0, 0)]
    for f, y, r in seq:
        key(arm, bone, f, y=y, r=r)
for f, y, r in ((f0 + 4, -.03, 0), (f0 + 9, .04, -2), (UP, .05, 1), (LAND + 1, -.04, 0), (BEATS[0] + 2, .02, -3), (BEATS[1] + 2, .02, 3),
                (BEATS[2] + 2, .015, -2), (BEATS[3] + 2, .01, 1), (f0 + 45, 0, 0), (f1, 0, 0)):
    key(arm, "hood", f, y=y, r=r)
for f, s in ((f0 + 4, .97), (UP, 1.04), (LAND + 1, .97), (f0 + 26, 1.02), (f0 + 40, 1.0), (f1, 1)):
    key(arm, "chest", f, sx=1 + (s - 1) * .5, sy=s)
follow(f0, f1, gain=.6)
rest(arm, ["root", "body", "chest", "sh_l", "sh_r", "hood"], f1)
fxkit.end_action(arm, act, f0)

# ================================================================== multi: static - a breath in three pulls, then the discharge
f0, f1 = CLIPS["multi"]
act = fxkit.begin_action(arm, SID + "_multi")
rest(arm, BONES, f0)
PULSES = (f0 + 5, f0 + 13, f0 + 21)
GO = f0 + 27
for f, s in ((PULSES[0] - 2, .99), (PULSES[0] + 1, 1.035), (PULSES[0] + 4, 1.025), (PULSES[1] + 1, 1.065), (PULSES[1] + 4, 1.055),
             (PULSES[2] + 1, 1.095), (GO - 1, 1.1), (GO + 2, .95), (GO + 6, 1.025), (GO + 10, .99), (GO + 15, 1), (f1, 1)):
    key(arm, "chest", f, sx=1 + (s - 1) * .45, sy=s, y=(s - 1) * .4)
fxkit.hard(act, "chest", "scale", 1, GO + 2)
for f, y in ((PULSES[0] + 2, .025), (PULSES[1] + 2, .05), (PULSES[2] + 2, .075), (GO - 1, .08), (GO + 2, -.03), (GO + 7, .012), (GO + 12, 0), (f1, 0)):
    key(arm, "hood", f, y=y)
for bone, s in (("sh_l", 1), ("sh_r", -1)):
    for f, y, r in ((PULSES[0] + 2, .02, -s), (PULSES[1] + 2, .04, -2 * s), (PULSES[2] + 2, .06, -3 * s), (GO - 1, .065, -3 * s),
                    (GO + 2, -.04, 2 * s), (GO + 7, .015, -.5 * s), (GO + 12, 0, 0), (f1, 0, 0)):
        key(arm, bone, f, y=y, r=r)
for i, f in enumerate(range(PULSES[1], GO - 1, 2)):    # charged: it trembles
    key(arm, "body", f, r=(.6 if i % 2 else -.6) * (1 + .4 * (f >= PULSES[2])), x=(.01 if i % 2 else -.01))
key(arm, "body", GO - 1, r=0, x=0); key(arm, "body", f1, r=0, x=0)
for f, sx, sy in ((GO + 1, 1.05, .93), (GO + 5, .975, 1.025), (GO + 10, 1, 1), (f1, 1, 1)):
    key(arm, "root", f, sx=sx, sy=sy)


def static(name, i, t):
    f = f0 + t * FPS
    env = (smooth(PULSES[0] - 1, PULSES[0] + 2, f) * .4 + smooth(PULSES[1] - 1, PULSES[1] + 2, f) * .3
           + smooth(PULSES[2] - 1, PULSES[2] + 2, f) * .3) * (1 - smooth(GO - 1, GO + 1, f))
    s = -1 if name == "cord_l" else 1                  # they repel: out apart, and lifted
    jit = math.sin(2 * math.pi * 9 * t + (0 if s < 0 else 1.7)) * env
    return Vector((s * (150 * env + 30 * jit) * (i / 4) ** .8, 0, 110 * env * (i / 4)))


follow(f0, f1, forces=static, gain=.85)
rest(arm, ["root", "body", "chest", "sh_l", "sh_r", "hood"], f1)
fxkit.end_action(arm, act, f0)

# ================================================================== effects
# (sizes in units: the frame is 13 across, 512 px - a unit is ~39 px, so a line needs a radius of ~.025 to read)
sc.frame_set(1)
LIM = 6.25
MIST = [(.92, .92, .9, 1), (.78, .78, .77, 1), (.98, .98, .96, 1)]
TAG = [(290, 340), (360, 300), (430, 320), (520, 270), (610, 300), (665, 330), (450, 440), (560, 420), (500, 500), (640, 470), (330, 380)]


def bone_pt(bone, x, y, f):
    """where icon point (x, y) on a bone's part sits at frame f (world x, z)"""
    sc.frame_set(int(f))
    pb = arm.pose.bones[bone]
    m = arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted()
    v = m @ wpt(x, y)
    return v.x, v.z


TIP = {"cord_l": CORDS["cord_l"][-1], "cord_r": CORDS["cord_r"][-1]}

# --- over the art (bloomed): crackles, bolts, bounce marks, sparkles
fxw = gp_object(FX, SID + "_fx", depth=-.8)
w_white = gp_mat(fxw, "fx_white_line", WHITE)
w_lime = gp_mat(fxw, "fx_lime_line", LIME)
w_spark = gp_mat(fxw, "fx_white_fill", WHITE, fill=WHITE)
w_limef = gp_mat(fxw, "fx_lime_fill", LIME, fill=LIME)
world = Board()


def bolt(f, p0, p1, seed, width=.03, amp=.18, hold=2, mats=None):
    """a crackle of static between two points: a lime zigzag with a white-hot core"""
    pts = fxkit.zigzag(*p0, *p1, n=max(4, int(math.dist(p0, p1) / .25)), amp=amp, seed=seed)
    pts = [(max(-LIM, min(LIM, x)), max(-LIM, min(LIM, z))) for x, z in pts]
    mats = mats or (w_lime, w_white)
    world.add(f, lambda dr, pts=pts: stroke(dr, pts, width, mat=mats[0]), hold=hold)
    world.add(f, lambda dr, pts=pts: stroke(dr, pts, width * .4, mat=mats[1]), hold=hold)


def bounce_marks(f0, x, z, side, size=1.0):
    """two little curved motion marks beside a shoulder on a beat: they pop out and shrink away"""
    for k in range(6):
        t = k / 5
        for j in range(2):
            r = (.5 + .26 * j + .16 * t) * size
            a0, a1 = (20, 70) if side > 0 else (110, 160)
            cx, cz = x + side * (.15 + .1 * t), z
            n = 8
            pts = [(cx + math.cos(math.radians(a0 + (a1 - a0) * i / n)) * r, cz + math.sin(math.radians(a0 + (a1 - a0) * i / n)) * r)
                   for i in range(n + 1)]
            world.add(f0 + k, lambda dr, pts=pts, t=t, n=n: stroke(dr, pts, 0, radii=[(.05 * (1 - t) + .008) * math.sin(math.pi * i / n) ** .5
                                                                                for i in range(n + 1)], mat=w_white))


# hit: bounce marks beside the shoulders on each beat
f0, f1 = CLIPS["hit"]
for k, bt in enumerate(BEATS):
    s = 1 if k % 2 == 0 else -1                        # the side it rocks toward
    x, z = bone_pt("sh_l" if s < 0 else "sh_r", *(SH_L if s < 0 else SH_R), bt + 1)
    bounce_marks(bt + 1, x + s * .6, z + .3, s, size=1.0 - .15 * k)
# multi: sparks crackle off the aglets and along the cords, more each pull; the discharge: a zap between the aglets,
# bolts flying out from the chest
f0, f1 = CLIPS["multi"]
for f in range(PULSES[0], GO, 2):
    lvl = sum(smooth(p_ - 1, p_ + 2, f) for p_ in PULSES)
    rr = random.Random(f)
    for name in ("cord_l", "cord_r"):
        for j in range(1 + int(lvl > 1.2)):
            tx, tz = bone_pt(f"{name}.3", *TIP[name], f)
            a = rr.uniform(-2.4, -.7)
            ln = .45 + .3 * lvl
            bolt(f, (tx, tz), (tx + math.cos(a) * ln * (1 if name == "cord_r" else -1), tz + math.sin(a) * ln), f * 5 + j * 3 + (name == "cord_r"),
                 width=.028 + .008 * lvl, amp=.12)
        k_ = rr.randrange(1, 3)                         # and off the cord itself, out into the air
        cx_, cz_ = bone_pt(f"{name}.{k_}", *CORDS[name][k_], f)
        s_ = -1 if name == "cord_l" else 1
        bolt(f, (cx_, cz_), (cx_ + s_ * (.4 + .2 * lvl), cz_ + rr.uniform(-.2, .3)), f * 7 + k_ + (name == "cord_r"), width=.024 + .006 * lvl, amp=.1)
    if lvl > 1.5:                                       # the charge jumps the gap between the cords
        a_, b_ = bone_pt("cord_l.2", *CORDS["cord_l"][2], f), bone_pt("cord_r.2", *CORDS["cord_r"][2], f)
        bolt(f, a_, b_, f * 11, width=.024, amp=.12)
ta, tb = bone_pt("cord_l.3", *TIP["cord_l"], GO), bone_pt("cord_r.3", *TIP["cord_r"], GO)
for k in range(3):
    bolt(GO + k, ta, tb, 900 + k, width=.06 - .015 * k, amp=.22)
CXF, CZF = px(*CHEST)
for k in range(5):                                       # the discharge: a white flash at the chest, flung out in rays
    t = k / 4
    world.add(GO + k, lambda dr, t=t: stroke(dr, star(CXF, CZF, .7 + 1.6 * t, .2 + .5 * t, points=8, inner=.2 * (1 - .8 * t)), .004,
                                             mat=w_spark if t < .5 else w_limef, cyclic=True, fill=True, line=False))
CX, CZ = px(*CHEST)
rnd = random.Random(12)
for i in range(9):
    a = 2 * math.pi * i / 9 + rnd.uniform(-.2, .2)
    for k in range(5):
        t = k / 4
        r0 = 1.4 + 3.0 * t
        r1 = r0 + 1.5 * (1 - .5 * t)
        p0 = (CX + math.cos(a) * r0, CZ + math.sin(a) * r0)
        p1 = (CX + math.cos(a) * min(r1, 5.6), CZ + math.sin(a) * min(r1, 5.6))
        bolt(GO + 1 + k, p0, p1, i * 37 + k, width=(.055 - .01 * k), amp=.16, hold=1)
world.draw(gp_layer(fxw, "fx"))

# sparkles on the aglets (they ride them; parented on the rest pose, frame 1)
sc.frame_set(CLIPS["idle"][0])
for name in ("cord_l", "cord_r"):
    ob = gp_object(FX, f"{SID}_fx_{name}", depth=-.85)
    ride(ob, arm, f"{name}.3")
    m_s = gp_mat(ob, "fx_white_fill", WHITE, fill=WHITE)
    m_g = gp_mat(ob, "fx_gold_fill", GOLD, fill=GOLD)
    bd = Board()
    tx, tz = px(*TIP[name])
    tx2, tz2 = px(TIP[name][0] - 4, TIP[name][1] - 22)
    if name == "cord_r":
        fxkit.sparkle(bd, CLIPS["idle"][0] + 60, 9, tx2, tz2, .3, m_s, rot0=.3)     # the tag's light catches it
        fxkit.sparkle(bd, CLIPS["hit"][0] + 12, 10, tx2, tz2, .44, m_g, rot0=.1)
        fxkit.sparkle(bd, CLIPS["land"][0] + 6, 9, tx2, tz2, .34, m_s, rot0=.6)
    else:
        fxkit.sparkle(bd, CLIPS["idle"][0] + 45, 8, tx2, tz2, .26, m_s, rot0=.5)
        fxkit.sparkle(bd, CLIPS["hit"][0] + 25, 10, tx2, tz2, .44, m_s, rot0=.4)
    fxkit.sparkle(bd, GO + 2, 10, tx, tz, .5, m_s, rot0=.2)
    bd.draw(gp_layer(ob, "fx"))

# --- on the art: spray-paint mist bursting off the tag, puffs under the hem
art_fx = gp_object(ART, SID + "_mist", depth=-1.0)
m_mist = [gp_mat(art_fx, f"fx_mist{i}", c, fill=c) for i, c in enumerate(MIST)]
m_puff = gp_mat(art_fx, "fx_puff", (.3, .3, .33, 1), fill=(.62, .62, .66, 1))
ab = Board()


def mist(f0, n, seed, life=14, speed=(1.6, 4.0)):
    """overspray: fine paint dots puffing out of the tag in every direction, slowing, shrinking to nothing"""
    rnd = random.Random(seed)
    for i in range(n):
        x, y = TAG[rnd.randrange(len(TAG))]
        st = f0 + rnd.randint(0, 3)
        x0, z0 = bone_pt("chest", x + rnd.uniform(-30, 30), y + rnd.uniform(-20, 20), st)
        a = rnd.uniform(0, 2 * math.pi)
        sp = rnd.uniform(*speed)
        r0 = rnd.uniform(.03, .065)
        mat = m_mist[i % 3]
        for k in range(life):
            u = k / life
            d = sp * (1 - (1 - u) ** 2) / 2.2                # flung out, slowing in the air
            xx, zz = x0 + math.cos(a) * d, z0 + math.sin(a) * d - .3 * u * u
            r = r0 * (1 - u ** 1.5)
            if r < .01 or abs(xx) > LIM or abs(zz) > LIM:
                break
            ab.add(st + k, lambda dr, xx=xx, zz=zz, r=r, mat=mat: stroke(dr, fxkit.ring(xx, zz, r, n=10), .003, mat=mat, cyclic=True,
                                                                         fill=True, line=False))


f0, f1 = CLIPS["hit"]
mist(UP - 1, 70, 3)
mist(BEATS[0] + 1, 26, 5, speed=(1.0, 2.6))
f0, f1 = CLIPS["land"]
for side, seed in ((-1, 3), (1, 5), (-1, 9), (1, 13)):
    far = 1 if seed in (3, 5) else .65
    x, z = px(510 + side * 210, 935)
    fxkit.dust(ab, f0 + 2, 11, x, z, .4 * far + .1, m_puff, drift=(side * 1.5 * far, .3), seed=seed)
f0, f1 = CLIPS["hit"]
for side, seed in ((-1, 23), (1, 25)):
    x, z = px(510 + side * 220, 935)
    fxkit.dust(ab, LAND, 11, x, z, .48, m_puff, drift=(side * 1.6, .3), seed=seed)
ab.draw(gp_layer(art_fx, "mist"))

# ================================================================== idle accent: the tag lights up like neon
# Copies of the hoodie's skinned mesh (the SAME mesh and bones, so they bend exactly as the cloth does) showing only
# the tag's letters - a mask made here from the body's own pixels: the light grey paint inside the tag's box. On the
# second beat a band of lime neon runs across the letters left to right, white-hot at its front, and switches off
# from the left behind it: wiped on and wiped off (never faded), bloomed by the compositor. Before and after it the
# band sits off the tag: frame 1 and the loop's end are plain (the land / hit / multi hand-offs see no light).
import numpy as np
f0, f1 = CLIPS["idle"]
body_ob = bpy.data.objects[SID + "_body"]
src = next(n.image for n in body_ob.data.materials[0].node_tree.nodes if n.type == "TEX_IMAGE")
iw, ih = src.size
pix = np.empty(iw * ih * 4, np.float32)
src.pixels.foreach_get(pix)
pix = pix.reshape(ih, iw, 4)
bx0, by0, bx1, by1 = PARTS["body"]["box"]
X, Y = np.meshgrid(bx0 + (np.arange(iw) + .5) / iw * (bx1 - bx0), by0 + (1 - (np.arange(ih) + .5) / ih) * (by1 - by0))


def nss(e0, e1, v):
    t = np.clip((v - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


lum = pix[..., :3].mean(-1)
sat = pix[..., :3].max(-1) - pix[..., :3].min(-1)
mask = nss(.40, .58, lum) * (1 - nss(.10, .2, sat)) * nss(.5, 1, pix[..., 3])
mask *= nss(232, 246, X) * (1 - nss(708, 722, X)) * nss(196, 208, Y) * (1 - nss(574, 586, Y))
full = mask.copy()                                     # (the copy under the cords keeps all of it)
for n_, chn in CORDS.items():                          # clear of the cords
    d = np.full(X.shape, 1e9, np.float32)
    for (ax, ay), (bx, by) in zip(chn, chn[1:]):
        dx, dy = bx - ax, by - ay
        t = np.clip(((X - ax) * dx + (Y - ay) * dy) / (dx * dx + dy * dy), 0, 1)
        d = np.minimum(d, np.hypot(ax + dx * t - X, ay + dy * t - Y))
    mask *= nss(19, 27, d)
print(f"  tag mask: {float((mask > .5).mean()) * 100:.1f}% of the body image lit, lum p50 {float(np.median(lum[mask > .5])):.2f}")


def mask_image(name, m):
    img = bpy.data.images.get(name)
    if img:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, iw, ih, alpha=True)
    img.colorspace_settings.name = "Non-Color"
    buf = np.ones((ih, iw, 4), np.float32)
    buf[..., 0] = buf[..., 1] = buf[..., 2] = m
    img.pixels.foreach_set(buf.ravel())
    img.update()
    try:
        img.pack()
    except Exception as e:                             # (a generated image packs as PNG; if not, it is rebuilt each run)
        print("  tag mask not packed:", e)
    return img


def tag_neon(name, img, coll, depth):
    """the lit copy of the hoodie: `img` the letters it shows, in collection `coll` at `depth`"""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    NN, LL = nt.nodes, nt.links

    def mth(op, a, b=None, clamp=False):
        n = NN.new("ShaderNodeMath")
        n.operation, n.use_clamp = op, clamp
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                LL.new(v, n.inputs[i])
        return n.outputs[0]

    uvn = NN.new("ShaderNodeTexCoord")
    sep = NN.new("ShaderNodeSeparateXYZ")
    LL.new(uvn.outputs["UV"], sep.inputs[0])
    tex = NN.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Linear"
    LL.new(uvn.outputs["UV"], tex.inputs["Vector"])
    vhead, vtail = NN.new("ShaderNodeValue"), NN.new("ShaderNodeValue")
    vhead.name = vhead.label = "head"
    vtail.name = vtail.label = "tail"
    u = sep.outputs["X"]
    E, E2 = .018, .035                                     # the band's soft edges; the white-hot front
    on = mth("MULTIPLY", mth("ADD", mth("MULTIPLY", mth("SUBTRACT", u, vtail.outputs[0]), 1 / E), .5, clamp=True),
             mth("ADD", mth("MULTIPLY", mth("SUBTRACT", vhead.outputs[0], u), 1 / E), .5, clamp=True))
    hot = mth("MULTIPLY", mth("ADD", mth("MULTIPLY", mth("ABSOLUTE", mth("SUBTRACT", u, vhead.outputs[0])), -1 / E2), 1, clamp=True), on)
    alpha = mth("MULTIPLY", mth("MINIMUM", mth("ADD", mth("MULTIPLY", on, .78), hot), 1.0), tex.outputs["Color"])
    col = NN.new("ShaderNodeMix")
    col.data_type = "RGBA"
    cin = [s_ for s_ in col.inputs if s_.type == "RGBA"]
    cin[0].default_value, cin[1].default_value = LIME, WHITE
    LL.new(hot, col.inputs[0])
    emi = NN.new("ShaderNodeEmission")
    LL.new(next(s_ for s_ in col.outputs if s_.type == "RGBA"), emi.inputs["Color"])
    emi.inputs["Strength"].default_value = 1.0
    tr = NN.new("ShaderNodeBsdfTransparent")
    mix = NN.new("ShaderNodeMixShader")
    LL.new(alpha, mix.inputs[0])
    LL.new(tr.outputs[0], mix.inputs[1])
    LL.new(emi.outputs[0], mix.inputs[2])
    outn = NN.new("ShaderNodeOutputMaterial")
    LL.new(mix.outputs[0], outn.inputs["Surface"])
    for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
        try:
            setattr(mat, attr, val)
        except Exception:
            pass
    U0, U1 = (225 - bx0) / (bx1 - bx0), (735 - bx0) / (bx1 - bx0)    # just off the tag, either side
    for node, keys_ in ((vhead, ((0, U0), (19, U0), (40, U1), (N, U1))), (vtail, ((0, U0), (29, U0), (52, U1), (N, U1)))):
        for k, v in keys_:
            node.outputs[0].default_value = v
            node.outputs[0].keyframe_insert("default_value", frame=f0 + k)
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    neon_ob = body_ob.copy()                               # shares the skinned mesh: its bone groups, its Armature modifier
    neon_ob.name = name
    coll.objects.link(neon_ob)
    neon_ob.material_slots[0].link = "OBJECT"
    neon_ob.material_slots[0].material = mat
    neon_ob.matrix_world = Matrix.Translation((0, depth, 0))
    return neon_ob


# on the effects layer (bloomed), clear of the cords; and on the art layer, between the hoodie and the cords, the
# whole tag - so the letters under a cord light up too, and the cord still hangs over them
tag_neon(SID + "_tagneon", mask_image(SID + "_tagmask", mask), FX, -.7)
tag_neon(SID + "_tagneon_art", mask_image(SID + "_tagmask_art", full), ART, -.15)

# the paint catching the light just after the band has passed: two glints on the letters (they ride the chest)
sc.frame_set(f0)
tg = gp_object(FX, SID + "_fx_tag", depth=-.75)
ride(tg, arm, "chest")
t_s = gp_mat(tg, "fx_white_fill", WHITE, fill=WHITE)
t_l = gp_mat(tg, "fx_lime_fill", LIME, fill=LIME)
tb = Board()
fxkit.sparkle(tb, f0 + 31, 9, *px(470, 268), .3, t_s, rot0=.2)
fxkit.sparkle(tb, f0 + 41, 9, *px(668, 318), .34, t_l, rot0=.6)
tb.draw(gp_layer(tg, "fx"))

sc.frame_start, sc.frame_end = 1, max(b for a, b in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], "| saved", fxkit.save(SID))
