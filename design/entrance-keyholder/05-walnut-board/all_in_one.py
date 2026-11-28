"""
All print pieces of the walnut board in ONE file, laid out on the printer bed
(main brown piece + verse panel, each in its print orientation, side by side).

- all_parts_one_file.stl : geometry only (STL has no colours) - print in one colour,
  or split it into objects in the slicer and give each its own filament.
- all_parts_one_file.3mf : the same layout with colours set per part
  (filament 1 brown board, 2 white panel, 3 dark verse) for an AMS / multi-colour printer.

For the least filament waste, the per-colour plates (print_kit.py) are still better.

Usage:  python3 all_in_one.py [30cm|small]
Output: <size>/stl/all_parts_one_file.stl, <size>/print_kit/all_parts_one_file.3mf
"""

import importlib.util
import json
import os
import sys

import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
SIZE = sys.argv[1] if len(sys.argv) > 1 else "30cm"
STL = os.path.join(HERE, SIZE, "stl")
BED_X, BED_Y = 330.0, 320.0            # Bambu Lab A2L
EDGE = 8.0                              # keep this far from the bed edge
MAX_GAP = 40.0                          # room between the pieces; the small size still fits a 220 x 220 bed
OUT_STL = os.path.join(STL, "all_parts_one_file.stl")
OUT_3MF = os.path.join(HERE, SIZE, "print_kit", "all_parts_one_file.3mf")

# object -> list of (stl file, part name, filament)
OBJECTS = [
    ("main_brown_board_shelf_knobs", [("main_brown_board_shelf_knobs.stl", "brown_board_shelf_knobs", 1)]),
    ("panel_white_dark_verse", [("mmu_panel_white.stl", "white_panel", 2), ("mmu_verse_dark.stl", "dark_verse", 3)]),
]


def load(name):
    return trimesh.load(os.path.join(STL, name), force="mesh")


def main():
    spec = importlib.util.spec_from_file_location("print_kit", os.path.join(HERE, "print_kit.py"))
    pk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pk)

    objs = [[(load(f), part, ext) for f, part, ext in vols] for _, vols in OBJECTS]
    ext = [trimesh.util.concatenate([m for m, _, _ in o]).bounds for o in objs]
    sizes = [b[1] - b[0] for b in ext]
    gap = min(MAX_GAP, BED_Y - 2 * EDGE - sum(s[1] for s in sizes))
    assert gap >= 10.0, "pieces do not fit side by side"
    y = (BED_Y - sum(s[1] for s in sizes) - gap) / 2
    placed = []
    for o, b, s in zip(objs, ext, sizes):
        d = [(BED_X - s[0]) / 2 - b[0][0], y - b[0][1], -b[0][2]]
        vols = []
        for m, part, e in o:
            m = m.copy()
            m.apply_translation(d)
            vols.append((m, part, e))
        placed.append(vols)
        y += s[1] + gap

    # one STL: the printable bodies (main piece + panel with its verse)
    stl_parts = [load("main_brown_board_shelf_knobs.stl"), load("panel_white_with_verse.stl")]
    main_m, panel_m = stl_parts
    main_m.apply_translation(placed[0][0][0].bounds[0] - main_m.bounds[0])
    pb = trimesh.util.concatenate([m for m, _, _ in placed[1]]).bounds
    panel_m.apply_translation(pb[0] - panel_m.bounds[0])
    allm = trimesh.util.concatenate([main_m, panel_m])
    allm.export(OUT_STL)

    # one 3MF: same layout, colour per part
    os.makedirs(os.path.dirname(OUT_3MF), exist_ok=True)
    pk.write_plate_3mf(OUT_3MF, [(name, vols) for (name, _), vols in zip(OBJECTS, placed)])

    lo, hi = allm.bounds
    rep = {
        "stl": os.path.relpath(OUT_STL, HERE),
        "3mf": os.path.relpath(OUT_3MF, HERE),
        "filaments_3mf": {part: e for _, vols in OBJECTS for _, part, e in vols},
        "gap_mm": round(float(gap), 1),
        "pieces_watertight": [bool(main_m.is_watertight), bool(panel_m.is_watertight)],
        "size_mm": [round(float(v), 1) for v in hi - lo],
        "fits_330x320_bed": bool(lo.min() >= -1e-6 and hi[0] <= BED_X and hi[1] <= BED_Y),
        "fits_220x220_bed": bool((hi - lo)[0] <= 220 and (hi - lo)[1] <= 220),
    }
    print(json.dumps(rep))
    return rep


if __name__ == "__main__":
    main()
