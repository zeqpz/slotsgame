# Smukiez Tag Run — Systems Design & Math Spec

Slot game for **Stake Engine** (stake-engine.com). Systems-first build per the master
brief; art layers on later. This document is the source of truth for rules, math
architecture, and the frontend event contract.

**Stack**

| layer | tech | status |
|---|---|---|
| Math model | Stake Engine `math-sdk` (Python 3.12), game module `games/smukiez_tag_run/` | built, simulating |
| Outcome optimization | SDK Rust optimizer (`cargo run --release`) | wired into `run.py --optimize` |
| Frontend | Stake Engine `web-sdk` (Svelte 5 + PixiJS 8), start from the `lines` app | not started (next phase) |
| RGS client | `stake-engine` npm package (`RGSClient`: Authenticate/Play/EndRound/Event) | n/a until frontend |

Repos: github.com/StakeEngine/{math-sdk, web-sdk, ts-client} (the engineio links in the
brief point at an unrelated org).

---

## 0. Platform reality check (two brief items adapted)

Stake Engine games are **pre-simulated**: the math model generates millions of complete
round outcomes ("books" of frontend events + a payout), the optimizer assigns each book a
draw weight to hit exact RTP, and the RGS simply draws a weighted book per bet. Every
round is **stateless and independent** — nothing persists server-side between bets.

1. **Full Wall progressive → in-round climax.** A cross-round/cross-player progressive
   jackpot is not implementable on this platform. v2 compressed it into the bonus as a
   painted-reel mural whose completion paid the 5,000x max win; v3 removed the mural and
   the max win is now reached through stacked Multi values (section 3).
2. **Drip persistence between base-game spins** is likewise impossible server-side (each
   base spin is its own round). Drips are permanent **within a spin** in the base game and
   **for the whole bonus** during free spins (a bonus is one round internally, so full
   persistence is legal there — and that is where it matters).

Everything else in the brief mapped 1:1.

---

## 1. Board, clusters, volatility targets

* **7 reels x 7 rows, cluster pays** (`win_type = "cluster"`): a win is 5 or more of the
  same symbol connected side to side (no diagonals), anywhere on the board. Every cluster
  on a board pays. Tumbling reels: winning symbols are removed, new ones drop in, every
  new board is paid again. There are no paylines.
* RTP **96.7%** every mode (v5, the top of the SDK's 3-star volatility band). Max win
  **10,000x**, reached through stacked Multi values.
* High volatility: the base game is a steady drip of small clusters (about one spin in
  two and a half pays, by the optimised tables); the big wins live in the Multi, and in
  the bonus where its values persist across spins.

## 2. Symbols & paytable

Pays are total-bet multiples per cluster, by cluster size, verbatim from `game_config.py`
(`convert_range_table` expands the tiers to every size up to 49):

| sym | theme | 5 | 6 | 7-8 | 9-11 | 12-15 | 16+ |
|-----|-------|---|---|-----|------|-------|-----|
| H1 | Bag of Cash | 4 | 8 | 16 | 40 | 100 | 400 |
| H2 | Cartoon Glock | 3.2 | 6 | 12 | 30 | 80 | 300 |
| H3 | Gold Chain | 2.4 | 4.8 | 10 | 24 | 60 | 200 |
| H4 | Fresh Kicks | 2 | 4 | 8 | 20 | 48 | 160 |
| H5, H6 | Boombox, Skateboard | 1.6 | 3.2 | 6.4 | 16 | 40 | 120 |
| H7 | Limited Drop Box | 1.2 | 2.4 | 4.8 | 12 | 32 | 100 |
| L1, L2 | Spray Can, Markers | 0.8 | 1.6 | 3.2 | 8 | 20 | 60 |
| L3 | Beanie | 0.8 | 1.2 | 2.4 | 6 | 16 | 48 |
| L4 | Hangtag | 0.4 | 1.2 | 2.4 | 6 | 16 | 48 |
| L5, L6 | Dice, Shirt | 0.4 | 0.8 | 2 | 4.8 | 12 | 40 |
| L7, L8 | Hoodie, Weed Bag | 0.4 | 0.8 | 1.6 | 4 | 10 | 32 |
| L9, L10 | Freight Train, Lowrider | 0.4 | 0.8 | 1.2 | 3.2 | 8 | 24 |

Non-paying: **M** Multi (booster), **BS** Crew Leader (bonus scatter), **ES** The Phantom
(extreme scatter). **There is no wild.** Every pay is a multiple of 0.4, and every cluster
win is exact by construction: every Multi value is a multiple of 0.25, so the product is
always a whole tenth of the bet, the granularity the RGS accepts.

Cluster games live or die on symbol frequency, so the strips skew hard: on the base strip
L1 is ~19% of stops and L10 ~1%, the seven premiums together ~14%, three Multis (one before
v5) and one Crew Leader per reel. With 17 icons and no skew, a 5-cluster was a 1-in-10 event.

Removed in v3: the Paint Drip wild and painted reels, the Full Wall, and the C1/C2/C3
characters. Replaced in v4: the 5x4 board and its 30 paylines. Removed in v5: the Tag
Meter (a bonus drops walls instead of adding spins). v5's Full Wall is a new event that
shares the old name (section 3).

## 3. The Multi (booster)

* Lands with a value rolled on landing from the current criteria's table (`booster_mults_*`
  in `game_config.py`): 1.25x up to 1000x, heavy at the bottom, a long thin tail. Every
  value is a multiple of 0.25 and every pay a multiple of 0.4, so a line times any sum of
  values is exactly a tenth of the bet - the RGS's granularity - with nothing rounded.
* **Clusters first.** Every cluster on the board is evaluated and paid before the Multi does
  anything, so a Multi landing beside a winning cluster can never blow it away unpaid.
* Then it **blows out**: the Multi and the four cells sharing an edge with it (not
  diagonals) are flagged to leave, and each of those five cells has the value **added** to
  its own multiplier (`grid_mults[reel][row]`). Scatters in the cross are immune. The paid
  cluster symbols and the blast cells leave in ONE tumble, the refill lands on the values,
  and the clusters are evaluated again - now through the values. A refill can land another
  Multi, which waits for that board's clusters in turn.
* **Cluster multiplier = SUM of the cell values on the cluster's cells.** No multiplied
  cell means the cluster pays flat. Two Multis reaching one cell add.
* Cell values belong to the cell, not the symbol on it, so they survive every refill.
  Base game: they last for the rest of the spin. Bonus: wiped once on entry, then they
  persist across every free spin - the board fills up as the feature goes on.

### Wall events and line drops (v5)

* **More walls, mostly teasers.** Three Multis per 100-stop reel on every strip
  (`BR0`/`BRE`/`FR0`/`FRE`, one before v5), with value tables that lean small (three base
  walls in four are x1.25 or x1.5): most walls land without a cluster under them, while the
  500x and 1000x keep turning up. A 1000x is one base wall in ~1,800 and lands one base spin
  in 1,500 (the owner's ask; `tools/finish_luts.py` holds it there), and it is a teaser: it
  pays about once in 500,000 spins, because the books where it pays are among the rarest the
  table draws. The client
  draws any value or cell total over 500x in purple instead of the red the heat scale tops
  out at.
* **Wall Line.** On a reveal, a straight run of 3 or 4 Multis (70:30) can land along a row or
  down a column, never over a scatter (`wall_line_chance`: 1 in 40 base spins, 1 in 6 free
  spins). Neighbouring walls' blasts overlap, so a line leaves a strip of stacked values.
* **Full Wall.** Every cell but a scatter becomes a Multi at once (`cover_mult_values`, 5x
  to 100x) and they all blow out together: each cell ends up the sum of its own value and
  up to four neighbours', and the whole board refills on top. Base game only, and only in
  the books of criteria `wallcover` (`force_cover` on the reveal), so the optimiser sets how
  rare it is: about 1 in 80,000 spins.
* **Line drops.** Every paid cluster leaves small multipliers (x1.25 / 1.5 / 2,
  `line_drop_values`) on its own cells, one per five symbols it held (`line_drop_per`). Each
  adds to its cell like a Multi's value and lasts as long. There are none once the cap is hit.

## 4. Bonus rounds

**Standard Bonus** - 3/4/5 Crew Leaders -> 10/12/15 free spins. Multi density 3 per
100-stop reel on `FR0` (2 before v5) and a Wall Line on about one free spin in six,
`booster_mults_free` (mean ~3.4x a wall).

**Extreme Bonus** - two entry paths:
* *Direct:* 2 Phantoms anywhere -> 17 free spins.
* *Upgrade:* standard trigger + >=1 Phantom on the same spin -> standard spin count, extreme rules.

Extreme rules: the same Multi density and Wall Lines on `FRE`, but `booster_mults_extreme`
(mean ~5.7x, every value 2x or more).

**No Tag Meter** (removed in v5) - a bonus plays exactly the spins its trigger awarded: no
meter, no extra spins, no scatter retriggers. It drops more walls instead (section 3).

## 5. Bet modes & buy features

| mode | cost | entry |
|------|------|-------|
| base | 1x | natural triggers |
| bonus (buy) | 100x | guaranteed Standard Bonus |
| extremebonus (buy) | 400x | guaranteed Extreme Bonus |

## 6. Math architecture

* **Criteria/distributions** (per SDK): each mode's sims split into forced buckets -
  `wincap` (exact 10,000x books), `extremegame`, `freegame`, `wallcover` (base only: the
  Full Wall), `basegame`, `0` (no-win). Custom forcing (`force_smukiez_board`) plants exact
  BS/ES counts on one board; `force_cover` turns a `wallcover` book's reveal into the Full Wall.
* **Strips**: `BR0` base, `BRE` base+Phantoms (extreme criteria only), `FR0`/`FRE` free
  spins, `FRWCAP` a wall of 1000x Multis for the wincap sims.
* **RTP allocation** (per mode, totals 0.967): base = wincap .002 + freegame .34 (hr 240)
  + extremegame .047 (hr 8000) + wallcover .012 (hr 80000) + basegame .566 (hr 2.5);
  bonus = wincap .004 + freegame .963; extremebonus = wincap .0018 + extremegame .9652.
  Lives in `game_optimization.py`. The optimiser asserts that a mode's criteria rtps add up
  to its betmode rtp exactly. The av_win each criteria is asked for sits near its simulated
  pool mean (free game ~82x, extreme ~375x, Full Wall ~920x), so the optimiser weights the
  pool rather than fighting it.
* **3-star volatility band** (the SDK's RGS checks): rtp at most 0.967 (0.968 fails), and
  the return from 10,000x wins (etl10k) at most 0.8. That is why the extreme buy's cap
  share is .0018: at .01 the cap landed once in 2,500 buys (etl10k 4.0).
* **Raw pool** (v5, before optimisation, in-memory tune runs): base winning spins average
  ~2.6x; the bonus buy pool comes to ~0.92x its cost and the extreme buy ~0.93x. The
  optimiser weights each mode to 0.967.
* **Base-game weighting** (`base_book_scaling` in `game_optimization.py`): the optimiser builds
  each criteria's distribution as curves over its payout VALUES and splits each value's weight
  evenly over the books that pay it. Left to that, it put 23% of all base rounds on the 277
  books paying exactly 0.5x or 0.6x (the heaviest drawn 1 in 1,021 spins) and almost nothing
  on the 22,000 paying 0.8x; and as every payout value got about the same weight, a 20-100x
  win (140 values, 393 books) came 1 in 143 spins and a 1-2x win (10 values, 13,094 books)
  1 in 2,600. So every payout of the `basegame` criteria is scaled by its book count, read off
  the pool after the sims (`run.py` builds the optimisation setup after them), times a target
  per-book shape: 5-20x 1 in 100 base spins, 20-100x 1 in 250, 100x+ 1 in 15,000
  (`BASE_TAIL`, asked at 80% so the optimiser's RTP fix-up adds high wins rather than piling
  onto 0.4x), the wins under 5x tilted toward the bottom to fit the criteria's 1.415x mean.
  Hit rate and RTP are fixed, so the small wins' mean and the tail's RTP trade one for one:
  keeping the old tail (RTP 0.373) leaves the small wins a 0.5x mean, which takes every 0.4x
  book at ~1 in 10,000 spins. v5 (2026-10-26) by the finished table: no board more often than
  1 in 28,000 spins (0 over 1 in 10,000, from 271 books); 0.4x 10% of rounds, 0.5x/0.6x 0.5%,
  0.8x 22%, 1-2x 5%, 2-5x 0.5%; base wins 5-20x 1 in 127, 20-100x 1 in 204, 100x+ 1 in 29,500
  (the tail's RTP 0.373 -> 0.246). A player is up after 50 / 100 / 200 base spins 28% / 34% /
  37% of the time (32% / 36% / 38% before) - the score the optimiser maximises, a little lower
  for the flatter table.
* **What a player sees** (base mode, by the finished weights): a Wall Line 1 round in ~36,
  a line drop 1 in 2.5, a 1000x wall 1 in ~1,450 (1 in 1,500 in the base game itself, the
  rest in bonuses), the Full Wall 1 in 80,000, a bonus trigger 1 in ~233, an Extreme
  trigger 1 in ~2,430, a 100x+ win 1 in ~650, a 1000x+ win 1 in ~92,000, the 10,000x cap 1 in
  5 million.
* **Finishing the tables** (`tools/finish_luts.py`, after every optimisation): the sims decide
  which books show a 1000x wall, the table how often each is drawn. No book showing one may
  outweigh a losing round's book, and together they come at most once in 1,500 base spins
  (`--rare-wall-rate`; per-book weighting alone gives ~1 in 1,000, from the teasers among the
  0.8x books): the cap comes down until they fit, the difference going to the other books of
  the same payout, so no payout's odds move. It also brings each mode's exact RTP 1e-10 under
  0.967: the 3-star check reads the table in float64 and exactly 0.967 can come out a hair over.
  The bonus and extreme buy tables are still value-weighted: their heaviest books come about 1
  in 500 and 1 in 900 buys.
* **Cascade budget**: `max_tumbles_per_spin = 12` board changes; a board's paid clusters
  and its Multi blow-outs leave in the same tumble and count as one.

## 7. Frontend event contract (web-sdk)

Standard SDK events: `reveal` (board includes 1-row padding; a Multi carries `booster:
true` and its rolled `multiplier`), `tumbleBoard` (`explodingSymbols`, `newSymbols`),
`winInfo` (per-cluster wins: `kind` is the cluster size, `meta.multiplier` the float SUM of
cell values, `meta.cellMults` the per-position values), `setWin`, `setTotalWin`,
`freeSpinTrigger`, `updateFreeSpin`,
`freeSpinEnd`, `enterBonus` (`reason`: standard | extreme_direct | extreme_upgrade),
`wincap`, `finalWin`.

Custom events (positions padded +1):

| type | payload | meaning |
|------|---------|---------|
| `booster` | `boosters: [{reel,row,mult,cells:[{reel,row}]}]`, `gridMults` (7x7, reel-major, unpadded, AFTER the add) | every Multi that just blew out, always after that board's `winInfo` and `lineMults`; the `tumbleBoard` that follows lists those cells together with the paid cluster symbols |
| `wallDrop` | `kind` (`line` \| `cover`), `positions[]` | a Wall Line or the Full Wall, right after the `reveal` that carries those Multis (their values come in the `booster` event when they blow out) |
| `lineMults` | `drops: [{reel,row,mult}]`, `gridMults` (AFTER the add) | the small multipliers a board's paid clusters leave, after that board's `winInfo` |
| `extremeTrigger` | `positions[], reason` | Phantom cells on the trigger spin |

Books are compacted for publish by `tools/shrink_books.py`: each `winInfo` win becomes
`[symbol, size, win, [[reel,row]...], null, multiplier]` (the fifth slot was the payline
index and is kept, empty, so the shape never changed). The client reads both shapes.

## 8. Tuning knobs (all in `game_config.py` / `reels/gen_reels.py`)

* Multi counts per strip (`"M"` in `STRIPS`) - how often the feature fires; the single
  strongest dial on bonus value because values persist across spins.
* `booster_mults_base` / `_free` / `_extreme` - what a Multi is worth when it does.
* `freespin_triggers`, `extreme_direct_spins` - bonus length (fixed by the trigger since v5).
* `wall_line_chance` / `wall_line_lengths`, `cover_mult_values`, `line_drop_per` /
  `line_drop_values` - the v5 wall events and line drops. How often the Full Wall comes is
  the `wallcover` criteria's hr in `game_optimization.py`, not a config value.
* Paytable tiers - base-game hit value. Six size tiers per symbol; the 16+ tier is the
  whole-board dream.
* `LOW_WEIGHTS` and the high counts in `gen_reels.py` - the cluster hit rate. Skew the lows
  harder for more clusters; thin the premiums to keep a premium cluster rare.
* Reel strips regenerate deterministically: `python reels/gen_reels.py`.

Calibration lessons learned: with no wild, paylines paid ~0.1x a spin in every mode, so
the Multi had to carry the game; on the 7x7 cluster board the lesson is symbol frequency -
17 evenly weighted icons gave a 10% natural hit rate and a bonus worth a quarter of its
price, a hard skew toward L1-L4 lifted it to 25% and a bonus worth its price. Multi density
per 100-stop reel is the strongest single dial: 2 per reel in the bonus strips lands about
one Multi a spin, 3 makes the extreme buy worth 1.5x its cost, 5 makes it 3x. v5 put 3 on
every strip and made the value tables lean small to match (~2.5x a base wall, half of it the
1000x tail; ~3.4x free, ~5.7x extreme): walls became a constant sight, and the buys came out
at ~0.92x their cost in the pool for the optimiser to lift to 0.967.
