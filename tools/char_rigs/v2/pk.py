"""Part kit: build complete rig parts from a master and its aligned edits.

Every part image is canvas-sized (the master's 1024 x 1536 frame), premultiplied float RGBA in 0..1:
- the visible pixels come from the master (or an expression image) - exactly the drawing;
- the hidden pixels (under parts in front of it) come from an edit image where those parts were
  removed (segmented with the master's labels as priors, so the edit's own outlines decide the
  shape), from procedural growth (inpainted colour + an outline round the new edge), or - at a
  joint cut through continuous cloth or skin - from the neighbour's own pixels (a band past the
  cut), with the front part's edge feathered over it.
Hidden pixels are only ever placed under parts in front (at rest the assembly is the master).
"""
import json, os, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import segcfg
import paths

INK_LUM = 48
REACH = 9.0
_cache = {}


def load_rgba(p):
    a = np.asarray(Image.open(p).convert('RGBA')).astype(np.float32)
    a[..., 3] = np.clip((a[..., 3] - 2) / (250 - 2), 0, 1) * 255
    return a


def fix_alpha(img):
    """The model's matting leaves see-through specks in pure white areas (eye whites, highlights)
    and keeps the inside at 253. Holes inside the figure that are bright or small are closed."""
    a = img[..., 3] / 255.
    lum = img[..., :3].mean(-1)
    sil = ndimage.binary_fill_holes(a > .5)
    core = ndimage.binary_erosion(sil, iterations=2)
    bad = core & (a < .985)
    lab, n = ndimage.label(bad)
    if n:
        sl = ndimage.find_objects(lab)
        for i, s in enumerate(sl, 1):
            m = lab[s] == i
            if m.sum() < 400 or lum[s][m].mean() > 110:
                sub = img[s][..., 3]; sub[m] = 255
    return img


def src_path(who, name):
    if name == 'master':
        return segcfg.CFG[who]['master']
    return paths.aligned(who, name)


def src(who, name):
    k = (who, name)
    if k not in _cache:
        _cache[k] = fix_alpha(load_rgba(src_path(who, name)))
    return _cache[k]


def master_labels(who):
    names = json.load(open(os.path.join(paths.WORK, 'seg', f'{who}_names.json')))
    return np.load(os.path.join(paths.WORK, 'seg', f'{who}_labels.npy')), names


def poly_mask(shape, pts, ss=1):
    H, W = shape
    m = Image.new('L', (W * ss, H * ss), 0)
    ImageDraw.Draw(m).polygon([(float(x) * ss, float(y) * ss) for x, y in pts], fill=255)
    m = np.asarray(m).astype(np.float32) / 255.
    if ss > 1:
        m = cv2.resize(m, (W, H), interpolation=cv2.INTER_AREA)
    return m


def premul(img255):
    p = img255 / 255.
    p[..., :3] *= p[..., 3:4]
    return p


def unpremul(p):
    o = p.copy(); al = o[..., 3:4]
    o[..., :3] = np.where(al > 1e-4, o[..., :3] / np.maximum(al, 1e-4), 0)
    return o


# ---------------------------------------------------------------- segmenting a source image

_segcache = {}


def seg_src(who, name, removed=(), force=(), order=None):
    """Labels for a source image. Outside the removed parts the master's labels are the prior;
    each region between the source's own lines takes the majority prior label; regions with no
    prior take the nearest known label; ink goes to the front-most part within REACH.
    force: [(name, polygon)] labels a polygon outright (new parts the master does not have)."""
    key = (who, name, tuple(removed), json.dumps(force), tuple(order or ()))
    if key in _segcache:
        return _segcache[key]
    lab_m, names = master_labels(who)
    names = list(names)
    for nm, _ in force:
        if nm not in names: names.append(nm)
    if name == 'master' and not force:
        _segcache[key] = (lab_m, names); return lab_m, names
    S = src(who, name)
    H, W = S.shape[:2]
    fig = S[..., 3] > 127
    lum = S[..., :3].mean(-1)
    ink = fig & (lum < INK_LUM)
    prior = lab_m.astype(np.int32).copy()
    rem = np.isin(lab_m, [names.index(r) for r in removed if r in names])
    rem = cv2.dilate(rem.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    prior[rem] = -1
    prior[~fig] = -1
    fmask = {}
    for nm, pts in force:
        fm = poly_mask((H, W), pts) > .5
        fmask[nm] = fm
        prior[fm & fig] = names.index(nm)
    known = prior >= 0
    _, (iy, ix) = ndimage.distance_transform_edt(~known, return_indices=True)
    near = prior[iy, ix]
    paint = fig & ~ink
    comp, nc = ndimage.label(paint)
    lab = np.full((H, W), -1, np.int32)
    for i, s in enumerate(ndimage.find_objects(comp), 1):
        if s is None: continue
        m = comp[s] == i
        pr = prior[s][m]
        kn = pr[pr >= 0]
        if len(kn) > .1 * m.sum():
            v = np.bincount(kn, minlength=len(names))
            best = int(np.argmax(v))
            straddles = any(a in names and b in names and v[names.index(a)] > .03 * len(kn) and v[names.index(b)] > .03 * len(kn)
                            for _, _, a, b in segcfg.CFG[who].get('cuts', []) + segcfg.CFG[who].get('final_cuts', []))
            if v[best] >= .7 * len(kn) and not straddles:
                lab[s][m] = best
            else:
                nr = near[s][m]
                lab[s][m] = np.where(pr >= 0, pr, nr)
        else:
            nr = near[s][m]
            lab[s][m] = int(np.argmax(np.bincount(nr, minlength=len(names))))
    for nm, fm in fmask.items():
        lab[fm & fig] = names.index(nm)
    # ink: front-most part with paint within reach, else nearest
    order = order or segcfg.CFG[who]['order']
    todo = fig & (lab < 0)
    best = np.full((H, W), -1, np.int32); best_r = np.full((H, W), -1)
    for r, nm in enumerate(order):
        if nm not in names: continue
        core = lab == names.index(nm)
        if not core.any(): continue
        d = ndimage.distance_transform_edt(~core)
        better = todo & (d <= segcfg.CFG[who].get('reach', {}).get(nm, REACH)) & (r > best_r)
        best[better] = names.index(nm); best_r[better] = r
    got = best >= 0
    lab[todo & got] = best[todo & got]
    rest = todo & ~got
    if rest.any():
        k2 = lab >= 0
        _, (iy, ix) = ndimage.distance_transform_edt(~k2, return_indices=True)
        lab[rest] = lab[iy, ix][rest]
    for nm, fm in fmask.items():
        lab[fm & fig] = names.index(nm)
    if segcfg.CFG[who].get('final_cuts'):
        import seg as _seg
        for src_l, line, left, right in segcfg.CFG[who]['final_cuts']:
            if left in removed or right in removed or src_l not in names:
                continue
            sd = _seg.side_of((H, W), line); mm = lab == names.index(src_l)
            lab[mm & (sd > 0)] = names.index(left); lab[mm & (sd < 0)] = names.index(right)
    _segcache[key] = (lab, names)
    return lab, names


def rk_smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


_rimcache = {}


def rims(who, order):
    """The anti-aliased rim where a back part's paint meets a front part's outline: pixels labelled
    as the back part, within 2.5 px of the front part's ink, darker than the back part's own paint
    there. Left with the back part they read as a dark ghost line along the old boundary once the
    front part moves; they belong to the front part's outline instead, as ink with partial alpha
    (unmixed against the back part's paint). Returns (rim mask, owner label idx, alpha)."""
    key = (who, tuple(order))
    if key in _rimcache: return _rimcache[key]
    lab, names = master_labels(who)
    M = src(who, 'master')
    rgb = M[..., :3]; lum = rgb.mean(-1); fig = M[..., 3] > 127
    ink = fig & (lum < INK_LUM)
    paint = fig & ~ink
    rank = {names.index(n): k for k, n in enumerate(order) if n in names}
    H, W = lab.shape
    rim = np.zeros((H, W), bool); owner = np.full((H, W), -1, np.int32); alpha = np.zeros((H, W), np.float32)
    inkc = np.array([11, 10, 13], np.float32)
    for Y, rY in rank.items():
        inkY = ink & (lab == Y)
        if not inkY.any(): continue
        near = ndimage.distance_transform_edt(~inkY) <= 3.5
        for X, rX in rank.items():
            if rX >= rY: continue                       # only parts behind Y
            px = near & paint & (lab == X)
            if not px.any(): continue
            core = paint & (lab == X) & ~near
            if not core.any(): continue
            _, (iy, ix) = ndimage.distance_transform_edt(~core, return_indices=True)
            pc = rgb[iy, ix]                             # the back part's paint colour nearby
            dark = px & (lum < pc.mean(-1) - 10)
            if not dark.any(): continue
            v = pc - inkc
            a = ((pc - rgb) * v).sum(-1) / np.maximum((v * v).sum(-1), 1e-3)
            a = np.clip(a, 0, 1)
            rim |= dark; owner[dark] = Y; alpha[dark] = a[dark]
    _rimcache[key] = (rim, owner, alpha)
    return _rimcache[key]


# ---------------------------------------------------------------- assembling a part

class Part:
    def __init__(self, who, name, order):
        self.who, self.name, self.order = who, name, order
        self.lab_m, self.names = master_labels(who)
        M = src(who, 'master')
        self.H, self.W = M.shape[:2]
        self.img = np.zeros((self.H, self.W, 4), np.float32)     # premultiplied
        self.vis = np.zeros((self.H, self.W), bool)              # its visible pixels at rest
        i = order.index(name)
        front = [n for n in order[i + 1:] if n in self.names]
        fidx = [self.names.index(n) for n in front]
        self.front = np.isin(self.lab_m, fidx)
        self.rim, self.rim_owner, self.rim_a = rims(who, order)
        self.my_rim = self.rim & (self.lab_m == self.names.index(name)) if name in self.names else np.zeros_like(self.rim)
        self.front |= self.rim & np.isin(self.rim_owner, fidx)       # rims of parts in front count as theirs

    def have(self):
        return self.img[..., 3] > .5

    def paste(self, src_img255, mask, soft=None):
        """put source pixels where mask (bool) and nothing better is there yet"""
        m = mask & (self.img[..., 3] < .02)
        p = premul(src_img255)
        if soft is not None:
            p = p * soft[..., None]
        self.img[m] = p[m]

    def base(self, source='master', labels=None, removed=(), force=()):
        """the visible part: master labels (or the part's region in an expression image)"""
        labels = labels or [self.name]
        if source == 'master':
            lab, names = self.lab_m, self.names
        else:
            lab, names = seg_src(self.who, source, removed, force, self.order)
        m = np.isin(lab, [names.index(l) for l in labels if l in names])
        m &= ~self.front
        m &= ~self.my_rim
        self.paste(src(self.who, source), m)
        self.vis |= m
        # this part's own outline rims (where its ink meets paint behind it): ink with partial alpha
        if self.name in self.names:
            mine = self.rim & (self.rim_owner == self.names.index(self.name)) & (self.img[..., 3] < .02)
            if mine.any():
                a = self.rim_a[mine]
                self.img[mine] = np.stack([np.full_like(a, 11 / 255.) * a, np.full_like(a, 10 / 255.) * a,
                                           np.full_like(a, 13 / 255.) * a, a], -1)
        return m

    def ext(self, source, removed=(), force=(), labels=None, clip=None, under=None, blend=0):
        """hidden pixels from an edit, only under parts in front (or under `under`, a bool mask).
        blend: the part's own visible pixels within `blend` px of the new ones cross-fade into the
        edit's version, so the join is not a hard seam once what was in front moves away"""
        labels = labels or [self.name]
        lab, names = seg_src(self.who, source, removed, force, self.order)
        m = np.isin(lab, [names.index(l) for l in labels if l in names])
        if under is None:
            under = self.front
            if removed:      # an edit only speaks for where the parts it removed were (and their rims)
                ridx = [self.names.index(r) for r in removed if r in self.names]
                where = np.isin(self.lab_m, ridx) | (self.rim & np.isin(self.rim_owner, ridx))
                where = cv2.dilate(where.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
                under = under & where
        m &= under
        if clip is not None:
            m &= poly_mask((self.H, self.W), clip) > .5
        before = self.img[..., 3] > .5
        newpx = m & (self.img[..., 3] < .02)
        self.paste(src(self.who, source), m)
        if blend and newpx.any():
            E = premul(src(self.who, source))
            own = np.isin(lab, [names.index(l) for l in labels if l in names]) & (E[..., 3] > .5)
            d = ndimage.distance_transform_edt(~newpx)
            w = np.clip(1 - (d - 1) / blend, 0, 1) * (before & own & (d <= blend + 1))
            w = cv2.GaussianBlur(w.astype(np.float32), (0, 0), 1.0) * before
            self.img = self.img * (1 - w[..., None]) + E * w[..., None]
        return int(m.sum())

    def grow(self, poly, ink_w=5.0, ink_rgb=(11, 10, 13), only_under_front=True, keep_ink_from=None, fill_rgb=None):
        """procedural continuation: fill polygon `poly` (outside what the part already has) with
        the part's own colours, inpainted, and draw an outline round the new silhouette edge."""
        H, W = self.H, self.W
        cov = poly_mask((H, W), poly, ss=4)
        cur = self.have()
        z = (cov > .02) & ~cur
        if only_under_front:
            z &= self.front | cur
        if not z.any(): return 0
        U = unpremul(self.img)
        rgb = (U[..., :3] * 255).clip(0, 255).astype(np.uint8)
        lum = rgb.astype(np.float32).mean(-1)
        paint = cur & (lum > INK_LUM + 10)
        ys, xs = np.nonzero(z | paint)
        y0, y1 = max(0, ys.min() - 20), min(H, ys.max() + 21)
        x0, x1 = max(0, xs.min() - 20), min(W, xs.max() + 21)
        sub = rgb[y0:y1, x0:x1].copy()
        unknown = (~paint[y0:y1, x0:x1]).astype(np.uint8) * 255
        filled = cv2.inpaint(sub, unknown, 9, cv2.INPAINT_TELEA)
        fill = np.zeros_like(rgb); fill[y0:y1, x0:x1] = filled
        new_sil = cur | (cov > .5)
        d = ndimage.distance_transform_edt(new_sil)            # distance to the outside
        ink_a = np.clip(ink_w + .5 - d, 0, 1)
        col = fill.astype(np.float32) / 255.
        if fill_rgb is not None:                     # a flat colour (the dark inside of the hood)
            col = np.broadcast_to(np.array(fill_rgb, np.float32) / 255., col.shape).copy()
        col = col * (1 - ink_a[..., None]) + (np.array(ink_rgb, np.float32) / 255.) * ink_a[..., None]
        a = np.where(cur, 0, cov)                                # coverage of the new pixels (antialiased)
        a = a * z
        newp = np.concatenate([col * a[..., None], a[..., None]], -1)
        self.img = self.img + newp * (1 - self.img[..., 3:4])
        return int(z.sum())

    def fill_inpaint(self, mask):
        """the part continues, opaque, under `mask` (only where parts in front cover it): colours
        inpainted from its own paint around (thin things in front - laces, drawstrings)"""
        z = mask & self.front & (self.img[..., 3] < .5)
        if not z.any(): return 0
        U = unpremul(self.img)
        rgb = (U[..., :3] * 255).clip(0, 255).astype(np.uint8)
        known = self.img[..., 3] > .5
        unknown = (~known | z).astype(np.uint8) * 255
        ys, xs = np.nonzero(z)
        y0, y1 = max(0, ys.min() - 30), min(self.H, ys.max() + 31)
        x0, x1 = max(0, xs.min() - 30), min(self.W, xs.max() + 31)
        sub = cv2.inpaint(rgb[y0:y1, x0:x1], unknown[y0:y1, x0:x1], 6, cv2.INPAINT_TELEA)
        fill = np.zeros_like(rgb); fill[y0:y1, x0:x1] = sub
        p = np.concatenate([fill.astype(np.float32) / 255., np.ones((self.H, self.W, 1), np.float32)], -1)
        self.img[z] = p[z]
        return int(z.sum())

    def clean(self, near=12, min_px=30):
        """drop specks: keep the largest piece and pieces within `near` px of it"""
        a = self.img[..., 3] > .1
        lab, n = ndimage.label(a)
        if n <= 1: return 0
        areas = ndimage.sum(a, lab, range(1, n + 1))
        main = lab == (1 + int(np.argmax(areas)))
        d = ndimage.distance_transform_edt(~main)
        keep = np.zeros(n + 1, bool)
        for i in range(1, n + 1):
            if areas[i - 1] < min_px: continue
            keep[i] = d[lab == i].min() <= near
        drop = ~keep[lab] & a
        self.img[drop] = 0
        return int(drop.sum())

    def _paint_source(self, margin=8):
        """where to take fill colours from: the part's own solid paint, away from its outer edge (the
        rim light lives there) and not the cyan rim highlight itself; falls back to any solid paint"""
        a = self.img[..., 3]
        U = unpremul(self.img)
        rgb = U[..., :3] * 255
        lum = rgb.mean(-1)
        solid = a > .9
        paint = solid & (lum > INK_LUM + 8)
        cyan = (rgb[..., 2] > rgb[..., 0] + 14) & (rgb[..., 1] > rgb[..., 0] + 6)     # the rim light's tint, however faint
        deep = paint & ~cyan & (ndimage.distance_transform_edt(a > .5) > margin)
        for cand in (deep, paint & ~cyan, paint, solid):
            if cand.sum() > 50:
                return U, cand
        return U, solid

    def solidify(self, edge=2):
        """no see-through inside a part: every pixel more than `edge` px inside its silhouette becomes
        fully opaque, its missing coverage filled with the nearest solid paint (the edits' matting left
        faint cracks along some inner lines; moved outline rims leave holes)"""
        a = self.img[..., 3]
        sil = ndimage.binary_fill_holes(a > .5)
        core = ndimage.binary_erosion(sil, iterations=edge)
        weak = core & (a < .999)
        if not weak.any(): return 0
        U, src_ok = self._paint_source()
        _, (iy, ix) = ndimage.distance_transform_edt(~src_ok, return_indices=True)
        fill = U[iy, ix, :3]
        aw = a[weak][:, None]
        self.img[weak, :3] = self.img[weak, :3] + fill[weak] * (1 - aw)      # what is there, over the paint
        self.img[weak, 3] = 1.0
        return int(weak.sum())

    def runon(self, width=24.0, ink_width=3.0):
        """the part runs on under every part in front of it, `width` px past what it already has: its
        own paint colours, nearest-filled (the drawing's ink kept as ink only within `ink_width` px of
        its edge, so a small drift meets black on black and a big one shows cloth, not a ghost line),
        fading out over its last px. At rest nothing of it shows (it is only under parts in front);
        when a part in front moves, what opens up is this part, never the wall."""
        a = self.img[..., 3]
        have = a > .5
        if not have.any(): return 0
        d = ndimage.distance_transform_edt(~have)
        z = (d > 0) & (d <= width) & self.front & (a < .98)
        if not z.any(): return 0
        U, src_ok = self._paint_source()
        # a smooth local average of the part's own paint (normalised convolution): a nearest-colour fill
        # made flat Voronoi shards wherever the run-on showed
        m = src_ok.astype(np.float32)
        num = cv2.GaussianBlur(U[..., :3].astype(np.float32) * m[..., None], (0, 0), 10)
        den = cv2.GaussianBlur(m, (0, 0), 10)
        _, (iy, ix) = ndimage.distance_transform_edt(~src_ok, return_indices=True)
        near = cv2.GaussianBlur(U[iy, ix, :3].astype(np.float32), (0, 0), 6)
        col = np.where(den[..., None] > .03, num / np.maximum(den, 1e-4)[..., None], near)
        M = src(self.who, 'master')
        # deeper under the part in front it is in that part's shadow (STYLE.md: occlusion in creases):
        # an exposed run-on reads as the shaded inside of the limb, never as a flat patch
        col = col * (1 - .32 * rk_smooth(2.0, width, d))[..., None]
        ink = (M[..., :3].mean(-1) < INK_LUM) & (M[..., 3] > 127) & (d <= ink_width)
        col = np.where(ink[..., None], M[..., :3] / 255., col)
        al = np.clip((width + .5 - d) / 3.0, 0, 1)
        # where it meets the drawing's open space (outside the figure, the gap between the legs) it fades
        # instead of ending on the outline of the part in front
        fig = M[..., 3] > 127
        al = al * rk_smooth(0.0, 5.0, ndimage.distance_transform_edt(fig))
        new = np.concatenate([col * al[..., None], al[..., None]], -1)
        cur = self.img
        out = cur + new * (1 - cur[..., 3:4])                       # under what the part already has
        self.img = np.where(z[..., None], out, cur)
        return int(z.sum())

    def inpaint_hidden(self, cond):
        """hidden pixels where cond(rgb_unpremul, lum) is true are repainted from the part's other
        pixels around them (e.g. an edit's print showing through where the master had plain cloth)"""
        U = unpremul(self.img)
        rgb = (U[..., :3] * 255).clip(0, 255).astype(np.uint8)
        lum = rgb.astype(np.float32).mean(-1)
        a = self.img[..., 3] > .5
        bad = a & ~self.vis & cond(rgb, lum)
        bad = cv2.dilate(bad.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        bad &= a & ~self.vis
        if not bad.any(): return 0
        filled = cv2.inpaint(rgb, bad.astype(np.uint8) * 255, 7, cv2.INPAINT_TELEA)
        al = self.img[..., 3:4]
        self.img[..., :3] = np.where(bad[..., None], filled.astype(np.float32) / 255. * al, self.img[..., :3])
        return int(bad.sum())

    def save(self, path):
        U = unpremul(self.img)
        Image.fromarray((U * 255 + .5).clip(0, 255).astype(np.uint8), 'RGBA').save(path)


def joint(front, back, feather=8.0, band=40.0, front_src='master'):
    """A cut through continuous cloth or skin between two parts (no drawn line between them):
    the back part continues `band` px past the cut with the front part's own pixels, and the
    front part's edge along the cut fades out over `feather` px - over the identical pixels of the
    back part, so at rest nothing changes and when the meshes bend together the seam stays soft."""
    lab, names = front.lab_m, front.names
    fi, bi = names.index(front.name), names.index(back.name)
    F = lab == fi; B = lab == bi
    # the cut: front pixels touching back pixels
    db = ndimage.distance_transform_edt(~B)          # distance from the back part's region
    near_cut = F & (db <= band)
    # only the stretch of the boundary that is a real contact (front pixels near back pixels)
    S = src(front.who, front_src)
    back.paste(S, near_cut)
    ramp = np.clip((db - 1.0) / feather, 0, 1)
    zone = F & (db <= feather + 1)
    a = np.where(zone, ramp, 1.0)
    front.img *= a[..., None]
    return int(near_cut.sum())


def keep_edge(part, ref, near, band=12.0, feather=6.0):
    """An expression's head redraws the face, and its outline where the beanie sits lands a few px off
    the master's: along the master beanie's edge a sliver of the expression's skull showed. Within `band`
    px of the parts in `near` (and under them), the expression takes the idle head's pixels, feathered
    over `feather` px into its own."""
    lab, names = part.lab_m, part.names
    m = np.isin(lab, [names.index(n) for n in near if n in names])
    d = ndimage.distance_transform_edt(~m)
    w = np.clip((band + feather - d) / feather, 0, 1).astype(np.float32)[..., None]
    part.img = part.img * (1 - w) + ref.img * w
    return int((w[..., 0] > 0).sum())
