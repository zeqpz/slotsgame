"""Bring a Stake Math SDK build (index.json, lookUpTable_<mode>_0.csv, books_<mode>.jsonl.zst) into a Slot Engine
game's __build__ folder, laid out the way Slot Engine's own simulation writes it, so its local gaming server and
panel serve those exact books - nothing re-simulated, the same ids, weights and events.
  __build__/publish_files/          the publish files (hard links, not copies)
  __build__/books_<mode>.index.meta.json, books_chunks/books_<mode>_0.index.txt, books_<mode>_chunk_0-<n>.jsonl.zst
usage: python engine/tools/import_math_sdk.py <math-sdk publish_files dir> <slot-engine game dir> [books per chunk]"""
import io, json, os, re, shutil, sys
import zstandard

ID = re.compile(r'\{\s*"id"\s*:\s*(\d+)')

src, game_dir = sys.argv[1], sys.argv[2]
per_chunk = int(sys.argv[3]) if len(sys.argv) > 3 else 2000
build = os.path.join(game_dir, "__build__")
pub = os.path.join(build, "publish_files")
chunks_dir = os.path.join(build, "books_chunks")
shutil.rmtree(chunks_dir, ignore_errors=True)
os.makedirs(pub, exist_ok=True)
os.makedirs(chunks_dir, exist_ok=True)

index = json.load(open(os.path.join(src, "index.json")))
for name in os.listdir(src):
    if name == "index.json" or name.startswith("lookUpTable_") or name.startswith("books_"):
        dst = os.path.join(pub, name)
        if os.path.exists(dst):
            os.remove(dst)
        try:
            os.link(os.path.join(src, name), dst)             # same file on disk, no second copy
        except OSError:
            shutil.copy2(os.path.join(src, name), dst)

cctx = zstandard.ZstdCompressor(level=3)
for mode in index["modes"]:
    m = mode["name"]
    ids, chunk, buf, n = [], 0, [], 0
    with open(os.path.join(chunks_dir, f"books_{m}_0.index.txt"), "w", newline="\n") as idx, \
            open(os.path.join(src, mode["events"]), "rb") as fh:
        reader = io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(fh), encoding="utf-8")

        def flush():
            global chunk, buf
            if buf:
                with open(os.path.join(chunks_dir, f"books_{m}_chunk_0-{chunk}.jsonl.zst"), "wb") as out:
                    out.write(cctx.compress(("\n".join(buf) + "\n").encode("utf-8")))
                chunk += 1
                buf = []
        for line in reader:
            line = line.strip()
            if not line:
                continue
            hit = ID.match(line)                              # the id leads each book: no need to parse it all
            book_id = int(hit.group(1)) if hit else json.loads(line)["id"]
            idx.write(f"{book_id},0,{chunk}\n")
            ids.append(book_id)
            buf.append(line)
            n += 1
            if len(buf) >= per_chunk:
                flush()
        flush()
    meta = [{"worker": 0, "chunks": chunk, "simStart": min(ids), "simEnd": max(ids)}]
    json.dump(meta, open(os.path.join(build, f"books_{m}.index.meta.json"), "w"), indent=2)
    print(f"{m}: {n} books -> {chunk} chunks (ids {min(ids)}..{max(ids)})", flush=True)
print("->", build)
