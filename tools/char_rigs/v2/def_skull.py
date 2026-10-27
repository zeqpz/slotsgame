"""SMOKE SKULL rig definition: bones on the master's joints (master px), slots back to front."""
import json, math, os, sys
import numpy as np
import cv2
from PIL import Image
import rigkit as rk
import paths

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = os.path.join(paths.WORK, 'parts', 'skull')
FRAME = rk.Frame(0.97, 14, 730)
F = FRAME
GRID = 30
FACES = ['idle', 'anticipation', 'win', 'big_win', 'lose']
EMBER = (258, 753)
CIGAR_MOUTH = (402, 656)
HINGE = tuple(json.load(open(os.path.join(PARTS, 'skull_meta.json')))['jaw_hinge'][:2])


def old_extras():
    """the ember glow and the ash pieces: the old rig's own little images, at their old size in units,
    placed at the new cigar's tip (canvas-sized pngs like every other part)"""
    sys.path.insert(0, os.path.join(rk.REPO, 'tools', 'char_rigs'))
    import atlaskit as ak
    d = paths.DELIVERED           # the rig as first delivered still holds the ember glow and the ash
    atlas = ak.Atlas(open(os.path.join(d, 'smoke-skull.atlas'), encoding='utf-8').read())
    pages = {p['name']: Image.open(os.path.join(d, p['name'])).convert('RGBA') for p in atlas.pages}
    sizes = {'ember_glow': (58, 65), 'ash_0': (32, 32), 'ash_1': (20, 20), 'ash_2': (20, 20), 'ash_3': (20, 20),
             'ash_4': (20, 20)}
    for n, (wu, hu) in sizes.items():
        out = os.path.join(PARTS, n + '.png')
        im = ak.crop(pages, atlas, n)
        w, h = max(2, int(round(wu * F.s))), max(2, int(round(hu * F.s)))
        im = im.resize((w, h), Image.LANCZOS)
        can = Image.new('RGBA', (1024, 1536), (0, 0, 0, 0))
        cx, cy = EMBER
        if n.startswith('ash'):
            cx, cy = EMBER[0] + 4, EMBER[1] - 2
        can.paste(im, (int(round(cx - w / 2)), int(round(cy - h / 2))))
        can.save(out)


old_extras()

LACE = {'left': ('l', 'lace_l_up', (330, 1236), (232, 1112)), 'right': ('r', 'lace_r_right', (650, 1256), (792, 1214))}


def laced_shoes():
    """Each loose lace end is its own part on its own bone (it swings after the shoe), but it is drawn
    in its shoe's slot - one mesh weighted to the shoe and the lace bones - so the shoe slots keep the
    laces: the game's neon rim light leaves the slots shoe_left / shoe_right alone (owner, 2026-10-25:
    the laces are not lit) and its foot shadows measure them, as before."""
    masks = {}
    for side, (s, lace, R, T) in LACE.items():
        shoe = np.asarray(Image.open(os.path.join(PARTS, f'shoe_{s}.png')).convert('RGBA')).astype(np.float32) / 255
        lc = np.asarray(Image.open(os.path.join(PARTS, lace + '.png')).convert('RGBA')).astype(np.float32) / 255
        ps = shoe.copy(); ps[..., :3] *= ps[..., 3:4]
        pl = lc.copy(); pl[..., :3] *= pl[..., 3:4]
        o = ps * (1 - pl[..., 3:4]) + pl                                   # the lace in front of its shoe
        out = o.copy()
        out[..., :3] = np.where(o[..., 3:4] > 1e-4, o[..., :3] / np.maximum(o[..., 3:4], 1e-4), 0)
        Image.fromarray((out * 255 + .5).clip(0, 255).astype(np.uint8), 'RGBA').save(os.path.join(PARTS, f'shoe_{s}_laced.png'))
        body = shoe[..., 3] > .5
        free = (lc[..., 3] > .3) & ~(cv2.dilate(body.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)
        masks[side] = (cv2.distanceTransform((~free).astype(np.uint8), cv2.DIST_L2, 5), body)
    return masks


SHOE_MASKS = laced_shoes()

BONES = [
    ('root', None, F.px(0, 0), None, {}),
    ('motion', 'root', F.px(0, 0), None, {}),
    ('pelvis', 'motion', (505, 1005), (505, 960), {}),
    ('torso', 'pelvis', (505, 990), (503, 870), {}),
    ('chest', 'torso', (503, 870), (505, 765), {}),
    ('neck', 'chest', (505, 765), (515, 690), {}),
    ('head', 'neck', (515, 690), (520, 330), {}),
    ('jaw', 'head', HINGE, (470, 735), {}),
    ('beanie', 'head', (545, 245), (548, 150), {}),
    ('beanie_tip', 'beanie', (548, 150), (585, 80), {}),
    ('cigar', 'head', CIGAR_MOUTH, EMBER, {}),
    ('ember', 'cigar', EMBER, 'inherit:20', {}),
    ('ash_cap', 'cigar', (EMBER[0] + 4, EMBER[1] - 2), 'inherit:25', {}),
    ('ash_1', 'cigar', (EMBER[0] + 4, EMBER[1] - 2), 'inherit:15', {}),
    ('ash_2', 'cigar', (EMBER[0] + 4, EMBER[1] - 2), 'inherit:15', {}),
    ('ash_3', 'cigar', (EMBER[0] + 4, EMBER[1] - 2), 'inherit:15', {}),
    ('ash_4', 'cigar', (EMBER[0] + 4, EMBER[1] - 2), 'inherit:15', {}),
    ('string_left', 'chest', (432, 762), (430, 846), {}),
    ('string_right', 'chest', (575, 742), (575, 803), {}),
    ('hand_left', 'torso', (392, 935), (450, 950), {}),
    ('hand_right', 'torso', (612, 925), (560, 950), {}),
    ('arm_left_upper', 'chest', (365, 782), (322, 900), {}),
    ('elbow_left', 'arm_left_upper', (322, 900), 'inherit:30', {}),
    ('arm_left_fore', 'arm_left_upper', (322, 900), (392, 935), {}),
    ('arm_right_upper', 'chest', (682, 790), (750, 895), {}),
    ('elbow_right', 'arm_right_upper', (750, 895), 'inherit:30', {}),
    ('arm_right_fore', 'arm_right_upper', (750, 895), (612, 925), {}),
    ('thigh_left', 'pelvis', (420, 1035), (408, 1138), {}),
    ('knee_left', 'thigh_left', (408, 1138), 'inherit:40', {}),
    ('shin_left', 'thigh_left', (408, 1138), (400, 1236), {}),
    ('thigh_right', 'pelvis', (590, 1035), (600, 1148), {}),
    ('knee_right', 'thigh_right', (600, 1148), 'inherit:40', {}),
    ('shin_right', 'thigh_right', (600, 1148), (608, 1256), {}),
    ('foot_left', 'motion', (400, 1236), None, {}),
    ('shoe_left', 'foot_left', (400, 1236), (170, 1330), {}),
    ('lace_left', 'shoe_left', (330, 1236), (232, 1112), {}),
    ('foot_right', 'motion', (608, 1256), None, {}),
    ('shoe_right', 'foot_right', (608, 1256), (622, 1450), {}),
    ('lace_right', 'shoe_right', (650, 1256), (792, 1214), {}),
]

IK = [
    {'name': 'arm_left', 'order': 2, 'bones': ['arm_left_upper', 'arm_left_fore'], 'target': 'hand_left',
     'bendPositive': True, 'stretch': True, 'softness': 6},
    {'name': 'arm_right', 'order': 3, 'bones': ['arm_right_upper', 'arm_right_fore'], 'target': 'hand_right',
     'bendPositive': False, 'stretch': True, 'softness': 6},
]
LEGS = [('thigh_left', 'shin_left', 'foot_left'), ('thigh_right', 'shin_right', 'foot_right')]
TRANSFORM = [
    {'name': n, 'order': 4 + k, 'bones': [n], 'target': t, 'mixRotate': .5, 'mixX': 0, 'mixY': 0, 'mixScaleX': 0,
     'mixScaleY': 0, 'mixShearY': 0}
    for k, (n, t) in enumerate((('knee_left', 'shin_left'), ('knee_right', 'shin_right'),
                                ('elbow_left', 'arm_left_fore'), ('elbow_right', 'arm_right_fore')))]

U = F.u
J = {n: np.array(U(*p)) for n, p in {
    'hem': (505, 990), 'chest': (503, 870), 'collar': (505, 765), 'neck_top': (515, 690),
    'hip_l': (420, 1035), 'knee_l': (408, 1138), 'ankle_l': (400, 1236),
    'hip_r': (590, 1035), 'knee_r': (600, 1148), 'ankle_r': (608, 1256),
    'shoulder_l': (365, 782), 'elbow_l': (322, 900), 'wrist_l': (392, 935),
    'shoulder_r': (682, 790), 'elbow_r': (750, 895), 'wrist_r': (612, 925),
    'brim': (545, 245), 'beanie_mid': (548, 150), 'beanie_top': (585, 80), 'crotch': (497, 1095)}.items()}


def leg_field(p, side):
    s = 'l' if side == 'left' else 'r'
    top = J[f'hip_{s}'] + np.array([0, 80.0])
    return rk.chain_weights(p, [top, J[f'hip_{s}'], J[f'knee_{s}'], J[f'ankle_{s}']],
                            ['pelvis', f'thigh_{side}', f'shin_{side}'], [None, f'knee_{side}'], [30, 55])


def wf_leg(side):
    return lambda world: [leg_field(p, side) for p in world]


def wf_pelvis(world):
    out = []
    cx = J['crotch'][0]
    for p in world:
        r = float(rk.smoothstep(cx - 30, cx + 30, p[0]))
        out.append(rk.mix((1 - r, leg_field(p, 'left')), (r, leg_field(p, 'right'))))
    return out


def body_field(p):
    """pelvis -> torso -> chest up the hoodie"""
    lo = J['hem'] + np.array([0, -60.0])
    return rk.chain_weights(p, [lo, J['hem'], J['chest'], J['collar'], J['collar'] + np.array([0, 80.0])],
                            ['pelvis', 'torso', 'chest', 'chest'], [None, None, None], [25, 60, 30])


def wf_torso(world):
    out = []
    for p in world:
        w = body_field(p)
        sl = float(rk.smoothstep(J['shoulder_l'][0] + 40, J['shoulder_l'][0] - 5, p[0])) * \
            float(rk.smoothstep(J['shoulder_l'][1] + 10, J['shoulder_l'][1] - 60, p[1]))
        sr = float(rk.smoothstep(J['shoulder_r'][0] - 40, J['shoulder_r'][0] + 5, p[0])) * \
            float(rk.smoothstep(J['shoulder_r'][1] + 10, J['shoulder_r'][1] - 60, p[1]))
        out.append(rk.mix((1 - .5 * sl - .5 * sr, w), (.5 * sl, {'arm_left_upper': 1}), (.5 * sr, {'arm_right_upper': 1})))
    return out


def wf_hood(world):
    out = []
    for p in world:
        h = float(rk.smoothstep(J['collar'][1] - 10, J['collar'][1] + 90, p[1]))
        out.append(rk.mix((1 - h, {'chest': 1}), (h * .6, {'neck': 1}), (h * .4, {'head': 1})))
    return out


def wf_neck(world):
    lo = J['collar'] + np.array([0, -60.0]); hi = J['neck_top'] + np.array([0, 60.0])
    return [rk.chain_weights(p, [lo, J['collar'], J['neck_top'], hi], ['chest', 'neck', 'head'], [None, None], [20, 25])
            for p in world]


def wf_beanie(world):
    lo = J['brim'] + np.array([0, -120.0])
    return [rk.chain_weights(p, [lo, J['brim'], J['beanie_mid'], J['beanie_top']], ['head', 'beanie', 'beanie_tip'],
                             [None, None], [40, 50]) for p in world]


def arm_field(p, side):
    s = 'l' if side == 'left' else 'r'
    top = J[f'shoulder_{s}'] + np.array([0, 70.0])
    end = J[f'wrist_{s}'] + (J[f'wrist_{s}'] - J[f'elbow_{s}']) / np.linalg.norm(J[f'wrist_{s}'] - J[f'elbow_{s}']) * 80
    return rk.chain_weights(p, [top, J[f'shoulder_{s}'], J[f'elbow_{s}'], J[f'wrist_{s}'], end],
                            ['chest', f'arm_{side}_upper', f'arm_{side}_fore', f'hand_{side}'],
                            [None, f'elbow_{side}', None], [25, 34, 20])


def wf_arm(side):
    return lambda world: [arm_field(p, side) for p in world]


def wf_shoe(side):
    """the shoe rigid on its bone; the free lace end (off the shoe, past its root) on the lace bone"""
    dist, body = SHOE_MASKS[side]
    _, _, R, T = LACE[side]
    ax = np.subtract(T, R).astype(float); ax /= np.hypot(*ax)
    H, Wd = body.shape

    def f(world):
        out = []
        for p in world:
            px, py = F.px(*p)
            xi, yi = int(np.clip(round(px), 0, Wd - 1)), int(np.clip(round(py), 0, H - 1))
            proj = (px - R[0]) * ax[0] + (py - R[1]) * ax[1]
            w = float(rk.smoothstep(0, 30, proj)) * float(rk.smoothstep(16, 4, dist[yi, xi])) * (0.0 if body[yi, xi] else 1.0)
            out.append(rk.mix((1 - w, {f'shoe_{side}': 1}), (w, {f'lace_{side}': 1})))
        return out
    return f


def wf_pocket(world):
    return [rk.mix((.85, {'torso': 1}), (.15, {'pelvis': 1})) for _ in world]


SLOTS = [
    ('hood', 'chest', [('hood', 'hood', 'mesh', wf_hood)]),
    ('neck', 'neck', [('neck', 'neck', 'mesh', wf_neck)]),
    ('pelvis', 'pelvis', [('pelvis', 'pelvis', 'mesh', wf_pelvis)]),
    ('shoe_left', 'shoe_left', [('shoe_left', 'shoe_l_laced', 'mesh', wf_shoe('left'))]),
    ('shoe_right', 'shoe_right', [('shoe_right', 'shoe_r_laced', 'mesh', wf_shoe('right'))]),
    ('shin_left', 'shin_left', [('shin_left', 'shin_l', 'mesh', wf_leg('left'))]),
    ('shin_right', 'shin_right', [('shin_right', 'shin_r', 'mesh', wf_leg('right'))]),
    ('thigh_left', 'thigh_left', [('thigh_left', 'thigh_l', 'mesh', wf_leg('left'))]),
    ('thigh_right', 'thigh_right', [('thigh_right', 'thigh_r', 'mesh', wf_leg('right'))]),
    ('torso', 'torso', [('torso', 'torso', 'mesh', wf_torso)]),
    ('hand_left', 'hand_left', [('hand_left', 'hand_l', 'region', None)]),
    ('hand_right', 'hand_right', [('hand_right', 'hand_r', 'region', None)]),
    ('arm_left_upper', 'arm_left_upper', [('arm_left_upper', 'arm_l_upper', 'mesh', wf_arm('left'))]),
    ('arm_right_upper', 'arm_right_upper', [('arm_right_upper', 'arm_r_upper', 'mesh', wf_arm('right'))]),
    ('arm_left_fore', 'arm_left_fore', [('arm_left_fore', 'arm_l_fore', 'mesh', wf_arm('left'))]),
    ('arm_right_fore', 'arm_right_fore', [('arm_right_fore', 'arm_r_fore', 'mesh', wf_arm('right'))]),
    ('pocket', 'torso', [('pocket', 'pocket', 'mesh', wf_pocket)]),
    ('string_left', 'string_left', [('string_left', 'string_l', 'region', None)]),
    ('string_right', 'string_right', [('string_right', 'string_r', 'region', None)]),
    ('mouth', 'head', [('mouth', 'mouth', 'region', None)]),
    ('jaw', 'jaw', [(f'jaw_{f}', f'jaw_{f}', 'region', None) for f in FACES]),
    ('face', 'head', [(f'face_{f}', f'cranium_{f}', 'region', None) for f in FACES]),
    ('beanie', 'beanie', [('beanie', 'beanie', 'mesh', wf_beanie)]),
    ('cigar', 'cigar', [('cigar', 'cigar', 'region', None)]),
    ('ember_glow', 'ember', [('ember_glow', 'ember_glow', 'region', None)]),
    ('ash_cap', 'ash_cap', [('ash_0', 'ash_0', 'region', None)]),
    ('ash_1', 'ash_1', [('ash_1', 'ash_1', 'region', None)]),
    ('ash_2', 'ash_2', [('ash_2', 'ash_2', 'region', None)]),
    ('ash_3', 'ash_3', [('ash_3', 'ash_3', 'region', None)]),
    ('ash_4', 'ash_4', [('ash_4', 'ash_4', 'region', None)]),
]
SLOT_DEFAULT = {'face': 'face_idle', 'jaw': 'jaw_idle', 'ash_cap': None, 'ash_1': None, 'ash_2': None, 'ash_3': None, 'ash_4': None}
SLOT_EXTRA = {'ember_glow': {'color': 'ffffff00', 'blend': 'additive'}}
SKELETON = {'hash': 'smoke-skull-v2-redo-2026-10-27', 'spine': '4.2.43', 'fps': 30, 'images': './images/', 'audio': '',
            'height': 1465}
EVENTS = {'win_hit': {}, 'big_win_hit': {}, 'land': {}, 'ash_split': {}}
