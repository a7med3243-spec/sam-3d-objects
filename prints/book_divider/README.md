# Book Dividers – 6 shapes, filament-optimized (STL / 3MF)

![preview](preview.png)

Same design in six outlines: concentric ribs (3 mm deep) on **both faces**, closed plate,
**hollow skeleton base**, prints upright with **no supports**.

| Shape | Files (in `models/`) | Filament* | Time* (fast CoreXY) |
|---|---|---|---|
| Arch | `arch.3mf` · `arch_x2.3mf` · `arch.stl` | 65 g | 2 h 56 m |
| Pointed arch | `pointed_arch.3mf` · `pointed_arch_x2.3mf` · `pointed_arch.stl` | 60 g | 2 h 42 m |
| House | `house.3mf` · `house_x2.3mf` · `house.stl` | 60 g | 2 h 45 m |
| Mountain | `mountain.3mf` · `mountain_x2.3mf` · `mountain.stl` | 40 g | 1 h 55 m |
| Tablet | `tablet.3mf` · `tablet_x2.3mf` · `tablet.stl` | 69 g | 2 h 52 m |
| Octagon | `octagon.3mf` · `octagon_x2.3mf` · `octagon.stl` | 65 g | 2 h 47 m |

\* one piece, 2 walls + Lightning 8 %, measured in PrusaSlicer 2.7. Standard-speed printers take ~2× longer.

- `<shape>.3mf` / `<shape>.stl` – one piece.
- `<shape>_x2.3mf` – **pair ready to print**: two pieces on one plate (218 × 135 mm), fits
  Bambu X1/P1/A1 (256 × 256) and Prusa MK4/MK3 (250 × 210). On a 220 × 220 bed print the
  single file twice.

**Size (all shapes):** 135 W × 155 H × 105 D mm, plate 20 mm deep, base 4.5 mm thick (85 mm protrusion).

## Print settings – the infill type is what saves filament
| Setting | Value |
|---|---|
| Orientation | As exported – base flat on the bed |
| Supports | **Off** |
| Infill | **Lightning 8 %** (a 15 % grid default roughly doubles the filament) |
| Walls | 2 (3 for a stiffer part, ~+25 g) |
| Layer height | 0.2 mm, nozzle 0.4 mm, 4 top / 3 bottom layers |
| Material | PLA or PETG |

## Generator
`book_divider.py` builds every shape from the same rib profile and base
(`pip install manifold3d numpy`, then `python book_divider.py [shape ...]`).
Width, height, rib count/depth, base size etc. are parameters at the top of the file;
new outlines are a few lines each (see `SHAPES`).

![pair](preview_x2.png)
