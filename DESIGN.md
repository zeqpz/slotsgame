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
   jackpot is not implementable on this platform. Implemented instead as the brief's
   "hybrid" option compressed into the bonus: every painted reel fills one of 5 mural
   sections; painting **all 5 reels during free spins completes the Full Wall and pays
   the 5,000x max win**. It is the game's wincap event and its thematic climax. A
   client-side cosmetic "career wall" (local persistence, no payout) can still accumulate
   across sessions in the frontend layer.
2. **Drip persistence between base-game spins** is likewise impossible server-side (each
   base spin is its own round). Drips are permanent **within a spin** in the base game and
   **for the whole bonus** during free spins (a bonus is one round internally, so full
   persistence is legal there — and that is where it matters).

Everything else in the brief mapped 1:1.

---

## 1. Board, lines, volatility targets

* 5 reels x 4 rows, 30 fixed paylines (defined in `game_config.py`), pays left-to-right,
  tumbling reels: winning symbols are removed, new ones drop in, every new board is paid.
* RTP **96.5%** every mode. Max win **5,000x**, reached through stacked Multi values.
* High volatility: the base game is a steady drip of small line wins; the big wins live
  in the Multi, and in the bonus where its values persist across spins.

## 2. Symbols & paytable

Pays are total-bet multiples per line, 5/4/3-of-a-kind, verbatim from `game_config.py`:

| sym | theme | 5 | 4 | 3 |
|-----|-------|---|---|---|
| H1 | Bag of Cash | 4.8 | 2 | 0.8 |
| H2 | Cartoon Glock | 4 | 1.6 | 0.8 |
| H3 | Gold Chain | 3.2 | 1.2 | 0.4 |
| H4 | Fresh Kicks | 2.4 | 1.2 | 0.4 |
| H5 | Boombox | 2 | 0.8 | 0.4 |
| H6 | Skateboard | 2 | 0.8 | 0.4 |
| H7 | Limited Drop Box | 1.6 | 0.8 | 0.4 |
| L1 | Spray Can | 1.2 | 0.8 | 0.4 |
| L2 | Graffiti Markers | 1.2 | 0.4 | 0.4 |
| L3-L6 | Beanie, Hangtag, Dice, Shirt | 0.8 | 0.4 | 0.4 |
| L7-L10 | Hoodie, Weed Bag, Freight Train, Brick Wall | 0.4 | 0.4 | 0.4 |

Non-paying: **M** Multi (booster), **BS** Crew Leader (bonus scatter), **ES** The Phantom
(extreme scatter). **There is no wild.** Every pay is a multiple of 0.4, and every line win
is exact by construction: every Multi value is a multiple of 0.25, so the product is always
a whole tenth of the bet, the granularity the RGS accepts.

Removed in v3: the Paint Drip wild and painted reels, the Full Wall, and the C1/C2/C3
characters.

## 3. The Multi (booster)

* Lands with a value rolled on landing from the current criteria's table (`booster_mults_*`
  in `game_config.py`): 1.25x up to 1000x, heavy at the bottom, a long thin tail. Every
  value is a multiple of 0.25 and every pay a multiple of 0.4, so a line times any sum of
  values is exactly a tenth of the bet - the RGS's granularity - with nothing rounded.
* Before lines are paid it **blows out**: the Multi and the four cells sharing an edge with
  it (not diagonals) are cleared, and each of those five cells has the value **added** to
  its own multiplier (`grid_mults[reel][row]`). Scatters in the cross are immune. The board
  refills; a refill can land another Multi, which blows out in turn.
* **Line multiplier = SUM of the cell values on the line's winning positions.** No
  multiplied cell means the line pays flat. Two Multis reaching one cell add.
* Cell values belong to the cell, not the symbol on it, so they survive every refill.
  Base game: they last for the rest of the spin. Bonus: wiped once on entry, then they
  persist across every free spin - the board fills up as the feature goes on.

## 4. Bonus rounds

**Standard Bonus** - 3/4/5 Crew Leaders -> 10/12/15 free spins. Multi density ~7 per
reel on `FR0`, `booster_mults_free` (mean ~8x). Tag Meter target 4.

**Extreme Bonus** - two entry paths:
* *Direct:* 2 Phantoms anywhere -> 17 free spins.
* *Upgrade:* standard trigger + >=1 Phantom on the same spin -> standard spin count, extreme rules.

Extreme rules: Multi density ~11 per reel on `FRE`, `booster_mults_extreme` (mean ~14x),
Tag Meter target 3.

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
* **Raw pool that optimised cleanly** to 0.965 in every mode: basegame ~0.70, bonus buy
  ~0.99, extreme buy ~1.07 (100k/20k/20k sims).
* **Cascade budget**: `max_tumbles_per_spin = 12` board changes, a Multi blow-out and a
  winning tumble each counting one. Largest book ~70 KB before compaction.

## 7. Frontend event contract (web-sdk)

Standard SDK events: `reveal` (board includes 1-row padding; a Multi carries `booster:
true` and its rolled `multiplier`), `tumbleBoard` (`explodingSymbols`, `newSymbols`),
`winInfo` (per-line wins; `meta.multiplier` is the float SUM of cell values, `meta.cellMults`
the per-position values), `setWin`, `setTotalWin`, `freeSpinTrigger`, `updateFreeSpin`,
`freeSpinEnd`, `enterBonus` (`reason`: standard | extreme_direct | extreme_upgrade),
`wincap`, `finalWin`.

Custom events (positions padded +1):

| type | payload | meaning |
|------|---------|---------|
| `booster` | `boosters: [{reel,row,mult,cells:[{reel,row}]}]`, `gridMults` (5x4, reel-major, unpadded, AFTER the add) | every Multi that just blew out; a `tumbleBoard` listing exactly those cells follows |
| `tagMeter` | `tags, target` | meter progress |
| `tagMeterFull` | `extraSpins, totalFs` | meter payoff |
| `extremeTrigger` | `positions[], reason` | Phantom cells on the trigger spin |

Books are compacted for publish by `tools/shrink_books.py`: each `winInfo` win becomes
`[symbol, kind, win, [[reel,row]...], lineIndex, multiplier]`. The client reads both shapes.

## 8. Tuning knobs (all in `game_config.py` / `reels/gen_reels.py`)

* Multi counts per strip (`"M"` in `STRIPS`) - how often the feature fires; the single
  strongest dial on bonus value because values persist across spins.
* `booster_mults_base` / `_free` / `_extreme` - what a Multi is worth when it does.
* `freespin_triggers`, `extreme_direct_spins`, `tag_meter_*` - bonus length.
* Paytable scale - base-game hit value. v3 is 4x the v2 cascade table because there is
  no wild to make lines hit.
* Reel strips regenerate deterministically: `python reels/gen_reels.py`.

Calibration lesson learned: with no wild, lines pay ~0.1x a spin in every mode, so nothing
about the base economy distinguishes a bonus spin. Persisting the cell multipliers across
the bonus is what does; density and value tables then set how hard.

## 11. Playable beta

`beta/server.py` + `beta/index.html`: a local RGS stand-in that draws from the
**optimized lookup tables** (real 96.5% live odds) and a no-art client that animates the
full event stream — drips flooding reels, wall meter, character multipliers, tag meter,
Full Wall/max-win takeovers — with play-money balance, bet stepper, and both buy
buttons. Run `smukiez-slot/.venv/Scripts/python.exe smukiez-slot/beta/server.py`, open
http://localhost:8722. See `beta/README.md` (includes a replay-by-book-id debug hook).

Presentation rule (applies to the real frontend too): the landed board always equals the
book's board; blurred spin-through symbols come from the real reel strips; scatter
teases use only the engine's `anticipation` data. Near-miss boards (2 scatters, no
bonus) occur naturally in the math — the client never fabricates or reorders outcomes.

## 12. Roadmap

1. **Done**: full 140k-sim run + Rust optimization (all modes exactly RTP 0.96500) +
   PAR sheet + RGS format checks + playable no-art beta.
2. Iterate strips/paytable until optimized hit-rates and win-distribution feel right
   (`analyze_books.py` + `utils/game_analytics` outputs).
3. **Frontend**: fork `web-sdk`, copy the `lines` app, implement handlers for the custom
   events above (drip expansion, wall meter, character celebrations, tag meter, Full
   Wall sequence), cosmetic career wall via local storage.
4. Upload `library/publish_files/` (books + lookup tables + `index.json`) and the built
   frontend via the Stake Engine dashboard; verify on the RGS test harness.
5. v2 candidates: drip bleed to adjacent reels, character stacking events, ways-pay variant.
