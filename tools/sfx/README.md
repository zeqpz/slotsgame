# Sound effects pipeline (2026-11-03 pass)

How the 47 sound sets (`frontend/assets/sfx_<stem>_<n>.wav` + `.ogg`) were made. Kept here so the pass can be re-run;
the raw generations and review spectrograms were left out (rebuildable, ~140 MB).

- `gen.py` / `orapi.py` - generate takes with OpenRouter's Seed Audio model (key read from
  `Documents/gamdevkey.txt`; never printed). `newlist.txt` / `cand.json` - the prompts and the takes made.
- `clean3.py` (+ `report3.json`) - the final clean (2026-11-03, after the owner still heard hiss): noise profile from
  the take's own bed (not its silent padding), per-type high-pass, noisereduce stationary (+ non-stationary on
  transients), a hard gate to exact digital zero, trims at the gate, damage checks with gentler retries.
- `process.py`, `process2.py`, `audiolib.py` - the first clean: DC + high-pass, spectral gate from the take's own quiet
  stretches, cut into single events, tight start / natural tail, expander, slow-attack compression, loudness match,
  a -1.5 dBFS limiter, end fades.
- `pick_takes.py` (+ `picks.json`, `manual_picks.json`) - choose the best, most alike takes per set.
- `synth.py` - the sets made in numpy instead (paint drips, sparkles, glow, shine).
- `assemble.py` -> `final.json`, then `encode_new.js` (the same settings as `tools/encode_sfx.js`) for the Opus copies.
- `an_existing.py`, `spec.py` - loudness/noise analysis of the existing set, spectrograms for review.

Run with the venv at `ClaudeRoblox/smukiez-slot/.venv` (numpy, scipy, soundfile, noisereduce). The sets are registered
in `SFX_SETS` / `SFX_VOL` in `frontend/index.html`; `sfx(name)` picks a take other than the last and nudges its pitch.
