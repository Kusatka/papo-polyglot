# Кадры самостоятельных заданий ПР №1 (подключается точкой из term_frame.ps1; рабочий каталог — pr1).
# Каждая команда печатается после приглашения и выполняется; вывод под ней — настоящий.
$env:PYTHONIOENCODING = 'utf-8'
$pw = $envs['REDIS_PASSWORD']; $neo = $envs['NEO4J_PASSWORD']

# команда выполняется в области сценария (точкой), чтобы переменные одной строки были видны в следующих;
# у docker logs вывод сервера идёт в stderr — показываем его как текст, без обёртки ошибок PowerShell
$X = { param([string]$__cmd)
  PS-Line $__cmd
  if ($__cmd -match '^\s*#') { return }
  if ($__cmd -match '^docker logs') {
    $__p = $__cmd -split '\|', 2
    $__a = $__p[0] + ' 2>&1 | ForEach-Object { "$_" }'
    if ($__p.Count -gt 1) { $__a += ' |' + $__p[1] }
    Invoke-Expression $__a | Out-Host
  } else { Invoke-Expression $__cmd | Out-Host }
}
function Neo([string]$q) {
  PS-Line "docker exec practice01-neo4j cypher-shell -u neo4j -p $neo `"$q`""
  & docker exec practice01-neo4j cypher-shell -u neo4j -p $neo $q 2>&1 | ForEach-Object { "$_" } | Out-Host
}
function Es([string]$method, [string]$url, [string]$file = '', [string]$type = 'application/json') {
  $show = "curl.exe -s -X $method `"$url`""
  if ($file) { $show += " -H `"Content-Type: $type`" --data-binary `"@$file`"" }
  PS-Line $show
  if ($file) { & curl.exe -s -X $method $url -H "Content-Type: $type" --data-binary "@$file" | Out-Host }
  else { & curl.exe -s -X $method $url | Out-Host }
  Write-Host ''
}

switch ($Scenario) {
  'pr1sw_pw' {      # 1. смена паролей
    . $X '# Задание 1. Новые пароли из selfwork\new_passwords.env во всех конфигурациях стенда и шлюза ЛР №1'
    . $X 'python -P selfwork\rotate_passwords.py new'
    . $X 'Select-String -Path .env, ..\lab1\.env -Pattern "PASSWORD=|PG_DSN|REDIS_URL" | ForEach-Object { "$(Split-Path (Split-Path $_.Path) -Leaf)/$($_.Filename): $($_.Line)" }'
    $global:KeepPrompt = $true
  }
  'pr1sw_pwback' {  # 1. возврат паролей методички
    . $X '# Возврат паролей методички: их используют скрипты ПР №2–3 и шлюз ЛР №1'
    . $X 'python -P selfwork\rotate_passwords.py original'
    $global:KeepPrompt = $true
  }
  'pr1sw_init' {    # 2. скрипт инициализации PostgreSQL
    . $X '# Задание 2. Скрипты /docker-entrypoint-initdb.d выполняются при первом запуске контейнера на пустом томе'
    . $X 'docker compose --progress plain -f selfwork\docker-compose.initdb.yml up -d --wait'
    . $X 'docker logs practice01-postgres-init | Select-String "initdb.d|CREATE|INSERT|COMMENT"'
    . $X 'docker exec practice01-postgres-init psql -U admin -d initdb_demo -c "\dt" -c "SELECT g.name, count(DISTINCT s.id) AS students, count(*) AS marks, round(100.0 * avg(v.is_present::int), 1) AS visit_pct FROM students s JOIN student_groups g ON g.id = s.group_id JOIN lecture_visits v ON v.student_id = s.id GROUP BY g.name ORDER BY 1;"'
    . $X '# Повторный запуск на том же томе: инициализация пропускается'
    . $X 'docker compose --progress plain -f selfwork\docker-compose.initdb.yml restart'
    . $X 'docker logs practice01-postgres-init | Select-String "init process complete|Skipping initialization"'
    $global:KeepPrompt = $true
  }
  'pr1sw_mongo' {   # 3. вложенные документы и агрегация
    Mongo-Session @('use selfwork',
      'db.orders.insertMany([{_id: 1, customer: {name: "Иванов И. И.", city: "Москва"}, items: [{sku: "NB-14", title: "Ноутбук", qty: 1, price: 85000}, {sku: "MS-02", title: "Мышь", qty: 2, price: 1500}]}, {_id: 2, customer: {name: "Петрова А. С.", city: "Казань"}, items: [{sku: "PH-15", title: "Смартфон", qty: 1, price: 62000}, {sku: "CS-15", title: "Чехол", qty: 1, price: 1200}, {sku: "CH-65", title: "Зарядка", qty: 2, price: 2500}]}, {_id: 3, customer: {name: "Иванов И. И.", city: "Москва"}, items: [{sku: "MN-27", title: "Монитор", qty: 2, price: 24000}]}])',
      'db.orders.findOne({_id: 2})',
      'db.orders.aggregate([{$unwind: "$items"}, {$group: {_id: "$_id", customer: {$first: "$customer.name"}, positions: {$sum: 1}, total: {$sum: {$multiply: ["$items.qty", "$items.price"]}}}}, {$sort: {_id: 1}}])',
      'db.orders.aggregate([{$unwind: "$items"}, {$group: {_id: "$customer.name", orders: {$addToSet: "$_id"}, total: {$sum: {$multiply: ["$items.qty", "$items.price"]}}}}, {$project: {orders: {$size: "$orders"}, total: 1}}, {$sort: {total: -1}}])')
  }
  'pr1sw_redis' {   # 4. счётчик посещений INCR + TTL
    $r = "docker exec practice01-redis redis-cli -a $pw --no-auth-warning"
    . $X '# Задание 4. Счётчик посещений страницы: INCR атомарно увеличивает значение, EXPIRE задаёт время жизни ключа'
    . $X "1..5 | ForEach-Object { $r INCR visits:page:/schedule }"
    . $X "$r GET visits:page:/schedule"
    . $X "$r EXPIRE visits:page:/schedule 10"
    . $X "$r TTL visits:page:/schedule"
    . $X 'Start-Sleep -Seconds 5'
    . $X "$r INCR visits:page:/schedule; $r TTL visits:page:/schedule"
    . $X '# INCR не сбрасывает срок жизни ключа; ждём, пока он истечёт'
    . $X 'Start-Sleep -Seconds 6'
    . $X "$r TTL visits:page:/schedule; $r EXISTS visits:page:/schedule; $r GET visits:page:/schedule"
    $global:KeepPrompt = $true
  }
  'pr1sw_neo' {     # 5. друзья друзей
    Neo "UNWIND [['Анна', 'Борис'], ['Анна', 'Вера'], ['Борис', 'Глеб'], ['Борис', 'Дина'], ['Вера', 'Дина'], ['Вера', 'Егор'], ['Глеб', 'Егор'], ['Дина', 'Жанна']] AS p MERGE (a:SNUser {name: p[0]}) MERGE (b:SNUser {name: p[1]}) MERGE (a)-[:FRIEND]-(b) RETURN count(*) AS friendships"
    Neo "MATCH (u:SNUser)-[:FRIEND]-(f) RETURN u.name AS user, collect(f.name) AS friends ORDER BY user"
    Neo "MATCH (me:SNUser {name: 'Анна'})-[:FRIEND]-(f)-[:FRIEND]-(fof) WHERE fof <> me AND NOT (me)-[:FRIEND]-(fof) RETURN fof.name AS candidate, count(DISTINCT f) AS mutual_friends, collect(DISTINCT f.name) AS via ORDER BY mutual_friends DESC, candidate"
    Neo "MATCH (me:SNUser {name: 'Глеб'})-[:FRIEND]-(f)-[:FRIEND]-(fof) WHERE fof <> me AND NOT (me)-[:FRIEND]-(fof) RETURN fof.name AS candidate, count(DISTINCT f) AS mutual_friends ORDER BY mutual_friends DESC, candidate"
    $global:KeepPrompt = $true
  }
  'pr1sw_es' {      # 6. полнотекстовый поиск с ранжированием
    Es PUT 'http://localhost:9200/books' 'selfwork/es/books_index.json'
    Es POST 'http://localhost:9200/_bulk?refresh=true&filter_path=errors,items.index.result' 'selfwork/es/books.ndjson' 'application/x-ndjson'
    Es GET 'http://localhost:9200/books/_count'
    . $X 'Get-Content selfwork\es\search_ranked.json -Encoding UTF8'
    . $X '$res = curl.exe -s -H "Content-Type: application/json" --data-binary "@selfwork/es/search_ranked.json" "http://localhost:9200/books/_search" | ConvertFrom-Json'
    . $X '"найдено: $($res.hits.total.value), максимальная оценка: $($res.hits.max_score)"'
    . $X '$res.hits.hits | ForEach-Object { [pscustomobject]@{score = [math]::Round($_._score, 3); title = $_._source.title; author = $_._source.author; fragment = $_.highlight.description[0]} } | Format-Table -AutoSize'
    $global:KeepPrompt = $true
  }
}
