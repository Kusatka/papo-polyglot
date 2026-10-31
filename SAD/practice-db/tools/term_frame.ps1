# Окно консоли для кадра отчёта: печатает приглашение и команду, затем настоящий вывод этой команды.
# Запуск в отдельном развёрнутом окне (см. termshot.sh):
#   powershell -NoProfile -NoExit -File term_frame.ps1 -Scenario redis [-Dir <каталог работы>]
param([Parameter(Mandatory)][string]$Scenario, [string]$Dir = 'C:\Users\sudov\Desktop\study debt autumn\SAD\practice-db\pr1')

[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = 'Windows PowerShell'
Set-Location $Dir
Clear-Host
$envs = @{}
$envFile = Join-Path $Dir '.env'; if (-not (Test-Path $envFile)) { $envFile = Join-Path $Dir '..\pr1\.env' }
Get-Content $envFile -ErrorAction SilentlyContinue | Where-Object { $_ -match '^\s*([A-Z_0-9]+)=(.*)$' } | ForEach-Object { $envs[$Matches[1]] = $Matches[2] }

function PS-Line([string]$cmd) { Write-Host -NoNewline "PS $((Get-Location).Path)> "; Write-Host $cmd }
function Run([string]$cmd) { PS-Line $cmd; Invoke-Expression $cmd | Out-Host }

function Split-Args([string]$s) {   # разбор строки команды с учётом кавычек
  $out = @()
  foreach ($x in [regex]::Matches($s, '"([^"]*)"|(\S+)')) { if ($x.Groups[1].Success) { $out += $x.Groups[1].Value } else { $out += $x.Groups[2].Value } }
  return $out
}

# Сеанс redis-cli: строка запуска, затем «приглашение + команда» и настоящий ответ (--no-raw = формат интерактивного режима)
function Redis-Session([string[]]$cmds) {
  $pw = $envs['REDIS_PASSWORD']
  PS-Line "docker exec -it practice01-redis redis-cli -a $pw"
  Write-Host "Warning: Using a password with '-a' or '-u' option on the command line interface may not be safe."
  foreach ($c in $cmds) {
    Write-Host "127.0.0.1:6379> $c"
    $a = @('exec', 'practice01-redis', 'redis-cli', '-a', $pw, '--no-auth-warning', '--no-raw') + (Split-Args $c)
    & docker @a | Out-Host
  }
  Write-Host -NoNewline '127.0.0.1:6379> '
}

# Сеанс mongosh: без TTY mongosh печатает приглашения, но не эхо ввода — вставляем команды после приглашений
function Mongo-Session([string[]]$cmds, [string]$db = '') {
  $u = $envs['MONGO_USER']; $p = $envs['MONGO_PASSWORD']
  PS-Line "docker exec -it practice01-mongodb mongosh -u $u -p $p --authenticationDatabase admin $db".TrimEnd()
  $dbArg = @(); if ($db) { $dbArg = @($db) }
  $lines = (($cmds -join "`n") + "`n") | docker exec -i practice01-mongodb mongosh -u $u -p $p --authenticationDatabase admin @dbArg 2>&1
  $i = 0; $out = New-Object System.Collections.Generic.List[string]
  foreach ($l in $lines) {
    $m = [regex]::Match([string]$l, '^(\w+)> (.*)$')
    if ($m.Success -and $i -lt $cmds.Count) { $out.Add("$($m.Groups[1].Value)> $($cmds[$i])"); $i++; if ($m.Groups[2].Value) { $out.Add($m.Groups[2].Value) } }
    else { $out.Add([string]$l) }
  }
  # на EOF mongosh печатает лишние пустые приглашения — оставляем одно
  while ($out.Count -ge 2 -and $out[$out.Count - 1] -match '^\w+>\s*$' -and $out[$out.Count - 2] -match '^\w+>\s*$') { $out.RemoveAt($out.Count - 1) }
  $last = $out[$out.Count - 1]; $out.RemoveAt($out.Count - 1)
  $out | Out-Host
  Write-Host -NoNewline ($last.TrimEnd() + ' ')
}

# Сеанс psql: приглашение «база=#» + команда, ответ psql -c (тот же табличный формат)
function Psql-Session([string[]]$cmds, [string]$db = '') {
  $u = $envs['POSTGRES_USER']; if (-not $db) { $db = $envs['POSTGRES_DB'] }
  PS-Line "docker exec -it practice01-postgres psql -U $u -d $db"
  $ver = (docker exec practice01-postgres psql -U $u -d $db -tAc 'SHOW server_version;').Trim()
  Write-Host "psql ($ver)"; Write-Host 'Type "help" for help.'; Write-Host ''
  foreach ($c in $cmds) {
    Write-Host "$db=# $c"
    docker exec practice01-postgres psql -U $u -d $db -c $c 2>&1 | Out-Host
  }
  Write-Host -NoNewline "$db=# "
}

# Сеанс произвольного CLI: строка запуска, необязательный баннер, «приглашение + команда» и ответ $exec
function Cli-Session([string]$launch, [string]$prompt, [string[]]$cmds, [scriptblock]$exec, [string]$banner = '', [string]$quit = '') {
  PS-Line $launch
  if ($banner) { Write-Host $banner }
  foreach ($c in $cmds) { Write-Host "$prompt$c"; & $exec $c | Out-Host }
  if ($quit) { Write-Host "$prompt$quit" } else { Write-Host -NoNewline $prompt }
}

# Сценарии кадров. Сценарии других работ — в файлах term_<имя>.ps1 или term_<prN>.ps1 рядом (подключаются точкой).
$extra = Join-Path $PSScriptRoot "term_$Scenario.ps1"
if (-not (Test-Path $extra) -and $Scenario -match '^(pr\d|lab\d)') { $extra = Join-Path $PSScriptRoot "term_$($Matches[1]).ps1" }
if (Test-Path $extra) { . $extra }
else {
  switch ($Scenario) {
    'ps' {
      Run 'docker compose ps --format "table {{.Name}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"'
      Write-Host ''
      Run 'docker volume ls --filter name=practice01'
      Write-Host ''
      return   # дальше настоящее приглашение PowerShell (-NoExit)
    }
    'redis' { Redis-Session @('PING', 'CONFIG GET dir', 'CONFIG GET appendonly', 'CONFIG GET logfile', 'SET mykey "Hello, Redis!"', 'GET mykey', 'HGETALL user:1', 'DBSIZE') }
    'mongo' { Mongo-Session @('db.version()', 'db.adminCommand({getCmdLineOpts: 1}).parsed', 'use practice_db', 'db.students.find({}, {_id: 0, name: 1, group: 1})') }
    'psql'  { Psql-Session @('SELECT version();', 'SHOW data_directory;', 'SHOW log_directory;', 'SHOW logging_collector;', 'SELECT * FROM pr1_students;') }
  }
}
# сеанс CLI «открыт»: окно ждёт, пока его не закроют после съёмки (иначе появится приглашение PowerShell)
if ($Scenario -ne 'ps' -and -not $global:KeepPrompt) { [Console]::CursorVisible = $true; while ($true) { Start-Sleep 60 } }
