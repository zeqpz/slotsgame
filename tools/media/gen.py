"""Raw model art for the lobby tile (Engine tile editor layers), one job per call.

  ../../.venv312/Scripts/python.exe -I tools/media/gen.py <job> [suffix]
jobs:
  char_full  Smukiez alone, whole figure, transparent, 2352x3520 (the pixel budget is 3840x2160), drawn from the game's own character art
  bg_16x9    the bright graffiti street, 3840x2160 (no characters, no lettering)
  bg_3x4     the same street laid out for the 3:4 tile, 2480x3312, with bg_16x9 as the style/colour reference
Writes media/src/<job>[_suffix].png (the opaque backgrounds are then kept as lossless .webp, ~20% smaller). Prompts live in tools/media/prompts/; every call goes to tools/media/ledger.jsonl."""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import orimg

ROOT = orimg.ROOT
A = lambda *p: os.path.join(ROOT, *p)
P = lambda n: open(os.path.join(HERE, "prompts", n), encoding="utf-8").read().strip()

BOY = A("art", "characters-src", "v2", "boy", "master.webp")          # the game's Smukiez master (identity)
GRIN = A("art", "characters-src", "v2", "boy", "expressions", "cash_show.webp")   # the FS-card wink grin
FS = A("frontend", "assets", "bonus", "banner_fs.webp")                # the FS card (style of the world)

JOBS = {
    "char_full": dict(prompt="char_full.txt", refs=[BOY, GRIN], aspect="2:3", size="2352x3520", transparent=True),
    "bg_16x9": dict(prompt="bg.txt", refs=[FS], aspect="16:9", size="3840x2160", transparent=False),
    "bg_3x4": dict(prompt="bg.txt", refs=[A("media", "src", "bg_16x9_a.webp")], aspect="3:4", size="2480x3312",
                   transparent=False),
}

if __name__ == "__main__":
    job = sys.argv[1]
    suffix = ("_" + sys.argv[2]) if len(sys.argv) > 2 else ""
    j = JOBS[job]
    left = orimg.credit()
    print(f"credit ${left:.2f}", flush=True)
    if left < 1.5:
        sys.exit("credit too low")
    prompt = P(j["prompt"])
    if job == "bg_16x9":
        prompt = ("The reference is a card from the game: copy only its drawing style, its glossy drippy graffiti paint and "
                  "its lime/purple palette, NOT its dark night wall - this picture is bright daylight. " + prompt)
    if job == "bg_3x4":
        prompt = ("Redraw the street in the reference as a portrait 3:4 picture: same wall, same mural colours and style, "
                  "same sky, same bright daylight. " + prompt)
    out, rec = orimg.generate(A("media", "src", f"{job}{suffix}.png"), prompt, j["refs"], j["aspect"], j["transparent"],
                              extra={"size": j["size"]}, tag=job)
    if not j["transparent"]:
        from PIL import Image
        Image.open(out).save(out[:-4] + ".webp", lossless=True, method=6)
        os.remove(out)
    print(job, rec.get("size"), rec.get("mode"), "cost", rec.get("cost"), rec.get("secs"), "s")
