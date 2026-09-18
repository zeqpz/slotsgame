# Smukiez Tag Run

Graffiti/streetwear slot game for [Stake Engine](https://stake-engine.com). 5x4, 30
paylines, RTP 96.5% (verified 0.96500 on the optimized tables in all three bet modes),
max win 5,000x via the **Full Wall** — paint all five reels during free spins and the
mural completes.

Core systems: **Paint Drip** expanding wilds that paint reels (sticky through the bonus,
+1x/+2x/+3x color bonus per painted reel), **Smukiez character** multipliers (sum within
a type, multiply across types), Crew Leader scatters (3/4/5 → 8/10/12 free spins), The
Phantom extreme scatter (2 direct, or 1 upgrades a standard trigger), and the Tag Meter
(winning-spin streaks add spins and upgrade paint).

Full design + math spec: [DESIGN.md](DESIGN.md)

## SMUKIEZ animated character

The [Spine 4.2 V7 character package](character-assets/SMUKIEZ_Spine42_v7/README.md) includes editable skeleton JSON, cutout images, three atlas pages, a standalone preview, and ten animations: idle, anticipation, win, big_win, lose, cash_show, cash_count, cash_toss, enter, and exit.

[Download the complete ZIP](character-assets/SMUKIEZ_Spine42_v7.zip). Open the extracted `preview.html` locally to preview the animations. These assets are ready for integration; the game has not been changed to load them automatically.

## Layout

| path | what |
|---|---|
| `math-sdk/games/smukiez_tag_run/` | the math model: config, gamestate, forcing, events, reels, optimization targets |
| `math-sdk/games/smukiez_tag_run/library/publish_files/` | the verified build: books + optimized lookup tables + index.json (the Stake Engine upload set) |
| `beta/` | playable beta — local RGS stand-in (`server.py`) + no-framework client drawing real outcomes from the optimized tables |
| `docs/spec.html` | shareable systems/spec page |
| `math-sdk/` (rest) | vendored [StakeEngine/math-sdk](https://github.com/StakeEngine/math-sdk) @ `e2f0db9` (MIT — see `math-sdk/LICENSE`) |

## Run the playable beta

```
python -m venv .venv
.venv/Scripts/pip install -r req-local.txt
.venv/Scripts/pip install -e math-sdk
.venv/Scripts/python.exe beta/server.py
```

Open http://localhost:8722. First launch decompresses the books into a local cache
(~30s). Details, controls, and debug tricks: [beta/README.md](beta/README.md).

(`req-local.txt` is the SDK's `requirements.txt` minus its self-referencing git line;
the editable install of `math-sdk` replaces it.)

## Regenerate / retune the math

```
cd math-sdk/games/smukiez_tag_run
python run.py --base 100000 --bonus 20000 --extreme 20000 --threads 8 --optimize --analysis --checks
python verify_rtp.py      # weighted RTP of the optimized tables
python analyze_books.py   # payout distributions, Full Wall %, feature histograms
```

`--optimize` needs a Rust toolchain (`cargo`) on PATH. Reel strips regenerate
deterministically via `reels/gen_reels.py`. After regenerating, delete
`library/beta_cache/` so the beta picks up the new books.
