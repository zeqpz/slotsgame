# Smukiez Tag Run — math model (v3)

5x4 board, 30 fixed paylines, tumbling reels, RTP 0.965, max win 5000x. See `DESIGN.md` at
the project root for the systems spec and the frontend event contract.

## Symbols

| id | role |
|----|------|
| M  | Multi — the booster. Lands with a value from 1.25x to 1000x, rolled on landing. It blows out: itself and the four cells sharing an edge with it are cleared, each of those five cells has the value ADDED to its own multiplier, and new symbols drop in on top. A line paying through multiplied cells is multiplied by the SUM of the values on its cells. Scatters are immune to the blast. No line value. |
| BS | Crew Leader — bonus scatter; 3/4/5 trigger 10/12/15 free spins |
| ES | The Phantom — extreme scatter; 2 = direct Extreme Bonus (17 spins), 1 + standard trigger = upgraded Extreme |
| H1-H7 | premiums |
| L1-L10 | lows |

There is no wild. The Paint Drip wild, the painted-reel colour bonus, the Full Wall award and
the C1/C2/C3 characters were all removed in v3.

## Cell multipliers

The values a Multi leaves behind belong to the CELL, not the symbol on it (`grid_mults`), so
they survive every refill. In the base game they last for the rest of the spin. In a bonus
they are wiped once at bonus entry and then persist across every free spin of that bonus -
this is what makes a bonus spin worth more than a base spin.

Every Multi value is a multiple of 0.25 and every pay a multiple of 0.4, so a line times any
sum of values is exactly a whole tenth of the bet - the only granularity the RGS accepts -
with nothing rounded. That is why the floor is 1.25x rather than 1.2x.

## Modes

* `base` (1x) — natural triggers
* `bonus` (100x) — buys the Standard Bonus
* `extremebonus` (400x) — buys the Extreme Bonus

## Free spins

Tag Meter: every winning spin adds a tag; a full meter awards +3 spins (at most +9 per
bonus) and resets. Multis land more often in the bonus strips (`FR0`, `FRE`) and their value
tables run richer (`booster_mults_free`, `booster_mults_extreme` in `game_config.py`).

## Running

The SDK needs Python 3.12 and the optimiser needs Rust. On this machine both live outside the
system install: `..\..\..\.venv312\Scripts\python.exe` (built with `uv`) and the
`stable-x86_64-pc-windows-gnu` toolchain, pinned to `optimization_program/` with a rustup
override because there is no MSVC linker here.

```
python run.py --base 100000 --bonus 20000 --extreme 20000 --threads 8 --optimize --checks
python reels/gen_reels.py                        # regenerate reel CSVs after editing specs
python ../../../tools/shrink_books.py library/publish_files/books_*.jsonl.zst   # compact wins
python ../../../tools/check_books.py  library/publish_files/books_base.jsonl.zst  # publisher rules
```

Books and lookup tables are written to `library/publish_files/`. That is also what gets
uploaded to engine.io, so a simulation overwrites the last published set; git has the
published versions.

The `wincap` criteria used to dominate run time: each forced-cap sim replays whole bonuses
until one lands on exactly 5000x, and a first full run took 23 hours. The cap quotas are now
tiny and the wincap strip (`FRWCAP`) is a wall of 1000x Multis, so a full run takes minutes.
