# L8 - Zip bag of buds: what Blender's cut changes from the rig recipe (tools/icon_rigs/recipes/L8.py).
# The bag is ONE image - plastic, seal, sticker border and every bud - and all its motion is skinning in Blender
# (anim_L8.py): the bag breathes by a belly bone that bulges its middle more than its corners, the seal flexes on a
# chain of bones along it, the pile of buds slumps and bounces on its own bone and the loose buds round its edge
# jostle on bones of their own, each a soft local weight that fades into its neighbours. The plastic's creases lie
# OVER the buds, so a bud cut out and moved would tear the crease running across it; bent with the mesh, the film
# crinkles with the buds instead. One image means nothing moving ever uncovers anything (no clean plate needed) and
# there is no seam anywhere: the recipe's seal band met the bag on a hard line, and its buds sat on a blur fill.
# The bag takes the art's own pixels everywhere (plate "art" = art/blender/plates/L8_art.png, a byte copy of
# art/icons-src/L8.png - nothing painted: it only lets FILLS put the art's pixels into a part).
DROP = ["zip", "bud_top", "bud_ur", "bud_r", "bud_br", "bud_b", "bud_l", "bud_ul", "under"]
FILLS = [{"part": "bag", "region": ("rect", -8, -8, 1008, 1008), "plate": "art"}]
