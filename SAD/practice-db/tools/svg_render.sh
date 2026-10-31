#!/usr/bin/env bash
# Рендер SVG-диаграмм (*.html с одним <svg>) в PNG через Brave: tools/svg_render.sh <каталог> [имя ...]
cd "$(dirname "$0")/.."
DIR="$1"; shift
names=("$@"); [ ${#names[@]} -eq 0 ] && names=($(ls "$DIR"/*.html | xargs -n1 basename | sed 's/\.html$//'))
for name in "${names[@]}"; do
  url="file:///$(cygpath -m "$PWD/$DIR/$name.html" | sed 's/ /%20/g')"
  node tools/cdp.mjs nav "$url" >/dev/null
  node tools/cdp.mjs wait "svg" 10000 >/dev/null || { echo "не отрисовалось: $name"; continue; }
  node tools/cdp.mjs svgpng "svg" "$(cygpath -w "$PWD/$DIR/$name.png")" 2
done
