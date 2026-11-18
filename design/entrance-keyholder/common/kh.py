"""
Shared geometry for the entrance key-holder designs.

Units are millimetres. Assembly frame (used for renders):
    X = across the wall (left -> right), Y = up, Z = out of the wall.
The wall is the plane Z = 0.
"""

import math
import os

import numpy as np
import shapely
import trimesh
import uharfbuzz as hb
from fontTools.pens.basePen import BasePen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.geometry import box as sbox
from shapely.ops import nearest_points, unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "fonts")

FONT_NASKH = os.path.join(FONTS, "AmiriQuran-Regular-arabic.ttf")
FONT_RUQAA = os.path.join(FONTS, "ArefRuqaa-Bold-arabic.ttf")
FONT_KUFI = os.path.join(FONTS, "ReemKufi-Bold-arabic.ttf")

# Ad-Duha 93:5
VERSE_PLAIN = "ولسوف يعطيك ربك فترضى"
VERSE_LINE1 = "وَلَسَوْفَ يُعْطِيكَ"
VERSE_LINE2 = "رَبُّكَ فَتَرْضَىٰ"
VERSE_FULL = VERSE_LINE1 + " " + VERSE_LINE2


# ----------------------------------------------------------------------------
# 2D helpers
# ----------------------------------------------------------------------------
def polys(geom):
    """Iterate the polygons of a (Multi)Polygon / GeometryCollection."""
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    out = []
    for g in getattr(geom, "geoms", []):
        out.extend(polys(g))
    return out


def rounded_rect(x0, y0, x1, y1, r):
    if r <= 0:
        return sbox(x0, y0, x1, y1)
    return sbox(x0 + r, y0 + r, x1 - r, y1 - r).buffer(r, quad_segs=16)


def circle(cx, cy, r, segs=256):
    return Point(cx, cy).buffer(r, quad_segs=segs // 4)


def pointed_arch(width, height, point=0.10, corner_r=3.0, segs=160):
    """Islamic two-centred (slightly pointed) arch standing on y = 0, centred on x = 0.

    `point` is the offset of each arc centre from the axis, as a fraction of the width
    (0 gives a round arch, larger values give a sharper point)."""
    half = width / 2.0
    d = point * width
    R = half + d
    theta_apex = math.acos(-d / R)          # angle of the apex seen from the right-hand centre
    h_arch = R * math.sin(theta_apex)
    ys = height - h_arch                    # springing line
    pts = [(-half, 0.0), (half, 0.0), (half, ys)]
    # right arc: centre (-d, ys), from angle 0 up to the apex
    th_r = math.acos(d / R)
    for t in np.linspace(0, th_r, segs):
        pts.append((-d + R * math.cos(t), ys + R * math.sin(t)))
    # left arc: centre (+d, ys), from the apex down to angle pi
    for t in np.linspace(theta_apex, math.pi, segs):
        pts.append((d + R * math.cos(t), ys + R * math.sin(t)))
    poly = Polygon(pts).buffer(0)
    if corner_r > 0:
        poly = poly.buffer(-corner_r, join_style="round").buffer(corner_r, join_style="round")
    return poly, ys


def outline(geom, inset, width):
    """A thin ring `width` wide, `inset` inside the outline of geom."""
    a = geom.buffer(-inset, join_style="mitre")
    b = geom.buffer(-inset - width, join_style="mitre")
    return a.difference(b)


def eight_point_star(cx, cy, r, line_w=None):
    """Rub el Hizb style 8-point star (two squares). Solid, or an outline if line_w."""
    sq = sbox(-r, -r, r, r)
    star = unary_union([sq, affinity.rotate(sq, 45, origin=(0, 0))])
    star = affinity.translate(star, cx, cy)
    if line_w:
        return star.difference(star.buffer(-line_w, join_style="mitre"))
    return star


# ----------------------------------------------------------------------------
# Text: shape with HarfBuzz, outline with fontTools
# ----------------------------------------------------------------------------
class _FlattenPen(BasePen):
    def __init__(self, glyph_set, steps=14):
        super().__init__(glyph_set)
        self.steps = steps
        self.contours = []
        self._cur = None

    def _moveTo(self, p):
        self._cur = [p]

    def _lineTo(self, p):
        self._cur.append(p)

    def _curveToOne(self, p1, p2, p3):
        p0 = self._cur[-1]
        for i in range(1, self.steps + 1):
            t = i / self.steps
            m = 1 - t
            self._cur.append((
                m ** 3 * p0[0] + 3 * m * m * t * p1[0] + 3 * m * t * t * p2[0] + t ** 3 * p3[0],
                m ** 3 * p0[1] + 3 * m * m * t * p1[1] + 3 * m * t * t * p2[1] + t ** 3 * p3[1]))

    def _qCurveToOne(self, p1, p2):
        p0 = self._cur[-1]
        for i in range(1, self.steps + 1):
            t = i / self.steps
            m = 1 - t
            self._cur.append((m * m * p0[0] + 2 * m * t * p1[0] + t * t * p2[0],
                              m * m * p0[1] + 2 * m * t * p1[1] + t * t * p2[1]))

    def _closePath(self):
        if self._cur and len(self._cur) >= 3:
            self.contours.append(self._cur)
        self._cur = None

    _endPath = _closePath


def _signed_area(pts):
    x = np.array([p[0] for p in pts])
    y = np.array([p[1] for p in pts])
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _glyph_geometry(contours):
    """Non-zero fill of one glyph's contours (handles overlaps, holes and islands)."""
    items = [(abs(_signed_area(c)), np.sign(_signed_area(c)), c) for c in contours if len(c) >= 3]
    items = [it for it in items if it[0] > 1e-6]
    if not items:
        return Polygon()
    items.sort(key=lambda it: -it[0])
    outer_sign = items[0][1]
    g = Polygon()
    for _, s, c in items:
        p = Polygon(c).buffer(0)
        g = g.union(p) if s == outer_sign else g.difference(p)
    return g


def shape_text(text, font_path, em_mm=None, width_mm=None, features=None):
    """Return (geometry, info) for `text` set in `font_path`.

    The geometry is in mm, baseline on y = 0, horizontally centred on x = 0.
    Give either em_mm (font size) or width_mm (scale the inked width to this)."""
    blob = hb.Blob.from_file_path(font_path)
    font = hb.Font(hb.Face(blob))
    buf = hb.Buffer()
    buf.add_str(text)
    buf.direction = "rtl"
    buf.script = "Arab"
    buf.language = "ar"
    hb.shape(font, buf, features or {"kern": True, "liga": True, "calt": True})

    tt = TTFont(font_path)
    upem = tt["head"].unitsPerEm
    gs = tt.getGlyphSet()
    pen_x = 0.0
    parts = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        pen = _FlattenPen(gs)
        gs[tt.getGlyphName(info.codepoint)].draw(
            TransformPen(pen, (1, 0, 0, 1, pen_x + pos.x_offset, pos.y_offset)))
        pen_x += pos.x_advance
        g = _glyph_geometry(pen.contours)
        if not g.is_empty:
            parts.append(g)
    geom = unary_union(parts)
    minx, miny, maxx, maxy = geom.bounds
    if width_mm is not None:
        s = width_mm / (maxx - minx)
    else:
        s = em_mm / upem
    geom = affinity.translate(geom, -(minx + maxx) / 2.0, 0)
    geom = affinity.scale(geom, s, s, origin=(0, 0))
    b = geom.bounds
    return geom, {"scale": s, "em_mm": s * upem, "bounds": b,
                  "width": b[2] - b[0], "height": b[3] - b[1]}


def warp_to_arc(geom, radius, centre=(0.0, 0.0), theta_mid=math.pi / 2, step=0.35):
    """Bend text laid along y = 0 onto a circle of `radius` (baseline on the circle),
    reading clockwise across the top, letters pointing outward."""
    geom = shapely.segmentize(geom, step)

    def f(x, y, z=None):
        x = np.asarray(x)
        y = np.asarray(y)
        th = theta_mid - x / radius
        r = radius + y
        return centre[0] + r * np.cos(th), centre[1] + r * np.sin(th)

    return shapely.ops.transform(f, geom).buffer(0)


def connect_islands(geom, width=1.6, anchor=None):
    """Join every separate piece of `geom` to the main body with short bridges so a
    cut-out stays in one piece. `anchor` (optional) is geometry that counts as main."""
    pieces = polys(geom)
    main = unary_union([anchor] if anchor is not None else []) if anchor is not None else None
    pieces.sort(key=lambda p: -p.area)
    if main is None:
        main = pieces.pop(0)
    else:
        main = main.union(Polygon())
    pending = [p for p in pieces if not p.intersects(main)]
    main = unary_union([main] + [p for p in pieces if p.intersects(main)])
    bridges = []
    while pending:
        best = None
        for i, p in enumerate(pending):
            a, b = nearest_points(p, main)
            d = a.distance(b)
            if best is None or d < best[0]:
                best = (d, i, a, b)
        d, i, a, b = best
        p = pending.pop(i)
        # Extend slightly into both shapes so the bridge overlaps them.
        v = np.array([b.x - a.x, b.y - a.y])
        n = np.linalg.norm(v) or 1.0
        v = v / n
        a2 = (a.x - v[0] * 0.6, a.y - v[1] * 0.6)
        b2 = (b.x + v[0] * 0.6, b.y + v[1] * 0.6)
        br = LineString([a2, b2]).buffer(width / 2.0, cap_style="flat")
        bridges.append(br)
        main = unary_union([main, p, br])
        still = [q for q in pending if not q.intersects(main)]
        main = unary_union([main] + [q for q in pending if q.intersects(main)])
        pending = still
    return main, bridges


# ----------------------------------------------------------------------------
# 3D helpers
# ----------------------------------------------------------------------------
def extrude(geom, z0, z1):
    """Extrude 2D geometry (XY) between z0 and z1. Disjoint polygons are concatenated."""
    meshes = []
    for p in polys(geom):
        if p.area < 1e-4:
            continue
        m = trimesh.creation.extrude_polygon(p, height=z1 - z0)
        m.apply_translation([0, 0, z0])
        meshes.append(m)
    return trimesh.util.concatenate(meshes)


def union(meshes):
    meshes = [m for m in meshes if m is not None and len(m.faces)]
    if len(meshes) == 1:
        return meshes[0]
    return trimesh.boolean.union(meshes, engine="manifold")


def difference(a, cutters):
    cutters = [c for c in cutters if c is not None and len(c.faces)]
    if not cutters:
        return a
    return trimesh.boolean.difference([a, union(cutters)], engine="manifold")


def box3(x0, x1, y0, y1, z0, z1):
    m = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0])
    m.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return m


def cyl_z(x, y, r, z0, z1, sections=64):
    m = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=sections)
    m.apply_translation([x, y, (z0 + z1) / 2])
    return m


def cone_z(x, y, r0, z0, r1, z1, sections=64):
    """Frustum along Z from radius r0 at z0 to r1 at z1."""
    prof = [(0, z0), (r0, z0), (r1, z1), (0, z1)]
    m = trimesh.creation.revolve(np.array(prof), sections=sections)
    m.apply_translation([x, y, 0])
    if m.volume < 0:
        m.invert()
    return m


def extrude_y(geom_xz, y0, y1):
    """Extrude 2D geometry drawn in the (X, Z) plane upward along Y from y0 to y1."""
    m = extrude(geom_xz, 0, y1 - y0)
    v = m.vertices
    out = trimesh.Trimesh(np.column_stack([v[:, 0], y0 + v[:, 2], v[:, 1]]),
                          m.faces[:, ::-1], process=True)
    if out.volume < 0:
        out.invert()
    return out


def heightfield_solid(x0, x1, y0, y1, step_x, step_y, height_fn):
    """Watertight solid with a flat bottom on z = 0 and its top at z = height_fn(X, Y)
    (vectorised, all heights > 0), over the rectangle [x0, x1] x [y0, y1]."""
    xs = np.linspace(x0, x1, int(round((x1 - x0) / step_x)) + 1)
    ys = np.linspace(y0, y1, int(round((y1 - y0) / step_y)) + 1)
    X, Y = np.meshgrid(xs, ys)
    Z = height_fn(X, Y)
    ny, nx = X.shape
    top = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    bot = np.column_stack([X.ravel(), Y.ravel(), np.zeros(X.size)])
    verts = np.vstack([top, bot])
    n = X.size
    idx = np.arange(n).reshape(ny, nx)
    a, b = idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel()
    c, d = idx[1:, :-1].ravel(), idx[1:, 1:].ravel()
    faces = [np.column_stack([a, b, d]), np.column_stack([a, d, c]),            # top (up)
             np.column_stack([a + n, d + n, b + n]), np.column_stack([a + n, c + n, d + n])]

    def wall(edge, flip):
        e0, e1 = edge[:-1], edge[1:]
        f = [np.column_stack([e0, e0 + n, e1 + n]), np.column_stack([e0, e1 + n, e1])]
        return [ff[:, ::-1] for ff in f] if flip else f
    faces += wall(idx[0, :], False)        # y = y0 edge
    faces += wall(idx[-1, :], True)        # y = y1 edge
    faces += wall(idx[:, 0], True)         # x = x0 edge
    faces += wall(idx[:, -1], False)       # x = x1 edge
    m = trimesh.Trimesh(verts, np.vstack(faces), process=True)
    trimesh.repair.fix_normals(m)
    if m.volume < 0:
        m.invert()
    return m


def profile_x(profile_zy, x0, x1):
    """Prism along X from a closed 2D profile given as (z, y) points."""
    poly = Polygon(profile_zy).buffer(0)
    m = trimesh.creation.extrude_polygon(poly, height=x1 - x0)
    v = m.vertices
    out = trimesh.Trimesh(np.column_stack([x0 + v[:, 2], v[:, 1], v[:, 0]]),
                          m.faces[:, ::-1], process=True)
    if out.volume < 0:
        out.invert()
    return out


# --- fasteners -------------------------------------------------------------
PEG_HOLE_D = 8.4      # hole in the panel for the peg tenon (0.2 mm glue gap)
PEG_TENON_D = 8.0
PEG_TENON_L = 5.5


def peg_hole(x, y, z_front, depth=6.0):
    """Blind hole from the front face for a peg tenon."""
    return cyl_z(x, y, PEG_HOLE_D / 2, z_front - depth, z_front + 1)


def keyhole_cutter(x, y, slot_len=10.0, head_d=9.6, shank_w=4.6, z_shank=2.2, z_head=4.6):
    """Keyhole hanger cut into the back face (Z = 0). The screw head enters at (x, y)
    and the piece drops so the screw ends at the top of the slot (y + slot_len)."""
    parts = []
    entry = cyl_z(x, y, head_d / 2, -1.0, z_head)
    parts.append(entry)
    shank = extrude(LineString([(x, y), (x, y + slot_len)]).buffer(shank_w / 2), -1.0, z_shank + 0.01)
    head = extrude(LineString([(x, y), (x, y + slot_len)]).buffer(head_d / 2), z_shank, z_head)
    parts += [shank, head]
    return union(parts)


def screw_from_back(x, y, length, shaft_d=3.4, head_d=6.6, sink=1.7):
    """Through hole with the countersink on the back face (Z = 0); for screws that go
    from behind a panel into a part in front of it."""
    shaft = cyl_z(x, y, shaft_d / 2, -1.0, length + 0.01)
    head = cone_z(x, y, head_d / 2, -0.01, shaft_d / 2, sink)
    under = cyl_z(x, y, head_d / 2, -1.0, 0.0)
    return union([shaft, head, under])


def countersunk_front(x, y, z_front, shaft_d=4.4, head_d=8.8, z_back=-1.0):
    """Wall screw: countersink on the front face at z_front."""
    shaft = cyl_z(x, y, shaft_d / 2, z_back, z_front + 1)
    head = cone_z(x, y, shaft_d / 2, z_front - (head_d - shaft_d) / 2, head_d / 2, z_front)
    top = cyl_z(x, y, head_d / 2, z_front, z_front + 1)
    return union([shaft, head, top])


def pilot_hole_z(x, y, z_start, depth, d=2.6):
    return cyl_z(x, y, d / 2, z_start - 0.01, z_start + depth)


def make_peg(length=30.0, shaft_d=10.5, cap_d=14.0, cap_t=3.0):
    """Key peg printed standing on its flat cap (no supports). Returned in print
    orientation: cap face on z = 0, tenon at the top."""
    r_s, r_c, r_t = shaft_d / 2, cap_d / 2, PEG_TENON_D / 2
    ch = 0.6
    z = 0.0
    prof = [(0, 0), (r_c - ch, 0), (r_c, ch), (r_c, cap_t)]
    z = cap_t + (r_c - r_s)                       # 45-degree transition into the shaft
    prof.append((r_s, z))
    z_sh = cap_t + length
    prof.append((r_s, z_sh))
    prof.append((r_t, z_sh))                      # shoulder that seats against the panel
    prof.append((r_t, z_sh + PEG_TENON_L - 0.5))
    prof.append((r_t - 0.5, z_sh + PEG_TENON_L))  # lead-in chamfer
    prof.append((0, z_sh + PEG_TENON_L))
    m = trimesh.creation.revolve(np.array(prof), sections=72)
    if m.volume < 0:
        m.invert()
    return m, z_sh   # z_sh = distance from cap face to the shoulder


def peg_in_place(x, y, z_front, **kw):
    """The peg positioned on the assembly: shoulder touching the panel face at z_front."""
    m, z_sh = make_peg(**kw)
    m = m.copy()
    # print frame: axis +Z from cap (0) to tenon. Assembly: tenon points to -Z (into panel).
    m.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]))
    # now cap at z=0 and tenon toward -z; shoulder at z = -z_sh
    m.apply_translation([x, y, z_front + z_sh])
    return m


# ----------------------------------------------------------------------------
# Checks
# ----------------------------------------------------------------------------
def overhang_report(mesh, max_angle=45.0, ignore_below=0.3):
    """Area of downward faces steeper than max_angle (from vertical) in print orientation
    (Z up), ignoring faces lying on the bed."""
    n = mesh.face_normals
    c = mesh.triangles_center
    a = mesh.area_faces
    zmin = mesh.bounds[0][2]
    lim = -math.sin(math.radians(90 - max_angle))   # normal.z below this = overhang > max_angle
    steep = (n[:, 2] < lim) & (c[:, 2] > zmin + ignore_below)
    return float(a[steep].sum())


def part_report(name, mesh, bed=(220, 220, 250)):
    ext = mesh.extents
    fits = sorted(ext[:2]) <= sorted(bed[:2]) and ext[2] <= bed[2]
    return {
        "part": name,
        "watertight": bool(mesh.is_watertight),
        "size_mm": [round(float(v), 1) for v in ext],
        "fits_220_bed": bool(fits),
        "volume_cm3": round(float(mesh.volume) / 1000.0, 1),
        "overhang_mm2_over_45deg": round(overhang_report(mesh), 1),
    }


def thin_area_pct(geom2d, min_width=0.8):
    """Share of the 2D area that belongs to strokes thinner than min_width (an opening
    by min_width / 2 removes them). Small numbers mean the lettering prints cleanly with
    a 0.4 mm nozzle."""
    r = min_width / 2.0
    kept = geom2d.buffer(-r, quad_segs=8).buffer(r, quad_segs=8)
    return round(100.0 * (geom2d.area - kept.intersection(geom2d).area) / geom2d.area, 2)


def export(mesh, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mesh.export(path)


def write_outputs(here, assembly, prints, meta):
    """Write print-ready STLs (stl/), the assembled parts for renders (assembly/) and
    report.json with the checks."""
    import json
    rep = []
    for name, mesh in prints.items():
        export(mesh, os.path.join(here, "stl", name))
        rep.append(part_report(name, mesh))
    manifest = []
    for name, (mesh, mat) in assembly.items():
        export(mesh, os.path.join(here, "assembly", name + ".stl"))
        manifest.append({"file": f"{name}.stl", "material": mat})
    with open(os.path.join(here, "assembly", "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    with open(os.path.join(here, "report.json"), "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "parts": rep}, f, ensure_ascii=False, indent=1)
    return rep
