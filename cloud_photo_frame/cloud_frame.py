#!/usr/bin/env python3
"""
Cloud / bubble photo frame - parametric generator
=================================================

Target printer : Bambu Lab A2L (build volume 330 x 320 x 325 mm)
Photo          : 290 x 200 mm paper photo, no glass / acrylic

Coordinate system (mm):
    X = frame width, Y = frame height, Z = depth.
    Z = 0 is the flat BACK face (this face goes on the print bed),
    +Z points to the viewer (front, bubbles).

Parts
-----
  * front frame  - ring of spheres ("bubbles") on a flat inner rim, photo window,
                   rabbet/recess for photo + back panel, snap grooves, stand slot,
                   key-hole wall hangers, finger notches.
                   Variant A is printed in two halves (joined with blind dovetails),
                   variant B is printed in one piece (smaller "pearl" bubbles).
  * back panel   - sits flush inside the frame (one-piece look from the back),
                   six flexible snap latches, PRINT-IN-PLACE fold-out stand leg
                   (cone hinge + hard stop -> frame leans back 18 deg = 72 deg stand angle).

Run:  python3 cloud_frame.py [A|B|all]
"""
import json
import math
import os
import sys
from dataclasses import dataclass, asdict, field

import numpy as np
import manifold3d as m3
import trimesh

M = m3.Manifold
CS = m3.CrossSection
ADD = m3.OpType.Add

HERE = os.path.dirname(os.path.abspath(__file__))


# --------------------------------------------------------------------------- helpers
def box(x0, x1, y0, y1, z0, z1):
    return M.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def rect_cs(x0, x1, y0, y1):
    return CS.square((x1 - x0, y1 - y0)).translate((x0, y0))


def prism(cs, z0, z1):
    return cs.extrude(z1 - z0).translate((0, 0, z0))


def cyl_x(x0, x1, y, z, r0, r1=None, seg=64):
    """Cylinder / cone along +X from x0 (radius r0) to x1 (radius r1)."""
    if r1 is None:
        r1 = r0
    c = M.cylinder(x1 - x0, r0, r1, seg)  # along +Z
    return c.rotate((0, 90, 0)).translate((x0, y, z))  # +Z -> +X


def union(parts):
    parts = [p for p in parts if p is not None and not p.is_empty()]
    if not parts:
        return M()
    return M.batch_boolean(parts, ADD)


def hull(points):
    return M.hull_points(np.asarray(points, dtype=float))


def rot_yz(y, z, phi_deg, yc, zc):
    """Rotate point (y,z) about axis (yc,zc) by phi (deg). Positive phi swings a
    downward-pointing leg towards -Z (backwards)."""
    p = math.radians(phi_deg)
    dy, dz = y - yc, z - zc
    return yc + dy * math.cos(p) - dz * math.sin(p), zc + dy * math.sin(p) + dz * math.cos(p)


# --------------------------------------------------------------------------- config
@dataclass
class Cfg:
    name: str = "A"
    title: str = ""
    # photo / window
    photo_w: float = 290.0
    photo_h: float = 200.0
    overlap: float = 3.0          # photo edge hidden behind the lip (per side)
    photo_clear: float = 0.5      # photo -> recess wall clearance (per side)
    panel_clear: float = 0.3      # back panel -> recess wall clearance (per side)
    T: float = 8.0                # back panel thickness
    photo_gap: float = 0.6        # space for the photo paper
    lip: float = 2.4              # lip thickness in front of the photo
    win_chamfer: float = 1.2      # 45deg bevel on the window edge (front)
    # bubbles
    R: float = 18.0
    zc: float = 5.2
    rim: float = 4.0              # flat rim between window and bubbles
    nx: int = 10                  # bubble intervals along width
    ny: int = 7                   # bubble intervals along height
    seg: int = 160                # sphere tessellation
    # split (variant A)
    split: bool = True
    dovetail_y: float = 110.0
    # stand leg (print-in-place)
    leg_w: float = 29.0
    leg_t: float = 4.5
    leg_rect_bottom: float = None  # y where the straight part ends (None -> -B)
    foot_wall: float = 2.5
    tail_w: float = 17.0
    tail_t: float = 3.25
    y_h: float = 80.0             # hinge axis height
    floor_z: float = 5.7          # underside of the panel floor above the leg
    cone_r: float = 1.9
    leg_gap: float = 0.4          # print-in-place clearance
    slot_clear: float = 0.3       # leg -> frame slot clearance
    slot_depth: float = 4.9
    target_tilt: float = 18.0     # deg from vertical (72 deg stand angle)
    # snaps
    latch_len: float = 24.0
    latch_w: float = 2.4
    latch_slot: float = 1.0
    bump: float = 0.8
    bump_z: float = 4.0
    groove_depth: float = 0.9
    latch_bump_x: float = 98.4    # top/bottom latch bumps at +-x (aligned with a bubble)
    latch_side_y: tuple = (0.0,)
    # misc features
    keyhole_x: float = 125.0
    keyhole_y: float = 107.5
    keyhole_travel: float = 8.5
    keyhole_head_r: float = 4.5
    notch_x: float = 135.0
    lip_support: bool = True      # break-away ring under the photo lip (print aid)
    # derived (filled in by derive())
    d: dict = field(default_factory=dict)

    def derive(self):
        d = {}
        d["win_w"] = self.photo_w - 2 * self.overlap
        d["win_h"] = self.photo_h - 2 * self.overlap
        d["pocket_w"] = self.photo_w + 2 * self.photo_clear
        d["pocket_h"] = self.photo_h + 2 * self.photo_clear
        d["panel_w"] = d["pocket_w"] - 2 * self.panel_clear
        d["panel_h"] = d["pocket_h"] - 2 * self.panel_clear
        d["z_lip0"] = self.T + self.photo_gap
        d["z_rim"] = d["z_lip0"] + self.lip
        d["A"] = d["win_w"] / 2 + self.rim + self.R
        d["B"] = d["win_h"] / 2 + self.rim + self.R
        d["r0"] = math.sqrt(self.R ** 2 - self.zc ** 2)  # bubble radius at back face
        d["px"] = 2 * d["A"] / self.nx
        d["py"] = 2 * d["B"] / self.ny
        d["outer_w"] = 2 * (d["A"] + self.R)
        d["outer_h"] = 2 * (d["B"] + self.R)
        d["depth"] = self.zc + self.R
        d["z_a"] = self.leg_t / 2  # hinge axis depth
        d["foot_r"] = d["r0"] - self.foot_wall
        d["rect_bot"] = self.leg_rect_bottom if self.leg_rect_bottom is not None else -d["B"]
        d["y_tip"] = -d["B"] - d["foot_r"]
        # valleys for the seams (variant A)
        d["seam_top_x"] = -d["A"] + 3.5 * d["px"]
        d["seam_bot_x"] = -d["seam_top_x"]
        self.d = d
        return d


def variant_A():
    c = Cfg(name="A", title="Chunky cloud (2-piece front, glued)")
    c.derive()
    return c


def variant_B():
    c = Cfg(
        name="B", title="Pearl cloud (1-piece front)",
        R=9.5, zc=5.4, rim=1.0, nx=20, ny=14, split=False,
        leg_w=30.0, leg_rect_bottom=-106.5, foot_wall=2.2,
        keyhole_y=106.5, keyhole_travel=3.5, keyhole_head_r=4.0, keyhole_x=122.0,
        latch_bump_x=91.5,
    )
    c.derive()
    return c


# --------------------------------------------------------------------------- stand maths
def leg_end_corners(c, phi):
    d = c.d
    pts = []
    for z in (0.0, c.leg_t):
        pts.append(rot_yz(d["y_tip"], z, phi, c.y_h, d["z_a"]))
    return pts


def stand_pose(c, phi):
    """Return tilt alpha (deg from vertical) and base depth for a leg opening phi."""
    d = c.d
    yC, zC = -d["B"] - d["r0"], 0.0  # back-bottom edge of the bottom bubbles
    best = None
    for (yF, zF) in leg_end_corners(c, phi):
        a = math.degrees(math.atan2(yF - yC, zC - zF))
        # the lowest leg corner is the one giving the largest tilt
        if best is None or a > best[0]:
            best = (a, yF, zF)
    a, yF, zF = best
    ar = math.radians(a)
    hC = -yC * math.sin(ar) + zC * math.cos(ar)
    hF = -yF * math.sin(ar) + zF * math.cos(ar)
    return a, hC - hF, (yF, zF)


def solve_phi(c):
    lo, hi = 1.0, 80.0
    for _ in range(80):
        mid = (lo + hi) / 2
        a, _, _ = stand_pose(c, mid)
        if a < c.target_tilt:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def tail_length_for(c, phi):
    d = c.d
    h = c.tail_t - d["z_a"]
    lift = c.floor_z - d["z_a"]
    p = math.radians(phi)
    return (lift - h * math.cos(p)) / math.sin(p)


def stop_angle(c, e):
    d = c.d
    h = c.tail_t - d["z_a"]
    lift = c.floor_z - d["z_a"]
    lo, hi = 0.0, 89.0
    for _ in range(80):
        mid = (lo + hi) / 2
        p = math.radians(mid)
        if e * math.sin(p) + h * math.cos(p) < lift:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# --------------------------------------------------------------------------- geometry
def bubble_centers(c):
    d = c.d
    A, B = d["A"], d["B"]
    pts = []
    for i in range(c.nx + 1):
        x = -A + i * d["px"]
        pts += [(x, B), (x, -B)]
    for j in range(1, c.ny):
        y = -B + j * d["py"]
        pts += [(-A, y), (A, y)]
    return pts


def leg_outline(c, y_top):
    d = c.d
    w = c.leg_w / 2
    rect = rect_cs(-w, w, d["rect_bot"], y_top)
    foot = CS.circle(d["foot_r"], 96).translate((0, -d["B"]))
    return CS.batch_boolean([rect, foot], ADD)


def latch_local(c):
    """Latch cut + bump + frame groove in a local frame: panel edge on y=0
    (outward +y), strip along x in [-L/2, L/2] with the free end at +L/2."""
    L, w, s = c.latch_len, c.latch_w, c.latch_slot
    T = c.T
    cut = union([
        box(-L / 2, L / 2 + s, -w - s, -w, -1, T + 1),
        box(L / 2, L / 2 + s, -w - s, 1.0, -1, T + 1),
    ])
    zb = c.bump_z
    bl = 9.0
    x0 = L / 2 - 2.5 - bl
    x1 = L / 2 - 2.5
    b = c.bump
    bump = hull([
        (x0, -0.3, zb - 1.2), (x1, -0.3, zb - 1.2), (x0, -0.3, zb + 1.2), (x1, -0.3, zb + 1.2),
        (x0 + b, b, zb - 0.4), (x1 - b, b, zb - 0.4), (x0 + b, b, zb + 0.4), (x1 - b, b, zb + 0.4),
    ])
    wall = c.panel_clear
    gd = c.groove_depth
    g0, g1 = x0 - 2.5, x1 + 2.5
    groove = hull([
        (g0, wall - 0.2, zb - 1.6), (g1, wall - 0.2, zb - 1.6),
        (g0, wall - 0.2, zb + 1.6), (g1, wall - 0.2, zb + 1.6),
        (g0 + gd, wall + gd, zb - 0.5), (g1 - gd, wall + gd, zb - 0.5),
        (g0 + gd, wall + gd, zb + 0.5), (g1 - gd, wall + gd, zb + 0.5),
    ])
    return cut, bump, groove


def latch_placements(c):
    d = c.d
    hw, hh = d["panel_w"] / 2, d["panel_h"] / 2
    pl = []
    bc = c.latch_len / 2 - 2.5 - 4.5             # bump centre in latch-local x
    for bx in (-c.latch_bump_x, c.latch_bump_x):
        pl.append(((0, 0, 0), (bx - bc, hh)))     # top edge
        pl.append(((0, 0, 180), (bx + bc, -hh)))  # bottom edge
    for y in c.latch_side_y:
        pl.append(((0, 0, -90), (hw, y)))        # right edge
        pl.append(((0, 0, 90), (-hw, y)))        # left edge
    return pl


def place(m, rot, xy):
    return m.rotate(rot).translate((xy[0], xy[1], 0))


def build_frame(c):
    d = c.d
    A, B = d["A"], d["B"]
    zr = d["z_rim"]
    spheres = [M.sphere(c.R, c.seg).translate((x, y, c.zc)) for (x, y) in bubble_centers(c)]
    plate = box(-A, A, -B, B, 0, zr)
    body = union(spheres + [plate]).trim_by_plane((0, 0, 1), 0.0)

    cuts = []
    ww, wh = d["win_w"], d["win_h"]
    # photo window (through)
    cuts.append(box(-ww / 2, ww / 2, -wh / 2, wh / 2, -1, zr + 30))
    # 45 deg bevel on the window front edge
    ch = c.win_chamfer + 3.0
    bev = CS.square((ww, wh), True).extrude(
        ch, scale_top=((ww + 2 * ch) / ww, (wh + 2 * ch) / wh)).translate((0, 0, zr - c.win_chamfer))
    cuts.append(bev)
    # recess for photo + back panel (open to the back)
    pw, ph = d["pocket_w"], d["pocket_h"]
    cuts.append(box(-pw / 2, pw / 2, -ph / 2, ph / 2, -1, d["z_lip0"]))
    # small lead-in chamfer around the recess opening (also kills elephant foot)
    lead = 0.5
    cuts.append(CS.square((pw + 2 * lead + 2, ph + 2 * lead + 2), True).extrude(
        lead + 1, scale_top=((pw) / (pw + 2 * lead + 2), (ph) / (ph + 2 * lead + 2))).translate((0, 0, -1)))
    # snap grooves
    _, _, groove = latch_local(c)
    for rot, xy in latch_placements(c):
        cuts.append(place(groove, rot, xy))
    # stand slot in the bottom border (leg reaches the bottom bubble)
    slot = leg_outline(c, -d["panel_h"] / 2 + 2).offset(c.slot_clear, m3.JoinType.Round, 2.0, 64)
    cuts.append(prism(slot, -1, c.slot_depth))
    # finger scoop to lift the leg
    cuts.append(M.sphere(5.5, 48).translate((c.leg_w / 2 + 1.5, -d["panel_h"] / 2 - 6.0, -2.3)))
    # finger notches to pull the back panel out (bottom corners)
    for sx in (-1, 1):
        cuts.append(M.sphere(7.0, 48).translate((sx * c.notch_x, -ph / 2 - 2.6, -4.2)))
    # key-hole wall hangers
    for sx in (-1, 1):
        x = sx * c.keyhole_x
        y0, y1 = c.keyhole_y, c.keyhole_y + c.keyhole_travel
        hr = c.keyhole_head_r
        skin = 2.2
        head = CS.circle(hr, 48).translate((x, y0))
        slot2 = CS.hull(CS.batch_boolean([CS.circle(2.3, 32).translate((x, y0)),
                                          CS.circle(2.3, 32).translate((x, y1))], ADD))
        cuts.append(prism(CS.batch_boolean([head, slot2], ADD), -1, skin + 0.01))
        cav = CS.hull(CS.batch_boolean([CS.circle(hr + 0.1, 48).translate((x, y0)),
                                        CS.circle(hr + 0.1, 48).translate((x, y1))], ADD))
        cuts.append(prism(cav, skin, skin + 3.8))
    frame = body - union(cuts)
    return frame


def build_lip_support(c):
    """Break-away ring printed under the 3.5 mm photo lip (separate body, 0.2 mm
    air gap = one layer). Remove after printing."""
    d = c.d
    ww, wh = d["win_w"] / 2, d["win_h"] / 2
    t, o = 1.2, 0.25
    zt = d["z_lip0"] - 0.2
    outer = CS.square((2 * (ww + o + t), 2 * (wh + o + t)), True)
    inner = CS.square((2 * (ww + o), 2 * (wh + o)), True)
    return prism(outer - inner, 0, zt)


def dovetail_cs(c, x_s, yc, grow=0.0):
    """Trapezoid tenon: narrow at the seam (x_s), wide 6 mm into the -x side."""
    return CS([[(x_s + 0.01, yc - 3 - grow), (x_s + 0.01, yc + 3 + grow),
                (x_s - 6 - grow, yc + 5 + grow), (x_s - 6 - grow, yc - 5 - grow)]])


def split_frame(c, frame):
    d = c.d
    big = 400
    xt, xb = d["seam_top_x"], d["seam_bot_x"]
    left_region = union([box(-big, xt, 0, big, -big, big), box(-big, xb, -big, 0, -big, big)])
    left = frame ^ left_region
    right = frame - left_region
    tenons, sockets = [], []
    for xs, yc in ((xt, c.dovetail_y), (xb, -c.dovetail_y)):
        tenons.append(prism(dovetail_cs(c, xs, yc), 0, 7.0))
        sockets.append(prism(dovetail_cs(c, xs, yc, grow=0.15), -1, 7.3))
    right = union([right] + tenons)
    left = left - union(sockets)
    # make sure tenons are inside the original solid envelope
    return left, right


def build_leg(c, e):
    d = c.d
    w = c.leg_w / 2
    plate = prism(leg_outline(c, c.y_h), 0, c.leg_t)
    hinge = cyl_x(-w, w, c.y_h, d["z_a"], d["z_a"], seg=64)
    tail = box(-c.tail_w / 2, c.tail_w / 2, c.y_h, c.y_h + e, 0, c.tail_t)
    cones = [cyl_x(w - 0.01, w + c.cone_r, c.y_h, d["z_a"], c.cone_r, 0.0, 48),
             cyl_x(-w - c.cone_r, -w + 0.01, c.y_h, d["z_a"], 0.0, c.cone_r, 48)]
    leg = union([plate, hinge, tail] + cones)
    # small lead-in chamfer on the foot front edge (slides into the frame slot)
    return leg


def build_panel(c, e):
    d = c.d
    hw, hh, T = d["panel_w"] / 2, d["panel_h"] / 2, c.T
    panel = box(-hw, hw, -hh, hh, 0, T)
    # chamfers: back edge 0.4 (elephant foot), front edge 0.6 (lead-in)
    ch_b, ch_f = 0.4, 0.6
    W, H = 2 * hw, 2 * hh
    env = union([
        CS.square((W - 2 * ch_b, H - 2 * ch_b), True).extrude(
            ch_b, scale_top=(W / (W - 2 * ch_b), H / (H - 2 * ch_b))),
        box(-hw, hw, -hh, hh, ch_b, T - ch_f),
        CS.square((W, H), True).extrude(
            ch_f, scale_top=((W - 2 * ch_f) / W, (H - 2 * ch_f) / H)).translate((0, 0, T - ch_f)),
    ])
    panel = panel ^ env

    g = c.leg_gap
    w = c.leg_w / 2
    cuts = []
    # leg channel (open to the back, open at the bottom edge)
    chan = leg_outline(c, c.y_h + d["z_a"] + 0.6).offset(g, m3.JoinType.Miter, 2.0)
    cuts.append(prism(chan, -1, c.floor_z))
    # narrower tail channel (stop pocket)
    cuts.append(box(-c.tail_w / 2 - g, c.tail_w / 2 + g, c.y_h, c.y_h + e + 1.0, -1, c.floor_z))
    # cone sockets (0.35 mm normal clearance)
    off = 0.35 * math.sqrt(2)
    rs = c.cone_r + off
    cuts.append(cyl_x(w, w + rs, c.y_h, d["z_a"], rs, 0.0, 48))
    cuts.append(cyl_x(-w - rs, -w, c.y_h, d["z_a"], 0.0, rs, 48))
    # snap latch slots
    cut, bump, _ = latch_local(c)
    bumps = []
    for rot, xy in latch_placements(c):
        cuts.append(place(cut, rot, xy))
        bumps.append(place(bump, rot, xy))
    # fingernail ledges on the bottom edge (match the frame notches)
    for sx in (-1, 1):
        cuts.append(box(sx * c.notch_x - 4.5, sx * c.notch_x + 4.5, -hh - 1, -hh + 1.2, 1.4, 3.6))
    panel = panel - union(cuts)
    panel = union([panel] + bumps)
    return panel


def build_photo(c):
    d = c.d
    return box(-c.photo_w / 2, c.photo_w / 2, -c.photo_h / 2, c.photo_h / 2, c.T + 0.02, c.T + 0.3)


# --------------------------------------------------------------------------- export
def to_trimesh(m):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3]
    f = np.asarray(mesh.tri_verts)
    return trimesh.Trimesh(vertices=v, faces=f, process=False)


def save_stl(m, path):
    tm = to_trimesh(m)
    tm.export(path)
    return tm


def leg_transform(c, phi):
    """4x4 matrix rotating the leg about the hinge axis by phi (deg)."""
    d = c.d
    p = math.radians(phi)
    yc, zc = c.y_h, d["z_a"]
    Rm = np.eye(4)
    Rm[1, 1], Rm[1, 2] = math.cos(p), -math.sin(p)
    Rm[2, 1], Rm[2, 2] = math.sin(p), math.cos(p)
    T1 = np.eye(4); T1[1, 3], T1[2, 3] = -yc, -zc
    T2 = np.eye(4); T2[1, 3], T2[2, 3] = yc, zc
    return T2 @ Rm @ T1


def rotate_leg(c, leg, phi):
    Mx = leg_transform(c, phi)
    return leg.transform(Mx[:3, :])


def filament_estimate(m, infill=0.12, shell=0.85):
    """Rough slicer-like estimate: shell (walls/top/bottom) + sparse infill, PLA."""
    V = m.volume()
    S = m.surface_area()
    sh = min(V, S * shell)
    return 1.24e-3 * (sh + infill * (V - sh))


def overhang_report(m, limit_deg=50.0):
    """Area of down-facing surfaces steeper than limit (from vertical), excluding the bed."""
    tm = to_trimesh(m)
    n = tm.face_normals
    a = tm.area_faces
    zc = tm.triangles_center[:, 2]
    th = math.sin(math.radians(limit_deg))
    mask = (n[:, 2] < -th) & (zc > 0.05)
    return float(a[mask].sum())


def build(c, outdir):
    os.makedirs(outdir, exist_ok=True)
    vdir = os.path.join(outdir, "render")
    os.makedirs(vdir, exist_ok=True)
    d = c.d
    phi = solve_phi(c)
    e = tail_length_for(c, phi)
    phi_stop = stop_angle(c, e)
    tilt, base, foot = stand_pose(c, phi_stop)

    frame = build_frame(c)
    ring = build_lip_support(c) if c.lip_support else M()
    leg = build_leg(c, e)
    panel = build_panel(c, e)
    photo = build_photo(c)

    rep = {"variant": c.name, "title": c.title, "cfg": {k: v for k, v in asdict(c).items() if k != "d"},
           "derived": d}
    rep["stand"] = {"phi_stop_deg": phi_stop, "tilt_from_vertical_deg": tilt,
                    "stand_angle_deg": 90 - tilt, "base_depth_mm": base, "tail_len_mm": e}

    # render-only parts (no print aids)
    rparts = {}
    pparts = {}
    if c.split:
        left, right = split_frame(c, frame)
        rparts["frame_left"], rparts["frame_right"] = left, right
        big = 400
        lr = union([box(-big, d["seam_top_x"], 0, big, -big, big), box(-big, d["seam_bot_x"], -big, 0, -big, big)])
        pparts["front_frame_left"] = union([left, ring ^ lr])
        pparts["front_frame_right"] = union([right, ring - lr])
    else:
        rparts["frame"] = frame
        pparts["front_frame"] = union([frame, ring])
    rparts["panel"], rparts["leg"], rparts["photo"] = panel, leg, photo
    pparts["back_panel_with_stand"] = union([panel, leg])

    for k, m in rparts.items():
        save_stl(m, os.path.join(vdir, f"{k}.stl"))
    info = {}
    for k, m in pparts.items():
        bb = m.bounding_box()
        info[k] = {"volume_cm3": m.volume() / 1000, "bbox": bb,
                   "size": (bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2]),
                   "bodies": len(m.decompose()), "status": str(m.status()),
                   "filament_g": filament_estimate(m), "overhang_mm2_gt50deg": overhang_report(m),
                   "fits_A2L": (bb[3] - bb[0]) <= 330 and (bb[4] - bb[1]) <= 320 and (bb[5] - bb[2]) <= 325}
        save_stl(m, os.path.join(outdir, f"{k}.stl"))
    rep["print_parts"] = info
    rep["filament_total_g"] = sum(v["filament_g"] for v in info.values())

    # centre of mass of the standing assembly (uniform density approximation of the print)
    def com(m):
        tm = to_trimesh(m)
        return tm.center_mass, tm.volume
    S_parts = [frame, panel]
    cs, vs = zip(*[com(m) for m in S_parts])
    legd = rotate_leg(c, leg, phi_stop)
    cl, vl = com(legd)
    cm = (np.sum([ci * vi for ci, vi in zip(cs, vs)], axis=0) + cl * vl) / (sum(vs) + vl)
    ar = math.radians(tilt)
    hG = -cm[1] * math.sin(ar) + cm[2] * math.cos(ar)
    yC = -d["B"] - d["r0"]
    hC = -yC * math.sin(ar)
    hF = -foot[0] * math.sin(ar) + foot[1] * math.cos(ar)
    rep["stand"]["com_behind_front_contact_mm"] = hC - hG
    rep["stand"]["foot_behind_front_contact_mm"] = hC - hF

    # ---- kinematic checks: leg must swing freely up to the stop, then collide
    sweep = []
    for a in [0, 5, 10, 15, 20, 25, phi_stop - 2, phi_stop - 0.5, phi_stop + 1.5, phi_stop + 4]:
        legr = rotate_leg(c, leg, a)
        sweep.append((round(a, 2), round((legr ^ panel).volume(), 3)))
    rep["leg_sweep_overlap_mm3"] = sweep
    rep["leg_frame_overlap_mm3"] = (leg ^ frame).volume()
    rep["panel_frame_overlap_mm3"] = (panel ^ frame).volume()
    rep["ring_frame_overlap_mm3"] = (ring ^ frame).volume() if c.lip_support else 0.0
    rep["min_gap_panel_leg_mm"] = panel.min_gap(leg, 2.0)
    rep["min_gap_ring_frame_mm"] = ring.min_gap(frame, 2.0) if c.lip_support else None

    with open(os.path.join(outdir, "report.json"), "w") as fh:
        json.dump(rep, fh, indent=1, default=str)
    return rep


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    cfgs = {"A": variant_A, "B": variant_B}
    for k in (cfgs if which == "all" else [which]):
        c = cfgs[k]()
        out = os.path.join(HERE, "build", k)
        r = build(c, out)
        keys = ("variant", "stand", "leg_sweep_overlap_mm3", "leg_frame_overlap_mm3", "panel_frame_overlap_mm3",
                "ring_frame_overlap_mm3", "min_gap_panel_leg_mm", "min_gap_ring_frame_mm", "filament_total_g")
        print(json.dumps({kk: r[kk] for kk in keys}, indent=1, default=str))
        for p, inf in r["print_parts"].items():
            print(f"  {p:24s} size={tuple(round(s,1) for s in inf['size'])} bodies={inf['bodies']} "
                  f"fil={inf['filament_g']:.0f}g overhang>50={inf['overhang_mm2_gt50deg']:.0f}mm2 fits={inf['fits_A2L']}")
        print("  derived:", {k2: round(v, 2) for k2, v in r["derived"].items()})
