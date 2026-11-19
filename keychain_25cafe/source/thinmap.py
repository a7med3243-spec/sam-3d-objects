import pickle, sys
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import Polygon
D = pickle.load(open(sys.argv[1], 'rb')); W = float(sys.argv[3]) if len(sys.argv) > 3 else 0.42
def polys(g): return [g] if isinstance(g, Polygon) else list(getattr(g, 'geoms', []))
def draw(ax, g, c, a=1):
    for p in polys(g):
        xs, ys = p.exterior.xy; ax.fill(xs, ys, color=c, lw=0, alpha=a)
        for h in p.interiors: xs, ys = h.xy; ax.fill(xs, ys, color='#d8c8ad', lw=0)
L = D['logo']; Fm = max(polys(D['face']), key=lambda p: p.area)
thin = L.difference(L.buffer(-W/2, quad_segs=32).buffer(W/2, quad_segs=32))
gaps = L.buffer(W/2, quad_segs=32).buffer(-W/2, quad_segs=32).difference(L).intersection(Fm)
fig, ax = plt.subplots(figsize=(11, 11))
draw(ax, D['face'], '#d8c8ad'); draw(ax, L, '#4a3426')
draw(ax, thin, 'red'); draw(ax, gaps, 'cyan')
for p in polys(thin) + polys(gaps):
    if p.area > 0.003: ax.annotate(f'{p.area:.3f}', (p.centroid.x, p.centroid.y), fontsize=6, color='k')
b = L.bounds; ax.set_xlim(b[0]-.5, b[2]+.5); ax.set_ylim(b[1]-.5, b[3]+.5); ax.set_aspect('equal'); ax.grid(alpha=.3)
ax.set_title(f'red = brown thinner than {W} mm, cyan = gaps narrower than {W} mm')
fig.savefig(sys.argv[2], dpi=100, bbox_inches='tight')
