# Кадры ПР №2 (подключается точкой из term_frame.ps1; рабочий каталог — pr2). Каждый кадр выполняет
# настоящие операции над СУБД; порядок кадров важен: r1 → r2, m1 → m2 → m3, n1 → n2, e1 → e2, p1 → p2 → p3.
$pw = $envs['REDIS_PASSWORD']; $neo = $envs['NEO4J_PASSWORD']; $pgu = $envs['POSTGRES_USER']
$SID = '7c6ff099-7f7e-5949-9b0e-47d6eaeb925f'   # id курса «NoSQL и полиглотное хранение» (UUID v5, одинаковый во всех хранилищах)

$redisExec = { param($c) $a = @('exec', 'practice01-redis', 'redis-cli', '-a', $pw, '--no-auth-warning', '-n', '1', '--raw') + (Split-Args $c); & docker @a }
$redisLaunch = "docker exec -it practice01-redis redis-cli -a $pw -n 1 --raw"
$redisWarn = "Warning: Using a password with '-a' or '-u' option on the command line interface may not be safe."

function Neo([string]$q) {   # одна команда cypher-shell: строка PowerShell и настоящий вывод
  PS-Line "docker exec practice01-neo4j cypher-shell -u neo4j -p $neo --format verbose `"$q`""
  & docker exec practice01-neo4j cypher-shell -u neo4j -p $neo --format verbose $q 2>&1 | ForEach-Object { "$_" } | Out-Host
}
function NeoFile([string]$f) {
  PS-Line "docker exec practice01-neo4j cypher-shell -u neo4j -p $neo --format verbose -f $f"
  & docker exec practice01-neo4j cypher-shell -u neo4j -p $neo --format verbose -f $f 2>&1 | ForEach-Object { "$_" } | Out-Host
}
function Es([string]$method, [string]$url, [string]$file = '') {
  $show = "curl.exe -s -X $method `"$url`""
  if ($file) { $show += " -H `"Content-Type: application/json`" --data-binary `"@$file`"" }
  PS-Line $show
  if ($file) { & curl.exe -s -X $method $url -H 'Content-Type: application/json' --data-binary "@$file" | Out-Host }
  else { & curl.exe -s -X $method $url | Out-Host }
}
function Pg-Session([string]$db, [string[]]$cmds, [switch]$Quit) {
  PS-Line "docker exec -it practice01-postgres psql -U $pgu -d $db"
  $ver = (docker exec practice01-postgres psql -U $pgu -d $db -tAc 'SHOW server_version;').Trim()
  Write-Host "psql ($ver)"; Write-Host 'Type "help" for help.'; Write-Host ''
  foreach ($c in $cmds) {
    Write-Host "$db=# $c"
    if ($c -match '^\\i (\S+)') { docker exec practice01-postgres psql -U $pgu -d $db -f $Matches[1] 2>&1 | ForEach-Object { "$_" } | Out-Host }
    else { docker exec practice01-postgres psql -U $pgu -d $db -c $c 2>&1 | ForEach-Object { "$_" } | Out-Host }
  }
  if ($Quit) { Write-Host "$db=# \q" } else { Write-Host -NoNewline "$db=# " }
}

switch ($Scenario) {
  'pr2r1' {
    Cli-Session $redisLaunch '127.0.0.1:6379[1]> ' @('DBSIZE') $redisExec $redisWarn 'quit'
    Run 'docker cp data\redis_students.resp practice01-redis:/tmp/'
    Run "docker exec practice01-redis sh -c `"redis-cli -a $pw --no-auth-warning -n 1 --pipe < /tmp/redis_students.resp`""
    Cli-Session $redisLaunch '127.0.0.1:6379[1]> ' @('DBSIZE', 'KEYS 23Б010*', 'HGETALL 23Б0101', 'HGET 23Б0102 email') $redisExec $redisWarn
  }
  'pr2r2' {
    Cli-Session $redisLaunch '127.0.0.1:6379[1]> ' @('HSET 23Б0101 phone "+7 916 555-01-01" status academic_leave',
      'HMGET 23Б0101 phone status', 'DEL 23Б0125', 'EXISTS 23Б0125', 'DBSIZE', 'FLUSHDB', 'DBSIZE') $redisExec $redisWarn
  }
  'pr2m1' {
    Run 'docker cp data\mongo_create.js practice01-mongodb:/tmp/'
    Run 'docker cp data\mongo_groups.js practice01-mongodb:/tmp/'
    Mongo-Session @('use university', 'load("/tmp/mongo_create.js")',
      'db.getCollectionInfos({name: "student_groups"})[0].options.validator.$jsonSchema.required',
      'load("/tmp/mongo_groups.js")', 'db.student_groups.countDocuments()',
      'db.student_groups.findOne({name: "БСБО-01-23"}, {students: {$slice: 1}})')
  }
  'pr2m2' {
    Mongo-Session @('use university',
      'db.student_groups.updateOne({name: "БСБО-01-23"}, {$set: {curator: "Беляев А.Н."}})',
      'db.student_groups.updateOne({name: "БСБО-01-23"}, {$push: {students: {student_card_number: "23Б0126", last_name: "Новиков", first_name: "Игорь", status: "active"}}, $inc: {students_count: 1}})',
      'db.student_groups.updateOne({name: "БСБО-01-23"}, {$set: {"students.$[s].status": "academic_leave"}}, {arrayFilters: [{"s.student_card_number": "23Б0102"}]})',
      'db.student_groups.findOne({name: "БСБО-01-23"}, {_id: 0, curator: 1, students_count: 1, students: {$elemMatch: {status: "academic_leave"}}})')
  }
  'pr2m3' {
    Mongo-Session @('use university',
      'db.student_groups.updateOne({name: "БСБО-01-23"}, {$pull: {students: {student_card_number: "23Б0126"}}, $inc: {students_count: -1}})',
      'db.student_groups.deleteOne({name: "БСБО-02-23"})',
      'db.student_groups.find({}, {_id: 0, name: 1, students_count: 1})',
      'db.student_groups.drop()', 'db.dropDatabase()', 'show dbs')
  }
  'pr2n1' {
    Run 'docker cp data\neo4j_schema.cypher practice01-neo4j:/tmp/'
    Run 'docker cp data\neo4j_load.cypher practice01-neo4j:/tmp/'
    NeoFile '/tmp/neo4j_schema.cypher'
    Neo 'SHOW CONSTRAINTS YIELD name, labelsOrTypes, properties'
    NeoFile '/tmp/neo4j_load.cypher'
    Neo 'MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt'
    Neo 'MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS cnt'
    $global:KeepPrompt = $true
  }
  'pr2n2' {
    Neo "MATCH (s:Student {student_card_number: '23Б0101'})-[:MEMBER_OF]->(g:Group)-[:STUDIES]->(c:LectureCourse) RETURN c.name AS course, 'обязательный' AS kind UNION MATCH (s:Student {student_card_number: '23Б0101'})-[:CHOSE]->(c:LectureCourse) RETURN c.name AS course, 'по выбору' AS kind"
    Neo "MATCH (s:Student {student_card_number: '23Б0101'})-[r:CHOSE]->(:LectureCourse {name: 'Бизнес-аналитика'}) DELETE r WITH s MATCH (c:LectureCourse {name: 'NoSQL и полиглотное хранение'}) MERGE (s)-[:CHOSE]->(c) RETURN s.last_name AS student, [(s)-[:CHOSE]->(x) | x.name] AS electives"
    Neo "MATCH (s:Student {student_card_number: '23Б0125'}) DETACH DELETE s"
    Neo 'MATCH (n) WHERE n:Group OR n:Student OR n:LectureCourse DETACH DELETE n'
    Neo 'DROP CONSTRAINT group_name; DROP CONSTRAINT student_card; DROP CONSTRAINT course_id;'
    Neo 'SHOW CONSTRAINTS YIELD name'
    $global:KeepPrompt = $true
  }
  'pr2e1' {
    Es PUT 'http://localhost:9200/lecture_courses?pretty' 'data/es_mapping.json'
    PS-Line 'curl.exe -s -X POST "http://localhost:9200/_bulk?refresh=true&filter_path=errors,items.*.result" -H "Content-Type: application/x-ndjson" --data-binary "@data/es_courses.ndjson"'
    & curl.exe -s -X POST 'http://localhost:9200/_bulk?refresh=true&filter_path=errors,items.*.result' -H 'Content-Type: application/x-ndjson' --data-binary '@data/es_courses.ndjson' | Out-Host
    Write-Host ''
    Es GET 'http://localhost:9200/lecture_courses/_count?filter_path=count'
    Write-Host ''
    Es GET "http://localhost:9200/lecture_courses/_doc/$SID`?pretty&_source=name,total_hours,is_elective,tags"
    $global:KeepPrompt = $true
  }
  'pr2e2' {
    Es POST "http://localhost:9200/lecture_courses/_update/$SID`?refresh=true&filter_path=result,_version" 'data/es_update.json'
    Write-Host ''
    Es GET "http://localhost:9200/lecture_courses/_doc/$SID`?filter_path=_version,_source&_source=name,total_hours,tags"
    Write-Host ''
    Es DELETE "http://localhost:9200/lecture_courses/_doc/$SID`?refresh=true&filter_path=result"
    Write-Host ''
    Es GET 'http://localhost:9200/lecture_courses/_count?filter_path=count'
    Write-Host ''
    Es DELETE 'http://localhost:9200/lecture_courses?pretty'
    Es GET 'http://localhost:9200/_cat/indices?v&h=index,docs.count'
    $global:KeepPrompt = $true
  }
  'pr2p1' {
    Run 'docker cp data\pg_schema.sql practice01-postgres:/tmp/'
    Run 'docker cp data\pg_fill.sql practice01-postgres:/tmp/'
    Pg-Session 'practice_db' @('CREATE DATABASE pr2_attendance;') -Quit
    Pg-Session 'pr2_attendance' @('\i /tmp/pg_schema.sql',
      "SELECT count(*) AS partitions, min(c.relname) AS first_partition FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid WHERE i.inhparent = 'attendance'::regclass AND c.relname <> 'attendance_default';",
      '\i /tmp/pg_fill.sql')
  }
  'pr2p2' {
    Pg-Session 'pr2_attendance' @(
      'SELECT tableoid::regclass AS partition, count(*) AS rows, round(100.0 * avg(is_present::int), 1) AS present_pct FROM attendance GROUP BY 1 ORDER BY 1;',
      "SELECT a.id, a.week_start_date, st.last_name, sc.course_name, a.is_present FROM attendance a JOIN students st ON st.id = a.student_id JOIN schedule sc ON sc.id = a.schedule_id WHERE st.student_card_number = '23Б0101' AND a.week_start_date = '2026-03-30' ORDER BY sc.scheduled_date;",
      "EXPLAIN (COSTS OFF) SELECT count(*) FROM attendance WHERE week_start_date = '2026-03-30';")
  }
  'pr2p3' {
    Pg-Session 'pr2_attendance' @(
      "UPDATE attendance a SET is_present = true, note = 'исправлено по справке' WHERE (a.id, a.week_start_date) = (SELECT a2.id, a2.week_start_date FROM attendance a2 JOIN students st ON st.id = a2.student_id WHERE st.student_card_number = '23Б0101' AND NOT a2.is_present ORDER BY a2.week_start_date LIMIT 1) RETURNING a.week_start_date, a.is_present, a.note;",
      "DELETE FROM attendance a USING students st WHERE st.id = a.student_id AND st.student_card_number = '23Б0125';",
      'ALTER TABLE attendance DETACH PARTITION attendance_w2026_05_25;', 'DROP TABLE attendance_w2026_05_25;',
      'SELECT count(*) AS rows FROM attendance;', 'DROP TABLE attendance;') -Quit
    Pg-Session 'practice_db' @('DROP DATABASE pr2_attendance WITH (FORCE);', "SELECT datname FROM pg_database WHERE datname LIKE 'pr2%';")
  }
}
