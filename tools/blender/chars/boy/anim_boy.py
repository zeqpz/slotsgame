# SMUKIEZ (the boy) - every clip animated in Blender: one Action per clip on the rig's NLA track "clips", laid one
# after another on the timeline; faces swapped by keyed visibility; follow-through worked out in Blender from how
# the rig really moves (fxkit.secondary); the legs and arms reach their feet / hands by a two-bone solve keyed as
# plain turns. Runs INSIDE Blender after build_boy.py (tools/blender/chars/boy/run.py).
#
#   layers    acting keys (root, hips, torso, chest, neck, head, beanie, grip, hands, bills, feet - beats keyed by
#             hand, Bezier-eased) -> the leg guard (body: drops the hips where a leg would have to stretch past its
#             drawn length, so a knee never locks and a shin never parts from its shoe) -> the limbs (thigh / shin
#             to the foot, upper arm / forearm to the hand) -> the springs (head_fx: the big head's follow-through;
#             cap.0/1: the beanie's crown and slouching tip on it; billfx_k.0/1: each bill's base and tip flapping,
#             each on its own springs so they move apart)
#   rest      every one-shot starts and ends on the rest pose (the idle's first frame); the idle passes through it
#             on every beat (cues, measured in run.py's meta step)
#
#   idle         a street bop at 112 bpm: six 16-frame beats, a knee dip on each with the weight swaying side to
#                side (the off heel lifting), a nod into each dip; beat 3 a cocky look up, beat 5 a riffle of the
#                fan, beat 6 a shoulder roll. Through the rest pose at the top of every beat
#   anticipation leans in, clutching the money (the bills shiver), peering at the reels, the right toe tapping twice
#   win          crouch, spring up with the money thrust high and the fan spread, heels kicked up; lands heavy, bounces,
#                a shoulder shimmy
#   big_win      a little hop, a deep wind-up, a big jump: at the top he flicks five bills off the fan - they fly up
#                and flutter down out of the frame - lands hard, waves the fan to the beat
#   lose         a breath in, then it all sags: knees, shoulders, head; the fan closes; a sigh; he shakes it off
#   cash_show    a little wind-up, then presents the money up and out, the fan opened wide, chin up; taps his toe
#   cash_count   looks down at the money and thumbs through it, a bill at a time (six), a nod on each, a satisfied
#                snap of the stack at the end
#   enter        pops up from below the frame, knees tucked, lands into his stance
#   exit         a dip, a hop, and he drops out of the frame (ends fully hidden)
import bpy, json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, os.path.join(ROOT, "tools", "blender"))
import fxkit                    # noqa: E402
fxkit.ICON[0], fxkit.ICON[1] = 1024, 1536

SID = "BOY"
sc = bpy.data.scenes[SID]
arm = bpy.data.objects[SID + "_rig"]
spec = json.load(open(os.path.join(ROOT, "art", "blender", "chars", "boy", "parts", "parts.json")))
FACES = spec["faces"]
NB = 6
THROWN = 5
P = .01                          # one master px in units
FAN_ANGS = spec["fan"]["angles"]  # front .. back (deg)

ACTING = {"root": "xys", "hips": "xyr", "torso": "r", "chest": "r", "neck": "r", "head": "ryS", "beanie": "rS",
          "grip": "xyr", "hand_l": "r", "hand_r": "r", "foot_l": "xyr", "foot_r": "xyr"}
for _k in range(NB):
    ACTING[f"bill_{_k}"] = "r"
LIMBS = [("thigh_l", "shin_l", "foot_l", "body"), ("thigh_r", "shin_r", "foot_r", "body"),
         ("arm_l_upper", "arm_l_fore", "hand_l", "chest"), ("arm_r_upper", "arm_r_fore", "hand_r", "chest")]

CLIP_LIST = [  # name, frames, loop
    ("idle", 140, True), ("anticipation", 36, False), ("win", 72, False), ("big_win", 96, False),
    ("lose", 66, False), ("cash_show", 78, False), ("cash_count", 192, False), ("enter", 36, False),
    ("exit", 21, False)]


class Clip:
    f0 = 1
    n = 1
    loop = False
    act = None


C = Clip()


# ================================================================== keying (local frames, master px, degrees)
def k(f, bone, x=None, y=None, r=None, s=None, sx=None, sy=None):
    fxkit.key(arm, bone, C.f0 + f, x=None if x is None else x * P, y=None if y is None else y * P, r=r, s=s, sx=sx, sy=sy)


def pose(f, **bones):
    """key several bones at local frame f: pose(8, hips=dict(y=-6), head=dict(r=-2))"""
    for b, ch in bones.items():
        k(f, b, **ch)


def hard(f, bone, path, index):
    fxkit.hard(C.act, bone, path, index, C.f0 + f)


def series(bone, vals, channel="r", scale=1.0, tol=None):
    """key a per-frame series (local frame 0 on) on every frame - solved and simulated motion is baked like a
    simulation, so the rendered frames carry it exactly (x / y in master px, r in degrees, sx / sy factors)"""
    pb = arm.pose.bones[bone]
    v = [float(a) * scale for a in vals]
    if C.loop:
        v = v + [v[0]]
    for i, a in enumerate(v):
        if channel in ("x", "y"):
            setattr(pb.location, channel, a * P)
            pb.keyframe_insert("location", index=0 if channel == "x" else 1, frame=C.f0 + i, group=bone)
        elif channel == "r":
            pb.rotation_euler.z = math.radians(a)
            pb.keyframe_insert("rotation_euler", index=2, frame=C.f0 + i, group=bone)
        else:
            setattr(pb.scale, channel[1], a)
            pb.keyframe_insert("scale", index=0 if channel == "sx" else 1, frame=C.f0 + i, group=bone)


def rest_all(f):
    for b, chans in ACTING.items():
        kw = {}
        if "x" in chans: kw["x"] = 0
        if "y" in chans: kw["y"] = 0
        if "r" in chans: kw["r"] = 0
        if "s" in chans or "S" in chans: kw["sx"] = 1; kw["sy"] = 1
        k(f, b, **kw)


def take(f, amp=1.0):
    """a quick squash-stretch of the big head from the chin as a new face pops in at f"""
    for df, sx, sy in ((0, 1, 1), (2, 1 + .035 * amp, 1 - .05 * amp), (5, 1 - .015 * amp, 1 + .025 * amp), (8, 1, 1)):
        if 0 <= f + df < C.n:
            k(f + df, "head", sx=sx, sy=sy)


def foot_pivot(side, f, deg, pivot, lift=0.0, dx=0.0):
    """turn a foot by deg about a point of its shoe (heel or toe ball, master px) - the ankle bone moves round it"""
    ank = (338, 1278) if side == "l" else (585, 1300)
    a = math.radians(deg)
    # screen y down: turn counter-clockwise on screen
    vx, vy = ank[0] - pivot[0], ank[1] - pivot[1]
    nx = pivot[0] + vx * math.cos(a) + vy * math.sin(a)
    ny = pivot[1] - vx * math.sin(a) + vy * math.cos(a)
    k(f, "foot_" + side, x=nx - ank[0] + dx, y=-(ny - ank[1]) + lift, r=deg)


HEEL_R, BALL_R = (500, 1446), (742, 1446)          # the right shoe in profile (toe to the right)
HEEL_L, BALL_L = (300, 1452), (205, 1440)          # the left shoe, seen from the front-left


def fan(f, spread=0.0, close=0.0, extra=None):
    """the fan: spread > 0 opens it wider (back bills further back), close > 0 folds them onto the front bill"""
    for b in range(NB):
        ang = FAN_ANGS[NB - 1 - b]                  # this bill's angle in the fan (front 0 .. back 30)
        r = (2.5 - b) * 2.6 * spread - ang * close
        if extra:
            r += extra[b]
        k(f, f"bill_{b}", r=r)


# ================================================================== the clips
def idle():
    D = [5.5, 4.5, 2.5, 5.5, 3.5, 4.0]              # each beat's knee dip (px)
    X = 4.0                                         # the sway (px)
    for b in range(6):
        s = 16 * b
        side = -1 if b % 2 == 0 else 1              # even beats lean onto the left leg
        pose(s, hips=dict(x=0, y=0, r=0), torso=dict(r=0), chest=dict(r=0), head=dict(r=0, y=0), grip=dict(x=0, y=0, r=0))
        k(s + 5, "hips", y=-D[b])
        k(s + 8, "hips", x=side * X, r=-side * .7)
        k(s + 9, "torso", r=side * .55)
        k(s + 10, "chest", r=side * .35 * (2.2 if b == 5 else 1))
        if b == 2:                                  # a cocky look up and back
            k(s + 4, "head", r=1.2, y=0)
            k(s + 9, "head", r=2.6, y=1.0)
        else:
            k(s + 7, "head", r=-1.7 * D[b] / 5, y=-2.2 * D[b] / 5)
        k(s + 7, "grip", y=-2.2 * D[b] / 5, r=side * .8)
        if b == 5:                                  # a shoulder roll
            k(s + 5, "chest", r=-1.3)
            k(s + 11, "chest", r=1.0)
            k(s + 8, "grip", x=-2, y=1.5)
        # the off heel lifts as the weight goes over the other leg
        if side < 0:
            foot_pivot("r", s, 0, BALL_R)
            foot_pivot("r", s + 8, -2.2, BALL_R)
            foot_pivot("r", s + 16, 0, BALL_R)
        else:
            foot_pivot("l", s, 0, BALL_L)
            foot_pivot("l", s + 8, 1.4, BALL_L, lift=.8)
            foot_pivot("l", s + 16, 0, BALL_L)
    # beat 5: a riffle of the fan (back bills open, then the front ones, then it settles)
    s = 64
    fan(s, 0)
    fan(s + 6, extra=[3.0, 2.2, 1.4, .6, 0, 0])
    fan(s + 10, extra=[1.0, 1.4, 1.6, 1.2, .5, -.8])
    fan(s + 16, 0)
    pose(96, hips=dict(x=0, y=0, r=0), torso=dict(r=0), chest=dict(r=0), head=dict(r=0, y=0), grip=dict(x=0, y=0, r=0))
    # the chill (keyed 96-140, ~2 s on screen): he stands easy at the rest pose and just breathes - two slow
    # breaths (shoulders and money lift a touch, the head rides up), the second with a hair of weight onto the
    # left leg - with a beat of stillness at rest before, between and after them (the cut points)
    CALM = dict(hips=dict(x=0, y=0, r=0), torso=dict(r=0), chest=dict(r=0), head=dict(r=0, y=0),
                grip=dict(x=0, y=0, r=0))
    pose(101, **CALM)
    pose(108, chest=dict(r=.25), head=dict(y=1.3, r=-.3), grip=dict(y=1.8), hips=dict(y=.6))
    pose(115, **CALM)
    pose(120, **CALM)
    pose(127, chest=dict(r=-.2), head=dict(y=1.2, r=.35), grip=dict(y=1.6, x=-.6), hips=dict(y=.5, x=-1.4))
    pose(134, **CALM)


def anticipation():
    pose(7, hips=dict(x=-5, y=-10), torso=dict(r=-2.5), chest=dict(r=-1), head=dict(r=1.8, y=-2),
         grip=dict(x=-8, y=-6, r=4))
    pose(13, head=dict(r=-3.2, y=-3), chest=dict(r=-1.6))
    pose(16, hips=dict(x=3, y=-9))
    pose(21, head=dict(r=-2.4, y=-3), torso=dict(r=-2.2), grip=dict(x=-7, y=-5, r=3))
    pose(24, hips=dict(x=-2, y=-8))
    pose(29, hips=dict(x=0, y=-1.5), torso=dict(r=.4), chest=dict(r=.3), head=dict(r=.6, y=0),
         grip=dict(x=1, y=1, r=-.5))
    take(25, .8)
    # the money shivers in his grip
    for b in range(NB):
        env = [fxkit.smooth(4, 8, f) * (1 - fxkit.smooth(20, 26, f)) for f in range(36)]
        series(f"bill_{b}", [e * (.55 + .12 * b) * math.sin(2 * math.pi * f / 3.4 + b * .7) for f, e in enumerate(env)], tol=.05)
    # two nervous taps of the right toe (heel planted)
    for f, a in ((5, 0), (8, 9), (11, 0), (15, 0), (18, 10), (21, 0)):
        foot_pivot("r", f, a, HEEL_R)
    for f in (11, 21):
        hard(f, "foot_r", "rotation_euler", 2)


def win():
    # crouch
    pose(9, hips=dict(y=-20, x=-2), torso=dict(r=-3), chest=dict(r=-1), head=dict(r=-2.5, y=-3),
         grip=dict(y=-12, x=-4, r=-2))
    k(12, "hips", y=-21)
    # spring up: the whole figure leaves the ground (root), knees tuck (feet up), the money high
    pose(13, root=dict(y=0))
    pose(15, hips=dict(y=3, x=0), torso=dict(r=2), head=dict(r=4, y=1))
    pose(22, root=dict(y=78), grip=dict(y=58, x=2, r=10), head=dict(r=6))
    pose(25, root=dict(y=82), hips=dict(y=-6))
    pose(31, root=dict(y=0))
    hard(31, "root", "location", 1)
    for side, d, dx, rr in (("l", 0, -7, -9), ("r", 1, 3, 7)):
        k(15 + d, "foot_" + side, x=0, y=0, r=0)
        k(23 + d, "foot_" + side, x=dx, y=24 - 6 * d, r=rr)
        k(29, "foot_" + side, x=0, y=1, r=0)
        k(30, "foot_" + side, x=0, y=0, r=0)
    # land heavy, bounce, shimmy
    pose(31, hips=dict(y=-3), grip=dict(y=30, r=7))
    pose(33, hips=dict(y=-22, x=1), torso=dict(r=-3), head=dict(r=-4, y=-6), grip=dict(y=10, r=3))
    pose(39, hips=dict(y=0), torso=dict(r=1.5), head=dict(r=2, y=0), grip=dict(y=22, r=6))
    pose(45, hips=dict(y=-7, x=-4), chest=dict(r=2.5), head=dict(r=-1.5), grip=dict(y=12, r=-3))
    pose(51, hips=dict(y=-1, x=3), chest=dict(r=-2.5), head=dict(r=1), grip=dict(y=15, r=4))
    pose(57, hips=dict(y=-5, x=-2), chest=dict(r=1.5), head=dict(r=-1), torso=dict(r=-.5), grip=dict(y=8, r=-1))
    pose(64, hips=dict(y=-1, x=0), chest=dict(r=-.4), head=dict(r=.4, y=0), torso=dict(r=0), grip=dict(y=2, r=0))
    take(61, .7)
    # the fan opens on the way up
    fan(10, 0)
    fan(22, 1.0)
    fan(42, 1.0)
    fan(56, .5)


def big_win():
    # a little hop
    pose(6, hips=dict(y=-12), torso=dict(r=-2), head=dict(r=-2, y=-2), grip=dict(y=-6))
    pose(9, root=dict(y=0), hips=dict(y=1))
    pose(13, root=dict(y=30), head=dict(r=3, y=1), grip=dict(y=12, r=3))
    pose(18, root=dict(y=0))
    hard(18, "root", "location", 1)
    for side in ("l", "r"):
        k(9, "foot_" + side, y=0, x=0, r=0)
        k(13, "foot_" + side, y=7, x=-3 if side == "l" else 3, r=-3 if side == "l" else 3)
        k(17, "foot_" + side, y=0, x=0, r=0)
    pose(20, hips=dict(y=-12), head=dict(r=-2, y=-4), grip=dict(y=0, r=0))
    # the deep wind-up
    pose(24, hips=dict(y=-6), torso=dict(r=0), head=dict(r=0, y=0))
    pose(31, hips=dict(y=-27, x=-3), torso=dict(r=-4), chest=dict(r=-1.5), head=dict(r=-3, y=-4),
         grip=dict(y=-18, x=-6, r=-4))
    # the big jump: the money up high, five bills flicked off the top
    pose(33, root=dict(y=0), hips=dict(y=4, x=0), torso=dict(r=3), chest=dict(r=1.5), head=dict(r=6, y=2))
    pose(40, root=dict(y=140), grip=dict(y=66, x=4, r=12), head=dict(r=8))
    pose(44, root=dict(y=150), grip=dict(y=74, r=15), hips=dict(y=-6))
    pose(48, grip=dict(y=44, r=7), head=dict(r=5))
    pose(52, root=dict(y=0), hips=dict(y=-3), grip=dict(y=26, r=4))
    hard(52, "root", "location", 1)
    for side, d, dx, rr in (("l", 0, -10, -9), ("r", 1, 9, 8)):
        k(34 + d, "foot_" + side, x=0, y=0, r=0)
        k(42 + d, "foot_" + side, x=dx, y=34 - 6 * d, r=rr)
        k(50, "foot_" + side, x=0, y=1.5, r=0)
        k(51, "foot_" + side, x=0, y=0, r=0)
    # lands hard, waves the fan to the beat
    pose(54, hips=dict(y=-26, x=2), torso=dict(r=-3.5), chest=dict(r=-1), head=dict(r=-5, y=-7), grip=dict(y=6, r=0))
    pose(60, hips=dict(y=1, x=0), torso=dict(r=2), chest=dict(r=1), head=dict(r=3, y=0), grip=dict(y=26, r=-9))
    pose(66, hips=dict(y=-8, x=-4), chest=dict(r=2.5), head=dict(r=-1.5), grip=dict(y=18, r=9))
    pose(72, hips=dict(y=-1, x=3), chest=dict(r=-2.5), head=dict(r=1.5), grip=dict(y=20, r=-6))
    pose(78, hips=dict(y=-6, x=-2), chest=dict(r=1.5), head=dict(r=-1), torso=dict(r=-.5), grip=dict(y=10, r=4))
    pose(86, hips=dict(y=-1, x=0), chest=dict(r=-.4), head=dict(r=.4, y=0), torso=dict(r=0), grip=dict(y=2, r=0))
    take(85, .7)
    fan(8, .4)
    fan(31, .2)
    fan(40, 1.5)
    fan(62, 1.3)
    fan(80, .5)
    take(1, 1.0)


def lose():
    pose(5, chest=dict(r=1.2), head=dict(r=2, y=1.5), grip=dict(y=3))
    pose(22, hips=dict(y=-17, x=-4), torso=dict(r=-2.5), chest=dict(r=-2), neck=dict(r=-2),
         head=dict(r=-7, y=-8), grip=dict(y=-20, x=-3, r=-7))
    pose(30, hips=dict(y=-15), head=dict(r=-6, y=-7))
    pose(36, hips=dict(y=-19, x=-5), head=dict(r=-7.5, y=-9), grip=dict(y=-22, r=-8))      # the sigh
    pose(43, hips=dict(y=-16, x=-4), head=dict(r=-6.5, y=-8), torso=dict(r=-2.2), chest=dict(r=-1.8),
         neck=dict(r=-1.8), grip=dict(y=-19, x=-3, r=-7))
    # shakes it off
    pose(50, hips=dict(y=-3, x=1), torso=dict(r=.6), chest=dict(r=.4), neck=dict(r=0), head=dict(r=1.5, y=0),
         grip=dict(y=2, x=0, r=1))
    pose(57, hips=dict(y=-2, x=0), torso=dict(r=-.3), chest=dict(r=0), head=dict(r=-.6), grip=dict(y=0, r=0))
    take(54, .6)
    fan(5, 0)
    fan(24, close=.55)
    fan(43, close=.5)
    fan(54, 0)
    # a scuff of the right foot
    k(18, "foot_r", x=0, y=0, r=0)
    k(21, "foot_r", x=3, y=5, r=-3)
    k(25, "foot_r", x=6, y=0, r=0)
    hard(25, "foot_r", "location", 1)
    k(46, "foot_r", x=6, y=0, r=0)
    k(49, "foot_r", x=3, y=4, r=2)
    k(52, "foot_r", x=0, y=0, r=0)
    hard(52, "foot_r", "location", 1)


# rest passes (keyed local frames) inside the one-shots: the game cuts only at frames at the rest pose, so the idle
# breaks come back to it every ~1.2 s on screen (body, arms and money, head exactly at rest; the springs pinned)
REST_PASS = {"cash_show": [26, 27, 52, 53], "cash_count": [27, 28, 55, 56, 83, 84, 111, 112, 139, 140, 167, 168]}


def rest_pass(f):
    """every acting bone at rest on frames f and f + 1 (a brief hold: a clean cut point)"""
    rest_all(f)
    rest_all(f + 1)


def cash_show():
    """three shows of the money, each back to the rest pose: a quick flash of the fan up and out, then a bigger
    one with the fan spread wide and a toe tap, then a cocky little pump of the stack"""
    # show 1: up and out, a flash of the fan, back
    pose(5, hips=dict(y=-5, x=1), torso=dict(r=1.2), head=dict(r=-1), grip=dict(y=-8, x=-3, r=-2))
    pose(13, hips=dict(y=-3, x=-6), torso=dict(r=2.2), chest=dict(r=1.2), head=dict(r=4.5, y=1),
         grip=dict(y=78, x=44, r=17))
    pose(18, grip=dict(y=72, x=41, r=15), head=dict(r=4))
    pose(23, hips=dict(y=-2, x=1), torso=dict(r=.4), chest=dict(r=.3), head=dict(r=-.5, y=0), grip=dict(y=-3, x=-1, r=-1))
    fan(5, 0); fan(13, 1.9); fan(18, 1.6); fan(23, 0)
    rest_pass(26)
    # show 2: the big one - the fan wide, chin up, the toe tapping
    pose(31, hips=dict(y=-6, x=1), torso=dict(r=1.5), head=dict(r=-1), grip=dict(y=-10, x=-4, r=-3))
    pose(38, hips=dict(y=-5, x=-8), torso=dict(r=2.5), chest=dict(r=1.5), head=dict(r=5, y=1), grip=dict(y=92, x=52, r=19))
    pose(43, grip=dict(y=84, x=48, r=16), head=dict(r=4))
    pose(46, grip=dict(y=90, x=52, r=19), head=dict(r=5))
    pose(50, hips=dict(y=-2, x=1), torso=dict(r=.4), chest=dict(r=.3), head=dict(r=-.6, y=0), grip=dict(y=-3, x=-1, r=-1))
    fan(31, 0); fan(38, 2.3); fan(43, 1.9); fan(46, 2.2); fan(50, 0)
    for f, a_ in ((37, 0), (40, 8), (42, 0), (44, 0), (46, 9), (48, 0)):
        foot_pivot("r", f, a_, HEEL_R)
    for f in (42, 48):
        hard(f, "foot_r", "rotation_euler", 2)
    rest_pass(52)
    # show 3: a cocky pump of the stack at chest height, a nod
    pose(58, hips=dict(y=-4), grip=dict(y=24, x=10, r=6), head=dict(r=2.5, y=1))
    pose(62, grip=dict(y=12, x=6, r=2), head=dict(r=-1.2, y=-1))
    pose(66, grip=dict(y=20, x=9, r=5), head=dict(r=1.5, y=.5))
    pose(72, hips=dict(y=-1), grip=dict(y=1, x=0, r=.3), head=dict(r=.2, y=0))
    fan(58, .8); fan(66, .6); fan(72, 0)
    take(67, .6)
    take(1, .8)


def cash_count():
    """he counts the money a bill at a time, in rounds: leans in and thumbs the front bill over, a nod as it
    passes, and straightens back to the rest pose before the next (six rounds); then a satisfied look up and a
    snap of the stack"""
    for i in range(6):
        r0 = 28 * i                                 # this round (rest at r0, back at rest by r0 + 27)
        b = NB - 1 - i                              # the front bill first
        t0 = r0 + 7
        pose(r0 + 5, hips=dict(y=-3, x=-1 + (1.2 if i % 2 else -1.2)), torso=dict(r=-.8), neck=dict(r=-1.2),
             head=dict(r=-3.8, y=-2.2), grip=dict(y=7, x=-4, r=-3))
        k(t0 - 3, "hand_l", r=0)
        k(t0 + 3, "hand_l", r=-7)
        k(t0 + 10, "hand_l", r=0)
        k(t0, f"bill_{b}", r=0)
        k(t0 + 5, f"bill_{b}", r=-26)
        k(t0 + 9, f"bill_{b}", r=-28)
        k(t0 + 16, f"bill_{b}", r=0)
        for j in range(b):                          # the ones behind open up a little as it passes
            k(t0 + 1, f"bill_{j}", r=0)
            k(t0 + 7, f"bill_{j}", r=1.6)
            k(t0 + 16, f"bill_{j}", r=0)
        k(t0 + 7, "head", r=-5.8, y=-3.6)           # the nod as it goes over
        k(t0 + 8, "grip", y=5, x=-4, r=-4)
        pose(t0 + 13, head=dict(r=-3.4, y=-2), grip=dict(y=6, x=-4, r=-3), hips=dict(y=-3, x=-1),
             torso=dict(r=-.7), neck=dict(r=-1))
        rest_pass(r0 + 27)
    # done: a satisfied look up, a snap of the stack
    pose(174, head=dict(r=2.5, y=1), torso=dict(r=.5), hips=dict(y=-2, x=0), grip=dict(y=14, x=-2, r=3))
    pose(178, grip=dict(y=-3, r=-2))
    pose(182, grip=dict(y=4, x=0, r=1), head=dict(r=1.5, y=0))
    pose(187, hips=dict(y=-1), head=dict(r=-.3), torso=dict(r=0), grip=dict(y=0, r=0))
    take(181, .6)
    take(1, .7)


def enter():
    # from below the frame, knees tucked, up into the air and down into the stance
    pose(0, root=dict(y=-1500), hips=dict(y=-8), head=dict(r=3), grip=dict(y=10))
    for side, ty in (("l", 18), ("r", 13)):
        k(0, "foot_" + side, x=0, y=ty, r=0)
        k(13, "foot_" + side, x=0, y=ty - 2, r=0)
        k(20, "foot_" + side, x=0, y=1, r=0)
        k(21, "foot_" + side, x=0, y=0, r=0)
    hard(0, "root", "location", 1)
    pose(13, root=dict(y=24), hips=dict(y=-4), head=dict(r=2), grip=dict(y=8))
    pose(16, root=dict(y=27))
    pose(21, root=dict(y=0), hips=dict(y=-3))
    hard(21, "root", "location", 1)
    pose(23, hips=dict(y=-17), head=dict(r=-3, y=-4), grip=dict(y=-10), torso=dict(r=-1.5))
    pose(28, hips=dict(y=1), head=dict(r=1, y=0), grip=dict(y=4), torso=dict(r=.5))
    pose(31, hips=dict(y=-2.5), head=dict(r=-.4), grip=dict(y=-1), torso=dict(r=0))


def exit_():
    pose(4, hips=dict(y=-12), head=dict(r=-2, y=-2), grip=dict(y=-6), torso=dict(r=-1.5))
    pose(7, root=dict(y=0), hips=dict(y=0))
    pose(9, root=dict(y=12), hips=dict(y=-2), head=dict(r=2), grip=dict(y=6))
    pose(20, root=dict(y=-1560), hips=dict(y=-6))
    for side, ty in (("l", 16), ("r", 12)):
        k(7, "foot_" + side, x=0, y=0, r=0)
        k(12, "foot_" + side, x=0, y=ty, r=0)
        k(20, "foot_" + side, x=0, y=ty + 4, r=0)


FN = {"idle": idle, "anticipation": anticipation, "win": win, "big_win": big_win, "lose": lose,
      "cash_show": cash_show, "cash_count": cash_count, "enter": enter, "exit": exit_}
FACE_PLAN = {"idle": [(0, "idle")], "anticipation": [(0, "anticipation"), (25, "idle")],
             "win": [(0, "win"), (61, "idle")], "big_win": [(0, "big_win"), (85, "idle")],
             "lose": [(0, "lose"), (54, "idle")], "cash_show": [(0, "cash_show"), (67, "idle")],
             "cash_count": [(0, "cash_count"), (181, "idle")], "enter": [(0, "idle")], "exit": [(0, "idle")]}
SPRING_GAIN = {"enter": .55, "exit": .45}


# ================================================================== guard, limbs, springs
def frames():
    return range(C.f0, C.f0 + C.n)


def head_xz(bone):
    pb = arm.pose.bones[bone]
    v = arm.matrix_world @ pb.head
    return np.array([v.x, v.z])


def world_rot(bone):
    pb = arm.pose.bones[bone]
    m = pb.matrix @ pb.bone.matrix_local.inverted()
    return math.atan2(m[2][0], m[0][0])


def rest_xz(bone, tail=False):
    b = arm.data.bones[bone]
    v = b.tail_local if tail else b.head_local
    return np.array([v.x, v.z])


LIMB_REST = {}
for _u, _l, _t, _p in LIMBS:
    H0, K0, A0 = rest_xz(_u), rest_xz(_l), rest_xz(_l, True)
    L1, L2 = np.linalg.norm(K0 - H0), np.linalg.norm(A0 - K0)
    u = A0 - H0
    sgn = 1.0 if (u[0] * (K0 - H0)[1] - u[1] * (K0 - H0)[0]) > 0 else -1.0
    LIMB_REST[_u] = dict(L1=L1, L2=L2, d0=np.linalg.norm(A0 - H0), sgn=sgn,
                         a1=math.atan2(*(K0 - H0)[::-1]), a2=math.atan2(*(A0 - K0)[::-1]))
STATS = {}


def guard():
    """drop the hips (bone 'body') wherever a leg would have to reach past its drawn length"""
    drops = []
    for f in frames():
        sc.frame_set(f)
        need = 0.0
        for u, l, t, p in LIMBS[:2]:
            R = LIMB_REST[u]
            Hp, A = head_xz(u), head_xz(t)
            dx, dz = A[0] - Hp[0], A[1] - Hp[1]             # dz < 0: the ankle below the hip
            lim = R["d0"] + 1e-6
            if abs(dx) < lim:
                need = max(need, -math.sqrt(lim * lim - dx * dx) - dz)
        drops.append(-need / P)
    STATS.setdefault(C.name, {})["guard_px"] = round(float(-min(drops)), 2)
    series("body", drops, channel="y", tol=.05)
    if C.loop:
        fxkit.make_cyclic(C.act)


def solve_limbs():
    out = {u: [] for u, *_ in LIMBS}
    out.update({l: [] for _, l, *_ in LIMBS})
    miss = {}
    stretch = {"arm_r_upper": []}
    for f in frames():
        sc.frame_set(f)
        for u, l, t, p in LIMBS:
            R = LIMB_REST[u]
            Hp, A = head_xz(u), head_xz(t)
            v = A - Hp
            d = float(np.linalg.norm(v))
            dmax = R["L1"] + R["L2"] - 1e-4
            st = 1.0
            if d > dmax:
                if u == "arm_r_upper":                     # the hidden arm (behind the shirt and the money) reaches
                    st = d / dmax                           # by stretching its plain skin tube
                else:
                    miss[u] = max(miss.get(u, 0), (d - dmax) / P)
                d = dmax
            if u in stretch:
                stretch[u].append(st)
            dmin = abs(R["L1"] - R["L2"]) + 1e-4
            d = max(d, dmin)
            a = math.atan2(v[1], v[0])
            cb = (R["L1"] ** 2 + d * d - R["L2"] ** 2) / (2 * R["L1"] * d)
            phi1 = a + R["sgn"] * math.acos(max(-1.0, min(1.0, cb)))
            # (a stretched arm: both bones longer by st, the same bend)
            Kp = Hp + R["L1"] * st * np.array([math.cos(phi1), math.sin(phi1)])
            phi2 = math.atan2(*(A - Kp)[::-1]) if np.linalg.norm(A - Kp) > 1e-6 else phi1
            rho = world_rot(p)
            r1 = phi1 - R["a1"] - rho
            r2 = (phi2 - R["a2"]) - (phi1 - R["a1"])
            wrap = lambda x: (x + math.pi) % (2 * math.pi) - math.pi
            out[u].append(math.degrees(wrap(r1)))
            out[l].append(math.degrees(wrap(r2)))
    STATS.setdefault(C.name, {})["limb_miss_px"] = {u: round(float(m), 2) for u, m in miss.items()}
    STATS[C.name]["arm_r_stretch"] = round(max(stretch["arm_r_upper"]), 3)
    for b, vals in out.items():
        series(b, vals)
    for b in ("arm_r_upper", "arm_r_fore"):
        series(b, stretch["arm_r_upper"], channel="sy")
    if C.loop:
        fxkit.make_cyclic(C.act)


def pin_to_cues(vals, cues):
    """a loop's spring motion pinned to zero on every cue frame (subtract a smooth periodic curve through its
    values there), so the idle passes exactly through the rest pose on every beat and still swings between"""
    n = len(vals)
    cs = sorted(cues)
    out = []
    for i in range(n):
        j = max(c for c in cs if c <= i)
        jn = cs[(cs.index(j) + 1) % len(cs)]
        span = (jn - j) % n or n
        t = (i - j) / span
        w = .5 - .5 * math.cos(math.pi * t)
        out.append(vals[i] - (vals[j] * (1 - w) + vals[jn] * w))
    return out


def pin_open(vals, cues):
    """a one-shot's spring motion pinned to zero on the given frames (a smooth curve through its values there
    taken off between them), so it passes exactly through rest there"""
    cs = sorted(set(c for c in cues if 0 <= c < len(vals)))
    out = list(vals)
    for j, jn in zip(cs, cs[1:]):
        for i in range(j, jn + 1):
            t = (i - j) / max(1, jn - j)
            w = .5 - .5 * math.cos(math.pi * t)
            out[i] = vals[i] - (vals[j] * (1 - w) + vals[jn] * w)
    return out


IDLE_CUES = [0, 16, 32, 48, 64, 80, 96, 101, 115, 120, 134]


def springs():
    g = SPRING_GAIN.get(C.name, 1.0)
    f1 = C.f0 + C.n - 1
    J = dict(neck_top=(462, 712), head_top=(470, 330), cuff=(478, 372), cap_mid=(425, 205), cap_top=(338, 80))
    kw = dict(loop=C.loop, rest_start=False, settle=0 if C.loop else 8)

    def apply(rec, tol=.08):
        for b, vals in rec.items():
            if b.endswith(":sy"):
                continue
            if C.loop:
                vals = pin_to_cues(list(vals), IDLE_CUES)
            elif C.name in REST_PASS:
                vals = pin_open(list(vals), [0] + REST_PASS[C.name] + [C.n - 1])
            series(b, vals, tol=tol)

    apply(fxkit.secondary(sc, arm, "head", C.f0, f1, {"head_fx": dict(
        chain=[J["neck_top"], J["head_top"]], freq=[2.3], zeta=.42, limit=4.5, gain=.9)}, gain=g, **kw))
    apply(fxkit.secondary(sc, arm, "beanie", C.f0, f1, {"cap": dict(
        chain=[J["cuff"], J["cap_mid"], J["cap_top"]], freq=[3.0, 2.4], zeta=.26, limit=9, gain=1.0)}, gain=g, **kw))
    for b in range(NB):
        top_mid = [tuple(arm.data.bones[f"billfx_{b}.0"].head_local), tuple(arm.data.bones[f"billfx_{b}.1"].head_local),
                   tuple(arm.data.bones[f"billfx_{b}.1"].tail_local)]
        chain = [((v[0] * 100 + 512), (768 - v[2] * 100)) for v in top_mid]
        apply(fxkit.secondary(sc, arm, f"bill_{b}", C.f0, f1, {f"billfx_{b}": dict(
            chain=chain, freq=[4.6 - .25 * b, 3.4 - .15 * b], zeta=.2, limit=9, gain=.9)}, gain=g, **kw))
    if C.loop:
        fxkit.make_cyclic(C.act)


# ================================================================== faces, loose bills
def key_vis(ob, f, visible):
    ob.hide_render = not visible
    ob.hide_viewport = not visible
    ob.keyframe_insert("hide_render", frame=f)
    ob.keyframe_insert("hide_viewport", frame=f)


def faces(name, f0):
    for df, face in FACE_PLAN[name]:
        for fc in FACES:
            key_vis(bpy.data.objects[f"{SID}_head_{fc}"], f0 + df, fc == face)


def frame_bounds(margin=8):
    """the rendered frame in master px (x0, y0, x1, y1), `margin` screen px inside its edges"""
    k = float(arm["screen_scale"])
    W_, H_ = sc.render.resolution_x, sc.render.resolution_y
    cx = (spec["rest_box"][0] + spec["rest_box"][2]) / 2
    gy = spec["rest_box"][3]
    g_scr = float(arm["ground_y"])
    return (cx + (margin - W_ / 2) / k, gy + (margin - g_scr) / k, cx + (W_ - margin - W_ / 2) / k,
            gy + (H_ - margin - g_scr) / k)


def toss(f0):
    """big_win: five bills flicked off the top of the fan at the jump's peak - they fly up into the headroom and out
    to the sides, tumbling (flipping and spinning), and shrink away to nothing inside the frame; a bill nearing
    an edge shrinks faster, so no bill ever touches the frame's edge (bones without a parent: free of the rig)"""
    import random
    rnd = random.Random(7)
    c0 = spec["fan"]["front_centre"]
    bw, bh = spec["bill_size"]
    X0, Y0, X1, Y1 = frame_bounds(8)
    launch = [41, 42, 42, 43, 44]
    vx = [-15.0, -9.0, 5.0, 10.5, 16.0]             # master px / frame
    vy = [40.0, 47.0, 50.0, 44.0, 37.0]             # up
    life = [32, 36, 38, 34, 30]                     # frames until it has shrunk away
    g = 2.3
    for i in range(THROWN):
        fl = launch[i]
        src = NB - 1 - (i % 3)
        sc.frame_set(f0 + fl)
        pos = (arm.matrix_world @ arm.pose.bones[f"billfx_{src}.1"].matrix).translation      # the bill's middle
        x0 = pos.x * 100 + 512 - c0[0]                      # px from the loose bill's rest centre, y up
        y0 = -((768 - pos.z * 100) - c0[1])
        rot0 = -spec["fan"]["front_angle"] + FAN_ANGS[NB - 1 - src] + math.degrees(world_rot(f"billfx_{src}.1"))
        bone = f"toss_{i}"
        ob = bpy.data.objects[f"{SID}_toss_{i}"]
        key_vis(ob, 0, False)
        key_vis(ob, f0 + fl, True)
        spin = rnd.uniform(-9, 9)
        ph = rnd.uniform(0, 6.28)
        x, y, vxx, vyy = x0, y0, vx[i], vy[i]
        gone = f0 + 96
        for t in range(0, 96 - fl):
            r = rot0 + spin * t + 14 * math.sin(.25 * t + ph) * min(1, t / 8)
            fl_x = math.cos(.21 * t) if t > 0 else 1.0
            # planned size: whole, then shrinking away over its last 16 frames
            u = (t - (life[i] - 16)) / 16
            sz = 1.0 if u <= 0 else max(0.0, 1 - u * u * (3 - 2 * u))
            # and never past the frame: the largest size whose corners stay inside it
            X, Y = c0[0] + x, c0[1] - y
            a_ = math.radians(r)
            ex = max(abs(bw / 2 * fl_x * math.cos(a_)) + abs(bh / 2 * math.sin(a_)), 1e-3)
            ey = max(abs(bw / 2 * fl_x * math.sin(a_)) + abs(bh / 2 * math.cos(a_)), 1e-3)
            room = min((X - X0) / ex, (X1 - X) / ex, (Y - Y0) / ey, (Y1 - Y) / ey)
            sz = max(0.0, min(sz, room))
            if sz < .04:
                gone = f0 + fl + t
                break
            fxkit.key(arm, bone, f0 + fl + t, x=x * P, y=y * P, r=r, sx=fl_x * sz, sy=sz)
            vyy = max(vyy - g, -30.0)
            vxx *= .99
            x += vxx + 2.2 * math.sin(.3 * t + ph) * min(1, t / 10)
            y += vyy
        key_vis(ob, gone, False)
        STATS.setdefault("toss", []).append(gone - f0)


# ================================================================== the slow-down (time remapping at render)
SLOW = 1.35                                       # every clip plays this many times slower than keyed (the owner:
                                                  # "moving very quickly"): rendered with Blender's Time Remapping
SLOW_LOOP = 2.0                                   # the idle slower still (the owner: "make human's idle animation still
                                                  # physically slower just stretch out the duration of it")


def remap(n, loop):
    """(old, new) for a clip of n keyed frames: a loop's cycle (n frames) becomes round(n * SLOW) rendered frames;
    a one-shot's span (n - 1 frames, first to last key) becomes round((n - 1) * SLOW) - its first and last
    rendered frames land exactly on its first and last keys (the rest pose)"""
    old = n if loop else n - 1
    return old, int(round(old * (SLOW_LOOP if loop else SLOW)))


def place_next(f, clip):
    """the first frame >= f where this clip may start: a multiple of its remap's 'old', so its rendered frames
    fall on whole frames of the remapped timeline"""
    if clip is None:
        return f
    old, _ = remap(clip[1], clip[2])
    return int(math.ceil(f / old) * old)


# ================================================================== build every clip
def build():
    fxkit.ICON[0], fxkit.ICON[1] = 1024, 1536
    for o in bpy.data.objects:
        if o.animation_data:
            o.animation_data_clear()
    arm.animation_data_create()
    clips, f0 = {}, place_next(1, CLIP_LIST[0])
    for name, n, loop in CLIP_LIST:
        C.name, C.f0, C.n, C.loop = name, f0, n, loop
        C.act = fxkit.begin_action(arm, f"{SID}_{name}")
        # every bone starts at rest; a one-shot ends there, a loop's last key is its first
        rest_all(0)
        rest_all(n if loop else n - 1)
        k(0, "body", x=0, y=0, r=0, sx=1, sy=1)
        FN[name]()
        if loop:
            fxkit.make_cyclic(C.act)
        guard()
        solve_limbs()
        springs()
        fxkit.end_action(arm, C.act, f0)
        faces(name, f0)
        clips[name] = [f0, f0 + n - 1]
        print(f"  {name}: frames {f0}-{f0 + n - 1} ({n}), {STATS.get(name)}", flush=True)
        f0 = place_next(f0 + n + 24, CLIP_LIST[[c[0] for c in CLIP_LIST].index(name) + 1] if name != CLIP_LIST[-1][0] else None)
    # the loose bills: their own Action on their own NLA track (they are no part of any clip's pose)
    C.f0 = clips["big_win"][0]
    act = fxkit.begin_action(arm, f"{SID}_toss")
    for i in range(THROWN):
        fxkit.key(arm, f"toss_{i}", 0, x=0, y=0, r=0, sx=1, sy=1)
    toss(C.f0)
    ad = arm.animation_data
    slot = ad.action_slot
    ad.action = None
    tr = ad.nla_tracks.new()
    tr.name = "toss"
    st = tr.strips.new(act.name, 0, act)
    try:
        st.action_slot = slot
    except Exception:
        pass
    st.extrapolation = "HOLD"
    for ob in bpy.data.objects:
        if ob.animation_data and ob.animation_data.action:
            for fc in fxkit.fcurves(ob.animation_data.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"
    arm["clips"] = clips
    arm["loops"] = [n for n, _, lp in CLIP_LIST if lp]
    arm["idle_cues_keyed"] = IDLE_CUES
    arm["remap"] = {nm: list(remap(n, lp)) for nm, n, lp in CLIP_LIST}
    sc.frame_start, sc.frame_end = 1, max(b for a, b in clips.values())
    return clips


# ================================================================== effects (Grease Pencil, drawn frame by frame)
def effects(clips):
    """landing dust under the shoes, glints of light off the money - drawn in Grease Pencil in front of the art"""
    import random
    old = bpy.data.objects.get(SID + "_fx")
    gp = fxkit.gp_object(sc.collection, SID + "_fx", depth=-2.4)
    m_dust = fxkit.gp_mat(gp, "boy_dust", (.42, .38, .5, 1), fill=(.86, .83, .93, 1))
    m_white = fxkit.gp_mat(gp, "boy_glint_white", fxkit.WHITE, fill=fxkit.WHITE)
    m_gold = fxkit.gp_mat(gp, "boy_glint_gold", fxkit.GOLD, fill=fxkit.GOLD)
    m_lime = fxkit.gp_mat(gp, "boy_glint_lime", fxkit.LIME, fill=fxkit.LIME)
    for m in gp.data.materials:                         # the shoe pass draws them black (they cover, never glow)
        g = m.grease_pencil
        m["color_beauty"] = list(g.color); m["fill_beauty"] = list(g.fill_color)
    dust, glint = fxkit.Board(), fxkit.Board()
    rnd = random.Random(3)

    def puffs(f, scale=1.0, n=3):
        for side, xs in (("l", (215, 300, 420)), ("r", (505, 640, 820))):
            for j, X in enumerate(xs[:n]):
                # sized so the puff's bottom stays above the frame's bottom edge (frame_bounds), rolling out
                # sideways and up rather than down
                bot = frame_bounds(8)[3]
                cy = 1440.0
                size = min((.32 + .1 * rnd.random()) * scale, (bot - cy) / 100 / 1.15)
                x, z = fxkit.px(X + rnd.uniform(-12, 12), cy)
                dr = (-.6 if X < 500 and j == 0 else .6 if j == len(xs) - 1 else rnd.uniform(-.25, .25)) * scale
                fxkit.dust(dust, f + j % 2, 9 + j, x, z, size, m_dust, drift=(dr, .3 * scale), seed=rnd.randint(0, 99))

    def glints(f0, f1, every=3, r=.22):
        for f in range(f0, f1, every):
            sc.frame_set(f)
            b = rnd.randint(0, NB - 1)
            pb = arm.pose.bones[f"billfx_{b}.1"]
            t = rnd.uniform(.2, 1.0)
            v = arm.matrix_world @ pb.head.lerp(pb.tail, t)
            mat = (m_white, m_gold, m_lime)[rnd.randint(0, 2)]
            fxkit.sparkle(glint, f, 7, v.x + rnd.uniform(-.5, .5), v.z + rnd.uniform(-.3, .4), r * rnd.uniform(.7, 1.2),
                          mat, rot0=rnd.uniform(0, .8))

    w0 = clips["win"][0]
    puffs(w0 + 31)
    glints(w0 + 18, w0 + 44, 3)
    b0 = clips["big_win"][0]
    puffs(b0 + 18, .7, 2)
    puffs(b0 + 52, 1.25)
    glints(b0 + 34, b0 + 70, 2, .26)
    e0 = clips["enter"][0]
    puffs(e0 + 21, .9)
    c0 = clips["cash_show"][0]
    glints(c0 + 18, c0 + 46, 4, .2)
    k0 = clips["cash_count"][0]
    glints(k0 + 168, k0 + 178, 5, .18)
    dust.draw(fxkit.gp_layer(gp, "dust"))
    glint.draw(fxkit.gp_layer(gp, "glints"))
    return gp


CLIPS = build()
effects(CLIPS)
print("BOY clips:", CLIPS, "loose bills leave at", STATS.get("toss"), flush=True)
