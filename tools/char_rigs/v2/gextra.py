import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from genkit import run_many
from gedits import BOY, SKL, TAIL
from partspec import MASTER
jobs = [
    dict(tag='boy_edits', name='nohands', prompt=BOY + ('remove both of his hands and arms, but keep the fan of dollar bills '
         'exactly where it is, floating in the air in front of him: every bill complete, including the parts the hands '
         'covered before. His T-shirt stays complete with both short sleeves empty.') + ' ' + TAIL,
         refs=[MASTER['boy']], aspect='2:3', quality='high'),
]
run_many(jobs)
