import pickle, sys, numpy as np, trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from shapely.geometry import Polygon
D = pickle.load(open(sys.argv[1], 'rb')); dist = sys.argv[2]; out = sys.argv[3]
plt.rcParams['font.family'] = 'Inter'
C = dict(black='#1e1e1e', beige='#d3c2a4', brown='#4b3324', dim='#b5452b', txt='#222')
def polys(g): return [g] if isinstance(g, Polygon) else list(getattr(g, 'geoms', []))
def draw(ax, g, c, hole='white'):
    for p in polys(g):
        xs, ys = p.exterior.xy; ax.fill(xs, ys, color=c, lw=0)
        for h in p.interiors: xs, ys = h.xy; ax.fill(xs, ys, color=hole, lw=0)
def dim(ax, a, b, label, off=(0, 0), rot=0, fs=11):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle='<|-|>', mutation_scale=9, color=C['dim'], lw=1.1))
    m = ((a[0] + b[0]) / 2 + off[0], (a[1] + b[1]) / 2 + off[1])
    ax.text(*m, label, color=C['dim'], fontsize=fs, ha='center', va='center', rotation=rot, fontweight='bold',
            bbox=dict(fc='white', ec='none', pad=1.5))
fig = plt.figure(figsize=(12, 9.2), facecolor='white')
ax = fig.add_axes([0.03, 0.06, 0.52, 0.86]); ax.set_aspect('equal'); ax.axis('off')
draw(ax, D['sil'], C['black']); draw(ax, D['face'], C['beige']); draw(ax, D['logo'], C['brown'], hole=C['beige'])
b = D['sil'].bounds
ax.plot([b[0], b[0]], [b[1] - 0.5, b[1] - 4.5], color='#999', lw=0.6); ax.plot([b[2], b[2]], [b[1] - 0.5, b[1] - 4.5], color='#999', lw=0.6)
dim(ax, (b[0], b[1] - 3.5), (b[2], b[1] - 3.5), f'{b[2]-b[0]:.1f} mm')
ax.plot([b[2] + 0.5, b[2] + 6], [b[3], b[3]], color='#999', lw=0.6); ax.plot([b[2] + 0.5, b[2] + 6], [b[1], b[1]], color='#999', lw=0.6)
dim(ax, (b[2] + 5, b[1]), (b[2] + 5, b[3]), f'{b[3]-b[1]:.1f} mm', rot=90)
H = D['P']['H']
ax.plot([b[0] - 0.5, b[0] - 6], [H, H], color='#999', lw=0.6); ax.plot([b[0] - 0.5, b[0] - 6], [0, 0], color='#999', lw=0.6)
dim(ax, (b[0] - 5, 0), (b[0] - 5, H), f'cup {H:.0f} mm', rot=90)
hc = (0, H + D['P']['ring_dy']); hr = D['P']['hole_r']
ax.annotate(f'key-ring hole Ø{2*hr:.1f} mm\nwall {D["P"]["ring_r"]-hr:.2f} mm', xy=(hc[0] + hr * 0.7, hc[1] + hr * 0.7), xytext=(hc[0] + 9, hc[1] + 5),
            color=C['dim'], fontsize=10, fontweight='bold', arrowprops=dict(arrowstyle='->', color=C['dim']))
ax.set_xlim(b[0] - 9, b[2] + 12); ax.set_ylim(b[1] - 6, b[3] + 8)
ax.set_title('Front view  (black bar = 10 mm)', fontsize=12, color=C['txt'], loc='left')
ax.plot([b[0], b[0] + 10], [b[1] - 5.6, b[1] - 5.6], color='k', lw=2); ax.text(b[0] + 5, b[1] - 5.2, '10 mm', ha='center', fontsize=8)
# side section through the centre line (x = 0), Z exaggerated x3
bx = fig.add_axes([0.60, 0.40, 0.38, 0.52]); bx.axis('off')
EX = 3.0
for tag, col in (('1_black', C['black']), ('2_beige', C['beige']), ('3_brown', C['brown'])):
    m = trimesh.load(f'{dist}_{tag}.stl')
    for x0 in (0.0, -2.6):
        sec = m.section(plane_origin=[x0, 0, 0], plane_normal=[1, 0, 0])
        if sec is None: continue
        for path in sec.discrete:
            yz = np.asarray(path)[:, 1:3]
            off = 0 if x0 == 0 else 14
            bx.fill(yz[:, 1] * EX + off, yz[:, 0], color=col, lw=0)
bx.set_aspect('equal'); bx.set_xlim(-2, 32); bx.set_ylim(-2, 50)
bx.text(7, 49, 'Cross-sections (thickness ×3)', fontsize=11, color=C['txt'], ha='center')
bx.text(7.2, -1.6, 'centre line', fontsize=8, ha='center', color='#555'); bx.text(21, -1.6, 'through logo', fontsize=8, ha='center', color='#555')
tx = fig.add_axes([0.60, 0.04, 0.38, 0.34]); tx.axis('off')
rows = [('Black', '0 – 2.4 mm', 'back, outline, lid (to 4.8), loop (3.2)'),
        ('Beige', '2.4 – 4.0 mm', 'cup face, 1.6 mm thick'),
        ('Dark brown', '4.0 – 4.6 mm', 'logo, raised 0.6 mm'),
        ('', '', ''),
        ('Total', '4.8 mm', 'thickest point (lid rim)'),
        ('Layer height', '0.20 mm', 'all colour borders on 0.2 mm steps'),
        ('Colour changes', '≈ 12 / plate', 'same for 1 or 50 keychains'),
        ('Supports', 'none', 'prints face-up, flat back')]
for i, (a, b_, c_) in enumerate(rows):
    y = 1 - i * 0.12
    if a in ('Black', 'Beige', 'Dark brown'):
        tx.add_patch(plt.Rectangle((0, y - 0.045), 0.05, 0.08, color={'Black': C['black'], 'Beige': C['beige'], 'Dark brown': C['brown']}[a], transform=tx.transAxes))
    tx.text(0.07, y, a, fontsize=10.5, fontweight='bold', va='center', transform=tx.transAxes)
    tx.text(0.38, y, b_, fontsize=10.5, va='center', transform=tx.transAxes)
    tx.text(0.62, y, c_, fontsize=8.8, va='center', color='#555', transform=tx.transAxes, wrap=True)
fig.suptitle('25 Percent Cafe – cup keychain   (Bambu Lab A2L Combo, 0.4 mm nozzle)', fontsize=14, fontweight='bold', x=0.03, ha='left', y=0.985)
fig.savefig(out, dpi=170)
