"""rigkit - cut slot icons into parts and author them as Spine 4.2 skeletons.

There is no Spine editor on the build machine, so every skeleton is written here from a small
recipe (one per icon, recipes/<ID>.py). A recipe names the parts (masks over the icon art),
where each part pivots, how parts hang off each other, and the clips (idle / land / win) as
keyframes on bones and slots. rigkit turns that into:

  - the part images, cut from the icon with antialiased masks; the hole a moving part leaves in
    the part under it is filled from the surrounding colours (push-pull inpainting), so a part
    can move off its spot without opening a gap
  - one shared atlas page (frontend/assets/icons/icons.png + .atlas, Spine's own format)
  - a Spine 4.2 skeleton per icon (bones, slots, region attachments, rotate/translate/scale/
    alpha timelines with bezier curves) - loadable by any Spine 4.2 runtime and importable into
    the Spine editor
  - a preview sheet per icon (Pillow, evaluating the same keyframes) for a quick look

Coordinates in recipes are icon pixels (x right, y down, origin top-left of the source PNG).
Skeleton units: the icon's longer side is 100 units; the skeleton origin is the icon's centre
and y points up, as Spine expects.
"""
import json, math, os, re
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SRC_DIR = os.path.join(ROOT, "art", "icons-src")      # the full-size icon art (the game ships flat/ WebP copies and the rigs)
OUT_DIR = os.path.join(ROOT, "frontend", "assets", "icons")
OUT_PX_PER_UNIT = 3.2      # atlas pixels per skeleton unit: a 100-unit icon is 320 px - sharp at 2x DPR with a win pop
PAD = 2                    # transparent pixels round every atlas region

# ------------------------------------------------------------------ masks
class Canvas:
    """Mask evaluation for one icon. Every mask is a float array 0..1 the size of the source."""
    def __init__(self, src):
        self.src = src                                  # PIL RGBA
        self.W, self.H = src.size
        self.rgba = np.asarray(src).astype(np.float32) / 255.0
        self.alpha = self.rgba[..., 3]

    def poly(self, pts, ss=4):
        big = Image.new("L", (self.W * ss, self.H * ss), 0)
        ImageDraw.Draw(big).polygon([(x * ss, y * ss) for x, y in pts], fill=255)
        return np.asarray(big.resize((self.W, self.H), Image.BOX)).astype(np.float32) / 255.0

    def ellipse(self, cx, cy, rx, ry, deg=0, ss=4):
        n = 72; a = math.radians(deg)
        pts = [(cx + rx * math.cos(t) * math.cos(a) - ry * math.sin(t) * math.sin(a),
                cy + rx * math.cos(t) * math.sin(a) + ry * math.sin(t) * math.cos(a))
               for t in (2 * math.pi * i / n for i in range(n))]
        return self.poly(pts, ss)

    def eval(self, m):
        """m is a mask expression: ("poly", pts) ("disc", cx, cy, r) ("ellipse", cx, cy, rx, ry, deg)
        ("rect", x0, y0, x1, y1) ("color", "#rrggbb", tol) ("ink",) ("opaque",) ("or", *m) ("and", *m)
        ("minus", a, b) ("grow", m, px) ("shrink", m, px) ("blur", m, px) ("cc", m, x, y)"""
        if isinstance(m, np.ndarray):
            return m
        k = m[0]
        if k == "poly":
            return self.poly(m[1])
        if k == "disc":
            return self.ellipse(m[1], m[2], m[3], m[3])
        if k == "ellipse":
            return self.ellipse(*m[1:6]) if len(m) > 5 else self.ellipse(m[1], m[2], m[3], m[4])
        if k == "rect":
            return self.poly([(m[1], m[2]), (m[3], m[2]), (m[3], m[4]), (m[1], m[4])])
        if k == "color":           # pixels near a colour (RGB distance, 0..441), opaque only
            ref = np.array([int(m[1][i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255.0
            tol = (m[2] if len(m) > 2 else 60) / 255.0
            d = np.sqrt(((self.rgba[..., :3] - ref) ** 2).sum(-1))
            return np.clip((tol - d) / (tol * .25) + 1, 0, 1) * (self.alpha > .5)
        if k == "ink":             # the black linework
            lum = self.rgba[..., :3].max(-1)
            return ((lum < .28) & (self.alpha > .5)).astype(np.float32)
        if k == "opaque":
            return self.alpha.copy()
        if k == "or":
            out = np.zeros((self.H, self.W), np.float32)
            for s in m[1:]:
                out = np.maximum(out, self.eval(s))
            return out
        if k == "and":
            out = np.ones((self.H, self.W), np.float32)
            for s in m[1:]:
                out = np.minimum(out, self.eval(s))
            return out
        if k == "minus":
            return np.clip(self.eval(m[1]) - self.eval(m[2]), 0, 1)
        if k in ("grow", "shrink"):
            img = Image.fromarray((self.eval(m[1]) * 255).astype(np.uint8))
            px = max(1, int(round(m[2])))
            f = ImageFilter.MaxFilter if k == "grow" else ImageFilter.MinFilter
            for _ in range(px // 2 or 1):
                img = img.filter(f(3 if px == 1 else 5 if px >= 2 else 3))
            return np.asarray(img).astype(np.float32) / 255.0
        if k == "blur":
            img = Image.fromarray((self.eval(m[1]) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(m[2]))
            return np.asarray(img).astype(np.float32) / 255.0
        if k == "along":           # ("along", mask, [(x,y)...], t0, t1): the part of a mask whose
            #                        nearest point on a polyline lies between t0 and t1 of its length
            #                        - slices a painted stroke in drawing order, hard-edged, so the
            #                        slices tile the stroke exactly
            base = self.eval(m[1]); path = np.array(m[2], np.float32); t0, t1 = m[3], m[4]
            key = (id(m[1]), tuple(map(tuple, m[2])))
            if not hasattr(self, "_along"): self._along = {}
            if key not in self._along:
                ys, xs = np.nonzero(base > .01)
                P = np.stack([xs, ys], 1).astype(np.float32)
                seg = path[1:] - path[:-1]; L = np.sqrt((seg ** 2).sum(1)); cum = np.concatenate([[0], np.cumsum(L)])
                best_d = np.full(len(P), np.inf, np.float32); best_t = np.zeros(len(P), np.float32)
                for i in range(len(seg)):
                    d0 = P - path[i]; u = np.clip((d0 @ seg[i]) / max(L[i] ** 2, 1e-6), 0, 1)
                    q = path[i] + u[:, None] * seg[i]; dist = ((P - q) ** 2).sum(1)
                    better = dist < best_d; best_d[better] = dist[better]; best_t[better] = (cum[i] + u[better] * L[i]) / cum[-1]
                tmap = np.full(base.shape, -1.0, np.float32); tmap[ys, xs] = best_t
                self._along[key] = tmap
            tmap = self._along[key]
            return base * ((tmap >= t0) & (tmap < t1 if t1 < 1 else tmap <= 1)).astype(np.float32)
        if k == "cc":              # the connected piece of a mask that contains a point
            base = self.eval(m[1]) > .5
            x0, y0 = int(m[2]), int(m[3])
            seen = np.zeros_like(base); stack = [(y0, x0)]
            if not base[y0, x0]:
                return np.zeros_like(self.alpha)
            while stack:
                y, x = stack.pop()
                if y < 0 or x < 0 or y >= self.H or x >= self.W or seen[y, x] or not base[y, x]:
                    continue
                seen[y, x] = True
                stack.extend(((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)))
            return seen.astype(np.float32)
        raise ValueError(f"unknown mask op {k}")


def inpaint(rgba, hole):
    """Fill the hole (bool HxW) of a premultiplied-RGBA float image from its surroundings by
    push-pull: average the known pixels down a pyramid (each level remembers what fraction of
    its area was known), then pull the averages back up, bilinearly, into the unknown parts.
    Smooth, edge-continuous and fast; alpha is filled the same way, so a hole on the icon's
    silhouette fades out where the silhouette did."""
    known = (~hole).astype(np.float32)
    levels = [(rgba * known[..., None], known)]          # (premultiplied-by-known colour sum, known fraction)
    while min(levels[-1][1].shape) > 2:
        c, f = levels[-1]
        h2, w2 = (c.shape[0] + 1) // 2, (c.shape[1] + 1) // 2
        cp = np.zeros((h2 * 2, w2 * 2, 4), np.float32); cp[:c.shape[0], :c.shape[1]] = c
        fp = np.zeros((h2 * 2, w2 * 2), np.float32); fp[:f.shape[0], :f.shape[1]] = f
        levels.append((cp.reshape(h2, 2, w2, 2, 4).mean((1, 3)), fp.reshape(h2, 2, w2, 2).mean((1, 3))))

    def upsample(a, shape):
        return np.stack([np.asarray(Image.fromarray(a[..., i].astype(np.float32), "F").resize((shape[1], shape[0]), Image.BILINEAR))
                         for i in range(a.shape[-1])], -1)
    c, f = levels[-1]
    est = c / np.maximum(f[..., None], 1e-6)
    for c, f in reversed(levels[:-1]):
        mine = c / np.maximum(f[..., None], 1e-6)          # the average of what is known here
        t = np.clip(f * 2.0, 0, 1)[..., None]               # mostly known -> trust it; mostly hole -> the coarser guess
        est = mine * t + upsample(est, c.shape[:2]) * (1 - t)
    out = rgba.copy()
    out[hole] = est[hole]
    return out


# ------------------------------------------------------------------ procedural sprites
def sprite_sparkle(size=96, color=(255, 255, 255)):
    """A four-point star with a soft glow - the win twinkle."""
    ss = 4; S = size * ss
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = S / 2; r = S * .48; w = S * .085
    d.polygon([(c, c - r), (c + w, c - w), (c + r, c), (c + w, c + w), (c, c + r), (c - w, c + w), (c - r, c), (c - w, c - w)], fill=color + (255,))
    glow = im.filter(ImageFilter.GaussianBlur(S * .05))
    out = Image.alpha_composite(glow, im).resize((size, size), Image.LANCZOS)
    return out


def sprite_puff(size=96, color=(235, 235, 235), outline=(0, 0, 0)):
    """A cartoon smoke/dust puff in the icons' sticker style (outlined blobs)."""
    ss = 4; S = size * ss
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    blobs = [(.5, .55, .26), (.32, .6, .18), (.68, .6, .18), (.42, .38, .17), (.6, .4, .16)]
    ow = S * .035
    for x, y, r in blobs:
        d.ellipse([(x - r) * S - ow, (y - r) * S - ow, (x + r) * S + ow, (y + r) * S + ow], fill=outline + (255,))
    for x, y, r in blobs:
        d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=color + (255,))
    return im.resize((size, size), Image.LANCZOS)


def sprite_streak(w=120, h=18, color=(255, 255, 255)):
    """A speed / shine streak: a tapered capsule."""
    ss = 4; S = (w * ss, h * ss)
    im = Image.new("RGBA", S, (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon([(0, S[1] / 2), (S[0] * .15, 0), (S[0], S[1] * .35), (S[0], S[1] * .65), (S[0] * .15, S[1])], fill=color + (230,))
    return im.filter(ImageFilter.GaussianBlur(ss * .6)).resize((w, h), Image.LANCZOS)


SPRITES = {"sparkle": sprite_sparkle, "puff": sprite_puff, "streak": sprite_streak}


# ------------------------------------------------------------------ easing -> spine curves
EASE = {   # normalised cubic beziers (x1, y1, x2, y2), CSS-style
    "linear": None, "in": (.42, 0, 1, 1), "out": (0, 0, .58, 1), "inout": (.42, 0, .58, 1),
    "back": (.34, 1.56, .64, 1), "snap": (.2, .9, .3, 1), "drop": (.55, 0, .9, .4), "soft": (.37, 0, .63, 1),
}


def curve_for(t0, v0, t1, v1, ease):
    """Spine 4.2 stores a segment's bezier on its first key, in absolute (time, value)."""
    if ease == "step":
        return "stepped"
    b = EASE.get(ease, ease) if isinstance(ease, str) else ease
    if b is None:
        return None
    x1, y1, x2, y2 = b
    return [round(t0 + x1 * (t1 - t0), 4), round(v0 + y1 * (v1 - v0), 4),
            round(t0 + x2 * (t1 - t0), 4), round(v0 + y2 * (v1 - v0), 4)]


def bez(p, t):   # cubic bezier y for a normalised x via bisection (preview only)
    if p is None:
        return t
    x1, y1, x2, y2 = p
    lo, hi = 0.0, 1.0
    for _ in range(30):
        m = (lo + hi) / 2
        x = 3 * (1 - m) ** 2 * m * x1 + 3 * (1 - m) * m * m * x2 + m ** 3
        lo, hi = (m, hi) if x < t else (lo, m)
    m = (lo + hi) / 2
    return 3 * (1 - m) ** 2 * m * y1 + 3 * (1 - m) * m * m * y2 + m ** 3


def sample(keys, t, default):
    """Value of a key list [(t, v, ease)...] at time t (ease on a key shapes the run INTO it)."""
    if not keys:
        return default
    if t <= keys[0][0]:
        return keys[0][1]
    for (ta, va, *_), (tb, vb, *eb) in zip(keys, keys[1:]):
        if ta <= t <= tb:
            e = eb[0] if eb else "inout"
            if e == "step":
                return va
            p = EASE.get(e, e) if isinstance(e, str) else e
            u = 0 if tb == ta else (t - ta) / (tb - ta)
            return va + (vb - va) * bez(p, u)
    return keys[-1][1]


# ------------------------------------------------------------------ the rig
CHANNELS = {"x": ("translatex", 0.0), "y": ("translatey", 0.0), "r": ("rotate", 0.0),
            "sx": ("scalex", 1.0), "sy": ("scaley", 1.0), "hx": ("shearx", 0.0), "hy": ("sheary", 0.0)}


class Rig:
    def __init__(self, recipe):
        self.r = recipe
        self.id = recipe["id"]
        self.src = Image.open(os.path.join(SRC_DIR, recipe.get("src", self.id + ".png"))).convert("RGBA")
        self.cv = Canvas(self.src)
        self.ppu = max(self.cv.W, self.cv.H) / 100.0          # source px per skeleton unit
        self.parts = {}                                        # name -> dict(img=PIL, box=(x0,y0,x1,y1) src px)
        self.slots = []                                        # draw order: dicts(name, bone, region, ...)

    # icon px -> skeleton units (origin at the centre, y up)
    def u(self, x, y):
        return ((x - self.cv.W / 2) / self.ppu, (self.cv.H / 2 - y) / self.ppu)

    def cut(self):
        """Claim pixels for every part (in recipe order), fill the holes they leave in the parts
        listed as lying under them, and trim each part to its pixels."""
        cv = self.cv
        src = cv.rgba.copy(); src[..., :3] *= src[..., 3:4]       # premultiplied
        claimed = np.zeros((cv.H, cv.W), np.float32)
        layers = {}
        for p in self.r["parts"]:
            if p.get("sprite") or p.get("copy"):
                continue
            if p.get("mask", "rest") == "rest":
                m = np.clip(cv.alpha - claimed, 0, 1) / np.maximum(cv.alpha, 1e-6) * (cv.alpha > 0)
            else:
                m = np.clip(cv.eval(p["mask"]), 0, 1)
                if p.get("exclusive", True):
                    m = np.clip(m - claimed, 0, 1)
                if p.get("feather"):
                    m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(p["feather"])), np.float32) / 255.0
            claimed = np.clip(claimed + m * (cv.alpha > 0), 0, 1)
            layers[p["name"]] = src * m[..., None]
        # holes: a part lifted off another leaves a hole there - fill it from around
        for p in self.r["parts"]:
            under = p.get("fill")                               # name of the part beneath to repair
            if not under or p["name"] not in layers:
                continue
            for u_name in ([under] if isinstance(under, str) else under):
                base = layers[u_name]
                lifted = layers[p["name"]][..., 3] > .02
                hole = np.asarray(Image.fromarray((lifted * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)), np.uint8) > 127
                hole &= base[..., 3] < .98
                region = hole | (base[..., 3] > .02)
                filled = inpaint(base, hole)
                # keep the fill inside the icon's silhouette so nothing grows past the outline
                filled[..., :4] *= np.where(region, 1, 0)[..., None]
                layers[u_name] = filled
        for name, arr in layers.items():
            a = np.clip(arr[..., 3:4], 0, 1)
            rgb = np.where(a > 1e-4, arr[..., :3] / np.maximum(a, 1e-4), 0)
            img = Image.fromarray((np.concatenate([np.clip(rgb, 0, 1), a], -1) * 255).round().astype(np.uint8), "RGBA")
            bb = img.getbbox()
            if not bb:
                raise ValueError(f"{self.id}: part {name} is empty")
            self.parts[name] = {"img": img.crop(bb), "box": bb}
        for p in self.r["parts"]:
            if p.get("sprite"):
                kind = p["sprite"]
                spr = SPRITES[kind](**p.get("args", {}))
                sz = p.get("size", 18)                          # in skeleton units
                spr_px = spr.resize((max(4, int(sz * self.ppu)), max(4, int(sz * self.ppu * spr.height / spr.width))), Image.LANCZOS)
                cx, cy = p["at"]
                self.parts[p["name"]] = {"img": spr_px, "box": (int(cx - spr_px.width / 2), int(cy - spr_px.height / 2),
                                                                 int(cx - spr_px.width / 2) + spr_px.width, int(cy - spr_px.height / 2) + spr_px.height), "sprite": True}

    # ------------------------------------------------------------ spine json
    def skeleton(self, region_names):
        r = self.r
        bones = [{"name": "root"}]
        bone_of = {}
        pivots = {}
        for p in r["parts"]:
            name = p["name"]
            piv = p.get("pivot")
            if piv is None:
                src = self.parts[p["copy"]] if p.get("copy") else self.parts[name]
                b = src["box"]; piv = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) if not p.get("copy") else p.get("at", ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2))
            pivots[name] = piv
        order = []                                             # parents before children
        def add(n):
            if n in order: return
            par = next((p.get("parent", "root") for p in r["parts"] if p["name"] == n), "root")
            if par != "root": add(par)
            order.append(n)
        for p in r["parts"]:
            add(p["name"])
        for n in order:
            p = next(q for q in r["parts"] if q["name"] == n)
            par = p.get("parent", "root")
            ux, uy = self.u(*pivots[n])
            if par != "root":
                px, py = self.u(*pivots[par]); ux, uy = ux - px, uy - py
            bones.append({"name": n, "parent": par, "x": round(ux, 3), "y": round(uy, 3)})
            bone_of[n] = n
        slots, att = [], {}
        draw = r.get("draw") or [p["name"] for p in r["parts"]]
        for n in draw:
            p = next(q for q in r["parts"] if q["name"] == n)
            reg = p.get("copy") or n
            part = self.parts[reg]
            b = part["box"]
            if p.get("copy"):
                cx, cy = p.get("at", pivots[n])
                w = part["img"].width / self.ppu * p.get("scale", 1); h = part["img"].height / self.ppu * p.get("scale", 1)
                ox, oy = 0, 0
            else:
                cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
                w, h = (b[2] - b[0]) / self.ppu, (b[3] - b[1]) / self.ppu
                bx, by = self.u(cx, cy); px, py = self.u(*pivots[n])
                ox, oy = bx - px, by - py
                # region offset is in the bone's own space: undo the parent chain's offset (no rest rotation)
            slot = {"name": n, "bone": bone_of[n], "attachment": region_names[reg]}
            if p.get("hidden"):
                slot["color"] = "ffffff00"      # attached but invisible until a clip fades it in
            if p.get("alpha") is not None:
                slot["color"] = "ffffff" + format(int(p["alpha"] * 255), "02x")
            if p.get("blend"):
                slot["blend"] = p["blend"]
            slots.append(slot)
            att[n] = {region_names[reg]: {"x": round(ox, 3), "y": round(oy, 3), "width": round(w, 3), "height": round(h, 3)}}
        anims = {}
        for clip, spec in r["anims"].items():
            a = {"bones": {}, "slots": {}}
            for bone, chans in spec.get("bones", {}).items():
                tl = {}
                for ch, keys in chans.items():
                    kind, base = CHANNELS[ch]
                    out = []
                    for i, k in enumerate(keys):
                        t, v = k[0], k[1]
                        key = {"time": round(t, 4)} if t else {}
                        key["value"] = round(v, 4)
                        if i + 1 < len(keys):
                            nt, nv, *ne = keys[i + 1]
                            c = curve_for(t, v, nt, nv, ne[0] if ne else "inout")
                            if c is not None:
                                key["curve"] = c
                        out.append(key)
                    tl[kind] = out
                a["bones"][bone] = tl
            for slot, keys in spec.get("alpha", {}).items():
                out = []
                for i, k in enumerate(keys):
                    t, v = k[0], k[1]
                    key = {"time": round(t, 4)} if t else {}
                    key["value"] = round(v, 4)
                    if i + 1 < len(keys):
                        nt, nv, *ne = keys[i + 1]
                        c = curve_for(t, v, nt, nv, ne[0] if ne else "linear")
                        if c is not None:
                            key["curve"] = c
                    out.append(key)
                a["slots"][slot] = {"alpha": out}
            if not a["slots"]:
                del a["slots"]
            # Spine runtimes size a clip by its last key; pin the authored length with an event-free hold
            dur = spec.get("dur")
            if dur:
                a.setdefault("bones", {}).setdefault("root", {})["rotate"] = [{"value": 0}, {"time": round(dur, 4), "value": 0}]
            anims[clip] = a
        W, H = self.cv.W / self.ppu, self.cv.H / self.ppu
        return {
            "skeleton": {"hash": self.id, "spine": "4.2.43", "x": round(-W / 2, 3), "y": round(-H / 2, 3), "width": round(W, 3), "height": round(H, 3), "images": "./", "audio": ""},
            "bones": bones, "slots": slots,
            "skins": [{"name": "default", "attachments": att}],
            "animations": anims,
        }

    # ------------------------------------------------------------ preview (same keyframes, Pillow)
    def pose(self, clip, t, scale=.32):
        """Rasterise the rig at time t of a clip (preview only - the game evaluates the skeleton
        with the Spine runtime). Bones compose parent-first: translate, rotate, scale about the pivot."""
        r = self.r; spec = r["anims"].get(clip, {}); chans = spec.get("bones", {}); alph = spec.get("alpha", {})
        S = int(max(self.cv.W, self.cv.H) * scale * 1.3)
        out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        off = (S - self.cv.W * scale) / 2, (S - self.cv.H * scale) / 2
        pivots = {}
        for p in r["parts"]:
            b = self.parts[p.get("copy") or p["name"]]["box"]
            pivots[p["name"]] = p.get("pivot") or (p.get("at") if p.get("copy") else ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2))
        def local(n):
            c = chans.get(n, {})
            g = lambda k, d: sample(c.get(k, []), t, d)
            return g("x", 0) * self.ppu, -g("y", 0) * self.ppu, -g("r", 0), g("sx", 1), g("sy", 1)
        def world(n):   # affine (a, b, c, d, e, f) in icon px, CSS orientation
            p = next(q for q in r["parts"] if q["name"] == n)
            par = p.get("parent", "root")
            tx, ty, rot, sx, sy = local(n)
            px, py = pivots[n]
            co, si = math.cos(math.radians(rot)), math.sin(math.radians(rot))
            # T(pivot + t) R S T(-pivot)
            a, b, c, d = co * sx, si * sx, -si * sy, co * sy
            e = px + tx - (a * px + c * py); f = py + ty - (b * px + d * py)
            M = (a, b, c, d, e, f)
            if par != "root":
                A = world(par)
                M = (A[0] * M[0] + A[2] * M[1], A[1] * M[0] + A[3] * M[1], A[0] * M[2] + A[2] * M[3], A[1] * M[2] + A[3] * M[3],
                     A[0] * M[4] + A[2] * M[5] + A[4], A[1] * M[4] + A[3] * M[5] + A[5])
            return M
        for n in (r.get("draw") or [p["name"] for p in r["parts"]]):
            p = next(q for q in r["parts"] if q["name"] == n)
            part = self.parts[p.get("copy") or n]
            al = sample(alph.get(n, []), t, 0.0 if p.get("hidden") else p.get("alpha", 1.0))
            if al <= .01:
                continue
            img = part["img"]
            if p.get("copy"):
                sc = p.get("scale", 1); cx, cy = pivots[n]
                img = img.resize((max(1, int(img.width * sc)), max(1, int(img.height * sc))), Image.LANCZOS)
                x0, y0 = cx - img.width / 2, cy - img.height / 2
            else:
                x0, y0 = part["box"][0], part["box"][1]
            a, b, c, d, e, f = world(n)
            # map: icon px -> preview px: scale & offset; image px -> icon px: translate (x0, y0)
            A = [a * scale, b * scale, c * scale, d * scale, (a * x0 + c * y0 + e) * scale + off[0], (b * x0 + d * y0 + f) * scale + off[1]]
            det = A[0] * A[3] - A[1] * A[2]
            if abs(det) < 1e-9:
                continue
            inv = (A[3] / det, -A[1] / det, -A[2] / det, A[0] / det)
            ia = (inv[0], inv[2], -(inv[0] * A[4] + inv[2] * A[5]), inv[1], inv[3], -(inv[1] * A[4] + inv[3] * A[5]))
            layer = img.transform((S, S), Image.AFFINE, ia, resample=Image.BICUBIC)
            if al < .99:
                arr = np.asarray(layer).copy(); arr[..., 3] = (arr[..., 3] * al).astype(np.uint8); layer = Image.fromarray(arr)
            out.alpha_composite(layer)
        return out


# ------------------------------------------------------------------ atlas packing
def pack(images, page=2048):
    """Shelf-pack named images (tallest first) onto pages; returns {name: (page, x, y, w, h)} and pages."""
    order = sorted(images.items(), key=lambda kv: -kv[1].height)
    pages, placed = [], {}
    x = y = shelf = 0; cur = None
    for name, im in order:
        w, h = im.width + PAD * 2, im.height + PAD * 2
        if cur is None or x + w > page:
            x = 0; y += shelf; shelf = 0
        if cur is None or y + h > page:
            cur = Image.new("RGBA", (page, page), (0, 0, 0, 0)); pages.append(cur); x = y = shelf = 0
        cur.paste(im, (x + PAD, y + PAD))
        placed[name] = (len(pages) - 1, x + PAD, y + PAD, im.width, im.height)
        x += w; shelf = max(shelf, h)
    return placed, pages


def trim_pages(pages):
    """Crop each page to its used height (rounded up to a multiple of 4)."""
    out = []
    for p in pages:
        bb = p.getbbox() or (0, 0, 4, 4)
        h = min(p.height, ((bb[3] + PAD + 3) // 4) * 4)
        out.append(p.crop((0, 0, p.width, h)))
    return out
