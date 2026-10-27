"""Removal / change edits of the masters: each keeps the whole picture in place and reveals what was
hidden behind some parts, or changes the expression.
usage: gedits.py <set> [names]   sets: boy_edits, skull_edits, boy_expr, skull_expr"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
import paths
sys.path.insert(0, HERE)
from genkit import run_many, STYLE, LIGHTING
from partspec import MASTER

TAIL = ('Everything else in the picture stays exactly the same - the same drawing, in exactly the same place and at '
        'the same size - so the two pictures line up perfectly when laid on top of each other. Same art style, line '
        f'weight, colours and lighting.\n\n{STYLE}\n\n{LIGHTING}\n\nBackground: fully transparent around the figure.')

BOY = 'Edit this picture of SMUKIEZ, a cartoon boy: '
SKL = 'Edit this picture of SMOKE SKULL, a cartoon skeleton: '

EDITS = {
    'boy_edits': {
        'noarms': BOY + ('remove the fan of dollar bills and both of his arms and hands completely. His T-shirt stays, '
                         'complete, with both short sleeves empty (no arms in them) hanging at his sides; the whole front '
                         'of the shirt is now visible, with the SMUKIEZ print in full and its folds continuing naturally. '
                         'Nothing is in front of his chest.'),
        'nocash': BOY + ('remove only the fan of dollar bills. His two hands stay exactly where they are, in the same '
                         'grip, holding nothing. Now his other arm (on the right of the picture, hidden behind the money '
                         'before) is visible: its short T-shirt sleeve at the shoulder and the bare arm reaching down to '
                         'that hand. The T-shirt behind where the money was is visible too.'),
        'nobeanie': BOY + ('remove his beanie. Show the top of his head, round, covered in short neat black hair; his '
                           'ears, his face and the hair at the sides of his head stay as they are.'),
        'shortjeans': BOY + ('make his jeans end higher, in a neat rolled cuff just above his ankles, so that both '
                             'sneakers are fully visible, with the tops of his white socks above them. The sneakers and '
                             'socks are complete.'),
        'croptop': BOY + ('make his T-shirt shorter, ending higher at his belly, so that the whole top of his jeans is '
                          'visible below it: the waistband with its drawstring tie, the tops of both legs and the crotch.'),
    },
    'skull_edits': {
        'noarms': SKL + ('remove both arms of his hoodie - the sleeves - completely, and remove the front kangaroo '
                         'pocket and the two drawstrings. The hoodie body becomes sleeveless, with neat armholes at the '
                         'shoulders, and its whole front is visible: the chest with the SMUKIEZ graffiti tag in full, the '
                         'plain fleece belly where the pocket was, and the ribbed hem band.'),
        'nobeanie': SKL + 'remove his beanie. Show the complete, smooth, rounded top of his bare skull.',
        'nohead': SKL + ('remove his skull, his lower jaw, his beanie and the cigar. In their place show his bony neck - '
                         'a short column of two or three cartoon vertebrae - rising out of the hoodie\'s neck opening, '
                         'and the hoodie\'s hood complete, bunched up behind the neck.'),
        'nopocket': SKL + ('remove the front kangaroo pocket of his hoodie, so his hands show: two cartoon skeleton '
                           'hands (white bone fingers) at the ends of his sleeves, resting together in front of his '
                           'belly where the pocket was. The hoodie behind them is plain black fleece.'),
        'jawopen': SKL + ('remove the cigar, and drop his lower jaw open: the upper teeth stay exactly where they are, the '
                          'lower jaw with all its lower teeth hinges down a little, and the dark inside of the mouth '
                          'shows between the two rows of teeth.'),
        'shortpants': SKL + ('make his trousers end higher, in a neat rolled cuff above his ankles, so that both '
                             'sneakers are fully visible, with dark grey socks above them. The sneakers and their long '
                             'untied laces are complete.'),
        'croptop': SKL + ('make his hoodie shorter, its ribbed hem ending higher, so that the whole top of his trousers '
                          'is visible below it: the waistband, the tops of both legs and the crotch.'),
    },
}

EXPR = {
    'boy_expr': {
        'anticipation': ('nervous and tense: eyebrows raised and pinched together with worry lines, eyes wide open '
                         'glancing up to the right, teeth clenched in an anxious grimace showing both rows of teeth'),
        'win': 'thrilled: a huge happy grin showing his top teeth, eyes bright and wide, eyebrows raised',
        'big_win': ('laughing with joy: eyes squeezed shut in happy upturned arcs, mouth wide open in a big laugh '
                    'showing his teeth and his tongue'),
        'lose': ('sad and disappointed: eyebrows tilted up in the middle, eyes looking down to the side, a downturned '
                 'frowning mouth'),
        'cash_show': ('cocky and sly: one eye winking, the other narrowed under a cocked eyebrow, a confident lopsided '
                      'grin showing his teeth'),
        'cash_count': ('concentrating: eyes looking down at the money in his hands, eyebrows lowered a little, a small '
                       'focused frown'),
    },
    'skull_expr': {
        'anticipation': 'alarmed: the eye sockets wide and round, the brow ridges raised high',
        'win': 'gleeful: the eye sockets squinting in a wicked grin, the cheekbones raised',
        'big_win': ('ecstatic: gold star-shaped sparkles glowing inside both eye sockets, the brow ridges raised in '
                    'excitement'),
        'lose': 'glum: the brow ridges drooping sadly, the eye sockets tilted down at their outer corners',
    },
}


def expr_prompt(who, face, desc):
    if who == 'boy':
        return (f'{BOY}change only his facial expression, to the expression of image 2 (an older drawing of the same '
                f'character\'s "{face}" face): {desc}. Keep his head shape, ears, hair, beanie and everything else '
                f'exactly as in image 1. {TAIL}')
    return (f'{SKL}change only the expression of his eye sockets and brow ridges, to the expression of image 2 (an '
            f'older drawing of the same character\'s "{face}" face): {desc}. Keep his teeth, lower jaw, nose hole, '
            f'skull shape, cigar, beanie and everything else exactly as in image 1. {TAIL}')


if __name__ == '__main__':
    st = sys.argv[1]; only = sys.argv[2].split(',') if len(sys.argv) > 2 else None
    who = st.split('_')[0]
    jobs = []
    if st.endswith('_edits'):
        for n, p in EDITS[st].items():
            if only and n not in only: continue
            jobs.append(dict(tag=st, name=n, prompt=p + ' ' + TAIL, refs=[MASTER[who]], aspect='2:3', quality='high'))
    else:
        for n, d in EXPR[st].items():
            if only and n not in only: continue
            old = os.path.join(paths.WORK, 'oldfaces', f'{who}_face_{n}.png')   # the delivered rig's face (oldfaces.py)
            jobs.append(dict(tag=st, name=n, prompt=expr_prompt(who, n, d), refs=[MASTER[who], old], aspect='2:3',
                             quality='max'))
    run_many(jobs, workers=7)
