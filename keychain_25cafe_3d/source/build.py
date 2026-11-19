"""25 Percent Cafe - takeaway cup keychain (3-colour, AMS friendly).

All XY units mm, cup bottom centre at origin, Y up. Z = print direction (face up).
Colour stacking (0.2 mm layers):
  black : 0 -> 4.0 (outline, back, lid up to 4.8, ring 3.2)
  beige : 2.4 -> 4.0 (cup face, inlaid into black frame)
  brown : 4.0 -> 4.6 (logo, raised 0.6 mm on the beige face)
"""
import json, os, pickle, sys
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, box
from shapely.ops import unary_union
from shapely import affinity
from manifold3d import Manifold, CrossSection, FillRule
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties

HERE = os.path.dirname(os.path.abspath(__file__))
TRACE = sys.argv[1]
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)

P = dict(
    H=float(os.environ.get('CUP_H', 40.0)),  # cup height, lid top -> cup bottom
    border=0.9,        # black outline around beige face
    band_line=0.7,     # black line above rolled bottom band
    slash_w=0.6, halo=0.45, crease=0.45, small_bean_scale=1.35,
    text_gap=0.5, text_cap=2.4, letter_gap=0.62, text_below=1.0, slash_top_extend=1.9, small_bean=(3.0, 1.75), small_bean_scale_max=0.9, sb_halo=0.42, straighten=0.04, smooth_sigma=0.14,
    font='/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf', k_max=1.0, logo_cy_frac=0.53,
    logo_margin=1.0,   # min distance logo -> black border
    z_face0=2.4, z_face=4.0, z_logo=4.6, z_lip=4.2, z_cap=4.4,
    z_rim_lo=4.6, z_rim=4.8, z_ring=3.2,
    ring_r=5.0, hole_r=2.25, ring_dy=2.6,
)
H = P['H']; s = H / 351.0          # photo pixels -> mm (cup = 351 px tall)
Q = 32                              # arc resolution (segments per quarter circle)

def clean(g, tol=0.01):
    g = g.buffer(0)
    return g.simplify(tol, preserve_topology=True)

def polys(g):
    if g.is_empty: return []
    if isinstance(g, Polygon): return [g]
    return [p for p in getattr(g, 'geoms', []) if isinstance(p, Polygon) and not p.is_empty]

def rround(g, r):          # round convex corners
    return g.buffer(-r, quad_segs=Q).buffer(r, quad_segs=Q)

def fillet(g, r):          # round concave corners
    return g.buffer(r, quad_segs=Q).buffer(-r, quad_segs=Q)

# ---------------------------------------------------------------- cup outline
body = rround(Polygon([(-78.5*s, 0), (78.5*s, 0), (115*s, 273*s), (-115*s, 273*s)]), 1.2)
lip = box(-117*s, 272*s, 117*s, 280.5*s)
rim = rround(box(-125.7*s, 280*s, 125.7*s, 310*s), 1.25)
rim_split = 280*s + 0.42*(30*s)
cap = rround(Polygon([(-108*s, 308*s), (108*s, 308*s), (99*s, 351*s), (-99*s, 351*s)]), 1.0)
ring_c = (0.0, H + P['ring_dy'])
ring = Point(ring_c).buffer(P['ring_r'], quad_segs=Q)
hole = Point(ring_c).buffer(P['hole_r'], quad_segs=Q)
cup = unary_union([body, lip, rim, cap])
sil = unary_union([fillet(cup, 0.8), fillet(unary_union([ring, cap]), 1.6)])
sil = clean(sil.difference(hole), 0.005)
ring_zone = clean(sil.difference(fillet(cup, 0.8)).buffer(0.01).intersection(box(-50, H - 2, 50, H + 20)))
ring_zone = unary_union([p for p in polys(ring_zone) if p.area > 1])

face_all = body.buffer(-P['border'], quad_segs=Q)
band_y = 26*s
face = clean(face_all.difference(box(-50, band_y - P['band_line']/2, 50, band_y + P['band_line']/2)))
face_main = max(polys(face), key=lambda p: p.area)

# ---------------------------------------------------------------- logo
if TRACE.endswith('.wkt'):
    from shapely import wkt as _wkt
    TR = _wkt.loads(open(TRACE).read())
else:
    TR = pickle.load(open(TRACE, 'rb'))
pcs = sorted(polys(TR), key=lambda g: -g.area)
p5, p2, bA, bB, bS = pcs[:5]
assert p5.bounds[2] > 50 and p2.bounds[0] < -80, 'unexpected trace order'

# separate slash from the "5" (px space)
opened = p5.buffer(-2.5).buffer(2.5)
thin = max(polys(p5.difference(opened)), key=lambda g: g.minimum_rotated_rectangle.length)
xy = np.asarray(thin.exterior.coords)
mu = xy.mean(0); _, _, vt = np.linalg.svd(xy - mu); d = vt[0]
if d[1] > 0: d = -d                          # trace y is negative-down: make d point up-right in image
t = (xy - mu) @ d
p_lo, p_hi = mu + d*t.min(), mu + d*t.max()
if p_lo[1] > p_hi[1]: p_lo, p_hi = p_hi, p_lo
dd = (p_hi - p_lo) / np.linalg.norm(p_hi - p_lo)
block5 = unary_union([g for g in polys(p5.difference(LineString([p_lo, p_hi]).buffer(3.0, cap_style=2))) if g.area > 50])
# the photo blur fused half of the small bean onto the "5": a light opening splits it off, then drop it
block5 = unary_union([g for g in polys(block5.buffer(-1.5).buffer(1.5)) if g.area > 300])
# the slash continues up the narrow channel between the two parts of the "5" (blurred in the photo)
q = p_hi.copy(); ext_px = 0
for i in range(400):
    q2 = q + dd*0.5; pt = Point(q2)
    if block5.contains(pt) or pt.distance(block5) > 4.0: break
    q = q2; ext_px += 0.5
p_hi = q
print(f'slash extended {ext_px:.1f} px up the channel')
slash_px = LineString([p_lo, p_hi])
big_bean = fillet(unary_union([bA, bB]), 3.0)
big_crease = max(polys(big_bean.difference(unary_union([bA, bB]))), key=lambda g: g.area)
small_bean = fillet(bS, 2.0)

px2mm = [s, 0, 0, s, 0, 778*s]
T = lambda g: affinity.affine_transform(g, px2mm)
G = dict(block5=T(block5), block2=T(p2), slash=T(slash_px), bean=T(big_bean), crease=T(big_crease), sbean=T(small_bean))
rough = unary_union([G['block5'], G['block2'], G['bean'], G['sbean'], G['slash'].buffer(0.3)])
_rb = rough.bounds; _cx = (_rb[0] + _rb[2]) / 2
rough = unary_union([rough, box(_cx - 5.2, _rb[1] - P['text_cap'] - P['text_below'], _cx + 5.2, _rb[1])])  # room for CAFE

# fit: biggest logo (k <= k_max) whose centre sits near the visual centre of the cup face
target_cy = P['logo_cy_frac'] * 273*s
best = None
for k in np.arange(P['k_max'], 0.60, -0.01):
    sc = affinity.scale(rough, k, k, origin=(0, 0)); bx = sc.bounds
    for cyc in np.arange(target_cy - 3, target_cy + 3.01, 0.1):
        for dx in np.arange(-1.5, 1.51, 0.1):
            cx = -(bx[0] + bx[2]) / 2 + dx; cy = cyc - (bx[1] + bx[3]) / 2
            cand = affinity.translate(sc, cx, cy)
            if face_main.buffer(-P['logo_margin']).contains(cand):
                score = abs(dx) * 0.3 + abs(cyc - target_cy)
                if best is None or score < best[0]: best = (score, k, cx, cy)
    if best and best[0] <= 1.0: break
    best = None
_, K, CX, CY = best
print(f'logo scale k={K:.2f} offset=({CX:.2f},{CY:.2f})')
F = lambda g: affinity.translate(affinity.scale(g, K, K, origin=(0, 0)), CX, CY)
for k_ in G: G[k_] = F(G[k_])
# straighten the photo-trace wobble: Douglas-Peucker at 0.07 mm (well under one 0.4 mm extrusion line)
from scipy.ndimage import gaussian_filter1d
def smooth_ring(xy, dp, sigma, step=0.02):
    ln = LineString(xy).simplify(dp)
    n = max(int(ln.length / step), 16)
    pts = np.array([ln.interpolate(t).coords[0] for t in np.linspace(0, ln.length, n, endpoint=False)])
    sg = sigma / (ln.length / n)
    return np.c_[gaussian_filter1d(pts[:, 0], sg, mode='wrap'), gaussian_filter1d(pts[:, 1], sg, mode='wrap')]
def smooth_poly(g, dp, sigma):
    out = []
    for p in polys(g):
        ext_ = smooth_ring(np.asarray(p.exterior.coords), dp, sigma)
        holes = [smooth_ring(np.asarray(h.coords), dp, sigma) for h in p.interiors]
        out.append(Polygon(ext_, holes).buffer(0))
    return unary_union(out).simplify(0.004)
for k_ in ('block2', 'block5', 'bean'):
    G[k_] = smooth_poly(G[k_], P['straighten'], P['smooth_sigma'])
G['crease'] = smooth_poly(G['crease'], 0.02, 0.08)
sl = G['slash']
c = np.asarray(sl.coords); p_bot0, p_top = (c[0], c[1]) if c[0][1] < c[1][1] else (c[1], c[0])
u_sl = (p_top - p_bot0) / np.linalg.norm(p_top - p_bot0)
p_top = p_top + u_sl * P['slash_top_extend']
slash_body = lambda a, b, extra=0: LineString([a, b]).buffer(P['slash_w']/2 + extra, cap_style=2, quad_segs=Q)

# big bean: traced outline, crease widened to >= crease width, slivers removed
bean_out = rround(G['bean'], 0.3)
cw = 2 * G['crease'].area / max(G['crease'].length, 1e-6)
bean = bean_out.difference(G['crease'].buffer(max(0, (P['crease'] - cw) / 2) + 0.02, quad_segs=Q))
bean = rround(bean, 0.21)
# small bean: clean parametric bean (ellipse + S-crease) sized for a 0.4 mm nozzle,
# placed where the traced one was, nudged clear of the slash and the "5"
sb0 = G['sbean']; c_tr = np.array(sb0.centroid.coords[0])
mrr = np.asarray(sb0.minimum_rotated_rectangle.exterior.coords)[:4]
e = [mrr[1]-mrr[0], mrr[2]-mrr[1]]; ax_ = max(e, key=np.linalg.norm); ax_ = ax_ / np.linalg.norm(ax_)
if ax_[0] < 0: ax_ = -ax_
ang = np.degrees(np.arctan2(ax_[1], ax_[0])); nrm = np.array([-ax_[1], ax_[0]])
def small_bean_at(cc, Lb, Wb):
    ell = affinity.translate(affinity.rotate(affinity.scale(Point(0, 0).buffer(1, quad_segs=Q), Lb/2, Wb/2), ang), *cc)
    tt = np.linspace(-0.22, 0.22, 60)        # crease stops short of the tips -> bean stays one solid piece
    pts = [cc + ax_*ti*Lb + nrm*0.06*Wb*np.sin(np.pi*ti/0.22) for ti in tt]
    return ell, ell.difference(LineString(pts).buffer(P['crease']/2, quad_segs=Q))
_v = c_tr - p_bot0; side = np.sign(u_sl[0]*_v[1] - u_sl[1]*_v[0]) or 1.0
away = np.array([-u_sl[1], u_sl[0]]) * side
SB = slash_body(p_bot0, p_top); B5 = G['block5']
best_sb = None
for scl in np.arange(P['small_bean_scale_max'], 0.79, -0.02):
    Lb, Wb = P['small_bean'][0]*scl, P['small_bean'][1]*scl
    for off in np.arange(-2.0, 2.01, 0.05):
        for along in np.arange(-3.5, 1.01, 0.1):
            cc = c_tr + away*off + u_sl*along
            o, _ = small_bean_at(cc, Lb, Wb)
            if o.distance(SB) >= P['sb_halo'] and o.distance(B5) >= P['sb_halo'] and o.distance(bean_out) >= P['halo']:
                sc_ = abs(off) + abs(along)
                if best_sb is None or sc_ < best_sb[0]: best_sb = (sc_, cc, Lb, Wb)
    if best_sb: break
_, c0, Lb, Wb = best_sb
sb_out, sbean = small_bean_at(c0, Lb, Wb)
print(f'small bean {Lb:.2f} x {Wb:.2f} mm')
beans = unary_union([bean, sbean])

blocks = unary_union([G['block2'], G['block5']])
blocks = blocks.difference(unary_union([bean_out.buffer(P['halo'], quad_segs=Q), sb_out.buffer(P['sb_halo'], quad_segs=Q)]))
blocks = blocks.difference(slash_body(p_bot0, p_top, P['halo']))
blocks = rround(blocks, 0.22)
beans = beans.difference(slash_body(p_bot0, p_top, P['halo']))

# CAFE text (Inter ExtraBold, per-letter spacing so every gap >= letter_gap),
# right-aligned to the bowl of the "5" on its baseline; slash foot trimmed if it would touch the text.
fp = FontProperties(fname=P['font'])
def glyph(ch):
    tp = TextPath((0, 0), ch, size=10, prop=fp)
    rings_, cur = [], []
    for bz, code in tp.iter_bezier():           # evaluate font curves finely (smooth "C")
        if code == 1:                           # MOVETO starts a new contour
            if len(cur) > 2: rings_.append(cur)
            cur = [tuple(bz.control_points[0])]; continue
        n = 1 if bz.degree <= 1 else 24
        cur += [tuple(pt) for pt in bz(np.linspace(0, 1, n + 1)[1:])]
    if len(cur) > 2: rings_.append(cur)
    rr = sorted([Polygon(r).buffer(0) for r in rings_], key=lambda r: -r.area)
    g = Polygon()
    for r in rr: g = g.symmetric_difference(r)
    return g
cap_h10 = glyph('E').bounds[3] - glyph('E').bounds[1]
def make_text(cap_mm):
    sc_ = cap_mm / cap_h10; x = 0; out = []
    for ch in 'CAFE':
        g = affinity.scale(glyph(ch), sc_, sc_, origin=(0, 0))
        # fill counters too small to print (e.g. the A at this size)
        g = unary_union([Polygon(p.exterior, [h for h in p.interiors if not Polygon(h).buffer(-0.2).is_empty]) for p in polys(g)])
        g = affinity.translate(g, x - g.bounds[0], 0)
        out.append(g); x = g.bounds[2] + P['letter_gap']
    return unary_union(out)
slash = slash_body(p_bot0, p_top); trim = 0.0
mark = unary_union([blocks, beans, slash])
cap_txt = P['text_cap']
t1 = make_text(cap_txt)
mb = mark.bounds
text = affinity.translate(t1, (mb[0] + mb[2]) / 2 - (t1.bounds[0] + t1.bounds[2]) / 2, mb[1] - P['text_below'] - t1.bounds[3])
# re-centre logo + text group vertically on the face
grp = unary_union([mark, text]); gb = grp.bounds
dy_g = P['logo_cy_frac'] * 273*s - (gb[1] + gb[3]) / 2
fm_in = face_main.buffer(-P['logo_margin'])
for _ in range(80):
    if fm_in.contains(affinity.translate(grp, 0, dy_g)): break
    dy_g += 0.05 if (gb[1] + dy_g) < fm_in.bounds[1] + 1 else -0.05
blocks, beans, slash, text = [affinity.translate(g, 0, dy_g) for g in (blocks, beans, slash, text)]
print(f'CAFE cap height {cap_txt:.2f} mm, width {text.bounds[2]-text.bounds[0]:.2f} mm; group shifted {dy_g:+.2f} mm')

logo = clean(unary_union([blocks, beans, slash, text]), 0.005)
logo = unary_union([p for p in polys(logo) if p.area > 0.05])
print('LOGO INSIDE FACE (with margin):', face_main.buffer(-0.8).contains(logo))

# ---------------------------------------------------------------- feature-size report
def thin_report(g, w):
    lost = g.difference(g.buffer(-w/2, quad_segs=Q).buffer(w/2, quad_segs=Q))
    return sum(p.area for p in polys(lost) if p.area > 0.002)
def gap_report(g, w, within):
    filled = g.buffer(w/2, quad_segs=Q).buffer(-w/2, quad_segs=Q).difference(g).intersection(within)
    return sum(p.area for p in polys(filled) if p.area > 0.002)
rep = dict(scale=K, cafe_cap=cap_txt, slash_trim=trim,
           logo_bbox=[round(v, 2) for v in logo.bounds],
           brown_under_0p40=thin_report(logo, 0.40), brown_under_0p35=thin_report(logo, 0.35),
           gaps_under_0p40=gap_report(logo, 0.40, face_main), gaps_under_0p35=gap_report(logo, 0.35, face_main))

# ---------------------------------------------------------------- solids
def cs(g):
    rings_ = []
    for p in polys(g):
        rings_.append(np.asarray(p.exterior.coords)[:-1])
        rings_ += [np.asarray(h.coords)[:-1] for h in p.interiors]
    return CrossSection(rings_, FillRule.EvenOdd)

def ext(g, z0, z1):
    return Manifold.extrude(cs(g), z1 - z0).translate([0, 0, z0])

z = P
inner = sil.difference(ring_zone).buffer(0.0)
black = (ext(sil.buffer(-0.30, quad_segs=Q), 0, 0.2)
         + ext(sil.buffer(-0.15, quad_segs=Q), 0.2, 0.4)
         + ext(sil, 0.4, z['z_ring'] - 0.2)
         + ext(sil.buffer(-0.3, quad_segs=Q), z['z_ring'] - 0.2, z['z_ring'])
         + ext(fillet(cup, 0.8), 0.4, z['z_face'])
         + ext(lip, z['z_face'], z['z_lip'])
         + ext(rim, z['z_face'], z['z_rim_lo'])
         + ext(rim.intersection(box(-50, rim_split, 50, 99)).buffer(-0.28, quad_segs=Q), z['z_rim_lo'], z['z_rim'])
         + ext(cap, z['z_face'], z['z_cap'] - 0.2)
         + ext(cap.buffer(-0.3, quad_segs=Q), z['z_cap'] - 0.2, z['z_cap']))
black = black - ext(face, z['z_face0'], z['z_face'] + 0.01)
beige = ext(face, z['z_face0'], z['z_face'])
brown = ext(logo, z['z_face'], z['z_logo'])

parts = dict(black=black, beige=beige, brown=brown)
for n, m in parts.items():
    rep[f'{n}_volume_mm3'] = round(m.volume(), 1)
    rep[f'{n}_genus'] = m.genus()
    assert m.status().name == 'NoError', (n, m.status())
inter = [(a, b, (parts[a] ^ parts[b]).volume()) for a, b in [('black', 'beige'), ('black', 'brown'), ('beige', 'brown')]]
rep['overlaps_mm3'] = {f'{a}-{b}': round(v, 4) for a, b, v in inter}
union = black + beige + brown
bb = union.bounding_box()
rep['size_mm'] = [round(bb[3]-bb[0], 2), round(bb[4]-bb[1], 2), round(bb[5]-bb[2], 2)]
rep['union_genus'] = union.genus()

pickle.dump(dict(sil=sil, face=face, logo=logo, ring_zone=ring_zone, hole=hole, P=P, cup=cup,
                 rim=rim, cap=cap, lip=lip, body=body), open(os.path.join(OUT, 'geom2d.pkl'), 'wb'))
for n, m in parts.items():
    m = m.as_original().simplify(0.01)         # merge micro slivers (10 um, far below print resolution)
    assert m.status().name == 'NoError'
    me = m.to_mesh64()                         # float64 -> no vertices collapsing on export
    np.savez(os.path.join(OUT, f'{n}.npz'), v=np.asarray(me.vert_properties)[:, :3], f=np.asarray(me.tri_verts))
json.dump(rep, open(os.path.join(OUT, 'report.json'), 'w'), indent=1)
print(json.dumps(rep, indent=1))
