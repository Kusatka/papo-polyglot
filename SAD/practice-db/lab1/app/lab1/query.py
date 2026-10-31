"""ЛР №1. Отчёт о 10 студентах с минимальным процентом посещения лекций, содержащих заданный термин
или фразу, за период обучения.

Порядок выборки (каждый шаг попадает в трассировку ответа и в журнал сервиса):
  1. Elasticsearch, индекс lectures — лекции (lecture_type = lecture), в названии, аннотации или тексте
     которых встречается термин/фраза: multi_match type=phrase с русским анализатором (словоформы),
     постраничный проход search_after — без молчаливого усечения выдачи.
  2. PostgreSQL — посещаемость найденных лекций за период: attendance ⋈ schedule по id лекций,
     условие на week_start_date отсекает партиции журнала (partition pruning); агрегат на стороне СУБД,
     сортировка по проценту посещения, первые N.
  3. Redis, база №2 — полные карточки найденных студентов по ключам student:{id} (cache-aside);
     промахи читаются из PostgreSQL одним запросом и кладутся в кэш с TTL 2 ч.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import date, timedelta

import httpx
import psycopg
import redis
from psycopg.rows import dict_row

log = logging.getLogger('lab1')
ES_URL = os.environ.get('ES_URL', 'http://elasticsearch:9200')
PG_DSN = os.environ.get('PG_DSN', 'postgresql://admin:secret@postgres:5432/university_system')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://:mypassword@redis:6379/2')
CACHE_TTL = 7200
PAGE = 200
STUDENT_FIELDS = ['id', 'student_card_number', 'last_name', 'first_name', 'patronymic', 'group', 'specialty_code',
                  'specialty', 'email', 'phone', 'enrollment_date', 'status']

_redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)


class Trace:
    def __init__(self):
        self.steps = []

    def add(self, store: str, action: str, result: str, started: float, details=None):
        ms = round((time.perf_counter() - started) * 1000, 1)
        self.steps.append({'step': len(self.steps) + 1, 'store': store, 'action': action, 'result': result,
                           'ms': ms, **({'details': details} if details is not None else {})})
        log.info('шаг %d [%s] %s -> %s (%.1f мс)', len(self.steps), store, action, result, ms)


def find_lectures(term: str, trace: Trace) -> list[dict]:
    t0 = time.perf_counter()
    body = {
        'size': PAGE, 'track_total_hits': True,
        '_source': ['lecture_id', 'course_id', 'course_name', 'title', 'specialty_code'],
        'query': {'bool': {
            'must': [{'multi_match': {'query': term, 'type': 'phrase',
                                      'fields': ['title^3', 'annotation^2', 'content_text']}}],
            'filter': [{'term': {'lecture_type': 'lecture'}}]}},
        'highlight': {'fields': {'content_text': {'fragment_size': 120, 'number_of_fragments': 1}, 'title': {}}},
        'sort': [{'lecture_id': 'asc'}],
    }
    lectures, total = [], None
    with httpx.Client(base_url=ES_URL, timeout=10) as es:
        while True:
            resp = es.post('/lectures/_search', json=body)
            resp.raise_for_status()
            data = resp.json()['hits']
            total = data['total']['value'] if total is None else total
            for h in data['hits']:
                src = h['_source']
                hl = h.get('highlight', {})
                lectures.append({**src, 'highlight': (hl.get('title') or hl.get('content_text') or [''])[0]})
            if len(data['hits']) < PAGE:
                break
            body['search_after'] = data['hits'][-1]['sort']        # следующая страница
    courses = sorted({(x['specialty_code'], x['course_name']) for x in lectures})
    trace.add('Elasticsearch', f'multi_match(phrase) «{term}» по title/annotation/content_text, lecture_type=lecture',
              f'найдено лекций: {len(lectures)} из {total}, курсов: {len(courses)}', t0,
              {'courses': [{'specialty': s, 'course': c,
                            'lectures': sum(1 for x in lectures if x['course_name'] == c and x['specialty_code'] == s)}
                           for s, c in courses],
               'lecture_ids': [x['lecture_id'] for x in lectures]})
    return lectures


ATTENDANCE_SQL = """
SELECT a.student_id::text AS student_id,
       count(*)                                 AS total,
       count(*) FILTER (WHERE a.is_present)     AS attended,
       round(100.0 * count(*) FILTER (WHERE a.is_present) / count(*), 1) AS attendance_pct,
       array_agg(DISTINCT lc.name ORDER BY lc.name) AS term_courses
FROM attendance a
JOIN schedule s         ON s.id = a.schedule_id
JOIN lectures l         ON l.id = s.lecture_id
JOIN lecture_courses lc ON lc.id = l.course_id
WHERE s.lecture_id = ANY(%(ids)s::uuid[])
  AND a.week_start_date BETWEEN %(week_from)s AND %(date_to)s       -- отсечение партиций журнала
  AND s.scheduled_date  BETWEEN %(date_from)s AND %(date_to)s
GROUP BY a.student_id
ORDER BY attendance_pct, total DESC, a.student_id
LIMIT %(limit)s
"""
SCOPE_SQL = """
SELECT count(DISTINCT s.id) AS classes, count(*) AS marks, count(DISTINCT a.student_id) AS students
FROM attendance a JOIN schedule s ON s.id = a.schedule_id
WHERE s.lecture_id = ANY(%(ids)s::uuid[])
  AND a.week_start_date BETWEEN %(week_from)s AND %(date_to)s
  AND s.scheduled_date  BETWEEN %(date_from)s AND %(date_to)s
"""


def attendance_top(ids: list[str], date_from: date, date_to: date, limit: int, trace: Trace) -> tuple[list[dict], dict]:
    t0 = time.perf_counter()
    params = {'ids': ids, 'date_from': date_from, 'date_to': date_to, 'limit': limit,
              'week_from': date_from - timedelta(days=date_from.weekday())}      # понедельник первой недели
    with psycopg.connect(PG_DSN, row_factory=dict_row) as conn:
        scope = conn.execute(SCOPE_SQL, params).fetchone()
        rows = conn.execute(ATTENDANCE_SQL, params).fetchall()
        names = [r['relname'] for r in conn.execute(
            "SELECT c.relname FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid "
            "WHERE i.inhparent = 'attendance'::regclass").fetchall()]
    # недельные партиции attendance_wГГГГ_ММ_ДД, попадающие в период (их и читает запрос после отсечения)
    weeks = [date.fromisoformat(n[12:].replace('_', '-')) for n in names if n.startswith('attendance_w')]
    parts = {'n': sum(1 for w in weeks if params['week_from'] <= w <= date_to)}
    trace.add('PostgreSQL', f'attendance JOIN schedule по {len(ids)} лекциям за {date_from}…{date_to}, '
                            f'week_start_date ≥ {params["week_from"]}',
              f'занятий: {scope["classes"]}, отметок: {scope["marks"]}, студентов: {scope["students"]}, '
              f'недельных партиций в периоде: {parts["n"]}; отобрано {len(rows)} с минимальной посещаемостью', t0,
              [{k: (float(v) if k == 'attendance_pct' else v) for k, v in r.items()} for r in rows])
    return rows, scope


STUDENTS_SQL = """
SELECT st.id::text AS id, st.student_card_number, st.last_name, st.first_name, st.patronymic,
       g.name AS group, sp.code AS specialty_code, sp.name AS specialty, st.email, st.phone,
       st.enrollment_date::text AS enrollment_date, st.status
FROM students st JOIN student_groups g ON g.id = st.group_id JOIN specialties sp ON sp.id = g.specialty_id
WHERE st.id = ANY(%(ids)s::uuid[])
"""


def student_cards(ids: list[str], trace: Trace) -> dict[str, dict]:
    t0 = time.perf_counter()
    pipe = _redis.pipeline()
    for sid in ids:
        pipe.hgetall(f'student:{sid}')
    cached = dict(zip(ids, pipe.execute()))
    cards = {sid: c for sid, c in cached.items() if c and all(f in c for f in STUDENT_FIELDS)}
    misses = [sid for sid in ids if sid not in cards]
    if misses:
        with psycopg.connect(PG_DSN, row_factory=dict_row) as conn:
            rows = conn.execute(STUDENTS_SQL, {'ids': misses}).fetchall()
        pipe = _redis.pipeline()
        for r in rows:
            card = {k: '' if r[k] is None else str(r[k]) for k in STUDENT_FIELDS}
            cards[card['id']] = card
            pipe.hset(f'student:{card["id"]}', mapping=card)
            pipe.expire(f'student:{card["id"]}', CACHE_TTL)
        pipe.execute()
    trace.add('Redis', f'HGETALL student:{{id}} для {len(ids)} студентов (cache-aside, TTL {CACHE_TTL // 3600} ч)',
              f'из кэша: {len(ids) - len(misses)}, промахов: {len(misses)}'
              + (f' → прочитано из PostgreSQL и записано в Redis: {len(misses)}' if misses else ''), t0)
    return cards


def build_report(term: str, date_from: date, date_to: date, limit: int = 10) -> dict:
    trace = Trace()
    lectures = find_lectures(term, trace)
    rows, scope = attendance_top([x['lecture_id'] for x in lectures], date_from, date_to, limit, trace) if lectures else ([], {})
    cards = student_cards([r['student_id'] for r in rows], trace) if rows else {}
    t0 = time.perf_counter()
    top = []
    for i, r in enumerate(rows, start=1):
        c = cards.get(r['student_id'], {})
        top.append({
            'rank': i,
            'student': {'id': r['student_id'], 'student_card_number': c.get('student_card_number'),
                        'full_name': ' '.join(filter(None, [c.get('last_name'), c.get('first_name'), c.get('patronymic')])),
                        'group': c.get('group'), 'specialty': f'{c.get("specialty_code")} {c.get("specialty")}',
                        'email': c.get('email'), 'phone': c.get('phone'), 'enrollment_date': c.get('enrollment_date'),
                        'status': c.get('status')},
            'attended': r['attended'], 'total': r['total'], 'attendance_pct': float(r['attendance_pct']),
            'term_in_courses': r['term_courses'],
        })
    by_course = {}
    for x in lectures:
        by_course.setdefault((x['specialty_code'], x['course_name']), []).append({'title': x['title'], 'fragment': x['highlight']})
    report = {
        'term': term,
        'period': {'from': date_from.isoformat(), 'to': date_to.isoformat()},
        'lectures_found': len(lectures),
        'term_in_courses': [{'specialty': s, 'course': c, 'lectures': len(v), 'examples': v[:2]}
                            for (s, c), v in sorted(by_course.items())],
        'scope': {k: int(v) for k, v in scope.items()} if scope else {},
        'students': top,
    }
    trace.add('Сервис ЛР №1', 'сборка отчёта', f'в отчёте {len(top)} студентов', t0)
    report['trace'] = trace.steps
    return report
