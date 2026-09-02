"""Handles the state and output for a single Smukiez Tag Run simulation round."""

from game_override import GameStateOverride
from game_events import paint_drips_event, painted_wall_event, character_mults_event
from src.calculations.lines import Lines
from src.events.events import reveal_event


class GameState(GameStateOverride):
    """Handle game logic and event emission for a given simulation number."""

    def run_spin(self, sim, simulation_seed=None):
        """Entry point for all game modes."""
        self.reset_seed(sim, simulation_seed)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            self.draw_board(emit_event=False)

            new_drips = self.apply_base_drips()
            reveal_event(self)
            if new_drips:
                paint_drips_event(self, new_drips)
                painted_wall_event(self)

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
        painted_wall_event(self)

        while self.fs < self.tot_fs and not self.wincap_triggered:
            self.update_freespin()
            self.draw_board(emit_event=False)

            natural_drips = self.find_natural_drips()
            for drip in natural_drips:
                self.painted_reels.append(drip["reel"])
            injected_drips = self.inject_freespin_drips()
            for drip in injected_drips:
                self.painted_reels.append(drip["reel"])
            new_drips = natural_drips + injected_drips
            self.expand_painted_reels()

            reveal_event(self)
            if new_drips:
                paint_drips_event(self, new_drips)
                painted_wall_event(self)

            if len(self.painted_reels) >= self.config.num_reels:
                self.award_full_wall()
                break

            self.evaluate_and_emit_wins()
            self.win_manager.update_gametype_wins(self.gametype)
            self.update_tag_meter()

        self.end_freespin()

    def evaluate_and_emit_wins(self):
        """Shared per-reveal win pipeline: evaluate, record, and emit win events."""
        self.evaluate_smukiez_wins()
        Lines.record_lines_wins(self)
        self.win_manager.update_spinwin(self.win_data["totalWin"])
        if self.active_char_mult > 1:
            character_mults_event(self)
        Lines.emit_linewin_events(self)
