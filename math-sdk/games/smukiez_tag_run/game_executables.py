"""Executables for Smukiez Tag Run: drip expansion/painting, bonus triggers,
extreme-board forcing, the Tag Meter, and the Full Wall award."""

import random
from game_calculations import GameCalculations
from game_events import (
    paint_drips_event,
    painted_wall_event,
    tag_meter_event,
    tag_meter_full_event,
    full_wall_event,
    extreme_trigger_event,
)
from src.calculations.statistics import get_random_outcome
from src.events.events import (
    reveal_event,
    fs_trigger_event,
    enter_bonus_event,
    set_total_event,
)


class GameExecutables(GameCalculations):
    """Executable functions for paint, trigger, and bonus mechanics."""

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

    # ------------------------------------------------------------------ paint drips
    def find_natural_drips(self) -> list:
        """Unpainted reels where a Paint Drip landed from the reelstrip (one origin per reel)."""
        drips = []
        for reel, _ in enumerate(self.board):
            if reel in self.painted_reels:
                continue
            for row, sym in enumerate(self.board[reel]):
                if sym.name == "W":
                    drips.append({"reel": reel, "row": row})
                    break
        return drips

    def inject_freespin_drips(self) -> list:
        """Distribution-driven extra drips landing on unpainted reels during free spins."""
        conds = self.get_current_distribution_conditions()
        num_drips = get_random_outcome(conds["landing_drips"])
        new_drips = []
        unpainted = [r for r in range(self.config.num_reels) if r not in self.painted_reels]
        random.shuffle(unpainted)
        for reel in unpainted[:num_drips]:
            open_rows = [
                row
                for row in range(self.config.num_rows[reel])
                if not self.board[reel][row].check_attribute("character", "scatter", "scatter_extreme")
            ]
            if not open_rows:
                continue
            row = random.choice(open_rows)
            self.board[reel][row] = self.create_symbol("W")
            new_drips.append({"reel": reel, "row": row})
        return new_drips

    def expand_painted_reels(self) -> None:
        """Fill every painted reel with wilds, painting around scatters and characters."""
        for reel in self.painted_reels:
            for row, sym in enumerate(self.board[reel]):
                if not sym.check_attribute("character", "scatter", "scatter_extreme"):
                    self.board[reel][row] = self.create_symbol("W")
        self.get_special_symbols_on_board()

    def apply_base_drips(self) -> list:
        """Expand drips that landed on the base-game reveal; reels stay painted for this spin."""
        new_drips = self.find_natural_drips()
        for drip in new_drips:
            self.painted_reels.append(drip["reel"])
        if new_drips:
            self.expand_painted_reels()
        return new_drips

    # ------------------------------------------------------------------ bonus triggers
    def check_smukiez_triggers(self):
        """Return 'extreme', 'standard', or None for the current base board.

        Extreme: 2+ Phantoms directly, or a standard scatter trigger with 1+ Phantom.
        Triggers the current distribution did not ask for force a resimulation.
        """
        n_bs = self.count_special_symbols("scatter")
        n_es = self.count_special_symbols("scatter_extreme")
        min_bs = min(self.config.freespin_triggers[self.gametype].keys())
        conds = self.get_current_distribution_conditions()

        trigger = None
        if n_es >= self.config.extreme_direct_count:
            trigger = "extreme"
            self.bonus_type = "extreme_direct"
            self.tot_fs = self.config.extreme_direct_spins
        elif n_bs >= min_bs and n_es >= 1:
            trigger = "extreme"
            self.bonus_type = "extreme_upgrade"
            self.tot_fs = self.config.freespin_triggers[self.gametype][n_bs]
        elif n_bs >= min_bs:
            trigger = "standard"
            self.bonus_type = "standard"
            self.tot_fs = self.config.freespin_triggers[self.gametype][n_bs]

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

        if trigger == "extreme":
            # painted reels from the triggering spin carry into the Extreme Bonus
            self.paint_level = self.config.paint_bonus_extreme
            self.paint_max = self.config.paint_bonus_max_extreme
            self.tag_target = self.config.tag_meter_target_extreme
        else:
            self.painted_reels = []
            self.paint_level = self.config.paint_bonus_base
            self.paint_max = self.config.paint_bonus_max_standard
            self.tag_target = self.config.tag_meter_target_standard
        self.run_freespin()

    # ------------------------------------------------------------------ tag meter / full wall
    def update_tag_meter(self) -> None:
        """A winning free spin adds a tag; a full meter adds spins and upgrades the paint bonus."""
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
            if self.paint_level < self.paint_max:
                self.paint_level += 1
            tag_meter_full_event(self, extra_spins)

    def award_full_wall(self) -> None:
        """All 5 reels painted: complete the mural and pay up to the max win."""
        self.full_wall_awarded = True
        remaining = max(round(self.config.wincap - self.win_manager.running_bet_win, 2), 0)
        self.win_manager.update_spinwin(remaining)
        self.win_manager.update_gametype_wins(self.gametype)
        full_wall_event(self)
        self.evaluate_wincap()
        set_total_event(self)
