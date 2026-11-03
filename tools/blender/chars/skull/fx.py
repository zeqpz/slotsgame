# SMOKE SKULL - the effects, drawn INSIDE Blender in Grease Pencil, frame by frame (run after anim.py, same Blender).
#   smoke   the cigar's smoke (its own view layer "smoke", laid over the figure at 80 %): a thin thread off the ember
#           that wavers, swells into billows and leans over his beanie (away from the board), drawn in the characters'
#           cartoon paint like the game's old smoke (frontend/smoke.js): an ink line, a cool grey shade, a pale fill set up
#           and to the left, a soft haze round the spent puffs. Worked out here as a stream of particles off the ember
#           wherever the ember goes (the rig's own pose, frame by frame), each one living ~10 s, in a draft and a slow
#           swirl. The idle's smoke loops: everything that drives it repeats every 4 s and the ember's path loops, so
#           after a few laps the smoke at frame 121 is the smoke at frame 1. The one-shots carry on from the idle's
#           frame-1 smoke and, over their last 14 frames, morph back into it (each bit of smoke into the bit of the
#           same age), so they hand back to the idle without a jump. The exit's smoke thins away to nothing.
#   ember   the glow on the cigar's tip (view layer "fx", drawn soft in stacked discs): it breathes and flickers in every
#           clip, flaring on a drag
#   ash     ash_break: the ash grows on the tip, breaks off at the flick, falls in three chunks that crumble on the ground
import bpy, math, os, random
import numpy as np

SID = "SKULL"
sc = bpy.context.scene
FPS = 30
PACE = .35                       # the smoke's own time runs at 35 % (smoke.js: a lazy curl)
T_LOOP = 120                     # the idle's frames: everything that drives the smoke repeats every 4 s
OM = 2 * math.pi / (T_LOOP / FPS * PACE)      # one cycle per loop, in the smoke's time (rad / smoke-second)


def srgb(h):
    c = [((h >> s) & 255) / 255 for s in (16, 8, 0)]
    return tuple(((v + .055) / 1.055) ** 2.4 if v > .04045 else v / 12.92 for v in c) + (1.0,)


LOOK = {"haze": srgb(0xb7bcc8), "line": srgb(0x18191e), "shade": srgb(0x9fa4b1), "fill": srgb(0xebedf2)}


def to_px(p):                    # world (x, z) -> master px (x, y down)
    return np.array([p[0] * 100 + 512, 768 - p[1] * 100])


def ember_px(clip, f):
    """the ember (its bone's head) in master px at a clip's frame f"""
    R = RESULT[clip]
    D = R["mats"][f]["cigar"]
    return to_px(app(D, HEAD["ember"]))


def cigar_axis(clip, f):
    D = RESULT[clip]["mats"][f]["cigar"]
    a, b = to_px(app(D, HEAD["cigar"])), to_px(app(D, HEAD["ember"]))
    d = b - a
    return b, d / np.linalg.norm(d)


# ------------------------------------------------------------------------------------------------ the smoke, simulated
rng = random.Random(7)
WAVES = [dict(l=170, v=120, w=0.0, d=.3), dict(l=110, v=90, w=OM, d=2.1), dict(l=260, v=70, w=0.0, d=4.0),
         dict(l=75, v=55, w=-OM, d=1.2), dict(l=140, v=80, w=0.0, d=5.3)]
for Wv in WAVES:
    Wv.update(ph=rng.uniform(0, 2 * math.pi), kx=math.cos(Wv["d"]), ky=math.sin(Wv["d"]))


def life_at(tb):                  # smoke-seconds, by when it left the cigar (slow along the stream)
    return 3.6 + .3 * np.sin(OM * tb) + .15 * np.sin(2 * OM * tb + 2)


def sway_at(tb):
    return np.sin(3 * OM * tb + .4) + .45 * np.sin(7 * OM * tb + 2.7) + .2 * np.sin(13 * OM * tb)


def puff_at(tb):
    return 1 + .34 * np.sin(2 * OM * tb) + .22 * np.sin(5 * OM * tb + 1.1) + .16 * np.sin(9 * OM * tb + 2.3)


def draft_at(t):
    return 95 + 18 * np.sin(OM * t + .7) + 8 * np.sin(2 * OM * t + 2.2)


def ss(v):
    v = np.clip(v, 0, 1)
    return v * v * (3 - 2 * v)


SUB = 2                           # particles per frame (and sim steps per frame)


def simulate(clip):
    """the smoke of a clip: {frame: arrays (x, y, r, rh, u, age_index)} for f in 0..n-1. Particles born before the
    clip's frame 0 come off the idle's (looping) ember path, so frame 0 is the idle's frame 0."""
    R = RESULT[clip]
    n = R["n"]
    life_max = 4.2 / PACE * FPS                      # frames
    first = -int(life_max) - (3 * T_LOOP if clip == "idle" else T_LOOP)
    first = -int(math.ceil((-first) / T_LOOP)) * T_LOOP     # a whole number of loops back: births line up with the idle
    if clip == "enter":
        first = -1                                   # he comes up from below the frame: no smoke yet (none born before 0)
    idle_n = RESULT["idle"]["n"]
    drag = RESULT["idle"]["drag"]

    def ember_at(fr):                                # fractional frame -> px, and how hard he is drawing on it
        fi = math.floor(fr)
        a = fr - fi

        def at(k):
            if clip != "idle" and k >= 0:
                k = min(k, n - 1)
                return ember_px(clip, k), float(R["drag"][k])
            k = k % idle_n
            return ember_px("idle", k), float(drag[k])
        (p0, d0), (p1, d1) = at(fi), at(fi + 1)
        return p0 * (1 - a) + p1 * a, d0 * (1 - a) + d1 * a

    steps = (n - first) * SUB
    births = np.arange(steps) / SUB + first           # birth frame of particle i (one per step)
    N = len(births)
    X = np.zeros(N); Y = np.zeros(N); VX = np.zeros(N); VY = np.zeros(N); AGE = np.zeros(N)
    alive = np.zeros(N, bool)
    tb = births / FPS * PACE                          # smoke-time of birth
    LIFE = life_at(tb)
    SW = sway_at(tb)
    PF = np.zeros(N)
    out = {}
    dt = PACE / FPS / SUB                             # smoke-seconds per step
    for st in range(steps):
        fr = first + st / SUB                         # the frame at this step
        t = fr / FPS * PACE
        # this step's new particle
        i = st
        p, dg = ember_at(fr)
        pprev, _ = ember_at(fr - 1.0 / SUB)
        ev = (p - pprev) / dt
        X[i], Y[i] = p[0], p[1] - 4
        VX[i], VY[i] = ev[0] * .12, ev[1] * .12 - 40
        PF[i] = max(.55, puff_at(tb[i])) * (1 + .7 * dg)
        alive[i] = not (clip == "enter" and fr < 0)
        # every living particle moves
        idx = np.nonzero(alive)[0]
        AGE[idx] += dt
        u = AGE[idx] / LIFE[idx]
        dead = u >= 1
        alive[idx[dead]] = False
        idx, u = idx[~dead], u[~dead]
        cx = np.zeros(len(idx)); cy = np.zeros(len(idx))
        for Wv in WAVES:
            kk = 2 * math.pi / Wv["l"]
            c_ = np.cos(kk * (Wv["kx"] * X[idx] + Wv["ky"] * Y[idx]) + Wv["w"] * t + Wv["ph"]) * Wv["v"] * .7
            cx += Wv["ky"] * c_
            cy -= Wv["kx"] * c_
        tbw = ss((u - .36) / .38) * 1.15
        rise = (85 + 270 * ss(AGE[idx] / 1.2)) * (1 - .3 * u)
        wave = 40 * SW[idx] * ss(u / .25) * (1 - .6 * ss((u - .5) / .4))
        tx = draft_at(t) * (.12 + .88 * ss((u - .3) / .3)) + wave + cx * tbw
        ty = -rise + cy * tbw
        k = min(1.0, dt * 2.4)
        VX[idx] += (tx - VX[idx]) * k
        VY[idx] += (ty - VY[idx]) * k
        X[idx] += VX[idx] * dt
        Y[idx] += VY[idx] * dt
        if st % SUB == SUB - 1 and fr + 1.0 / SUB >= 0:
            f = int(round(fr + 1.0 / SUB))
            if 0 <= f < n:
                ii = np.nonzero(alive)[0]
                uu = AGE[ii] / LIFE[ii]
                grow = 2.8 + PF[ii] * 30 * ss((uu - .3) / .42)
                r = grow * (1 - ss((uu - .66) / .26))
                rh = (grow + 34 * ss((uu - .45) / .55)) * 1.35
                agei = np.round((fr + 1.0 / SUB - births[ii]) * SUB).astype(int)
                order = np.argsort(births[ii])
                ii, uu, r, rh, agei = ii[order], uu[order], r[order], rh[order], agei[order]
                out[f] = dict(x=X[ii].copy(), y=Y[ii].copy(), r=r, rh=rh, u=uu, age=agei)
    return out


def morph(a, b, w):
    """smoke a turned into smoke b by weight w (0..1): each bit of smoke into the bit of b of the same age; bits only
    one of them has fade in / out with the weight"""
    ia = {int(k): j for j, k in enumerate(a["age"])}
    ib = {int(k): j for j, k in enumerate(b["age"])}
    ages = sorted(set(ia) | set(ib))
    o = {k: [] for k in ("x", "y", "r", "rh", "u", "age", "op")}
    for g in ages:
        if g in ia and g in ib:
            ja, jb = ia[g], ib[g]
            for k in ("x", "y", "r", "rh", "u"):
                o[k].append(a[k][ja] * (1 - w) + b[k][jb] * w)
            o["op"].append(1.0)
        elif g in ia:
            ja = ia[g]
            for k in ("x", "y", "r", "rh", "u"):
                o[k].append(a[k][ja])
            o["op"].append(1 - w)
        else:
            jb = ib[g]
            for k in ("x", "y", "r", "rh", "u"):
                o[k].append(b[k][jb])
            o["op"].append(w)
        o["age"].append(g)
    o = {k: np.array(v) for k, v in o.items()}
    if w >= .999:                                     # the last frame: exactly b
        keep = np.array([g in ib for g in ages])
        o = {k: v[keep] for k, v in o.items()}
    return o


# ------------------------------------------------------------------------------------------------ grease pencil helpers
def coll(name):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in sc.collection.children:
        sc.collection.children.link(c)
    return c


def gp_object(c, name, depth):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    gpd = bpy.data.grease_pencils.new(name)
    ob = bpy.data.objects.new(name, gpd)
    c.objects.link(ob)
    ob.location.y = depth
    ob.use_grease_pencil_lights = False
    return ob


def gp_mat(ob, name, color, fill=None):
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name)
        bpy.data.materials.create_gpencil_data(mat)
    g = mat.grease_pencil
    g.color = color
    if fill is not None:
        g.fill_color = fill
        g.show_fill = True
    ob.data.materials.append(mat)
    return len(ob.data.materials) - 1


def layer(ob, name):
    L = ob.data.layers.new(name)
    L.use_lights = False
    return L


def put(L, f, strokes):
    """one frame of a layer: strokes = [(points [(x, z)], radii, opacities, material, fill)] (world units)"""
    fr = L.frames.new(f)
    dr = fr.drawing
    strokes = [s for s in strokes if len(s[0])]
    if not strokes:
        return
    dr.add_strokes([len(s[0]) for s in strokes])
    pos = np.zeros((sum(len(s[0]) for s in strokes), 3), np.float32)
    rad = np.zeros(len(pos), np.float32)
    opa = np.zeros(len(pos), np.float32)
    k = 0
    for pts, radii, ops, m, fill in strokes:
        m_ = len(pts)
        pts = np.asarray(pts, np.float32)
        pos[k:k + m_, 0] = pts[:, 0]
        pos[k:k + m_, 2] = pts[:, 1]
        rad[k:k + m_] = radii
        opa[k:k + m_] = ops
        k += m_
    dr.attributes["position"].data.foreach_set("vector", pos.ravel())
    for nm, arr in (("radius", rad), ("opacity", opa)):
        a = dr.attributes.get(nm) or dr.attributes.new(nm, "FLOAT", "POINT")
        a.data.foreach_set("value", arr)
    for i, (pts, radii, ops, m, fill) in enumerate(strokes):
        s = dr.strokes[i]
        s.material_index = m
        if fill:
            s.cyclic = True
            s.fill_id = i + 1
            s.fill_opacity = float(np.max(ops))
            s.hide_stroke = True
    dr.tag_positions_changed()


def W(x, y):                      # master px -> world (x, z)
    return ((np.asarray(x) - 512) / 100.0, (768 - np.asarray(y)) / 100.0)


# ------------------------------------------------------------------------------------------------ view layers + compositor
ART = coll(SID + "_ART")
SMOKE = coll(SID + "_SMOKE")
FXC = coll(SID + "_FX")
for o in list(sc.collection.objects):
    ART.objects.link(o)
    sc.collection.objects.unlink(o)
for c_ in (SMOKE, FXC):
    if sc.camera.name not in c_.objects:
        c_.objects.link(sc.camera)
vls = {"art": sc.view_layers[0]}
vls["art"].name = "art"
for nm in ("smoke", "fx"):
    vls[nm] = sc.view_layers.get(nm) or sc.view_layers.new(nm)
own = {"art": ART, "smoke": SMOKE, "fx": FXC}
for nm, vl in vls.items():
    for c_ in (ART, SMOKE, FXC):
        vl.layer_collection.children[c_.name].exclude = c_ is not own[nm]


def compositor(mode):
    """beauty: the art, the smoke over it at 80 % (one layer: puffs do not show through each other), the ember's
    glow over all. unlit: white where the unlit parts show (the art layer rendered in its mask mode)."""
    name = f"{SID}_comp_{mode}"
    ng = bpy.data.node_groups.get(name) or bpy.data.node_groups.new(name, "CompositorNodeTree")
    ng.use_fake_user = True                           # kept in skull.blend even while not in use (run.py render-only)
    ng.nodes.clear()
    if not any(getattr(s, "in_out", "") == "OUTPUT" for s in ng.interface.items_tree):
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    N, L = ng.nodes, ng.links
    out = N.new("NodeGroupOutput")
    art = N.new("CompositorNodeRLayers"); art.scene = sc; art.layer = "art"
    if mode == "unlit":
        sep = N.new("CompositorNodeSeparateColor")
        L.new(art.outputs["Image"], sep.inputs[0])
        sa = N.new("CompositorNodeSetAlpha")
        sa.inputs["Type"].default_value = "Replace Alpha"
        sa.inputs["Image"].default_value = (1, 1, 1, 1)
        L.new(sep.outputs[0], sa.inputs["Alpha"])
        L.new(sa.outputs["Image"], out.inputs[0])
        return ng
    sm_ = N.new("CompositorNodeRLayers"); sm_.scene = sc; sm_.layer = "smoke"
    fade = N.new("CompositorNodeSetAlpha")
    fade.inputs["Type"].default_value = "Apply Mask"
    L.new(sm_.outputs["Image"], fade.inputs["Image"])
    fade.inputs["Alpha"].default_value = .8
    o1 = N.new("CompositorNodeAlphaOver")
    L.new(art.outputs["Image"], o1.inputs["Background"]); L.new(fade.outputs["Image"], o1.inputs["Foreground"])
    fx = N.new("CompositorNodeRLayers"); fx.scene = sc; fx.layer = "fx"
    o2 = N.new("CompositorNodeAlphaOver")
    L.new(o1.outputs["Image"], o2.inputs["Background"]); L.new(fx.outputs["Image"], o2.inputs["Foreground"])
    L.new(o2.outputs["Image"], out.inputs[0])
    return ng


COMP = {m: compositor(m) for m in ("beauty", "unlit")}
sc.compositing_node_group = COMP["beauty"]
sc.render.use_compositing = True

# ------------------------------------------------------------------------------------------------ draw the smoke
smoke_ob = gp_object(SMOKE, SID + "_smoke", -5.0)
M_ = {k: gp_mat(smoke_ob, f"{SID}_smoke_{k}", LOOK[k]) for k in ("haze", "line", "shade", "fill")}
LY = {k: layer(smoke_ob, k) for k in ("haze", "line", "shade", "fill")}
SMOKE_STATE = {}
idle_sim = simulate("idle")
SMOKE_STATE["idle"] = idle_sim
MORPH = 14
for clip in RESULT:
    sim = idle_sim if clip == "idle" else simulate(clip)
    n = RESULT[clip]["n"]
    if clip not in ("idle", "exit"):
        for f in range(n - MORPH, n):
            w = (f - (n - MORPH) + 1) / MORPH
            w = w * w * (3 - 2 * w)
            sim[f] = morph(sim[f], idle_sim[0], w)
    SMOKE_STATE[clip] = sim
for clip, sim in SMOKE_STATE.items():
    f0, n = RESULT[clip]["f0"], RESULT[clip]["n"]
    for f in range(n):
        s = sim[f]
        x, y, r, rh, u = s["x"], s["y"], s["r"], s["rh"], s["u"]
        op = s.get("op", np.ones(len(x)))
        if clip == "exit":                            # the smoke thins away as he goes
            op = op * (1 - ss((f - 2) / (n - 3)))
        ink = ss(u / .12) * (1 - ss((u - .5) / .35))
        o = (3.6 + .08 * r) * ink
        hz = ss((u - .25) / .3) * (1 - ss((u - .72) / .28))
        MIN = 1.2
        strokes = {k: [] for k in LY}
        # the ribbon: runs of neighbours that hold together (both drawn, not torn apart)
        body = r > MIN
        link = np.zeros(len(x), bool)
        if len(x) > 1:
            dd = np.hypot(np.diff(x), np.diff(y))
            rm = np.minimum(r[:-1], r[1:])
            link[:-1] = body[:-1] & body[1:] & (dd <= rm * 9)
        runs, cur = [], []
        for i in range(len(x)):
            if body[i]:
                cur.append(i)
                if not link[i]:
                    runs.append(cur); cur = []
            elif cur:
                runs.append(cur); cur = []
        if cur:
            runs.append(cur)
        for run in runs:
            run = np.array(run)
            xs_, ys_ = x[run].astype(float), y[run].astype(float)
            if len(run) >= 5:                         # the thread drawn smooth along its length (no zigzag)
                k_ = np.array([1, 2, 3, 2, 1], float) / 9
                xs_ = np.concatenate([xs_[:2], np.convolve(xs_, k_, "valid"), xs_[-2:]])
                ys_ = np.concatenate([ys_[:2], np.convolve(ys_, k_, "valid"), ys_[-2:]])
            if (len(run) == 1 and r[run[0]] < 7) or (len(run) < 4 and r[run].max() < 3.5):
                continue                              # a speck alone reads as a bubble
            px_, pz_ = W(xs_, ys_)
            pts = list(zip(px_, pz_))
            oo = op[run]
            if len(pts) == 1:
                pts = pts * 2
                run = np.array([run[0], run[0]])
                oo = np.array([oo[0], oo[0]])
            strokes["line"].append((pts, (r[run] + o[run]) / 100, oo, M_["line"], False))
            strokes["shade"].append((pts, r[run] / 100, oo, M_["shade"], False))
            fx_, fz_ = W(xs_[:len(run)] - .2 * r[run], ys_[:len(run)] - .22 * r[run])
            strokes["fill"].append((list(zip(fx_, fz_)), .8 * r[run] / 100, oo, M_["fill"], False))
        hh = np.nonzero(hz > .02)[0]
        if len(hh) > 1:
            px_, pz_ = W(x[hh], y[hh])
            strokes["haze"].append((list(zip(px_, pz_)), rh[hh] / 100, .16 * hz[hh] * op[hh], M_["haze"], False))
        for k, L in LY.items():
            put(L, f0 + f, strokes[k])

# ------------------------------------------------------------------------------------------------ the ember's glow
glow_ob = gp_object(FXC, SID + "_ember", -6.0)
E_IDLE0 = float(RESULT["idle"]["ember"][0]) * (1 + .08 * math.sin(1) + .05 * math.sin(2))
G_ = {k: gp_mat(glow_ob, f"{SID}_ember_{k}", c, fill=c) for k, c in
      (("hot", (1.0, .72, .25, 1)), ("warm", (1.0, .32, .04, 1)), ("red", (.75, .06, .01, 1)))}
GL = layer(glow_ob, "glow")
for clip, R in RESULT.items():
    f0, n = R["f0"], R["n"]
    for f in range(n):
        p, ax = cigar_axis(clip, f)
        tt = f / FPS
        if clip == "idle":
            fl = .12 * math.sin(2 * math.pi * 7 * tt / 4) + .08 * math.sin(2 * math.pi * 17 * tt / 4 + 1) + .05 * math.sin(2 * math.pi * 31 * tt / 4 + 2)
        else:
            fl = .12 * math.sin(2 * math.pi * 1.8 * tt) + .08 * math.sin(2 * math.pi * 4.3 * tt + 1) + .05 * math.sin(2 * math.pi * 7.7 * tt + 2)
        e = float(R["ember"][f]) * (1 + fl)
        if clip != "idle":                             # a one-shot starts and ends on the idle's frame-1 glow
            w = min(ss(f / 6), ss((n - 1 - f) / 10))
            e = e * w + E_IDLE0 * (1 - w)
        if clip == "exit":
            e *= 1 - ss((f - 2) / (R["n"] - 3))
        c = p + ax * -4                                # the glow sits on the burning end
        cx, cz = W(c[0], c[1])
        s_ = []
        for rr, oo, m in ((34, .05, "red"), (27, .07, "red"), (21, .1, "warm"), (15, .16, "warm"), (10, .3, "warm"),
                          (6.5, .5, "hot"), (3.5, .75, "hot")):
            s_.append(([(cx, cz), (cx + 1e-4, cz)], [rr * (.75 + .35 * e) / 100] * 2, [min(1, oo * e)] * 2, G_[m], False))
        put(GL, f0 + f, s_)

# ------------------------------------------------------------------------------------------------ the ash (ash_break)
ash_ob = gp_object(ART, SID + "_ash", -3.55)
A_ = {"ash": gp_mat(ash_ob, f"{SID}_ash_body", srgb(0x8d8a86), fill=srgb(0x8d8a86)),
      "light": gp_mat(ash_ob, f"{SID}_ash_light", srgb(0xc9c5bf), fill=srgb(0xc9c5bf)),
      "ink": gp_mat(ash_ob, f"{SID}_ash_ink", srgb(0x16161a), fill=srgb(0x16161a)),
      "dust": gp_mat(ash_ob, f"{SID}_ash_dust", srgb(0xa9a6a1), fill=srgb(0xa9a6a1))}
AL = layer(ash_ob, "ash")
R = RESULT["ash_break"]
F_BREAK = ASH_BREAK
GROUND = 1462.0


def ash_shape(p, ax, L, wid, rot=0.0, seed=0):
    """a crumbly ash cylinder from p along ax, length L, width wid (master px) -> outline points (px)"""
    nx_ = np.array([-ax[1], ax[0]])
    rr = random.Random(seed)
    pts = []
    for i in range(9):
        s = i / 8
        pts.append(p + ax * L * s + nx_ * wid / 2 * (1 + .08 * rr.uniform(-1, 1)))
    for i in range(7):                                  # the rounded crumbly end
        a = math.pi / 2 - math.pi * i / 6
        pts.append(p + ax * (L + math.cos(a) * wid * .28 * (1 + .15 * rr.uniform(-1, 1))) + nx_ * math.sin(a) * wid / 2)
    for i in range(9):
        s = 1 - i / 8
        pts.append(p + ax * L * s - nx_ * wid / 2 * (1 + .08 * rr.uniform(-1, 1)))
    return pts


def draw_ash(f_abs, pieces, dusts=()):
    s_ = []
    for c, rr in dusts:                                 # crumbled ash: soft round puffs, under the chunks
        ring = [(c[0] + math.cos(t) * rr, c[1] + math.sin(t) * rr * .8) for t in np.linspace(0, 2 * math.pi, 20, endpoint=False)]
        xs, zs = W(np.array([q[0] for q in ring]), np.array([q[1] for q in ring]))
        s_.append((list(zip(xs, zs)), [.004] * len(xs), [1.0] * len(xs), A_["dust"], True))
    for pts, light_pts in pieces:
        xs, zs = W(np.array([q[0] for q in pts]), np.array([q[1] for q in pts]))
        outline = list(zip(xs, zs))
        s_.append((outline, [.022] * len(outline), [1.0] * len(outline), A_["ink"], False))
        s_.append((outline, [.004] * len(outline), [1.0] * len(outline), A_["ash"], True))
        if light_pts is not None:
            xs, zs = W(np.array([q[0] for q in light_pts]), np.array([q[1] for q in light_pts]))
            s_.append((list(zip(xs, zs)), [.012] * len(xs), [1.0] * len(xs), A_["light"], False))
    put(AL, f_abs, s_)


chunks = []
for f in range(R["n"]):
    p, ax = cigar_axis("ash_break", f)
    if f < F_BREAK:
        g_ = ss((f - 1) / (F_BREAK - 5))               # nothing on frame 0 (the rest pose), grown by the flick
        L = 22 * g_
        back = 6 * g_
        base = p - ax * back
        if L + back > 1.0:
            pts = ash_shape(base, ax, L + back, 30 * (.7 + .3 * g_), seed=3)
            nx_ = np.array([-ax[1], ax[0]])
            light = [base + ax * (L + back) * s + nx_ * 8 for s in np.linspace(.15, .8, 5)]
            draw_ash(R["f0"] + f, [(pts, light)])
        else:
            put(AL, R["f0"] + f, [])
        if f == F_BREAK - 1:
            # the break: three chunks fly off with the flick, then fall
            p1, ax1 = cigar_axis("ash_break", f + 1)
            tipv = (p1 - p) * FPS
            Lfull = L + back
            for j, (s0, s1) in enumerate(((0, .35), (.35, .7), (.7, 1.0))):
                c0 = base + ax * Lfull * (s0 + s1) / 2
                chunks.append(dict(c=c0.copy(), v=tipv * .6 + np.array([(j - 1) * 40.0, -60 - 30 * j]), ax=ax.copy(),
                                   L=Lfull * (s1 - s0), spin=(1 - 2 * (j % 2)) * (6 + 4 * j), rot=0.0, landed=None, seed=10 + j))
    else:
        pieces = []
        dusts = []
        for ch in chunks:
            if ch["landed"] is None:
                ch["v"] = ch["v"] + np.array([0.0, 2600.0]) / FPS
                ch["c"] = ch["c"] + ch["v"] / FPS
                ch["rot"] += ch["spin"]
                if ch["c"][1] >= GROUND - 8:
                    ch["c"][1] = GROUND - 8
                    ch["landed"] = f
            a = math.radians(ch["rot"])
            ca, sa = math.cos(a), math.sin(a)
            axr = np.array([ch["ax"][0] * ca - ch["ax"][1] * sa, ch["ax"][0] * sa + ch["ax"][1] * ca])
            k = 0 if ch["landed"] is None else f - ch["landed"]
            sc_ = max(0.0, 1 - k / 7)
            if sc_ > .05:
                pts = ash_shape(ch["c"] - axr * ch["L"] / 2 * sc_, axr, ch["L"] * sc_, 26 * (.6 + .4 * sc_), seed=ch["seed"])
                pieces.append((pts, None))
            if ch["landed"] is not None and k < 12:   # it crumbles into a little puff of ash dust
                for q in range(3):
                    u = k / 11
                    rr_ = (6 + 10 * math.sin(math.pi * min(1, u * 1.1)) ** .6) * (1 - u * .5)
                    dusts.append((ch["c"] + np.array([(q - 1) * 14 * (1 + u), -8 - 14 * u - q * 3]), rr_))
        draw_ash(R["f0"] + f, pieces, dusts)
    if f == R["n"] - 1 or (f >= F_BREAK and all(ch["landed"] is not None and f - ch["landed"] > 12 for ch in chunks)):
        put(AL, R["f0"] + f + 1, [])
        break
ASH_MATS = list(A_.values())
print(SID, "fx drawn: smoke", {k: len(v) for k, v in SMOKE_STATE.items()}, flush=True)
