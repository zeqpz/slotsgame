"""Upload changed frontend/ files to the Stake Engine (engine.io) scratch bucket.

There is no API key. engine.io only trusts the logged-in browser session, so the flow is:

  1. In a browser tab that is logged in and sitting on
     https://engine.io/teams/smukiez/games/smukiezs-mural/files
     run the JavaScript printed by  `python tools/stake_upload.py mint index.html rgs.js`
     (same-origin fetch to POST /api/file/upload, ONE file per call, body
     {team, game, path: "front/<rel>", size}). It prints one 'rel|url' line per file.
  2. Save those lines to a text file and run  `python tools/stake_upload.py put urls.txt`
     which PUTs the bytes to each presigned S3 URL from this machine.
  3. Press "Publish Game" on the same dashboard page (or POST /api/file/publish/front
     {team, game} from the tab). The launcher then serves the new version.

Presigned URLs use STS credentials that expire well before the advertised 6 hours —
mint, PUT, done; never reuse a saved table. Math files use the "math/" prefix instead.
"""
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONT = os.path.join(ROOT, "frontend")
PUBLISH = os.path.join(ROOT, "math-sdk", "games", "smukiez_tag_run", "library", "publish_files")
TEAM, GAME = "smukiez", "smukiezs-mural"

# target -> (local base dir, remote prefix). `front` files live in frontend/,
# `math` files (books + LUTs + index.json) live in the game's publish_files/.
TARGETS = {"front": (FRONT, "front"), "math": (PUBLISH, "math")}


def _target(args):
    """Split an optional leading `front`/`math` word off the arg list (default front)."""
    if args and args[0] in TARGETS:
        return args[0], args[1:]
    return "front", args


def mint(rels, target="front"):
    """Print the browser-side snippet that mints one presigned PUT URL per file."""
    base, prefix = TARGETS[target]
    want = [[f"{prefix}/{rel}", os.path.getsize(os.path.join(base, rel.replace("/", os.sep)))] for rel in rels]
    print(f"// paste into the DevTools console (or the app browser's javascript tool) on the engine.io Files page ({target}):")
    print(
        "const want=" + json.dumps(want) + ";"
        "const out=[];for(const [path,size] of want){"
        "const r=await fetch('/api/file/upload',{method:'POST',headers:{'Content-Type':'application/json'},"
        f"body:JSON.stringify({{team:'{TEAM}',game:'{GAME}',path,size}})}});"
        f"const j=await r.json();out.push(path.replace(/^{prefix}\\//,'')+'|'+(j.url||JSON.stringify(j)));}}"
        "console.log(out.join('\\n'));out.join('\\n')"
    )


def put(urls_file, target="front"):
    base, _ = TARGETS[target]
    fails = 0
    for line in open(urls_file, encoding="utf-8"):
        line = line.strip()
        if not line or "|" not in line:
            continue
        rel, url = line.split("|", 1)
        data = open(os.path.join(base, rel.replace("/", os.sep)), "rb").read()
        req = urllib.request.Request(url, data=data, method="PUT")
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                print(f"  ok   {rel}  HTTP {r.status}  {len(data):,} bytes")
        except Exception as e:  # noqa: BLE001 - report and keep going
            fails += 1
            body = getattr(e, "read", None)
            print(f"  FAIL {rel}: {e}" + (("\n" + body()[:300].decode("utf-8", "replace")) if body else ""))
    return 1 if fails else 0


if __name__ == "__main__":
    # usage: mint [front|math] <files...>   |   put [front|math] urls.txt
    if len(sys.argv) >= 3 and sys.argv[1] == "mint":
        tgt, rels = _target(sys.argv[2:])
        mint(rels, tgt)
    elif len(sys.argv) >= 3 and sys.argv[1] == "put":
        tgt, rest = _target(sys.argv[2:])
        if len(rest) != 1:
            print(__doc__)
            sys.exit(2)
        sys.exit(put(rest[0], tgt))
    else:
        print(__doc__)
        sys.exit(2)
