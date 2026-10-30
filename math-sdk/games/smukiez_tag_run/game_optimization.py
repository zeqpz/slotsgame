"""Optimization parameters for Smukiez Tag Run bet modes.

RTP allocation (total 0.967 per mode, v5 - the top of the 3-star volatility band):
    base:         wincap 0.002 | freegame 0.340 (hr 240) | extremegame 0.047 (hr 8000)
                  | wallcover 0.012 (hr 80000) | basegame 0.566 (hr 2.5)
    bonus:        wincap 0.004 | freegame 0.963
    extremebonus: wincap 0.0018 | extremegame 0.9652

The extreme's cap share is small on purpose: the 3-star band asks etl10k (the return from
10,000x wins) <= 0.8, and at 0.01 the 10,000x landed once in 2,500 extreme buys (etl10k 4.0).

The av_win each criteria is asked for (rtp x hr) sits near the simulated pool's own mean, so the
optimiser weights the pool rather than fighting it (v5 pools, tune_v5): the natural free game
averages ~82x and is asked for 82x, the extreme ~375x for 376x, the board cover ~920x for 960x.
The base game's winning spins average ~2.9x in the pool against 1.415x asked: with three times the
walls the big multiplied wins are there to be seen, and the optimiser keeps them rare.

The base game's winning spins are weighted per BOOK, not per payout (see base_book_scaling): the
optimiser on its own weights payout values and splits each one evenly over the books that pay it,
which put 23% of all base rounds on the 277 books paying exactly 0.5x or 0.6x (each drawn about
1 in 1,100 spins) and left the 22,000 books paying 0.8x with almost nothing.
"""

import json
import os
from collections import Counter

from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructConditions,
    ConstructFenceBias,
    verify_optimization_input,
)

# The base game's winning spins as a player should meet them once the table is weighted: how
# often (1 in N base spins) a win lands in each band above 5x. The wins below 5x take the rest of
# the criteria's hit rate and RTP, leaning toward the bottom (a v^-a tilt, a solved to fit).
# The old value-weighted table had 5-20x 1 in 167, 20-100x 1 in 143, 100x+ 1 in 12,555: keeping
# all of that leaves the small wins averaging 0.5x, which can only be paid by drawing each 0.4x
# book about 1 in 10,000 spins, so the tail gives up about a third of its RTP (0.373 -> ~0.25).
BASE_TAIL = ((5, 20, 100), (20, 100, 250), (100, None, 15000))
# The tail is asked for at 80% of that. The table's own mean then sits a little under the
# criteria's and the optimiser lands the RTP by mixing in a few more high wins (measured: 5-20x
# 1 in 92-127, 20-100x 1 in 181-204); asked for in full, two runs in six instead piled the
# difference onto the 0.4x books (1 in ~13,000 each), while at 80% all three runs kept every
# board rarer than 1 in 20,000.
BASE_TAIL_ASK = 0.8
# Over 100x the optimiser's own curves thin the pool's few books (38 of them) to a third or less
# of what is asked, so they are asked for three times as much.
BASE_TOP_LIFT = 3.0


def base_book_scaling(game_config, conditions, criteria="basegame", mode="base"):
    """One scaling entry per payout of the `criteria` fence, read off the simulated pool.

    The optimiser builds each criteria's distribution as smooth curves over its PAYOUT VALUES and
    splits each value's weight evenly over the books that pay it, so a payout few books reach is
    drawn as often as one thousands reach: 0.5x (165 books) and 0.6x (112) each took ~12% of all
    rounds while 0.8x (22,000 books) got 0.004%. Scaling each payout by its book count makes the
    curves weigh BOOKS instead - every board of a payout drawn about as often as its neighbours'.
    On top of that sits the win profile above (BASE_TAIL), so the curves start from the shape
    wanted and the optimiser only has to fit the RTP and pick the best-scoring variation.

    Returns [] when there is no pool yet, which is why run.py builds the setup after the sims.
    """
    lut = os.path.join(game_config.library_path, "lookup_tables", f"lookUpTable_{mode}.csv")
    forces = os.path.join(game_config.library_path, "forces", f"force_record_{mode}.json")
    if not (os.path.exists(lut) and os.path.exists(forces)):
        return []

    # the books the optimiser hands to earlier criteria: exact payouts (wincap, 0) and searches
    names = list(conditions)
    fixed, searches = set(), []
    for name in names[: names.index(criteria)]:
        cond = conditions[name]
        if cond["force_search"]:
            searches.append(cond["force_search"])
        elif cond["search_range"][0] == cond["search_range"][1] != -1:
            fixed.add(round(cond["search_range"][0] * 100))
    taken = set()
    for option in json.load(open(forces, encoding="UTF-8")):
        keys = {(k["name"], k["value"]) for k in option["search"]}
        if any(all((str(n), str(v)) in keys for n, v in s.items()) for s in searches):
            taken.update(option["bookIds"])
    counts = Counter()
    with open(lut, encoding="UTF-8") as f:
        for line in f:
            book, _, payout = (int(x) for x in line.split(","))
            if book not in taken and payout not in fixed:
                counts[payout / 100] += 1

    share = 1 / conditions[criteria]["hr"]    # the criteria's share of all rounds
    mean = conditions[criteria]["rtp"] * conditions[criteria]["hr"]
    split = BASE_TAIL[0][0]
    bands = []
    for lo, hi, one_in in BASE_TAIL:
        books = {v: n for v, n in counts.items() if lo < v <= (hi or float("inf"))}
        size = sum(books.values())
        bands.append((lo, hi or float("inf"), (1 / one_in) / share, size, sum(v * n for v, n in books.items()) / size))
    tail_mass = sum(m for _, _, m, _, _ in bands)
    small_mean = (mean - sum(m * avg for _, _, m, _, avg in bands)) / (1 - tail_mass)
    small = {v: n for v, n in counts.items() if v <= split}
    lo_a, hi_a = -5.0, 10.0
    for _ in range(100):
        a = (lo_a + hi_a) / 2
        tilted = sum(n * v**-a for v, n in small.items())
        if sum(n * v**-a * v for v, n in small.items()) / tilted > small_mean:
            lo_a = a
        else:
            hi_a = a
    assert abs(sum(n * v**-a * v for v, n in small.items()) / tilted - small_mean) < 1e-6, (
        f"BASE_TAIL leaves the small wins a {small_mean:.3f}x mean the pool cannot tilt to")
    total = tilted / (1 - tail_mass)          # the per-book weights' sum, small part included
    levels = [(lo, hi, BASE_TAIL_ASK * m * total / size * (BASE_TOP_LIFT if lo >= 100 else 1.0))
              for lo, hi, m, size, _ in bands]

    most = max(counts.values())
    scaling = []
    for v, n in sorted(counts.items()):
        per_book = v**-a if v <= split else next(level for lo, hi, level in levels if lo < v <= hi)
        scaling.append({
            "criteria": criteria,
            "scale_factor": n / most * per_book,
            "win_range": (round(v - 0.005, 3), round(v + 0.005, 3)),
            "probability": 1.0,
        })
    return scaling


class OptimizationSetup:
    """Handle all game mode optimization parameters."""

    def __init__(self, game_config):
        self.game_config = game_config
        wincaps = {}
        for bm in game_config.bet_modes:
            wincaps[bm.get_name()] = bm.get_wincap()
        # Targets for the v5 wall economy (av_win = rtp*hr must be reachable from each criteria's
        # simulated distribution - see the pool means above).
        base_conditions = {
            "wincap": ConstructConditions(
                rtp=0.002, av_win=wincaps["base"], search_conditions=wincaps["base"]
            ).return_dict(),
            "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
            "freegame": ConstructConditions(
                rtp=0.34, hr=240, search_conditions={"symbol": "scatter"}
            ).return_dict(),
            "extremegame": ConstructConditions(
                rtp=0.047, hr=8000, search_conditions={"symbol": "scatter_extreme"}
            ).return_dict(),
            # the whole board covered in walls: the base game's jackpot, about once in 80,000 spins
            "wallcover": ConstructConditions(
                rtp=0.012, hr=80000, search_conditions={"symbol": "wallcover"}
            ).return_dict(),
            "basegame": ConstructConditions(hr=2.5, rtp=0.566).return_dict(),
        }
        self.game_config.opt_params = {
            "base": {
                "conditions": base_conditions,
                "scaling": ConstructScaling(base_book_scaling(game_config, base_conditions)).return_dict(),
                "parameters": ConstructParameters(
                    num_show=1500,
                    num_per_fence=2000,
                    min_m2m=1,
                    max_m2m=400,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[50, 100, 200],
                    test_weights=[0.3, 0.4, 0.3],
                    score_type="rtp",
                ).return_dict(),
            },
            "bonus": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.004, av_win=wincaps["bonus"], search_conditions=wincaps["bonus"]
                    ).return_dict(),
                    "freegame": ConstructConditions(rtp=0.963, hr="x").return_dict(),
                },
                "scaling": ConstructScaling([]).return_dict(),
                "parameters": ConstructParameters(
                    num_show=1500,
                    num_per_fence=2000,
                    min_m2m=1,
                    max_m2m=400,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[10, 20, 50],
                    test_weights=[0.6, 0.2, 0.2],
                    score_type="rtp",
                ).return_dict(),
            },
            "extremebonus": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.0018, av_win=wincaps["extremebonus"], search_conditions=wincaps["extremebonus"]
                    ).return_dict(),
                    "extremegame": ConstructConditions(rtp=0.9652, hr="x").return_dict(),
                },
                "scaling": ConstructScaling([]).return_dict(),
                "parameters": ConstructParameters(
                    num_show=1500,
                    num_per_fence=2000,
                    min_m2m=1,
                    max_m2m=400,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[10, 20, 50],
                    test_weights=[0.6, 0.2, 0.2],
                    score_type="rtp",
                ).return_dict(),
            },
        }

        verify_optimization_input(self.game_config, self.game_config.opt_params)
