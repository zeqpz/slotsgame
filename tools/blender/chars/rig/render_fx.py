"""Render a character's Grease Pencil effects on their own - the parts of its clips a live rig cannot be: the boy's
landing dust and money glints, the skull's ember glow and the ash of ash_break. Run in a background Blender on the
character's .blend (read only, never saved):
  "C:/Users/CooperHinkel/Blender/blender-5.2.3-windows-x64/blender.exe" -b --factory-startup \\
      art/blender/chars/<char>/<char>.blend --python tools/blender/chars/rig/render_fx.py -- [clips]
Every mesh part is hidden (its visibility keys dropped in this throwaway session), everything else renders as the
character's own render step does (tools/blender/chars/<char>/run.py: same camera, samples, filter, Time Remapping,
compositor), so each frame is exactly the effect's share of the shipped frame:
  renders/<clip>_fx/####.png      the effects of that rendered frame (only the boy's clips that have any: a frame
                                  with nothing in it is written empty and dropped by the packer)
  renders/ash_break_fxmask/       the skull's ash in the unlit mask's colours (the light leaves it alone)
Both figures' effects lie over every part (the boy's Grease Pencil is nearer the camera than any part; the skull's
ash too, and the ember's glow is laid over the whole art layer by the compositor)."""
import bpy, math, os, sys, time

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
only = [c for c in (argv[0].split(",") if argv else []) if c]
sc = bpy.data.scenes.get("BOY") or bpy.data.scenes.get("SKULL") or bpy.context.scene
arm = next(o for o in sc.objects if o.type == "ARMATURE")
CHAR = "boy" if sc.name == "BOY" else "skull"
REN = os.path.join(os.path.dirname(bpy.data.filepath), "renders")
clips = {k: (int(v[0]), int(v[1])) for k, v in arm["clips"].items()}
REMAP = {k: (int(v[0]), int(v[1])) for k, v in arm["remap"].items()} if "remap" in arm.keys() else None
loops = set(arm.get("loops", ["idle"]))

# the parts out of the picture: drop their visibility keys (this session only) and hide them
for o in sc.objects:
    if o.type == "MESH":
        if o.animation_data:
            o.animation_data_clear()
        o.hide_render = True
sc.render.film_transparent = True
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
sc.render.image_settings.color_depth = "8"
t_all = time.time()


def clean(d):
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        if f.endswith(".png"):
            os.remove(os.path.join(d, f))


def gp_spans(ob, k0, k1):
    """keyed frames in [k0, k1] where any of the object's layers shows a drawing with strokes"""
    on = set()
    for L in ob.data.layers:
        fr = sorted(L.frames, key=lambda f: f.frame_number)
        for i, f in enumerate(fr):
            if not f.drawing or len(f.drawing.strokes) == 0:
                continue
            end = fr[i + 1].frame_number if i + 1 < len(fr) else k1 + 1
            for k in range(max(k0, f.frame_number), min(k1 + 1, end)):
                on.add(k)
    return on


if CHAR == "boy":
    # as run.py's render step: the boy's beauty pass, no compositor, BOY_SAMPLES (32)
    sc.render.use_compositing = False
    sc.eevee.taa_render_samples = int(os.environ.get("BOY_SAMPLES", "32"))
    gp = bpy.data.objects["BOY_fx"]
    for name, (a, b) in clips.items():
        if only and name not in only:
            continue
        old, new = REMAP[name]
        n_out = new if name in loops else new + 1
        on = gp_spans(gp, a, b)
        js = [j for j in range(n_out) if int(math.floor(a + j * old / new + 1e-9)) in on]
        d = os.path.join(REN, name + "_fx")
        clean(d)
        if not js:
            os.rmdir(d)
            continue
        F0 = a * new // old
        assert F0 * old == a * new
        # contiguous spans of rendered frames (gaps of empty frames under 8 are rendered through)
        spans, s0 = [], js[0]
        for p, q in zip(js, js[1:] + [None]):
            if q is None or q - p > 8:
                spans.append((s0, p)); s0 = q
        tmp = os.path.join(d, "_raw")
        os.makedirs(tmp, exist_ok=True)
        sc.render.frame_map_old, sc.render.frame_map_new = old, new
        try:
            for j0, j1 in spans:
                sc.frame_start, sc.frame_end, sc.frame_step = F0 + j0, F0 + j1, 1
                sc.render.filepath = tmp + os.sep
                bpy.ops.render.render(animation=True, scene=sc.name)
        finally:
            sc.render.frame_map_old = sc.render.frame_map_new = 100
        for f in os.listdir(tmp):
            F = int(f[:4])
            os.replace(os.path.join(tmp, f), os.path.join(d, f"{F - F0 + 1:04d}.png"))
        os.rmdir(tmp)
        print(f"fx {name}: {len(js)} frames with effects, spans {spans} | {time.time() - t_all:.0f} s", flush=True)
else:
    # as run.py set_mode("beauty"): the art layer (now only the ash) with the ember's glow composited over it
    sc.render.use_compositing = True

    def mode(m):
        for vl in sc.view_layers:
            vl.use = vl.name in {"beauty": ("art", "fx"), "unlit": ("art",)}[m]
        for mt in bpy.data.materials:
            if mt.name.startswith("SKULL_ash_") and mt.grease_pencil:
                if "orig" not in mt.keys():
                    mt["orig"] = list(mt.grease_pencil.color); mt["orig_fill"] = list(mt.grease_pencil.fill_color)
                mt.grease_pencil.color = (1, 1, 1, 1) if m == "unlit" else tuple(mt["orig"])
                mt.grease_pencil.fill_color = (1, 1, 1, 1) if m == "unlit" else tuple(mt["orig_fill"])
        sc.compositing_node_group = bpy.data.node_groups["SKULL_comp_" + m]

    for m in ("beauty", "unlit"):
        mode(m)
        for name, (a, b) in clips.items():
            if (only and name not in only) or (m == "unlit" and name != "ash_break"):
                continue
            d = os.path.join(REN, name + ("_fx" if m == "beauty" else "_fxmask"))
            clean(d)
            for i in range(b - a + 1):         # as run.py render_clip: frame f0 + i -> ####.png from 0001
                sc.frame_set(a + i)
                sc.render.filepath = os.path.join(d, f"{i + 1:04d}.png")
                bpy.ops.render.render(write_still=True)
            print(f"fx {name} {m}: {b - a + 1} frames | {time.time() - t_all:.0f} s", flush=True)
    mode("beauty")
print(f"{CHAR} fx done | {time.time() - t_all:.0f} s", flush=True)
