import numpy as np, pickle, sys
from PIL import Image
from scipy import ndimage
from skimage import measure
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt

IMG = sys.argv[1]; OUT = sys.argv[2]
im = np.asarray(Image.open(IMG).convert('RGB')).astype(float)
L = im.mean(2)
x0, y0, x1, y1 = 125, 515, 300, 715
S = 8
crop = Image.fromarray(L[y0:y1, x0:x1].astype(np.uint8)).resize(((x1-x0)*S, (y1-y0)*S), Image.BICUBIC)
A = ndimage.gaussian_filter(np.asarray(crop).astype(float), 3.0)
cs = measure.find_contours(A, 88.0)   # dark (logo) is below level

def unwrap(px, py):
    # px,py in original-image pixel coords -> flattened cylinder coords (pixels)
    R = 115.0 - 0.13 * (py - 505.0)
    xc = 211.7 + (py - 505.0) * (1.6 / 273)
    u = R * np.arcsin(np.clip((px - xc) / R, -0.999, 0.999))
    return u, py

polys = []
for c in cs:
    if len(c) < 20: continue
    py = c[:, 0] / S + y0; px = c[:, 1] / S + x0
    u, v = unwrap(px, py)
    p = Polygon(np.c_[u, -v])
    if not p.is_valid: p = p.buffer(0)
    if p.area < 0.5: continue
    polys.append(p)
# even-odd composition: sort by area, xor
polys.sort(key=lambda p: -p.area)
shape = Polygon()
for p in polys: shape = shape.symmetric_difference(p)
print('pieces', len(polys), 'area', shape.area, 'bounds', shape.bounds)
pickle.dump(shape, open(OUT + '.pkl', 'wb'))
fig, ax = plt.subplots(figsize=(8, 9))
geoms = shape.geoms if hasattr(shape, 'geoms') else [shape]
for g in geoms:
    xs, ys = g.exterior.xy; ax.fill(xs, ys, color='#4a3426')
    for h in g.interiors: xs, ys = h.xy; ax.fill(xs, ys, color='white')
ax.set_aspect('equal'); ax.grid(alpha=.3); fig.savefig(OUT + '.png', dpi=110, bbox_inches='tight')
