# L4 - two hangtags on a string loop - animated in Blender: four Actions on its rig (idle, land, hit, multi) laid one
# after another on the rig's NLA track, and its effects drawn frame by frame in Grease Pencil on the same timeline.
#   the string  keyed by hand: the loop hangs from its top and swings like a pendulum - a breeze (idle), a drop that
#               stretches it (land), a hard flick (hit), shaken faster and faster (multi)
#   the tags    worked out in Blender from how the keys move the string: each tag hangs from the grommet on its own
#               spring - the front tag stiff and close to the string, the back tag heavier and slower, so it lags,
#               overshoots and fans out behind - keyed onto their bones sparsely. The back tag twists on the string
#               as it swings (it narrows as it turns edge-on). (Their bones turn about the grommet.)
#   effects     a glare sweeping the front tag, glints off the lettering, motion arcs off the tags' corners in the big
#               swings, clink ticks at the grommet, a ring of light and a spray of streaks when the multiplier lets go
# Runs INSIDE Blender, after build_symbol_scene.py (tools/blender/run.py runs both in a background Blender).
import bpy, importlib, math, os, random, sys
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
import fxkit
importlib.reload(fxkit)
from fxkit import key, rest, px, vec, smooth, gp_object, gp_mat, gp_layer, ride, stroke, star, ring, Board, WHITE, GOLD

SID = "L4"
sc, arm, spec = fxkit.setup(SID)
FPS = sc.render.fps
HOLE, TOP = (497, 298), (450, 44)
ICE = (0.72, 0.86, 1.0, 1)                   # a cool white-blue for the glare and glints on the dark card

ART, FXB, FX = fxkit.layers(sc, SID)
fxkit.glow_compositor(sc, SID, back=dict(strength=.9, size=.5, gain=1.5), front=dict(strength=.8, size=.4, gain=1.5))
if arm.animation_data:
    arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)

BONES = ["string", "front", "back"]
# the tags on the grommet: their chain runs from the grommet to the middle of the tag's bottom edge (icon px)
HANGING = {
    "front": dict(chain=[HOLE, (420, 860)], freq=[2.8], zeta=.3, gain=1.0, limit=1.2),     # stiff: rides the string
    "back": dict(chain=[HOLE, (735, 905)], freq=[1.25], zeta=.14, gain=1.0, limit=7),      # heavy, slow, swings wide
}
CLIPS = {"idle": (1, 80), "land": (101, 126), "hit": (201, 250), "multi": (301, 346)}
arm["clips"] = {k: list(v) for k, v in CLIPS.items()}


def back_soft(r):
    """The back tag may swing forward freely, back only a little: turned back past ~3 deg it would sink its top
    corner (and the white border on it) behind the front tag."""
    return r if r >= 0 else -2.8 * math.tanh(-r / 2.8)


def follow(f0, f1, loop=False, forces=None, gain=1.0, twist=.0):
    """The tags, worked out from how this clip moves the string, keyed onto their bones; the back tag twists on the
    string as it swings out (twist: how far it narrows per degree it hangs off true), so it is square-on at rest."""
    res = fxkit.secondary(sc, arm, "string", f0, f1, HANGING, loop=loop, forces=forces, gain=gain)
    res["back"] = [back_soft(r) for r in res["back"]]
    print(f"  {f0}-{f1}:", ", ".join(f"{b} {min(v):+.2f}..{max(v):+.2f}" for b, v in res.items()))
    for bone, vals in res.items():
        fxkit.key_series(arm, bone, f0, vals, channel="r", tol=.12, loop=loop)
    if twist:
        sx = [1 - .16 * math.tanh(twist * abs(r) / .16) for r in res["back"]]
        series = sx + ([sx[0]] if loop else [])
        for i in sorted(set(fxkit.sparse(series, .004))):
            key(arm, "back", f0 + i, sx=series[i], sy=1)
    return res


# ================================================================== idle: a breeze; the loop sways, the tags follow
f0, f1 = CLIPS["idle"]
act = fxkit.begin_action(arm, SID + "_idle")
rest(arm, BONES, f0)
for f, r in ((21, 1.5), (41, 0), (61, -1.5), (81, 0)):
    key(arm, "string", f, r=r)


def breeze(name, i, t):
    T = 80 / FPS
    if name != "back":
        return Vector((0, 0, 0))
    return Vector((15 * math.sin(2 * math.pi * t / T + 1.3), 0, 0))


follow(f0, f1, loop=True, forces=breeze, twist=.03)
fxkit.make_cyclic(act)
fxkit.end_action(arm, act, f0)

# ================================================================== land: the tags drop onto the string and swing
f0, f1 = CLIPS["land"]
act = fxkit.begin_action(arm, SID + "_land")
rest(arm, BONES, f0)
for f, sy, r in ((103, 1.035, 0), (106, .985, -1.6), (110, 1.008, 1.1), (114, 1, -.5), (119, 1, .15), (f1, 1, 0)):
    key(arm, "string", f, sx=1 / math.sqrt(sy), sy=sy, r=r)
fxkit.hard(act, "string", "scale", 1, 103)
follow(f0, f1, gain=.9, twist=.03)
fxkit.end_action(arm, act, f0)

# ================================================================== hit: a hard flick, a big swing that dies down
f0, f1 = CLIPS["hit"]
act = fxkit.begin_action(arm, SID + "_hit")
rest(arm, BONES, f0)
for f, r in ((204, 1.8), (209, -6.0), (215, 5.0), (221, -3.6), (227, 2.3), (233, -1.3), (239, .6), (244, -.2), (f1, 0)):
    key(arm, "string", f, r=r)
for f, s in ((204, .99), (209, 1.02), (214, 1), (f1, 1)):
    key(arm, "string", f, sx=1 / math.sqrt(s), sy=s)
follow(f0, f1, gain=1.0, twist=.025)
fxkit.end_action(arm, act, f0)

# ================================================================== multi: shaken faster and faster, then let go
f0, f1 = CLIPS["multi"]
act = fxkit.begin_action(arm, SID + "_multi")
rest(arm, BONES, f0)
LET_GO = 326
rows, f, k, per = [], 304, 0, 6.0
while f < LET_GO - 2:
    amp = 1.2 + 2.6 * (f - 304) / (LET_GO - 304)
    rows.append((round(f), amp * (1 if k % 2 == 0 else -1)))
    f += per; per = max(2.2, per * .82); k += 1
rows += [(LET_GO, -2.5), (LET_GO + 5, 6.5), (LET_GO + 11, -4.2), (LET_GO + 17, 2.2), (f1 - 3, -.3), (f1, 0)]
for f, r in rows:
    key(arm, "string", f, r=r)
for f, s in ((LET_GO - 1, 1.02), (LET_GO + 2, .97), (LET_GO + 6, 1.01), (LET_GO + 10, 1), (f1, 1)):
    key(arm, "string", f, sx=1 / math.sqrt(s), sy=s)
follow(f0, f1, gain=1.0, twist=.03)
fxkit.end_action(arm, act, f0)


# ================================================================== effects
def track(bone, pts, frames, sub=1):
    pb = arm.pose.bones[bone]
    inv = pb.bone.matrix_local.inverted()
    out = {}
    for f in frames:
        for s in range(sub):
            sc.frame_set(f, subframe=s / sub)
            M = arm.matrix_world @ pb.matrix @ inv
            out[f + s / sub] = [((M @ vec(*p)).x, (M @ vec(*p)).z) for p in pts]
    sc.frame_set(1)
    return out


sc.frame_set(1)
fx = gp_object(FX, SID + "_fx", depth=-.8)
on_front = gp_object(FX, SID + "_fx_front", depth=-.8)
ride(on_front, arm, "front")
back = gp_object(FXB, SID + "_fxb_glow", depth=.35)       # (never a part's name: gp_object replaces that object)
m = dict(white=gp_mat(fx, "fx_white_line", WHITE), white_f=gp_mat(fx, "fx_white_fill", WHITE, fill=WHITE),
         ice=gp_mat(fx, "fx_ice_line", ICE), ice_f=gp_mat(fx, "fx_ice_fill", ICE, fill=ICE), gold_f=gp_mat(fx, "fx_gold_fill", GOLD, fill=GOLD))
mf = dict(white=gp_mat(on_front, "fx_white_line", WHITE), white_f=gp_mat(on_front, "fx_white_fill", WHITE, fill=WHITE),
          ice_f=gp_mat(on_front, "fx_ice_fill", ICE, fill=ICE))
mb = dict(white=gp_mat(back, "glow_white", WHITE), ice=gp_mat(back, "glow_ice", ICE))
world, front_b, behind = Board(), Board(), Board()

# the front tag's face (icon px corners, inside its ink edge): the glare runs across it
FACE = [(262, 268), (640, 300), (555, 870), (240, 828)]


def glare(board, f0, life, width=.32, angle=55, mat=None):
    """A band of light sweeping across the front tag's face (clipped to the face), riding the tag."""
    (ax, az), (bx, bz), (cx, cz), (dx, dz) = [px(*p) for p in FACE]
    a = math.radians(angle)
    ux, uz = math.cos(a), math.sin(a)                     # the band runs along u, sweeps along its normal
    nx_, nz_ = -uz, ux
    corners = [px(*p) for p in FACE]
    proj = [x * nx_ + z * nz_ for x, z in corners]
    lo, hi = min(proj) - width, max(proj) + width
    for k in range(life):
        t = k / (life - 1)
        c = lo + (hi - lo) * t
        poly = clip_band(corners, (nx_, nz_), c - width / 2, c + width / 2)
        if len(poly) >= 3:
            board.add(f0 + k, lambda dr, poly=poly: stroke(dr, poly, .004, opacity=.55, mat=mat, cyclic=True, fill=True, line=False))


def clip_band(poly, n, lo, hi):
    """The part of a convex polygon between two lines (x.n = lo and x.n = hi)."""
    def clip(pts, keep):
        out = []
        for i in range(len(pts)):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            vp, vq = keep(p), keep(q)
            if vp >= 0:
                out.append(p)
            if vp * vq < 0:
                t = vp / (vp - vq)
                out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
        return out
    pts = clip(poly, lambda p: p[0] * n[0] + p[1] * n[1] - lo)
    return clip(pts, lambda p: hi - (p[0] * n[0] + p[1] * n[1])) if pts else []


def trails(board, paths, f0, f1, mats, w=.06, span=1.5, samples=7, min_len=.3):
    for f in range(f0, f1 + 1):
        times = [f - span + span * j / (samples - 1) for j in range(samples)]
        for ci in range(len(paths[f])):
            pts = [paths[math.floor(t * 4) / 4][ci] for t in times if math.floor(t * 4) / 4 in paths]
            if len(pts) < 3 or math.dist(pts[0], pts[-1]) < min_len:
                continue
            n = len(pts)
            radii = [w * (j / (n - 1)) ** 1.4 for j in range(n)]
            board.add(f, lambda dr, pts=pts, radii=radii: stroke(dr, pts, 0, radii=radii, mat=mats[0]))
            board.add(f, lambda dr, pts=pts, radii=[r * .4 for r in radii]: stroke(dr, pts, 0, radii=radii, mat=mats[1]))


def ticks(board, f0, x, z, mats, a0=0, a1=360, n=6, r0=.15, r1=.6, life=5, w=.03, seed=0):
    rnd = random.Random(seed)
    angs = [math.radians(a0 + (a1 - a0) * (i + .5) / n + rnd.uniform(-8, 8)) for i in range(n)]
    for k in range(life):
        t = k / max(1, life - 1)
        for i, a in enumerate(angs):
            ra = r0 + (r1 - r0) * t ** .7
            rb = ra + .22 * (1 - t) + .04
            board.add(f0 + k, lambda dr, a=a, ra=ra, rb=rb, t=t, i=i: stroke(
                dr, [(x + math.cos(a) * ra, z + math.sin(a) * ra), (x + math.cos(a) * rb, z + math.sin(a) * rb)],
                w * (1 - t) ** .8 + .006, mat=mats[i % len(mats)]))


def rings_out(board, f0, cx, cz, r0, r1, mats, life=11, lag=3, width=.12):
    for j, mat in enumerate(mats):
        for k in range(life):
            t = k / (life - 1)
            r = r0 + (r1 - r0) * (1 - (1 - t) ** 1.6)
            w = width * (1 - t) ** 1.3
            if w > .004:
                board.add(f0 + lag * j + k, lambda dr, r=r, w=w, mat=mat, f=f0 + k: stroke(
                    dr, ring(cx, cz, r, n=96, wobble=.02, seed=f), w, mat=mat, cyclic=True))


# ---- idle: a glint on the lettering now and then
fxkit.sparkle(front_b, 18, 9, *px(470, 330), .28, mf["white_f"], rot0=.4)
fxkit.sparkle(front_b, 57, 9, *px(345, 760), .24, mf["white_f"], rot0=1.0)

# ---- land: the grommet clinks, a glare runs over the tag
gx, gz = px(*HOLE)
ticks(world, 103, gx, gz, (m["white"], m["ice"]), a0=-60, a1=240, n=6, seed=3)
glare(front_b, 104, 9, mat=mf["white_f"])

# ---- hit: motion arcs off the tags' bottom corners through the big swing, a glare and glints, sparkles
CORN = {"front": [(240, 840), (560, 880)], "back": [(589, 939), (893, 872)]}
for bone, pts in CORN.items():
    paths = track(bone, pts, range(203, 236), sub=4)
    trails(world, paths, 205, 234, (m["ice"], m["white"]), min_len=.35)
ticks(world, 208, gx, gz, (m["white"], m["ice"]), a0=-60, a1=240, n=7, seed=8)
glare(front_b, 210, 10, mat=mf["white_f"])
for i, (lx, ly) in enumerate(((455, 360), (330, 520), (500, 610), (360, 760), (470, 820))):
    fxkit.sparkle(front_b, 214 + 3 * i, 9, *px(lx, ly), .3 if i % 2 else .36, mf["white_f"] if i % 2 else mf["ice_f"], rot0=i * .6)
rnd = random.Random(4)
for i in range(7):
    fxkit.sparkle(world, 222 + rnd.randint(0, 16), rnd.randint(7, 10), rnd.uniform(-4.6, 4.6), rnd.uniform(-4.4, 4.8),
                  rnd.uniform(.2, .38), m["white_f"] if i % 3 else m["gold_f"], rot0=rnd.uniform(0, 1))

# ---- multi: clink ticks quicker and quicker as it is shaken, motion arcs; a ring of light and streaks as it lets go
for f, r in rows[:-6]:
    ticks(world, f, gx, gz, (m["white"], m["ice"]), a0=-40, a1=220, n=5, r0=.12, r1=.45, life=4, w=.024, seed=f)
for bone, pts in CORN.items():
    paths = track(bone, pts, range(LET_GO - 2, LET_GO + 20), sub=4)
    trails(world, paths, LET_GO, LET_GO + 18, (m["ice"], m["white"]), min_len=.35)
cx, cz = px(500, 560)
rings_out(behind, LET_GO, cx, cz, 1.6, 5.4, (mb["ice"], mb["white"], mb["ice"]), life=11, lag=3, width=.13)
fxkit.streaks(world, LET_GO, 9, cx, cz, 3.4, 6.2, (m["white"], m["ice"]), n=16, rot=.15)
glare(front_b, LET_GO - 6, 8, mat=mf["white_f"])
rnd = random.Random(12)
for i in range(6):
    fxkit.sparkle(world, LET_GO + 3 + rnd.randint(0, 8), rnd.randint(7, 8), rnd.uniform(-4.6, 4.6), rnd.uniform(-4.4, 4.8),
                  rnd.uniform(.2, .36), m["white_f"] if i % 2 else m["gold_f"], rot0=rnd.uniform(0, 1))

world.draw(gp_layer(fx, "fx"))
front_b.draw(gp_layer(on_front, "fx"))
behind.draw(gp_layer(back, "burst"))

sc.frame_start, sc.frame_end = 1, max(b for a, b in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], "| saved", fxkit.save(SID))
