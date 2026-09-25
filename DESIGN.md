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
* RTP **96.5%** every mode. Max win **5,000x**, reached through stacked Multi values.
* High volatility: the base game is a steady drip of small clusters (about one spin in
  four pays naturally); the big wins live in the Multi, and in the bonus where its values
  persist across spins.

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
L1 is ~19% of stops and L10 ~1%, the seven premiums together ~14%, one Multi and one Crew
Leader per reel. With 17 icons and no skew, a 5-cluster was a 1-in-10 event.

Removed in v3: the Paint Drip wild and painted reels, the Full Wall, and the C1/C2/C3
characters. Replaced in v4: the 5x4 board and its 30 paylines.

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

## 4. Bonus rounds

**Standard Bonus** - 3/4/5 Crew Leaders -> 10/12/15 free spins. Multi density 2 per
100-stop reel on `FR0` (about one Multi a spin on 49 cells), `booster_mults_free` (mean
~8x). Tag Meter target 4.

**Extreme Bonus** - two entry paths:
* *Direct:* 2 Phantoms anywhere -> 17 free spins.
* *Upgrade:* standard trigger + >=1 Phantom on the same spin -> standard spin count, extreme rules.

Extreme rules: same Multi density on `FRE` but `booster_mults_extreme` (mean ~10x, every
value 2x or more), Tag Meter target 3.

**Tag Meter** - every winning free spin adds a tag. Full meter: **+3 free spins** (max +9
per bonus). Meter resets and refills. No scatter retriggers.

## 5. Bet modes & buy features

| mode | cost | entry |
|------|------|-------|
| base | 1x | natural triggers |
| bonus (buy) | 100x | guaranteed Standard Bonus |
| extremebonus (buy) | 400x | guaranteed Extreme Bonus |

## 6. Math architecture

* **Criteria/distributions** (per SDK): each mode's sims split into forced buckets -
  `wincap` (exact 5000x books), `extremegame`, `freegame`, `basegame`, `0` (no-win).
  Custom forcing (`force_smukiez_board`) plants exact BS/ES counts on one board.
* **Strips**: `BR0` base, `BRE` base+Phantoms (extreme criteria only), `FR0`/`FRE` free
  spins, `FRWCAP` a wall of 1000x Multis for the wincap sims.
* **RTP allocation** (per mode, totals 0.965): base = wincap .002 + freegame .30 (hr 200)
  + extremegame .06 (hr 8000) + basegame .603; bonus = wincap .004 + freegame .961;
  extremebonus = wincap .01 + extremegame .955. Lives in `game_optimization.py`. The
  av_win each criteria is asked for sits near its simulated pool mean (free game ~55x,
  extreme ~500x) so the optimiser weights the pool rather than fighting it.
* **Raw pool** (7x7, before optimisation): natural base RTP ~0.58 at a 25% hit rate;
  bonus buy pool ~1.0x its cost, extreme buy ~0.85x (`tune77.py`-style in-memory runs);
  the optimiser weights each mode to 0.965.
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
| `booster` | `boosters: [{reel,row,mult,cells:[{reel,row}]}]`, `gridMults` (7x7, reel-major, unpadded, AFTER the add) | every Multi that just blew out, always after that board's `winInfo`; the `tumbleBoard` that follows lists those cells together with the paid cluster symbols |
| `tagMeter` | `tags, target` | meter progress |
| `tagMeterFull` | `extraSpins, totalFs` | meter payoff |
| `extremeTrigger` | `positions[], reason` | Phantom cells on the trigger spin |

Books are compacted for publish by `tools/shrink_books.py`: each `winInfo` win becomes
`[symbol, size, win, [[reel,row]...], null, multiplier]` (the fifth slot was the payline
index and is kept, empty, so the shape never changed). The client reads both shapes.

## 8. Tuning knobs (all in `game_config.py` / `reels/gen_reels.py`)

* Multi counts per strip (`"M"` in `STRIPS`) - how often the feature fires; the single
  strongest dial on bonus value because values persist across spins.
* `booster_mults_base` / `_free` / `_extreme` - what a Multi is worth when it does.
* `freespin_triggers`, `extreme_direct_spins`, `tag_meter_*` - bonus length.
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
one Multi a spin, 3 makes the extreme buy worth 1.5x its cost, 5 makes it 3x.
