"""Smukiez's City sound pass: name -> (prompt, takes, kind).
kind drives the trim/clean rules in process.py."""
PRE = "[Sound effect only. No voice, no speech, no music.] "
CLOSE = " Close-up, dry, clean studio foley recording, crisp and punchy, no background noise, no room hiss."

S = {
    # ---------------- win presentation ----------------
    "spray_short": ("A spray paint can spraying one quick short burst while sweeping across a brick wall: a crisp, airy, bright pssht hiss lasting half a second, starting with the tiny click of the nozzle.", 6, "spray"),
    "spray_long": ("A spray paint can spraying one smooth continuous line across a wall: a steady, crisp, airy hiss that swells slightly and stops cleanly after about one and a half seconds.", 6, "spray"),
    "paint_drip": ("A single fat drop of wet paint falling onto a hard floor: one tiny, wet, juicy plip.", 8, "drop"),
    "glow_pulse": ("A soft warm magical glow swelling up and fading: a short airy shimmering swell with a gentle bright twinkle, under one second, very smooth.", 5, "tone"),
    "shine": ("A quick bright glint of light sweeping across shiny chrome: one short, crisp, high sparkling shimmer swipe, like a cartoon shine.", 5, "tone"),
    "sparkle": ("A few tiny glittering sparkles: a quick light cascade of soft, high, crystalline twinkling chimes, delicate and magical, under one second.", 6, "tone"),
    "count_tick": ("One single, very short, crisp and pleasant tick of a small mechanical counter wheel clicking one notch. Just one tick.", 8, "click"),
    "count_end": ("A satisfying cash register finishing a sale: a solid mechanical ka-chunk of the drawer lock and one bright clear bell ding.", 6, "hit"),
    "mult_slam": ("A heavy, punchy, very satisfying impact: a big steel rubber stamp slammed down hard on a thick wooden desk, a deep chesty thump with a short bright metallic clang on top.", 7, "impact"),
    "count_whoosh": ("A fast rising whoosh building upward, swelling air rushing up in pitch for about one second, smooth and exciting.", 5, "whoosh"),
    "float_away": ("A soft airy whoosh drifting upward and fading out gently, like a light balloon floating away into the sky, with a faint shimmer.", 5, "whoosh"),
    "paint_burst": ("A small balloon filled with paint bursting: a juicy wet pop with a short wet splatter.", 6, "hit"),

    # ---------------- board foley: symbols landing ----------------
    "land_soft": ("A small object dropping onto a wooden table: one soft, short, solid thud.", 6, "hit"),
    "land_bag": ("A small heavy canvas money bag full of cash dropped onto a table: a soft weighty thud with a short crisp rustle of the bag.", 5, "hit"),
    "land_can": ("A metal spray paint can set down hard on a table: a short metallic tonk with the mixing ball inside rattling once.", 6, "hit"),
    "land_chain": ("A thick gold chain necklace dropped onto a table: a short bright heavy clinking jingle of metal links.", 6, "hit"),
    "land_coin": ("A few coins dropped onto a wooden table: a short crisp bright clink and jingle.", 5, "hit"),
    "land_dice": ("Two dice thrown onto a wooden table: a short crisp clatter as they tumble and stop.", 6, "hit"),
    "land_baggie": ("A small plastic zip baggie tossed onto a table: a short soft crinkle of thin plastic.", 5, "hit"),
    "land_fabric": ("A knitted beanie hat tossed onto a table: a soft muffled fabric flop.", 6, "hit"),
    "land_hoodie": ("A folded cotton hoodie dropped onto a table: a soft heavy fabric whump with a little rustle.", 5, "hit"),
    "land_marker": ("Two plastic permanent markers dropped onto a table: a short light plastic clack and rattle.", 5, "hit"),
    "land_brick": ("A red clay brick set down hard on concrete: one solid dry, hard, heavy knock.", 6, "impact"),
    "land_board": ("A skateboard dropped flat onto concrete: one sharp woody clack with the wheels rattling briefly.", 5, "hit"),
    "land_box": ("A cardboard sneaker box dropped onto a table: a short hollow papery thump.", 5, "hit"),
    "land_shoe": ("A sneaker dropped onto a wooden floor: a soft rubbery thud with a tiny squeak.", 5, "hit"),
    "land_boombox": ("A plastic boombox radio set down on a table: a short hollow plastic thunk with a slight speaker buzz.", 5, "hit"),
    "land_metal": ("A small die-cast metal toy car dropped onto a table: a short solid metallic clunk with a little rattle.", 5, "hit"),
    "land_card": ("A thick cardboard tag card flicked down onto a table: a short crisp papery snap.", 5, "hit"),
    "land_toy": ("A chunky plastic toy dropped onto a table: one short solid hollow plastic clack.", 5, "hit"),
    "cascade": ("A handful of small mixed objects tumbling and dropping down onto a table in a quick short clatter.", 5, "hit"),
    "reel_stop": ("A heavy mechanical slot reel stopping: one short, solid, satisfying soft thunk with a tiny click.", 6, "hit"),
    "can_shake": ("Shaking a spray paint can quickly twice: the metal mixing ball rattling, clack-clack, crisp.", 6, "hit"),

    # ---------------- HUD / UI ----------------
    "ui_click": ("One soft, satisfying, tactile click of a quality plastic button being pressed. Short and crisp.", 7, "click"),
    "ui_hover": ("One very soft, tiny, light tick, like a fingertip tapping a smooth plastic surface. Barely there.", 6, "click"),
    "slider_tick": ("One tiny crisp plastic detent click of a dial turning one notch.", 6, "click"),
    "swish_in": ("A short smooth soft swoosh, like a sheet of paper swiped quickly through the air, quick and clean.", 6, "whoosh"),
    "swish_out": ("A short soft downward swoosh, like a cloth swiped quickly through the air, quick and clean.", 6, "whoosh"),
    "cap_pop": ("Popping the plastic cap off a spray paint can: one crisp, satisfying plastic pop.", 6, "click"),
    "buy_confirm": ("A satisfying purchase: a crisp cash register cha-ching with a bright bell and coins.", 6, "hit"),
    "fs_tick": ("One short bright click-clack of a mechanical flip scoreboard turning one number.", 6, "click"),

    # ---------------- character foley ----------------
    "sneaker_scuff": ("A sneaker sole scuffing briefly on concrete: a short rubbery scrape.", 6, "foley"),
    "cigar_puff": ("A lit cigar's ember crackling softly as someone takes a puff: a quiet fizzing crackle of burning tobacco leaf, then a soft exhaled breath of smoke.", 5, "foley"),
    "lighter": ("A metal flip lighter opened and struck: a crisp metallic clink and a quick flint scratch with a soft flame whoosh.", 5, "foley"),
    "cash_riffle": ("Flicking quickly through a thick stack of crisp paper money bills with a thumb: a fast papery riffle.", 6, "foley"),
    "cash_flick": ("One crisp paper money bill snapped and flicked between two fingers: a short sharp papery snap.", 6, "foley"),
}


def jobs():
    for name, (prompt, takes, kind) in S.items():
        yield name, PRE + prompt + CLOSE, takes, kind
