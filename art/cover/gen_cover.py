"""Cover art for Smukiez's City (3:4 and 16:9), GPT Image 2.5 with the game's own art as references.
usage: python gen_cover.py [takes per format]   (writes cover_<ratio>_<n>.png + ledger.jsonl here)"""
import base64, io, json, os, sys, time
sys.path.insert(0, r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\icon_redraw")
import orapi
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current"
REFS = [r"art\characters-src\v2\boy\master.webp", r"art\characters-src\v2\skull\master.webp",
        r"art\wall-src\wall_tag_gen.png", r"art\wall-src\bonus_wall_master.png",
        r"frontend\assets\flat\L1.webp", r"frontend\assets\flat\M.webp", r"frontend\assets\flat\H3.webp"]
TAKES = int(sys.argv[1]) if len(sys.argv) > 1 else 2


def ref(path):
    im = Image.open(os.path.join(REPO, path)).convert("RGBA")
    im.thumbnail((1024, 1024))
    buf = io.BytesIO(); im.save(buf, "WEBP", quality=90)
    return {"type": "image_url", "image_url": {"url": "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()}}


STYLE = ("Hand-inked cartoon in a streetwear graffiti style, drawn by a professional: bold confident black outlines "
         "with varied line weight, rich form shading, fine material texture (fabric weave, spray-paint grain, brick), "
         "small extra details. Lighting: one key light from the upper left, in front of the subject; soft front fill; "
         "a thin cool pale-cyan rim light along the right and lower-right edges; core shadows and ambient occlusion on "
         "the lower-right side; any cast shadow falls down and to the right. Palette: neon graffiti at night - violet "
         "(#6C24B4, #B454E4, #E4B4FC) and neon lime (#6CFC54, #9CE424) on charcoal brick and concrete (#18171c, "
         "#24222a, #34313b); gold (#F5C518) only for money. No electric blue.")
SCENE = ("Cover art for an online slot game called \"SMUKIEZ'S CITY\". A city alley at night: a charcoal brick wall "
         "covered in graffiti, the big SMUKIEZ graffiti tag from the reference sprayed across it with its lime neon "
         "tube outline glowing, wet violet and lime paint drips running down the bricks; above the wall, a night city "
         "skyline with lit windows and a couple of neon signs under a deep violet sky. In front stand the two "
         "characters exactly as drawn in the references - the boy in the ribbed beanie holding a fan of cash, grinning, "
         "and the skull character in the black hoodie and beanie - drawn the same way, same outfits and proportions, "
         "full of attitude. Around them, game symbols from the references burst out: neon-green spray cans, the brick "
         "Multi tile glowing with its value, cash. The title \"SMUKIEZ'S CITY\" in huge graffiti bubble lettering: "
         "\"SMUKIEZ'S\" in neon lime with a violet outline and paint drips, \"CITY\" in bright violet with a lime "
         "outline, thick black keylines and white highlights; spelled exactly S-M-U-K-I-E-Z-'-S C-I-T-Y. "
         "No other text, no watermark, no UI, no frame. ")
LAYOUT = {
    "3:4": "Composition for a 3:4 portrait game thumbnail: the title across the top third, the two characters side "
           "by side in the lower two thirds, symbols around them; keep the outer 5% free of anything important.",
    "16:9": "Composition for a 16:9 landscape banner: the boy on the left, the skull character on the right, the title "
            "large in the upper middle between them, symbols bursting out from the centre; keep the outer 5% free of "
            "anything important.",
}
refs = [ref(p) for p in REFS]
before = orapi.call("/credits")["data"]
left = before["total_credits"] - before["total_usage"]
print(f"credit before: ${left:.2f}", flush=True)
if left < 31:
    sys.exit("credit too low (floor $30)")
for ratio, lay in LAYOUT.items():
    for n in range(TAKES):
        t0 = time.time()
        try:
            j = orapi.call("/images", {"model": "openai/gpt-image-2.5-sunburst", "prompt": SCENE + lay + " " + STYLE,
                                       "quality": "high", "aspect_ratio": ratio, "input_references": refs}, timeout=900)
        except RuntimeError as e:
            print(ratio, n, "FAILED", str(e)[:300], flush=True); continue
        img = base64.b64decode(j["data"][0]["b64_json"])
        out = os.path.join(HERE, f"cover_{ratio.replace(':', 'x')}_{n}.png")
        open(out, "wb").write(img)
        w, h = Image.open(out).size
        cost = (j.get("usage") or {}).get("cost")
        open(os.path.join(HERE, "ledger.jsonl"), "a").write(json.dumps({"file": os.path.basename(out), "ratio": ratio, "size": [w, h], "cost": cost, "sec": round(time.time() - t0)}) + "\n")
        print(ratio, n, f"{w}x{h}", "cost", cost, f"{time.time() - t0:.0f}s", flush=True)
after = orapi.call("/credits")["data"]
print(f"credit after: ${after['total_credits'] - after['total_usage']:.2f}", flush=True)
