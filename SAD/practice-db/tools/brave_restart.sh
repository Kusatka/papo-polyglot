#!/usr/bin/env bash
# Штатно закрыть Brave с профилем sad-brave-profile (через CDP) и открыть заново на адресе $1
cd "$(dirname "$0")"
node --input-type=module -e '
try { const v = await (await fetch("http://127.0.0.1:9222/json/version")).json(); const ws = new WebSocket(v.webSocketDebuggerUrl);
  ws.onopen = () => { ws.send(JSON.stringify({ id: 1, method: "Browser.close" })); setTimeout(() => process.exit(0), 1500); }; } catch { }' 2>/dev/null
sleep 3
powershell -NoProfile -ExecutionPolicy Bypass -File brave.ps1 "${1:-about:blank}"
for i in $(seq 1 20); do curl -s http://127.0.0.1:9222/json/version >/dev/null && break; sleep 1; done; sleep 3
node cdp.mjs only >/dev/null
