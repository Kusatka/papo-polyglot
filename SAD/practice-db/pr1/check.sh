#!/usr/bin/env bash
# ПР №1: проверка доступности пяти СУБД, мест хранения данных и журналов.
# Запуск из Git Bash в каталоге pr1:  ./check.sh
# Вывод каждой проверки сохраняется в evidence/NN_<служба>.txt для отчёта.

export MSYS_NO_PATHCONV=1          # Git Bash не должен переписывать пути /var/... в аргументах docker
cd "$(dirname "$0")"
set -a; source .env; set +a
OUT=evidence
mkdir -p "$OUT"

# run "описание" команда...  -> печатает "$ команда", затем её вывод
run() { echo "\$ ${*}"; "$@" 2>&1; echo; }
sh_run() { echo "\$ $1"; bash -c "$1" 2>&1; echo; }
# es МЕТОД URL JSON -> запрос к Elasticsearch; тело идёт через stdin, иначе curl.exe
# под Windows портит кириллицу в аргументах командной строки
es() { echo "\$ curl -s -X $1 '$2' -H 'Content-Type: application/json' -d '$3'"
       printf '%s' "$3" | curl -s -X "$1" "$2" -H 'Content-Type: application/json' --data-binary @- 2>&1; echo; echo; }

section() { echo "==== $1 ===="; echo "Дата проверки: $(date '+%Y-%m-%d %H:%M:%S')"; echo; }

# ---------------------------------------------------------------- 01 состояние стенда
{
  section "Состояние контейнеров"
  run docker compose ps --format "table {{.Name}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
  run docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
} > "$OUT/01_containers.txt"

# ---------------------------------------------------------------- 02 Redis
{
  section "Redis"
  run docker exec practice01-redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning PING
  sh_run "docker exec practice01-redis redis-cli -a '$REDIS_PASSWORD' --no-auth-warning INFO server | grep -E 'redis_version|os|uptime_in_seconds|tcp_port'"
  echo "-- место хранения данных и журнала:"
  run docker exec practice01-redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning CONFIG GET dir
  run docker exec practice01-redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning CONFIG GET appendonly
  run docker exec practice01-redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning CONFIG GET save
  run docker exec practice01-redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning CONFIG GET logfile
  echo "-- базовые операции:"
  run docker exec practice01-redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning SET mykey "Hello, Redis!"
  run docker exec practice01-redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning GET mykey
  run docker exec practice01-redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning HSET user:1 name Ivanov age 20 group IKBO-01-22
  run docker exec practice01-redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning HGETALL user:1
  run docker exec practice01-redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning DBSIZE
  run docker exec practice01-redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning BGREWRITEAOF
  sleep 2
  run docker exec practice01-redis ls -la /data /data/appendonlydir
  run docker exec practice01-redis tail -n 8 /var/log/redis/redis.log
} > "$OUT/02_redis.txt"

# ---------------------------------------------------------------- 03 MongoDB
MONGO="docker exec practice01-mongodb mongosh --quiet -u $MONGO_USER -p $MONGO_PASSWORD --authenticationDatabase admin"
{
  section "MongoDB"
  run $MONGO --eval "db.runCommand({ping: 1})"
  run $MONGO --eval "db.version()"
  echo "-- место хранения данных и журнала (параметры запуска mongod):"
  run $MONGO --eval "printjson(db.adminCommand({getCmdLineOpts: 1}).parsed)"
  echo "-- базовые операции:"
  run $MONGO practice_db --eval '
    db.students.deleteMany({});
    db.students.insertMany([
      {name: "Иванов Иван",     age: 20, group: "ИКБО-01-22", grades: {math: 5, physics: 4, programming: 5}},
      {name: "Петрова Мария",   age: 21, group: "ИКБО-02-22", grades: {math: 4, physics: 5, programming: 4}},
      {name: "Сидоров Алексей", age: 19, group: "ИКБО-01-22", grades: {math: 3, physics: 4, programming: 5}}
    ]);
    printjson(db.students.find({group: "ИКБО-01-22"}, {_id: 0, name: 1, group: 1}).toArray());
    print("countDocuments = " + db.students.countDocuments());'
  run docker exec practice01-mongodb ls -la /data/db
  run docker exec practice01-mongodb tail -n 3 /var/log/mongodb/mongod.log
} > "$OUT/03_mongodb.txt"

# ---------------------------------------------------------------- 04 Neo4j
CYPHER="docker exec practice01-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD"
{
  section "Neo4j"
  run $CYPHER "CALL dbms.components() YIELD name, versions, edition RETURN name, versions, edition;"
  run $CYPHER "SHOW DATABASES YIELD name, currentStatus;"
  sh_run "curl -s http://localhost:7474"
  echo "-- место хранения данных и журналов:"
  run $CYPHER "SHOW SETTINGS YIELD name, value WHERE name STARTS WITH 'server.directories.data' OR name STARTS WITH 'server.directories.logs' RETURN name, value;"
  echo "-- базовые операции:"
  run $CYPHER "MATCH (n {pr1: true}) DETACH DELETE n;"
  run $CYPHER "CREATE (s1:Student {name: 'Иванов Иван', group: 'ИКБО-01-22', pr1: true}), (s2:Student {name: 'Петрова Мария', group: 'ИКБО-02-22', pr1: true}), (c1:Course {title: 'Базы данных', credits: 4, pr1: true}), (c2:Course {title: 'Программирование', credits: 5, pr1: true}), (s1)-[:ENROLLED_IN {semester: 'весна 2024'}]->(c1), (s1)-[:ENROLLED_IN {semester: 'весна 2024'}]->(c2), (s2)-[:ENROLLED_IN {semester: 'весна 2024'}]->(c1);"
  run $CYPHER "MATCH (s:Student {pr1: true})-[:ENROLLED_IN]->(c:Course) RETURN c.title AS course, count(s) AS students ORDER BY students DESC;"
  run docker exec practice01-neo4j ls -la /data /logs
} > "$OUT/04_neo4j.txt"

# ---------------------------------------------------------------- 05 Elasticsearch
{
  section "Elasticsearch"
  sh_run "curl -s http://localhost:9200"
  sh_run "curl -s 'http://localhost:9200/_cluster/health?pretty'"
  echo "-- место хранения данных и журналов:"
  sh_run "curl -s 'http://localhost:9200/_nodes/stats/fs?pretty&filter_path=nodes.*.fs.data.path'"
  sh_run "curl -s 'http://localhost:9200/_nodes/settings?pretty&filter_path=nodes.*.settings.path'"
  echo "-- базовые операции:"
  curl -s -X DELETE 'http://localhost:9200/students' > /dev/null
  es PUT 'http://localhost:9200/students' '{"settings":{"number_of_shards":1,"number_of_replicas":0},"mappings":{"properties":{"name":{"type":"text"},"group":{"type":"keyword"},"bio":{"type":"text"}}}}'
  es PUT 'http://localhost:9200/students/_doc/1?refresh=true' '{"name":"Иванов Иван Иванович","group":"ИКБО-01-22","bio":"Студент третьего курса, увлекается программированием и машинным обучением"}'
  es PUT 'http://localhost:9200/students/_doc/2?refresh=true' '{"name":"Петрова Мария Сергеевна","group":"ИКБО-02-22","bio":"Студентка, занимается анализом данных и визуализацией"}'
  es GET 'http://localhost:9200/students/_search?pretty&filter_path=hits.total,hits.hits._source' '{"query":{"match":{"bio":"данных"}}}'
  sh_run "curl -s 'http://localhost:9200/_cat/indices/students?v'"
  run docker exec practice01-elasticsearch ls -la /usr/share/elasticsearch/logs
} > "$OUT/05_elasticsearch.txt"

# ---------------------------------------------------------------- 06 PostgreSQL
PSQL="docker exec practice01-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB"
{
  section "PostgreSQL"
  run docker exec practice01-postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"
  run $PSQL -c "SELECT version();"
  echo "-- место хранения данных и журнала:"
  run $PSQL -c "SELECT name, setting FROM pg_settings WHERE name IN ('data_directory','logging_collector','log_directory','log_filename','log_rotation_size','log_statement') ORDER BY name;"
  echo "-- базовые операции:"
  run $PSQL -c "DROP TABLE IF EXISTS pr1_students; CREATE TABLE pr1_students (id SERIAL PRIMARY KEY, last_name VARCHAR(50) NOT NULL, first_name VARCHAR(50) NOT NULL, grp VARCHAR(20));"
  run $PSQL -c "INSERT INTO pr1_students (last_name, first_name, grp) VALUES ('Иванов','Иван','ИКБО-01-22'), ('Петрова','Мария','ИКБО-02-22'), ('Сидоров','Алексей','ИКБО-01-22');"
  run $PSQL -c "SELECT * FROM pr1_students ORDER BY id;"
  run docker exec practice01-postgres ls -la /var/lib/postgresql/data/pgdata /var/log/postgresql
  sh_run "docker exec practice01-postgres sh -c 'tail -n 5 /var/log/postgresql/*.log'"
} > "$OUT/06_postgres.txt"

# ---------------------------------------------------------------- 07 тома
{
  section "Тома Docker (место хранения данных)"
  run docker volume ls --filter name=practice01
  for v in $(docker volume ls -q --filter name=practice01); do
    sh_run "docker volume inspect $v --format '{{.Name}} -> {{.Mountpoint}}'"
  done
  echo "-- какие тома и каталоги смонтированы в каждый контейнер:"
  for c in practice01-redis practice01-mongodb practice01-neo4j practice01-elasticsearch practice01-postgres; do
    sh_run "docker inspect $c --format '{{.Name}}:{{range .Mounts}}
  {{.Type}}  {{if .Name}}{{.Name}}{{else}}{{.Source}}{{end}} -> {{.Destination}}{{end}}'"
  done
} > "$OUT/07_volumes.txt"

# ---------------------------------------------------------------- 08 журналы
{
  section "Журналы (лог-записи)"
  echo "-- драйвер журналов контейнеров (stdout/stderr) и ротация:"
  for c in practice01-redis practice01-mongodb practice01-neo4j practice01-elasticsearch practice01-postgres; do
    sh_run "docker inspect $c --format '{{.Name}}  driver={{.HostConfig.LogConfig.Type}}  opts={{json .HostConfig.LogConfig.Config}}'"
  done
  echo "-- файлы журналов СУБД на хосте (каталог logs):"
  sh_run "ls -la logs/*"
} > "$OUT/08_logs.txt"

# ---------------------------------------------------------------- 09 веб-интерфейсы
{
  section "Веб-интерфейсы (HTTP-код ответа)"
  for u in "Redis Commander|http://localhost:8081" "Mongo Express|http://localhost:8082" "Neo4j Browser|http://localhost:7474" "Kibana|http://localhost:5601/api/status" "pgAdmin 4|http://localhost:8083/misc/ping"; do
    name="${u%%|*}"; url="${u#*|}"
    printf '%-16s %-40s HTTP %s\n' "$name" "$url" "$(curl -s -o /dev/null -w '%{http_code}' -u "$ME_USER:$ME_PASSWORD" "$url")"
  done
} > "$OUT/09_web_ui.txt"

echo "Готово. Файлы проверки:"; ls -1 "$OUT"
