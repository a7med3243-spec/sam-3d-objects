"""Slice every printed part with PrusaSlicer and add up filament weight and print time.

Settings (common for PLA, 0.4 mm nozzle): 0.2 mm layers, 3 perimeters, 5 top / 4 bottom
layers, 15 % gyroid infill, PLA density 1.24 g/cm3, no supports, no brim.
Usage: python3 measure_weight.py [small|30cm ...]   (needs prusa-slicer on PATH)
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = """layer_height = 0.2
first_layer_height = 0.2
perimeters = 3
top_solid_layers = 5
bottom_solid_layers = 4
fill_density = 15%
fill_pattern = gyroid
nozzle_diameter = 0.4
filament_diameter = 1.75
filament_density = 1.24
bed_shape = 0x0,220x0,220x220,0x220
max_print_height = 250
support_material = 0
skirts = 0
brim_width = 0
gcode_flavor = marlin2
"""
# part -> (how many to print, colour)
PARTS = {
    "small": {"board.stl": (1, "walnut"), "shelf.stl": (1, "walnut"),
              "panel_white_with_verse.stl": (1, "white+dark"), "mmu_verse_dark.stl": (0, "dark"),
              "knob.stl": (5, "brass")},
    "30cm": {"main_brown_board_shelf_knobs.stl": (1, "walnut"),
             "panel_white_with_verse.stl": (1, "white+dark"), "mmu_verse_dark.stl": (0, "dark")},
}


BEDS = {"30cm": (330, 320, 325)}   # Bambu Lab A2L; other sizes use the 220 mm bed above
STRONG = {"30cm"}                  # sliced with 4 walls and 25 % infill


def config_for(size):
    if size not in BEDS:
        return CONFIG, "110,110"
    x, y, z = BEDS[size]
    cfg = CONFIG.replace("bed_shape = 0x0,220x0,220x220,0x220", f"bed_shape = 0x0,{x}x0,{x}x{y},0x{y}")
    cfg = cfg.replace("max_print_height = 250", f"max_print_height = {z}")
    if size in STRONG:
        # load-bearing piece: more walls and infill (shelf and knobs carry weight)
        cfg = (cfg.replace("perimeters = 3", "perimeters = 4").replace("fill_density = 15%", "fill_density = 25%")
               .replace("bottom_solid_layers = 4", "bottom_solid_layers = 5"))
    return cfg, f"{x / 2:g},{y / 2:g}"


def slice_part(stl, workdir, size="small"):
    ini = os.path.join(workdir, "pla.ini")
    cfg, centre = config_for(size)
    with open(ini, "w") as f:
        f.write(cfg)
    out = os.path.join(workdir, os.path.basename(stl) + ".gcode")
    subprocess.run(["prusa-slicer", "--export-gcode", "--load", ini, "--center", centre,
                    "--output", out, stl], check=True, capture_output=True, timeout=1800)
    txt = open(out, errors="ignore").read()
    grams = float(re.search(r"; total filament used \[g\] = ([\d.]+)", txt).group(1))
    t = re.search(r"; estimated printing time \(normal mode\) = (.+)", txt).group(1).strip()
    os.remove(out)
    return grams, t


def to_minutes(t):
    mins = 0.0
    for v, u in re.findall(r"(\d+)([dhms])", t):
        mins += int(v) * {"d": 1440, "h": 60, "m": 1, "s": 1 / 60}[u]
    return mins


def measure(size):
    stl_dir = os.path.join(HERE, size, "stl")
    rows, total_g, total_min, by_colour = [], 0.0, 0.0, {}
    with tempfile.TemporaryDirectory() as wd:
        for name, (n, colour) in PARTS[size].items():
            g, t = slice_part(os.path.join(stl_dir, name), wd, size)
            rows.append({"part": name, "count": n, "grams_each": g, "time_each": t})
            if n:
                total_g += g * n
                total_min += to_minutes(t) * n
                by_colour[colour] = by_colour.get(colour, 0.0) + g * n
    dark = sum(r["grams_each"] for r in rows if r["part"].startswith("mmu_verse"))
    by_colour["dark (part of white+dark)"] = dark
    res = {"size": size, "settings": "0.2 mm layers, 3 walls, 15% gyroid, PLA 1.24 g/cm3",
           "parts": rows, "total_grams": round(total_g, 1),
           "total_print_hours": round(total_min / 60, 1),
           "by_colour_grams": {k: round(v, 1) for k, v in by_colour.items()}}
    with open(os.path.join(HERE, size, "weight.json"), "w") as f:
        json.dump(res, f, indent=1)
    return res


if __name__ == "__main__":
    for s in sys.argv[1:] or ["small", "30cm"]:
        print(json.dumps(measure(s), indent=1))
