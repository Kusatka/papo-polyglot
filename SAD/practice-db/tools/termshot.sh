#!/usr/bin/env bash
# Кадр консоли: termshot.sh <сценарий term_frame.ps1> <файл.png> [секунд ожидания] [каталог работы]
cd "$(dirname "$0")"
T="$(cygpath -w "$PWD")"
DIR="${4:-C:\Users\sudov\Desktop\study debt autumn\SAD\practice-db\pr1}"
PID=$(powershell -NoProfile -Command "(Start-Process powershell -WindowStyle Maximized -PassThru -ArgumentList '-NoProfile','-NoExit','-ExecutionPolicy','Bypass','-File','\"$T\term_frame.ps1\"','-Scenario','$1','-Dir','\"$DIR\"').Id" | tr -d '\r')
sleep "${3:-12}"
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '$T\hostshot.ps1' -Out '$2' -Activate 'Windows PowerShell' -Delay 2 -Mouse 1910,1000" >/dev/null
powershell -NoProfile -Command "Stop-Process -Id $PID -Force -ErrorAction SilentlyContinue"
echo "кадр $2 (окно $PID закрыто)"
