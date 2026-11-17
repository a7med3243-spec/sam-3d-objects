"""
Design 3 — "البدر والأفق" (The Moon over the Horizon)

A round ivory disc, like a full moon, with the verse in modern Kufi following its upper
edge in gold, inside a fine gold ring. A slim walnut shelf crosses the disc like a
horizon line and reaches past it on both sides; three gold pegs below it hold the keys.
The image of a moon rising over the horizon carries the promise of the verse.

Parts (each prints without supports):
  disc    - 200 mm diameter, 7 mm thick; gold starts at Z = 7.0 mm
  shelf   - 210 x 60 mm horizon shelf, printed floor-down, fixed with 2 x M3 screws
  peg x3  - printed standing on the flat cap, glued into the disc
"""

import json
import math
import os
import sys

import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import kh  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

R, T = 100.0, 7.0                 # disc radius and thickness; centre at (0, 0)
RELIEF = 1.2
RING_INSET, RING_W = 5.5, 1.4

TEXT_W = 168.0                    # verse length along the arc before bending
TEXT_BASE_R = 69.0                # baseline radius
TEXT_THICKEN = 0.12

# Horizon shelf (assembly frame; disc front face at Z = T)
SHELF_L, SHELF_D = 210.0, 60.0
SHELF_Y = -45.0                   # underside of the shelf floor
FLOOR_T, LIP_H, LIP_T = 5.0, 5.0, 4.0
BACK_T, BACK_H = 7.0, 20.0
SHELF_SCREWS = ((-45.0, SHELF_Y + 13.0), (45.0, SHELF_Y + 13.0))

PEG_Y = -74.0
PEG_X = (-34.0, 0.0, 34.0)
KEYHOLES = ((-42.0, 30.0), (42.0, 30.0))


def build():
    disc2d = kh.circle(0, 0, R, segs=360)
    ring = kh.outline(disc2d, RING_INSET, RING_W)
    text, info = kh.shape_text(kh.VERSE_PLAIN, kh.FONT_KUFI, width_mm=TEXT_W)
    text = text.buffer(TEXT_THICKEN, quad_segs=6)
    arc_text = kh.warp_to_arc(text, TEXT_BASE_R)
    accents2d = unary_union([ring, arc_text])

    base = kh.extrude(disc2d, 0, T)
    gold = kh.extrude(accents2d, T - 0.01, T + RELIEF)
    cut = [kh.peg_hole(x, PEG_Y, T) for x in PEG_X]
    cut += [kh.keyhole_cutter(x, y) for x, y in KEYHOLES]
    cut += [kh.screw_from_back(x, y, T) for x, y in SHELF_SCREWS]
    base = kh.difference(base, cut)
    disc = kh.union([base, gold])

    # horizon shelf: floor, low front lip, back plate rising behind
    z0, z1 = T, T + SHELF_D
    y0 = SHELF_Y
    prof = Polygon([(z0, y0), (z1, y0), (z1, y0 + FLOOR_T + LIP_H), (z1 - LIP_T, y0 + FLOOR_T + LIP_H),
                    (z1 - LIP_T, y0 + FLOOR_T), (z0 + BACK_T, y0 + FLOOR_T),
                    (z0 + BACK_T, y0 + BACK_H), (z0, y0 + BACK_H)])
    prof = prof.buffer(-1.0, join_style="round").buffer(1.0, join_style="round")
    shelf = kh.profile_x(list(prof.exterior.coords), -SHELF_L / 2, SHELF_L / 2)
    shelf = kh.difference(shelf, [kh.pilot_hole_z(x, y, z0, 6.0) for x, y in SHELF_SCREWS])

    pegs = [kh.peg_in_place(x, PEG_Y, T) for x in PEG_X]
    assembly = {"disc_base": (base, "ivory"), "disc_gold": (gold, "gold"), "shelf": (shelf, "walnut")}
    for i, pg in enumerate(pegs):
        assembly[f"peg_{i + 1}"] = (pg, "gold")

    shift = -disc.bounds[0]
    prints = {}
    for name, m in (("disc.stl", disc), ("disc_base_ivory.stl", base), ("disc_accent_gold.stl", gold)):
        mm = m.copy()
        mm.apply_translation(shift)
        prints[name] = mm
    sh = shelf.copy()
    sh.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    sh.apply_translation(-sh.bounds[0])
    prints["shelf.stl"] = sh
    prints["peg.stl"], _ = kh.make_peg()

    ab = arc_text.bounds
    meta = {"design": "03-horizon-moon", "colour_change_z_mm": T,
            "text_em_mm": round(info["em_mm"], 1), "text_height_mm": round(info["height"], 1),
            "arc_text_bounds": [round(v, 1) for v in ab],
            "arc_span_deg": round(math.degrees(TEXT_W / TEXT_BASE_R), 1),
            "gold_area_in_strokes_under_0.8mm_pct": kh.thin_area_pct(accents2d)}
    return assembly, prints, meta


if __name__ == "__main__":
    a, p, m = build()
    rep = kh.write_outputs(HERE, a, p, m)
    print(json.dumps(m, ensure_ascii=False))
    for r in rep:
        print(r)
