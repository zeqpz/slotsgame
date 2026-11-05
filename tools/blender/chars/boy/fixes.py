"""Per-joint clean-up of the boy's parts for a cutout rig whose pieces turn at their joints (called by prep_parts.py).

The v2 cut gave every part a soft "run-on" halo under the parts in front (a blurred, fading smear of its own
colours) - fine for Spine's weighted meshes, a dirty smudge as soon as a rigid piece turns and shows it. Here:
  clean     every part keeps its solid paint (its own drawing + the solid fills from the edits) with a crisp
            1 px edge; the halos go. Its outer outline (the drawing's own anti-aliased silhouette) is kept as drawn
  joints    what a back part keeps hidden under a front part is limited to what stays under that front part (or
            inside its own outline) through the joint's whole range of turn - nothing pokes out past the limb's
            outline when it bends - plus a round cap at the pivot (filled with the drawing that lies there), so the
            outside of a bent knee / elbow is a rounded joint, never a notch or a gap
  print     the T-shirt's SMUKIEZ print, half lost under the hand in the old cut, put back from the drawing and the
            hands-removed edit
"""
import math
import numpy as np
import cv2
from scipy import ndimage

LAB = {"neck": "neck", "torso": "torso", "hand_l": "hand_l", "hand_r": "hand_r", "pelvis": "pelvis",
       "shoe_l": "shoe_l", "shoe_r": "shoe_r", "thigh_l": "thigh_l", "shin_l": "shin_l", "thigh_r": "thigh_r",
       "shin_r": "shin_r", "arm_l_upper": "arm_l_upper", "arm_l_fore": "arm_l_fore", "beanie": "beanie"}

# (back part, front part, pivot (master px), the front part's turn in the back part's frame over the clips (deg,
# from - to: the knees and hips bend one way only; measured from the rendered clips' pose report), round cap?)
JOINTS = [
    ("thigh_l", "torso", (395, 1042), (-4, 35), False),
    ("thigh_r", "torso", (548, 1048), (-31, 4), False),
    ("arm_l_fore", "hand_l", (456, 928), (-10, 10), True),
]
# round joints (front part, back part, pivot, the back part's far end, the front part's far end): the classic cutout
# joint - the back piece ends in a round cap about the pivot (filled with the drawing that lies there, outlined
# where it is never seen at rest), the front piece keeps only what lies on its side of the joint line or inside
# the cap, and the bit of it past the line (the corners of its cut end) goes over to the back piece. Turning
# about the pivot, the cap stays under the front piece, the corners travel with the piece they now belong to:
# no bite out of the outline, no gap, nothing smeared
ROUND = [("thigh_l", "shin_l", (356, 1158), (338, 1278), (395, 1042)),
         ("thigh_r", "shin_r", (580, 1168), (585, 1300), (548, 1048)),
         ("arm_l_fore", "arm_l_upper", (300, 932), (318, 800), (456, 928))]
CLOSE = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (29, 29))     # the inside corner of a bent joint counts as limb


def rot(mask, pivot, deg):
    M = cv2.getRotationMatrix2D((float(pivot[0]), float(pivot[1])), deg, 1.0)
    return cv2.warpAffine(mask.astype(np.uint8), M, (mask.shape[1], mask.shape[0]), flags=cv2.INTER_NEAREST) > 0


def soft(mask, sigma=.6):
    return np.clip(cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigma) * 1.0, 0, 1)


PRINT = dict(font="frontend/assets/bromo.otf", text="",              # "" = no print: a plain black tee centre=(455, 845), width=112, angle=14.0, tracking=.08,
             arc=2.5, taper=.07, colour=(238, 237, 232))


def plain_chest(t, region):
    """the chest where the print was (and the edits' traces round it, under the thumb): rebuilt as plain cloth -
    the shirt's own light and folds carried in smoothly from the cloth round the patch, and the fabric's fine
    grain at its own strength - so no ghost of letters and no flat blur patch is left"""
    H, W = t.shape[:2]
    poly = np.array([(392, 852), (418, 826), (470, 816), (540, 812), (566, 826), (568, 872), (524, 896),
                     (452, 904), (398, 890)], np.int32)
    pm = np.zeros((H, W), np.uint8)
    cv2.fillPoly(pm, [poly], 1)
    patch = (pm > 0) & region
    rgb = t[..., :3].astype(np.float32)
    lum = rgb.mean(-1)
    ring = ndimage.binary_dilation(patch, iterations=26) & ~ndimage.binary_dilation(patch, iterations=3) & region
    ring &= np.abs(lum - cv2.GaussianBlur(lum, (0, 0), 6)) < .08         # plain cloth, not seams or ink
    # the light and the folds: a smooth surface through the cloth round the patch (normalised convolution, wide
    # then narrower so the gradients carry in)
    low = np.zeros_like(rgb)
    w8 = ring.astype(np.float32)
    for sig in (22, 12):
        num = cv2.GaussianBlur(rgb * w8[..., None], (0, 0), sig)
        den = cv2.GaussianBlur(w8, (0, 0), sig)[..., None]
        est = num / np.maximum(den, 1e-4)
        low = np.where(den > .02, est, low) if sig == 22 else np.where(den > .08, .5 * est + .5 * low, low)
    # the grain: the cloth's own fine texture (high-pass) at its measured strength, as fine noise
    hp = lum - cv2.GaussianBlur(lum, (0, 0), 1.4)
    rnd = np.random.RandomState(11).normal(0, 1, (H, W)).astype(np.float32)
    rnd = cv2.GaussianBlur(rnd, (0, 0), .55)
    rnd *= hp[ring].std() / max(rnd[ring].std(), 1e-6)
    fill = np.clip(low + rnd[..., None], 0, 1)
    k = cv2.GaussianBlur(patch.astype(np.float32), (0, 0), 3.0)[..., None] * patch[..., None]
    k = np.clip(cv2.GaussianBlur(patch.astype(np.float32), (0, 0), 3.0) * 1.6 - .3, 0, 1)[..., None]
    t[..., :3] = np.where(region[..., None], rgb * (1 - k) + fill * k, rgb)


def print_shirt(t, region):
    """repaint the chest print on the torso part (master px, premultiplied-free RGBA floats)"""
    import os
    from PIL import Image, ImageDraw, ImageFont
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    H, W = t.shape[:2]
    rgb8 = (t[..., :3] * 255 + .5).clip(0, 255).astype(np.uint8)
    lum = t[..., :3].mean(-1)
    # 1. the old letters out: everything clearly lighter than the cloth round it in the print's area
    area = np.zeros((H, W), bool); area[788:900, 375:575] = True
    cloth_lum = np.percentile(lum[area & region], 50)
    old = area & region & (lum > cloth_lum + .1)
    old = ndimage.binary_dilation(old, iterations=3) & region
    rgb8 = cv2.inpaint(np.ascontiguousarray(rgb8[..., ::-1]), old.astype(np.uint8) * 255, 6, cv2.INPAINT_TELEA)[..., ::-1]
    base = rgb8.astype(np.float32) / 255.
    # the cloth's grain back over the painted-out patch (the inpaint is smooth): fine noise at the fabric's own
    # strength, measured on the plain cloth round it
    grain = lum - cv2.GaussianBlur(lum.astype(np.float32), (0, 0), 1.6)
    plain = area & region & ~ndimage.binary_dilation(old, iterations=4)
    rnd = np.random.RandomState(5).normal(0, 1, (H, W)).astype(np.float32)
    rnd = cv2.GaussianBlur(rnd, (0, 0), .6)
    rnd *= grain[plain].std() / max(rnd[plain].std(), 1e-6)
    grain = np.where(ndimage.binary_dilation(old, iterations=2), rnd, grain)
    base[old] += grain[old][:, None]
    if not PRINT.get("text"):                       # a plain tee (the owner: "get rid of the text on the shirt")
        plain_chest(t, region)
        return
    # 2. the new letters, set 8x large and warped onto the chest
    SS = 8
    font = ImageFont.truetype(os.path.join(root, PRINT["font"]), 60 * SS)
    track = PRINT.get("tracking", .07) * 60 * SS                # a little air between the letters
    adv = [font.getlength(ch) for ch in PRINT["text"]]
    x0, y0, x1, y1 = font.getbbox(PRINT["text"])
    wid = int(sum(adv) + track * (len(adv) - 1)) + (x1 - x0) // 4
    im = Image.new("L", (wid + 8 * SS, y1 - y0 + 8 * SS), 0)
    dr = ImageDraw.Draw(im)
    xp = 4 * SS - x0
    for ch, w_ in zip(PRINT["text"], adv):
        dr.text((xp, 4 * SS - y0), ch, font=font, fill=255)
        xp += w_ + track
    im = im.crop(im.getbbox())
    im2 = Image.new("L", (im.width + 8 * SS, im.height + 8 * SS), 0); im2.paste(im, (4 * SS, 4 * SS)); im = im2
    txt = np.asarray(im).astype(np.float32) / 255.
    th, tw = txt.shape
    hw = PRINT["width"] / 2
    hh = hw * th / tw
    cx, cy = PRINT["centre"]
    a = math.radians(PRINT["angle"])
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    dx, dy = xs - cx, ys - cy
    qx = dx * math.cos(a) - dy * math.sin(a)                   # into the print's own frame (it rises to the right)
    qy = dx * math.sin(a) + dy * math.cos(a)
    u = qx / hw                                               # -1 .. 1 along it
    qy = qy + PRINT["arc"] * (1 - u * u)                      # the chest's curve: the middle a touch lower
    sc = 1 - PRINT["taper"] * (u + 1) / 2                     # the far end turns away a little
    # sampled 4x finer than the master's pixels, then averaged down: clean anti-aliased edges
    R4 = 4
    bx0, by0, bx1, by1 = int(cx - hw - 20), int(cy - hw * .6), int(cx + hw + 20), int(cy + hw * .6)
    gy, gx = np.mgrid[by0 * R4:by1 * R4, bx0 * R4:bx1 * R4].astype(np.float32)
    gx, gy = (gx + .5) / R4 - .5, (gy + .5) / R4 - .5
    ddx, ddy = gx - cx, gy - cy
    px_ = ddx * math.cos(a) - ddy * math.sin(a)
    py_ = ddx * math.sin(a) + ddy * math.cos(a)
    uu = px_ / hw
    py_ = py_ - PRINT["arc"] * (1 - np.clip(uu, -1, 1) ** 2)
    ss = 1 - PRINT["taper"] * (uu + 1) / 2
    mx = ((uu + 1) / 2 * tw).astype(np.float32)
    my = ((py_ / (hh * ss) + 1) / 2 * th).astype(np.float32)
    txt_s = cv2.GaussianBlur(txt, (0, 0), tw / (2 * hw * R4) * .5)
    big = cv2.remap(txt_s, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    small = cv2.resize(big, ((bx1 - bx0), (by1 - by0)), interpolation=cv2.INTER_AREA)
    cov = np.zeros((H, W), np.float32)
    cov[by0:by1, bx0:bx1] = small
    cov *= region
    # 3. printed on the cloth: the shirt's folds and light over it, its grain through it
    lumc = base.mean(-1)
    shade_big = cv2.GaussianBlur(lumc, (0, 0), 18)
    shade = cv2.GaussianBlur(lumc, (0, 0), 4.0) / np.maximum(shade_big, 1e-3)
    shade = np.clip(1 + .8 * (shade - 1), .84, 1.08)              # the folds, softened
    light = np.clip(1 + 1.0 * (shade_big - np.median(shade_big[area & region])), .88, 1.04)
    col = np.array(PRINT["colour"], np.float32) / 255. * (shade * light)[..., None] + grain[..., None] * .7
    col = np.clip(col, 0, 1)
    k = (cov * .97)[..., None]
    out = base * (1 - k) + col * k
    t[..., :3] = np.where(region[..., None], out, t[..., :3])
    if os.environ.get("BOY_PRINT_DEBUG"):
        d = os.environ["BOY_PRINT_DEBUG"]
        Image.fromarray((cov[780:900, 370:580] * 255).astype(np.uint8)).save(d + "_cov.png")
        Image.fromarray((old[780:900, 370:580] * 255).astype(np.uint8)).save(d + "_old.png")
        Image.fromarray((base[780:900, 370:580] * 255).clip(0, 255).astype(np.uint8)).save(d + "_base.png")


def apply(P, heads, M, labs, aligned):
    lab, names = labs
    own = {n: ndimage.binary_dilation(lab == names.index(l), iterations=1) for n, l in LAB.items() if l in names}
    outline = ndimage.binary_dilation(M[..., 3] < .98, iterations=1)       # the drawing's own soft silhouette

    def clean(img, own_mask):
        a = img[..., 3]
        hard = soft(a > .9)
        keep_soft = (own_mask & outline) if own_mask is not None else outline
        img[..., 3] = np.where(keep_soft, a, hard)
        img[img[..., 3] < 1 / 255.] = 0

    for n, img in P.items():
        clean(img, own.get(n))
    for f, img in heads.items():
        clean(img, None)
    # nothing hanging under the chin (the old cut left a smear of neck and collar there, under the money): the
    # chin's outline is read off the arms-removed edit (all of it drawn there, no money in front), column by column
    na = aligned("noarms")
    hl = lab == names.index("head")
    chin = np.full(lab.shape[1], -1)
    for x in range(300, 720):
        col = hl[:, x]
        if not col.any():
            continue
        y = int(np.nonzero(col)[0].max())                     # the lowest face pixel the drawing shows here
        y = max(y - 6, 600)
        dark = (na[y:y + 140, x, :3].max(-1) < .25) & (na[y:y + 140, x, 3] > .5)
        if not dark.any():
            continue
        i = int(np.argmax(dark))
        while i < len(dark) and dark[i]:
            i += 1
        chin[x] = y + i
    xs_ = np.nonzero(chin >= 0)[0]
    # a smooth chin: a running median, filled in between
    if len(xs_):
        from scipy.ndimage import median_filter
        cc = np.interp(np.arange(lab.shape[1]), xs_, chin[xs_])
        cc = median_filter(cc, 15)
        yy0 = np.mgrid[0:lab.shape[0], 0:lab.shape[1]][0]
        below = (yy0 > cc[None, :] + 1) & (np.arange(lab.shape[1])[None, :] >= xs_.min()) & (np.arange(lab.shape[1])[None, :] <= xs_.max())
        # the new chin edge: smoothed, and inked like the rest of the outline
        keep_c = ~below
        sm = cv2.GaussianBlur(keep_c.astype(np.float32), (0, 0), 3.0) > .5
        below = ~(sm & keep_c)
        edge_d = ndimage.distance_transform_edt(~below)
        chin_ink = (edge_d <= 4) & (yy0 > 640) & ~below
        for f, img in heads.items():
            img[..., 3] *= 1 - soft(below, .6)
            img[chin_ink & (img[..., 3] > .5), :3] = ink if False else np.array([11, 10, 13]) / 255.
            green = (img[..., 1] > img[..., 0] + .08) & (img[..., 1] > img[..., 2] + .06) & (img[..., 3] > 0)
            img[..., 3] *= 1 - soft(ndimage.binary_dilation(green, iterations=1), .6)
            img[img[..., 3] < 1 / 255.] = 0

    # the T-shirt: the drawing where it shows; everywhere the arms, hands and money hide it, the arms-removed
    # edit (the whole shirt, its print and right sleeve, no skin, no bills) - and nothing past the shirt's outline
    t = P["torso"]
    na = aligned("noarms")
    skin = (na[..., 0] > .55) & (na[..., 0] > na[..., 2] + .15)
    shirt = lab == names.index("torso")
    head = ndimage.binary_dilation(lab == names.index("head"), iterations=4)
    cloth = (na[..., 3] > .5) & ~skin & ~head
    cloth = ndimage.binary_opening(cloth, iterations=1)
    collar_box = np.zeros_like(shirt); collar_box[700:830, 470:690] = True       # the shirt round the collar on the
    arm_zone = ndimage.binary_dilation(np.isin(lab, [names.index(n) for n in ("arm_l_upper", "arm_l_fore", "hand_l")]),
                                       iterations=25) & (np.mgrid[0:lab.shape[0], 0:lab.shape[1]][0] < 1030)
    region = ((t[..., 3] > .5) | collar_box | arm_zone) & (shirt | cloth)       # money side, all of it; and the
                                                                                # shirt's whole side behind the arm
    holes_ = ndimage.binary_fill_holes(region) & ~region                      # only pinholes are filled
    hl_, hk_ = ndimage.label(holes_)
    if hk_:
        hs_ = ndimage.sum(holes_, hl_, range(1, hk_ + 1))
        region |= np.isin(hl_, 1 + np.nonzero(hs_ < 400)[0])
    # under the head only what stays under it as the head turns (no collar edge peeking past the chin)
    hd = heads["idle"][..., 3] > .5
    under_head = np.ones_like(hd)
    for d in np.linspace(-10, 10, 9):
        under_head &= rot(hd, (462, 712), d)
    region &= shirt | under_head | (np.mgrid[0:lab.shape[0], 0:lab.shape[1]][0] > 790) | (collar_box & cloth)
    # not the chin's outline and neck shadow the edit drew above the collar on the money side
    nb = np.zeros_like(region); nb[690:768, 500:660] = True
    region &= ~(nb & ~shirt & (na[..., :3].max(-1) < .15))
    lab_r, k_r = ndimage.label(region)
    if k_r > 1:
        sz = ndimage.sum(region, lab_r, range(1, k_r + 1))
        region = lab_r == 1 + int(np.argmax(sz))
    hid = region & ~shirt
    t[hid, :3] = na[hid, :3]
    # anything skin-toned or inky-orange left in the hidden shirt (the edit's traces of the arms): the nearest cloth
    near_arm = ndimage.binary_dilation(np.isin(lab, [names.index(n) for n in ("arm_l_upper", "arm_l_fore", "hand_l", "hand_r", "cash")]), iterations=10)
    zone = hid | (region & near_arm)
    tint = zone & ((t[..., 0] > t[..., 2] + .07) | (t[..., 0] > .5) | (t[..., 1] > t[..., 0] + .06))
    tint = ndimage.binary_dilation(tint, iterations=2) & zone
    if tint.any():
        okc = region & ~tint & ~((t[..., 0] > t[..., 2] + .07) | (t[..., 0] > .5) | (t[..., 1] > t[..., 0] + .06))
        _, (iy, ix) = ndimage.distance_transform_edt(~okc, return_indices=True)
        t[tint, :3] = t[iy[tint], ix[tint], :3]
    # the print: the drawing's AI-made lettering (uneven, half-formed letters - the owner: "looks like AI") is
    # painted out, and a clean SMUKIEZ set in the brand's street face (frontend/assets/bromo.otf) is printed on
    # the shirt in its place - on the chest's slant and curve, the shirt's folds and fabric shading over it
    print_shirt(t, region)
    t[..., 3] = np.where(shirt & outline, t[..., 3], soft(region))
    t[t[..., 3] < 1 / 255.] = 0

    # the hidden right arm (two skin tubes) and the neck column: cut to their own ink outline
    neck_poly = np.zeros(lab.shape, np.uint8)
    cv2.fillPoly(neck_poly, [np.array([(402, 660), (560, 660), (578, 700), (578, 800), (556, 826), (420, 826), (398, 790)], np.int32)], 1)
    for n in ("arm_r_upper", "arm_r_fore", "neck"):
        img = P[n]
        ink = (img[..., 3] > .5) & (img[..., :3].max(-1) < .25)
        inside = neck_poly > 0 if n == "neck" else ndimage.binary_fill_holes(ndimage.binary_closing(ink, iterations=2))
        inside = ndimage.binary_dilation(inside, iterations=1)
        holes = inside & (img[..., 3] < .9)
        if holes.any():
            okc = (img[..., 3] > .9) & inside & ~ink
            _, (iy, ix) = ndimage.distance_transform_edt(~okc, return_indices=True)
            img[holes, :3] = img[iy[holes], ix[holes], :3]
            img[holes, 3] = 1
        img[..., 3] = np.minimum(img[..., 3], soft(inside))
        img[img[..., 3] < 1 / 255.] = 0
        if n == "neck":                                   # its skin as the arms-removed edit paints the neck; no smudges
            core = ndimage.binary_erosion(inside, iterations=6)
            sk = core & ~own["neck"] & (na[..., 3] > .9) & (na[..., :3].max(-1) > .3)
            img[sk, :3] = na[sk, :3]
            dirt = core & ~sk & ~own["neck"]
            if dirt.any():
                okc = core & ~dirt
                _, (iy, ix) = ndimage.distance_transform_edt(~okc, return_indices=True)
                img[dirt, :3] = img[iy[dirt], ix[dirt], :3]

    # the round joints
    yy, xx = np.mgrid[0:lab.shape[0], 0:lab.shape[1]].astype(np.float32)
    ink = np.array([11, 10, 13]) / 255.
    for fn, bn, piv, bend, fend in ROUND:
        F, B = P[fn], P[bn]
        unit = lambda v: np.array(v, np.float32) / np.linalg.norm(v)
        n = unit(unit(np.subtract(bend, piv)) - unit(np.subtract(fend, piv)))      # toward the back piece
        side = (xx - piv[0]) * n[0] + (yy - piv[1]) * n[1]
        Fs = F[..., 3] > .5
        Bo = own[bn]
        limb = ndimage.binary_fill_holes(ndimage.binary_closing(own[fn] | Bo, iterations=3))
        r = ndimage.distance_transform_edt(limb)[piv[1], piv[0]] - 2
        disc = (xx - piv[0]) ** 2 + (yy - piv[1]) ** 2 <= r * r
        move = Fs & (side > 0) & ~disc
        need = (move | disc) & (B[..., 3] < .9) & (M[..., 3] > .5)
        B[need, :3] = M[need, :3]
        B[..., 3] = np.where(need, np.maximum(B[..., 3], M[..., 3]), B[..., 3])
        F[..., 3] *= 1 - soft(move)
        Fnew = ndimage.binary_erosion(F[..., 3] > .97, iterations=3)
        drop = (side <= 0) & ~disc & ~ndimage.binary_dilation(Bo, iterations=2) & Fnew
        B[..., 3] *= 1 - soft(drop)
        ring = disc & ~ndimage.binary_erosion(disc, iterations=4) & (side < -2) & ~ndimage.binary_dilation(Bo, iterations=3)
        B[ring, :3] = ink
        # no thin slivers of outline left standing off the back piece (they would stick out as it turns)
        body = cv2.morphologyEx((B[..., 3] > .5).astype(np.uint8), cv2.MORPH_OPEN,
                                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))) > 0
        B[..., 3] *= soft(body | Bo, .6)
        # the front piece's cut end: a clean edge (the old feathered cut left a frayed fringe at the threshold)
        m = F[..., 3] > .5
        sm = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 2.0) > .5
        F[..., 3] = np.where(outline & own[fn], F[..., 3], F[..., 3] * soft(sm & m, .7))
        for img in (F, B):
            img[img[..., 3] < 1 / 255.] = 0
    # the joints
    solid = {n: P[n][..., 3] > .5 for n in P}
    solid["head"] = heads["idle"][..., 3] > .5
    allowed = {}
    for back, front, pivot, (lo, hi), cap in JOINTS:
        B = P[back]
        base = own.get(back, np.zeros_like(solid[back]))
        disc = np.zeros_like(base)
        if cap:
            union = solid[front] | base
            r = ndimage.distance_transform_edt(union)[pivot[1], pivot[0]] - 3
            yy, xx = np.mgrid[0:B.shape[0], 0:B.shape[1]]
            disc = (xx - pivot[0]) ** 2 + (yy - pivot[1]) ** 2 <= r * r
            fill = disc & (B[..., 3] < .9)
            B[fill, :3] = M[fill, :3]
            # the cap's own ink edge where it lies past the back part's drawing (hidden at rest; when the joint
            # bends, the rounded joint is outlined like the rest of the figure)
            ring = disc & ~ndimage.binary_erosion(disc, iterations=4) & ~ndimage.binary_dilation(base, iterations=2)
            B[ring, :3] = np.array([11, 10, 13]) / 255.
            B[..., 3] = np.maximum(B[..., 3], soft(disc) * (M[..., 3] > .5))
        ok = np.ones_like(base)
        for d in np.linspace(lo, hi, 12):
            limb = (rot(solid[front], pivot, d) | base | disc).astype(np.uint8)
            # (the thighs: the crotch corner under the shirt counts as limb; the wrist: only the hand itself, so
            # no bit of forearm ever peeks past the back of the hand)
            ok &= (cv2.morphologyEx(limb, cv2.MORPH_CLOSE, CLOSE) > 0) if back.startswith("thigh") else limb > 0
        allowed.setdefault(back, np.zeros_like(base))
        allowed[back] |= ok
        # whatever of it shows at rest stays (the strip under the front part's softened cut included)
        shows = (B[..., 3] > .02) & ~ndimage.binary_erosion(P[front][..., 3] > .97 if front in P else solid[front], iterations=2)
        allowed.setdefault(back + ":base", base | disc | shows)
        allowed[back + ":base"] |= disc | shows
    # the shoes: their drawing and the sock / ankle column the short-jeans edit drew above it - not the blurred
    # smear round it
    sj = aligned("shortjeans")
    for n in ("shoe_l", "shoe_r"):
        img = P[n]
        same = (np.abs(img[..., :3] - sj[..., :3]).max(-1) < .1) & (sj[..., 3] > .9)
        keep = own[n] | ndimage.binary_opening(same & (img[..., 3] > .5), iterations=2)
        lab_i, k = ndimage.label(keep)
        if k > 1:
            sizes = ndimage.sum(keep, lab_i, range(1, k + 1))
            keep = lab_i == 1 + int(np.argmax(sizes))
        keep = ndimage.binary_fill_holes(keep)
        # above the shoe only the sock and ankle column itself (its convex outline), nothing beside it
        ext = keep & ~ndimage.binary_dilation(own[n], iterations=2)
        col = ext & ((img[..., :3].min(-1) > .7) | ((img[..., 0] > .6) & (img[..., 0] > img[..., 2] + .12)))
        if col.sum() > 50:
            ys_, xs_ = np.nonzero(col)
            hull = cv2.convexHull(np.stack([xs_, ys_], 1).astype(np.int32))
            hm = np.zeros(keep.shape, np.uint8); cv2.fillPoly(hm, [hull], 1)
            hm = ndimage.binary_dilation(hm > 0, iterations=6)
            keep &= ~ext | hm
        img[..., 3] = np.where(own[n] & outline, img[..., 3], np.minimum(img[..., 3], soft(keep)))
        img[img[..., 3] < 1 / 255.] = 0
    # the jean cuffs: no bits of the shoe or sock in them (the shoe is its own piece under the cuff)
    for n in ("shin_l", "shin_r"):
        img = P[n]
        a = img[..., 3] > .5
        ys = np.nonzero(a.any(1))[0]
        band = np.zeros_like(a); band[ys.max() - 60:ys.max() + 1] = True
        red = (img[..., 0] > img[..., 1] + .25) & (img[..., 0] > .35)
        drop = band & a & ndimage.binary_dilation(red, iterations=2) & ~own[n] | (band & a & red)
        img[drop] = 0
        lab_i, k = ndimage.label(img[..., 3] > .1)
        if k > 1:
            sizes = ndimage.sum(img[..., 3] > .1, lab_i, range(1, k + 1))
            keep_i = 1 + int(np.argmax(sizes))
            img[(lab_i != keep_i) & (lab_i > 0)] = 0
    # the jeans' top (behind the shirt hem and both thighs): only well inside the jeans' outline, so a thigh
    # turning at the hip never shows it past the leg
    pants = np.isin(lab, [names.index(n) for n in ("pelvis", "thigh_l", "thigh_r", "torso")])
    pv = P["pelvis"]
    pv[..., 3] *= soft(own["pelvis"] | ndimage.binary_erosion(pants, iterations=9), .7)
    for back in {j[0] for j in JOINTS}:
        B = P[back]
        keep = allowed[back] | allowed[back + ":base"]
        B[..., 3] *= soft(ndimage.binary_erosion(keep, iterations=1) | allowed[back + ":base"], .7)
        B[B[..., 3] < 1 / 255.] = 0
    # the forearm under the hand: nothing of it past the hand's outline (it showed as skin specks along the back
    # of the hand); its own drawing and its elbow end stay as they are
    Fo, Hd = P["arm_l_fore"], P["hand_l"][..., 3] > .5
    yy1, xx1 = np.mgrid[0:lab.shape[0], 0:lab.shape[1]]
    elbow_end = (xx1 - 300) ** 2 + (yy1 - 932) ** 2 < 90 ** 2
    keep = ndimage.binary_dilation(lab == names.index("arm_l_fore"), iterations=8) | ndimage.binary_erosion(Hd, iterations=2) | elbow_end
    Fo[..., 3] *= soft(keep, .6)
    Fo[Fo[..., 3] < 1 / 255.] = 0
    # the beanie's brim: the old cut ended the beanie on a ragged line through the brim's black outline, so specks
    # of the forehead showed through the outline (a light, spiky fringe - plain at 2x); the brim's whole ink line
    # (and its soft lower edge) goes into the beanie, which covers the head there
    Bn = P["beanie"]
    bs = Bn[..., 3] > .5
    band = ndimage.binary_dilation(bs, iterations=12) & ~bs & np.isin(lab, [names.index("head"), names.index("beanie")])
    inky = band & (M[..., :3].max(-1) < .55) & (M[..., 3] > .9)
    lab_i, k = ndimage.label(inky | bs)
    keep_l = np.unique(lab_i[bs])
    add = np.isin(lab_i, keep_l[keep_l > 0]) & inky
    add = ndimage.binary_closing(add | bs, iterations=2) & ~bs & band
    Bn[add, :3] = M[add, :3]
    Bn[..., 3] = np.maximum(Bn[..., 3], soft(add, .6) * (M[..., 3] > .9))
