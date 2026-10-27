"""Register edit images onto their master (ECC affine, on the parts the edit left alone).

align(who, edit_path, anchor_parts) -> (warped RGBA float32 [0..255], 2x3 matrix edit->master, score dict)
"""
import json, os, sys
import numpy as np
import cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths


def load_rgba(p):
    a = np.asarray(Image.open(p).convert('RGBA')).astype(np.float32)
    a[..., 3] = np.clip((a[..., 3] - 2) / (250 - 2), 0, 1) * 255
    return a


def labels(who):
    names = json.load(open(os.path.join(paths.WORK, 'seg', f'{who}_names.json')))
    return np.load(os.path.join(paths.WORK, 'seg', f'{who}_labels.npy')), names


def gray(rgba):
    a = rgba[..., 3:4] / 255.
    g = (rgba[..., :3] * a + 255 * (1 - a)).mean(-1)      # on white
    return g.astype(np.float32)


def init_from_bbox(mm, em):
    """similarity guess mapping edit mask bbox -> master mask bbox"""
    ys, xs = np.nonzero(mm); ye, xe = np.nonzero(em)
    s = np.sqrt(mm.sum() / max(em.sum(), 1))
    cx_m, cy_m = xs.mean(), ys.mean(); cx_e, cy_e = xe.mean(), ye.mean()
    return np.array([[s, 0, cx_m - s * cx_e], [0, s, cy_m - s * cy_e]], np.float32)


def align(who, edit_path, anchor_parts, master_path=None, motion=cv2.MOTION_AFFINE, guess=False):
    lab, names = labels(who)
    import segcfg
    M = load_rgba(master_path or segcfg.CFG[who]['master'])
    E = load_rgba(edit_path)
    H, W = M.shape[:2]
    anchor = np.isin(lab, [names.index(p) for p in anchor_parts])
    anchor = cv2.dilate(anchor.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    gm = gray(M); ge = gray(E)
    warp = np.eye(2, 3, dtype=np.float32)
    if guess:
        # SIFT matches between the master's anchor parts and the whole edit -> similarity (edit -> master),
        # then inverted into ECC's convention (master coords -> edit coords)
        sift = cv2.SIFT_create(8000)
        k1, d1 = sift.detectAndCompute(gm.astype(np.uint8), anchor.astype(np.uint8) * 255)
        k2, d2 = sift.detectAndCompute(ge.astype(np.uint8), ((E[..., 3] > 30) * 255).astype(np.uint8))
        mt = cv2.BFMatcher().knnMatch(d1, d2, k=2)
        good = [m for m, n in mt if m.distance < .75 * n.distance]
        src = np.float32([k2[m.trainIdx].pt for m in good]); dst = np.float32([k1[m.queryIdx].pt for m in good])
        S, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=3.0, maxIters=5000)
        print('sift matches', len(good), 'inliers', int(inl.sum()), 'similarity edit->master', np.round(S, 4).tolist())
        A = np.vstack([S, [0, 0, 1]]); warp = np.linalg.inv(A)[:2].astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-6)
    # coarse to fine
    for scale in (0.25, 0.5, 1.0):
        sm = cv2.resize(gm, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        se = cv2.resize(ge, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        sa = cv2.resize(anchor.astype(np.uint8), None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
        w = warp.copy(); w[:, 2] *= scale
        try:
            _, w = cv2.findTransformECC(sm, se, w, motion, crit, sa, 5)
        except cv2.error as e:
            print('ECC failed at', scale, e)
            break
        w[:, 2] /= scale; warp = w
    # warp maps master coords -> edit coords (ECC convention: template=master, input=edit)
    out = cv2.warpAffine(E, warp, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    ga = gray(out)
    m = anchor & (M[..., 3] > 200) & (out[..., 3] > 200)
    err = float(np.abs(ga[m] - gm[m]).mean()) if m.any() else -1
    am = (M[..., 3] > 127) & anchor; ao = (out[..., 3] > 127) & anchor
    iou = float((am & ao).sum() / max((am | ao).sum(), 1))
    return out, warp, dict(err=round(err, 2), iou=round(iou, 4), warp=np.round(warp, 4).tolist())


if __name__ == '__main__':
    import segcfg
    who, edit = sys.argv[1], sys.argv[2]
    anchors = sys.argv[3].split(',')
    out, warp, sc = align(who, edit, anchors, guess=len(sys.argv) > 4)
    print(sc)
