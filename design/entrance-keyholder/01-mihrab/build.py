"""
Design 1 — "المحراب" (The Arch)

A slim pointed arch, like a doorway or a mihrab, in matte black. The verse sits in two
lines of Quranic Naskh under the arch, inside a thin gold frame line and under a small
eight-point star. At the base, a full-width pocket takes a phone (lying sideways),
a wallet or earbuds. Three gold pegs under the pocket hold the keys.

Everything that is visible stays clear of the verse: what stands in the pocket ends
below the second line.

Parts (each prints without supports):
  panel   - arch board 160 x 210 x 7 mm; the gold relief starts at Z = 7.0 mm, so
            a single filament change at that height gives the two colours
  pocket  - 160 x 48 x 30 mm open box, printed floor-down, fixed with 2 x M3 screws
  peg x3  - printed standing on the flat cap, glued into the panel
"""

import json
import math
import os
import sys

import trimesh
from shapely import affinity
from shapely.geometry import Point
from shapely.ops import unary_union

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import kh  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

W, H, T = 160.0, 210.0, 7.0        # arch board
RELIEF = 1.2                       # gold relief height
FRAME_INSET, FRAME_W = 6.5, 1.4

TEXT_EM = 20.0                     # font size of the verse (mm per em)
TEXT_THICKEN = 0.18                # grows the outline so the hairlines print cleanly
LINE1_Y, LINE2_Y = 149.0, 116.0    # baselines, 1.65 em apart so each line keeps its own marks

STAR_Y, STAR_R, STAR_LINE = 184.0, 6.0, 1.3

# Pocket (assembly frame: panel front face at Z = T)
POCKET_Y0, POCKET_H, POCKET_D = 28.0, 42.0, 30.0
NOTCH_W, NOTCH_DEPTH = 64.0, 12.0     # finger dip in the front wall, echoing the arch
WALL_BACK, WALL_FRONT, WALL_SIDE, FLOOR_T = 6.0, 3.5, 3.0, 4.0
POCKET_R = 3.0
POCKET_SCREWS = ((-50.0, 50.0), (50.0, 50.0))

PEG_Y = 14.0
PEG_X = (-40.0, 0.0, 40.0)
KEYHOLES = ((-45.0, 140.0), (45.0, 140.0))


def verse_geometry():
    l1, i1 = kh.shape_text(kh.VERSE_LINE1, kh.FONT_NASKH, em_mm=TEXT_EM)
    l2, i2 = kh.shape_text(kh.VERSE_LINE2, kh.FONT_NASKH, em_mm=TEXT_EM)
    g = unary_union([affinity.translate(l1, 0, LINE1_Y), affinity.translate(l2, 0, LINE2_Y)])
    return g.buffer(TEXT_THICKEN, quad_segs=6), (i1, i2)


def pocket_mesh():
    z0 = T
    outer = kh.rounded_rect(-W / 2, z0, W / 2, z0 + POCKET_D, POCKET_R)
    # keep the back edge square so it sits flat on the panel
    outer = outer.union(kh.rounded_rect(-W / 2, z0, W / 2, z0 + POCKET_R + 0.5, 0))
    inner = kh.rounded_rect(-W / 2 + WALL_SIDE, z0 + WALL_BACK,
                            W / 2 - WALL_SIDE, z0 + POCKET_D - WALL_FRONT, 1.5)
    y0, y1 = POCKET_Y0, POCKET_Y0 + POCKET_H
    body = kh.extrude_y(outer, y0, y1)
    hollow = kh.extrude_y(inner, y0 + FLOOR_T, y1 + 1)
    # one fine groove across the front, under the dip
    gy = y1 - NOTCH_DEPTH - 6.0
    groove = kh.box3(-W / 2 - 1, W / 2 + 1, gy - 0.5, gy + 0.5,
                     z0 + POCKET_D - 0.6, z0 + POCKET_D + 1)
    holes = [kh.pilot_hole_z(x, y, z0, 5.5) for x, y in POCKET_SCREWS]
    # soft dip in the front wall's rim (half-ellipse), for reaching in
    dip = affinity.scale(Point(0, 0).buffer(1.0, quad_segs=32), NOTCH_W / 2, NOTCH_DEPTH)
    dip = affinity.translate(dip, 0, y1)
    dip3 = kh.extrude(dip, z0 + POCKET_D - WALL_FRONT - 1.0, z0 + POCKET_D + 1.0)
    return kh.difference(body, [hollow, groove, dip3] + holes)


def build():
    arch, y_spring = kh.pointed_arch(W, H, point=0.10, corner_r=2.0)
    apex_y = arch.bounds[3]

    # gold accents: all start at Z = T, so one colour change at that layer does it
    frame = kh.outline(arch, FRAME_INSET, FRAME_W)
    star = kh.eight_point_star(0, STAR_Y, STAR_R, line_w=STAR_LINE)
    star = star.union(kh.circle(0, STAR_Y, 1.7, segs=48))
    verse, infos = verse_geometry()
    accents2d = unary_union([frame, star, verse])

    base = kh.extrude(arch, 0, T)
    accent = kh.extrude(accents2d, T - 0.01, T + RELIEF)
    cut = [kh.peg_hole(x, PEG_Y, T) for x in PEG_X]
    cut += [kh.keyhole_cutter(x, y) for x, y in KEYHOLES]
    cut += [kh.screw_from_back(x, y, T) for x, y in POCKET_SCREWS]
    base = kh.difference(base, cut)
    panel = kh.union([base, accent])

    pocket = pocket_mesh()
    pegs = [kh.peg_in_place(x, PEG_Y, T) for x in PEG_X]

    assembly = {"panel_base": (base, "black"), "panel_gold": (accent, "gold"),
                "pocket": (pocket, "black")}
    for i, pg in enumerate(pegs):
        assembly[f"peg_{i + 1}"] = (pg, "gold")

    # print orientation
    shift = -panel.bounds[0]
    prints = {}
    for name, m in (("panel.stl", panel), ("panel_base_black.stl", base),
                    ("panel_accent_gold.stl", accent)):
        mm = m.copy()
        mm.apply_translation(shift)
        prints[name] = mm
    pk = pocket.copy()
    pk.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    pk.apply_translation(-pk.bounds[0])
    prints["pocket.stl"] = pk
    prints["peg.stl"], _ = kh.make_peg()

    meta = {"design": "01-mihrab", "colour_change_z_mm": T,
            "verse_line_widths_mm": [round(i["width"], 1) for i in infos],
            "apex_y": round(apex_y, 1), "spring_y": round(y_spring, 1),
            "gold_area_in_strokes_under_0.8mm_pct": kh.thin_area_pct(accents2d)}
    return assembly, prints, meta


if __name__ == "__main__":
    a, p, m = build()
    rep = kh.write_outputs(HERE, a, p, m)
    print(json.dumps(m, ensure_ascii=False))
    for r in rep:
        print(r)
