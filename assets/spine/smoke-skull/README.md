# Smoke Skull — Spine 4.2

Open **preview/index.html** in Edge or Chrome after extracting the ZIP. It works offline and includes animation controls, smoke toggle, playback speed, and mesh inspection.

The package has **five expressions, ten animations, 26 bones, 19 slots, and one 2048 × 2048 atlas image**. The original hands-in-pocket pose is retained. Shoes are 10% smaller, with independent foot taps and leg bends.

## Game import

Copy these three files together, keeping their filenames unchanged:

- smoke-skull.json
- smoke-skull.atlas
- smoke-skull.png

Use a Spine **4.2** runtime. The atlas uses straight alpha (pma: false) and linear filtering. Loose images are for editing and are not needed by the game runtime.

## Spine editor import

In Spine **4.2 Professional**, choose **Import Data**, select smoke-skull.json at scale 1, and keep the images/ directory beside it. The configured Images path is ./images/. Save the imported project as a native .spine file or export .skel if required.

This delivery is a JSON import and runtime package, not a native .spine project. Desktop editor import has not been tested here. Weighted meshes require Professional. [Import documentation](https://esotericsoftware.com/spine-import) · [Mesh documentation](https://esotericsoftware.com/spine-meshes)

## Animations

| Clip | Seconds | Playback | Behavior |
|---|---:|---|---|
| idle | 4.0 | Loop | Calm face, breathing, gentle feet |
| anticipation | 1.6 | Loop | Alert face and quicker alternating feet |
| win | 2.4 | Once | Confident grin, bounce and taps |
| big_win | 3.6 | Once | Laughing face with gold sparks and larger steps |
| lose | 2.0 | Once | Drooping face and head dip |
| ash_break | 2.4 | Once | Ash cap splits into four falling fragments |
| enter | 1.2 | Once | Rise and settle |
| exit | 0.7 | Once | Lower and fade |
| smoke_loop | 4.8 | Loop on track 1 | Curling plume and drifting wisps |
| ember_loop | 1.2 | Loop on track 2 | Additive ember pulse |

Play character clips on track 0, smoke on track 1, and ember on track 2. Queue idle after one-shot reactions. Fade the effect tracks before exit so their keys do not override its fade; the included controller handles this.

The face slot has face_idle, face_anticipation, face_win, face_big_win, and face_lose attachments. Animations choose them automatically. Expressions switch crisply, with skeletal movement within each pose. Event hooks: land, win_hit, big_win_hit, ash_split. No audio is included.

## Stake Engine / engine.io

The integration/ folder contains an asset entry, Svelte component, and animation controller. Adapt paths to your game. The manifest follows the SDK's type: 'spine' entry with src.atlas, src.skeleton, and src.scale. The component uses SpineProvider and SpineTrack.

[SDK asset example](https://github.com/engineio/web-sdk/blob/main/apps/lines/src/game/assets.ts) · [Component documentation](https://stakeengine-web-sdk.mintlify.app/api/spine)

Validated with official Spine/Pixi runtime 4.2.120 and PixiJS 8.20.1: sampled geometry, expression selection, loop endpoints, and transitions to idle. This has not been tested in your specific game project.

## Artwork

Original body pixels and the white sticker border are retained. Expressions, the clean cigar, secondary wisps, and ash use reconstructed artwork. Original cutouts remain for revision. Shared weights keep body cut edges together during restrained motion; substantially different poses would need more artwork. The origin is near the ground. Shoe reduction is a rig transform, so loose shoe images remain full size.

See ART-NOTES.md for artwork preparation. Runtime license notices are included in preview/.
