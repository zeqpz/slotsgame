# L1 - Spray can: what Blender's cut changes from the rig recipe (tools/icon_rigs/recipes/L1.py).
# The can sprays: its cap's top is pressed down (it squashes about the nozzle, so the jet never leaves it), the jet
# stays put on the can and the painted cloud billows from where the jet runs into it (anim_L1.py weights its mesh).
# So each piece must own what moves with it, cut again from the new art (the recipe's masks were read off the old
# drawing):
#   jet    the cone from the cloud to the nozzle and the white, speckled border round it - the recipe split that
#          border between the can and the cap, and the cap's top now squashes
#   cap    the cap itself with its whole outline and cyan rim (the recipe's mask clipped the new art's rim) and its
#          own border; the recipe's blur fill under it is wiped from the can
#   cloud  the full cone where the jet's end fades over it (the recipe split them along a soft ramp, which left a
#          see-through seam where the two half-transparent edges overlap)
# No clean plate is needed: nothing that moves uncovers anything. The "art" plate is the icon itself through
# tools/blender/plate.py --fit-only (a copy of art/icons-src/L1.png as art/blender/plates/L1_art_raw.png; no
# generation, the fit is the identity), so FILLS put the art's own pixels where they belong.
import os, sys
import numpy as np
from PIL import Image
from scipy import ndimage
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_a = np.asarray(Image.open(os.path.join(ROOT, "art", "icons-src", "L1.png")).convert("RGBA")).astype(np.float32) / 255
_rgb, _al = _a[..., :3], _a[..., 3]
_yy, _xx = np.mgrid[0:1000, 0:1000]
_white = (_rgb.min(-1) > .80) & (_rgb.max(-1) - _rgb.min(-1) < .12)
_solid = (_al > .5) & ~_white                                  # the drawing, not its sticker border
_green = (_rgb[..., 1] > .45) & (_rgb[..., 0] < .65) & (_rgb[..., 2] < .55) & (_al > .5)
_dark = (_rgb.max(-1) < .32) & (_al > .5)


def _poly(pts):
    from PIL import ImageDraw
    im = Image.new("L", (1000, 1000), 0)
    ImageDraw.Draw(im).polygon(pts, fill=255)
    return np.asarray(im) > 127


# the cone: green and its ink lines inside the recipe's jet outline (grown a little), from where it runs into the
# cloud to the nozzle's hole
_cone_poly = ndimage.binary_dilation(_poly([(455, 123), (676, 144), (676, 174), (455, 240)]), iterations=4)
_cone_green = _cone_poly & _green & (_xx >= 455) & (_xx <= 652)
_cone_green = ndimage.binary_opening(_cone_green, iterations=1)
# the cone: its green and the ink lines right against it (not the cap's lines the cone passes over)
_d_green = ndimage.distance_transform_edt(~_cone_green)
# (its ink lines are ~10 px thick; where the cone passes over the cap only the ink right against it, not the cap's)
CONE = _cone_green | (_cone_poly & _dark & (_d_green <= np.where(_xx < 585, 13, 6)) & (_xx >= 455) & (_xx <= 652))
CONE = ndimage.binary_closing(CONE, iterations=1) & (_xx >= 455)
# the cap: everything drawn inside the recipe's cap outline, grown to take in the new art's rim - not the cone,
# not the green spray speckles round it and not the can's green dome under it
_cap_poly = _poly([(562, 96), (598, 60), (812, 68), (802, 142), (762, 302), (700, 308), (640, 304), (612, 276)])
CAP = ndimage.binary_dilation(_cap_poly, iterations=8) & _solid & ~CONE & ~_green
CAP = ndimage.binary_fill_holes(ndimage.binary_closing(CAP, iterations=2)) & ~CONE & ~(_green & (_yy > 262))
lab, n = ndimage.label(CAP)
CAP = lab == 1 + np.argmax(ndimage.sum(CAP, lab, range(1, n + 1)))          # one piece: no stray bits
# the rest of the drawing near the cap and the cone: the can's dome and top ring, the cloud - big pieces (the speckles in
# the jet's border and their green haloes run together into small blobs: they belong to the jet's border)
_other = _solid & ~CAP & ~CONE
lab, n = ndimage.label(_other)
_other = np.isin(lab, 1 + np.nonzero(ndimage.sum(_other, lab, range(1, n + 1)) >= 2000)[0])
_d_cap = ndimage.distance_transform_edt(~CAP)
_d_cone = ndimage.distance_transform_edt(~CONE)
_d_other = ndimage.distance_transform_edt(~_other)
_border = (_al > .01) & ~CONE & ~CAP & ~_other
# the jet's white border, speckles and all: border pixels nearer the cone than anything else, right of the cloud
JET_BORDER = _border & (_d_cone <= 40) & (_d_cone < _d_cap) & (_d_cone < _d_other) & (_xx >= 470) & (_xx <= 660)
JET_BORDER = ndimage.binary_fill_holes(JET_BORDER | CONE) & ~CONE & _border
# the cap's own border: border pixels nearer the cap than anything else
CAP_BORDER = _border & (_d_cap <= 40) & (_d_cap <= _d_cone) & (_d_cap < _d_other)
JET = CONE | JET_BORDER
CAPR = CAP | CAP_BORDER
# under the jet's soft end the cloud keeps the whole cone (the jet lies over it there)
UNDER_JET = CONE & (_xx <= 525)

# what stays the can's (and the cloud's): its drawing and the border nearer it than the cap or the cone
CAN_OWN = _other | (_border & (_d_other <= _d_cap) & (_d_other <= _d_cone))
_grow = lambda m, k: ndimage.binary_dilation(m, iterations=k)

# The cloud: the recipe cut it off at x 480 where it meets the can, so it had no sticker border of its own there and
# a sliver opened when it swelled away from the can. It gets a whole white border on that side (made here like the
# art's own: white, a soft dark outer edge -> art/blender/plates/L1_cloudrim.png), lying under the can at rest.
_cloud_poly = _poly([(146, 92), (168, 48), (250, 32), (335, 48), (412, 88), (474, 196), (486, 300), (424, 344), (364, 354),
                     (318, 372), (306, 428), (240, 440), (164, 424), (136, 330), (140, 250)])
CLOUD_CORE = ndimage.binary_fill_holes(ndimage.binary_dilation(_cloud_poly, iterations=6) & _solid & ~CONE & ~CAP)
lab, n = ndimage.label(CLOUD_CORE)
CLOUD_CORE = lab == 1 + np.argmax(ndimage.sum(CLOUD_CORE, lab, range(1, n + 1)))
_dcc = ndimage.distance_transform_edt(~CLOUD_CORE)
_zone = (_xx >= 440) & (_yy >= 250) & (_yy <= 450)
_inside = ndimage.distance_transform_edt(_al > .5) > 8
# the band the cloud shares with the can there is two borders wide: the cloud's white reaches 40 px out, under the
# can (behind it at rest), so the two always overlap as the cloud swells and sways
_cut_off = _poly([(480, 60), (1000, 60), (1000, 1000), (300, 1000), (300, 470), (480, 400)])
CLOUD_RIM = _zone & (_dcc > 0) & (_dcc <= 40) & ((_cut_off & (ndimage.distance_transform_edt(_al > .5) > 1)) | (_inside & _white & (_al > .98)))
# the bit of the can's outline the recipe's cloud mask took: the can's own again (drawn in front, so the cloud's
# white behind it never shows at rest)
CAN_SLIVER = _zone & _solid & ~CLOUD_CORE & ~CONE & ~CAP & (_dcc > 24) & (_xx >= 460)     # (not the cloud's own outline)


def _cloudrim():
    out = np.zeros((1000, 1000, 4), np.float32)
    out[..., :3] = .99
    out[..., 3] = np.clip((41 - _dcc) / 3, 0, 1) * (_dcc > 0)
    path = os.path.join(ROOT, "art", "blender", "plates", "L1_cloudrim.png")
    Image.fromarray((np.clip(out, 0, 1) * 255).round().astype(np.uint8), "RGBA").save(path)


_cloudrim()

FILLS = [   # each region grown 2 px (its soft edge falls past it, onto the same art pixels in the part behind)
    {"part": "jet", "region": (_grow(JET, 2) & ~CAPR).astype(np.float32), "plate": "art"},
    {"part": "cap", "region": (_grow(CAPR, 2) & ~JET).astype(np.float32), "plate": "art"},
    {"part": "cloud", "region": UNDER_JET.astype(np.float32), "plate": "art"},
    {"part": "cloud", "region": (CLOUD_RIM & ~UNDER_JET).astype(np.float32), "plate": "cloudrim"},
    {"part": "can", "region": ndimage.binary_dilation(CAN_SLIVER, iterations=2).astype(np.float32), "plate": "art"},
]
CLEAR = [
    # the recipe's blur under the cap and round the jet, all of it (a remnant would ghost when the cap squashes)
    {"part": "can", "region": (_grow(CAPR | JET, 4) & ~_grow(CAN_OWN & ~_grow(CAPR | JET, 1), 1)).astype(np.float32)},
    {"part": "cap", "region": (_grow(JET & ~CAPR, 1) & ~CAPR).astype(np.float32)},
    {"part": "jet", "region": (~_grow(JET, 3)).astype(np.float32)},
]
