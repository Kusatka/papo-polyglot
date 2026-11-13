"""Точные аналитические выборки ЛР2–3 по источнику истины PostgreSQL.

Слушатели: студенты группы для обязательного курса, только выбравшие курс
для факультатива. План часов строится по расписанию, посещения LEFT JOIN:
пропущенная отметка не удаляет запланированное занятие.
"""
import os
import time

import psycopg
from psycopg.rows import dict_row

from app.lab1.query import Trace

PG_DSN = os.environ.get('PG_DSN', 'postgresql://admin:secret@postgres:5432/university_system')

ROOM_SQL = """
SELECT to_jsonb(c) AS course, to_jsonb(l) AS lecture,
       count(DISTINCT st.id) AS listeners,
       coalesce(jsonb_agg(DISTINCT jsonb_build_object('id', g.id, 'name', g.name))
                FILTER (WHERE g.id IS NOT NULL), '[]') AS groups
FROM lecture_courses c
JOIN lectures l ON l.course_id = c.id
LEFT JOIN student_groups g ON g.specialty_id = c.specialty_id
 AND g.enrollment_year = %(academic_year)s - %(study_year)s + 1
LEFT JOIN students st ON st.group_id = g.id AND st.status = 'active'
 AND (NOT c.is_elective OR EXISTS
      (SELECT 1 FROM student_electives e WHERE e.student_id = st.id AND e.course_id = c.id))
WHERE c.id = %(course_id)s::uuid AND c.semester = %(semester)s
GROUP BY c.id, l.id
ORDER BY l.order_number, l.id
"""

HOURS_SQL = """
SELECT to_jsonb(st) AS student, to_jsonb(c) AS course,
       count(DISTINCT s.id) * 2 AS planned_hours,
       count(DISTINCT s.id) FILTER (WHERE a.is_present) * 2 AS attended_hours
FROM students st
JOIN student_groups g ON g.id = st.group_id
JOIN lecture_courses c ON c.specialty_id = g.specialty_id
 AND (NOT c.is_elective OR EXISTS
      (SELECT 1 FROM student_electives e WHERE e.student_id = st.id AND e.course_id = c.id))
JOIN lectures l ON l.course_id = c.id AND l.lecture_type = 'lecture'
 AND l.tags @> ARRAY[%(tag)s]::text[]
LEFT JOIN schedule s ON s.lecture_id = l.id AND s.group_id = g.id
 AND s.status <> 'cancelled' AND s.scheduled_date BETWEEN %(date_from)s AND %(date_to)s
LEFT JOIN attendance a ON a.schedule_id = s.id AND a.student_id = st.id
 AND a.week_start_date = s.week_start_date
 AND a.week_start_date BETWEEN %(week_from)s AND %(date_to)s
WHERE g.name = %(group_name)s
GROUP BY st.id, c.id
ORDER BY st.last_name, st.first_name, st.id, c.name, c.id
"""


def rooms_report(course_id, semester, study_year, academic_year):
    trace = Trace()
    started = time.perf_counter()
    params = dict(course_id=str(course_id), semester=semester, study_year=study_year,
                  academic_year=academic_year)
    with psycopg.connect(PG_DSN, row_factory=dict_row) as conn:
        rows = conn.execute(ROOM_SQL, params).fetchall()
    trace.add('PostgreSQL', 'Курс и занятия; слушатели по специальности, году набора и выбору курса',
              f'занятий: {len(rows)}', started,
              {'enrollment_year': academic_year - study_year + 1})
    return {'parameters': params, 'academic_year_meaning': 'год начала учебного года',
            'capacity_policy': 'одно занятие для всех слушателей курса выбранного года обучения',
            'classes': rows, 'trace': trace.steps}


def hours_report(group_name, date_from, date_to, tag):
    from datetime import timedelta
    trace = Trace()
    started = time.perf_counter()
    params = dict(group_name=group_name, date_from=date_from, date_to=date_to, tag=tag,
                  week_from=date_from - timedelta(days=date_from.weekday()))
    with psycopg.connect(PG_DSN, row_factory=dict_row) as conn:
        # Один снимок для карточки группы и расчёта.
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        group = conn.execute('SELECT * FROM student_groups WHERE name = %s', (group_name,)).fetchone()
        rows = conn.execute(HOURS_SQL, params).fetchall() if group else []
    trace.add('PostgreSQL', 'Расписание лекций с тегом; LEFT JOIN посещений, отсечение недельных партиций',
              f'строк студент–курс: {len(rows)}', started,
              {'academic_hours_per_lecture': 2, 'missing_mark': 'не посещено'})
    return {'group': group, 'period': {'from': date_from, 'to': date_to}, 'tag': tag,
            'students_courses': rows, 'trace': trace.steps}
