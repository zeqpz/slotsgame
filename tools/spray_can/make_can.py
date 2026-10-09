"""The spray can that paints a Multi's value on: a tall aerosol can standing straight up, seen
from directly BEHIND - its nozzle points into the picture, at the wall - drawn as hand-inked
vector art in the icons' style. (Final pass over judged candidate A.)

  python make_can.py            -> can.svg, can_raw.png (Playwright), can.png (+ sticker edge), meta.json

Every ink line is a filled shape of varying width (inkgeo.py). Paint-coloured parts are hue-134
greens around the key green rgb(0,255,61) so the game's tintGreen() can re-colour them; metal,
the charcoal spray button, the label, ink and the white sticker edge are pure neutrals. After
rendering, enforce_rule() snaps every anti-aliased pixel that is green-led but too grey for
tintGreen (spread < 48) either up to the tint threshold (same hue) or down to a neutral grey.

Facing-away cues: the spray button (a charcoal actuator with a rounded top) shows only its plain
back - no nozzle hole - and the paint that has caked round the nozzle crusts its FAR lip and
runs back over the top and down the side facing us.
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from inkgeo import (outline_ring, ribbon, sliver, ellipse_pts, chaikin, resample, d_of, d_ring, arr)

NODE = 'node'
SIZE = 1000

# ---------- palette ----------
G = 'rgb(0,255,61)'          # the key green: the paint
GH = 'rgb(120,255,152)'      # its highlight (same hue 134; saturated enough that its blends with ink stay tintable)
GS = 'rgb(0,170,40)'         # its shadow (same hue 134)
M = 'rgb(186,186,186)'       # metal
MH = 'rgb(228,228,228)'
MS = 'rgb(126,126,126)'
LB = 'rgb(204,204,204)'      # the label: a mid-light neutral grey so yellow / lime paint still reads on it
LH = 'rgb(224,224,224)'
LS = 'rgb(160,160,160)'
A = 'rgb(76,76,76)'          # the spray button: charcoal plastic
AH = 'rgb(122,122,122)'
AHH = 'rgb(166,166,166)'
AS = 'rgb(44,44,44)'
INK = 'rgb(0,0,0)'

# ---------- geometry (source px, y down) ----------
cx = 500.0
k = 0.2                      # ellipse ry/rx: seen from a touch above eye level
R = 135.0                    # body radius
yS, hb, Rb = 330.0, 10.0, R + 9          # top rolled seam bead
yD0, R1, Rc, Hd = yS - hb, R + 1, 62.0, 84.0   # dome: base y, base r, top r, height
yCb, yCt, Rcup = 245.0, 224.0, 66.0            # valve cup (rolled ring the actuator sits in)
yAb, yAs, Rbt = 226.0, 186.0, 54.0             # actuator: base (front arc centre), top of its side wall, radius
rtA, HtA = 27.0, 19.0                          # actuator's rounded top: flat-ish crown radius, rise
yBe, yBb, Rbb = 848.0, 872.0, R + 6            # body bottom edge / bottom bead
yL, yLb = 470.0, 592.0                          # label band top / bottom (front-arc centres): ~24% of the body

# outline weights: the silhouette stays >= 12 px on the lit side, ~16-20 px in shadow (L1's weight)
SIL = dict(bias=.42, amp=.2, wls=(64, 140, 290), wob=1.4)

els, defs = [], []


def P(d, fill, clip=None, rule=None):
    a = f' clip-path="url(#{clip})"' if clip else ''
    r = f' fill-rule="{rule}"' if rule else ''
    els.append(f'<path d="{d}" fill="{fill}"{a}{r}/>')


def group_open(clip):
    els.append(f'<g clip-path="url(#{clip})">')


def group_close():
    els.append('</g>')


def clip(cid, d, rule=None):
    r = f' clip-rule="{rule}"' if rule else ''
    defs.append(f'<clipPath id="{cid}"><path d="{d}"{r}/></clipPath>')


def ring(poly, base, seed, **kw):
    o, i = outline_ring(poly, base, seed, **kw)
    P(d_ring(o, i), INK, rule='evenodd')


def line(pts, w, seed, clipid=None, **kw):
    P(d_of(ribbon(pts, w, seed=seed, **kw)), INK, clipid)


def hatch(p0, p1, w, bow=0.0, seed=0, color=INK, clipid=None, kind='stroke'):
    P(d_of(sliver(p0, p1, w, bow, seed, kind)), color, clipid)


def front_arc(cy, r, x0=None, x1=None, n=None):
    """The near half of a horizontal ellipse, left to right."""
    pts = ellipse_pts(cx, cy, r, k * r, 180, 0, n)
    if x0 is not None:
        pts = pts[(pts[:, 0] >= x0) & (pts[:, 0] <= x1)]
    return pts


def band_poly(y_top, y_bot, r):
    """A cylinder band's silhouette: back arc of its top ellipse, sides, front arc of its bottom."""
    top = ellipse_pts(cx, y_top, r, k * r, 180, 360)
    bot = ellipse_pts(cx, y_bot, r, k * r, 0, 180)
    return np.vstack([top, bot])


def full_ellipse(cy, r, ry=None, x=None):
    return ellipse_pts(cx if x is None else x, cy, r, k * r if ry is None else ry, 0, 360)[:-1]


def arc_y(x, cy, r):
    dx = np.clip(np.asarray(x, float) - cx, -r, r)
    return cy + k * np.sqrt(np.maximum(r * r - dx * dx, 0))


def lens_band(x0, x1, ya, yb, taper=.18, wob=0.0, seed=0):
    """A vertical highlight band from x0..x1 between ya and yb, pointed at both ends."""
    rng = np.random.default_rng(seed)
    ys = np.linspace(ya, yb, 80)
    u = (ys - ya) / (yb - ya)
    t = np.clip(np.minimum(u / taper, (1 - u) / taper), 0, 1) ** .6
    mid, hw = (x0 + x1) / 2, (x1 - x0) / 2
    wobv = wob * np.sin(u * 7 + rng.uniform(0, 6))
    left = np.stack([mid - hw * t + wobv, ys], 1)
    right = np.stack([mid + hw * t + wobv, ys], 1)
    return np.vstack([left, right[::-1]])


def vstrip(x0, ya, yb, x1=None, wob=2.5, seed=0):
    """Everything right of a slightly wavering vertical edge at x0."""
    rng = np.random.default_rng(seed)
    ys = np.linspace(ya, yb, 120)
    xs = x0 + wob * np.sin(ys / 47 + rng.uniform(0, 6)) + wob * .6 * np.sin(ys / 19 + rng.uniform(0, 6))
    edge = np.stack([xs, ys], 1)
    x1 = x1 if x1 is not None else cx + 400
    return np.vstack([edge, [[x1, yb], [x1, ya]]])


def vband(x0, x1, ya, yb, wob=2.0, seed=0):
    """A band between two wavering vertical edges."""
    rng = np.random.default_rng(seed)
    ys = np.linspace(ya, yb, 120)
    w0 = wob * np.sin(ys / 41 + rng.uniform(0, 6))
    w1 = wob * np.sin(ys / 53 + rng.uniform(0, 6))
    return np.vstack([np.stack([x0 + w0, ys], 1), np.stack([x1 + w1, ys], 1)[::-1]])


# ===================== the parts, back to front =====================

def bottom_bead():
    poly = band_poly(yBe, yBb, Rbb)
    clip('c_bb', d_of(poly))
    P(d_of(poly), M)
    group_open('c_bb')
    # rolled edge: lit on its upper half, shadowed underneath and on the right
    sh = np.vstack([front_arc(yBe + 15, Rbb + 30), [[cx + 400, yBb + 80], [cx - 400, yBb + 80]]])
    P(d_of(sh), MS)
    P(d_of(vstrip(cx + .62 * Rbb, yBe - 60, yBb + 60, seed=3)), MS)
    P(d_of(vstrip(cx + .86 * Rbb, yBe - 60, yBb + 60, wob=1, seed=4)), INK)
    P(d_of(ribbon(front_arc(yBe + 7, Rbb, cx - .9 * Rbb, cx + .35 * Rbb), 7, seed=11, t0=.25, t1=.3, amp=.1)), MH)
    for i, x in enumerate([cx + 52, cx + 100, cx - 70]):
        y = float(arc_y(x, yBe + 17, Rbb))
        hatch((x - 13, y + 1.5), (x + 13, y - 1.5), 5.0, seed=40 + i)
    group_close()
    ring(poly, 15.5, seed=1, floor=11.5, **SIL)


def body():
    poly = band_poly(yS, yBe, R)
    clip('c_body', d_of(poly))
    P(d_of(poly), G)
    group_open('c_body')
    # cel shading: shadow strip down the right, a highlight band and a thin shine on the left
    P(d_of(vstrip(cx + .54 * R, yS - 40, yBe + 60, x1=cx + .8 * R, seed=5)), GS)
    P(d_of(lens_band(cx - .74 * R, cx - .50 * R, yS + 14, yBe + 18, taper=.06, wob=1.2, seed=6)), GH)
    P(d_of(lens_band(cx - .40 * R, cx - .34 * R, yS + 30, yL + 30, taper=.3, seed=7)), GH)
    P(d_of(lens_band(cx - .40 * R, cx - .33 * R, yLb + 50, yBe - 14, taper=.3, seed=8)), GH)
    edges = label()
    # the rim light is paint on the green and paper on the label: two pieces that never overlap
    clip('c_nolabel', d_of(poly, np.vstack([edges[0], edges[1][::-1]])), rule='evenodd')
    core_shadow(cx + .77 * R, cx + .865 * R, cx + .925 * R, yS - 30, yBe + 40, yS + 40, yBe - 26, G, seed=9,
                rim_clip='c_nolabel')
    P(d_of(lens_band(cx + .865 * R, cx + .925 * R, yS + 40, yBe - 26, taper=.22, wob=.8, seed=10)), LB, 'c_label')
    label_ink(*edges)
    # a few long hatch strokes riding the shadow edge (no small specks: the lower body stays a clean field)
    xe = cx + .54 * R
    for i, (dx, y, L, w) in enumerate([(-10, 372, 52, 5.2), (-19, 392, 26, 4.4), (-9, 648, 64, 5.4), (-18, 676, 30, 4.6),
                                       (-11, 760, 44, 5.0)]):
        hatch((xe + dx, y), (xe + dx + 1.2, y + L), w, seed=60 + i, kind='lens')
    # one bold scuff flick on the lower left, big enough to stay a mark (not a speck) at game size
    hatch((cx - 96, 742), (cx - 58, 728), 6.0, bow=.06, seed=71)
    hatch((cx - 88, 758), (cx - 70, 752), 4.6, bow=.05, seed=72)
    group_close()
    bottom_edge = lambda Q: np.where((Q[:, 1] > yBe - 1) & (np.abs(Q[:, 0] - cx) < R - 6), .62, 1.0)
    ring(poly, 16.0, seed=2, wmul=bottom_edge, floor=10.5, **dict(SIL, amp=.27, wob=2.4, wls=(90, 170, 330)))


def core_shadow(x0, xr0, xr1, ya, yb, ra, rb, rim, seed=0, rim_clip=None):
    """L1's form shadow: everything right of x0 goes black (it runs into the outline), with a
    thin sliver of rim light (colour rim) standing in it between xr0 and xr1, from ra to rb."""
    P(d_of(vstrip(x0, ya, yb, wob=1.6, seed=seed)), INK)
    P(d_of(lens_band(xr0, xr1, ra, rb, taper=.22, wob=.8, seed=seed + 1)), rim, rim_clip)


# drips hanging off the label's top edge: (x offset, half width, length, bulb radius)
DRIPS = [(-98, 10.5, 50, 12.0), (-36, 14.5, 96, 16.0), (22, 9.0, 34, 10.5), (80, 11.5, 64, 13.5)]


def drip_path(xd, y_at, hw, ln, rb, f=None):
    """One drip hanging off an edge y_at(x), left to right: a flared top (round fillets),
    a column that thins as it runs, and a round bead of paint at the bottom."""
    f = f if f is not None else .8 * hw + 4
    pts = []
    xl = xd - hw - f
    yl = float(y_at(xl))
    for a in np.linspace(-90, 0, 10):                       # left fillet: edge turns down
        pts.append((xl + f * math.cos(math.radians(a)), yl + f + f * math.sin(math.radians(a))))
    y0 = float(y_at(xd))
    yb = y0 + ln - rb                                          # bulb centre
    ys = np.linspace(yl + f + 2, yb - rb * .7, 8)
    u = (ys - ys[0]) / (ys[-1] - ys[0])
    half = hw * (1 - .42 * u ** .8)
    pts += [(xd - h, y) for h, y in zip(half, ys)]
    for a in np.linspace(208, -28, 28):
        pts.append((xd + .4 + rb * math.cos(math.radians(a)), yb + rb * math.sin(math.radians(a))))
    xr = xd + hw + f
    yr = float(y_at(xr))
    ys = np.linspace(yr + f + 2, yb - rb * .7, 8)
    pts += [(xd + h * 1.02, y) for h, y in zip(half, ys)][::-1]
    for a in np.linspace(180, 270, 10):                      # right fillet: back up onto the edge
        pts.append((xr + f * math.cos(math.radians(a)), yr + f + f * math.sin(math.radians(a))))
    return pts, (xl, xr)


def label_top_edge():
    """The label's top edge, left to right, with the green drips running down over it."""
    y_at = lambda x: arc_y(x, yL, R) + 2.2 * np.sin(np.asarray(x) / 11.0 + 1.0) + 1.6 * np.sin(np.asarray(x) / 6.1)
    pts = []
    xi = cx - R - 40
    for dx, hw, ln, rb in sorted(DRIPS):
        dp, (xl, xr) = drip_path(cx + dx, y_at, hw, ln, rb)
        pts += [(x, float(y_at(x))) for x in np.arange(xi, xl, 2.0)]
        pts += dp
        xi = xr + 2
    pts += [(x, float(y_at(x))) for x in np.arange(xi, cx + R + 41, 2.0)]
    return chaikin(np.array(pts), False, 2)


# the torn bite out of the label's bottom edge: (x offset from cx, rise above the edge; + = down).
# Uneven teeth, a long ragged climb, and one tongue of paper left hanging down out of the bite.
TEAR = [(-30, 0), (-26, -6), (-22, -3), (-17, -13), (-13, -9), (-9, -19), (-4, -14), (0, -25), (4, -21),
        (8, -33), (12, -28), (15, -37),                                      # a ragged climb, uneven teeth
        (19, -25), (23, -13), (27, -3), (31, 7), (35, 12), (39, 6), (42, -6),  # a broad flap of paper left
        (45, -18), (48, -30),                                                # hanging in the middle
        (52, -38), (56, -31), (61, -41), (65, -28), (68, -32), (72, -19), (75, -23), (79, -11),
        (82, -14), (86, -4), (90, 0)]


def label_bottom_edge():
    """The label's bottom edge, left to right, with a torn bite out of it (worn)."""
    xs = np.linspace(cx - R - 40, cx + R + 40, 300)
    ys = arc_y(xs, yLb, R) + 1.6 * np.sin(xs / 13.0 + 2.0)
    t0, t1 = TEAR[0][0], TEAR[-1][0]
    pts = []
    for x, y in zip(xs, ys):
        dx = x - cx
        if t0 <= dx <= t1:
            continue
        pts.append((x, y))
        if dx < t0 and (x + (xs[1] - xs[0]) - cx) >= t0:
            for tx, ty in TEAR:
                pts.append((cx + tx, float(arc_y(cx + tx, yLb, R)) + ty))
    return np.array(pts)


def label():
    top = label_top_edge()
    bot = label_bottom_edge()
    poly = np.vstack([top, bot[::-1]])
    clip('c_label', d_of(poly))
    P(d_of(poly), LB)
    group_open('c_label')
    P(d_of(vstrip(cx + .54 * R, yL - 40, yLb + 60, x1=cx + .8 * R, seed=15)), LS)
    P(d_of(lens_band(cx - .74 * R, cx - .50 * R, yL - 20, yLb + 60, taper=.04, seed=16)), LH)
    # worn: a few scuffs on the paper
    for i, (p0, p1) in enumerate([((cx + 46, 522), (cx + 74, 514)), ((cx - 74, 566), (cx - 54, 572))]):
        hatch(p0, p1, 4.2, bow=.05, seed=90 + i, color=LS)
    hatch((cx + 108, 500), (cx + 109, 530), 5.2, seed=95)
    group_close()
    # drips: a highlight sliver down each and a shine on each bulb
    for i, (dx, hw, ln, rb) in enumerate(DRIPS):
        xd = cx + dx
        y0 = float(arc_y(xd, yL, R))
        bc = (xd + .5, y0 + ln - rb)
        hatch((bc[0] - rb * .58, bc[1] + rb * .05), (bc[0] - rb * .12, bc[1] - rb * .6), rb * .36, bow=-.14, seed=100 + i, color=GH, kind='lens')
        if ln > 45:
            hatch((xd - hw * .42, y0 + 16), (xd - hw * .42, y0 + ln - rb * 2.0), hw * .42, seed=110 + i, color=GH, kind='lens')
    # splatter: a few flecks of paint on the label, each inked so it re-tints cleanly
    for i, (x, y, r) in enumerate([(cx - 68, 542, 8.0)]):
        dot = full_ellipse(y, r, r, x)
        o, inn = outline_ring(dot, 4.4, 200 + i, bias=.9, amp=.1, inner_frac=.25)
        P(d_of(o), INK)
        P(d_of(inn), G)
    return top, bot


def label_ink(top, bot):
    """The label's edges, drips included (drawn after the core shadow, so the rim light's
    paint and paper never meet without a line between them)."""
    line(top, 8.5, 31, 'c_body', t0=0, t1=0, bias=.5)
    line(bot, 8.5, 32, 'c_body', t0=0, t1=0, bias=.5)


def top_bead():
    poly = band_poly(yS - hb, yS + hb, Rb)
    clip('c_tb', d_of(poly))
    P(d_of(poly), M)
    group_open('c_tb')
    sh = np.vstack([front_arc(yS + 2, Rb + 30), [[cx + 400, yS + 120], [cx - 400, yS + 120]]])
    P(d_of(sh), MS)
    P(d_of(vstrip(cx + .62 * Rb, yS - 80, yS + 80, seed=13)), MS)
    P(d_of(vstrip(cx + .86 * Rb, yS - 80, yS + 80, wob=1, seed=14)), INK)
    P(d_of(ribbon(front_arc(yS - hb + 4.5, Rb, cx - .92 * Rb, cx + .4 * Rb), 7, seed=12, t0=.25, t1=.3, amp=.1)), MH)
    for i, x in enumerate([cx + 40, cx + 98, cx - 62]):
        y = float(arc_y(x, yS + 5, Rb))
        hatch((x - 11, y + 1), (x + 11, y - 1.5), 5.0, seed=140 + i)
    group_close()
    ring(poly, 15.0, seed=3, floor=11.5, **SIL)


def revolve_top(y_base, r_base, r_top, height, pw=1.0, n=400, nx=500):
    """Top silhouette of a surface of revolution seen from a little above: its profile runs
    from radius r_base at y_base up a quarter-curve to radius r_top, height px higher.
    Returns points left to right over x in [cx - r_base, cx + r_base]."""
    th = np.linspace(0, np.pi / 2, n)
    r = r_top + (r_base - r_top) * np.cos(th) ** pw
    yc = y_base - height * np.sin(th) * math.sqrt(1 - k * k)
    xs = np.linspace(cx - r_base, cx + r_base, nx)
    out = []
    for x in xs:
        dx = x - cx
        ok = r >= abs(dx)
        out.append((x, float(np.min(yc[ok] - k * np.sqrt(np.maximum(r[ok] ** 2 - dx * dx, 0))))))
    return np.array(out)


def dome_point(theta, phi):
    """A point on the dome: theta 0 (base) .. pi/2 (top); phi in degrees, 90 = facing us."""
    r = Rc + (R1 - Rc) * np.cos(theta) ** 1.15
    yc = yD0 - Hd * np.sin(theta) * math.sqrt(1 - k * k)
    return np.stack([cx + r * np.cos(np.radians(phi)), yc + k * r * np.sin(np.radians(phi))], -1)


def dome():
    top = revolve_top(yD0, R1, Rc, Hd, pw=1.15, nx=600)
    base = ellipse_pts(cx, yD0, R1, k * R1, 0, 180)
    poly = np.vstack([top, base])
    clip('c_dome', d_of(poly))
    P(d_of(poly), M)
    group_open('c_dome')
    # shadow: everything right of a meridian on the front-right
    ths = np.linspace(0, np.pi / 2, 60)
    mer = dome_point(ths, 42)
    P(d_of(np.vstack([mer, [[cx + 300, mer[-1, 1] - 60], [cx + 300, mer[0, 1] + 60]]])), MS)
    tb = np.linspace(0, np.pi / 2, 60)
    mk = dome_point(tb, 22)
    P(d_of(np.vstack([mk, [[cx + 300, mk[-1, 1] - 60], [cx + 300, mk[0, 1] + 60]]])), INK)
    tb = np.linspace(.12, 1.05, 50)
    ca, cb = dome_point(tb, 12), dome_point(tb, 6)
    wv = np.sin(np.linspace(0, np.pi, 50)) ** .5
    mc = (ca + cb) / 2
    P(d_of(np.vstack([mc + (ca - mc) * wv[:, None], (mc + (cb - mc) * wv[:, None])[::-1]])), M)
    # highlight band between two meridians on the front-left, pointed at both ends
    t2 = np.linspace(.1, 1.2, 50)
    a = dome_point(t2, 124)
    b = dome_point(t2, 148)
    w = np.sin(np.linspace(0, np.pi, 50)) ** .5
    mid = (a + b) / 2
    a2 = mid + (a - mid) * w[:, None]
    b2 = mid + (b - mid) * w[:, None]
    P(d_of(np.vstack([a2, b2[::-1]])), MH)
    # a thin second shine
    t3 = np.linspace(.25, .95, 30)
    c1, c2 = dome_point(t3, 112), dome_point(t3, 106)
    w3 = np.sin(np.linspace(0, np.pi, 30)) ** .5
    m3 = (c1 + c2) / 2
    P(d_of(np.vstack([m3 + (c1 - m3) * w3[:, None], (m3 + (c2 - m3) * w3[:, None])[::-1]])), MH)
    # hatching along the shadow edge, running with the dome's curve
    for i, (t0, t1, ph) in enumerate([(.12, .44, 47), (.5, .82, 50), (.08, .32, 58)]):
        pts = dome_point(np.linspace(t0, t1, 12), ph)
        P(d_of(ribbon(pts, 4.4, seed=150 + i, t0=.3, t1=.55, power=.8, amp=.05)), INK)
    for i, (t0, t1, ph) in enumerate([(.15, .42, 158), (.48, .72, 162)]):
        pts = dome_point(np.linspace(t0, t1, 12), ph)
        P(d_of(ribbon(pts, 3.8, seed=160 + i, t0=.3, t1=.55, power=.8, amp=.05)), INK)
    group_close()
    ring(poly, 15.5, seed=4, floor=13.0, **SIL)


def valve_cup():
    poly = band_poly(yCt, yCb, Rcup)
    clip('c_cup', d_of(poly))
    P(d_of(poly), M)
    group_open('c_cup')
    P(d_of(lens_band(cx - .8 * Rcup, cx - .3 * Rcup, yCt + 8, yCb + 6, taper=.3, seed=24)), MH)   # a shine on the roll
    sh = np.vstack([front_arc(yCt + 7, Rcup + 20), [[cx + 200, yCb + 60], [cx - 200, yCb + 60]]])
    P(d_of(sh), MS)
    P(d_of(vstrip(cx + .6 * Rcup, yCt - 40, yCb + 40, seed=23)), MS)
    group_close()
    line(ellipse_pts(cx, yCt, Rcup, k * Rcup, 222, -42), 7.5, 25, 'c_cup', t0=.0, t1=.0)   # wraps the ends, so no sliver of the roll's top peeks out
    ring(poly, 13.5, seed=5, floor=12.0, bias=.42, amp=.15)


def drip_down(x, y_top, hw, yb, rb, wob=(0, 0, 0)):
    """A drip running straight down from under something at y_top to a bead of paint centred
    at yb, as a closed outline (its top is hidden under whatever it runs out from)."""
    pts = [(x - hw, y_top), (x - hw - wob[0], y_top + (yb - y_top) * .35), (x - hw * .95 - wob[1], y_top + (yb - y_top) * .7),
           (x - hw * .8, yb - rb * 1.05)]
    for a in np.linspace(196, -16, 26):
        pts.append((x + .6 + rb * math.cos(math.radians(a)), yb + rb * math.sin(math.radians(a))))
    pts += [(x + hw * .8, yb - rb * 1.05), (x + hw * .95 + wob[2], y_top + (yb - y_top) * .68),
            (x + hw + wob[1] * .5, y_top + (yb - y_top) * .33), (x + hw, y_top)]
    return chaikin(np.array(pts), False, 3)


def dome_seep():
    """A short run of paint that seeped out from under the valve cup and stopped on the shoulder
    (drawn before the cup, so its top is tucked under it)."""
    x, hw, yb, rb = cx + 34, 9.0, 290.0, 11.5
    pts = drip_down(x, yCt + 4, hw, yb, rb, (-.6, .8, .5))
    P(d_of(pts), G)
    hatch((x - rb * .58, yb + rb * .05), (x - rb * .12, yb - rb * .6), rb * .36, bow=-.14, seed=174, color=GH, kind='lens')
    line(pts, 7.5, 176, t0=.03, t1=.03, bias=.4)


# ---------- the spray button ----------
def act_silhouette():
    top = revolve_top(yAs, Rbt, rtA, HtA, pw=1.0, nx=320)
    bot = ellipse_pts(cx, yAb, Rbt, k * Rbt, 0, 180)
    return top, np.vstack([top, bot])


ACT_TOP, ACT_POLY = act_silhouette()


def act_top_y(x):
    return np.interp(np.asarray(x, float), ACT_TOP[:, 0], ACT_TOP[:, 1])


def actuator():
    """The spray button seen from behind: a charcoal cylinder with a rounded crown. Its nozzle is
    on the far side, pointing at the wall, so all we get is its plain back."""
    poly = ACT_POLY
    clip('c_act', d_of(poly))
    P(d_of(poly), A)
    group_open('c_act')
    # the crown (above the wall's top edge) faces the light: lighter
    crown = np.vstack([ACT_TOP, ellipse_pts(cx, yAs, Rbt, k * Rbt, 0, 180)[::-1]])
    P(d_of(crown), AH)
    P(d_of(vstrip(cx + .46 * Rbt, yAs - 60, yAb + 40, seed=34)), AS)
    P(d_of(vstrip(cx + .74 * Rbt, yAs - 60, yAb + 40, wob=1.2, seed=38)), INK)
    P(d_of(lens_band(cx - .78 * Rbt, cx - .52 * Rbt, yAs + 4, yAb + 12, taper=.25, seed=35)), AH)
    P(d_of(lens_band(cx - .44 * Rbt, cx - .38 * Rbt, yAs + 8, yAb + 2, taper=.3, seed=36)), AHH)
    hatch((cx + .40 * Rbt, yAs + 12), (cx + .41 * Rbt, yAs + 36), 4.4, seed=181, kind='lens')
    group_close()
    # the crown's edge: an ink line where the rounded top turns down into the wall, broken in the light
    fa = front_arc(yAs, Rbt, cx - Rbt * .5, cx + Rbt - 2)
    line(fa, 6.5, 37, 'c_act', t0=.25, t1=.06)
    base_edge = lambda Q: np.where(Q[:, 1] > yAb - 2, .62, 1.0)    # lighter where it sits in the cup
    ring(poly, 15.5, seed=7, floor=8.0, bias=.4, amp=.14, wls=(40, 90, 170), wob=.8, wmul=base_edge)


def drip_col(xd, y_at, y_bead, rb, hw_fn, f=None, xwob=None):
    """A drip hanging off an edge y_at(x), left to right, whose column half-width follows
    hw_fn(y) (so it can pool where it runs over a lip) and ends in a bead centred at y_bead."""
    hw0 = float(hw_fn(float(y_at(xd))))
    f = f if f is not None else .7 * hw0 + 3
    xw = xwob if xwob is not None else (lambda y: 0.0)
    pts = []
    xl = xd - hw0 - f
    yl = float(y_at(xl))
    for a in np.linspace(-90, 0, 10):
        pts.append((xl + f * math.cos(math.radians(a)), yl + f + f * math.sin(math.radians(a))))
    ys = np.linspace(yl + f + 2, y_bead - rb * .7, 60)
    pts += [(xd - hw_fn(y) + xw(y), y) for y in ys]
    for a in np.linspace(208, -28, 30):
        pts.append((xd + .4 + rb * math.cos(math.radians(a)), y_bead + rb * math.sin(math.radians(a))))
    xr = xd + hw0 + f
    yr = float(y_at(xr))
    ys = np.linspace(yr + f + 2, y_bead - rb * .7, 60)
    pts += [(xd + hw_fn(y) * 1.02 + xw(y), y) for y in ys][::-1]
    for a in np.linspace(180, 270, 10):
        pts.append((xr + f * math.cos(math.radians(a)), yr + f + f * math.sin(math.radians(a))))
    return pts, (xl, xr)


# paint caked round the nozzle on the button's FAR lip: a lumpy crust over the top, with two runs
# coming back over the crown towards us - a short one, and a long one that runs off the button,
# over the valve cup and down the dome to the seam
CRUST_X = (cx - 44, cx + 46)
LONG_X, SHORT_X = cx - 15, cx + 21
LONG_BEAD, SHORT_BEAD = 249.0, 203.0            # the long run hangs off the button's base over the cup


def crust_shape():
    x0, x1 = CRUST_X
    xs = np.linspace(x0, x1, 160)
    u = (xs - x0) / (x1 - x0)
    taper = np.sin(np.pi * u) ** .55
    sil = act_top_y(xs)
    lump = taper * (4.4 + 3.0 * np.sin(xs / 6.3 + .7) + 1.6 * np.sin(xs / 3.1 + 2.0))
    top = np.stack([xs, sil + 1.5 - lump], 1)
    thick = lambda x: (np.sin(np.pi * np.clip((np.asarray(x, float) - x0) / (x1 - x0), 0, 1)) ** .6
                       * (17.0 + 2.6 * np.sin(np.asarray(x, float) / 8.0 + 1.3) + 1.4 * np.sin(np.asarray(x, float) / 4.3)))
    y_at = lambda x: act_top_y(x) + 2.5 + thick(x)
    # the long run: pools a little where it goes over the button's base and the cup's roll
    ya1 = float(arc_y(LONG_X, yAb, Rbt)) + 1
    ya2 = float(arc_y(LONG_X, yCb, Rcup)) + 1
    hwL = lambda y: (9.6 - 1.6 * np.clip((y - 180) / 60, 0, 1) + 3.2 * math.exp(-((y - ya1) / 4.5) ** 2))
    xwL = lambda y: .9 * math.sin(y / 13.0) + .5 * math.sin(y / 6.0 + 1)
    dL, (lx0, lx1) = drip_col(LONG_X, y_at, LONG_BEAD, 12.0, hwL, xwob=xwL)
    hwS = lambda y: 7.6 - 1.4 * np.clip((y - 180) / 25, 0, 1)
    dS, (sx0, sx1) = drip_col(SHORT_X, y_at, SHORT_BEAD, 9.5, hwS)
    bot = []
    xi = x0
    for (dp, (a, b)) in sorted([(dL, (lx0, lx1)), (dS, (sx0, sx1))], key=lambda t: t[1][0]):
        bot += [(x, float(y_at(x))) for x in np.arange(xi, a, 1.5)]
        bot += dp
        xi = b + 1.5
    bot += [(x, float(y_at(x))) for x in np.arange(xi, x1 + .01, 1.5)]
    bot = chaikin(np.array(bot), False, 1)
    return np.vstack([top, bot[::-1]]), top


def crust():
    poly, top = crust_shape()
    clip('c_crust', d_of(poly))
    P(d_of(poly), G)
    group_open('c_crust')
    # its shade side and its light side, in the paint's own greens
    P(d_of(vstrip(cx + .40 * Rbt, 100, 400, x1=cx + 200, wob=1.2, seed=191)), GS)
    P(d_of(vband(LONG_X + 3.0, LONG_X + 8, 178, LONG_BEAD - 6, wob=.6, seed=192)), GS)
    P(d_of(lens_band(LONG_X - 6.5, LONG_X - 2.5, 176, LONG_BEAD - 16, taper=.25, wob=.6, seed=193)), GH)
    # the crust's top catches the light on the left
    xs = np.linspace(cx - 34, cx + 4, 40)
    ys = act_top_y(xs) + 2.5
    P(d_of(ribbon(np.stack([xs, ys + 3.5], 1), 4.6, seed=194, t0=.4, t1=.4, amp=.1)), GH)
    for i, (x, yb, rb) in enumerate([(LONG_X, LONG_BEAD, 12.0), (SHORT_X, SHORT_BEAD, 9.5)]):
        hatch((x + .5 - rb * .58, yb + rb * .05), (x + .5 - rb * .12, yb - rb * .6), rb * .36, bow=-.14, seed=196 + i, color=GH, kind='lens')
    group_close()
    # heavier ink along the crust's top (it is the silhouette there), lighter where it runs
    topw = lambda Q: np.where(Q[:, 1] < act_top_y(Q[:, 0]) + 4.0, 1.85, 1.0)
    ring(poly, 10.0, seed=199, bias=.5, amp=.12, wmul=topw, floor=6.5, inner_frac=.38)


def build(transform=''):
    els.clear(); defs.clear()
    bottom_bead()
    body()
    top_bead()
    dome()
    dome_seep()
    valve_cup()
    actuator()
    crust()
    body_svg = '\n'.join(els)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}" viewBox="0 0 {SIZE} {SIZE}">'
            f'<defs>{"".join(defs)}</defs><g transform="{transform}">{body_svg}</g></svg>')


def render(svg_path, png_path):
    subprocess.run([NODE, os.path.join(HERE, 'render.js'), svg_path, png_path, str(SIZE)], check=True)


def disc_offsets(r):
    return [(dx, dy) for dy in range(-r, r + 1) for dx in range(-r, r + 1) if dx * dx + dy * dy <= r * r + .5 * r]


def dilate(a, r):
    H, W = a.shape
    pad = np.pad(a, r)
    out = a.copy()
    for dx, dy in disc_offsets(r):
        np.maximum(out, pad[r + dy:r + dy + H, r + dx:r + dx + W], out=out)
    return out


def sticker(img, px=14):
    """The icons' white sticker edge: a band px wide round the silhouette, under the art."""
    a = np.asarray(img, dtype=np.float32)[..., 3] / 255.0
    grown = dilate(a, px + 3)
    grown = 1 - dilate(1 - grown, 3)                # close: rounds off the inner corners
    base = np.zeros(a.shape + (4,), np.uint8)
    base[..., :3] = 255
    base[..., 3] = np.clip(grown * 255 + .5, 0, 255).astype(np.uint8)
    out = Image.alpha_composite(Image.fromarray(base, 'RGBA'), img)
    arr_ = np.array(out)
    arr_[arr_[..., 3] < 3] = 0                       # no stray near-invisible pixels
    return Image.fromarray(arr_, 'RGBA')


def despeckle(img):
    """Ink over any tiny light speck that the overlapping ink rings left enclosed in black (a pixel
    or two of metal caught between two outlines reads as dirt at full size)."""
    from numpy.lib.stride_tricks import sliding_window_view as sw
    a = np.array(img)
    L = a[..., :3].max(-1).astype(int)
    lite = (L > 60) & (a[..., 3] > 200)
    ink = (L < 40) & (a[..., 3] > 200)
    n_lite = sw(np.pad(lite, 3), (7, 7)).sum((-1, -2))
    n_ink = sw(np.pad(ink, 3), (7, 7)).sum((-1, -2))
    kill = lite & (n_lite <= 5) & (n_ink >= 40)
    a[kill, :3] = 0
    return Image.fromarray(a, 'RGBA'), int(kill.sum())


KEY_H = (61 - 0) / 255 + 2                           # the key green's hue / 60 (tintGreen's units)


def enforce_rule(img):
    """Colour rule: every visible pixel is either tinted by tintGreen (green-led, spread >= 48,
    hue 93-177) or a pure neutral. Anti-aliasing between paint green and ink/metal makes some
    green-led pixels too grey to be tinted (they would stay green on a red can): lift those that
    are bright and green enough to spread 48 at the key hue, snap the rest to a neutral grey."""
    a = np.array(img).astype(np.float64)
    r, g, b, al = a[..., 0].copy(), a[..., 1].copy(), a[..., 2].copy(), a[..., 3]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    dl = mx - mn
    with np.errstate(divide='ignore', invalid='ignore'):
        h = np.where(dl > 0, (b - r) / np.maximum(dl, 1e-9) + 2, 0)
    green_led = (g >= mx) & (dl > 0)
    tint = (al > 0) & green_led & (dl >= 48) & (h >= 1.55) & (h <= 2.95)
    off = (al > 0) & ~tint & (dl > 0)
    lift = off & green_led & (dl >= 22) & (mx >= 64)
    snap = off & ~lift
    # lift: keep the value, set spread 48 at the key hue
    v = mx[lift]
    a[..., 0][lift] = v - 48
    a[..., 1][lift] = v
    a[..., 2][lift] = v - 48 + (KEY_H - 2) * 48
    # snap: perceived luminance as a pure grey
    y = .299 * r + .587 * g + .114 * b
    for c in range(3):
        a[..., c][snap] = y[snap]
    out = np.clip(np.round(a), 0, 255).astype(np.uint8)
    # rounding can knock a lifted pixel back under 48: nudge red down once more
    o = out.astype(int)
    mx2, mn2 = o[..., :3].max(-1), o[..., :3].min(-1)
    bad = lift & ((mx2 - mn2) < 48)
    out[..., 0][bad] = np.clip(o[..., 0][bad] - 1, 0, 255)
    return Image.fromarray(out, 'RGBA'), int(lift.sum()), int(snap.sum())


NOZZLE_SRC = (cx, float(act_top_y(cx)) - 1.0)        # the top centre of the button, on the far lip's
                                                    # crust: the mist leaves from here into the wall


def main():
    svg0 = build()
    p0 = os.path.join(HERE, 'can_pass0.svg'); open(p0, 'w').write(svg0)
    raw0 = os.path.join(HERE, 'can_pass0.png'); render(p0, raw0)
    a = np.array(Image.open(raw0))[..., 3]
    ys, xs = np.where(a > 8)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    art_h = y1 - y0 + 1
    target_art_h = 830 - 2 * 14                     # 83% of the canvas, sticker edge included
    s = target_art_h / art_h
    mx, my = (cx, (y0 + y1 + 1) / 2)                 # centre on the can's axis, not its (lumpy) bbox
    tf = f'translate(500 500) scale({s:.5f}) translate({-mx:.3f} {-my:.3f})'
    svg = build(tf)
    open(os.path.join(HERE, 'can.svg'), 'w').write(svg)
    raw = os.path.join(HERE, 'can_raw.png'); render(os.path.join(HERE, 'can.svg'), raw)
    img = Image.open(raw).convert('RGBA')
    out = sticker(img, 14)
    out, n_speck = despeckle(out)
    out, n_lift, n_snap = enforce_rule(out)
    out.save(os.path.join(HERE, 'can.png'))
    nz = [round(float(500 + (NOZZLE_SRC[0] - mx) * s), 1), round(float(500 + (NOZZLE_SRC[1] - my) * s), 1)]
    al = np.array(out)[..., 3]
    ys, xs = np.where(al > 8)
    # what tools/make_spray_fx.py makes of it: trimmed to the alpha bbox + 8 px, 480 px tall
    bx = out.getbbox(); bx = (max(0, bx[0] - 8), max(0, bx[1] - 8), min(SIZE, bx[2] + 8), min(SIZE, bx[3] + 8))
    ks = 480 / (bx[3] - bx[1])
    ship = ((round((bx[2] - bx[0]) * ks), 480), [round((nz[0] - bx[0]) * ks, 1), round((nz[1] - bx[1]) * ks, 1)])
    meta = {
        'nozzle': nz,
        'notes': ('Brand-new aerosol can, upright and symmetric about x=500, seen from directly behind: '
                  'the charcoal spray button shows only its plain back (no nozzle hole) and the paint caked '
                  'round the hidden nozzle crusts its FAR lip and runs back over the crown towards us, one run '
                  'going on down the dome to the seam. nozzle = the top centre of the button on that crust, '
                  'where the mist leaves heading into the wall. Paint-coloured parts (body, label drips and fleck, '
                  'button crust and runs, dome seep) are hue-134 greens: key rgb(0,255,61), highlight '
                  'rgb(120,255,152), shadow rgb(0,170,40). Metal, charcoal button, grey label (204), ink and '
                  'sticker edge are pure neutrals; anti-aliased pixels are post-snapped so every pixel is '
                  'either tintGreen-tinted or neutral. Has its own 14 px white sticker edge (make_spray_fx '
                  'detects it and adds none). Bbox (alpha>8): x %d-%d, y %d-%d. Shipped by make_spray_fx '
                  '(trim + 8 px, 480 tall): %dx%d, nozzle there %s.'
                  % (xs.min(), xs.max(), ys.min(), ys.max(), ship[0][0], ship[0][1], ship[1])),
    }
    json.dump(meta, open(os.path.join(HERE, 'meta.json'), 'w'), indent=2)
    print('scale', round(s, 4), 'bbox', xs.min(), xs.max(), ys.min(), ys.max(), 'nozzle', nz, 'specks', n_speck, 'lifted', n_lift, 'snapped', n_snap)


if __name__ == '__main__':
    main()
