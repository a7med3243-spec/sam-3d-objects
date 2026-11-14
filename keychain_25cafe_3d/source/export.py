"""Export the three colour parts as STL files and one 3MF (one object, three named, coloured parts)."""
import os, sys, zipfile, io
import numpy as np, trimesh

SRC, DST, NAME = sys.argv[1], sys.argv[2], sys.argv[3]
THUMB = sys.argv[4] if len(sys.argv) > 4 else None
os.makedirs(DST, exist_ok=True)
MODE = os.environ.get('KC_MODE', 'flat')
PARTS = [  # file tag, part name shown in the slicer, display colour
    ('1_black', '1 - Black (lid, outline, back, ring)', '#1E1E1EFF'),
    ('2_beige', '2 - Beige (cup)', '#D8C8ADFF'),
    ('3_brown', '3 - Dark brown (logo)', '#4A3426FF'),
] if MODE == 'flat' else [
    ('1_black', '1 - Black (lid and loop)', '#1E1E1EFF'),
    ('2_beige', '2 - Beige (cup)', '#D8C8ADFF'),
    ('3_brown', '3 - Dark brown (logo and text)', '#4A3426FF'),
    ('4_white', '4 - White (rolled bottom ring)', '#F2EFE8FF'),
]
meshes = {}
for tag, label, col in PARTS:
    d = np.load(os.path.join(SRC, tag.split('_')[1] + '.npz'))
    m = trimesh.Trimesh(d['v'].astype(np.float64), d['f'].astype(np.int64), process=False)
    e = np.linalg.norm(m.vertices[m.faces[:, [1, 2, 0]]] - m.vertices[m.faces], axis=2)
    nz = int((m.area_faces < 1e-9).sum())
    assert nz <= 60, (tag, nz)   # a few zero-area slivers from booleans are harmless; slicers drop them
    if nz: print(f'{tag}: {nz} zero-area sliver triangles (harmless)')
    assert m.is_watertight and m.is_winding_consistent and m.volume > 0, tag
    meshes[tag] = m
    m.export(os.path.join(DST, f'{NAME}_{tag}.stl'))

def mesh_xml(m):
    v = '\n'.join(f'<vertex x="{a:.5f}" y="{b:.5f}" z="{c:.5f}"/>' for a, b, c in m.vertices)
    t = '\n'.join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces)
    return f'<mesh><vertices>\n{v}\n</vertices><triangles>\n{t}\n</triangles></mesh>'

objs, comps, mats = [], [], []
for i, (tag, label, col) in enumerate(PARTS):
    oid = i + 2
    mats.append(f'<base name="{label.split(" (")[0][4:]}" displaycolor="{col}"/>')
    objs.append(f'<object id="{oid}" name="{label}" type="model" pid="1" pindex="{i}">{mesh_xml(meshes[tag])}</object>')
    comps.append(f'<component objectid="{oid}"/>')
model = f'''<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
<metadata name="Title">25 Percent Cafe - cup keychain</metadata>
<metadata name="Designer">Claude Code</metadata>
<metadata name="Description">{'3-colour keychain: black lid/outline, beige cup, dark-brown logo. Print face up, no supports, 0.2 mm layers.' if MODE == 'flat' else '3D mini cup keychain: black lid+loop, beige cup, dark-brown logo/text, white bottom ring. Print upright, no supports.'}</metadata>
<resources>
<basematerials id="1">{''.join(mats)}</basematerials>
{chr(10).join(objs)}
<object id="{len(PARTS) + 2}" name="{NAME}" type="model"><components>{''.join(comps)}</components></object>
</resources>
<build><item objectid="{len(PARTS) + 2}" transform="1 0 0 0 1 0 0 0 1 165 160 0"/></build>
</model>'''
ct = '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
<Default Extension="png" ContentType="image/png"/>
</Types>'''
rels = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
''' + ('<Relationship Target="/Metadata/thumbnail.png" Id="rel1" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail"/>\n' if THUMB else '') + '</Relationships>'
with zipfile.ZipFile(os.path.join(DST, f'{NAME}.3mf'), 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml', ct)
    z.writestr('_rels/.rels', rels)
    z.writestr('3D/3dmodel.model', model)
    if THUMB: z.write(THUMB, 'Metadata/thumbnail.png')
for f in sorted(os.listdir(DST)):
    print(f, os.path.getsize(os.path.join(DST, f)) // 1024, 'KB')
