"""Win evaluation for Smukiez Tag Run: line wins, then the multipliers the Multis left on
the cells the line runs through."""

from src.executables.executables import Executables
from src.calculations.lines import Lines


class GameCalculations(Executables):
    """Line evaluation with per-cell multipliers."""

    def evaluate_smukiez_wins(self) -> None:
        """Evaluate paylines, then scale each one by the multipliers on its cells.

        A cell carries a multiplier only after a Multi has blown out over it. A line's
        multiplier is the SUM of the values on the cells it pays through - two cells at x3
        make x6, not x9 - and a line that crosses no multiplied cell pays flat. The values
        are multiples of 0.25 (1.25x is the smallest) so the product is always a whole tenth.
        """
        self.win_data = Lines.get_lines(
            self.board, self.config, multiplier_method="global", global_multiplier=1
        )
        if self.win_data["totalWin"] <= 0:
            return

        new_total = 0.0
        for win in self.win_data["wins"]:
            cell_mults = [self.grid_mults[p["reel"]][p["row"]] for p in win["positions"]]
            mult = round(sum(cell_mults), 2)
            if mult > 0:
                # Exact by construction: pays are multiples of 0.4 and every Multi value a
                # multiple of 0.25, so this product is always a whole tenth of the bet - the
                # granularity the RGS accepts - and the amount paid is exactly pay x the
                # multiplier the events show. The 2-dp round only clears float noise.
                win["win"] = round(win["win"] * mult, 2)
                win["meta"]["multiplier"] = mult
                win["meta"]["cellMults"] = [round(m, 2) for m in cell_mults]
            new_total += win["win"]
        self.win_data["totalWin"] = round(new_total, 2)
