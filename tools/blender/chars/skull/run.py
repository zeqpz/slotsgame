"""SMOKE SKULL, made in Blender start to finish - in a background Blender, never the one the owner has open:
  python tools/blender/chars/skull/parts.py            (once, or after changing the cut: the parts the rig is built from)
  "C:/Users/CooperHinkel/Blender/blender-5.2.3-windows-x64/blender.exe" -b --factory-startup \\
      --python tools/blender/chars/skull/run.py -- [steps] [clips]
steps (comma separated, default build,anim,fx,save,render,meta):
  build   the cut-out scene and rig (build.py)
  anim    the clips keyed on the rig (anim.py)
  fx      the smoke, the ember's glow, the ash (fx.py, Grease Pencil)
  save    art/blender/chars/skull/skull.blend
  render  art/blender/chars/skull/renders/<clip>/####.png (beauty: the figure + the ember glow, no smoke), <clip>_unlit/
          (the unlit mask) and smoke/####.png (the standalone smoke loop; clips arg "smoke" renders only it)
  meta    art/blender/chars/skull/renders/meta.json (frames, loops, the idle's cues, the shoes' spans per frame)
clips: comma separated (default all) - render only these
Then: python tools/blender/chars/skull/qa.py (sheets, zooms, holes, seams, rest checks)."""
import json, math, os, sys, time
import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
OUT = os.path.join(REPO, "art", "blender", "chars", "skull")
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
steps = (argv[0] if argv else "build,anim,fx,save,render,meta").split(",")
only = argv[1].split(",") if len(argv) > 1 else None
G = {"__name__": "__main__"}


def run(name):
    p = os.path.join(HERE, name)
    G["__file__"] = p
    t0 = time.time()
    exec(compile(open(p, encoding="utf-8").read(), p, "exec"), G)
    print(f"[{name}] {time.time() - t0:.1f} s", flush=True)


t_all = time.time()
if "build" in steps or "anim" in steps or "fx" in steps:      # each needs what the one before left in G
    run("build.py")
    run("anim.py")
    if "fx" in steps or "render" in steps:
        run("fx.py")
else:
    bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "skull.blend"))
sc = bpy.context.scene
if "save" in steps:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "skull.blend"))
    print("saved", bpy.data.filepath, flush=True)

CLIPS = G.get("CLIPS") or {k: (v[0], v[1] - v[0] + 1, k == "idle") for k, v in bpy.data.objects["SKULL_rig"]["clips"].items()}


def set_mode(mode):
    """beauty, the unlit mask or the smoke loop: the parts' materials, the ash's colours, which view layers render,
    the compositor"""
    unlit = mode == "unlit"
    for m in bpy.data.materials:
        if m.node_tree and m.name.startswith("SKULL_") and "mode" in m.node_tree.nodes:
            m.node_tree.nodes["mode"].outputs[0].default_value = 1.0 if unlit else 0.0
    for m in bpy.data.materials:
        if m.name.startswith("SKULL_ash_") and m.grease_pencil:
            if "orig" not in m.keys():
                m["orig"] = list(m.grease_pencil.color)
                m["orig_fill"] = list(m.grease_pencil.fill_color)
            c = (1, 1, 1, 1) if unlit else tuple(m["orig"])
            m.grease_pencil.color = c
            m.grease_pencil.fill_color = (1, 1, 1, 1) if unlit else tuple(m["orig_fill"])
    # the clips: the art (+ the ember's glow in beauty); the smoke loop: its own layer alone
    use = {"beauty": ("art", "fx"), "unlit": ("art",), "smoke": ("smoke",)}[mode]
    for vl in sc.view_layers:
        vl.use = vl.name in use
    sc.compositing_node_group = bpy.data.node_groups["SKULL_comp_" + mode]
    sc.render.use_compositing = True


def render_clip(name, unlit):
    f0, n = CLIPS[name][0], CLIPS[name][1]
    d = os.path.join(OUT, "renders", name + ("_unlit" if unlit else ""))
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        if f.endswith(".png"):
            os.remove(os.path.join(d, f))
    for i in range(n):
        sc.frame_set(f0 + i)
        sc.render.filepath = os.path.join(d, f"{i + 1:04d}.png")
        bpy.ops.render.render(write_still=True)


if "render" in steps:
    sc.render.resolution_percentage = 100
    for mode in ("beauty", "unlit"):
        set_mode(mode)
        for name in CLIPS:
            if only and name not in only:
                continue
            t0 = time.time()
            render_clip(name, mode == "unlit")
            print(f"rendered {name}{' unlit' if mode == 'unlit' else ''}: {CLIPS[name][1]} frames, {time.time() - t0:.0f} s", flush=True)
    if not only or "smoke" in only:
        # the smoke loop, on its own clock (fx.py: SMOKE_F0 .. + SMOKE_N)
        set_mode("smoke")
        f0 = int(bpy.data.objects["SKULL_rig"].get("smoke", [1001, 210])[0])
        n = int(bpy.data.objects["SKULL_rig"].get("smoke", [1001, 210])[1])
        d = os.path.join(OUT, "renders", "smoke")
        os.makedirs(d, exist_ok=True)
        for f in os.listdir(d):
            if f.endswith(".png"):
                os.remove(os.path.join(d, f))
        t0 = time.time()
        for i in range(n):
            sc.frame_set(f0 + i)
            sc.render.filepath = os.path.join(d, f"{i + 1:04d}.png")
            bpy.ops.render.render(write_still=True)
        print(f"rendered smoke loop: {n} frames, {time.time() - t0:.0f} s", flush=True)
    set_mode("beauty")

if "meta" in steps:
    R = G["RESULT"]
    cam = G["CAMINFO"]
    k, cpx, cpy = cam["k"], cam["cam_px"], cam["cam_py"]
    W_, H_ = sc.render.resolution_x, sc.render.resolution_y

    def to_out(p):                       # world (x, z) -> frame px (x, y down)
        mx, my = p[0] * 100 + 512, 768 - p[1] * 100
        return W_ / 2 + (mx - cpx) * k, H_ / 2 + (my - cpy) * k
    spec = G["spec"]
    hull = {p["name"]: np.array(p["hull"], float) for p in spec["parts"] if "hull" in p}
    track = {}
    for name, r in R.items():
        rows = []
        for f in range(r["n"]):
            row = []
            for s in "lr":
                D = r["mats"][f][f"shoe_{s}"]
                pts = [to_out(G["app"](D, np.array([(x - 512) / 100, (768 - y) / 100]))) for x, y in hull[f"shoe_{s}"]]
                xs, ys = [q[0] for q in pts], [q[1] for q in pts]
                row.append([round(min(xs), 1), round(max(xs), 1), round(max(ys), 1)])
            ember = to_out(G["app"](r["mats"][f]["cigar"], G["HEAD"]["ember"]))
            rows.append({"shoes": row, "ember": [round(ember[0], 1), round(ember[1], 1)]})
        track[name] = rows
    idle = R["idle"]
    heads = G["HEAD"]
    chain_tips = {p["name"]: p["chain"][-1] for p in spec["parts"] if p.get("chain")}

    rigid = [b for b in heads if "." not in b]

    def sample(m, which):
        if which == "body":
            return np.array([to_out(G["app"](m[b], heads[b])) for b in rigid])
        pts = []
        for nm, (x, y) in chain_tips.items():
            last = max((b for b in heads if b.startswith(nm + ".")), default=None)
            if last:
                pts.append(to_out(G["app"](m[last], np.array([(x - 512) / 100, (768 - y) / 100]))))
        return np.array(pts)
    devs = {}
    for which in ("body", "hang"):
        rest = sample(idle["mats"][0], which)
        devs[which] = np.array([np.abs(sample(m, which) - rest).max() for m in idle["mats"]])
    dev = devs["body"]
    # cues: frames within a hair of rest - the body (every rigid bone) within 1.5 px, what hangs off it (beanie tip,
    # strings, laces) within 5 px - one every ~0.4-0.75 s where the pose allows (the groove passes rest on each beat,
    # the chill sits at it)
    ok = (dev <= 1.5) & (devs["hang"] <= 5)
    cues = [0]
    while True:
        last = cues[-1]
        win = [f for f in range(last + 12, min(idle["n"] - 6, last + 23)) if ok[f]]
        if not win:
            later = [f for f in range(last + 23, idle["n"] - 6) if ok[f]]
            if not later:
                break
            win = later[:1]
        cues.append(int(min(win, key=lambda f: dev[f] + .3 * devs["hang"][f])))
    # the hips' height per clip (world z of the pelvis bone vs its rest height): the body never bobs
    pel = {}
    for name, r in R.items():
        zs = [float(G["app"](m["pelvis"], heads["pelvis"])[1]) for m in r["mats"]]
        pel[name] = [round(min(zs) - float(heads["pelvis"][1]), 4), round(max(zs) - float(heads["pelvis"][1]), 4)]
        print(f"pelvis z vs rest ({name}): {pel[name][0] * 100 * k:+.2f} .. {pel[name][1] * 100 * k:+.2f} frame px", flush=True)
    sm = G["SMOKE_EMIT"]
    org = to_out(((sm[0] - 512) / 100, (768 - sm[1]) / 100))
    meta = {"fps": 30, "size": [W_, H_], "rest_height_px": cam["rest_height_px"], "ground_y": cam["ground_y"],
            "smoke": {"frames": G["SMOKE_N"], "loop": True, "origin": [round(org[0], 1), round(org[1], 1)]},
            "clips": {}, "track": track,
            "notes": {"pelvis_z_vs_rest_units": pel, "cue_rule": "body within 1.5 px of rest, hanging parts within 5 px",
                      "idle_body_dev_px": [round(float(v), 2) for v in dev],
                      "idle_hang_dev_px": [round(float(v), 2) for v in devs["hang"]]}}
    for name, r in R.items():
        e = {"frames": r["n"], "loop": bool(r["loop"])}
        if name == "idle":
            e["cues"] = cues
        meta["clips"][name] = e
    os.makedirs(os.path.join(OUT, "renders"), exist_ok=True)
    json.dump(meta, open(os.path.join(OUT, "renders", "meta.json"), "w"), indent=1)
    print("meta: cues", cues, "| at cues body/hang px:", [(b_, round(float(dev[b_]), 2), round(float(devs["hang"][b_]), 2)) for b_ in cues], "| smoke", meta["smoke"], flush=True)
print(f"skull done: {','.join(steps)} | {time.time() - t_all:.0f} s", flush=True)
