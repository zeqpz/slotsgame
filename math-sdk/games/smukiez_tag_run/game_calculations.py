"""Win evaluation for Smukiez Tag Run: line wins -> paint color bonus -> character multipliers."""

from src.executables.executables import Executables
from src.calculations.lines import Lines


class GameCalculations(Executables):
    """Line evaluation with painted-reel color bonuses and spin-level character multipliers."""

    def evaluate_smukiez_wins(self) -> None:
        """Evaluate paylines, then apply the two Smukiez win modifiers.

        1. Paint color bonus: each painted reel used by a winning line adds
           +paint_level x to that line (line_mult = 1 + painted_reels_used * paint_level).
        2. Character multipliers: if the spin has any win, character values sum within a
           character type and multiply across types; the product scales every line win.
        """
        self.win_data = Lines.get_lines(
            self.board, self.config, multiplier_method="global", global_multiplier=1
        )

        if self.painted_reels and self.win_data["totalWin"] > 0:
            new_total = 0.0
            for win in self.win_data["wins"]:
                painted_used = len(
                    {pos["reel"] for pos in win["positions"] if pos["reel"] in self.painted_reels}
                )
                line_mult = 1 + painted_used * self.paint_level
                win["win"] = round(win["win"] * line_mult, 2)
                win["meta"]["paintMult"] = line_mult
                win["meta"]["multiplier"] = line_mult
                new_total += win["win"]
            self.win_data["totalWin"] = round(new_total, 2)

        self.active_char_mult = 1
        self.char_mult_details = []
        if self.win_data["totalWin"] > 0:
            type_sums, type_positions = {}, {}
            for reel, _ in enumerate(self.board):
                for row, sym in enumerate(self.board[reel]):
                    if sym.check_attribute("character"):
                        type_sums[sym.name] = type_sums.get(sym.name, 0) + sym.get_attribute("multiplier")
                        type_positions.setdefault(sym.name, []).append({"reel": reel, "row": row})

            if type_sums:
                char_mult = 1
                for name in sorted(type_sums):
                    char_mult *= type_sums[name]
                    self.char_mult_details.append(
                        {"name": name, "mult": type_sums[name], "positions": type_positions[name]}
                    )
                char_mult = min(char_mult, self.config.char_mult_cap)

                if char_mult > 1:
                    self.active_char_mult = char_mult
                    new_total = 0.0
                    for win in self.win_data["wins"]:
                        win["win"] = round(win["win"] * char_mult, 2)
                        win["meta"]["charMult"] = char_mult
                        win["meta"]["multiplier"] = int(win["meta"].get("paintMult", 1) * char_mult)
                        new_total += win["win"]
                    self.win_data["totalWin"] = round(new_total, 2)
