import glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audiolib import *
D = r"C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\frontend\assets"
print(f"{'file':28s} sr  ch bits  dur   peak  LUFS  Mmax  cent  floor  st   end")
for p in sorted(glob.glob(D + r"\sfx_*.wav")):
    x, sr, sw = read_wav(p)
    a = analyze(x, sr)
    print(f"{os.path.basename(p):28s} {sr} {x.shape[1]} {sw*8:2d} {a['dur']:5.2f} {a['peak_db']:6.1f} {a['lufs']:6.1f} {a['mmax']:6.1f} {a['centroid']:5.0f} {a['floor_db']:6.1f} {a['start_db']:5.0f} {a['end_db']:5.0f}")
