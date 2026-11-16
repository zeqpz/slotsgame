"""Median frame times of interleaved lag.py runs: DIR holds final_<before|after>_<n>.json.
usage: lagtable.py DIR"""
import glob, json, os, statistics, sys
d = sys.argv[1]
runs = {t: [json.load(open(f)) for f in sorted(glob.glob(os.path.join(d, f"final_{t}_*.json")))] for t in ("before", "after")}
scen = ["idle", "spin_3", "tumble_36873", "bigwin_33152", "bonus_38"]
med = lambda xs: statistics.median(xs) if xs else None
print(f"runs: before {len(runs['before'])}, after {len(runs['after'])}")
print("| scenario | p50 ms | p95 ms | p99 ms | worst ms | frames > 20 ms | long tasks (sum ms) | long tasks in the first second |")
print("|---|---:|---:|---:|---:|---:|---:|---:|")
for s in scen:
    row = []
    for k in ("p50", "p95", "p99", "worst", "over20", "long"):
        b = med([r["scen"][s][k] for r in runs["before"] if s in r["scen"]]); a = med([r["scen"][s][k] for r in runs["after"] if s in r["scen"]])
        row.append(f"{b:g} -> **{a:g}**" if b is not None and a is not None else "-")
    ls = lambda t: med([r["scen"][s]["longSum"] for r in runs[t] if s in r["scen"]])
    fs = lambda t: med([len(r["scen"][s].get("longFirstSec", [])) for r in runs[t] if s in r["scen"]])
    row[-1] = f"{row[-1]} ({ls('before'):g} -> {ls('after'):g})"
    print(f"| {s} | " + " | ".join(row) + f" | {fs('before'):g} -> {fs('after'):g} |")
