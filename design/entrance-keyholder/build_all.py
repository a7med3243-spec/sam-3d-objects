"""Build all designs: print-ready STLs, assembled parts and report.json for each."""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for d in ("01-mihrab", "02-floating-shelf", "03-horizon-moon", "04-fluted-arch", "05-walnut-board"):
    print("==", d)
    sys.argv = [os.path.join(HERE, d, "build.py")]
    runpy.run_path(sys.argv[0], run_name="__main__")
