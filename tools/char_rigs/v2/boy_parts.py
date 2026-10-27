"""SMUKIEZ parts: every part complete, drawn on the master's frame. -> parts/boy/<part>.png + previews."""
import json, os, sys
import numpy as np
import cv2
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pk
import paths

WHO = 'boy'
OUT = os.path.join(paths.WORK, 'parts', WHO)
# back -> front
ORDER = ['neck', 'arm_r_upper', 'arm_r_fore', 'pelvis', 'shoe_l', 'shoe_r', 'shin_l', 'shin_r',
         'thigh_l', 'thigh_r', 'torso', 'arm_l_upper', 'head', 'beanie', 'arm_l_fore', 'cash', 'hand_l', 'hand_r']
ARMS_CASH = ['arm_l_upper', 'arm_l_fore', 'hand_l', 'hand_r', 'cash']
FACES = ['idle', 'anticipation', 'win', 'big_win', 'lose', 'cash_show', 'cash_count']
SKIN_LIT, SKIN_SHADE = (247, 196, 160), (214, 150, 118)


def tube(part, pts, r, lit=SKIN_LIT, shade=SKIN_SHADE, ink_w=5.0, under=None):
    """a capsule chain through pts (radius r) painted lit top-left / shaded bottom-right, outlined"""
    H, W = part.H, part.W; ss = 4
    m = np.zeros((H * ss, W * ss), np.uint8)
    P = (np.array(pts, float) * ss).astype(np.int32)
    for a, b in zip(P[:-1], P[1:]):
        cv2.line(m, tuple(a), tuple(b), 255, int(2 * r * ss))
    for p in P:
        cv2.circle(m, tuple(p), int(r * ss), 255, -1)
    cov = cv2.resize(m.astype(np.float32) / 255., (W, H), interpolation=cv2.INTER_AREA)
    from scipy import ndimage
    inside = cov > .5
    d = ndimage.distance_transform_edt(inside)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # shade across the tube: distance from the upper-left edge
    g = np.clip((xx + yy - (xx + yy)[inside].min()) / max(1, np.ptp((xx + yy)[inside])), 0, 1) if inside.any() else 0
    col = np.array(lit, np.float32) * (1 - g[..., None] * .8) + np.array(shade, np.float32) * (g[..., None] * .8)
    ink = np.clip(ink_w + .5 - d, 0, 1)[..., None]
    col = col * (1 - ink) + np.array((11, 10, 13), np.float32) * ink
    a = cov * (under if under is not None else 1)
    p = np.concatenate([col / 255. * a[..., None], a[..., None]], -1)
    keep = part.img[..., 3:4]
    part.img = part.img + p * (1 - keep)


def build():
    os.makedirs(OUT, exist_ok=True)
    P = {}
    mk = lambda n: pk.Part(WHO, n, ORDER)

    # --- head, per expression: the face from its own image, the crown from the beanie-less edit,
    #     the chin behind the money from the money-less edit
    heads = {}
    for f in FACES:
        h = mk('head')
        h.base('master' if f == 'idle' else f)
        h.ext('nobeanie', removed=['beanie'])
        h.ext('noarms', removed=ARMS_CASH, blend=8)
        # whatever is still empty inside the head (a thin seam where the expression's brim sat a
        # pixel lower than the master's): the master's head, then the beanie-less head
        labm, nm = pk.master_labels(WHO)
        headm = (labm == nm.index('head')) & ~h.rim
        h.paste(pk.src(WHO, 'master'), headm)
        h.ext('nobeanie', removed=['beanie'], under=(h.front & (labm == nm.index('beanie'))) | headm)
        heads[f] = h
    beanie = mk('beanie'); beanie.base()

    neck = mk('neck'); neck.base()
    # the neck: a column of skin from inside the head down into the collar, wide enough that a turn
    # or a dip of the head never opens the space under the chin
    neck.grow([(402, 660), (548, 660), (562, 700), (560, 800), (540, 826), (420, 826), (398, 790)], ink_w=4.5)

    torso = mk('torso'); torso.base()
    torso.ext('noarms', removed=ARMS_CASH, blend=8)
    torso.ext('nocash', removed=['cash'], blend=8)

    # left arm (picture left): upper arm in the sleeve, forearm across the belly, hand on the money
    aU = mk('arm_l_upper'); aU.base()
    aF = mk('arm_l_fore'); aF.base()
    pk.joint(aF, aU, feather=7, band=34)           # elbow: forearm in front, the upper arm runs on under it
    # (the upper arm is in front of the shirt now: the sleeve above it moves with it, so it needs no
    # run-on up into the sleeve)
    hL = mk('hand_l'); hL.base()
    pk.joint(hL, aF, feather=7, band=40)           # wrist: the hand in front, the forearm runs on under it
    hR = mk('hand_r'); hR.base()

    # right arm (picture right): hidden behind the money - a short sleeve-to-wrist limb
    aRU = mk('arm_r_upper'); aRF = mk('arm_r_fore')
    tube(aRU, [(622, 800), (626, 880)], 27, under=aRU.front)
    tube(aRF, [(626, 880), (668, 925)], 25, under=aRF.front)

    # legs: jeans top under the hem from the crop-top edit; thigh/shin cut through the denim
    pelvis = mk('pelvis'); pelvis.base()
    pelvis.ext('croptop', removed=['torso'], clip=[(240, 975), (720, 975), (720, 1110), (240, 1110)])
    legs = {}
    for s in ('l', 'r'):
        th = mk(f'thigh_{s}'); th.base()
        th.ext('croptop', removed=['torso'], clip=[(230, 975), (720, 975), (720, 1120), (230, 1120)])
        sh = mk(f'shin_{s}'); sh.base()
        sho = mk(f'shoe_{s}'); sho.base()
        sho.ext('shortjeans', removed=['shin_l', 'shin_r'],
                clip=[(170, 1175), (880, 1175), (880, 1340), (170, 1340)])
        legs[s] = (th, sh, sho)
    for s in ('l', 'r'):
        th, sh, sho = legs[s]
        pk.joint(th, sh, feather=8, band=42)        # knee: thigh in front, shin runs on under it
        pk.joint(th, pelvis, feather=8, band=36)    # hip: thigh in front, pelvis runs on under it

    P.update(neck=neck, torso=torso, arm_l_upper=aU, arm_l_fore=aF, hand_l=hL, hand_r=hR, arm_r_upper=aRU,
             arm_r_fore=aRF, pelvis=pelvis, beanie=beanie)
    for s in ('l', 'r'):
        P[f'thigh_{s}'], P[f'shin_{s}'], P[f'shoe_{s}'] = legs[s]
    # the edits' SMUKIEZ print sits a little to the right of the master's: under the hand it read
    # as a doubled letter - hidden pixels of white print on the shirt are repainted as cloth
    torso.inpaint_hidden(lambda rgb, lum: lum > 150)
    for k, v in P.items():
        v.solidify(); v.runon(); v.solidify(); v.clean()
        v.save(os.path.join(OUT, k + '.png'))
    for f in FACES[1:]:
        pk.keep_edge(heads[f], heads['idle'], ['beanie'], band=10)
    for f, h in heads.items():
        h.solidify(); h.runon(); h.solidify(); h.clean()
        h.save(os.path.join(OUT, f'head_{f}.png'))
    print('parts', sorted(P), 'faces', FACES)
    return P, heads


if __name__ == '__main__':
    build()
