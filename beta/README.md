# Smukiez Tag Run — playable beta (no art)

Plays the **real optimized math**: the server draws a book id from each mode's optimized
lookup table exactly like the Stake Engine RGS (96.5% RTP live odds) and the page
animates that book's event stream with placeholder tiles. Play money only.

## Run

```
smukiez-slot/.venv/Scripts/python.exe smukiez-slot/beta/server.py
```

Open http://localhost:8722. First launch decompresses the books into
`library/beta_cache/` (~30s); later launches are instant. If the math is regenerated
(`run.py`), delete `library/beta_cache/` so the beta picks up the new books.

## Controls

* **Spin** (or Space) — base game at the selected bet
* **Buy Bonus / Buy Extreme** — 100x / 400x buys
* **Turbo** checkbox — 4x speed; **click the board** mid-round to fast-forward to the result
* Bet stepper: $0.10 – $20

## Assets

`beta/assets/` holds the delivered art: `background.png` (Smukiez wall), `H1–H7.png` /
`L1–L10.png` (all 17 paying symbols: moneybag, glock, chain, kicks, boombox, skateboard,
limited box / spray can, marker, beanie, hangtag, dice, shirt, hoodie, weed bag, train,
brick wall), `mural.png` + `mural_0..4.png` (the Full Wall — painted reels reveal their
slice; the complete art crowns the max-win takeover and fills the wall meter),
`winframe.png` (green spray line-win highlight), `BS.png` (Crew Leader — money-counting
kid, bonus scatter),
`ES.png` (The Phantom — skull kid, extreme scatter), `frame.png` (spray-paint board
frame — replaces the old panel/grid chrome; idle cells are borderless, only feedback
states draw outlines), `brickwall.png` (Full Wall meter texture), and staged
`extra_*.png` (shirt, hoodie, weed bag, skateboard, limited box, train, weed-bud
wordmark) not yet in play. To swap a symbol's art, replace its
`<code>.png` — transparent PNG, ~1000px. Remaining specials (W wild, C1–C3 characters)
render as styled text tiles until their art exists.

## Spin presentation & compliance

The reels spin with motion blur, stagger, and scatter anticipation (slow-spin + gold
glow on remaining reels when 2 scatters land early — near-misses occur naturally in the
math, ~5% of base spins). Compliance model: **the landed board is always exactly the
drawn book's board**; the blurred pass-through symbols are the game's *real reel strips*
(served at `/api/strips`), and teases are driven only by the engine's own
`anticipation` data in the reveal event. Nothing about the outcome is invented or
altered client-side. Background bounce + board pop fire on every reveal (each free spin
included). Symbols land with a gravity drop — bottom-up, one at a time, bounce-shake on
impact. Painted reels show their Full Wall mural slice as divided cubes (each cell
carries its quarter). All motion respects `prefers-reduced-motion`, and reel landings
never depend on animation events alone (hard timeouts keep hidden tabs from hanging).

## Debug

* Footer shows book id + criteria + payout for every round.
* Replay any book from the console: `state.forceId = 395` (then spin/buy that mode;
  set `state.forceId = null` to go back to random). Book ids per mode live in
  `library/beta_cache/books_<mode>.jsonl`.
