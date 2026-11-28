"""
All print pieces of the walnut board in ONE STL file, laid out on the printer bed
(main brown piece + verse panel, each in its print orientation, side by side).

STL has no colours: this file is for printing everything in one go in one colour,
or for slicers where you split it into objects and give each its own filament.
For brown board + white panel + dark verse with the least waste, use the per-colour plates.

Usage:  python3 all_in_one.py [30cm|small]
Output: <size>/stl/all_parts_one_file.stl
"""

import json
import os
import sys

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
SIZE = sys.argv[1] if len(sys.argv) > 1 else "30cm"
STL = os.path.join(HERE, SIZE, "stl")
BED_X, BED_Y = 330.0, 320.0            # Bambu Lab A2L
GAP = 12.0
PARTS = ["main_brown_board_shelf_knobs.stl", "panel_white_with_verse.stl"]
OUT = os.path.join(STL, "all_parts_one_file.stl")


def main():
    meshes = [trimesh.load(os.path.join(STL, p), force="mesh") for p in PARTS]
    total_y = sum(m.extents[1] for m in meshes) + GAP * (len(meshes) - 1)
    y = (BED_Y - total_y) / 2
    placed = []
    for m in meshes:
        m = m.copy()
        lo = m.bounds[0]
        m.apply_translation([(BED_X - m.extents[0]) / 2 - lo[0], y - lo[1], -lo[2]])
        y += m.extents[1] + GAP
        placed.append(m)
    # no overlap between the pieces' footprints
    b = [p.bounds for p in placed]
    assert b[0][1][1] + GAP - 1e-6 <= b[1][0][1], "pieces overlap"
    allm = trimesh.util.concatenate(placed)
    allm.export(OUT)
    lo, hi = allm.bounds
    rep = {
        "file": os.path.relpath(OUT, HERE),
        "pieces": PARTS,
        "pieces_watertight": [bool(p.is_watertight) for p in placed],
        "bodies": len(allm.split(only_watertight=False)),
        "size_mm": [round(float(v), 1) for v in hi - lo],
        "fits_330x320_bed": bool(hi[0] <= BED_X and hi[1] <= BED_Y and lo.min() >= -1e-6),
        "fits_220x220_bed": bool((hi - lo)[0] <= 220 and (hi - lo)[1] <= 220),
        "volume_cm3": round(sum(p.volume for p in placed) / 1000, 1),
    }
    print(json.dumps(rep))
    return rep


if __name__ == "__main__":
    main()
