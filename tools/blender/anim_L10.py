# L10 - the lowrider - animated in Blender: four Actions on its rig (idle, land, hit, multi) laid one after another
# on the rig's NLA track, and its effects drawn frame by frame in Grease Pencil on the same timeline.
#   the car     keyed by hand, pivoting on the rear tyre's contact patch like a car on hydraulics: it breathes on its
#               rams (idle), thumps down and bucks (land), squats, fires its nose into the air and slams back down
#               scraping sparks (hit), pumps three times harder and harder while its underglow charges, then launches
#               (multi)
#   the wheel   the big front wheel hangs on its springs, worked out in Blender from how the keys move the car: while
#               its tyre is on the ground it stays there and the spring stretches as the nose lifts; once the nose
#               lifts past the spring's reach the wheel leaves the ground and dangles on it (a damped spring), and it
#               is pushed home when the nose comes down. The tyre squashes on each slam
#   effects     dust rolling out from the tyres, sparks scraped off the front of the frame, hydraulic hiss, motion
#               lines, chrome glints, and the lime underglow the multiplier charges up (behind the car, bloomed)
# A low symbol: no tier glow - these effects are its own.
# Runs INSIDE Blender, after build_symbol_scene.py (tools/blender/run.py runs both in a background Blender).
import bpy, importlib, math, os, random, sys
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
import fxkit
importlib.reload(fxkit)
from fxkit import (key, rest, px, smooth, gp_object, gp_mat, gp_layer, ride, stroke, star, ring, Board,
                   LIME, WHITE, GOLD)

SID = "L10"
sc, arm, spec = fxkit.setup(SID)
FPS = sc.render.fps
ART, FXB, FX = fxkit.layers(sc, SID)
fxkit.glow_compositor(sc, SID, back=dict(strength=1.0, size=.6, gain=1.7), front=dict(strength=.9, size=.42, gain=1.5))
if arm.animation_data:
    arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)

BONES = ["body", "wheel_near"]
CLIPS = {"idle": (1, 72), "land": (101, 124), "hit": (201, 250), "multi": (301, 348)}
arm["clips"] = {k: list(v) for k, v in CLIPS.items()}
ORANGE = (1.0, .55, .12, 1)

# where things are (icon px)
TYRE = (546, 668)            # the big front tyre's contact patch
HUB = (546, 566)
FAR_TYRE = (196, 738)        # the far front tyre's
REAR_TYRE = (862, 692)       # the rear tyre's (the pivot)
BUMPER_LOW = (96, 612)       # the bottom of the front bumper: where it scrapes
REACH = .30                  # how far the big wheel's spring lets it drop out of the arch (units)
TYRE_R = 1.02                # hub to the tyre's bottom (units)


CH = {"x": ("location", 0), "y": ("location", 1), "r": ("rotation_euler", 2), "sx": ("scale", 0), "sy": ("scale", 1)}


def k1(bone, f, **chans):
    """Key single channels of a bone (x / y units, r degrees, sx / sy): only those F-curves get a key."""
    pb = arm.pose.bones[bone]
    for ch, v in chans.items():
        path, i = CH[ch]
        getattr(pb, path)[i] = math.radians(v) if ch == "r" else v
        pb.keyframe_insert(path, index=i, frame=f, group=bone)


def series(bone, f0, vals, ch, tol, loop=False):
    """A per-frame series keyed sparsely (fxkit.sparse: its turning points and what keeps it within tol)."""
    s = list(vals) + ([vals[0]] if loop else [])
    for i in fxkit.sparse(s, tol):
        k1(bone, f0 + i, **{ch: s[i]})


def hard(act, f, chans=("loc_y", "rot")):
    """Keys on the car that are hit, not eased into (a slam)."""
    if "loc_y" in chans:
        fxkit.hard(act, "body", "location", 1, f)
    if "rot" in chans:
        fxkit.hard(act, "body", "rotation_euler", 2, f)
    if "scale" in chans:
        fxkit.hard(act, "body", "scale", 1, f)


def car(keys):
    """Key the car: (frame, r, y, sx, sy) - r degrees (nose up is negative: it turns about the rear tyre), y units."""
    for f, r, y, sx, sy in keys:
        k1("body", f, r=r, y=y, sx=sx, sy=sy)


def hang(f0, f1, squash=(), loop=False, settle=6):
    """The big front wheel on its spring, worked out from how this clip moves the car. h = how far the car has lifted
    the tyre's resting contact patch off the ground (world, units). While the tyre is down (h below the spring's
    stretch) it stays on the ground: the spring stretches by h. Once the car lifts it past that, the wheel leaves the
    ground and hangs on the spring, a damped mass driven by how the car accelerates. It drops by d (units, along the
    car's own down) - never above home, where the tyre would ride up over the fender. squash: [(frame, amount)] the
    tyre squashes on its contact patch as it is slammed home, and springs back."""
    pb = arm.pose.bones["body"]
    rest_inv = pb.bone.matrix_local.inverted()
    c0 = fxkit.vec(*TYRE)
    hs = []
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        M = arm.matrix_world @ pb.matrix @ rest_inv
        hs.append((M @ c0).z - c0.z)
    n = len(hs)
    om, zeta, sub = 2 * math.pi * 3.2, .16, 8
    dt = 1 / (FPS * sub)
    laps = 3 if loop else 1
    d, v = 0.0, 0.0
    out = []
    for lap in range(laps):
        rec = []
        for k in range(n):
            rec.append(d)                           # the state at frame k
            k2 = (k + 1) % n if loop else min(k + 1, n - 1)
            km = (k - 1) % n if loop else max(k - 1, 0)
            acc = (hs[k2] - 2 * hs[k] + hs[km]) * FPS * FPS     # how the car accelerates at the tyre
            for s in range(sub):
                h1 = hs[k] + (hs[k2] - hs[k]) * (s + 1) / sub
                # free, it hangs on its spring (it lags the car's moves); the ground under the tyre stops it
                # dropping further than the car has lifted it, and the bump stop at home
                a = om * om * (REACH - d) - 2 * zeta * om * v + acc * .8
                nd = d + (v + a * dt) * dt
                lim = max(h1, 0.0)
                if nd >= lim:
                    nd, v = lim, (lim - d) / dt
                else:
                    v += a * dt
                if nd < 0:
                    nd, v = 0.0, max(0.0, -v * .3)
                if nd > REACH * 1.12:               # the rams' full stroke: it stops there and bounces back
                    nd, v = REACH * 1.12, min(0.0, -v * .35)
                d = nd
        out = rec
    if not loop and settle:                         # ease the last frames onto home
        for j in range(settle):
            i = n - settle + j
            t = (j + 1) / settle
            out[i] *= 1 - t * t * (3 - 2 * t)
    # the tyre's squash on a slam: about its contact patch (the hub moves down by what the squash takes off the
    # tyre's height, so the patch stays on the ground)
    sq = [0.0] * n
    for fs, amt in squash:
        for k in range(n):
            f = f0 + k
            if f >= fs:
                t = (f - fs) / FPS
                sq[k] += amt * math.exp(-t * 9) * math.cos(t * 28)
    if not loop and settle:                         # home exactly on the last frame
        for j in range(settle):
            t = (j + 1) / settle
            sq[n - settle + j] *= 1 - t * t * (3 - 2 * t)
    S = [1 - max(0.0, q) for q in sq]
    series("wheel_near", f0, [-d - TYRE_R * (1 - s) for d, s in zip(out, S)], "y", .002, loop)
    series("wheel_near", f0, S, "sy", .002, loop)
    series("wheel_near", f0, [1 + .55 * (1 - s) for s in S], "sx", .002, loop)
    series("wheel_near", f0, [-d / REACH * 3.0 for d in out], "r", .08, loop)
    print(f"  {f0}-{f1}: wheel drop {min(out) * 100:.1f}..{max(out) * 100:.1f} px")
    return out


# ================================================================== idle: it breathes on its hydraulics
f0, f1 = CLIPS["idle"]
act = fxkit.begin_action(arm, SID + "_idle")
rest(arm, BONES, f0)
car([(19, -1.0, .02, 1, 1.006), (30, -.85, .015, 1, 1.004), (46, .18, 0, 1.002, .995), (57, -.08, 0, 1, 1.001), (73, 0, 0, 1, 1)])
idle_drop = hang(f0, f1, loop=True)
fxkit.make_cyclic(act)
fxkit.end_action(arm, act, f0)

# ================================================================== land: it thumps down on its tyres and bucks
f0, f1 = CLIPS["land"]
act = fxkit.begin_action(arm, SID + "_land")
rest(arm, BONES, f0)
car([(103, 1.3, -.02, 1.012, .935), (107, -2.8, .06, .996, 1.025), (111, .7, 0, 1.004, .985), (115, -.6, .01, 1, 1.006),
     (119, .12, 0, 1, 1), (124, 0, 0, 1, 1)])
hard(act, 103, ("loc_y", "rot", "scale")); hard(act, 111)
hang(f0, f1, squash=[(103, .1), (111, .035)])
fxkit.end_action(arm, act, f0)

# ================================================================== hit: squat, the nose fires up, slam, scrape, bounce
f0, f1 = CLIPS["hit"]
act = fxkit.begin_action(arm, SID + "_hit")
rest(arm, BONES, f0)
car([(204, 1.7, -.03, 1.01, .95), (206, 1.9, -.035, 1.012, .945),
     (211, -9.0, .5, .994, 1.05), (216, -11.2, .72, 1, 1.0), (219, -10.2, .6, 1, 1.0),
     (223, 2.4, 0, 1.02, .9), (226, -4.6, .12, .996, 1.03), (229, .9, 0, 1.006, .965), (233, -1.3, .02, 1, 1.008),
     (237, .35, 0, 1, 1), (242, 0, 0, 1, 1), (250, 0, 0, 1, 1)])
for i, f in enumerate((205, 206)):                   # the rams shudder as they build pressure
    k1("body", f, x=.012 if i % 2 else -.012)
k1("body", 204, x=0); k1("body", 207, x=0)
hard(act, 223, ("loc_y", "rot", "scale")); hard(act, 229)
hang(f0, f1, squash=[(223, .13), (229, .05)])
fxkit.end_action(arm, act, f0)

# ================================================================== multi: three pumps, harder each time, then launch
f0, f1 = CLIPS["multi"]
act = fxkit.begin_action(arm, SID + "_multi")
rest(arm, BONES, f0)
car([(304, .9, -.01, 1.004, .975), (307, -3.0, .07, 1, 1.02), (310, .8, 0, 1.006, .96), (313, -5.2, .14, 1, 1.03),
     (316, 1.0, 0, 1.008, .95), (319, -7.0, .24, .998, 1.035), (322, 1.4, 0, 1.01, .94),
     (325, 2.2, -.04, 1.014, .915), (327, 2.3, -.045, 1.016, .91),
     (332, -12.0, .85, .992, 1.06), (335, -11.4, .8, 1, 1.0), (339, 2.6, 0, 1.02, .9), (342, -2.8, .06, .996, 1.02),
     (345, .4, 0, 1, .996), (348, 0, 0, 1, 1)])
for i, f in enumerate(range(323, 328)):              # charged to bursting, it trembles
    k1("body", f, x=.014 if i % 2 else -.014)
k1("body", 322, x=0); k1("body", 328, x=0)
for f in (310, 316, 322, 339):
    hard(act, f)
hard(act, 339, ("loc_y", "rot", "scale"))
hang(f0, f1, squash=[(310, .04), (316, .05), (322, .06), (339, .13)])
fxkit.end_action(arm, act, f0)


# ================================================================== effects
def onbody(name, coll, depth):
    ob = gp_object(coll, SID + name, depth=depth)
    ride(ob, arm, "body")
    return ob


def car_at(f, x, y):
    """Where icon point (x, y) on the car is at frame f (world x, z), as the clips move it."""
    sc.frame_set(f)
    pb = arm.pose.bones["body"]
    p = arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted() @ fxkit.vec(x, y)
    return p.x, p.z


def ellipse(cx, cz, rx, ry, n=96):
    return [(cx + rx * math.cos(2 * math.pi * i / n), cz + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


fxw = gp_object(FX, SID + "_fx", depth=-.8)           # stays where the frame is
fxc = onbody("_fx_on", FX, -.8)                       # rides the car
fxt = gp_object(FX, SID + "_fx_tyre", depth=-.8)      # rides the big wheel
ride(fxt, arm, "wheel_near")
w_white = gp_mat(fxw, "fx_white_line", WHITE); w_gold = gp_mat(fxw, "fx_gold_line", GOLD); w_or = gp_mat(fxw, "fx_orange_line", ORANGE)
w_spark = gp_mat(fxw, "fx_white_fill", WHITE, fill=WHITE); w_goldf = gp_mat(fxw, "fx_gold_fill", GOLD, fill=GOLD)
w_lime = gp_mat(fxw, "fx_lime_line", LIME); w_limef = gp_mat(fxw, "fx_lime_fill", LIME, fill=LIME)
c_spark = gp_mat(fxc, "fx_white_fill", WHITE, fill=WHITE); c_white = gp_mat(fxc, "fx_white_line", WHITE)
c_lime = gp_mat(fxc, "fx_lime_line", LIME)
t_spark = gp_mat(fxt, "fx_white_fill", WHITE, fill=WHITE)
world, oncar, ontyre = Board(), Board(), Board()
GROUND = (530, 716)          # under the middle of the car, on the ground (icon px)


def sparks(board, f0, n, x, z, seed, speed=(4.5, 8.5), ang=(100, 170), life=(6, 10), mats=(w_gold, w_white, w_or), g=30.0,
           width=.034):
    """Sparks scraped off the frame: hot streaks flung out and falling, each a short line along its own path that
    thins to nothing as it cools (a dimmed spark reads dirty)."""
    rnd = random.Random(seed)
    for i in range(n):
        a = math.radians(rnd.uniform(*ang))
        sp = rnd.uniform(*speed)
        vx, vz = math.cos(a) * sp, math.sin(a) * sp
        lf = rnd.randint(*life)
        st = f0 + rnd.randint(0, 2)
        mat = mats[i % len(mats)]
        for k in range(lf):
            t0, t1 = k / FPS, (k + 1.8) / FPS
            p0 = (x + vx * t0, z + vz * t0 - .5 * g * t0 * t0)
            p1 = (x + vx * t1, z + vz * t1 - .5 * g * t1 * t1)
            w = width * (1 - k / lf) ** 1.3 + .005
            board.add(st + k, lambda dr, p0=p0, p1=p1, w=w, mat=mat: stroke(dr, [p0, p1], w, mat=mat))


def flash(board, f0, x, z, r, mat, life=5, points=6, rot=.3):
    """A hot star where something hits: it blooms and is gone in a few frames."""
    for k in range(life):
        t = k / (life - 1)
        rr = r * math.sin(math.pi * min(1, .2 + t * .95))
        board.add(f0 + k, lambda dr, rr=rr, t=t: stroke(dr, star(x, z, rr + .02, rot + .5 * t, points=points, inner=.24), .004,
                                                      mat=mat, cyclic=True, fill=True, line=False))


def trails(board, f0, f1, pts, mat, scale=1.0):
    """Speed lines under the car while it shoots up: from where each point on its underside is now, down to where it
    was a few frames ago (world space: straight down the way it came), thinning as it slows."""
    for f in range(f0, f1 + 1):
        for j, (x, y) in enumerate(pts):
            ax, az = car_at(f, x, y)
            bx, bz = car_at(max(f - 3, f0 - 1), x, y)
            ln = math.hypot(ax - bx, az - bz)
            if ln < .12:
                continue
            board.add(f, lambda dr, ax=ax, az=az, bx=bx, bz=bz, ln=ln, j=j: stroke(
                dr, [(ax, az - .18), (ax + (bx - ax) * 1.6 * scale, az - .18 + (bz - az) * 1.6 * scale)], 0, mat=mat,
                radii=[.022 + .008 * min(1, ln), .004], opacities=[.95, .2]))


# idle: the chrome catches the light - a glint on the bumper, the hubcap twinkles
fxkit.sparkle(oncar, 30, 9, *px(300, 488), .36, c_spark)
fxkit.sparkle(ontyre, 52, 8, *px(560, 548), .3, t_spark, rot0=.5)

# land: impact ticks at the tyres
for k, f in enumerate(range(102, 108)):
    t = k / 5
    for (cx, cz) in (px(*TYRE), px(*FAR_TYRE)):
        for side in (-1, 1):
            world.add(f, lambda dr, cx=cx, cz=cz, sd=side, t=t: stroke(
                dr, [(cx + sd * (.6 + .9 * t), cz - .04), (cx + sd * (1.0 + 1.3 * t), cz + .06 + .06 * t)], .03 * (1 - t) + .008,
                mat=w_white))

# hit: hydraulic hiss as it squats, speed lines under it as the nose fires up, glints on the chrome at the top, the
# frame scraping sparks and a hot flash on the slam
for i, (hx, hy) in enumerate(((470, 530), (228, 606), (640, 560))):
    for k in range(8):
        t = k / 7
        cx, cz = px(hx, hy)
        r = .1 + .2 * math.sin(math.pi * min(1, t * 1.05)) ** .7
        oncar.add(203 + k + (i == 2), lambda dr, cx=cx, cz=cz, t=t, r=r, i=i: stroke(
            dr, fxkit.puff(cx + (-.45 if i < 2 else .4) * t, cz - .2 - .25 * t, r, seed=i + 3, bump=.12), .006,
            mat=c_spark, cyclic=True, fill=True, line=False))
trails(world, 208, 214, [(90, 616), (230, 640), (380, 650), (546, 676), (700, 690)], w_white)
fxkit.sparkle(oncar, 213, 10, *px(372, 396), .55, c_spark)            # headlights
fxkit.sparkle(oncar, 215, 9, *px(78, 498), .45, c_spark, rot0=.6)
fxkit.sparkle(oncar, 217, 8, *px(240, 520), .34, c_spark, rot0=.2)    # the grille
fxkit.sparkle(ontyre, 214, 9, *px(560, 548), .38, t_spark, rot0=.4)   # the hubcap
flash(world, 223, *px(*BUMPER_LOW), .7, w_goldf)
flash(world, 223, *px(*BUMPER_LOW), .4, w_spark, rot=.0)
sparks(world, 223, 26, *px(*BUMPER_LOW), seed=7)
sparks(world, 223, 12, *px(330, 652), seed=8, speed=(3.5, 6.5), ang=(95, 150))
sparks(world, 229, 10, *px(*BUMPER_LOW), seed=9, speed=(3, 5.5), width=.026)
flash(world, 229, *px(*BUMPER_LOW), .36, w_goldf, life=4)

# multi: the underglow charges with each pump (behind the car, bloomed), lightning arcs from the frame to the ground,
# and as it launches the glow goes off in rings across the ground
back = gp_object(FXB, SID + "_glow", depth=.4)
ride(back, arm, "body")
g_lime = gp_mat(back, "glow_lime", LIME); g_white = gp_mat(back, "glow_white", WHITE)
ground = gp_object(FXB, SID + "_ground", depth=.4)
gr_lime = gp_mat(ground, "glow_lime", LIME); gr_white = gp_mat(ground, "glow_white", WHITE)
gr_limef = gp_mat(ground, "glow_lime_fill", LIME, fill=LIME)
bb, gb = Board(), Board()
UNDER = [px(70, 604), px(200, 630), px(330, 634), px(470, 644), px(640, 654), px(800, 680), px(905, 672)]
under = fxkit.resample(UNDER, 60, closed=False)
f0, f1 = CLIPS["multi"]
for f in range(f0, f1 + 1):
    pulse = sum(math.exp(-((f - p) / 2.2) ** 2) * w for p, w in ((307, .55), (313, .8), (319, 1.05)))
    charge = smooth(303, 323, f) * (1 - smooth(328, 331, f))
    burst = math.exp(-max(0, f - 327) / 3.0) if f >= 327 else 0
    lv = .35 * charge + .6 * pulse + 1.4 * burst
    if lv < .03:
        continue

    def fn(dr, lv=lv):
        for r, a in ((.46, .08), (.33, .1), (.22, .13), (.13, .17)):
            stroke(dr, [(x, z - .1) for x, z in under], r * (.8 + .4 * min(1, lv)), opacity=min(1, a * lv * 1.7), mat=g_lime)
        stroke(dr, [(x, z - .07) for x, z in under], .04 * min(1.4, lv) + .012, opacity=min(1, .85 * lv), mat=g_white if lv > .8 else g_lime)
    bb.add(f, fn)
gx, gz = px(*GROUND)
for j, (mat, lag) in enumerate(((gr_lime, 0), (gr_white, 3), (gr_lime, 6))):
    for k in range(12):
        t = k / 11
        rx = 1.4 + 5.0 * (1 - (1 - t) ** 2)
        gb.add(327 + lag + k, lambda dr, rx=rx, t=t, mat=mat: stroke(dr, ellipse(gx, gz, rx, rx * .17), .1 * (1 - t) + .014,
                                                                     opacity=(1 - t) ** 1.1, mat=mat, cyclic=True))
for k in range(6):                                   # the flash under it as it fires
    t = k / 5
    gb.add(327 + k, lambda dr, t=t: stroke(dr, star(gx, gz + .25, 2.6 * math.sin(math.pi * min(1, .25 + t)), .1 + .3 * t, points=8, inner=.12),
                                           .004, opacity=1 - t * .5, mat=gr_limef, cyclic=True, fill=True, line=False))
bb.draw(gp_layer(back, "underglow"))
gb.draw(gp_layer(ground, "ground"))
rnd = random.Random(31)
for f in range(312, 327, 2):                          # arcs from the frame down to the ground, crackling
    for j in range(2 if f < 320 else 3):
        x = rnd.uniform(150, 760)
        a0 = car_at(f, x, 640 + (x - 150) * .05)
        a1 = (a0[0] + rnd.uniform(-.5, .5), px(x, 735)[1])
        world.add(f, lambda dr, a0=a0, a1=a1, f=f, j=j: stroke(dr, fxkit.zigzag(*a0, *a1, n=5, amp=.16, seed=f * 5 + j), .026,
                                                               mat=(w_lime, w_white)[j % 2]), hold=2)
for i, f in enumerate((307, 313, 319)):               # each pump crackles a spark off the rams
    fxkit.sparkle(oncar, f, 7, *px(470 - 120 * i, 610 + 6 * i), .3 + .07 * i, c_spark, rot0=.3 * i)
sparks(world, 327, 18, gx, gz + .1, seed=27, speed=(3, 6), ang=(-170, -10), life=(5, 8), mats=(w_lime, w_white), g=-8.0)
sparks(world, 339, 22, *px(*BUMPER_LOW), seed=17)
flash(world, 339, *px(*BUMPER_LOW), .6, w_goldf)
world.draw(gp_layer(fxw, "fx"))
oncar.draw(gp_layer(fxc, "fx"))
ontyre.draw(gp_layer(fxt, "fx"))

# ================================================================== road dust rolling out from under the tyres
# solid cartoon puffs (they swell and shrink away - a fade would leave grey smudges): the big ones roll out
# behind the car, low along the ground, small ones kick up in front of the tyres
dust_b = gp_object(ART, SID + "_dust_back", depth=.05)     # behind the car
dust_f = gp_object(ART, SID + "_dust", depth=-1.0)         # in front of every part
m_db = gp_mat(dust_b, "fx_dust", (.42, .4, .41, 1), fill=(.8, .77, .73, 1))
m_df = gp_mat(dust_f, "fx_dust", (.42, .4, .41, 1), fill=(.8, .77, .73, 1))
db, df = Board(), Board()
for base, life, big in ((102, 11, .62), (223, 13, 1.0), (229, 9, .55), (339, 12, .9), (310, 7, .35), (316, 7, .4), (322, 8, .45)):
    for (x, y), side, seed in ((TYRE, -1, 3), (TYRE, 1, 5), (FAR_TYRE, -1, 9), (FAR_TYRE, 1, 13), (REAR_TYRE, 1, 21)):
        if (x, y) == REAR_TYRE and big < .6:
            continue
        cx, cz = px(x, y)
        fxkit.dust(db, base + (side > 0), life, cx + side * .5, cz + .05, big * .75, m_db,
                   drift=(side * 2.2 * big, .25 * big), seed=seed + base)
        if big >= .55 and (x, y) != REAR_TYRE:
            fxkit.dust(df, base + 1, life - 3, cx + side * .4, cz - .12, big * .32, m_df,
                       drift=(side * 1.2 * big, .12), seed=seed + base + 50)
db.draw(gp_layer(dust_b, "dust"))
df.draw(gp_layer(dust_f, "dust"))

sc.frame_start, sc.frame_end = 1, max(b for a, b in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], "| saved", fxkit.save(SID))
