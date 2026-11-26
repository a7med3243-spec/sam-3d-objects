import json, sys, os
sp = os.path.dirname(os.path.abspath(__file__))
tpl = open(os.path.join(sp, "template.html"), encoding="utf-8").read()
geo = open(os.path.join(sp, "geo.json")).read()
core = open(os.path.join(sp, "core.js"), encoding="utf-8").read()
out = tpl.replace("/*GEO*/", geo).replace("/*CORE*/", core.replace("</script", "<\\/script"))
dst = sys.argv[1]; open(dst, "w", encoding="utf-8").write(out)
if len(sys.argv) > 2:   # local test copy: wrap in a document + load libraries from node_modules
    loc = out.replace("https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js", "/node_modules/three/build/three.min.js") \
             .replace("https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js", "/node_modules/three/examples/js/controls/OrbitControls.js") \
             .replace("https://cdn.jsdelivr.net/npm/d3-array@3.2.4/dist/d3-array.min.js", "/node_modules/d3-array/dist/d3-array.min.js") \
             .replace("https://cdn.jsdelivr.net/npm/d3-contour@4.0.2/dist/d3-contour.min.js", "/node_modules/d3-contour/dist/d3-contour.min.js")
    loc = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
           '<style>:root{color-scheme:light;padding:env(safe-area-inset-top,0px) 0 env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui}img{max-width:100%}[hidden]{display:none!important}</style></head><body>'
           + loc + '</body></html>')
    open(sys.argv[2], "w", encoding="utf-8").write(loc)
print(dst, len(out) // 1024, "KB")
