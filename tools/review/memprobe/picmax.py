"""Biggest size each picture is drawn at across picfit.py runs (device px), against its file: what a phone copy needs.
usage: picmax.py PICFIT.json [...]"""
import json, sys
best = {}
for f in sys.argv[1:]:
    for u, r in json.load(open(f)).items():
        b = best.setdefault(u, {"file": r["file"], "mb": r["mb"], "w": 0, "h": 0, "at": set()})
        b["w"] = max(b["w"], r["shown"][0]); b["h"] = max(b["h"], r["shown"][1])
        b["at"].update(a.split(":")[0] for a in r["at"])
for u, b in sorted(best.items(), key=lambda kv: -kv[1]["mb"]):
    if b["mb"] < 1.5:
        continue
    over = max(b["file"][0] / max(1, b["w"]), b["file"][1] / max(1, b["h"]))
    print(f'{b["mb"]:6.2f} MB {b["file"][0]}x{b["file"][1]} max shown {b["w"]}x{b["h"]} over {over:4.2f} {u} {sorted(b["at"])}')
