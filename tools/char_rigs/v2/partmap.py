"""Flat-colour part maps of the masters (segmentation priors)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from genkit import run_many

import paths
BOY_PARTS = [
    ('beanie', '#FFFF00', 'the knit beanie'),
    ('head', '#FF0000', 'the head: face, hair and both ears'),
    ('neck', '#FF8800', 'the bare neck between chin and collar'),
    ('torso', '#0000FF', 'the T-shirt body and both of its sleeves'),
    ('arm_l', '#00FFFF', "his right arm (on the left of the picture): the bare skin below the sleeve and the forearm"),
    ('hand_l', '#008080', 'the hand gripping the bottom of the money'),
    ('hand_r', '#800080', 'the hand holding the right edge of the money'),
    ('cash', '#00FF00', 'the fan of dollar bills'),
    ('pelvis', '#808080', 'the jeans waistband, drawstring and crotch (the top of the jeans)'),
    ('leg_l', '#FF00FF', 'the jeans leg on the left of the picture, hip to cuff'),
    ('leg_r', '#8000FF', 'the jeans leg on the right of the picture, hip to cuff'),
    ('shoe_l', '#804000', 'the sneaker and white sock on the left of the picture'),
    ('shoe_r', '#FFC0C0', 'the sneaker and white sock on the right of the picture'),
]
SKULL_PARTS = [
    ('beanie', '#FFFF00', 'the knit beanie'),
    ('cranium', '#FF0000', 'the skull from the beanie down to the upper teeth: eye sockets, nose, cheekbones, upper teeth'),
    ('jaw', '#FF8800', 'the lower jaw bone and lower teeth'),
    ('cigar', '#804000', 'the cigar'),
    ('hood', '#808080', 'the hood bunched behind the neck'),
    ('torso', '#0000FF', 'the hoodie body: chest with the logo, shoulders, and the ribbed hem band'),
    ('strings', '#FFFFFF', 'the two hoodie drawstrings'),
    ('arm_l', '#00FFFF', 'the sleeve on the left of the picture, shoulder to pocket'),
    ('arm_r', '#008080', 'the sleeve on the right of the picture, shoulder to pocket'),
    ('pocket', '#00FF00', 'the front kangaroo pocket panel'),
    ('pelvis', '#800000', 'the top of the trousers below the hem (waist and crotch)'),
    ('leg_l', '#FF00FF', 'the trouser leg on the left of the picture, hip to cuff'),
    ('leg_r', '#8000FF', 'the trouser leg on the right of the picture, hip to cuff'),
    ('shoe_l', '#FFC0C0', 'the sneaker on the left of the picture, with its laces'),
    ('shoe_r', '#C0C0FF', 'the sneaker on the right of the picture, with its laces'),
]


def prompt(parts, who):
    lines = '\n'.join(f'- {desc}: solid {col}' for _, col, desc in parts)
    return (f'Turn this exact picture of {who} into a flat-colour segmentation map for a 2D animation rig. Keep every '
            'shape exactly where it is, at exactly the same size and position, with the same outer silhouette. Replace '
            'all lines, shading, texture, highlights and details with flat, solid, uniform colours - one colour per body '
            'part, as listed below. Each black outline takes the colour of the part it belongs to. No outlines, no '
            'gradients, no anti-aliased blending between parts, no text.\n\n' + lines +
            '\n\nBackground: fully transparent around the figure.')


if __name__ == '__main__':
    jobs = [
        dict(tag='partmap', name='boy_map', prompt=prompt(BOY_PARTS, 'a cartoon boy'),
             refs=[paths.art('boy', 'master')], aspect='2:3', quality='high'),
        dict(tag='partmap', name='skull_map', prompt=prompt(SKULL_PARTS, 'a cartoon skeleton'),
             refs=[paths.art('skull', 'master')], aspect='2:3', quality='high'),
    ]
    run_many(jobs)
