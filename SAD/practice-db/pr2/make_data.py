"""Файлы данных ПР №2 для пяти СУБД из общего набора common/dataset.py.  Запуск: python -P make_data.py

  data/redis_students.resp   студенты группы БСБО-01-23: хеш на студента, ключ = номер зачётной книжки (протокол RESP для redis-cli --pipe)
  data/mongo_create.js       коллекция student_groups с проверкой схемы ($jsonSchema) и уникальным индексом
  data/mongo_groups.js       документы групп с вложенным составом студентов
  data/neo4j_schema.cypher   ограничения уникальности (схема графа)
  data/neo4j_load.cypher     узлы Group / Student / LectureCourse и связи MEMBER_OF / STUDIES / CHOSE
  data/es_mapping.json       индекс lecture_courses с русским анализатором
  data/es_courses.ndjson     курсы с полнотекстовым описанием (Bulk API)
  data/es_*.json             тела запросов поиска и обновления
  data/pg_schema.sql         студенты, расписание и журнал посещений, партиционированный по неделям
  data/pg_fill.sql           студенты, расписание и случайные отметки посещаемости
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'common'))
import dataset  # noqa: E402

D = HERE / 'data'
D.mkdir(exist_ok=True)
ds = dataset.build()
GROUP = 'БСБО-01-23'
st_main = [s for s in ds['students'] if s['group'] == GROUP]


def w(name, text):
    (D / name).write_text(text, encoding='utf-8', newline='\n')


def q(v):   # литерал Cypher: ключи словаря без кавычек, строки в двойных кавычках
    if isinstance(v, dict):
        return '{' + ', '.join(f'{k}: {q(x)}' for k, x in v.items()) + '}'
    if isinstance(v, list):
        return '[' + ', '.join(q(x) for x in v) + ']'
    return json.dumps(v, ensure_ascii=False)


# ---------------- Redis ----------------
def resp(*args):
    out = [f'*{len(args)}\r\n'.encode()]
    for a in args:
        b = str(a).encode('utf-8')
        out.append(f'${len(b)}\r\n'.encode() + b + b'\r\n')
    return b''.join(out)


FIELDS = ['id', 'last_name', 'first_name', 'patronymic', 'group', 'email', 'phone', 'enrollment_date', 'status']
(D / 'redis_students.resp').write_bytes(b''.join(
    resp('HSET', s['student_card_number'], *[x for f in FIELDS for x in (f, s[f])]) for s in st_main))

# ---------------- MongoDB ----------------
spec = {s['code']: s for s in ds['specialties']}
dept = {d['short_name']: d for d in ds['departments']}
mongo_docs = []
for g in ds['groups']:
    sp = spec[g['specialty_code']]
    d = dept[[x for x, primary in sp['departments'] if primary][0]]
    members = [s for s in ds['students'] if s['group'] == g['name']]
    mongo_docs.append({
        '_id': g['id'], 'name': g['name'], 'enrollment_year': g['enrollment_year'], 'course_year': g['course_year'],
        'curator': g['curator'],
        'specialty': {'code': sp['code'], 'name': sp['name'], 'degree_level': sp['degree_level']},
        'department': {'short_name': d['short_name'], 'name': d['name']},
        'students_count': len(members),
        'students': [{'id': s['id'], 'student_card_number': s['student_card_number'], 'last_name': s['last_name'],
                      'first_name': s['first_name'], 'patronymic': s['patronymic'], 'email': s['email'],
                      'status': s['status'], 'electives': s['electives']} for s in members],
    })
w('mongo_groups.js', '// Документы групп: данные группы и вложенный состав студентов (агрегат читается одним запросом)\n'
  f'db.student_groups.insertMany({json.dumps(mongo_docs, ensure_ascii=False, indent=2)});\n')
w('mongo_create.js', '''// Создание хранилища: коллекция с проверкой структуры документа и уникальным индексом по названию группы
db.createCollection("student_groups", {
  validator: { $jsonSchema: {
    bsonType: "object",
    required: ["name", "enrollment_year", "specialty", "students"],
    properties: {
      name:            { bsonType: "string", pattern: "^[А-ЯЁ]{4}-[0-9]{2}-[0-9]{2}$" },
      enrollment_year: { bsonType: "number", minimum: 2000 },
      students:        { bsonType: "array", items: { bsonType: "object",
                         required: ["student_card_number", "last_name", "first_name"] } }
    }
  } }
});
db.student_groups.createIndex({ name: 1 }, { unique: true });
''')

# ---------------- Neo4j ----------------
w('neo4j_schema.cypher', '''CREATE CONSTRAINT group_name IF NOT EXISTS FOR (g:Group) REQUIRE g.name IS UNIQUE;
CREATE CONSTRAINT student_card IF NOT EXISTS FOR (s:Student) REQUIRE s.student_card_number IS UNIQUE;
CREATE CONSTRAINT course_id IF NOT EXISTS FOR (c:LectureCourse) REQUIRE c.id IS UNIQUE;
''')
groups = [{'id': g['id'], 'name': g['name'], 'enrollment_year': g['enrollment_year'], 'curator': g['curator']}
          for g in ds['groups']]
courses = [{'id': c['id'], 'name': c['name'], 'semester': c['semester'], 'total_hours': c['total_hours'],
            'is_elective': c['is_elective']} for c in ds['courses']]
students = [{'id': s['id'], 'card': s['student_card_number'], 'last_name': s['last_name'],
             'first_name': s['first_name'], 'patronymic': s['patronymic'], 'group': s['group'],
             'electives': s['electives']} for s in ds['students']]
w('neo4j_load.cypher', f'''// Узлы групп и курсов
UNWIND {q(groups)} AS g
MERGE (n:Group {{name: g.name}}) SET n.id = g.id, n.enrollment_year = g.enrollment_year, n.curator = g.curator;
UNWIND {q(courses)} AS c
MERGE (n:LectureCourse {{id: c.id}}) SET n.name = c.name, n.semester = c.semester, n.total_hours = c.total_hours,
  n.is_elective = c.is_elective;
// Студенты и их членство в группе
UNWIND {q(students)} AS s
MATCH (g:Group {{name: s.group}})
MERGE (n:Student {{student_card_number: s.card}})
SET n.id = s.id, n.last_name = s.last_name, n.first_name = s.first_name, n.patronymic = s.patronymic,
  n.name = s.last_name + ' ' + left(s.first_name, 1) + '.' + left(s.patronymic, 1) + '.'
MERGE (n)-[:MEMBER_OF]->(g);
// Обязательные курсы изучает вся группа
MATCH (g:Group), (c:LectureCourse {{is_elective: false}}) MERGE (g)-[:STUDIES]->(c);
// Курсы по выбору — индивидуально каждый студент
UNWIND {q(students)} AS s
UNWIND s.electives AS course
MATCH (n:Student {{student_card_number: s.card}}), (c:LectureCourse {{name: course}})
MERGE (n)-[:CHOSE]->(c);
''')

# ---------------- Elasticsearch ----------------
w('es_mapping.json', json.dumps({
    'settings': {'number_of_shards': 1, 'number_of_replicas': 0, 'analysis': {
        'analyzer': {'russian_custom': {'type': 'custom', 'tokenizer': 'standard',
                                        'filter': ['lowercase', 'russian_stop', 'russian_stemmer']}},
        'filter': {'russian_stop': {'type': 'stop', 'stopwords': '_russian_'},
                   'russian_stemmer': {'type': 'stemmer', 'language': 'russian'}}}},
    'mappings': {'properties': {
        'course_id': {'type': 'keyword'},
        'name': {'type': 'text', 'analyzer': 'russian_custom', 'fields': {'keyword': {'type': 'keyword'}}},
        'description': {'type': 'text', 'analyzer': 'russian_custom'},
        'specialty_code': {'type': 'keyword'}, 'department': {'type': 'keyword'},
        'semester': {'type': 'integer'}, 'total_hours': {'type': 'integer'},
        'is_elective': {'type': 'boolean'}, 'tags': {'type': 'keyword'}, 'terms': {'type': 'keyword'}}},
}, ensure_ascii=False, indent=2))
lines = []
for c in ds['courses']:
    lines.append(json.dumps({'index': {'_index': 'lecture_courses', '_id': c['id']}}, ensure_ascii=False))
    lines.append(json.dumps({'course_id': c['id'], 'name': c['name'], 'description': c['description'],
                             'specialty_code': c['specialty_code'], 'department': c['department'],
                             'semester': c['semester'], 'total_hours': c['total_hours'],
                             'is_elective': c['is_elective'], 'tags': c['tags'], 'terms': c['terms']},
                            ensure_ascii=False))
w('es_courses.ndjson', '\n'.join(lines) + '\n')
w('es_search.json', json.dumps({'_source': ['name', 'is_elective'],
                                'query': {'match': {'description': 'партиционированием таблиц'}},
                                'highlight': {'fields': {'description': {}}}}, ensure_ascii=False, indent=2))
w('es_update.json', json.dumps({'doc': {'total_hours': 90, 'tags': ['курс по выбору', 'обновлено']}},
                               ensure_ascii=False))

# ---------------- PostgreSQL ----------------
w('pg_schema.sql', '''-- Справочник студентов и расписание (минимальный набор для журнала посещений)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_card_number VARCHAR(20) NOT NULL UNIQUE,
    last_name VARCHAR(100) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    patronymic VARCHAR(100),
    group_name VARCHAR(50) NOT NULL
);

CREATE TABLE schedule (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_name VARCHAR(50) NOT NULL,
    course_name VARCHAR(500) NOT NULL,
    lecture_number INT NOT NULL,
    scheduled_date DATE NOT NULL,
    week_start_date DATE NOT NULL,       -- понедельник недели = ключ партиционирования журнала
    classroom VARCHAR(50),
    teacher_name VARCHAR(300)
);

-- Журнал посещений лекций, партиционированный по неделе посещения (RANGE по понедельнику недели)
CREATE TABLE attendance (
    id UUID NOT NULL DEFAULT uuid_generate_v4(),
    schedule_id UUID NOT NULL,
    student_id UUID NOT NULL,
    week_start_date DATE NOT NULL,
    is_present BOOLEAN NOT NULL DEFAULT FALSE,
    marked_at TIMESTAMP DEFAULT NOW(),
    note VARCHAR(500),
    PRIMARY KEY (id, week_start_date)    -- ключ партиционирования обязан входить в первичный ключ
) PARTITION BY RANGE (week_start_date);

CREATE UNIQUE INDEX uq_attendance_schedule_student ON attendance (schedule_id, student_id, week_start_date);
CREATE INDEX idx_attendance_student ON attendance (student_id);

-- Партиции на N недель вперёд: attendance_wГГГГ_ММ_ДД = [понедельник, следующий понедельник)
CREATE OR REPLACE FUNCTION create_weekly_partitions(start_date DATE, num_weeks INT) RETURNS VOID AS $$
DECLARE
    week_start DATE := date_trunc('week', start_date)::DATE;
    part TEXT;
BEGIN
    FOR i IN 0..num_weeks - 1 LOOP
        part := 'attendance_w' || to_char(week_start, 'YYYY_MM_DD');
        IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = part) THEN
            EXECUTE format('CREATE TABLE %I PARTITION OF attendance FOR VALUES FROM (%L) TO (%L)',
                           part, week_start, week_start + 7);
        END IF;
        week_start := week_start + 7;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

SELECT create_weekly_partitions('2026-02-09', 20);          -- весенний семестр 2026: 20 недель
CREATE TABLE attendance_default PARTITION OF attendance DEFAULT;   -- даты вне семестра
''')


def sql(v):
    return 'NULL' if v is None else "'" + str(v).replace("'", "''") + "'"


st_rows = ',\n'.join(f"({sql(s['id'])}, {sql(s['student_card_number'])}, {sql(s['last_name'])}, "
                     f"{sql(s['first_name'])}, {sql(s['patronymic'])}, {sql(s['group'])})" for s in ds['students'])
sc_rows = ',\n'.join(f"({sql(r['id'])}, {sql(r['group'])}, {sql(r['course_name'])}, {r['order_number']}, "
                     f"{sql(r['scheduled_date'])}, {sql(r['week_start_date'])}, {sql(r['classroom'])}, "
                     f"{sql(r['teacher_name'])})" for r in ds['schedule'])
# какие курсы слушает студент: обязательные курсы группы + его курсы по выбору
takes = ',\n'.join(f"({sql(s['id'])}, {sql(c['name'])})" for s in ds['students'] for c in ds['courses']
                   if not c['is_elective'] or c['name'] in s['electives'])
rates = ',\n'.join(f"({sql(s['id'])}, {s['presence_rate']})" for s in ds['students'])
w('pg_fill.sql', f'''INSERT INTO students (id, student_card_number, last_name, first_name, patronymic, group_name) VALUES
{st_rows};

INSERT INTO schedule (id, group_name, course_name, lecture_number, scheduled_date, week_start_date, classroom, teacher_name) VALUES
{sc_rows};

-- Отметки посещаемости формируются случайным выбором: у каждого студента своя «склонность»
-- посещать лекции (rate), отметка = random() < rate. setseed делает выборку воспроизводимой.
SELECT setseed(0.2026);
WITH takes(student_id, course_name) AS (VALUES
{takes}),
     rate(student_id, p) AS (VALUES
{rates})
INSERT INTO attendance (schedule_id, student_id, week_start_date, is_present, marked_at, note)
SELECT sc.id, st.id, sc.week_start_date, x.present,
       sc.scheduled_date + time '10:30',
       CASE WHEN NOT x.present AND random() < 0.3 THEN 'уважительная причина' END
FROM schedule sc
JOIN students st ON st.group_name = sc.group_name
JOIN takes t ON t.student_id = st.id::text AND t.course_name = sc.course_name
JOIN rate r ON r.student_id = st.id::text
CROSS JOIN LATERAL (SELECT random() < r.p AS present) x
WHERE sc.scheduled_date <= DATE '2026-05-31';     -- журнал ведётся по прошедшие занятия
''')

print('файлы:', ', '.join(sorted(p.name for p in D.iterdir())))
print('студентов в Redis:', len(st_main), '| групп в MongoDB:', len(mongo_docs), '| курсов в ES:', len(ds['courses']),
      '| занятий в расписании:', len(ds['schedule']))
