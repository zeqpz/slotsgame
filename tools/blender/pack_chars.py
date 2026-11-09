"""Pack a character for the game as a LIVE 2D RIG (2026-11-09; until then every clip shipped as pre-rendered WebP
frames, 40-150 MB a figure per density): the parts' images in one small atlas per density plus Blender's own per-frame
part transforms and bone deforms, drawn live by frontend/charrig.js. No motion is made here - every number comes off
the character's .blend. What a rig cannot be (Grease Pencil: the boy's dust and glints, the skull's ember glow and
ash, the skull's smoke loop) ships as small frame tracks.

From the .blend to the game, per character (boy, skull):
  1. the clips and renders, if the .blend changed (tools/blender/chars/<char>/run.py: anim, render, meta). The renders
     are what the rig is checked against; meta.json gives the fps, size, ground, cues, shoe and ember tracks; the
     skull's smoke loop is renders/smoke/.
  2. the rig, read off the .blend (read only):
       "C:/Users/CooperHinkel/Blender/blender-5.2.3-windows-x64/blender.exe" -b --factory-startup \\
           art/blender/chars/<char>/<char>.blend --python tools/blender/chars/rig/export_rig.py -- \\
           art/blender/chars/<char>/renders/rig.json
  3. the effects on their own (read only):
       "C:/Users/CooperHinkel/Blender/blender-5.2.3-windows-x64/blender.exe" -b --factory-startup \\
           art/blender/chars/<char>/<char>.blend --python tools/blender/chars/rig/render_fx.py
  4. this packer:  python tools/blender/pack_chars.py <char,char..|all> [--out <dir>]
     (--out writes the pack elsewhere, e.g. to check it before it replaces the game's; default frontend/assets/chars)
  5. the parity check, every clip, the game's rig player vs the renders (sheets + PSNR in art/blender/chars/<char>/qa/rig):
       node tools/blender/chars/rig/parity.mjs <char> <dd> [step]
       python tools/blender/chars/rig/parity.py <char> <dd>
     and look at the sheets (3x zooms of the moving joints) before shipping.

What it writes to <out>/<char>/:
  rig.bin                 the geometry (each part's vertices in its own space - rigid parts - or in the armature's
                          rest space with up to 4 bone weights - skinned parts -, its triangles) and the animation:
                          every distinct pose once (each rigid part's 2D map and each bone's deform map, int16), which
                          parts show and in what order (Eevee's depth sort), and per clip, frame -> pose
  <dd>/atlas<k>.webp      the parts' images at density dd (d5 = half the master frame's size, d7, d10 = full),
                          straight alpha, colour bled into the clear texels (the game samples them in linear light)
  <dd>/uv.bin             each part's atlas UVs at that density (uint16)
  <dd>/fx_<clip>.bin      a clip's effect frames (only the frames that have any, each cropped to what it shows),
                          WebP back to back; fxmask_<clip>.bin: the skull's ash in the unlit mask
  <dd>/smoke.bin          the skull's own smoke loop, at half the figure's density (soft, it needs no more)
  manifest.json           sizes, rest height, ground, densities, each clip's frames / loop / cues, the rig's layout,
                          the tracks' frames and boxes, and the per-frame shoe spans / ember the game follows
"""
import glob, io, json, math, os, sys
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "art", "blender", "chars")
OUT = os.path.join(ROOT, "frontend", "assets", "chars")
DENSITIES = {"boy": (.25, .35, .5, .7), "skull": (.5, .7, 1.0)}
SNAP = {"boy": 20, "skull": 10}       # master px: a box on this grid is a whole number of px at every density
ATLAS_Q, FX_Q, SMOKE_Q = 90, 84, 84
SMOKE_SCALE = .5                      # the smoke loop at half the figure's density
PAGE = 2048                           # atlas page limit (old iPhones: never 4096)
PAD = 4                               # texels round each tile, filled with its edge colours (mipmaps never bleed)


def dname(d):
    """A density's folder name: tenths (d5, d7, d10) when exact, else hundredths (d25, d35)."""
    return f"d{round(d * 10)}" if abs(d * 10 - round(d * 10)) < 1e-6 else f"d{round(d * 100)}"


def resize(im, size):
    """Shrink with the colour premultiplied, so see-through edges never pick up dark fringes."""
    return im.convert("RGBa").resize(size, Image.LANCZOS).convert("RGBA")


def bleed(im, passes):
    """Straight-alpha image -> the same with the colour of its painted texels spread into the clear ones (alpha
    untouched): sampled with bilinear / mipmap filtering in straight alpha, an edge then never darkens."""
    a = np.asarray(im, np.float32)
    rgb, al = a[..., :3].copy(), a[..., 3]
    have = al > 0
    for _ in range(passes):
        if have.all():
            break
        acc = np.zeros_like(rgb); cnt = np.zeros(have.shape, np.float32)
        hp = np.pad(have, 1); rp = np.pad(rgb * have[..., None], ((1, 1), (1, 1), (0, 0)))
        for dy in (0, 1, 2):
            for dx in (0, 1, 2):
                acc += rp[dy:dy + have.shape[0], dx:dx + have.shape[1]]
                cnt += hp[dy:dy + have.shape[0], dx:dx + have.shape[1]]
        new = (~have) & (cnt > 0)
        rgb[new] = acc[new] / cnt[new, None]
        have = have | new
    out = np.dstack([np.clip(np.round(rgb), 0, 255), al]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def webp(im, q, alpha_q=100, method=6):
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=q, method=method, alpha_quality=alpha_q, exact=True)
    return buf.getvalue()


def snap_box(box, m, W, H):
    x0, y0, x1, y1 = box
    return (max(0, x0 // m * m), max(0, y0 // m * m), min(W, -(-x1 // m) * m), min(H, -(-y1 // m) * m))


def alpha_box(a, pad=2):
    ys, xs = np.nonzero(a > 0)
    if not len(xs):
        return None
    return int(xs.min()) - pad, int(ys.min()) - pad, int(xs.max()) + pad + 1, int(ys.max()) + pad + 1


# ------------------------------------------------------------------------------------------------ the rig
def ap(A, P):
    a, b, c, d, e, f, tx, ty = A
    return np.stack([a * P[:, 0] + c * P[:, 2] + e * P[:, 1] + tx, b * P[:, 0] + d * P[:, 2] + f * P[:, 1] + ty], 1)


def build_rig(char, R, meta):
    st = R["static"]
    clips = R["clips"]
    names = list(st)
    # canonical part order: by depth in the first frame each shows (farthest first)
    first = {}
    for C in clips.values():
        for fr in C["frames"]:
            for n, p in fr["parts"].items():
                first.setdefault(n, p["z"])
    names = sorted(names, key=lambda n: -first.get(n, -1e9))
    rigid = [n for n in names if not st[n]["skinned"]]
    bones = list(R["bones"])
    need_arm = any(not ws for n in names if st[n]["skinned"] for ws in st[n]["w"])
    if need_arm:
        bones.append("__arm")
    items = len(rigid) + len(bones)
    # depth (y) folded into the translation: every rigid plane is flat in its own space, and the bones only turn in
    # the picture plane (checked)
    y0 = {}
    for n in rigid:
        L = np.array(st[n]["local"]).reshape(-1, 3)
        assert np.ptp(L[:, 1]) < 1e-6, (n, "not flat")
        y0[n] = float(L[0, 1])
    ymax = max([abs(np.array(st[n]["rest"]).reshape(-1, 3)[:, 1]).max() for n in names if st[n]["skinned"]] or [0])
    rows, vis, keys = [], [], []
    efmax = 0.0
    for clip, C in clips.items():
        for fr in C["frames"]:
            row = np.zeros((items, 6), np.float64)
            for k, n in enumerate(rigid):
                p = fr["parts"].get(n)
                if p is None:
                    continue
                a, b, c, d, e, f, tx, ty = p["A"]
                row[k] = (a, b, c, d, tx + e * y0[n], ty + f * y0[n])
            for k, bn in enumerate(bones):
                A = R["arm_identity"] if bn == "__arm" else fr["bones"][bn]
                efmax = max(efmax, abs(A[4]), abs(A[5]))
                row[len(rigid) + k] = (A[0], A[1], A[2], A[3], A[6], A[7])
            order = sorted(fr["parts"], key=lambda n: -fr["parts"][n]["z"])
            v = np.zeros(len(names), np.uint8)
            for r, n in enumerate(order):
                v[names.index(n)] = r + 1
            rows.append(row); vis.append(v)
    assert efmax * ymax < .01, ("bones tilt out of the picture plane", efmax, ymax)
    rows = np.array(rows)
    mx_m = np.abs(rows[:, :, :4]).max(); mx_t = np.abs(rows[:, :, 4:]).max()
    qm = min(256, math.floor(32000 / mx_m)); qt = min(16, math.floor(32000 / mx_t))
    q = np.empty(rows.shape, np.int16)
    q[:, :, :4] = np.round(rows[:, :, :4] * qm); q[:, :, 4:] = np.round(rows[:, :, 4:] * qt)
    # every distinct pose once
    table, poses, pvis, maps, i = {}, [], [], {}, 0
    for clip, C in clips.items():
        mp = []
        for _ in C["frames"]:
            key = q[i].tobytes() + vis[i].tobytes()
            if key not in table:
                table[key] = len(poses); poses.append(q[i]); pvis.append(vis[i])
            mp.append(table[key]); i += 1
        maps[clip] = mp
    return {"names": names, "rigid": rigid, "bones": bones, "qm": qm, "qt": qt, "poses": np.array(poses),
            "vis": np.array(pvis), "maps": maps, "y0": y0}


def rig_error(char, R, rg):
    """max |vertex from the quantised pose - vertex from Blender's floats|, master px (rigid + skinned parts)"""
    st = R["static"]
    qf = rg["poses"].astype(np.float64); qf[:, :, :4] /= rg["qm"]; qf[:, :, 4:] /= rg["qt"]
    worst = 0.0
    for clip, C in R["clips"].items():
        for fi in sorted({0, len(C["frames"]) // 2, len(C["frames"]) - 1}):
            fr = C["frames"][fi]; P = qf[rg["maps"][clip][fi]]
            for n, p in fr["parts"].items():
                s = st[n]
                if not s["skinned"]:
                    L = np.array(s["local"]).reshape(-1, 3)
                    k = rg["rigid"].index(n); a, b, c, d, tx, ty = P[k]
                    mine = np.stack([a * L[:, 0] + c * L[:, 2] + tx, b * L[:, 0] + d * L[:, 2] + ty], 1)
                    ref = ap(p["A"], L)
                else:
                    rest = np.array(s["rest"]).reshape(-1, 3)
                    mine = np.zeros((len(rest), 2)); ref = np.zeros((len(rest), 2))
                    for vi, ws in enumerate(s["w"]):
                        ws = ws[:4] if ws else [["__arm", 1.0]]
                        tot = sum(w for _, w in ws)
                        for bn, w in ws:
                            k = len(rg["rigid"]) + rg["bones"].index(bn); a, b, c, d, tx, ty = P[k]
                            x, z = rest[vi, 0], rest[vi, 2]
                            mine[vi] += w / tot * np.array([a * x + c * z + tx, b * x + d * z + ty])
                        wsall = s["w"][vi] or [["__arm", 1.0]]
                        tot = sum(w for _, w in wsall)
                        for bn, w in wsall:
                            A = R["arm_identity"] if bn == "__arm" else fr["bones"][bn]
                            ref[vi] += w / tot * ap(A, rest[vi:vi + 1])[0]
                worst = max(worst, float(np.abs(mine - ref).max()))
    return worst


def texel_ratio(R, name):
    """master px per texel of a part's image, where it shows at its full size (the median over its triangles)"""
    st = R["static"]; s = st[name]
    for C in R["clips"].values():
        for fr in C["frames"]:
            p = fr["parts"].get(name)
            if p is None:
                continue
            if s["skinned"]:
                rest = np.array(s["rest"]).reshape(-1, 3); v = np.zeros((len(rest), 2))
                for i, ws in enumerate(s["w"]):
                    ws = ws or [["__arm", 1.0]]; tot = sum(w for _, w in ws)
                    for bn, w in ws:
                        A = R["arm_identity"] if bn == "__arm" else fr["bones"][bn]
                        v[i] += w / tot * ap(A, rest[i:i + 1])[0]
            else:
                v = ap(p["A"], np.array(s["local"]).reshape(-1, 3))
            uv = np.array(s["uv"]).reshape(-1, 2) * s["img"]["size"]
            t = np.array(s["tris"]).reshape(-1, 3)
            r = []
            for i, j in ((0, 1), (1, 2), (2, 0)):
                e = np.linalg.norm(v[t[:, j]] - v[t[:, i]], axis=1); u = np.linalg.norm(uv[t[:, j]] - uv[t[:, i]], axis=1)
                ok = u > 1e-6
                r += list(e[ok] / u[ok])
            return float(np.median(r))
    return None


def pack_atlas(tiles):
    """tiles {key: Image} -> pages [(w, h)], place {key: (page, x, y)}: shelves, tallest first, pages <= PAGE"""
    order = sorted(tiles, key=lambda k: (-tiles[k].height, -tiles[k].width))
    area = sum((t.width + 2 * PAD) * (t.height + 2 * PAD) for t in tiles.values())
    best = None
    for W in (256, 512, 1024, 2048):
        if W > PAGE:
            break
        pages, place, x, y, row, pg = [], {}, 0, 0, 0, 0
        for k in order:
            t = tiles[k]; w, h = t.width + 2 * PAD, t.height + 2 * PAD
            if w > W:
                pages = None; break
            if x + w > W:
                x = 0; y += row; row = 0
            if y + h > PAGE:
                pages.append((W, y)); pg += 1; x = y = row = 0
            place[k] = (pg, x + PAD, y + PAD); x += w; row = max(row, h)
        if pages is None:
            continue
        pages.append((W, y + row))
        pages = [(w, -(-h // 8) * 8) for w, h in pages]
        cost = (len(pages), sum(w * h for w, h in pages))
        if best is None or cost < best[0]:
            best = (cost, pages, place)
    return best[1], best[2]


def build_atlases(char, R, rg, out):
    st = R["static"]
    imgs = {}
    for n in rg["names"]:
        p = st[n]["img"]["path"]
        r = texel_ratio(R, n)
        imgs[p] = max(imgs.get(p, 0), r)
    srcs = {p: Image.open(p).convert("RGBA") for p in imgs}
    res = {}
    for D in DENSITIES[char]:
        dd = dname(D)
        tiles = {}
        for p, r in imgs.items():
            k = min(1.0, r * D)
            src = srcs[p]
            tiles[p] = resize(src, (max(2, round(src.width * k)), max(2, round(src.height * k)))) if k < 1 else src
        pages, place = pack_atlas(tiles)
        os.makedirs(os.path.join(out, dd), exist_ok=True)
        files = []
        for pi, (W, H) in enumerate(pages):
            atlas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            for p, (pg, x, y) in place.items():
                if pg != pi:
                    continue
                t = tiles[p]
                big = Image.new("RGBA", (t.width + 2 * PAD, t.height + 2 * PAD), (0, 0, 0, 0)); big.paste(t, (PAD, PAD))
                atlas.paste(bleed(big, 2 * PAD + 2), (x - PAD, y - PAD))
            atlas = bleed(atlas, 12)                 # the clear gaps too: mip levels average over them
            raw = webp(atlas, ATLAS_Q)
            fn = f"atlas{pi}.webp"
            open(os.path.join(out, dd, fn), "wb").write(raw)
            files.append({"file": fn, "w": W, "h": H, "bytes": len(raw)})
        uvs, page_of = [], []
        for n in rg["names"]:
            s = st[n]; p = s["img"]["path"]; t = tiles[p]; pg, ox, oy = place[p]; W, H = pages[pg]
            uv = np.array(s["uv"]).reshape(-1, 2)
            u = (ox + uv[:, 0] * t.width) / W; v = (oy + (1 - uv[:, 1]) * t.height) / H
            uvs.append(np.round(np.stack([u, v], 1).ravel() * 65535).astype(np.uint16)); page_of.append(pg)
        blob = np.concatenate(uvs).tobytes()
        open(os.path.join(out, dd, "uv.bin"), "wb").write(blob)
        res[dd] = {"pages": files, "uv": {"file": "uv.bin", "bytes": len(blob)}, "page_of": page_of,
                   "texel": {os.path.basename(p): round(min(1.0, r * D), 4) for p, r in imgs.items()}}
        print(f"  {char} {dd}: atlas {len(pages)} page(s) {[(f['w'], f['h']) for f in files]} {sum(f['bytes'] for f in files) / 1e3:.0f} KB", flush=True)
    return res


def write_rig_bin(char, R, rg, out):
    st = R["static"]
    blob = bytearray()

    def put(arr):
        nonlocal blob
        while len(blob) % 4:
            blob += b"\0"
        off = len(blob); blob += arr.tobytes(); return off
    parts = []
    for n in rg["names"]:
        s = st[n]
        P = np.array(s["rest" if s["skinned"] else "local"]).reshape(-1, 3)
        pos = put(np.stack([P[:, 0], P[:, 2]], 1).astype(np.float32).ravel())
        tris = np.array(s["tris"], np.uint32 if s["nv"] > 65535 else np.uint16)
        e = {"name": n.split("_", 1)[1], "skin": s["skinned"], "nv": s["nv"], "nt": len(tris) // 3, "unlit": s["unlit"],
             "pos": pos, "idx": put(tris), "idx32": bool(s["nv"] > 65535)}
        if s["skinned"]:
            wi = np.zeros((s["nv"], 4), np.uint8); ww = np.zeros((s["nv"], 4), np.uint16)
            for vi, ws in enumerate(s["w"]):
                ws = ws[:4] if ws else [["__arm", 1.0]]
                tot = sum(w for _, w in ws)
                q = [int(round(w / tot * 65535)) for _, w in ws]
                q[0] += 65535 - sum(q)                       # they sum to one exactly
                for k, (bn, _) in enumerate(ws):
                    wi[vi, k] = rg["bones"].index(bn); ww[vi, k] = q[k]
            e["wi"] = put(wi.ravel()); e["ww"] = put(ww.ravel())
        else:
            e["item"] = rg["rigid"].index(n)
        parts.append(e)
    poses = put(rg["poses"].astype(np.int16).ravel())
    vis = put(rg["vis"].astype(np.uint8).ravel())
    maps = {c: put(np.array(m, np.uint16)) for c, m in rg["maps"].items()}
    open(os.path.join(out, "rig.bin"), "wb").write(bytes(blob))
    return {"file": "rig.bin", "bytes": len(blob), "qm": rg["qm"], "qt": rg["qt"], "parts": parts,
            "rigid": len(rg["rigid"]), "bones": [b for b in rg["bones"]], "items": len(rg["rigid"]) + len(rg["bones"]),
            "poses": {"off": poses, "n": int(len(rg["poses"]))}, "vis": vis, "maps": maps}


# ------------------------------------------------------------------------------------------------ frame tracks
def pack_track(args):
    """a clip's effect frames -> per density one file of cropped WebP frames, each frame's slot and master px box"""
    char, clip, kind, files, n, (W, H), outdir = args
    m = SNAP[char]
    slots, boxes, imgs = [-1] * n, [], []
    for f in files:
        i = int(os.path.basename(f)[:4]) - 1
        im = Image.open(f).convert("RGBA")
        if kind == "fxmask":                       # white, the mask in its alpha
            a = im.getchannel("A")
            im = Image.merge("RGBA", (a.point(lambda v: 255),) * 3 + (a,))
        b = alpha_box(np.asarray(im.getchannel("A")))
        if b is None or i >= n:
            continue
        slots[i] = len(boxes); boxes.append(list(snap_box(b, m, W, H))); imgs.append(im)
    if not boxes:
        return char, clip, kind, None
    # every frame of a track the same size (the largest), each where its own effect is: the game uploads each frame
    # into the same texture then, instead of making a new one for every frame (the ember's crop changes every frame)
    bw = max(b[2] - b[0] for b in boxes); bh = max(b[3] - b[1] for b in boxes)
    for k, b in enumerate(boxes):
        x0 = max(0, min(b[0], W - bw)); y0 = max(0, min(b[1], H - bh))
        boxes[k] = [x0, y0, x0 + bw, y0 + bh]; imgs[k] = imgs[k].crop(boxes[k])
    out = {"frames": slots, "boxes": boxes, "files": {}}
    for D in DENSITIES[char]:
        dd = dname(D)
        blob, offs = bytearray(), [0]
        for b, im in zip(boxes, imgs):
            sz = (round((b[2] - b[0]) * D), round((b[3] - b[1]) * D))
            t = bleed(resize(im, sz), 6)
            blob += webp(t, FX_Q if kind == "fx" else 70, 100 if kind == "fx" else 80); offs.append(len(blob))
        fn = f"{kind}_{clip}.bin"
        os.makedirs(os.path.join(outdir, char, dd), exist_ok=True)
        open(os.path.join(outdir, char, dd, fn), "wb").write(bytes(blob))
        out["files"][dd] = {"file": fn, "bytes": len(blob), "offsets": offs, "density": D}
    return char, clip, kind, out


def pack_smoke(char):
    files = sorted(glob.glob(os.path.join(SRC, char, "renders", "smoke", "*.png")))
    seen = None
    for f in files:
        a = np.asarray(Image.open(f).getchannel("A")) > 2
        seen = a if seen is None else seen | a
    ys, xs = np.nonzero(seen); Hh, Ww = seen.shape
    box = (max(0, xs.min() - 4), max(0, ys.min() - 4), min(Ww, xs.max() + 5), min(Hh, ys.max() + 5))
    res = {}
    for D in DENSITIES[char]:
        dd = dname(D); ds = D * SMOKE_SCALE
        size = (max(2, round((box[2] - box[0]) * ds)), max(2, round((box[3] - box[1]) * ds)))
        blob, offs = bytearray(), [0]
        for f in files:
            im = resize(Image.open(f).convert("RGBA").crop(box), size)
            blob += webp(im, SMOKE_Q, 100); offs.append(len(blob))
        os.makedirs(os.path.join(OUTDIR, char, dd), exist_ok=True)
        open(os.path.join(OUTDIR, char, dd, "smoke.bin"), "wb").write(bytes(blob))
        res[dd] = {"file": "smoke.bin", "w": size[0], "h": size[1], "bytes": len(blob), "offsets": offs, "density": ds}
    return [int(v) for v in box], res


def cues_of(char, R, rg, clip, meta):
    """meta.json's cues where Blender measured them (the boy: every clip; the skull: the idle); else the frames where
    every rigid part is within 1.5 px of the idle's first pose and every skinned vertex within 5 px (the skull's rule)"""
    c = meta["clips"][clip].get("cues")
    if c:
        return c
    qf = rg["poses"].astype(np.float64); qf[:, :, :4] /= rg["qm"]; qf[:, :, 4:] /= rg["qt"]
    rest = qf[rg["maps"]["idle"][0]]
    out = []
    for i, p in enumerate(rg["maps"][clip]):
        dv = np.abs(qf[p] - rest)
        # a map's change at a point ~3 units out (a part's corner) + its translation
        dev = dv[:, 4:].max(1) + 3 * dv[:, :4].max(1)
        nr = len(rg["rigid"])
        if dev[:nr].max() <= 1.5 and dev[nr:].max() <= 5:
            out.append(i)
    return out


OUTDIR = OUT
META = {}
if __name__ == "__main__":
    args = sys.argv[1:]
    if "--out" in args:
        k = args.index("--out"); OUTDIR = os.path.abspath(args[k + 1]); del args[k:k + 2]
    chars = sorted(DENSITIES) if args[0] == "all" else args[0].split(",")
    for char in chars:
        META[char] = json.load(open(os.path.join(SRC, char, "renders", "meta.json")))
    for char in chars:
        out = os.path.join(OUTDIR, char)
        os.makedirs(out, exist_ok=True)
        meta = META[char]
        R = json.load(open(os.path.join(SRC, char, "renders", "rig.json")))
        rg = build_rig(char, R, meta)
        err = rig_error(char, R, rg)
        rig = write_rig_bin(char, R, rg, out)
        rig["atlas"] = build_atlases(char, R, rg, out)
        nfr = sum(len(m) for m in rg["maps"].values())
        print(f"{char}: {len(rg['names'])} parts ({len(rg['rigid'])} rigid), {len(rg['bones'])} bones, {nfr} frames -> "
              f"{rig['poses']['n']} poses, rig.bin {rig['bytes'] / 1e3:.0f} KB, quantisation <= {err:.3f} master px", flush=True)
        # the effect tracks
        jobs = []
        for clip, info in meta["clips"].items():
            for kind in ("fx", "fxmask"):
                fs = sorted(glob.glob(os.path.join(SRC, char, "renders", f"{clip}_{kind}", "*.png")))
                if fs:
                    jobs.append((char, clip, kind, fs, info["frames"], tuple(meta["size"]), OUTDIR))
        tracks = {}
        with ProcessPoolExecutor(max_workers=min(8, max(1, len(jobs)))) as ex:
            for ch, clip, kind, t in ex.map(pack_track, jobs):
                if t:
                    tracks.setdefault(clip, {})[kind] = t
                    print(f"  {char} {clip} {kind}: {len(t['boxes'])} frames | " + " | ".join(f"{dd} {v['bytes'] / 1e3:.0f} KB" for dd, v in t["files"].items()), flush=True)
        # which effect tracks go into the unlit mask and how: the boy's Grease Pencil is black in his shoe pass (it
        # covers the shoes), the skull's ash is white in his (the light leaves it alone: fxmask)
        rig["fx"] = {"mask": "erase" if char == "boy" else None, "tracks": tracks}
        clips = {}
        for clip, info in meta["clips"].items():
            clips[clip] = {"frames": info["frames"], "loop": bool(info.get("loop")), "cues": cues_of(char, R, rg, clip, meta)}
            assert len(rg["maps"][clip]) == info["frames"], (clip, len(rg["maps"][clip]), info["frames"])
        dens = DENSITIES[char]
        man = {"fps": meta["fps"], "size": meta["size"], "rest_height": meta["rest_height_px"], "ground_y": meta["ground_y"],
               "densities": [dname(d) for d in dens], "density_of": {dname(d): d for d in dens}, "clips": clips,
               "track": meta.get("track", {}), "rig": rig}
        if "smoke" in meta:
            box, files = pack_smoke(char)
            man["smoke"] = {"frames": meta["smoke"]["frames"], "origin": meta["smoke"]["origin"], "box": box, "files": files}
            print(f"  {char} smoke: " + " | ".join(f"{dd} {v['bytes'] / 1e6:.2f} MB" for dd, v in files.items()), flush=True)
        json.dump(man, open(os.path.join(out, "manifest.json"), "w"), separators=(",", ":"))
        for D in dens:
            dd = dname(D)
            tot = rig["bytes"] + os.path.getsize(os.path.join(out, "manifest.json")) + sum(f["bytes"] for f in rig["atlas"][dd]["pages"]) + rig["atlas"][dd]["uv"]["bytes"]
            tot += sum(t["files"][dd]["bytes"] for c in tracks.values() for t in c.values())
            if "smoke" in man:
                tot += man["smoke"]["files"][dd]["bytes"]
            print(f"-> {char} {dd}: {tot / 1e6:.2f} MB to download", flush=True)
