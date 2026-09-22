"""Regenerate frontend/strips.js from the game's reel CSVs.

The RGS serves no strips endpoint, so the blurred spin-through the client shows while the
reels turn ships with the client as STRIP_SETS. Only the strips a player can see are
included: the wincap strip exists for the simulator alone.

Run:  python tools/gen_strips_js.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REELS = os.path.join(ROOT, "math-sdk", "games", "smukiez_tag_run", "reels")
OUT = os.path.join(ROOT, "frontend", "strips.js")
SHIPPED = ["BR0", "BRE", "FR0", "FRE"]


def read_strip(name):
    with open(os.path.join(REELS, name + ".csv"), encoding="utf-8") as fh:
        rows = [line.strip().split(",") for line in fh if line.strip()]
    reels = list(zip(*rows))
    return [list(r) for r in reels]


sets = {name: read_strip(name) for name in SHIPPED}
with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("/* Reel strips, generated from math-sdk/games/smukiez_tag_run/reels/*.csv by\n")
    fh.write("   tools/gen_strips_js.py. The RGS serves no strips endpoint, so the blurred\n")
    fh.write("   spin-through ships with the client. */\n")
    fh.write("const STRIP_SETS = " + json.dumps(sets, separators=(",", ":")) + ";\n")
n = {k: (len(v), len(v[0])) for k, v in sets.items()}
print("wrote", OUT, n)
