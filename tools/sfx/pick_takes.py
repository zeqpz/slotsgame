"""Score every candidate event, keep the best + most alike `keep` per sound (or hand picks in
PICKS), write picks.json and a review sheet per sound (picked ones framed green).
Usage: python select.py [name ...]"""
import os, sys, json, itertools
import numpy as np
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audiolib import read_wav
import process2 as P

HERE = os.path.dirname(os.path.abspath(__file__))
SHEETS = os.path.join(HERE, "sheets2")
PICKS = json.load(open(os.path.join(HERE, "manual_picks.json"))) if os.path.exists(os.path.join(HERE, "manual_picks.json")) else {}


def penalty(c, mn, mx):
    p = 0.0
    p += max(0, c["hiss"] + 66) * 1.0          # residual generator hiss, dB re the event's peak
    if c["dur"] < mn: p += 40 * (mn - c["dur"]) / max(mn, .01)
    if c["dur"] > mx * 1.02: p += 20 * (c["dur"] - mx)
    if c["cut"]: p += 6
    p += max(0, -c["ev_pk"]) * 0.7
    p += max(0, c["nf_raw"] + 55) * 0.25
    return p


def main():
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    db = json.load(open(os.path.join(HERE, "cand.json")))
    picks = json.load(open(os.path.join(HERE, "picks.json"))) if os.path.exists(os.path.join(HERE, "picks.json")) else {}
    os.makedirs(SHEETS, exist_ok=True)
    filt = sys.argv[1:]
    for name, cs in db.items():
        if filt and name not in filt:
            continue
        if not cs:
            print(name, "NO CANDIDATES"); continue
        mn, mx, keep, _ = P.T[name]
        for c in cs:
            c["pen"] = penalty(c, mn, mx)
        cs.sort(key=lambda c: c["pen"])
        if name in PICKS:
            chosen = [c for f in PICKS[name] for c in cs if c["file"] == f]
        else:
            top = cs[:max(keep, min(8, len(cs)))]
            best, bestv = None, 1e9
            for combo in itertools.combinations(range(len(top)), min(keep, len(top))):
                B = [np.array(top[i]["bands"]) for i in combo]
                dist = np.mean([np.abs(a - b).mean() for a, b in itertools.combinations(B, 2)]) if len(B) > 1 else 0
                v = dist * 2 + np.mean([top[i]["pen"] for i in combo])
                if v < bestv:
                    best, bestv = combo, v
            chosen = [top[i] for i in best]
        picks[name] = [c["file"] for c in chosen]
        show = cs[:12]
        for c in chosen:
            if c not in show: show.append(c)
        cols = 3
        rows = -(-len(show) // cols)
        fig, axes = plt.subplots(rows, cols, figsize=(12, 1.6 * rows), squeeze=False)
        for ax in axes.flat: ax.axis("off")
        for ax, c in zip(axes.flat, show):
            ax.axis("on")
            x, sr, _ = read_wav(os.path.join(P.CAND, name, c["file"]))
            mm = x.mean(1)
            nper = 256 if len(mm) < sr * .3 else 512
            f, t, S = signal.spectrogram(mm, sr, nperseg=min(nper, len(mm)), noverlap=min(nper, len(mm)) * 3 // 4)
            ax.pcolormesh(t, f / 1000, 10 * np.log10(S + 1e-14), vmin=-125, vmax=-35, cmap="magma", shading="auto")
            tt = np.arange(len(mm)) / sr
            ax2 = ax.twinx(); ax2.plot(tt, mm, color="cyan", lw=.4, alpha=.6); ax2.set_ylim(-1, 1); ax2.axis("off")
            sel = c in chosen
            ax.set_title(f"{'** ' if sel else ''}{c['file']} {c['dur']:.3f}s pk{c['peak']:.1f} M{c['mmax']:.1f} hiss{c['hiss_raw']:.0f}>{c['hiss']:.0f} pen{c['pen']:.1f}{' CUT' if c['cut'] else ''}",
                         fontsize=7, color="green" if sel else "black")
            ax.tick_params(labelsize=5)
        fig.tight_layout(); fig.savefig(os.path.join(SHEETS, name + ".png"), dpi=72); plt.close(fig)
        print(f"{name:14s} keep {picks[name]}  " + "  ".join(f"{c['dur']:.2f}s hiss{c['hiss_raw']:.0f}>{c['hiss']:.0f}dBr pk{c['peak']:.1f}" for c in chosen))
    json.dump(picks, open(os.path.join(HERE, "picks.json"), "w"), indent=1)
    json.dump(db, open(os.path.join(HERE, "cand.json"), "w"), indent=0)


if __name__ == "__main__":
    main()
