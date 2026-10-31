# Кадры ПР №3 (подключается точкой из term_frame.ps1; рабочий каталог — pr3). Только чтение: примеры
# запросов к каждому хранилищу по заполненной структуре (пункт 9 требований к отчёту).
$pw = $envs['REDIS_PASSWORD']; $neo = $envs['NEO4J_PASSWORD']; $pgu = $envs['POSTGRES_USER']
$G1 = '18216887-5128-552b-8269-fed53ee98175'      # id группы БСБО-01-23 (UUID v5)

function Pg-Run([string]$db, [string[]]$cmds) {
  PS-Line "docker exec -it practice01-postgres psql -U $pgu -d $db"
  $ver = (docker exec practice01-postgres psql -U $pgu -d $db -tAc 'SHOW server_version;').Trim()
  Write-Host "psql ($ver)"; Write-Host 'Type "help" for help.'; Write-Host ''
  foreach ($c in $cmds) { Write-Host "$db=# $c"; docker exec practice01-postgres psql -U $pgu -d $db -c $c 2>&1 | ForEach-Object { "$_" } | Out-Host }
  Write-Host -NoNewline "$db=# "
}
function Neo([string]$q) {
  PS-Line "docker exec practice01-neo4j cypher-shell -u neo4j -p $neo --format verbose `"$q`""
  & docker exec practice01-neo4j cypher-shell -u neo4j -p $neo --format verbose $q 2>&1 | ForEach-Object { "$_" } | Out-Host
}
function Es([string]$method, [string]$url, [string]$file = '') {
  $show = "curl.exe -s -X $method `"$url`""
  if ($file) { $show += " -H `"Content-Type: application/json`" --data-binary `"@$file`"" }
  PS-Line $show
  if ($file) { & curl.exe -s -X $method $url -H 'Content-Type: application/json' --data-binary "@$file" | Out-Host }
  else { & curl.exe -s -X $method $url | Out-Host }
}
$redisExec = { param($c) $a = @('exec', 'practice01-redis', 'redis-cli', '-a', $pw, '--no-auth-warning', '-n', '2', '--raw') + (Split-Args $c); & docker @a }

switch ($Scenario) {
  'pr3pg1' {
    Pg-Run 'university_system' @(
      "SELECT table_name, (xpath('/row/c/text()', query_to_xml('SELECT count(*) AS c FROM ' || table_name, false, true, '')))[1]::text::int AS rows FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' AND table_name NOT LIKE 'attendance_%' ORDER BY 1;",
      "SELECT count(*) AS partitions, min(c.relname) AS first, max(c.relname) FILTER (WHERE c.relname <> 'attendance_default') AS last FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid WHERE i.inhparent = 'attendance'::regclass;",
      'SELECT viewname FROM pg_views WHERE schemaname = ''public'' ORDER BY 1;')
  }
  'pr3pg2' {
    Pg-Run 'university_system' @(
      "SELECT start_time, end_time, course_name, lecture_type, classroom, teacher_name FROM v_full_schedule WHERE group_name = 'БСБО-01-23' AND scheduled_date = '2026-03-16' ORDER BY start_time;",
      "SELECT student_card_number, student_name, total_classes, attended, attendance_percentage FROM v_student_attendance_stats WHERE group_name = 'БСБО-01-23' ORDER BY attendance_percentage LIMIT 5;",
      "EXPLAIN (COSTS OFF) SELECT a.is_present FROM attendance a JOIN students st ON st.id = a.student_id WHERE a.week_start_date = '2026-03-16' AND st.group_id = '$G1';",
      "SELECT sp.code, sp.name AS specialty, d.short_name AS department, ds.is_primary FROM specialties sp JOIN department_specialties ds ON ds.specialty_id = sp.id JOIN departments d ON d.id = ds.department_id ORDER BY 1, 4 DESC;")
  }
  'pr3redis' {
    Cli-Session "docker exec -it practice01-redis redis-cli -a $pw -n 2 --raw" '127.0.0.1:6379[2]> ' @(
      'DBSIZE', "TYPE schedule:$G1`:2026-03-16", "HGETALL schedule:$G1`:2026-03-16", "TTL schedule:$G1`:2026-03-16",
      "LRANGE today_schedule:$G1 0 -1", 'GET session:student-23b0101', 'TTL session:student-23b0101',
      'HGET student:0abd7fcf-8a20-5394-b4b3-e3fc647063ab last_name', 'TTL student:0abd7fcf-8a20-5394-b4b3-e3fc647063ab') $redisExec `
      "Warning: Using a password with '-a' or '-u' option on the command line interface may not be safe."
  }
  'pr3neo' {
    Neo "MATCH (u:University)-[:HAS_INSTITUTE]->(i)-[:HAS_DEPARTMENT]->(d)-[h:HAS_SPECIALTY]->(s)-[:HAS_COURSE]->(c) WHERE h.is_primary AND c.name STARTS WITH 'Проектирование' RETURN u.short_name, i.short_name, d.short_name, s.code, c.name"
    Neo "MATCH p = shortestPath((u:University)-[*]->(c:LectureCourse {name: 'NoSQL и полиглотное хранение'})) RETURN [n IN nodes(p) | coalesce(n.short_name, n.code, n.name)] AS breadcrumbs"
    Neo "MATCH (i:Institute {short_name: 'ИКБ'})-[:HAS_DEPARTMENT]->(:Department)-[:TEACHES]->(c:LectureCourse) RETURN c.name AS course, c.is_elective AS elective ORDER BY course"
    Neo "MATCH (c:LectureCourse)<-[:HAS_COURSE]-(sp:Specialty)-[:HAS_GROUP]->(:Group)<-[:MEMBER_OF]-(s:Student) WHERE NOT c.is_elective OR (s)-[:CHOSE]->(c) RETURN sp.code AS specialty, c.name AS course, c.is_elective AS elective, count(DISTINCT s) AS listeners ORDER BY specialty, listeners DESC"
    $global:KeepPrompt = $true
  }
  'pr3mongo' {
    Mongo-Session @('use university_system',
      'db.lecture_materials.findOne({course_name: "NoSQL и полиглотное хранение", lecture_type: "lab"}, {_id: 0, lecture_title: 1, order_number: 1, "content.word_count": 1, materials: 1, "metadata.tags": 1})',
      'db.lecture_materials.countDocuments({"materials.type": "code_sample", "materials.language": "python"})',
      'db.lecture_materials.aggregate([{$group: {_id: "$course_name", lectures: {$sum: 1}, materials: {$sum: {$size: "$materials"}}, avg_words: {$avg: "$content.word_count"}}}, {$project: {lectures: 1, materials: 1, avg_words: {$round: ["$avg_words", 1]}}}, {$sort: {lectures: -1}}, {$limit: 3}])')
  }
  'pr3es' {
    Es GET 'http://localhost:9200/lectures/_search?size=2&pretty&filter_path=hits.total.value,hits.hits._score,hits.hits._source,hits.hits.highlight' 'queries/es_search_terms.json'
    Es GET 'http://localhost:9200/lectures/_search?size=2&pretty&filter_path=hits.total.value,hits.hits._source' 'queries/es_labs_docker.json'
    $global:KeepPrompt = $true
  }
  'pr3es2' {
    Es GET 'http://localhost:9200/lectures/_search?filter_path=aggregations.by_type.buckets.key,aggregations.by_type.buckets.doc_count,aggregations.by_type.buckets.by_specialty.buckets' 'queries/es_aggs_type.json'
    $global:KeepPrompt = $true
  }
}
