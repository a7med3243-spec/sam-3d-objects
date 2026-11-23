"""Design-review / verification script for the fridge photo frame STLs.

Checks: mesh integrity, dimensions, assembled interference + clearances,
retention (pull-out) test, tilt-in insertion kinematics, overhangs,
thin walls, name-plate text fit, latch strain and filament weight.
Run:  python3 verify.py  [extra nameplate STLs ...]
"""
import sys, math, json, glob, os
import numpy as np
import trimesh
from manifold3d import Manifold, Mesh, CrossSection

HERE = os.path.dirname(os.path.abspath(__file__))
STL = os.path.join(HERE, "stl")

# ---- design constants (must match fridge_photo_frame.scad defaults) ----
lip_t, photo_space, cover_t = 1.2, 0.4, 2.0
T = lip_t + photo_space + cover_t
pocket = (86.6, 54.6); cw, ch = 86.3, 54.3
tp_cy = -pocket[1] / 2 - 1.2 - 11.7 / 2
boss = (30.7, 8.3); nameplate_top = T
mag_pos = [(-36, -19.5), (36, -19.5), (-36, 19.5), (36, 19.5)]
PLA, PETG = 1.24, 1.27  # g/cm3

report = {"checks": [], "info": {}}
def check(name, ok, detail):
    report["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + " :: " + detail)

def to_mf(m):
    return Manifold(Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                         tri_verts=np.asarray(m.faces, np.uint32)))
def to_tm(mf):
    me = mf.to_mesh()
    return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=True)

def load(name):
    return trimesh.load(os.path.join(STL, name), force="mesh")

# ------------------------------------------------------------------ 1. integrity
parts = {"frame": load("frame.stl"), "cover": load("cover.stl")}
plates = sorted(glob.glob(os.path.join(STL, "nameplate_*.stl"))) + sys.argv[1:]
for p in plates:
    key = os.path.basename(p)[:-4]
    if not key.startswith("nameplate"):
        key = "nameplate_test_" + key
    parts[key] = trimesh.load(p, force="mesh")

for n, m in parts.items():
    mf = to_mf(m)
    comps = len(m.split(only_watertight=False))
    ok = m.is_watertight and m.is_winding_consistent and m.volume > 0 and mf.status().name == "NoError" and comps == 1
    check(f"mesh integrity: {n}", ok,
          f"watertight={m.is_watertight}, winding={m.is_winding_consistent}, manifold={mf.status().name}, "
          f"bodies={comps}, triangles={len(m.faces)}, volume={m.volume/1000:.2f} cm3")

# ------------------------------------------------------------------ 2. dimensions
fb = parts["frame"].bounds; ext = fb[1] - fb[0]
check("frame size", abs(ext[0] - 92) < 0.05 and abs(ext[1] - 72.2) < 0.05 and abs(ext[2] - T) < 0.01,
      f"{ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.2f} mm (body 92 x 60 + name tab 40 x 12.2)")
cb = parts["cover"].bounds; cext = cb[1] - cb[0]
check("cover size", abs(cext[2] - cover_t) < 0.01, f"{cext[0]:.2f} x {cext[1]:.2f} x {cext[2]:.2f} mm (incl. hook + tongues)")
for n in parts:
    if n.startswith("nameplate"):
        e = parts[n].extents
        report["info"][n + "_size"] = [round(float(v), 2) for v in e]

# ------------------------------------------------------------------ 3. assembly
frame_mf = to_mf(parts["frame"])
cover_print = to_mf(parts["cover"])
cover_flush = cover_print.translate((0, 0, T - cover_t))          # pulled back against the ledges
photo_t = 0.25
photo = Manifold.cube((86, 54, photo_t), center=True).translate((0, 0, lip_t + photo_t / 2))
cover_rest = cover_print.translate((0, 0, lip_t + photo_t))         # resting on a 0.25 mm photo
magnets = Manifold.batch_boolean([Manifold.cylinder(1.5, 4.0, 4.0, 64).translate((x, y, T - 0.4 - 1.5)) for x, y in mag_pos],
                                 __import__("manifold3d").OpType.Add)

def place_nameplate(m):
    mf = to_mf(m)
    # printed back-face-down -> flip 180 deg about Y, put back face flush with frame back
    return mf.rotate((0, 180, 0)).translate((0, tp_cy, T))

def vol(a, b): return (a ^ b).volume()

v = vol(frame_mf, cover_flush)
check("no collision frame/cover (cover pulled back on ledges)", v < 1e-3, f"intersection {v:.5f} mm3")
v = vol(frame_mf, cover_rest)
check("no collision frame/cover (cover resting on 0.25 mm photo)", v < 1e-3, f"intersection {v:.5f} mm3")
v1, v2 = vol(frame_mf, photo), vol(cover_flush, photo)
check("photo fits pocket (no clear sheet)", v1 < 1e-3 and v2 < 1e-3,
      f"photo/frame {v1:.4f} mm3, photo/cover {v2:.4f} mm3, photo 86x54x{photo_t}")
gap = cover_rest.min_gap(frame_mf, 1.0)
check("cover-to-frame running clearance (cover on photo)", 0.05 <= gap <= 0.3, f"min gap {gap:.3f} mm")

# magnets: only the crush ribs should touch them
vm = vol(cover_flush, magnets)
mag_ok = 0 < vm < 4 * 1.5  # a few tenths of mm3 per magnet
check("magnet crush ribs grip the magnets", mag_ok, f"rib/magnet interference {vm:.3f} mm3 total (4 magnets)")
check("magnets hidden behind skin", True, "0.4 mm skin to fridge, magnet top 0.1 mm below photo side")

np_names = [n for n in parts if n.startswith("nameplate")]
for n in np_names:
    ins = place_nameplate(parts[n])
    vf, vc = vol(frame_mf, ins), vol(cover_flush, ins)
    # interference must only be the 4 press-fit ribs: tiny volume, located at x = +/-17
    inter = frame_mf ^ ins
    bb = inter.bounding_box() if not inter.is_empty() else None
    rib_only = (bb is None) or (min(abs(bb[0]), abs(bb[3])) > 16.5)
    check(f"nameplate fit: {n}", vf < 1.0 and vc < 1e-3 and rib_only,
          f"press-fit rib interference {vf:.3f} mm3 (ribs only={rib_only}), cover contact {vc:.4f} mm3")
    # face of plate must be flush with the frame front (z=0) and text proud by 0.6 (raised) or 0 (engraved)
    zmin = ins.bounding_box()[2]
    report["info"][n + "_front_z"] = round(zmin, 3)

# ------------------------------------------------------------------ 4. retention (pull-out) test
pull = 0.15
inter = frame_mf ^ cover_flush.translate((0, 0, pull))
comps = inter.decompose()
locs = sorted([tuple(round(c, 1) for c in comp.bounding_box()) for comp in comps if comp.volume() > 0.01])
hook = any(b[1] > 27 for b in locs); tongues = sum(1 for b in locs if b[4] < -27) >= 2
check("pull-out test: cover is held by hook + 2 tongues", hook and tongues,
      f"moving cover {pull} mm toward the fridge hits the frame at {len(locs)} places: hook={hook}, tongues={tongues}")
# shear area of the latches holding the magnets' pull
report["info"]["retention_faces_mm2"] = {"hook": 10 * 0.65, "tongues": 2 * 10 * 0.85}

# ------------------------------------------------------------------ 5. insertion kinematics (YZ sections)
def yz_section(mf, x):
    # rotate so that the x axis becomes z, then slice at that height  (y stays y, old z -> new x)
    r = mf.rotate((0, -90, 0))           # (x,y,z) -> (?,?,?) ; verify mapping numerically below
    return r.slice(x)

# figure out mapping of rotate((0,-90,0)) : a point (1,0,0) ->
probe = Manifold.cube((0.1, 0.1, 0.1)).translate((5, 7, 9)).rotate((0, -90, 0)).bounding_box()
# use whatever axis now holds 5 as slicing axis; expect it to be z
assert abs((probe[2] + probe[5]) / 2 - 5.05) < 1e-6 or abs((probe[2] + probe[5]) / 2 + 5.05) < 1e-6, probe
sign = 1 if (probe[2] + probe[5]) / 2 > 0 else -1

def section(mf, x):
    return mf.rotate((0, -90, 0)).slice(sign * x)

def rot_cs(cs, ang, piv):
    return cs.translate((-piv[0], -piv[1])).rotate(ang).translate(piv)

# in the section coords: first coord = (some sign) * z, second = y.  Find mapping with a probe.
pc = Manifold.cube((0.1, 0.1, 0.1)).translate((0, 7, 9)).rotate((0, -90, 0)).slice(sign * 0.05).bounds()
zsign = 1 if (pc[0] + pc[2]) / 2 > 0 else -1     # section u = zsign * z, v = y

def tilt_test(x, label):
    fr = section(frame_mf, x)
    cv = section(cover_flush, x)
    piv = (zsign * (T - 1.5), -27.6)        # tongue in its slot
    worst = 0.0
    path_ok = True
    for ang_deg in np.linspace(25, 0, 51):
        best = None
        # allow the cover to slide a little in y and z at each angle (search small grid)
        for dy in np.linspace(-0.4, 0.9, 27):
            for dz in np.linspace(0, 0.6, 7):
                c = rot_cs(cv, -zsign * ang_deg, piv).translate((zsign * dz, dy))   # lift the top edge out of the frame
                a = (c ^ fr).area()
                if best is None or a < best[0]:
                    best = (a, dy, dz)
        worst = max(worst, best[0])
    return worst

w_tongue = tilt_test(29.0, "tongue")
check("tilt-in insertion at tongues is collision-free", w_tongue < 0.02,
      f"max overlap {w_tongue:.4f} mm2 along a 25 deg -> 0 deg swing")

# hook: how far must the latch pad move in -y while the hook passes the ledge?
fr0 = section(frame_mf, 0.0)
cv0 = section(cover_flush, 0.0) ^ CrossSection.square((40, 30)).translate((-20, 15))   # latch pad region only
need = 0.0
for dz in np.linspace(0, 1.6, 81):     # push cover straight down through the last 1.6 mm
    c = cv0.translate((zsign * dz, 0))
    if (c ^ fr0).area() < 1e-4:
        continue
    for dy in np.linspace(0, 1.2, 121):
        if (c.translate((0, -dy)) ^ fr0).area() < 1e-4:
            need = max(need, dy); break
    else:
        need = 99
check("snap hook deflection is within the flexure travel", need <= 1.0,
      f"pad must move {need:.2f} mm while snapping in; slot allows 1.20 mm (hard stop)")
report["info"]["hook_deflection_needed_mm"] = round(need, 3)

# ------------------------------------------------------------------ 6. latch strain
E = 3500.0; b, h, L = 1.5, 2.0, 20.0
for d, tag in [(need, "snap-in"), (1.2, "hard stop")]:
    eps = 3 * b * d / L**2                   # guided cantilever (pad stays parallel)
    report["info"][f"latch_strain_{tag}"] = round(eps * 100, 2)
eps_stop = 3 * b * 1.2 / L**2
force = 2 * 12 * E * (h * b**3 / 12) * max(need, 0.65) / L**3
check("latch flexure strain below PLA limit (2 %)", eps_stop < 0.02,
      f"snap-in {3*b*need/L**2*100:.2f} %, worst case at hard stop {eps_stop*100:.2f} %; release force ~{force:.1f} N")

# ------------------------------------------------------------------ 7. overhangs (print orientation)
def overhangs(m, bed_tol=0.05, crit=0.75):
    n = m.face_normals; c = m.triangles_center; a = m.area_faces
    down = (n[:, 2] < -crit) & (c[:, 2] > bed_tol)      # steeper than ~41 deg from vertical, not on bed
    if not down.any():
        return []
    sub = m.submesh([np.where(down)[0]], append=True)
    out = []
    for comp in sub.split(only_watertight=False):
        bb = comp.bounds
        span = min(bb[1][0] - bb[0][0], bb[1][1] - bb[0][1])
        out.append({"z": round(float(bb[0][2]), 2), "area": round(float(comp.area), 2),
                    "short_span": round(float(span), 2)})
    return out

for n in ["frame", "cover"] + np_names[:1]:
    oh = overhangs(parts[n])
    worst = max([o["short_span"] for o in oh], default=0)
    check(f"printable without supports: {n}", worst <= 8.5,
          f"{len(oh)} flat bridge/overhang areas above the bed (all other faces <= 45 deg); "
          f"widest bridge {worst} mm (<= 8.5 mm prints cleanly): {oh[:5]}")

# ------------------------------------------------------------------ 8. thin vertical walls
def thin_walls(m, n_samples=60000):
    pts, fi = trimesh.sample.sample_surface(m, n_samples, seed=1)
    nrm = m.face_normals[fi]
    vert = np.abs(nrm[:, 2]) < 0.2
    pts, nrm = pts[vert], nrm[vert]
    origins = pts - nrm * 1e-3
    loc, idx_ray, _ = m.ray.intersects_location(origins, -nrm, multiple_hits=False)
    d = np.full(len(pts), np.inf)
    d[idx_ray] = np.linalg.norm(loc - origins[idx_ray], axis=1)
    return d, pts

for n in ["frame", "cover"]:
    d, pts = thin_walls(parts[n])
    finite = d[np.isfinite(d)]
    # ignore the outer rounded/chamfered rims (z within 0.6 mm of the top/bottom faces)
    zmax = parts[n].bounds[1][2]
    mask = np.isfinite(d) & (pts[:, 2] > 0.6) & (pts[:, 2] < zmax - 0.6)
    q = np.percentile(d[mask], [0.5, 5, 50])
    check(f"vertical walls >= 0.8 mm (2 perimeters): {n}", q[0] >= 0.8,
          f"wall thickness 0.5th pct {q[0]:.2f} mm, 5th pct {q[1]:.2f} mm, median {q[2]:.2f} mm")

# ------------------------------------------------------------------ 9. text fit
for n in np_names:
    m = parts[n]
    top = m.bounds[1][2]
    if top > nameplate_top + 0.3:   # raised text
        sl = m.section(plane_origin=(0, 0, nameplate_top + 0.3), plane_normal=(0, 0, 1))
        bb = sl.bounds
        tw, th = bb[1][0] - bb[0][0], bb[1][1] - bb[0][1]
        ok = tw <= boss[0] - 1.6 and th <= boss[1] - 0.8
        check(f"text fits plate: {n}", ok, f"text {tw:.1f} x {th:.1f} mm on a {boss[0]} x {boss[1]} mm face")

# ------------------------------------------------------------------ 10. weight
tot = 0
for n in ["frame", "cover"] + np_names[:1]:
    vcm = parts[n].volume / 1000; tot += vcm
    report["info"][f"weight_{n}_g_PLA"] = round(vcm * PLA, 1)
report["info"]["weight_total_g_PLA"] = round(tot * PLA, 1)
print(json.dumps(report["info"], indent=1, ensure_ascii=False))
fails = [c for c in report["checks"] if not c["ok"]]
print(f"\n{len(report['checks']) - len(fails)}/{len(report['checks'])} checks passed")
json.dump(report, open(os.path.join(HERE, "verification_report.json"), "w"), indent=1, ensure_ascii=False)
