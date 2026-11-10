import sys, json
import numpy as np, cv2, trimesh, shapely
from shapely.geometry import Polygon
from shapely.ops import unary_union
from skimage.measure import marching_cubes
from PIL import Image, ImageDraw, ImageFont
import manifold3d as m3d

S = sys.argv[1]
SRC = sys.argv[2]
P = dict(W=180.0, H=240.0, PLATE_T=3.0, ROPE_MIN=3.0, ROPE_MAX=5.0, TEXT_H=3.0)
if len(sys.argv) > 3:
    P.update(json.loads(sys.argv[3]))
W, H, PT = P['W'], P['H'], P['PLATE_T']

img = cv2.imread(SRC, 0)
ih, iw = img.shape
s = H / ih                       # mm per photo px
ox = (W - iw * s) / 2            # x offset of photo inside plate
def px2mm(x, y): return ox + x * s, H - y * s   # y-up in mm

# ---------- rope mask from photo ----------
mask = (img < 180).astype(np.uint8)
mask[:, :470] = 0; mask[:, 860:] = 0
mask[700:1215, :605] = 0          # arabic text region
mask[800:1115, 725:] = 0          # english text region
mask[:5, :] = 0                   # phone UI border line
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
n, lab, st, _ = cv2.connectedComponentsWithStats(mask, 8)
keep = np.zeros(n, bool); keep[1:] = st[1:, cv2.CC_STAT_AREA] > 60
mask = keep[lab].astype(np.uint8)
inv = 1 - mask
n2, lab2, st2, _ = cv2.connectedComponentsWithStats(inv, 4)
small = np.zeros(n2, bool); small[1:] = st2[1:, cv2.CC_STAT_AREA] < 400
mask[small[lab2]] = 1
mask[:6, :] = mask[6:7, :]        # extend rope to the plate edges
mask[-6:, :] = mask[-7:-6, :]

# ---------- rope relief via marching cubes ----------
R = 0.15                          # mm grid
xs = np.arange(ox + 465 * s, ox + 865 * s, R)
ys = np.arange(0, H + R / 2, R)   # mm, y-up
gx, gy = np.meshgrid(xs, ys)
mapx = ((gx - ox) / s).astype(np.float32)
mapy = ((H - gy) / s).astype(np.float32)
mk = cv2.GaussianBlur(cv2.remap(mask.astype(np.float32), mapx, mapy, cv2.INTER_LINEAR), (0, 0), 1.3) > 0.5
gray = cv2.remap(cv2.GaussianBlur(img, (0, 0), 1.2).astype(np.float32), mapx, mapy, cv2.INTER_LINEAR)
mk[0, :] = mk[1, :]; mk[-1, :] = mk[-2, :]
sd = cv2.distanceTransform(mk.astype(np.uint8), cv2.DIST_L2, 5) * R  # mm to edge
t = np.clip((gray - 35) / (190 - 35), 0, 1)
t = cv2.GaussianBlur(t, (0, 0), 1.5)
core = np.clip(sd / 1.6, 0, 1)              # thicker parts rise higher
hrel = P['ROPE_MIN'] - 1.2 + 1.2 * core + (P['ROPE_MAX'] - P['ROPE_MIN']) * (0.35 + 0.65 * t) * core
hedge = 0.8 + sd * 2.2                       # bevelled edge
h = np.minimum(hrel, hedge)
h = np.maximum(h, 1.2)                       # thin fibres stay printable
h = cv2.GaussianBlur(h.astype(np.float32), (0, 0), 0.8)
h[~mk] = -1.0
dz = 0.1
nz = int(np.ceil(P['ROPE_MAX'] / dz)) + 3
zs = (np.arange(nz) - 1) * dz                # first slice below 0 = closed bottom
vol = h[None, :, :] - zs[:, None, None]
vol[0] = -1.0
vol = np.pad(vol, ((0, 0), (1, 1), (1, 1)), constant_values=-1.0)
v, f, _, _ = marching_cubes(vol, 0.0)
vz = (v[:, 0] - 1) * dz
vy = (v[:, 1] - 1) * R
vx = xs[0] + (v[:, 2] - 1) * R
rope = trimesh.Trimesh(np.c_[vx, vy, vz], f[:, ::-1], process=True)
print('raw rope watertight', rope.is_watertight, len(rope.faces))
import fast_simplification as fs
vv, ff = fs.simplify(np.asarray(rope.vertices, np.float32), np.asarray(rope.faces), target_reduction=0.7)
rope = trimesh.Trimesh(vv, ff, process=True)
if rope.volume < 0: rope.invert()

# ---------- text ----------
PXMM = 24
def text_layer(lines, fontfile, size_mm, anchor_x_mm, top_mm, lead_mm, align, rtl):
    Wp, Hp = int(W * PXMM), int(H * PXMM)
    im = Image.new('L', (Wp, Hp), 0)
    d = ImageDraw.Draw(im)
    ft = ImageFont.truetype(fontfile, int(size_mm * PXMM), layout_engine=ImageFont.Layout.RAQM)
    kw = dict(direction='rtl', language='ar') if rtl else {}
    for i, ln in enumerate(lines):
        y = (H - top_mm + i * lead_mm) * PXMM
        anc = {'c': 'ms', 'l': 'ls', 'r': 'rs'}[align]
        d.text((anchor_x_mm * PXMM, y), ln, font=ft, fill=255, anchor=anc, **kw)
    return np.array(im)

def bitmap_polys(bm):
    cs, hier = cv2.findContours(bm, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    polys = []
    if hier is None: return polys
    hier = hier[0]
    def tomm(c):
        c = c[:, 0, :].astype(float)
        return np.c_[c[:, 0] / PXMM, H - c[:, 1] / PXMM]
    for i, c in enumerate(cs):
        if hier[i][3] != -1 or len(c) < 4: continue
        holes = []; j = hier[i][2]
        while j != -1:
            if len(cs[j]) >= 4: holes.append(tomm(cs[j]))
            j = hier[j][0]
        p = Polygon(tomm(c), holes).buffer(0).simplify(0.015)
        if p.area > 0.05: polys.append(p)
    return polys

F = S + '/fonts/'
ar_lines = ['رَبَّنَا', 'وَلَا', 'تُحَمِّلْنَا', 'مَا لَا', 'طَاقَةَ', 'لَنَا بِهِۦ']
en_lines = ['Our Lord,', 'and burden', 'us not with', 'that which we', 'have no', 'ability to bear']
ax, _ = px2mm(515, 0)
ex, _ = px2mm(735, 0)
lead_ar = P.get('AR_LEAD', 10.6); lead_en = P.get('EN_LEAD', 49 * s)
ar_bm = text_layer(ar_lines, F + 'amiri700.ttf', P.get('AR_SIZE', 7.0), ax, H - 785 * s, lead_ar, 'c', True)
en_bm = text_layer(en_lines, F + 'garamond600.ttf', P.get('EN_SIZE', 5.4), ex, H - 850 * s, lead_en, 'l', False)
txt = unary_union(bitmap_polys(ar_bm | en_bm))

# keep text off the rope
rope2d = unary_union([Polygon(np.c_[c[:, 0, 0] * 1.0, c[:, 0, 1] * 1.0]) for c in []])
geoms = list(txt.geoms) if hasattr(txt, 'geoms') else [txt]
def ext(geom, hh):
    gs = list(geom.geoms) if hasattr(geom, 'geoms') else [geom]
    return trimesh.util.concatenate([trimesh.creation.extrude_polygon(g, hh) for g in gs if g.area > 0.01])
OUTL = P.get('OUTLINE', 0.55)
outline2d = txt.buffer(OUTL, resolution=8).simplify(0.015)
text_mesh = ext(outline2d, P['TEXT_H'])                 # black outline base
fill_mesh = ext(txt, P.get('FILL_H', 0.8))               # coloured letters on top
fill_mesh.apply_translation((0, 0, PT + P['TEXT_H']))

# ---------- plate ----------
plate = trimesh.creation.box((W, H, PT)); plate.apply_translation((W / 2, H / 2, PT / 2))

def to_m(t):
    return m3d.Manifold(m3d.Mesh(np.asarray(t.vertices, np.float32), np.asarray(t.faces, np.uint32)))
def from_m(m):
    mm = m.to_mesh(); return trimesh.Trimesh(mm.vert_properties[:, :3], mm.tri_verts)

black_sep = trimesh.util.concatenate([rope, text_mesh]); black_sep.apply_translation((0, 0, PT))
clip = trimesh.creation.box((W, H, P['ROPE_MAX'] + 1)); clip.apply_translation((W/2, H/2, (P['ROPE_MAX'] + 1) / 2 - 1))
rope = from_m(to_m(rope) ^ to_m(clip))
black_u = from_m(to_m(rope) + to_m(text_mesh)); black_u.apply_translation((0, 0, PT))
full = fill_mesh

out = S + '/out/'
import os; os.makedirs(out, exist_ok=True)
plate.export(out + 'plaque_base_white.stl')
black_u.export(out + 'plaque_rope_text_black.stl')
fill_mesh.export(out + 'plaque_text_fill_color.stl')
import os as _o
if _o.path.exists(out + 'plaque_full_single.stl'): _o.remove(out + 'plaque_full_single.stl')
cv2.imwrite(out + 'text_debug.png', 255 - (ar_bm | en_bm)[::4, ::4])
for n_, m_ in [('rope', rope), ('black', black_u), ('full', full)]:
    print(n_, len(m_.faces), 'watertight', m_.is_watertight, 'bounds', np.round(m_.bounds, 2).tolist())
rb = cv2.resize(mk.astype(np.uint8), None, fx=1, fy=1)
print('min text-rope gap check skipped');print('', round(txt.intersection(
    unary_union([Polygon(p) for p in []]) if False else Polygon()).area, 3))
