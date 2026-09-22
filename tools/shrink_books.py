"""Re-encode books so no single book exceeds Stake's 512 KiB publish limit.

Stake rejects any book (one line of books_<mode>.jsonl.zst) over 524,288 bytes. In this game
winInfo events are most of a large book: a long tumble chain produces thousands of line-win
entries, each spelled out in full:

    {"symbol": "L10", "kind": 3, "win": 60,
     "positions": [{"reel": 0, "row": 1}, {"reel": 1, "row": 2}, {"reel": 2, "row": 1}],
     "meta": {"lineIndex": 5, "multiplier": 6.2, "winWithoutMult": 10, "globalMult": 1,
              "lineMultiplier": 1, "cellMults": [1.2, 5, 0]}}               ~230 bytes

Only six of those values are ever read by the client, so a win becomes a flat tuple:

    ["L10", 3, 60, [[0,1],[1,2],[2,1]], 5, 6.2]                              ~40 bytes
     symbol kind win positions          line mult

Nothing is dropped that the game uses: winWithoutMult, globalMult and lineMultiplier are
derivable and no consumer reads them, and cellMults is already on the client from the
booster event's grid. The client accepts both shapes - an array is the compact form, an
object the legacy one - so old and new books both play.

This changes ENCODING ONLY. Book ids, their order, payoutMultiplier, the event list and every
win value are preserved exactly, so the lookup tables and the optimised RTP stay valid.

    python tools/shrink_books.py <books.jsonl.zst> [...]           # rewrite in place (.orig kept)
    python tools/shrink_books.py <books.jsonl.zst> --dry-run       # measure, change nothing
    python tools/shrink_books.py <books.jsonl.zst> --check         # verify a rewrite
"""
import argparse
import json
import os
import shutil
import sys

import zstandard as zstd

LIMIT = 524288          # 512 KiB - the publisher's per-book ceiling


def lines(path):
    """Yield each book as raw bytes, without the trailing newline."""
    with open(path, "rb") as fh:
        r = zstd.ZstdDecompressor().stream_reader(fh, read_across_frames=True)
        buf = b""
        while True:
            chunk = r.read(1 << 22)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                yield line
        if buf.strip():
            yield buf


def compact_win(w):
    """One win entry -> flat tuple. Already-compact entries pass straight through."""
    if isinstance(w, list):
        return w
    m = w.get("meta") or {}
    return [
        w.get("symbol"),
        w.get("kind"),
        w.get("win"),
        [[p["reel"], p["row"]] for p in w.get("positions", [])],
        m.get("lineIndex"),
        m.get("multiplier"),
    ]


def compact_book(book):
    for e in book.get("events", []):
        if e.get("type") == "winInfo" and isinstance(e.get("wins"), list):
            e["wins"] = [compact_win(w) for w in e["wins"]]
    return book


def payout_key(book):
    """The invariant that must survive: which book, and what it pays."""
    return (book.get("id"), book.get("payoutMultiplier"))


def process(path, dry_run=False):
    out = path + ".tmp"
    before_max = after_max = 0
    before_total = after_total = 0
    n = over_before = over_after = 0
    keys_before, keys_after = [], []

    writer_ctx = None
    if not dry_run:
        fo = open(out, "wb")
        writer_ctx = zstd.ZstdCompressor().stream_writer(fo, closefd=False)

    for raw in lines(path):
        if not raw.strip():
            continue
        n += 1
        book = json.loads(raw)
        keys_before.append(payout_key(book))
        before_total += len(raw)
        before_max = max(before_max, len(raw))
        over_before += len(raw) > LIMIT

        enc = json.dumps(compact_book(book)).encode("utf-8")
        keys_after.append(payout_key(json.loads(enc)))
        after_total += len(enc)
        after_max = max(after_max, len(enc))
        over_after += len(enc) > LIMIT

        if writer_ctx is not None:
            writer_ctx.write(enc + b"\n")

    if writer_ctx is not None:
        writer_ctx.close()
        fo.close()

    assert keys_before == keys_after, "payout invariant broken - ids or payoutMultipliers changed"

    name = os.path.basename(path)
    print(f"{name}")
    print(f"  books                {n:,}   (id/payoutMultiplier sequence preserved)")
    print(f"  largest book         {before_max:,} -> {after_max:,} bytes"
          f"   ({after_max / before_max * 100:.0f}% of before)")
    print(f"  over 512 KiB         {over_before} -> {over_after}")
    print(f"  uncompressed total   {before_total:,} -> {after_total:,} bytes"
          f"   ({after_total / before_total * 100:.0f}%)")

    if dry_run:
        return 0 if over_after == 0 else 1

    orig = path + ".orig"
    if not os.path.exists(orig):
        shutil.copy2(path, orig)
    os.replace(out, path)
    print(f"  written              {os.path.getsize(path):,} bytes compressed"
          f"   (original kept at {os.path.basename(orig)})")
    return 0 if over_after == 0 else 1


def check(path):
    """Confirm a rewritten file still matches its .orig on every value that matters."""
    orig = path + ".orig"
    if not os.path.exists(orig):
        print(f"{os.path.basename(path)}: no .orig to compare against")
        return 1
    bad = 0
    for a, b in zip(lines(orig), lines(path)):
        ba, bb = json.loads(a), json.loads(b)
        if payout_key(ba) != payout_key(bb):
            print(f"  id/payout mismatch at book {ba.get('id')}")
            bad += 1
            continue
        ea, eb = ba.get("events", []), bb.get("events", [])
        if len(ea) != len(eb) or [e["type"] for e in ea] != [e["type"] for e in eb]:
            print(f"  event stream changed in book {ba.get('id')}")
            bad += 1
            continue
        for x, y in zip(ea, eb):
            if x.get("type") != "winInfo":
                continue
            if [compact_win(w) for w in x.get("wins", [])] != list(y.get("wins", [])):
                print(f"  win values changed in book {ba.get('id')}")
                bad += 1
                break
        if bad > 5:
            break
    print(f"{os.path.basename(path)}: {'OK - ids, payouts, event order and win values all match' if not bad else str(bad) + ' mismatches'}")
    return 1 if bad else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("books", nargs="+")
    ap.add_argument("--dry-run", action="store_true", help="measure only")
    ap.add_argument("--check", action="store_true", help="verify a rewritten file against its .orig")
    a = ap.parse_args()
    rc = 0
    for p in a.books:
        rc |= check(p) if a.check else process(p, a.dry_run)
    sys.exit(rc)
