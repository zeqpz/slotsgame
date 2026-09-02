"""Game-specific state resets, symbol value assignment, and acceptance criteria."""

from game_executables import GameExecutables
from src.calculations.statistics import get_random_outcome


class GameStateOverride(GameExecutables):
    """Overrides and extensions of the universal state.py functions."""

    def reset_book(self):
        super().reset_book()
        self.painted_reels = []
        self.paint_level = self.config.paint_bonus_base
        self.paint_max = self.config.paint_bonus_max_standard
        self.tag_meter = 0
        self.tag_target = self.config.tag_meter_target_standard
        self.extra_spins_awarded = 0
        self.bonus_type = ""
        self.triggered_extreme = False
        self.full_wall_awarded = False
        self.active_char_mult = 1
        self.char_mult_details = []

    def assign_special_sym_function(self):
        self.special_symbol_functions = {
            "C1": [self.assign_char_mult],
            "C2": [self.assign_char_mult],
            "C3": [self.assign_char_mult],
        }

    def assign_char_mult(self, symbol):
        """Draw a character's multiplier value from the current distribution conditions."""
        values = self.get_current_distribution_conditions()["char_mult_values"][self.gametype][symbol.name]
        symbol.assign_attribute({"multiplier": get_random_outcome(values)})

    def check_repeat(self):
        """Resimulate when the outcome does not satisfy the assigned criteria."""
        if self.repeat is False:
            win_criteria = self.get_current_betmode_distributions().get_win_criteria()
            if win_criteria is not None and self.final_win != win_criteria:
                self.repeat = True

            conds = self.get_current_distribution_conditions()
            if conds["force_freegame"] and not self.triggered_freegame:
                self.repeat = True
            if conds.get("force_extreme", False) and not self.triggered_extreme:
                self.repeat = True
            if self.triggered_extreme and not conds.get("force_extreme", False):
                self.repeat = True

            if self.win_manager.running_bet_win == 0.0 and self.criteria != "0":
                self.repeat = True

        self.repeat_count += 1
        self.check_current_repeat_count()
