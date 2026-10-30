# Smukiez Tag Run — math model (v5, 7x7 cluster)

7x7 board, cluster pays, tumbling reels, RTP 0.967, max win 10,000x. See `DESIGN.md` at the
project root for the systems spec and the frontend event contract.

## Wins

A cluster is 5 or more of the same symbol connected side to side (no diagonals), anywhere
on the board. Every cluster on a board pays, by size tier (5 | 6 | 7-8 | 9-11 | 12-15 |
16+), then the winning symbols leave and the refill is paid again. There are no paylines.

## Symbols

| id | role |
|----|------|
| M  | Multi — the booster. Lands with a value from 1.25x to 1000x, rolled on landing. Every cluster on the board is paid first; then it blows out: itself and the four cells sharing an edge with it are cleared (in the same tumble as the paid cluster symbols), each of those five cells has the value ADDED to its own multiplier, and new symbols drop in on top. A cluster covering multiplied cells is multiplied by the SUM of the values on those cells. Scatters are immune to the blast. No pay of its own. |
| BS | Crew Leader — bonus scatter; 3/4/5 trigger 10/12/15 free spins |
| ES | The Phantom — extreme scatter; 2 = direct Extreme Bonus (17 spins), 1 + standard trigger = upgraded Extreme |
| H1-H7 | premiums (scarce on the strips) |
| L1-L10 | lows (L1-L4 carry the hit rate) |

There is no wild. The Paint Drip wild, the painted-reel colour bonus, the Full Wall award and
the C1/C2/C3 characters were removed in v3; the 5x4 payline board was replaced in v4.

## Wall events and line drops (v5)

* **More walls.** Every strip carries three Multis per reel (`BR0`/`BRE`/`FR0`/`FRE`), and the value
  tables lean small: most walls are teasers that land without a cluster under them, while the
  500x and 1000x keep turning up. A 1000x is one base wall in ~1,800 and lands one base spin
  in 1,500 (the owner's ask, held there by `tools/finish_luts.py`); it pays about once in
  500,000 spins, so it is a teaser.
* **Wall Line.** On any reveal a straight run of 3 or 4 Multis can land along a row or down a
  column (`wall_line_chance`: 1 in 40 base spins, 1 in 6 free spins); adjacent blasts overlap.
* **Full Wall.** Every cell but a scatter becomes a Multi (small values, `cover_mult_values`) and
  they all blow out together. Base game only, and only in the books of criteria `wallcover`
  (forced on the reveal), so the optimiser sets its frequency (about 1 in 80,000 spins).
* **Line drops.** Every paid cluster leaves a small multiplier (x1.25/1.5/2) on one of its own
  cells per five symbols it held, added to the cell like a Multi's value (`line_drop_values`).
* Events: `wallDrop` {kind: line|cover, positions} after the reveal; `lineMults` {drops, gridMults}
  after a board's wins.

## Cell multipliers

The values a Multi leaves behind belong to the CELL, not the symbol on it (`grid_mults`), so
they survive every refill. In the base game they last for the rest of the spin. In a bonus
they are wiped once at bonus entry and then persist across every free spin of that bonus -
this is what makes a bonus spin worth more than a base spin.

Every Multi value is a multiple of 0.25 and every pay a multiple of 0.4, so a cluster times
any sum of values is exactly a whole tenth of the bet - the only granularity the RGS accepts
- with nothing rounded. That is why the floor is 1.25x rather than 1.2x.

## Modes

* `base` (1x) — natural triggers
* `bonus` (100x) — buys the Standard Bonus
* `extremebonus` (400x) — buys the Extreme Bonus

## Free spins

A bonus plays exactly the spins its trigger awarded: the Tag Meter and its extra spins are gone
in v5, and the bonus drops walls instead - three per reel on `FR0`/`FRE` and a Wall Line on about
one free spin in six. The value tables are `booster_mults_free` and `booster_mults_extreme` in
`game_config.py`.

## Running

The SDK needs Python 3.12 and the optimiser needs Rust. On this machine both live outside the
system install: `..\..\..\.venv312\Scripts\python.exe` (built with `uv`) and the
`stable-x86_64-pc-windows-gnu` toolchain, pinned to `optimization_program/` with a rustup
override because there is no MSVC linker here.

```
python run.py --base 100000 --bonus 20000 --extreme 20000 --threads 8 --optimize --checks
python ../../../tools/finish_luts.py library/publish_files   # after EVERY optimisation (see below)
python reels/gen_reels.py                        # regenerate reel CSVs after editing specs
python ../../../tools/gen_strips_js.py           # then refresh the client's spin-through strips
python ../../../tools/shrink_books.py library/publish_files/books_*.jsonl.zst   # compact wins
python ../../../tools/check_books.py  library/publish_files/books_base.jsonl.zst  # publisher rules
```

Books and lookup tables are written to `library/publish_files/`. That is also what gets
uploaded to engine.io, so a simulation overwrites the last published set; git has the
published versions.

The optimiser weights payouts, not books: each payout's weight is split evenly over the books
that pay it. Left to that, the base game put about a quarter of all rounds on the ~280 books
paying exactly 0.5x or 0.6x (each drawn about 1 in 1,100 spins) and almost nothing on the
22,000 paying 0.8x. So `game_optimization.py` scales every payout of the base game's winning
spins by its book count and a target win profile (`base_book_scaling`, `BASE_TAIL`), read off
the pool after the sims - which is why `run.py` builds the optimisation setup after them. No
base board now comes more often than about 1 in 20,000 spins. The bonus and extreme buy tables
are still weighted by payout.

`tools/finish_luts.py` holds a 1000x wall to one base spin in 1,500 and keeps any one such
board rare (no book showing one may outweigh a losing round's book; the difference goes to the
other books of the same payout, so no payout's odds move), and brings each mode's exact RTP
1e-10 under 0.967, because the SDK's 3-star check reads the table in float64 and exactly 0.967
can come out a hair over. Its output says what it changed; a second run changes nothing.

The `wincap` criteria used to dominate run time: each forced-cap sim replays whole bonuses
until one lands on exactly the cap (5000x then, 10,000x now), and a first full run took 23 hours. The cap quotas are now
tiny and the wincap strip (`FRWCAP`) is a wall of 1000x Multis, so a full run takes minutes.
