# Classic snap frame for the rope plaque

Navy matte PLA, wood-grain face, mitred-corner look. Holds the printed plaque (180 x 240 x 2 mm).

| File | Size (mm) | Print orientation |
|---|---|---|
| `frame_front_navy.stl` | 194 x 254 x 13.5 | back face down (as exported), no supports |
| `frame_back_board.stl` | 186 x 246 x 18 (open lattice, 1.6 mm board) | as exported (flat side down), no supports |
| `frame_stand_leg.stl` | 18 x 134 x 4 | flat |

- Visible face width 11 mm; the window shows 172 x 232 mm of the plaque.
- Plaque pocket 180.6 x 240.6 x 2.2 mm (starts 1.6 mm from the back) (0.3 mm clearance); a 45 deg lip holds the plaque edge, and notches let the rope relief pass under the lip (fits either way up).
- Back board snaps in with 10 cantilever tabs that click into a groove; the coin slot at the bottom edge lets you pry it out.
- Keyhole for wall hanging (screw head up to 9 mm); a socket for the desk stand (about 15 deg lean back).
- Approx. filament (light version, 15% infill, 2 walls): frame ~52 g, back board ~35 g, leg ~6 g = ~93 g (was ~126 g).

Assembly: put the plaque face-down into the frame, press the back board in until all tabs click, then push the leg into the socket.

Build: `python3 build_frame.py <out_dir> '{"BACK_T":1.6}'`
