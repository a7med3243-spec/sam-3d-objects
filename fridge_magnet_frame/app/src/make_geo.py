"""Build geo.json for the nameplate maker: the verified plate bodies (normal / tight grip)
split into their flat top face loop + the rest, and a cropped frame for the preview.

usage (from fridge_magnet_frame/):
  ./render.sh insert app/src/base_normal.stl -D 'label=""'
  ./render.sh insert app/src/base_tight.stl  -D 'label=""' -D 'plate_grip=0.6'
  python3 app/src/make_geo.py app/src
  python3 app/src/build_app.py app/nameplate_maker.html
"""
import sys, os, base64, json
from collections import defaultdict
import numpy as np, trimesh

d = sys.argv[1]
enc = lambda a: base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()
out = {}
for name in ["normal", "tight"]:
    m = trimesh.load(os.path.join(d, f"base_{name}.stl")); m.merge_vertices()
    V, F = m.vertices, m.faces
    top = np.all(V[F][:, :, 2] > V[:, 2].max() - 1e-4, axis=1)
    cnt, dire = defaultdict(int), {}
    for f in F[top]:
        for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
            k = (min(a, b), max(a, b)); cnt[k] += 1; dire[k] = (a, b)
    nxt = {a: b for a, b in (dire[k] for k, c in cnt.items() if c == 1)}
    start = next(iter(nxt)); loop = [start]; cur = nxt[start]
    while cur != start: loop.append(cur); cur = nxt[cur]
    loop = np.array(loop); xy = V[loop, :2]
    if np.sum(xy[:, 0] * np.roll(xy[:, 1], -1) - np.roll(xy[:, 0], -1) * xy[:, 1]) < 0: loop = loop[::-1]
    out[name] = {"pos": enc(V.astype(np.float32)), "idx": enc(F[~top].astype(np.uint16)), "loop": enc(loop.astype(np.uint16))}
f = trimesh.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "stl", "frame.stl"))
c = f.triangles_center
fc = f.submesh([np.where((c[:, 1] < -16.5) & (np.abs(c[:, 0]) < 34))[0]], append=True); fc.merge_vertices()
out["frame"] = {"pos": enc(fc.vertices.astype(np.float32)), "idx": enc(fc.faces.astype(np.uint16)), "u32": False}
json.dump(out, open(os.path.join(d, "geo.json"), "w"))
print("geo.json written")
