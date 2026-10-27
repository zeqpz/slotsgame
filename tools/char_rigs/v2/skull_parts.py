"""SMOKE SKULL parts: every part complete, drawn on the master's frame. -> parts/skull/<part>.png"""
import json, os, sys
import numpy as np
import cv2
from PIL import Image
from scipy import ndimage
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pk
import paths

WHO = 'skull'
OUT = os.path.join(paths.WORK, 'parts', WHO)
ORDER = ['hood', 'neck', 'pelvis', 'shoe_l', 'shoe_r', 'lace_l_up', 'lace_r_right',
         'shin_l', 'shin_r', 'thigh_l', 'thigh_r', 'torso', 'hand_l', 'hand_r', 'arm_l_upper', 'arm_r_upper',
         'arm_l_fore', 'arm_r_fore', 'pocket', 'strings', 'string_l', 'string_r', 'mouth', 'jaw', 'cranium', 'beanie',
         'cigar']
FACES = ['idle', 'anticipation', 'win', 'big_win', 'lose']
ARMS = ['arm_l_upper', 'arm_l_fore', 'arm_r_upper', 'arm_r_fore', 'pocket', 'strings', 'string_l', 'string_r']
HINGE0 = (612, 585)
ABOVE_BITE = [(150, 300), (900, 300), (900, 500), (830, 500), (800, 520), (770, 545), (745, 580), (710, 598), (670, 600),
              (630, 597), (606, 600), (598, 625), (580, 652), (450, 657), (330, 657), (150, 655)]
BELOW_BITE = [(150, 645), (330, 647), (450, 647), (580, 642), (596, 615), (604, 590), (630, 587), (670, 590), (710, 588),
              (740, 570), (762, 538), (792, 512), (900, 490), (900, 800), (150, 800)]


def jaw_unrotate():
    """The jaw-open edit with its lower jaw turned back shut about the hinge, so its jaw lines up with
    the master's: the jaw's hidden top (behind the upper teeth and the cigar) comes from it."""
    lab, names = pk.master_labels(WHO)
    J = lab == names.index('jaw')
    J = ndimage.binary_erosion(J, iterations=4)
    J[:, :420] = False                                  # not under/near the cigar
    M = pk.src(WHO, 'master'); E = pk.src(WHO, 'jawopen')
    gm = pk.premul(M)[..., :3].mean(-1)
    H, W = J.shape
    best = None
    X0, Y0, X1, Y1 = 280, 480, 720, 820                 # work on the jaw's neighbourhood only
    gmc = gm[Y0:Y1, X0:X1]; Jc = J[Y0:Y1, X0:X1]; Ec = pk.premul(E)[..., :3].mean(-1)
    for hx in range(HINGE0[0] - 20, HINGE0[0] + 21, 5):
        for hy in range(HINGE0[1] - 20, HINGE0[1] + 21, 5):
            for th in np.arange(-2, 14.01, .5):
                R = cv2.getRotationMatrix2D((hx - X0, hy - Y0), -th, 1.0)
                g = cv2.warpAffine(Ec[Y0:Y1, X0:X1], R, (X1 - X0, Y1 - Y0), flags=cv2.INTER_LINEAR)
                err = np.abs(g[Jc] - gmc[Jc]).mean()
                if best is None or err < best[0]:
                    best = (err, hx, hy, th)
    err, hx, hy, th = best
    print('jaw-open edit: hinge (%d, %d), opened %.1f deg, residual %.4f' % (hx, hy, th, err))
    R = cv2.getRotationMatrix2D((hx, hy), -th, 1.0)
    out = cv2.warpAffine(E, R, (W, H), flags=cv2.INTER_CUBIC, borderValue=(0, 0, 0, 0))
    Image.fromarray(out.clip(0, 255).astype(np.uint8), 'RGBA').save(paths.aligned(WHO, 'jawshut'))
    pk._cache.pop((WHO, 'jawshut'), None)
    return (hx, hy, th)


def vertebrae(part):
    """The bony neck from the no-head edit (which redrew the body lower): the column of vertebrae,
    cut out of the dark hood opening, moved so its foot sits in the master's collar."""
    raw = pk.fix_alpha(pk.load_rgba(paths.art('skull', 'edits/nohead')))
    x0, y0, x1, y1 = 425, 425, 580, 612
    crop = raw[y0:y1, x0:x1].copy()
    lum = crop[..., :3].mean(-1)
    bone = (lum > 110) & (crop[..., 3] > 127)
    bone = ndimage.binary_opening(bone, iterations=1)
    lab, n = ndimage.label(bone)
    if n:
        areas = ndimage.sum(bone, lab, range(1, n + 1))
        bone = np.isin(lab, 1 + np.nonzero(areas > 150)[0])
    shape = ndimage.binary_fill_holes(ndimage.binary_dilation(bone, iterations=6))
    cov = cv2.GaussianBlur(shape.astype(np.float32), (0, 0), .8)
    crop[..., 3] = (cov * 255) * (crop[..., 3] / 255.)
    dx, dy = 5, 140                                      # raw (500, 605) -> master (505, 745)
    H, W = part.H, part.W
    big = np.zeros((H, W, 4), np.float32)
    big[y0 + dy:y1 + dy, x0 + dx:x1 + dx] = crop
    m = (big[..., 3] > 2) & part.front
    p = pk.premul(big)
    part.img[m] = p[m]
    return int(m.sum())


def flat_shape(part, poly, rgb, ink_w=0.0):
    """a flat colour shape (hidden backings: the mouth's inside)"""
    cov = pk.poly_mask((part.H, part.W), poly, ss=4)
    cov = cov * part.front
    col = np.array(rgb, np.float32) / 255.
    p = np.concatenate([np.broadcast_to(col, (part.H, part.W, 3)) * cov[..., None], cov[..., None]], -1)
    part.img = part.img + p * (1 - part.img[..., 3:4])


def build():
    os.makedirs(OUT, exist_ok=True)
    mk = lambda n: pk.Part(WHO, n, ORDER)
    P = {}
    hinge = jaw_unrotate()

    # --- head
    faces = {}
    for f in FACES:
        c = mk('cranium')
        c.base('master' if f == 'idle' else f, removed=[])
        c.ext('nobeanie', removed=['beanie'])
        c.ext('jawopen', removed=['cigar', 'jaw'], clip=ABOVE_BITE)   # the upper teeth behind the cigar
        faces[f] = c
    # one jaw per face, from that face's own drawing (an expression redraws the grin as well as the eyes:
    # its own jaw keeps the drawing whole), its hidden top from the jaw-shut edit
    jaws = {}
    for f in FACES:
        jw = mk('jaw')
        jw.base('master' if f == 'idle' else f)
        jw.ext('jawshut', removed=['cigar', 'cranium'], clip=BELOW_BITE)
        jaws[f] = jw
    jaw = jaws['idle']
    mouth = mk('mouth')
    flat_shape(mouth, [(330, 590), (600, 585), (640, 640), (630, 705), (330, 705)], (22, 20, 25))
    beanie = mk('beanie'); beanie.base()
    cigar = mk('cigar'); cigar.base()

    # --- neck and hood: the vertebrae, and the hood's dark inside behind the jaw
    neck = mk('neck'); vertebrae(neck)
    hood = mk('hood'); hood.base()
    # the hood's dark inside, behind the jaw and the cheek (the whole cheek is skull since the bite runs
    # along the cheekbone): whatever the head does, the opening shows the inside of the hood
    hood.grow([(318, 650), (430, 600), (560, 580), (650, 560), (720, 530), (790, 505), (850, 495), (865, 560),
               (830, 640), (760, 720), (636, 792), (318, 806)], ink_w=0, fill_rgb=(28, 28, 33))

    # --- hoodie: body complete behind sleeves, pocket and strings (behind the strings it is repainted
    #     from the master, the edit's logo sits elsewhere)
    torso = mk('torso'); torso.base()
    lab, names = pk.master_labels(WHO)
    strings = np.isin(lab, [names.index(n) for n in ('strings', 'string_l', 'string_r')])
    strings = cv2.dilate(strings.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    torso.ext('noarms', removed=ARMS, under=torso.front & ~strings)
    torso.fill_inpaint(strings)
    torso.inpaint_hidden(lambda rgb, lum: lum > 150)

    arms = {}
    for s in ('l', 'r'):
        up = mk(f'arm_{s}_upper'); up.base()
        fo = mk(f'arm_{s}_fore'); fo.base()
        fo.ext('nopocket', removed=['pocket'], clip=([(330, 850), (480, 850), (480, 1000), (330, 1000)] if s == 'l'
                                                       else [(520, 850), (650, 850), (650, 1000), (520, 1000)]))
        pk.joint(fo, up, feather=8, band=40)
        arms[s] = (up, fo)
    # bony hands from the pocket-less edit, split down the middle (they are crossed, inside the pocket)
    hands = {}
    for s, poly in (('l', [(395, 880), (500, 880), (500, 1010), (395, 1010)]),
                    ('r', [(500, 880), (610, 880), (610, 1010), (500, 1010)])):
        h = mk(f'hand_{s}')
        h.ext('nopocket', removed=['pocket'], force=[(f'hand_{s}', poly)], labels=[f'hand_{s}'])
        hands[s] = h
    pocket = mk('pocket'); pocket.base()
    strs = {}
    for s in ('l', 'r'):
        st = mk(f'string_{s}'); st.base(labels=[f'string_{s}', 'strings'] if s == 'r' else [f'string_{s}'])
        strs[s] = st

    # --- legs
    pelvis = mk('pelvis'); pelvis.base()
    pelvis.ext('croptop', removed=['torso'], clip=[(330, 950), (700, 950), (700, 1080), (330, 1080)])
    legs = {}
    for s in ('l', 'r'):
        th = mk(f'thigh_{s}'); th.base()
        th.ext('croptop', removed=['torso'], clip=[(330, 950), (700, 950), (700, 1080), (330, 1080)])
        sh = mk(f'shin_{s}'); sh.base()
        sho = mk(f'shoe_{s}'); sho.base()
        sho.ext('shortpants', removed=['shin_l', 'shin_r', 'thigh_l', 'thigh_r'],
                clip=[(150, 1150), (800, 1150), (800, 1330), (150, 1330)])
        legs[s] = (th, sh, sho)
    for s in ('l', 'r'):
        th, sh, sho = legs[s]
        pk.joint(th, sh, feather=8, band=40)
        pk.joint(th, pelvis, feather=8, band=34)
    laces = {}
    for n in ('lace_l_up', 'lace_r_right'):
        l = mk(n); l.base(); laces[n] = l
    # the shoes under their loose laces: repainted from the shoe around them
    lace_px = np.isin(lab, [names.index(n) for n in laces])
    lace_px = cv2.dilate(lace_px.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    for s in ('l', 'r'):
        sho = legs[s][2]
        own = cv2.dilate((lab == names.index(f'shoe_{s}')).astype(np.uint8), np.ones((31, 31), np.uint8)) > 0
        sho.fill_inpaint(lace_px & own & ndimage.binary_fill_holes(cv2.dilate((lab == names.index(f'shoe_{s}')).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0))

    P.update(mouth=mouth, beanie=beanie, cigar=cigar, neck=neck, hood=hood, torso=torso, pocket=pocket,
             pelvis=pelvis)
    for s in ('l', 'r'):
        P[f'arm_{s}_upper'], P[f'arm_{s}_fore'] = arms[s]
        P[f'hand_{s}'] = hands[s]; P[f'string_{s}'] = strs[s]
        P[f'thigh_{s}'], P[f'shin_{s}'], P[f'shoe_{s}'] = legs[s]
    P.update(laces)
    for k, v in P.items():
        v.solidify(); v.runon(); v.solidify(); v.clean(); v.save(os.path.join(OUT, k + '.png'))
    for f in FACES[1:]:
        pk.keep_edge(faces[f], faces['idle'], ['beanie'], band=14)
    for f, jw in jaws.items():
        jw.solidify(); jw.runon(); jw.solidify(); jw.clean(); jw.save(os.path.join(OUT, f'jaw_{f}.png'))
    for f, c in faces.items():
        c.solidify(); c.runon(); c.solidify(); c.clean(); c.save(os.path.join(OUT, f'cranium_{f}.png'))
    json.dump(dict(jaw_hinge=hinge), open(os.path.join(OUT, 'skull_meta.json'), 'w'))
    print('parts', sorted(P), 'faces', FACES)


if __name__ == '__main__':
    build()
