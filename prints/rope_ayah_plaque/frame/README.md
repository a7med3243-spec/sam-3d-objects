# Classic snap frame for the rope plaque (20 mm face)

Navy matte PLA, wood-grain face, mitred corners. Holds the printed plaque (180 x 240 x 2 mm).
See `frame_dimensions.png` for the drawing and `frame_preview.png` for renders.

| File | Size X x Y x Z (mm) | Notes |
|---|---|---|
| `frame_part_top.stl`, `frame_part_bottom.stl` | 212.0 x 20.0 x 13.5 | back face down |
| `frame_part_left.stl`, `frame_part_right.stl` | 192.3 x 192.3 x 13.5 | pre-rotated 45 deg to fit a 256 mm bed; back face down |
| `frame_corner_keys_x4.stl` | 123.8 x 27.8 x 4.5 | 4 L-keys that join the corners from the back |
| `frame_back_board.stl` | 185.6 x 245.6 x 18.2 | snap-in back board (open lattice) with keyhole + stand socket |
| `frame_stand_leg.stl` | 18.0 x 142.7 x 4.0 | desk stand, about 15 deg lean back |
| `frame_front_navy_ONE_PIECE.stl` | 212.0 x 272.0 x 13.5 | optional, only for beds >= 275 mm |

- Outer 212 x 272 mm, visible face 20 mm, window 172 x 232 mm, total depth 13.5 mm.
- Plaque pocket 180.6 x 240.6 x 2.2 mm (z 1.6 – 3.8 from the back), 45 deg lip, notches for the rope.
- Hollow channel inside each member (open to the back, 45 deg roof), so no supports are needed.
- Approx. filament (15% infill, 2 walls): ~134 g for the 4-piece kit.

Assembly: glue the 4 frame parts at the mitres with the corner keys pressed into the channels at the back,
then put the plaque face-down in the pocket and snap the back board in (10 tabs). Push the leg into the socket.

Build: `python3 build_frame.py <out_dir>` (defaults: BORDER 20, BACK_T 1.6, RES 0.25).

## Bambu Lab A2L (330 x 320 bed)

The one-piece frame fits, so no corner keys are needed.
- `A2L_plate1_frame_and_leg.stl`: one-piece frame + stand leg (262 x 272 mm), plate 1.
- `A2L_plate2_back_board.stl`: back board, plate 2.
- `A2L_ALL_frame_parts_one_file.stl`: all three parts in one file. In Bambu Studio use right-click > Split > To objects, then move the back board to a second plate.
