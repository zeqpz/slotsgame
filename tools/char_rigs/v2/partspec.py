import os
HERE = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(0, HERE)
import paths
MASTER = {'boy': paths.art('boy', 'master'), 'skull': paths.art('skull', 'master')}
CHAR = {'boy': 'SMUKIEZ, a cartoon boy in a beanie, a SMUKIEZ T-shirt and baggy jeans, holding a fan of dollar bills',
        'skull': 'SMOKE SKULL, a cartoon skeleton in a beanie and a black hoodie, smoking a cigar, hands in his pocket'}

SPEC = {'boy': {}, 'skull': {}}

SPEC['boy']['torso'] = dict(
    labels=['torso'],
    what='his dark-grey SMUKIEZ T-shirt',
    complete=('the whole T-shirt on its own: the body of the shirt and both short sleeves, complete behind where his '
              'head, arms, hands and the money were. Continue the SMUKIEZ print, the folds and the hem naturally. At '
              'the top, draw the crew-neck collar as an opening, with the dark inside of the back of the collar '
              'showing where the neck goes in. Both sleeve openings are empty (no arms in them) and show the dark '
              'inside of the sleeve. The sleeve on the right of the picture (hidden behind the money in image 1) is '
              'drawn complete too, hanging beside the chest.'),
    not_='no head, no neck, no arms or hands, no money, no jeans')

SPEC['boy']['head'] = dict(
    labels=['head'],
    what='his head: the face, the black hair and both ears (the beanie is not part of this piece)',
    complete=('the whole head without the beanie: draw the top of his head that the beanie covered - a rounded '
              'head with short black hair all over it - so the head is complete and round. Keep the face, the '
              'expression, the ears and the hair at the sides exactly as they are. The chin and jaw are complete; '
              'there is no neck below the chin (the neck is a separate piece).'),
    not_='no beanie, no neck, no T-shirt, no money')

SPEC['skull']['torso'] = dict(
    labels=['torso'],
    what="the body of his black hoodie",
    complete=('the hoodie body on its own: the chest with the white SMUKIEZ graffiti tag, the shoulders and the '
              'ribbed hem band, complete behind where his jaw, his sleeves, the front pocket and the drawstrings '
              'were. The sleeves are not part of this piece: at each shoulder the body ends in a rounded armhole '
              'seam. At the top, the neck opening is an empty dark opening (the inside of the hood) where the neck '
              'goes in. Continue the logo, the fleece texture and the folds naturally.'),
    not_='no skull, no jaw, no neck, no hood behind the head, no sleeves, no pocket, no drawstrings, no trousers')

for who in SPEC:
    for k, v in SPEC[who].items():
        v['not'] = v.pop('not_')
