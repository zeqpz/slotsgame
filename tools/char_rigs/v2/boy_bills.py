"""The boy's cash: one complete bill (the front bill of the hands-removed edit, straightened) and a
6-bill fan fitted to the master: a common pivot and one angle per bill, front to back, so the fan of
identical bills covers the master's money where it shows. -> parts/boy/bill.png + parts/boy/fan.json"""
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
QUAD = [(612, 727), (755, 783), (660, 1022), (518, 962)]     # the front bill, roughly (TL, TR, BR, BL)


def main():
    os.makedirs(OUT, exist_ok=True)
    lab, names = pk.seg_src(WHO, 'nohands', removed=['arm_l_upper', 'arm_l_fore', 'hand_l', 'hand_r'])
    S = pk.src(WHO, 'nohands')
    H, W = S.shape[:2]
    cash = lab == names.index('cash')
    # the front bill: the cash inside its (grown) quad
    q = np.array(QUAD, np.float32); c = q.mean(0)
    qg = c + (q - c) * 1.08
    m = (pk.poly_mask((H, W), qg) > .5) & cash & (S[..., 3] > 127)
    cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cnt = max(cs, key=cv2.contourArea)
    (cx, cy), (bw, bh), ang = cv2.minAreaRect(cnt)
    if bw > bh:                      # make the long side the height
        bw, bh = bh, bw; ang += 90
    print('front bill rect: centre (%.1f, %.1f) size %.1f x %.1f angle %.2f' % (cx, cy, bw, bh, ang))
    # straighten: rotate the image about the bill centre by -ang, crop the rect (+pad)
    pad = 6
    Mrot = cv2.getRotationMatrix2D((cx, cy), ang, 1.0)
    P = pk.premul(S)
    Pm = P * (cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)[..., None]
    rot = cv2.warpAffine(Pm, Mrot, (W, H), flags=cv2.INTER_CUBIC, borderValue=(0, 0, 0, 0))
    x0, y0 = int(round(cx - bw / 2 - pad)), int(round(cy - bh / 2 - pad))
    bill = rot[y0:y0 + int(bh + 2 * pad), x0:x0 + int(bw + 2 * pad)].clip(0, 1)
    hh, ww = bill.shape[:2]
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    inset = 1.5
    inside = np.clip(np.minimum.reduce([xx - (pad + inset) + 1, (pad + bw - inset) - xx + 1, yy - (pad + inset) + 1, (pad + bh - inset) - yy + 1]), 0, 1)
    bill = bill * inside[..., None]
    Image.fromarray((pk.unpremul(bill) * 255 + .5).clip(0, 255).astype(np.uint8), 'RGBA').save(os.path.join(OUT, 'bill.png'))
    # the fan: bills rotated about a pivot; fit pivot + per-bill angles to the master's money
    labm, nm = pk.master_labels(WHO)
    target = labm == nm.index('cash')
    hands = np.isin(labm, [nm.index('hand_l'), nm.index('hand_r')])
    sc = .5
    Ht, Wt = int(H * sc), int(W * sc)
    T = cv2.resize(target.astype(np.uint8), (Wt, Ht), interpolation=cv2.INTER_NEAREST) > 0
    Hd = cv2.resize(hands.astype(np.uint8), (Wt, Ht), interpolation=cv2.INTER_NEAREST) > 0
    corners0 = cv2.boxPoints(((cx, cy), (bw, bh), ang))         # front bill corners

    def rect_mask(px, py, th):
        R = cv2.getRotationMatrix2D((px, py), th, 1.0)          # cv2: positive = counter-clockwise on screen
        pts = np.hstack([corners0, np.ones((4, 1))]) @ R.T
        mm = np.zeros((Ht, Wt), np.uint8)
        cv2.fillPoly(mm, [np.round(pts * sc).astype(np.int32)], 1)
        return mm > 0

    best = None
    for px in range(530, 620, 4):
        for py in range(960, 1050, 4):
            for dlt in np.arange(4, 12.5, .5):
                angs = [float(k * dlt) for k in range(6)]
                covered = np.zeros((Ht, Wt), bool)
                for th in angs: covered |= rect_mask(px, py, th)
                iou = (covered & T).sum() / max(1, (covered & ~Hd | T).sum())
                if best is None or iou > best[0]:
                    best = (iou, px, py, angs)
    iou, px, py, angs = best
    print('fan pivot (%d, %d), angles (front->back) %s, IoU %.3f' % (px, py, [round(a, 1) for a in angs], iou))
    json.dump(dict(pivot=[px, py], front_centre=[cx, cy], size=[bw, bh], front_angle=ang, angles=angs, pad=pad,
                   iou=iou), open(os.path.join(OUT, 'fan.json'), 'w'), indent=1)
    # preview: the fan drawn over the master's figure without money
    prev = pk.premul(pk.src(WHO, 'master')) * (~target)[..., None]
    for th in angs[::-1]:                       # back bill first
        R = cv2.getRotationMatrix2D((px, py), th, 1.0)
        # bill image placed: upright bill -> rotate by ang about centre -> rotate by th about pivot
        A = cv2.getRotationMatrix2D((cx, cy), -ang, 1.0)
        A3 = np.vstack([A, [0, 0, 1]]); R3 = np.vstack([R, [0, 0, 1]])
        T0 = np.array([[1, 0, x0], [0, 1, y0], [0, 0, 1]], float)
        F = (R3 @ A3 @ T0)[:2]
        lay = cv2.warpAffine(bill, F, (W, H), flags=cv2.INTER_CUBIC, borderValue=(0, 0, 0, 0)).clip(0, 1)
        prev = prev * (1 - lay[..., 3:4]) + lay
    bg = np.array([1, 0, 1], np.float32)
    img = prev[..., :3] + bg * (1 - prev[..., 3:4])
    Image.fromarray((img[650:1080, 380:820] * 255).clip(0, 255).astype(np.uint8)).save(os.path.join(paths.WORK, 'boy_fan.png'))


if __name__ == '__main__':
    main()
