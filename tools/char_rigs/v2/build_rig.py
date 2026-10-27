"""build_rig.py boy|skull [--fast] [--clips-only]: rig + clips -> build/<name>/"""
import importlib, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rigbuild
import paths

NAMES = {'boy': 'smukiez', 'skull': 'smoke-skull'}


# The game queues idle behind every clip with a 0.2 s mix that ENDS on the clip's last frame (spine's
# addAnimation with delay 0), at a 0.8 time scale: the last 0.16 s of clip time is a linear crossfade
# into idle starting from idle's first frame. Each clip therefore eases into idle's own motion over its
# last half second and plays idle's first 0.16 s exactly - the crossfade blends two identical poses.
ONTO_IDLE = ('anticipation', 'win', 'big_win', 'lose', 'cash_show', 'cash_count', 'enter', 'ash_break')
MIX = .2 * .8


def end_on_idle(c, idle, m=MIX, blend=.5):
    import numpy as np
    D, t = c.dur, c.t
    u = np.clip((t - (D - m - blend)) / blend, 0, 1)
    w = u * u * u * (u * (u * 6 - 15) + 10)
    tau = (t - (D - m)) % idle.dur
    for bone in set(c.ch) | set(idle.ch):
        comps = set(c.ch.get(bone, {})) | set(idle.ch.get(bone, {}))
        for comp in comps:
            cv = c.get(bone, comp)
            iv = np.interp(tau, idle.t, idle.get(bone, comp))
            c.set(bone, comp, cv * (1 - w) + iv * w)


def main():
    who = sys.argv[1]; fast = '--fast' in sys.argv; clips_only = '--clips-only' in sys.argv
    name = NAMES[who]
    out = os.path.join(paths.OUT, name)
    defn = importlib.import_module(f'def_{who}')
    clips = importlib.import_module(f'clips_{who}')
    t0 = time.time()
    os.makedirs(os.path.join(paths.WORK, 'cache'), exist_ok=True)
    cache = os.path.join(paths.WORK, 'cache', name + '_skeleton.json')
    if clips_only and os.path.exists(cache):
        j = json.load(open(cache))
    else:
        j, W, bidx = rigbuild.build(defn, out, name, upscale=not fast)
        json.dump(j, open(cache, 'w'))
    j['animations'] = {}
    import legs
    import numpy as np
    built = {}
    for n, f in clips.CLIPS.items():
        c = f()
        if getattr(defn, 'LEGS', None):
            legs.solve(j, c, defn.LEGS)
        built[n] = c
    idle = built['idle']
    for n, c in built.items():
        if n in ONTO_IDLE:
            end_on_idle(c, idle)
        j['animations'][n] = c.json()
    if hasattr(clips, 'post'):
        clips.post(j)
    rigbuild.write_json(j, out, name)
    nk = sum(len(k) for a in j['animations'].values() for tl in a.get('bones', {}).values() for k in tl.values())
    print(f'{name}: clips {list(j["animations"])} ({nk} bone keys), {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
