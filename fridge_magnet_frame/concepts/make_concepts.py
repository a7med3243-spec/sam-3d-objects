"""Shape concepts for the fridge photo frame.

Every concept re-uses the SAME back cover, magnets, name plate and snap system:
only the front silhouette, the photo window and engraved (debossed) details change.
The internal cuts (pocket, socket, tongue slots, latch + click grooves) come from
`fridge_photo_frame.scad` (part="cutters"), so each concept is a real frame.

usage: python3 make_concepts.py <cutters.stl> <out_dir>
"""
import sys, os, math, json
import numpy as np
import trimesh
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
from shapely.geometry.polygon import orient
from shapely import affinity
from manifold3d import CrossSection, Manifold, Mesh, FillRule

T, LIP = 4.4, 1.8
RF, RB, RW = 1.6, 1.2, 1.2            # front edge, back edge, window edge roundings
DEBOSS = 0.6                          # engraved detail depth (front face)

def rrect(x0, x1, y0, y1, r):
    return box(x0 + r, y0 + r, x1 - r, y1 - r).buffer(r, resolution=32)

PHOTO_LIMIT = box(-41.8, -25.8, 41.8, 25.8)                 # window must stay inside (1.2 mm lip overlap)
CORE = unary_union([rrect(-46.3, 46.3, -30.3, 30.3, 4),      # pocket + 3 mm wall
                    rrect(-18.7, 18.7, -42.3, -26.5, 4)])     # name-plate socket + 2.2 mm wall
NAME_WIN = rrect(-14.95, 14.95, -38.55, -30.25, 3.2)

def tear_d(z, r):
    if z >= r: return 0.0
    if z < r * (1 - 1 / math.sqrt(2)): return r * (2 - math.sqrt(2)) - z
    return r - math.sqrt(max(0.0, r * r - (r - z) ** 2))

def back_d(z, r):
    u = z - (T - r)
    return 0.0 if u <= 0 else r - math.sqrt(max(0.0, r * r - u * u))

def to_cs(geom):
    polys = [geom] if geom.geom_type == "Polygon" else [g for g in geom.geoms if g.geom_type == "Polygon"]
    contours = []
    for p in polys:
        p = orient(p, 1.0)
        contours.append(np.asarray(p.exterior.coords[:-1], dtype=np.float64))
        contours += [np.asarray(i.coords[:-1], dtype=np.float64) for i in p.interiors]
    return CrossSection(contours, FillRule.Positive)

def slab(geom, z0, z1, lap=0.0):
    # `lap` overlaps neighbouring layers: exactly touching solids are not fused by manifold
    z0, z1 = z0 - lap, z1 + lap
    return Manifold.extrude(to_cs(geom), z1 - z0).translate((0, 0, z0))

def solid_with_round_edges(outline):
    parts, n_f, n_b, lap = [], 16, 12, 0.002
    for i in range(n_f):                                   # printable teardrop front edge
        z0, z1 = RF * i / n_f, RF * (i + 1) / n_f
        parts.append(slab(outline.buffer(-tear_d((z0 + z1) / 2, RF), resolution=16), z0, z1 + lap))
    parts.append(slab(outline, RF, T - RB + lap))
    for i in range(n_b):                                   # rounded back edge
        z0 = T - RB + RB * i / n_b; z1 = z0 + RB / n_b
        parts.append(slab(outline.buffer(-back_d((z0 + z1) / 2, RB), resolution=16), z0, z1 + (lap if i < n_b - 1 else 0)))
    return Manifold.batch_boolean(parts, __import__("manifold3d").OpType.Add)

def window_cutter(win):
    parts, n = [slab(win.buffer(tear_d(0, RW) + 0.3, resolution=16), -0.3, 0.0, 0.002)], 12
    for i in range(n):
        z0, z1 = RW * i / n, RW * (i + 1) / n
        parts.append(slab(win.buffer(tear_d((z0 + z1) / 2, RW), resolution=16), z0, z1, 0.002))
    parts.append(slab(win, RW, LIP + 1.0, 0.002))
    return Manifold.batch_boolean(parts, __import__("manifold3d").OpType.Add)

def ring(geom, inset, width=0.8):
    """engraved line following a shape, `inset` mm outside it"""
    return geom.buffer(inset + width / 2, resolution=24).difference(geom.buffer(inset - width / 2, resolution=24))

def line(points, width=0.8):
    return LineString(points).buffer(width / 2, resolution=12)

def mirror_x(g):
    return unary_union([g, affinity.scale(g, -1, 1, origin=(0, 0))])

def smooth(g, r_in=1.5, r_out=1.0):
    g = g.buffer(r_in, resolution=24).buffer(-r_in, resolution=24)      # fillet concave corners
    return g.buffer(-r_out, resolution=24).buffer(r_out, resolution=24)  # round convex corners

def tudor_arch(half, y_shoulder, y_apex, dx):
    """shallow pointed (four-centred style) arch top: two big circles meeting at the apex"""
    cy = (dx**2 + y_apex**2 - (half + dx)**2 - y_shoulder**2) / (2 * (y_apex - y_shoulder))
    R = math.hypot(dx, y_apex - cy)
    left = Point(dx, cy).buffer(R, resolution=256)       # forms the left flank
    right = Point(-dx, cy).buffer(R, resolution=256)
    return left.intersection(right).intersection(box(-half, y_shoulder - 1, half, y_apex + 1))

# ------------------------------------------------------------------ concepts
def stamp():
    x0, x1, y0, y1, r = -51, 51, -46.5, 35, 1.7
    body = box(x0, y0, x1, y1)
    bites = []
    nx = round((x1 - x0) / 4.4); ny = round((y1 - y0) / 4.4)
    for i in range(nx + 1):
        x = x0 + i * (x1 - x0) / nx
        bites += [Point(x, y0).buffer(r, 24), Point(x, y1).buffer(r, 24)]
    for j in range(ny + 1):
        y = y0 + j * (y1 - y0) / ny
        bites += [Point(x0, y).buffer(r, 24), Point(x1, y).buffer(r, 24)]
    outer = body.difference(unary_union(bites))
    win = rrect(-41, 41, -25, 25, 0.8)
    post = Point(36, 26.5).buffer(7.9, 64).difference(Point(36, 26.5).buffer(7.1, 64))
    waves = [line([(x, yb + 0.7 * math.sin((x - 43) * 1.1)) for x in np.linspace(43.5, 48.5, 30)], 0.7)
             for yb in (30.5, 26.5, 22.5)]
    deb = unary_union([ring(win, 2.2), post] + waves)
    return outer, win, deb

def airplane():
    outer = rrect(-54, 54, -47.5, 38, 24)
    win = rrect(-41.8, 41.8, -25.8, 25.8, 17)
    rivet_path = outer.buffer(-3.4).exterior
    L = rivet_path.length
    rivets = [rivet_path.interpolate(d).buffer(0.9, 16) for d in np.arange(0, L, L / 36)]
    deb = unary_union([ring(win, 3.8)] + rivets)
    return outer, win, deb

def retro_tv():
    body = rrect(-52, 52, -47, 35, 11)
    rods = [line([(sx * 3, 37), (sx * 19.5, 55)], 3.0) for sx in (-1, 1)]
    balls = [Point(sx * 20.3, 56).buffer(3.2, 32) for sx in (-1, 1)]
    dome = Point(0, 35).buffer(7, 48)
    feet = [Polygon([(sx * 30, -46), (sx * 42, -46), (sx * 40, -51.5), (sx * 32, -51.5)]) for sx in (-1, 1)]
    outer = smooth(unary_union([body, dome] + rods + balls + feet), 1.8, 0.8)
    n, a, b = 4.5, 41.8, 25.8                                   # super-ellipse CRT screen
    th = np.linspace(0, 2 * np.pi, 360, endpoint=False)
    win = Polygon(np.c_[a * np.sign(np.cos(th)) * np.abs(np.cos(th)) ** (2 / n),
                        b * np.sign(np.sin(th)) * np.abs(np.sin(th)) ** (2 / n)])
    knobs = []
    for sx in (-1, 1):
        c = (sx * 34, -37.5)
        knobs += [Point(c).buffer(4.6, 48).difference(Point(c).buffer(3.8, 48)),
                  line([c, (c[0] + 2.6 * math.cos(math.radians(60 + 60 * sx)), c[1] + 2.6 * math.sin(math.radians(60 + 60 * sx)))], 0.8)]
    deb = unary_union([ring(win, 2.6)] + knobs)
    return outer, win, deb

def ottoman():
    base = rrect(-52, 52, -47, 31.5, 7)
    crown = tudor_arch(52, 31.5, 50, 35)
    # tulip finial (lale)
    cup = Point(0, 55.2).buffer(4.6, 48).intersection(box(-6, 50, 6, 55.6))
    petals = [affinity.rotate(affinity.scale(Point(0, 0).buffer(1, 48), 1.9, 4.8), a, origin=(0, 0)) for a in (0, 26, -26)]
    petals = [affinity.translate(p, dx, 58.6 + dy) for p, dx, dy in zip(petals, (0, -2.6, 2.6), (0, -0.6, -0.6))]
    stem = box(-1.4, 47, 1.4, 52)
    tulip = unary_union([cup, stem] + petals)
    outer = smooth(unary_union([base, crown, tulip]), 1.5, 0.8)
    arch = tudor_arch(41.8, 10, 25.8, 30)
    win = smooth(unary_union([box(-41.8, -25.8, 41.8, 10.5), arch]), 0.1, 3.5)
    # 8-point Seljuk star in the crown
    sq = box(-4.6, -4.6, 4.6, 4.6)
    star = unary_union([sq, affinity.rotate(sq, 45)])
    star = affinity.translate(star, 0, 39)
    deb = unary_union([ring(win, 2.6), star.boundary.buffer(0.4, 8)])
    return outer, win, deb

def boarding_pass():
    body = rrect(-52, 84, -47, 34, 5)
    notches = [Point(55, 34).buffer(5, 48), Point(55, -47).buffer(5, 48)]
    outer = body.difference(unary_union(notches))
    win = rrect(-41.8, 41.8, -25.8, 25.8, 2)
    dashes = [box(54.6, y, 55.4, y + 2.6) for y in np.arange(-40.5, 28, 4.2)]
    rng = np.random.default_rng(7); bars, x = [], 61.5
    while x < 78:
        w = rng.choice([0.7, 0.7, 1.1, 1.6]); bars.append(box(x, -39, x + w, -10)); x += w + rng.choice([0.7, 1.0])
    plane = unary_union([
        affinity.scale(Point(0, 0).buffer(1, 32), 1.2, 6.5),                       # fuselage
        Polygon([(-8, -0.6), (0, 2.2), (8, -0.6), (8, -2.0), (0, 0.4), (-8, -2.0)]),  # wings
        Polygon([(-3.2, -5.6), (0, -4.2), (3.2, -5.6), (3.2, -6.6), (0, -5.6), (-3.2, -6.6)])])
    plane = affinity.translate(affinity.rotate(plane, -90, origin=(0, 0)), 69.5, 18)
    deb = unary_union(dashes + bars + [plane.boundary.buffer(0.4, 8)])
    return outer, win, deb

def suitcase():
    body = rrect(-53, 53, -47, 33.5, 8)
    handle = rrect(-15, 15, 31, 44.5, 6).difference(rrect(-10, 10, 35, 40.5, 2.5))
    wheels = [Point(sx * 43, -48.5).buffer(3.6, 32) for sx in (-1, 1)]
    outer = smooth(unary_union([body, handle] + wheels), 1.5, 0.8)
    win = rrect(-41.8, 41.8, -25.8, 25.8, 3)
    caps = []
    for sx in (-1, 1):
        for sy, yc in ((1, 33.5), (-1, -47)):
            c = Point(sx * 53, yc).buffer(11.5, 64).boundary.buffer(0.4, 8)
            caps += [c, Point(sx * 46.8, yc - sy * 6.2).buffer(0.9, 16)]
    straps = [box(sx * 30 - 2.9, -60, sx * 30 - 2.1, 60) for sx in (-1, 1)] + \
             [box(sx * 30 + 2.1, -60, sx * 30 + 2.9, 60) for sx in (-1, 1)]
    deb = unary_union(caps + straps)
    return outer, win, deb

CONCEPTS = {"stamp": stamp, "airplane": airplane, "retro_tv": retro_tv,
            "ottoman": ottoman, "boarding_pass": boarding_pass, "suitcase": suitcase}

def build(name, cutters):
    outer, win, deb = CONCEPTS[name]()
    # engraving only on solid frame face, away from edges and from the windows
    deb = deb.intersection(outer.buffer(-1.0)).difference(win.buffer(0.8)).difference(NAME_WIN.buffer(0.8))
    report = {
        "core_inside_outline": round(CORE.difference(outer).area, 4) < 0.01,
        "window_inside_photo_lip": round(win.difference(PHOTO_LIMIT).area, 4) < 0.01,
        "min_border_mm": round(outer.exterior.distance(win), 2),
        "outline_mm": [round(v, 1) for v in (outer.bounds[2] - outer.bounds[0], outer.bounds[3] - outer.bounds[1])],
    }
    solid = solid_with_round_edges(outer) - window_cutter(win) - cutters
    if not deb.is_empty:
        solid = solid - slab(deb, -1, DEBOSS)
    keep = [c for c in solid.decompose() if c.volume() > 0.01]          # drop zero-volume slivers
    solid = Manifold.compose(keep).simplify(0.002)                      # and degenerate faces
    m = solid.to_mesh()
    tm = trimesh.Trimesh(np.asarray(m.vert_properties)[:, :3], np.asarray(m.tri_verts))
    if not tm.is_watertight or len(tm.split(only_watertight=False)) > 1:
        tm.update_faces(tm.nondegenerate_faces(height=1e-5)); tm.remove_unreferenced_vertices()
        tm = max(tm.split(only_watertight=False), key=lambda b: abs(b.volume))
    report.update(watertight=bool(tm.is_watertight), bodies=len(tm.split(only_watertight=False)),
                  weight_g_PLA=round(tm.volume / 1000 * 1.24, 1))
    return tm, report

if __name__ == "__main__":
    cut_path, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    ct = trimesh.load(cut_path, force="mesh")
    cutters = Manifold(Mesh(vert_properties=np.asarray(ct.vertices, np.float32), tri_verts=np.asarray(ct.faces, np.uint32)))
    allrep = {}
    for name in (sys.argv[3:] or CONCEPTS):
        tm, rep = build(name, cutters)
        tm.export(os.path.join(out, f"concept_{name}.stl"))
        allrep[name] = rep
        print(name, rep)
    json.dump(allrep, open(os.path.join(out, "concepts_report.json"), "w"), indent=1)
