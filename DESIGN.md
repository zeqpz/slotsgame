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

* 5 reels x 4 rows, 30 fixed paylines (defined in `game_config.py`), pays left-to-right.
* RTP **96.5%** every mode. Max win **5,000x**, reached via Full Wall or stacked multipliers.
* Base game medium volatility; big wins concentrated in character products, painted-reel
  free spins, and the Extreme Bonus.

## 2. Symbols & paytable

Pays are total-bet multiples per line, 5/4/3-of-a-kind:

| sym | theme | 5 | 4 | 3 |
|-----|-------|---|---|---|
| W | Paint Drip (wild) | 25 | 10 | 4 |
| C3 | Character 3 (rare) | 25 | 10 | 4 |
| C2 | Character 2 (uncommon) | 20 | 8 | 3 |
| C1 | Character 1 (common) | 15 | 6 | 2.5 |
| H1 | Bag of Cash | 12 | 5 | 2 |
| H2 | Cartoon Glock | 10 | 4 | 1.5 |
| H3 | Gold Chain | 8 | 3 | 1.2 |
| H4 | Fresh Kicks | 6 | 2.5 | 1 |
| H5 | Boombox | 5 | 2 | 0.8 |
| L1-L5 | Spray Can, Markers, Beanie, Hangtag, Dice | 2.5-1 | 1-0.5 | 0.4-0.2 |

Math v0.2 adds the rest of the delivered icons as paying symbols: **H6** Skateboard
(4.5/1.8/0.7), **H7** Limited Drop Box (4/1.6/0.6), **L6** Shirt, **L7** Hoodie, **L8**
Weed Bag, **L9** Freight Train, **L10** Brick Wall (1–0.6 / 0.5–0.3 / 0.2–0.1) — 17
paying items total. Non-paying: **BS** Crew Leader (bonus scatter), **ES** The Phantom
(extreme scatter).

Wilds substitute for every paying symbol (characters included), never for BS/ES.

## 3. Paint Drips (wild system)

* A drip landing **expands vertically to paint its whole reel** wild. It paints *around*
  scatters and characters (never erases a trigger or a multiplier — the reel still counts
  as fully painted).
* **Color bonus:** every winning line gets `1 + (painted reels it crosses) x paint_level`.
  `paint_level` is +1x in base/standard bonus, +2x at Extreme start, upgradeable to +3x.
  Multiple painted reels stack additively within a line, exactly per brief.
* Base game: drips come from the reel strips (reels 2-4), expand for that spin.
* Free spins: painted reels are **sticky for the whole bonus**; new drips arrive via
  per-spin `landing_drips` distributions (free-spin strips carry no W, so drip frequency
  is a pure tuning dial per mode/criteria).
* Brief's optional "bleed to adjacent reels" is deferred (v2 candidate).

## 4. Smukiez characters (multiplier symbols)

Premium symbols that pay lines **and** multiply the whole spin:

| char | rarity | value drawn on landing |
|------|--------|------------------------|
| C1 | common | 2x (70%) / 3x (30%) — free spins 55/45 |
| C2 | uncommon | 5x |
| C3 | rare | 8x (75%) / 10x (25%) — free spins 60/40 |

If the spin has any line win: values **sum within a character type** (stacked characters)
and **multiply across different types** (brief: 3x + 5x = 15x), capped at 128x, applied
to every line win. Characters can appear singly or stacked; density lives on the strips.

## 5. Bonus rounds

**Standard Bonus** — 3/4/5 Crew Leaders → 8/10/12 free spins. Sticky drips, +1x paint,
Tag Meter target 4.

**Extreme Bonus** — two entry paths, per brief:
* *Direct:* 2 Phantoms anywhere → 10 free spins.
* *Upgrade:* standard trigger + ≥1 Phantom on the same spin → standard spin count, extreme rules.

Extreme rules: painted reels from the triggering spin **carry over**, paint starts at
+2x, richer character values/density, Tag Meter target 3, best odds of reaching the Full Wall.

**Tag Meter** — every winning free spin adds a tag. Full meter: **+2 free spins** (max +6
per bonus) and **paint bonus upgrade** (+1x per painted reel, capped +2x standard / +3x
extreme). Meter resets and refills.

No scatter retriggers — extra spins come only from the meter (keeps books bounded).

## 6. Full Wall

During any free spins, each painted reel fills a mural section (events expose `sections /
totalSections`). **5/5 sections = Full Wall**: the mural completes, the round pays up to
the 5,000x cap, the bonus ends in celebration. Measured raw frequency: ~0.25% of standard
bonuses, ~7% of extreme bonuses pre-optimization (the optimizer re-weights live frequency
down further).

## 7. Bet modes & buy features

| mode | cost | entry |
|------|------|-------|
| base | 1x | natural triggers |
| bonus (buy) | 100x | guaranteed Standard Bonus |
| extremebonus (buy) | 400x | guaranteed Extreme Bonus |

## 8. Math architecture

* **Criteria/distributions** (per SDK): each mode's sims split into forced buckets —
  `wincap` (exact 5000x books), `extremegame`, `freegame`, `basegame`, `0` (no-win).
  Custom forcing (`force_smukiez_board`) plants exact BS/ES counts by merging stop
  positions for both scatter classes on one board (SDK only forces one symbol class).
* **Dedicated strips**: `BR0` base, `BRE` base+Phantoms (extreme criteria only), `FR0`/
  `FRE` free spins, `FRWCAP` drip-rich wincap strip. Natural extreme frequency in the
  live game comes from optimizer weights (target hit-rate 1/2000 spins), not strip odds.
* **RTP allocation** (per mode, totals 0.965): base = wincap .001 + freegame .27 (hr 170)
  + extremegame .07 (hr 2000) + basegame .624 (hr 3.4); bonus = wincap .004 + freegame
  .961; extremebonus = wincap .01 + extremegame .955. Lives in `game_optimization.py`.
* **Wincap books** converge fast because `FRWCAP` + hot drip injection complete the wall
  (exact-cap payout) organically.
* Raw sims are deliberately hotter than target with mids on both sides — the Rust
  optimizer shapes final weights; `analyze_books.py` prints per-criteria distributions,
  wall %, painted-section and character-multiplier histograms for tuning passes.

## 9. Frontend event contract (web-sdk)

Standard SDK events: `reveal` (board includes 1-row padding; special flags `wild`,
`scatter`, `scatter_extreme`, `character`, `multiplier` value on characters),
`winInfo` (per-line wins; `meta.paintMult`, `meta.charMult`, `meta.multiplier`),
`setWin`, `setTotalWin`, `freeSpinTrigger`, `updateFreeSpin`, `freeSpinEnd`,
`enterBonus` (`reason`: standard | extreme_direct | extreme_upgrade), `wincap`, `finalWin`.

Custom events (all rows padded +1, amounts in cents like the SDK standard):

| type | payload | meaning |
|------|---------|---------|
| `paintDrips` | `drips: [{reel,row}]` | drip origin cells this reveal (animate expansion) |
| `paintedWall` | `paintedReels[], paintLevel, sections, totalSections` | wall state after painting |
| `characterMults` | `characters: [{name, mult, positions[]}], totalMult` | character breakdown before winInfo |
| `tagMeter` | `tags, target` | meter progress |
| `tagMeterFull` | `extraSpins, paintLevel, totalFs` | meter payoff |
| `fullWall` | `amount` | mural complete, max win |
| `extremeTrigger` | `positions[], reason` | Phantom cells on the trigger spin |

Note: free-spin `reveal` boards are post-expansion (painted reels show as W columns);
`paintDrips`/`paintedWall` carry what's new so the client can animate the transition —
same convention as the SDK's expanding-wilds sample.

## 10. Tuning knobs (all in `game_config.py` / `reels/gen_reels.py`)

* `landing_drips` per criteria — drip frequency = bonus volatility + Full Wall rate.
* Character counts per strip + `char_mult_values` — multiplier frequency/size.
* `paint_bonus_*`, `tag_meter_*` — feature escalation and bonus length (books bounded).
* `freespin_triggers`, `extreme_direct_spins`, buy costs, RTP splits.
* Reel strips regenerate deterministically: `python reels/gen_reels.py`.

Calibration lesson learned: sticky full-reel wilds + total-spin multipliers compound
violently. First cut walled ~100% of bonuses; final drip EVs are ~0.1/spin (standard)
and ~0.13/spin (extreme) with character density halved on free-spin strips.

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
