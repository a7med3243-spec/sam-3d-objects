"""
Entrance key & personal-items holder with the calligraphic phrase
"ولسوف يعطيك ربك فترضى" (Surah Ad-Duha 93:5), built as a 3D-printable model.

The model is written in millimetres in wall-mount orientation:
  X = across the wall (left -> right), Y = up, Z = out from the wall.
  The back face of the board sits on Z = 0.

Outputs (next to this script):
  keyholder.stl      - printable mesh
  keyholder_report.json - geometry checks used in the review

Run:  python3 build_keyholder.py
Requires: trimesh, manifold3d, shapely, mapbox-earcut, uharfbuzz, fonttools, numpy
"""

import json
import math
import os

import numpy as np
import trimesh
import uharfbuzz as hb
from fontTools.pens.basePen import BasePen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from shapely.affinity import translate
from shapely.geometry import Point, Polygon, box as shp_box
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(HERE, "fonts", "Amiri-Bold-arabic.ttf")
PHRASE = "ولسوف يعطيك ربك فترضى"

# ----------------------------------------------------------------------------
# Main dimensions (mm)
# ----------------------------------------------------------------------------
BOARD_W = 210.0      # overall width
BOARD_H = 122.0      # overall height
BOARD_T = 5.0        # back board thickness
BOARD_R = 14.0       # corner radius of the board

PLAQUE_X0, PLAQUE_X1 = 5.0, 205.0
PLAQUE_Y0, PLAQUE_Y1 = 90.0, 120.0    # 30 mm high stadium plaque
PLAQUE_T = 2.0                        # raised above board
RING_T = 1.0                          # thin decorative inner ring
TEXT_T = 2.0                          # raised calligraphy
TEXT_WIDTH = 170.0                    # target width of the phrase (~21 mm tall)

# Hooks (keys)
HOOK_X = [28.0, 58.0, 88.0]
HOOK_Y = 44.0
HOOK_POST_R = 4.0
HOOK_BASE_R = 6.0
HOOK_POST_TOP = 27.0                  # z where the post ends
HOOK_ARM_R = 3.2
HOOK_ARM_TIP = (33.0, 34.0)           # (z, y) of the arm tip

# Phone shelf (upper left)
SHELF_X0, SHELF_X1 = 0.0, 120.0
SHELF_Y0, SHELF_Y1 = 62.0, 67.0
SHELF_DEPTH = 50.0                    # how far it sticks out from the wall
LIP_Y1 = 75.0
LIP_T = 5.0

# Glasses tray (lower right)
TRAY_X0, TRAY_X1 = 125.0, 205.0
TRAY_FLOOR_Y0, TRAY_FLOOR_Y1 = 16.0, 20.0
TRAY_WALL_T = 4.0
TRAY_DEPTH = 45.0
TRAY_LIP_Y1 = 30.0
TRAY_LIP_Z0 = 41.0

GUSSET_T = 4.0
GUSSET_LEG = 14.0                     # 45 degree bracing legs

# Wall screws (countersunk). Two low ones carry the shelf and tray; two high ones
# stop the top of the board from levering off the wall under the weight.
# Each entry: (x, y, z_surface) where z_surface is the face the screw head sits on.
SCREW_POS = [
    (40.0, 9.0, BOARD_T),
    (170.0, 9.0, BOARD_T),
    (12.0, 105.0, BOARD_T + PLAQUE_T),   # through the plaque's rounded end
    (198.0, 105.0, BOARD_T + PLAQUE_T),
]
SCREW_R = 2.2
SCREW_HEAD_R = 4.4


# ----------------------------------------------------------------------------
# Geometry helpers
# ----------------------------------------------------------------------------
def rounded_rect(x0, y0, x1, y1, r):
    return shp_box(x0 + r, y0 + r, x1 - r, y1 - r).buffer(r, quad_segs=16)


def stadium(x0, y0, x1, y1):
    r = (y1 - y0) / 2.0
    return unary_union([
        Point(x0 + r, y0 + r).buffer(r, quad_segs=24),
        Point(x1 - r, y0 + r).buffer(r, quad_segs=24),
        shp_box(x0 + r, y0, x1 - r, y1),
    ])


def extrude_xy(poly, z0, z1):
    """Extrude a shapely (Multi)Polygon (XY plane) from z0 to z1."""
    geoms = list(poly.geoms) if hasattr(poly, "geoms") else [poly]
    meshes = []
    for g in geoms:
        if g.is_empty or g.area < 1e-6:
            continue
        m = trimesh.creation.extrude_polygon(g, height=z1 - z0)
        m.apply_translation([0, 0, z0])
        meshes.append(m)
    if len(meshes) == 1:
        return meshes[0]
    return trimesh.boolean.union(meshes, engine="manifold")


def box(x0, x1, y0, y1, z0, z1):
    m = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0])
    m.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return m


def prism_zy(points_zy, x0, x1):
    """Prism whose cross-section is given in the (Z, Y) plane, spanning X x0..x1."""
    poly = Polygon(points_zy)
    m = trimesh.creation.extrude_polygon(poly, height=x1 - x0)
    v = m.vertices
    # local (u, v, w) -> world (X = x0 + w, Y = v, Z = u)
    new_v = np.column_stack([x0 + v[:, 2], v[:, 1], v[:, 0]])
    faces = m.faces[:, ::-1]  # the axis swap mirrors the mesh; restore winding
    out = trimesh.Trimesh(new_v, faces, process=True)
    return out


def frustum(p0, r0, p1, r1, sections=48):
    """Solid between two circles whose axes are p0->p1 (convex hull)."""
    p0 = np.asarray(p0, float)
    p1 = np.asarray(p1, float)
    axis = p1 - p0
    axis /= np.linalg.norm(axis)
    tmp = np.array([1.0, 0, 0]) if abs(axis[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(axis, tmp)
    u /= np.linalg.norm(u)
    w = np.cross(axis, u)
    pts = []
    for ang in np.linspace(0, 2 * math.pi, sections, endpoint=False):
        d = math.cos(ang) * u + math.sin(ang) * w
        pts.append(p0 + d * r0)
        pts.append(p1 + d * r1)
    return trimesh.Trimesh(vertices=np.array(pts)).convex_hull


def capsule(p, q, r):
    p = np.asarray(p, float)
    q = np.asarray(q, float)
    parts = [
        trimesh.creation.icosphere(subdivisions=3, radius=r),
        trimesh.creation.icosphere(subdivisions=3, radius=r),
        trimesh.creation.cylinder(radius=r, segment=[p, q], sections=48),
    ]
    parts[0].apply_translation(p)
    parts[1].apply_translation(q)
    return trimesh.boolean.union(parts, engine="manifold")


def cylinder_z(x, y, r, z0, z1, sections=48):
    m = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=sections)
    m.apply_translation([x, y, (z0 + z1) / 2])
    return m


# ----------------------------------------------------------------------------
# Calligraphy: shape with HarfBuzz, outline with fontTools, flatten curves
# ----------------------------------------------------------------------------
class _FlattenPen(BasePen):
    def __init__(self, glyph_set, steps=10):
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
            mt = 1 - t
            x = mt**3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t**3 * p3[0]
            y = mt**3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t**3 * p3[1]
            self._cur.append((x, y))

    def _qCurveToOne(self, p1, p2):
        p0 = self._cur[-1]
        for i in range(1, self.steps + 1):
            t = i / self.steps
            mt = 1 - t
            x = mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0]
            y = mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1]
            self._cur.append((x, y))

    def _closePath(self):
        if self._cur and len(self._cur) >= 3:
            self.contours.append(self._cur)
        self._cur = None

    _endPath = _closePath


def _signed_area(pts):
    a = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        a += x0 * y1 - x1 * y0
    return a / 2.0


def phrase_polygon(text=PHRASE, font_path=FONT_PATH, width=TEXT_WIDTH):
    """Return a shapely (Multi)Polygon of the shaped phrase, scaled to `width` mm
    and centred on the origin."""
    blob = hb.Blob.from_file_path(font_path)
    hb_font = hb.Font(hb.Face(blob))
    buf = hb.Buffer()
    buf.add_str(text)
    buf.direction = "rtl"
    buf.script = "Arab"
    buf.language = "ar"
    hb.shape(hb_font, buf, {"kern": True, "liga": True, "calt": True})

    tt = TTFont(font_path)
    upem = tt["head"].unitsPerEm
    glyph_set = tt.getGlyphSet()

    # Lay the glyphs out along X in the visual order HarfBuzz returns.
    pen_x = 0.0
    glyph_polys = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = tt.getGlyphName(info.codepoint)
        flat = _FlattenPen(glyph_set, steps=10)
        tpen = TransformPen(flat, (1, 0, 0, 1, pen_x + pos.x_offset, pos.y_offset))
        glyph_set[name].draw(tpen)
        pen_x += pos.x_advance

        outers, holes = [], []
        for c in flat.contours:
            if len(c) < 3:
                continue
            (outers if _signed_area(c) < 0 else holes).append(Polygon(c).buffer(0))
        if outers:
            g = unary_union(outers)
            if holes:
                g = g.difference(unary_union(holes))
            glyph_polys.append(g)

    shape = unary_union(glyph_polys)
    minx, miny, maxx, maxy = shape.bounds
    s = width / (maxx - minx)
    shape = translate(shape, -(minx + maxx) / 2, -(miny + maxy) / 2)
    from shapely import affinity
    shape = affinity.scale(shape, s, s, origin=(0, 0))
    return shape, {"upem": upem, "glyphs": len(buf.glyph_infos), "scale": s}


# ----------------------------------------------------------------------------
# Build the model
# ----------------------------------------------------------------------------
def build():
    parts_add = []
    parts_cut = []

    # 1. Back board
    board_poly = rounded_rect(0, 0, BOARD_W, BOARD_H, BOARD_R)
    parts_add.append(extrude_xy(board_poly, 0, BOARD_T))

    # 2. Calligraphy plaque with a thin raised inner ring
    plaque = stadium(PLAQUE_X0, PLAQUE_Y0, PLAQUE_X1, PLAQUE_Y1)
    parts_add.append(extrude_xy(plaque, BOARD_T, BOARD_T + PLAQUE_T))
    ring = plaque.buffer(-3.0, quad_segs=24).difference(plaque.buffer(-3.0 - RING_T, quad_segs=24))
    parts_add.append(extrude_xy(ring, BOARD_T + PLAQUE_T, BOARD_T + PLAQUE_T + RING_T))

    # 3. Calligraphy (raised relief), centred on the plaque
    text, text_info = phrase_polygon()
    cx = (PLAQUE_X0 + PLAQUE_X1) / 2
    cy = (PLAQUE_Y0 + PLAQUE_Y1) / 2
    text = translate(text, cx, cy)
    text_z0 = BOARD_T + PLAQUE_T
    parts_add.append(extrude_xy(text, text_z0, text_z0 + TEXT_T))

    # 4. Key hooks: post + 45-degree base flare + rounded arm
    for x in HOOK_X:
        parts_add.append(frustum([x, HOOK_Y, BOARD_T - 0.01], HOOK_BASE_R,
                                 [x, HOOK_Y, BOARD_T + 6.0], HOOK_POST_R))
        parts_add.append(cylinder_z(x, HOOK_Y, HOOK_POST_R, BOARD_T, HOOK_POST_TOP))
        parts_add.append(capsule([x, HOOK_Y, HOOK_POST_TOP],
                                 [x, HOOK_ARM_TIP[1], HOOK_ARM_TIP[0]], HOOK_ARM_R))

    # 5. Phone shelf with front lip and two 45-degree braces
    z_out = BOARD_T + SHELF_DEPTH
    parts_add.append(box(SHELF_X0, SHELF_X1, SHELF_Y0, SHELF_Y1, BOARD_T - 0.01, z_out))
    parts_add.append(box(SHELF_X0, SHELF_X1, SHELF_Y1 - 0.01, LIP_Y1,
                         z_out - LIP_T, z_out))
    for gx in (12.0, SHELF_X1 - 12.0 - GUSSET_T):
        parts_add.append(prism_zy(
            [(BOARD_T - 0.01, SHELF_Y0), (BOARD_T - 0.01, SHELF_Y0 - GUSSET_LEG),
             (BOARD_T + GUSSET_LEG, SHELF_Y0)], gx, gx + GUSSET_T))

    # 6. Glasses tray: floor, side walls, front lip, braces
    tz1 = BOARD_T + TRAY_DEPTH
    parts_add.append(box(TRAY_X0, TRAY_X1, TRAY_FLOOR_Y0, TRAY_FLOOR_Y1,
                         BOARD_T - 0.01, tz1))
    parts_add.append(box(TRAY_X0, TRAY_X0 + TRAY_WALL_T, TRAY_FLOOR_Y0 - 0.01,
                         TRAY_LIP_Y1, BOARD_T - 0.01, tz1))
    parts_add.append(box(TRAY_X1 - TRAY_WALL_T, TRAY_X1, TRAY_FLOOR_Y0 - 0.01,
                         TRAY_LIP_Y1, BOARD_T - 0.01, tz1))
    parts_add.append(box(TRAY_X0, TRAY_X1, TRAY_FLOOR_Y1 - 0.01, TRAY_LIP_Y1,
                         TRAY_LIP_Z0, tz1))
    for gx in (140.0, TRAY_X1 - 15.0 - GUSSET_T):
        parts_add.append(prism_zy(
            [(BOARD_T - 0.01, TRAY_FLOOR_Y0), (BOARD_T - 0.01, TRAY_FLOOR_Y0 - GUSSET_LEG),
             (BOARD_T + GUSSET_LEG, TRAY_FLOOR_Y0)], gx, gx + GUSSET_T))

    model = trimesh.boolean.union(parts_add, engine="manifold")

    # 7. Countersunk wall-screw holes through the board
    for sx, sy, zs in SCREW_POS:
        shaft = cylinder_z(sx, sy, SCREW_R, -1.0, zs + 1.0)
        head = frustum([sx, sy, zs - 2.4], SCREW_R, [sx, sy, zs], SCREW_HEAD_R)
        head_top = cylinder_z(sx, sy, SCREW_HEAD_R, zs, zs + 1.0)
        parts_cut += [shaft, head, head_top]
    cutter = trimesh.boolean.union(parts_cut, engine="manifold")
    model = trimesh.boolean.difference([model, cutter], engine="manifold")
    model.merge_vertices()
    return model, text_info


def report(model, text_info):
    fa = model.face_normals
    areas = model.area_faces
    # Faces pointing down more than 45 degrees need support when printed in this orientation.
    steep = (fa[:, 1] < -math.cos(math.radians(45))) & (model.triangles_center[:, 1] > 0.5)
    overhang_area = float(areas[steep].sum())
    volume_cm3 = float(model.volume) / 1000.0
    pla_density = 1.24
    infill_factor = 0.30  # ~20% infill + walls/top/bottom, rough estimate
    mass_g = volume_cm3 * pla_density * infill_factor
    return {
        "watertight": bool(model.is_watertight),
        "winding_consistent": bool(model.is_winding_consistent),
        "volume_cm3": round(volume_cm3, 2),
        "bbox_mm": [round(float(v), 2) for v in model.extents],
        "triangles": int(len(model.faces)),
        "overhang_area_mm2": round(overhang_area, 1),
        "overhang_share_pct": round(100 * overhang_area / float(areas.sum()), 1),
        "est_mass_g_20pct_infill": round(mass_g, 1),
        "phrase": PHRASE,
        "phrase_glyphs": text_info["glyphs"],
    }


if __name__ == "__main__":
    model, info = build()
    stl_path = os.path.join(HERE, "keyholder.stl")
    model.export(stl_path)
    rep = report(model, info)
    with open(os.path.join(HERE, "keyholder_report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
