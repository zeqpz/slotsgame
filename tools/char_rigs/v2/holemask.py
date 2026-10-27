"""holemask.py <who> <out.png> [film_scale=.5] [cy]: the master's own see-through enclosed space (between the
legs), mapped into film frames (1000x1000, the skeleton point (0, cy) at the centre), dilated 14 px"""
import sys, numpy as np, cv2
from PIL import Image
from scipy import ndimage
sys.path.insert(0, '.')
import pk, rigkit as rk
who, out = sys.argv[1], sys.argv[2]
S = float(sys.argv[3]) if len(sys.argv) > 3 else .5
cy = float(sys.argv[4]) if len(sys.argv) > 4 else (740 if who == 'skull' else 810)
F = rk.Frame(.97, 14, 730) if who == 'skull' else rk.Frame(.864, 5, 800)
M = pk.src(who, 'master'); fig = M[..., 3] > 127
holes = ndimage.binary_fill_holes(fig) & ~fig
holes = ndimage.binary_opening(holes, iterations=2)
print('master hole px', int(holes.sum()))
# master px -> film px: skeleton u = F.u(px); film = (500 + u.x*S, 500 - (u.y - cy)*S)
A = np.array([[1 / F.s * S, 0, 500 + (-512 / F.s + F.cx) * S], [0, 1 / F.s * S, 500 - (F.cy + 768 / F.s - cy) * S]], np.float32)
m = cv2.warpAffine(holes.astype(np.uint8) * 255, A, (1000, 1000), flags=cv2.INTER_NEAREST)
m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (29, 29)))
Image.fromarray(m).save(out); print(out, int((m > 0).sum()))
ys, xs = np.nonzero(holes)
pts = np.stack([(xs - 512) / F.s + F.cx, F.cy - (ys - 768) / F.s], 1)
np.save(out.replace('.png', '.npy'), pts.astype(np.float32)); print('points', len(pts))
