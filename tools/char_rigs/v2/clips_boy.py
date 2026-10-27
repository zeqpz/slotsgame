"""SMUKIEZ clips. Same names, lengths, faces and beats as before; the motion now runs through the
longer chains with overlap and follow-through:
hips -> torso -> chest -> neck -> head -> beanie -> beanie_tip, and grip -> bills -> bill tips; the
arms are IK chains to the hands on the money, the legs IK chains to the feet (knees bend for real)."""
import math
import numpy as np
from motionkit import Clip, keys, bump, osc, hop, lag, spring, settle, smooth, ease, ease_out, ease_in

NB = 6
CHAIN = ['torso', 'chest', 'neck', 'head', 'beanie', 'beanie_tip']
LAGS = {'chest': (.03, 2.8, .55), 'neck': (.04, 2.6, .5), 'head': (.05, 2.3, .48), 'beanie': (.07, 2.1, .45),
        'beanie_tip': (.09, 2.0, .42)}
BILL_LAG = (.03, 3.2, .4)


GAIN = {'head': .85, 'beanie': .3, 'beanie_tip': .4}
CALM = {'head': .6, 'beanie': .12, 'beanie_tip': .15}   # walk-on / walk-off: the whole figure moves, the hat stays put on it


def follow(c, scale_lag=1.0, gains=None):
    """overlapping action: every link of the spine/head chain trails the one before it, and the
    bills trail the hands' grip (each tip trailing its bill)"""
    world = c.get('torso', 'rotate').copy()
    for b in CHAIN[1:]:
        d, f, z = LAGS[b]
        local = c.get(b, 'rotate')
        new = lag(c, b, world, local, d * scale_lag, f, z)
        g = (gains or GAIN).get(b, GAIN.get(b, 1.0))
        new = local + g * (new - local)          # how much of the trailing this link shows
        c.set(b, 'rotate', new)
        world = world + new
    gw = c.get('torso', 'rotate') + c.get('chest', 'rotate') + c.get('grip', 'rotate')
    for k in range(NB):
        d, f, z = BILL_LAG
        loc = c.get(f'bill_{k}', 'rotate')
        nb = lag(c, f'bill_{k}', gw, loc, d + .012 * k, f - .15 * k, z)
        c.set(f'bill_{k}', 'rotate', nb)
        tip = c.get(f'bill_{k}_tip', 'rotate')
        c.set(f'bill_{k}_tip', 'rotate', lag(c, f'bill_{k}_tip', gw + nb, tip, .03, 3.6, .35))


def weight(c, amount=1.0):
    """the big head dips on a landing and lifts on a push-off; the torso squashes with it"""
    y = smooth(c.get('hips', 'y'), c.t, .03)
    a = np.gradient(np.gradient(y, c.t), c.t)
    a = smooth(a, c.t, .03)
    sq = np.clip(-a * 2.8e-5 * amount, -.045, .045)
    sy = 1 + spring(sq, c.t, 3.4, .45, c.loop)
    if not c.loop: sy = settle(c, sy, 1)
    c.set('torso', 'sy', c.get('torso', 'sy') * sy)
    c.set('torso', 'sx', c.get('torso', 'sx') * (1 - .5 * (sy - 1)))
    hy = spring(np.clip(-a * .0018 * amount, -5, 5), c.t, 2.6, .5, c.loop)
    if not c.loop: hy = settle(c, hy, 0)
    c.add('head', 'y', hy)


def take(c, at, amp=1.0):
    """a quick squash-stretch-settle of the head as a new face comes in at `at`"""
    k = 1.0 if c.loop else min(1.0, max(.35, (c.dur - .03 - at) / (.56 - .09)))   # it must be over before the clip ends
    kt = np.array([0, .09, .22, .38, .56]) * k + at - (.09 * k if at > 0 else 0)
    amp = amp * .55
    sy = np.interp(c.t, kt, [1, 1 - .06 * amp, 1 + .03 * amp, 1 - .006 * amp, 1])
    sx = np.interp(c.t, kt, [1, 1 + .045 * amp, 1 - .018 * amp, 1 + .003 * amp, 1])
    c.set('head', 'sx', c.get('head', 'sx') * smooth(sx, c.t, .045))
    c.set('head', 'sy', c.get('head', 'sy') * smooth(sy, c.t, .045))


def feet_with_hips(c, tuck=0.0, start=0.0, end=None):
    """during a hop the feet leave the ground with the hips (minus a little tuck)"""
    pass


def idle():
    D = 3.2; c = Clip(D, loop=True); t = c.t
    c.set('hips', 'x', osc(t, 3.2, 6))
    c.set('hips', 'y', -4.5 * (1 - np.cos(2 * math.pi * t / 1.6)))
    c.set('hips', 'rotate', osc(t, 3.2, -.6, .05))
    c.set('torso', 'rotate', osc(t, 3.2, 1.3, .12))
    c.set('chest', 'rotate', osc(t, 3.2, .7, .2))
    c.set('neck', 'rotate', osc(t, 3.2, -.5, .3))
    c.set('head', 'rotate', osc(t, 3.2, 1.8, .32) + osc(t, 1.6, .5, .1))
    c.set('head', 'y', -1.6 * (1 - np.cos(2 * math.pi * (t / 1.6 - .1))))
    c.set('beanie', 'rotate', osc(t, 1.6, .4, .3))
    c.set('grip', 'y', 2 * (1 - np.cos(2 * math.pi * (t / 1.6 - .15))))
    c.set('grip', 'rotate', osc(t, 3.2, 1.6, .22))
    for k in range(NB):
        c.set(f'bill_{k}', 'rotate', osc(t, 1.6, .9 + .18 * k, -.06 * k))
    # weight shifts onto the planted feet: the far heel lifts a touch as he sways off it
    c.set('shoe_right', 'rotate', 1.2 * np.clip(osc(t, 3.2, 1, .25), 0, None))
    follow(c); weight(c, .6)
    c.face('head', [(0, 'face_idle')])
    return c


def anticipation():
    D = 1.2; c = Clip(D); t = c.t
    c.set('hips', 'y', keys(t, [(0, 0), (.6, -17), (1.2, 0)]))
    c.set('hips', 'x', keys(t, [(0, 0), (.3, 4.5), (.9, -4.5), (1.2, 0)]))
    c.set('torso', 'rotate', keys(t, [(0, 0), (.4, -1.3), (1.0, 1.2), (1.2, 0)]))
    c.set('chest', 'rotate', keys(t, [(0, 0), (.45, -1), (1.05, .8), (1.2, 0)]))
    c.set('head', 'rotate', keys(t, [(0, 0), (.35, 2.4), (.95, -2.2), (1.2, 0)]))
    c.set('head', 'y', keys(t, [(0, 0), (.57, 3), (1.2, 0)]))
    c.set('grip', 'y', keys(t, [(0, 0), (.6, 6.5), (1.2, 0)]))
    c.set('grip', 'rotate', keys(t, [(0, 0), (.35, 2.6), (.95, -2.6), (1.2, 0)]))
    # two nervous taps of the right foot
    tap = bump(t, .1, .3, .5, 10) + bump(t, .55, .75, .97, 11)
    c.set('foot_right', 'y', tap)
    c.set('shoe_right', 'rotate', tap * .45)
    # the money shivers in his grip
    shiver = np.sin(2 * math.pi * t / .11) * bump(t, .1, .5, 1.0, 1.0)
    for k in range(NB):
        c.set(f'bill_{k}', 'rotate', shiver * (.5 + .12 * k))
    follow(c); weight(c)
    c.face('head', [(0, 'face_anticipation'), (.84, 'face_idle')]); take(c, 0); take(c, .84, .7)
    c.event(.5, 'foot_tap'); c.event(.97, 'foot_tap')
    return c


def win():
    D = 2.4; c = Clip(D); t = c.t
    # crouch, spring up into a hop with a heel kick, land, bounce
    y = keys(t, [(0, 0), (.42, -14), (.62, 4)]) * (t <= .62) + 0
    y = np.where(t <= .62, y, 0) + hop(t, .62, 1.12, 38)
    y += np.where(t > 1.12, keys(t, [(1.12, 0), (1.24, -12), (1.5, 2), (1.75, -3), (2.1, 0), (2.4, 0)]), 0)
    c.set('hips', 'y', smooth(y, t, .015))
    c.set('hips', 'x', keys(t, [(0, 0), (.9, -7), (1.5, 7), (2.4, 0)], 'flow'))
    c.set('foot_left', 'y', hop(t, .66, 1.1, 30) + bump(t, .8, 1.0, 1.3, 26))
    c.set('foot_left', 'x', bump(t, .7, 1.0, 1.3, -9))
    c.set('shoe_left', 'rotate', bump(t, .7, 1.0, 1.3, -11))
    c.set('foot_right', 'y', hop(t, .68, 1.08, 24))
    c.set('shoe_right', 'rotate', bump(t, .62, .8, 1.1, 5))
    c.set('torso', 'rotate', keys(t, [(0, 0), (.4, 1), (.9, -2.2), (1.5, 2), (2.0, -.6), (2.4, 0)], 'flow'))
    c.set('chest', 'rotate', keys(t, [(0, 0), (.9, -1.5), (1.5, 1.2), (2.4, 0)], 'flow'))
    c.set('head', 'rotate', keys(t, [(0, 0), (.5, 1.5), (1.15, -8), (1.7, -2), (2.1, -2.5), (2.4, 0)], 'flow'))
    c.set('grip', 'y', keys(t, [(0, 0), (.45, -4), (.95, 20), (1.6, 16), (2.4, 0)], 'flow'))
    c.set('grip', 'rotate', keys(t, [(0, 0), (.6, 3), (1.05, 8.5), (1.7, 5), (2.4, 0)], 'flow'))
    fan = bump(t, .55, 1.0, 1.9, 1.0)
    for k in range(NB):
        c.set(f'bill_{k}', 'rotate', (k - 2.5) * -2.2 * fan)
    c.set('torso', 'sy', 1 + bump(t, .5, .66, .85, .03) - bump(t, 1.1, 1.22, 1.45, .04))
    follow(c); weight(c)
    c.face('head', [(0, 'face_win'), (2.04, 'face_idle')]); take(c, 0); take(c, 2.04, .7)
    c.event(.55, 'win_hit'); c.event(1.1, 'cash_rustle'); c.event(1.18, 'land')
    return c


def big_win():
    D = 3.2; c = Clip(D); t = c.t
    y = keys(t, [(0, 0), (.3, -10), (.45, 2)]) * (t <= .45)
    y += hop(t, .45, .8, 22)
    y += np.where((t > .8) & (t <= 1.35), keys(t, [(.8, 0), (.9, -9), (1.15, 2), (1.35, -16)]), 0)
    y += np.where((t > 1.35) & (t <= 1.5), keys(t, [(1.35, -16), (1.5, 0)]), 0)
    y += hop(t, 1.5, 2.15, 64)
    y += np.where(t > 2.15, keys(t, [(2.15, 0), (2.27, -15), (2.55, 3), (2.85, -2), (3.2, 0)]), 0)
    c.set('hips', 'y', smooth(y, t, .012))
    c.set('hips', 'x', keys(t, [(0, 0), (.6, 5), (1.3, -6), (1.9, 7), (2.5, -3), (3.2, 0)], 'flow'))
    for side, ph in (('left', 0.0), ('right', .03)):
        fy = hop(t, .48 + ph, .78 + ph, 16) + hop(t, 1.53 + ph, 2.12 + ph, 58) + bump(t, 1.6, 1.85, 2.05, 22)
        c.set(f'foot_{side}', 'y', fy)
        c.set(f'shoe_{side}', 'rotate', bump(t, 1.55, 1.85, 2.15, -9 if side == 'left' else 9))
        c.set(f'foot_{side}', 'x', bump(t, 1.5, 1.85, 2.2, -14 if side == 'left' else 14))
    c.set('torso', 'rotate', keys(t, [(0, 0), (.5, 1.5), (1.2, -2.5), (1.85, 3), (2.4, -2.2), (2.9, .6), (3.2, 0)], 'flow'))
    c.set('chest', 'rotate', keys(t, [(0, 0), (1.2, -1.8), (1.9, 2.2), (2.5, -1.2), (3.2, 0)], 'flow'))
    c.set('head', 'rotate', keys(t, [(0, 0), (.6, 3), (1.4, -6.5), (1.95, 7), (2.45, -4), (2.85, 1), (3.2, 0)], 'flow'))
    c.set('grip', 'y', keys(t, [(0, 0), (.4, -3), (.9, 12), (1.4, 8), (1.95, 24), (2.6, 10), (3.2, 0)], 'flow'))
    c.set('grip', 'rotate', keys(t, [(0, 0), (.7, 4), (1.5, 13), (2.1, 6), (2.6, 9), (3.2, 0)], 'flow'))
    fan = bump(t, .4, 1.2, 2.9, 1.0) + .5 * bump(t, 1.6, 1.95, 2.4, 1.0)
    for k in range(NB):
        c.set(f'bill_{k}', 'rotate', (k - 2.5) * -3.2 * fan)
    c.set('torso', 'sy', 1 + bump(t, 1.38, 1.52, 1.75, .045) - bump(t, 2.15, 2.27, 2.55, .05))
    follow(c); weight(c)
    c.face('head', [(0, 'face_big_win'), (2.84, 'face_idle')]); take(c, 0, 1.2); take(c, 2.84, .7)
    c.event(.55, 'big_win_hit'); c.event(.8, 'land'); c.event(1.2, 'cash_rustle'); c.event(2.15, 'land')
    return c


def lose():
    D = 2.2; c = Clip(D); t = c.t
    c.set('hips', 'y', keys(t, [(0, 0), (.25, 3), (1.05, -26), (1.6, -20), (2.2, 0)], 'flow'))
    c.set('hips', 'x', keys(t, [(0, 0), (1.1, -8), (2.2, 0)]))
    c.set('torso', 'rotate', keys(t, [(0, 0), (1.15, -3.4), (1.6, -3), (2.2, 0)], 'flow'))
    c.set('chest', 'rotate', keys(t, [(0, 0), (1.2, -2.4), (2.2, 0)]))
    c.set('neck', 'rotate', keys(t, [(0, 0), (1.2, 2.5), (2.2, 0)]))
    c.set('head', 'rotate', keys(t, [(0, 0), (.3, -1), (1.2, 7.5), (1.7, 6), (2.2, 0)], 'flow'))
    c.set('head', 'y', keys(t, [(0, 0), (1.15, -9), (2.2, 0)]))
    c.set('grip', 'y', keys(t, [(0, 0), (.2, 2), (1.1, -15), (1.7, -12), (2.2, 0)], 'flow'))
    c.set('grip', 'rotate', keys(t, [(0, 0), (1.25, -7), (2.2, 0)]))
    close = bump(t, .3, 1.1, 2.0, 1.0)
    for k in range(NB):
        c.set(f'bill_{k}', 'rotate', (k - 2.5) * 1.3 * close)
    c.set('foot_right', 'x', bump(t, .7, 1.0, 1.4, 6)); c.set('foot_right', 'y', bump(t, .7, .85, 1.0, 5))
    c.set('shoe_right', 'rotate', bump(t, .7, .9, 1.3, 3))
    c.set('torso', 'sy', 1 - bump(t, .4, 1.2, 2.0, .02))
    follow(c, 1.3); weight(c)
    c.face('head', [(0, 'face_lose'), (1.84, 'face_idle')]); take(c, 0, .8); take(c, 1.84, .6)
    return c


def cash_show():
    D = 2.6; c = Clip(D); t = c.t
    c.set('hips', 'x', keys(t, [(0, 0), (1.25, -13), (1.6, -12), (2.6, 0)], 'flow'))
    c.set('hips', 'y', keys(t, [(0, 0), (.45, -4), (1.2, -8), (2.0, -3), (2.6, 0)], 'flow'))
    c.set('torso', 'rotate', keys(t, [(0, 0), (1.2, 2.2), (2.6, 0)]))
    c.set('chest', 'rotate', keys(t, [(0, 0), (1.3, 1.6), (2.6, 0)]))
    c.set('head', 'rotate', keys(t, [(0, 0), (.4, 1.5), (1.4, -5.5), (2.0, -4), (2.6, 0)], 'flow'))
    c.set('grip', 'y', keys(t, [(0, 0), (.35, -3), (1.25, 17), (1.8, 15), (2.6, 0)], 'flow'))
    c.set('grip', 'x', keys(t, [(0, 0), (1.25, 8), (2.6, 0)]))
    c.set('grip', 'rotate', keys(t, [(0, 0), (1.4, 8.5), (2.6, 0)]))
    spread = bump(t, .3, 1.35, 2.4, 1.0)
    for k in range(NB):
        c.set(f'bill_{k}', 'rotate', (k - 2.5) * -4.6 * spread)
    tap = bump(t, .95, 1.15, 1.36, 12) + bump(t, 1.4, 1.6, 1.82, 13)
    c.set('foot_right', 'y', tap); c.set('shoe_right', 'rotate', tap * .5)
    follow(c); weight(c)
    c.face('head', [(0, 'face_cash_show'), (2.24, 'face_idle')]); take(c, 0); take(c, 2.24, .6)
    c.event(.7, 'cash_rustle')
    return c


def cash_count():
    D = 6.4; c = Clip(D); t = c.t
    c.set('hips', 'y', keys(t, [(0, 0), (.6, -3), (5.8, -3), (6.4, 0)]))
    c.set('head', 'rotate', keys(t, [(0, 0), (.5, 2.2), (5.9, 2.2), (6.4, 0)]))
    c.set('neck', 'rotate', keys(t, [(0, 0), (.5, 1.2), (5.9, 1.2), (6.4, 0)]))
    c.set('grip', 'y', keys(t, [(0, 0), (.5, 2), (5.9, 2), (6.4, 0)]))
    c.set('grip', 'rotate', keys(t, [(0, 0), (.5, -1), (5.9, -1), (6.4, 0)]))
    hl = np.zeros_like(t); nod = np.zeros_like(t)
    for i in range(NB):                          # front bill first: thumbed over, one by one
        k = NB - 1 - i
        t0 = .62 + .85 * i
        flick = bump(t, t0, t0 + .22, t0 + .6, 1.0)
        c.add(f'bill_{k}', 'rotate', -26 * flick)
        c.add(f'bill_{k}_tip', 'rotate', -14 * bump(t, t0, t0 + .12, t0 + .3, 1.0) + 6 * bump(t, t0 + .3, t0 + .42, t0 + .6, 1.0))
        # the bills behind open up a little as each one passes
        for j in range(k):
            c.add(f'bill_{j}', 'rotate', -2.2 * bump(t, t0 + .05, t0 + .25, t0 + .6, 1.0))
        hl += bump(t, t0 - .08, t0 + .06, t0 + .3, 1.0)
        nod += bump(t, t0 + .1, t0 + .25, t0 + .5, 1.0)
        c.event(t0 + .22, 'bill_count', int=i + 1)
    c.set('hand_left', 'rotate', -4 * hl)
    c.add('head', 'rotate', .9 * nod)
    follow(c); weight(c, .5)
    c.face('head', [(0, 'face_cash_count'), (6.04, 'face_idle')]); take(c, 0, .7); take(c, 6.04, .6)
    return c


def enter():
    D = 1.2; c = Clip(D); t = c.t
    c.set('root', 'y', keys(t, [(0, -100), (.75, 3), (.95, -1), (1.2, 0)], 'flow'))
    s = .88 + .12 * ease_out(t / .9)
    c.set('root', 'sx', np.minimum(s, 1)); c.set('root', 'sy', np.minimum(s, 1))
    c.set('head', 'rotate', keys(t, [(0, 0), (.3, 3.8), (.8, -1.4), (1.2, 0)], 'flow'))
    c.set('grip', 'y', keys(t, [(0, 0), (.35, -6), (.8, 3), (1.2, 0)], 'flow'))
    for side, ph in (('left', 0), ('right', .26)):
        lift = bump(t, .25 + ph, .36 + ph, .48 + ph, 7)
        c.set(f'foot_{side}', 'y', lift); c.set(f'shoe_{side}', 'rotate', lift * (.4 if side == 'right' else -.4))
    follow(c, gains=CALM)
    c.event(.5, 'land')
    return c


def exit_():
    """the walk-off: the old clip's own sink and shrink (its curves, sampled), the hat and head calm"""
    D = .7; c = Clip(D); t = c.t
    c.set('root', 'y', keys(t, [(0, 0), (.0875, -1.1), (.175, -4.4), (.2625, -9.7), (.35, -18.9), (.4375, -28.9), (.525, -40.9), (.6125, -55.2), (.7, -75)], 'flow'))
    sc = keys(t, [(0, 1), (.0875, .998), (.175, .993), (.2625, .984), (.35, .970), (.4375, .954), (.525, .934), (.6125, .911), (.7, .88)], 'flow')
    c.set('root', 'sx', sc); c.set('root', 'sy', sc)
    c.set('head', 'rotate', keys(t, [(0, 0), (.35, -1.2), (.7, .4)], 'flow'))
    for side, ph in (('left', 0), ('right', .14)):
        c.set(f'foot_{side}', 'y', bump(t, .12 + ph, .25 + ph, .4 + ph, 3))
    follow(c, gains=CALM)
    return c


CLIPS = {'idle': idle, 'anticipation': anticipation, 'win': win, 'big_win': big_win, 'lose': lose,
         'cash_show': cash_show, 'cash_count': cash_count, 'enter': enter, 'exit': exit_}
