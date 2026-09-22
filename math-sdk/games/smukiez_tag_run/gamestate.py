"""Handles the state and output for a single Smukiez Tag Run simulation round."""

from game_override import GameStateOverride
from src.calculations.lines import Lines
from src.events.events import reveal_event, win_info_event, update_tumble_win_event


class GameState(GameStateOverride):
    """Handle game logic and event emission for a given simulation number."""

    def run_spin(self, sim, simulation_seed=None):
        """Entry point for all game modes."""
        self.reset_seed(sim, simulation_seed)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            self.draw_board(emit_event=False)
            reveal_event(self)

            self.evaluate_and_emit_wins()
            self.win_manager.update_gametype_wins(self.gametype)

            trigger = None
            if not self.repeat:
                trigger = self.check_smukiez_triggers()
            if trigger is not None:
                self.run_smukiez_freespin_entry(trigger)

            self.evaluate_finalwin()
            self.check_repeat()

        self.imprint_wins()

    def run_freespin(self):
        """Free spin loop shared by the Standard and Extreme Bonus (profile set on entry)."""
        self.reset_fs_spin()
        self.tag_meter = 0
        self.extra_spins_awarded = 0
        # In the bonus the multipliers a Multi leaves behind stay on their cells for every
        # spin that follows, so the board fills with them as the feature goes on and the
        # late spins pay through everything the early ones laid down. The base game wipes
        # them each spin (reset_book). This is what makes a bonus spin worth more than a
        # base spin now that the sticky paint is gone.
        self.reset_grid_mults()

        while self.fs < self.tot_fs and not self.wincap_triggered:
            self.update_freespin()
            self.draw_board(emit_event=False)
            reveal_event(self)

            self.evaluate_and_emit_wins()
            self.win_manager.update_gametype_wins(self.gametype)
            if not self.wincap_triggered:   # the round is over at the cap; no meter after it
                self.update_tag_meter()

        self.end_freespin()

    def evaluate_and_emit_wins(self):
        """Cascade pipeline for one spin.

        1. Any Multi on the board blows out first: it and its four edge-neighbours are
           cleared, their cells pick up its multiplier, the board refills. The refill can
           land another Multi, so this repeats until none is left.
        2. Lines are evaluated on the settled board, paid, and the winning symbols explode.
        3. The board refills, Multis are settled again, lines again - until a reveal pays
           nothing, the wincap trips, or the spin's tumble budget runs out.
        """
        tumbles = self.settle_boosters(0)
        self.evaluate_smukiez_wins()
        exploded = self._pay_and_mark_tumble()
        while (self.win_data["totalWin"] > 0 and exploded and not self.wincap_triggered
               and tumbles < self.config.max_tumbles_per_spin):
            self.tumble_game_board()          # remove exploded symbols, refill from the strip, emit tumbleBoard
            tumbles += 1
            tumbles = self.settle_boosters(tumbles)
            self.evaluate_smukiez_wins()
            exploded = self._pay_and_mark_tumble()
        # If the budget ran out with a Multi still on the board it would sit there as a tile
        # that never blows out. Let it go off - a few extra board changes at most - so what the
        # player sees is what happened; in a bonus the values it leaves carry into the next
        # spin. No more wins are paid this spin.
        if not self.wincap_triggered:
            self.settle_boosters(tumbles, cap=self.config.max_tumbles_per_spin + 4)
        self.set_end_tumble_event()           # final setWin / setTotalWin for the cascade sequence

    def _pay_and_mark_tumble(self) -> bool:
        """Record + emit this reveal's wins, flag every winning symbol to explode.
        Returns True if at least one symbol was flagged (i.e. the board will change)."""
        if self.win_data["totalWin"] <= 0:
            return False
        Lines.record_lines_wins(self)
        self.win_manager.update_spinwin(self.win_data["totalWin"])
        win_info_event(self)
        update_tumble_win_event(self)
        self.evaluate_wincap()
        # Record exactly which cells we flag, in the win-position row space, so the tumbleBoard
        # event lists precisely these (the SDK's shallow-copied board_before_tumble can't be
        # trusted to re-derive them - its inner reels are mutated during refill).
        any_exploded = False
        seen = set()
        self.tumble_explode_positions = []
        for win in self.win_data["wins"]:
            for pos in win["positions"]:
                self.board[pos["reel"]][pos["row"]].explode = True
                any_exploded = True
                key = (pos["reel"], pos["row"])
                if key not in seen:
                    seen.add(key)
                    self.tumble_explode_positions.append({"reel": pos["reel"], "row": pos["row"]})
        return any_exploded
