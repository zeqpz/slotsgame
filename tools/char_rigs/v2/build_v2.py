"""Character rigs v2 (2026-10-27): SMUKIEZ and SMOKE SKULL redrawn and re-rigged.

  python tools/char_rigs/v2/build_v2.py [boy|skull] [--from seg|align|parts|rig|clips] [--fast]

Needs PIL, numpy, scipy and OpenCV (smukiez-slot/.venv has them) and Real-ESRGAN
(.tools/realesrgan; --fast uses a Lanczos resize instead). Intermediates go to paths.WORK
(%TEMP%/smukiez-chars-v2); the rigs are written to frontend/assets/spine/<name>/. About 10 minutes.

Why: the owner's review asked for the characters "redone and generated in a higher quality with
more body parts separated so the animations are smoother", with "no exposed gaps in between body
parts". The v1 rigs (tools/char_rigs/enhance.py) were cut from flat delivered illustrations; v2 is
drawn for rigging.

SOURCE ART (art/characters-src/v2, lossless WebP; every API call and its cost in ledger.jsonl)
openai/gpt-image-2.5-sunburst through OpenRouter, with the STYLE.md lighting fragment in every prompt:
- <who>/master: the character redrawn at quality "max" with a render of the v1 rig as the reference
  (refs/), in the v1 rig's frame (1024 x 1536), so the figure stands where it stood (IoU 0.96 with v1).
- <who>/partmap: the master as flat colours per body part (a segmentation prior).
- <who>/edits/*: the master with parts removed (the arms and money, the beanie, the pocket, the head,
  the jaw shut and open, the trouser cuffs raised, the shirt cropped): each reveals what is hidden
  behind those parts, drawn by the same hand. Aligned onto the master (ECC, IoU > 0.99 on the parts
  left alone).
- <who>/expressions/*: one per face the clips use, the old face as the second reference.
The generation scripts are here for provenance (genkit.py, prompts.py, partmap.py, gedits.py,
gextra*.py; key from %USERPROFILE%\\.smukiez\\openrouter-key.txt, never printed); a rebuild does
not call the API.

PIPELINE
- seg.py: the master's part labels: regions between the drawing's own lines take the part map's
  majority; ink goes to the front-most part next to it; cut lines split continuous cloth at the
  joints (segcfg*.py).
- align_all.py / align_expr.py: every edit and expression aligned onto the master.
- pk.py + boy_parts.py / skull_parts.py: every part complete and canvas-sized: visible pixels from
  the master (or the expression), hidden pixels from the edit that removed what was in front (only
  where that was), a 24 px run-on in the part's own colours under every part in front of it, outline
  rims moved to the part whose outline it is (no ghost lines when parts part), interiors solid.
- boy_bills.py: one complete bill (from the hands-removed edit) and a six-bill fan fitted to the master.
- rigbuild.py / rigkit.py + def_boy.py / def_skull.py: Spine 4.2 skeletons (38 / 39 bones), contour
  meshes whose weights come from smooth fields along each limb (shared by overlapping parts, so they
  bend as one), knee/elbow helper bones, arm IK to the hands, atlas pages at 1.1 px per unit.
- clips_boy.py / clips_skull.py + motionkit.py + legs.py: every clip re-authored with the same name,
  length, faces and beats: overlapping action down the spine and head chain, follow-through on the
  hat, the drawstrings, the laces and the bills, weight on landings; legs solved here (the drawing's
  legs are nearly straight, where a two-bone IK is singular); every reaction eases into idle's own
  motion so the game's 0.2 s crossfade into idle blends two identical poses.

VERIFY (verify/): filmcheck.js films every clip; gapcheck.py counts see-through pixels inside the
figure per frame; jerk.js measures per-bone acceleration under the game's own playback; gameshot.js
shoots the real game with the rigs frozen on one pose.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
STEPS = ['seg', 'align', 'parts', 'rig']


def run(*args):
    print('>>', ' '.join(args), flush=True)
    subprocess.run([PY, os.path.join(HERE, args[0])] + list(args[1:]), check=True, cwd=HERE)


def main():
    who = [a for a in sys.argv[1:] if a in ('boy', 'skull')] or ['boy', 'skull']
    start = sys.argv[sys.argv.index('--from') + 1] if '--from' in sys.argv else 'seg'
    fast = ['--fast'] if '--fast' in sys.argv else []
    todo = STEPS[STEPS.index(start if start != 'clips' else 'rig'):]
    for w in who:
        if 'seg' in todo: run('seg.py', w)
        if 'align' in todo: run('align_all.py', w); run('align_expr.py', w)
        if 'parts' in todo:
            if w == 'boy': run('boy_bills.py'); run('boy_parts.py')
            else: run('skull_parts.py')
        if 'rig' in todo:
            run('runbuild.py', w, *fast, *(['--clips-only'] if start == 'clips' else []))


if __name__ == '__main__':
    main()
