"""Legs solved here, not by Spine IK: both characters are drawn with nearly straight legs (the hip,
knee and ankle almost in line), and a two-bone IK is singular there - with softness it falls short of
the foot even at rest (the shin parted from the shoe), without it the knee snaps as the leg straightens.
Per frame of a clip: the hip from the body's own pose, the foot from its bone; the leg may not reach
further than it does in the drawing (a smooth clamp: past that, the foot comes up with the body, as it
does in a hop); the thigh and shin are turned so the shin's end lands exactly on the foot, and written
as ordinary rotate keys. The knee helper (a half-angle transform constraint) still smooths the crease."""
import math
import numpy as np
import sys
sys.path.insert(0, r'C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\char_rigs')
import motion as mo          # fk(j, ch, n, wanted)


def _rot(m):
    return np.degrees(np.arctan2(m[2], m[0]))


def _scale(m):
    return np.sqrt(np.abs(m[0] * m[3] - m[1] * m[2]))


def solve(j, c, legs, soft=7.0, reach=1.0):
    """legs: [(thigh, shin, foot)] bone names. Edits c.ch in place (thigh/shin rotate, foot x/y)."""
    B = {b['name']: b for b in j['bones']}
    n = c.n
    for thigh, shin, foot in legs:
        parent = B[thigh]['parent']; fparent = B[foot]['parent']
        # setup: lengths and the bend direction, from setup world positions
        W0 = mo.fk(j, {}, 1, [thigh, shin, foot])
        pt = lambda m: np.array([float(np.ravel(m[4])[0]), float(np.ravel(m[5])[0])])
        hip0, knee0, ank0 = pt(W0[thigh]), pt(W0[shin]), pt(W0[foot])
        L1 = np.linalg.norm(knee0 - hip0); L2 = np.linalg.norm(ank0 - knee0)
        d0 = np.linalg.norm(ank0 - hip0)
        u = (ank0 - hip0) / d0
        side = np.sign(u[0] * (knee0 - hip0)[1] - u[1] * (knee0 - hip0)[0]) or 1.0
        dmax = d0 * reach
        # per frame world matrices of the thigh's parent and of the foot (its own channels)
        W = mo.fk(j, c.ch, n, [parent, foot, fparent])
        P = W[parent]
        hx = P[0] * B[thigh].get('x', 0) + P[1] * B[thigh].get('y', 0) + P[4]
        hy = P[2] * B[thigh].get('x', 0) + P[3] * B[thigh].get('y', 0) + P[5]
        fx, fy = np.broadcast_to(W[foot][4], (n,)).astype(float), np.broadcast_to(W[foot][5], (n,)).astype(float)
        s = np.broadcast_to(_scale(P), (n,)).astype(float)                # uniform scale of the body
        dx, dy = fx - hx, fy - hy
        d = np.hypot(dx, dy)
        lim = dmax * s
        k = soft * s
        over = d > lim - k
        d_eff = np.where(over, lim - k * np.exp(-(d - (lim - k)) / np.maximum(k, 1e-6)), d)
        # the foot comes along where the leg cannot reach
        ux, uy = dx / np.maximum(d, 1e-6), dy / np.maximum(d, 1e-6)
        nfx, nfy = hx + ux * d_eff, hy + uy * d_eff
        if np.any(np.abs(nfx - fx) + np.abs(nfy - fy) > 1e-4):
            # back into the foot's parent space
            Q = W[fparent]
            a, b_, cc, dd, qx, qy = [np.broadcast_to(v, (n,)).astype(float) for v in Q]
            det = a * dd - b_ * cc
            lx = (dd * (nfx - qx) - b_ * (nfy - qy)) / det
            ly = (a * (nfy - qy) - cc * (nfx - qx)) / det
            c.set(foot, 'x', lx - B[foot].get('x', 0))
            c.set(foot, 'y', ly - B[foot].get('y', 0))
        l1, l2 = L1 * s, L2 * s
        cos_a = np.clip((l1 * l1 + d_eff * d_eff - l2 * l2) / (2 * l1 * d_eff), -1, 1)
        a1 = np.degrees(np.arccos(cos_a))                                 # hip angle off the hip-foot line
        cos_k = np.clip((l1 * l1 + l2 * l2 - d_eff * d_eff) / (2 * l1 * l2), -1, 1)
        kb = 180 - np.degrees(np.arccos(cos_k))                           # knee bend
        base = np.degrees(np.arctan2(uy, ux))
        thigh_w = base + side * a1
        shin_w = thigh_w - side * kb
        pr = _rot(P)
        thigh_rot0 = B[thigh].get('rotation', 0); shin_rot0 = B[shin].get('rotation', 0)
        tl = thigh_w - pr - thigh_rot0
        sl = shin_w - thigh_w - shin_rot0
        wrap = lambda v: (v + 180) % 360 - 180
        c.set(thigh, 'rotate', wrap(tl))
        c.set(shin, 'rotate', wrap(sl))
    return c
