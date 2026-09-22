"""Executables for Smukiez Tag Run: the Multi booster, bonus triggers, extreme-board
forcing, and the Tag Meter."""

import random
from game_calculations import GameCalculations
from game_events import (
    booster_event,
    tag_meter_event,
    tag_meter_full_event,
    extreme_trigger_event,
)
from src.calculations.cluster import Cluster
from src.calculations.statistics import get_random_outcome
from src.events.events import (
    reveal_event,
    fs_trigger_event,
    enter_bonus_event,
)


class GameExecutables(GameCalculations):
    """Executable functions for the booster, trigger, and bonus mechanics."""

    # ------------------------------------------------------------------ board / forcing
    def draw_board(self, emit_event: bool = True, trigger_symbol: str = "scatter") -> None:
        """Extend the engine draw to force Extreme Bonus boards when the criteria demands it."""
        conds = self.get_current_distribution_conditions()
        if self.gametype == self.config.basegame_type and conds.get("force_extreme", False):
            style = get_random_outcome(conds["extreme_trigger_style"])
            if style == "direct":
                n_bs = get_random_outcome({0: 60, 1: 25, 2: 15})
                self.force_smukiez_board(n_bs, self.config.extreme_direct_count)
            else:
                n_bs = get_random_outcome(conds["scatter_triggers"])
                self.force_smukiez_board(n_bs, 1)
            if emit_event:
                reveal_event(self)
        else:
            super().draw_board(emit_event, trigger_symbol)

    def force_smukiez_board(self, n_bs: int, n_es: int) -> None:
        """Force a base board holding exactly n_bs Crew Leader and n_es Phantom scatters."""
        conds = self.get_current_distribution_conditions()
        reelstrip_id = get_random_outcome(conds["reel_weights"][self.gametype])
        bs_stops = self.get_syms_on_reel(reelstrip_id, "scatter")
        es_stops = self.get_syms_on_reel(reelstrip_id, "scatter_extreme")
        es_reels = [r for r in range(self.config.num_reels) if len(es_stops[r]) > 0]
        assert len(es_reels) >= n_es, f"strip {reelstrip_id} does not hold ES on {n_es} reels"

        for _ in range(100):
            force_positions = {}
            for r in random.sample(es_reels, n_es):
                force_positions[r] = random.choice(es_stops[r])
            bs_reels = [
                r for r in range(self.config.num_reels) if len(bs_stops[r]) > 0 and r not in force_positions
            ]
            if len(bs_reels) < n_bs:
                continue
            for r in random.sample(bs_reels, n_bs):
                force_positions[r] = random.choice(bs_stops[r])

            self.force_board_from_reelstrips(reelstrip_id, dict(sorted(force_positions.items())))
            if (
                self.count_special_symbols("scatter") == n_bs
                and self.count_special_symbols("scatter_extreme") == n_es
            ):
                return
        raise RuntimeError(f"could not force extreme board ({n_bs} BS, {n_es} ES) on {reelstrip_id}")

    # ------------------------------------------------------------------ the Multi
    def find_boosters(self) -> list:
        """Every Multi on the visible board, as (reel, row)."""
        return [
            (reel, row)
            for reel, column in enumerate(self.board)
            for row, sym in enumerate(column)
            if sym.check_attribute("booster")
        ]

    def mark_boosters(self) -> bool:
        """Blow out every Multi on the board and leave its multiplier behind.

        Each Multi takes itself and the four cells sharing an edge with it. Those cells get
        the Multi's value ADDED to whatever they already carry and are flagged to leave, so
        the refill lands on top of the multipliers. Scatters are immune: a bonus that has
        just landed must not be blown off the board by the thing that landed next to it.

        This only flags and emits the booster event; it never tumbles. The caller takes
        everything flagged - the symbols of the lines it has just paid AND these blast cells
        - off the board in one tumble, so a Multi can never remove a line before it pays.
        Returns True if anything was flagged.
        """
        boosters = self.find_boosters()
        if not boosters:
            return False

        self.booster_details = []
        for reel, row in boosters:
            value = self.board[reel][row].get_attribute("multiplier")
            cells = [(reel, row)] + Cluster.get_neighbours(self.board, reel, row, [])
            hit = []
            for r, c in cells:
                target = self.board[r][c]
                if (r, c) != (reel, row) and target.check_attribute("scatter", "scatter_extreme"):
                    continue
                self.grid_mults[r][c] = round(self.grid_mults[r][c] + value, 2)
                target.explode = True
                hit.append({"reel": r, "row": c})
            self.booster_details.append({"reel": reel, "row": row, "mult": value, "cells": hit})

        booster_event(self)
        return True

    def flagged_positions(self) -> list:
        """Every visible cell whose symbol is flagged to leave, reel-major, win-position rows."""
        return [
            {"reel": r, "row": c}
            for r, column in enumerate(self.board)
            for c, sym in enumerate(column)
            if sym.explode
        ]

    def tumble_flagged(self) -> None:
        """Take every flagged symbol off the board in ONE tumble.

        The tumbleBoard event lists exactly the cells flagged right now (the SDK's
        shallow-copied board_before_tumble can't be trusted to re-derive them - its inner
        reels are mutated during the refill), so paid line symbols and Multi blast cells
        leave together and the client sees one drop.
        """
        self.tumble_explode_positions = self.flagged_positions()
        self.tumble_game_board()

    def resolve_boosters(self) -> bool:
        """Blow out the Multis and tumble the result: one board change per pass."""
        if not self.mark_boosters():
            return False
        self.tumble_flagged()
        return True

    def settle_boosters(self, tumbles: int, cap: int = None) -> int:
        """Resolve Multis until none are left on the board, within the spin's tumble budget."""
        cap = self.config.max_tumbles_per_spin if cap is None else cap
        while tumbles < cap and self.resolve_boosters():
            tumbles += 1
        return tumbles

    # ------------------------------------------------------------------ bonus triggers
    def check_smukiez_triggers(self):
        """Return 'extreme', 'standard', or None for the current base board.

        Extreme: 2+ Phantoms directly, or a standard scatter trigger with 1+ Phantom.
        Triggers the current distribution did not ask for force a resimulation.
        """
        n_bs = self.count_special_symbols("scatter")
        n_es = self.count_special_symbols("scatter_extreme")
        trig_map = self.config.freespin_triggers[self.gametype]
        min_bs = min(trig_map.keys())
        # cascades can accumulate more scatters than the table defines - cap at the top tier
        bs_key = min(n_bs, max(trig_map.keys()))
        conds = self.get_current_distribution_conditions()

        trigger = None
        if n_es >= self.config.extreme_direct_count:
            trigger = "extreme"
            self.bonus_type = "extreme_direct"
            self.tot_fs = self.config.extreme_direct_spins
        elif n_bs >= min_bs and n_es >= 1:
            trigger = "extreme"
            self.bonus_type = "extreme_upgrade"
            self.tot_fs = trig_map[bs_key]
        elif n_bs >= min_bs:
            trigger = "standard"
            self.bonus_type = "standard"
            self.tot_fs = trig_map[bs_key]

        if trigger is None:
            return None
        if trigger == "extreme" and not conds.get("force_extreme", False):
            self.repeat = True
            return None
        if trigger == "standard" and (not conds["force_freegame"] or conds.get("force_extreme", False)):
            self.repeat = True
            return None

        self.triggered_extreme = trigger == "extreme"
        if n_es > 0:
            self.record({"kind": n_es, "symbol": "scatter_extreme", "gametype": self.gametype})
        if n_bs >= min_bs:
            self.record({"kind": n_bs, "symbol": "scatter", "gametype": self.gametype})
        return trigger

    def run_smukiez_freespin_entry(self, trigger: str) -> None:
        """Emit trigger events, set the bonus profile, and run the free spins."""
        fs_trigger_event(self, basegame_trigger=True, freegame_trigger=False)
        if trigger == "extreme":
            extreme_trigger_event(self)
        enter_bonus_event(self)
        self.tag_target = (
            self.config.tag_meter_target_extreme if trigger == "extreme" else self.config.tag_meter_target_standard
        )
        self.run_freespin()

    # ------------------------------------------------------------------ tag meter
    def update_tag_meter(self) -> None:
        """A winning free spin adds a tag; a full meter adds spins."""
        if self.win_manager.spin_win <= 0:
            return
        self.tag_meter += 1
        tag_meter_event(self)
        if self.tag_meter >= self.tag_target:
            self.tag_meter = 0
            extra_spins = 0
            if self.extra_spins_awarded < self.config.tag_meter_max_extra_spins:
                extra_spins = self.config.tag_meter_extra_spins
                self.tot_fs += extra_spins
                self.extra_spins_awarded += extra_spins
            tag_meter_full_event(self, extra_spins)
