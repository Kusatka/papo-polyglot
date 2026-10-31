# Развёртывание стенда ПР №1–3 и ЛР №1 на новом компьютере одной командой.
# Нужны: Docker Desktop (запущен, «Engine running»), Git for Windows (Git Bash), Python 3.11+.
# Запуск из папки SAD в обычном PowerShell (права администратора не нужны):
#   powershell -ExecutionPolicy Bypass -File .\deploy_laptop.ps1          весь стенд (нужно 16 ГБ ОЗУ)
#   powershell -ExecutionPolicy Bypass -File .\deploy_laptop.ps1 -Lean    только Redis, PostgreSQL, Elasticsearch + ЛР №1 (8 ГБ)
# Первый запуск скачивает образы (около 3 ГБ) и пакеты Python для шлюза. Повторный запуск безопасен:
# данные ПР №3 пересоздаются теми же (генерация детерминированная).
param([switch]$Lean)
$ErrorActionPreference = 'Continue'   # ошибки внешних команд проверяются по коду возврата
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'
$root = Join-Path $PSScriptRoot 'practice-db'
# Git Bash: рядом с git.exe из PATH (…\Git\cmd\git.exe → …\Git\bin\bash.exe) или в стандартных местах установки
$gitCmd = Get-Command git -ErrorAction SilentlyContinue
$bash = @($(if ($gitCmd) { Join-Path (Split-Path (Split-Path $gitCmd.Source)) 'bin\bash.exe' }),
          "$env:ProgramFiles\Git\bin\bash.exe", "$env:LOCALAPPDATA\Programs\Git\bin\bash.exe") |
        Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $bash) { $bash = "$env:ProgramFiles\Git\bin\bash.exe" }
$t0 = Get-Date

function Step([string]$text) { Write-Host "`n== $text" -ForegroundColor Cyan }
function Fail([string]$text) { Write-Host "ОШИБКА: $text" -ForegroundColor Red; exit 1 }
function Bash([string]$dir, [string]$cmd) {
  # bash наследует текущий каталог; без -l, иначе профиль Git Bash перейдёт в домашний каталог
  Push-Location $dir
  try { & $bash -c $cmd; if ($LASTEXITCODE -ne 0) { Fail "в $dir команда '$cmd' завершилась с кодом $LASTEXITCODE" } }
  finally { Pop-Location }
}
function Wait-Healthy([string]$dir, [int]$timeoutSec = 600) {
  $start = Get-Date
  while (((Get-Date) - $start).TotalSeconds -lt $timeoutSec) {
    Push-Location $dir; $rows = @(docker compose ps --format '{{.Name}} {{.Status}}'); Pop-Location
    $bad = @($rows | Where-Object { $_ -match 'starting|unhealthy|Restarting|Exited' })
    if ($rows.Count -gt 0 -and $bad.Count -eq 0) { $rows | ForEach-Object { "   $_" }; return }
    Write-Host "   ждём готовности: $($bad -join '; ')"
    Start-Sleep 10
  }
  Fail "службы в $dir не стали healthy за $timeoutSec с: $($bad -join '; ')"
}

Step 'Проверка программ'
$v = docker version --format '{{.Server.Version}}' 2>$null
if ($LASTEXITCODE -ne 0 -or -not $v) { Fail 'Docker Desktop не запущен. Запусти его и дождись «Engine running».' }
Write-Host "   Docker Engine $v"
if (-not (Test-Path $bash)) { Fail "нет Git Bash ($bash). Установи: winget install -e --id Git.Git" }
Write-Host "   $(& $bash --version | Select-Object -First 1)"
$py = (python --version) 2>&1
if ("$py" -notmatch 'Python 3\.(1[1-9]|[2-9]\d)') { Fail "нужен Python 3.11+ в PATH, сейчас: $py" }
Write-Host "   $py"

Step 'Стенд ПР №1: запуск контейнеров (первый раз — скачивание образов)'
Push-Location (Join-Path $root 'pr1')
if ($Lean) { docker compose up -d redis postgres elasticsearch } else { docker compose up -d }
if ($LASTEXITCODE -ne 0) { Fail 'docker compose up в pr1' }
Pop-Location
Wait-Healthy (Join-Path $root 'pr1')

Step 'Данные ПР №1 и ПР №3'
if ($Lean) {
  foreach ($s in 'pg', 'redis', 'es') { Bash (Join-Path $root 'pr3') "./load_all.sh $s" }
} else {
  Bash (Join-Path $root 'pr1') './check.sh'
  Bash (Join-Path $root 'pr3') './load_all.sh'
}

Step 'ЛР №1: сборка образа и запуск шлюза и сервиса'
Push-Location (Join-Path $root 'lab1')
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { Fail 'docker compose up --build в lab1' }
Pop-Location
Wait-Healthy (Join-Path $root 'lab1')

Step 'Проверка ЛР №1: отчёт сервиса против прямого SQL'
Push-Location (Join-Path $root 'lab1')
python -P tests\verify.py масштабирование 2026-02-09 2026-04-19
$ok = $LASTEXITCODE -eq 0
Pop-Location
if (-not $ok) { Fail 'сверка ЛР №1 не прошла' }

Step "Готово за $([int]((Get-Date) - $t0).TotalMinutes) мин"
Write-Host @"
   Swagger UI шлюза ЛР №1 : http://localhost:8000/docs   (Authorize: teacher / teacher-pass)
   Kibana                 : http://localhost:5601
   Neo4j Browser          : http://localhost:7474         (neo4j / mysecretpassword)
   Redis Commander        : http://localhost:8081
   Mongo Express          : http://localhost:8082         (admin / admin)
   pgAdmin                : http://localhost:8083         (admin@example.com / admin)
   Сценарии показа        : pr1\ЗАЩИТА_ПР1.md, pr2\ЗАЩИТА_ПР2.md, pr3\ЗАЩИТА_ПР3.md, lab1\ЗАЩИТА_ЛР1.md
   Остановить всё         : docker compose stop  (в practice-db\lab1, затем в practice-db\pr1)
"@
