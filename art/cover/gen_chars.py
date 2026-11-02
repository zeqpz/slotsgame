"""The two figures for the cover, each on its own transparent sheet, drawn from the game's character art.
usage: python gen_chars.py   -> char_boy.png, char_skull.png (+ ledger.jsonl)"""
import base64, io, json, os, sys, time
sys.path.insert(0, r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\icon_redraw")
import orapi
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current"


def ref(path):
    im = Image.open(os.path.join(REPO, path)).convert("RGBA")
    im.thumbnail((1024, 1024))
    buf = io.BytesIO(); im.save(buf, "WEBP", quality=92)
    return {"type": "image_url", "image_url": {"url": "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()}}


COMMON = ("Full-body character art for a game cover: the character exactly as drawn in the reference - same face, "
          "same outfit, same colours and proportions - standing on an invisible floor, feet fully visible, the whole "
          "figure inside the frame with a small margin. Hand-inked cartoon in a streetwear graffiti style: bold "
          "confident black outlines with varied line weight, rich form shading, fine fabric texture. Lighting: one key "
          "light from the upper left, soft front fill, and a soft neon-lime rim light from behind on the right edges "
          "(a neon sign glows behind them). Transparent background. No floor, no cast shadow, no white sticker border, "
          "no outline halo, no text, no logo besides what is on the clothes, no other objects or icons.")
CHARS = {
    "boy": (r"art\characters-src\v2\boy\master.webp",
            "The boy in the ribbed grey beanie and black SMUKIEZ tee, holding a fan of green cash in one hand, a cocky "
            "confident grin, standing slightly turned toward the right of the frame. "),
    "skull": (r"art\characters-src\v2\skull\master.webp",
              "The skull character in the black SMUKIEZ hoodie and grey beanie, hands in the hoodie pocket, a menacing "
              "grin, standing slightly turned toward the left of the frame. "),
}
c = orapi.call("/credits")["data"]; left = c["total_credits"] - c["total_usage"]
print(f"credit before: ${left:.2f}", flush=True)
if left < 31: sys.exit("credit too low (floor $30)")
for name, (path, pose) in CHARS.items():
    t0 = time.time()
    j = orapi.call("/images", {"model": "openai/gpt-image-2.5-sunburst", "prompt": pose + COMMON, "quality": "high",
                               "background": "transparent", "aspect_ratio": "2:3", "input_references": [ref(path)]}, timeout=900)
    out = os.path.join(HERE, f"char_{name}.png")
    open(out, "wb").write(base64.b64decode(j["data"][0]["b64_json"]))
    im = Image.open(out)
    cost = (j.get("usage") or {}).get("cost")
    open(os.path.join(HERE, "ledger.jsonl"), "a").write(json.dumps({"file": os.path.basename(out), "size": im.size, "mode": im.mode, "cost": cost}) + "\n")
    print(name, im.size, im.mode, "cost", cost, f"{time.time() - t0:.0f}s", flush=True)
