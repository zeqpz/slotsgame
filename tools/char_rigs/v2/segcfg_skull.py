# appended to segcfg: the skull's cuts and forced parts
# the bite: between the upper and lower teeth, then (right of the mouth's corner) along the cheekbone's
# drawn lower outline, so the whole cheek is skull and the jaw's seam lies on ink
BITE = [(200, 655), (330, 657), (450, 657), (580, 652), (598, 625), (606, 600), (630, 597), (670, 600), (710, 598),
        (745, 580), (770, 545), (800, 520), (830, 500)]
SKULL_EXTRA = ['thigh_l', 'shin_l', 'thigh_r', 'shin_r', 'arm_l_upper', 'arm_l_fore', 'arm_r_upper', 'arm_r_fore',
               'lace_l_up', 'lace_r_right', 'string_l', 'string_r']
SKULL_CUTS = [
    ('jaw', BITE, 'jaw', 'cranium'),
    ('cranium', BITE, 'jaw', 'cranium'),
    ('leg_l', [(340, 1040), (497, 1095)], 'leg_l', 'pelvis'),
    ('leg_r', [(497, 1095), (680, 1040)], 'leg_r', 'pelvis'),
    ('leg_l', [(340, 1135), (500, 1140)], 'shin_l', 'thigh_l'),
    ('leg_r', [(495, 1150), (680, 1145)], 'shin_r', 'thigh_r'),
    ('arm_l', [(295, 925), (360, 865)], 'arm_l_fore', 'arm_l_upper'),
    ('arm_r', [(775, 930), (700, 870)], 'arm_r_upper', 'arm_r_fore'),
]
SKULL_LINES = [
    ('lace_l_up', [(328, 1236), (290, 1214), (256, 1188), (241, 1150), (232, 1112)], 11, ['shoe_l']),
    ('lace_r_right', [(650, 1256), (700, 1241), (750, 1229), (792, 1214)], 11, ['shoe_r']),
    ('string_l', [(432, 762), (431, 800), (430, 845)], 9, ['strings', 'torso']),
    ('string_r', [(566, 758), (568, 800), (570, 842)], 9, ['strings', 'torso']),
]
SKULL_ORDER = ['hood', 'pelvis', 'shoe_l', 'shoe_r', 'lace_l_up', 'lace_r_right',
               'shin_l', 'shin_r', 'thigh_l', 'thigh_r', 'torso', 'arm_l_upper', 'arm_r_upper', 'arm_l_fore',
               'arm_r_fore', 'pocket', 'strings', 'string_l', 'string_r', 'jaw', 'cranium', 'beanie', 'cigar']

SKULL_REACH = {'string_l': 3, 'string_r': 3, 'strings': 3, 'lace_l_up': 3, 'lace_r_right': 3}

SKULL_BANDS = [
    ('string_l', [(432, 764), (431, 800), (429, 845)], 8),
    ('string_r', [(575, 742), (575, 775), (575, 802)], 8),
]
SKULL_BAND_FROM = {'string_l': ['strings', 'torso', 'string_l', 'string_r'], 'string_r': ['strings', 'torso', 'string_l', 'string_r']}

# applied to the finished labels: the skull's outer outline under the beanie's right side - the dark knit
# beside it is beanie (as ink it had taken the label of the nearest paint, the skull's)
SKULL_FINAL_CUTS = [
    ('cranium', [(560, 225), (600, 262), (642, 302), (688, 347), (738, 401), (776, 451), (796, 491), (801, 526)], 'cranium', 'beanie'),
]
