"""The before/after table (markdown) from iosprobe3.py results (Smukiez & Skelly phone pass, 2026-11-16; after
Tipsy Harvest's table3.py).
usage: table3.py DIR [BEFORE_TAG AFTER_TAG]   (DIR holds <tag>_<scenario>.json, as runset.sh writes them)
"""
import json, os, sys

d = sys.argv[1]
TB, TA = (sys.argv[2], sys.argv[3]) if len(sys.argv) > 3 else ("before", "after")
NAMES = {
    "boot_p": "boot (live: load, ident, features, first touch, a spin), portrait 390x844",
    "boot_l": "boot, landscape 844x390", "boot_crios": "boot, Chrome for iOS UA",
    "boot_bar": "boot, Safari toolbar (390x664 window, 844 screen)",
    "tumble_p": "base 36873 (7 tumbles, 4 Multis), portrait", "tumble_l": "base 36873, landscape",
    "tumble_crios": "base 36873, Chrome for iOS UA",
    "bigwin_p": "9,120x big win (base 33152), portrait", "bigwin_l": "big win 33152, landscape",
    "bigwin_bar": "big win 33152, Safari toolbar",
    "bonus_p": "bonus (bonus 5: 12 free spins, 963x), portrait", "bonus_l": "bonus 5, landscape",
    "extreme_p": "extreme bonus (extremebonus 3: 17 spins), portrait",
}


def load(tag, sc):
    f = os.path.join(d, f"{tag}_{sc}.json")
    try:
        return json.load(open(f))
    except Exception:
        return None


def g(r, *path):
    for k in path:
        r = (r or {}).get(k) if isinstance(r, dict) else None
    return r


def fmt(a, b):
    if a is None or b is None:
        return "-"
    return f"{a:.0f} -> **{b:.0f}** ({a / b:.1f}x)" if b else f"{a:.0f} -> 0"


rows = ["| scenario | whole run: WebKit model | at the pops | + decoded audio | 2D canvases MB (count) | WebGL buffers + textures | ImageBitmaps | pictures | layers | WebGL contexts |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
for sc, name in NAMES.items():
    B, A = load(TB, sc), load(TA, sc)
    if not B or not A:
        continue
    pb, pa = B["peak"], A["peak"]
    rows.append(f"| {name} | {fmt(pb['total'], pa['total'])} | "
                f"{fmt(g(B, 'peak_corkpop', 'total'), g(A, 'peak_corkpop', 'total')) if not sc.startswith('boot') else '-'} | "
                f"{fmt(pb['totalAudio'], pa['totalAudio'])} | "
                f"{pb['canvas2d']:.0f} ({pb['canvasN']}) -> {pa['canvas2d']:.0f} ({pa['canvasN']}) | "
                f"{pb['gl'] + pb['tex']:.0f} -> {pa['gl'] + pa['tex']:.0f} | {pb['bmp']:.0f} -> {pa['bmp']:.0f} | "
                f"{pb['pics']:.0f} -> {pa['pics']:.0f} | {pb['layers']:.0f} -> {pa['layers']:.0f} | {pb['glN']:.0f} -> {pa['glN']:.0f} |")
print("\n".join(rows))
print()
print("Heaviest sample of each run: canvas2d / gl / tex / bitmaps / pictures / layers / audio, and the top layers")
for sc in NAMES:
    for tag in (TB, TA):
        r = load(tag, sc)
        if r:
            p = r["peak_at"]
            print(f"  {tag:7s} {sc:12s} t={p['t']:5.1f} {p['tag']:8s} total {p['total']:6.1f}: cv {p['canvas2d']:5.1f} gl {p['gl']:4.1f} tex {p['tex']:5.1f} "
                  f"bmp {p['bmp']:4.1f} pics {p['pics']:5.1f} layers {p['layers']:5.1f} audio {p['audio']:5.1f}  top {p['topLayers'][:3]}  console {len(r.get('console', []))}")
