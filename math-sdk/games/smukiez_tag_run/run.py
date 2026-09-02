"""Main file for generating Smukiez Tag Run books, lookup tables, and config files.

Usage:
    python run.py                         # simulate with the default counts below
    python run.py --base 100000 --bonus 20000 --extreme 20000 --threads 8
    python run.py --optimize --analysis --checks   # full pipeline (requires Rust toolchain)
"""

import argparse

from gamestate import GameState
from game_config import GameConfig
from game_optimization import OptimizationSetup
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate Smukiez Tag Run outcomes.")
    parser.add_argument("--base", type=int, default=int(2e4), help="base mode simulation count")
    parser.add_argument("--bonus", type=int, default=int(5e3), help="bonus buy simulation count")
    parser.add_argument("--extreme", type=int, default=int(5e3), help="extreme bonus buy simulation count")
    parser.add_argument("--threads", type=int, default=1, help="simulation processes")
    parser.add_argument("--rust-threads", type=int, default=16)
    parser.add_argument("--no-sims", action="store_true", help="skip book generation")
    parser.add_argument("--optimize", action="store_true", help="run the Rust optimization program")
    parser.add_argument("--analysis", action="store_true", help="build the PAR/stat sheet")
    parser.add_argument("--checks", action="store_true", help="run RGS format verification")
    args = parser.parse_args()

    batching_size = 50000
    compression = True
    profiling = False

    num_sim_args = {"base": args.base, "bonus": args.bonus, "extremebonus": args.extreme}
    target_modes = list(num_sim_args.keys())

    config = GameConfig()
    gamestate = GameState(config)
    OptimizationSetup(config)

    if not args.no_sims:
        create_books(
            gamestate,
            config,
            num_sim_args,
            batching_size,
            args.threads,
            compression,
            profiling,
        )

    generate_configs(gamestate)

    if args.optimize:
        from optimization_program.run_script import OptimizationExecution

        OptimizationExecution().run_all_modes(config, target_modes, args.rust_threads)
        generate_configs(gamestate)

    if args.analysis:
        from utils.game_analytics.run_analysis import create_stat_sheet

        custom_keys = [{"symbol": "scatter"}, {"symbol": "scatter_extreme"}]
        create_stat_sheet(gamestate, custom_keys=custom_keys)

    if args.checks:
        from utils.rgs_verification import execute_all_tests

        execute_all_tests(config)
