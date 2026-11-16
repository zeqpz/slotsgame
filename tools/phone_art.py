r"""Phone copies of the big interface pictures (Smukiez & Skelly phone tier, 2026-11-16) -> frontend/assets/phone/.

A phone (window.PHONE: the mobile tier on a screen no wider than 500 CSS px on its short side) draws these at well
under their pixels; each copy is cut to the biggest a phone ever draws it - measured with tools/review/memprobe/picfit.py
at 390x844, 844x390, 440x956 and 956x440 @3 (picmax.py) - plus headroom, so it is still drawn by scaling DOWN and looks
the same. Resized in premultiplied alpha with Lanczos, saved as lossy WebP like the originals.

The wall (bonus_wall.webp, 3840x2160, 33 MB decoded) gets two copies:
  wall_portrait.webp   the middle 1620x2160 of it, uncut in scale: an upright phone shows the wall `cover`ed and
                       height-bound (any window up to 3:4), so only the middle of it is ever on screen, at the very
                       same pixels
  wall_landscape.webp  2560x1440: a phone on its side shows the whole wall `contain`ed at most 1426 device px tall
usage: .venv312\Scripts\python.exe tools/phone_art.py
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / "frontend" / "assets"
OUT = ROOT / "phone"
# file -> scale (or a target width); the biggest a phone draws it (device px, picmax.py) in the comment
COPIES = {
    "wall_tag.webp": 1900,            # 3303x1674, drawn at most 1848x937 (956x440)
    "frame.webp": 1400,               # 2200x1982, at most 1300x1055
    "plate_grey.webp": 1450,          # 1935x1135, the plate behind the reels (covered, at .72 opacity): at most 1239x994, i.e. 1694 wide;
                                      # a soft grey texture: three quarters of that looks the same
    "title_logo.webp": 1300,          # 1700x1140, at most 1214x814 (the features screen)
    "feature_box.webp": 630,          # 840x1074, at most 571x723
    "xbonus_text.webp": 540,          # 1065x897, at most 478x402
    "total_win.webp": 1300,           # 1800x508, at most 1178x346
    "big_win.webp": 1300,             # the win headlines, drawn like TOTAL WIN
    "mega_win.webp": 1300,
    "xtreme_win.webp": 1300,
    "bonus_btn_text.webp": 300,       # 1140x759, the Bonus button: at most 244x124 (contained: ~186 wide)
    "bonus_btn_bg.webp": 300,         # 950x610, likewise
    "wallfx/bonus_glow.webp": 380,    # 1216x780, the button's soft glow: at most 312x159
}


def resize(im, w):
    h = round(im.height * w / im.width)
    if im.mode == "RGBA":
        return im.convert("RGBa").resize((w, h), Image.LANCZOS).convert("RGBA")
    return im.resize((w, h), Image.LANCZOS)


def save(im, name):
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    im.save(p, "WEBP", quality=90, alpha_quality=100, method=6)
    print(f"{name:28s} {im.width}x{im.height}  {p.stat().st_size / 1024:7.1f} KB  {im.width * im.height * 4 / 1e6:5.1f} MB decoded")


def main():
    for name, w in COPIES.items():
        im = Image.open(ROOT / name)
        im.load()
        save(resize(im, w), name)
    wall = Image.open(ROOT / "bonus_wall.webp").convert("RGB")
    cw = 1620
    x0 = (wall.width - cw) // 2
    save(wall.crop((x0, 0, x0 + cw, wall.height)), "wall_portrait.webp")
    save(resize(wall, 2560), "wall_landscape.webp")


if __name__ == "__main__":
    main()
