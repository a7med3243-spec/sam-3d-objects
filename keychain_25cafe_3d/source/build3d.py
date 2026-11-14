"""25 Percent Cafe - 3D mini takeaway-cup keychain (4 colours, prints upright in one piece).

Coordinates: mm, cup bottom centre at origin, Z up (print direction).
Logo faces -X, back text faces +X, blank strips at +/-Y (Bambu "Back" seam lands at +Y).
Parts: black lid + loop | beige cup | dark-brown logo/text inlay (flush, 0.9 mm deep) | white rolled bottom ring.
Artwork x = arc length on the cup wall at that height (same as the photo), y = height.
"""
import json, os, pickle, sys
import numpy as np
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
from shapely import affinity
from manifold3d import Manifold, CrossSection, FillRule
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties

ART, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
A = pickle.load(open(ART, 'rb'))
H = A['P']['H']; s = H / 351.0
P = dict(seg=512, inlay=0.9, tol_inlay=float(os.environ.get('TOL', 0.002)), ring_r=5.0, hole_r=2.25, ring_dy=2.6, loop_t=3.4,
         font_txt='/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf',
         t1=('TWENTY-FIVE', 'PERCENT CAFE'), t1_cap=2.2, t1_gap=0.42, t1_z=18.633, t1_lead=0.9,
         t2='25percent.cafe', t2_cap=1.9, t2_gap=0.38, t2_z=11.633, ig=3.0, font_t1='/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf')

def polys(g):
    if g.is_empty: return []
    if isinstance(g, Polygon): return [g]
    return [p for p in getattr(g, 'geoms', []) if isinstance(p, Polygon) and not p.is_empty]

def cs_of(g):
    rr = []
    for p in polys(g):
        rr.append(np.asarray(p.exterior.coords)[:-1])
        rr += [np.asarray(h.coords)[:-1] for h in p.interiors]
    return CrossSection(rr, FillRule.EvenOdd)

def arc(cx, cz, rad, a0, a1, n=12):
    a = np.radians(np.linspace(a0, a1, n))
    return [(cx + rad * np.cos(t), cz + rad * np.sin(t)) for t in a]

# ------------------------------------------------------------ cup profile (r, z) from the photo
zb, r0, rb = 273 * s, 78.5 * s, 115 * s
R = lambda z: r0 + (rb - r0) * np.asarray(z) / zb
zg = 26 * s                                    # rolled-bottom ring line
body_prof = [(0, 0), (r0 - 0.3, 0), (float(R(0.4)), 0.4),
             (float(R(zg - 0.3)), zg - 0.3), (float(R(zg)) - 0.25, zg - 0.05), (float(R(zg)) - 0.25, zg + 0.05), (float(R(zg + 0.4)), zg + 0.4),
             (rb, zb), (0, zb)]
body = Manifold.revolve(CrossSection([np.array(body_prof)]), P['seg'])

r_lip, z_rim0, z_rim1, r_rim = 117 * s, 280 * s, 310 * s, 125.7 * s
r_cap0, r_cap1 = 108 * s, 99 * s
rc = 0.8                                       # lid top corner radius
r_rec = r_cap1 - 2.2                           # top recess
z_ch = z_rim0 + (r_rim - r_lip)                # end of 45 deg chamfer under the rim
z_rg = (z_ch + z_rim1) / 2                     # bead groove on the rim
lid_prof = ([(0, zb), (rb, zb), (r_lip, zb + (r_lip - rb)), (r_lip, z_rim0), (r_rim, z_ch),
             (r_rim, z_rg - 0.25), (r_rim - 0.25, z_rg), (r_rim, z_rg + 0.25)]
            + arc(r_rim - 0.55, z_rim1 - 0.55, 0.55, 0, 90, 10)
            + [(r_cap0, z_rim1)]
            + arc(r_cap1 - rc, H - rc, rc, -8, 90, 14)
            + [(r_rec, H), (r_rec, H - 0.5), (0, H - 0.5)])
lid = Manifold.revolve(CrossSection([np.array(lid_prof)]), P['seg'])
# sip slot on the lid ring, above the logo (-X)
slot = Manifold.cube([0.75, 3.0, 2.0], center=True).translate([-(r_rec + 0.75), 0, H])
lid = lid - slot

# ------------------------------------------------------------ key-ring loop (plane YZ, hole along X)
c = H + P['ring_dy']; rh = P['hole_r']; k = rh * np.sqrt(0.5)
outer = unary_union([Point(0, c).buffer(P['ring_r'], quad_segs=48), box(-6, H - 1.5, 6, H - 0.5)])
outer = outer.buffer(1.6, quad_segs=32).buffer(-1.6, quad_segs=32).intersection(box(-9, H - 1.5, 9, H + 20))
tear = unary_union([Point(0, c).buffer(rh, quad_segs=48),
                    Polygon([(-k, c + k), (k, c + k), (0.6, c + rh * np.sqrt(2) - 0.6), (-0.6, c + rh * np.sqrt(2) - 0.6)])])
loop2d = outer.difference(tear)
T = P['loop_t']
loop = Manifold.extrude(cs_of(loop2d), T).warp_batch(lambda p: np.c_[p[:, 2] - T / 2, p[:, 0], p[:, 1]])
black = lid + loop

# ------------------------------------------------------------ artwork: logo (front) + text (back)
FP = {}
def glyph(ch, font=None):
    font = font or P['font_txt']
    fp = FP.setdefault(font, FontProperties(fname=font))
    tp = TextPath((0, 0), ch, size=10, prop=fp)
    rings, cur = [], []
    for bz, code in tp.iter_bezier():
        if code == 1:
            if len(cur) > 2: rings.append(cur)
            cur = [tuple(bz.control_points[0])]; continue
        n = 1 if bz.degree <= 1 else 20
        cur += [tuple(pt) for pt in bz(np.linspace(0, 1, n + 1)[1:])]
    if len(cur) > 2: rings.append(cur)
    g = Polygon()
    for r in sorted([Polygon(r).buffer(0) for r in rings], key=lambda r: -r.area): g = g.symmetric_difference(r)
    return g
CAPREF = glyph('H').bounds[3]
def text_line(txt, cap, gap, font=None):
    sc = cap / CAPREF; x = 0; out = []
    space = glyph('n', font).bounds[2] * sc * 0.55
    for ch in txt:
        if ch == ' ':
            x += space; continue
        g = affinity.scale(glyph(ch, font), sc, sc, origin=(0, 0))
        g = unary_union([Polygon(p.exterior, [h for h in p.interiors if not Polygon(h).buffer(-0.18).is_empty]) for p in polys(g)])
        g = affinity.translate(g, x - g.bounds[0], 0)
        out.append(g); x = g.bounds[2] + gap
    t = unary_union(out)
    return affinity.translate(t, -(t.bounds[0] + t.bounds[2]) / 2, 0)

logo = A['logo']
logo = affinity.translate(logo, -(logo.bounds[0] + logo.bounds[2]) / 2, 0)
l1 = text_line(P['t1'][0], P['t1_cap'], P['t1_gap'], P['font_t1']); l2 = text_line(P['t1'][1], P['t1_cap'], P['t1_gap'], P['font_t1'])
t1 = unary_union([affinity.translate(l1, 0, P['t1_z'] + P['t1_lead'] / 2),
                  affinity.translate(l2, 0, P['t1_z'] - P['t1_lead'] / 2 - P['t1_cap'])])
# Instagram icon (rounded square + lens ring) + handle, like the cup
a = P['ig'] / 2
sq = box(-a, -a, a, a).buffer(-0.8, quad_segs=24).buffer(0.8, quad_segs=24)
icon = unary_union([sq.difference(sq.buffer(-0.48, quad_segs=24)), Point(0, 0).buffer(0.55, quad_segs=32)])
hnd = text_line(P['t2'], P['t2_cap'], P['t2_gap'])
hnd = affinity.translate(hnd, -hnd.bounds[0], 0)
icon = affinity.translate(icon, -a - 0.6, P['t2_cap'] / 2)
t2 = unary_union([icon, hnd]); t2 = affinity.translate(t2, -(t2.bounds[0] + t2.bounds[2]) / 2, P['t2_z'] - P['t2_cap'] / 2)
art = dict(logo=(logo, np.pi), text=(unary_union([t1, t2]), 0.0))

def wall_inlay(g, th_c, depth, out_extra=0.4):
    slab = Manifold.extrude(cs_of(g), depth + out_extra).refine_to_length(0.8)
    def f(p):
        x, y, w = p[:, 0], p[:, 1], p[:, 2]
        Ry = R(y); r = Ry - depth + w
        th = th_c + x / Ry                     # arc length preserved at every height
        return np.c_[r * np.cos(th), r * np.sin(th), y]
    return slab.warp_batch(f)
inlay = wall_inlay(*art['logo'], P['inlay']) + wall_inlay(*art['text'], P['inlay'])
brown = body ^ inlay                                   # exact complementary pair: no simplification on these,
cup = body - inlay                                     # so the logo/cup interface stays identical in both parts
white = cup.trim_by_plane([0, 0, -1], -zg)     # keep z <= zg
beige = cup.trim_by_plane([0, 0, 1], zg)       # keep z >= zg
parts = dict(black=black, beige=beige, brown=brown, white=white)

# ------------------------------------------------------------ report + save
rep = dict(H=H, height_total=round(c + P['ring_r'], 2), max_diameter=round(2 * r_rim, 2),
           art_bounds={k: [round(v, 2) for v in g.bounds] for k, (g, _) in art.items()},
           text1_width=round(t1.bounds[2] - t1.bounds[0], 2), text2_width=round(t2.bounds[2] - t2.bounds[0], 2),
           circumference_at_t1=round(2 * np.pi * float(R(P['t1_z'])), 2), circumference_at_t2=round(2 * np.pi * float(R(P['t2_z'])), 2),
           logo_arc_deg=round(np.degrees((logo.bounds[2] - logo.bounds[0]) / float(R(15))), 1))
for n, m in parts.items():
    m = m.as_original().simplify(0.01 if n == 'black' else P['tol_inlay'])   # tiny tol keeps logo/cup interface within microns
    assert m.status().name == 'NoError', n
    parts[n] = m
    rep[f'{n}_volume'] = round(m.volume(), 1); rep[f'{n}_bodies'] = len(m.decompose())
    me = m.to_mesh64()
    np.savez(os.path.join(OUT, f'{n}.npz'), v=np.asarray(me.vert_properties)[:, :3], f=np.asarray(me.tri_verts))
pickle.dump(dict(art=art, P=P, H=H, t1=t1, t2=t2, logo=logo, loop2d=loop2d), open(os.path.join(OUT, 'art3d.pkl'), 'wb'))
print(json.dumps(rep, indent=1))
