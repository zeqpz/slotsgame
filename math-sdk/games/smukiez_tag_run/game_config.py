"""Smukiez Tag Run - game configuration: symbols, cluster paytable, bet modes.

Symbol legend (art layer maps these ids to final art):
    M   Multi             the booster (1.25x .. 1000x). It lands, blows out itself and the four cells that
                          share an edge with it, leaves its multiplier on each of those
                          five cells, and new symbols drop in. A cluster covering
                          multiplied cells is multiplied by the SUM of the values on those
                          cells. Two Multis reaching the same cell add. Pays nothing itself.
    BS  Crew Leader       bonus scatter: 3/4/5 -> 8/10/12 free spins
    ES  The Phantom       extreme scatter: 2 = direct Extreme Bonus, 1 + standard trigger = upgrade
    H1  Bag of Cash   H2  Cartoon Glock   H3  Gold Chain   H4  Fresh Kicks   H5  Boombox
    H6  Skateboard    H7  Limited Drop Box
    L1  Spray Can     L2  Graffiti Markers L3 Smukiez Beanie L4 Custom Hangtag L5 Dice
    L6  Smukiez Shirt L7  Hoodie           L8 Bag of Weed    L9 Freight Train  L10 Brick Wall Chunk

Wall events (v5, owner 2026-10-25): far more Multis (walls) land, most of them teasers; now
and then a straight line of 3 or 4 walls drops in together, and very rarely - an outcome of
its own that the optimiser places - the whole board is covered in walls. Every winning
cluster also drops small multipliers (x1.25-x2) on some of its own cells. Max win 10,000x.

Gone since v2: the Paint Drip wild and the painted-reel colour bonus, the Full Wall mural
award, and the C1/C2/C3 characters with their spin multipliers. Gone in v5: the Tag Meter
and its extra spins - the bonus drops more walls instead.
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
        self.wincap = 10000.0
        self.win_type = "cluster"
        self.rtp = 0.967   # the top of the SDK's 3-star volatility band (rgs_verification: rtp <= 0.967)
        self.construct_paths()

        # Game dimensions: a 7x7 cluster board
        self.num_reels = 7
        self.num_rows = [7] * self.num_reels

        # Max board changes (cascades) within a single spin. Each pass of the cascade loop is
        # one: a board's paid clusters and any Multi blow-outs on it leave in the same tumble.
        # Without a cap a spin can chain for a very long time
        # toward the wincap, which bloats the book past what the RGS will ingest and buries
        # the player in an endless tumble.
        self.max_tumbles_per_spin = 12

        # Paytable: (cluster size, symbol) -> payout in total-bet multiples, per cluster.
        # Six size tiers: 5 | 6 | 7-8 | 9-11 | 12-15 | 16+ (up to the whole 49-cell board).
        # Every value is a multiple of 0.4: a cluster times any SUM of Multi values (multiples
        # of 0.25) then lands exactly on a tenth of the bet, the only granularity the RGS
        # accepts. The Multi is what makes them big; a bare cluster is a nudge.
        t5, t6, t7, t9, t12, t16 = (5, 5), (6, 6), (7, 8), (9, 11), (12, 15), (16, 49)
        tiers = (t5, t6, t7, t9, t12, t16)
        cluster_pays = {
            "H1": (4.0, 8.0, 16.0, 40.0, 100.0, 400.0),
            "H2": (3.2, 6.0, 12.0, 30.0, 80.0, 300.0),
            "H3": (2.4, 4.8, 10.0, 24.0, 60.0, 200.0),
            "H4": (2.0, 4.0, 8.0, 20.0, 48.0, 160.0),
            "H5": (1.6, 3.2, 6.4, 16.0, 40.0, 120.0),
            "H6": (1.6, 3.2, 6.4, 16.0, 40.0, 120.0),
            "H7": (1.2, 2.4, 4.8, 12.0, 32.0, 100.0),
            "L1": (0.8, 1.6, 3.2, 8.0, 20.0, 60.0),
            "L2": (0.8, 1.6, 3.2, 8.0, 20.0, 60.0),
            "L3": (0.8, 1.2, 2.4, 6.0, 16.0, 48.0),
            "L4": (0.4, 1.2, 2.4, 6.0, 16.0, 48.0),
            "L5": (0.4, 0.8, 2.0, 4.8, 12.0, 40.0),
            "L6": (0.4, 0.8, 2.0, 4.8, 12.0, 40.0),
            "L7": (0.4, 0.8, 1.6, 4.0, 10.0, 32.0),
            "L8": (0.4, 0.8, 1.6, 4.0, 10.0, 32.0),
            "L9": (0.4, 0.8, 1.2, 3.2, 8.0, 24.0),
            "L10": (0.4, 0.8, 1.2, 3.2, 8.0, 24.0),
        }
        pay_group = {}
        for sym, pays in cluster_pays.items():
            for tier, pay in zip(tiers, pays):
                pay_group[(tier, sym)] = pay
        self.paytable = self.convert_range_table(pay_group)

        self.include_padding = True
        # Wins are clusters: five or more of a kind touching side to side, anywhere on the
        # 7x7 board (win_type "cluster"; there are no paylines).
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

        # Wall events. A wall line: a straight row or column of 3 or 4 walls landing together,
        # a chance on every reveal - rarely in the base game, often in a bonus, which drops
        # walls where it used to give spins. Adjacent walls' blasts overlap, so a line leaves
        # a strip of stacked values behind it.
        self.wall_line_chance = {self.basegame_type: 1 / 40, self.freegame_type: 1 / 6}
        self.wall_line_lengths = {3: 70, 4: 30}
        # The board cover: every cell but a scatter turns to a wall at once - each cell ends up
        # the sum of its own value and up to four neighbours', and the whole board refills on
        # top of them: the base game's jackpot, a four-figure win on average. Only in the base
        # game, and only in the outcomes forced for it (criteria "wallcover"), so the optimiser
        # sets how rare it is.
        self.cover_mult_values = {5: 30, 10: 30, 20: 25, 50: 12, 100: 3}
        # Line drops: every winning cluster leaves small multipliers on some of its own cells -
        # one per five symbols it held - under the tiles, for the refill to land on. They add to
        # whatever the cell holds, like a wall's, and last as a wall's do (the spin in the base
        # game, the whole bonus in free spins).
        self.line_drop_per = 5
        self.line_drop_values = {1.25: 60, 1.5: 25, 2: 15}

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
        # cluster times any SUM of values lands exactly on a tenth of the bet - the only
        # granularity the RGS accepts - with nothing rounded and nothing shown that is not
        # exactly what was paid. That is why the floor is 1.25x and not 1.2x.
        # v5: three times the walls, so a wall is mostly a small teaser while the 500x and 1000x
        # keep turning up - a sight far more often than a win. The 1000x is one wall in ~1,800
        # (owner, 2026-10-25: about one base spin in 1,500 once the books are weighted;
        # tools/finish_luts.py holds it there and keeps any one such board from repeating), and
        # it is nearly always a teaser: the books where it pays are the ones the optimiser keeps
        # rarest.
        booster_mults_base = {
            1.25: 480, 1.5: 280, 2: 150, 3: 60, 5: 22, 10: 7, 20: 3,
            50: 1.2, 100: 0.5, 250: 0.22, 500: 0.12, 1000: 0.55,
        }
        # in a bonus the values persist and stack across spins, with the line drops on top of
        # them: the standard bonus averages ~3.4x a wall, the extreme ~5.7x, every one 2x or more
        booster_mults_free = {
            1.25: 300, 1.5: 240, 2: 220, 3: 150, 5: 80, 10: 35, 20: 14,
            50: 5, 100: 2, 250: 0.7, 500: 0.3, 1000: 0.15,
        }
        booster_mults_extreme = {
            2: 320, 3: 260, 5: 160, 10: 70, 20: 25, 50: 8,
            100: 3, 250: 1, 500: 0.45, 1000: 0.22,
        }
        # wincap simulations only: the strip is dense with Multis and every one is huge, so
        # the 10,000x is reached in a handful of cascades instead of a thousand resimulations
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
                        # the board cover: forced on the reveal, so how often a player sees one
                        # is the optimiser's call (game_optimization: hr for "wallcover")
                        criteria="wallcover",
                        quota=0.002,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "booster_mult_values": {self.basegame_type: booster_mults_base},
                            "force_wincap": False,
                            "force_freegame": False,
                            "force_cover": True,
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
                        quota=0.5578,
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
