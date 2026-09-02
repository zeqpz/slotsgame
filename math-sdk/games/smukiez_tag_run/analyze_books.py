"""Quick diagnostic stats over generated Smukiez Tag Run books.

Usage: python analyze_books.py [mode ...]   (default: base bonus extremebonus)
"""

import io
import json
import os
import sys
from collections import Counter

import zstandard


def read_books(path):
    with open(path, "rb") as fh:
        reader = zstandard.ZstdDecompressor().stream_reader(fh)
        for line in io.TextIOWrapper(reader, encoding="utf-8"):
            line = line.strip()
            if line:
                yield json.loads(line)


def pct(values, q):
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(int(len(ordered) * q), len(ordered) - 1)
    return ordered[idx]


def analyze(mode):
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "library", "publish_files", f"books_{mode}.jsonl.zst"
    )
    if not os.path.exists(path):
        print(f"[{mode}] no book file at {path}")
        return

    payouts, spins_per_bonus, sections_end, char_totals, drip_counts = [], [], [], [], []
    full_walls, bonuses, criteria_payouts = 0, 0, {}
    for book in read_books(path):
        payout = book["payoutMultiplier"] / 100
        payouts.append(payout)
        criteria_payouts.setdefault(book["criteria"], []).append(payout)

        events = book["events"]
        n_spins = sum(1 for e in events if e["type"] == "updateFreeSpin")
        max_sections = max((e["sections"] for e in events if e["type"] == "paintedWall"), default=0)
        n_drips = sum(len(e["drips"]) for e in events if e["type"] == "paintDrips")
        chars = [e["totalMult"] for e in events if e["type"] == "characterMults"]
        has_wall = any(e["type"] == "fullWall" for e in events)

        if any(e["type"] == "freeSpinTrigger" for e in events):
            bonuses += 1
            spins_per_bonus.append(n_spins)
            sections_end.append(max_sections)
        full_walls += 1 if has_wall else 0
        char_totals.extend(chars)
        drip_counts.append(n_drips)

    n = len(payouts)
    print(f"\n[{mode}] books={n} mean={sum(payouts)/n:.2f}x  "
          f"p50={pct(payouts,0.5):.2f} p90={pct(payouts,0.9):.2f} p99={pct(payouts,0.99):.2f} max={max(payouts):.0f}")
    for crit, vals in sorted(criteria_payouts.items()):
        print(f"    criteria {crit:<12} n={len(vals):<6} mean={sum(vals)/len(vals):8.2f}x  "
              f"p50={pct(vals,0.5):8.2f} p90={pct(vals,0.9):8.2f} max={max(vals):8.0f}")
    if bonuses:
        print(f"    bonuses={bonuses}  fullWall={full_walls} ({100*full_walls/bonuses:.2f}% of bonuses)")
        print(f"    spins/bonus: mean={sum(spins_per_bonus)/bonuses:.1f} max={max(spins_per_bonus)}")
        print(f"    painted sections at end: {dict(sorted(Counter(sections_end).items()))}")
    if char_totals:
        print(f"    charMult events={len(char_totals)} mean={sum(char_totals)/len(char_totals):.2f} "
              f"dist={dict(sorted(Counter(min(c, 50) for c in char_totals).items()))}")


if __name__ == "__main__":
    modes = sys.argv[1:] or ["base", "bonus", "extremebonus"]
    for m in modes:
        analyze(m)
