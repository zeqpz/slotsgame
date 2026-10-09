# L10 - Lowrider. It sits nose-up on three wheels, so it hops on its hydraulics: the body
# pivots on the rear wheel, the nose kicks up and slams back, and the front wheel dangles on
# its suspension while the nose is in the air. Win: one big hop with a dust puff on the slam
# and the headlights glinting at the top.
REAR = (866, 692)          # the rear tyre's contact patch: the hydraulics pivot here
WHEEL = (205, 663)         # front wheel hub

RIG = {
    "id": "L10",
    "parts": [
        {"name": "wheel_f", "mask": ("ellipse", 205, 663, 75, 77), "pivot": WHEEL, "parent": "body", "fill": "body"},
        {"name": "body", "mask": "rest", "pivot": REAR},
        {"name": "puff", "sprite": "puff", "size": 26, "at": (170, 728), "hidden": True},
        {"name": "glint_a", "sprite": "sparkle", "size": 13, "at": (74, 498), "hidden": True, "parent": "body"},
        {"name": "glint_b", "sprite": "sparkle", "size": 15, "at": (352, 402), "hidden": True, "parent": "body"},
    ],
    "draw": ["body", "wheel_f", "puff", "glint_a", "glint_b"],   # the wheel hangs below the bumper, in front
    "anims": {
        # two hops of different heights, then a breath of stillness
        "idle": {"dur": 2.6, "bones": {
            "body": {
                "r": [(0, 0), (.18, -6, "out"), (.40, 1.5, "in"), (.55, -1.8, "out"), (.70, .6), (.86, 0),
                      (1.36, 0), (1.52, -3.5, "out"), (1.72, .8, "in"), (1.90, -.5), (2.10, 0)],
                "y": [(0, 0), (.18, 2.5, "out"), (.40, -.8, "in"), (.55, .6, "out"), (.86, 0),
                      (1.36, 0), (1.52, 1.4, "out"), (1.72, -.4, "in"), (2.0, 0)],
            },
            "wheel_f": {
                "y": [(0, 0), (.18, -2.2, "out"), (.40, .4, "in"), (.60, 0), (1.36, 0), (1.52, -1.2, "out"), (1.72, .2, "in"), (1.9, 0)],
                "sy": [(0, 1), (.38, 1), (.43, .92, "in"), (.56, 1.0, "out"), (1.70, 1), (1.74, .95, "in"), (1.86, 1)],
                "r": [(0, 0), (.18, -8, "out"), (.5, 3), (.9, 0), (1.36, 0), (1.52, -5), (1.9, 0)],
            },
        }},
        # dropped onto its wheels: sinks on the springs and comes back up
        "land": {"dur": .55, "bones": {
            "body": {"y": [(0, 0), (.10, -2.5, "in"), (.24, 1.0, "out"), (.40, -.3), (.55, 0)],
                     "r": [(0, 0), (.10, 1.2, "in"), (.26, -.8, "out"), (.42, .2), (.55, 0)]},
            "wheel_f": {"sy": [(0, 1), (.10, .9, "in"), (.24, 1.03, "out"), (.4, 1)]},
        }},
        "win": {"dur": 1.4, "bones": {
            "body": {"r": [(0, 0), (.25, -10, "out"), (.50, 2.5, "in"), (.68, -4, "out"), (.86, 1), (1.02, -1), (1.2, 0)],
                     "y": [(0, 0), (.25, 5, "out"), (.50, -1.5, "in"), (.68, 2, "out"), (.86, -.4), (1.2, 0)]},
            "wheel_f": {"y": [(0, 0), (.25, -3.5, "out"), (.50, .6, "in"), (.70, -1), (.9, 0)],
                        "r": [(0, 0), (.25, -14, "out"), (.6, 6), (1.0, 0)],
                        "sy": [(0, 1), (.48, 1), (.53, .88, "in"), (.66, 1.02, "out"), (.8, 1)]},
            "puff": {"sx": [(0, .5), (.48, .5), (1.0, 1.45, "out")], "sy": [(0, .5), (.48, .5), (1.0, 1.3, "out")],
                     "x": [(0, 0), (.48, 0), (1.0, -7, "out")], "y": [(0, 0), (.48, 0), (1.0, 2, "out")]},
            "glint_a": {"sx": [(0, .3), (.16, .3), (.32, 1.2, "out"), (.55, .2, "in")], "sy": [(0, .3), (.16, .3), (.32, 1.2, "out"), (.55, .2, "in")],
                        "r": [(0, 0), (.55, 90, "linear")]},
            "glint_b": {"sx": [(0, .3), (.22, .3), (.38, 1.25, "out"), (.62, .2, "in")], "sy": [(0, .3), (.22, .3), (.38, 1.25, "out"), (.62, .2, "in")],
                        "r": [(0, 0), (.62, -90, "linear")]},
        }, "alpha": {
            "puff": [(0, 0), (.48, 0, "step"), (.52, .95), (1.0, 0, "in")],
            "glint_a": [(0, 0), (.16, 0, "step"), (.26, 1), (.55, 0)],
            "glint_b": [(0, 0), (.22, 0, "step"), (.32, 1), (.62, 0)],
        }},
    },
}
