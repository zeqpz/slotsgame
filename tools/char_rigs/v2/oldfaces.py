import os, sys
sys.path.insert(0, r'C:\Users\CooperHinkel\Documents\ClaudeRoblox\slotsgame-current\tools\char_rigs')
import atlaskit as ak
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths
out = os.path.join(paths.WORK, 'oldfaces'); os.makedirs(out, exist_ok=True)
for name in ('smukiez', 'smoke-skull'):
    d = paths.DELIVERED
    atlas = ak.Atlas(open(os.path.join(d, name + '.atlas'), encoding='utf-8').read())
    pages = {p['name']: Image.open(os.path.join(d, p['name'])).convert('RGBA') for p in atlas.pages}
    for p in atlas.pages:
        for n, r in p['regions']:
            if n.startswith('face_'):
                im = ak.crop(pages, atlas, n)
                im.save(os.path.join(out, f'{"boy" if name == "smukiez" else "skull"}_{n}.png'))
                print(n, im.size)
