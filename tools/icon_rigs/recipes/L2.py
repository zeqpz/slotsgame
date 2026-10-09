# L2 - Graffiti marker. The orange line is the marker's own stroke, so the marker writes it:
# the line wipes away and is drawn back on in the order it was scribbled (five passes, top
# right to bottom left) while the marker scribbles along with it. Land: the marker rocks.
# Win: a fast, bold redraw with the marker punching up.
MARKER = ("poly", [(706, 100), (758, 66), (926, 186), (914, 246), (474, 826), (452, 840), (398, 884),
                   (306, 968), (160, 890), (208, 792), (236, 724), (290, 642)])
STROKE = ("minus", ("grow", ("color", "#ff9200", 70), 3), ("grow", MARKER, 6))   # grown 3px: the soft edge goes with the stroke
# the stroke's centre line, in the order it was drawn
PATH = [(575, 100), (420, 140), (280, 195), (165, 270), (175, 330), (300, 335), (450, 295), (575, 250),
        (500, 320), (390, 430), (260, 520), (165, 590), (190, 650), (330, 660), (520, 640), (700, 600),
        (820, 610), (855, 670), (720, 730), (560, 790), (420, 850)]
N = 12                                     # slices of the stroke
SLICES = [f"s{i + 1:02d}" for i in range(N)]

parts = [{"name": s, "mask": ("along", STROKE, PATH, i / N, (i + 1) / N), "pivot": (500, 500)} for i, s in enumerate(SLICES)]
parts.append({"name": "marker", "mask": "rest", "pivot": (545, 515)})


def draw_on(start, span, each=.12, gone=.0, fade=.2):
    """alpha keys for every slice: fade out together, then appear one after another."""
    out = {}
    for i, s in enumerate(SLICES):
        t = start + span * i / N
        out[s] = [(0, 1), (gone + fade, 0, "in"), (t, 0, "step"), (t + each, 1, "out")]
    return out


def scribble(start, span, amp_x=2.6, amp_r=2.4, drift_y=5.0):
    """the marker rides the passes: across and back five times, working down the wall"""
    xs, rs, ys = [(0, 0), (start, 0)], [(0, 0), (start, 0)], [(0, 0), (start, 1.6)]
    passes = 5
    for k in range(passes):
        t = start + span * (k + .5) / passes
        sgn = -1 if k % 2 == 0 else 1
        xs.append((t, sgn * amp_x, "inout")); rs.append((t, -sgn * amp_r, "inout"))
    end = start + span
    ys.append((end, 1.6 - drift_y, "inout"))
    xs.append((end + .25, 0, "out")); rs.append((end + .25, 0, "out")); ys.append((end + .35, 0, "out"))
    return {"x": xs, "r": rs, "y": ys}


RIG = {
    "id": "L2",
    "parts": parts,
    "draw": SLICES + ["marker"],
    "anims": {
        "idle": {"dur": 2.5, "bones": {"marker": scribble(.32, 1.45)}, "alpha": draw_on(.32, 1.45)},
        "land": {"dur": .55, "bones": {"marker": {"r": [(0, 0), (.1, -3.4, "out"), (.26, 2.2), (.42, -.6), (.55, 0)],
                                                  "y": [(0, 0), (.08, -1.4, "in"), (.22, .6, "out"), (.4, 0)]}}},
        "win": {"dur": 1.5, "bones": {"marker": dict(scribble(.18, .85, amp_x=3.4, amp_r=3.2),
                                                     sx=[(0, 1), (.12, 1.08, "out"), (1.1, 1.05), (1.4, 1)],
                                                     sy=[(0, 1), (.12, 1.08, "out"), (1.1, 1.05), (1.4, 1)])},
                "alpha": draw_on(.18, .85, each=.08, fade=.14)},
    },
}
