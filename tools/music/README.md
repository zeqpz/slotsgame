# Music (2026-10-30)

Five cues, generated with Google's Lyria 3 Pro through OpenRouter and cut into seamless loops for
the game: the base game, the bonus buy menu, the YOU WON n FREE SPINS screen, the free spins and
the bonus's TOTAL WIN. Instrumental, early-90s piano house and UK rave with heist-score tension.

| cue   | take (art/music-src/) | key       | tempo | in the game                                          |
|-------|-----------------------|-----------|-------|------------------------------------------------------|
| base  | base.mp3              | G minor   | 125   | 32-bar loop, resumes where it left off                |
| menu  | menu.mp3              | G minor   | 120   | 16-bar loop while the buy menu is open                |
| intro | intro.mp3             | C minor   | 174   | impact and build (5.6 s, once), then an 8-bar loop    |
| bonus | bonus.mp3             | C minor   | 174   | 32-bar loop, drops in on the intro's next beat        |
| total | total.mp3             | B-flat    | 120   | celebration hit (8.6 s, once), then an 8-bar loop     |

## Regenerate

```
python tools/music/lyria.py base --takes 3     # takes -> %TEMP%/music_gen/base/ (~$0.08 each)
copy %TEMP%\music_gen\base\<take>.mp3 art\music-src\base.mp3   (and its .json)
python tools/music/build.py base --wav         # cut + encode -> frontend/assets/music_base.ogg/.aac
```

`build.py` prints the cue's `MUSIC` entry; paste it over the old one in `frontend/index.html`.
`--wav` also writes `%TEMP%/music_build/<cue>.wav` (the head, then the loop twice) to listen to.
Runs on `.venv312` (numpy, scipy, PyAV). The key is read from
`%USERPROFILE%\.smukiez\openrouter-key.txt`, as `tools/icon_redraw` does.

## Things the first round taught

- Lyria follows the tempo it is asked for (within ~4%) but **not the key**: of 15 takes, the keys
  were all over. Takes were picked for their key so the cues crossfade without clashing; check
  with a chroma readout before keeping one. A prompt can come back `PROHIBITED_CONTENT` once and
  pass the next time.
- OpenRouter returns MP3 (44.1 kHz, 192 kbps) whatever format is asked for; `build.py` resamples to
  48 kHz.
- The beat grid can lock onto house's off-beat open hats: `beat_grid` moves half a beat when the
  kick lines up there clearly better. Downbeats come from the claps on 2 and 4 plus where the
  arrangement changes (not chord changes alone: house piano pushes its chords a beat early).
- Seams are chosen by the spectrum in dB and the chroma either side of the junction, then lined up
  on the drum transients. A cue with a head keeps the head's beat of the bar, so the loop carries
  on its meter.
- Opus decodes to the exact frame count in Chrome; FFmpeg's AAC puts 1024 frames of encoder delay
  in front, which `aacStart` covers (checked in Chrome: offset error 0 for every cue).
