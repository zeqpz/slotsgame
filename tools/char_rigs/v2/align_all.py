"""Align every edit / expression image onto its master; save aligned RGBA + a diff preview."""
import json, os, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from align import align, load_rgba
import segcfg
import paths
JOBS = {
    'boy': [
        ('edits/noarms', 'head,beanie,shoe_l,shoe_r,shin_l,shin_r,thigh_l,thigh_r', False),
        ('edits/nocash', 'head,beanie,shoe_l,shoe_r,shin_l,shin_r,thigh_l,thigh_r,arm_l_fore', False),
        ('edits/nobeanie', 'torso,cash,hand_l,hand_r,shoe_l,shoe_r,shin_l,shin_r,thigh_l,thigh_r', False),
        ('edits/shortjeans', 'head,beanie,torso,cash,hand_l,hand_r,arm_l_fore', False),
        ('edits/croptop', 'head,beanie,cash,hand_l,hand_r,shoe_l,shoe_r,shin_l,shin_r', False),
    ],
    'skull': [
        ('edits/noarms', 'cranium,beanie,jaw,cigar,leg_l,leg_r,shoe_l,shoe_r', False),
        ('edits/nobeanie', 'jaw,torso,arm_l,arm_r,pocket,leg_l,leg_r,shoe_l,shoe_r', False),
        ('edits/nohead', 'torso,arm_l,arm_r,pocket,leg_l,leg_r,shoe_l,shoe_r', True),
        ('edits/nopocket', 'cranium,beanie,jaw,cigar,leg_l,leg_r,shoe_l,shoe_r', False),
        ('edits/jawopen', 'beanie,torso,arm_l,arm_r,pocket,leg_l,leg_r,shoe_l,shoe_r', False),
        ('edits/shortpants', 'cranium,beanie,jaw,cigar,torso,arm_l,arm_r,pocket', False),
        ('edits/croptop', 'cranium,beanie,jaw,cigar,arm_l,arm_r,shoe_l,shoe_r', False),
    ],
}


def run(who, only=None):
    od = os.path.join(paths.WORK, 'aligned', who); os.makedirs(od, exist_ok=True)
    M = load_rgba(segcfg.CFG[who]['master'])
    res = {}
    for rel, anchors, guess in JOBS[who]:
        name = rel.split('/')[-1]
        if only and name not in only: continue
        out, warp, sc = align(who, paths.art(who, rel), anchors.split(','), guess=guess)
        Image.fromarray(out.clip(0, 255).astype(np.uint8), 'RGBA').save(os.path.join(od, name + '.png'))
        # diff preview: master (red) vs aligned edit (cyan) silhouettes + 50/50 blend
        H, W = out.shape[:2]
        a = M[..., 3] > 127; b = out[..., 3] > 127
        ov = np.zeros((H, W, 3), np.uint8); ov[a & ~b] = (255, 60, 60); ov[b & ~a] = (60, 200, 255); ov[a & b] = (90, 90, 90)
        blend = (M[..., :3] * .5 + out[..., :3] * .5).clip(0, 255).astype(np.uint8)
        prev = np.concatenate([ov, blend], 1)
        Image.fromarray(prev).resize((W, H // 2)).save(os.path.join(od, name + '_diff.png'))
        res[name] = sc
        print(who, name, sc, flush=True)
    json.dump(res, open(os.path.join(od, 'scores.json'), 'w'), indent=1)


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2].split(',') if len(sys.argv) > 2 else None)
