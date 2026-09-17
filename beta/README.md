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
`winframe.png` (green spray line-win highlight), `sprayline.png` (a single spray-can dab,
tiled along the winning payline to draw the stroke — swap this one file to restyle every
payline), `BS.png` (Crew Leader — money-counting
kid, bonus scatter),
`ES.png` (The Phantom — skull kid, extreme scatter), `frame.png` (spray-paint board
frame — replaces the old panel/grid chrome; idle cells are borderless, only feedback
states draw outlines), `brickwall.png` (Full Wall meter texture),
`jraot-hollow.ttf` (the graffiti face the whole UI is set in), the right character's
`char_a.mp4` + `char_b.mp4` (idle) and `char_bonus_a.mp4` + `char_bonus_b.mp4` (bonus),
the left character's `char2_a.mp4` + `char2_b.mp4` (idle) and
`char2_bonus_a.mp4` + `char2_bonus_b.mp4` (bonus), the `sfx_*.wav` sound effects
(the idle character — see below; `server.py` serves fonts and video out of this folder
alongside the art, by the `ASSET_TYPES` extension allow-list), and staged
`extra_*.png` (shirt, hoodie, weed bag, skateboard, limited box, train, weed-bud
wordmark) not yet in play. To swap a symbol's art, replace its
`<code>.png` — transparent PNG, ~1000px. Remaining specials (W wild, C1–C3 characters)
render as styled text tiles until their art exists.

## Scene

Three knobs at the top of the stylesheet: `--wall-scale` sizes the background wall
(`contain` fits the whole piece in view, `cover` fills and crops it), `--char-height`
sizes both characters, and `--bounce` scales the per-spin bounce/shake — every keyframe in
`bgbounce`, `boardpop` and `charbounce` is expressed as `calc(<full value> * var(--bounce))`,
so one number tunes all three together. It currently sits at `.2` (a fifth of the original
force); `1` restores the full-strength version.

Two characters flank the board, driven by the same rig: the skull kid on the **right**
(`#charfx`) and the money-counting kid on the **left** (`#charfx2`). The `CHARACTERS` array
declares each one's element plus its idle and bonus reels, and `--char-shift` per container
centres that character's own column (the figure sits at a slightly different fraction of the
frame width in each set of clips — 44% vs 49.6%). A character declared with an empty bonus
reel would simply keep idling through a bonus; both currently have one.

Everything plays at **80% speed** — `CHAR_IDLE_RATE` and `CHAR_BONUS_RATE`, kept as separate
constants so the two can diverge later. The right character's idle pair is
`char_a.mp4` / `char_b.mp4`, played back to back — each clip is 640x360, ~10s,
with the figure on pure black at roughly 44-48% of the frame width. `#charvid` is scaled to the
box height and shifted to centre the figure, and `mix-blend-mode: screen` drops the black
surround (the figure's own dark tones read as the dark wall anyway). The window is deliberately
wider than the figure (0.94 x height) — sized to the union of every clip's content box, since a
narrower window sliced the arms off the frames where a character swings wide. The extra margin
is pure black, so it costs nothing on screen. There is no bottom mask: a fade there ate their
feet. `--char-shift` is set per character from that same union (40% / 49.7%).

`--char-stretch` (1.30) sets their height. It stretches rather than scales deliberately: the
video's width is pinned to the *unstretched* `--char-height`, so the frame gets taller without
getting wider. Scaling up uniformly instead would widen the boxes over the reels and — because
the window is a fixed fraction of the frame — start cropping the arms again. Slightly
off-ratio, intentionally.

The figures fill their frames top-to-bottom (measured: 98-100% of frame height), so once the
box reaches full screen height, *any* further height has to be cropped somewhere.
`--char-drop` (12vh) decides where: it sinks the box below the bottom edge so the overflow is
taken off the shoes and the heads stay intact. Raising `--char-stretch` without raising
`--char-drop` to match starts cutting off their heads.

The clips don't loop themselves, so they are **double-buffered across two stacked `<video>`
elements**: the standby always holds the next clip decoded and parked on frame 0, and a
`timeupdate` watcher starts the handover `LEAD` (0.45s) *before* the active clip runs out.
One player on its own would have to `load()` a new `src` at that point, and the blank it paints
while loading is keyed straight through by `screen` — the figure disappears for a beat. The
incoming clip fades up **over** the outgoing one (`--char-fade`, z-index raised) and the
outgoing is only dropped once it is fully hidden behind it; cross-dissolving both at once
would leave him ~25% transparent at the midpoint. Measured across a live handover, composite
coverage never falls below 1.0. On every spin he takes
the same beat as the wall — a hop and shake (`charbounce`), scaled from `50% 100%` so he pops up
off his feet rather than out of his middle. He is hidden under 1080px wide, where there is no
room beside the board (and note a `display:none` element runs no animations, so nothing fires
for him there either).

Hitting a bonus swaps him to his bonus reel — `char_bonus_a.mp4` / `char_bonus_b.mp4` — the moment
it triggers (`freeSpinTrigger` and `extremeTrigger` both call `setCharMode(true)`), through the same
crossfade rather than waiting for the current clip to finish. The rate is derived from the clip
itself rather than the current mode, because the standby is often holding a clip for the other
reel and `load()` resets `playbackRate` to `defaultPlaybackRate` (both are set). A bonus always
opens on `_a` (the reaction) and then alternates that character's pair for the rest of the
free-spin session, returning to the idle pair at `freeSpinEnd`. If a mode change lands *while* a crossfade is already in flight it is queued
and runs the instant that fade completes, rather than being swallowed by the re-entry guard. `playRound` also resets him to
idle on every round start, so a skipped or errored round can't strand him in bonus mode.

Browsers only advance video in a **visible** tab, and a page that *loads* hidden never starts
at all — so a `visibilitychange` handler picks him up whenever the tab comes back to the front.
To swap the character, drop new clips in and edit `CHAR_CLIPS` (use new filenames, or the
hour-long asset cache will keep serving the old ones).

Banners (FREE SPINS, BONUS COMPLETE, BIG WIN) have no panel behind them — the text stands
straight on the board, carrying its own shadow for contrast. Before the closing banner a
**payout tally** pops up over the board and rolls 0 to the bonus total (`tallyUp`, reusing
`countTo` so it always lands exact), with the coin rush pitched to the count's speed and the
bell on the total.

Character symbols render their **multiplier as the tile** (`x5`) rather than a C1/C2/C3 name
with a corner badge. Blurred pass-through tiles still show the bare name, correctly: a strip
symbol carries no multiplier until it lands.

The rail is down to the Free Spins card; **Full Wall and Tag Meter moved up into the header
bar**, left of Win/Balance. They are the same `#wall` / `#tags` / `#wallN` / `#paintLvl`
elements the game logic already drives, just sized down to sit on one bar, so no wiring
changed. The free-spin counter under the board is bare text (`N / total`), not a card. `setWall`/`setTags`/`enableMural` each no-op on missing DOM rather than throwing, so
either readout can be pulled again without breaking a round — and `setWall()` paints the reels
(and the mural reveal with them) regardless of whether its meter is on screen.

## Fitting the screen

Board size is `--cell-w: 120px; --cell-h: 103px; --cell-gap: 7px` (was 110/94/6 — raised ~9% on request). The spin overlay reads CELL_STEP from these, so resize here only.


`#app` wraps the header, stage and controls and is scaled with `transform: scale(fit)` from
a layout done at `window / fit` — so the bars still span the full width at any factor. The
board is the one thing that cannot wrap, so it sets the floor on the scale; the height is
fitted after the width so nothing wraps back taller. `html, body` never scroll and carry
`touch-action: manipulation` (no double-tap zoom). The old approach (`zoom` on three separate
blocks) left the header stuck narrow on phones and let the centred board overflow both edges.

Characters have three regimes: desktop beside the board; **portrait phone** (`--char-height`
26vh, inset 0, drop 2vh) standing whole in the bottom corners behind the controls, since the
width-fitted board leaves the lower half of the screen empty; **landscape phone**
(`max-height: 500px`, 82vh, inset -4vw) flanking the height-fitted board.

### (previous notes)


The layout has a natural size of roughly 1440x994, so on most windows it would scroll.
`fitToScreen()` measures the flow content and sets `--fit`, a `zoom` applied to `.top`,
`.main` and `.bottom`, so the whole UI scales down to whatever the window is — a round is
always fully visible. It re-measures at `--fit: 1` every time, so the factor always comes
from the natural size rather than compounding on the last one, and it re-runs on resize,
on `load` and once fonts settle. Scenery (`#bgwall`, `.charfx`) is viewport-sized already
and is deliberately left unscaled.

Measured: 1920x1080 → 0.998 · 1440x860 → 0.863 · 1366x768 → 0.771 · 1280x660 → 0.662,
with zero overflow on either axis at each.

## Sound

Web Audio, not `<audio>` elements — an `AudioBufferSourceNode`'s `playbackRate` resamples, so
it shifts pitch, which is the whole point here. Browsers block audio until the player
interacts, so the context opens on the first `pointerdown` and every clip is decoded up front.
A clip that fails to load just means silence; it never breaks a round.

* `sfx_spin.wav` — the spin button, only when a spin actually starts.
* `sfx_skip.wav` — fast-forwarding: the same button once it reads Skip, and clicking the board.
  Guarded so a second board click during an already-skipping round stays quiet.
* `sfx_line.wav` — one call per payline as it lights up, in step with the win cycle.
* `sfx_bet.wav` — the bet stepper, the same toggle pitched **1.22x up** for `+` and **0.8x
  down** for `−`.
* `sfx_reels.wav` — one loop for the whole spin, **its pitch following the reels' own speed**.
  `SPIN_SHAPE` mirrors the keyframe offsets, easings and travel fractions in `spinReel()`;
  evaluating those cubic-beziers and differentiating the result gives velocity, which maps onto
  playback rate (0.55x–1.5x). It peaks at exactly the halfway point — the reels wind up, then
  glide down into the stop — so the sound rises and falls with the symbols rather than being
  hand-drawn. **Keep `SPIN_SHAPE` in step with `spinReel()`'s keyframes.**
* `sfx_jackpot_a.wav` / `sfx_jackpot_b.wav` — picked at random on a big win (the same
  `win >= 20x` gate as the BIG WIN banner).
* `sfx_bonus_start.wav` / `sfx_bonus_end.wav` — on the bonus trigger and on the closing banner.
* `sfx_drip_a..f.wav` — one of six at random each time a Paint Drip floods a reel. `pickSfx()`
  excludes the previous pick, so a round with several drips never plays the same clip twice
  running (the jackpot pair uses it too).
* `sfx_coins.wav` / `sfx_bell.wav` — the bonus payout tally: a coin rush pitched to the count's
  own speed (`TALLY_CURVE`, peaking mid-roll) with the bell landing on the total.

`rateCurve()` builds any of these pitch curves — hand it a 0..1 progress function and it
differentiates it into playback rates, so both the reel spin and the coin rush are driven by
the motion they accompany rather than a hand-drawn envelope.

## Money readouts

Win and Balance roll to their new figure rather than snapping (`countTo`, ease-out, 650ms —
260ms in turbo) and shake as they change, tinted green up / pink down. Balance counts in both
directions; Win only counts on a rise, since resetting it to zero at the start of a round wants
no fanfare.

`requestAnimationFrame` is suspended in a hidden tab, so each tween also carries a hard
timeout that lands the exact final figure. That pair needs care: a throttled frame can fire
*after* the timeout has landed, and if it is allowed to write it repaints a stale number with
nothing left to correct it — stranding the readout on a wrong value. Each tween therefore
carries a token, and a frame whose token no longer matches (landed, or superseded by a newer
change) writes nothing.

## Spin feel (Sept 2026 rework)

Per reel the overlay winds UP 7–13 px, punches down, glides, overshoots 8–14 px past the
stop and rebounds 2–4 px — all four numbers are drawn per reel per spin so no two spins
match. Blur follows speed with eased segments (0 → 6 px over the punch, curved fall through
the glide, fully clear by 86 % so the wind-up, landing and rebound are sharp). Stagger 215 ms
(turbo 75) with ±55 ms jitter keeps landings one-at-a-time but never metronomic. On each
landing the column ripples top→bottom (`.reel.impact`, 45 ms per tile, squash/spring),
the board takes a `boardthud` nudge scaled by `--thud` (heavier for later reels) and a
pitched-down click plays. `SPIN_SHAPE` mirrors the new curve so the reel sound still
follows the motion. Background tabs freeze Web Animations — measure with the tab fronted.

## Spin presentation & compliance

The reels spin with motion blur, stagger, and scatter anticipation (slow-spin + gold
glow on remaining reels when 2 scatters land early — near-misses occur naturally in the
math, ~5% of base spins). Compliance model: **the landed board is always exactly the
drawn book's board**; the blurred pass-through symbols are the game's *real reel strips*
(served at `/api/strips`), and teases are driven only by the engine's own
`anticipation` data in the reveal event. Nothing about the outcome is invented or
altered client-side. Background bounce + board pop + the character's hop all fire together on
every reveal (each free spin included) — one `bounceFx()` restarts the three in lockstep. The spinning column is **pinned at both ends**, so a symbol never changes face
— not when the reel starts, not when it stops. Its bottom rows are the board that is on
screen at that moment (the reel accelerates away from what the player is already looking
at) and its top rows are this round's drawn board, with the board's padding row above it
(the reel decelerates onto the result, overshoots ~9px, and settles). In between, the
pass-through continues the strip out of the previous stop and back into the new one, the
two runs meeting mid-column under full blur. Blur builds only as the reel picks up speed
and clears completely before it stops, so the starting and landing tiles are both sharp.
Both handoffs between the column and the result cells happen in one synchronous block —
and the column is parked on its start position inline before it is ever painted — so no
frame can show a half-swapped reel. Impact is a bottom-up settle in place (each cell
squashes ~2px, staggered 26ms) rather than a second drop-in pass. Line wins cycle one
payline at a time and the `winframe` box pops in on each: scale 0 to 1.22 in ~60ms, then a
decaying shake (±2px / ±1.8°) that settles by 380ms. Every payline re-pops its full set of
boxes, carried-over cells included. The line itself is sprayed on underneath: one tiled
segment per leg, measured from the real cell rects so it follows the payline's zigzag, each
slashed in along its own axis (140ms, staggered ~55ms) so the whole stroke lands in
~200-270ms. Three offset phases of `sprayline.png` at different sizes close the gaps a
single tiled dab would leave, and per-segment thickness jitter (17-22px) keeps it
hand-sprayed. A line carrying a multiplier (`meta.multiplier` — paint x characters) punches
its value over the middle of the stroke as e.g. `12X`, timed to land as the spray finishes:
scale 0 to 1.45 in ~70ms, then a decaying shake (±5°) that settles by 500ms. Lines with no
multiplier (1x) get no badge. Painted reels show
their Full Wall mural slice as divided cubes (each cell
carries its quarter). All motion respects `prefers-reduced-motion`, and reel landings
never depend on animation events alone (hard timeouts keep hidden tabs from hanging).

## Fixes taken from the engine.io Discord (Sept 2026)

Read `research/discord/` for the source. What changed and why:

* **Bet survives a refresh** (`smukiez.bet.<currency>` in localStorage, preferred over
  `defaultBetLevel`) — reviewers refresh mid-spin and expect the same bet on return.
* **Balance capped at the currency's 2 decimals; bets/wins may show up to 4** —
  `RGS.money(amount, currency, extra)`; the balance readout uses `extra = 0`. (Reviewer
  rule from May–Jun 2026: 3-decimal bet levels are coming, balance stays at 2.)
* **429 / "Slow down"** maps to `ERR_ACT` and a calm message; plays are throttled to one
  per 250 ms so a key-repeat or double tap can't trigger it.
* **end-round retries 3× then confirms via authenticate** — a sporadic 500 on end-round is
  a known RGS wobble; the round settles anyway, so we never tell the player a win failed.
* **Tab return**: audio context resumed, balance re-synced if away > 30 s.
* **Sound button is a drawn SVG speaker**, not a text glyph — reviewers read glyph/emoji
  HUDs as low effort ("massive Claude tell").
* **Win tiers** BIG ≥15x / MEGA ≥40x / EPIC ≥100x with the board tally, so the celebration
  scales with the hit; `state.tallied` stops a bonus total being counted twice.
* **Max win chip** in the header; **Recent rounds** (last 50, per currency, localStorage)
  at the top of the (i) panel — no replay link because the RGS returns `betID`, not the
  book's event id. (To enable share-by-replay the math would need to put `event-id` on the
  reveal event, per Stake staff.)
* Long balances (ARS/IDR) shrink via `.long` / `.vlong` so the header holds on Popout S.

## Approval checklist features (frontend/)

* **Rules page** — `rules.js` renders the (i) panel: RTP, max win, mode costs, the full
  paytable (multiples of the total bet *and* the amount at the current bet), special symbols
  with every obtainable multiplier value, free-spin triggers / Tag Meter / Full Wall, all 30
  paylines drawn, a UI guide and the disclaimer. Numbers mirror `game_config.py`; if the
  paytable changes there, change `PAYS` here or the reviewer's win checks fail.
* **Bet Replay** — `?replay=true&game=<uuid>&version=<n>&mode=<mode>&event=<id>&amount=
  <bet>&currency=..&rgs_url=..` loads `GET {rgs_url}/bet/replay/{game}/{version}/{mode}/
  {event}` with no session, shows a Play button, animates the round with `settle:false`
  (no wallet call ever), then shows bet cost / payout / multiplier and Play again. Every
  betting control is removed via `body.replay`. The game UUID is the one in the scratch
  bucket path (`01a09492-cff1-7dee-98a7-3dc642d55cc2`); version is the math version.
* **Bonus chooser** — the bar has one `Bonus` button; it opens a centred card
  (`#bonusWrap`) that drifts a few px on a 9s `bonusdrift` loop and springs in with
  `bonuspop`. Pop-in lives on the wrapper, drift on the card — two elements, so the two
  transforms never fight. Inside: Standard / Extreme selection cards showing `xCost ·
  amount` at the live bet, a bet stepper wired to the same `state.betIdx` as the bar, the
  running total, and Play. Unaffordable modes grey out; the button stays live so the player
  can step the bet down. This panel replaced the old buy buttons and the confirm dialog —
  open, pick, Play is three deliberate actions with the charge on screen, and it is the only
  caller of `playRound()` with a non-base mode.
* **Autoplay** — twin-arrow icon button; opens a count picker (10/25/50/100) that must be
  confirmed; same button stops it; stops itself on a failed round or when the balance can't
  cover the next. Hidden when `jurisdiction.disabledAutoplay`.
* **Bottom-bar pop-ups** — the autoplay picker and the sound settings are `.popover`s
  anchored above their own button (`.popanchor`), not full-screen modals; one open at a
  time; the same button, click-away or Esc closes (no Cancel button); each open runs the
  `popin` tween (scale .55 → 1.06 → 1, origin at the arrow); spacebar ignored while one is up. Icon buttons are orange
  (`--orange`); the autoplay button fills orange while running.
* **Sound settings** — Music and Sound-effects sliders drive two Web Audio buses
  (`musicBus`, `sfxBus`) plus a mute switch; saved as `smukiez.vol` / `smukiez.muted`.
  There is no music track yet: set `MUSIC_URL` to a bundled file and `startMusic()` loops
  it through `musicBus` from the first gesture.
* **Social mode** — `social=true` in the URL runs every player-facing string through
  `RULES.T()`, which swaps Stake's restricted vocabulary (bet→play, buy→get, cash→coins,
  pay→win, ...) with per-word recasing. Rules copy avoids sentences that read badly once
  "pay" becomes "win".
* **Jurisdiction flags honoured** — disabledTurbo, disabledBuyFeature, disabledAutoplay,
  disabledSpacebar, disabledSlamstop (no skip), minimumRoundDuration, displayRTP /
  displaySessionTimer / displayNetPosition (header readout).
* Fonts are bundled (Google Fonts link removed — everything must come from the Engine CDN).

## Live RGS wire format (verified against rgsd.engine.io, not just the docs)

The published docs describe the endpoints but not the exact envelopes, and the live RGS
differs from the math-sdk book format in four ways that each silently break the client:

| what | math books / our first mock | live RGS |
| --- | --- | --- |
| event stream | `round.events` | **`round.state`** |
| round total | `payoutMultiplier` in hundredths (70 == 0.70x) | **plain multiple** (0.7 == 0.7x), plus `payout` in money units |
| losing round | stays open until `end-round` | **auto-settled on `/play`**, comes back `active: false`; calling `end-round` on one answers `ERR_VAL "player does not have active round"` |
| `end-round` body | `{ balance: { amount, currency } }` | **bare `{ amount, currency }`** |

Event-level amounts (`setWin`, `setTotalWin`, `finalWin`, `winInfo.win`) *are* in hundredths,
so `cents()` stays correct for those — only the round total needed rescaling.

`authenticate` omits `round` entirely unless one is open, and its config carries `gameModes`
(`{mode, costMultiplier, maxBet}`) which the client now reads instead of trusting its local
cost table. Errors arrive as `{"error": "ERR_VAL", "message": "..."}`.

`rgs.js` absorbs all of this so the presentation layer only ever sees `round.events`, and
`frontend/mock_rgs.py` now reproduces the live shapes — the earlier mock was too forgiving,
which is why the client passed locally and did nothing on Stake.

## Debug

* Book id + criteria + payout for every round go to the browser console (`console.debug`) —
  the on-screen footer line was removed.
* Replay any book from the console: `state.forceId = 395` (then spin/buy that mode;
  set `state.forceId = null` to go back to random). Book ids per mode live in
  `library/beta_cache/books_<mode>.jsonl`.
