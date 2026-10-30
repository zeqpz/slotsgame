"""The game's five music cues: where each plays, what Lyria is asked for, and how build.py cuts it.

Every cue is instrumental and shares one world (owner, 2026-10-30: early-90s piano house and UK
rave with the tension of a heist score, "almost rave / dnb / house"): house at 125 BPM, rave at 174,
G minor, the win lifting to its relative major. Lyria takes the tempo but not the key, so takes were
kept for their key: the shipped ones are in art/music-src/ (G minor base and menu - the menu came
back at 120 BPM - C minor intro and bonus at 173.9, B-flat major total at 120).

  bars       the loop's length in bars (4/4)
  head       None: the cue is only the loop. A number: the take's opening plays once and the loop
             starts that many seconds in (snapped to the take's beat), cut from wherever after
             loop_from fits best; the opening keeps ringing under it for `tail` seconds (default 2)
  loop_from  seconds into the take before which no loop may start (past its intro)
  game_lufs  how loud the cue should sit in the game (the music bar at 100); sets its MUSIC level.
             The old loops sat at -24.4 (base) and -22.1 (bonus)
"""

CUES = {
    "base": {
        "where": "the base game",
        "bpm": 125, "bars": 32, "head": None, "loop_from": 0, "game_lufs": -24.5,
        "prompt": (
            "Instrumental only. Key: G minor. Tempo: 125 BPM. An early-1990s piano house track with UK rave energy and the cool tension "
            "of a heist-movie score. 125 BPM, G minor, 4/4. Punchy four-on-the-floor kick, crisp claps on 2 "
            "and 4, shuffled 16th-note hi-hats with open hats on the off-beats, a chopped breakbeat layered "
            "under the kick, a bouncy M1-style organ bassline, bright syncopated house piano chord stabs over "
            "Gm9 - Ebmaj7 - Cm9 - D7, a warm pad and a tense plucked synth arpeggio. Confident, stylish and "
            "driving with steady energy: background music for a slot game. Structure: [Short intro] -> "
            "[Main groove] -> [Main groove, piano and arpeggio variations] -> [Main groove]. "
            "No breakdown, no fade-out."),
    },
    "menu": {
        "where": "the bonus buy menu",
        "bpm": 125, "bars": 16, "head": None, "loop_from": 0, "game_lufs": -27,
        "prompt": (
            "Instrumental only. Key: G minor (G, B-flat, D). Tempo: 125 BPM. Mellow, filtered deep house: the same early-90s piano house world, heard "
            "quietly while a heist is being planned. 125 BPM, G minor, 4/4. Soft muffled kick, gentle shaker "
            "and rimshots, warm round sub bass, dreamy Rhodes electric piano chords over Gm9 - Ebmaj7 - Cm9 - "
            "D7, airy pads, a little vinyl warmth. Calm, suspenseful and classy, low energy but still grooving. "
            "The same relaxed groove from start to finish: no build-ups, no drops, no fade-out."),
    },
    "intro": {
        "where": "the YOU WON n FREE SPINS screen (waits for a click)",
        "bpm": 174, "bars": 8, "head": 5.59, "tail": .6, "loop_from": 10, "game_lufs": -23.5,
        "prompt": (
            "Instrumental only. Key: G minor. Tempo: 174 BPM. A 90s rave announcement for a bonus round: 174 BPM drum and bass in G minor. "
            "It opens instantly with a huge impact - a crash, a deep sub boom and a bright rave stab chord - "
            "then settles into a tense half-time anticipation groove that holds steady: a rolling breakbeat at "
            "low intensity, a reese bass drone on G, rave piano stabs, a fast sparkling synth arpeggio and "
            "atmospheric pads. Exciting, like the moment before a heist kicks off. Structure: [Impact] -> "
            "[Tense half-time groove, steady and repeating]. No big drop, no fade-out."),
    },
    "bonus": {
        "where": "the free spins",
        "bpm": 174, "bars": 32, "head": None, "loop_from": 0, "game_lufs": -22,
        "prompt": (
            "Instrumental only. A high-energy 90s jungle and drum and bass rave anthem for a slot bonus round. "
            "174 BPM, G minor. Fast chopped breakbeats with a rolling two-step kick and snare, a deep growling "
            "reese bassline over a clean sub, euphoric rave piano stabs over Gm - Eb - Cm - D, a hoover-style "
            "rave lead hook, shimmering pads, rides and crashes. Euphoric, exciting and relentless, like the "
            "getaway in a heist. Full energy from the first bar: [Drop] -> [Main section] -> [Main section with "
            "variations] -> [Main section]. No intro, no breakdown, no fade-out."),
    },
    "total": {
        "where": "the bonus's TOTAL WIN screen (waits for a click)",
        "bpm": 125, "bars": 8, "head": 8.64, "tail": 1.2, "loop_from": 15, "game_lufs": -22.5,
        "prompt": (
            "Instrumental only. A triumphant early-90s piano house anthem celebrating a huge win. 125 BPM, "
            "B-flat major, 4/4. It opens with a big celebratory hit - a crash cymbal, a rave stab chord and a "
            "fast piano glissando - then a joyful groove: four-on-the-floor kick, claps, open hats, a bouncing "
            "organ bassline, big gospel-house piano chords over Bb - F/A - Gm7 - Eb, lush string pads and "
            "sparkling bells. Uplifting, euphoric and victorious. Structure: [Celebration hit] -> [Joyful "
            "groove, steady and repeating]. No breakdown, no fade-out."),
    },
}
