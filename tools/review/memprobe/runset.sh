#!/bin/bash
# The WebKit memory model's scenarios (iosprobe3.py), one JSON each: OUTDIR/<TAG>_<scenario>.json; then table3.py OUTDIR.
# usage: tools/review/memprobe/runset.sh OUTDIR TAG BASEURL [scenario ...]   (default: all 13)
# e.g. before = db20be6 served on :8734 (a copy of frontend/ through mock_rgs.py), after = :8733
OUT=$1; TAG=$2; BASE=$3; shift 3
cd "$(dirname "$0")/../../.."
P=".venv312/Scripts/python.exe -I tools/review/memprobe/iosprobe3.py"
declare -A A=(
 [boot_p]="--boot" [boot_l]="--boot --w 844 --h 390" [boot_crios]="--boot --ua crios" [boot_bar]="--boot --h 664 --screenh 844"
 [tumble_p]="--mode base --event 36873" [tumble_l]="--mode base --event 36873 --w 844 --h 390" [tumble_crios]="--mode base --event 36873 --ua crios"
 [bigwin_p]="--mode base --event 33152" [bigwin_l]="--mode base --event 33152 --w 844 --h 390" [bigwin_bar]="--mode base --event 33152 --h 664 --screenh 844"
 [bonus_p]="--mode bonus --event 5" [bonus_l]="--mode bonus --event 5 --w 844 --h 390" [extreme_p]="--mode extremebonus --event 3")
SC=("$@"); [ ${#SC[@]} -eq 0 ] && SC=(boot_p boot_l boot_crios boot_bar tumble_p tumble_l tumble_crios bigwin_p bigwin_l bigwin_bar bonus_p bonus_l extreme_p)
mkdir -p "$OUT"
for sc in "${SC[@]}"; do echo "== $TAG $sc"; $P "$OUT/${TAG}_$sc.json" --base "$BASE" ${A[$sc]} 2>&1 | grep -v -i warning | head -4; done
