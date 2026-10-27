"""Spine 4.2 rig building from canvas-sized part images.

A part image lives on the master's frame (master px, y down); `Frame` maps that to skeleton units
(y up). Every part is cropped, scaled to the atlas density (ESRGAN x4 then area-downsampled, with
some of a plain Lanczos resize mixed back in to keep the cloth texture), packed into 2048 pages, and
becomes a region (rigid parts) or a contour mesh whose vertices take their weights from a weight
field - a function of the vertex's setup-pose world position - so two parts that overlap at a joint
deform identically where they overlap.
"""
import json, math, os, subprocess, sys
import numpy as np
import cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r'C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current'
sys.path.insert(0, os.path.join(REPO, 'tools', 'char_rigs'))
import meshkit as mk          # noqa: E402  (outline, interior, triangulate, weighted_mesh, setup_world)

ESRGAN = r'C:\Users\CooperHinkel\Documents\ClaudeRoblox\.tools\realesrgan\realesrgan-ncnn-vulkan.exe'


class Frame:
    """master px <-> skeleton units: x = (px - 512) / s + cx, y = cy - (py - 768) / s"""

    def __init__(self, s, cx, cy):
        self.s, self.cx, self.cy = s, cx, cy

    def u(self, px, py):
        return ((px - 512) / self.s + self.cx, self.cy - (py - 768) / self.s)

    def U(self, P):
        P = np.asarray(P, float)
        return np.stack([(P[..., 0] - 512) / self.s + self.cx, self.cy - (P[..., 1] - 768) / self.s], -1)

    def px(self, x, y):
        return ((x - self.cx) * self.s + 512, 768 - (y - self.cy) * self.s)


# ---------------------------------------------------------------- images

def load_part(path):
    return np.asarray(Image.open(path).convert('RGBA'))


def crop_box(rgba, pad=3):
    a = rgba[..., 3]
    ys, xs = np.nonzero(a > 2)
    x0, y0 = max(0, xs.min() - pad), max(0, ys.min() - pad)
    x1, y1 = min(a.shape[1], xs.max() + 1 + pad), min(a.shape[0], ys.max() + 1 + pad)
    return x0, y0, x1, y1


def premul(a8):
    p = a8.astype(np.float32) / 255.
    p[..., :3] *= p[..., 3:4]
    return p


def unpremul8(p):
    o = p.copy(); al = o[..., 3:4]
    o[..., :3] = np.where(al > 1e-4, o[..., :3] / np.maximum(al, 1e-4), 0)
    return (np.clip(o, 0, 1) * 255 + .5).astype(np.uint8)


def upscale_many(crops, factor, workdir, texture_mix=.35):
    """{name: RGBA uint8 crop} -> {name: RGBA uint8 at `factor`}. Colour: Real-ESRGAN (x4plus) on the
    crop's colour alone (transparent pixels bled to their neighbours' colour, no alpha - the ncnn build's
    alpha output is unreliable), area-resized down, mixed with a Lanczos resize so fine cloth texture
    survives. Alpha: the Lanczos resize of the true alpha."""
    import shutil
    src = os.path.join(workdir, 'in'); dst = os.path.join(workdir, 'out')
    for d in (src, dst):
        if os.path.isdir(d): shutil.rmtree(d)
        os.makedirs(d)
    bled = {n: bleed(c) for n, c in crops.items()}
    for n, c in bled.items():
        Image.fromarray(np.ascontiguousarray(c[..., :3]), 'RGB').save(os.path.join(src, n + '.png'))
    subprocess.run([ESRGAN, '-i', src, '-o', dst, '-n', 'realesrgan-x4plus', '-f', 'png'],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out = {}
    for n, c in crops.items():
        h, w = c.shape[:2]
        tw, th = max(1, int(round(w * factor))), max(1, int(round(h * factor)))
        big = np.asarray(Image.open(os.path.join(dst, n + '.png')).convert('RGB')).astype(np.float32) / 255.
        ce = cv2.resize(big, (tw, th), interpolation=cv2.INTER_AREA)
        cl = cv2.resize(bled[n][..., :3].astype(np.float32) / 255., (tw, th), interpolation=cv2.INTER_LANCZOS4)
        al = cv2.resize(c[..., 3].astype(np.float32) / 255., (tw, th), interpolation=cv2.INTER_LANCZOS4)
        col = np.clip(ce * (1 - texture_mix) + cl * texture_mix, 0, 1)
        o = np.concatenate([col, np.clip(al, 0, 1)[..., None]], -1)
        out[n] = (o * 255 + .5).astype(np.uint8)
    return out


def bleed(c):
    """RGB of transparent pixels set to the nearest opaque colour (no dark halo when filtered)"""
    from scipy import ndimage
    a = c[..., 3] > 8
    if a.all() or not a.any(): return c
    _, (iy, ix) = ndimage.distance_transform_edt(~a, return_indices=True)
    o = c.copy(); o[..., :3] = c[iy, ix, :3]
    return o


# ---------------------------------------------------------------- atlas

def pack(images, size=2048, pad=4):
    """skyline packing of {name: HxWx4} into as many size x size pages as needed -> pages, {name: (page, x, y)}"""
    order = sorted(images, key=lambda n: (-images[n].shape[0], -images[n].shape[1]))
    pages = []; where = {}
    def new_page():
        pages.append({'sky': np.zeros(size, int), 'img': np.zeros((size, size, 4), np.uint8)})
    new_page()
    for n in order:
        h, w = images[n].shape[:2]
        placed = False
        for pi, pg in enumerate(pages):
            sky = pg['sky']; best = None
            for x in range(pad, size - w - pad + 1, 4):
                y = int(sky[x - pad:x + w + pad].max()) + pad
                if y + h + pad > size: continue
                if best is None or y < best[1]: best = (x, y)
            if best:
                x, y = best
                sky[x:x + w + pad] = y + h
                pg['img'][y:y + h, x:x + w] = images[n]
                where[n] = (pi, x, y); placed = True
                break
        if not placed:
            new_page()
            pg = pages[-1]; x, y = pad, pad
            pg['sky'][x:x + w + pad] = y + h
            pg['img'][y:y + h, x:x + w] = images[n]
            where[n] = (len(pages) - 1, x, y)
    return [p['img'] for p in pages], where


def atlas_text(page_names, page_sizes, regions):
    """regions: {name: (page, x, y, w, h)}"""
    out = []
    for pi, pn in enumerate(page_names):
        out += [pn, f'size: {page_sizes[pi][0]},{page_sizes[pi][1]}', 'format: RGBA8888', 'filter: Linear,Linear',
                'repeat: none', 'pma: false']
        for n, (p, x, y, w, h) in sorted(regions.items(), key=lambda kv: (kv[1][2], kv[1][1])):
            if p != pi: continue
            out += [n, '  rotate: false', f'  xy: {x}, {y}', f'  size: {w}, {h}', f'  orig: {w}, {h}', '  offset: 0, 0',
                    '  index: -1']
        out.append('')
    return '\n'.join(out).rstrip('\n') + '\n'


def crop_page(img):
    """trim a page to the smallest power-of-two height that holds its content (width stays 2048)"""
    ys = np.nonzero(img[..., 3].max(1) > 0)[0]
    h = int(ys.max()) + 1 if len(ys) else 1
    H = 256
    while H < h: H *= 2
    return img[:H]


# ---------------------------------------------------------------- skeleton

def bone_list(spec, frame):
    """spec: [(name, parent, (px, py) head, (px, py) tail or None, extra dict)] in master px ->
    Spine bones with local x/y/rotation/length (no inherited rotation in the setup pose: every
    bone's rotation is its world angle minus its parent's)"""
    world = {}
    bones = []
    for name, parent, head, tail, extra in spec:
        hx, hy = frame.u(*head)
        if isinstance(tail, str) and tail.startswith('inherit'):
            ang = world[parent][2]; length = float(tail.split(':')[1]) if ':' in tail else 30.0
        elif tail is not None:
            tx, ty = frame.u(*tail)
            ang = math.degrees(math.atan2(ty - hy, tx - hx)); length = math.hypot(tx - hx, ty - hy)
        else:
            ang, length = 0.0, 0.0
        world[name] = (hx, hy, ang)
        b = {'name': name}
        if parent:
            px, py, pa = world[parent]
            dx, dy = hx - px, hy - py
            r = math.radians(-pa)
            b['parent'] = parent
            b['x'] = round(dx * math.cos(r) - dy * math.sin(r), 3)
            b['y'] = round(dx * math.sin(r) + dy * math.cos(r), 3)
            rot = ang - pa
        else:
            b['x'], b['y'] = round(hx, 3), round(hy, 3); rot = ang
        rot = (rot + 180) % 360 - 180
        if abs(rot) > 1e-4: b['rotation'] = round(rot, 4)
        if length: b['length'] = round(length, 3)
        b.update(extra or {})
        bones.append(b)
    return bones


# ---------------------------------------------------------------- attachments

def region_attachment(frame, crop_box_px, atlas_density, bone_world):
    """a region placed exactly over its master-frame crop, in the bone's setup-pose local space"""
    x0, y0, x1, y1 = crop_box_px
    cx, cy = frame.u((x0 + x1) / 2, (y0 + y1) / 2)
    lx, ly = mk.to_local(bone_world, (cx, cy))
    a, b, c, d = bone_world[:4]
    rot = -math.degrees(math.atan2(c, a))               # the bone's world rotation, undone
    return {'x': round(lx, 2), 'y': round(ly, 2), 'rotation': round(rot, 3) if abs(rot) > 1e-4 else 0,
            'width': round((x1 - x0) / frame.s, 2), 'height': round((y1 - y0) / frame.s, 2)}


def despeckle(img, min_area=40, thresh=3):
    """zero the alpha of tiny isolated specks (resampling ringing): nothing outside a mesh may show"""
    m = (img[..., 3] > thresh).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    if n <= 2: return img
    big = np.zeros(n, bool); big[1:] = st[1:, cv2.CC_STAT_AREA] >= min_area
    keep = big[lab] | (m == 0)
    near = cv2.dilate((big[lab] & (m > 0)).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    out = img.copy()
    out[..., 3] = np.where(keep | near, out[..., 3], 0)
    out[..., 3] = np.where(m.astype(bool) | near, out[..., 3], np.where(out[..., 3] <= thresh, out[..., 3], out[..., 3]))
    return out


def _simple(P):
    """True if the closed polygon P (n,2) has no crossing non-adjacent edges"""
    n = len(P)
    A = P; B = np.roll(P, -1, 0)
    for i in range(n):
        a, b = A[i], B[i]
        j = np.arange(n)
        ok = (j != i) & (j != (i + 1) % n) & (j != (i - 1) % n)
        c, d = A[ok], B[ok]
        def orient(p, q, r):
            return (q[..., 0] - p[..., 0]) * (r[..., 1] - p[..., 1]) - (q[..., 1] - p[..., 1]) * (r[..., 0] - p[..., 0])
        o1 = orient(a, b, c); o2 = orient(a, b, d); o3 = orient(c, d, a[None]); o4 = orient(c, d, b[None])
        if np.any((o1 * o2 < 0) & (o3 * o4 < 0)):
            return False
    return True


def hull_outline(alpha, pad=3, step=26, tol=1.2, thresh=3, smooth=1.5):
    """one closed, simple outline round every visible pixel of a part"""
    base = (alpha > thresh).astype(np.uint8)
    B = 80
    m = cv2.copyMakeBorder(base, B, B, B, B, cv2.BORDER_CONSTANT, value=0)
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * pad + 1, 2 * pad + 1)))
    for r in (4, 8, 16, 32, 60):
        n, _ = cv2.connectedComponents(m)
        if n <= 2: break
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
    from scipy import ndimage
    m = ndimage.binary_fill_holes(m).astype(np.uint8)
    cover = cv2.dilate(cv2.copyMakeBorder(base, B, B, B, B, cv2.BORDER_CONSTANT, value=0),
                       cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * max(1, pad - 1) + 1,) * 2))
    for k in range(5):
        sm = (cv2.GaussianBlur(m.astype(np.float32), (0, 0), smooth * (1 + k)) > .5).astype(np.uint8) | m | cover
        sm = ndimage.binary_fill_holes(sm).astype(np.uint8)
        n, _ = cv2.connectedComponents(sm)
        cs, _ = cv2.findContours(sm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = cv2.convexHull(np.vstack(cs)) if n > 2 else max(cs, key=cv2.contourArea)
        c = cv2.approxPolyDP(c, tol * (1 + .5 * k), True)[:, 0, :].astype(float) - B
        pts = []
        for i in range(len(c)):
            a, b = c[i], c[(i + 1) % len(c)]
            seg = np.hypot(*(b - a)); kk = max(1, int(math.ceil(seg / step)))
            for j in range(kk):
                pts.append(a + (b - a) * j / kk)
        P = np.array(pts)
        # drop near-duplicate points
        keep = [0]
        for i in range(1, len(P)):
            if np.hypot(*(P[i] - P[keep[-1]])) > .75: keep.append(i)
        P = P[keep]
        if len(P) > 3 and np.hypot(*(P[0] - P[-1])) < .75: P = P[:-1]
        if _simple(P):
            break
        m = cv2.dilate(m, np.ones((3, 3), np.uint8))
    area = 0.5 * np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1])
    return P[::-1] if area < 0 else P


def triangulate(poly, inner, iters=25):
    """Delaunay over outline + interior points, keeping the triangles inside the outline; outline
    edges Delaunay skipped are split and the whole thing redone (meshkit's, with more rounds)"""
    from scipy.spatial import Delaunay
    hull = [tuple(p) for p in poly]
    for _ in range(iters):
        P = np.vstack([np.array(hull), inner]) if len(inner) else np.array(hull)
        tri = Delaunay(P).simplices
        H = np.array(hull)
        cen = P[tri].mean(1)
        keep = mk.inside(H, cen) > 0
        tri = tri[keep]
        nh = len(hull)
        edges = set()
        for t in tri:
            for i in range(3):
                a, b = int(t[i]), int(t[(i + 1) % 3]); edges.add((min(a, b), max(a, b)))
        missing = [i for i in range(nh) if (min(i, (i + 1) % nh), max(i, (i + 1) % nh)) not in edges]
        if not missing:
            out = []
            for t in tri:
                a, b, c = P[t[0]], P[t[1]], P[t[2]]
                cr = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
                out.append([int(t[0]), int(t[2]), int(t[1])] if cr < 0 else [int(t[0]), int(t[1]), int(t[2])])
            return P, np.array(out), nh
        if len(hull) > 6 * len(poly) + 50:
            break
        for i in sorted(missing, reverse=True):
            a, b = np.array(hull[i]), np.array(hull[(i + 1) % nh])
            hull.insert(i + 1, tuple((a + b) / 2))
        # interior points too close to the outline block its edges: drop them
        if len(inner):
            d = np.abs(mk.inside(np.array(hull), inner))
            inner = inner[d > 3.0]
    raise RuntimeError('could not keep the outline in the triangulation')


def mesh_attachment(frame, crop_box_px, img_scaled, weight_fn, bone_index, W, grid_px=26, pad=3, thresh=6,
                    extra_points=None, to_master=None):
    """contour mesh over a scaled part image; weight_fn(world (N,2)) -> list of {bone: w}.
    to_master(P): image px -> master px, for images not cut axis-aligned from the master frame"""
    x0, y0, x1, y1 = crop_box_px
    hh, ww = img_scaled.shape[:2]
    sx, sy = ww / (x1 - x0), hh / (y1 - y0)          # scaled px per master px
    poly = hull_outline(img_scaled[..., 3], pad=pad, step=grid_px)
    poly = np.clip(poly, 0, [ww, hh])
    extra = []
    if extra_points is not None:                       # denser rows across joints (given in master px)
        for p in extra_points:
            extra.append(((p[0] - x0) * sx, (p[1] - y0) * sy))
    inner = mk.interior(poly, spacing=grid_px, margin=.5, extra=extra)
    try:
        P, T, nh = triangulate(poly, inner)
    except RuntimeError:
        poly = hull_outline(img_scaled[..., 3], pad=pad + 4, step=grid_px, tol=2.0, smooth=3.0)
        inner = mk.interior(poly, spacing=grid_px, margin=.5, extra=extra)
        P, T, nh = triangulate(poly, inner)
    master_px = to_master(P) if to_master else np.stack([x0 + P[:, 0] / sx, y0 + P[:, 1] / sy], 1)
    world = frame.U(master_px)
    weights = weight_fn(world)
    verts, uvs = mk.weighted_mesh(P, (ww, hh), world, weights, bone_index, W)
    return {'type': 'mesh', 'uvs': uvs, 'triangles': [int(i) for i in T.flatten()], 'vertices': verts, 'hull': int(nh),
            'width': round((x1 - x0) / frame.s, 2), 'height': round((y1 - y0) / frame.s, 2)}, len(P)


# ---------------------------------------------------------------- weight fields

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def chain_weights(p, joints, bones, helpers, blend):
    """weights along a limb chain. joints: world points J0..Jn (n segments, bone i spans J_i -> J_i+1);
    bones: n bone names; helpers: n-1 helper bone names (or None) at the inner joints; blend: half-width
    of each joint's blend (units). Returns {bone: w}: each joint blends prev -> helper -> next by the
    point's position along the axis through the joint (the bisector of the two segments)."""
    p = np.asarray(p, float)
    J = [np.asarray(j, float) for j in joints]
    w = {bones[0]: 1.0}
    for k in range(1, len(J) - 1):
        u1 = J[k] - J[k - 1]; u1 /= np.linalg.norm(u1)
        u2 = J[k + 1] - J[k]; u2 /= np.linalg.norm(u2)
        ax = u1 + u2; ax /= np.linalg.norm(ax)
        z = float((p - J[k]) @ ax)
        b = blend[k - 1] if isinstance(blend, (list, tuple)) else blend
        before = float(smoothstep(0, b, -z)); after = float(smoothstep(0, b, z))
        mid = 1 - before - after
        # what was on the previous bone is split at this joint
        prev_total = w.pop(bones[k - 1], 0.0)
        w[bones[k - 1]] = prev_total * before
        h = helpers[k - 1]
        if h: w[h] = w.get(h, 0) + prev_total * mid
        else:
            w[bones[k - 1]] += prev_total * mid * .5; after += mid * .5
        w[bones[k]] = w.get(bones[k], 0) + prev_total * after
    return {k: v for k, v in w.items() if v > 1e-4}


def mix(*pairs):
    """mix((weight, {bone: w}), ...) -> {bone: w}"""
    out = {}
    for s, d in pairs:
        if s <= 0: continue
        for k, v in d.items():
            out[k] = out.get(k, 0) + s * v
    t = sum(out.values()) or 1
    return {k: v / t for k, v in out.items() if v / t > 1e-4}
