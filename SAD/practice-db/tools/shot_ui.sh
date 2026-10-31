#!/usr/bin/env bash
# Кадр окна браузера: shot_ui.sh <часть заголовка окна> <файл.png> [x y курсора]
cd "$(dirname "$0")"
T="$(cygpath -w "$PWD")"
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '$T\hostshot.ps1' -Out '$2' -Activate '$1' -Delay 2 -Mouse ${3:-1780},${4:-1000}" >/dev/null && echo "кадр $2"
