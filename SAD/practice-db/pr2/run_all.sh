#!/usr/bin/env bash
# ПР №2: полный цикл CRUD в пяти СУБД — создать хранилище, добавить данные, прочитать по ключу,
# изменить, удалить записи, удалить хранилище.  Запуск из Git Bash:  ./run_all.sh [redis|mongo|neo4j|es|pg] [--keep]
#   --keep  — не выполнять последний шаг «удалить хранилище» (данные остаются для показа в веб-интерфейсах)
# Вывод каждой СУБД сохраняется в evidence/<субд>.txt
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")"
set -a; source ../pr1/.env; set +a
mkdir -p evidence
ONLY="${1:-all}"; KEEP=""; [[ "$*" == *--keep* ]] && KEEP=1; [[ "$ONLY" == --keep ]] && ONLY=all
run() { echo "\$ ${*}"; "$@" 2>&1; echo; }
step() { echo; echo "==== $1 ===="; }

RCLI="docker exec practice01-redis redis-cli -a $REDIS_PASSWORD --no-auth-warning -n 1 --raw"
MONGO="docker exec -i practice01-mongodb mongosh --quiet -u $MONGO_USER -p $MONGO_PASSWORD --authenticationDatabase admin"
CY="docker exec practice01-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD --format plain"
PSQL="docker exec practice01-postgres psql -U $POSTGRES_USER"
ES=http://localhost:9200
SID=$(PYTHONIOENCODING=utf-8 python -P -c "import sys;sys.path.insert(0,'../common');import dataset as d;print([c['id'] for c in d.build()['courses'] if c['name']=='NoSQL и полиглотное хранение'][0])")
esj() { echo "\$ curl -X $1 $2 ${3:+--data-binary @$3}"; if [ -n "$3" ]; then curl -s -X "$1" "$2" -H 'Content-Type: application/json' --data-binary "@$3"; else curl -s -X "$1" "$2"; fi; echo; echo; }

redis() {
  step "1. Создание хранилища: логическая база Redis №1 (SELECT 1), проверка, что она пуста"; run $RCLI DBSIZE
  step "2. Добавление: 25 хешей, ключ = номер зачётной книжки (redis-cli --pipe)"
  docker cp data/redis_students.resp practice01-redis:/tmp/ >/dev/null
  run docker exec practice01-redis sh -c "redis-cli -a $REDIS_PASSWORD --no-auth-warning -n 1 --pipe < /tmp/redis_students.resp"
  run $RCLI DBSIZE
  step "3. Чтение по ключу"; run $RCLI HGETALL 23Б0101; run $RCLI HGET 23Б0102 email
  step "4. Изменение"; run $RCLI HSET 23Б0101 phone "+7 916 555-01-01" status academic_leave; run $RCLI HMGET 23Б0101 phone status
  step "5. Удаление записи"; run $RCLI DEL 23Б0125; run $RCLI EXISTS 23Б0125; run $RCLI DBSIZE
  [ -n "$KEEP" ] && return
  step "6. Удаление хранилища"; run $RCLI FLUSHDB; run $RCLI DBSIZE
}

mongo() {
  for f in mongo_create.js mongo_groups.js; do docker cp "data/$f" practice01-mongodb:/tmp/ >/dev/null; done
  step "1. Создание хранилища: база university, коллекция student_groups с проверкой схемы"
  cat <<'JS' | $MONGO 2>&1
use university
load("/tmp/mongo_create.js")
db.getCollectionInfos({name: "student_groups"})[0].options.validator.$jsonSchema.required
JS
  step "2. Добавление документов групп"
  cat <<'JS' | $MONGO 2>&1
use university
load("/tmp/mongo_groups.js")
db.student_groups.countDocuments()
JS
  step "3. Чтение по ключу (название группы)"
  cat <<'JS' | $MONGO 2>&1
use university
db.student_groups.findOne({name: "БСБО-01-23"}, {name: 1, curator: 1, specialty: 1, students_count: 1, students: {$slice: 2}})
JS
  step "4. Изменение: куратор, новый студент, статус студента"
  cat <<'JS' | $MONGO 2>&1
use university
db.student_groups.updateOne({name: "БСБО-01-23"}, {$set: {curator: "Беляев А.Н."}})
db.student_groups.updateOne({name: "БСБО-01-23"}, {$push: {students: {student_card_number: "23Б0126", last_name: "Новиков", first_name: "Игорь", patronymic: "Сергеевич", status: "active", electives: ["Бизнес-аналитика"]}}, $inc: {students_count: 1}})
db.student_groups.updateOne({name: "БСБО-01-23"}, {$set: {"students.$[s].status": "academic_leave"}}, {arrayFilters: [{"s.student_card_number": "23Б0102"}]})
db.student_groups.aggregate([{$match: {name: "БСБО-01-23"}}, {$project: {_id: 0, curator: 1, students_count: 1, size: {$size: "$students"}, leave: {$filter: {input: "$students", as: "s", cond: {$eq: ["$$s.status", "academic_leave"]}}}}}, {$project: {curator: 1, students_count: 1, size: 1, "leave.student_card_number": 1}}])
JS
  step "5. Удаление: студент из состава и документ группы БСБО-02-23"
  cat <<'JS' | $MONGO 2>&1
use university
db.student_groups.updateOne({name: "БСБО-01-23"}, {$pull: {students: {student_card_number: "23Б0126"}}, $inc: {students_count: -1}})
db.student_groups.deleteOne({name: "БСБО-02-23"})
db.student_groups.find({}, {_id: 0, name: 1, students_count: 1})
JS
  [ -n "$KEEP" ] && return
  step "6. Удаление хранилища"
  cat <<'JS' | $MONGO 2>&1
use university
db.student_groups.drop()
db.dropDatabase()
db.adminCommand({listDatabases: 1, nameOnly: true}).databases.map(d => d.name)
JS
}

neo4j() {
  for f in neo4j_schema.cypher neo4j_load.cypher; do docker cp "data/$f" practice01-neo4j:/tmp/ >/dev/null; done
  step "1. Создание хранилища: ограничения уникальности (схема графа)"
  run $CY "MATCH (n {pr1: true}) DETACH DELETE n"
  run $CY -f /tmp/neo4j_schema.cypher; run $CY "SHOW CONSTRAINTS YIELD name, labelsOrTypes, properties RETURN name, labelsOrTypes, properties"
  step "2. Добавление узлов и связей"; run $CY -f /tmp/neo4j_load.cypher
  run $CY "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt ORDER BY label"
  run $CY "MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS cnt ORDER BY rel"
  step "3. Чтение по ключу: курсы студента = обязательные курсы группы + его курсы по выбору"
  run $CY "MATCH (s:Student {student_card_number: '23Б0101'})-[:MEMBER_OF]->(g:Group)-[:STUDIES]->(c:LectureCourse) RETURN s.last_name AS student, g.name AS grp, c.name AS course, 'обязательный' AS kind UNION MATCH (s:Student {student_card_number: '23Б0101'})-[:MEMBER_OF]->(g:Group), (s)-[:CHOSE]->(c:LectureCourse) RETURN s.last_name AS student, g.name AS grp, c.name AS course, 'по выбору' AS kind"
  step "4. Изменение: замена курса по выбору"
  run $CY "MATCH (s:Student {student_card_number: '23Б0101'})-[r:CHOSE]->(:LectureCourse {name: 'Бизнес-аналитика'}) DELETE r WITH s MATCH (c:LectureCourse {name: 'NoSQL и полиглотное хранение'}) MERGE (s)-[:CHOSE]->(c) SET s.updated = date() RETURN s.last_name AS student, [(s)-[:CHOSE]->(x) | x.name] AS electives"
  step "5. Удаление записи: студент вместе со связями"
  run $CY "MATCH (s:Student {student_card_number: '23Б0125'}) DETACH DELETE s"
  run $CY "MATCH (g:Group {name: 'БСБО-01-23'})<-[:MEMBER_OF]-(s) RETURN g.name AS grp, count(s) AS students"
  [ -n "$KEEP" ] && return
  step "6. Удаление хранилища: все узлы и связи, затем ограничения"
  run $CY "MATCH (n) WHERE n:Group OR n:Student OR n:LectureCourse DETACH DELETE n"
  run $CY "DROP CONSTRAINT group_name IF EXISTS; DROP CONSTRAINT student_card IF EXISTS; DROP CONSTRAINT course_id IF EXISTS"
  run $CY "MATCH (n) WHERE n:Group OR n:Student OR n:LectureCourse RETURN count(n) AS left"
}

es() {
  step "1. Создание хранилища: индекс lecture_courses с русским анализатором"; esj PUT "$ES/lecture_courses?pretty" data/es_mapping.json
  step "2. Добавление документов (Bulk API)"
  echo "\$ curl -X POST $ES/_bulk?refresh=true --data-binary @data/es_courses.ndjson"
  curl -s -X POST "$ES/_bulk?refresh=true&filter_path=errors,items.*.result" -H 'Content-Type: application/x-ndjson' --data-binary @data/es_courses.ndjson; echo; echo
  esj GET "$ES/lecture_courses/_count?pretty"
  step "3. Чтение по ключу и полнотекстовый поиск"
  esj GET "$ES/lecture_courses/_doc/$SID?pretty&_source=name,total_hours,tags"
  esj GET "$ES/lecture_courses/_search?pretty" data/es_search.json
  step "4. Изменение документа"; esj POST "$ES/lecture_courses/_update/$SID?pretty&refresh=true" data/es_update.json
  esj GET "$ES/lecture_courses/_doc/$SID?pretty&_source=name,total_hours,tags"
  step "5. Удаление документа"; esj DELETE "$ES/lecture_courses/_doc/$SID?pretty&refresh=true"; esj GET "$ES/lecture_courses/_count?pretty"
  [ -n "$KEEP" ] && return
  step "6. Удаление хранилища"; esj DELETE "$ES/lecture_courses?pretty"; esj GET "$ES/_cat/indices/lecture_courses?v"
}

pg() {
  for f in pg_schema.sql pg_fill.sql; do docker cp "data/$f" practice01-postgres:/tmp/ >/dev/null; done
  step "1. Создание хранилища: база pr2_attendance, таблица attendance с недельными партициями"
  run $PSQL -d $POSTGRES_DB -c "CREATE DATABASE pr2_attendance;"
  run $PSQL -d pr2_attendance -q -f /tmp/pg_schema.sql
  run $PSQL -d pr2_attendance -c "SELECT count(*) AS partitions, min(c.relname) AS first, max(c.relname) FILTER (WHERE c.relname <> 'attendance_default') AS last FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid WHERE i.inhparent = 'attendance'::regclass;"
  step "2. Добавление: студенты, расписание, случайные отметки посещаемости"
  run $PSQL -d pr2_attendance -f /tmp/pg_fill.sql
  run $PSQL -d pr2_attendance -c "SELECT tableoid::regclass AS partition, count(*) AS rows, round(100.0 * avg(is_present::int), 1) AS present_pct FROM attendance GROUP BY 1 ORDER BY 1;"
  step "3. Чтение по ключу и отсечение партиций"
  run $PSQL -d pr2_attendance -c "SELECT a.id, a.week_start_date, st.last_name, sc.course_name, sc.scheduled_date, a.is_present FROM attendance a JOIN students st ON st.id = a.student_id JOIN schedule sc ON sc.id = a.schedule_id WHERE st.student_card_number = '23Б0101' AND a.week_start_date = '2026-03-30' ORDER BY sc.scheduled_date;"
  run $PSQL -d pr2_attendance -c "EXPLAIN (COSTS OFF) SELECT count(*) FROM attendance WHERE week_start_date = '2026-03-30';"
  step "4. Изменение: отметка задним числом"
  run $PSQL -d pr2_attendance -c "UPDATE attendance a SET is_present = true, note = 'исправлено по справке', marked_at = now() WHERE (a.id, a.week_start_date) = (SELECT a2.id, a2.week_start_date FROM attendance a2 JOIN students st ON st.id = a2.student_id WHERE st.student_card_number = '23Б0101' AND NOT a2.is_present ORDER BY a2.week_start_date LIMIT 1) RETURNING a.id, a.week_start_date, a.is_present, a.note;"
  step "5. Удаление: записи одного студента и целая неделя (DETACH + DROP партиции)"
  run $PSQL -d pr2_attendance -c "DELETE FROM attendance a USING students st WHERE st.id = a.student_id AND st.student_card_number = '23Б0125';"
  run $PSQL -d pr2_attendance -c "ALTER TABLE attendance DETACH PARTITION attendance_w2026_05_25; DROP TABLE attendance_w2026_05_25;"
  run $PSQL -d pr2_attendance -c "SELECT count(*) AS rows, count(DISTINCT tableoid) AS partitions_with_rows FROM attendance;"
  [ -n "$KEEP" ] && return
  step "6. Удаление хранилища"
  run $PSQL -d pr2_attendance -c "DROP TABLE attendance;"
  run $PSQL -d $POSTGRES_DB -c "DROP DATABASE pr2_attendance WITH (FORCE);"
  run $PSQL -d $POSTGRES_DB -c "SELECT datname FROM pg_database WHERE datname LIKE 'pr2%';"
}

for db in redis mongo neo4j es pg; do
  if [ "$ONLY" = all ] || [ "$ONLY" = "$db" ]; then
    { echo "==== ПР №2: $db, $(date '+%Y-%m-%d %H:%M:%S') ===="; $db; } > "evidence/$db.txt" 2>&1
    echo "$db -> evidence/$db.txt"
  fi
done
