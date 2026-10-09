# Effect art sources

Full-size sources for art that is not a symbol. `tools/make_spray_fx.py` turns them into what the
game ships in `frontend/assets/fx/`.

| Source | Shipped as | Used by |
| --- | --- | --- |
| `spray_can.png` (1000 px) + `spray_can.json` | `spray_can_<hue>.webp`, 480 px tall, one per heat hue | the can that sprays a Multi's value onto its brick (`sprayMulti` in `frontend/index.html`) |
| `spray_puff.png` (drawn by the script) | `spray_puff_<hue>.webp`, 256 px wide, one per heat hue | the cartoon puffs of paint the can blows out while it sprays |

The can itself is drawn by `tools/spray_can/` (see its README).

## The spray can

Its own design, not the L1 symbol's can: a tall aerosol can standing straight up, seen from directly
behind. Its nozzle points into the picture, at the wall it is about to paint, so we see the plain
back of the spray button (no nozzle hole), with paint caked on the button's far lip. Same ink,
flat colour, hatching and white sticker edge as the symbols.

`spray_can.json` holds `nozzle`, the source-pixel point the spray comes out of. After a change,
run the script and copy the `canSize` and `nozzle` it prints into `SPRAY` in `frontend/index.html`.

## Colour

Both pictures are painted in L1's exact green, `rgb(0, 255, 61)`. `tools/make_spray_fx.py` turns
that green to the heat colour of every Multi value (the values and the heat scale are read out of
`frontend/index.html`), keeping saturation and brightness, and ships one WebP per hue. Greys, cream,
ink and white are left alone. Keep anything that should take the paint's colour in that green, and
anything that should not out of the green range.
