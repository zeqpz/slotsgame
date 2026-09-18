# SMUKIEZ V7

The regular hand pose stays in idle, anticipation, win, big_win, lose, and cash_show. Cash counting retains its timed pinch, flick, release, and re-grip. The new cash_toss uses one brief release pose and returns to the original grip.

The sleeve openings have been flattened to remove the oval underside. The upper arm remains behind the shirt, with the forearm and hands in front.

## Enter and exit

enter fades every slot from transparent to fully visible in 0.8 seconds, using an eased curve. exit reverses this and holds the character invisible at its end. Both are one-shot animations. Use controller.enter() to fade in then continue idle, and controller.exit() to fade out and stay hidden. Do not queue idle after exit. Ordinary clips explicitly restore full opacity. The preview stops at each fade endpoint and offers Replay.

These are native slot-alpha timelines, including all face, clothing, hand, leg, shoe, and money slots. Overlapping parts can become visible through one another during partial transparency, as with standard Spine alpha fades.

## New animation: cash_toss

A 4.2-second one-shot: wind-up, upward flick, three separate bills spinning and fluttering away while the remaining bills stay held, then settle. The stack resets at the end for repeatable slot reactions. Use the cash_toss animation or controller.cashToss(). A cash_toss event fires at 0.72 seconds for a sound cue. No sound or payout logic is included.

## Preview

Open preview.html manually and choose any of the ten clips. Enter is selected initially. Hand close-up, pause, speed, and scrubbing controls are available. cash_toss-preview.webp is an animated export; cash-toss-sequence.png shows its stages.

## Import

Extract the ZIP. In Spine 4.2, use Import Data with smukiez.json at scale 1, keeping images beside it. Save as a native .spine project after import. Mesh and IK support is required. This package supplies editable JSON, not a native .spine file.

For game playback use smukiez.json, smukiez.atlas, and all three smukiez*.png atlas pages with a Spine 4.2 runtime and straight alpha (pma: false). The optional slot-controller.js accepts your existing AnimationState. Reactions return to idle; cash_count can loop.

Hand and face changes are illustrated attachment swaps. Fingers are not individually bone-rigged. Cash toss reuses existing money artwork and bill meshes. Chin repairs, SMUKIEZ lettering, leg IK, fitted shoes, and one-bill-at-a-time counting remain included.

## Checks

Loaded and evaluated with the official Spine 4.2 runtime, including finite motion, animation endpoints, and transitions back to idle. Targeted checks cover steady hands, preserved cash count, three independently moving tossed bills, ordered keys, and restored bill attachments after playback. See validation.json. The Spine desktop editor and your game engine have not been tested.

The sleeve artwork was edited using the built-in image-generation tool. Prompts are recorded in artwork-notes.txt.
