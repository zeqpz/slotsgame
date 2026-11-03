"""Final set: picks (cand/) + synth/ -> build/sfx_<file>_<n>.wav at the key's loudness target,
peak-limited, faded, 44.1 kHz stereo s16 like the existing set. Prints the QA table and
writes final.json (key -> [files], vol) for the index.html wiring."""
import os, sys, json, shutil
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audiolib import read_wav, write_wav, lufs, analyze, noise_floor
import process2 as P

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
picks = json.load(open(os.path.join(HERE, "picks.json")))
cand = json.load(open(os.path.join(HERE, "cand.json")))

# sfx key: (source, file stem, target momentary-max LUFS, SFX_VOL, what)
# source "gen:<name>" = the picked takes; "syn:<prefix>:<n,n,..>" = synth files
FINAL = {
    # win presentation
    "sprayLineShort": ("gen:spray_short", "spray_short", -22, .36, "spray hiss sweep, short line"),
    "sprayLineLong": ("gen:spray_long", "spray_long", -22, .32, "spray hiss sweep, long line"),
    "paintDrip": ("syn:paint_drip:1,2,3,5,6", "paint_drip", -24, .3, "paint drip plip"),
    "glowPulse": ("syn:glow_pulse:1,2", "glow_pulse", -25, .26, "symbol glow swell"),
    "shine": ("syn:shine:1,2", "shine", -24, .3, "chrome shine swipe + glints"),
    "sparkle": ("syn:sparkle:1,2,3", "sparkle", -24, .28, "glitter sparkle run"),
    "glint": ("syn:glint:1,2,3,4", "glint", -25, .24, "single bright ting"),
    "countTick": ("gen:count_tick", "count_tick", -26, .26, "win counter tick"),
    "countEnd": ("gen:count_end", "count_end", -21, .5, "counter lands: register ka-chunk + bell"),
    "multSlam": ("gen:mult_slam", "mult_slam", -17, .62, "multiplier slam"),
    "countWhoosh": ("gen:count_whoosh", "count_whoosh", -23, .4, "rising whoosh, count-up again"),
    "floatAway": ("gen:float_away", "float_away", -24, .36, "airy whoosh, number floats off"),
    "paintBurst": ("gen:paint_burst", "paint_burst", -22, .4, "wet paint pop, icon burst"),
    # board foley
    "landSoft": ("gen:land_soft", "land_soft", -24, .26, "soft table thud"),
    "landBag": ("gen:land_bag", "land_bag", -24, .28, "cash bag thud + rustle"),
    "landCan": ("gen:land_can", "land_can", -24, .26, "spray can tonk + ball rattle"),
    "landChain": ("gen:land_chain", "land_chain", -25, .24, "gold chain clink"),
    "landCoin": ("gen:land_coin", "land_coin", -25, .24, "coin clink"),
    "landDice": ("gen:land_dice", "land_dice", -25, .24, "dice clatter"),
    "landBaggie": ("gen:land_baggie", "land_baggie", -25, .24, "plastic baggie crinkle"),
    "landFabric": ("gen:land_fabric", "land_fabric", -24, .28, "beanie / shirt fabric flop"),
    "landHoodie": ("gen:land_hoodie", "land_hoodie", -24, .28, "hoodie whump"),
    "landMarker": ("gen:land_marker", "land_marker", -25, .24, "marker clack"),
    "landBrick": ("gen:land_brick", "land_brick", -21, .34, "brick knock (Multi)"),
    "landBoard": ("gen:land_board", "land_board", -24, .26, "skateboard clack"),
    "landBox": ("gen:land_box", "land_box", -24, .28, "shoe box thump"),
    "landShoe": ("gen:land_shoe", "land_shoe", -24, .28, "sneaker thud"),
    "landBoombox": ("gen:land_boombox", "land_boombox", -24, .26, "boombox plastic thunk"),
    "landMetal": ("gen:land_metal", "land_metal", -25, .24, "die-cast toy clunk"),
    "landCard": ("gen:land_card", "land_card", -25, .24, "hang tag card snap"),
    "landToy": ("gen:land_toy", "land_toy", -25, .26, "chunky plastic toy clack"),
    "cascade": ("gen:cascade", "cascade", -23, .34, "tumble clatter"),
    "reelStop": ("gen:reel_stop", "reel_stop", -22, .3, "reel stop thunk"),
    "canShake": ("gen:can_shake", "can_shake", -23, .34, "spray can shake, spin start"),
    # HUD
    "uiClick": ("gen:ui_click", "ui_click", -26, .32, "button click"),
    "uiHover": ("gen:ui_hover", "ui_hover", -28, .14, "button hover tick"),
    "sliderTick": ("gen:slider_tick", "slider_tick", -27, .22, "volume slider detent"),
    "swishIn": ("gen:swish_in", "swish_in", -25, .3, "panel open swoosh"),
    "swishOut": ("gen:swish_out", "swish_out", -25, .28, "panel close swoosh"),
    "capPop": ("gen:cap_pop", "cap_pop", -24, .38, "spray cap pop (bonus open)"),
    "buyConfirm": ("gen:buy_confirm", "buy_confirm", -21, .5, "bonus buy cha-ching"),
    "fsTick": ("gen:fs_tick", "fs_tick", -25, .32, "free-spin counter flip"),
    # character foley
    "sneakerScuff": ("gen:sneaker_scuff", "sneaker_scuff", -26, .2, "sneaker scuff"),
    "cigarPuff": ("gen:cigar_puff", "cigar_puff", -27, .22, "cigar ember crackle"),
    "lighter": ("gen:lighter", "lighter", -25, .26, "flip lighter clink + strike"),
    "cashRiffle": ("gen:cash_riffle", "cash_riffle", -25, .28, "bills riffle"),
    "cashFlick": ("gen:cash_flick", "cash_flick", -25, .28, "single bill snap"),
}


def master(y, sr, tgt, lim_db=2.0):
    _, M = lufs(y, sr)
    pk = 20 * np.log10(np.abs(y).max() + 1e-12)
    gain = min(tgt - M, -1.5 - pk + lim_db)
    y = y * 10 ** (gain / 20)
    y = P.limit(y, sr)
    # de-click: 0.3 ms in (never smears a transient), 4 ms minimum out, ends exactly at zero
    nin = max(2, int(.0003 * sr)); nout = max(2, min(len(y) // 4, int(.004 * sr)))
    y[:nin] *= np.linspace(0, 1, nin)[:, None]
    y[-nout:] *= (np.linspace(1, 0, nout) ** 2)[:, None]
    y[0] = 0; y[-1] = 0
    return y - 0  # (DC was removed at the source)


def main():
    shutil.rmtree(BUILD, ignore_errors=True); os.makedirs(BUILD)
    out, rows = {}, []
    for key, (src, stem, tgt, vol, what) in FINAL.items():
        if src.startswith("gen:"):
            name = src[4:]
            files = [os.path.join(P.CAND, name, f) for f in picks[name]]
            meta = {c["file"]: c for c in cand[name]}
            hiss = [meta[f]["hiss"] for f in picks[name]]
            hraw = [meta[f]["hiss_raw"] for f in picks[name]]
        else:
            _, pre, ns = src.split(":")
            files = [os.path.join(HERE, "synth", f"{pre}_{n}.wav") for n in ns.split(",")]
            hiss = [None] * len(files); hraw = [None] * len(files)
        lst = []
        for i, f in enumerate(files, 1):
            x, sr, _ = read_wav(f)
            assert sr == 44100 and x.shape[1] == 2
            lim = 1.0 if key in ("countTick", "uiClick", "uiHover", "sliderTick", "fsTick", "capPop", "paintDrip", "glint") else 2.0
            y = master(x, sr, tgt, lim)
            fn = f"sfx_{stem}_{i}.wav"
            write_wav(os.path.join(BUILD, fn), y, sr)
            a = analyze(y, sr)
            clip = int((np.abs(y) >= .999).sum())
            dc = float(np.abs(y.mean(0)).max())
            rows.append((fn, a["dur"], a["peak_db"], lufs(y, sr)[1], a["lufs"], noise_floor(y, sr), hraw[i - 1], hiss[i - 1],
                         clip, abs(y[0]).max(), abs(y[-1]).max(), dc))
            lst.append(fn)
        out[key] = dict(files=lst, vol=vol, what=what)
    print(f"{'file':26s} {'dur':>5s} {'peak':>6s} {'Mmax':>6s} {'I':>6s} {'nfOut':>6s} {'hissRaw':>7s} {'hiss':>6s} clip  edge  dc")
    for r in rows:
        fn, d, pk, M, I, nf, hr, h, cl, e0, e1, dc = r
        hs = lambda v: "  synth" if v is None else f"{v:7.1f}"
        print(f"{fn:26s} {d:5.2f} {pk:6.1f} {M:6.1f} {I:6.1f} {nf:6.1f} {hs(hr)} {hs(h)[1:]} {cl:4d} {max(e0, e1):5.3f} {dc:.4f}")
    json.dump(out, open(os.path.join(HERE, "final.json"), "w"), indent=1)
    print(len(rows), "files")


if __name__ == "__main__":
    main()
