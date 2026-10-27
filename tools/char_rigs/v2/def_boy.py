"""SMUKIEZ rig definition: bones on the master's joints (master px), slots back to front, weight
fields shared across every joint so overlapping parts bend as one."""
import json, math, os
import numpy as np
import rigkit as rk
import paths

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = os.path.join(paths.WORK, 'parts', 'boy')
FRAME = rk.Frame(0.864, 5, 800)
F = FRAME
GRID = 30
FACES = ['idle', 'anticipation', 'win', 'big_win', 'lose', 'cash_show', 'cash_count']

FAN = json.load(open(os.path.join(PARTS, 'fan.json')))
PIV = tuple(FAN['pivot']); C0 = FAN['front_centre']; BW, BH = FAN['size']; ANG = FAN['front_angle']; PAD = FAN['pad']
ANGS = FAN['angles']            # front -> back, degrees (screen CCW)
NB = len(ANGS)


def rot_screen(p, c, deg):
    """rotate point p about c by deg, counter-clockwise on screen (y down)"""
    a = math.radians(deg); x, y = p[0] - c[0], p[1] - c[1]
    return (c[0] + x * math.cos(a) + y * math.sin(a), c[1] - x * math.sin(a) + y * math.cos(a))


def bill_place(k):
    """bill k (0 = back .. 5 = front): image px (of the upright bill crop, scaled) -> master px"""
    th = ANGS[NB - 1 - k]
    def f(P):                                          # P: px of the upright bill png
        x = C0[0] - (BW / 2 + PAD) + P[:, 0]; y = C0[1] - (BH / 2 + PAD) + P[:, 1]   # in the bill's rotated frame
        out = []
        for xi, yi in zip(x, y):
            q = rot_screen((xi, yi), C0, -ANG)        # undo the straightening
            q = rot_screen(q, PIV, th)                # into the fan
            out.append(q)
        return np.array(out)
    return f, th


def bill_points(k):
    f, th = bill_place(k)
    top = f(np.array([[PAD + BW / 2, PAD]]))[0]; mid = f(np.array([[PAD + BW / 2, PAD + BH * .5]]))[0]
    return top, mid


BONES = [
    ('root', None, F.px(0, 0), None, {}),
    ('hips', 'root', (482, 1040), (482, 990), {}),
    ('torso', 'hips', (480, 1012), (468, 880), {}),
    ('chest', 'torso', (468, 880), (458, 772), {}),
    ('neck', 'chest', (455, 785), (462, 712), {}),
    ('head', 'neck', (462, 712), (470, 330), {}),
    ('beanie', 'head', (470, 300), (465, 175), {}),
    ('beanie_tip', 'beanie', (465, 175), (455, 85), {}),
    ('arm_left_upper', 'chest', (318, 800), (300, 932), {}),
    ('elbow_left', 'arm_left_upper', (300, 932), 'inherit:30', {}),
    ('arm_left_fore', 'arm_left_upper', (300, 932), (456, 928), {}),
    ('arm_right_upper', 'chest', (622, 800), (626, 880), {}),
    ('arm_right_fore', 'arm_right_upper', (626, 880), (668, 925), {}),
    ('grip', 'chest', PIV, (PIV[0], PIV[1] - 60), {}),
]
for k in range(NB):
    top, mid = bill_points(k)
    BONES.append((f'bill_{k}', 'grip', PIV, tuple(top), {}))
    BONES.append((f'bill_{k}_tip', f'bill_{k}', tuple(mid), tuple(top), {}))
BONES += [
    ('hand_left', 'grip', (456, 928), (540, 930), {}),
    ('hand_right', 'grip', (668, 925), (735, 945), {}),
    ('thigh_left', 'hips', (395, 1042), (356, 1158), {}),
    ('knee_left', 'thigh_left', (356, 1158), 'inherit:40', {}),
    ('shin_left', 'thigh_left', (356, 1158), (338, 1278), {}),
    ('thigh_right', 'hips', (548, 1048), (580, 1168), {}),
    ('knee_right', 'thigh_right', (580, 1168), 'inherit:40', {}),
    ('shin_right', 'thigh_right', (580, 1168), (585, 1300), {}),
    ('foot_left', 'root', (338, 1278), None, {}),
    ('shoe_left', 'foot_left', (338, 1278), (230, 1330), {}),
    ('foot_right', 'root', (585, 1300), None, {}),
    ('shoe_right', 'foot_right', (585, 1300), (800, 1360), {}),
]

IK = [
    {'name': 'arm_left', 'order': 2, 'bones': ['arm_left_upper', 'arm_left_fore'], 'target': 'hand_left',
     'bendPositive': True, 'stretch': True, 'softness': 8},
    {'name': 'arm_right', 'order': 3, 'bones': ['arm_right_upper', 'arm_right_fore'], 'target': 'hand_right',
     'bendPositive': True, 'stretch': True, 'softness': 8},
]
LEGS = [('thigh_left', 'shin_left', 'foot_left'), ('thigh_right', 'shin_right', 'foot_right')]
TRANSFORM = [
    {'name': 'knee_left', 'order': 4, 'bones': ['knee_left'], 'target': 'shin_left', 'mixRotate': .5,
     'mixX': 0, 'mixY': 0, 'mixScaleX': 0, 'mixScaleY': 0, 'mixShearY': 0},
    {'name': 'knee_right', 'order': 5, 'bones': ['knee_right'], 'target': 'shin_right', 'mixRotate': .5,
     'mixX': 0, 'mixY': 0, 'mixScaleX': 0, 'mixScaleY': 0, 'mixShearY': 0},
    {'name': 'elbow_left', 'order': 6, 'bones': ['elbow_left'], 'target': 'arm_left_fore', 'mixRotate': .5,
     'mixX': 0, 'mixY': 0, 'mixScaleX': 0, 'mixScaleY': 0, 'mixShearY': 0},
]

# ---------------------------------------------------------------- weight fields (world units, y up)
U = F.u
J = {n: np.array(U(*p)) for n, p in {
    'waist': (480, 1012), 'chest': (468, 880), 'collar': (455, 785), 'neck_top': (462, 712),
    'hip_l': (395, 1042), 'knee_l': (356, 1158), 'ankle_l': (338, 1278),
    'hip_r': (548, 1048), 'knee_r': (580, 1168), 'ankle_r': (585, 1300),
    'shoulder_l': (318, 800), 'elbow_l': (300, 932), 'wrist_l': (456, 928),
    'shoulder_r': (622, 800), 'elbow_r': (626, 880), 'wrist_r': (668, 925),
    'brim': (470, 300), 'beanie_mid': (465, 175), 'beanie_top': (455, 85),
    'crotch': (480, 1120)}.items()}


def rigid(bone):
    return lambda world: [{bone: 1.0} for _ in world]


def leg_field(p, side):
    s = 'l' if side == 'left' else 'r'
    top = J[f'hip_{s}'] + np.array([0, 90.0])
    return rk.chain_weights(p, [top, J[f'hip_{s}'], J[f'knee_{s}'], J[f'ankle_{s}']],
                            ['hips', f'thigh_{side}', f'shin_{side}'], [None, f'knee_{side}'], [38, 70])


def wf_leg(side):
    return lambda world: [leg_field(p, side) for p in world]


def wf_pelvis(world):
    out = []
    cx = J['crotch'][0]
    for p in world:
        r = float(rk.smoothstep(cx - 30, cx + 30, p[0]))          # 0 left leg .. 1 right leg
        out.append(rk.mix((1 - r, leg_field(p, 'left')), (r, leg_field(p, 'right'))))
    return out


def wf_torso(world):
    out = []
    for p in world:
        c = float(rk.smoothstep(J['chest'][1] - 70, J['chest'][1] + 70, p[1]))     # 0 torso .. 1 chest
        w = rk.mix((1 - c, {'torso': 1}), (c, {'chest': 1}))
        # each sleeve: the chest at the shoulder seam, its upper arm at the hem (the arm below the hem
        # moves with the same bone, so hem and arm never part)
        sl = float(rk.smoothstep(J['shoulder_l'][0] + 48, J['shoulder_l'][0] + 18, p[0])) *             float(rk.smoothstep(J['shoulder_l'][1] + 5, J['shoulder_l'][1] - 95, p[1]))
        sr = float(rk.smoothstep(J['shoulder_r'][0] - 48, J['shoulder_r'][0] - 18, p[0])) *             float(rk.smoothstep(J['shoulder_r'][1] + 5, J['shoulder_r'][1] - 80, p[1]))
        w = rk.mix((1 - sl - sr, w), (sl, {'arm_left_upper': 1}), (sr, {'arm_right_upper': 1}))
        out.append(w)
    return out


def wf_neck(world):
    lo = J['collar'] + np.array([0, -60.0]); hi = J['neck_top'] + np.array([0, 60.0])
    return [rk.chain_weights(p, [lo, J['collar'], J['neck_top'], hi], ['chest', 'neck', 'head'], [None, None], [25, 25])
            for p in world]


def wf_beanie(world):
    lo = J['brim'] + np.array([0, -120.0])
    return [rk.chain_weights(p, [lo, J['brim'], J['beanie_mid'], J['beanie_top']], ['head', 'beanie', 'beanie_tip'],
                             [None, None], [45, 60]) for p in world]


def arm_field(p, side):
    s = 'l' if side == 'left' else 'r'
    top = J[f'shoulder_{s}'] + np.array([0, 70.0])
    helper = 'elbow_left' if side == 'left' else None
    end = J[f'wrist_{s}'] + (J[f'wrist_{s}'] - J[f'elbow_{s}']) / np.linalg.norm(J[f'wrist_{s}'] - J[f'elbow_{s}']) * 90
    return rk.chain_weights(p, [top, J[f'shoulder_{s}'], J[f'elbow_{s}'], J[f'wrist_{s}'], end],
                            ['chest', f'arm_{side}_upper', f'arm_{side}_fore', f'hand_{side}'], [None, helper, None],
                            [25, 32, 22])


def wf_arm(side):
    return lambda world: [arm_field(p, side) for p in world]


def wf_bill(k):
    top, mid = bill_points(k)
    base = np.array(U(*PIV)); tip = np.array(U(*top)); m = np.array(U(*mid))
    ax = tip - base; L = np.linalg.norm(ax); ax /= L
    def f(world):
        out = []
        for p in world:
            z = float((p - base) @ ax) / L                       # 0 at the pivot .. 1 at the top
            t = float(rk.smoothstep(.35, .95, z))
            out.append(rk.mix((1 - t, {f'bill_{k}': 1}), (t, {f'bill_{k}_tip': 1})))
        return out
    return f


SLOTS = [
    ('neck', 'neck', [('neck', 'neck', 'mesh', wf_neck)]),
    ('arm_right_upper', 'arm_right_upper', [('arm_right_upper', 'arm_r_upper', 'mesh', wf_arm('right'))]),
    ('arm_right_fore', 'arm_right_fore', [('arm_right_fore', 'arm_r_fore', 'mesh', wf_arm('right'))]),
    ('pelvis', 'hips', [('pelvis', 'pelvis', 'mesh', wf_pelvis)]),
    ('shoe_left', 'shoe_left', [('shoe_left', 'shoe_l', 'region', None)]),
    ('shoe_right', 'shoe_right', [('shoe_right', 'shoe_r', 'region', None)]),
    ('shin_left', 'shin_left', [('shin_left', 'shin_l', 'mesh', wf_leg('left'))]),
    ('shin_right', 'shin_right', [('shin_right', 'shin_r', 'mesh', wf_leg('right'))]),
    ('thigh_left', 'thigh_left', [('thigh_left', 'thigh_l', 'mesh', wf_leg('left'))]),
    ('thigh_right', 'thigh_right', [('thigh_right', 'thigh_r', 'mesh', wf_leg('right'))]),
    ('torso', 'torso', [('torso', 'torso', 'mesh', wf_torso)]),
    ('arm_left_upper', 'arm_left_upper', [('arm_left_upper', 'arm_l_upper', 'mesh', wf_arm('left'))]),
    ('head', 'head', [(f'face_{f}', f'head_{f}', 'region', None) for f in FACES]),
    ('beanie', 'beanie', [('beanie', 'beanie', 'mesh', wf_beanie)]),
    ('arm_left_fore', 'arm_left_fore', [('arm_left_fore', 'arm_l_fore', 'mesh', wf_arm('left'))]),
]
SLOTS += [(f'bill_{k}', f'bill_{k}', [('bill', 'bill', 'mesh', wf_bill(k))]) for k in range(NB)]
SLOTS += [
    ('hand_left', 'hand_left', [('hand_left', 'hand_l', 'region', None)]),
    ('hand_right', 'hand_right', [('hand_right', 'hand_r', 'region', None)]),
]
TO_MASTER = {(f'bill_{k}', 'bill'): bill_place(k)[0] for k in range(NB)}
SLOT_DEFAULT = {'head': 'face_idle'}
SLOT_EXTRA = {}
SKELETON = {'hash': 'SMUKIEZ-v8-redo-2026-10-27', 'spine': '4.2.43', 'fps': 30, 'images': './images/', 'audio': '',
            'height': 1621.96}
EVENTS = {'cash_rustle': {}, 'bill_count': {}, 'win_hit': {}, 'big_win_hit': {}, 'land': {}, 'foot_tap': {}}
