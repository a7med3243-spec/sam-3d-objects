#!/bin/bash
# usage: ./render.sh <part> <out.stl> [extra -D args...]
p=$1; out=$2; shift 2
start=$(date +%s)
openscad -o "$out" -D "part=\"$p\"" "$@" fridge_photo_frame.scad > "$out.log" 2>&1
rc=$?
echo "$p -> $out rc=$rc $(( $(date +%s)-start ))s"
grep -i -E "warning|error" "$out.log" | head -5
