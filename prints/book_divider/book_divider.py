"""
Filament-optimized arch book divider / bookend - parametric generator.

Outputs a watertight, print-ready mesh as STL and 3MF (units: mm).

Design:
  * Arch plate 135 x 155 mm with 7 concentric "rainbow" ribs, 3 mm deep, on
    BOTH faces (front and back look the same; books rest on the rib crests).
  * The arch is a CLOSED solid, modelled solid on purpose so the slicer fills
    it with light sparse infill (the cheapest way to make a closed shape).
  * Only the BASE is hollowed: a skeleton frame with a large lightening window
    and chamfered edges.
  * All rib flanks are limited to <= 48 deg from vertical, so the ribs print
    cleanly even where they run horizontally over the top of the arch ->
    the part prints upright with NO supports.

Print orientation: as modelled (base flat on the bed, arch standing up).

Run:  python book_divider.py            (needs: pip install manifold3d numpy)
"""

import math
import os
import struct
import zipfile

import numpy as np
from manifold3d import CrossSection, Manifold

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

ARC_SEGMENTS = 200      # segments over the 180 deg top arc
PAIR_GAP = 8.0          # gap between the two parts in the pair file

R = WIDTH / 2.0                 # arch outer radius
H_LEG = HEIGHT - R              # height of the straight legs (arc centre z)


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


def plate_section():
    """Full (mirrored) plate section, rho in [-R, R], ribs on BOTH faces."""
    half = front_profile()
    left = [(-x, y) for x, y in reversed(half) if x > 1e-9]
    front = left + half                                  # rho: -R -> R
    back = [(x, PLATE_DEPTH - y) for x, y in reversed(front)]   # rho: R -> -R
    return CrossSection([front + back]).simplify(0.005)


def right_half(sec):
    return sec ^ CrossSection.square([R + 5, PLATE_DEPTH + 10]).translate([0, -5])


# --------------------------------------------------------------------------
# 3D assembly
# --------------------------------------------------------------------------
def arch_solid(sec):
    """Sweep a (rho, y) section along the arch: two straight legs + 180 deg arc."""
    legs = Manifold.extrude(sec, H_LEG)                     # (x=rho, y, z)
    top = Manifold.revolve(right_half(sec), ARC_SEGMENTS, 180.0)
    top = top.rotate([90, 0, 0]).mirror([0, 1, 0]).translate([0, 0, H_LEG])
    return legs + top


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


def build():
    return arch_solid(plate_section()) + base_frame()


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


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    rc, pitch, _ = rib_geometry()
    part = build()
    v, f = centred(part)
    write_stl(os.path.join(out_dir, "book_divider.stl"), v, f)
    write_3mf(os.path.join(out_dir, "book_divider.3mf"), [("Book Divider", v, f)])

    (va, vb), _ = pair_layout(v, f)
    write_3mf(os.path.join(out_dir, "book_divider_x2.3mf"),
              [("Book Divider A", va, f), ("Book Divider B", vb, f)],
              title="Arch Book Divider - pair")
    write_stl(os.path.join(out_dir, "book_divider_x2.stl"),
              np.vstack([va, vb]), np.vstack([f, f + len(va)]))

    size = v.max(0) - v.min(0)
    both = np.vstack([va, vb])
    psize = both.max(0) - both.min(0)
    print(f"rib crest radius {rc:.2f} mm, pitch {pitch:.2f} mm")
    print(f"triangles {len(f)}, genus {part.genus()}, status {part.status()}")
    print(f"size  X {size[0]:.2f}  Y {size[1]:.2f}  Z {size[2]:.2f} mm")
    print(f"pair footprint  X {psize[0]:.1f}  Y {psize[1]:.1f} mm")
    print("written book_divider(.stl/.3mf) and book_divider_x2(.stl/.3mf)")
