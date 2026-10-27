"""Where the v2 character pipeline reads and writes.

SRC   art/characters-src/v2: the generated source art (lossless WebP) and the API cost ledger
WORK  intermediates (aligned edits, labels, parts, upscales, films): %TEMP%/smukiez-chars-v2, or
      SMUKIEZ_CHARS_WORK
OUT   frontend/assets/spine: the rigs the game loads
"""
import os, tempfile
V2 = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(V2)))
SRC = os.path.join(REPO, 'art', 'characters-src', 'v2')
DELIVERED = os.path.join(REPO, 'art', 'characters-src')
WORK = os.environ.get('SMUKIEZ_CHARS_WORK') or os.path.join(tempfile.gettempdir(), 'smukiez-chars-v2')
OUT = os.path.join(REPO, 'frontend', 'assets', 'spine')
os.makedirs(WORK, exist_ok=True)


def art(who, name):
    """a source image: art('boy', 'master'), art('skull', 'edits/nohead'), art('boy', 'expressions/win')"""
    return os.path.join(SRC, who, name + '.webp')


def aligned(who, name):
    return os.path.join(WORK, 'aligned', who, name + '.png')
