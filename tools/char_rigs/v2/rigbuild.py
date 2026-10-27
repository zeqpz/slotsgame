"""Build a Spine 4.2 skeleton (JSON + atlas + WebP pages) from a character definition module.

The definition gives: FRAME (master px <-> units), BONES (master-px spec), SLOTS (draw order: slot,
bone, attachments [(name, part png, 'region'|'mesh', weight field)]), IK and TRANSFORM constraints,
SKELETON header values; clips are added afterwards by the clip module."""
import json, math, os, sys
import numpy as np
import cv2
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rigkit as rk
import paths

ATLAS_DENSITY = 1.1        # atlas px per skeleton unit


def build(defn, out_dir, name, page_prefix=None, upscale=True):
    os.makedirs(out_dir, exist_ok=True)
    F = defn.FRAME
    bones = rk.bone_list(defn.BONES, F)
    helpers = [(t['bones'][0], t['target'], t['mixRotate']) for t in defn.TRANSFORM if t.get('mixRotate')]
    W = rk.mk.setup_world(bones, helpers)
    bidx = {b['name']: i for i, b in enumerate(bones)}
    factor = ATLAS_DENSITY / F.s
    # every distinct image: crop on the master frame, then scale to atlas density
    crops, boxes = {}, {}
    for slot, bone, atts in defn.SLOTS:
        for an, png, kind, wf in atts:
            if png in crops: continue
            img = rk.load_part(os.path.join(defn.PARTS, png + '.png'))
            if img[..., 3].max() == 0:
                raise ValueError(f'{png} is empty')
            box = rk.crop_box(img, pad=4)
            boxes[png] = box
            crops[png] = img[box[1]:box[3], box[0]:box[2]]
    if upscale:
        scaled = rk.upscale_many(crops, factor, os.path.join(paths.WORK, 'esr', name))
    else:
        scaled = {n: cv2.resize(c, (int(round(c.shape[1] * factor)), int(round(c.shape[0] * factor))),
                                interpolation=cv2.INTER_LANCZOS4) for n, c in crops.items()}
    scaled = {n: rk.despeckle(im) for n, im in scaled.items()}
    pages, where = rk.pack(scaled)
    page_names = [f'{page_prefix or name}{"" if i == 0 else "-" + str(i + 1)}.webp' for i in range(len(pages))]
    pages = [rk.crop_page(p) for p in pages]
    regions = {}
    for n, (pi, x, y) in where.items():
        h, w = scaled[n].shape[:2]
        regions[n] = (pi, x, y, w, h)
    # attachments
    skin = {}
    slots_json = []
    stats = {}
    for slot, bone, atts in defn.SLOTS:
        skin[slot] = {}
        for an, png, kind, wf in atts:
            box = boxes[png]
            if kind == 'region':
                a = rk.region_attachment(F, box, ATLAS_DENSITY, W[bone])
            else:
                tm = defn.TO_MASTER.get((slot, an)) if hasattr(defn, 'TO_MASTER') else None
                def to_master(P, tm=tm, box=box, sh=scaled[png].shape):
                    bx0, by0, bx1, by1 = box                      # scaled crop px -> the png's own px
                    return tm(np.stack([bx0 + P[:, 0] * (bx1 - bx0) / sh[1], by0 + P[:, 1] * (by1 - by0) / sh[0]], 1))
                a, nv = rk.mesh_attachment(F, box, scaled[png], wf, bidx, W, grid_px=getattr(defn, 'GRID', 30),
                                           to_master=to_master if tm else None)
                stats[slot + '/' + an] = nv
            if png != an: a['path'] = png
            skin[slot][an] = a
        first = atts[0][0] if atts else None
        sj = {'name': slot, 'bone': bone}
        if first and defn.SLOT_DEFAULT.get(slot, first) is not None:
            sj['attachment'] = defn.SLOT_DEFAULT.get(slot, first)
        sj.update(defn.SLOT_EXTRA.get(slot, {}))
        slots_json.append(sj)
    # setup-pose bounds (units) from every default attachment's crop box
    xs, ys = [], []
    for slot, bone, atts in defn.SLOTS:
        if not atts: continue
        if (slot, atts[0][0]) in getattr(defn, 'TO_MASTER', {}): continue
        b = boxes[atts[0][1]]
        for px, py in ((b[0], b[1]), (b[2], b[3])):
            u = F.u(px, py); xs.append(u[0]); ys.append(u[1])
    sk = dict(defn.SKELETON)
    sk.update({'x': round(min(xs), 2), 'y': round(min(ys), 2), 'width': round(max(xs) - min(xs), 2)})
    cons = sorted([('ik', c) for c in defn.IK] + [('transform', c) for c in defn.TRANSFORM], key=lambda kc: kc[1]['order'])
    for k, (_, cdef) in enumerate(cons): cdef['order'] = k
    j = {'skeleton': sk, 'bones': bones, 'slots': slots_json,
         'ik': defn.IK, 'transform': defn.TRANSFORM,
         'skins': [{'name': 'default', 'attachments': skin}],
         'events': getattr(defn, 'EVENTS', {}), 'animations': {}}
    # pages
    for pn, img in zip(page_names, pages):
        Image.fromarray(img, 'RGBA').save(os.path.join(out_dir, pn), 'WEBP', quality=95, method=6, alpha_quality=100)
    atl = rk.atlas_text(page_names, [(p.shape[1], p.shape[0]) for p in pages], regions)
    open(os.path.join(out_dir, name + '.atlas'), 'w', encoding='utf-8', newline='\n').write(atl)
    print(f'{name}: {len(bones)} bones, {len(slots_json)} slots, {len(regions)} regions on {len(pages)} pages '
          f'{[p.shape[:2] for p in pages]}, mesh verts {sum(stats.values())}')
    return j, W, bidx


def write_json(j, out_dir, name):
    with open(os.path.join(out_dir, name + '.json'), 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(j, fh, separators=(',', ':'))
