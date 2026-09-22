"""Win evaluation for Smukiez Tag Run: cluster wins, then the multipliers the Multis left
on the cells the cluster covers."""

from src.executables.executables import Executables
from src.calculations.cluster import Cluster


class GameCalculations(Executables):
    """Cluster evaluation with per-cell multipliers."""

    def evaluate_smukiez_wins(self) -> None:
        """Find every paying cluster, then scale each one by the multipliers on its cells.

        A cluster is five or more of the same symbol connected side to side (no diagonals),
        anywhere on the 7x7 board; its pay comes from the size tier in the paytable. A cell
        carries a multiplier only after a Multi has blown out over it. A cluster's
        multiplier is the SUM of the values on the cells it covers - two cells at x3 make
        x6, not x9 - and a cluster that covers no multiplied cell pays flat. The values are
        multiples of 0.25 (1.25x is the smallest) and every pay a multiple of 0.4, so the
        product is always a whole tenth of the bet, the granularity the RGS accepts.
        """
        clusters = Cluster.get_clusters(self.board, "wild")   # there is no wild; nothing joins a cluster
        wins = []
        total = 0.0
        for sym, groups in clusters.items():
            for cluster in groups:
                size = len(cluster)
                if (size, sym) not in self.config.paytable:
                    continue
                base = self.config.paytable[(size, sym)]
                cell_mults = [self.grid_mults[r][c] for r, c in cluster]
                mult = round(sum(cell_mults), 2)
                win = round(base * mult, 2) if mult > 0 else base
                positions = [{"reel": r, "row": c} for r, c in cluster]
                meta = {"clusterSize": size, "winWithoutMult": base, "multiplier": mult if mult > 0 else 1}
                if mult > 0:
                    meta["cellMults"] = [round(m, 2) for m in cell_mults]
                wins.append({"symbol": sym, "kind": size, "win": win, "positions": positions, "meta": meta})
                total += win
        self.win_data = {"totalWin": round(total, 2), "wins": wins}

    def record_smukiez_wins(self) -> None:
        """Force-record keys for every cluster paid on this board (mirrors Lines.record_lines_wins)."""
        for win in self.win_data["wins"]:
            self.record({"kind": win["kind"], "symbol": win["symbol"], "gametype": self.gametype})
