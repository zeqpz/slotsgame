"""Upload changed frontend/ and math files to the Stake Engine (engine.io) scratch bucket.
(Route B in howtotuploadonengine/README.md; the same script as tools/stake_upload.py.)

There is no API key. engine.io only trusts the logged-in browser session, so the minting happens
in a logged-in tab on https://studio.engine.io/teams/smukiez/games/smukiezs-mural/files and the
bytes go up from this machine. Two ways:

  Whole game, only what changed (the usual one):
  1. `python tools/stake_upload.py manifest`  writes upload_manifest.txt (every local file:
     `front/<rel> md5 size`, then `math/<rel> ...`) and upload_tab.js next to it. Run upload_tab.js in
     the tab (DevTools console, or the app browser's javascript tool): it checks the manifest against
     its SHA-256, diffs it against the scratch listings (their etags are plain MD5s), mints one URL
     per changed or new file, and returns {upload, sha, json}.
  2. Save `json` exactly to a file and run  `python tools/stake_upload.py build mint.json <sha>`:
     it refuses a table whose SHA-256 is not the tab's (a copying slip) and writes urls_front.txt and
     one urls_math_<n>.txt per math file.
  3. `python tools/stake_upload.py put front urls_front.txt`, and `put math urls_math_<n>.txt` for each
     book - in parallel: one connection to the bucket can crawl while another runs at speed.

  A few named files:  `mint [front|math] <files...>` prints a snippet that mints them and prints
  'rel|url' lines; save those and `put` them.

Then press "Publish Game" on the dashboard (or POST /api/file/publish/front|math {team, game} from the
tab); the launcher serves the new version. Presigned URLs use STS credentials that expire well
before the advertised 6 hours - mint, PUT, done; never reuse a saved table. The pane's browser in
the Claude app cannot fetch from this machine (https -> localhost is blocked), which is why the
manifest and the table travel by copy, guarded by their checksums.
"""
import hashlib
import http.client
import json
import os
import ssl
import sys
import time
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONT = os.path.join(ROOT, "frontend")
PUBLISH = os.path.join(ROOT, "math-sdk", "games", "smukiez_tag_run", "library", "publish_files")
TEAM, GAME = "smukiez", "smukiezs-mural"
SKIP_DIRS, SKIP_FILES = {"__pycache__"}, {"mock_rgs.py"}   # the local dev server is not part of the bundle

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


def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# The tab's half: check the manifest, diff it against the scratch listings, mint a URL per file
# that differs, hand back the table compactly (the long STS token once, not per URL) with its hash.
TAB_JS = r"""const MAN = `%(man)s`, WANT = '%(sha)s', TEAM = '%(team)s', GAME = '%(game)s';
const hex = b => Array.from(new Uint8Array(b)).map(x => x.toString(16).padStart(2, '0')).join('');
const sha = async s => hex(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s)));
if (await sha(MAN) !== WANT) throw new Error('manifest checksum mismatch: copy it again');
const remote = new Map();
for (const kind of ['front', 'math']) for (const f of await (await fetch(`/api/file/game/${TEAM}/${GAME}/scratch/${kind}`)).json()) remote.set(f.key, String(f.etag).replace(/"/g, ''));
const plan = MAN.split('\n').map(l => l.split(' ')).filter(([key, md5]) => remote.get(key) !== md5);
const rows = [], tokens = [], creds = []; let origin = null;
for (const [key, , size] of plan) {
  const j = await (await fetch('/api/file/upload', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ team: TEAM, game: GAME, path: key, size: +size }) })).json();
  if (!j.url) throw new Error(key + ': ' + JSON.stringify(j));
  const u = new URL(j.url), q = u.searchParams; origin = u.origin;
  const at = (list, v) => { let i = list.indexOf(v); if (i < 0) { list.push(v); i = list.length - 1; } return i; };
  rows.push([key, u.pathname, at(tokens, q.get('X-Amz-Security-Token')), at(creds, q.get('X-Amz-Credential')), q.get('X-Amz-Date'), q.get('X-Amz-Expires'), q.get('X-Amz-SignedHeaders'), q.get('x-id'), q.get('X-Amz-Algorithm'), q.get('X-Amz-Signature')]);
}
const json = JSON.stringify({ origin, tokens, creds, rows });
({ upload: plan.map(([key, , size]) => key + ' ' + size), sha: await sha(json), json })
"""


def manifest(out_dir):
    """Write the local manifest and the tab script that diffs and mints against it."""
    lines = []
    for target, (base, prefix) in TARGETS.items():
        for d, dirs, files in os.walk(base):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
            for f in files:
                if target == "front" and f in SKIP_FILES:
                    continue
                p = os.path.join(d, f)
                lines.append(f"{prefix}/{os.path.relpath(p, base).replace(os.sep, '/')} {_md5(p)} {os.path.getsize(p)}")
    text = "\n".join(sorted(lines))
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "upload_manifest.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    with open(os.path.join(out_dir, "upload_tab.js"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(TAB_JS % {"man": text, "sha": digest, "team": TEAM, "game": GAME})
    print(f"{len(lines)} files, manifest sha256 {digest}; run upload_tab.js in the logged-in Files tab")


def build(table_path, want):
    """Rebuild the presigned URLs from the tab's table, refusing a table that is not the tab's."""
    raw = open(table_path, encoding="utf-8").read().strip()
    got = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    if got != want:
        sys.exit(f"table checksum mismatch ({got}): copy the tab's json again")
    m = json.loads(raw)
    out_dir = os.path.dirname(os.path.abspath(table_path))
    front, math = [], []
    for key, pathname, ti, ci, date, expires, signed, xid, algo, sig in [r[:10] for r in m["rows"]]:
        q = [("X-Amz-Algorithm", algo), ("X-Amz-Credential", m["creds"][ci]), ("X-Amz-Date", date),
             ("X-Amz-Expires", expires), ("X-Amz-Security-Token", m["tokens"][ti]),
             ("X-Amz-SignedHeaders", signed), ("x-id", xid), ("X-Amz-Signature", sig)]
        url = m["origin"] + pathname + "?" + "&".join(f"{k}={urllib.parse.quote(v, safe='')}" for k, v in q)
        target, rel = key.split("/", 1)
        (front if target == "front" else math).append(f"{rel}|{url}")
    with open(os.path.join(out_dir, "urls_front.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(front) + "\n")
    for i, line in enumerate(math):
        with open(os.path.join(out_dir, f"urls_math_{i}.txt"), "w", encoding="utf-8") as fh:
            fh.write(line + "\n")
    print(f"table ok: urls_front.txt ({len(front)} files), {len(math)} urls_math_<n>.txt")


CHUNK, ATTEMPTS, STALL = 1 << 20, 4, 300   # stream 1 MB at a time; a socket that stalls 5 min fails


def _put_one(local, url, rel):
    p = urllib.parse.urlsplit(url)
    size = os.path.getsize(local)
    conn = http.client.HTTPSConnection(p.hostname, 443, timeout=STALL, context=ssl.create_default_context())
    conn.putrequest("PUT", p.path + ("?" + p.query if p.query else ""))
    conn.putheader("Content-Length", str(size))
    conn.endheaders()
    sent, t0, mark = 0, time.time(), 0
    with open(local, "rb") as fh:
        for buf in iter(lambda: fh.read(CHUNK), b""):
            conn.send(buf)
            sent += len(buf)
            if sent - mark >= 8 * CHUNK and sent < size:   # a line per 8 MB, so a stall shows
                mark = sent
                print(f"    {rel}: {sent / 1e6:.1f} / {size / 1e6:.1f} MB ({sent / max(1e-6, time.time() - t0) / 1024:,.0f} KB/s)", flush=True)
    resp = conn.getresponse()
    body = resp.read()[:200]
    conn.close()
    return resp.status, body


def put(urls_file, target="front"):
    base, _ = TARGETS[target]
    fails = 0
    for line in open(urls_file, encoding="utf-8"):
        line = line.strip()
        if not line or "|" not in line:
            continue
        rel, url = line.split("|", 1)
        local = os.path.join(base, rel.replace("/", os.sep))
        for attempt in range(1, ATTEMPTS + 1):
            try:
                status, body = _put_one(local, url, rel)
                if status == 200:
                    print(f"  ok   {rel}  HTTP 200  {os.path.getsize(local):,} bytes", flush=True)
                    break
                print(f"  attempt {attempt}: {rel} HTTP {status} {body!r}", flush=True)
            except Exception as e:  # noqa: BLE001 - report, retry, keep going
                print(f"  attempt {attempt}: {rel} failed: {e}", flush=True)
            time.sleep(5)
        else:
            fails += 1
            print(f"  FAIL {rel} after {ATTEMPTS} attempts", flush=True)
    return 1 if fails else 0


if __name__ == "__main__":
    # usage: manifest [out dir] | build <table.json> <sha256> | mint [front|math] <files...> | put [front|math] urls.txt
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("", [])
    if cmd == "manifest":
        manifest(args[0] if args else os.getcwd())
    elif cmd == "build" and len(args) == 2:
        build(*args)
    elif cmd == "mint" and args:
        tgt, rels = _target(args)
        mint(rels, tgt)
    elif cmd == "put" and args:
        tgt, rest = _target(args)
        if len(rest) != 1:
            print(__doc__)
            sys.exit(2)
        sys.exit(put(rest[0], tgt))
    else:
        print(__doc__)
        sys.exit(2)
