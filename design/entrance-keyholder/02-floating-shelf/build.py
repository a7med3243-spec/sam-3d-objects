"""
Design 2 — "الرف العائم" (The Floating Shelf)

Closest to the reference photo: a light-oak floating shelf with the verse standing on it,
written in Ruqaa. The gold letters sit on a frosted clear plate (like acrylic), so from a
step away they seem to stand on the shelf by themselves. Four brass pegs under the shelf
hold the keys; the shelf takes a phone, glasses and a wallet lying flat.

Parts (each prints without supports):
  shelf        - 210 x 90 x 86 mm, printed upside down (shelf top on the bed)
  calligraphy  - 202 x 50 x 4.8 mm plate, printed flat in clear PLA/PETG; gold starts
                 at Z = 3.6 mm
  peg x4       - printed standing on the flat cap, glued into the back plate
"""

import json
import math
import os
import sys

import trimesh
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import kh  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# Shelf body (assembly frame: wall at Z = 0, bottom of the back plate at Y = 0)
L = 210.0                 # length
D = 90.0                  # depth from the wall
BACK_H, BACK_T = 86.0, 6.0
TOP_T = 6.0
APRON_H, APRON_T = 22.0, 6.0
END_T = 6.0
EDGE_R = 1.2              # rounding of the outside edges
TOP_Y = BACK_H            # shelf top surface

SLOT_Z0 = BACK_T + 4.0    # slot for the calligraphy, near the back of the shelf top
SLOT_W, SLOT_DEPTH = 4.0, 4.0
SLOT_LEN = 172.0

PEG_Y = 34.0
PEG_X = (-66.0, -22.0, 22.0, 66.0)
WALL_SCREWS = ((-86.0, 72.0), (86.0, 72.0))   # tucked under the shelf

# Calligraphy piece (its own 2D frame: baseline y = 0)
TEXT_W = 186.0
CAL_T, RELIEF = 3.6, 1.2   # 3.6 = 18 layers of 0.2 mm, so the colour change lands on a layer
MARGIN_X, MARGIN_TOP, MARGIN_BOTTOM = 8.0, 8.0, 5.0
PLATE_R = 9.0
TAB_W, TAB_H = 166.0, SLOT_DEPTH - 0.3


def calligraphy_2d():
    """Gold verse and the clear plate behind it, in the plate's own 2D frame (baseline y = 0)."""
    text, info = kh.shape_text(kh.VERSE_PLAIN, kh.FONT_RUQAA, width_mm=TEXT_W)
    text = text.buffer(0.1)
    x0, y0, x1, y1 = text.bounds
    bottom = y0 - MARGIN_BOTTOM
    plate = kh.rounded_rect(x0 - MARGIN_X, bottom, x1 + MARGIN_X, y1 + MARGIN_TOP, PLATE_R)
    # square bottom corners so it stands flat on the shelf
    plate = plate.union(box(x0 - MARGIN_X, bottom, x1 + MARGIN_X, bottom + PLATE_R))
    tab = box(-TAB_W / 2, bottom - TAB_H, TAB_W / 2, bottom + 0.5)
    return text, unary_union([plate, tab]), info, bottom


def shelf_mesh():
    half = L / 2
    # U-profile in (z, y): back plate, top, apron
    prof = Polygon([
        (0, 0), (BACK_T, 0), (BACK_T, TOP_Y - TOP_T), (D - APRON_T, TOP_Y - TOP_T),
        (D - APRON_T, TOP_Y - APRON_H), (D, TOP_Y - APRON_H), (D, TOP_Y), (0, TOP_Y)])
    prof = prof.buffer(-EDGE_R, join_style="round").buffer(EDGE_R, join_style="round")
    body = kh.profile_x(list(prof.exterior.coords), -half + END_T, half - END_T)
    end_prof = Polygon([(0, TOP_Y - APRON_H), (D, TOP_Y - APRON_H), (D, TOP_Y), (0, TOP_Y)])
    end_prof = end_prof.buffer(-EDGE_R, join_style="round").buffer(EDGE_R, join_style="round")
    ends = [kh.profile_x(list(end_prof.exterior.coords), -half, -half + END_T + 0.01),
            kh.profile_x(list(end_prof.exterior.coords), half - END_T - 0.01, half)]
    # back plate edges past the ends are part of the profile body; extend it to full length
    back = kh.profile_x([(0, 0), (BACK_T, 0), (BACK_T, TOP_Y - 1), (0, TOP_Y - 1)], -half, half)
    shelf = kh.union([body, back] + ends)

    cut = [kh.box3(-SLOT_LEN / 2, SLOT_LEN / 2, TOP_Y - SLOT_DEPTH, TOP_Y + 1,
                   SLOT_Z0, SLOT_Z0 + SLOT_W)]
    cut += [kh.peg_hole(x, PEG_Y, BACK_T) for x in PEG_X]
    cut += [kh.countersunk_front(x, y, BACK_T) for x, y in WALL_SCREWS]
    return kh.difference(shelf, cut)


def build():
    text2d, sil2d, info, band_bottom = calligraphy_2d()
    cal_base = kh.extrude(sil2d, 0, CAL_T)
    cal_gold = kh.extrude(text2d, CAL_T - 0.01, CAL_T + RELIEF)
    cal_print = kh.union([cal_base, cal_gold])

    # place the calligraphy upright in the slot (assembly frame)
    def to_assembly(m):
        m = m.copy()
        # 2D frame: x across, y up, z = thickness; stand it with its back toward the wall
        m.apply_translation([0, -(band_bottom - TAB_H), 0])   # tab bottom at y = 0
        m.apply_translation([0, TOP_Y - SLOT_DEPTH + 0.3, SLOT_Z0 + (SLOT_W - CAL_T) / 2])
        return m

    shelf = shelf_mesh()
    pegs = [kh.peg_in_place(x, PEG_Y, BACK_T) for x in PEG_X]
    assembly = {"shelf": (shelf, "wood"), "calligraphy_clear": (to_assembly(cal_base), "clear"),
                "calligraphy_gold": (to_assembly(cal_gold), "gold")}
    for i, pg in enumerate(pegs):
        assembly[f"peg_{i + 1}"] = (pg, "brass")

    # print orientation
    sh = shelf.copy()
    sh.apply_transform(trimesh.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0]))  # top down
    sh.apply_translation(-sh.bounds[0])
    shift = -cal_print.bounds[0]
    prints = {"shelf.stl": sh}
    for name, m in (("calligraphy.stl", cal_print), ("calligraphy_base_clear.stl", cal_base),
                    ("calligraphy_accent_gold.stl", cal_gold)):
        mm = m.copy()
        mm.apply_translation(shift)
        prints[name] = mm
    prints["peg.stl"], _ = kh.make_peg()

    meta = {"design": "02-floating-shelf", "calligraphy_colour_change_z_mm": CAL_T,
            "text_mm": [round(info["width"], 1), round(info["height"], 1)],
            "calligraphy_height_above_shelf_mm": round(sil2d.bounds[3] - band_bottom, 1),
            "gold_area_in_strokes_under_0.8mm_pct": kh.thin_area_pct(text2d)}
    return assembly, prints, meta


if __name__ == "__main__":
    a, p, m = build()
    rep = kh.write_outputs(HERE, a, p, m)
    print(json.dumps(m, ensure_ascii=False))
    for r in rep:
        print(r)
