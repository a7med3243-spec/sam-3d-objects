import pickle, sys
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import Polygon
D = pickle.load(open(sys.argv[1], 'rb'))
def polys(g): return [g] if isinstance(g, Polygon) else list(getattr(g, 'geoms', []))
def draw(ax, g, c):
    for p in polys(g):
        xs, ys = p.exterior.xy; ax.fill(xs, ys, color=c, lw=0)
        for h in p.interiors: xs, ys = h.xy; ax.fill(xs, ys, color='white', lw=0)
lim = sys.argv[3].split(',') if len(sys.argv) > 3 else None
fig, ax = plt.subplots(figsize=(9, 13) if not lim else (10, 10))
draw(ax, D['sil'], '#1b1b1b'); draw(ax, D['face'], '#d8c8ad'); draw(ax, D['logo'], '#4a3426')
ax.set_aspect('equal'); ax.grid(alpha=.35, lw=.5)
if lim:
    x0, x1, y0, y1 = map(float, lim); ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    import numpy as np; ax.set_xticks(np.arange(np.floor(x0), x1, 0.5)); ax.set_yticks(np.arange(np.floor(y0), y1, 0.5))
    ax.tick_params(labelsize=6)
fig.savefig(sys.argv[2], dpi=110, bbox_inches='tight')
