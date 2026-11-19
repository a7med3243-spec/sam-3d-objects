"""Cross-section figure of the 30 cm main piece: shelf and a knob with their reinforcing screws."""
import importlib.util
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from trimesh.intersections import mesh_plane

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("walnut", os.path.join(HERE, "build.py"))
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)
c = w.SIZES["30cm"]
asm, _, _ = w.build_merged("30cm")
main, panel = asm["main_brown"][0], asm["panel_white"][0]

fig, axs = plt.subplots(1, 2, figsize=(11, 5.2), dpi=140, gridspec_kw={"width_ratios": [1.6, 1]})
for ax, x, title, view in ((axs[0], c["REBAR_SHELF_X"][1], "Shelf section (through a screw)", (95, 160)),
                           (axs[1], c["KNOB_X"][2], "Knob section", (5, 40))):
    for mesh, col in ((main, "#6B4A33"), (panel, "#bdb6aa")):
        segs = mesh_plane(mesh, plane_normal=[1, 0, 0], plane_origin=[x, 0, 0])
        for s in segs:
            ax.plot(s[:, 2], s[:, 1], color=col, lw=1.4)
    T = c["T"]
    if "Shelf" in title:
        y = c["SHELF_TOP"] - c["REBAR_SHELF_FROM_TOP"]
        ax.add_patch(Rectangle((0, y - 2), 60, 4, fc="#9aa3ab", ec="#555", lw=0.6))
        ax.text(30, y + 4.5, "4 x 60 mm screw", ha="center", fontsize=9)
        ax.text(T + c["SHELF_D"] - 2, c["SHELF_TOP"] + c["LIP"] + 3, "phone lip", ha="right", fontsize=9)
        ax.text(T + 9, c["SHELF_TOP"] + c["COVE"] + 4, "rounded root", fontsize=9)
        ax.text(T + 14, c["SHELF_TOP"] - c["SHELF_T"] - 7, "verse panel (glued)", fontsize=9, color="#7a7469")
        ax.set_xlim(-5, T + c["SHELF_D"] + 8)
    else:
        y = c["KNOB_Y"]
        ax.add_patch(Rectangle((0, y - 1.5), 25, 3, fc="#9aa3ab", ec="#555", lw=0.6))
        ax.text(12, y + 13, "M3 x 25 screw", ha="center", fontsize=9)
        ax.set_xlim(-5, 40)
    ax.set_ylim(*view)
    ax.axvline(0, color="#999", lw=1, ls="--")
    ax.text(0.5, view[1] - 4, "wall", fontsize=8, color="#777")
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("mm from the wall")
fig.tight_layout()
out = os.path.join(HERE, "30cm", "print_kit", "section.png")
fig.savefig(out, facecolor="white", bbox_inches="tight")
print(out)
