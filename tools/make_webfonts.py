"""The game's fonts as subset WOFF2 (2026-11-09).

The masters (TTF/OTF, as bought or downloaded) live in art/fonts/; the game ships only the WOFF2 made from
them, cut down to the characters the game can ever show:

  - Basic Latin and Latin-1 (every UI string, the rules and their social-mode wording are English: rules.js
    T() only swaps words, never the language), Latin Extended-A (the zloty's "zl" with its stroke, names),
    general punctuation (dashes, quotes, the ellipsis), every currency sign (rgs.js CURRENCY: $ EUR JPY RUB
    PHP INR KRW VND TRY ...), the minus and the multiplication sign;
  - and every other character any file in frontend/ contains, found afresh on each run, so a new string
    with a new character is covered the next time this runs.

Glyphs a master does not have stay missing (as before: the browser falls through to the next face in the
CSS stack, glyph by glyph). Outlines, hinting, kerning and every OpenType feature are kept unchanged, and
the whole name table (copyright, licence description and URL) rides along. Each master's licence file, if
it has one beside it (<stem>_OFL.txt, <stem>_LICENSE.txt), is copied next to the WOFF2.

usage: python tools/make_webfonts.py           build frontend/assets/<stem>.woff2 for every master
       python tools/make_webfonts.py --check   also decode each WOFF2 and compare every glyph with the master

Python: the project's (smukiez-slot/.venv: fontTools). WOFF2's Brotli step runs in Node's own zlib (Node is
needed anyway for the sfx tools), so nothing else has to be installed.
"""
import glob, io, json, os, re, shutil, subprocess, sys, types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTERS = os.path.join(ROOT, "art", "fonts")
OUT = os.path.join(ROOT, "frontend", "assets")
SCAN = os.path.join(ROOT, "frontend")

RANGES = [(0x20, 0x7E), (0xA0, 0x17F), (0x2010, 0x2027), (0x2030, 0x203A), (0x2044, 0x2044), (0x20A0, 0x20C0),
          (0x2116, 0x2116), (0x2122, 0x2122), (0x2190, 0x2195), (0x2212, 0x2212), (0x2215, 0x2215)]


# ---- Brotli through Node (fontTools' woff2 module imports `brotli`; this stands in for it)
_NODE = r"""
const zlib = require('zlib'); const c = zlib.constants; const chunks = [];
process.stdin.on('data', d => chunks.push(d)).on('end', () => {
  const buf = Buffer.concat(chunks), [op, mode, q] = process.argv.slice(1);
  const out = op === 'c'
    ? zlib.brotliCompressSync(buf, { params: { [c.BROTLI_PARAM_MODE]: +mode, [c.BROTLI_PARAM_QUALITY]: +q, [c.BROTLI_PARAM_SIZE_HINT]: buf.length } })
    : zlib.brotliDecompressSync(buf);
  process.stdout.write(out);
});
"""


def _node(args, data):
    r = subprocess.run(["node", "-e", _NODE, "--"] + args, input=data, capture_output=True)
    if r.returncode:
        raise RuntimeError("node brotli failed: " + r.stderr.decode(errors="replace"))
    return r.stdout


brotli = types.ModuleType("brotli")
brotli.MODE_GENERIC, brotli.MODE_TEXT, brotli.MODE_FONT = 0, 1, 2
brotli.compress = lambda data, mode=0, quality=11, lgwin=22, lgblock=0: _node(["c", str(mode), str(quality)], bytes(data))
brotli.decompress = lambda data: _node(["d", "0", "0"], bytes(data))
brotli.error = RuntimeError
sys.modules.setdefault("brotli", brotli)

from fontTools import subset                      # noqa: E402  (after the brotli stand-in)
from fontTools.ttLib import TTFont                # noqa: E402


def wanted():
    cps = set()
    for a, b in RANGES:
        cps.update(range(a, b + 1))
    for f in glob.glob(os.path.join(SCAN, "*.html")) + glob.glob(os.path.join(SCAN, "*.js")):
        txt = open(f, encoding="utf-8").read()
        cps.update(ord(ch) for ch in txt if ord(ch) > 0x7E and ch.isprintable())
        for m in re.finditer(r"&#x([0-9a-fA-F]+);|&#([0-9]+);", txt):   # numeric entities
            cps.add(int(m.group(1), 16) if m.group(1) else int(m.group(2)))
        for m in re.finditer(r"\\u([0-9a-fA-F]{4})|\\u\{([0-9a-fA-F]+)\}", txt):   # JS escapes
            v = int(m.group(1) or m.group(2), 16)
            if not 0xD800 <= v <= 0xDFFF:
                cps.add(v)
    return sorted(c for c in cps if c >= 0x20)


def build(master, cps):
    stem = os.path.splitext(os.path.basename(master))[0]
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["*"]          # every feature (kerning, ligatures, tabular figures, alternates)
    opts.name_IDs = ["*"]                 # the whole name table: copyright, licence text and URL
    opts.name_languages = ["*"]
    opts.name_legacy = True
    opts.notdef_outline = True
    opts.glyph_names = True
    opts.legacy_kern = True
    opts.hinting = True
    font = subset.load_font(master, opts)
    have = set(font.getBestCmap())
    sub = subset.Subsetter(opts)
    sub.populate(unicodes=cps)
    sub.subset(font)
    out = os.path.join(OUT, stem + ".woff2")
    subset.save_font(font, out, opts)
    kept = len(have & set(cps))
    for lic in glob.glob(os.path.join(MASTERS, stem + "_*.txt")):
        shutil.copyfile(lic, os.path.join(OUT, os.path.basename(lic)))
    return stem, os.path.getsize(master), os.path.getsize(out), len(have), kept


def check(master, cps):
    """Every character the subset keeps draws exactly as in the master: same advance, same outline."""
    stem = os.path.splitext(os.path.basename(master))[0]
    a, b = TTFont(master), TTFont(os.path.join(OUT, stem + ".woff2"))
    ca, cb = a.getBestCmap(), b.getBestCmap()
    keep = [c for c in cps if c in ca]
    missing = [c for c in keep if c not in cb]
    gsa, gsb = a.getGlyphSet(), b.getGlyphSet()
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    bad = []
    for c in keep:
        if c not in cb:
            continue
        ga, gb = ca[c], cb[c]
        pa, pb = DecomposingRecordingPen(gsa), DecomposingRecordingPen(gsb)
        gsa[ga].draw(pa); gsb[gb].draw(pb)
        if pa.value != pb.value or a["hmtx"][ga][0] != b["hmtx"][gb][0]:
            bad.append(c)
    return stem, len(keep), missing, bad


if __name__ == "__main__":
    cps = wanted()
    masters = sorted(glob.glob(os.path.join(MASTERS, "*.ttf")) + glob.glob(os.path.join(MASTERS, "*.otf")))
    if not masters:
        sys.exit("no masters in " + MASTERS)
    tot_a = tot_b = 0
    for m in masters:
        stem, sa, sb, n, kept = build(m, cps)
        tot_a += sa; tot_b += sb
        print(f"{stem:28s} {sa / 1024:7.1f} KB -> {sb / 1024:6.1f} KB woff2   ({kept} of the master's {n} characters kept)")
    print(f"{'total':28s} {tot_a / 1024:7.1f} KB -> {tot_b / 1024:6.1f} KB")
    if "--check" in sys.argv:
        ok = True
        for m in masters:
            stem, n, missing, bad = check(m, cps)
            ok &= not missing and not bad
            print(f"check {stem:22s} {n} characters: {'identical' if not missing and not bad else f'MISSING {missing[:10]} DIFFERENT {bad[:10]}'}")
        sys.exit(0 if ok else 1)
