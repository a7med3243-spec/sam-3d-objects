"""Independent check of the EXPORTED files (reads the 3MF back, not the in-memory model)."""
import sys, zipfile, json
import numpy as np, trimesh
import xml.etree.ElementTree as ET
from manifold3d import Manifold, Mesh
from shapely.geometry import Polygon
from shapely.ops import unary_union

F3MF = sys.argv[1]; LAYER = 0.2
ns = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
root = ET.fromstring(zipfile.ZipFile(F3MF).read('3D/3dmodel.model'))
parts = {}
for o in root.find('m:resources', ns).findall('m:object', ns):
    me = o.find('m:mesh', ns)
    if me is None: continue
    v = np.array([[float(x.get(k)) for k in 'xyz'] for x in me.find('m:vertices', ns)])
    f = np.array([[int(x.get(k)) for k in ('v1', 'v2', 'v3')] for x in me.find('m:triangles', ns)])
    parts[o.get('name')] = trimesh.Trimesh(v, f, process=True)
names = list(parts)
rep = {'parts': {}}
mf = {}
for n, m in parts.items():
    mf[n] = Manifold(Mesh(vert_properties=m.vertices.astype(np.float32), tri_verts=m.faces.astype(np.uint32)))
    rep['parts'][n] = dict(watertight=bool(m.is_watertight), winding_ok=bool(m.is_winding_consistent),
                           volume_mm3=round(float(m.volume), 1), triangles=len(m.faces),
                           grams_PLA_100pct=round(float(m.volume) * 1.24e-3, 2),
                           z_range=[round(float(m.bounds[0][2]), 3), round(float(m.bounds[1][2]), 3)],
                           manifold_ok=mf[n].status().name == 'NoError')
ov = {}
for i in range(3):
    for j in range(i + 1, 3):
        ov[f'{names[i][:12]} x {names[j][:12]}'] = round((mf[names[i]] ^ mf[names[j]]).volume(), 4)
rep['overlap_volumes_mm3'] = ov
U = mf[names[0]] + mf[names[1]] + mf[names[2]]
rep['assembled'] = dict(bodies=len(U.decompose()), genus=U.genus(), volume_mm3=round(U.volume(), 1),
                        size_mm=[round(b - a, 2) for a, b in zip(U.bounding_box()[:3], U.bounding_box()[3:])])

def sl(m, z):
    ps = m.slice(z).to_polygons()
    g = Polygon()
    for p in sorted([Polygon(p).buffer(0) for p in ps if len(p) > 2], key=lambda p: -p.area): g = g.symmetric_difference(p)
    return g
zmax = rep['assembled']['size_mm'][2]
layers = []; prev = None; overhang = 0.0; seq = []
for k in range(int(round(zmax / LAYER))):
    z = (k + 0.5) * LAYER
    cols = [n for n in names if sl(mf[n], z).area > 0.01]
    layers.append((round(z, 2), [c.split(' ')[2] for c in cols]))
    allg = unary_union([sl(mf[n], z) for n in names])
    if prev is not None: overhang = max(overhang, allg.difference(prev.buffer(LAYER * 1.0)).area)  # >45 deg unsupported
    prev = allg
    order = sorted(cols, key=lambda c: 0 if seq and c == seq[-1] else 1)
    for c in order:
        if not seq or seq[-1] != c: seq.append(c)
rep['filament_changes_per_plate'] = len(seq) - 1
rep['max_overhang_area_beyond_45deg_mm2'] = round(overhang, 4)
# compress layer table
tab = []
for z, c in layers:
    if tab and tab[-1][2] == c: tab[-1][1] = z
    else: tab.append([z, z, c])
rep['layer_colours'] = [f'z {a - 0.1:.1f}-{b + 0.1:.1f} mm: {"+".join(c)}' for a, b, c in tab]
# ring wall and hole
ring = sl(U, 1.5)
hole = [Polygon(h) for p in (ring.geoms if hasattr(ring, 'geoms') else [ring]) for h in p.interiors]
if hole:
    h = max(hole, key=lambda p: p.area); r_h = (h.area / np.pi) ** 0.5
    rep['key_ring_hole_diameter_mm'] = round(2 * r_h, 2)
    top = U.bounding_box()[4]; cy = h.centroid.y
    rep['ring_wall_top_mm'] = round(top - (cy + r_h), 2)
print(json.dumps(rep, indent=1))
