"""Generate raw takes (resumable). Usage: python gen.py [--max N] [filter ...]
Stops before the balance would drop under FLOOR."""
import os, sys, time, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orapi, spec

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
FLOOR = float(os.environ.get("FLOOR", "0"))


def one(name, prompt, take):
    out = os.path.join(RAW, f"{name}_{take}.pcm")
    if os.path.exists(out) and os.path.getsize(out) > 1000:
        return name, take, "kept", 0
    try:
        b, ct = orapi.speech(prompt, fmt="pcm")
    except Exception as e:
        return name, take, f"ERR {str(e)[:160]}", 0
    if "rate=24000" not in ct or "channels=2" not in ct:
        open(out + ".ct", "w").write(ct)
    open(out + ".part", "wb").write(b)
    os.replace(out + ".part", out)
    return name, take, f"{len(b) / 4 / 24000:.2f}s", len(b) / 4 / 24000


def main():
    os.makedirs(RAW, exist_ok=True)
    args = sys.argv[1:]
    mx = None
    if args and args[0] == "--max":
        mx = int(args[1]); args = args[2:]
    work = []
    for name, prompt, takes, kind in spec.jobs():
        if args and not any(f == name for f in args):
            continue
        for t in range(1, takes + 1):
            if not os.path.exists(os.path.join(RAW, f"{name}_{t}.pcm")):
                work.append((name, prompt, t))
    if mx is not None:
        work = work[:mx]
    c0 = orapi.credits()
    print(f"{len(work)} takes; credits {c0:.4f}", flush=True)
    if c0 < FLOOR:
        print("under floor"); return
    t0 = time.time(); secs = 0; errs = 0
    with cf.ThreadPoolExecutor(6) as ex:
        for i, (n, t, r, d) in enumerate(ex.map(lambda w: one(*w), work)):
            secs += d
            if r.startswith("ERR"): errs += 1
            print(f"[{i + 1}/{len(work)}] {n}_{t}: {r}", flush=True)
    c1 = orapi.credits()
    print(f"done {time.time() - t0:.0f}s, {errs} errors, {secs:.1f}s audio; credits {c1:.4f} (spent {c0 - c1:.4f})", flush=True)


if __name__ == "__main__":
    main()
