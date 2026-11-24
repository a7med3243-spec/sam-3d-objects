// =====================================================================
//  Slim magnetic fridge photo frame  -  NO glass / NO clear sheet
//  ---------------------------------------------------------------
//  3 printed parts:
//    1) Front frame      - printed face-down, no supports
//    2) Back cover       - 4 hidden magnets (8 x 1.5 mm), 2 rigid tongues
//                          at the bottom + 1 flexible snap latch at the top
//    3) Name plate       - press-fit into the bottom tab from the back,
//                          push it out from the front to swap (no tools,
//                          no need to open the frame)
//
//  Units: mm.  Works in OpenSCAD 2021.01+ and in the Customizer
//  (OpenSCAD  Window > Customizer, or MakerWorld "Parametric Model Maker").
//  To make a new name plate: set part = "insert", type your text in
//  "label", press F6 (Render) then F7 (Export STL).
// =====================================================================

/* [What to render] */
part = "insert"; // [frame:Front frame, cover:Back cover, insert:Name plate, plate:All parts on one build plate, assembly:Assembled preview, exploded:Exploded preview]

/* [Name plate text] */
// Country / city / date ... (Arabic is supported)
label = "TURKEY";
// Optional smaller second line (leave empty for one line)
second_line = "";
text_style = "raised"; // [raised:Raised (2 colours by filament change), engraved:Engraved]
// Max text height (it shrinks automatically if the text is long)
text_size = 5.0;
// Raised height / engraving depth
text_depth = 0.6;
font_latin = "Liberation Sans:style=Bold";
font_arabic = "Noto Kufi Arabic:style=Bold";

/* [Photo] */
photo_w = 86;
photo_h = 54;
// Room for the photo between the front lip and the cover (0.4 = normal photo paper up to ~0.35 mm, 0.8 = Instax / thick card)
photo_space = 0.4; // [0.4, 0.6, 0.8, 1.0]
// Side clearance around the photo (per side)
photo_clr = 0.3;
// How much the front lip covers the photo edge (per side)
lip_overlap = 1.2;

/* [Magnets] */
mag_d = 8;
mag_t = 1.5;
// Plastic skin between magnet and fridge (keeps magnets hidden, protects the fridge)
mag_skin = 0.4;
// Interference of the crush ribs that hold the magnets (0 = loose, use glue)
mag_grip = 0.05;

/* [Fit / tolerances] */
// Gap between cover and frame (per side)
cover_clr = 0.15;
// Gap between name plate and its socket (per side)
insert_clr = 0.15;
// Name-plate hold: how far the 4 spring arms press on the socket wall (bigger = firmer)
plate_grip = 0.45; // [0.3:Soft, 0.45:Normal, 0.6:Tight]
// Click grooves for the name plate in the frame (plates also hold by spring force without them)
plate_click = true;

/* [Hidden] */
$fa = 3; $fs = 0.2;
eps = 0.01;

// ---------------- derived dimensions ----------------
lip_t    = 1.8;                                   // thick front lip (9 layers @0.2)
cover_t  = max(2.2, mag_t + 0.1 + mag_skin);      // back cover thickness
T        = lip_t + photo_space + cover_t;         // total thickness (4.4 default, like the reference)
pocket   = [photo_w + 2*photo_clr, photo_h + 2*photo_clr];   // 86.6 x 54.6
pocket_r = 1.0;                                    // sharp photo corners still fit
window   = [photo_w - 2*lip_overlap, photo_h - 2*lip_overlap]; // 83.6 x 51.6
win_r    = 5.0;                                   // soft window corners
wall     = 3.5;
outer    = pocket + [2*wall, 2*wall];             // 93.6 x 61.6
R_out    = 9.0;                                   // large rounded corners

// name-plate socket in the bottom tab
tab_w     = 38;  tab_h = 11.5;                    // bottom tab (below the body)
tab_r     = 5;   fil_r = 4;                        // tab corners / blend into body
shoulder  = 1.4;                                   // lip that stops the plate
sep       = 1.4;                                   // wall between photo and plate
tab_bot   = -outer.y/2 - tab_h;                    // -42.3
tp_top    = -pocket.y/2 - sep;                     // -28.7
tab_pocket= [tab_w - 2*2.5, tp_top - (tab_bot + 2.2)];   // 33 x 11.4 (walls 2.5 / 2.2)
tp_cy     = tp_top - tab_pocket.y/2;               // socket / window centre y
nwin      = tab_pocket - 2*[shoulder + insert_clr, shoulder + insert_clr]; // 29.9 x 8.3
nwin_r    = 3.2;                                   // pill-shaped name plate
tp_r      = nwin_r + shoulder + insert_clr;

// back cover
cw   = pocket.x - 2*cover_clr;                     // 86.3
ch   = pocket.y - 2*cover_clr;                     // 54.3
cr   = pocket_r - cover_clr;
// latch & tongues (retention faces sit latch_a above the cover back face)
latch_a  = 1.0;                                    // = ledge thickness in the frame
hook_e   = 0.8;  hook_w = 10;
tongue_e = 1.0;  tongue_w = 10;  tongue_x = 29;
beam_b   = 1.5;  slot_s = 1.2;  beam_L = 20;  pad_w = 12;  pad_h = 6.15;
mag_pos  = [[-36,-19.5],[36,-19.5],[-36,19.5],[36,19.5]];
mag_pr   = mag_d/2 + 0.15;                         // magnet pocket radius
recess_d = 0.8;                                    // filament-saving back recess

// name plate spring arms (4 cantilevers on the long edges, bumps near their free ends)
arm_b  = 0.8;   arm_s = 0.65;                      // arm width (2 perimeters) / flexure slot
arm_x0 = 1.0;   arm_x1 = 11.0;                     // anchor ... free end (x, each side)
bump_x = [8.2, 10.6];
groove_d = 0.3;                                    // click-groove depth in the frame
// name plate
flange = tab_pocket - 2*[insert_clr, insert_clr];  // 32.7 x 11.1
boss   = nwin - 2*[0.15, 0.15];                    // 30.7 x 8.3
F      = T - lip_t;                                // flange thickness (flush with back)

// ---------------- helpers ----------------
module rrect(s, r) {
    rr = max(r, 0.01);
    offset(r = rr) square([max(s.x - 2*rr, eps), max(s.y - 2*rr, eps)], center = true);
}
module slab(s, r, z, c = 0) {          // ultra-thin rounded rect, grown by c, at height z
    translate([0, 0, z]) linear_extrude(eps) rrect(s + 2*[c, c], r + c);
}
module prism(s, r, z0, z1) { translate([0, 0, z0]) linear_extrude(z1 - z0) rrect(s, r); }
// rounded-rect solid whose size changes linearly between z-levels (exact chamfers).
// Each segment is hulled separately so non-convex profiles (e.g. a chamfer only
// at one end of a pocket) stay exact.
module lofted(s, r, zc) {             // zc = [[z, grow], ...]
    n = len(zc);
    for (i = [0:n-2]) hull() {
        slab(s, r, zc[i][0], zc[i][1]);
        slab(s, r, zc[i+1][0] - (i == n-2 ? eps : 0), zc[i+1][1]);
    }
}

// ---------------- frame outline (body + tab), offset-able ----------------
function arc(c, r, a0, a1, n) = [for (i = [0:n]) c + r*[cos(a0 + (a1 - a0)*i/n), sin(a0 + (a1 - a0)*i/n)]];
function outline_pts(d, n = 18) =
    let(W = outer.x/2, H = outer.y/2, tw = tab_w/2)
    concat(
        arc([ tw - tab_r, tab_bot + tab_r], tab_r - d, -90,   0, n),
        arc([ tw + fil_r, -H - fil_r],      fil_r + d, 180,  90, n),   // concave fillet
        arc([ W - R_out, -H + R_out],       R_out - d, -90,   0, n),
        arc([ W - R_out,  H - R_out],       R_out - d,   0,  90, n),
        arc([-W + R_out,  H - R_out],       R_out - d,  90, 180, n),
        arc([-W + R_out, -H + R_out],       R_out - d, 180, 270, n),
        arc([-tw - fil_r, -H - fil_r],      fil_r + d,  90,   0, n),   // concave fillet
        arc([-tw + tab_r, tab_bot + tab_r], tab_r - d, 180, 270, n)
    );
module frame_outline_2d(d = 0) polygon(outline_pts(d));

// front edges: printable "teardrop" fillet (45 deg at the bed, round above)
// back edge  : quarter-round
rf = 2.0;  rb = 1.5;  rw = 1.2;  rn = 0.8;       // outer front, outer back, photo window, name window
function tear_d(z, r) = z < r*(1 - 1/sqrt(2)) ? r*(2 - sqrt(2)) - z
                                              : (z >= r ? 0 : r - sqrt(max(0, r*r - (r - z)*(r - z))));
function back_d(z)  = let(u = z - (T - rb)) u <= 0 ? 0 : rb - sqrt(max(0, rb*rb - u*u));
function edge_profile() = concat(
    [for (i = [0:24]) let(z = rf*i/24) [z, tear_d(z, rf)]],
    [for (i = [0:18]) let(z = T - rb + rb*i/18) [z, back_d(z)]]
);
// window cutter profile: rounded front edge, straight through the lip
function win_profile(r) = concat([[-0.3, tear_d(0, r) + 0.3]], [for (i = [0:12]) let(z = r*i/12) [z, tear_d(z, r)]], [[lip_t + 1, 0]]);

module loft_outline(profile) {
    rings = [for (p = profile) [for (q = outline_pts(p[1])) [q.x, q.y, p[0]]]];
    N = len(rings[0]);  L = len(rings);
    pts = [for (r = rings) each r];
    faces = concat(
        [[for (i = [0:N-1]) i]],                                   // bottom
        [[for (i = [N-1:-1:0]) (L-1)*N + i]],                      // top
        [for (l = [0:L-2], i = [0:N-1])
            let(a = l*N + i, b = l*N + (i+1)%N, c = (l+1)*N + (i+1)%N, d = (l+1)*N + i) [a, d, c]],
        [for (l = [0:L-2], i = [0:N-1])
            let(a = l*N + i, b = l*N + (i+1)%N, c = (l+1)*N + (i+1)%N) [a, c, b]]
    );
    polyhedron(pts, faces, convexity = 4);
}

// =====================================================================
//  PART 1 : FRONT FRAME  (z = 0 is the front face, printed face-down)
// =====================================================================
module frame() {
    ledge_z = T - latch_a;                         // underside of the retaining ledges
    difference() {
        loft_outline(edge_profile());
        // photo window with rounded front edge
        lofted(window, win_r, win_profile(rw));
        frame_cutters();
    }
}
// Everything a front frame needs inside (same for every frame shape): name window,
// photo + cover pocket, name-plate socket, tongue slots, latch groove, click grooves.
module frame_cutters() {
    ledge_z = T - latch_a;
    union() {
        // name window with rounded front edge
        translate([0, tp_cy, 0]) lofted(nwin, nwin_r, win_profile(rn));
        // photo + cover pocket, 0.4 mm lead-in chamfer at the back
        lofted(pocket, pocket_r, [[lip_t, 0], [T - 0.4, 0], [T + 0.5, 0.9]]);
        // name-plate socket, 0.3 mm lead-in chamfer
        translate([0, tp_cy, 0]) lofted(tab_pocket, tp_r, [[lip_t, 0], [T - 0.3, 0], [T + 0.5, 0.8]]);
        // slots for the two cover tongues (bottom)
        for (sx = [-1, 1])
            translate([sx*tongue_x - (tongue_w + 0.6)/2, -(ch/2 + tongue_e + 0.35), lip_t])
                cube([tongue_w + 0.6, tongue_e + 0.35 + 1.0, ledge_z - lip_t]);
        // groove for the snap hook (top)
        translate([-(hook_w + 0.6)/2, pocket.y/2 - 1.0, lip_t])
            cube([hook_w + 0.6, (ch/2 + hook_e + 0.2) - (pocket.y/2 - 1.0), ledge_z - lip_t]);
        // click grooves for the name-plate spring bumps (45 deg flanks, printable face-down)
        if (plate_click) for (sx = [-1, 1], sy = [-1, 1])
            translate([0, tp_cy, T - plate_bump_zc() - 0.1]) mirror([sx < 0 ? 1 : 0, 0, 0]) mirror([0, sy < 0 ? 1 : 0, 0])
                hull() {
                    translate([bump_x[0] - 1.2, tab_pocket.y/2 - 0.2, -0.65 - groove_d]) cube([bump_x[1] - bump_x[0] + 2.2, 0.2, 2*(0.65 + groove_d)]);
                    translate([bump_x[0] - 1.2, tab_pocket.y/2, -0.65]) cube([bump_x[1] - bump_x[0] + 2.2, groove_d, 1.3]);
                }
    }
}

// =====================================================================
//  PART 2 : BACK COVER   (modelled with z = 0 at the fridge side)
// =====================================================================
module latch_slot_2d() {
    ys = ch/2 - beam_b - slot_s/2;                 // slot centre-line under the beams
    xl = pad_w/2 + slot_s/2;                       // vertical legs beside the pad
    yb = ch/2 - pad_h - slot_s/2;                  // slot under the pad
    xe = pad_w/2 + beam_L;                         // beam anchors
    path = [[-xe, ys], [-xl, ys], [-xl, yb], [xl, yb], [xl, ys], [xe, ys]];
    for (i = [0:len(path) - 2]) hull() { translate(path[i]) circle(d = slot_s); translate(path[i+1]) circle(d = slot_s); }
}
module recess_2d() {
    offset(r = 1.5) offset(delta = -1.5)           // round convex corners
    offset(r = -1.5) offset(delta = 1.5)           // round concave corners
    difference() {
        rrect([cw - 6.4, ch - 6.4], 2);
        for (p = mag_pos) translate(p) circle(r = mag_pr + 1.5);
        translate([-(pad_w/2 + beam_L + 2.6), ch/2 - pad_h - slot_s - 1.6]) square([2*(pad_w/2 + beam_L + 2.6), 20]);
    }
}
module cover_zc() {
    difference() {
        union() {
            // plate: 0.4 chamfer on the fridge side, 0.3 chamfer on the photo side
            lofted([cw, ch], cr, [[0, -0.4], [0.4, 0], [cover_t - 0.3, 0], [cover_t, -0.3]]);
            // two rigid tongues (bottom edge)
            for (sx = [-1, 1]) translate([sx*tongue_x, 0, 0]) hull() {
                translate([0, -ch/2 - tongue_e/2 + 0.25, latch_a]) linear_extrude(cover_t - 0.3 - latch_a) rrect([tongue_w, tongue_e + 0.5], 0.4);
                translate([0, -ch/2 - tongue_e/2 + 0.25 + 0.15, cover_t - 0.3]) linear_extrude(0.3) rrect([tongue_w - 0.6, tongue_e + 0.2], 0.1);
            }
            // snap hook on the latch pad (top edge): flat retention face, 45 deg lead-in ramp
            hull() {
                translate([-hook_w/2, ch/2 - 0.5, latch_a]) cube([hook_w, 0.5 + hook_e, 0.2]);
                translate([-hook_w/2, ch/2 - 0.5, cover_t - eps]) cube([hook_w, 0.5, eps]);
            }
        }
        // flexure slot that frees the latch pad on two 20 mm beams
        translate([0, 0, -1]) linear_extrude(cover_t + 2) latch_slot_2d();
        // finger-nail notch on the pad (pull it toward the photo centre to open)
        translate([-4.5, ch/2 - pad_h + 1.2, -1]) cube([9, 1.8, 1 + 1.0]);
        // magnet pockets (open toward the photo, 0.4 skin toward the fridge)
        for (p = mag_pos) translate(p) {
            translate([0, 0, mag_skin]) cylinder(r = mag_pr, h = cover_t);
            translate([0, 0, cover_t - 0.3]) cylinder(r1 = mag_pr, r2 = mag_pr + 0.3, h = 0.3 + eps);
        }
        // filament-saving recess on the fridge side
        translate([0, 0, -1]) linear_extrude(1 + recess_d) recess_2d();
    }
    // magnet crush ribs (4 per pocket)
    if (mag_grip > 0) for (p = mag_pos, a = [45:90:315]) translate(p) rotate(a)
        intersection() {
            translate([0, 0, mag_skin]) cylinder(r = mag_pr + 0.1, h = cover_t - mag_skin);
            hull() {
                translate([mag_d/2 - mag_grip + 0.35, 0, mag_skin]) cylinder(r = 0.35, h = cover_t - mag_skin - 0.6, $fn = 16);
                translate([mag_pr + 0.1, 0, cover_t - 0.1]) cylinder(r = 0.05, h = 0.1, $fn = 8);
            }
        }
}
// cover in frame coordinates (photo side down)
module cover_real() translate([0, 0, T]) rotate([0, 180, 0]) cover_zc();

// =====================================================================
//  PART 3 : NAME PLATE   (z = 0 is the back face, text on top)
// =====================================================================
function is_ar(c) = let(o = ord(c)) (o >= 1536 && o <= 1791) || (o >= 1872 && o <= 1919) || (o >= 64336 && o <= 65279);
function has_ar(s) = len([for (c = s) if (is_ar(c)) 1]) > 0;
// approximate advance widths (x text size), calibrated on the default fonts and
// kept slightly generous so long text is always scaled DOWN to fit (never up)
function cwid(c) = let(o = ord(c))
      o == 32 ? 0.38
    : (o >= 48 && o <= 57) ? 0.76
    : (o >= 65 && o <= 90) ? (c == "I" ? 0.40 : (c == "M" || c == "W") ? 1.24 : 0.96)
    : (o >= 97 && o <= 122) ? ((c == "i" || c == "l" || c == "j") ? 0.38 : (c == "m" || c == "w") ? 1.12
                              : (c == "f" || c == "t" || c == "r") ? 0.56 : 0.80)
    : is_ar(c) ? 0.86
    : 0.45;
function sumw(s, i = 0) = i >= len(s) ? 0 : cwid(s[i]) + sumw(s, i + 1);

// Arabic glyphs (with dots / ascenders) are ~1.45x taller than Latin capitals at the same size
module label_2d(s, size, maxw) {
    ar = has_ar(s);
    sz = ar ? size*0.85 : size;
    k  = min(1, maxw/max(sumw(s)*sz, eps));
    if (len(s) > 0 && sz*k < 3.6)
        echo(str("WARNING: text '", s, "' is long - letters shrink to ~", round(sz*k*10)/10,
                 " mm and may print poorly with a 0.4 mm nozzle. Use fewer characters (about 10 max)."));
    if (len(s) > 0)
        scale([k, k])
            text(s, size = sz, halign = "center", valign = "center",
                 font = ar ? font_arabic : font_latin,
                 direction = ar ? "rtl" : "ltr",
                 script = ar ? "arabic" : "latin",
                 language = ar ? "ar" : "en");
}
module text_2d() {
    maxw = boss.x - 4.2;                           // keeps text inside the pill ends
    if (second_line == "") label_2d(label, text_size, maxw);
    else {
        s1 = min(text_size, 3.6);
        translate([0,  1.9]) label_2d(label, s1, maxw);
        translate([0, -2.1]) label_2d(second_line, 2.8, maxw);
    }
}
module insert() {
    top = F + lip_t;
    difference() {
        union() {
            // flange (0.3 bed chamfer against elephant foot)
            lofted(flange, tp_r - insert_clr, [[0, -0.3], [0.3, 0], [F, 0]]);
            // visible face, flush with the frame front, 0.3 chamfer
            lofted(boss, nwin_r - 0.15, [[F - eps, 0], [top - 0.5, 0], [top - 0.15, -0.12], [top, -0.5]]);
            // bumps on the 4 spring arms: they press on the socket wall and click into
            // the frame grooves. 45 deg ramps both ways -> push in from the back,
            // push out from the front.
            for (sx = [-1, 1], sy = [-1, 1]) mirror([sx < 0 ? 1 : 0, 0, 0]) mirror([0, sy < 0 ? 1 : 0, 0]) plate_bump();
            if (text_style == "raised")
                translate([0, 0, top - eps]) linear_extrude(text_depth + eps) text_2d();
        }
        // flexure slots that free the 4 spring arms (wider on the first layer: elephant-foot relief)
        for (sx = [-1, 1], sy = [-1, 1]) mirror([sx < 0 ? 1 : 0, 0, 0]) mirror([0, sy < 0 ? 1 : 0, 0]) {
            translate([0, 0, -1]) linear_extrude(1 + F + eps) arm_slot_2d();
            translate([0, 0, -1]) linear_extrude(1 + 0.2) offset(delta = 0.15) arm_slot_2d();
        }
        if (text_style == "engraved")
            translate([0, 0, top - text_depth]) linear_extrude(text_depth + 1) text_2d();
    }
}
function plate_bump_e()  = insert_clr + plate_grip;              // bump height above the flange edge
function plate_bump_zc() = F/2 + 0.05;                           // bump centre height (plate coords)
module plate_bump() {
    e = plate_bump_e();  fy = flange.y/2;
    r = max(0.6, e);                                              // ramp length -> <= 45 deg
    hull() {
        translate([bump_x[0], fy - 0.3, 0.2 + r]) cube([bump_x[1] - bump_x[0], 0.3 + e, max(0.05, F - 0.4 - 2*r)]);
        translate([bump_x[0], fy - 0.3, 0.2]) cube([bump_x[1] - bump_x[0], 0.3, F - 0.4]);
    }
}
module arm_slot_2d() {
    fy = flange.y/2;  ys = fy - arm_b - arm_s;
    translate([arm_x0, ys]) square([arm_x1 + arm_s - arm_x0, arm_s]);
    translate([arm_x1, ys]) square([arm_s, fy + 1 - ys]);
    translate([arm_x0, ys + arm_s/2]) circle(d = arm_s, $fn = 24);
}
module insert_real() translate([0, tp_cy, T]) rotate([0, 180, 0]) insert();

// =====================================================================
//  OUTPUT
// =====================================================================
if (part == "frame") frame();
else if (part == "cover") translate([0, 0, cover_t]) rotate([0, 180, 0]) cover_zc();   // photo side down
else if (part == "insert") insert();
else if (part == "cutters") frame_cutters();
else if (part == "plate") {
    frame();
    translate([0, outer.y/2 + ch/2 + 6 + 8, cover_t]) rotate([0, 180, 0]) cover_zc();
    translate([outer.x/2 + flange.y/2 + 6, -10, 0]) rotate(90) insert();
}
else if (part == "assembly") {
    color("SteelBlue") frame();
    color("LightGray") cover_real();
    color("White") insert_real();
}
else if (part == "exploded") {
    color("SteelBlue") frame();
    color("LightGray") translate([0, 0, 18]) cover_real();
    color("White") translate([0, 0, -12]) insert_real();
}
