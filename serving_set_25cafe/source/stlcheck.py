import sys, glob, numpy as np, trimesh
from manifold3d import Manifold, Mesh64
ok = True
for f in sorted(glob.glob(sys.argv[1] + '*.stl')):
    m = trimesh.load(f, process=True)          # exact-duplicate merge, like a slicer
    nz = int((m.area_faces < 1e-10).sum())
    e = np.linalg.norm(m.vertices[m.faces[:, [1, 2, 0]]] - m.vertices[m.faces], axis=2)
    print(f.split('/')[-1], 'tris', len(m.faces), 'watertight', m.is_watertight, 'winding', m.is_winding_consistent, 'zero-area', nz, 'min edge um', round(e.min() * 1000, 2))
    ok &= m.is_watertight and m.is_winding_consistent
print('ALL OK' if ok else 'PROBLEM')
