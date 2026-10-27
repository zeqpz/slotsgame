# Smukiezs Mural - art direction (2026-10-27)

One look for every picture in the game: icons, UI, characters, effects. Written after the
review notes "symbol hierarchy impossible to tell", "theme mismatch everywhere (blue flaming UI,
neon green background)", "UI needs redrawing with higher detail", "characters need redoing".

## Look

A hand-inked cartoon sticker in a streetwear / graffiti style, drawn by a professional: bold,
confident black outlines with varied line weight (heavier on the outside edge and on the shadow
side), rich form shading, fine material texture where it fits (fabric weave and stitching,
leather grain, brushed or worn metal, paper fibre, spray-paint grain), and small extra details.
Every cut-out object keeps a thick, even white die-cut sticker border around its outer silhouette
(the symbol tiers below change its colour).

## Lighting - the same for every image

- **Key light:** upper left, in front of the subject (about 45 degrees up and 45 degrees left).
  The lit side of every form faces up-left; speculars sit on the upper-left of shiny forms.
- **Fill:** soft and from the front, so the shadow side stays readable.
- **Rim light:** a thin, cool, pale cyan-white rim (#CFF6F6) along the right and lower-right
  edges, the neon wall behind the board.
- **Shadows:** core shadows and ambient occlusion on the lower-right side and in creases where
  parts meet; any cast shadow falls down and to the right.
- No other light sources, no coloured scene lighting baked into the art (the game adds its own
  glows at runtime).

Prompt fragment to paste into every generation:

> Lighting: one key light from the upper left, in front of the subject; soft front fill; a thin
> cool pale-cyan rim light along the right and lower-right edges; core shadows and ambient
> occlusion on the lower-right side and in creases; any cast shadow falls down and to the right.

## Palette - neon graffiti at night

Taken from the wall tag, the BONUS logo and the FS / XFS letters. Electric blue is retired.

| role | colours |
|---|---|
| ground | charcoal brick and concrete: #18171c, #24222a, #34313b |
| primary accent: neon lime | #9CE424 (paint), #6CFC54 (neon glow), #E4FC84 (hot highlight), #3C6C0C (shade) |
| secondary accent: violet | #B454E4 (paint), #6C24B4 (deep), #E4B4FC (highlight), #3C0C6C (shade), #E484CC (pink tint, sparingly) |
| wins and money | gold #F5C518, warm highlight #FFE58A, shade #8A5A00 |
| ink | black #0b0a0d outlines, white #ffffff sticker borders and lettering |
| tiny highlight only | pale cyan #9CE4E4 (the tag's inner light, the rim light) |

UI frames, panels and buttons: dark charcoal plates with violet spray-paint edges and neon-lime
trim / glow. Gold is for amounts and wins only.

## Symbol tiers (readable at a glance, not only by colour)

Every icon keeps the plain white sticker border (the owner turned down gold / chrome edges as off
style). The paying tiers wear an animated neon glow round the sticker in the theme colours, drawn
by the game, not baked into the art:

| tier | symbols | treatment |
|---|---|---|
| top | H1 Bag of Cash, H2 Glock, H3 Gold Chain | the strongest glow: neon lime tube light with a violet halo, pulsing |
| premium | H4 Kicks, H5 Boombox, H6 Skateboard, H7 Drop Box | a violet neon glow, pulsing more quietly |
| low | L1-L10 | no glow |
| special | M Multi, BS / ES scatters | their own art and effects (sprayed value, dripping letters) |

## Generation

- Model: `openai/gpt-image-2.5-sunburst` through OpenRouter's Images API
  (`POST https://openrouter.ai/api/v1/images`), `quality: "high"`, `background: "transparent"`
  for cut-outs, the current art as the `input_references` image so a redraw keeps the drawing.
- Key: `%USERPROFILE%\.smukiez\openrouter-key.txt` (never print it, never put it in the repo).
  The key has a $50 limit shared by everyone working on this; log every image's `usage.cost`.
- Keep compositions where they are when the art is rigged (icons, characters): the rigs cut parts
  by position, so a redraw that moves things means re-fitting the rig.
