import os, json

base = "frontend"
skip = {"mock_rgs.py"}          # test harness, not part of the shipped bundle
out = []
for root, dirs, files in os.walk(base):
    for f in sorted(files):
        if f in skip:
            continue
        full = os.path.join(root, f)
        rel = os.path.relpath(full, base).replace(os.sep, "/")
        out.append([rel, os.path.getsize(full)])
out.sort()
with open("frontend_manifest.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, separators=(",", ":"))
print(json.dumps(out, separators=(",", ":")))
print("\nfiles:", len(out), "| bytes:", sum(s for _, s in out))
