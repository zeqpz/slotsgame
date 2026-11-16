"""The win (hit) and Multi clips on a phone, frozen mid-clip, at two settings side by side (QA for the mobile tier's clip
density, 2026-11-16). Boots the live game at 390x844 @3, plays CLIP on every cell, holds the symbol loop at MS into it and
shoots the board; once per --extra variant. Writes OUTPREFIX_<i>.png and a crop sheet OUTPREFIX_sheet.png.
usage: clipshot.py OUTPREFIX --clip hit --ms 600 --extra "&clipres=1" --extra ""
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import Browser, IPHONE_UA, MOCK, game_url, enter_game

a = sys.argv[1:]
pre = a[0]
clip = a[a.index("--clip") + 1] if "--clip" in a else "hit"
ms = int(a[a.index("--ms") + 1]) if "--ms" in a else 600
extras = [a[i + 1] for i, x in enumerate(a) if x == "--extra"] or [""]
FREEZE = """(async (clip, ms) => {
  await new Promise(r => setTimeout(r, 1500));
  const now0 = performance.now.bind(performance);
  eachCell(c => rigPlay(c, clip));
  const t0 = now0();
  await new Promise(r => setTimeout(r, ms));
  performance.now = () => t0 + ms;   // the symbol loop reads the clock: hold it here
  BoardGL.touch();
  await new Promise(r => setTimeout(r, 400));
  return 1;
})(%r, %d)"""
shots = []
for i, ex in enumerate(extras):
    b = Browser(390, 844, 3, ua=IPHONE_UA, mobile=True)
    try:
        b.open(game_url(MOCK, ex), .3)
        enter_game(b)
        b.js(FREEZE % (clip, ms))
        shots.append(b.shot(f"{pre}_{i}.png"))
        print(i, ex, b.console()[:3])
    finally:
        b.close()
from PIL import Image
ims = [Image.open(p).convert("RGB") for p in shots]
box = (60, 1050, 1110, 1600)   # three rows of the board, device px
crops = [im.crop(box) for im in ims]
sheet = Image.new("RGB", (crops[0].width, sum(c.height for c in crops) + 10 * (len(crops) - 1)), (255, 0, 255))
y = 0
for c in crops:
    sheet.paste(c, (0, y)); y += c.height + 10
sheet.save(f"{pre}_sheet.png")
