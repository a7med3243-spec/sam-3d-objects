"""
Design 4 — "القوس المضلّع" (The Fluted Arch)

After the reference photo: a matte-black half-round arch with vertical fluting, a slab
shelf across its base and a plain board below with six round pegs.

The verse ﴿ولسوف يعطيك ربك فترضى﴾ crowns the arch: a separate piece made only of
letters, in gold Ruqaa, with nothing behind it but the wall. The letters stand on a fine
gold trim that follows the arch edge down to the shelf; the trim keeps every word and
dot joined, so the verse prints as one piece and can also be hung on its own. Five pins
on small studs along the trim drop into holes in the arch.

Parts (each prints without supports):
  panel        - arch + peg board, 210 x 183 mm, printed lying on its back
  shelf        - 210 x 85 mm slab with a hidden back flange, printed upside down
  verse        - about 210 x 145 x 3.2 mm, printed flat (front face down), letters only
  peg x6       - printed standing on the end face, glued into the board
"""

import json
import math
import os
import sys

import numpy as np
import trimesh
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import kh  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- panel (assembly frame: wall at Z = 0, bottom of the board at Y = 0)
W = 210.0
R = W / 2                       # arch radius
T = 7.0                         # board thickness
SHELF_T = 8.0
SHELF_BOTTOM = 60.0
SHELF_TOP = SHELF_BOTTOM + SHELF_T
YC = SHELF_TOP + 10.0           # centre of the half-round arch
CORNER_R = 4.0

FLUTE_PITCH, FLUTE_R = 6.0, 2.6   # half-round reeds, 6 mm apart, 2.6 mm proud
RIM = 6.0                         # smooth border round the fluting (the gold trim sits on it)
FLUTE_TOP = T + FLUTE_R

# ---- shelf
SHELF_D = 85.0
SHELF_CORNER_R = 10.0
FLANGE_H, FLANGE_T = 18.0, 6.0
FLANGE_SCREWS_X = (-90.0, 0.0, 90.0)   # M3 from behind the board into the flange
SCREW_Y = SHELF_BOTTOM - FLANGE_H / 2
KEYHOLES = ((0.0, 140.0), (-66.0, 12.0), (66.0, 12.0))   # all hidden on the back

# ---- pegs
PEG_Y = 28.0
PEG_X = tuple(-82.5 + 33.0 * i for i in range(6))
PEG_LEN, PEG_D, PEG_END_D = 34.0, 12.0, 13.0

# ---- verse: a crown of letters above the arch, standing on a gold trim along its edge
TEXT_W = 196.0                  # length along the baseline before bending
TRIM_R = R - 4.0                # centre line of the gold trim, on the smooth border
TRIM_W = 2.4
BASE_R = TRIM_R + TRIM_W / 2    # letters stand on the outer side of the trim
VERSE_T = 3.2                   # 16 layers of 0.2 mm
BRIDGE_W = 1.5
BEAD_R = 2.8                    # small round studs on the trim that carry the pins
BEAD_ANGLES = (14.0, 50.0, 90.0, 130.0, 166.0)
PIN_D, PIN_LEN = 2.5, 6.0       # locating pins on the back of the verse
PIN_HOLE_D, PIN_HOLE_DEPTH = 2.9, 7.0


# ----------------------------------------------------------------------------
def panel_outline():
    top = Point(0, YC).buffer(R, quad_segs=128).intersection(box(-R - 1, YC, R + 1, YC + R + 1))
    body = kh.rounded_rect(-R, 0, R, YC + CORNER_R + 1, CORNER_R)
    return unary_union([top, body, box(-R, CORNER_R, R, YC + 0.01)])


def fluting():
    """Half-round vertical reeds clipped to the arch, inside a smooth rim."""
    area = panel_outline().buffer(-RIM, join_style="round").intersection(
        box(-R, SHELF_TOP + 0.2, R, YC + R + 1))
    y0, y1 = SHELF_TOP + 0.2, YC + R
    reeds = []
    n = int((W - 2 * RIM) // FLUTE_PITCH)
    x_first = -(n - 1) * FLUTE_PITCH / 2
    for i in range(n):
        x = x_first + i * FLUTE_PITCH
        c = trimesh.creation.cylinder(radius=FLUTE_R, height=y1 - y0, sections=28)
        c.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
        c.apply_translation([x, (y0 + y1) / 2, T])
        reeds.append(c)
    reeds = kh.union(reeds)
    clip = kh.extrude(area, T - 0.01, FLUTE_TOP + 1)
    return trimesh.boolean.intersection([reeds, clip], engine="manifold")


def verse_2d():
    """The verse as a crown over the arch, all one connected piece (assembly XY)."""
    text, info = kh.shape_text(kh.VERSE_PLAIN, kh.FONT_RUQAA, width_mm=TEXT_W)
    arc_text = kh.warp_to_arc(text, BASE_R, centre=(0, YC))
    disc = lambda r: Point(0, YC).buffer(r, quad_segs=160)  # noqa: E731
    trim = disc(TRIM_R + TRIM_W / 2 + 0.3).difference(disc(TRIM_R - TRIM_W / 2))
    trim = trim.intersection(box(-300, YC, 300, 400))
    legs = [box(s * TRIM_R - TRIM_W / 2, SHELF_TOP, s * TRIM_R + TRIM_W / 2, YC + 0.5) for s in (-1, 1)]
    beads = [Point(TRIM_R * math.cos(math.radians(a)), YC + TRIM_R * math.sin(math.radians(a)))
             .buffer(BEAD_R, quad_segs=24) for a in BEAD_ANGLES]
    g = unary_union([arc_text, trim] + legs + beads)
    g, bridges = kh.connect_islands(g, width=BRIDGE_W)
    return g, arc_text, bridges, info


def pin_points(g=None):
    return [(TRIM_R * math.cos(math.radians(a)), YC + TRIM_R * math.sin(math.radians(a)))
            for a in BEAD_ANGLES]


def build():
    outline = panel_outline()
    board = kh.extrude(outline, 0, T)
    reeds = fluting()

    verse2d, arc_text, bridges, info = verse_2d()
    pins = pin_points(verse2d)

    cut = [kh.peg_hole(x, PEG_Y, T, depth=5.8) for x in PEG_X]
    cut += [kh.screw_from_back(x, SCREW_Y, T) for x in FLANGE_SCREWS_X]
    cut += [kh.keyhole_cutter(x, y) for x, y in KEYHOLES]
    cut += [kh.cyl_z(x, y, PIN_HOLE_D / 2, FLUTE_TOP - PIN_HOLE_DEPTH, FLUTE_TOP + 1) for x, y in pins]
    panel = kh.difference(kh.union([board, reeds]), cut)

    # verse piece: its back rests on the reed tops
    verse = kh.extrude(verse2d, FLUTE_TOP, FLUTE_TOP + VERSE_T)
    pin_meshes = [kh.cyl_z(x, y, PIN_D / 2, FLUTE_TOP - PIN_LEN, FLUTE_TOP + 0.01, sections=32)
                  for x, y in pins]
    verse = kh.union([verse] + pin_meshes)

    # shelf: slab with rounded front corners + flange under its back edge
    z0 = T
    slab2d = kh.rounded_rect(-W / 2, z0 - SHELF_CORNER_R - 1, W / 2, z0 + SHELF_D, SHELF_CORNER_R)
    slab2d = slab2d.intersection(box(-W, z0, W, z0 + SHELF_D + 1))
    slab = kh.extrude_y(slab2d, SHELF_BOTTOM, SHELF_TOP)
    flange = kh.box3(-W / 2, W / 2, SHELF_BOTTOM - FLANGE_H, SHELF_BOTTOM + 0.01, z0, z0 + FLANGE_T)
    shelf = kh.union([slab, flange])
    shelf = kh.difference(shelf, [kh.pilot_hole_z(x, SCREW_Y, z0, 5.0) for x in FLANGE_SCREWS_X])

    # pegs: plain cylinders, slightly wider end so rings stay on
    peg_print = make_peg()
    pegs = []
    for x in PEG_X:
        m = peg_print.copy()
        m.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]))
        m.apply_translation([x, PEG_Y, T + PEG_LEN])
        pegs.append(m)

    assembly = {"panel": (panel, "black"), "shelf": (shelf, "black"), "verse": (verse, "gold")}
    for i, m in enumerate(pegs):
        assembly[f"peg_{i + 1}"] = (m, "black")

    # print orientation
    prints = {}
    p = panel.copy()
    p.apply_translation(-p.bounds[0])
    prints["panel.stl"] = p
    sh = shelf.copy()   # upside down: shelf top on the bed, flange up
    sh.apply_transform(trimesh.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0]))
    sh.apply_translation(-sh.bounds[0])
    prints["shelf.stl"] = sh
    v = verse.copy()    # front face down, pins up
    v.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [0, 1, 0]))
    v.apply_translation(-v.bounds[0])
    prints["verse.stl"] = v
    prints["peg.stl"] = peg_print

    # fit check: the assembled parts must not overlap (touching is fine)
    clashes = {}
    names = ["panel", "shelf", "verse"] + [f"peg_{i + 1}" for i in range(len(pegs))]
    meshes = {n: assembly[n][0] for n in names}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if a.startswith("peg") and b.startswith("peg"):
                continue
            inter = trimesh.boolean.intersection([meshes[a], meshes[b]], engine="manifold")
            with np.errstate(all="ignore"):
                vol = float(inter.volume) if len(inter.faces) else 0.0
            if vol > 1.0:   # mm^3
                clashes[f"{a}/{b}"] = round(vol, 1)
    vb = verse2d.bounds
    meta = {
        "design": "04-fluted-arch",
        "verse_em_mm": round(info["em_mm"], 1),
        "verse_size_mm": [round(vb[2] - vb[0], 1), round(vb[3] - vb[1], 1), VERSE_T],
        "verse_pieces": len(kh.polys(verse2d)),
        "verse_bridges": len(bridges),
        "verse_strokes_under_0.8mm_pct": kh.thin_area_pct(verse2d),
        "verse_trim_mm": TRIM_W,
        "verse_top_above_arch_mm": round(vb[3] - (YC + R), 1),
        "pins": [[round(x, 1), round(y, 1)] for x, y in pins],
        "reeds": int((W - 2 * RIM) // FLUTE_PITCH),
        "assembly_clashes_mm3": clashes,
        "overall_mm": [round(max(W, vb[2] - vb[0]), 1), round(max(YC + R, vb[3]), 1), round(T + SHELF_D, 1)],
    }
    return assembly, prints, meta


def make_peg():
    """Peg in print orientation: end face on the bed, tenon on top."""
    r, re_, rt = PEG_D / 2, PEG_END_D / 2, kh.PEG_TENON_D / 2
    prof = [(0, 0), (re_ - 0.6, 0), (re_, 0.6), (re_, 2.5), (r, 2.5 + (re_ - r)),
            (r, PEG_LEN), (rt, PEG_LEN), (rt, PEG_LEN + kh.PEG_TENON_L - 0.5),
            (rt - 0.5, PEG_LEN + kh.PEG_TENON_L), (0, PEG_LEN + kh.PEG_TENON_L)]
    m = trimesh.creation.revolve(np.array(prof), sections=72)
    if m.volume < 0:
        m.invert()
    return m


if __name__ == "__main__":
    a, p, m = build()
    rep = kh.write_outputs(HERE, a, p, m)
    print(json.dumps(m, ensure_ascii=False))
    for r in rep:
        print(r)
