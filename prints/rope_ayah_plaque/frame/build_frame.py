"""Classic snap frame with wood-grain face for the 180 x 240 x 2 mm rope plaque.

Frame coordinates: x across (0..OW), y up (0..OH), z = 0 at the back, +z toward the front.
"""
import sys, os, json
import numpy as np, trimesh, manifold3d as m3d
from scipy.ndimage import gaussian_filter
import fast_simplification as fs

OUT = sys.argv[1]
P = dict(
    PW=180.0, PH=240.0, PT=2.0,          # printed plaque
    CL=0.3,                              # plaque clearance per side
    BORDER=11.0,                         # visible face width
    OVER=4.3,                            # lip overlap over plaque edge
    BACK_T=2.0,                          # back board thickness
    BACK_CL=0.2,                         # back board clearance per side
    WALL=4.7,                            # rear wall thickness
    RES=0.2,
)
if len(sys.argv) > 2: P.update(json.loads(sys.argv[2]))
R = P['RES']
pocket_w, pocket_h = P['PW'] + 2 * P['CL'], P['PH'] + 2 * P['CL']
win_w, win_h = pocket_w - 2 * P['OVER'], pocket_h - 2 * P['OVER']
OW, OH = win_w + 2 * P['BORDER'], win_h + 2 * P['BORDER']
rec_w, rec_h = pocket_w + 4.0, pocket_h + 4.0          # back-board recess
assert abs((OW - rec_w) / 2 - P['WALL']) < 0.5, (OW, rec_w)
Z_REC = P['BACK_T']                    # back board: z 0..2.0
Z_PKT = Z_REC + P['PT'] + 0.2          # plaque pocket: z 2.0..4.2
Z_CHAMF = Z_PKT + P['OVER']            # 45 deg lip chamfer up to here
Z_NOTCH = Z_PKT + 4.7 + 0.6            # clearance over rope relief at the edges (rope is 4.7 mm tall there)
print('outer', OW, OH, 'window', win_w, win_h, 'pocket', pocket_w, pocket_h)

def M(t):
    return m3d.Manifold(m3d.Mesh(np.asarray(t.vertices, np.float32), np.asarray(t.faces, np.uint32)))
def T(m):
    mm = m.to_mesh(); return trimesh.Trimesh(mm.vert_properties[:, :3], mm.tri_verts, process=False)
def box(x0, x1, y0, y1, z0, z1):
    return m3d.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])

# ---------------- face profile (v = distance from outer edge, mm) ----------------
def profile(v):
    B = P['BORDER']
    s = v / B * 11.0                      # designed for an 11 mm face
    h = np.full_like(s, 12.6)
    # outer round-over + bead
    h = np.where(s < 2.0, 13.0 + 2.0 * np.sqrt(np.clip(1 - ((s - 2.0) / 2.0) ** 2, 0, 1)), h)
    h = np.where(s < 0.0, 13.0, h)
    # bead to cove
    a = (s >= 2.0) & (s < 3.2); h = np.where(a, 15.0 - 0.6 * ((s - 2.0) / 1.2) ** 2, h)
    # cove (concave)
    a = (s >= 3.2) & (s < 7.4); c = (s - 3.2) / 4.2
    h = np.where(a, 14.4 - 1.2 * np.sin(np.pi * c) - 0.3 * c, h)
    # inner bead
    a = (s >= 7.4) & (s < 9.6); c = (s - 8.5) / 1.1
    h = np.where(a, 13.4 + 0.75 * np.sqrt(np.clip(1 - c ** 2, 0, 1)), h)
    # inner bevel down to the window
    a = s >= 9.6; c = (s - 9.6) / 1.4
    h = np.where(a, 13.4 - 0.8 * c, h)
    return h - P.get('DROP', 1.5)

# ---------------- wood grain ----------------
rng = np.random.default_rng(7)
def smooth_noise(n, sigma, seed):
    r = np.random.default_rng(seed).standard_normal(n)
    r = gaussian_filter(r, sigma, mode='wrap'); return r / (r.std() + 1e-9)
def grain(u, v, side):
    """u along the member, v across it (mm). Returns a height offset (mm)."""
    L = 400
    k = np.clip((u / 0.25).astype(int), 0, int(L / 0.25) - 1)
    w1 = smooth_noise(int(L / 0.25), 60, 10 + side)[k] * 1.6     # long waves
    w2 = smooth_noise(int(L / 0.25), 14, 20 + side)[k] * 0.35    # short wiggles
    ph = (v + w1 + w2 * (1 + 0.3 * np.sin(v))) / 1.15 + side * 0.37
    g = np.cos(2 * np.pi * ph)
    rings = np.clip(g, 0, 1) ** 3                                # narrow late-wood grooves
    # varying ring strength along the member
    amp = 0.55 + 0.45 * smooth_noise(int(L / 0.25), 40, 30 + side)[k].clip(-1, 1)
    pores = gaussian_filter(rng.standard_normal(u.shape), 0.6) * 0.02
    return -0.38 * rings * amp + pores

# ---------------- heightfield solid for the frame face ----------------
nx, ny = int(round(OW / R)), int(round(OH / R))
xs = np.linspace(0, OW, nx + 1); ys = np.linspace(0, OH, ny + 1)
X, Y = np.meshgrid(xs, ys)
d = np.stack([X, OW - X, Y, OH - Y])            # left, right, bottom, top
side = d.argmin(0); v = d.min(0)
u = np.where(side < 2, Y, X)                    # grain runs along each member
Z = profile(v)
for sd_ in range(4):
    msk = side == sd_
    Z[msk] += grain(u[msk], v[msk], sd_)
# mitre line: fine V-groove where two members meet
mit = np.abs(np.sort(d, 0)[1] - v)
Z -= 0.3 * np.exp(-(mit / 0.18) ** 2) * (v < P['BORDER'] - 0.2)

cx0, cy0 = int(round(P['BORDER'] / R)), int(round(P['BORDER'] / R))
cell = np.ones((ny, nx), bool)
cell[cy0:ny - cy0, cx0:nx - cx0] = False         # window

def heightfield_solid(Z, cell, xs, ys):
    ny, nx = cell.shape
    nv = (ny + 1) * (nx + 1)
    idx = lambda iy, ix: iy * (nx + 1) + ix
    iy, ix = np.nonzero(cell)
    a, b, c, dd = idx(iy, ix), idx(iy, ix + 1), idx(iy + 1, ix + 1), idx(iy + 1, ix)
    top = np.r_[np.c_[a, b, c], np.c_[a, c, dd]]
    bot = np.r_[np.c_[a, c, b], np.c_[a, dd, c]] + nv
    walls = []
    pad = np.pad(cell, 1)
    # vertical edges (between ix-1 and ix): x = xs[ix]
    left = pad[1:-1, 1:] & ~pad[1:-1, :-1]       # cell at ix filled, ix-1 empty  -> wall facing -x
    jy, jx = np.nonzero(left[:, :nx + 1])
    p0, p1 = idx(jy, jx), idx(jy + 1, jx)
    walls.append(np.r_[np.c_[p0, p1, p1 + nv], np.c_[p0, p1 + nv, p0 + nv]])
    right = ~pad[1:-1, 1:] & pad[1:-1, :-1]
    jy, jx = np.nonzero(right[:, :nx + 1])
    p0, p1 = idx(jy, jx), idx(jy + 1, jx)
    walls.append(np.r_[np.c_[p0, p1 + nv, p1], np.c_[p0, p0 + nv, p1 + nv]])
    bottom = pad[1:, 1:-1] & ~pad[:-1, 1:-1]     # cell at iy filled, iy-1 empty -> wall facing -y
    jy, jx = np.nonzero(bottom[:ny + 1, :])
    p0, p1 = idx(jy, jx), idx(jy, jx + 1)
    walls.append(np.r_[np.c_[p0, p1 + nv, p1], np.c_[p0, p0 + nv, p1 + nv]])
    topw = ~pad[1:, 1:-1] & pad[:-1, 1:-1]
    jy, jx = np.nonzero(topw[:ny + 1, :])
    p0, p1 = idx(jy, jx), idx(jy, jx + 1)
    walls.append(np.r_[np.c_[p0, p1, p1 + nv], np.c_[p0, p1 + nv, p0 + nv]])
    XX, YY = np.meshgrid(xs, ys)
    V = np.r_[np.c_[XX.ravel(), YY.ravel(), Z.ravel()], np.c_[XX.ravel(), YY.ravel(), np.zeros(nv)]]
    F = np.r_[top, bot, *walls]
    m = trimesh.Trimesh(V, F, process=False); m.remove_unreferenced_vertices()
    return m

face = heightfield_solid(Z, cell, xs, ys)
print('face tris', len(face.faces), 'watertight', face.is_watertight)
fr = M(face)

# ---------------- rear cut-outs ----------------
ox_r, oy_r = (OW - rec_w) / 2, (OH - rec_h) / 2
ox_p, oy_p = (OW - pocket_w) / 2, (OH - pocket_h) / 2
ox_w, oy_w = (OW - win_w) / 2, (OH - win_h) / 2
cut = box(ox_r, OW - ox_r, oy_r, OH - oy_r, -1, Z_REC)                         # back-board recess
cut += box(ox_p, OW - ox_p, oy_p, OH - oy_p, Z_REC - 0.01, Z_PKT)              # plaque pocket
cut += m3d.Manifold.batch_hull([box(ox_p, OW - ox_p, oy_p, OH - oy_p, Z_PKT - 0.01, Z_PKT),
                                box(ox_w, OW - ox_w, oy_w, OH - oy_w, Z_CHAMF, Z_CHAMF + 0.01)])  # 45deg lip
cut += box(ox_w, OW - ox_w, oy_w, OH - oy_w, Z_CHAMF, 30)                      # window
# snap groove around the recess wall (back board bumps click in here)
G0, G1, GD = 0.5, 1.5, 0.8
cut += box(ox_r - GD, OW - ox_r + GD, oy_r - GD, OH - oy_r + GD, G0, G1) - box(ox_r, OW - ox_r, oy_r, OH - oy_r, G0 - 1, G1 + 1)
# rope notches (rope runs under the lip at top and bottom; mirrored so the plaque fits either way up)
pl_x0 = ox_p + P['CL']
nx0, nx1 = pl_x0 + 80.5, pl_x0 + 99.5
cut += box(nx0, nx1, oy_p - 0.01, oy_w + 1.0, Z_PKT - 0.01, Z_NOTCH)
cut += box(nx0, nx1, OH - oy_w - 1.0, OH - oy_p + 0.01, Z_PKT - 0.01, Z_NOTCH)
# coin slot to pry the back board out (bottom edge, centre)
cut += box(OW / 2 - 6, OW / 2 + 6, oy_r - 1.6, oy_r + 0.1, -1, 1.2)
frame = fr - cut
frame_t = T(frame)
vv, ff = fs.simplify(np.asarray(frame_t.vertices, np.float32), np.asarray(frame_t.faces), target_reduction=0.45)
frame_t = trimesh.Trimesh(vv, ff)
print('frame tris', len(frame_t.faces), 'bounds', frame_t.bounds.round(2).tolist())

# ---------------- back board ----------------
bw, bh, bt = rec_w - 2 * P['BACK_CL'], rec_h - 2 * P['BACK_CL'], P['BACK_T']
bx0, by0 = ox_r + P['BACK_CL'], oy_r + P['BACK_CL']
board = box(bx0, bx0 + bw, by0, by0 + bh, 0, bt)
# lightening windows (leave rim 16, centre bars)
rim, vbar, hbar_y, hbar_h = 10.0, 14.0, by0 + bh * 0.47, 16.0
cx = bx0 + bw / 2
def rrect(x0, x1, y0, y1, r=6):
    sq = m3d.CrossSection.square([x1 - x0 - 2 * r, y1 - y0 - 2 * r]).translate([x0 + r, y0 + r]).offset(r, m3d.JoinType.Round)
    return m3d.Manifold.extrude(sq, bt + 2).translate([0, 0, -1])
win_y = [(by0 + rim, hbar_y - hbar_h / 2), (hbar_y + hbar_h / 2, by0 + bh - rim)]
for (y0, y1) in win_y:
    board -= rrect(bx0 + rim, cx - vbar / 2, y0, y1)
    board -= rrect(cx + vbar / 2, bx0 + bw - rim, y0, y1)
# snap tabs: cantilever strips along the edges with a ramped bump on the tip
SL, SW, SS = 24.0, 1.8, 1.0          # strip length, strip width, slot width
bumps = []
def tab(edge, pos):
    """edge: 'L','R','B','T'; pos: centre along the edge."""
    global board
    if edge in 'LR':
        x_e = bx0 if edge == 'L' else bx0 + bw
        sgn = 1 if edge == 'L' else -1          # inward direction
        y0, y1 = pos - SL / 2, pos + SL / 2
        xi = x_e + sgn * SW
        board -= box(min(xi, xi + sgn * SS), max(xi, xi + sgn * SS), y0, y1 + SS, -1, bt + 1)     # long slot
        board -= box(min(x_e - sgn, xi + sgn * SS), max(x_e - sgn, xi + sgn * SS), y1, y1 + SS, -1, bt + 1)  # free end
        # bump near the free end, protruding outward
        cs = m3d.CrossSection([[[0, 0.6], [0.7, 0.6], [0.7, 0.8], [0, 1.4]]])  # (out, z)
        b = m3d.Manifold.extrude(cs, 7.0)            # along +z of 2D -> becomes the edge direction
        # map: 2D x=out, 2D y=z, extrude=edge dir (y)
        b = b.transform([[sgn * -1, 0, 0, x_e], [0, 0, 1, y1 - 8.0], [0, 1, 0, 0]]) if True else b
        bumps.append(b)
    else:
        y_e = by0 if edge == 'B' else by0 + bh
        sgn = 1 if edge == 'B' else -1
        x0, x1 = pos - SL / 2, pos + SL / 2
        yi = y_e + sgn * SW
        board -= box(x0, x1 + SS, min(yi, yi + sgn * SS), max(yi, yi + sgn * SS), -1, bt + 1)
        board -= box(x1, x1 + SS, min(y_e - sgn, yi + sgn * SS), max(y_e - sgn, yi + sgn * SS), -1, bt + 1)
        cs = m3d.CrossSection([[[0, 0.6], [0.7, 0.6], [0.7, 0.8], [0, 1.4]]])
        b = m3d.Manifold.extrude(cs, 7.0)
        b = b.transform([[0, 0, 1, x1 - 8.0], [sgn * -1, 0, 0, y_e], [0, 1, 0, 0]])
        bumps.append(b)
for yy in (by0 + bh * 0.2, by0 + bh * 0.5, by0 + bh * 0.8):
    tab('L', yy); tab('R', yy)
for xx in (bx0 + bw * 0.27, bx0 + bw * 0.73):
    tab('B', xx); tab('T', xx)
for b in bumps:
    board += b
# pry notch matching the coin slot
board -= box(OW / 2 - 6, OW / 2 + 6, by0 - 1, by0 + 1.2, -1, 1.2)

# keyhole boss (wall hanging), top centre, on the back (z < 0)
ky = by0 + bh - rim - 13
kb = box(cx - 9, cx + 9, ky - 13, ky + 12, -5.0, 0.01)
kh = m3d.Manifold.cylinder(6, 4.8, 4.8, 48).translate([cx, ky - 5, -5.5])                 # head entry
kh += box(cx - 2.3, cx + 2.3, ky - 5, ky + 6, -5.5, -0.5 - 2.5)                           # shank slot
kh += box(cx - 4.8, cx + 4.8, ky - 5, ky + 6, -3.0, -0.6)                                 # head channel
kh += m3d.Manifold.cylinder(2.4, 4.8, 4.8, 48).translate([cx, ky + 6, -3.0])
kh += m3d.Manifold.cylinder(6, 2.3, 2.3, 48).translate([cx, ky + 6, -5.5])
board += box(cx - 11, cx + 11, ky - 15, ky + 14, 0, bt)   # solid patch under the keyhole
board += kb - kh

# desk-stand socket on the centre bar
ALPHA, THETA = np.radians(15), np.radians(32)     # lean back 15 deg; leg 32 deg from the board
LW, LT, CLs = 18.0, 4.0, 0.15
sy = hbar_y + 12
dvec = np.array([0, -np.cos(THETA), -np.sin(THETA)])
nvec = np.array([0, np.sin(THETA), -np.cos(THETA)])
top_c = np.array([cx, sy, -1.2]) + nvec * (LT / 2 + CLs + 0.8)   # centre of the leg's top end
def leg_solid(length, w, t, start):
    rot = np.c_[[1, 0, 0], -dvec, nvec]          # local x, y(=-d), z(=n)
    m = box(-w / 2, w / 2, -length, 0, -t / 2, t / 2)
    A = np.c_[rot, start]
    return m.transform(A[:3].tolist())
sock = leg_solid(40, LW + 2 * CLs, LT + 2 * CLs, top_c)
sleeve = leg_solid(20, LW + 2 * CLs + 4.4, LT + 2 * CLs + 3.2, top_c - dvec * 1.6)
bb = sleeve.bounding_box()
foot = box(bb[0], bb[3], bb[1], bb[4], -0.6, 0.01)
boss = m3d.Manifold.batch_hull([sleeve, foot])
board += box(bb[0] - 2, bb[3] + 2, bb[1] - 2, bb[4] + 2, 0, bt)   # solid patch under the stand socket
board += boss - sock - box(cx - 20, cx + 20, sy - 60, sy + 10, 0.0, 5)  # keep board front flat
# leg length so that the foot meets the desk with the frame leaning back ALPHA
up = np.array([0, np.cos(ALPHA), np.sin(ALPHA)])
# frame pivots on its bottom-back edge (y=0, z=0) -> heights measured along 'up'
Lfoot = -(top_c @ up) / (dvec @ up)
INS = 12.0
print('leg length', round(Lfoot, 1), 'foot behind pivot', round(-(top_c + Lfoot * dvec) @ np.array([0, np.sin(ALPHA), -np.cos(ALPHA)]) * -1, 1))
board_t = T(board)
print('board tris', len(board_t.faces), 'bounds', board_t.bounds.round(2).tolist())

# stand leg (printed flat): length Lfoot from the top end, rounded foot, chamfered sides
Ltot = Lfoot
leg2d = m3d.CrossSection.square([LW, Ltot - LW / 2]).translate([-LW / 2, 0]) + m3d.CrossSection.circle(LW / 2, 64).translate([0, Ltot - LW / 2])
leg2d = leg2d - m3d.CrossSection.square([6, 30]).translate([-3, Ltot - 40]).offset(1.5, m3d.JoinType.Round)  # grip slot
leg = m3d.Manifold.extrude(leg2d, LT)
leg_t = T(leg)

# ---------------- export ----------------
os.makedirs(OUT, exist_ok=True)
frame_t.export(OUT + '/frame_front_navy.stl')
bt_print = board_t.copy(); bt_print.apply_transform(trimesh.transformations.reflection_matrix([0, 0, 0], [0, 0, 1]))
bt_print.apply_translation((0, 0, -bt_print.bounds[0, 2]))
board_t.export(OUT + '/_board_assembled.stl')
bt_print.export(OUT + '/frame_back_board.stl')
leg_t.export(OUT + '/frame_stand_leg.stl')
# assembled leg for previews
lg = T(leg_solid(Ltot, LW, LT, top_c)); lg.export(OUT + '/_leg_assembled.stl')
for n in ['frame_front_navy', 'frame_back_board', 'frame_stand_leg']:
    m = trimesh.load(OUT + f'/{n}.stl')
    print(n, 'vol cm3', round(abs(m.volume) / 1000, 1), 'size', (m.bounds[1] - m.bounds[0]).round(1).tolist(), 'wt', m.is_watertight)
json.dump(dict(OW=OW, OH=OH, plaque_xy=[ox_p + P['CL'], oy_p + P['CL']], plaque_z=Z_REC), open(OUT + '/_layout.json', 'w'))
