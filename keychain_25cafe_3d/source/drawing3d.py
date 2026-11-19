import sys, json, numpy as np, trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from shapely.geometry import Polygon
base, rep_f, ver_f, out = sys.argv[1:5]
rep = json.load(open(rep_f)); ver = json.load(open(ver_f))
plt.rcParams['font.family'] = 'Inter'
C = {'1_black': '#1e1e1e', '2_beige': '#d3c2a4', '3_brown': '#4b3324', '4_white': '#ece8df'}
fig = plt.figure(figsize=(12, 9.2), facecolor='white')
ax = fig.add_axes([0.02, 0.05, 0.56, 0.86]); ax.set_aspect('equal'); ax.axis('off')
Hc0 = rep['H']
for tag, col in C.items():
    m = trimesh.load(f'{base}_{tag}.stl')
    sec = m.section(plane_origin=[0, 0, 0], plane_normal=[0, 1, 0])
    if sec is None: continue
    for path in sec.discrete:
        p = np.asarray(path)
        if tag == '1_black' and p[:, 2].min() > Hc0 - 0.6: continue          # loop crown: drawn from the other section below
        ax.fill(p[:, 0], p[:, 2], color=col, lw=0.3, ec='#999' if tag == '4_white' else col)
# loop shown face-on (section across it), so the teardrop hole is visible
m = trimesh.load(f'{base}_1_black.stl')
sec = m.section(plane_origin=[0, 0, 0], plane_normal=[1, 0, 0])
from shapely.geometry import box as _box
rings = sorted([Polygon(np.asarray(pth)[:, 1:3]).buffer(0) for pth in sec.discrete], key=lambda q: -q.area)
full = Polygon()
for r_ in rings: full = full.symmetric_difference(r_)
for poly in [full]:
    g = poly.intersection(_box(-50, Hc0 - 0.6, 50, 99))
    for q in ([g] if g.geom_type == 'Polygon' else list(getattr(g, 'geoms', []))):
        if q.is_empty: continue
        xs, ys = q.exterior.xy; ax.fill(xs, ys, color='#1e1e1e', lw=0)
        for h in q.interiors: xs, ys = h.xy; ax.fill(xs, ys, color='white', lw=0)
dimc = '#b5452b'
def dim(a, b, label, rot=0, off=(0, 0)):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle='<|-|>', mutation_scale=9, color=dimc, lw=1.1))
    ax.text((a[0] + b[0]) / 2 + off[0], (a[1] + b[1]) / 2 + off[1], label, color=dimc, fontsize=11, ha='center', va='center',
            rotation=rot, fontweight='bold', bbox=dict(fc='white', ec='none', pad=1.5))
Ht, Hc, D = rep['height_total'], rep['H'], rep['max_diameter']
dim((18, 0), (18, Ht), f'{Ht:.1f} mm', rot=90); ax.plot([13.5, 19], [Ht, Ht], color='#aaa', lw=.6); ax.plot([9, 19], [0, 0], color='#aaa', lw=.6)
dim((-17, 0), (-17, Hc), f'cup {Hc:.0f} mm', rot=90); ax.plot([-17.5, -10], [Hc, Hc], color='#aaa', lw=.6)
dim((-D / 2, 33.6), (D / 2, 33.6), '')
ax.text(0, 33.6 + 0.0, f'Ø {D:.1f} mm', color=dimc, fontsize=10.5, ha='center', va='center', fontweight='bold', bbox=dict(fc='#1e1e1e', ec='none', pad=1.2), zorder=5)
ax.annotate('key-ring hole 4.5 mm\n(teardrop: prints without support)', xy=(1.2, Hc + 2.6), xytext=(7, Hc + 6.5), color=dimc, fontsize=9.5,
            fontweight='bold', arrowprops=dict(arrowstyle='->', color=dimc))
ax.annotate('logo / text inlay\n0.9 mm deep, flush', xy=(-10.2, 15), xytext=(-27, 8), color=dimc, fontsize=9.5, fontweight='bold',
            arrowprops=dict(arrowstyle='->', color=dimc))
ax.set_xlim(-30, 26); ax.set_ylim(-3, Ht + 7)
ax.set_title('Cross-section through the logo (true scale)', fontsize=12, loc='left')
ax.plot([-10, 0], [-2, -2], color='k', lw=2); ax.text(-5, -1.3, '10 mm', ha='center', fontsize=8)
tx = fig.add_axes([0.6, 0.05, 0.38, 0.86]); tx.axis('off')
g = {k: v['grams_PLA_100pct'] for k, v in ver['parts'].items()}
rows = [('Black', 'lid + loop', '#1e1e1e'), ('Beige', 'cup', '#d3c2a4'), ('Dark brown', 'logo + back text', '#4b3324'),
        ('White', 'rolled bottom ring\n(or use beige)', '#ece8df')]
y = 0.95
tx.text(0, y, 'Colours (AMS Lite slots)', fontsize=12, fontweight='bold', transform=tx.transAxes); y -= 0.07
for i, (a, b, c) in enumerate(rows):
    tx.add_patch(plt.Rectangle((0, y - 0.022), 0.06, 0.045, color=c, ec='#999', transform=tx.transAxes))
    tx.text(0.09, y, f'{i + 1}  {a}', fontsize=10.5, fontweight='bold', va='center', transform=tx.transAxes)
    tx.text(0.45, y, b, fontsize=9.5, va='center', color='#444', transform=tx.transAxes); y -= 0.075
y -= 0.03
spec = [('Size', f'Ø {D:.1f} × {Ht:.1f} mm'), ('Weight', '≈ 6–8 g PLA (15 % infill)'), ('Print', 'upright, one piece, no supports'),
        ('Layer height', '0.12 mm best · 0.20 mm faster'), ('Colour changes', f"{ver['filament_changes_per_plate']} per plate at 0.12 mm"),
        ('', 'same for 1 or 36 cups'), ('Per plate (A2L)', '36 recommended (max ≈ 90)')]
tx.text(0, y, 'Print facts', fontsize=12, fontweight='bold', transform=tx.transAxes); y -= 0.065
for a, b in spec:
    tx.text(0, y, a, fontsize=10.5, fontweight='bold', va='center', transform=tx.transAxes)
    tx.text(0.4, y, b, fontsize=10, va='center', transform=tx.transAxes); y -= 0.058
fig.suptitle('25 Percent Cafe – 3D mini cup keychain   (Bambu Lab A2L Combo, 0.4 mm nozzle)', fontsize=14, fontweight='bold', x=0.02, ha='left', y=0.985)
fig.savefig(out, dpi=170)
