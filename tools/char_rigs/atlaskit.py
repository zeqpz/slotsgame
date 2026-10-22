"""Spine atlas text <-> data, region crops, and page writing for the character rig pass."""
import os
from PIL import Image


class Atlas:
    """Pages in order; each page: name, header [(key, value)], regions [(name, {key: value})]."""

    def __init__(self, text):
        self.pages = []
        page = None; region = None
        for line in text.replace("\r\n", "\n").split("\n"):
            if not line.strip():
                page = None; region = None; continue
            if ":" not in line:
                if page is None:
                    page = {"name": line.strip(), "header": [], "regions": []}; self.pages.append(page)
                else:
                    region = (line.strip(), {}); page["regions"].append(region)
                continue
            k, v = [s.strip() for s in line.split(":", 1)]
            if region is None: page["header"].append((k, v))
            else: region[1][k] = v

    def text(self):
        out = []
        for p in self.pages:
            out.append(p["name"])
            out += [f"{k}: {v}" for k, v in p["header"]]
            for name, r in p["regions"]:
                out.append(name)
                out += [f"  {k}: {v}" for k, v in r.items()]
            out.append("")
        return "\n".join(out).rstrip("\n") + "\n"

    def region(self, name):
        for p in self.pages:
            for n, r in p["regions"]:
                if n == name: return p, r
        raise KeyError(name)

    def rect(self, name):
        p, r = self.region(name)
        x, y = [int(v) for v in r["xy"].split(",")]; w, h = [int(v) for v in r["size"].split(",")]
        if r.get("rotate", "false") not in ("false", "0"):
            raise ValueError("rotated regions are not handled")
        return p["name"], x, y, w, h

    def page_size(self, page_name):
        for p in self.pages:
            if p["name"] == page_name:
                return tuple(int(v) for v in dict(p["header"])["size"].split(","))

    def set_page_size(self, page_name, w, h):
        for p in self.pages:
            if p["name"] == page_name:
                p["header"] = [(k, f"{w}, {h}" if k == "size" else v) for k, v in p["header"]]

    def add(self, page_name, name, x, y, w, h):
        for p in self.pages:
            if p["name"] == page_name:
                p["regions"].append((name, {"rotate": "false", "xy": f"{x}, {y}", "size": f"{w}, {h}",
                                            "orig": f"{w}, {h}", "offset": "0, 0", "index": "-1"}))
                return
        raise KeyError(page_name)

    def move(self, name, x, y, w=None, h=None):
        p, r = self.region(name)
        r["xy"] = f"{x}, {y}"
        if w is not None:
            r["size"] = f"{w}, {h}"; r["orig"] = f"{w}, {h}"


def crop(pages, atlas, name):
    pg, x, y, w, h = atlas.rect(name)
    return pages[pg].crop((x, y, x + w, y + h))


def paste(pages, atlas, name, img):
    pg, x, y, w, h = atlas.rect(name)
    assert img.size == (w, h), (name, img.size, (w, h))
    box = pages[pg]
    box.paste(Image.new("RGBA", (w, h), (0, 0, 0, 0)), (x, y))
    box.paste(img, (x, y))


def free_spot(atlas, page_name, w, h, pad=4):
    """First free (x, y) on a page for a w x h region (simple shelf search over occupied rects)."""
    W, H = atlas.page_size(page_name)
    rects = []
    for p in atlas.pages:
        if p["name"] != page_name: continue
        for n, r in p["regions"]:
            x, y = [int(v) for v in r["xy"].split(",")]; rw, rh = [int(v) for v in r["size"].split(",")]
            rects.append((x - pad, y - pad, x + rw + pad, y + rh + pad))
    for y in range(pad, H - h - pad, 4):
        for x in range(pad, W - w - pad, 4):
            if all(x + w <= a or x >= c or y + h <= b or y >= d for a, b, c, d in rects):
                return x, y
    return None


def write_pages(out_dir, name, atlas, images, quality=95):
    """Write every page as WebP (quality 95, lossless alpha) and the atlas pointing at them."""
    os.makedirs(out_dir, exist_ok=True)
    for p in atlas.pages:
        src = p["name"]
        img = images[src]
        dst = os.path.splitext(src)[0] + ".webp"
        img.save(os.path.join(out_dir, dst), "WEBP", quality=quality, method=6, alpha_quality=100)
        stale = os.path.join(out_dir, src)
        if src != dst and os.path.exists(stale):
            os.remove(stale)
        p["name"] = dst
    with open(os.path.join(out_dir, name + ".atlas"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(atlas.text())
