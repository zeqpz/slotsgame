"""Smukiez Tag Run - game configuration: symbols, paytable, paylines, bet modes.

Symbol legend (art layer maps these ids to final art):
    W   Paint Drip        expanding wild, paints its reel (+color multiplier)
    BS  Crew Leader       bonus scatter: 3/4/5 -> 8/10/12 free spins
    ES  The Phantom       extreme scatter: 2 = direct Extreme Bonus, 1 + standard trigger = upgrade
    C1  Character 1       common Smukiez character, 2x-3x spin multiplier
    C2  Character 2       uncommon Smukiez character, 5x spin multiplier
    C3  Character 3       rare Smukiez character, 8x-10x spin multiplier
    H1  Bag of Cash   H2  Cartoon Glock   H3  Gold Chain   H4  Fresh Kicks   H5  Boombox
    H6  Skateboard    H7  Limited Drop Box
    L1  Spray Can     L2  Graffiti Markers L3 Smukiez Beanie L4 Custom Hangtag L5 Dice
    L6  Smukiez Shirt L7  Hoodie           L8 Bag of Weed    L9 Freight Train  L10 Brick Wall Chunk
"""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode


class GameConfig(Config):
    """Smukiez Tag Run configuration class."""

    def __init__(self):
        super().__init__()
        self.game_id = "smukiez_tag_run"
        self.game_name = "smukiez_tag_run"
        self.provider_numer = 0
        self.provider_number = 0
        self.provider_name = "smukiez"
        self.working_name = "Smukiez Tag Run"
        self.wincap = 5000.0
        self.win_type = "lines"
        self.rtp = 0.965
        self.construct_paths()

        # Game dimensions
        self.num_reels = 5
        self.num_rows = [4] * self.num_reels

        # Paytable: (kind, symbol): payout in total-bet multiples, paid per line
        # Wilds substitute only — no own-pay. With sticky wilds + cascades, an all-wild line
        # would otherwise re-pay on every tumble and explode the RTP.
        # Cascade paytable — cut ~10x from the single-hit values: with sticky wilds and
        # tumbling, wins arrive in chains, so per-line pays are small and the frequency carries.
        self.paytable = {
            (5, "C3"): 2.5, (4, "C3"): 1, (3, "C3"): 0.4,
            (5, "C2"): 2, (4, "C2"): 0.8, (3, "C2"): 0.3,
            (5, "C1"): 1.5, (4, "C1"): 0.6, (3, "C1"): 0.3,
            (5, "H1"): 1.2, (4, "H1"): 0.5, (3, "H1"): 0.2,
            (5, "H2"): 1, (4, "H2"): 0.4, (3, "H2"): 0.2,
            (5, "H3"): 0.8, (4, "H3"): 0.3, (3, "H3"): 0.1,
            (5, "H4"): 0.6, (4, "H4"): 0.3, (3, "H4"): 0.1,
            (5, "H5"): 0.5, (4, "H5"): 0.2, (3, "H5"): 0.1,
            (5, "H6"): 0.5, (4, "H6"): 0.2, (3, "H6"): 0.1,
            (5, "H7"): 0.4, (4, "H7"): 0.2, (3, "H7"): 0.1,
            (5, "L1"): 0.3, (4, "L1"): 0.2, (3, "L1"): 0.1,
            (5, "L2"): 0.3, (4, "L2"): 0.1, (3, "L2"): 0.1,
            (5, "L3"): 0.2, (4, "L3"): 0.1, (3, "L3"): 0.1,
            (5, "L4"): 0.2, (4, "L4"): 0.1, (3, "L4"): 0.1,
            (5, "L5"): 0.2, (4, "L5"): 0.1, (3, "L5"): 0.1,
            (5, "L6"): 0.2, (4, "L6"): 0.1, (3, "L6"): 0.1,
            (5, "L7"): 0.1, (4, "L7"): 0.1, (3, "L7"): 0.1,
            (5, "L8"): 0.1, (4, "L8"): 0.1, (3, "L8"): 0.1,
            (5, "L9"): 0.1, (4, "L9"): 0.1, (3, "L9"): 0.1,
            (5, "L10"): 0.1, (4, "L10"): 0.1, (3, "L10"): 0.1,
        }

        # 20 fixed paylines on the 5x4 board (row index per reel, 0 = top)
        self.paylines = {
            1: [0, 0, 0, 0, 0],
            2: [1, 1, 1, 1, 1],
            3: [2, 2, 2, 2, 2],
            4: [3, 3, 3, 3, 3],
            5: [0, 1, 0, 1, 0],
            6: [1, 0, 1, 0, 1],
            7: [1, 2, 1, 2, 1],
            8: [2, 1, 2, 1, 2],
            9: [2, 3, 2, 3, 2],
            10: [3, 2, 3, 2, 3],
            11: [0, 1, 2, 1, 0],
            12: [3, 2, 1, 2, 3],
            13: [1, 2, 3, 2, 1],
            14: [2, 1, 0, 1, 2],
            15: [0, 0, 1, 0, 0],
            16: [3, 3, 2, 3, 3],
            17: [1, 1, 0, 1, 1],
            18: [2, 2, 3, 2, 2],
            19: [0, 1, 2, 3, 3],
            20: [3, 2, 1, 0, 0],
            21: [1, 0, 0, 0, 1],
            22: [2, 3, 3, 3, 2],
            23: [0, 1, 1, 1, 0],
            24: [3, 2, 2, 2, 3],
            25: [1, 1, 2, 3, 3],
            26: [2, 2, 1, 0, 0],
            27: [0, 2, 0, 2, 0],
            28: [3, 1, 3, 1, 3],
            29: [1, 3, 1, 3, 1],
            30: [2, 0, 2, 0, 2],
        }
        self.include_padding = True
        self.special_symbols = {
            "wild": ["W"],
            "scatter": ["BS"],
            "scatter_extreme": ["ES"],
            "character": ["C1", "C2", "C3"],
            "multiplier": ["C1", "C2", "C3"],
        }

        self.freespin_triggers = {self.basegame_type: {3: 8, 4: 10, 5: 12}}
        self.anticipation_triggers = {
            self.basegame_type: min(self.freespin_triggers[self.basegame_type].keys()) - 1,
        }

        # Smukiez feature constants
        self.extreme_direct_count = 2  # ES symbols needed to trigger Extreme Bonus directly
        self.extreme_direct_spins = 10
        self.paint_bonus_base = 1  # +1x per painted reel crossed by a win (base game + standard bonus)
        self.paint_bonus_extreme = 2  # Extreme Bonus starts at +2x per painted reel
        self.paint_bonus_max_standard = 2  # Tag Meter can upgrade the paint bonus up to this
        self.paint_bonus_max_extreme = 3
        self.tag_meter_target_standard = 4  # winning spins needed to fill the Tag Meter
        self.tag_meter_target_extreme = 3
        self.tag_meter_extra_spins = 2
        self.tag_meter_max_extra_spins = 6  # bound on meter-awarded spins per bonus
        self.char_mult_cap = 128  # combined character-multiplier ceiling per spin

        # Reels
        reels = {
            "BR0": "BR0.csv",  # base game
            "BRE": "BRE.csv",  # base game with Phantom (extreme) scatters present
            "FR0": "FR0.csv",  # standard bonus free spins
            "FRE": "FRE.csv",  # extreme bonus free spins
            "FRWCAP": "FRWCAP.csv",  # drip/character-rich strip for wincap simulations
        }
        self.reels = {}
        for r, f in reels.items():
            self.reels[r] = self.read_reels_csv(os.path.join(self.reels_path, f))

        self.padding_reels = {
            "basegame": self.reels["BR0"],
            "freegame": self.reels["FR0"],
        }

        # Character multiplier value tables, drawn per landed symbol
        char_mults_base = {
            "C1": {2: 70, 3: 30},
            "C2": {5: 100},
            "C3": {8: 75, 10: 25},
        }
        char_mults_free = {
            "C1": {2: 55, 3: 45},
            "C2": {5: 100},
            "C3": {8: 60, 10: 40},
        }
        char_mults_rich = {
            "C1": {3: 100},
            "C2": {5: 100},
            "C3": {10: 100},
        }

        # Injected-drip counts per free spin. Painting is cumulative and irreversible, so
        # these rates dominate bonus volatility and the Full Wall frequency: the standard
        # bonus averages ~1 painted reel, the extreme bonus ~2-3 (plus carried drips).
        # Free-spin strips hold no W; every free-spin drip comes from these tables.
        drips_standard = {0: 93, 1: 6, 2: 1}
        drips_extreme = {0: 90, 1: 7, 2: 2, 3: 1}
        drips_wincap = {1: 10, 2: 40, 3: 35, 4: 15}

        self.bet_modes = [
            BetMode(
                name="base",
                cost=1.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=self.wincap,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BRE": 1},
                                self.freegame_type: {"FRWCAP": 1},
                            },
                            "char_mult_values": {
                                self.basegame_type: char_mults_base,
                                self.freegame_type: char_mults_rich,
                            },
                            "landing_drips": drips_wincap,
                            "scatter_triggers": {3: 1, 4: 2},
                            "extreme_trigger_style": {"direct": 50, "upgrade": 50},
                            "force_wincap": True,
                            "force_freegame": True,
                            "force_extreme": True,
                        },
                    ),
                    Distribution(
                        criteria="extremegame",
                        quota=0.02,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BRE": 1},
                                self.freegame_type: {"FRE": 1},
                            },
                            "char_mult_values": {
                                self.basegame_type: char_mults_base,
                                self.freegame_type: char_mults_free,
                            },
                            "landing_drips": drips_extreme,
                            "scatter_triggers": {3: 75, 4: 25},
                            "extreme_trigger_style": {"direct": 60, "upgrade": 40},
                            "force_wincap": False,
                            "force_freegame": True,
                            "force_extreme": True,
                        },
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.07,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1},
                            },
                            "char_mult_values": {
                                self.basegame_type: char_mults_base,
                                self.freegame_type: char_mults_free,
                            },
                            "landing_drips": drips_standard,
                            "scatter_triggers": {3: 80, 4: 15, 5: 5},
                            "force_wincap": False,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="0",
                        quota=0.35,
                        win_criteria=0.0,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "char_mult_values": {self.basegame_type: char_mults_base},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=0.559,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "char_mult_values": {self.basegame_type: char_mults_base},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                ],
            ),
            BetMode(
                name="bonus",
                cost=100.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.002,
                        win_criteria=self.wincap,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FRWCAP": 1},
                            },
                            "char_mult_values": {
                                self.basegame_type: char_mults_base,
                                self.freegame_type: char_mults_rich,
                            },
                            "landing_drips": drips_wincap,
                            "scatter_triggers": {3: 1, 4: 2, 5: 1},
                            "force_wincap": True,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.998,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1},
                            },
                            "char_mult_values": {
                                self.basegame_type: char_mults_base,
                                self.freegame_type: char_mults_free,
                            },
                            "landing_drips": drips_standard,
                            "scatter_triggers": {3: 70, 4: 20, 5: 10},
                            "force_wincap": False,
                            "force_freegame": True,
                        },
                    ),
                ],
            ),
            BetMode(
                name="extremebonus",
                cost=400.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.005,
                        win_criteria=self.wincap,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BRE": 1},
                                self.freegame_type: {"FRWCAP": 1},
                            },
                            "char_mult_values": {
                                self.basegame_type: char_mults_base,
                                self.freegame_type: char_mults_rich,
                            },
                            "landing_drips": drips_wincap,
                            "scatter_triggers": {3: 1, 4: 2},
                            "extreme_trigger_style": {"direct": 50, "upgrade": 50},
                            "force_wincap": True,
                            "force_freegame": True,
                            "force_extreme": True,
                        },
                    ),
                    Distribution(
                        criteria="extremegame",
                        quota=0.995,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BRE": 1},
                                self.freegame_type: {"FRE": 1},
                            },
                            "char_mult_values": {
                                self.basegame_type: char_mults_base,
                                self.freegame_type: char_mults_free,
                            },
                            "landing_drips": drips_extreme,
                            "scatter_triggers": {3: 75, 4: 25},
                            "extreme_trigger_style": {"direct": 60, "upgrade": 40},
                            "force_wincap": False,
                            "force_freegame": True,
                            "force_extreme": True,
                        },
                    ),
                ],
            ),
        ]
