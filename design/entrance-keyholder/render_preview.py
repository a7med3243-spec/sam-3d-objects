"""Render simple shaded previews of keyholder.stl (front and oblique views)."""
import os
import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__))
mesh = trimesh.load(os.path.join(HERE, "keyholder.stl"))
# Wall-mount frame: X right, Y up, Z out of wall. Matplotlib 3D uses (x, y, z) with z up,
# so plot with horizontal = X, vertical = Y, depth = Z mapped to matplotlib's z.
V = mesh.vertices
F = mesh.faces
light = np.array([0.4, 0.5, 0.8]); light /= np.linalg.norm(light)
normals = mesh.face_normals
shade = np.clip(normals @ light, 0, 1) * 0.75 + 0.25
base = np.array([0.80, 0.66, 0.46])  # wood-like tone
colors = np.clip(shade[:, None] * base[None, :], 0, 1)

def render(elev, azim, name, title):
    fig = plt.figure(figsize=(9, 7), dpi=110)
    ax = fig.add_subplot(111, projection="3d")
    tris = V[F]
    coll = Poly3DCollection(tris, facecolors=colors, edgecolor="none", linewidth=0)
    ax.add_collection3d(coll)
    ax.set_xlim(0, 210); ax.set_ylim(-60, 0); ax.set_zlim(-5, 125)
    ax.set_box_aspect((210, 60, 130))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_title(title, fontsize=11)
    fig.savefig(os.path.join(HERE, name), bbox_inches="tight", facecolor="white")
    plt.close(fig)

# Front view: looking at the wall from the room (camera on +Z, looking -Z).
# Matplotlib's z is vertical, so map the mesh: plot_x = X, plot_y = Z(depth), plot_z = Y(up).
V2 = np.column_stack([V[:, 0], -V[:, 2], V[:, 1]])
V = V2
render(elev=8, azim=-90, name="preview_front.png", title="Front view")
render(elev=24, azim=-60, name="preview_oblique.png", title="Oblique view")
print("ok")
