"""Smukiez Tag Run - game configuration: symbols, paytable, paylines, bet modes.

Symbol legend (art layer maps these ids to final art):
    M   Multi             the booster (1.25x .. 1000x). It lands, blows out itself and the four cells that
                          share an edge with it, leaves its multiplier on each of those
                          five cells, and new symbols drop in. A line paying through
                          multiplied cells is multiplied by the SUM of the values on its
                          cells. Two Multis reaching the same cell add. Pays nothing itself.
    BS  Crew Leader       bonus scatter: 3/4/5 -> 8/10/12 free spins
    ES  The Phantom       extreme scatter: 2 = direct Extreme Bonus, 1 + standard trigger = upgrade
    H1  Bag of Cash   H2  Cartoon Glock   H3  Gold Chain   H4  Fresh Kicks   H5  Boombox
    H6  Skateboard    H7  Limited Drop Box
    L1  Spray Can     L2  Graffiti Markers L3 Smukiez Beanie L4 Custom Hangtag L5 Dice
    L6  Smukiez Shirt L7  Hoodie           L8 Bag of Weed    L9 Freight Train  L10 Brick Wall Chunk

Gone since v2: the Paint Drip wild and the painted-reel colour bonus, the Full Wall mural
award, and the C1/C2/C3 characters with their spin multipliers. The Tag Meter stays for its
extra spins only.
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

        # Max board changes (cascades) within a single spin. A Multi blowing out counts as one,
        # a winning tumble counts as one. Without a cap a spin can chain for a very long time
        # toward the wincap, which bloats the book past what the RGS will ingest and buries
        # the player in an endless tumble.
        self.max_tumbles_per_spin = 12

        # Paytable: (kind, symbol): payout in total-bet multiples, paid per line.
        # There is no wild any more, so lines hit less often and cascades run shorter than
        # they did with sticky paint; the pays are four times the v2 cascade table to carry
        # that. The Multi is what makes them big.
        self.paytable = {
            (5, "H1"): 4.8, (4, "H1"): 2, (3, "H1"): 0.8,
            (5, "H2"): 4, (4, "H2"): 1.6, (3, "H2"): 0.8,
            (5, "H3"): 3.2, (4, "H3"): 1.2, (3, "H3"): 0.4,
            (5, "H4"): 2.4, (4, "H4"): 1.2, (3, "H4"): 0.4,
            (5, "H5"): 2, (4, "H5"): 0.8, (3, "H5"): 0.4,
            (5, "H6"): 2, (4, "H6"): 0.8, (3, "H6"): 0.4,
            (5, "H7"): 1.6, (4, "H7"): 0.8, (3, "H7"): 0.4,
            (5, "L1"): 1.2, (4, "L1"): 0.8, (3, "L1"): 0.4,
            (5, "L2"): 1.2, (4, "L2"): 0.4, (3, "L2"): 0.4,
            (5, "L3"): 0.8, (4, "L3"): 0.4, (3, "L3"): 0.4,
            (5, "L4"): 0.8, (4, "L4"): 0.4, (3, "L4"): 0.4,
            (5, "L5"): 0.8, (4, "L5"): 0.4, (3, "L5"): 0.4,
            (5, "L6"): 0.8, (4, "L6"): 0.4, (3, "L6"): 0.4,
            (5, "L7"): 0.4, (4, "L7"): 0.4, (3, "L7"): 0.4,
            (5, "L8"): 0.4, (4, "L8"): 0.4, (3, "L8"): 0.4,
            (5, "L9"): 0.4, (4, "L9"): 0.4, (3, "L9"): 0.4,
            (5, "L10"): 0.4, (4, "L10"): 0.4, (3, "L10"): 0.4,
        }

        # 30 fixed paylines on the 5x4 board (row index per reel, 0 = top)
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
        # "multiplier" gives the Multi its value slot (rolled when it lands) and puts that
        # value into every reveal/tumble event, so the client can show it on the tile.
        # "booster" is what the game logic looks for. There is no wild in this game.
        self.special_symbols = {
            "wild": [],
            "scatter": ["BS"],
            "scatter_extreme": ["ES"],
            "booster": ["M"],
            "multiplier": ["M"],
        }

        self.freespin_triggers = {self.basegame_type: {3: 10, 4: 12, 5: 15}}
        self.anticipation_triggers = {
            self.basegame_type: min(self.freespin_triggers[self.basegame_type].keys()) - 1,
        }

        # Smukiez feature constants
        self.extreme_direct_count = 2  # ES symbols needed to trigger Extreme Bonus directly
        self.extreme_direct_spins = 17
        self.tag_meter_target_standard = 4  # winning spins needed to fill the Tag Meter
        self.tag_meter_target_extreme = 3
        self.tag_meter_extra_spins = 3
        self.tag_meter_max_extra_spins = 9  # bound on meter-awarded spins per bonus

        # Reels
        reels = {
            "BR0": "BR0.csv",  # base game
            "BRE": "BRE.csv",  # base game with Phantom (extreme) scatters present
            "FR0": "FR0.csv",  # standard bonus free spins
            "FRE": "FRE.csv",  # extreme bonus free spins
            "FRWCAP": "FRWCAP.csv",  # Multi-rich free-spin strip for wincap simulations
        }
        self.reels = {}
        for r, f in reels.items():
            self.reels[r] = self.read_reels_csv(os.path.join(self.reels_path, f))

        self.padding_reels = {
            "basegame": self.reels["BR0"],
            "freegame": self.reels["FR0"],
        }

        # The Multi's value, rolled the moment it lands. Heavy at the bottom with a long,
        # thin tail up to 1000x: most Multis are a nudge, and once in a long while one is the
        # whole game. The optimiser decides how often Multi outcomes appear at all; these
        # tables only shape what a Multi is worth when it does.
        # Every value is a multiple of 0.25 and every paytable entry a multiple of 0.4, so a
        # line times any SUM of values lands exactly on a tenth of the bet - the only
        # granularity the RGS accepts - with nothing rounded and nothing shown that is not
        # exactly what was paid. That is why the floor is 1.25x and not 1.2x.
        booster_mults_base = {
            1.25: 300, 1.5: 240, 2: 200, 3: 130, 5: 70, 10: 35, 20: 14,
            50: 6, 100: 2.5, 250: 0.9, 500: 0.35, 1000: 0.15,
        }
        # in a bonus the values persist and stack across spins, so the tables lean richer:
        # the standard bonus averages ~8x a Multi, the extreme ~14x
        booster_mults_free = {
            1.25: 120, 1.5: 140, 2: 180, 3: 180, 5: 140, 10: 90, 20: 45,
            50: 20, 100: 8, 250: 3, 500: 1.2, 1000: 0.6,
        }
        booster_mults_extreme = {
            2: 130, 3: 170, 5: 190, 10: 150, 20: 85, 50: 38,
            100: 15, 250: 6, 500: 2.5, 1000: 1.2,
        }
        # wincap simulations only: the strip is dense with Multis and every one is huge, so
        # the 5000x is reached in a handful of cascades instead of a thousand resimulations
        booster_mults_rich = {1000: 100}

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
                        quota=0.0002,
                        win_criteria=self.wincap,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BRE": 1},
                                self.freegame_type: {"FRWCAP": 1},
                            },
                            "booster_mult_values": {
                                self.basegame_type: booster_mults_base,
                                self.freegame_type: booster_mults_rich,
                            },
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
                            "booster_mult_values": {
                                self.basegame_type: booster_mults_base,
                                self.freegame_type: booster_mults_extreme,
                            },
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
                            "booster_mult_values": {
                                self.basegame_type: booster_mults_base,
                                self.freegame_type: booster_mults_free,
                            },
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
                            "booster_mult_values": {self.basegame_type: booster_mults_base},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=0.5598,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "booster_mult_values": {self.basegame_type: booster_mults_base},
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
                        quota=0.0005,
                        win_criteria=self.wincap,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FRWCAP": 1},
                            },
                            "booster_mult_values": {
                                self.basegame_type: booster_mults_base,
                                self.freegame_type: booster_mults_rich,
                            },
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
                            "booster_mult_values": {
                                self.basegame_type: booster_mults_base,
                                self.freegame_type: booster_mults_free,
                            },
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
                        quota=0.001,
                        win_criteria=self.wincap,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BRE": 1},
                                self.freegame_type: {"FRWCAP": 1},
                            },
                            "booster_mult_values": {
                                self.basegame_type: booster_mults_base,
                                self.freegame_type: booster_mults_rich,
                            },
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
                            "booster_mult_values": {
                                self.basegame_type: booster_mults_base,
                                self.freegame_type: booster_mults_extreme,
                            },
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
