"""Generate the Smukiez Tag Run reel-strip CSVs (deterministic; stdlib only).

Strips (100 positions x 5 reels):
    BR0     base game
    BRE     base game with Phantom (ES) scatters, used for forced Extreme entries
    FR0     standard bonus free spins (no scatters)
    FRE     extreme bonus free spins (no scatters)
    FRWCAP  Multi-rich free-spin strip for wincap simulations

Symbol counts below are per reel (a single int applies to all 5 reels, a 5-list sets
each reel). Scatter-class symbols (BS/ES) keep a circular gap of >= 6 so at most one can
appear in any 4-row window, which the exact-count board forcing relies on.

Run:  python gen_reels.py
"""

import os
import random

STRIP_LEN = 100
NUM_REELS = 5
SCATTER_GAP = 6  # min circular distance between scatter-class symbols on a reel
LOW_WEIGHTS = {
    "L1": 1.0, "L2": 1.05, "L3": 1.1, "L4": 1.15, "L5": 1.2,
    "L6": 1.2, "L7": 1.25, "L8": 1.25, "L9": 1.3, "L10": 1.3,
}

# per-strip symbol counts: {symbol: int | [r0, r1, r2, r3, r4]}
STRIPS = {
    # M is the Multi. Every C1/C2/C3 and W slot they replaced went to the premiums, so the
    # premium density is a little higher than v2 rather than a little lower.
    "BR0": {
        "seed": 101,
        "scatters": {"BS": 2},
        "specials": {"M": 1},
        "highs": {"H1": 5, "H2": 5, "H3": 5, "H4": 5, "H5": 5, "H6": 5, "H7": 5},
    },
    "BRE": {
        "seed": 202,
        "scatters": {"BS": 2, "ES": [0, 2, 0, 2, 0]},
        "specials": {"M": 1},
        "highs": {"H1": 5, "H2": 5, "H3": 5, "H4": 5, "H5": 5, "H6": 5, "H7": 5},
    },
    "FR0": {
        "seed": 303,
        "scatters": {},
        "specials": {"M": 7},
        "highs": {"H1": 7, "H2": 7, "H3": 7, "H4": 7, "H5": 7, "H6": 7, "H7": 7},
    },
    "FRE": {
        "seed": 404,
        "scatters": {},
        "specials": {"M": 11},
        "highs": {"H1": 7, "H2": 7, "H3": 7, "H4": 7, "H5": 7, "H6": 7, "H7": 7},
    },
    "FRWCAP": {
        "seed": 505,
        "scatters": {},
        "specials": {"M": 22},
        "highs": {"H1": 8, "H2": 8, "H3": 8, "H4": 8, "H5": 8, "H6": 8, "H7": 8},
    },
}


def per_reel(count) -> list:
    return list(count) if isinstance(count, (list, tuple)) else [count] * NUM_REELS


def circular_gap(a: int, b: int, length: int) -> int:
    diff = abs(a - b) % length
    return min(diff, length - diff)


def place_spaced(rng: random.Random, count: int, taken: set, min_gap: int, spaced: list) -> list:
    """Pick `count` free positions keeping `min_gap` circular distance from `spaced` members."""
    chosen = []
    for _ in range(count):
        candidates = [
            p
            for p in range(STRIP_LEN)
            if p not in taken and all(circular_gap(p, s, STRIP_LEN) >= min_gap for s in spaced)
        ]
        assert candidates, "no spaced position available; lower counts or the gap"
        pick = rng.choice(candidates)
        chosen.append(pick)
        taken.add(pick)
        spaced.append(pick)
    return chosen


def build_reel(rng: random.Random, reel_idx: int, spec: dict) -> list:
    strip = [None] * STRIP_LEN
    taken, scatter_positions = set(), []

    for sym, counts in spec["scatters"].items():
        for pos in place_spaced(rng, per_reel(counts)[reel_idx], taken, SCATTER_GAP, scatter_positions):
            strip[pos] = sym

    for sym, counts in spec["specials"].items():
        placed = 0
        while placed < per_reel(counts)[reel_idx]:
            pos = rng.randrange(STRIP_LEN)
            if pos in taken:
                continue
            strip[pos] = sym
            taken.add(pos)
            placed += 1

    open_slots = [p for p in range(STRIP_LEN) if strip[p] is None]
    bag = []
    for sym, counts in spec["highs"].items():
        bag.extend([sym] * per_reel(counts)[reel_idx])
    lows_needed = len(open_slots) - len(bag)
    assert lows_needed >= 0, "high-symbol counts exceed open slots"
    total_weight = sum(LOW_WEIGHTS.values())
    low_counts = {sym: int(lows_needed * w / total_weight) for sym, w in LOW_WEIGHTS.items()}
    leftovers = lows_needed - sum(low_counts.values())
    for sym in sorted(LOW_WEIGHTS, key=LOW_WEIGHTS.get, reverse=True)[:leftovers]:
        low_counts[sym] += 1
    for sym, n in low_counts.items():
        bag.extend([sym] * n)

    rng.shuffle(bag)
    for pos, sym in zip(open_slots, bag):
        strip[pos] = sym
    return strip


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    for name, spec in STRIPS.items():
        rng = random.Random(spec["seed"])
        reels = [build_reel(rng, r, spec) for r in range(NUM_REELS)]
        path = os.path.join(out_dir, f"{name}.csv")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            for row in range(STRIP_LEN):
                f.write(",".join(reels[r][row] for r in range(NUM_REELS)) + "\n")
        counts = {}
        for r in range(NUM_REELS):
            for s in reels[r]:
                counts[s] = counts.get(s, 0) + 1
        print(f"{name}: wrote {path}")
        print("   totals:", dict(sorted(counts.items())))


if __name__ == "__main__":
    main()
