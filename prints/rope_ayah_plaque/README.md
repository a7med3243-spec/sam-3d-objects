# Rope plaque, "rabbana wa la tuhammilna ma la taqata lana bih" (3D print)

Size 180 x 240 mm (18x24 cm frame). PLA, 0.2 mm layer height.

| File | Color | Z range |
|---|---|---|
| `1_base_white.stl` | white | 0 – 2 mm |
| `2_rope_and_outline_black.stl` | black | 2 – 7 mm |
| `3_letters_face_white.stl` | white | 7 – 7.8 mm |
| `plaque_single_file_pause_at_2mm_and_7mm.stl` | all merged | 0 – 7.75 mm |

- AMS / multi-color: import files 1–3 together as one multi-part object and assign colors.
- Single-color printer: use the merged file with a filament change at 2.0 mm (white -> black) and 7.0 mm (black -> white).
- Print sequence: by layer (not by object).
- Approx. filament (15% infill): ~100 g white + ~13 g black.

`build_plaque.py` regenerates the meshes (needs trimesh, shapely, manifold3d, scikit-image, opencv, Pillow with raqm, Amiri + EB Garamond fonts).

Build parameters used: `{"AR_SIZE":7.7,"EN_SIZE":6.2,"EN_LEAD":7.0,"OUTLINE":0.45,"TEXT_H":5.0,"PLATE_T":2.0,"AR_DX":5,"EN_DX":7.5}`
