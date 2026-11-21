"""
Print kit for the walnut board (30 cm or small) on a Bambu Lab A2L (330 x 320 mm bed).

Nothing is cut. Board, shelf and knobs are ONE strong piece; only the verse panel prints
on its own. Each plate runs on one filament (the white panel switches once, to the dark
verse, at the reed crests):
  1  brown  - board + shelf + knobs in one piece (4 walls, 15 % gyroid)
  2  white  - wavy panel with the verse in dark (one filament change), glued in (2 walls, 10 %)
Builds <size>/print_kit/ (python3 print_kit.py [30cm|small]): the plates as 3MF (parts placed, filament slots set), a plate
layout figure, an exploded assembly for the render, and plates.json with the weight and
time of each plate measured by PrusaSlicer. make_guide.py then writes the Arabic guide
and the ZIP.
"""

import json
import math
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from xml.sax.saxutils import escape

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
SIZE = sys.argv[1] if len(sys.argv) > 1 else "30cm"      # "30cm" or "small"
STL = os.path.join(HERE, SIZE, "stl")
OUT = os.path.join(HERE, SIZE, "print_kit")
BED_X, BED_Y, BED_Z = 330.0, 320.0, 325.0     # Bambu Lab A2L
GAP = 10.0

COLOUR = {"walnut": "#6B4A33", "white": "#F1EDE6", "dark": "#2A1D16", "brass": "#C8A25A"}

# plate id, title, objects; each object is a list of (stl, colour) volumes
PLATES = [
    ("1_brown_main_board_shelf_knobs", "Brown: board + shelf + knobs (one piece)",
     [[("main_brown_board_shelf_knobs.stl", "walnut")]]),
    ("2_white_panel_dark_verse", "White panel + dark verse",
     [[("mmu_panel_white.stl", "white"), ("mmu_verse_dark.stl", "dark")]]),
]


PROFILE_OF = {"1_brown_main_board_shelf_knobs": "strong", "2_white_panel_dark_verse": "light"}


def load(name):
    return trimesh.load(os.path.join(STL, name), force="mesh")


def layout(objects):
    """Place objects (lists of meshes sharing one frame) on the bed; returns offsets."""
    sizes = [np.max([m.bounds[1] for m in o], axis=0)[:2] - np.min([m.bounds[0] for m in o], axis=0)[:2]
             for o in objects]
    mins = [np.min([m.bounds[0] for m in o], axis=0)[:2] for o in objects]
    n = len(objects)
    if n <= 2:                                   # stacked along Y, centred
        total = sum(s[1] for s in sizes) + GAP * (n - 1)
        y = (BED_Y - total) / 2
        offs = []
        for s, mn in zip(sizes, mins):
            offs.append(np.array([(BED_X - s[0]) / 2, y]) - mn)
            y += s[1] + GAP
        return offs
    cols = 3                                     # small parts on a grid
    rows = math.ceil(n / cols)
    pitch = max(max(s) for s in sizes) + GAP
    x0 = (BED_X - (cols - 1) * pitch) / 2
    y0 = (BED_Y - (rows - 1) * pitch) / 2
    offs = []
    for i, (s, mn) in enumerate(zip(sizes, mins)):
        cx, cy = x0 + (i % cols) * pitch, y0 + (i // cols) * pitch
        offs.append(np.array([cx - s[0] / 2, cy - s[1] / 2]) - mn)
    return offs


def write_plate_3mf(path, objects):
    """objects: list of (name, [(mesh, volume_name, extruder), ...]) with baked positions."""
    res, cfg = [], []
    for oid, (oname, vols) in enumerate(objects, start=1):
        V, F, ranges, off, t0 = [], [], [], 0, 0
        for m, vname, ext in vols:
            V.append(m.vertices)
            F.append(m.faces + off)
            ranges.append((vname, t0, t0 + len(m.faces) - 1, ext))
            off += len(m.vertices)
            t0 += len(m.faces)
        V, F = np.vstack(V), np.vstack(F)
        v = "".join(f'<vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in V)
        t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in F)
        res.append(f'<object id="{oid}" type="model" name="{escape(oname)}"><mesh>'
                   f'<vertices>{v}</vertices><triangles>{t}</triangles></mesh></object>')
        vx = "".join(
            f'<volume firstid="{a}" lastid="{b}"><metadata type="volume" key="name" value="{escape(n)}"/>'
            '<metadata type="volume" key="volume_type" value="ModelPart"/>'
            f'<metadata type="volume" key="extruder" value="{e}"/>'
            '<metadata type="volume" key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>'
            '<mesh edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" '
            'backwards_edges="0"/></volume>' for n, a, b, e in ranges)
        cfg.append(f'<object id="{oid}" instances_count="1">'
                   f'<metadata type="object" key="name" value="{escape(oname)}"/>{vx}</object>')
    items = "".join(f'<item objectid="{i}" printable="1"/>' for i in range(1, len(objects) + 1))
    model = ('<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
             'xmlns:slic3rpe="http://schemas.slic3r.org/3mf/2017/06">'
             '<metadata name="slic3rpe:Version3mf">1</metadata>'
             f'<resources>{"".join(res)}</resources><build>{items}</build></model>')
    config = f'<?xml version="1.0" encoding="UTF-8"?><config>{"".join(cfg)}</config>'
    ctypes = ('<?xml version="1.0" encoding="UTF-8"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
              '<Default Extension="config" ContentType="text/xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
        z.writestr("Metadata/Slic3r_PE_model.config", config)


# Speeds and accelerations close to Bambu Lab's A-series PLA profile, so the time estimate
# is in the A2L's range (they change the time only, not the weight).
FAST = """
external_perimeter_speed = 200
perimeter_speed = 300
infill_speed = 270
solid_infill_speed = 250
top_solid_infill_speed = 200
gap_fill_speed = 250
travel_speed = 500
first_layer_speed = 50
bridge_speed = 50
max_volumetric_speed = 21
default_acceleration = 10000
perimeter_acceleration = 5000
external_perimeter_acceleration = 5000
infill_acceleration = 10000
travel_acceleration = 10000
first_layer_acceleration = 500
machine_limits_usage = time_estimate_only
machine_max_acceleration_extruding = 12000
machine_max_acceleration_travel = 12000
machine_max_acceleration_x = 12000
machine_max_acceleration_y = 12000
machine_max_feedrate_x = 500
machine_max_feedrate_y = 500
"""


def slice_plate(path, profile="normal"):
    sys.path.insert(0, HERE)
    import measure_weight as mw
    with tempfile.TemporaryDirectory() as wd:
        cfgp = os.path.join(wd, "pla.ini")
        with open(cfgp, "w") as f:
            f.write(mw.apply_profile(mw.config_for(SIZE)[0], profile) + FAST)  # same profiles as the weights
        out = os.path.join(wd, "p.gcode")
        subprocess.run(["prusa-slicer", "--export-gcode", "--load", cfgp, "--dont-arrange",
                        "--output", out, path], check=True, capture_output=True, timeout=3600)
        txt = open(out, errors="ignore").read()
    g = float(re.search(r"; total filament used \[g\] = ([\d.]+)", txt).group(1))
    t = re.search(r"; estimated printing time \(normal mode\) = (.+)", txt).group(1).strip()
    return g, t, mw.to_minutes(t)


def plate_figure(plates, path):
    """Top view of every plate on the bed, parts filled in their filament colour."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    import shapely

    def projected(m, **_):
        """Top-view outline: union of the upward-facing triangles."""
        up = m.face_normals[:, 2] > 1e-3
        tri = m.vertices[m.faces[up]][:, :, :2]
        e1, e2 = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
        area = 0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
        tri = tri[area > 1e-8]
        if not len(tri):
            return None
        polys = shapely.polygons(np.concatenate([tri, tri[:, :1]], axis=1))
        return shapely.union_all(shapely.buffer(polys, 0.02)).buffer(-0.02)
    fig, axs = plt.subplots(1, len(plates), figsize=(5.2 * len(plates), 5.2), dpi=130)
    for ax, (pid, title, objs, info) in zip(axs, plates):
        ax.add_patch(Rectangle((0, 0), BED_X, BED_Y, fc="#f3f1ec", ec="#999", lw=1))
        for _, vols in objs:
            for m, _, ext, colour in vols:
                shape = projected(m, normal=[0, 0, 1], ignore_sign=True)
                if shape is None:
                    continue
                for p in getattr(shape, "geoms", [shape]):
                    xs, ys = p.exterior.xy
                    ax.fill(xs, ys, fc=COLOUR[colour], ec="#333" if colour != "dark" else "none", lw=0.6)
                    for hole in p.interiors:
                        hx, hy = hole.xy
                        ax.fill(hx, hy, fc="#f3f1ec" if colour != "dark" else COLOUR["white"], ec="none")
        ax.set_xlim(-5, BED_X + 5)
        ax.set_ylim(-5, BED_Y + 5)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.set_title(f"Plate {pid[0]}: {title}\n{info['grams']:.0f} g  |  {info['time']}", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, facecolor="white", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


def build_kit():
    os.makedirs(os.path.join(OUT, "plates"), exist_ok=True)
    ext_of = {"walnut": 1, "white": 1, "dark": 2, "brass": 1}
    summary, fig_rows = [], []
    for pid, title, objs in PLATES:
        meshes = [[load(n) for n, _ in o] for o in objs]
        offs = layout(meshes)
        placed = []
        for k, (o, vols, off) in enumerate(zip(objs, meshes, offs)):
            vv = []
            for (name, colour), m in zip(o, vols):
                m = m.copy()
                m.apply_translation([off[0], off[1], 0])
                vv.append((m, name.replace(".stl", ""), ext_of[colour], colour))
            placed.append((f"{pid}_{k + 1}", vv))
        allb = np.array([[m.bounds for m, *_ in vv] for _, vv in placed]).reshape(-1, 2, 3)
        lo, hi = allb[:, 0].min(axis=0), allb[:, 1].max(axis=0)
        assert lo[0] >= 0 and lo[1] >= 0 and hi[0] <= BED_X and hi[1] <= BED_Y and hi[2] <= BED_Z, (pid, lo, hi)
        path = os.path.join(OUT, "plates", pid + ".3mf")
        write_plate_3mf(path, [(n, [(m, vn, e) for m, vn, e, _ in vv]) for n, vv in placed])
        g, t, mins = slice_plate(path, PROFILE_OF.get(pid, "normal"))
        info = {"plate": pid, "title": title, "file": f"plates/{pid}.3mf", "grams": round(g, 1),
                "time": t, "minutes": round(mins), "margin_mm": round(float(min(lo[0], lo[1], BED_X - hi[0], BED_Y - hi[1])), 1),
                "colours": sorted({c for _, vv in placed for *_, c in vv})}
        summary.append(info)
        fig_rows.append((pid, title, placed, info))
        print(info)
    plate_figure(fig_rows, os.path.join(OUT, "plates_layout.png"))
    total = {"total_grams": round(sum(p["grams"] for p in summary), 1),
             "total_hours": round(sum(p["minutes"] for p in summary) / 60, 1)}
    with open(os.path.join(OUT, "plates.json"), "w") as f:
        json.dump({"printer": "Bambu Lab A2L", "bed_mm": [BED_X, BED_Y, BED_Z], "plates": summary, **total},
                  f, indent=1)
    print(total)


def w_sizes():
    import importlib.util
    spec = importlib.util.spec_from_file_location("walnut_sizes", os.path.join(HERE, "build.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.SIZES


def exploded_assembly():
    """Main piece and the verse panel pulled apart, for an assembly picture."""
    c = w_sizes()[SIZE]
    import importlib.util
    spec = importlib.util.spec_from_file_location("walnut", os.path.join(HERE, "build.py"))
    w = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(w)
    asm, _, _ = w.build_merged(SIZE)
    out = os.path.join(OUT, "exploded")
    os.makedirs(out, exist_ok=True)
    pieces = [("main", asm["main_brown"][0], "walnut", (0, 0, 0)),
              ("panel", asm["panel_white"][0], "ivory", (0, -0.45 * c["H"], 0.4 * c["W"])),
              ("verse", asm["verse_dark"][0], "espresso", (0, -0.45 * c["H"], 0.4 * c["W"]))]
    manifest = []
    for name, m, mat, d in pieces:
        m = m.copy()
        m.apply_translation(d)
        m.export(os.path.join(out, name + ".stl"))
        manifest.append({"file": name + ".stl", "material": mat})
    with open(os.path.join(out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)


if __name__ == "__main__":
    build_kit()
    exploded_assembly()
