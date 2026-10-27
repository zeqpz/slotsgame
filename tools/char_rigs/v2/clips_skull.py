"""SMOKE SKULL clips: same names, lengths, faces and beats as before; the motion runs through
pelvis -> torso -> chest -> neck -> head -> beanie -> beanie_tip with overlap and follow-through,
the jaw flaps on landings, the drawstrings and the loose laces swing after the body, the arms are IK
chains to the hands in the pocket, the legs IK chains to the planted shoes."""
import math
import numpy as np
from motionkit import Clip, keys, bump, osc, hop, lag, spring, settle, smooth, ease, ease_out, ease_in

CHAIN = ['torso', 'chest', 'neck', 'head', 'beanie', 'beanie_tip']
LAGS = {'chest': (.03, 2.8, .55), 'neck': (.04, 2.6, .5), 'head': (.05, 2.3, .46), 'beanie': (.07, 2.1, .45),
        'beanie_tip': (.09, 2.0, .42)}


def world_of(c, chain_upto):
    w = np.zeros(c.n)
    for b in ['pelvis'] + CHAIN:
        w = w + c.get(b, 'rotate')
        if b == chain_upto: break
    return w


GAIN = {'head': .85, 'beanie': .3, 'beanie_tip': .4}
CALM = {'head': .6, 'beanie': .12, 'beanie_tip': .15}   # walk-on / walk-off: the whole figure moves, the hat stays put on it


def follow(c, scale_lag=1.0, gains=None):
    world = c.get('pelvis', 'rotate') + c.get('torso', 'rotate')
    for b in CHAIN[1:]:
        d, f, z = LAGS[b]
        local = c.get(b, 'rotate')
        new = lag(c, b, world, local, d * scale_lag, f, z)
        g = (gains or GAIN).get(b, GAIN.get(b, 1.0))
        new = local + g * (new - local)          # how much of the trailing this link shows
        c.set(b, 'rotate', new)
        world = world + new
    chest_w = world_of(c, 'chest')
    # the drawstrings hang: they keep pointing down while the chest turns, then swing back
    for s in ('string_left', 'string_right'):
        loc = c.get(s, 'rotate')
        c.set(s, 'rotate', lag(c, s, chest_w, loc - 0 * chest_w, .02, 1.6, .22))
    # the loose laces trail their shoes
    for side in ('left', 'right'):
        sw = c.get(f'shoe_{side}', 'rotate')
        loc = c.get(f'lace_{side}', 'rotate')
        lift = c.get(f'foot_{side}', 'y')
        vy = np.gradient(smooth(lift + c.get('motion', 'y'), c.t, .03), c.t)
        swing = np.clip(-vy * .03, -5, 5)
        swing = np.where(swing > 0, swing * .5, swing) * (1 if side == 'left' else -1)   # a lace falls more than it lifts
        tgt = loc + swing
        c.set(f'lace_{side}', 'rotate', lag(c, f'lace_{side}', sw, tgt, .03, 2.2, .25))


def weight(c, amount=1.0, bone='motion'):
    y = smooth(c.get(bone, 'y') + c.get('pelvis', 'y'), c.t, .03)
    a = smooth(np.gradient(np.gradient(y, c.t), c.t), c.t, .03)
    sq = np.clip(-a * 2.6e-5 * amount, -.05, .05)
    sy = 1 + spring(sq, c.t, 3.4, .42, c.loop)
    if not c.loop: sy = settle(c, sy, 1)
    c.set('torso', 'sy', c.get('torso', 'sy') * sy)
    c.set('torso', 'sx', c.get('torso', 'sx') * (1 - .5 * (sy - 1)))
    hy = spring(np.clip(-a * .0016 * amount, -6, 6), c.t, 2.6, .5, c.loop)
    if not c.loop: hy = settle(c, hy, 0)
    c.add('head', 'y', hy)
    # the jaw drops a touch on a landing
    jw = spring(np.clip(a * .0008 * amount, 0, 3.5), c.t, 3.0, .45, c.loop)
    if not c.loop: jw = settle(c, jw, 0)
    c.add('jaw', 'rotate', -np.maximum(jw, 0))


def take(c, at, amp=.8):
    k = 1.0 if c.loop else min(1.0, max(.35, (c.dur - .03 - at) / (.56 - .09)))   # it must be over before the clip ends
    kt = np.array([0, .09, .22, .38, .56]) * k + at - (.09 * k if at > 0 else 0)
    amp = amp * .55
    sy = np.interp(c.t, kt, [1, 1 - .06 * amp, 1 + .03 * amp, 1 - .006 * amp, 1])
    sx = np.interp(c.t, kt, [1, 1 + .045 * amp, 1 - .018 * amp, 1 + .003 * amp, 1])
    c.set('head', 'sx', c.get('head', 'sx') * smooth(sx, c.t, .045))
    c.set('head', 'sy', c.get('head', 'sy') * smooth(sy, c.t, .045))


def chew(c, at, amt=2.6, dur=.4):
    c.add('jaw', 'rotate', -bump(c.t, at, at + dur * .45, at + dur, amt))


def idle():
    D = 4.0; c = Clip(D, loop=True); t = c.t
    c.set('pelvis', 'y', -2 * (1 - np.cos(2 * math.pi * t / 2.0)))
    c.set('pelvis', 'x', osc(t, 4.0, 5.5, .2))
    c.set('pelvis', 'rotate', osc(t, 4.0, .7, .22))
    c.set('torso', 'rotate', osc(t, 4.0, -1.6, .02))
    c.set('chest', 'rotate', osc(t, 4.0, -.6, .1))
    c.set('head', 'rotate', osc(t, 4.0, 1.7, .55) + osc(t, 2.0, .6, .2))
    c.set('head', 'y', 1.0 * (1 - np.cos(2 * math.pi * (t / 2.0 - .12))))
    c.set('beanie', 'rotate', osc(t, 2.0, .5, .3))
    for at in (.35, 2.55):                        # a chew on the cigar, twice a loop
        chew(c, at, 2.4)
    c.set('cigar', 'rotate', -bump(t, .35, .52, .75, 2.2) - bump(t, 2.55, 2.72, 2.95, 2.6))
    # the hands shift in the pocket
    c.set('hand_left', 'y', 2 * np.sin(2 * math.pi * (t / 4.0 + .1)))
    c.set('hand_right', 'y', 2 * np.sin(2 * math.pi * (t / 4.0 + .35)))
    # a slow tap of the front foot, then the back one
    tapl = bump(t, 1.45, 1.75, 2.1, 9)
    c.set('foot_left', 'y', tapl); c.set('shoe_left', 'rotate', -tapl * .3)
    tapr = bump(t, 3.25, 3.52, 3.85, 8)
    c.set('foot_right', 'y', tapr); c.set('shoe_right', 'rotate', tapr * .22)
    follow(c); weight(c, .6, 'pelvis')
    c.face('face', [(0, 'face_idle')])
    for s in ('ash_cap', 'ash_1', 'ash_2', 'ash_3', 'ash_4'):
        c.slots.setdefault(s, {})['attachment'] = [{'name': None}]
    return c


def anticipation():
    D = 1.6; c = Clip(D); t = c.t
    c.set('torso', 'rotate', keys(t, [(0, 0), (.45, 2.1), (1.25, -2.1), (1.6, 0)], 'flow'))
    c.set('torso', 'x', keys(t, [(0, 0), (.4, 4.3), (1.2, -4.3), (1.6, 0)], 'flow'))
    c.set('pelvis', 'y', keys(t, [(0, 0), (.8, 8.5), (1.6, 0)]))
    c.set('head', 'rotate', keys(t, [(0, 0), (.48, 3), (1.27, -3), (1.6, 0)], 'flow'))
    c.set('head', 'y', keys(t, [(0, 0), (.47, 4), (1.27, -4), (1.6, 0)], 'flow'))
    chew(c, .55, 3.5, .7)
    c.set('cigar', 'rotate', keys(t, [(0, 0), (.6, -4), (1.0, 2), (1.6, 0)], 'flow'))
    # up on his toes, twice
    rise = bump(t, .1, .38, .62, 9) + bump(t, .72, .98, 1.3, 9)
    for side in ('left', 'right'):
        c.set(f'foot_{side}', 'y', rise)
    c.set('shoe_left', 'rotate', -rise * .25); c.set('shoe_right', 'rotate', rise * .1)
    c.set('hand_left', 'y', bump(t, .2, .7, 1.3, 4)); c.set('hand_right', 'y', bump(t, .3, .8, 1.4, 4))
    follow(c); weight(c, 1, 'pelvis')
    c.face('face', [(0, 'face_anticipation'), (1.24, 'face_idle')]); take(c, 0); take(c, 1.24, .6)
    return c


def win():
    D = 2.4; c = Clip(D); t = c.t
    y = np.where(t < .38, keys(t, [(0, 0), (.3, -8), (.38, 0)]), 0)
    y += hop(t, .38, .98, 30)
    y += np.where((t > .98) & (t < 1.2), keys(t, [(.98, 0), (1.08, -9), (1.2, 0)]), 0)
    y += hop(t, 1.2, 1.7, 21)
    y += np.where(t >= 1.7, keys(t, [(1.7, 0), (1.8, -7), (2.0, 1.5), (2.2, -1), (2.4, 0)]), 0)
    c.set('motion', 'y', smooth(y, t, .012))
    c.set('motion', 'x', keys(t, [(0, 0), (.9, -4.4), (1.5, 4.4), (2.4, 0)], 'flow'))
    c.set('torso', 'rotate', keys(t, [(0, 0), (.6, 1), (1.03, -4.4), (1.57, 4.4), (2.0, -1), (2.4, 0)], 'flow'))
    c.set('chest', 'rotate', keys(t, [(0, 0), (1.05, -2), (1.6, 2), (2.4, 0)], 'flow'))
    c.set('head', 'rotate', keys(t, [(0, 0), (.6, -1), (1.05, 6.5), (1.57, -5.8), (2.0, 1), (2.4, 0)], 'flow'))
    chew(c, 1.0, 5.5, .5)                           # a laugh round the cigar
    c.add('jaw', 'rotate', -bump(t, 1.5, 1.6, 1.85, 3))
    for side, ph in (('left', 0), ('right', .03)):
        fy = hop(t, .42 + ph, .94 + ph, 9) + hop(t, 1.24 + ph, 1.66 + ph, 8)
        c.set(f'foot_{side}', 'y', fy)
        c.set(f'foot_{side}', 'x', (fy > 0) * 0 + bump(t, .4, .7, 1.0, -4 if side == 'left' else 4))
    c.set('shoe_left', 'rotate', bump(t, .4, .7, 1.0, 3)); c.set('shoe_right', 'rotate', bump(t, .4, .7, 1.0, -2))
    c.set('hand_left', 'y', bump(t, .3, .7, 1.2, 4)); c.set('hand_right', 'y', bump(t, .35, .75, 1.25, 4))
    follow(c); weight(c)
    c.face('face', [(0, 'face_win'), (2.04, 'face_idle')]); take(c, 0); take(c, 2.04, .6)
    c.event(.648, 'win_hit'); c.event(.98, 'land'); c.event(1.7, 'land')
    return c


def big_win():
    D = 3.6; c = Clip(D); t = c.t
    y = np.where(t < .55, keys(t, [(0, 0), (.45, -12), (.55, 0)]), 0)
    y += hop(t, .55, 1.4, 48)
    y += np.where((t > 1.4) & (t < 1.75), keys(t, [(1.4, 0), (1.52, -13), (1.75, 0)]), 0)
    y += hop(t, 1.75, 2.45, 36)
    y += np.where(t >= 2.45, keys(t, [(2.45, 0), (2.57, -10), (2.85, 2), (3.15, -1), (3.6, 0)]), 0)
    c.set('motion', 'y', smooth(y, t, .012))
    c.set('motion', 'x', keys(t, [(0, 0), (1.4, -7.5), (2.2, 7.5), (3.0, -2), (3.6, 0)], 'flow'))
    c.set('torso', 'rotate', keys(t, [(0, 0), (.9, 1.5), (1.5, -7.5), (2.3, 7.5), (2.9, -2), (3.6, 0)], 'flow'))
    c.set('chest', 'rotate', keys(t, [(0, 0), (1.5, -3), (2.3, 3), (3.6, 0)], 'flow'))
    c.set('head', 'rotate', keys(t, [(0, 0), (.9, -2), (1.53, 10), (2.33, -9), (2.9, 2), (3.6, 0)], 'flow'))
    chew(c, 1.3, 8.5, .9)
    for side, ph in (('left', 0), ('right', .04)):
        fy = hop(t, .6 + ph, 1.36 + ph, 16) + hop(t, 1.8 + ph, 2.4 + ph, 14)
        c.set(f'foot_{side}', 'y', fy)
        c.set(f'foot_{side}', 'x', bump(t, .6, 1.0, 1.4, -6 if side == 'left' else 6))
    c.set('shoe_left', 'rotate', bump(t, .6, 1.0, 1.4, 4)); c.set('shoe_right', 'rotate', bump(t, .6, 1.0, 1.4, -3))
    c.set('hand_left', 'y', bump(t, .4, 1.0, 1.6, 5)); c.set('hand_right', 'y', bump(t, .45, 1.05, 1.65, 5))
    follow(c); weight(c)
    c.face('face', [(0, 'face_big_win'), (3.24, 'face_idle')]); take(c, 0, 1.0); take(c, 3.24, .6)
    c.event(.972, 'big_win_hit'); c.event(1.4, 'land'); c.event(2.45, 'land')
    return c


def lose():
    D = 2.0; c = Clip(D); t = c.t
    c.set('head', 'rotate', keys(t, [(0, 0), (.3, 1), (1.15, -8.6), (1.6, -7), (2.0, 0)], 'flow'))
    c.set('head', 'y', keys(t, [(0, 0), (1.0, -15), (2.0, 0)]))
    c.set('neck', 'rotate', keys(t, [(0, 0), (1.1, -2), (2.0, 0)]))
    c.set('torso', 'rotate', keys(t, [(0, 0), (1.1, -3.4), (2.0, 0)]))
    c.set('pelvis', 'y', keys(t, [(0, 0), (1.03, -5), (2.0, 0)]))
    c.add('jaw', 'rotate', -bump(t, .5, 1.0, 1.7, 4))          # a sigh
    c.set('cigar', 'rotate', bump(t, .5, 1.05, 1.7, 7))         # the cigar droops with it
    sh = bump(t, .55, .8, 1.05, 1.0)
    c.set('foot_right', 'x', 7 * sh); c.set('foot_right', 'y', bump(t, .55, .7, .9, 4.5))
    c.set('shoe_right', 'rotate', -3 * sh)
    c.set('hand_left', 'y', -bump(t, .4, 1.0, 1.8, 4)); c.set('hand_right', 'y', -bump(t, .4, 1.0, 1.8, 4))
    follow(c, 1.3); weight(c, 1, 'pelvis')
    c.face('face', [(0, 'face_lose'), (1.64, 'face_idle')]); take(c, 0, .7); take(c, 1.64, .5)
    return c


def enter():
    D = 1.2; c = Clip(D); t = c.t
    c.set('motion', 'y', keys(t, [(0, -100), (.75, 3), (.95, -1), (1.2, 0)], 'flow'))
    s = .88 + .12 * ease_out(t / .9)
    c.set('motion', 'sx', np.minimum(s, 1)); c.set('motion', 'sy', np.minimum(s, 1))
    c.set('head', 'rotate', keys(t, [(0, 0), (.27, 3.8), (.8, -1.4), (1.2, 0)], 'flow'))
    for side, ph in (('left', 0), ('right', .26)):
        lift = bump(t, .25 + ph, .36 + ph, .48 + ph, 7)
        c.set(f'foot_{side}', 'y', lift)
    follow(c, gains=CALM)
    c.event(.5, 'land')
    return c


def exit_():
    """the walk-off: the old clip's own sink and shrink (its curves, sampled), the hat and head calm"""
    D = .7; c = Clip(D); t = c.t
    c.set('motion', 'y', keys(t, [(0, 0), (.0875, -1.1), (.175, -4.4), (.2625, -9.7), (.35, -18.9), (.4375, -28.9), (.525, -40.9), (.6125, -55.2), (.7, -75)], 'flow'))
    sc = keys(t, [(0, 1), (.0875, .998), (.175, .993), (.2625, .984), (.35, .970), (.4375, .954), (.525, .934), (.6125, .911), (.7, .88)], 'flow')
    c.set('motion', 'sx', sc); c.set('motion', 'sy', sc)
    c.set('head', 'rotate', keys(t, [(0, 0), (.35, -1.2), (.7, .4)], 'flow'))
    for side, ph in (('left', 0), ('right', .14)):
        c.set(f'foot_{side}', 'y', bump(t, .12 + ph, .25 + ph, .4 + ph, 3))
    follow(c, gains=CALM)
    return c


def ember_loop():
    """the glow on the ember breathes (the old clip's pulse, as one smooth curve)"""
    D = 1.2; c = Clip(D, loop=True); t = c.t
    a = .22 + .1 * np.sin(2 * math.pi * t / D) + .015 * np.sin(2 * math.pi * 3 * t / D + 1)
    ks = [{'value': round(float(a[0]), 4)}]
    for tt, v in list(zip(t, a))[6::6]:
        ks.append({'time': round(float(tt), 4), 'value': round(float(v), 4)})
    if ks[-1].get('time', 0) < D - 1e-4:
        ks.append({'time': D, 'value': ks[0]['value']})
    c.slots['ember_glow'] = {'alpha': ks}
    return c


def ash_break():
    D = 2.4; c = Clip(D); t = c.t
    # the ash grows on the tip; he taps the cigar (a flick of the head and the cigar) and it breaks off
    grow = ease(t / .95)
    c.set('ash_cap', 'sx', .25 + .75 * grow); c.set('ash_cap', 'sy', .7 + .3 * grow)
    c.set('cigar', 'rotate', -bump(t, .55, .83, 1.05, 6.8) + bump(t, .83, .95, 1.25, 2))
    c.set('head', 'rotate', keys(t, [(0, 0), (.5, .8), (.85, -1.5), (1.2, -4), (2.4, 0)], 'flow'))
    chew(c, .6, 2.5, .4)
    for k, (dx, sp, sc) in enumerate(((-88, 201.5, .78), (-29, -201.5, .86), (29, 201.5, .94), (88, -201.5, 1.02)), 1):
        u = np.clip((t - .85) / (D - .85), 0, 1)
        c.set(f'ash_{k}', 'x', dx * u)
        c.set(f'ash_{k}', 'y', 4 * bump(t, .85, .95, 1.1, 1) - 394 * u ** 2)
        c.set(f'ash_{k}', 'rotate', sp * u)
        c.set(f'ash_{k}', 'sx', np.full(c.n, sc)); c.set(f'ash_{k}', 'sy', np.full(c.n, sc))
    follow(c)
    c.face('face', [(0, 'face_anticipation'), (1.3, 'face_win'), (2.04, 'face_idle')])
    take(c, 0, .6); take(c, 1.3, .7); take(c, 2.04, .5)
    c.slots['ash_cap'] = {'attachment': [{'name': 'ash_0'}, {'time': .85, 'name': None}]}
    for k in range(1, 5):
        c.slots[f'ash_{k}'] = {'attachment': [{'name': None}, {'time': .85, 'name': f'ash_{k}'}, {'time': 2.05, 'name': None}],
                               'alpha': [{'value': 0}, {'time': .85, 'value': 1}, {'time': 1.55, 'value': 1}, {'time': 2.05, 'value': 0}]}
    c.event(.85, 'ash_split')
    return c


CLIPS = {'idle': idle, 'anticipation': anticipation, 'win': win, 'big_win': big_win, 'lose': lose,
         'enter': enter, 'exit': exit_, 'ember_loop': ember_loop, 'ash_break': ash_break}


def post(j):
    """the jaw swaps with the face: every face attachment key, mirrored onto the jaw slot"""
    for a in j['animations'].values():
        keys = a.get('slots', {}).get('face', {}).get('attachment')
        if not keys:
            continue
        a['slots'].setdefault('jaw', {})['attachment'] = [
            dict(k, name=k['name'].replace('face_', 'jaw_', 1)) if k.get('name') else dict(k) for k in keys]
