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
                # Targets retuned for the cascade economy (av_win = rtp*hr must be reachable
                # from each criteria's simulated distribution — see analyze_books means).
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.002, av_win=wincaps["base"], search_conditions=wincaps["base"]
                    ).return_dict(),
                    "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
                    "freegame": ConstructConditions(
                        rtp=0.35, hr=250, search_conditions={"symbol": "scatter"}
                    ).return_dict(),
                    "extremegame": ConstructConditions(
                        rtp=0.05, hr=1000, search_conditions={"symbol": "scatter_extreme"}
                    ).return_dict(),
                    "basegame": ConstructConditions(hr=2.5, rtp=0.563).return_dict(),
                },
                "scaling": ConstructScaling([]).return_dict(),
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
                    "freegame": ConstructConditions(rtp=0.961, hr="x").return_dict(),
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
                        rtp=0.01, av_win=wincaps["extremebonus"], search_conditions=wincaps["extremebonus"]
                    ).return_dict(),
                    "extremegame": ConstructConditions(rtp=0.955, hr="x").return_dict(),
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
