# Smukiez native port vs v5 - parity tables

Generated 2026-11-03T01:24:38.356Z by tools/compare.ts.

## Optimised statistics (weighted by the published lookup tables)

### base

| statistic | v5 (published) | native (default, v5 shape) | native (tilt only) |
|---|---|---|---|
| RTP | 0.967000 | 0.967000 | 0.967000 |
| hit rate (non-zero) | 1 in 2.473 | 1 in 2.473 | 1 in 2.473 |
| P(win < cost) | 92.00% | 92.00% | 93.75% |
| volatility (std, x bet) | 10.9 | 11.52 | 20.19 |
| max win (10,000x) frequency | 1 in 5,000,000 | 1 in 5,000,000 | 1 in 5,000,000 |
| free-spin trigger frequency | 1 in 233 | 1 in 233 | 1 in 233 |
|   standard / direct / upgrade | 1 in 257.7 / 1 in 7,566 / 1 in 3,572 | 1 in 268.2 / 1 in 7,480 / 1 in 2,326 | 1 in 263.3 / 1 in 7,410 / 1 in 2,783 |
| average bonus win (freeSpinEnd) | 90x | 90.16x | 90.16x |
| average payout of a bonus round | 90.64x | 90.61x | 90.61x |
| RTP from free spins / base | 0.3863 / 0.5807 | 0.3870 / 0.5800 | 0.3869 / 0.5801 |
| full-wall cover frequency | 1 in 80,000 | 1 in 79,939 | 1 in 79,939 |
| base 1000x-wall rounds | 1 in 1,500 | 1 in 1,500 | 1 in 1,500 |
| base wall-line rounds | 1 in 41.58 | 1 in 40.92 | 1 in 41.52 |

### bonus

| statistic | v5 (published) | native (default, v5 shape) | native (tilt only) |
|---|---|---|---|
| RTP | 0.967000 | 0.967000 | 0.967000 |
| hit rate (non-zero) | 1 in 1.000 | 1 in 1.000 | 1 in 1.000 |
| P(win < cost) | 69.36% | 69.43% | 74.33% |
| volatility (std, x bet) | 136.3 | 137.3 | 222.1 |
| max win (10,000x) frequency | 1 in 25,000 | 1 in 25,000 | 1 in 25,000 |
| free-spin trigger frequency | 1 in 1 | 1 in 1 | 1 in 1 |
|   standard / direct / upgrade | 1 in 1 / - / - | 1 in 1 / - / - | 1 in 1 / - / - |
| average bonus win (freeSpinEnd) | 96.32x | 96.27x | 96.26x |
| average payout of a bonus round | 96.7x | 96.7x | 96.7x |
| RTP from free spins / base | 0.9632 / 0.0038 | 0.9627 / 0.0043 | 0.9626 / 0.0044 |
| full-wall cover frequency | - | - | - |
| base 1000x-wall rounds | 1 in 1,608 | 1 in 1,983 | 1 in 1,420 |
| base wall-line rounds | 1 in 38.54 | 1 in 42.55 | 1 in 43.13 |

### extremebonus

| statistic | v5 (published) | native (default, v5 shape) | native (tilt only) |
|---|---|---|---|
| RTP | 0.967000 | 0.967000 | 0.967000 |
| hit rate (non-zero) | 1 in 1.000 | 1 in 1.000 | 1 in 1.000 |
| P(win < cost) | 67.39% | 67.62% | 71.83% |
| volatility (std, x bet) | 440.9 | 445.6 | 627.2 |
| max win (10,000x) frequency | 1 in 13,889 | 1 in 13,889 | 1 in 13,889 |
| free-spin trigger frequency | 1 in 1 | 1 in 1 | 1 in 1 |
|   standard / direct / upgrade | - / 1 in 1.496 / 1 in 3.015 | - / 1 in 1.524 / 1 in 2.908 | - / 1 in 1.547 / 1 in 2.827 |
| average bonus win (freeSpinEnd) | 386.2x | 386.3x | 386.3x |
| average payout of a bonus round | 386.8x | 386.8x | 386.8x |
| RTP from free spins / base | 0.9656 / 0.0014 | 0.9658 / 0.0012 | 0.9657 / 0.0013 |
| full-wall cover frequency | - | - | - |
| base 1000x-wall rounds | 1 in 1,058 | 1 in 2,976 | 1 in 2,239 |
| base wall-line rounds | 1 in 40.99 | 1 in 39.91 | 1 in 40.9 |

## Raw simulated pools per criteria (unweighted: the math itself, before any optimiser)

| mode | criteria | books v5 / native | mean payout v5 / native | z (diff / SE) | std v5 / native | max | 10,000x books |
|---|---|---|---|---|---|---|---|
| base | 0 | 35000 / 35000 | 0 / 0 | - | 0 / 0 | 0 / 0 | 0 / 0 |
| base | basegame | 55780 / 55779 | 2.938 / 2.707 | -1.30 | 36.31 / 21.08 | 6,424 / 3,210 | 0 / 0 |
| base | freegame | 7000 / 7001 | 95.01 / 94.67 | -0.09 | 232.7 / 222.6 | 7,277 / 6,667 | 0 / 0 |
| base | extremegame | 2000 / 2000 | 384.4 / 357.5 | -1.31 | 670.4 / 625.1 | 10,000 / 9,078 | 2 / 0 |
| base | wallcover | 200 / 200 | 763.5 / 902.9 | 1.20 | 999.1 / 1,300 | 9,120 / 10,000 | 0 / 1 |
| base | wincap | 20 / 20 | 10,000 / 10,000 | - | 0 / 0 | 10,000 / 10,000 | 20 / 20 |
| bonus | freegame | 19990 / 19990 | 99.88 / 101.5 | 0.70 | 243.1 / 234.7 | 10,000 / 10,000 | 1 / 1 |
| bonus | wincap | 10 / 10 | 10,000 / 10,000 | - | 0 / 0 | 10,000 / 10,000 | 10 / 10 |
| extremebonus | extremegame | 19980 / 19980 | 350.4 / 352.2 | 0.30 | 603.8 / 605.7 | 10,000 / 10,000 | 9 / 10 |
| extremebonus | wincap | 20 / 20 | 10,000 / 10,000 | - | 0 / 0 | 10,000 / 10,000 | 20 / 20 |

## Mechanic distributions (unweighted, per criteria / game type)

| mode criteria/gametype | measure | v5 | native |
|---|---|---|---|
| base basegame/basegame | reveals | 55780 | 55779 |
| base basegame/basegame | Multis per board | 1.539 | 1.544 |
| base basegame/basegame | mean Multi value (blow-outs) | 2.65 | 2.55 |
| base basegame/basegame | Multi 1000x share | 0.1% | 0.1% |
| base basegame/basegame | wall line per reveal | 0.0281 | 0.0270 |
| base basegame/basegame | wall line 3 / 4 | 71.3% / 28.7% | 68.4% / 31.6% |
| base basegame/basegame | line drop 1.25/1.5/2 | 60.4% / 24.8% / 14.8% | 60.2% / 24.8% / 15.0% |
| base basegame/basegame | tumbles per spin | 1.636 | 1.642 |
| base basegame/basegame | spins with a win | 100.00% | 100.00% |
| base basegame/basegame | 5-clusters share | 64.4% | 64.3% |
| base freegame/basegame | reveals | 7000 | 7001 |
| base freegame/basegame | Multis per board | 1.588 | 1.616 |
| base freegame/basegame | mean Multi value (blow-outs) | 2.43 | 2.70 |
| base freegame/basegame | Multi 1000x share | 0.1% | 0.1% |
| base freegame/basegame | wall line per reveal | 0.0271 | 0.0263 |
| base freegame/basegame | wall line 3 / 4 | 73.7% / 26.3% | 73.4% / 26.6% |
| base freegame/basegame | line drop 1.25/1.5/2 | 59.0% / 25.9% / 15.0% | 60.3% / 25.6% / 14.1% |
| base freegame/basegame | tumbles per spin | 1.111 | 1.119 |
| base freegame/basegame | spins with a win | 18.17% | 17.95% |
| base freegame/basegame | 5-clusters share | 67.5% | 69.8% |
| base freegame/freegame | reveals | 75012 | 74867 |
| base freegame/freegame | Multis per board | 2.007 | 2.003 |
| base freegame/freegame | mean Multi value (blow-outs) | 3.43 | 3.45 |
| base freegame/freegame | Multi 1000x share | 0.0% | 0.0% |
| base freegame/freegame | wall line per reveal | 0.1673 | 0.1668 |
| base freegame/freegame | wall line 3 / 4 | 69.8% / 30.2% | 70.2% / 29.8% |
| base freegame/freegame | line drop 1.25/1.5/2 | 60.3% / 24.9% / 14.8% | 60.3% / 24.9% / 14.8% |
| base freegame/freegame | tumbles per spin | 1.169 | 1.163 |
| base freegame/freegame | spins with a win | 25.23% | 25.02% |
| base freegame/freegame | 5-clusters share | 67.7% | 67.5% |
| base 0/basegame | reveals | 35000 | 35000 |
| base 0/basegame | Multis per board | 1.544 | 1.546 |
| base 0/basegame | mean Multi value (blow-outs) | 2.53 | 2.59 |
| base 0/basegame | Multi 1000x share | 0.1% | 0.1% |
| base 0/basegame | wall line per reveal | 0.0232 | 0.0243 |
| base 0/basegame | wall line 3 / 4 | 69.2% / 30.8% | 72.1% / 27.9% |
| base 0/basegame | line drop 1.25/1.5/2 | - / - / - | - / - / - |
| base 0/basegame | tumbles per spin | 0.981 | 0.983 |
| base 0/basegame | spins with a win | 0.00% | 0.00% |
| base 0/basegame | 5-clusters share | - | - |
| base extremegame/basegame | reveals | 2000 | 2000 |
| base extremegame/basegame | Multis per board | 1.275 | 1.258 |
| base extremegame/basegame | mean Multi value (blow-outs) | 1.82 | 2.75 |
| base extremegame/basegame | Multi 1000x share | 0.0% | 0.1% |
| base extremegame/basegame | wall line per reveal | 0.0310 | 0.0245 |
| base extremegame/basegame | wall line 3 / 4 | 69.4% / 30.6% | 59.2% / 40.8% |
| base extremegame/basegame | line drop 1.25/1.5/2 | 58.6% / 24.0% / 17.4% | 57.1% / 27.9% / 15.0% |
| base extremegame/basegame | tumbles per spin | 0.953 | 0.963 |
| base extremegame/basegame | spins with a win | 21.05% | 21.15% |
| base extremegame/basegame | 5-clusters share | 67.5% | 65.6% |
| base extremegame/freegame | reveals | 29066 | 29364 |
| base extremegame/freegame | Multis per board | 2.011 | 2.012 |
| base extremegame/freegame | mean Multi value (blow-outs) | 5.80 | 5.73 |
| base extremegame/freegame | Multi 1000x share | 0.0% | 0.0% |
| base extremegame/freegame | wall line per reveal | 0.1681 | 0.1645 |
| base extremegame/freegame | wall line 3 / 4 | 69.3% / 30.7% | 71.4% / 28.6% |
| base extremegame/freegame | line drop 1.25/1.5/2 | 59.7% / 24.9% / 15.4% | 59.3% / 25.0% / 15.8% |
| base extremegame/freegame | tumbles per spin | 1.172 | 1.168 |
| base extremegame/freegame | spins with a win | 26.58% | 26.20% |
| base extremegame/freegame | 5-clusters share | 65.9% | 65.3% |
| base wallcover/basegame | reveals | 200 | 200 |
| base wallcover/basegame | Multis per board | 48.670 | 48.630 |
| base wallcover/basegame | mean Multi value (blow-outs) | 17.83 | 18.03 |
| base wallcover/basegame | Multi 1000x share | 0.0% | 0.0% |
| base wallcover/basegame | wall line per reveal | 0.0000 | 0.0000 |
| base wallcover/basegame | wall line 3 / 4 | - / - | - / - |
| base wallcover/basegame | line drop 1.25/1.5/2 | 59.1% / 22.4% / 18.6% | 59.4% / 22.8% / 17.9% |
| base wallcover/basegame | tumbles per spin | 2.580 | 2.530 |
| base wallcover/basegame | spins with a win | 100.00% | 100.00% |
| base wallcover/basegame | 5-clusters share | 69.6% | 65.0% |
| base wincap/freegame | reveals | 103 | 102 |
| base wincap/freegame | Multis per board | 7.583 | 8.078 |
| base wincap/freegame | mean Multi value (blow-outs) | 1000.00 | 1000.00 |
| base wincap/freegame | Multi 1000x share | 100.0% | 100.0% |
| base wincap/freegame | wall line per reveal | 0.1553 | 0.1765 |
| base wincap/freegame | wall line 3 / 4 | 68.8% / 31.3% | 61.1% / 38.9% |
| base wincap/freegame | line drop 1.25/1.5/2 | 33.3% / 33.3% / 33.3% | 50.0% / 50.0% / 0.0% |
| base wincap/freegame | tumbles per spin | 3.592 | 3.745 |
| base wincap/freegame | spins with a win | 21.36% | 21.57% |
| base wincap/freegame | 5-clusters share | 62.5% | 72.7% |
| bonus freegame/basegame | reveals | 19990 | 19990 |
| bonus freegame/basegame | Multis per board | 1.587 | 1.592 |
| bonus freegame/basegame | mean Multi value (blow-outs) | 2.48 | 2.34 |
| bonus freegame/basegame | Multi 1000x share | 0.0% | 0.0% |
| bonus freegame/basegame | wall line per reveal | 0.0258 | 0.0233 |
| bonus freegame/basegame | wall line 3 / 4 | 70.5% / 29.5% | 69.5% / 30.5% |
| bonus freegame/basegame | line drop 1.25/1.5/2 | 59.6% / 24.5% / 15.9% | 59.3% / 25.8% / 14.9% |
| bonus freegame/basegame | tumbles per spin | 1.107 | 1.104 |
| bonus freegame/basegame | spins with a win | 17.14% | 16.92% |
| bonus freegame/basegame | 5-clusters share | 68.8% | 67.2% |
| bonus freegame/freegame | reveals | 220668 | 220434 |
| bonus freegame/freegame | Multis per board | 2.011 | 2.006 |
| bonus freegame/freegame | mean Multi value (blow-outs) | 3.42 | 3.40 |
| bonus freegame/freegame | Multi 1000x share | 0.0% | 0.0% |
| bonus freegame/freegame | wall line per reveal | 0.1678 | 0.1662 |
| bonus freegame/freegame | wall line 3 / 4 | 69.9% / 30.1% | 69.3% / 30.7% |
| bonus freegame/freegame | line drop 1.25/1.5/2 | 60.0% / 24.9% / 15.1% | 59.8% / 25.1% / 15.1% |
| bonus freegame/freegame | tumbles per spin | 1.165 | 1.166 |
| bonus freegame/freegame | spins with a win | 25.00% | 25.15% |
| bonus freegame/freegame | 5-clusters share | 67.9% | 67.9% |
| extremebonus extremegame/basegame | reveals | 19980 | 19980 |
| extremebonus extremegame/basegame | Multis per board | 1.266 | 1.253 |
| extremebonus extremegame/basegame | mean Multi value (blow-outs) | 2.48 | 2.27 |
| extremebonus extremegame/basegame | Multi 1000x share | 0.1% | 0.0% |
| extremebonus extremegame/basegame | wall line per reveal | 0.0257 | 0.0244 |
| extremebonus extremegame/basegame | wall line 3 / 4 | 72.2% / 27.8% | 69.9% / 30.1% |
| extremebonus extremegame/basegame | line drop 1.25/1.5/2 | 59.9% / 25.0% / 15.1% | 59.6% / 25.6% / 14.8% |
| extremebonus extremegame/basegame | tumbles per spin | 0.950 | 0.945 |
| extremebonus extremegame/basegame | spins with a win | 20.19% | 19.90% |
| extremebonus extremegame/basegame | 5-clusters share | 67.4% | 66.3% |
| extremebonus extremegame/freegame | reveals | 291319 | 292027 |
| extremebonus extremegame/freegame | Multis per board | 2.004 | 2.001 |
| extremebonus extremegame/freegame | mean Multi value (blow-outs) | 5.67 | 5.69 |
| extremebonus extremegame/freegame | Multi 1000x share | 0.0% | 0.0% |
| extremebonus extremegame/freegame | wall line per reveal | 0.1672 | 0.1663 |
| extremebonus extremegame/freegame | wall line 3 / 4 | 69.9% / 30.1% | 70.1% / 29.9% |
| extremebonus extremegame/freegame | line drop 1.25/1.5/2 | 60.0% / 24.9% / 15.1% | 59.9% / 25.1% / 15.0% |
| extremebonus extremegame/freegame | tumbles per spin | 1.170 | 1.170 |
| extremebonus extremegame/freegame | spins with a win | 26.26% | 26.04% |
| extremebonus extremegame/freegame | 5-clusters share | 66.3% | 65.9% |

## Triggers (unweighted counts in the pools: reason | spins | Crew Leaders | Phantoms)

| base trigger | v5 | native |
|---|---|---|
| extreme_direct|fs17|bs0|es2 | 686 | 698 |
| extreme_direct|fs17|bs0|es3 | 14 | 11 |
| extreme_direct|fs17|bs1|es2 | 337 | 328 |
| extreme_direct|fs17|bs1|es3 | 7 | 7 |
| extreme_direct|fs17|bs2|es2 | 175 | 214 |
| extreme_direct|fs17|bs2|es3 | 0 | 2 |
| extreme_direct|fs17|bs3|es2 | 20 | 22 |
| extreme_direct|fs17|bs3|es3 | 1 | 0 |
| extreme_direct|fs17|bs4|es2 | 5 | 1 |
| extreme_upgrade|fs10|bs3|es1 | 555 | 502 |
| extreme_upgrade|fs12|bs4|es1 | 216 | 229 |
| extreme_upgrade|fs15|bs5|es1 | 4 | 6 |
| standard|fs10|bs3|es0 | 5154 | 5204 |
| standard|fs12|bs4|es0 | 1406 | 1376 |
| standard|fs15|bs5|es0 | 422 | 406 |
| standard|fs15|bs6|es0 | 18 | 15 |

| bonus trigger | v5 | native |
|---|---|---|
| standard|fs10|bs3|es0 | 12939 | 12996 |
| standard|fs12|bs4|es0 | 4834 | 4822 |
| standard|fs15|bs5|es0 | 2138 | 2118 |
| standard|fs15|bs6|es0 | 88 | 64 |
| standard|fs15|bs7|es0 | 1 | 0 |

| extremebonus trigger | v5 | native |
|---|---|---|
| extreme_direct|fs17|bs0|es2 | 6826 | 6817 |
| extreme_direct|fs17|bs0|es3 | 129 | 125 |
| extreme_direct|fs17|bs1|es2 | 3342 | 3409 |
| extreme_direct|fs17|bs1|es3 | 58 | 48 |
| extreme_direct|fs17|bs2|es2 | 1836 | 1885 |
| extreme_direct|fs17|bs2|es3 | 26 | 23 |
| extreme_direct|fs17|bs3|es2 | 203 | 191 |
| extreme_direct|fs17|bs3|es3 | 3 | 2 |
| extreme_direct|fs17|bs4|es2 | 27 | 31 |
| extreme_direct|fs17|bs5|es2 | 2 | 1 |
| extreme_upgrade|fs10|bs3|es1 | 5402 | 5258 |
| extreme_upgrade|fs12|bs4|es1 | 2078 | 2149 |
| extreme_upgrade|fs15|bs5|es1 | 66 | 61 |
| extreme_upgrade|fs15|bs6|es1 | 2 | 0 |

## Event-schema parity

Per event type, every field path with its key order(s) and value types (int = integral number, frac = fractional), over all books of both builds.

| event type | field paths | top-level keys (v5) | differences (v5 vs native) |
|---|---|---|---|
| booster | 15 | index,type,boosters,gridMults | identical |
| enterBonus | 4 | index,type,reason | identical |
| extremeTrigger | 8 | index,type,positions,reason | identical |
| finalWin | 4 | index,type,amount | identical |
| freeSpinEnd | 5 | index,type,amount,winLevel | identical |
| freeSpinTrigger | 8 | index,type,totalFs,positions | identical |
| lineMults | 11 | index,type,drops,gridMults | identical |
| reveal | 16 | index,type,board,paddingPositions,gameType,anticipation | identical |
| setTotalWin | 4 | index,type,amount | identical |
| setWin | 5 | index,type,amount,winLevel | identical |
| tumbleBoard | 15 | index,type,newSymbols,explodingSymbols | identical |
| updateFreeSpin | 5 | index,type,amount,total | identical |
| updateTumbleWin | 4 | index,type,amount | identical |
| wallDrop | 8 | index,type,kind,positions | identical |
| winInfo | 19 | index,type,totalWin,wins | identical |
| wincap | 4 | index,type,amount | identical |

Schema differences: 0.
