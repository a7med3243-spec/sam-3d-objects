"""
Filament-optimized book divider / bookend - parametric generator.

Outputs watertight, print-ready meshes as STL and 3MF (units: mm) for six
outline shapes: arch, pointed_arch, house, mountain, tablet, octagon.

Design (shared by all shapes):
  * Plate 135 x 155 mm with 7 concentric ribs, 3 mm deep, on BOTH faces; the
    ribs follow the outline as exact offsets (mitred at sharp corners).
  * The arch is a CLOSED solid, modelled solid on purpose so the slicer fills
    it with light sparse infill (the cheapest way to make a closed shape).
  * Only the BASE is hollowed: a skeleton frame with a large lightening window
    and chamfered edges.
  * All rib flanks are limited to <= 48 deg from vertical, so the ribs print
    cleanly even where they run horizontally over the top of the arch ->
    the part prints upright with NO supports.

Print orientation: as modelled (base flat on the bed, plate standing up).

Run:  python book_divider.py [shape ...]     (default: all shapes -> models/)
      needs: pip install manifold3d numpy
"""

import math
import os
import struct
import zipfile

import numpy as np
from manifold3d import CrossSection, JoinType, Manifold, OpType

# --------------------------------------------------------------------------
# Parameters (mm)
# --------------------------------------------------------------------------
WIDTH = 135.0           # arch width
HEIGHT = 155.0          # arch height
PLATE_DEPTH = 20.0      # arch thickness crest-to-crest (ribs on both faces)
RIB_DEPTH = 3.0         # groove depth of the rainbow ribs
N_RIBS = 7              # ribs per side (outermost forms the rounded edge)
FLANK_ANGLE = 48.0      # max rib flank angle from the plate (= overhang angle)
GROOVE_RADIUS = 1.0     # radius at the bottom of each groove

BASE_DEPTH = 105.0      # total depth incl. plate
BASE_THICK = 4.5
BASE_SIDE = 10.0        # width of the side / far frame bars
BASE_FRONT_BAR = 4.0    # solid strip right behind the plate
BASE_CORNER_R = 16.0    # far-end outer corner radius
WINDOW_CORNER_R = 9.0   # lightening window corner radius
TOP_CHAMFER = 0.8       # base top-edge chamfer
FOOT_CHAMFER = 0.4      # base bottom-edge chamfer (elephant-foot relief)

PAIR_GAP = 8.0          # gap between the two parts in the pair file

R = WIDTH / 2.0                 # arch outer radius


# --------------------------------------------------------------------------
# 2D rib profile in the (rho, y) half-plane
#   rho = "arch radius" coordinate (distance from the arch centre line)
#   y   = depth (0 = rib crests / front, PLATE_DEPTH = back)
# --------------------------------------------------------------------------
def _arc(cx, cy, r, a0, a1, n):
    """Points on an arc; angle a measured so that point = (cx + r sin a, cy + r cos a)."""
    return [(cx + r * math.sin(a), cy + r * math.cos(a))
            for a in np.linspace(a0, a1, n)]


def rib_geometry():
    b = math.radians(FLANK_ANGLE)
    A = 2 * math.sin(b) - 2 * (1 - math.cos(b)) / math.tan(b)
    B = 2 * RIB_DEPTH / math.tan(b)
    k = N_RIBS - 0.5
    rc = (R - k * (A * GROOVE_RADIUS + B)) / (k * A + 1)   # crest radius
    pitch = A * (rc + GROOVE_RADIUS) + B
    assert rc > 0 and RIB_DEPTH - (rc + GROOVE_RADIUS) * (1 - math.cos(b)) > 0
    return rc, pitch, b


def front_profile():
    """Front surface y = f(rho) for rho in [0, R], ending on the outer side wall."""
    rc, p, b = rib_geometry()
    rg, d = GROOVE_RADIUS, RIB_DEPTH
    pts = []
    for i in range(N_RIBS):
        g = i * p                       # groove centre
        c = g + p / 2                   # crest centre
        a_start = 0.0 if i == 0 else -b  # centre groove is mirrored
        # groove bottom: centre (g, d - rg), deepest point at y = d
        pts += _arc(g, d - rg, rg, a_start, b, 6 if i == 0 else 10)
        if i < N_RIBS - 1:
            # rib crest: centre (c, rc), front-most point at y = 0
            pts += [(c + rc * math.sin(a), rc - rc * math.cos(a))
                    for a in np.linspace(-b, b, 22)]
        else:
            # last crest wraps round into the side wall -> rounded outer edge
            pts += [(c + rc * math.sin(a), rc - rc * math.cos(a))
                    for a in np.linspace(-b, math.pi / 2, 34)]
    out = [pts[0]]
    for q in pts[1:]:
        if math.dist(q, out[-1]) > 1e-4:
            out.append(q)
    out[-1] = (R, out[-1][1])
    return out


def profile_section(d_max=None):
    """Rib section in the (d, y) plane: d = distance in from the outline edge
    (0 = outer edge, R = centre groove), y = depth; ribs on BOTH faces."""
    front = [(R - rho, y) for rho, y in front_profile()]          # d: R -> 0
    back = [(d, PLATE_DEPTH - y) for d, y in reversed(front)]      # d: 0 -> R
    poly = front + back
    sec = CrossSection([poly])
    if sec.area() <= 0:                                            # make it CCW
        sec = CrossSection([poly[::-1]])
    if d_max is not None and d_max < R:                            # arcs: r >= 0
        sec = sec ^ CrossSection.square([d_max, PLATE_DEPTH + 2]).translate([0, -1])
    return sec.simplify(0.005)


# --------------------------------------------------------------------------
# Outline shapes.  Every shape is symmetric and described by its LEFT half
# (x <= 0) as a list of edges, each with the region ("cell") of the plate
# where that edge is the nearest one.  Inside its cell the ribs are the
# rib section swept along the edge (straight edge -> extrusion, arc ->
# revolve), so all ribs follow the outline as exact concentric offsets.
# --------------------------------------------------------------------------
class Line:
    def __init__(self, a, b):
        """Edge from a to b (2D points in the x/z plane), interior on its right."""
        self.a = np.array(a, float)
        t = np.array(b, float) - self.a
        self.t = t / np.linalg.norm(t)
        self.n = np.array([self.t[1], -self.t[0]])                 # inward normal

    def dist(self, p):
        return float(self.n @ (np.asarray(p, float) - self.a))

    def halfplane_closer_than(self, other):
        """a.x + b.z <= c  where this edge is at least as close as `other`."""
        g = self.n - other.n
        return g[0], g[1], float(self.n @ self.a - other.n @ other.a)

    def solid(self, sec):
        m = Manifold.extrude(sec, 1000.0)                          # (d, y, e)
        n, t = self.n, self.t
        o = self.a - 500.0 * t
        return m.transform([[n[0], 0, t[0], o[0]],
                            [0, 1, 0, 0],
                            [n[1], 0, t[1], o[1]]])


class Arc:
    def __init__(self, c, r, a0, a1):
        """Convex arc, centre c, radius r, from angle a0 to a1 (deg, from +x
        toward +z); the plate lies inside the circle."""
        self.c, self.r, self.a0, self.a1 = np.array(c, float), r, a0, a1

    def solid(self, sec_r):
        a0, a1 = self.a0 - 2, self.a1 + 2                         # clipped later
        seg = max(8, int(math.ceil((a1 - a0) / 0.9)))
        m = Manifold.revolve(sec_r, seg, a1 - a0)                  # (r cos, r sin, y)
        m = m.rotate([90, 0, 0]).mirror([0, 1, 0])                 # (r cos, y, r sin)
        m = m.rotate([0, -a0, 0])                                  # start at angle a0
        return m.translate([self.c[0], 0, self.c[1]])


def clip_polygon(poly, a, b, c):
    """Sutherland-Hodgman: keep the part of convex `poly` with a*x + b*z <= c."""
    out = []
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        fp, fq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
        if fp <= 0:
            out.append(p)
        if fp * fq < 0:
            s = fp / (fp - fq)
            out.append((p[0] + s * (q[0] - p[0]), p[1] + s * (q[1] - p[1])))
    return out


def cell(*halfplanes):
    """Convex cell in the left half (x <= 0, z >= 0) cut by halfplanes a,b,c."""
    poly = [(-R - 5, 0), (0, 0), (0, HEIGHT + 5), (-R - 5, HEIGHT + 5)]
    for hp in halfplanes:
        poly = clip_polygon(poly, *hp)
    return poly


def cell_prism(poly, overlap=0.02):
    """Cell as a prism through the plate; grown a hair so neighbours overlap
    (no coincident seam faces -> clean unions)."""
    cs = CrossSection([poly]).offset(overlap, JoinType.Miter, 4.0)
    m = Manifold.extrude(cs, PLATE_DEPTH + 2)                       # (x, z, e)
    return m.rotate([90, 0, 0]).translate([0, PLATE_DEPTH + 1, 0])


def lines_only(lines):
    """Cells for an outline made only of straight edges (exact bisectors)."""
    return [(ln, cell(*[ln.halfplane_closer_than(o) for o in lines if o is not ln]))
            for ln in lines]


H = HEIGHT


def shape_arch():
    """Rainbow arch: straight sides + semicircle."""
    h = H - R
    return [(Line((-R, 0), (-R, h)), cell((0, 1, h))),
            (Arc((0, h), R, 90, 180), cell((0, -1, -h)))]


def shape_pointed_arch(k=0.75):
    """Pointed (Moroccan / gothic) arch: two arcs whose centres sit k*R
    across the centre line, meeting in a point."""
    c = k * R
    ra = R + c
    rise = math.sqrt(ra * ra - c * c)
    h = H - rise
    apex = math.degrees(math.atan2(rise, -c))
    return [(Line((-R, 0), (-R, h)), cell((0, 1, h))),
            (Arc((c, h), ra, apex, 180), cell((0, -1, -h)))]


def shape_house(roof_deg=38.0):
    """House: straight walls + pitched roof."""
    h = H - R * math.tan(math.radians(roof_deg))
    return lines_only([Line((-R, 0), (-R, h)), Line((-R, h), (0, H))])


def shape_mountain():
    """Mountain / tree: a single peak, chevron ribs."""
    return lines_only([Line((-R, 0), (0, H))])


def shape_tablet(rc=30.0):
    """Tablet: straight walls, rounded top corners, flat top."""
    xc, zc = -R + rc, H - rc
    wall = Line((-R, 0), (-R, zc))
    top = Line((xc, H), (0, H))
    return [(wall, cell((0, 1, zc), (1, 1, H - R))),
            (Arc((xc, zc), rc, 90, 180), cell((1, 0, xc), (0, -1, -zc))),
            (top, cell((-1, 0, -xc), (-1, -1, -(H - R))))]


def shape_octagon(k=38.0):
    """Octagon top: straight walls, 45 deg chamfers, flat top."""
    return lines_only([Line((-R, 0), (-R, H - k)), Line((-R, H - k), (-R + k, H)),
                       Line((-R + k, H), (0, H))])


SHAPES = {
    "arch": shape_arch,
    "pointed_arch": shape_pointed_arch,
    "house": shape_house,
    "mountain": shape_mountain,
    "tablet": shape_tablet,
    "octagon": shape_octagon,
}


def plate(shape="arch"):
    sec = profile_section()
    pieces = []
    for edge, poly in SHAPES[shape]():
        if isinstance(edge, Arc):
            s = profile_section(d_max=edge.r)
            # section in (r, y) with r = arc radius - d
            s = s.mirror([1, 0]).translate([edge.r, 0])
            body = edge.solid(s)
        else:
            body = edge.solid(sec)
        pieces.append(body ^ cell_prism(poly))
    half = Manifold.batch_boolean(pieces, OpType.Add)
    full = half + half.mirror([1, 0, 0])
    # mitred seams can leave zero-volume slivers as separate shells: drop them
    solids = [c for c in full.decompose() if c.volume() > 1.0]
    return Manifold.batch_boolean(solids, OpType.Add)


def rounded_rect(x0, x1, y0, y1, radii, n=24):
    """Convex rounded rectangle; radii = (r_x0y0, r_x1y0, r_x1y1, r_x0y1)."""
    corners = [((x0, y0), (1, 1), math.pi), ((x1, y0), (-1, 1), 1.5 * math.pi),
               ((x1, y1), (-1, -1), 0.0), ((x0, y1), (1, -1), 0.5 * math.pi)]
    pts = []
    for ((cx, cy), (sx, sy), a0), r in zip(corners, radii):
        if r <= 1e-9:
            pts.append((cx, cy))
            continue
        ox, oy = cx + sx * r, cy + sy * r
        for a in np.linspace(a0, a0 + math.pi / 2, n):
            pts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    return pts


def prism_hull(rings):
    """Convex loft through a list of (z, 2D points) rings."""
    pts = [(x, y, z) for z, ring in rings for x, y in ring]
    return Manifold.hull_points(pts)


def base_frame():
    """Hollow skeleton base: chamfered slab minus a large lightening window."""
    y0 = 5.0                         # front edge hidden inside the plate
    y1 = BASE_DEPTH
    T, c, f = BASE_THICK, TOP_CHAMFER, FOOT_CHAMFER
    rr = (0, 0, BASE_CORNER_R, BASE_CORNER_R)

    def outer(d):                    # inset by d
        r = tuple(max(x - d, 0) for x in rr)
        return rounded_rect(-R + d, R - d, y0 + d, y1 - d, r)

    slab = prism_hull([(0, outer(f)), (f, outer(0)), (T - c, outer(0)), (T, outer(c))])

    wx0, wx1 = -R + BASE_SIDE, R - BASE_SIDE
    wy0, wy1 = PLATE_DEPTH + BASE_FRONT_BAR, BASE_DEPTH - BASE_SIDE

    def window(d):                   # grown by d
        r = WINDOW_CORNER_R + d
        return rounded_rect(wx0 - d, wx1 + d, wy0 - d, wy1 + d, (r, r, r, r))

    cut = (prism_hull([(-0.1, window(f + 0.1)), (f, window(0))]) +
           prism_hull([(f, window(0)), (T - c, window(0))]) +
           prism_hull([(T - c, window(0)), (T + 0.1, window(c + 0.1))]))
    return slab - cut


def build(shape="arch"):
    return plate(shape) + base_frame()


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------
def mesh_arrays(m):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3].astype(np.float64)
    f = np.asarray(mesh.tri_verts).astype(np.int64)
    return v, f


def write_stl(path, v, f, name="book_divider"):
    tri = v[f]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    data = np.zeros(len(f), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    data["n"], data["v"] = n, tri
    with open(path, "wb") as fh:
        fh.write(name.encode().ljust(80, b" ")[:80])
        fh.write(struct.pack("<I", len(f)))
        fh.write(data.tobytes())


def write_3mf(path, objects, title="Arch Book Divider"):
    """objects: list of (name, vertices, faces); geometry is written in place."""
    res, items = [], []
    for i, (name, v, f) in enumerate(objects, start=1):
        verts = "\n".join(f'<vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in v)
        tris = "\n".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in f)
        res.append(f'<object id="{i}" type="model" name="{name}">\n<mesh>\n<vertices>\n'
                   f'{verts}\n</vertices>\n<triangles>\n{tris}\n</triangles>\n</mesh>\n</object>')
        items.append(f'<item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>')
    nl = "\n"
    model = f"""<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
<metadata name="Title">{title}</metadata>
<metadata name="Designer">Parametric generator (book_divider.py)</metadata>
<metadata name="Description">Filament-optimized arch book divider. Print upright, no supports.</metadata>
<resources>
{nl.join(res)}
</resources>
<build>
{nl.join(items)}
</build>
</model>
"""
    ctypes = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>
"""
    rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>
"""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)


def centred(part):
    """Mesh with the footprint centred on the origin and the base on z = 0."""
    v, f = mesh_arrays(part)
    lo, hi = v.min(0), v.max(0)
    return v - [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]], f


def pair_layout(v, f, gap=PAIR_GAP):
    """Two copies for one print: each turned 90 deg (arch along Y, base pointing
    +X) and placed side by side along X -> 218 x 135 mm footprint."""
    rot = np.column_stack([v[:, 1], -v[:, 0], v[:, 2]])     # -90 deg about Z
    dx = (rot[:, 0].max() - rot[:, 0].min() + gap) / 2
    return [rot + [-dx, 0, 0], rot + [dx, 0, 0]], f


NAMES = {
    "arch": "Arch", "pointed_arch": "Pointed Arch", "house": "House",
    "mountain": "Mountain", "tablet": "Tablet", "octagon": "Octagon",
}


def export_shape(shape, out_dir):
    """<shape>.stl, <shape>.3mf and <shape>_x2.3mf (pair laid out on one plate)."""
    part = build(shape)
    v, f = centred(part)
    title = f"{NAMES[shape]} Book Divider"
    write_stl(os.path.join(out_dir, f"{shape}.stl"), v, f, name=shape)
    write_3mf(os.path.join(out_dir, f"{shape}.3mf"), [(title, v, f)], title=title)
    (va, vb), _ = pair_layout(v, f)
    write_3mf(os.path.join(out_dir, f"{shape}_x2.3mf"),
              [(title + " A", va, f), (title + " B", vb, f)], title=title + " - pair")
    return part, v, f


if __name__ == "__main__":
    import sys
    shapes = sys.argv[1:] or list(SHAPES)
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    os.makedirs(out_dir, exist_ok=True)
    rc, pitch, _ = rib_geometry()
    print(f"rib crest radius {rc:.2f} mm, pitch {pitch:.2f} mm")
    for shape in shapes:
        part, v, f = export_shape(shape, out_dir)
        size = v.max(0) - v.min(0)
        print(f"{shape:13s} {size[0]:.0f} x {size[1]:.0f} x {size[2]:.0f} mm, "
              f"{len(f)} triangles, genus {part.genus()}, {part.status()}")
