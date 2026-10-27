import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from genkit import run_many
from gedits import BOY, SKL, TAIL
from partspec import MASTER
jobs = [
    dict(tag='skull_edits', name='nolaces', prompt=SKL + ('remove the long loose ends of his shoelaces: both sneakers are '
         'neatly laced up with short tied bows, and nothing lies on the ground around them. The parts of the sneakers '
         'that the loose laces covered are drawn complete.') + ' ' + TAIL,
         refs=[MASTER['skull']], aspect='2:3', quality='high'),
]
run_many(jobs)
