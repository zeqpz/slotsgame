"""Make a symbol's animation in a background Blender, start to finish, and render it - Blender's own work, no
window needed, so several symbols can run side by side without touching the Blender the owner has open:
  "C:/Users/CooperHinkel/Blender/blender-5.2.3-windows-x64/blender.exe" -b --factory-startup \
      --python tools/blender/run.py -- <ID> [steps]
steps, comma separated (default build,anim,render,qa):
  build   the cutout scene from art/blender/parts/<ID> (build_symbol_scene.py)
  anim    tools/blender/anim_<ID>.py: the clips, the follow-through, the effects; it saves
          art/blender/symbols/<ID>.blend
  render  every clip through the compositor -> art/blender/renders/<ID>/<clip>/####.png (512 px, RGBA)
  qa      the art layer alone at 1024 px -> art/blender/qa/art/<ID>/<clip>/ (read by tools/blender/qa_clips.py)
Without build, the saved art/blender/symbols/<ID>.blend is opened first."""
import os, sys, time
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import fxkit                    # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
sid = argv[0]
steps = (argv[1] if len(argv) > 1 else "build,anim,render,qa").split(",")
os.environ["SMK_SID"] = sid
blend = os.path.join(ROOT, "art", "blender", "symbols", sid + ".blend")


def run(path):
    g = {"__name__": "__main__", "__file__": path}
    exec(compile(open(path, encoding="utf-8").read(), path, "exec"), g)


t0 = time.time()
if "build" in steps:
    run(os.path.join(HERE, "build_symbol_scene.py"))
else:
    bpy.ops.wm.open_mainfile(filepath=blend)
if "anim" in steps:
    run(os.path.join(HERE, f"anim_{sid}.py"))
sc = bpy.data.scenes[sid]
clips = fxkit.clip_ranges(sid)
if "render" in steps:
    sc.render.resolution_x = sc.render.resolution_y = 512
    for vl in sc.view_layers:
        vl.use = True
    sc.render.use_compositing = True
    for name, (a, b) in clips.items():
        fxkit.render_clip(sc, name, a, b, os.path.join(ROOT, "art", "blender", "renders", sid), fxkit.clip_slow(sid, name))
if "qa" in steps:
    # the cut parts alone (no effects drawn on the art layer - dust, thrown pieces - which would read as gaps)
    import json
    names = {f"{sid}_{p['name']}" for p in json.load(open(os.path.join(ROOT, "art", "blender", "parts", sid, "parts.json")))["parts"]}
    for o in sc.objects:                            # (not saved: this pass only renders)
        if o.type in ("MESH", "GREASEPENCIL") and o.name not in names:
            if o.animation_data:                    # keyed visibility would switch it back on
                o.animation_data.action = None
            o.hide_render = True
    for vl in sc.view_layers:
        vl.use = vl.name == "art"
    sc.render.use_compositing = False
    sc.render.resolution_x = sc.render.resolution_y = 1024
    for name, (a, b) in clips.items():
        fxkit.render_clip(sc, name, a, b, os.path.join(ROOT, "art", "blender", "qa", "art", sid), fxkit.clip_slow(sid, name))
print(f"{sid} done: {','.join(steps)} | clips {clips} | {time.time() - t0:.0f} s", flush=True)
