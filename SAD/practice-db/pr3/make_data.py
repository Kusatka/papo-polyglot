"""Данные ПР №3 для пяти хранилищ из common/dataset3.py.  Запуск: python -P make_data.py

  data/pg_data.sql           PostgreSQL (master): все сущности; журнал посещений — случайный выбор в SQL
  data/redis_cache.resp      Redis (кэш, база №2): student:{id}, schedule:{group}:{date}, today_schedule:{group},
                             attendance:{schedule_id}, session:{user_id} — с TTL
  data/neo4j_load.cypher     Neo4j: иерархия университет → институт → кафедра → специальность → курс,
                             группы, студенты, курсы по выбору
  data/mongo_load.js         MongoDB: lecture_materials (агрегат материалов занятия), student_groups (группа с составом)
  data/es_lectures_*.json    Elasticsearch: индекс lectures (тексты, аннотации, требования к технике, теги)
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'common'))
import dataset3  # noqa: E402

D = HERE / 'data'
D.mkdir(exist_ok=True)
ds = dataset3.build()
U = ds['university']
by_code = {s['code']: s for s in ds['specialties']}
dept = {d['short_name']: d for d in ds['departments']}
inst = {i['short_name']: i for i in ds['institutes']}
course_by_id = {c['id']: c for c in ds['courses']}
lect_by_id = {x['id']: x for x in ds['lectures']}
group_by_name = {g['name']: g for g in ds['groups']}


def w(name, text):
    (D / name).write_text(text, encoding='utf-8', newline='\n')


def sql(v):
    if v is None:
        return 'NULL'
    if isinstance(v, bool):
        return 'TRUE' if v else 'FALSE'
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return 'ARRAY[' + ', '.join(sql(x) for x in v) + ']::text[]' if v else "'{}'::text[]"
    return "'" + str(v).replace("'", "''") + "'"


def insert(table, cols, rows):
    vals = ',\n'.join('(' + ', '.join(sql(r[c] if isinstance(c, str) else c(r)) for c in cols_src) + ')'
                      for r in rows for cols_src in [cols.values() if isinstance(cols, dict) else cols])
    names = ', '.join(cols.keys() if isinstance(cols, dict) else cols)
    return f'INSERT INTO {table} ({names}) VALUES\n{vals};\n'


# ---------------- PostgreSQL ----------------
dept_spec = [('КИС', '38.03.05', True), ('КПИ', '09.03.04', True), ('КИС', '09.03.04', False)]
parts = [
    insert('universities', ['id', 'name', 'short_name', 'address', 'website', 'founded_year'], [U]),
    insert('institutes', {'id': 'id', 'university_id': lambda r: U['id'], 'name': 'name', 'short_name': 'short_name',
                          'dean': 'dean'}, ds['institutes']),
    insert('departments', {'id': 'id', 'institute_id': lambda r: inst[r['institute']]['id'], 'name': 'name',
                           'short_name': 'short_name', 'head': 'head', 'room': 'room'}, ds['departments']),
    insert('specialties', ['id', 'name', 'code', 'degree_level', 'duration_years'], ds['specialties']),
    insert('department_specialties', {'department_id': lambda r: dept[r[0]]['id'],
                                      'specialty_id': lambda r: by_code[r[1]]['id'], 'is_primary': lambda r: r[2]},
           dept_spec),
    insert('lecture_courses', {'id': 'id', 'specialty_id': 'specialty_id', 'department_id': 'department_id',
                               'name': 'name', 'description': 'description', 'semester': 'semester',
                               'total_hours': 'total_hours', 'lecture_hours': 'lecture_hours',
                               'practice_hours': 'practice_hours', 'lab_hours': 'lab_hours',
                               'is_elective': 'is_elective', 'tags': 'tags'}, ds['courses']),
    insert('lectures', ['id', 'course_id', 'title', 'annotation', 'lecture_type', 'order_number', 'duration_minutes',
                        'tech_requirements', 'tags'], ds['lectures']),
    insert('lecture_materials', {'id': 'id', 'lecture_id': 'lecture_id', 'content_type': 'type', 'title': 'title',
                                 'content_text': lambda r: r.get('content_text'), 'file_url': lambda r: r.get('file_url'),
                                 'metadata': lambda r: json.dumps({k: v for k, v in r.items() if k not in
                                                                   ('id', 'lecture_id', 'type', 'title', 'content_text', 'file_url')},
                                                                  ensure_ascii=False)}, ds['materials']),
    insert('student_groups', ['id', 'specialty_id', 'name', 'enrollment_year', 'curator'], ds['groups']),
    insert('students', ['id', 'group_id', 'first_name', 'last_name', 'patronymic', 'email', 'phone',
                        'student_card_number', 'enrollment_date', 'status'], ds['students']),
]
el_rows = [(s['id'], c['id']) for s in ds['students'] for c in ds['courses']
           if c['is_elective'] and c['name'] in s['electives'] and c['specialty_id'] == group_by_name[s['group']]['specialty_id']]
parts.append(insert('student_electives', {'student_id': lambda r: r[0], 'course_id': lambda r: r[1]}, el_rows))
parts.append(insert('schedule', ['id', 'lecture_id', 'group_id', 'scheduled_date', 'week_start_date', 'start_time',
                                 'end_time', 'classroom', 'teacher_name', 'status'], ds['schedule']))
rates = ',\n'.join(f"({sql(s['id'])}, {s['presence_rate']})" for s in ds['students'])
parts.append(f'''-- Журнал посещений: отметки по прошедшим занятиям (до 31 мая) для слушателей курса
-- (вся группа — для обязательного курса, записавшиеся — для курса по выбору). Отметка формируется
-- случайным выбором: random() < индивидуальная вероятность посещения студента; setseed — воспроизводимость.
SELECT setseed(0.2026);
WITH rate(student_id, p) AS (VALUES
{rates})
INSERT INTO attendance (schedule_id, student_id, week_start_date, is_present, marked_at, marked_by, note)
SELECT s.id, cl.student_id, s.week_start_date, x.present, s.scheduled_date + s.end_time, s.teacher_name,
       CASE WHEN NOT x.present AND random() < 0.25 THEN 'уважительная причина' END
FROM schedule s
JOIN lectures l ON l.id = s.lecture_id
JOIN v_course_listeners cl ON cl.course_id = l.course_id
JOIN students st ON st.id = cl.student_id AND st.group_id = s.group_id
JOIN rate r ON r.student_id = cl.student_id::text
CROSS JOIN LATERAL (SELECT random() < r.p AS present) x
WHERE s.scheduled_date <= DATE '2026-05-31';
ANALYZE;
''')
w('pg_data.sql', '\n'.join(parts))


# ---------------- Redis (кэш) ----------------
def resp(*args):
    out = [f'*{len(args)}\r\n'.encode()]
    for a in args:
        b = str(a).encode('utf-8')
        out.append(f'${len(b)}\r\n'.encode() + b + b'\r\n')
    return b''.join(out)


cmds = []
g1 = group_by_name['БСБО-01-23']
for s in [x for x in ds['students'] if x['group'] == 'БСБО-01-23']:      # кэш карточек студентов, TTL 2 ч
    key = f'student:{s["id"]}'                                            # полная карточка (её же пишет сервис ЛР №1)
    sp = by_code[group_by_name[s['group']]['specialty_code']]
    cmds += [resp('HSET', key, 'id', s['id'], 'student_card_number', s['student_card_number'],
                  'last_name', s['last_name'], 'first_name', s['first_name'], 'patronymic', s['patronymic'],
                  'group', s['group'], 'specialty_code', sp['code'], 'specialty', sp['name'],
                  'email', s['email'], 'phone', s['phone'], 'enrollment_date', s['enrollment_date'],
                  'status', s['status']),
             resp('EXPIRE', key, 7200)]
for day in ('2026-03-16', '2026-03-17'):                                  # расписание группы на день, TTL 1 ч
    rows = sorted([x for x in ds['schedule'] if x['group_id'] == g1['id'] and x['scheduled_date'] == day],
                  key=lambda x: x['start_time'])
    key = f'schedule:{g1["id"]}:{day}'
    args = []
    for n, x in enumerate(rows, start=1):
        args += [f'slot_{n}', json.dumps({'schedule_id': x['id'], 'start_time': x['start_time'], 'end_time': x['end_time'],
                                          'course': x['course_name'], 'type': x['lecture_type'],
                                          'classroom': x['classroom'], 'teacher': x['teacher_name']}, ensure_ascii=False)]
    cmds += [resp('HSET', key, *args), resp('EXPIRE', key, 3600)]
today = sorted([x for x in ds['schedule'] if x['group_id'] == g1['id'] and x['scheduled_date'] == '2026-03-16'],
               key=lambda x: x['start_time'])
key = f'today_schedule:{g1["id"]}'                                        # список занятий «на сегодня», до конца дня
cmds += [resp('RPUSH', key, *[f'{x["start_time"]} {x["course_name"]} ({x["classroom"]})' for x in today]),
         resp('EXPIREAT', key, int(datetime.now().replace(hour=23, minute=59, second=59).timestamp()))]
open_class = today[0]                                                     # буфер отметок открытого занятия, TTL 30 мин
marks = []
for s in [x for x in ds['students'] if x['group'] == 'БСБО-01-23'][:12]:
    marks += [s['student_card_number'], 'present' if int(s['id'][:8], 16) % 5 else 'absent']
cmds += [resp('HSET', f'attendance:{open_class["id"]}', *marks), resp('EXPIRE', f'attendance:{open_class["id"]}', 1800)]
for user_id, role, name in (('teacher-belyaev', 'teacher', 'Беляев А.Н.'), ('student-23b0101', 'student', 'Судовский А.Л.')):
    cmds += [resp('SET', f'session:{user_id}', json.dumps({'user_id': user_id, 'role': role, 'name': name,
                                                           'issued_at': int(time.time())}, ensure_ascii=False),
                  'EX', 86400)]
(D / 'redis_cache.resp').write_bytes(b''.join(cmds))


# ---------------- Neo4j ----------------
def q(v):
    if isinstance(v, dict):
        return '{' + ', '.join(f'{k}: {q(x)}' for k, x in v.items()) + '}'
    if isinstance(v, list):
        return '[' + ', '.join(q(x) for x in v) + ']'
    return json.dumps(v, ensure_ascii=False)


nodes = {
    'University': [{'id': U['id'], 'name': U['name'], 'short_name': U['short_name']}],
    'Institute': [{'id': i['id'], 'name': i['name'], 'short_name': i['short_name'], 'dean': i['dean']} for i in ds['institutes']],
    'Department': [{'id': d['id'], 'name': d['name'], 'short_name': d['short_name'], 'head': d['head']} for d in ds['departments']],
    'Specialty': [{'id': s['id'], 'name': s['name'], 'code': s['code'], 'degree_level': s['degree_level']} for s in ds['specialties']],
    'LectureCourse': [{'id': c['id'], 'name': c['name'], 'semester': c['semester'], 'total_hours': c['total_hours'],
                       'is_elective': c['is_elective'], 'tags': c['tags']} for c in ds['courses']],
    'Group': [{'id': g['id'], 'name': g['name'], 'enrollment_year': g['enrollment_year']} for g in ds['groups']],
    'Student': [{'id': s['id'], 'student_card_number': s['student_card_number'],
                 'name': f'{s["last_name"]} {s["first_name"][0]}.{s["patronymic"][0]}.'} for s in ds['students']],
}
cy = ['// Ограничения уникальности по id: одинаковый UUID с PostgreSQL']
for label in nodes:
    cy.append(f'CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE;')
for label, rows in nodes.items():
    cy.append(f'UNWIND {q(rows)} AS r MERGE (n:{label} {{id: r.id}}) SET n += r;')
rels = [
    ('University', 'HAS_INSTITUTE', 'Institute', [{'a': U['id'], 'b': i['id']} for i in ds['institutes']]),
    ('Institute', 'HAS_DEPARTMENT', 'Department', [{'a': inst[d['institute']]['id'], 'b': d['id']} for d in ds['departments']]),
    ('Specialty', 'HAS_COURSE', 'LectureCourse', [{'a': c['specialty_id'], 'b': c['id']} for c in ds['courses']]),
    ('Department', 'TEACHES', 'LectureCourse', [{'a': c['department_id'], 'b': c['id']} for c in ds['courses']]),
    ('Specialty', 'HAS_GROUP', 'Group', [{'a': g['specialty_id'], 'b': g['id']} for g in ds['groups']]),
    ('Student', 'MEMBER_OF', 'Group', [{'a': s['id'], 'b': s['group_id']} for s in ds['students']]),
    ('Student', 'CHOSE', 'LectureCourse', [{'a': a, 'b': b} for a, b in el_rows]),
]
for a, r, b, rows in rels:
    cy.append(f'UNWIND {q(rows)} AS r MATCH (a:{a} {{id: r.a}}), (b:{b} {{id: r.b}}) MERGE (a)-[:{r}]->(b);')
cy.append('UNWIND ' + q([{'a': dept[d]['id'], 'b': by_code[s]['id'], 'p': p} for d, s, p in dept_spec]) +
          ' AS r MATCH (a:Department {id: r.a}), (b:Specialty {id: r.b}) MERGE (a)-[x:HAS_SPECIALTY]->(b) SET x.is_primary = r.p;')
w('neo4j_load.cypher', '\n'.join(cy) + '\n')

# ---------------- MongoDB ----------------
mats_by_lecture = {}
for m in ds['materials']:
    mats_by_lecture.setdefault(m['lecture_id'], []).append(m)
mdocs = []
for x in ds['lectures']:
    ms = mats_by_lecture.get(x['id'], [])
    text = next((m['content_text'] for m in ms if m['type'] == 'text'), '')
    mdocs.append({
        '_id': x['id'], 'lecture_id': x['id'], 'course_id': x['course_id'], 'course_name': x['course_name'],
        'lecture_title': x['title'], 'lecture_type': x['lecture_type'], 'order_number': x['order_number'],
        'content': {'format': 'markdown', 'text': text, 'word_count': len(text.split()),
                    'reading_time_minutes': max(1, round(len(text.split()) / 180))},
        'materials': [{k: v for k, v in m.items() if k not in ('id', 'lecture_id', 'content_text')} for m in ms
                      if m['type'] != 'text'],
        'metadata': {'author': x['teacher'], 'last_updated': '2026-03-10T14:00:00Z', 'version': 1,
                     'tags': x['tags'], 'department': x['department'],
                     'difficulty': {'lecture': 'basic', 'practice': 'intermediate', 'lab': 'advanced'}[x['lecture_type']]}})
gdocs = []
for g in ds['groups']:
    sp = by_code[g['specialty_code']]
    members = [s for s in ds['students'] if s['group'] == g['name']]
    gdocs.append({'_id': g['id'], 'name': g['name'], 'enrollment_year': g['enrollment_year'], 'curator': g['curator'],
                  'specialty': {'id': sp['id'], 'code': sp['code'], 'name': sp['name']},
                  'students_count': len(members),
                  'students': [{'id': s['id'], 'student_card_number': s['student_card_number'],
                                'name': f'{s["last_name"]} {s["first_name"]} {s["patronymic"]}', 'status': s['status'],
                                'electives': s['electives']} for s in members]})
w('mongo_load.js', f'''// Коллекция lecture_materials: один документ — все материалы одного занятия (агрегат)
db.lecture_materials.insertMany({json.dumps(mdocs, ensure_ascii=False)});
db.lecture_materials.updateMany({{}}, [{{$set: {{"metadata.last_updated": {{$toDate: "$metadata.last_updated"}}}}}}]);
db.lecture_materials.createIndex({{course_id: 1, order_number: 1}});
db.lecture_materials.createIndex({{"metadata.tags": 1}});
db.lecture_materials.createIndex({{"materials.type": 1}});
// Коллекция student_groups: группа с составом — документ-композиция (как в ПР №2)
db.student_groups.insertMany({json.dumps(gdocs, ensure_ascii=False)});
db.student_groups.createIndex({{name: 1}}, {{unique: true}});
''')

# ---------------- Elasticsearch ----------------
w('es_lectures_mapping.json', json.dumps({
    'settings': {'number_of_shards': 1, 'number_of_replicas': 0, 'analysis': {
        'analyzer': {'russian_custom': {'type': 'custom', 'tokenizer': 'standard',
                                        'filter': ['lowercase', 'russian_stop', 'russian_stemmer']}},
        'filter': {'russian_stop': {'type': 'stop', 'stopwords': '_russian_'},
                   'russian_stemmer': {'type': 'stemmer', 'language': 'russian'}}}},
    'mappings': {'properties': {
        'lecture_id': {'type': 'keyword'}, 'course_id': {'type': 'keyword'},
        'course_name': {'type': 'text', 'analyzer': 'russian_custom', 'fields': {'keyword': {'type': 'keyword'}}},
        'title': {'type': 'text', 'analyzer': 'russian_custom', 'fields': {'keyword': {'type': 'keyword'}}},
        'annotation': {'type': 'text', 'analyzer': 'russian_custom'},
        'content_text': {'type': 'text', 'analyzer': 'russian_custom'},
        'tech_requirements': {'type': 'text', 'analyzer': 'russian_custom'},
        'lecture_type': {'type': 'keyword'}, 'order_number': {'type': 'integer'},
        'specialty_code': {'type': 'keyword'}, 'department': {'type': 'keyword'}, 'semester': {'type': 'integer'},
        'tags': {'type': 'keyword'}, 'updated_at': {'type': 'date'}}},
}, ensure_ascii=False, indent=2))
lines = []
for x in ds['lectures']:
    lines.append(json.dumps({'index': {'_index': 'lectures', '_id': x['id']}}))
    lines.append(json.dumps({'lecture_id': x['id'], 'course_id': x['course_id'], 'course_name': x['course_name'],
                             'title': x['title'], 'annotation': x['annotation'], 'content_text': x['content_text'],
                             'tech_requirements': x['tech_requirements'], 'lecture_type': x['lecture_type'],
                             'order_number': x['order_number'], 'specialty_code': x['specialty_code'],
                             'department': x['department'], 'semester': 6, 'tags': x['tags'],
                             'updated_at': '2026-03-10T14:00:00Z'}, ensure_ascii=False))
w('es_lectures.ndjson', '\n'.join(lines) + '\n')

print({k: (len(v) if isinstance(v, list) else 1) for k, v in ds.items()}, '| выборов курсов:', len(el_rows),
      '| команд Redis:', len(cmds), '| документов Mongo:', len(mdocs) + len(gdocs))
