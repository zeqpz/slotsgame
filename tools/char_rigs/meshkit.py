"""Mesh building blocks for the character rig pass (enhance.py).

A Spine 4.2 weighted mesh is: uvs (normalised to its atlas region), triangles, a hull (the first
`hull` vertices, in order round the outline) and, per vertex, the bones it follows with a weight
and the vertex position in each bone's setup-pose space. These helpers build one from a region's
alpha: an outline that hugs the drawn shape, an even fill of interior vertices, a triangulation
that keeps to the outline, and weights from a smooth field - so a joint bends instead of folding.
"""
import math
import numpy as np
import cv2
from scipy.spatial import Delaunay


# ---------------------------------------------------------------- bones (setup pose)

def setup_world(bones, transforms=()):
    """Setup-pose world matrices {name: (a, b, c, d, x, y)} (y up). Transform constraints given as
    (bone, target, mixRotate) in world mode are applied - the rig's knee/elbow helpers."""
    W = {}
    for b in bones:
        r = b.get("rotation", 0); sx = b.get("scaleX", 1); sy = b.get("scaleY", 1)
        shx = b.get("shearX", 0); shy = b.get("shearY", 0)
        la = math.cos(math.radians(r + shx)) * sx; lb = math.cos(math.radians(r + 90 + shy)) * sy
        lc = math.sin(math.radians(r + shx)) * sx; ld = math.sin(math.radians(r + 90 + shy)) * sy
        x, y = b.get("x", 0), b.get("y", 0)
        p = b.get("parent")
        if not p:
            W[b["name"]] = (la, lb, lc, ld, x, y)
        else:
            pa, pb, pc, pd, px, py = W[p]
            W[b["name"]] = (pa * la + pb * lc, pa * lb + pb * ld, pc * la + pd * lc, pc * lb + pd * ld,
                            pa * x + pb * y + px, pc * x + pd * y + py)
    for bone, target, mix in transforms:
        a, b, c, d, x, y = W[bone]; ta, tb, tc, td = W[target][:4]
        r = math.atan2(tc, ta) - math.atan2(c, a)
        if r > math.pi: r -= 2 * math.pi
        elif r < -math.pi: r += 2 * math.pi
        r *= mix; cs, sn = math.cos(r), math.sin(r)
        W[bone] = (cs * a - sn * c, cs * b - sn * d, sn * a + cs * c, sn * b + cs * d, x, y)
    return W


def to_local(M, p):
    a, b, c, d, x, y = M
    det = a * d - b * c
    dx, dy = p[0] - x, p[1] - y
    return ((d * dx - b * dy) / det, (a * dy - c * dx) / det)


def to_world(M, q):
    a, b, c, d, x, y = M
    return (a * q[0] + b * q[1] + x, c * q[0] + d * q[1] + y)


def mesh_world(att, bone_names, W):
    """Setup-pose world positions of a weighted mesh's vertices."""
    v = att["vertices"]; out = []; i = 0
    n_uv = len(att["uvs"]) // 2
    if len(v) == len(att["uvs"]):
        raise ValueError("unweighted mesh")
    while i < len(v) and len(out) < n_uv:
        n = int(v[i]); i += 1; px = py = 0.0
        for _ in range(n):
            M = W[bone_names[int(v[i])]]; wx, wy = to_world(M, (v[i + 1], v[i + 2])); w = v[i + 3]
            px += wx * w; py += wy * w; i += 4
        out.append((px, py))
    return np.array(out)


def fit_affine(src, dst):
    """Least-squares affine map src (N,2) -> dst (N,2); returns (3x2 matrix, max residual)."""
    A = np.hstack([src, np.ones((len(src), 1))])
    M, *_ = np.linalg.lstsq(A, dst, rcond=None)
    res = np.abs(A @ M - dst).max()
    return M, res


def apply_affine(M, pts):
    pts = np.asarray(pts, float)
    return np.hstack([pts, np.ones((len(pts), 1))]) @ M


# ---------------------------------------------------------------- geometry from alpha

def outline(alpha, pad=3, step=22, tol=1.2, thresh=8):
    """Closed outline (CCW in image coords y-down -> list of (x, y) px) hugging every pixel with
    alpha > thresh, `pad` px outside it, resampled so no edge is longer than `step`."""
    m = (alpha > thresh).astype(np.uint8)
    if pad:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * pad + 1, 2 * pad + 1))
        m = cv2.dilate(m, k)
    m = cv2.copyMakeBorder(m, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=0)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea)
    c = cv2.approxPolyDP(c, tol, True)[:, 0, :].astype(float) - 2
    # approxPolyDP can cut corners inward by up to tol: push every vertex out by tol along the normal
    pts = []
    n = len(c)
    for i in range(n):
        a, b = c[i], c[(i + 1) % n]
        seg = np.hypot(*(b - a)); k = max(1, int(math.ceil(seg / step)))
        for j in range(k):
            pts.append(a + (b - a) * j / k)
    P = np.array(pts)
    area = 0.5 * np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1])
    if area < 0:
        P = P[::-1]
    return P


def outline_from_mask(mask, step=22, tol=1.2):
    m = cv2.copyMakeBorder(mask.astype(np.uint8), 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=0)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea)
    c = cv2.approxPolyDP(c, tol, True)[:, 0, :].astype(float) - 2
    pts = []
    n = len(c)
    for i in range(n):
        a, b = c[i], c[(i + 1) % n]
        seg = np.hypot(*(b - a)); k = max(1, int(math.ceil(seg / step)))
        for j in range(k):
            pts.append(a + (b - a) * j / k)
    P = np.array(pts)
    area = 0.5 * np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1])
    return P[::-1] if area < 0 else P


def inside(poly, pts):
    path = poly.astype(np.float32).reshape(-1, 1, 2)
    return np.array([cv2.pointPolygonTest(path, (float(x), float(y)), True) for x, y in pts])


def interior(poly, spacing=24, margin=.55, extra=()):
    """Interior vertices on a staggered grid, kept `margin*spacing` clear of the outline.
    `extra`: further points (e.g. a denser band across a joint) - filtered the same way."""
    x0, y0 = poly.min(0); x1, y1 = poly.max(0)
    pts = []
    row = 0
    y = y0 + spacing * .5
    while y < y1:
        off = spacing * .5 if row % 2 else 0
        x = x0 + spacing * .5 + off
        while x < x1:
            pts.append((x, y)); x += spacing
        y += spacing * .866; row += 1
    pts += list(extra)
    if not pts:
        return np.zeros((0, 2))
    pts = np.array(pts, float)
    d = inside(poly, pts)
    pts = pts[d > margin * spacing]
    # thin out points closer than half a spacing (extra bands overlap the grid)
    keep = []
    for p in pts:
        if all(np.hypot(*(p - q)) > spacing * .45 for q in keep):
            keep.append(p)
    return np.array(keep) if keep else np.zeros((0, 2))


def triangulate(poly, inner):
    """Delaunay over outline + interior points, keeping only triangles inside the outline; any
    outline edge Delaunay skipped is split and the whole thing redone, so the hull is exact."""
    hull = [tuple(p) for p in poly]
    for _ in range(8):
        P = np.vstack([np.array(hull), inner]) if len(inner) else np.array(hull)
        tri = Delaunay(P).simplices
        H = np.array(hull)
        cen = P[tri].mean(1)
        keep = inside(H, cen) > 0
        tri = tri[keep]
        nh = len(hull)
        edges = set()
        for t in tri:
            for i in range(3):
                a, b = int(t[i]), int(t[(i + 1) % 3]); edges.add((min(a, b), max(a, b)))
        missing = [i for i in range(nh) if (min(i, (i + 1) % nh), max(i, (i + 1) % nh)) not in edges]
        if not missing:
            # orient every triangle the same way (CCW in y-down image space)
            out = []
            for t in tri:
                a, b, c = P[t[0]], P[t[1]], P[t[2]]
                cr = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
                out.append([int(t[0]), int(t[2]), int(t[1])] if cr < 0 else [int(t[0]), int(t[1]), int(t[2])])
            return P, np.array(out), nh
        for i in sorted(missing, reverse=True):
            a, b = np.array(hull[i]), np.array(hull[(i + 1) % nh])
            hull.insert(i + 1, tuple((a + b) / 2))
    raise RuntimeError("could not keep the outline in the triangulation")


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- software render (setup pose)

class Canvas:
    """World space (y up) on a pixel grid: pixel = (ox + x*s, oy - y*s). Premultiplied float RGBA."""

    def __init__(self, x0, y0, x1, y1, s=1.0):
        self.s = s; self.ox = -x0 * s; self.oy = y1 * s
        self.w = int(math.ceil((x1 - x0) * s)); self.h = int(math.ceil((y1 - y0) * s))
        self.img = np.zeros((self.h, self.w, 4), np.float32)

    def to_px(self, P):
        P = np.asarray(P, float)
        return np.stack([self.ox + P[:, 0] * self.s, self.oy - P[:, 1] * self.s], 1)

    def to_world(self, Q):
        Q = np.asarray(Q, float)
        return np.stack([(Q[:, 0] - self.ox) / self.s, (self.oy - Q[:, 1]) / self.s], 1)


def premul(img):
    a = np.asarray(img, np.float32) / 255.
    a[..., :3] *= a[..., 3:4]
    return a


def unpremul(p):
    out = p.copy(); al = out[..., 3:4]
    out[..., :3] = np.where(al > 1e-4, out[..., :3] / np.maximum(al, 1e-4), 0)
    return (np.clip(out, 0, 1) * 255 + .5).astype(np.uint8)


def raster_mesh(canvas, world, uv_px, tris, tex_premul):
    """Draw a mesh into a premultiplied layer of the canvas size (returned, not composited).
    Each pixel centre is mapped through its triangle's barycentrics to texture space and
    sampled bilinearly (cv2.remap on premultiplied texels)."""
    H, W = canvas.h, canvas.w
    P = canvas.to_px(world)
    idx = np.full((H, W), -1, np.int32)
    for k, t in enumerate(tris):
        pts = np.round(P[list(t)] * 16).astype(np.int32)
        cv2.fillConvexPoly(idx, pts, int(k), lineType=cv2.LINE_8, shift=4)
    ys, xs = np.nonzero(idx >= 0)
    k = idx[ys, xs]
    T = np.asarray(tris)[k]
    a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    px = np.stack([xs + .5, ys + .5], 1)
    v0, v1, v2 = b - a, c - a, px - a
    d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1)
    d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
    den = d00 * d11 - d01 * d01
    den = np.where(np.abs(den) < 1e-9, 1e-9, den)
    l1 = (d11 * d20 - d01 * d21) / den; l2 = (d00 * d21 - d01 * d20) / den; l0 = 1 - l1 - l2
    U = uv_px[T[:, 0]] * l0[:, None] + uv_px[T[:, 1]] * l1[:, None] + uv_px[T[:, 2]] * l2[:, None]
    mapx = np.full((H, W), -10, np.float32); mapy = np.full((H, W), -10, np.float32)
    mapx[ys, xs] = U[:, 0] - .5; mapy[ys, xs] = U[:, 1] - .5
    layer = cv2.remap(tex_premul, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    layer[idx < 0] = 0
    return layer


def over(dst, src):
    """premultiplied src over dst, in place"""
    dst *= (1 - src[..., 3:4]); dst += src
    return dst


def weighted_mesh(px, region_wh, world, weights, bone_index, W, prune=.004):
    """Spine weighted mesh dict. px: (N,2) pixel positions in the region; world: (N,2) setup-pose
    world positions (y up); weights: list per vertex of {bone: w}."""
    rw, rh = region_wh
    verts = []
    for p, ws in zip(world, weights):
        ws = {b: w for b, w in ws.items() if w > prune}
        s = sum(ws.values())
        ws = {b: w / s for b, w in ws.items()}
        verts.append(len(ws))
        for b, w in sorted(ws.items(), key=lambda kv: bone_index[kv[0]]):
            lx, ly = to_local(W[b], p)
            verts += [bone_index[b], round(lx, 2), round(ly, 2), round(w, 4)]
    uvs = []
    for x, y in px:
        uvs += [round(float(x) / rw, 5), round(float(y) / rh, 5)]
    return verts, uvs
