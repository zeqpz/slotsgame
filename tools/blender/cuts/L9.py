# L9 - Freight car with a graffiti piece: what Blender's cut changes from the rig recipe (tools/icon_rigs/recipes/L9.py).
# The car is ONE image, skinned in Blender (anim_L9.py): the car body rides one bone (it rocks and bounces on its
# springs), each bogie rides its own (it stays on the rail and kicks up at every rail joint), and the strip between
# them - the bogies' bolsters and springs, just under the underframe - is weighted half and half, so it is the springs
# that give: they squeeze and stretch while the steel body and the wheels stay rigid. The sticker border round the
# wheels and the boxes under the car stretches with them, so it never breaks, and nothing moving uncovers anything
# (no clean plate needed). The recipe's bogies met the body on a hard line (a hairline once filtered) over copies of
# the underframe bar; here the car takes the art's own pixels everywhere (plate "art" =
# art/blender/plates/L9_art.png, a byte copy of art/icons-src/L9.png - nothing painted: it only lets FILLS put the
# art's pixels into a part).
DROP = ["bogie_l", "bogie_r", "frame_l", "frame_r"]
FILLS = [{"part": "body", "region": ("rect", -8, -8, 1008, 1008), "plate": "art"}]
