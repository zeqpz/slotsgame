"""Finish the optimiser's lookup tables before they are published: two corrections that leave
every payout's probability where the optimiser put it (exactly, or to within 10^-12).

1. A 1000x wall is a rare sight and never one board on repeat. The sims decide which books
   show one (booster_mults_base); the table decides how often each is drawn, and that swings
   how often a 1000x shows at all. While the optimiser weighted payouts, a teaser in one of the
   ~280 books paying exactly 0.5x or 0.6x was the same board every ~1,100 spins (one run: a
   1000x 1 in 417 rounds where the rest of the pool gave ~1 in 1,600); now that the base game's
   small wins are weighted per book (game_optimization.base_book_scaling), the teasers among the
   22,000 books paying 0.8x bring it to about 1 in 1,100 where the owner asked for about 1 in
   1,500. So no book showing a base-game wall of --rare-wall x or more may weigh more than an
   ordinary losing round's book, and together they may come at most once in --rare-wall-rate
   rounds: the cap comes down until they fit. The excess goes to the other books with the same
   payout, so each payout's total weight - and with it the RTP, the hit rate and every
   volatility statistic - is exactly unchanged. A payout that only rare-wall books reach is
   left alone. Base mode only.
2. The RTP is never a rounding error over its ceiling. Integer weights can land a mode a hair
   over 0.967 (the extreme buy came out 3.5e-13 above), and the SDK's 3-star volatility check
   (math-sdk/utils/rgs_verification.py) is a strict rtp > 0.967 - computed in float64 with
   numpy.dot over products near 1e17, good to about 1e-13, so exactly 0.967 can still read as
   over. The lowest-paying book gets the weight it takes to bring the exact RTP 1e-10 under the
   ceiling (MARGIN), well clear of that error and far below anything a statistic shows.

Run it after every optimisation (the optimiser rewrites the tables); a second run changes
nothing. The books are not touched, so the RGS verification sidecars stay valid.

    python tools/finish_luts.py <publish_files dir> [--rare-wall 1000] [--rare-wall-rate 1500]
                                [--rtp-ceiling 0.967] [--dry-run]
"""
import argparse
import io
import json
import os
from fractions import Fraction

import zstandard

MARGIN = Fraction(1, 10**10)   # how far under the ceiling the exact RTP is brought (see 2.)


def read_lut(path):
    text = open(path, encoding="utf-8", newline="").read()
    rows = [[int(x) for x in line.split(",")] for line in text.splitlines() if line.strip()]
    return rows, text.endswith("\n")


def write_lut(path, rows, trailing):
    body = "\n".join(f"{i},{w},{p}" for i, w, p in rows)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(body + ("\n" if trailing else ""))


def rare_wall_books(books_path, value):
    """Ids of the books where a wall worth `value` or more lands in the base game."""
    ids = set()
    with open(books_path, "rb") as fh:
        for line in io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(fh), encoding="utf-8"):
            if not line.strip():
                continue
            book = json.loads(line)
            gametype = "basegame"
            for ev in book["events"]:
                if ev.get("type") == "reveal":
                    gametype = ev.get("gameType", gametype)
                elif (gametype == "basegame" and ev.get("type") == "booster"
                      and any(b["mult"] >= value for b in ev["boosters"])):
                    ids.add(book["id"])
                    break
    return ids


def cap_rare(rows, rare, one_in=None):
    """Correction 1, in place. Returns (books capped, rare-wall weight before, after)."""
    zero = sorted(w for _, w, p in rows if p == 0)
    if not zero:
        return 0, 0, 0
    cap = zero[len(zero) // 2]   # an ordinary losing round's book
    before = sum(w for i, w, _ in rows if i in rare)
    groups = {}
    for r in rows:
        groups.setdefault(r[2], []).append(r)
    if one_in:
        # the rare-wall books whose payout has other books to take their excess
        movable = [r for g in groups.values() if any(x[0] not in rare for x in g) for r in g if r[0] in rare]
        allowed = sum(w for _, w, _ in rows) // one_in - (before - sum(r[1] for r in movable))
        if sum(min(r[1], cap) for r in movable) > allowed:
            lo, hi = 1, cap   # the largest cap that keeps them together within `allowed`
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if sum(min(r[1], mid) for r in movable) <= allowed:
                    lo = mid
                else:
                    hi = mid - 1
            cap = lo
    capped = 0
    for payout, group in groups.items():
        heavy = [r for r in group if r[0] in rare and r[1] > cap]
        others = [r for r in group if r[0] not in rare]
        if not heavy or not others:
            continue
        excess = sum(r[1] - cap for r in heavy)
        for r in heavy:
            r[1] = cap
        base = sum(r[1] for r in others)
        given = 0
        for r in others:
            share = excess * r[1] // base
            r[1] += share
            given += share
        max(others, key=lambda r: r[1])[1] += excess - given   # the rounding remainder: the payout's total is exact
        capped += len(heavy)
    after = sum(w for i, w, _ in rows if i in rare)
    return capped, before, after


def rtp(rows, cost):
    return Fraction(sum(w * p for _, w, p in rows), sum(w for _, w, _ in rows) * 100 * cost)


def trim_rtp(rows, cost, ceiling):
    """Correction 2, in place. Returns the weight added (0 when the RTP is already under)."""
    n, d = ceiling.numerator, ceiling.denominator
    excess = sum(w * p for _, w, p in rows) * d - n * 100 * cost * sum(w for _, w, _ in rows)
    if excess <= 0:
        return 0
    low = min(rows, key=lambda r: r[2])
    k = n * 100 * cost - low[2] * d   # how much each unit of weight on the lowest payout pulls the RTP down
    add = -(-excess // k)
    low[1] += add
    return add


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("publish_dir")
    ap.add_argument("--rare-wall", type=float, default=1000.0)
    ap.add_argument("--rare-wall-rate", type=int, default=1500, help="such rounds at most once in this many")
    ap.add_argument("--rtp-ceiling", default="0.967")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    index = json.load(open(os.path.join(args.publish_dir, "index.json")))
    ceiling = Fraction(args.rtp_ceiling) - MARGIN
    for mode in index["modes"]:
        name, cost = mode["name"], Fraction(mode["cost"]).limit_denominator()
        path = os.path.join(args.publish_dir, mode["weights"])
        rows, trailing = read_lut(path)
        total = sum(w for _, w, _ in rows)
        payouts = {}
        for _, w, p in rows:
            payouts[p] = payouts.get(p, 0) + w
        r0 = rtp(rows, cost)
        changed = False
        if name == "base":
            rare = rare_wall_books(os.path.join(args.publish_dir, mode["events"]), args.rare_wall)
            capped, before, after = cap_rare(rows, rare, args.rare_wall_rate)
            heaviest = max((w for i, w, _ in rows if i in rare), default=0)
            print(f"{name}: {len(rare)} books show a base-game wall of {args.rare_wall:g}x+; "
                  f"{capped} capped; such a round comes 1 in {total / max(before, 1):,.0f} -> 1 in {total / max(after, 1):,.0f}"
                  + (f", the most-drawn such board 1 in {total / heaviest:,.0f}" if heaviest else ""))
            changed |= capped > 0
        added = trim_rtp(rows, cost, ceiling)
        changed |= added > 0
        # each payout's share of the table must be where the optimiser left it
        after_payouts = {}
        for _, w, p in rows:
            after_payouts[p] = after_payouts.get(p, 0) + w
        drift = max(abs(Fraction(after_payouts[p], total + added) - Fraction(payouts[p], total)) for p in payouts)
        r1 = rtp(rows, cost)
        print(f"{name}: rtp {float(r0):.12f} -> {float(r1):.12f}"
              f"{f' (+{added} weight on the lowest payout)' if added else ''}; largest payout-share drift {float(drift):.1e}")
        if changed and not args.dry_run:
            write_lut(path, rows, trailing)
            print(f"  wrote {mode['weights']}")


if __name__ == "__main__":
    main()
