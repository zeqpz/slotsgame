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
front) with identical meshes and weights. Both cut edges are anti-aliased, so where they meet the
background bled through as a thin pink line across the elbow. The back layer now carries the
whole arm, so the front layer's soft edge always sits over the same arm.
"""
import math
import numpy as np
import cv2
from PIL import Image
import meshkit as mk
import atlaskit as ak

KNEE_BLEND = 118     # half-width (skeleton units) of the thigh -> knee -> shin blend
HIP_BAND = (-30, 75)  # torso holds the waistband: full above the first value, none below the second
GRID = 25            # mesh spacing in atlas px (the boy's atlas is about 1 px per skeleton unit)


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
    weights = []
    for p in world:
        z = float((p - K) @ ax)
        w_th = float(mk.smoothstep(0, KNEE_BLEND, -z)); w_sh = float(mk.smoothstep(0, KNEE_BLEND, z))
        w_kn = 1 - w_th - w_sh
        zh = float((p - Hp) @ ut)                     # distance down the thigh from the hip
        hold = 1 - float(mk.smoothstep(HIP_BAND[0], HIP_BAND[1], zh))
        ws = {f"thigh_{side}": w_th * (1 - hold), "torso": w_th * hold, f"knee_{side}": w_kn, f"shin_{side}": w_sh}
        weights.append(ws)
    verts, uvs = mk.weighted_mesh(P, (rw, rh), world, weights, bidx, W)
    new = {"type": "mesh", "uvs": uvs, "triangles": [int(i) for i in T.flatten()], "vertices": verts,
           "hull": nh, "width": rw, "height": rh}
    if "path" in att: new["path"] = att["path"]
    j["skins"][0]["attachments"][slot][slot] = new
    return len(P), len(T)


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
    inner = fix_inner_thigh(atlas, pages)          # before the mesh, so the mesh hugs the new edge
    stats = {s: rebuild_leg(j, s, atlas, pages, W) for s in ("left", "right")}
    stats["inner thigh px"] = inner
    stats["shoe holes px"] = fill_shoe_holes(atlas, pages)
    merge_arm(atlas, pages)
    fix_wrists(j, atlas, pages, W)
    return stats
