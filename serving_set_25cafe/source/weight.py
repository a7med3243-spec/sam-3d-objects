"""Estimate printed grams per colour like a slicer would: 3 walls (~1.3 mm), top 1.0 mm / bottom 0.6 mm solid,
15 % sparse infill, PLA 1.25 g/cm3. Slices every layer of the exported STLs."""
import sys, glob, numpy as np, trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union
base, dz = sys.argv[1], float(sys.argv[2])
WALL, TOP, BOT, INF, RHO = 1.3, 1.0, 0.6, 0.15, 1.25e-3
parts = {f.split('_')[-1][:-4]: trimesh.load(f) for f in sorted(glob.glob(base + '_*.stl'))}
def sl(m, z):
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if s is None: return Polygon()
    rr = sorted([Polygon(np.asarray(p)[:, :2]).buffer(0) for p in s.discrete if len(p) > 2], key=lambda p: -p.area)
    g = Polygon()
    for r in rr: g = g.symmetric_difference(r)
    return g
zmax = max(m.bounds[1][2] for m in parts.values())
zs = np.arange(dz / 2, zmax, dz)
U = {round(z, 4): unary_union([sl(m, z) for m in parts.values()]) for z in zs}
def Uat(z):
    k = min(U, key=lambda q: abs(q - z)); return U[k] if 0 < z < zmax else Polygon()
grams = {n: 0.0 for n in parts}; solid_total = 0
for z in zs:
    A = U[round(z, 4)]
    if A.is_empty: continue
    core = A.buffer(-WALL)
    covered = core.intersection(Uat(z + TOP).buffer(-WALL)).intersection(Uat(z - BOT).buffer(-WALL))
    solid = A.difference(covered); sparse = covered
    for n, m in parts.items():
        P = sl(m, z)
        if P.is_empty: continue
        grams[n] += (P.intersection(solid).area + INF * P.intersection(sparse).area) * dz * RHO
tot = sum(grams.values())
solid_g = sum(m.volume for m in parts.values()) * RHO
print({n: round(g, 2) for n, g in grams.items()}, 'TOTAL', round(tot, 2), 'g   (100% solid would be', round(solid_g, 2), 'g)')
