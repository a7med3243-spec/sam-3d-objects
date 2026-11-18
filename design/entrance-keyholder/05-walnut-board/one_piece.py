"""
Small walnut board as ONE printable model (no assembly).

Board, white wavy panel, dark verse, shelf and the five knobs are fused into a single
piece that prints lying on its back without supports: the shelf rises as a straight wall,
the knobs grow up from the board and their caps widen at under 45 degrees.

Outputs (in small/one_piece/):
  walnut_board_small_one_piece.3mf  - one object made of five parts (board, panel, verse,
                                      shelf, knobs) already set to filament slots 1-4;
                                      a multi-colour printer prints it in its colours,
                                      any other printer in one
  walnut_board_small_one_piece.stl  - the same piece merged into one body (one colour)
"""

import importlib.util
import json
import math
import os
import sys
import zipfile
from xml.sax.saxutils import escape

import numpy as np
import trimesh
from shapely.geometry import box

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from common import kh  # noqa: E402

_spec = importlib.util.spec_from_file_location("walnut", os.path.join(HERE, "build.py"))
walnut = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(walnut)

COLOURS = {  # name -> (display colour, suggested filament)
    "board": ("#6B4A33", "Wood PLA / matte brown"),
    "shelf": ("#6B4A33", "Wood PLA / matte brown"),
    "panel_white": ("#F1EDE6", "Matte white PLA"),
    "verse_dark": ("#2A1D16", "Dark brown / black PLA"),
    "knobs": ("#C8A25A", "Silk brass / gold PLA"),
}


def knob_without_tenon(c):
    """Knob that grows straight out of the board (shoulder on the board face)."""
    rc, rn = c["CAP_D"] / 2, c["NECK_D"] / 2
    ct, nl = c["CAP_T"], c["NECK_L"]
    prof = [(0, 0), (rc - 1.2, 0), (rc - 0.35, 0.35), (rc, 1.2),
            (rc, ct - (rc - rn) * 0.6), (rn, ct + 1.5), (rn, ct + nl), (0, ct + nl)]
    m = trimesh.creation.revolve(np.array(prof), sections=72)
    if m.volume < 0:
        m.invert()
    return m


def build():
    c = walnut.SIZES["small"]
    W, H, T = c["W"], c["H"], c["T"]
    shelf_top, shelf_t = c["SHELF_TOP"], c["SHELF_T"]
    shelf_bottom = shelf_top - shelf_t
    px, py0, py1 = c["PANEL_X"], c["PANEL_Y0"], shelf_bottom
    rec = c["RECESS"]
    crest = c["PANEL_BASE"] + c["REED_H"]

    # board: the panel sits in an exact-fit pocket so parts touch without overlapping
    board = kh.extrude(kh.rounded_rect(-W / 2, 0, W / 2, H, c["CORNER_R"]), 0, T)
    board = kh.difference(board, [kh.extrude(box(-px, py0, px, py1), T - rec, T + 1)]
                          + [kh.keyhole_cutter(x, y) for x, y in c["KEYHOLES"]])

    panel = kh.heightfield_solid(-px, px, py0, py1, c["REED_PITCH"] / 11.0, 1.0, walnut.reed_fn(c))
    panel = trimesh.boolean.intersection(
        [panel, kh.extrude(kh.rounded_rect(-px, py0, px, py1, 0.01), -1, crest + 1)], engine="manifold")
    verse2d, _ = walnut.verse_geometry(c, py0, py1)
    letters = kh.extrude(verse2d, c["PANEL_BASE"] - 0.01, crest + c["RELIEF"])
    panel_white = kh.difference(panel, [letters])
    for m in (panel_white, letters):
        m.apply_translation([0, 0, T - rec])

    slab2d = kh.rounded_rect(-W / 2, T - c["SHELF_R"] - 1, W / 2, T + c["SHELF_D"], c["SHELF_R"])
    slab2d = slab2d.intersection(box(-W, T, W, T + c["SHELF_D"] + 1))
    shelf = kh.extrude_y(slab2d, shelf_bottom, shelf_top)

    kn = knob_without_tenon(c)
    knobs = []
    for x in c["KNOB_X"]:
        m = kn.copy()
        m.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]))
        m.apply_translation([x, c["KNOB_Y"], T + c["CAP_T"] + c["NECK_L"]])
        knobs.append(m)
    knobs = trimesh.util.concatenate(knobs)

    parts = {"board": board, "panel_white": panel_white, "verse_dark": letters,
             "shelf": shelf, "knobs": knobs}
    # print frame: back of the board on the bed (z = 0), everything above it
    lo = np.min([m.bounds[0] for m in parts.values()], axis=0)
    for m in parts.values():
        m.apply_translation([-lo[0], -lo[1], 0])
    return parts, c


def check(parts):
    names = list(parts)
    clashes = {}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            inter = trimesh.boolean.intersection([parts[a], parts[b]], engine="manifold")
            with np.errstate(all="ignore"):
                vol = float(inter.volume) if len(inter.faces) else 0.0
            if vol > 1.0:
                clashes[f"{a}/{b}"] = round(vol, 1)
    return clashes


EXTRUDER = {"board": 1, "shelf": 1, "panel_white": 2, "verse_dark": 3, "knobs": 4}


def write_3mf(parts, path):
    """One object whose single mesh holds five parts. Part ranges, names and filament slots go
    in Metadata/Slic3r_PE_model.config (the multi-part layout PrusaSlicer writes and
    Bambu Studio / OrcaSlicer read), so slicers keep it as one object with coloured parts.
    A plain 3MF reader sees one mesh."""
    names = list(parts)
    verts, tris, ranges, off, t0 = [], [], [], 0, 0
    for n in names:
        m = parts[n]
        verts.append(m.vertices)
        tris.append(m.faces + off)
        ranges.append((n, t0, t0 + len(m.faces) - 1))
        off += len(m.vertices)
        t0 += len(m.faces)
    V, F = np.vstack(verts), np.vstack(tris)
    v = "".join(f'<vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in V)
    t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in F)
    model = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
             'xmlns:slic3rpe="http://schemas.slic3r.org/3mf/2017/06">'
             '<metadata name="slic3rpe:Version3mf">1</metadata>'
             '<metadata name="Title">Walnut key holder (small, one piece)</metadata>'
             f'<resources><object id="1" type="model" name="walnut_board_small"><mesh>'
             f'<vertices>{v}</vertices><triangles>{t}</triangles></mesh></object></resources>'
             '<build><item objectid="1" printable="1"/></build></model>')
    vols = ""
    for n, a, b in ranges:
        vols += (f'<volume firstid="{a}" lastid="{b}">'
                 f'<metadata type="volume" key="name" value="{escape(n)}"/>'
                 '<metadata type="volume" key="volume_type" value="ModelPart"/>'
                 f'<metadata type="volume" key="extruder" value="{EXTRUDER[n]}"/>'
                 '<metadata type="volume" key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>'
                 '<mesh edges_fixed="0" degenerate_facets="0" facets_removed="0" '
                 'facets_reversed="0" backwards_edges="0"/></volume>')
    config = ('<?xml version="1.0" encoding="UTF-8"?><config><object id="1" instances_count="1">'
              '<metadata type="object" key="name" value="walnut_board_small"/>'
              f'{vols}</object></config>')
    ctypes = ('<?xml version="1.0" encoding="UTF-8"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
              '<Default Extension="config" ContentType="text/xml"/>'
              '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
        z.writestr("Metadata/Slic3r_PE_model.config", config)


if __name__ == "__main__":
    parts, c = build()
    out = os.path.join(HERE, "small", "one_piece")
    os.makedirs(out, exist_ok=True)
    clashes = check(parts)
    merged = kh.union(list(parts.values()))
    stl_path = os.path.join(out, "walnut_board_small_one_piece.stl")
    merged.export(stl_path)
    write_3mf(parts, os.path.join(out, "walnut_board_small_one_piece.3mf"))
    # assembled parts for the renders (assembly frame: shift back is irrelevant for a render)
    asm = os.path.join(out, "assembly")
    os.makedirs(asm, exist_ok=True)
    mats = {"board": "walnut", "shelf": "walnut", "panel_white": "ivory", "verse_dark": "espresso", "knobs": "brass"}
    for n, m in parts.items():
        m.export(os.path.join(asm, n + ".stl"))
    with open(os.path.join(asm, "manifest.json"), "w") as f:
        json.dump([{"file": n + ".stl", "material": mats[n]} for n in parts], f, indent=1)
    rep = kh.part_report("walnut_board_small_one_piece.stl", merged)
    rep["parts_clash_mm3"] = clashes
    rep["colour_parts"] = {n: COLOURS[n] for n in parts}
    with open(os.path.join(out, "report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False, indent=1))
