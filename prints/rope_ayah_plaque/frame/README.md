# Classic frame with turn buttons for the rope plaque (15 mm face)

Navy matte PLA, wood-grain face, one piece (fits Bambu Lab A2L, 330 x 320 bed).
Holds the printed plaque (180 x 240 x 2 mm). See `frame_dimensions.png` and `frame_preview.png`.

| File | Size X x Y x Z (mm) | ~g (15% infill, 2 walls) |
|---|---|---|
| `frame_front_navy.stl` | 202.0 x 262.0 x 13.5 | 70 |
| `frame_back_board.stl` | 184.2 x 244.2 x 18.2 | 34 |
| `frame_turn_buttons_x8.stl` | 84.8 x 20.0 x 9.9 (8 buttons) | 3 |
| `frame_stand_leg.stl` | 18.0 x 137.6 x 4.0 | 7 |

A2L ready layouts:
- `A2L_plate1_frame_and_leg.stl` (258 x 262 mm)
- `A2L_plate2_back_board_and_buttons.stl` (290 x 244 mm)
- `A2L_ALL_frame_parts_one_file.stl`: everything in one file; in Bambu Studio use Split > To objects and move the board and buttons to plate 2.

## Closure: turn buttons
8 swivel buttons on the back face. Each has a split peg with a barb that clicks into a pivot hole
(4.15 mm hole, 4.9 mm barb chamber), so it stays on the frame but still turns.
Turn the button inward to hold the back board, or turn it parallel to the edge to release it.
A 0.3 mm nub under the tip presses the board, so it cannot spring back out.

- Outer 202 x 262 mm, face 15 mm, window 172 x 232 mm, depth 13.5 mm.
- Plaque pocket 180.6 x 240.6 x 2.2 mm (z 1.6 – 3.8 from the back), 45 deg lip, notches for the rope.
- Hollow channels inside the members (open to the back, 45 deg roof); solid around each pivot. No supports needed.

Build: `python3 build_frame.py <out_dir>` (defaults: BORDER 15, BACK_T 1.6, RES 0.25).
