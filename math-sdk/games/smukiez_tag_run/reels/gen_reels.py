"""Generate the Smukiez Tag Run reel-strip CSVs (deterministic; stdlib only).

Strips (100 positions x 7 reels), for the 7x7 cluster board:
    BR0     base game
    BRE     base game with Phantom (ES) scatters, used for forced Extreme entries
    FR0     standard bonus free spins (no scatters)
    FRE     extreme bonus free spins (no scatters)
    FRWCAP  Multi-rich free-spin strip for wincap simulations

Symbol counts below are per reel (a single int applies to all 7 reels, a 7-list sets
each reel). Scatter-class symbols (BS/ES) keep a circular gap of >= SCATTER_GAP so at most
one can appear in any 7-row window (plus its padding), which the exact-count board forcing
relies on.

Cluster pays live or die on symbol frequency: a cluster needs five of a kind touching, so
the lows are skewed hard toward a few common ones (L1/L2 carry the hit rate) and the
premiums are scarce so a premium cluster is an event.

Run:  python gen_reels.py
"""

import os
import random

STRIP_LEN = 100
NUM_REELS = 7
SCATTER_GAP = 10  # min circular distance between scatter-class symbols on a reel (window is 9 incl. padding)
LOW_WEIGHTS = {
    "L1": 3.0, "L2": 2.6, "L3": 2.2, "L4": 1.8, "L5": 1.4,
    "L6": 1.0, "L7": 0.7, "L8": 0.5, "L9": 0.35, "L10": 0.25,
}

BASE_HIGHS = {"H1": 1, "H2": 2, "H3": 2, "H4": 2, "H5": 2, "H6": 2, "H7": 3}
FREE_HIGHS = {"H1": 2, "H2": 2, "H3": 2, "H4": 2, "H5": 3, "H6": 3, "H7": 3}

# per-strip symbol counts: {symbol: int | [r0 .. r6]}
STRIPS = {
    "BR0": {
        "seed": 101,
        "scatters": {"BS": 1},
        "specials": {"M": 1},
        "highs": BASE_HIGHS,
    },
    "BRE": {
        "seed": 202,
        "scatters": {"BS": 1, "ES": [0, 1, 0, 1, 0, 1, 0]},
        "specials": {"M": 1},
        "highs": BASE_HIGHS,
    },
    "FR0": {
        "seed": 303,
        "scatters": {},
        "specials": {"M": 2},
        "highs": FREE_HIGHS,
    },
    "FRE": {
        "seed": 404,
        "scatters": {},
        "specials": {"M": 2},
        "highs": FREE_HIGHS,
    },
    "FRWCAP": {
        "seed": 505,
        "scatters": {},
        "specials": {"M": 15},
        "highs": {"H1": 4, "H2": 4, "H3": 4, "H4": 4, "H5": 4, "H6": 4, "H7": 5},
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
