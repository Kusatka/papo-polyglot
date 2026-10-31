# Кадры ЛР №1 (подключается точкой из term_frame.ps1; рабочий каталог — lab1). Протокол тестирования:
# каждая команда печатается после приглашения и выполняется, вывод под ней — настоящий.
Get-Content (Join-Path $Dir '..\pr1\.env') | Where-Object { $_ -match '^\s*([A-Z_0-9]+)=(.*)$' } |
  ForEach-Object { if (-not $envs.ContainsKey($Matches[1])) { $envs[$Matches[1]] = $Matches[2] } }
$env:PYTHONIOENCODING = 'utf-8'
$pw = $envs['REDIS_PASSWORD']; $pgu = $envs['POSTGRES_USER']

# команда выполняется в области сценария (точкой), чтобы переменные из одной строки были видны в следующих;
# у docker logs журнал приложения идёт в stderr — выводим его как текст, без обёртки ошибок PowerShell
$X = { param([string]$__cmd)
  PS-Line $__cmd
  if ($__cmd -match '^\s*#') { return }
  if ($__cmd -match '^docker logs') { Invoke-Expression ($__cmd + ' 2>&1 | ForEach-Object { "$_" }') | Out-Host }
  else { Invoke-Expression $__cmd | Out-Host }
}
# сеанс psql, в котором \set задаёт переменные для следующих запросов (каждый запрос — отдельный вызов psql
# с теми же \set впереди: результат тот же, что в одном интерактивном сеансе)
function Pg-Vars([string]$db, [string[]]$cmds) {
  PS-Line "docker exec -it practice01-postgres psql -U $pgu -d $db"
  $ver = (docker exec practice01-postgres psql -U $pgu -d $db -tAc 'SHOW server_version;').Trim()
  Write-Host "psql ($ver)"; Write-Host 'Type "help" for help.'; Write-Host ''
  $pre = @()
  foreach ($c in $cmds) {
    Write-Host "$db=# $c"
    if ($c -like '\set *') { $pre += $c; continue }
    if ($c -like '\pset *') { $c | docker exec -i practice01-postgres psql -U $pgu -d $db | Out-Host; $pre += $c; continue }
    (($pre + $c) -join "`n") | docker exec -i practice01-postgres psql -q -U $pgu -d $db 2>&1 | ForEach-Object { "$_" } | Out-Host
  }
  Write-Host -NoNewline "$db=# "
}
$login = @'
$tok = (Invoke-RestMethod -Method Post "$B/auth/login" -Body @{username = 'teacher'; password = 'teacher-pass'}).access_token
'@
$report = @'
$r = Invoke-RestMethod "$B/api/lab1/report?term=масштабирование&date_from=2026-02-09&date_to=2026-04-19&trace=true" -Headers @{Authorization = "Bearer $tok"}
'@

switch ($Scenario) {
  'lab1ps' {
    . $X '# Контейнеры ЛР №1: шлюз и сервис из одного образа, сервис наружу не опубликован'
    . $X 'docker compose ps --format "table {{.Name}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"'
    . $X 'docker image ls papo-lab'
    . $X '# Общая сеть со стендом ПР №1 (хранилища доступны по именам служб)'
    . $X 'docker network inspect practice01_default --format "{{range .Containers}}{{.Name}}  {{.IPv4Address}}{{println}}{{end}}"'
    . $X 'curl.exe -s http://localhost:8000/health'
    . $X '# Порт сервиса ЛР №1 (8001) с хоста недоступен: вызов только через шлюз'
    . $X '(Test-NetConnection localhost -Port 8001 -WarningAction SilentlyContinue).TcpTestSucceeded'
    $global:KeepPrompt = $true
  }
  'lab1auth' {
    . $X '$B = "http://localhost:8000"'
    . $X '# 1. Вызов метода без токена'
    . $X 'curl.exe -s -w "  [HTTP %{http_code}]`n" "$B/api/lab1/report?term=Kafka&date_from=2026-02-09&date_to=2026-04-19"'
    . $X '# 2. Вход с неверным паролем'
    . $X 'curl.exe -s -w "  [HTTP %{http_code}]`n" -d "username=teacher&password=wrong" "$B/auth/login"'
    . $X '# 3. Вход с верным паролем: шлюз выдаёт JWT (HS256, срок действия 60 мин)'
    . $X '$login = curl.exe -s -d "username=teacher&password=teacher-pass" "$B/auth/login" | ConvertFrom-Json'
    . $X '$login | Format-List'
    . $X '# 4. Полезная нагрузка токена, проверенного шлюзом'
    . $X 'curl.exe -s -w "  [HTTP %{http_code}]`n" -H "Authorization: Bearer $($login.access_token)" "$B/auth/me"'
    . $X '# 5. Тот же вызов метода ЛР №1 с токеном'
    . $X 'curl.exe -s -o NUL -w "HTTP %{http_code}, %{size_download} bytes, %{time_total} s`n" -H "Authorization: Bearer $($login.access_token)" "$B/api/lab1/report?term=Kafka&date_from=2026-02-09&date_to=2026-04-19"'
    . $X '# 6. Второй пользователь шлюза (роль student)'
    . $X 'curl.exe -s -w "  [HTTP %{http_code}]`n" -d "username=student&password=student-pass" "$B/auth/login"'
    $global:KeepPrompt = $true
  }
  'lab1auth2' {
    . $X '$B = "http://localhost:8000"'
    . $X '# 7. Токен, подписанный чужим ключом (подделка подписи и роли)'
    . $X @'
$fake = docker exec api-gateway python -c "import jwt, time; print(jwt.encode({'sub': 'admin', 'role': 'admin', 'iss': 'papo-gateway', 'exp': int(time.time()) + 600}, 'attacker-key-0123456789-0123456789-abcdef'))"
'@
    . $X 'curl.exe -s -w "  [HTTP %{http_code}]`n" -H "Authorization: Bearer $fake" "$B/auth/me"'
    . $X '# 8. Токен с истёкшим сроком (exp в прошлом), подписанный верным ключом'
    . $X @'
$old = docker exec api-gateway python -c "from app.common.security import *; print(jwt.encode({'sub': 'teacher', 'role': 'teacher', 'iss': ISSUER, 'exp': int(time.time()) - 60}, SECRET, algorithm=ALGORITHM))"
'@
    . $X 'curl.exe -s -w "  [HTTP %{http_code}]`n" -H "Authorization: Bearer $old" "$B/auth/me"'
    . $X '# 9. Обход шлюза: прямой вызов сервиса ЛР №1 внутри сети Docker без токена и с поддельным токеном'
    . $X @'
docker exec api-gateway python -c "import httpx; r = httpx.get('http://lab1:8001/report', params={'term': 'Kafka', 'date_from': '2026-02-09', 'date_to': '2026-04-19'}); print(r.status_code, r.text)"
'@
    . $X @'
docker exec api-gateway python -c "import httpx, sys; r = httpx.get('http://lab1:8001/report', params={'term': 'Kafka', 'date_from': '2026-02-09', 'date_to': '2026-04-19'}, headers={'Authorization': 'Bearer ' + sys.argv[1]}); print(r.status_code, r.text)" $fake
'@
    $global:KeepPrompt = $true
  }
  'lab1run' {
    . $X '$B = "http://localhost:8000"'
    . $X $login
    . $X $report
    . $X '$r | Format-List term, period, lectures_found, scope, requested_by'
    . $X '# Термин в занятиях курсов (Elasticsearch, фрагмент текста лекции с подсветкой)'
    . $X '$r.term_in_courses | ForEach-Object { $c = $_; $c.examples | ForEach-Object { [pscustomobject]@{Специальность = $c.specialty; Курс = $c.course; Лекций = $c.lectures; Лекция = $_.title; Фрагмент = $_.fragment} } } | Format-Table -AutoSize'
    . $X '# Последовательность исполнения запроса (трассировка сервиса)'
    . $X '$r.trace | Format-List step, store, action, result, ms'
    $global:KeepPrompt = $true
  }
  'lab1top' {
    . $X '$B = "http://localhost:8000"'
    . $X $login
    . $X $report
    . $X '# Отчёт: 10 студентов с минимальным процентом посещения лекций с термином «масштабирование» за 2026-02-09 … 2026-04-19'
    . $X '$r.students | Format-Table @{n = "№"; e = {$_.rank}}, @{n = "Зачётка"; e = {$_.student.student_card_number}}, @{n = "ФИО"; e = {$_.student.full_name}}, @{n = "Группа"; e = {$_.student.group}}, @{n = "Специальность"; e = {$_.student.specialty}}, @{n = "E-mail"; e = {$_.student.email}}, @{n = "Телефон"; e = {$_.student.phone}}, @{n = "Зачислен"; e = {$_.student.enrollment_date}}, @{n = "Статус"; e = {$_.student.status}} -AutoSize'
    . $X '$r.students | Format-Table @{n = "№"; e = {$_.rank}}, @{n = "ФИО"; e = {$_.student.full_name}}, @{n = "Посещено"; e = {$_.attended}}, @{n = "Всего лекций"; e = {$_.total}}, @{n = "% посещения"; e = {$_.attendance_pct}}, @{n = "Период"; e = {"$($r.period.from) … $($r.period.to)"}}, @{n = "Термин в занятиях курса"; e = {"«$($r.term)»: " + ($_.term_in_courses -join "; ")}} -AutoSize'
    $global:KeepPrompt = $true
  }
  'lab1es' {
    . $X '# Шаг 1 отдельно: тот же запрос к индексу lectures напрямую в Elasticsearch'
    . $X 'Get-Content queries\step1_es.json -Encoding UTF8'
    . $X '$es = curl.exe -s -H "Content-Type: application/json" --data-binary "@queries/step1_es.json" "http://localhost:9200/lectures/_search" | ConvertFrom-Json'
    . $X '"найдено лекций: $($es.hits.total.value), за $($es.took) мс"'
    . $X '$es.hits.hits._source | Format-Table specialty_code, course_name, order_number, title, lecture_id -AutoSize'
    $global:KeepPrompt = $true
  }
  'lab1pg' {
    # идентификаторы лекций из шага 1 (Elasticsearch) — подставляются в \set, как их передаёт сервис
    $body = Get-Content (Join-Path $Dir 'queries\step1_es.json') -Raw -Encoding UTF8
    $hits = (Invoke-RestMethod -Method Post 'http://localhost:9200/lectures/_search' -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($body))).hits.hits
    $ids = '{' + (($hits | ForEach-Object { $_._source.lecture_id }) -join ',') + '}'
    $cond = "WHERE s.lecture_id = ANY(:'ids'::uuid[]) AND a.week_start_date BETWEEN :'d1' AND :'d2' AND s.scheduled_date BETWEEN :'d1' AND :'d2'"
    Pg-Vars 'university_system' @("\set ids '$ids'", "\set d1 '2026-02-09'", "\set d2 '2026-04-19'",
      "SELECT count(DISTINCT s.id) AS classes, count(*) AS marks, count(DISTINCT a.student_id) AS students FROM attendance a JOIN schedule s ON s.id = a.schedule_id $cond;",
      '\pset tuples_only on',
      "EXPLAIN (COSTS OFF) SELECT a.student_id, count(*) FILTER (WHERE a.is_present) AS attended, count(*) AS total FROM attendance a JOIN schedule s ON s.id = a.schedule_id $cond GROUP BY a.student_id;")
  }
  'lab1redis' {
    $ids = docker exec practice01-postgres psql -U $pgu -d university_system -tAc "SELECT id FROM students WHERE student_card_number IN ('23Б0420', '23Б0315', '23Б0307') ORDER BY student_card_number DESC;"
    $keys = ($ids | Where-Object { $_ } | ForEach-Object { "student:$($_.Trim())" }) -join ' '
    $first = ($keys -split ' ')[0]
    . $X '$B = "http://localhost:8000"'
    . $X $login
    . $X '$q = "$B/api/lab1/report?term=масштабирование&date_from=2026-02-09&date_to=2026-04-19&trace=true"'
    . $X '# Шаг 3: карточки студентов в Redis (база 2). Удаляем карточки трёх первых студентов отчёта — как после истечения TTL'
    . $X "docker exec practice01-redis redis-cli -a $pw --no-auth-warning -n 2 DEL $keys"
    . $X '# Первый вызов: 3 промаха, карточки читаются из PostgreSQL и снова кладутся в кэш'
    . $X '(Invoke-RestMethod $q -Headers @{Authorization = "Bearer $tok"}).trace[2] | Format-List store, action, result, ms'
    . $X '# Повторный вызов: все карточки из кэша'
    . $X '(Invoke-RestMethod $q -Headers @{Authorization = "Bearer $tok"}).trace[2] | Format-List store, result, ms'
    . $X "docker exec practice01-redis redis-cli -a $pw --no-auth-warning -n 2 HGETALL $first"
    . $X "docker exec practice01-redis redis-cli -a $pw --no-auth-warning -n 2 TTL $first"
    $global:KeepPrompt = $true
  }
  'lab1verify' {
    . $X '# Независимая сверка: топ-10 сервиса и пересчёт другим SQL-запросом напрямую в PostgreSQL'
    . $X 'python tests\verify.py масштабирование 2026-02-09 2026-04-19'
    . $X 'python tests\verify.py "очередь сообщений" 2026-03-02 2026-05-31'
    $global:KeepPrompt = $true
  }
  'lab1logs' {
    . $X '$B = "http://localhost:8000"'
    . $X $login
    . $X $report
    . $X '# Журналы контейнеров за последние 15 с: шлюз (вход, маршрутизация вызова) и сервис ЛР №1 (шаги выборки)'
    . $X 'docker logs --since 15s api-gateway'
    . $X 'docker logs --since 15s lab1-service'
    $global:KeepPrompt = $true
  }
  'lab1neg' {
    . $X '$B = "http://localhost:8000"'
    . $X $login
    . $X '# Начало периода позже конца → 422'
    . $X 'curl.exe -s -w "  [HTTP %{http_code}]`n" -H "Authorization: Bearer $tok" "$B/api/lab1/report?term=Kafka&date_from=2026-04-19&date_to=2026-02-09"'
    . $X '# Термин короче 2 символов → 422 (проверка параметров на шлюзе)'
    . $X 'curl.exe -s -w "  [HTTP %{http_code}]`n" -H "Authorization: Bearer $tok" "$B/api/lab1/report?term=K&date_from=2026-02-09&date_to=2026-04-19"'
    . $X '# Фраза в другой словоформе: «очереди сообщений» находит «Очередь сообщений» (русский анализатор), limit = 3'
    . $X '$p = Invoke-RestMethod "$B/api/lab1/report?term=очереди сообщений&date_from=2026-03-02&date_to=2026-05-31&limit=3" -Headers @{Authorization = "Bearer $tok"}'
    . $X '$p.term_in_courses.examples | Format-Table title, fragment -AutoSize'
    . $X '$p.students | Format-Table rank, @{n = "ФИО"; e = {$_.student.full_name}}, @{n = "Группа"; e = {$_.student.group}}, attended, total, attendance_pct -AutoSize'
    . $X '# Термина нет ни в одной лекции → пустой отчёт, PostgreSQL и Redis не вызываются'
    . $X '$e = Invoke-RestMethod "$B/api/lab1/report?term=горизонтальное масштабирование&date_from=2026-02-09&date_to=2026-05-31&trace=true" -Headers @{Authorization = "Bearer $tok"}'
    . $X '$e.trace | Format-Table step, store, result -AutoSize'
    $global:KeepPrompt = $true
  }
}
