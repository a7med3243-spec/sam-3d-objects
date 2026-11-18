"""
Design 5 — "اللوح الخشبي" (The Walnut Board)

After the reference photo: a walnut board with rounded corners, a shelf across its upper
part, a white panel of soft wavy fluting under the shelf and five brass knobs below.

Optional: the verse ﴿ولسوف يعطيك ربك فترضى﴾ in gold Ruqaa as a separate letters-only
piece that sits on the white fluting (use panel_white_for_verse.stl, which has the pin
holes for it).

Parts (each prints without supports):
  board       - 210 x 122 x 8 mm, printed lying on its back
  panel_white - 200 x 49 mm wavy fluted panel, printed lying on its back, glued in
                a 1 mm recess in the board
  shelf       - 210 x 55 x 8 mm, printed flat; rests on the white panel, 3 x M3
                screws from behind the board
  knob x5     - printed standing on its flat face, glued into the board
  verse       - optional, 170 x 38 x 3.2 mm, printed front face down
"""

import json
import math
import os
import sys

import numpy as np
import trimesh
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import kh  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- board (assembly frame: wall at Z = 0, bottom-left corner of the board at (-W/2, 0))
W, H, T = 210.0, 122.0, 8.0
CORNER_R = 10.0

# ---- shelf
SHELF_T = 8.0
SHELF_TOP = 89.0
SHELF_BOTTOM = SHELF_TOP - SHELF_T
SHELF_D = 55.0                   # from the board face
SHELF_R = 3.0                    # rounded front corners
SHELF_SCREWS_X = (-80.0, 0.0, 80.0)

# ---- white wavy fluted panel (directly under the shelf)
PANEL_X = 100.0                  # half width
PANEL_Y0, PANEL_Y1 = 32.0, SHELF_BOTTOM
RECESS = 1.0                     # pocket in the board that locates the panel
PANEL_BASE, REED_H = 4.0, 3.0    # flat back + height of the reeds
REED_PITCH = 4.5
PANEL_FRONT = T - RECESS + PANEL_BASE + REED_H   # z of the reed crests

# ---- brass knobs
KNOB_Y = 16.0
KNOB_X = (-76.0, -38.0, 0.0, 38.0, 76.0)
NECK_D, NECK_L = 8.0, 13.0
CAP_D, CAP_T = 14.0, 7.0

KEYHOLES = ((-70.0, 102.0), (70.0, 102.0))

# ---- optional verse on the white panel
VERSE_W = 164.0
VERSE_T = 3.2
VERSE_BASELINE = 52.0
RAIL_W = 1.8
PIN_D, PIN_LEN, PIN_HOLE_D = 2.5, 5.0, 2.9


def reed_height(X, Y):
    """Soft vertical reeds whose crests drift in slow waves, like draped fabric."""
    amp = 1.1 + 0.8 * np.sin(X / 29.0 + 0.7) * np.cos(X / 53.0)
    drift = amp * np.sin(2 * np.pi * Y / 64.0 + X / 31.0) + 0.35 * np.sin(2 * np.pi * Y / 29.0 + X / 13.0)
    u = (X - drift) / REED_PITCH
    crest = (0.5 + 0.5 * np.cos(2 * np.pi * u)) ** 0.75
    return PANEL_BASE + REED_H * crest


def panel_mesh():
    m = kh.heightfield_solid(-PANEL_X, PANEL_X, PANEL_Y0, PANEL_Y1, 0.3, 0.6, reed_height)
    # soften the four corners a little
    clip = kh.extrude(kh.rounded_rect(-PANEL_X, PANEL_Y0, PANEL_X, PANEL_Y1, 1.5), -1, PANEL_BASE + REED_H + 1)
    m = trimesh.boolean.intersection([m, clip], engine="manifold")
    m.apply_translation([0, 0, T - RECESS])
    return m


def make_knob():
    """Brass knob in print orientation: flat face on the bed, tenon on top."""
    rc, rn, rt = CAP_D / 2, NECK_D / 2, kh.PEG_TENON_D / 2
    prof = [(0, 0), (rc - 1.2, 0), (rc - 0.35, 0.35), (rc, 1.2),          # rounded front edge
            (rc, CAP_T - (rc - rn) * 0.6), (rn, CAP_T + 1.5),             # sloped back of cap
            (rn, CAP_T + NECK_L), (rt, CAP_T + NECK_L),
            (rt, CAP_T + NECK_L + kh.PEG_TENON_L - 0.5),
            (rt - 0.5, CAP_T + NECK_L + kh.PEG_TENON_L), (0, CAP_T + NECK_L + kh.PEG_TENON_L)]
    m = trimesh.creation.revolve(np.array(prof), sections=72)
    if m.volume < 0:
        m.invert()
    return m


def verse_2d():
    """Gold verse standing on a fine tapered line, one connected piece (assembly XY)."""
    text, info = kh.shape_text(kh.VERSE_PLAIN, kh.FONT_RUQAA, width_mm=VERSE_W)
    text = affinity.translate(text, 0, VERSE_BASELINE)
    x0, x1 = text.bounds[0] - 6, text.bounds[2] + 6
    xs = np.linspace(x0, x1, 200)
    k = np.clip(np.minimum(xs - x0, x1 - xs) / 14.0, 0, 1)
    k = 0.5 + 0.5 * np.sin(k * np.pi / 2)    # tips stay 0.9 mm wide
    top = [(x, VERSE_BASELINE + 0.3) for x in xs]
    bot = [(x, VERSE_BASELINE + 0.3 - RAIL_W * kk) for x, kk in zip(xs[::-1], k[::-1])]
    rail = Polygon(top + bot).buffer(0)
    g, bridges = kh.connect_islands(unary_union([text, rail]), width=1.5)
    return g, bridges, info


def verse_pins(g, n=3):
    core = g.buffer(-(PIN_D / 2 + 0.5))
    cands = sorted([(p.representative_point().x, p.representative_point().y, p.area)
                    for p in kh.polys(core) if p.area > 0.25])
    targets = np.linspace(cands[0][0], cands[-1][0], n)
    chosen = []
    for t in targets:
        best = min((c for c in cands if (c[0], c[1]) not in chosen), key=lambda c: abs(c[0] - t) - 0.05 * c[2])
        chosen.append((best[0], best[1]))
    return chosen


def build():
    outline = kh.rounded_rect(-W / 2, 0, W / 2, H, CORNER_R)
    board = kh.extrude(outline, 0, T)
    recess = kh.extrude(box(-PANEL_X - 0.2, PANEL_Y0 - 0.2, PANEL_X + 0.2, PANEL_Y1 + 0.2), T - RECESS, T + 1)
    cut = [recess]
    cut += [kh.peg_hole(x, KNOB_Y, T, depth=6.0) for x in KNOB_X]
    cut += [kh.keyhole_cutter(x, y) for x, y in KEYHOLES]
    sy = SHELF_BOTTOM + SHELF_T / 2
    cut += [kh.screw_from_back(x, sy, T) for x in SHELF_SCREWS_X]
    board = kh.difference(board, cut)

    panel = panel_mesh()

    # shelf: slab with softly rounded front corners and edges
    slab2d = kh.rounded_rect(-W / 2, T - SHELF_R - 1, W / 2, T + SHELF_D, SHELF_R)
    slab2d = slab2d.intersection(box(-W, T, W, T + SHELF_D + 1))
    shelf = kh.extrude_y(slab2d, SHELF_BOTTOM, SHELF_TOP)
    # screws enter the shelf's back edge along Z
    shelf = kh.difference(shelf, [kh.pilot_hole_z(x, sy, T, 10.0) for x in SHELF_SCREWS_X])

    knob_print = make_knob()
    knobs = []
    for x in KNOB_X:
        m = knob_print.copy()
        m.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]))
        m.apply_translation([x, KNOB_Y, T + CAP_T + NECK_L])
        knobs.append(m)

    # optional verse + a panel variant with its pin holes
    v2d, bridges, info = verse_2d()
    pins = verse_pins(v2d)
    verse = kh.extrude(v2d, PANEL_FRONT, PANEL_FRONT + VERSE_T)
    verse = kh.union([verse] + [kh.cyl_z(x, y, PIN_D / 2, PANEL_FRONT - PIN_LEN, PANEL_FRONT + 0.01, 32)
                                for x, y in pins])
    panel_v = kh.difference(panel, [kh.cyl_z(x, y, PIN_HOLE_D / 2, PANEL_FRONT - PIN_LEN - 1.0,
                                             PANEL_FRONT + 1, 32) for x, y in pins])

    assembly = {"board": (board, "walnut"), "panel_white": (panel, "ivory"), "shelf": (shelf, "walnut")}
    for i, m in enumerate(knobs):
        assembly[f"knob_{i + 1}"] = (m, "brass")
    assembly_verse = dict(assembly)
    assembly_verse["panel_white"] = (panel_v, "ivory")
    assembly_verse["verse"] = (verse, "gold")

    # fit check (touching is fine, overlaps are not)
    clashes = {}
    names = list(assembly_verse)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if a.startswith("knob") and b.startswith("knob"):
                continue
            inter = trimesh.boolean.intersection([assembly_verse[a][0], assembly_verse[b][0]], engine="manifold")
            with np.errstate(all="ignore"):
                vol = float(inter.volume) if len(inter.faces) else 0.0
            if vol > 1.0:
                clashes[f"{a}/{b}"] = round(vol, 1)

    # print orientation
    def placed(m, tf=None):
        m = m.copy()
        if tf is not None:
            m.apply_transform(tf)
        m.apply_translation(-m.bounds[0])
        return m
    prints = {
        "board.stl": placed(board),
        "panel_white.stl": placed(panel),
        "panel_white_for_verse.stl": placed(panel_v),
        "shelf.stl": placed(shelf, trimesh.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0])),
        "knob.stl": knob_print,
        "verse.stl": placed(verse, trimesh.transformations.rotation_matrix(math.pi, [0, 1, 0])),
    }

    vb = v2d.bounds
    meta = {
        "design": "05-walnut-board",
        "overall_mm": [W, H, round(T + SHELF_D, 1)],
        "panel_front_z_mm": PANEL_FRONT,
        "reed_pitch_mm": REED_PITCH,
        "verse_em_mm": round(info["em_mm"], 1),
        "verse_size_mm": [round(vb[2] - vb[0], 1), round(vb[3] - vb[1], 1), VERSE_T],
        "verse_pieces": len(kh.polys(v2d)),
        "verse_bridges": len(bridges),
        "verse_strokes_under_0.8mm_pct": kh.thin_area_pct(v2d),
        "verse_pins": [[round(x, 1), round(y, 1)] for x, y in pins],
        "assembly_clashes_mm3": clashes,
    }
    return assembly, assembly_verse, prints, meta


if __name__ == "__main__":
    a, av, p, m = build()
    rep = kh.write_outputs(HERE, a, p, m)
    # second assembly (with the verse) for the renders
    manifest = []
    for name, (mesh, mat) in av.items():
        kh.export(mesh, os.path.join(HERE, "assembly_verse", name + ".stl"))
        manifest.append({"file": f"{name}.stl", "material": mat})
    with open(os.path.join(HERE, "assembly_verse", "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    print(json.dumps(m, ensure_ascii=False))
    for r in rep:
        print(r)
