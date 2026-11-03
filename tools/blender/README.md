# Symbol animations, made in Blender

Every board symbol's animations are made **in Blender**: a 2D cut-out rig (the icon cut into parts, a bone per
part, chains of bones in parts that bend), four clips keyed on it, effects drawn frame by frame in Grease Pencil,
a glow bloomed by Blender's compositor - rendered to frames the game plays as they are. The owner's rules
(2026-11-02): everything is made in Blender (no Spine - not owned; no CSS animation; no animation coded in the
game); each symbol gets its own idle, land, hit and multiplier animation; highest quality; 30 fps; more effects
than before; the paying tiers' glow made in Blender and more artistic than an outline. H1 (bag of cash) is the
finished example: `cuts/H1.py`, `anim_H1.py`, `art/blender/symbols/H1.blend`, `art/blender/qa/H1/`.

## The steps (one symbol, `<ID>`)

Python: `C:\Users\CooperHinkel\Documents\ClaudeRoblox\smukiez-slot\.venv\Scripts\python.exe` (numpy, scipy,
PIL, cv2). Blender: `C:\Users\CooperHinkel\Blender\blender-5.2.3-windows-x64\blender.exe`.

1. **Cut config** `tools/blender/cuts/<ID>.py` - what Blender's cut changes from the old rig recipe
   (`tools/icon_rigs/recipes/<ID>.py`: its part masks, pivots, parents, draw order are the starting point):
   - `PLATE_PROMPT` - for the clean plate: the same picture with the moving front parts taken away and what was
     behind them painted in. More plates if moving parts overlap: `PLATES = {"name": prompt}`.
   - `DROP` recipe parts left out (old patches, code-drawn bits).
   - `SPLIT = {part: [pieces]}` - cut a part into pieces along a polyline (`line`, `side` above/below), each a
     separate moving piece; `chain` (icon px, root first) makes it bend on a chain of bones; `rim: True` gives
     each piece its own sticker border as a part drawn behind all the pieces; `ink` draws a new ink edge where it
     was cut from its neighbour; `tuck` (px) runs the piece behind on under the one in front (no crack).
   - `FILLS` - where a part takes the plate's pixels (the area a moving part uncovers), `above`/`below`/`left`
     limits, `blend: "matched"` for opaque areas (colour-matched to the part round the patch), `plate: name`.
   - `CLEAR` - wipe a region from a part (`plate_clear: px` = only where the plate is empty that far from it).
     Use it to trim a part that is a copy laid over others (H1's tie) so it carries no frozen copy of a moving
     part.
   - `ISLANDS` - drop small cut-off bits; `ANCHOR = {part: {"bone": holder, "y0", "y1"}}` - a part held at its
     foot (weighted to the holder below y0, to its own bone above y1).
2. **Plate** `python tools/blender/plate.py <ID> [name]` -> `art/blender/plates/<ID>[_name].png` (OpenRouter
   gpt-image, ~$0.06; the key is read from `%USERPROFILE%\.smukiez\openrouter-key.txt`, never printed). LOOK at
   it next to the art before using it: same drawing, the parts gone, clean painting where they were.
3. **Parts** `python tools/blender/dump_parts.py <ID>` -> `art/blender/parts/<ID>/` (PNG per part, parts.json),
   then `python tools/blender/qa_parts.py <ID> <movers,comma,separated>` -> `art/blender/qa/<ID>_parts.png`:
   the parts laid back together must match the art ("rest vs art" ~2/255 mean), and the composite WITHOUT the
   movers must be clean (no blur, no ghost borders, no holes). Zoom into every junction (crop at 3-4x).
4. **Glow path** (tier symbols) `python tools/blender/outline.py <ID> 9 --plate` -> `outline_plate.json`.
5. **Animation** `tools/blender/anim_<ID>.py` (copy the shape of `anim_H1.py`). It must set
   `arm["clips"] = {"idle": [f0, f1], ...}` and end with `fxkit.save(SID)`.
6. **Run** in a background Blender (never the owner's open Blender / the MCP socket):
   `blender.exe -b --factory-startup --python tools/blender/run.py -- <ID> [build,anim,render,qa]`
   (needs the sandbox off). ~3 min a symbol. Several can run at once.
7. **Check** `python tools/blender/qa_clips.py <ID> <x0,y0,x1,y1 of the joints to zoom, icon px>` ->
   `art/blender/qa/<ID>/`: `<clip>_sheet.jpg` (every frame), `<clip>_zoom.jpg` (joints at 2x on the frames that
   move most), `<clip>.webp` (playing), `report.txt`. READ the zooms and sheets yourself - every clip, every
   time - and fix what shows before calling it done (owner: "Everytime you make a animation quality check it").

## Rig conventions (build_symbol_scene.py)

- 100 icon px = 1 Blender unit; the icon is centred on the origin (x right, z up); the camera looks along +y,
  orthographic, 13 units across (room for motion and effects). `fxkit.px(x, y)` turns icon px into (x, z).
- Bones: `rotation_euler.z` = turn in the picture, counter-clockwise positive (degrees in `fxkit.key`);
  `location` x / y = screen right / up (units); `scale` x / y. A rigid part rides its bone; a chain part bends
  (Armature modifier, weights blended 48 px across each joint); its rim uses the same bones.
- Draw order = depth: each step 0.1 units toward the camera (Eevee sorts the see-through parts by distance).
  Effects drawn on the art layer go in front of every part (y -1.0 and nearer).
- Keys: `fxkit.key(arm, bone, f, x=, y=, r=, sx=, sy=, s=)`, `fxkit.rest(...)`, one Action per clip
  (`begin_action` / `end_action` put it on the rig's NLA track "clips"), `fxkit.hard(...)` for a key that is
  hit, not eased into (a landing). Loops: `fxkit.make_cyclic(act)` (Cycles modifier: the ends join smoothly).
- Hanging / trailing parts (ropes, laces, straps, drips, flaps, cloth): `fxkit.secondary(...)` - point masses on
  springs driven by how the holder bone really moves in the clip; per chain `freq` (Hz, softer to the tip),
  `zeta`, `gain`, `limit` (soft cap per joint, degrees), `stretch` / `stretch_limit`; per clip `gain`,
  `forces(name, i, t)` (a breeze, a charge). Results keyed sparsely with `fxkit.key_series`. A loop starts
  exactly at rest (`rest_start`). Different parts get different weights/springs so they move separately.

## Clip rules

- 30 fps. idle = a seamless loop (72 frames is H1's; pick what suits), starting at rest. land / hit / multi
  start and end exactly on the rest pose (qa_clips checks: "vs rest 0.000") so the game can chain them.
- Each clip unique per symbol, and each symbol unique: land = the symbol dropping onto the reel; hit = it is
  part of a win (the big one); multi = a multiplier lands on / powers it (charges up and releases). Idle is calm
  (it plays on every symbol on the board at once).
- Squash and stretch, anticipation, follow-through, overlap; nothing leaves the 13-unit frame (a sprite is
  clipped at its frame).

## Effects and glow

- Three view layers: `art` (rig + parts + effects that sit on the art: dust, thrown pieces), `fxb` (behind the
  art, bloomed), `fx` (over the art, bloomed). `fxkit.layers()` + `fxkit.glow_compositor()` set them up.
- Grease Pencil drawn frame by frame with `fxkit.Board` (`add(frame, fn, hold)`, `draw(layer)`; `hold=2` = on
  twos). Ready-made: `sparkle`, `dust` (cartoon puffs: solid, swell then shrink - never fade to grey),
  `starburst`, `shock_rings`, `streaks`, `lightning`, shapes `star`, `ring`, `puff`, `zigzag`.
- The tier glow (art/STYLE.md "Symbol tiers"): `fxkit.neon(SID, arm, FXB, CLIPS, tier=...)` - tier 1 (H1-H3):
  violet backlight, lime comets, lime floods in when struck; tier 2 (H4-H7): violet, quieter, pink charge.
  Low symbols (L1-L10) and the specials (M, BS, ES) wear no tier glow: their effects are their own.
- Colours: `fxkit.LIME, VIOLET, WHITE, GOLD, PINK`; the game's neon is lime + violet.

## Blender 5.2 gotchas (all cost hours on H1)

- Grease Pencil fills are per stroke: `stroke(..., fill=True, line=False)` (fxkit sets `fill_id` / `hide_stroke`);
  the material's show_fill / show_stroke are ignored. `drawing.tag_positions_changed()` after setting points
  (Board.draw does it). GP is lit by scene lights unless turned off (fxkit.gp_object / gp_layer do) - with no
  lights it renders BLACK. Stroke `softness` thins the line to a hairline: build soft glows from stacked strokes.
- Compositor: node group on `scene.compositing_node_group`; AlphaOver inputs "Background"/"Foreground"; Glare
  settings are input sockets (Type "Bloom").
- Actions are slotted: F-curves in `act.layers[].strips[].channelbags[].fcurves` (`fxkit.fcurves(act)`).
- Set an object's `matrix_world` after parenting it to a bone; `location` then reading `matrix_world` is stale
  until a depsgraph update.

## What went wrong on H1, and the fix (check every symbol for these)

| defect | cause | fix |
|---|---|---|
| blur smudge where a part moved off | the old recipe filled hidden areas with a push-pull blur | clean plate + `FILLS` over exactly the hidden area |
| ghost of a border left in the air | the old cut left a moving part's border on the part under it | plate fill / `CLEAR` with `plate_clear` / `ISLANDS` |
| seam where a moving part meets a static copy | a part laid over others (the tie) held a frozen copy of the moving part | `CLEAR` the copy back to its own outline |
| hairline crack between two moving pieces | texture filtering softens both cut edges | `tuck` the piece behind under the one in front; rims reach 2 px under their piece |
| a part vanishing on some frames | two parts at the same depth | depth step 0.1 per draw step (build_symbol_scene) |
| effects black / fills missing | GP lights; per-stroke fills | see gotchas |
| grey dirty dust / dim rays | fading to low opacity over a dark board | shrink or thin to nothing instead of fading |
| rubbery ropes | raw cartoon accelerations | per-clip `gain`, `limit`, more damping |
