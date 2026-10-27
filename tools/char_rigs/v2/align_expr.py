import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import align_all
align_all.JOBS['boy'] = [('expressions/' + n, 'torso,cash,hand_l,hand_r,arm_l_fore,shoe_l,shoe_r,shin_l,shin_r,thigh_l,thigh_r,beanie', False)
                         for n in ('anticipation', 'win', 'big_win', 'lose', 'cash_show', 'cash_count')] + \
                        [('edits/nohands', 'head,beanie,shoe_l,shoe_r,shin_l,shin_r,thigh_l,thigh_r', False)]
align_all.JOBS['skull'] = [('expressions/' + n, 'torso,arm_l,arm_r,pocket,leg_l,leg_r,shoe_l,shoe_r,beanie,cigar', False)
                           for n in ('anticipation', 'win', 'big_win', 'lose')]
align_all.run(sys.argv[1])
