"""25 Percent Cafe - coaster and serving tray (3 colours, top-layer colour only -> few filament changes).

Same colour stack as the flat keychain: black base + raised rim, beige top surface inlaid in the black,
dark-brown logo/text inlaid flush in the top 0.6 mm (flush = cups stand flat on it).
"""
import json, os, pickle, sys
import numpy as np
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
from shapely import affinity
from manifold3d import Manifold, CrossSection, FillRule
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties

ART, OUT = sys.argv[1], sys.argv[2]
LOGO = pickle.load(open(ART, 'rb'))['logo']
Q = 48
FONT = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'

def polys(g):
    if g.is_empty: return []
    if isinstance(g, Polygon): return [g]
    return [p for p in getattr(g, 'geoms', []) if isinstance(p, Polygon) and not p.is_empty]

def cs_of(g):
    rr = []
    for p in polys(g):
        rr.append(np.asarray(p.exterior.coords)[:-1]); rr += [np.asarray(h.coords)[:-1] for h in p.interiors]
    return CrossSection(rr, FillRule.EvenOdd)

def ext(g, z0, z1, ov=0.0):
    z0 = z0 - ov if z0 > 0 else z0           # ov: small overlap so stacked pieces of ONE colour fuse into one body
    return Manifold.extrude(cs_of(g), z1 - z0).translate([0, 0, z0])

# ------------------------------------------------------------------ artwork helpers
FP = FontProperties(fname=FONT)
def glyph(ch):
    tp = TextPath((0, 0), ch, size=10, prop=FP)
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

def ig_icon(size):
    a = size / 2
    sq = box(-a, -a, a, a).buffer(-a * 0.5, quad_segs=24).buffer(a * 0.5, quad_segs=24)
    st = max(0.5, size * 0.13)
    lens = Point(0, 0).buffer(a * 0.42, quad_segs=32).difference(Point(0, 0).buffer(a * 0.42 - st, quad_segs=32))
    dot = Point(a * 0.52, a * 0.52).buffer(st * 0.6, quad_segs=16)
    return unary_union([sq.difference(sq.buffer(-st, quad_segs=24)), lens, dot])

def bean(L, W, ang, crease):
    ell = affinity.scale(Point(0, 0).buffer(1, quad_segs=48), L / 2, W / 2)
    t = np.linspace(-0.62, 0.62, 80)
    cr = LineString([(ti * L / 2 * 1.0, 0.16 * W * np.sin(np.pi * ti / 0.62)) for ti in t]).buffer(crease / 2, quad_segs=16)
    return affinity.rotate(ell.difference(cr), ang, origin=(0, 0))

def arc_text(items, r, cap, gap, center_deg, top=True):
    """items: list of glyph strings or shapely icons. top: reads along the top (tops outward);
    bottom: reads along the bottom, upright (tops toward the centre)."""
    sc = cap / CAPREF
    shapes = []
    for it in items:
        if isinstance(it, str):
            if it == ' ': shapes.append(None); continue
            g = affinity.scale(glyph(it), sc, sc, origin=(0, 0))
        else:
            g = it
        shapes.append(g)
    space = cap * 0.35
    widths = [space if g is None else g.bounds[2] - g.bounds[0] for g in shapes]
    rm = r + cap / 2 if top else r - cap / 2          # arc length measured at mid-cap height
    L = sum(widths) + gap * (len(widths) - 1)
    out, s = [], 0.0
    c = np.radians(center_deg)
    for g, w in zip(shapes, widths):
        mid = s + w / 2; s += w + gap
        if g is None: continue
        g = affinity.translate(g, -(g.bounds[0] + g.bounds[2]) / 2, 0)
        if not isinstance(g, Polygon) or True:
            pass
        if top:
            th = c + (L / 2 - mid) / rm
            g = affinity.translate(g, 0, r)                     # baseline on the circle, glyph outside
            g = affinity.rotate(g, np.degrees(th) - 90, origin=(0, 0))
        else:
            th = c - (L / 2 - mid) / rm
            g = affinity.translate(g, 0, -r)                    # baseline on the circle, glyph inside
            g = affinity.rotate(g, np.degrees(th) - 270, origin=(0, 0))
        out.append(g)
    return unary_union(out)

def place_logo(height, cx, cy):
    b = LOGO.bounds; k = height / (b[3] - b[1])
    g = affinity.scale(LOGO, k, k, origin=(0, 0)); b = g.bounds
    return affinity.translate(g, cx - (b[0] + b[2]) / 2, cy - (b[1] + b[3]) / 2)

def handle_row(cap, icon):
    ic = ig_icon(icon); ic = affinity.translate(ic, 0, cap / 2)
    return [ic] + list('25percent.cafe')

# ------------------------------------------------------------------ products
def coaster():
    R, rim = 50.0, 3.5
    Ri = R - rim
    outer = Point(0, 0).buffer(R, quad_segs=Q * 2)
    face = Point(0, 0).buffer(Ri, quad_segs=Q * 2)
    art = [place_logo(41.0, 0, 1.0),
           arc_text(list('TWENTY-FIVE PERCENT CAFE'), 36.0, 4.2, 0.55, 90, top=True),
           arc_text(handle_row(3.6, 5.0), 41.6, 3.6, 0.5, 270, top=False)]
    for ang in (0, 180):           # coffee-bean separators between the two text arcs
        p = (38.6 * np.cos(np.radians(ang)), 38.6 * np.sin(np.radians(ang)))
        art.append(affinity.translate(bean(6.0, 3.6, 90 + ang, 0.75), *p))
    art = unary_union(art)
    Z = dict(base=2.4, face=4.0, inlay=0.6, rim=5.0)
    black = (ext(outer.buffer(-0.3, quad_segs=Q), 0, 0.2) + ext(outer.buffer(-0.15, quad_segs=Q), 0.2, 0.4, 0.02)
             + ext(outer, 0.4, Z['base'], 0.02)
             + ext(outer.difference(face), Z['base'], Z['rim'] - 0.2, 0.02)
             + ext(outer.buffer(-0.35, quad_segs=Q).difference(face.buffer(0.35, quad_segs=Q)), Z['rim'] - 0.2, Z['rim'], 0.02))
    beige = ext(face, Z['base'], Z['face']) - ext(art, Z['face'] - Z['inlay'], Z['face'] + 0.1)
    brown = ext(art.intersection(face.buffer(-1.0)), Z['face'] - Z['inlay'], Z['face'])
    return dict(black=black, beige=beige, brown=brown), dict(face=face, outer=outer, art=art, Z=Z)

def tray():
    W2, Rr, rim = 45.0, 65.0, 6.0                   # stadium: two circles r=65 at x=+/-45 -> 220 x 130 mm
    stad = lambda r: unary_union([Point(-W2, 0).buffer(r, quad_segs=Q * 2), Point(W2, 0).buffer(r, quad_segs=Q * 2), box(-W2, -r, W2, r)])
    outer, inner = stad(Rr), stad(Rr - rim)
    cup_c = (-W2, 0.0); r_top, depth = 37.0, 2.4    # cup pocket: fits cup bottoms up to ~69 mm, 45 deg sides
    Z = dict(base=1.6, floor=5.2, inlay=0.6, rim=8.2)
    art = [arc_text(list('TWENTY-FIVE PERCENT CAFE'), 44.0, 5.0, 0.7, 90, top=True),
           arc_text(handle_row(4.4, 6.0), 50.0, 4.4, 0.6, 270, top=False)]
    for ang in (0, 180):
        p = (cup_c[0] + 47.0 * np.cos(np.radians(ang)), 47.0 * np.sin(np.radians(ang)))
        art.append(affinity.translate(bean(7.0, 4.2, 90 + ang, 0.9), *p))
    art[0] = affinity.translate(art[0], *cup_c); art[1] = affinity.translate(art[1], *cup_c)
    art.append(place_logo(66.0, W2 + 4.0, 0.0))
    art = unary_union(art)
    pocket = Manifold.cylinder(depth + 0.02, r_top - depth, r_top + 0.02, 256).translate([cup_c[0], cup_c[1], Z['floor'] - depth])
    feet = unary_union([Point(x, y).buffer(5.25, quad_segs=24) for x in (-80, 80) for y in (-38, 38)])
    black = (ext(outer.buffer(-0.3, quad_segs=Q).difference(feet), 0, 0.2) + ext(outer.buffer(-0.15, quad_segs=Q).difference(feet), 0.2, 0.4, 0.02)
             + ext(outer.difference(feet), 0.4, 0.8, 0.02) + ext(outer, 0.8, Z['base'], 0.02)
             + ext(outer.difference(inner), Z['base'], Z['rim'] - 0.2, 0.02)
             + ext(outer.buffer(-0.4, quad_segs=Q).difference(inner.buffer(0.4, quad_segs=Q)), Z['rim'] - 0.2, Z['rim'], 0.02))
    beige = ext(inner, Z['base'], Z['floor']) - pocket - ext(art, Z['floor'] - Z['inlay'], Z['floor'] + 0.1)
    brown = ext(art.intersection(inner.buffer(-1.5)), Z['floor'] - Z['inlay'], Z['floor'])
    return dict(black=black, beige=beige, brown=brown), dict(face=inner, outer=outer, art=art, Z=Z, pocket=(cup_c, r_top, depth))

def rrect(w, h, r):
    return box(-w / 2 + r, -h / 2 + r, w / 2 - r, h / 2 - r).buffer(r, quad_segs=Q)

def text_block(lines, cap, gap, lead, cx, cy):
    """straight centred lines, block centred at (cx, cy)"""
    sc = cap / CAPREF; rows = []
    for ln in lines:
        x, parts = 0.0, []
        for ch in ln:
            if not isinstance(ch, str):
                g = ch
            elif ch == ' ':
                x += cap * 0.35; continue
            else:
                g = affinity.scale(glyph(ch), sc, sc, origin=(0, 0))
            g = affinity.translate(g, x - g.bounds[0], 0); parts.append(g); x = g.bounds[2] + gap
        row = unary_union(parts); rows.append(affinity.translate(row, -(row.bounds[0] + row.bounds[2]) / 2, 0))
    out = []
    for i, r in enumerate(rows):
        out.append(affinity.translate(r, cx, cy + ((len(rows) - 1) / 2 - i) * (cap + lead) - cap / 2))
    return unary_union(out)

def tray4():
    """4-cup serving tray with a sweets dish, hand slots and rubber-feet pockets. Fits the A2L plate."""
    L, Wd, R, rim = 310.0, 232.0, 30.0, 7.0
    outer, inner = rrect(L, Wd, R), rrect(L - 2 * rim, Wd - 2 * rim, R - rim)
    cups = [(sx * 76.0, sy * 56.0) for sx in (-1, 1) for sy in (-1, 1)]
    r_top, depth = 37.0, 2.4
    Z = dict(base=1.6, floor=5.2, inlay=0.6, rim=16.0, dish=1.6)
    slots = unary_union([LineString([(sx * 131.0, -34.0), (sx * 131.0, 34.0)]).buffer(11.0, quad_segs=32) for sx in (-1, 1)])
    frame = slots.buffer(3.0, quad_segs=32)                      # black frame around each hand slot
    floor = inner.difference(frame)
    feet = unary_union([Point(x, y).buffer(5.25, quad_segs=24) for x in (-112, 0, 112) for y in (-86, 86)])
    da, db = 52.0, 38.0                                           # sweets dish: 104 x 76 mm oval, 1.6 mm deep
    art = [place_logo(44.0, 0.0, 78.0),
           text_block(['TWENTY-FIVE', 'PERCENT CAFE'], 5.0, 0.75, 2.4, 0.0, -74.0),
           text_block([[affinity.translate(ig_icon(5.6), 0, 2.2)] + list('25percent.cafe')], 4.4, 0.6, 0, 0.0, -99.0)]
    for c in cups:                                                # thin brown ring around each cup pocket
        art.append(Point(*c).buffer(40.0, quad_segs=64).difference(Point(*c).buffer(38.6, quad_segs=64)))
    for sx in (-1, 1):
        art.append(affinity.translate(bean(7.0, 4.2, 90, 0.9), sx * 63.0, 0.0))
    art = unary_union(art)
    pockets = None
    for c in cups:
        p = Manifold.cylinder(depth + 0.02, r_top - depth, r_top + 0.02, 256).translate([c[0], c[1], Z['floor'] - depth])
        pockets = p if pockets is None else pockets + p
    ell = affinity.scale(Point(0, 0).buffer(1, quad_segs=96), da - Z['dish'], db - Z['dish'])
    dish = Manifold.extrude(cs_of(ell), Z['dish'] + 0.02, 0, 0, (da / (da - Z['dish']), db / (db - Z['dish']))).translate([0, 0, Z['floor'] - Z['dish']])
    black = (ext(outer.buffer(-0.3, quad_segs=Q).difference(feet).difference(slots.buffer(0.3)), 0, 0.2)
             + ext(outer.buffer(-0.15, quad_segs=Q).difference(feet).difference(slots.buffer(0.15)), 0.2, 0.4, 0.02)
             + ext(outer.difference(feet).difference(slots), 0.4, 0.8, 0.02)
             + ext(outer.difference(slots), 0.8, Z['base'], 0.02)
             + ext(outer.difference(inner).union(frame.difference(slots)), Z['base'], Z['floor'], 0.02)
             + ext(outer.difference(inner), Z['floor'], Z['rim'] - 0.2, 0.02)
             + ext(outer.buffer(-0.4, quad_segs=Q).difference(inner.buffer(0.4, quad_segs=Q)), Z['rim'] - 0.2, Z['rim'], 0.02))
    beige = ext(floor, Z['base'], Z['floor']) - pockets - dish - ext(art, Z['floor'] - Z['inlay'], Z['floor'] + 0.1)
    brown = ext(art.intersection(floor.buffer(-1.5)), Z['floor'] - Z['inlay'], Z['floor'])
    return dict(black=black, beige=beige, brown=brown), dict(face=floor, outer=outer, art=art, Z=Z,
                                                             pockets=[(c, r_top, depth) for c in cups], dish=(da, db), slots=slots)

if __name__ == '__main__':
    todo = sys.argv[3].split(',') if len(sys.argv) > 3 else ['coaster', 'tray']
    for name, fn in [(n, globals()[n]) for n in todo]:
        parts, info = fn()
        d = os.path.join(OUT, name); os.makedirs(d, exist_ok=True)
        rep = {}
        for n, m in parts.items():
            m = m.as_original().simplify(0.005)
            assert m.status().name == 'NoError', (name, n)
            me = m.to_mesh64()
            np.savez(os.path.join(d, f'{n}.npz'), v=np.asarray(me.vert_properties)[:, :3], f=np.asarray(me.tri_verts))
            rep[n] = dict(volume=round(m.volume(), 1), bodies=len(m.decompose()))
        art_in = info['art'].difference(info['face'].buffer(-1.0 if name == 'coaster' else -1.5))
        rep['art_outside_face_mm2'] = round(art_in.area, 4)
        pickle.dump(info, open(os.path.join(d, 'info.pkl'), 'wb'))
        print(name, json.dumps(rep))
