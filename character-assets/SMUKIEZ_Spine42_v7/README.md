# SMUKIEZ V7

The regular hand pose stays in idle, anticipation, win, big_win, lose, and cash_show. Cash counting retains its timed pinch, flick, release, and re-grip. Cash toss uses the left hand for the flick and release, then the right hand retrieves a fresh stack from the pocket.

The sleeve openings have been flattened to remove the oval underside. The upper arm remains behind the shirt, with the forearm and hands in front.

## Enter and exit

Enter and exit match Smoke Skull's movement and timing. Enter rises from 100 units below the resting position, grows from 88% to full size, fades in during the first 0.18 seconds, and settles over 1.2 seconds with a small head and foot movement. Exit lowers by 75 units and shrinks to 88% over 0.7 seconds, with a fade beginning at 0.15 seconds.

Both are one-shot animations. Use controller.enter() to enter and continue into idle, and controller.exit() to exit and stay hidden. The preview now follows the same behavior: enter automatically selects idle, while exit holds its invisible endpoint and offers Replay. Ordinary clips restore root position, scale, and opacity, including when interrupting exit. Enter includes the same land event at 0.5 seconds as Smoke Skull.

These are native Spine bone and slot-alpha timelines. The existing IK rig, artwork, and other animation movements are preserved. Overlapping parts can show through during partial transparency, as with standard Spine alpha fades.

Rebuild and validate these transitions with `node tools/match_smukiez_transitions.cjs` from the repository. It uses the bundled official Spine runtime; no package install is required. See transition-validation.json for the latest checks.

## Cash toss: full stack and right-pocket refill

A 6.8-second one-shot. All six bills leave the stack and fall downward along varied paths, fading gradually for 2.6 seconds. Their vertical position decreases throughout flight; sideways flutter varies between the four patterns. The left forearm and hand wind up, flick the stack, and open at release before returning to rest. The right hand starts reaching down at 0.15 seconds, during the left-hand toss. It keeps a closed grip throughout the reach, without an opening or flick gesture. The jeans render over the right hand and lower forearm during entry and while inside the pocket; normal layer order returns once the hand is lifted clear. A fixed right bicep and a rigid forearm meet at an elbow hinge; only the forearm and hand move. The wrist stays attached at a constant distance from the elbow; the right hand swings inward to the left into the pocket, pauses inside, and draws a fresh stack back into the holding pose. A full-palm gripping pose replaces the fingers-only artwork during the reach; these reuse mirrored matching hand artwork from the existing atlas. The arm uses anatomically tapered mesh sections with a fuller upper arm, rounded elbow, narrower wrist, outline, and shading, sampling skin color from the existing atlas. Each section is attached to a single bone, so it cannot stretch or bend internally. The arm origin is shifted left and layered beneath the shirt sleeve. The bicep is fixed to the torso; the forearm rotates around the elbow, and the hand follows its endpoint. It appears only for cash toss.

The preview and `controller.cashToss()` randomly choose between four scatter patterns on each play. The main `cash_toss` clip and `cash_toss_alt_1`, `cash_toss_alt_2`, and `cash_toss_alt_3` share the same reach and refill. Direct playback of one named Spine clip uses that clip's fixed pattern. The ten main actions remain in the preview menu; the three scatter variants are selected internally.

Cue events: `cash_toss` at 0.72 seconds, `pocket_reach` at 1.35 seconds, and `cash_refill` at 4.25 seconds. No sound or payout logic is included. The controller returns to idle, and interrupting the clip restores the stack and normal layer order.

Rebuild from the repository with `node tools/build_smukiez_cash_toss.cjs`, then run the same command with `cash_toss_alt_1 72931`, `cash_toss_alt_2 39017`, and `cash_toss_alt_3 89263` as arguments. The tool uses the bundled official Spine 4.2 runtime. See cash-toss-validation.json for checks. `cash_toss-preview.webp` and `cash-toss-sequence.png` show the main scatter pattern.

## Preview

Open preview.html manually and choose any of the ten clips. Enter is selected initially. Hand close-up, pause, speed, and scrubbing controls are available. cash_toss-preview.webp is an animated export; cash-toss-sequence.png shows its stages.

## Import

Extract the ZIP. In Spine 4.2, use Import Data with smukiez.json at scale 1, keeping images beside it. Save as a native .spine project after import. Mesh and IK support is required. This package supplies editable JSON, not a native .spine file.

For game playback use smukiez.json, smukiez.atlas, and all three smukiez*.png atlas pages with a Spine 4.2 runtime and straight alpha (pma: false). The optional slot-controller.js accepts your existing AnimationState. Reactions return to idle; cash_count can loop.

Hand and face changes are illustrated attachment swaps. Fingers are not individually bone-rigged. Cash toss reuses existing money artwork and bill meshes. Chin repairs, SMUKIEZ lettering, leg IK, fitted shoes, and one-bill-at-a-time counting remain included.

## Checks

Loaded and evaluated with the official Spine 4.2 runtime, including finite motion, animation endpoints, and transitions back to idle. Targeted checks cover steady hands, preserved cash count, three independently moving tossed bills, ordered keys, and restored bill attachments after playback. See validation.json. The Spine desktop editor and your game engine have not been tested.

The sleeve artwork was edited using the built-in image-generation tool. Prompts are recorded in artwork-notes.txt.
