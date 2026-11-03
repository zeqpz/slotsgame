"""SMOKE SKULL - the cut-out parts for the Blender rig (run with the venv python, not in Blender):
    python tools/blender/chars/skull/parts.py
reads   art/characters-src/v2/skull/master.webp           the whole figure (1024 x 1536, "master px")
        art/blender/chars/skull/src/labels.npy             which part every master pixel belongs to (the old cut's labels)
        art/blender/chars/skull/src/old/*.png              the old cut's upper-body parts, master-sized (hidden areas filled)
writes  art/blender/chars/skull/parts/<piece>.png          each piece cropped to its box (straight RGBA)
        art/blender/chars/skull/parts/parts.json           box, draw order, bone, pivots, chains, flags per piece
        art/blender/chars/skull/qa/parts_*.png             the pieces laid back together (vs the master) and pulled apart

The legs are cut fresh, each into separate rigid pieces that move on their own (owner, 2026-11-03: the old legs smeared
at the knee and did not move separated): thigh / shin / cuff / shoe per leg, every free lace end its own piece.
  - every piece is the master's own pixels over its region; where a piece runs on UNDER the piece in front of it (so a
    bend never opens a gap) it carries a fill: the fabric mirrored across the cut (a seamless continuation), the
    shoe's ankle in the dark of the pant leg, the seat of the pants dark behind the thighs
  - the cut lines follow the drawing's own creases and folds (knee crease, the shadow under the first roll of the cuff,
    the cuff's hem over the shoe), so a cut edge reads as a fold when the joint bends
  - the piece in front gets a 1 px soft edge on its cut; the piece behind is solid under it (no hairline)
  - the laces: a band round each lace's centreline; the shoe (and cuff) under it filled across the lace (interpolated
    along the lace's normal, so the sole's stripes and the canvas run on under it)
The upper body reuses the old cut's parts (they lay back together into the master) with their blurred fringes
removed: a part keeps its visible pixels and only the SOLID part of its hidden fill (no grey halo)."""
import json, math, os
import numpy as np
import cv2
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
SRC = os.path.join(REPO, "art", "blender", "chars", "skull", "src")
OUT = os.path.join(REPO, "art", "blender", "chars", "skull", "parts")
QA = os.path.join(REPO, "art", "blender", "chars", "skull", "qa")
MASTER = os.path.join(REPO, "art", "characters-src", "v2", "skull", "master.webp")
H, W = 1536, 1024
FACES = ["idle", "anticipation", "win", "lose"]

# ------------------------------------------------------------------------------------------------ the joints (master px)
J = {
    "root": (512, 1464), "pelvis": (505, 1000), "torso": (505, 990), "chest": (503, 870), "neck": (505, 765),
    "head": (515, 690), "jaw": (592, 605), "cigar": (402, 656), "ember": (258, 753),
    "arm_l_upper": (365, 782), "arm_l_fore": (322, 900), "arm_r_upper": (682, 790), "arm_r_fore": (750, 895),
    "hood": (600, 700), "pocket": (485, 905),
    "thigh_l": (425, 1012), "shin_l": (420, 1143), "cuff_l": (418, 1190), "shoe_l": (438, 1242),
    "thigh_r": (592, 1012), "shin_r": (598, 1140), "cuff_r": (600, 1210), "shoe_r": (618, 1266),
}
# cut lines (polylines, x increasing): the knee crease and the shadow under the cuff's first roll
KNEE = {"l": [(300, 1154), (370, 1148), (420, 1143), (460, 1139), (500, 1131), (540, 1124)],
        "r": [(480, 1150), (545, 1148), (600, 1139), (650, 1131), (720, 1127)]}
CUFF = {"l": [(290, 1198), (350, 1193), (420, 1189), (470, 1185), (540, 1182)],
        "r": [(480, 1221), (545, 1214), (600, 1208), (650, 1202), (720, 1194)]}
HEM = {"l": [(290, 1212), (330, 1222), (375, 1231), (420, 1231), (460, 1232), (478, 1238), (500, 1248), (545, 1252)],
       "r": [(495, 1262), (515, 1272), (540, 1276), (576, 1272), (590, 1248), (610, 1243), (646, 1246), (690, 1240), (725, 1236)]}
FLY = [(506, 960), (507, 1000), (508, 1040), (504, 1080), (497, 1102), (497, 1200)]   # between the two legs
# the free lace ends: centreline root (at the shoe) -> tip, half width (lace + its ink)
LACES = {
    "lace_l_up": dict(shoe="l", hw=11.5, pts=[(320, 1207), (297, 1198), (267, 1180), (243, 1153), (233, 1118)]),
    "lace_l_down": dict(shoe="l", hw=10.0, pts=[(394, 1249), (409, 1262), (416, 1288), (413, 1320), (403, 1354), (393, 1386), (388, 1414)]),
    "lace_r_left": dict(shoe="r", hw=10.5, pts=[(566, 1274), (548, 1281), (517, 1287), (478, 1283), (448, 1271)]),
    "lace_r_right": dict(shoe="r", hw=11.0, pts=[(651, 1258), (690, 1253), (728, 1242), (748, 1235), (772, 1223)]),
}
# the chains that bend (skinned): bone chain points, root first
CHAINS = {
    "string_l": [(432, 760), (431, 800), (430, 852)],
    "string_r": [(575, 740), (575, 775), (575, 808)],
    "beanie": [(560, 330), (585, 205), (625, 120), (660, 70)],
}


def load(path):
    a = np.asarray(Image.open(path).convert("RGBA")).astype(np.float32) / 255
    return a


def premul(a):
    p = a.copy()
    p[..., :3] *= p[..., 3:4]
    return p


def straight(p):
    a = p.copy()
    al = a[..., 3:4]
    a[..., :3] = np.where(al > 1e-4, a[..., :3] / np.maximum(al, 1e-4), 0)
    return a


def ss(e0, e1, v):
    t = np.clip((v - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)


def line_y(line, x):
    xs, ys = zip(*line)
    return np.interp(x, xs, ys)


def below(line, soft=0.0):
    """1 below the polyline (y down), 0 above; soft = a 1 px antialiased edge"""
    d = YY - line_y(line, XX)
    if soft:
        return np.clip(d / soft + .5, 0, 1)
    return (d >= 0).astype(np.float32)


def right_of(line, soft=0.0):
    ys, xs = zip(*[(y, x) for x, y in line])
    d = XX - np.interp(YY, ys, xs)
    if soft:
        return np.clip(d / soft + .5, 0, 1)
    return (d >= 0).astype(np.float32)


def seg_dist(pts, cap_root=True):
    """distance of every pixel to a polyline; the normal at the nearest point; the arc position (0 at the root).
    cap_root: no round cap at the root (pixels behind the root's end are far)."""
    best = np.full((H, W), 1e9, np.float32)
    nx = np.zeros((H, W), np.float32)
    ny = np.zeros((H, W), np.float32)
    s_at = np.zeros((H, W), np.float32)
    acc = 0.0
    for i in range(len(pts) - 1):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy)
        t = ((XX - ax) * dx + (YY - ay) * dy) / (L * L)
        tc = np.clip(t, 0, 1)
        d = np.hypot(ax + dx * tc - XX, ay + dy * tc - YY)
        if i == 0 and cap_root:
            d = np.where(t < 0, 1e9, d)
        m = d < best
        best = np.where(m, d, best)
        nx = np.where(m, -dy / L, nx)
        ny = np.where(m, dx / L, ny)
        s_at = np.where(m, acc + tc * L, s_at)
        acc += L
    return best, nx, ny, s_at


def fill_across(P, K, nx, ny, reach=34):
    """fill P (premultiplied RGBA) over the band K: every pixel interpolated between the first pixels outside the band
    along its normal, both ways (so what crosses the band - stripes, ink - runs on under it)"""
    Kd = cv2.dilate(K.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    ys, xs = np.nonzero(K)
    out = P.copy()
    for y, x in zip(ys, xs):
        n = (nx[y, x], ny[y, x])
        side = []
        for sgn in (1, -1):
            hit = None
            for k in range(1, reach):
                xx, yy = int(round(x + sgn * n[0] * k)), int(round(y + sgn * n[1] * k))
                if not (0 <= xx < W and 0 <= yy < H):
                    break
                if not Kd[yy, xx]:
                    hit = (k, P[yy, xx])
                    break
            side.append(hit)
        if side[0] and side[1]:
            (k0, c0), (k1, c1) = side
            out[y, x] = (c0 * k1 + c1 * k0) / (k0 + k1)
        elif side[0] or side[1]:
            out[y, x] = (side[0] or side[1])[1]                 # one side only: the band ran along an edge
        else:
            out[y, x] = 0
    return out


def extend(P, mask, cover, direction, depth, dark=1.0, flat=None):
    """run a piece on under its neighbour: column by column from the piece's top (direction 'up') or bottom ('down')
    edge, `depth` px into `cover` (where the piece in front is), mirrored across that edge (the fabric continues);
    flat = an (r, g, b) colour instead (the dark inside of a pant leg). Returns the new premultiplied piece and mask."""
    out, m = P.copy(), mask.copy()
    cols = np.nonzero(mask.any(0))[0]
    for x in cols:
        ys = np.nonzero(mask[:, x])[0]
        e = ys.min() if direction == "up" else ys.max()
        rng = range(e - 1, e - 1 - depth, -1) if direction == "up" else range(e + 1, e + 1 + depth)
        for y in rng:
            if not (0 <= y < H) or not cover[y, x]:
                break
            src = 2 * e - y + (-1 if direction == "up" else 1)
            src = int(np.clip(src, ys.min(), ys.max()))
            if flat is not None:
                a = P[src, x, 3]
                c = np.array([*flat, 1.0], np.float32) * a
            else:
                c = P[src, x].copy()
                c[:3] *= dark
            out[y, x] = c
            m[y, x] = True
    return out, m


def clean_old(name, visible):
    """an old part with its blurred fringe removed: its visible pixels (where the labels say it shows, 2 px grace)
    and the solid part of its hidden fill, edged 1 px soft"""
    a = load(os.path.join(SRC, "old", name + ".png"))
    al = a[..., 3]
    solid = (al > .9).astype(np.float32)
    solid = cv2.GaussianBlur(cv2.erode(solid, np.ones((3, 3), np.uint8)), (0, 0), .7)
    vis = cv2.dilate(visible.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32) if visible is not None else 0
    keep = np.maximum(vis, np.clip(solid * 1.15, 0, 1))
    p = premul(a)
    return p * keep[..., None]


INK = np.array([.05, .05, .06], np.float32)


def run_on(P, own, region, line_at, direction, band=16, dark=1.0, flat=None, ink=3.0):
    """a piece running on under its neighbour: `region` (float, the neighbour's silhouette where the piece goes on
    under it) filled with the piece's own fabric tiled on from the band of rows next to its edge (line_at(xs) -> the
    edge row per column) - so the fabric and the side outlines carry straight on, no mirror flare - or a flat colour;
    the fill's own sides (not the edge it grows from) get an ink line, so a bend that bares them shows an outline"""
    out = P.copy()
    reg = (region > .02) & ~own
    ys, xs = np.nonzero(reg)
    ly = np.round(line_at(xs.astype(np.float32))).astype(int)
    if direction == "up":
        sy = ly + np.mod(ys - ly, band)
    else:
        sy = ly - band + np.mod(ys - ly, band)
    sy = np.clip(sy, 0, H - 1)
    src = P[sy, xs]
    a = src[:, 3:4]
    ok = own[ys, xs * 0 + xs] | True
    med = np.median(straight(P[own])[:, :3], 0) if own.any() else np.array([.1, .1, .11])
    col = np.where(a > .5, src[:, :3] / np.maximum(a, 1e-4), med) * dark
    if flat is not None:
        col = np.tile(np.array(flat, np.float32), (len(ys), 1))
    if ink:
        d = cv2.distanceTransform((reg | own).astype(np.uint8), cv2.DIST_L2, 5)[ys, xs]
        w = np.clip((ink + .5 - d), 0, 1)[:, None]
        col = col * (1 - w) + INK * w
    al = region[ys, xs][:, None]
    out[ys, xs, :3] = col * al
    out[ys, xs, 3:4] = al
    return out, own | reg


def top_of(mask):
    t = np.full(W, H, np.float32)
    cols = np.nonzero(mask.any(0))[0]
    t[cols] = mask[:, cols].argmax(0)
    return lambda xs: t[np.clip(xs.astype(int), 0, W - 1)]


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(QA, exist_ok=True)
    M = load(MASTER)
    MP = premul(M)
    A = M[..., 3]
    lab = np.load(os.path.join(SRC, "labels.npy"))
    names = json.load(open(os.path.join(SRC, "label_names.json")))
    L = lambda *ns: np.isin(lab, [names.index(n) for n in ns])
    pieces = {}            # name -> premultiplied RGBA (master-sized)
    pieces_vis = {}        # the shoes' own visible areas (no ankle fill)

    # ---------------------------------------------------------------------------------------- the legs
    fly_r = right_of(FLY)
    pel = L("pelvis") & (YY > 940)
    legs = {"l": (L("thigh_l", "shin_l") | (pel & (fly_r < .5))),
            "r": (L("thigh_r", "shin_r") | (pel & (fly_r >= .5)))}
    front_of_legs = L("torso", "pocket", "arm_l_fore", "arm_r_fore", "arm_l_upper", "arm_r_upper")
    lace_band, lace_norm = {}, {}
    for n, d in LACES.items():
        dist, nx, ny, s = seg_dist(d["pts"])
        band = (dist <= d["hw"]) & (A > .02)
        if n in ("lace_l_up", "lace_r_right"):        # the old labels drew these two: none of the lace left behind
            band |= L(n)
        lace_band[n] = band
        lace_norm[n] = (nx, ny, dist)
    any_lace = np.zeros((H, W), bool)
    for b in lace_band.values():
        any_lace |= b
    seat = np.zeros((H, W), bool)
    for s in "lr":
        leg = legs[s]
        knee_b, cuff_b = below(KNEE[s]), below(CUFF[s])
        knee_soft, cuff_soft = below(KNEE[s], 1.0), below(CUFF[s], 1.0)
        thigh = leg & (knee_b < .5)
        shin = leg & (knee_b >= .5) & (cuff_b < .5)
        # the cuff's last roll was labelled shoe by the old cut: down each column from the cuff, the dark fabric (and
        # its ink) belongs to the cuff until the shoe's white canvas begins
        lum = M[..., :3].mean(-1)
        sl = L(f"shoe_{s}")
        hem = sl & (cuff_b >= .5) & (below(HEM[s]) < .5) & (lum < .62) & (A > .5)
        hem = cv2.morphologyEx(hem.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool) & sl
        leg = leg | hem
        legs[s] = leg
        cuff = leg & (cuff_b >= .5) & ~any_lace
        shoe = sl & ~hem & ~any_lace
        kl = lambda xs, s=s: line_y(KNEE[s], xs)
        cl = lambda xs, s=s: line_y(CUFF[s], xs)
        # thigh: in front of the shin (its knee edge soft); runs up under the hoodie's hem (its fabric, in shadow)
        P = MP * thigh[..., None]
        tt = top_of(thigh)
        reg = front_of_legs & (YY < tt(XX)) & (YY >= tt(XX) - 46) & (tt(XX) < H)
        P, tm = run_on(P, thigh, reg * A, tt, "up", band=14, dark=.62)
        P = P * np.where(thigh[..., None] & (YY[..., None] > line_y(KNEE[s], XX)[..., None] - 2),
                         (1 - knee_soft)[..., None], 1)
        pieces[f"thigh_{s}"] = P
        seat |= tm & (YY < 1112)
        # shin: behind the thigh and the cuff - its fabric runs on up under the thigh and down under the cuff
        P = MP * shin[..., None]
        reg = thigh & (YY >= kl(XX) - 40)
        P, sm = run_on(P, shin, reg * A, kl, "up", band=16, dark=.95)
        cuffsil = leg & (cuff_b >= .5)
        reg = cuffsil & (YY <= cl(XX) + 34)
        P, sm = run_on(P, sm, reg * A, cl, "down", band=16, dark=.85)
        pieces[f"shin_{s}"] = P
        # cuff: in front of the shin (its top edge soft) and of the shoe
        P = MP * cuff[..., None] * np.where(cuff[..., None], cuff_soft[..., None], 1)
        pieces[f"cuff_{s}"] = P
        # shoe: behind the cuff; the ankle goes on up into the pant leg (dark inside it)
        P = MP * shoe[..., None]
        st = top_of(shoe)
        reg = cuffsil & (YY < st(XX)) & (YY >= st(XX) - 42)
        P, shm = run_on(P, shoe, reg * A, st, "up", flat=(.07, .07, .08), ink=0)
        pieces[f"shoe_{s}"] = P
        pieces_vis[f"shoe_{s}"] = shoe
    # the seat of the pants: dark fabric behind both thighs (shows only where they swing apart)
    seat = cv2.morphologyEx(seat.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8)) > 0
    seat &= (YY < 1108) & (YY > 975)
    sp = MP.copy()
    sp[..., :3] *= .55
    sp[..., 3] = 1
    sp[..., :3] = np.where((A > .5)[..., None], sp[..., :3], np.array([.09, .09, .1]))
    pieces["seat"] = sp * seat[..., None]
    # under the laces: the shoes and cuffs filled across each lace that lies over them
    for n, band in lace_band.items():
        nx, ny, dist = lace_norm[n]
        for s in "lr":
            for part in (f"shoe_{s}", f"cuff_{s}"):
                P = pieces[part]
                r = int(LACES[n]["hw"]) + 4
                disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
                outline = cv2.morphologyEx((P[..., 3] > .5).astype(np.uint8), cv2.MORPH_CLOSE, disk) > 0
                region = band & outline & (P[..., 3] < .5)
                if region.any():
                    F = fill_across(P, region, nx, ny)
                    ys, xs = np.nonzero(region)
                    c = straight(F[ys, xs])[:, :3]
                    d = cv2.distanceTransform(outline.astype(np.uint8), cv2.DIST_L2, 5)[ys, xs]
                    w = np.clip(3.5 - d, 0, 1)[:, None]
                    c = c * (1 - w) + INK * w
                    F[ys, xs, :3] = c
                    F[ys, xs, 3] = 1
                    pieces[part] = F
        P = MP * band[..., None]
        # the lace's own edge: soft over the outer half pixel of its band
        P = P * np.maximum(np.clip(LACES[n]["hw"] + .5 - dist, 0, 1), L(n) if n in names else 0)[..., None]
        pieces[n] = P

    # ---------------------------------------------------------------------------------------- no painted rim between the legs
    # The master has a cyan rim light painted down the INNER edge of the left leg (thigh, shin, cuff, shoe tongue) and a
    # pale one down the inner edge of the right leg; in the game they glow inside the gap between the legs (owner,
    # 2026-11-03). Those pixels are recoloured to the piece's own fabric (or canvas) right next to them - the median of
    # its plain pixels within 6 px - and the black ink line is kept.
    outside = cv2.distanceTransform((A >= .5).astype(np.uint8), cv2.DIST_L2, 5)     # px from the background
    zones = {"l": (430, 545, 1040, 1370), "r": (488, 575, 1085, 1305)}
    for s in "lr":
        x0, x1, y0, y1 = zones[s]
        for part in (f"thigh_{s}", f"shin_{s}", f"cuff_{s}", f"shoe_{s}") + ("lace_l_down", "lace_l_up", "lace_r_left"):
            P = pieces[part]
            S_ = straight(P)
            r_, g_, b_ = S_[..., 0], S_[..., 1], S_[..., 2]
            lum = S_[..., :3].mean(-1)
            box = (XX >= x0) & (XX < x1) & (YY >= y0) & (YY < y1) & (P[..., 3] > .02)
            cyan = (b_ - r_ > .08) & (g_ - r_ > .04) & (lum > .12)
            canvas = part.startswith(("shoe", "lace"))
            pale = ((lum > .42) & (outside <= 12) & (not canvas)) if s == "r" else np.zeros_like(cyan)
            rim = box & (cyan | pale)
            rim = cv2.dilate(rim.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & box & (lum > .1)
            if not rim.any():
                continue
            plain = (P[..., 3] > .9) & ~rim & (lum > .07) & ~((b_ - r_ > .05) & (g_ - r_ > .02))
            plain &= (lum > .5) if canvas else (lum < .42)
            ys, xs = np.nonzero(rim)
            for y, x in zip(ys, xs):
                for rad in (6, 10, 16):
                    sl = (slice(max(0, y - rad), y + rad + 1), slice(max(0, x - rad), x + rad + 1))
                    m = plain[sl]
                    if m.sum() >= 6:
                        S_[y, x, :3] = np.median(S_[sl][m][:, :3], 0)
                        break
            P[..., :3] = S_[..., :3] * P[..., 3:4]
            pieces[part] = P
            print(f"  rim painted out: {part} {int(rim.sum())} px")

    # ---------------------------------------------------------------------------------------- the upper body (old cut, cleaned)
    vis = {"hood": L("hood"), "neck": None, "torso": L("torso", "strings"), "pocket": L("pocket"),
           "arm_l_upper": L("arm_l_upper"), "arm_l_fore": L("arm_l_fore"), "arm_r_upper": L("arm_r_upper"),
           "arm_r_fore": L("arm_r_fore"), "string_l": L("string_l"), "string_r": L("string_r"), "mouth": None,
           "beanie": L("beanie"), "cigar": L("cigar")}
    for n, v in vis.items():
        pieces[n] = clean_old(n, v)
    for f in FACES:
        pieces[f"cranium_{f}"] = clean_old(f"cranium_{f}", L("cranium"))
        pieces[f"jaw_{f}"] = clean_old(f"jaw_{f}", L("jaw"))
    # the hood's interior: one dark slab behind the head - keep it, but never past the figure's own outline + 6 px
    # (its fill reached out over the background on the left, where nothing covers it once the head moves)
    sil = cv2.dilate((A > .5).astype(np.uint8), np.ones((13, 13), np.uint8)) > 0
    hp = pieces["hood"]
    lum = straight(hp)[..., :3].mean(-1)
    inner = (hp[..., 3] > .9) & (lum < .2) & (XX > 405) & (XX < 720) & (YY > 560) & (YY < 800)
    inner = cv2.morphologyEx(inner.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)) > 0
    keep = cv2.dilate(L("hood").astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    hood = np.where(keep[..., None], hp, 0)
    flat = np.zeros_like(hp); flat[..., :3] = .075; flat[..., 3] = 1
    hood = np.where((inner & ~keep)[..., None], flat, hood)
    pieces["hood"] = hood * sil[..., None]
    # the neck: the vertebrae and their ink only (the old fill's pale glow round them is gone)
    np_ = pieces["neck"]
    lum = straight(np_)[..., :3].mean(-1)
    ink = (np_[..., 3] > .5) & (lum < .3)
    shape = ndimage.binary_fill_holes(cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)) > 0)
    shape = ndimage.binary_opening(shape, iterations=2)
    pieces["neck"] = np_ * cv2.GaussianBlur(shape.astype(np.float32), (0, 0), .6)[..., None]
    # the jaws: their hidden top (under the upper teeth) only a few px past what shows - its blurred fill made a
    # ragged pale line when the jaw opened; the dark mouth behind shows instead
    jv = cv2.dilate(L("jaw").astype(np.uint8), np.ones((7, 7), np.uint8)).astype(np.float32)
    jv = cv2.GaussianBlur(jv, (0, 0), .7)
    for f in FACES:
        pieces[f"jaw_{f}"] = pieces[f"jaw_{f}"] * jv[..., None]

    # ---------------------------------------------------------------------------------------- order, bones, write
    ORDER = ["hood", "neck", "seat",
             "shoe_l", "shin_l", "cuff_l", "thigh_l", "lace_l_down", "lace_l_up",
             "shoe_r", "shin_r", "cuff_r", "thigh_r", "lace_r_left", "lace_r_right",
             "torso", "arm_l_upper", "arm_r_upper", "arm_l_fore", "arm_r_fore", "pocket", "string_l", "string_r",
             "mouth"] + [f"jaw_{f}" for f in FACES] + [f"cranium_{f}" for f in FACES] + ["beanie", "cigar"]
    BONE = {"hood": "chest", "neck": "neck", "seat": "pelvis", "torso": None, "pocket": "torso", "mouth": "head",
            "cigar": "cigar", "beanie": None, "string_l": None, "string_r": None}
    for s in "lr":
        for p in ("thigh", "shin", "cuff", "shoe"):
            BONE[f"{p}_{s}"] = f"{p}_{s}"
    for n in ("arm_l_upper", "arm_l_fore", "arm_r_upper", "arm_r_fore"):
        BONE[n] = n
    for f in FACES:
        BONE[f"cranium_{f}"] = "head"
        BONE[f"jaw_{f}"] = "jaw"
    spec = {"size": [W, H], "joints": {k: list(v) for k, v in J.items()}, "parts": []}
    for i, n in enumerate(ORDER):
        P = pieces[n]
        a = P[..., 3]
        ys, xs = np.nonzero(a > 1 / 255)
        x0, y0, x1, y1 = int(xs.min()) - 2, int(ys.min()) - 2, int(xs.max()) + 3, int(ys.max()) + 3
        img = straight(np.clip(P[y0:y1, x0:x1], 0, 1))
        Image.fromarray((img * 255 + .5).astype(np.uint8), "RGBA").save(os.path.join(OUT, n + ".png"))
        e = {"name": n, "box": [x0, y0, x1, y1], "draw": i, "bone": BONE.get(n)}
        if n in LACES:
            e["chain"] = [list(p) for p in LACES[n]["pts"]]
            e["parent"] = f"shoe_{LACES[n]['shoe']}"
        if n in CHAINS:
            e["chain"] = [list(p) for p in CHAINS[n]]
            e["parent"] = "chest" if n.startswith("string") else "head"
        if n == "torso":
            e["skin"] = "torso"
        if n.startswith("cranium_") or n.startswith("jaw_"):
            e["face"] = n.split("_", 1)[1]
        if n.startswith(("shoe_", "lace_", "cigar")):
            e["unlit"] = True
        if n.startswith("shoe_"):
            # the shoe's own outline (no ankle under the cuff): for the foot shadows the game draws
            m = ((P[..., 3] > .5) & (~np.isin(np.arange(H), []))[:, None]).astype(np.uint8)
            m &= (pieces_vis[n]).astype(np.uint8)
            cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cmax = max(cs, key=cv2.contourArea)
            e["hull"] = cv2.convexHull(cmax)[:, 0, :].tolist()
        spec["parts"].append(e)
    a = A > .5
    ys, xs = np.nonzero(a)
    spec["figure_box"] = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    json.dump(spec, open(os.path.join(OUT, "parts.json"), "w"), indent=1)

    # ---------------------------------------------------------------------------------------- QA: back together, pulled apart
    comp = np.zeros((H, W, 4), np.float32)
    for n in ORDER:
        if (n.startswith("cranium_") or n.startswith("jaw_")) and not n.endswith("_idle"):
            continue
        comp = pieces[n] + comp * (1 - pieces[n][..., 3:4])
    d = np.abs(comp - MP).max(-1)
    print(f"rest vs master: mean {d.mean() * 255:.2f}/255, p99.9 {np.percentile(d, 99.9) * 255:.1f}, "
          f"px > 24/255: {(d > 24 / 255).sum()}")
    Image.fromarray((np.clip(d * 4, 0, 1) * 255).astype(np.uint8)).save(os.path.join(QA, "parts_diff.png"))
    bg = np.zeros((H, W, 4), np.float32); bg[..., :] = (.35, .55, .35, 1)
    out = comp + bg * (1 - comp[..., 3:4])
    Image.fromarray((out[..., :3] * 255).astype(np.uint8)).save(os.path.join(QA, "parts_rest.png"))
    # every leg piece alone, on green, side by side (what each one carries under its neighbours)
    tiles = []
    for n in ["seat", "thigh_l", "shin_l", "cuff_l", "shoe_l", "thigh_r", "shin_r", "cuff_r", "shoe_r",
              "lace_l_up", "lace_l_down", "lace_r_left", "lace_r_right"]:
        P = pieces[n][940:1480, 140:800]
        o = P + bg[940:1480, 140:800] * (1 - P[..., 3:4])
        tiles.append((o[..., :3] * 255).astype(np.uint8))
    rows = [np.concatenate(tiles[i:i + 5] + [np.zeros_like(tiles[0])] * (5 - len(tiles[i:i + 5])), 1) for i in range(0, len(tiles), 5)]
    Image.fromarray(np.concatenate(rows, 0)).save(os.path.join(QA, "parts_legs.png"))
    print("parts:", len(ORDER), "->", OUT)


if __name__ == "__main__":
    main()
