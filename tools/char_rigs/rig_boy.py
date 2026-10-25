"""SMUKIEZ (the boy): joint repairs. Called from enhance.py on the delivered rig.

Legs: each trouser leg was one 45-vertex grid (a 4 x 8 lattice over the whole rectangle, hull =
the rectangle) blended thigh -> shin over a short band. The reactions bend the knees 50-77
degrees, so the inside of the knee folded over itself: a jagged notch opened where the art
flipped, and a hard crease cut across the other leg. Each leg is now a contour mesh that hugs
the drawn trouser (about 120 vertices), weighted along the leg through a knee helper bone that
turns half as far as the shin (a transform constraint), with wide smooth falloffs - the knee
bends like a soft tube of cloth instead of hinging. The waistband is held by the torso so it
stays tucked under the shirt hem while the thighs swing.

Left arm: drawn as two layers cut along one diagonal (arm_upper behind the torso, arm_left in
front). Both cut edges were anti-aliased, so the wall bled through as a hairline across the
elbow, and the straight cut slid across the sleeve whenever the arm turned. The arm is now one
whole layer in front of the shirt, and the sleeve's lower part is lifted out of the torso art
into its own slot (sleeve_left) in front of the arm: the arm slides under the sleeve's hem.

Also: the cash hands' wrists are rebuilt onto the forearm (fix_wrists), leg_right's inner edge
below the crotch is redrawn as one smooth curve (fix_inner_thigh), and the front sneaker's
see-through stitching is filled (fill_shoe_holes).
"""
import math
import numpy as np
import cv2
from PIL import Image
import meshkit as mk
import atlaskit as ak

KNEE_BLEND = 118     # half-width (skeleton units) of the thigh -> knee -> shin blend
HIP_BAND = (-30, 75)  # torso holds the waistband: full above the first value, none below the second
WHOLE_ARM_FRONT = True   # left arm: one layer in front of the shirt, under its own sleeve slot
IK_SOFT = 30         # units: the legs' IK eases straight over the last this-much of reach
CUFF_BAND = 90       # units above the foot over which the trouser hands over from shin to cuff bone
GRID = 25          # mesh spacing in atlas px (the boy's atlas is about 1 px per skeleton unit)


def add_knee_helpers(j):
    B = {b["name"]: b for b in j["bones"]}
    t = j.setdefault("transform", [])
    order = 1 + max([c.get("order", 0) for c in j.get("ik", [])] + [c.get("order", 0) for c in t] + [0])
    for side in ("left", "right"):
        name = f"knee_{side}"
        if name in B: continue
        thigh = B[f"thigh_{side}"]
        j["bones"].append({"name": name, "parent": f"thigh_{side}", "x": round(thigh.get("length", 0), 4), "y": 0, "length": 40})
        t.append({"name": name, "order": order, "bones": [name], "target": f"shin_{side}",
                  "mixRotate": 0.5, "mixX": 0, "mixY": 0, "mixScaleX": 0, "mixScaleY": 0, "mixShearY": 0})
        order += 1
    return [(f"knee_{s}", f"shin_{s}", 0.5) for s in ("left", "right")]


def soften_ik(j, W):
    """IK softness and a cuff that stays on the shoe.

    A two-bone IK snaps as the hip-to-foot distance reaches the bones' full length: the knee
    angle runs to zero in a frame or two (on every hop of win / big win the trouser legs visibly
    kinked straight). With softness the knee eases straight over the last IK_SOFT units of
    reach instead. The price is that a nearly straight leg now falls a little short of its foot -
    so the trouser cuff is weighted to a cuff bone that rides the shin's rotation but is pinned
    to the foot's position (a translate-only transform constraint): the cuff stays on the shoe."""
    for ik in j.get("ik", []):
        if ik["name"] in ("leg_left", "leg_right"):
            ik["softness"] = IK_SOFT
    B = {b["name"]: b for b in j["bones"]}
    t = j.setdefault("transform", [])
    order = 1 + max([c.get("order", 0) for c in j.get("ik", [])] + [c.get("order", 0) for c in t] + [0])
    for side in ("left", "right"):
        name = f"cuff_{side}"
        if name in B: continue
        lx, ly = mk.to_local(W[f"shin_{side}"], W[f"foot_{side}"][4:6])
        j["bones"].append({"name": name, "parent": f"shin_{side}", "x": round(lx, 3), "y": round(ly, 3), "length": 30})
        t.append({"name": name, "order": order, "bones": [name], "target": f"foot_{side}",
                  "mixRotate": 0, "mixX": 1, "mixY": 1, "mixScaleX": 0, "mixScaleY": 0, "mixShearY": 0})
        order += 1


def rebuild_leg(j, side, atlas, pages, W):
    bones = [b["name"] for b in j["bones"]]
    bidx = {n: i for i, n in enumerate(bones)}
    slot = f"leg_{side}"
    att = j["skins"][0]["attachments"][slot][slot]
    path = att.get("path", slot)
    pg, rx, ry, rw, rh = atlas.rect(path)
    img = pages[pg].crop((rx, ry, rx + rw, ry + rh))
    alpha = np.asarray(img)[..., 3]
    # the old mesh fixes where the region sits in the setup pose: uv -> world is an affine map
    old_uv = np.array(att["uvs"]).reshape(-1, 2) * [rw, rh]
    old_w = mk.mesh_world(att, bones, W)
    A, res = mk.fit_affine(old_uv, old_w)
    assert res < 0.5, f"{slot}: region is not placed affinely ({res})"
    poly = mk.outline(alpha, pad=3, step=GRID, tol=1.0)
    poly = np.clip(poly, 0, [rw, rh])
    # joint axis in world
    thigh, shin, knee = W[f"thigh_{side}"], W[f"shin_{side}"], W[f"knee_{side}"]
    K = np.array(shin[4:6]); Hp = np.array(thigh[4:6])
    ut = np.array([thigh[0], thigh[2]]); ut /= np.hypot(*ut)
    us = np.array([shin[0], shin[2]]); us /= np.hypot(*us)
    ax = ut + us; ax /= np.hypot(*ax)
    inner = mk.interior(poly, spacing=GRID, margin=.5)
    P, T, nh = mk.triangulate(poly, inner)
    world = mk.apply_affine(A, P)
    F = np.array(W[f"cuff_{side}"][4:6]) if f"cuff_{side}" in W else None
    weights = []
    for p in world:
        z = float((p - K) @ ax)
        w_th = float(mk.smoothstep(0, KNEE_BLEND, -z)); w_sh = float(mk.smoothstep(0, KNEE_BLEND, z))
        w_kn = 1 - w_th - w_sh
        zh = float((p - Hp) @ ut)                     # distance down the thigh from the hip
        hold = 1 - float(mk.smoothstep(HIP_BAND[0], HIP_BAND[1], zh))
        c = 0.0
        if F is not None:                             # the cuff rides the cuff bone (pinned to the foot)
            c = float(mk.smoothstep(-CUFF_BAND, -12, float((p - F) @ us)))
        ws = {f"thigh_{side}": w_th * (1 - hold), "torso": w_th * hold, f"knee_{side}": w_kn,
              f"shin_{side}": w_sh * (1 - c), f"cuff_{side}": w_sh * c}
        weights.append(ws)
    verts, uvs = mk.weighted_mesh(P, (rw, rh), world, weights, bidx, W)
    new = {"type": "mesh", "uvs": uvs, "triangles": [int(i) for i in T.flatten()], "vertices": verts,
           "hull": nh, "width": rw, "height": rh}
    if "path" in att: new["path"] = att["path"]
    j["skins"][0]["attachments"][slot][slot] = new
    return len(P), len(T)


# The lower part of the left sleeve, in the torso image's px: everything the forearm slides
# under. Its top and right edges lie on solid shirt (drawn over the same shirt, so they never
# show); its bottom is the sleeve's own drawn hem.
SLEEVE = [(0, 104), (131, 104), (128, 140), (126, 160), (124, 172), (121, 177), (117, 181), (113, 183.5),
          (110, 184), (100, 185), (60, 186), (20, 189), (0, 190)]   # the seam ends in a point at the hem


def split_sleeve(j, atlas, pages):
    """The forearm was drawn as two layers cut along a straight diagonal (elbow behind the
    torso, forearm in front), so whenever the arm turned, that straight cut slid across the
    sleeve - a hard diagonal edge of skin over the shirt. Now the whole arm is one layer in front
    of the shirt and the sleeve's hem is lifted out of the torso art into its own slot in front of
    the arm: the arm slides under the hem the way it does in the drawing."""
    T = np.asarray(ak.crop(pages, atlas, "torso")).copy()
    h, w = T.shape[:2]
    S = 8                                                    # anti-aliased mask
    big = np.zeros((h * S, w * S), np.uint8)
    cv2.fillPoly(big, [np.round(np.array(SLEEVE, float) * S).astype(np.int32)], 255)
    m = cv2.resize(big.astype(np.float32) / 255., (w, h), interpolation=cv2.INTER_AREA)
    ys, xs = np.nonzero((m > 0) & (T[..., 3] > 0))
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    img = T.copy(); img[..., 3] = (img[..., 3] * m + .5).astype(np.uint8)
    img = img[y0:y1, x0:x1]
    sw, sh = x1 - x0, y1 - y0
    pg = atlas.pages[-1]["name"]
    spot = ak.free_spot(atlas, pg, sw, sh)
    assert spot, "no room for the sleeve"
    atlas.add(pg, "sleeve_left", spot[0], spot[1], sw, sh)
    ak.paste(pages, atlas, "sleeve_left", Image.fromarray(img, "RGBA"))
    ta = j["skins"][0]["attachments"]["torso"]["torso"]
    assert not any(k in ta for k in ("rotation", "scaleX", "scaleY"))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    j["skins"][0]["attachments"]["sleeve_left"] = {"sleeve_left": {
        "x": round(ta.get("x", 0) + cx - ta["width"] / 2, 2), "y": round(ta.get("y", 0) - (cy - ta["height"] / 2), 2),
        "width": int(sw), "height": int(sh)}}
    # appended last: the draw-order keys of the cash clips address slots by index
    j["slots"].append({"name": "sleeve_left", "bone": "torso", "attachment": "sleeve_left"})


def merge_arm(atlas, pages, overlap=3):
    """The left arm is drawn as two layers cut along one diagonal: arm_upper (elbow, behind the
    torso) and arm_left (forearm, in front). Both cut edges are anti-aliased, and two half-covered
    pixels laid one over the other are still only three-quarters covered - a hairline of the wall
    showed through along the cut. Now:
    - arm_upper carries the whole arm, merged with ADDITIVE coverage (two complementary half-
      covered edge pixels add up to a fully covered one), so it is solid under the cut;
    - arm_left runs on `overlap` px past its cut with the elbow's own pixels, fading out, so its
      edge always lies over that solid arm."""
    up = mk.premul(ak.crop(pages, atlas, "arm_upper")); fo = mk.premul(ak.crop(pages, atlas, "arm_left"))
    assert up.shape == fo.shape
    whole = up + fo                                   # premultiplied sum: coverage adds across the cut
    a = whole[..., 3:4]
    whole = np.where(a > 1, whole / np.maximum(a, 1e-6), whole)
    seam = (up[..., 3] > .02) & (fo[..., 3] > .02)
    whole[seam] = whole[seam] / np.maximum(whole[seam][:, 3:4], 1e-6)   # fully covered along the cut
    ak.paste(pages, atlas, "arm_upper", Image.fromarray(mk.unpremul(whole), "RGBA"))
    if WHOLE_ARM_FRONT:     # the sleeve is its own slot over the arm (split_sleeve): no cut at all
        ak.paste(pages, atlas, "arm_left", Image.fromarray(mk.unpremul(whole), "RGBA"))
        return
    core = (fo[..., 3] > .5).astype(np.uint8)
    d = cv2.distanceTransform(1 - core, cv2.DIST_L2, 5)
    run = (d <= overlap) & (up[..., 3] > .02) & (fo[..., 3] < .995)
    fade = np.clip((overlap + .5 - d) / overlap, 0, 1)[..., None]
    front = fo.copy()
    ext = whole * fade
    front[run] = front[run] + ext[run] * (1 - front[run][:, 3:4])     # its own pixels over the run-on
    ak.paste(pages, atlas, "arm_left", Image.fromarray(mk.unpremul(front), "RGBA"))


HAND_POSES = ("hand_left_pinch", "hand_left_flick", "hand_left_release", "hand_left_tense", "hand_left_present")
WRIST_BAND = 60      # hand px from the wrist edge that are rebuilt
WRIST_FADE = 14      # the baked forearm fades in over this many px at the hand image's left edge
WRIST_BLEND = 26     # the hand's own wrist edge blends into the forearm over this many px
OUTLINE_W = 5.5      # px: the drawing's outline weight at the wrist


def fix_wrists(j, atlas, pages, W):
    """The counting / flicking hands (cash_count) were cut from the drawing with a soft wrist edge
    that did not meet the forearm: the forearm ends on a slant short of the hand at the top, so
    the shirt showed through the hand's half-transparent edge as a grey wedge, the thumb's
    highlight ended in a hard-edged white sliver, and the forearm's shading stopped in a vertical
    line under the hand. Each pose's wrist is rebuilt where it sits on the arm: the forearm is
    drawn into the hand image under the hand, the gap between the forearm's end and the hand is
    closed and filled with skin, and the top and bottom outlines are carried across the join -
    so the hand reads as growing out of the arm. Its far left edge fades out over the forearm
    itself (which is drawn the same there), so no edge shows when the hand turns."""
    bones = [b["name"] for b in j["bones"]]
    skin = j["skins"][0]["attachments"]
    hb = W["hand_left"]
    assert abs(hb[2]) < 1e-6 and abs(hb[0] - 1) < 1e-6, "hand_left must be unrotated in the setup pose"
    shared = {a.get("path") for s, atts in skin.items() if s != "hand_left" for a in atts.values()}
    for name in HAND_POSES:
        att = skin["hand_left"][name]
        assert not any(k in att for k in ("rotation", "scaleX", "scaleY"))
        pg, rx, ry, w, h = atlas.rect(att.get("path", name))
        H = mk.premul(pages[pg].crop((rx, ry, rx + w, ry + h)))
        x0 = hb[4] + att.get("x", 0) - w / 2; y1 = hb[5] + att.get("y", 0) + h / 2
        cvs = mk.Canvas(x0, y1 - h, x0 + w, y1, 1.0)
        F = np.zeros((cvs.h, cvs.w, 4), np.float32)
        for s in ("arm_upper", "arm_left"):
            a = skin[s][s]
            tex = mk.premul(ak.crop(pages, atlas, a.get("path", s)))
            th, tw = tex.shape[:2]
            uv = np.array(a["uvs"]).reshape(-1, 2) * [tw, th]
            mk.over(F, mk.raster_mesh(cvs, mk.mesh_world(a, bones, W), uv, np.array(a["triangles"]).reshape(-1, 3), tex))
        F = F[:h, :w]
        from scipy import ndimage
        xs = np.arange(w)[None, :].repeat(h, 0).astype(np.float32)
        # 1. the hand blends into the forearm over a wide band where its wrist edge lies on the arm
        Ha = H[..., 3]
        first = np.argmax(Ha > .05, 1)                          # where each row's hand begins
        on_arm = np.array([Ha[y].max() > .05 and first[y] < WRIST_BAND and F[y, min(w - 1, first[y] + 2), 3] > .5 for y in range(h)])
        on_arm = ndimage.binary_opening(on_arm, iterations=2)
        blend = np.clip((xs - first[:, None]) / WRIST_BLEND, 0, 1)
        blend = blend * blend * (3 - 2 * blend)
        Hw = H * np.where(on_arm[:, None], blend, 1.0)[..., None]
        C = mk.over(F.copy(), Hw)                                # the arm with the hand on it
        # 2. close the gap between the forearm's end and the hand (at 4x, for clean edges)
        S = 4
        U = ((F[..., 3] > .5) | (Ha > .9)).astype(np.float32)
        U4 = cv2.resize(U, (w * S, h * S), interpolation=cv2.INTER_LINEAR) > .5
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (19 * S, 19 * S))
        Uc4 = cv2.morphologyEx(U4.astype(np.uint8), cv2.MORPH_CLOSE, k)
        cov = cv2.resize(Uc4.astype(np.float32), (w, h), interpolation=cv2.INTER_AREA)
        din4 = ndimage.distance_transform_edt(Uc4) / S
        ink = cv2.resize((din4 <= OUTLINE_W).astype(np.float32) * Uc4, (w, h), interpolation=cv2.INTER_AREA)
        band = xs < WRIST_BAND
        need = band & (cov > C[..., 3] + .01)                    # closed shape not yet covered
        rgb = mk.unpremul(C)
        lum = rgb[..., :3].astype(np.float32).mean(-1)
        skin_px = (C[..., 3] > .95) & (lum > 120) & band
        _, (iy, ix) = ndimage.distance_transform_edt(~skin_px, return_indices=True)
        fill = cv2.GaussianBlur(rgb[iy, ix][..., :3].astype(np.float32) / 255., (0, 0), 1.5)
        out = C.copy()
        add = np.where(need, cov - C[..., 3], 0)[..., None]
        out[..., :3] += fill * add; out[..., 3:4] += add
        # 3. the outline carried across the join, only where the shape is new
        new_edge = cv2.dilate(need.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        la = (ink * new_edge)[..., None]
        out[..., :3] *= (1 - la)                                  # black over (premultiplied rgb 0)
        out[..., 3:4] = la * cov[..., None] + out[..., 3:4] * (1 - la)
        # 4. the baked forearm fades in from the image's left edge, over the real forearm
        fade = np.clip((xs - 1) / WRIST_FADE, 0, 1)
        own = Hw[..., 3] > .9
        out = out * np.where(own, 1.0, fade)[..., None]
        img = Image.fromarray(mk.unpremul(out), "RGBA")
        path = att.get("path", name)
        if path in shared:                          # another attachment draws this region too: keep it
            new = path + "_wrist"
            spot = ak.free_spot(atlas, pg, w, h)
            assert spot, f"no room on {pg} for {new}"
            atlas.add(pg, new, spot[0], spot[1], w, h)
            ak.paste(pages, atlas, new, img)
            att["path"] = new
        else:
            ak.paste(pages, atlas, path, img)


# leg_right's inner edge below the crotch, in its region's px (x at each y): a smooth curve from
# the hip line down to where the thigh's own outline resumes
INNER_EDGE_R = [(60, 19), (72, 16), (84, 13), (90, 17), (96, 26), (104, 32), (112, 35), (120, 36), (128, 32), (136, 27)]


def fix_inner_thigh(atlas, pages, region="leg_right", curve=INNER_EDGE_R, outline=6.0):
    """Where the trouser legs met in the drawing, leg_right kept a thin black wedge of the other
    leg's crease (a spike off the inside of the thigh, with a sliver of the other leg's white
    highlight beside it) and a notch of wall behind it. Once the legs move apart that read as a
    jagged tear. The inner edge there is redrawn as one smooth curve along the thigh's own
    outline: outside it is cleared, and anything left between it and the thigh is outline."""
    from scipy import ndimage
    img = ak.crop(pages, atlas, region)
    A = np.asarray(img).astype(np.float32) / 255.
    h, w = A.shape[:2]
    ys = np.array([p[0] for p in curve], float); xs = np.array([p[1] for p in curve], float)
    S = 4                                                   # work at 4x for smooth edges
    yy, xx = np.mgrid[0:h * S, 0:w * S] / S
    edge_x = np.interp(yy, ys, xs)
    rows = (yy >= ys[0]) & (yy <= ys[-1])
    near = xx < edge_x + 40
    inside4 = ~(rows & near & (xx < edge_x))
    inside = cv2.resize(inside4.astype(np.float32), (w, h), interpolation=cv2.INTER_AREA)
    d4 = np.abs(xx - edge_x)                                # horizontal distance to the curve
    ink4 = rows & near & (xx >= edge_x) & (xx < edge_x + outline)
    ink = cv2.resize(ink4.astype(np.float32), (w, h), interpolation=cv2.INTER_AREA)
    zone = cv2.resize((rows & near).astype(np.float32), (w, h), interpolation=cv2.INTER_AREA) > 0
    rgb = A[..., :3]; a = A[..., 3]
    lum = rgb.mean(-1)
    body4 = rows & near & (xx >= edge_x)
    body = cv2.resize(body4.astype(np.float32), (w, h), interpolation=cv2.INTER_AREA)
    out = A.copy()
    z = zone
    # inside the curve: the drawing, over outline where it was empty; outside: nothing
    cover = np.maximum(a, body)
    out[z, :3] = (rgb[z] * a[z][:, None]) / np.maximum(cover[z], 1e-4)[:, None]   # black under
    out[z, 3] = (inside * cover)[z]
    out[z, :3] = out[z, :3] * (1 - ink[z][:, None])
    soft = cv2.GaussianBlur(out[..., 3], (0, 0), .6)                # the old interior edge was aliased
    out[z, 3] = soft[z]
    # the stray white sliver left of the hip line above the curve
    stray = (yy[::S, ::S] < ys[0] + 2) & (yy[::S, ::S] > ys[0] - 24) & (lum > .8) & (np.arange(w)[None, :] < 26)
    out[stray, 3] = 0
    ak.paste(pages, atlas, region, Image.fromarray((out.clip(0, 1) * 255 + .5).astype(np.uint8), "RGBA"))
    return int(z.sum())


def despike_leg(atlas, pages, region, box, radius=5):
    """A thin spike of outline (the crease where the legs met in the drawing) stuck out of the
    inside of the thigh once the legs moved apart: opened away (only inside `box`)."""
    img = ak.crop(pages, atlas, region)
    A = np.asarray(img).astype(np.float32)
    m = (A[..., 3] > 8).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius + 1, 2 * radius + 1))
    opened = cv2.morphologyEx(m, cv2.MORPH_OPEN, k).astype(bool)
    x0, y0, x1, y1 = box
    inbox = np.zeros_like(opened); inbox[y0:y1, x0:x1] = True
    keep = opened | ~inbox
    soft = cv2.GaussianBlur(keep.astype(np.float32), (0, 0), .7)
    A[..., 3] = np.minimum(A[..., 3], np.where(inbox, soft * 255, 255))
    ak.paste(pages, atlas, region, Image.fromarray(A.clip(0, 255).astype(np.uint8), "RGBA"))
    return int((m.astype(bool) & ~keep).sum())


def fill_shoe_holes(atlas, pages, region="shoe_left", ref="shoe_right"):
    """The front shoe's lace stitching and side mesh were cut out of the art as see-through
    holes (the other shoe's mesh is painted dark red): the wall showed through the shoe. Every
    hole enclosed by the shoe is filled with that dark red, under the art's own soft edges."""
    from scipy import ndimage
    A = np.asarray(ak.crop(pages, atlas, region)).astype(np.float32) / 255.
    R = np.asarray(ak.crop(pages, atlas, ref)).astype(np.float32) / 255.
    red = (R[..., 3] > .95) & (R[..., 0] > .3) & (R[..., 0] < .55) & (R[..., 1] < .08) & (R[..., 2] < .08)
    colour = np.median(R[red][:, :3], 0) if red.any() else np.array([.45, 0, 0])
    t = A[..., 3] < .5
    lab, n = ndimage.label(t)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) | {0}
    holes = np.isin(lab, [i for i in range(1, n + 1) if i not in edge])
    zone = ndimage.binary_dilation(holes, iterations=2) & (A[..., 3] < .999)
    a = A[..., 3:4]
    out = A.copy()
    out[zone, :3] = (A[..., :3] * a + colour * (1 - a))[zone]
    out[zone, 3] = 1.0
    ak.paste(pages, atlas, region, Image.fromarray((out * 255 + .5).astype(np.uint8), "RGBA"))
    return int(holes.sum())


FACES = ("face_idle", "face_win", "face_big_win", "face_lose", "face_anticipation", "face_cash_show", "face_cash_count")


def fix_faces(atlas, pages):
    """Every face pose: the beanie's hanging tip gets the hair under it that the other side of
    his head has (the wedge of wall between tip and cheek read as the beanie chopped off), and
    the jaw's broken lower-right corner is redrawn round (artfix.py)."""
    import artfix
    done = {}
    for n in FACES:
        img = np.asarray(ak.crop(pages, atlas, n)).copy()
        img, a = artfix.beanie_tip(img)
        img, b = artfix.jaw_corner(img)
        ak.paste(pages, atlas, n, Image.fromarray(img, "RGBA"))
        done[n] = (a, b)
    return done


# The stripe of wall between the legs up to the shirt hem read as a cut in the jeans. A backing
# in the jeans' colour sits behind both legs: its top under the hem, its sides under each leg, and
# its lower edge - with the drawing's outline - is the crotch seam where the inner leg lines meet.
# It also runs on to the right under the shirt's flared hem, where a sliver of wall showed between
# the hem and the right hip (the jeans' waistband belongs there).
CROTCH = {"x": (-78, 74), "y_top": 500,
          "seam": [(-78, 446), (-52, 432), (-38, 427), (-24, 429), (14, 446), (44, 462), (74, 474)],
          "ink": 5.5}


def crotch_backing(j, atlas, pages, W):
    from scipy import ndimage
    bones = [b["name"] for b in j["bones"]]
    bidx = {n: i for i, n in enumerate(bones)}
    # the jeans' colours, sampled from the legs near the crotch
    legs = [np.asarray(ak.crop(pages, atlas, n)).astype(np.float32) for n in ("leg_left", "leg_right")]
    px = np.concatenate([L[L[..., 3] > 250][:, :3] for L in legs])
    lum = px.mean(-1)
    jeans = np.median(px[(lum > 45) & (lum < 110)], 0)
    inkc = np.median(px[lum < 30], 0) if (lum < 30).any() else np.zeros(3)
    x0, x1 = CROTCH["x"]; yt = CROTCH["y_top"]
    sx = np.array([p[0] for p in CROTCH["seam"]], float); sy = np.array([p[1] for p in CROTCH["seam"]], float)
    yb = int(sy.min()) - 8
    S = 4
    w, h = (x1 - x0), (yt - yb)
    xs = x0 + (np.arange(w * S) + .5) / S
    ys = yt - (np.arange(h * S) + .5) / S
    X, Y = np.meshgrid(xs, ys)
    seam = np.interp(X, sx, sy)
    inside = Y > seam
    # ink band along the seam, the drawing's weight
    dist = ndimage.distance_transform_edt(inside) / S
    cov = cv2.resize(inside.astype(np.float32), (w, h), interpolation=cv2.INTER_AREA)
    d1 = cv2.resize(dist.astype(np.float32), (w, h), interpolation=cv2.INTER_AREA)
    ink_a = np.clip(CROTCH["ink"] + .5 - d1, 0, 1)[..., None]
    rgb = jeans * (1 - ink_a) + inkc * ink_a
    img = np.concatenate([rgb, cov[..., None] * 255], -1).clip(0, 255).astype(np.uint8)
    # region on the boy's second page
    pg = "smukiez-2.png" if "smukiez-2.png" in pages else atlas.pages[0]["name"]
    spot = ak.free_spot(atlas, pg, w, h)
    assert spot, "no room for crotch_fill"
    atlas.add(pg, "crotch_fill", spot[0], spot[1], w, h)
    ak.paste(pages, atlas, "crotch_fill", Image.fromarray(img, "RGBA"))
    # mesh: left part follows the left thigh, right part the right thigh, the top the torso
    L_in, R_in = -38.0, -24.0            # the two legs' inner edges at the crotch
    poly = mk.outline(img[..., 3], pad=1, step=12, tol=.8, thresh=1)
    poly = np.clip(poly, 0, [w, h])
    inner = mk.interior(poly, spacing=12, margin=.5)
    P, T, nh = mk.triangulate(poly, inner)
    world = np.stack([x0 + P[:, 0], yt - P[:, 1]], 1)
    weights = []
    for xw, yw in world:
        r = float(mk.smoothstep(L_in - 6, R_in + 6, xw))        # 0 = left thigh, 1 = right thigh
        hold = float(mk.smoothstep(yt - 46, yt - 6, yw))          # under the hem: the torso
        weights.append({"thigh_left": (1 - r) * (1 - hold), "thigh_right": r * (1 - hold), "torso": hold})
    verts, uvs = mk.weighted_mesh(P, (w, h), world, weights, bidx, W)
    j["skins"][0]["attachments"]["crotch_fill"] = {"crotch_fill": {
        "type": "mesh", "path": "crotch_fill", "uvs": uvs, "triangles": [int(i) for i in T.flatten()],
        "vertices": verts, "hull": nh, "width": w, "height": h}}
    # first in the draw order: behind everything (offsets in the draw-order keys stay valid)
    j["slots"].insert(0, {"name": "crotch_fill", "bone": "root", "attachment": "crotch_fill"})
    return len(P)


# Socks (owner, 2026-10-24: his left shoe "has an open spot"). The trouser cuffs stop short of
# the shoes' tongues, and in the notch between a cuff's front and the shoe the wall showed
# through where his ankle should be.
SOCK_FILL, SOCK_SHADE, SOCK_INK = (238, 236, 232), (196, 195, 193), (12, 12, 14)


# One sock, fitted (owner, 2026-10-25): the front-on shoe's sock only ever showed as a white
# wedge sticking out beside the shoe, so it goes; the side-on shoe's sock is cut to the open spot
# itself instead of a box - it fills exactly what shows between the cuff and the shoe, with the
# art's line only along its open sides, and tucks a little way under both so a moving cuff never
# uncovers the wall. Behind the shoe and the jeans, it can never cover either.
SOCK_FIT = dict(side="left", box=(-420, 90, -10, 380), s=1.25, close=40, up=45, down=20, line=5.5)


def raster_region(cv, att, bone_W, tex):
    """Draw a region attachment (premultiplied tex) into a canvas-sized layer."""
    h, w = tex.shape[:2]
    sx, sy = att.get("scaleX", 1), att.get("scaleY", 1)
    r = math.radians(att.get("rotation", 0)); cs, sn = math.cos(r), math.sin(r)
    def world(u, v):
        lx, ly = (u - w / 2) * sx, (h / 2 - v) * sy
        lx, ly = lx * cs - ly * sn + att.get("x", 0), lx * sn + ly * cs + att.get("y", 0)
        return mk.to_world(bone_W, (lx, ly))
    src = np.float32([[0, 0], [w, 0], [0, h]])
    dst = np.float32(cv.to_px(np.array([world(0, 0), world(w, 0), world(0, h)], float)))
    return cv2.warpAffine(tex, cv2.getAffineTransform(src, dst), (cv.w, cv.h), flags=cv2.INTER_LINEAR, borderValue=0)


def fit_sock(j, atlas, pages, W):
    from scipy import ndimage
    side, F = SOCK_FIT["side"], SOCK_FIT
    s = F["s"]
    cv = mk.Canvas(*F["box"], s)
    skin = j["skins"][0]["attachments"]
    bones = [b["name"] for b in j["bones"]]
    leg = skin[f"leg_{side}"][f"leg_{side}"]
    tex = mk.premul(ak.crop(pages, atlas, leg.get("path", f"leg_{side}")))
    th, tw = tex.shape[:2]
    jeans = mk.raster_mesh(cv, mk.mesh_world(leg, bones, W), np.array(leg["uvs"]).reshape(-1, 2) * [tw, th],
                           np.array(leg["triangles"]).reshape(-1, 3), tex)[..., 3] > .5
    shoe_att = skin[f"shoe_{side}"][f"shoe_{side}"]
    shoe = raster_region(cv, shoe_att, W[f"shoe_{side}"], mk.premul(ak.crop(pages, atlas, shoe_att.get("path", f"shoe_{side}"))))[..., 3] > .5
    U = jeans | shoe
    closed = cv2.morphologyEx(U.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * int(F["close"] * s) + 1,) * 2)).astype(bool)
    gap = closed & ~U
    # the ankle: the openings that lie between the cuff and the shoe (touching both)
    lab, n = ndimage.label(gap)
    near_j = cv2.dilate(jeans.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    near_s = cv2.dilate(shoe.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    keep = [i for i in range(1, n + 1) if ((lab == i) & near_j).any() and ((lab == i) & near_s).any() and (lab == i).sum() > 40]
    ankle = np.isin(lab, keep)
    if not ankle.any():
        return []
    # The sock itself is an ankle tube: as wide as the opening (from notch to notch), down into the
    # shoe and up under the cuff, so when a reaction lifts the cuff the sock is what shows - but
    # never wider than the drawn figure (it stays inside the closed silhouette), so at rest only
    # the opening shows.
    gys, gxs = np.nonzero(ankle)
    box = np.zeros_like(ankle)
    box[max(0, gys.min() - int(F["up"] * s)): gys.max() + int(F["down"] * s), gxs.min(): gxs.max() + 1] = True
    sock = ndimage.binary_fill_holes((closed & box) | ankle)
    # paint: white, greying toward the back of the foot (left), a few soft ribs, and the art's line
    # along the open sides only (the cuff and the shoe draw their own edges)
    ys, xs = np.nonzero(sock)
    x0, x1 = xs.min(), xs.max()
    u = (np.arange(cv.w)[None, :] - x0) / max(1, x1 - x0)
    shade = np.clip((u - .05) / .45, 0, 1)
    rgb = np.array(SOCK_SHADE, np.float32) * (1 - shade[..., None]) + np.array(SOCK_FILL, np.float32) * shade[..., None]
    rgb = np.broadcast_to(rgb, (cv.h, cv.w, 3)).copy()
    rib = (np.abs(((np.arange(cv.w) - x0) / (9 * s)) % 1 - .5) < .07)[None, :] & np.ones((cv.h, 1), bool)
    rgb[rib] *= .93
    dS = ndimage.distance_transform_edt(sock)                      # its own edge all round: at rest only the
    ink = (np.clip(F["line"] * s + .5 - dS, 0, 1) * sock)[..., None]   # opening's open sides show
    rgb = rgb * (1 - ink) + np.array(SOCK_INK, np.float32) * ink
    a = cv2.GaussianBlur(sock.astype(np.float32), (3, 3), 0)
    img = np.concatenate([rgb, a[..., None] * 255], -1).clip(0, 255).astype(np.uint8)
    by0, by1, bx0, bx1 = ys.min() - 2, ys.max() + 3, x0 - 2, x1 + 3
    img = img[by0:by1, bx0:bx1]
    h, w = img.shape[:2]
    name = f"sock_{side}"
    pg = "smukiez-2.png" if "smukiez-2.png" in pages else atlas.pages[0]["name"]
    spot = ak.free_spot(atlas, pg, w, h)
    assert spot, f"no room for {name}"
    atlas.add(pg, name, spot[0], spot[1], w, h)
    ak.paste(pages, atlas, name, Image.fromarray(img, "RGBA"))
    # a region on the shoe bone: its centre in the bone's frame, 1/s units per px
    c = cv.to_world(np.array([[(bx0 + bx1) / 2, (by0 + by1) / 2]], float))[0]
    lx, ly = mk.to_local(W[f"shoe_{side}"], c)
    rot = -math.degrees(math.atan2(W[f"shoe_{side}"][2], W[f"shoe_{side}"][0]))
    skin[name] = {name: {"x": round(lx, 3), "y": round(ly, 3), "rotation": round(rot, 3), "width": w, "height": h,
                         "scaleX": round(1 / s, 5), "scaleY": round(1 / s, 5)}}
    names = [sl["name"] for sl in j["slots"]]
    first = min(names.index("shoe_left"), names.index("shoe_right"))
    j["slots"].insert(first, {"name": name, "bone": f"shoe_{side}", "attachment": name})   # behind both shoes
    return [name]


def finish_socks(j):
    """After every clip is final: each sock shows and hides with its shoe (the shoe's alpha and
    attachment keys, copied), and the cash clips' draw-order keys hold each sock in place - an
    offset key moves a slot by places, so a new slot it passes over would shift where it lands."""
    names = [sl["name"] for sl in j["slots"]]
    sides = [s for s in ("left", "right") if f"sock_{s}" in names]
    if not sides:
        return 0
    n = 0
    for anim in j["animations"].values():
        slots = anim.get("slots", {})
        for side in sides:
            shoe, sock = f"shoe_{side}", f"sock_{side}"
            if shoe in slots:
                tl = {}
                for kind, keys in slots[shoe].items():
                    if kind == "attachment":
                        tl[kind] = [dict(k, name=(sock if k.get("name") == shoe else k.get("name"))) if "name" in k else dict(k) for k in keys]
                    else:
                        tl[kind] = [dict(k) for k in keys]
                slots[sock] = tl; n += 1
        for key in anim.get("drawOrder", []):
            offs = key.get("offsets")
            if not offs:
                continue
            have = {o["slot"] for o in offs}
            for sock in (f"sock_{s}" for s in sides):
                if sock not in have:
                    offs.append({"slot": sock, "offset": 0})
            offs.sort(key=lambda o: names.index(o["slot"]))
    return n


def draw_order(names, offsets):
    """Spine's draw order for an offsets key (SkeletonJson), for checking."""
    count = len(names)
    order = [-1] * count; unchanged = [0] * (count - len(offsets))
    oi = ui = 0
    for o in offsets:
        si = names.index(o["slot"])
        while oi != si:
            unchanged[ui] = oi; ui += 1; oi += 1
        order[oi + o["offset"]] = oi; oi += 1
    while oi < count:
        unchanged[ui] = oi; ui += 1; oi += 1
    for i in range(count - 1, -1, -1):
        if order[i] == -1:
            ui -= 1; order[i] = unchanged[ui]
    return [names[i] for i in order]


def fix(j, atlas, pages):
    for ik in j.get("ik", []):
        if ik["name"] in ("leg_left", "leg_right"):
            ik["stretch"] = True
    # The trouser legs hung from the hips (body) while the shirt rides the torso: every lean of
    # the torso pulled the hem off the waistband. The thighs hang from the torso.
    B = {b["name"]: b for b in j["bones"]}
    t = B["torso"]
    for leg in ("thigh_left", "thigh_right"):
        b = B[leg]
        if b.get("parent") == "body":
            b["parent"] = "torso"
            b["x"] = round(b.get("x", 0) - t.get("x", 0), 3)
            b["y"] = round(b.get("y", 0) - t.get("y", 0), 3)
    helpers = add_knee_helpers(j)
    W = mk.setup_world(j["bones"], helpers)
    soften_ik(j, W)
    W = mk.setup_world(j["bones"], helpers)
    inner = fix_inner_thigh(atlas, pages)        # before the mesh, so the mesh hugs the new edge
    stats = {s: rebuild_leg(j, s, atlas, pages, W) for s in ("left", "right")}
    stats["inner thigh px"] = inner
    stats["shoe holes px"] = fill_shoe_holes(atlas, pages)
    if WHOLE_ARM_FRONT:
        split_sleeve(j, atlas, pages)
    merge_arm(atlas, pages)
    fix_wrists(j, atlas, pages, W)
    stats["faces (hair px, jaw px)"] = fix_faces(atlas, pages)
    stats["crotch_fill verts"] = crotch_backing(j, atlas, pages, W)
    stats["socks"] = fit_sock(j, atlas, pages, W)
    return stats
