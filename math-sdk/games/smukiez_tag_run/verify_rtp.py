"""Compute the weighted RTP of each mode's optimized lookup table (the live-game odds)."""

import os

MODES = {"base": 1.0, "bonus": 100.0, "extremebonus": 400.0}
LUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "library", "publish_files")

for mode, cost in MODES.items():
    path = os.path.join(LUT_DIR, f"lookUpTable_{mode}_0.csv")
    if not os.path.exists(path):
        print(f"{mode}: missing {path}")
        continue
    total_w = total_wp = 0
    zero_w = 0
    max_pay = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            _, w, p = line.strip().split(",")
            w, p = int(w), int(p)
            total_w += w
            total_wp += w * p
            max_pay = max(max_pay, p)
            if p == 0:
                zero_w += w
    rtp = total_wp / total_w / 100 / cost
    hit_rate = 1 / (1 - zero_w / total_w) if zero_w < total_w else float("inf")
    print(
        f"{mode:<13} rtp={rtp:.5f}  cost={cost:g}x  hitRate=1-in-{hit_rate:.2f}  "
        f"maxPay={max_pay/100:g}x  weightSum={total_w}"
    )
