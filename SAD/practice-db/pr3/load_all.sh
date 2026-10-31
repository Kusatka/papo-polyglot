#!/usr/bin/env bash
# ПР №3: развернуть спроектированную структуру во всех пяти хранилищах и наполнить тестовыми данными.
# Повторный запуск пересоздаёт данные с нуля. Запуск из Git Bash:  ./load_all.sh [pg|redis|neo4j|mongo|es]
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")"
set -a; source ../pr1/.env; set +a
mkdir -p evidence
ONLY="${1:-all}"
[ -f data/pg_data.sql ] || PYTHONIOENCODING=utf-8 python -P make_data.py
want() { [ "$ONLY" = all ] || [ "$ONLY" = "$1" ]; }

if want pg; then
  echo "== PostgreSQL: база university_system (master, полная схема)"
  docker cp schema.sql practice01-postgres:/tmp/pr3_schema.sql >/dev/null
  docker cp data/pg_data.sql practice01-postgres:/tmp/pr3_data.sql >/dev/null
  docker exec practice01-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -q \
    -c "DROP DATABASE IF EXISTS university_system WITH (FORCE);" -c "CREATE DATABASE university_system;"
  docker exec practice01-postgres psql -U "$POSTGRES_USER" -d university_system -q -v ON_ERROR_STOP=1 -f /tmp/pr3_schema.sql >/dev/null
  docker exec practice01-postgres psql -U "$POSTGRES_USER" -d university_system -q -v ON_ERROR_STOP=1 -f /tmp/pr3_data.sql >/dev/null
  docker exec practice01-postgres psql -U "$POSTGRES_USER" -d university_system -c "SELECT 'universities' AS table_name, count(*) AS rows FROM universities UNION ALL SELECT 'institutes' AS table_name, count(*) AS rows FROM institutes UNION ALL SELECT 'departments' AS table_name, count(*) AS rows FROM departments UNION ALL SELECT 'specialties' AS table_name, count(*) AS rows FROM specialties UNION ALL SELECT 'department_specialties' AS table_name, count(*) AS rows FROM department_specialties UNION ALL SELECT 'lecture_courses' AS table_name, count(*) AS rows FROM lecture_courses UNION ALL SELECT 'lectures' AS table_name, count(*) AS rows FROM lectures UNION ALL SELECT 'lecture_materials' AS table_name, count(*) AS rows FROM lecture_materials UNION ALL SELECT 'student_groups' AS table_name, count(*) AS rows FROM student_groups UNION ALL SELECT 'students' AS table_name, count(*) AS rows FROM students UNION ALL SELECT 'student_electives' AS table_name, count(*) AS rows FROM student_electives UNION ALL SELECT 'schedule' AS table_name, count(*) AS rows FROM schedule UNION ALL SELECT 'attendance' AS table_name, count(*) AS rows FROM attendance;"
fi

if want redis; then
  echo "== Redis: кэш в логической базе №2"
  docker cp data/redis_cache.resp practice01-redis:/tmp/ >/dev/null
  docker exec practice01-redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning -n 2 FLUSHDB
  docker exec practice01-redis sh -c "redis-cli -a $REDIS_PASSWORD --no-auth-warning -n 2 --pipe < /tmp/redis_cache.resp"
  docker exec practice01-redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning -n 2 DBSIZE
fi

if want neo4j; then
  echo "== Neo4j: иерархия, группы, студенты"
  docker cp data/neo4j_load.cypher practice01-neo4j:/tmp/pr3_neo4j.cypher >/dev/null
  docker exec practice01-neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
    "MATCH (n) WHERE n:University OR n:Institute OR n:Department OR n:Specialty OR n:LectureCourse OR n:Group OR n:Student DETACH DELETE n"
  docker exec practice01-neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" -f /tmp/pr3_neo4j.cypher
  docker exec practice01-neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" --format plain \
    "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS nodes ORDER BY label"
fi

if want mongo; then
  echo "== MongoDB: база university_system"
  docker cp data/mongo_load.js practice01-mongodb:/tmp/pr3_mongo.js >/dev/null
  docker exec -i practice01-mongodb mongosh --quiet -u "$MONGO_USER" -p "$MONGO_PASSWORD" --authenticationDatabase admin <<'JS'
use university_system
db.dropDatabase()
load("/tmp/pr3_mongo.js")
db.getCollectionNames().map(c => c + ": " + db[c].countDocuments())
JS
fi

if want es; then
  echo "== Elasticsearch: индекс lectures"
  curl -s -X DELETE "http://localhost:9200/lectures" >/dev/null
  curl -s -X PUT "http://localhost:9200/lectures" -H 'Content-Type: application/json' --data-binary @data/es_lectures_mapping.json; echo
  curl -s -X POST "http://localhost:9200/_bulk?refresh=true&filter_path=errors" -H 'Content-Type: application/x-ndjson' \
    --data-binary @data/es_lectures.ndjson; echo
  curl -s "http://localhost:9200/lectures/_count?filter_path=count"; echo
fi
