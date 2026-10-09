# Spray can drawing

Draws the spray can that paints a Multi's value on (see `art/fx-src/README.md`): a tall aerosol
can standing straight up, seen from directly behind, as hand-inked vector art in the icons' style.

    PLAYWRIGHT=<path to the playwright module> python tools/spray_can/make_can.py
    then copy tools/spray_can/can.png to art/fx-src/spray_can.png and the nozzle from
    tools/spray_can/meta.json into art/fx-src/spray_can.json, and run python tools/make_spray_fx.py

`make_can.py` builds `can.svg` (every ink line a filled shape of varying width, from `inkgeo.py`),
renders it with Chromium (`render.js`), adds the white sticker edge and snaps anti-aliased pixels
to the tint rule: paint parts are hue-134 greens around rgb(0, 255, 61), everything else neutral.
Its working files (can.svg, can_raw.png, can_pass0.*, can.png, meta.json) land next to it and are
not kept in the repo.
