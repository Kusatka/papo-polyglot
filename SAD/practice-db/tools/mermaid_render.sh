#!/usr/bin/env bash
# Рендер диаграмм Mermaid (*.mmd) в PNG через Brave: tools/mermaid_render.sh <каталог с .mmd>
cd "$(dirname "$0")/.."
DIR="$1"
for f in "$DIR"/*.mmd; do
  name=$(basename "$f" .mmd)
  node -e '
const fs=require("fs");const src=fs.readFileSync(process.argv[1],"utf8");
const html=`<!doctype html><html><head><meta charset="utf-8"><style>body{margin:16px;background:#fff} #d .nodeLabel, #d .label div, #d foreignObject div {white-space:nowrap !important; max-width:none !important}</style></head><body>
<div id="d"></div><script type="module">
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.esm.min.mjs";
mermaid.initialize({startOnLoad:false, theme:"neutral", securityLevel:"loose", fontFamily:"Arial",
  themeVariables:{fontSize:"15px"}, er:{useMaxWidth:false, fontSize:14}, flowchart:{useMaxWidth:false, htmlLabels:true, padding:12, wrappingWidth:600}, markdownAutoWrap:false});
const {svg} = await mermaid.render("g", ${JSON.stringify(src)});
document.getElementById("d").innerHTML = svg; document.body.dataset.done = "1";
</script></body></html>`;
fs.writeFileSync(process.argv[2],html);' "$f" "$DIR/$name.html"
  url="file:///$(cygpath -m "$PWD/$DIR/$name.html" | sed 's/ /%20/g')"
  node tools/cdp.mjs nav "$url" >/dev/null
  node tools/cdp.mjs wait "body[data-done] svg" 30000 >/dev/null || { echo "не отрисовалось: $name"; continue; }
  node tools/cdp.mjs shotel "#d svg" "$(cygpath -w "$PWD/$DIR/$name.png")" 2
done
