# L5 - the pair of dice - animated in Blender: four Actions on its rig (idle, land, hit, multi) laid one after
# another on the rig's NLA track, and its effects drawn frame by frame in Grease Pencil on the same timeline.
#   the rig     each die is two pieces on its own bone (its body, and its sticker border drawn behind both dice -
#               tools/blender/cuts/L5.py). Added here: a foot bone under each die at the corner it stands on. The
#               die's own bone turns it about its centre (a tumble); the foot bone carries it (a hop) and squashes it
#               on its corner (an impact). When a die rocks, the foot bone is shifted frame by frame so the corner it
#               stands on stays exactly where it is - the dice really rock on their corners.
#   idle        balanced on their corners they teeter, each to its own slow beat; a pip catches the light
#   land        both clack down on their corners a frame apart, squash, and rock to rest
#   hit         a crouch, then both leap and tumble a full turn the opposite way to each other, trailing motion arcs,
#               pips burst out between them at the top, and they land on their corners and rock to rest
#   multi       charged by the multiplier they rattle on their corners faster and harder, knocking together, their
#               pips heating white; then it lets go - they jump apart and slam down, a ring of light goes out
# Runs INSIDE Blender, after build_symbol_scene.py (tools/blender/run.py runs both in a background Blender).
import bpy, importlib, math, os, random, sys
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\blender"
sys.path.insert(0, HERE)
import fxkit
importlib.reload(fxkit)
from fxkit import key, rest, px, vec, smooth, gp_object, gp_mat, gp_layer, ride, stroke, star, ring, puff, Board, WHITE, GOLD

SID = "L5"
sc, arm, spec = fxkit.setup(SID)
FPS = sc.render.fps
RED = (1.0, 0.30, 0.10, 1)                  # the dice's own red, for their motion arcs
HOT = (1.0, 0.93, 0.62, 1)                  # white-hot, for the charged pips

DICE = {   # icon px: centre (its bone), the corner it stands on, its outer corners, its pips
    "top_die": dict(c=(304, 340), foot=(295, 609), side=-1,
                    corners=[(310, 72), (51, 219), (527, 166), (556, 393), (118, 475)],
                    pips=[(302, 121), (277, 175), (248, 237), (128, 328), (196, 465), (451, 279), (341, 347), (463, 351),
                          (353, 415), (474, 421), (367, 480)]),
    "low_die": dict(c=(700, 640), foot=(719, 903), side=1,
                    corners=[(651, 370), (433, 565), (876, 478), (959, 705), (487, 825)],
                    pips=[(605, 496), (513, 576), (644, 604), (548, 687), (814, 537), (735, 715), (841, 749), (732, 779),
                          (623, 805), (724, 842)]),
}
CONTACT = (536, 455)                         # where the two dice come closest

# ------------------------------------------------------------------ the rig: a foot bone under each die
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
for d, D in DICE.items():
    b = eb.get(d + "_foot") or eb.new(d + "_foot")
    b.head = vec(*D["foot"])
    b.tail = b.head + Vector((0, 0, .6))
    b.roll = 0
    eb[d + ".0"].use_connect = False
    eb[d + ".0"].parent = b
bpy.ops.object.mode_set(mode="OBJECT")
for pb in arm.pose.bones:
    pb.rotation_mode = "XYZ"
# both borders behind both dice: the cut's order has the lower die's border in front of the upper die
bpy.data.objects[SID + "_low_die_rim"].location.y = bpy.data.objects[SID + "_top_die_rim"].location.y - .05
BONES = [b for d in DICE for b in (d + "_foot", d + ".0")]

ART, FXB, FX = fxkit.layers(sc, SID)
fxkit.glow_compositor(sc, SID, back=dict(strength=.9, size=.5, gain=1.5), front=dict(strength=.8, size=.4, gain=1.5))
if arm.animation_data:
    arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)

CLIPS = {"idle": (1, 80), "land": (101, 126), "hit": (201, 252), "multi": (301, 348)}
arm["clips"] = {k: list(v) for k, v in CLIPS.items()}


# ------------------------------------------------------------------ keying helpers
def curve(act, bone, path, idx):
    for fc in fxkit.fcurves(act):
        if fc.data_path == f'pose.bones["{bone}"].{path}' and fc.array_index == idx:
            return fc
    return None


def comp(die, deg):
    """The foot bone's shift (units) that keeps the die's standing corner where it is while the die is turned
    deg degrees about its centre (whole turns ignored)."""
    D = DICE[die]
    fx, fy = (D["foot"][0] - D["c"][0]) / 100, (D["c"][1] - D["foot"][1]) / 100
    t = math.radians(deg - 360 * round(deg / 360))
    rx, ry = fx * math.cos(t) - fy * math.sin(t), fx * math.sin(t) + fy * math.cos(t)
    return fx - rx, fy - ry


def plant(act, die, f0, f1, air=(), extra=None):
    """Key the foot bone's shift frame by frame from the turn keyed on the die's own bone: on the ground the die
    turns about the corner it stands on (scaled with the foot's squash); in the air - air = [(up, down, height,
    drift)] - it flies a hop from where it took off to where it lands. extra(f) -> (dx, dy) adds a jolt."""
    rc = curve(act, die + ".0", "rotation_euler", 2)
    sxc, syc = curve(act, die + "_foot", "scale", 0), curve(act, die + "_foot", "scale", 1)
    ev = lambda fc, f, d: fc.evaluate(f) if fc else d
    xs, ys = [], []
    for f in range(f0, f1 + 1):
        th = math.degrees(ev(rc, f, 0))
        cx, cy = comp(die, th)
        x, y = ev(sxc, f, 1) * cx, ev(syc, f, 1) * cy
        for up, down, H, D in air:
            if up < f < down:
                u = (f - up) / (down - up)
                ax, ay = comp(die, math.degrees(ev(rc, up, 0)))
                bx, by = comp(die, math.degrees(ev(rc, down, 0)))
                x = ax + (bx - ax) * u + D * math.sin(math.pi * u)
                y = ay + (by - ay) * u + H * 4 * u * (1 - u)
        if extra:
            dx, dy = extra(f)
            x, y = x + dx, y + dy
        xs.append(x); ys.append(y)
    for i in sorted(set(fxkit.sparse(xs, .0015)) | set(fxkit.sparse(ys, .0015))):
        key(arm, die + "_foot", f0 + i, x=xs[i], y=ys[i])


def spin(act, bone, frames):
    """In the air a die turns at an even rate: linear between these keys."""
    for fc in fxkit.fcurves(act):
        if fc.data_path == f'pose.bones["{bone}"].rotation_euler':
            for kp in fc.keyframe_points:
                if any(abs(kp.co.x - f) < .5 for f in frames):
                    kp.interpolation = "LINEAR"
            fc.update()


def keys(bone, rows, ch="r"):
    for f, v in rows:
        key(arm, bone, f, **{ch: v})


def squash(bone, rows, hard_at=()):
    for f, sx, sy in rows:
        key(arm, bone, f, sx=sx, sy=sy)
    for f in hard_at:
        fxkit.hard(arm.animation_data.action, bone, "scale", 0, f)
        fxkit.hard(arm.animation_data.action, bone, "scale", 1, f)


# ================================================================== idle: balanced on their corners, they teeter
f0, f1 = CLIPS["idle"]
act = fxkit.begin_action(arm, SID + "_idle")
rest(arm, BONES, f0)
keys("top_die.0", [(21, -1.5), (41, .35), (61, 1.4), (81, 0)])
keys("low_die.0", [(11, 1.0), (31, -1.25), (51, .85), (71, -.45), (81, 0)])
for d in DICE:
    plant(act, d, f0, f1 + 1)
fxkit.make_cyclic(act)
fxkit.end_action(arm, act, f0)

# ================================================================== land: they clack down on their corners and rock
f0, f1 = CLIPS["land"]
act = fxkit.begin_action(arm, SID + "_land")
rest(arm, BONES, f0)
for d, lag in (("top_die", 0), ("low_die", 1)):
    squash(d + "_foot", [(f0 + lag, 1, 1), (103 + lag, 1.07, .9), (106 + lag, .985, 1.03), (110 + lag, 1, 1), (f1, 1, 1)],
           hard_at=(103 + lag,))
keys("top_die.0", [(103, 0), (106, -3.2), (110, 2.2), (114, -1.1), (118, .45), (122, -.12), (f1, 0)])
keys("low_die.0", [(104, 0), (107, 2.8), (111, -1.9), (115, .9), (119, -.35), (123, .1), (f1, 0)])
for d in DICE:
    plant(act, d, f0, f1)
fxkit.end_action(arm, act, f0)

# ================================================================== hit: crouch, leap, tumble, land on the corners
f0, f1 = CLIPS["hit"]
act = fxkit.begin_action(arm, SID + "_hit")
rest(arm, BONES, f0)
HOPS = {"top_die": (208, 225, 1.05, -.42), "low_die": (210, 227, .9, .42)}      # up, down, height, drift
for d, sgn, lag in (("top_die", 1, 0), ("low_die", -1, 2)):
    up, down = HOPS[d][:2]
    squash(d + "_foot", [(f0 + lag, 1, 1), (206 + lag, 1.08, .88), (up, .93, 1.1), (up + 3, 1, 1), (down, 1, 1),
                         (down + 1, 1.1, .86), (down + 5, .97, 1.04), (down + 9, 1, 1), (f1, 1, 1)], hard_at=(down + 1,))
    keys(d + ".0", [(f0 + lag, 0), (206 + lag, 3 * sgn), (up, 4 * sgn), ((up + down) / 2, 185 * sgn), (down, 366 * sgn),
                    (down + 4, 357.5 * sgn), (down + 8, 362.6 * sgn), (down + 12, 358.9 * sgn), (down + 16, 360.5 * sgn),
                    (down + 20, 359.85 * sgn), (f1, 360 * sgn)])
    spin(act, d + ".0", (up, (up + down) / 2))
    plant(act, d, f0, f1, air=[HOPS[d]])
fxkit.end_action(arm, act, f0)

# ================================================================== multi: rattled harder and harder, then let go
f0, f1 = CLIPS["multi"]
act = fxkit.begin_action(arm, SID + "_multi")
rest(arm, BONES, f0)
CHARGE, LET_GO = (303, 325), 327
JUMPS = {"top_die": (LET_GO, 333, .45, -.3), "low_die": (LET_GO + 1, 334, .4, .3)}
for d, sgn, lag in (("top_die", 1, 0), ("low_die", -1, 1)):
    rows = [(f0, 0)]
    for i, f in enumerate(range(CHARGE[0] + lag, CHARGE[1], 2)):        # the rattle: faster swings, growing
        a = 1.1 + 2.6 * (f - CHARGE[0]) / (CHARGE[1] - CHARGE[0])
        rows.append((f, a * sgn * (1 if i % 2 == 0 else -1)))
    up, down = JUMPS[d][:2]
    rows += [(up - 1, 0), (up + 3, 9 * sgn), (down, 4 * sgn), (down + 4, -3 * sgn), (down + 8, 1.4 * sgn),
             (down + 12, -.5 * sgn), (f1, 0)]
    keys(d + ".0", rows)
    squash(d + "_foot", [(f0, 1, 1), (CHARGE[0] + lag, 1, 1), (313 + lag, .98, 1.02), (319 + lag, 1.02, .98),
                         (up - 1, 1.07, .9), (up + 1, .94, 1.08), (up + 4, 1, 1), (down, 1, 1), (down + 1, 1.08, .88),
                         (down + 5, .98, 1.03), (down + 9, 1, 1), (f1, 1, 1)], hard_at=(down + 1,))

    def jolt(f, lag=lag):                                              # little hops off the corner as it rattles
        if CHARGE[0] <= f < CHARGE[1] and (f - lag) % 2 == 0:
            e = (f - CHARGE[0]) / (CHARGE[1] - CHARGE[0])
            return 0, .012 + .03 * e
        return 0, 0
    plant(act, d, f0, f1, air=[JUMPS[d]], extra=jolt)
fxkit.end_action(arm, act, f0)


# ================================================================== where things are, frame by frame (for effects)
def track(bone, pts, frames, sub=1):
    """World (x, z) of icon-px points riding a bone, at frames (and sub-steps between frames)."""
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

# ================================================================== effects: materials and boards
fx = gp_object(FX, SID + "_fx", depth=-.8)                     # stays where the frame is
on = {d: gp_object(FX, f"{SID}_fx_{d}", depth=-.8) for d in DICE}    # rides each die
for d, ob in on.items():
    ride(ob, arm, d + ".0")
back = gp_object(FXB, SID + "_fxb_glow", depth=.35)       # (never a part's name: gp_object replaces that object)
dust_ob = gp_object(ART, SID + "_fx_dust", depth=-1.0)            # on the art, in front of every piece

m = {}
m["white"] = gp_mat(fx, "fx_white_line", WHITE)
m["white_f"] = gp_mat(fx, "fx_white_fill", WHITE, fill=WHITE)
m["gold_f"] = gp_mat(fx, "fx_gold_fill", GOLD, fill=GOLD)
m["gold"] = gp_mat(fx, "fx_gold_line", GOLD)
m["red"] = gp_mat(fx, "fx_red_line", RED)
m["red_f"] = gp_mat(fx, "fx_red_fill", RED, fill=RED)
om = {d: dict(white_f=gp_mat(ob, "fx_white_fill", WHITE, fill=WHITE), hot_f=gp_mat(ob, "fx_hot_fill", HOT, fill=HOT),
              gold_f=gp_mat(ob, "fx_gold_fill", GOLD, fill=GOLD), gold=gp_mat(ob, "fx_gold_line", GOLD))
      for d, ob in on.items()}
bm = dict(white=gp_mat(back, "glow_white", WHITE), gold=gp_mat(back, "glow_gold", GOLD),
          gold_f=gp_mat(back, "glow_gold_fill", GOLD, fill=GOLD), red=gp_mat(back, "glow_red", RED))
m_dust = gp_mat(dust_ob, "fx_dust", (.62, .58, .6, 1), fill=(.96, .95, .97, 1))
world, behind, dust = Board(), Board(), Board()
riding = {d: Board() for d in DICE}


def ticks(board, f0, x, z, mats, a0=20, a1=160, n=5, r0=.22, r1=.8, life=6, w=.035, seed=0):
    """Impact ticks: short strokes thrown out round a point, flying out and thinning to nothing."""
    rnd = random.Random(seed)
    angs = [math.radians(a0 + (a1 - a0) * (i + .5) / n + rnd.uniform(-7, 7)) for i in range(n)]
    for k in range(life):
        t = k / max(1, life - 1)
        for i, a in enumerate(angs):
            ra = r0 + (r1 - r0) * t ** .7
            rb = ra + .3 * (1 - t) + .04
            board.add(f0 + k, lambda dr, a=a, ra=ra, rb=rb, t=t, i=i: stroke(
                dr, [(x + math.cos(a) * ra, z + math.sin(a) * ra), (x + math.cos(a) * rb, z + math.sin(a) * rb)],
                w * (1 - t) ** .8 + .006, mat=mats[i % len(mats)]))


def ground_ring(board, f0, x, z, mat, r0=.3, r1=1.5, life=8, w=.05, flat=.28):
    """A flat ring of shock rolling out along the ground from a landing corner, thinning as it goes."""
    for k in range(life):
        t = k / (life - 1)
        r = r0 + (r1 - r0) * (1 - (1 - t) ** 2)
        pts = [(x + math.cos(a) * r, z + math.sin(a) * r * flat) for a in (2 * math.pi * i / 48 for i in range(48))]
        board.add(f0 + k, lambda dr, pts=pts, t=t: stroke(dr, pts, w * (1 - t) + .008, mat=mat, cyclic=True))


def rings_out(board, f0, cx, cz, r0, r1, mats, life=11, lag=3, width=.12):
    """Rings of light rolling outward one after another, each at full strength, thinning to nothing (a ring that
    fades to a low opacity reads as a dirty brown line on the dark board)."""
    for j, mat in enumerate(mats):
        for k in range(life):
            t = k / (life - 1)
            r = r0 + (r1 - r0) * (1 - (1 - t) ** 1.6)
            w = width * (1 - t) ** 1.3
            if w > .004:
                board.add(f0 + lag * j + k, lambda dr, r=r, w=w, mat=mat, f=f0 + k: stroke(
                    dr, ring(cx, cz, r, n=96, wobble=.02, seed=f), w, mat=mat, cyclic=True))


def puffs(f0, x, z, scale=.55, life=11, seed=1):
    """Cartoon dust rolling out both ways from a corner that hits."""
    for side, sd in ((-1, seed), (1, seed + 4)):
        fxkit.dust(dust, f0, life, x + side * .25, z + .05, scale, m_dust, drift=(side * 1.0, .25), seed=sd)


def trails(paths, f0, f1, mats=("red", "white"), w=.075, span=1.5, samples=7):
    """Motion arcs: where each outer corner has just been, a stroke tapering away behind it."""
    for f in range(f0, f1 + 1):
        times = [f - span + span * j / (samples - 1) for j in range(samples)]
        for ci in range(len(paths[f])):
            pts = []
            for t in times:
                t0 = math.floor(t * 4) / 4
                if t0 in paths:
                    pts.append(paths[t0][ci])
            if len(pts) < 3 or math.dist(pts[0], pts[-1]) < .35:
                continue
            n = len(pts)
            radii = [w * (j / (n - 1)) ** 1.4 for j in range(n)]
            world.add(f, lambda dr, pts=pts, radii=radii: stroke(dr, pts, 0, radii=radii, mat=m[mats[0]]))
            world.add(f, lambda dr, pts=pts, radii=[r * .42 for r in radii]: stroke(dr, pts, 0, radii=radii, mat=m[mats[1]]))


# ---- idle: a pip on each die catches the light
fxkit.sparkle(riding["top_die"], 14, 10, *px(318, 108), .3, om["top_die"]["white_f"], rot0=.3)
fxkit.sparkle(riding["low_die"], 50, 10, *px(828, 522), .26, om["low_die"]["white_f"], rot0=.9)

# ---- land: the corners clack down
for d, f in (("top_die", 103), ("low_die", 104)):
    x, z = px(*DICE[d]["foot"])
    ticks(world, f, x, z - .02, (m["white"], m["gold"], m["white"]), seed=f)
    puffs(f, x, z, scale=.42, life=10, seed=f)

# ---- hit: dust off the corners as they leap, motion arcs through the tumble, pips burst out at the top,
#      corners clack down with a ring of shock along the ground, sparkles after
for d, (up, down, H, D) in HOPS.items():
    x, z = px(*DICE[d]["foot"])
    puffs(up - 1, x, z, scale=.38, life=9, seed=up)
    for k, f in enumerate(range(up + 1, up + 6)):                     # speed lines under the rising die
        for j, dx in enumerate((-.35, 0, .35)):
            xx = x + D * .3 + dx
            world.add(f, lambda dr, xx=xx, k=k, z=z: stroke(dr, [(xx, z - .2 + .25 * k), (xx, z - 1.0 + .25 * k)],
                                                             .022 * (1 - k / 5) + .006, mat=m["white"]))
    paths = track(d + ".0", DICE[d]["corners"], range(up - 1, down + 1), sub=4)
    trails(paths, up + 2, down - 1)
    fx_, fz_ = px(*DICE[d]["foot"])
    ticks(world, down + 1, fx_, fz_ - .02, (m["white"], m["gold"], m["red"]), n=6, r1=.95, seed=down)
    ground_ring(world, down + 1, fx_, fz_ - .05, m["white"])
    puffs(down + 1, fx_, fz_, scale=.55, life=12, seed=down + 3)
APEX = (216, 218)
ca = track("top_die.0", [DICE["top_die"]["c"]], [APEX[0]])[APEX[0]][0]
cb = track("low_die.0", [DICE["low_die"]["c"]], [APEX[0]])[APEX[0]][0]
mid = ((ca[0] + cb[0]) / 2, (ca[1] + cb[1]) / 2 + .2)                 # between the dice at the top of the leap
rnd = random.Random(7)
for i in range(16):                                                    # pips burst out from between the dice
    a = 2 * math.pi * i / 16 + rnd.uniform(-.15, .15)
    sp = rnd.uniform(2.6, 4.2)
    r0 = rnd.uniform(.08, .13)
    for k in range(12):
        t = k / 11
        x = mid[0] + math.cos(a) * sp * (1 - (1 - t) ** 2)
        z = mid[1] + math.sin(a) * sp * (1 - (1 - t) ** 2) - .5 * t * t
        r = r0 * (1 - t ** 2) + .01
        world.add(APEX[0] + k, lambda dr, x=x, z=z, r=r, i=i: stroke(dr, ring(x, z, r, n=14), .004,
                                                                 mat=m["white_f"] if i % 4 else m["gold_f"], cyclic=True,
                                                                 fill=True, line=False))
fxkit.sparkle(world, APEX[0] - 1, 9, mid[0], mid[1], .9, m["gold_f"], rot0=.2, spin=.4)
rings_out(behind, APEX[0], mid[0], mid[1], 1.0, 4.2, (bm["gold"], bm["white"]), life=10, lag=3, width=.1)
for i in range(7):
    fxkit.sparkle(world, 229 + rnd.randint(0, 14), rnd.randint(7, 10), rnd.uniform(-4.6, 4.6), rnd.uniform(-4.2, 4.8),
                  rnd.uniform(.22, .42), m["white_f"] if i % 3 else m["gold_f"], rot0=rnd.uniform(0, 1))

# ---- multi: the pips charge up gold, sparks are pulled in, they knock together; then a ring of light and a
#      spray of streaks as it lets go, and the pips flash white and go out
for d, D in DICE.items():
    rb = riding[d]
    for f in range(CHARGE[0], LET_GO + 7):
        if f < LET_GO:
            e = smooth(CHARGE[0], CHARGE[1] - 4, f)
            r = .25 * (.35 + .75 * e) * (1 + .1 * math.sin(f * 1.9))      # each pip fills with gold, throbbing
            mat_k = "gold_f"
        else:
            t = (f - LET_GO) / 6
            r = .25 * (1.3 - 1.3 * t * t)                                  # a white flash, shrinking away
            mat_k = "white_f"
        if r < .02:
            continue
        for (x, y) in D["pips"]:
            cx, cz = px(x, y)
            rb.add(f, lambda dr, cx=cx, cz=cz, r=r, d=d, mat_k=mat_k: stroke(dr, ring(cx, cz, r, n=16), .004,
                                                                             mat=om[d][mat_k], cyclic=True, fill=True,
                                                                             line=False))
    cx, cz = px(*D["c"])
    rnd = random.Random(11 if d == "top_die" else 23)
    for i in range(14):                                                 # sparks pulled into the die
        fs = CHARGE[0] + int(i * (CHARGE[1] - CHARGE[0] - 6) / 14)
        a = rnd.uniform(0, 2 * math.pi)
        for k in range(7):
            t = k / 6
            ra, rb_ = 3.5 - 1.6 * t, 3.5 - 1.6 * t + .5 * (1 - t) + .1      # (they start inside the frame)
            world.add(fs + k, lambda dr, a=a, ra=ra, rb=rb_, t=t, i=i, cx=cx, cz=cz: stroke(
                dr, [(cx + math.cos(a) * ra, cz + math.sin(a) * ra), (cx + math.cos(a) * rb, cz + math.sin(a) * rb)],
                .03 * (1 - t * .6), mat=m["gold"] if i % 2 else m["white"]))
    for k, f in enumerate(range(CHARGE[0] + 4, CHARGE[1], 2)):          # rattle marks beside it
        side = D["side"] * (1 if k % 2 else -1)
        ex = cx + side * 2.7
        for j in range(3):
            zz = cz + .5 - .5 * j
            world.add(f, lambda dr, ex=ex, zz=zz, j=j, side=side: stroke(
                dr, [(ex, zz + .18), (ex + side * .12, zz), (ex, zz - .18)], .024, mat=m["white"]), hold=2)
cx, cz = px(*CONTACT)
for f in range(CHARGE[0] + 3, CHARGE[1], 4):                             # they knock together
    ticks(world, f, cx, cz, (m["white"], m["gold"]), a0=-20, a1=200, n=6, r0=.12, r1=.55, life=4, w=.026, seed=f)
mx, mz = px(500, 520)
rings_out(behind, LET_GO, mx, mz, 1.6, 6.0, (bm["gold"], bm["white"], bm["gold"]), life=11, lag=3, width=.13)
fxkit.streaks(world, LET_GO, 9, mx, mz, 3.4, 6.2, (m["white"], m["gold"]), n=16, rot=.1)
for d, (up, down, H, D) in JUMPS.items():
    x, z = px(*DICE[d]["foot"])
    ticks(world, down + 1, x, z - .02, (m["white"], m["gold"]), n=5, seed=down + 50)
    puffs(down + 1, x, z, scale=.4, life=10, seed=down + 9)
rnd = random.Random(31)
for i in range(6):
    fxkit.sparkle(world, LET_GO + 4 + rnd.randint(0, 12), rnd.randint(7, 9), rnd.uniform(-4.5, 4.5), rnd.uniform(-4, 4.8),
                  rnd.uniform(.2, .36), m["white_f"] if i % 2 else m["gold_f"], rot0=rnd.uniform(0, 1))

world.draw(gp_layer(fx, "fx"))
behind.draw(gp_layer(back, "burst"))
dust.draw(gp_layer(dust_ob, "dust"))
for d, b in riding.items():
    b.draw(gp_layer(on[d], "fx"))

sc.frame_start, sc.frame_end = 1, max(b for a, b in CLIPS.values())
sc.frame_set(1)
print(SID, "animated:", [s.name for s in arm.animation_data.nla_tracks["clips"].strips], "| saved", fxkit.save(SID))
