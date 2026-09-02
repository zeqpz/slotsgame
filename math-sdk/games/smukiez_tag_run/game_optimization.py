"""Optimization parameters for Smukiez Tag Run bet modes.

RTP allocation (total 0.965 per mode):
    base:         wincap 0.001 | freegame 0.270 (hr 170) | extremegame 0.070 (hr 2000) | basegame 0.624
    bonus:        wincap 0.004 | freegame 0.961
    extremebonus: wincap 0.010 | extremegame 0.955
"""

from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructConditions,
    ConstructFenceBias,
    verify_optimization_input,
)


class OptimizationSetup:
    """Handle all game mode optimization parameters."""

    def __init__(self, game_config):
        self.game_config = game_config
        wincaps = {}
        for bm in game_config.bet_modes:
            wincaps[bm.get_name()] = bm.get_wincap()
        self.game_config.opt_params = {
            "base": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.001, av_win=wincaps["base"], search_conditions=wincaps["base"]
                    ).return_dict(),
                    "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
                    "freegame": ConstructConditions(
                        rtp=0.27, hr=170, search_conditions={"symbol": "scatter"}
                    ).return_dict(),
                    "extremegame": ConstructConditions(
                        rtp=0.07, hr=2000, search_conditions={"symbol": "scatter_extreme"}
                    ).return_dict(),
                    "basegame": ConstructConditions(hr=3.4, rtp=0.624).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "basegame", "scale_factor": 1.2, "win_range": (1, 2), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 1.5, "win_range": (10, 20), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 0.8, "win_range": (1000, 2000), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 1.2, "win_range": (3000, 4000), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=5000,
                    num_per_fence=10000,
                    min_m2m=4,
                    max_m2m=8,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[50, 100, 200],
                    test_weights=[0.3, 0.4, 0.3],
                    score_type="rtp",
                ).return_dict(),
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["basegame", "freegame"],
                    bias_ranges=[(2.5, 5.5), (200.0, 500.0)],
                    bias_weights=[0.7, 0.2],
                ).return_dict(),
            },
            "bonus": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.004, av_win=wincaps["bonus"], search_conditions=wincaps["bonus"]
                    ).return_dict(),
                    "freegame": ConstructConditions(rtp=0.961, hr="x").return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "freegame", "scale_factor": 0.9, "win_range": (20, 50), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 0.8, "win_range": (1000, 2000), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 1.2, "win_range": (3000, 4000), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=5000,
                    num_per_fence=10000,
                    min_m2m=4,
                    max_m2m=8,
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
                        rtp=0.01, av_win=wincaps["extremebonus"], search_conditions=wincaps["extremebonus"]
                    ).return_dict(),
                    "extremegame": ConstructConditions(rtp=0.955, hr="x").return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "extremegame", "scale_factor": 0.9, "win_range": (100, 250), "probability": 1.0},
                        {"criteria": "extremegame", "scale_factor": 1.2, "win_range": (3000, 4500), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=5000,
                    num_per_fence=10000,
                    min_m2m=4,
                    max_m2m=8,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[10, 20, 50],
                    test_weights=[0.6, 0.2, 0.2],
                    score_type="rtp",
                ).return_dict(),
            },
        }

        verify_optimization_input(self.game_config, self.game_config.opt_params)
