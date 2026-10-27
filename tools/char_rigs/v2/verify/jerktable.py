import json, sys
for who in ('boy', 'skull'):
    old = json.load(open(f'look/jerk_old_{who}.json')); new = json.load(open(f'look/jerk_new_{who}.json'))
    print(f'=== {who}: max accel px/frame^2 (60 fps, figure 1600 px tall) and RMS jerk; all bones | bones both rigs have')
    print(f"{'clip':13s} {'old all':>8s} {'new all':>8s} {'old common':>11s} {'new common':>11s}   {'old rmsJ':>8s} {'new rmsJ':>8s}   new worst bone")
    for clip in old:
        if clip not in new: continue
        o = {b[0]: b for b in old[clip]['all']}; n = {b[0]: b for b in new[clip]['all']}
        common = set(o) & set(n)
        oc = max(o[b][1] for b in common); nc = max(n[b][1] for b in common)
        om = sum(b[3] for b in o.values()) / len(o); nm = sum(b[3] for b in n.values()) / len(n)
        worst = max(n.values(), key=lambda b: b[1])
        print(f"{clip:13s} {old[clip]['maxAcc']:8.2f} {new[clip]['maxAcc']:8.2f} {oc:11.2f} {nc:11.2f}   {om:8.3f} {nm:8.3f}   {worst[0]} {worst[1]} @{worst[2]}s")
    print('common bones:', sorted(common))
