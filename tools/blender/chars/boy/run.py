"""SMUKIEZ (the boy), made in a background Blender from scratch - the cutout rig, every clip, the renders:
  "C:/Users/CooperHinkel/Blender/blender-5.2.3-windows-x64/blender.exe" -b --factory-startup \\
      --python tools/blender/chars/boy/run.py -- [steps]
steps, comma separated (default parts,build,anim,render,meta,qa):
  parts   the cutout parts: tools/blender/chars/boy/prep_parts.py (+ fixes.py) in the project venv python, from the
          imported v2 cut in art/blender/chars/boy/src -> art/blender/chars/boy/parts
  build   the cutout scene from art/blender/chars/boy/parts (build_boy.py; the parts come from prep_parts.py,
          run with the project venv python before this)
  anim    every clip (anim_boy.py); saves art/blender/chars/boy/boy.blend
  render  each clip -> art/blender/chars/boy/renders/<clip>/####.png (720 x 1200 RGBA, frames from 0001) and the
          shoe pass -> renders/<clip>_unlit/####.png (white, alpha = the shoes as they show on screen)
  meta    renders/meta.json: fps, size, rest height, ground line, clips (frames, loop, the idle's cues), the shoes'
          spans per frame (for the game's foot shadows)
  qa      tools/blender/chars/boy/qa_boy.py in the project venv: sheets, joint zooms, seams, holes ->
          art/blender/chars/boy/qa/
Without build, the saved boy.blend is opened first. Environment knobs (for quick looks): BOY_CLIPS=idle,win
(only these), BOY_PASSES=beauty,unlit, BOY_SAMPLES=32, BOY_UNLIT_SAMPLES=16, BOY_EVERY=1 (every nth frame),
BOY_RENDERS=<dir>."""
import glob, json, math, os, subprocess, sys, time
import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
BOY = os.path.join(ROOT, "art", "blender", "chars", "boy")
BLEND = os.path.join(BOY, "boy.blend")
RENDERS = os.environ.get("BOY_RENDERS") or os.path.join(BOY, "renders")
VENV = os.path.join(os.path.dirname(ROOT), "smukiez-slot", ".venv", "Scripts", "python.exe")

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
steps = (argv[0] if argv else "parts,build,anim,render,meta,qa").split(",")
only = [c for c in os.environ.get("BOY_CLIPS", "").split(",") if c]
passes = os.environ.get("BOY_PASSES", "beauty,unlit").split(",")
every = int(os.environ.get("BOY_EVERY", "1"))


def run(path):
    g = {"__name__": "__main__", "__file__": path}
    exec(compile(open(path, encoding="utf-8").read(), path, "exec"), g)


t0 = time.time()
if "parts" in steps:
    subprocess.run([VENV, os.path.join(HERE, "prep_parts.py")], check=True)
    subprocess.run([VENV, os.path.join(HERE, "hires_parts.py")], check=True)      # the 4x textures
if "build" in steps:
    run(os.path.join(HERE, "build_boy.py"))
else:
    bpy.ops.wm.open_mainfile(filepath=BLEND)
if "anim" in steps:
    run(os.path.join(HERE, "anim_boy.py"))
    for a in [a for a in bpy.data.actions if a.users == 0 and not a.use_fake_user]:
        bpy.data.actions.remove(a)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("saved", BLEND, flush=True)

sc = bpy.data.scenes["BOY"]
arm = bpy.data.objects["BOY_rig"]
cam = sc.camera
clips = {k: (int(v[0]), int(v[1])) for k, v in arm["clips"].items()}
loops = set(arm.get("loops", []))
todo = [c for c in clips if not only or c in only]
S = float(arm["screen_scale"])                       # screen px per master px
RES = (sc.render.resolution_x, sc.render.resolution_y)


def mask(v):
    bpy.data.node_groups["BOY_mask"].nodes["mask"].outputs[0].default_value = v
    for m in bpy.data.materials:                        # Grease Pencil effects: black in the shoe pass
        if m.grease_pencil and "color_beauty" in m.keys():
            m.grease_pencil.color = (0, 0, 0, 1) if v else tuple(m["color_beauty"])
            m.grease_pencil.fill_color = (0, 0, 0, 1) if v else tuple(m["fill_beauty"])


def to_shoe_alpha(path):
    """the shoe pass (shoes white, every other part black, as composed) -> white, alpha = how much shoe shows"""
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    a = np.clip(px[..., 0] * px[..., 3], 0, 1)
    out = np.ones_like(px)
    out[..., 3] = a
    img.pixels.foreach_set(out.ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


REMAP = {k: (int(v[0]), int(v[1])) for k, v in arm["remap"].items()} if "remap" in arm.keys() else {}


def rendered_times(name):
    """keyed (timeline) time of each rendered frame of a clip: slowed with Blender's Time Remapping (render
    frame F shows the timeline at F * old / new) - a loop sampled evenly round its whole cycle, a one-shot from
    its first key to its last"""
    a, b = clips[name]
    old, new = REMAP.get(name, (1, 1))
    n_out = new if name in loops else new + 1
    return [a + j * old / new for j in range(n_out)]


def render_clip(name, a, b, out_dir, unlit=False):
    os.makedirs(out_dir, exist_ok=True)
    for f in glob.glob(os.path.join(out_dir, "*.png")):
        os.remove(f)
    tmp = os.path.join(out_dir, "_raw")
    os.makedirs(tmp, exist_ok=True)
    old, new = REMAP.get(name, (1, 1))
    n_out = len(rendered_times(name))
    F0 = a * new // old                                 # a is a multiple of old (anim_boy.place_next)
    assert F0 * old == a * new, (name, a, old, new)
    sc.render.frame_map_old, sc.render.frame_map_new = old, new
    sc.frame_start, sc.frame_end, sc.frame_step = F0, F0 + n_out - 1, every
    sc.render.filepath = tmp + os.sep
    try:
        bpy.ops.render.render(animation=True, scene=sc.name)
    finally:
        sc.render.frame_map_old = sc.render.frame_map_new = 100
    for F in range(F0, F0 + n_out, every):
        src = os.path.join(tmp, f"{F:04d}.png")
        dst = os.path.join(out_dir, f"{F - F0 + 1:04d}.png")
        os.replace(src, dst)
        if unlit:
            to_shoe_alpha(dst)
    os.rmdir(tmp)
    sc.frame_step = 1


if "render" in steps:
    sc.render.film_transparent = True
    sc.render.use_compositing = False
    try:
        sc.eevee.taa_render_samples = int(os.environ.get("BOY_SAMPLES", "32"))
    except Exception:
        pass
    for name in todo:
        a, b = clips[name]
        if "beauty" in passes:
            mask(0.0)
            render_clip(name, a, b, os.path.join(RENDERS, name))
        if "unlit" in passes:
            mask(1.0)
            try:                                        # a flat two-tone pass: fewer samples smooth it as well
                sc.eevee.taa_render_samples = int(os.environ.get("BOY_UNLIT_SAMPLES", "16"))
            except Exception:
                pass
            render_clip(name, a, b, os.path.join(RENDERS, name + "_unlit"), unlit=True)
            try:
                sc.eevee.taa_render_samples = int(os.environ.get("BOY_SAMPLES", "32"))
            except Exception:
                pass
        mask(0.0)
        print(f"rendered {name} ({b - a + 1} frames) {time.time() - t0:.0f} s", flush=True)


def to_screen(v):
    return (RES[0] / 2 + (v.x - cam.location.x) * 100 * S, RES[1] / 2 - (v.z - cam.location.z) * 100 * S)


def shoe_outline(name):
    """points round the shoe's drawing (alpha > .5) in the mesh's own coordinates"""
    ob = bpy.data.objects["BOY_" + name]
    img = ob.active_material.node_tree.nodes["Image Texture"].image
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    al = px.reshape(h, w, 4)[::-1, :, 3] > .5           # rows top-down
    vs = [v.co for v in ob.data.vertices]
    x0, x1 = min(v.x for v in vs), max(v.x for v in vs)
    z0, z1 = min(v.z for v in vs), max(v.z for v in vs)
    pts = []
    for i in range(0, w, 2):
        col = np.nonzero(al[:, i])[0]
        if len(col):
            for j in (col[0], col[-1]):
                pts.append((x0 + (x1 - x0) * (i + .5) / w, z1 - (z1 - z0) * (j + .5) / h))
    return ob, pts


def bone_points():
    out = []
    for pb in arm.pose.bones:
        if pb.name.startswith("toss_"):
            continue
        out.append(arm.matrix_world @ pb.head)
        out.append(arm.matrix_world @ pb.tail)
    return out


JOINTS = {  # name: (bone, at its tail?, the bone whose turn is the bend there)
    "knee_l": ("shin_l", False, "shin_l"), "knee_r": ("shin_r", False, "shin_r"),
    "ankle_l": ("shin_l", True, "foot_l"), "ankle_r": ("shin_r", True, "foot_r"),
    "hip_l": ("thigh_l", False, "thigh_l"), "hip_r": ("thigh_r", False, "thigh_r"),
    "elbow_l": ("arm_l_fore", False, "arm_l_fore"), "wrist_l": ("arm_l_fore", True, "hand_l"),
    "shoulder_l": ("arm_l_upper", False, "arm_l_upper"), "neck": ("head", False, "head"),
    "waist": ("torso", False, "torso"), "cap": ("cap.0", True, "cap.1"), "grip": ("grip", False, "grip"),
    "print": ("chest", False, "chest")}       # the chest print (the T-shirt's SMUKIEZ)

if "meta" in steps:
    from mathutils import Vector
    rest = []
    for b in arm.data.bones:
        if not b.name.startswith("toss_"):
            rest += [arm.matrix_world @ b.head_local, arm.matrix_world @ b.tail_local]
    rest_s = [to_screen(v) for v in rest]
    shoes = [shoe_outline("shoe_l"), shoe_outline("shoe_r")]
    meta_path = os.path.join(RENDERS, "meta.json")
    meta = {"fps": sc.render.fps, "size": list(RES), "rest_height_px": round(float(arm["rest_px"]), 2),
            "ground_y": round(float(arm["ground_y"]), 2), "clips": {}, "track": {}}
    report = {}
    for name, (a, b) in clips.items():
        track, dist, joints = [], [], []
        for t in rendered_times(name):
            sc.frame_set(int(math.floor(t + 1e-9)), subframe=t - math.floor(t + 1e-9))
            jrow = {}
            for jn, (bn, end, rel) in JOINTS.items():
                pb = arm.pose.bones[bn]
                v = to_screen(arm.matrix_world @ (pb.tail if end else pb.head))
                jrow[jn] = [round(v[0], 1), round(v[1], 1), round(math.degrees(arm.pose.bones[rel].rotation_euler.z), 2) if rel else 0]
            joints.append(jrow)
            row = []
            for ob, pts in shoes:
                M = ob.matrix_world
                sp = [to_screen(M @ Vector((x, 0, z))) for x, z in pts]
                xs = [p[0] for p in sp]; ys = [p[1] for p in sp]
                row.append([round(min(xs), 1), round(max(xs), 1), round(max(ys), 1)])
            track.append({"shoes": row})
            now = [to_screen(v) for v in bone_points()]
            dist.append(max(math.hypot(p[0] - q[0], p[1] - q[1]) for p, q in zip(now, rest_s)))
        entry = {"frames": len(track), "loop": name in loops}
        # rest-pose frames (within 1.5 screen px of rest): the idle's cut points; in a one-shot, where the game
        # may cut out of it early
        entry["cues"] = [i for i, d in enumerate(dist) if d <= 1.5 * RES[1] / 1200]      # 1.5 px of the 1200 px frame
        meta["clips"][name] = entry
        meta["track"][name] = track
        report[name] = {"first_vs_rest_px": round(dist[0], 3), "last_vs_rest_px": round(dist[-1], 3),
                        "max_px": round(max(dist), 1)}
        report[name]["joints"] = joints
        if name in loops:
            report[name]["cues"] = entry["cues"]
            report[name]["dist"] = [round(d, 2) for d in dist]
    os.makedirs(RENDERS, exist_ok=True)
    json.dump(meta, open(meta_path, "w"), indent=None, separators=(",", ":"))
    os.makedirs(os.path.join(BOY, "qa"), exist_ok=True)
    json.dump(report, open(os.path.join(BOY, "qa", "pose_report.json"), "w"), indent=1)
    print("meta ->", meta_path, json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("dist", "joints")} for k, v in report.items()}), flush=True)

if "qa" in steps:
    if os.path.exists(VENV):
        subprocess.run([VENV, os.path.join(HERE, "qa_boy.py")] + (only or []), check=False)
    else:
        print("qa: no venv python at", VENV)
print(f"BOY done: {','.join(steps)} | {time.time() - t0:.0f} s", flush=True)
