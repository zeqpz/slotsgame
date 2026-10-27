from genkit import STYLE, LIGHTING

BOY = ('SMUKIEZ, a cartoon boy with a big head and a small body: a charcoal-grey ribbed knit beanie pulled low, short '
       'black hair, big ears, a cheeky smirk and big eyes glancing to the right; a dark-grey crew-neck T-shirt with '
       'the word SMUKIEZ printed in white on the chest; dark charcoal baggy jeans; dark crimson-red and cool-grey high-top basketball '
       'sneakers with white socks; he holds a fanned-out stack of green dollar bills at his chest in both hands.')

SKULL = ('SMOKE SKULL, a cartoon skeleton with a big white skull head: an angry grin with big black eye sockets, a '
         'cigar clenched in the left side of his teeth (the tip burning orange), a charcoal-grey knit beanie with a '
         'folded cuff; a black hoodie with a white graffiti SMUKIEZ tag on the chest, the hood bunched behind his '
         'neck, two drawstrings hanging from the neck, both hands in the front kangaroo pocket and a ribbed hem; dark '
         'charcoal baggy trousers with rolled cuffs; white low-top canvas sneakers with long untied laces lying on '
         'the ground.')


def master(who):
    desc = BOY if who == 'boy' else SKULL
    keep = ('Keep it the same character and the same drawing: the same pose, the same proportions, the same outfit '
            'and colours, the same face and expression, the same props, and the same size and position in the frame '
            '- it must line up with the original if laid on top of it. Every part of the figure stays inside the frame.')
    return (f'Redraw this character as a high-end, professionally illustrated version of the same drawing, for an '
            f'animated slot-game character: {desc}\n\n{keep}\n\n'
            f'Make it much better: cleaner, crisper linework, more detail and richer form shading on every part, '
            f'readable shapes, and fine material texture.\n\n{STYLE}\n\n{LIGHTING}\n\n'
            'Background: fully transparent around the figure. No cast shadow on the ground, no glow, no smoke, '
            'nothing else in the image.')
