# Smukiez Tag Run — math model

5x4 board, 20 fixed paylines, RTP 0.965, max win 5000x. See `DESIGN.md` at the project
root for the full systems spec and frontend event contract.

## Symbols

| id | role |
|----|------|
| W  | Paint Drip — expanding wild; paints its reel, painted reels add +1x/+2x/+3x per reel to lines crossing them |
| BS | Crew Leader — bonus scatter; 3/4/5 trigger 8/10/12 free spins |
| ES | The Phantom — extreme scatter; 2 = direct Extreme Bonus (10 spins), 1 + standard trigger = upgraded Extreme |
| C1/C2/C3 | Smukiez characters — pay as premiums and multiply the whole spin win (2-3x / 5x / 8-10x; same type sums, different types multiply) |
| H1-H5 | Bag of Cash, Cartoon Glock, Gold Chain, Fresh Kicks, Boombox |
| L1-L5 | Spray Can, Graffiti Markers, Smukiez Beanie, Custom Hangtag, Dice |

## Modes

* `base` (1x) — natural triggers
* `bonus` (100x) — buys the Standard Bonus
* `extremebonus` (400x) — buys the Extreme Bonus

## Free spins

Painted reels are sticky for the whole bonus. Drips arrive via the per-spin
`landing_drips` distributions (free-spin strips carry no W). Tag Meter: every winning
spin adds a tag; a full meter awards +2 spins (bounded) and upgrades the paint bonus.
Painting all 5 reels completes the mural — **Full Wall** — and pays the 5000x wincap.

## Running

```
python run.py --base 100000 --bonus 20000 --extreme 20000 --threads 8
python run.py --optimize --analysis --checks     # full pipeline (needs Rust)
python analyze_books.py                          # feature stats over generated books
python reels/gen_reels.py                        # regenerate reel CSVs after editing specs
```
