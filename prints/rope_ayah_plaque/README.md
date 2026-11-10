# Rope plaque, "rabbana wa la tuhammilna ma la taqata lana bih" (3D print)

Size 180 x 240 mm (18x24 cm frame). PLA, 0.2 mm layer height.

| File | Color | Z range |
|---|---|---|
| `1_base_white.stl` | white | 0 – 3 mm |
| `2_rope_and_outline_black.stl` | black | 3 – 8 mm |
| `3_letters_face_white.stl` | white | 8 – 8.8 mm |
| `plaque_single_file_pause_at_3mm_and_8mm.stl` | all merged | 0 – 8.75 mm |

- AMS / multi-color: import files 1–3 together as one multi-part object and assign colors.
- Single-color printer: use the merged file with a filament change at 3.0 mm (white -> black) and 8.0 mm (black -> white).
- Print sequence: by layer (not by object).
- Approx. filament (15% infill): ~105 g white + ~13 g black.

`build_plaque.py` regenerates the meshes (needs trimesh, shapely, manifold3d, scikit-image, opencv, Pillow with raqm, Amiri + EB Garamond fonts).
