"""Handles the state and output for a single Smukiez Tag Run simulation round."""

from game_override import GameStateOverride
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
        """Cascade pipeline for one spin. Clusters first, then the Multis, then one tumble.

        1. Every cluster on the board is evaluated and paid - through whatever multipliers
           already sit on its cells - and its symbols are flagged to leave.
        2. Only then does any Multi on that board blow out: it and its four edge-neighbours
           are flagged and pick up its value. A Multi landing next to a winning cluster can
           therefore never blow the cluster away unpaid; its value benefits the clusters
           that form after the refill.
        3. Everything flagged leaves in ONE tumble and the refill lands on the values.
        Repeat until a board pays nothing and holds no Multi, the wincap trips, or the
        spin's tumble budget runs out.
        """
        tumbles = 0
        while True:
            self.evaluate_smukiez_wins()
            exploded = self._pay_and_mark_tumble()          # the clusters, paid, before anything moves
            if self.wincap_triggered:
                break
            if tumbles >= self.config.max_tumbles_per_spin:
                break                                        # budget spent: no more pays this spin
            boosted = self.mark_boosters()                   # now the Multis go off
            if not exploded and not boosted:
                break
            self.tumble_flagged()                            # paid symbols + blast cells, one drop
            tumbles += 1
        # If the budget ran out with a Multi still on the board it would sit there as a tile
        # that never blows out. Let it go off - a few extra board changes at most - so what the
        # player sees is what happened; in a bonus the values it leaves carry into the next
        # spin. The symbols of the last paid clusters are still flagged, so they leave with the
        # blast (the event lists them). Nothing paid after this point in the spin.
        if not self.wincap_triggered:
            self.settle_boosters(tumbles, cap=self.config.max_tumbles_per_spin + 4)
        self.set_end_tumble_event()           # final setWin / setTotalWin for the cascade sequence

    def _pay_and_mark_tumble(self) -> bool:
        """Record + emit this board's cluster wins, flag every winning symbol to explode.
        Returns True if at least one symbol was flagged (i.e. the board will change)."""
        if self.win_data["totalWin"] <= 0:
            return False
        self.record_smukiez_wins()
        self.win_manager.update_spinwin(self.win_data["totalWin"])
        win_info_event(self)
        update_tumble_win_event(self)
        self.evaluate_wincap()
        # Only flag here. tumble_flagged() lists every flagged cell for the tumbleBoard event
        # at the moment of the tumble, so the Multi blast cells flagged after this join the
        # paid symbols in the same drop.
        any_exploded = False
        for win in self.win_data["wins"]:
            for pos in win["positions"]:
                self.board[pos["reel"]][pos["row"]].explode = True
                any_exploded = True
        return any_exploded
