"""Validate a math-sdk books file the way Stake's publisher does, and point at the bad line.

Stake reports failures as  books_<mode>.jsonl.zst:<line>:<column>  — column 0 means the
parser choked at the very START of a line, i.e. the line is blank or begins with a byte
that cannot open a JSON value. Python's own json module is more forgiving than the Go/Rust
parser they use (it accepts NaN and Infinity), so a file that loads fine in Python can
still be rejected on publish. This checks the strict rules.

    python tools/check_books.py <books_bonus.jsonl.zst> [--lut lookUpTable_bonus_0.csv]
    python tools/check_books.py <books_bonus.jsonl.zst> --fix    # drop blank lines, rewrite

Reports, per file: line count, blank lines, strict-JSON failures (with the line number and
the reason), non-UTF-8 lines, NaN/Infinity, duplicate or non-monotonic book ids, and — when
a lookup table is given — ids the table references that the book file does not contain.
"""
import argparse
import io
import json
import os
import sys

import zstandard as zstd


def reader(path):
    """Yield (line_number, raw_bytes_without_newline) for a .jsonl or .jsonl.zst file."""
    if path.endswith(".zst"):
        with open(path, "rb") as fh:
            stream = zstd.ZstdDecompressor().stream_reader(fh, read_across_frames=True)
            buf = b""
            n = 0
            while True:
                chunk = stream.read(1 << 22)
                if not chunk:
                    break
                buf += chunk
                while True:
                    nl = buf.find(b"\n")
                    if nl < 0:
                        break
                    n += 1
                    yield n, buf[:nl]
                    buf = buf[nl + 1:]
            if buf:
                yield n + 1, buf          # trailing line with no newline = truncated
    else:
        with io.open(path, "rb") as fh:
            for n, line in enumerate(fh, 1):
                yield n, line.rstrip(b"\n")


def strict_loads(text):
    """json.loads that rejects NaN/Infinity, exactly as a Go or Rust parser would."""
    def reject(c):
        raise ValueError(f"JSON does not allow the literal {c}")
    return json.loads(text, parse_constant=reject)


def check(path, lut=None, fix=False):
    blanks, bad, non_utf8, ids = [], [], [], []
    total = 0
    last_had_newline = True
    keep = []

    for n, raw in reader(path):
        total = n
        if not raw.strip():
            blanks.append(n)
            continue                       # never keep a blank line
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as e:
            non_utf8.append((n, str(e)[:70]))
            continue
        try:
            obj = strict_loads(text)
            if isinstance(obj, dict) and "id" in obj:
                ids.append(obj["id"])
        except Exception as e:                      # noqa: BLE001 - report every reason
            bad.append((n, str(e)[:90], text[:70]))
        if fix:
            keep.append(raw)

    print(f"{os.path.basename(path)}")
    print(f"  lines                {total:,}")
    print(f"  blank lines          {len(blanks)}" + (f"  -> {blanks[:8]}" if blanks else ""))
    print(f"  non-UTF-8 lines      {len(non_utf8)}" + (f"  -> {non_utf8[:3]}" if non_utf8 else ""))
    print(f"  strict-JSON failures {len(bad)}")
    for n, why, head in bad[:5]:
        print(f"    line {n}: {why}\n      starts: {head!r}")

    if ids:
        dupes = len(ids) - len(set(ids))
        gaps = [i for i in range(1, len(ids)) if ids[i] != ids[i - 1] + 1]
        print(f"  book ids             {min(ids)}..{max(ids)}  duplicates={dupes}  "
              f"non-consecutive at {len(gaps)} point(s)" + (f" e.g. line {gaps[0] + 1}" if gaps else ""))

    if lut:
        want = set()
        with io.open(lut, encoding="utf-8") as fh:
            for line in fh:
                parts = line.strip().split(",")
                if parts and parts[0].isdigit():
                    want.add(int(parts[0]))
        missing = want - set(ids)
        print(f"  lookup table         {len(want):,} ids referenced, {len(missing)} missing from the books"
              + (f" e.g. {sorted(missing)[:5]}" if missing else ""))

    problems = len(blanks) + len(bad) + len(non_utf8)
    if fix and problems:
        out = path.replace(".jsonl", ".fixed.jsonl")
        if bad or non_utf8:
            print("\n  NOT rewriting: --fix only removes blank lines, and this file has lines that "
                  "are genuinely malformed. Those books have to be regenerated.")
        else:
            data = b"\n".join(keep) + b"\n"
            if out.endswith(".zst"):
                with open(out, "wb") as fh:
                    fh.write(zstd.ZstdCompressor().compress(data))
            else:
                with open(out, "wb") as fh:
                    fh.write(data)
            print(f"\n  wrote {out} ({len(keep):,} lines, {len(blanks)} blank line(s) removed)")
            print("  publish that file in place of the original — book ids are unchanged, so the "
                  "lookup tables still line up.")

    print("\n  " + ("OK - this file will publish." if not problems else
                    f"{problems} problem line(s). Stake stops at the first one."))
    return 1 if problems else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("books", nargs="+", help="books_<mode>.jsonl[.zst]")
    ap.add_argument("--lut", help="matching lookUpTable_<mode>_0.csv")
    ap.add_argument("--fix", action="store_true", help="rewrite without blank lines")
    a = ap.parse_args()
    sys.exit(max(check(b, a.lut, a.fix) for b in a.books))
