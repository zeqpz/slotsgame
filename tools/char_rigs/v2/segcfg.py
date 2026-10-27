import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from partmap import BOY_PARTS, SKULL_PARTS
import paths

# cuts: (map part, polyline, part on the line's left-normal side, part on the other side).
# For a line drawn left -> right the left-normal side is BELOW it; drawn top -> bottom, it is LEFT of it.
CFG = {
    'boy': dict(
        master=paths.art('boy', 'master'),
        map=paths.art('boy', 'partmap'),
        palette=BOY_PARTS,
        extra=['thigh_l', 'shin_l', 'thigh_r', 'shin_r', 'arm_l_upper', 'arm_l_fore'],
        force=[('head', [(262, 470), (760, 470), (772, 600), (700, 700), (560, 736), (420, 736), (300, 700), (252, 600)])],
        cuts=[
            ('leg_l', [(158, 1111), (548, 1197)], 'shin_l', 'thigh_l'),
            ('leg_r', [(380, 1193), (776, 1141)], 'shin_r', 'thigh_r'),
            ('arm_l', [(330, 860), (305, 1010)], 'arm_l_upper', 'arm_l_fore'),
        ],
        order=['neck', 'pelvis', 'shoe_l', 'shoe_r', 'shin_l', 'shin_r', 'thigh_l', 'thigh_r', 'torso',
               'arm_l_upper', 'head', 'beanie', 'arm_l_fore', 'cash', 'hand_l', 'hand_r'],
    ),
    'skull': dict(
        master=paths.art('skull', 'master'),
        map=paths.art('skull', 'partmap'),
        palette=SKULL_PARTS,
        extra=[],
        cuts=[],
        order=['hood', 'pelvis', 'shoe_l', 'shoe_r', 'leg_l', 'leg_r', 'torso', 'arm_l', 'arm_r', 'pocket',
               'strings', 'jaw', 'cranium', 'beanie', 'cigar'],
    ),
}

from segcfg_skull import SKULL_EXTRA, SKULL_CUTS, SKULL_LINES, SKULL_ORDER, SKULL_REACH, SKULL_BANDS, SKULL_BAND_FROM, SKULL_FINAL_CUTS
CFG['skull'].update(extra=SKULL_EXTRA, cuts=SKULL_CUTS, force_lines=SKULL_LINES, order=SKULL_ORDER, reach=SKULL_REACH, bands=SKULL_BANDS, band_from=SKULL_BAND_FROM, final_cuts=SKULL_FINAL_CUTS)
CFG['boy']['reach'] = {'hand_l': 4, 'hand_r': 4}
