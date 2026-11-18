"""
Design 5 — "اللوح الخشبي" (The Walnut Board)

After the reference photo: a walnut board with rounded corners, a shelf across its upper
part, a white panel of soft wavy fluting under the shelf, and brass knobs below.

The verse ﴿وَلَسَوۡفَ يُعۡطِيكَ رَبُّكَ فَتَرۡضَىٰٓ﴾ (Ad-Duha 93:5) is written in Quranic Naskh
(Amiri Quran) with every mark, in a dark colour, rising out of the white fluting. It is
part of the white panel, so every dot and mark stays attached; one filament change at
the height of the reed crests prints it dark.

Two sizes, every part fitting a 220 x 220 mm bed:
  small  - 210 x 122 mm, each part in one piece
  large  - 360 x 209 mm (close to the photo), board, shelf and white panel each in two
           halves. Each board half hangs on its own wall screw; the halves meet on four
           pins of 1.75 mm filament and glue, and the white panel and the shelf (cut at
           other places) cross the board seam and tie the halves together.
"""

import json
import math
import os
import sys

import numpy as np
import trimesh
from shapely import affinity
from shapely.geometry import LineString, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import kh  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

SIZES = {
    "small": dict(
        W=210.0, H=122.0, T=8.0, CORNER_R=10.0,
        SHELF_T=8.0, SHELF_TOP=89.0, SHELF_D=55.0, SHELF_R=3.0,
        SHELF_SCREWS_X=(-80.0, 0.0, 80.0),
        PANEL_X=100.0, PANEL_Y0=32.0, RECESS=1.0, PANEL_BASE=4.0, REED_H=3.0, REED_PITCH=4.5,
        KNOB_Y=16.0, KNOB_X=(-76.0, -38.0, 0.0, 38.0, 76.0),
        NECK_D=8.0, NECK_L=13.0, CAP_D=14.0, CAP_T=7.0,
        KEYHOLES=((-70.0, 102.0), (70.0, 102.0)),
        VERSE_W=180.0, VERSE_THICKEN=0.08, RELIEF=1.4, SPLIT=False),
    "large": dict(
        W=360.0, H=209.0, T=10.0, CORNER_R=16.0,
        SHELF_T=12.0, SHELF_TOP=152.0, SHELF_D=90.0, SHELF_R=5.0,
        SHELF_SCREWS_X=(-160.0, -100.0, -45.0, 45.0, 100.0, 160.0),
        PANEL_X=170.0, PANEL_Y0=55.0, RECESS=1.2, PANEL_BASE=5.0, REED_H=4.0, REED_PITCH=6.0,
        KNOB_Y=27.0, KNOB_X=(-137.5, -82.5, -27.5, 27.5, 82.5, 137.5),
        NECK_D=11.0, NECK_L=18.0, CAP_D=20.0, CAP_T=9.0,
        KEYHOLES=((-130.0, 178.0), (130.0, 178.0)),
        VERSE_W=298.0, VERSE_THICKEN=0.15, RELIEF=1.6, SPLIT=True,
        SEAM_DOWELS_Y=(18.0, 75.0, 120.0, 190.0),   # 1.75 mm filament pins across the board seam
        SHELF_SEAM_X=20.0),                          # shelf joint staggered from the board seam
}


# ----------------------------------------------------------------------------
def reed_fn(c):
    """Soft vertical reeds whose crests drift in slow waves, like draped fabric."""
    k = c["W"] / 210.0
    base, h, pitch = c["PANEL_BASE"], c["REED_H"], c["REED_PITCH"]

    def f(X, Y):
        xs, ys = X / k, Y / k
        amp = 1.1 + 0.8 * np.sin(xs / 29.0 + 0.7) * np.cos(xs / 53.0)
        drift = amp * np.sin(2 * np.pi * ys / 64.0 + xs / 31.0) + 0.35 * np.sin(2 * np.pi * ys / 29.0 + xs / 13.0)
        u = (X - drift * k) / pitch
        return base + h * (0.5 + 0.5 * np.cos(2 * np.pi * u)) ** 0.75
    return f


def verse_geometry(c, panel_y0, panel_y1):
    g, info = kh.shape_text(kh.VERSE_MUSHAF, kh.FONT_NASKH, width_mm=c["VERSE_W"])
    g = g.buffer(c["VERSE_THICKEN"], quad_segs=6)
    b = g.bounds
    g = affinity.translate(g, 0, (panel_y0 + panel_y1) / 2 - (b[1] + b[3]) / 2)
    return g, info


def min_gap(g):
    ps = kh.polys(g)
    return min(min(p.distance(q) for j, q in enumerate(ps) if j != i) for i, p in enumerate(ps))


def make_knob(c):
    """Brass knob in print orientation: flat face on the bed, tenon on top."""
    rc, rn, rt = c["CAP_D"] / 2, c["NECK_D"] / 2, kh.PEG_TENON_D / 2
    ct, nl = c["CAP_T"], c["NECK_L"]
    prof = [(0, 0), (rc - 1.2, 0), (rc - 0.35, 0.35), (rc, 1.2),
            (rc, ct - (rc - rn) * 0.6), (rn, ct + 1.5),
            (rn, ct + nl), (rt, ct + nl), (rt, ct + nl + kh.PEG_TENON_L - 0.5),
            (rt - 0.5, ct + nl + kh.PEG_TENON_L), (0, ct + nl + kh.PEG_TENON_L)]
    m = trimesh.creation.revolve(np.array(prof), sections=72)
    if m.volume < 0:
        m.invert()
    return m


def clip_x(mesh, x0, x1):
    cl = kh.box3(x0, x1, -1000, 1000, -1000, 1000)
    return trimesh.boolean.intersection([mesh, cl], engine="manifold")


def x_dowel(x, y, z, d=2.0, depth=10.0):
    """Hole along X centred on a cut at x, for a pin of 1.75 mm filament (depth each side)."""
    m = trimesh.creation.cylinder(radius=d / 2, height=2 * depth, sections=24)
    m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
    m.apply_translation([x, y, z])
    return m


def best_split_x(verse2d, y0, y1, lo=-25.0, hi=25.0):
    """x for a vertical cut through the panel that keeps the most room from the letters."""
    best = None
    for x in np.arange(lo, hi + 0.01, 0.5):
        d = LineString([(x, y0), (x, y1)]).distance(verse2d)
        if best is None or d > best[0]:
            best = (d, float(x))
    return best[1], best[0]


# ----------------------------------------------------------------------------
def build(size):
    c = SIZES[size]
    W, H, T = c["W"], c["H"], c["T"]
    shelf_top, shelf_t = c["SHELF_TOP"], c["SHELF_T"]
    shelf_bottom = shelf_top - shelf_t
    px, py0, py1 = c["PANEL_X"], c["PANEL_Y0"], shelf_bottom
    panel_z0 = T - c["RECESS"]
    crest = c["PANEL_BASE"] + c["REED_H"]            # colour change height in the panel's print
    sy = shelf_bottom + shelf_t / 2                   # screw line into the shelf's back edge

    # --- board
    board = kh.extrude(kh.rounded_rect(-W / 2, 0, W / 2, H, c["CORNER_R"]), 0, T)
    cut = [kh.extrude(box(-px - 0.2, py0 - 0.2, px + 0.2, py1 + 0.2), panel_z0, T + 1)]
    cut += [kh.peg_hole(x, c["KNOB_Y"], T, depth=6.0) for x in c["KNOB_X"]]
    cut += [kh.keyhole_cutter(x, y) for x, y in c["KEYHOLES"]]
    cut += [kh.screw_from_back(x, sy, T) for x in c["SHELF_SCREWS_X"]]
    if c["SPLIT"]:
        cut += [x_dowel(0.0, yy, T / 2) for yy in c["SEAM_DOWELS_Y"]]
    board = kh.difference(board, cut)

    # --- white panel with the dark verse
    panel = kh.heightfield_solid(-px, px, py0, py1, c["REED_PITCH"] / 11.0, 1.0, reed_fn(c))
    panel = trimesh.boolean.intersection(
        [panel, kh.extrude(kh.rounded_rect(-px, py0, px, py1, 1.5), -1, crest + 1)], engine="manifold")
    verse2d, vinfo = verse_geometry(c, py0, py1)
    letters = kh.extrude(verse2d, c["PANEL_BASE"] - 0.01, crest + c["RELIEF"])
    panel_white = kh.difference(panel, [letters])      # for multi-colour printers
    panel_full = kh.union([panel, letters])             # single body: change filament at `crest`
    for m in (panel_white, letters, panel_full):
        m.apply_translation([0, 0, panel_z0])

    # --- shelf
    slab2d = kh.rounded_rect(-W / 2, T - c["SHELF_R"] - 1, W / 2, T + c["SHELF_D"], c["SHELF_R"])
    slab2d = slab2d.intersection(box(-W, T, W, T + c["SHELF_D"] + 1))
    shelf = kh.extrude_y(slab2d, shelf_bottom, shelf_top)
    shelf = kh.difference(shelf, [kh.pilot_hole_z(x, sy, T, 10.0) for x in c["SHELF_SCREWS_X"]])

    # --- knobs
    knob_print = make_knob(c)
    knobs = []
    for x in c["KNOB_X"]:
        m = knob_print.copy()
        m.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]))
        m.apply_translation([x, c["KNOB_Y"], T + c["CAP_T"] + c["NECK_L"]])
        knobs.append(m)

    # --- assembly (for renders and the clash check)
    assembly = {"board": (board, "walnut"), "panel_white": (panel_white, "ivory"),
                "verse_dark": (letters, "espresso"), "shelf": (shelf, "walnut")}
    for i, m in enumerate(knobs):
        assembly[f"knob_{i + 1}"] = (m, "brass")

    # --- print parts
    rot_x = lambda a: trimesh.transformations.rotation_matrix(a, [1, 0, 0])  # noqa: E731

    def placed(m, tf=None):
        m = m.copy()
        if tf is not None:
            m.apply_transform(tf)
        m.apply_translation(-m.bounds[0])
        return m

    prints, counts = {}, {}
    split_info = {}
    if not c["SPLIT"]:
        shift = -panel_full.bounds[0]
        prints["board.stl"] = placed(board)
        for name, m in (("panel_white_with_verse.stl", panel_full), ("mmu_panel_white.stl", panel_white),
                        ("mmu_verse_dark.stl", letters)):
            mm = m.copy()
            mm.apply_translation(shift)
            prints[name] = mm
        prints["shelf.stl"] = placed(shelf, rot_x(-math.pi / 2))
    else:
        bl, br = clip_x(board, -W, 0), clip_x(board, 0, W)
        prints["board_left.stl"] = placed(bl)
        prints["board_right.stl"] = placed(br)

        xs, clearance = best_split_x(verse2d, py0, py1)
        split_info.update({"panel_cut_x_mm": xs, "panel_cut_clearance_mm": round(clearance, 2)})
        shift = None
        for side, (a, b) in (("left", (-W, xs)), ("right", (xs, W))):
            full = clip_x(panel_full, a, b)
            off = -full.bounds[0]
            for name, m in ((f"panel_{side}_white_with_verse.stl", full),
                            (f"mmu_panel_{side}_white.stl", clip_x(panel_white, a, b)),
                            (f"mmu_verse_{side}_dark.stl", clip_x(letters, a, b))):
                mm = m.copy()
                mm.apply_translation(off)
                prints[name] = mm
        # shelf halves, cut away from the board seam, with two filament pins
        xs_sh = c["SHELF_SEAM_X"]
        sh = kh.difference(shelf, [x_dowel(xs_sh, sy, zz)
                                   for zz in (T + 0.3 * c["SHELF_D"], T + 0.75 * c["SHELF_D"])])
        prints["shelf_left.stl"] = placed(clip_x(sh, -W, xs_sh), rot_x(-math.pi / 2))
        prints["shelf_right.stl"] = placed(clip_x(sh, xs_sh, W), rot_x(-math.pi / 2))
        split_info["shelf_cut_x_mm"] = xs_sh
    prints["knob.stl"] = knob_print
    counts["knob.stl"] = len(c["KNOB_X"])

    # --- checks
    clashes = {}
    names = [n for n in assembly]
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if a.startswith("knob") and b.startswith("knob"):
                continue
            inter = trimesh.boolean.intersection([assembly[a][0], assembly[b][0]], engine="manifold")
            with np.errstate(all="ignore"):
                vol = float(inter.volume) if len(inter.faces) else 0.0
            if vol > 1.0:
                clashes[f"{a}/{b}"] = round(vol, 1)

    meta = {
        "design": "05-walnut-board", "size": size,
        "overall_mm": [W, H, round(T + c["SHELF_D"], 1)],
        "verse_text": kh.VERSE_MUSHAF,
        "verse_codepoints": " ".join(f"U+{ord(ch):04X}" for ch in kh.VERSE_MUSHAF),
        "verse_font": "Amiri Quran",
        "verse_em_mm": round(vinfo["em_mm"], 1),
        "verse_size_mm": [round(verse2d.bounds[2] - verse2d.bounds[0], 1),
                          round(verse2d.bounds[3] - verse2d.bounds[1], 1)],
        "verse_pieces_dots_and_marks": len(kh.polys(verse2d)),
        "verse_smallest_gap_mm": round(min_gap(verse2d), 2),
        "verse_strokes_under_0.8mm_pct": kh.thin_area_pct(verse2d),
        "panel_colour_change_z_mm": crest,
        "assembly_clashes_mm3": clashes,
        "counts": counts,
        **split_info,
    }
    return assembly, prints, meta


def write(size):
    a, p, m = build(size)
    out = os.path.join(HERE, size)
    rep = kh.write_outputs(out, a, p, m)
    return m, rep


if __name__ == "__main__":
    for size in sys.argv[1:] or list(SIZES):
        m, rep = write(size)
        print(json.dumps({k: v for k, v in m.items() if k not in ("verse_codepoints",)}, ensure_ascii=False))
        for r in rep:
            print("  ", r)
